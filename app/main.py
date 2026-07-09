import json
import os
import httpx
import threading
import time
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Optional, Tuple

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import Emergencia, Agente, Usuario, Despacho, PosicaoGPS
from app.schemas import (
    UsuarioCreate, UsuarioResponse, PushTokenUpdate,
    EmergenciaCreate, EmergenciaResponse,
    AgenteFrota,
    DespachoCreate, DespachoResponse, DespachoStatusUpdate,
    PosicaoCreate, PosicaoResponse,
    TriagemRequest, TriagemResponse,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SalvAI API",
    version="1.0.0-mvp",
    description=(
        "Plataforma SaaS B2G de gestão integrada de emergências — CAD digital, "
        "triagem por IA, despacho automático e rastreamento de frota. "
        "Depósitos INPI: BR 10 2026 006948 5 e adições."
    ),
    redirect_slashes=True,
)


@app.on_event("startup")
def popular_banco_se_vazio():
    """Roda o seed automaticamente se nao houver agentes (util em ambientes
    efemeros como Railway onde o SQLite zera a cada deploy)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Agente).count() == 0:
            from app.seed import seed
            seed()
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verificar_api_key(x_api_key: str = Header(None)):
    chave = os.environ.get("SALVAI_API_KEY")
    if not chave or x_api_key != chave:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente")


DESPACHO_STATUS_VALIDOS = {"a_caminho", "no_local", "finalizado"}

# Registra início e duração das simulações por despacho_id
_sim_info: dict = {}

def _simular_movimento(despacho_id: int, agente_id: int,
                        lat0: float, lon0: float,
                        lat1: float, lon1: float,
                        duracao: int = 120):
    """Thread: interpola GPS do agente de (lat0,lon0) até (lat1,lon1) em `duracao` segundos."""
    from app.database import SessionLocal
    steps = duracao // 3
    for i in range(1, steps + 1):
        if _sim_info.get(despacho_id, {}).get("stop"):
            break
        t = i / steps
        lat = lat0 + (lat1 - lat0) * t
        lon = lon0 + (lon1 - lon0) * t
        db = SessionLocal()
        try:
            pos = PosicaoGPS(id_agente=agente_id, lat=lat, lon=lon)
            db.add(pos)
            db.commit()
        finally:
            db.close()
        time.sleep(3)
    _sim_info.pop(despacho_id, None)


# ──────────────────────────── helpers ────────────────────────────

def enviar_push(token: str, title: str, body: str):
    """Envia push notification via Expo Push API."""
    if not token or not token.startswith("ExponentPushToken"):
        return
    try:
        httpx.post(
            "https://exp.host/--/api/v2/push/send",
            json={"to": token, "title": title, "body": body, "sound": "default"},
            timeout=5,
        )
    except Exception:
        pass


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Retorna a distancia em km entre dois pontos (lat/lon) usando Haversine."""
    R = 6371.0  # raio da Terra em km
    rlat1, rlon1, rlat2, rlon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ──────────────────────────── POST /usuario ──────────────────────

@app.post("/usuario", response_model=UsuarioResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.cpf == dados.cpf).first()
    if existente:
        return existente
    usuario = Usuario(cpf=dados.cpf, nome=dados.nome)
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


# ──────────────────────────── PUT /usuario/{id}/push-token ────────

@app.put("/usuario/{usuario_id}/push-token", dependencies=[Depends(verificar_api_key)])
def salvar_push_token(usuario_id: int, dados: PushTokenUpdate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    usuario.push_token = dados.push_token
    db.commit()
    return {"ok": True}


# ──────────────────────────── POST /emergencia ────────────────────

@app.post("/emergencia", response_model=EmergenciaResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def criar_emergencia(dados: EmergenciaCreate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == dados.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    emergencia = Emergencia(**dados.model_dump())
    db.add(emergencia)
    db.commit()
    db.refresh(emergencia)

    # Auto-despacho: tenta atribuir agente mais proximo. Se nao houver, segue como aberta.
    try:
        _executar_despacho(emergencia, db)
        db.refresh(emergencia)
    except Exception:
        pass

    return emergencia


# ──────────────────────────── GET /emergencia/{id} ───────────────

@app.get("/emergencia/{emergencia_id}", response_model=EmergenciaResponse)
def buscar_emergencia(emergencia_id: int, db: Session = Depends(get_db)):
    emergencia = db.query(Emergencia).filter(Emergencia.id == emergencia_id).first()
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia nao encontrada")
    return emergencia


# ──────────────────────── GET /emergencia/{id}/acompanhamento ─────

from app.schemas import AcompanhamentoResponse

@app.get("/emergencia/{emergencia_id}/acompanhamento", response_model=AcompanhamentoResponse)
def acompanhamento_emergencia(emergencia_id: int, db: Session = Depends(get_db)):
    emergencia = db.query(Emergencia).filter(Emergencia.id == emergencia_id).first()
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia nao encontrada")

    despacho = (
        db.query(Despacho)
        .filter(
            Despacho.id_emergencia == emergencia_id,
            Despacho.status.in_(["a_caminho", "no_local"]),
        )
        .order_by(Despacho.id.desc())
        .first()
    )

    if not despacho:
        return AcompanhamentoResponse(status=emergencia.status)

    agente = db.query(Agente).filter(Agente.id == despacho.id_agente).first()
    ultima_pos = (
        db.query(PosicaoGPS)
        .filter(PosicaoGPS.id_agente == despacho.id_agente)
        .order_by(PosicaoGPS.timestamp.desc())
        .first()
    )

    eta = None
    sim = _sim_info.get(despacho.id)
    if sim:
        eta = max(0, int(sim["start"] + sim["duracao"] - time.time()))

    dist = None
    if ultima_pos:
        dist = round(haversine(ultima_pos.lat, ultima_pos.lon, emergencia.lat, emergencia.lon), 2)

    return AcompanhamentoResponse(
        status=emergencia.status,
        despacho_id=despacho.id,
        agente_nome=agente.nome if agente else None,
        tipo_recurso=agente.tipo_recurso if agente else None,
        agente_lat=ultima_pos.lat if ultima_pos else None,
        agente_lon=ultima_pos.lon if ultima_pos else None,
        eta_segundos=eta,
        distancia_km=dist,
    )


# ──────────────────────────── GET /frota ──────────────────────────

@app.get("/frota", response_model=list[AgenteFrota])
def listar_frota(db: Session = Depends(get_db)):
    agentes = db.query(Agente).all()
    resultado = []
    for ag in agentes:
        despacho_ativo = (
            db.query(Despacho)
            .filter(Despacho.id_agente == ag.id, Despacho.status != "finalizado")
            .order_by(Despacho.created_at.desc())
            .first()
        )
        ultima_pos = (
            db.query(PosicaoGPS)
            .filter(PosicaoGPS.id_agente == ag.id)
            .order_by(PosicaoGPS.timestamp.desc())
            .first()
        )
        resultado.append(AgenteFrota(
            id=ag.id,
            nome=ag.nome,
            matricula=ag.matricula,
            tipo_recurso=ag.tipo_recurso,
            status=ag.status,
            viaturas=ag.viaturas,
            despacho_id=despacho_ativo.id if despacho_ativo else None,
            emergencia_id=despacho_ativo.id_emergencia if despacho_ativo else None,
            latitude=ultima_pos.lat if ultima_pos else None,
            longitude=ultima_pos.lon if ultima_pos else None,
        ))
    return resultado


# ──────────────────────────── GET /emergencias (dashboard) ────────

@app.get("/emergencias")
def listar_emergencias(limit: int = 50, db: Session = Depends(get_db)):
    """Lista emergências para o dashboard do gestor (mais recentes primeiro)."""
    emergencias = (
        db.query(Emergencia)
        .order_by(Emergencia.created_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for e in emergencias:
        despacho = (
            db.query(Despacho)
            .filter(Despacho.id_emergencia == e.id)
            .order_by(Despacho.id.desc())
            .first()
        )
        agente_nome = None
        if despacho:
            ag = db.query(Agente).filter(Agente.id == despacho.id_agente).first()
            agente_nome = ag.nome if ag else None
        usuario = db.query(Usuario).filter(Usuario.id == e.id_usuario).first()
        out.append({
            "id": e.id,
            "tipo": e.tipo,
            "gravidade": e.gravidade,
            "status": e.status,
            "lat": e.lat,
            "lon": e.lon,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "usuario_nome": usuario.nome if usuario else None,
            "despacho_id": despacho.id if despacho else None,
            "despacho_status": despacho.status if despacho else None,
            "agente_nome": agente_nome,
        })
    return out


# ──────────────────────────── helper: executar despacho ──────────

TIPO_EMERGENCIA_PARA_RECURSO = {
    "policia": "policia",
    "medica": "ambulancia",
}

def _executar_despacho(emergencia: Emergencia, db: Session) -> Optional[Tuple[Despacho, Agente, float]]:
    """Encontra o agente disponivel mais proximo e cria o despacho.
    Retorna (despacho, agente, distancia_km) ou None se nenhum disponivel."""
    tipo_recurso = TIPO_EMERGENCIA_PARA_RECURSO.get(emergencia.tipo)

    query = db.query(Agente).filter(Agente.status == "disponivel")
    if tipo_recurso:
        query = query.filter(Agente.tipo_recurso == tipo_recurso)
    agentes_disponiveis = query.all()

    # Fallback: qualquer agente disponivel se nao houver do tipo correto
    if not agentes_disponiveis:
        agentes_disponiveis = (
            db.query(Agente).filter(Agente.status == "disponivel").all()
        )
    if not agentes_disponiveis:
        return None

    melhor_agente = None
    menor_distancia = float("inf")

    for agente in agentes_disponiveis:
        ultima_pos = (
            db.query(PosicaoGPS)
            .filter(PosicaoGPS.id_agente == agente.id)
            .order_by(PosicaoGPS.timestamp.desc())
            .first()
        )
        if not ultima_pos:
            continue
        dist = haversine(emergencia.lat, emergencia.lon, ultima_pos.lat, ultima_pos.lon)
        if dist < menor_distancia:
            menor_distancia = dist
            melhor_agente = agente

    if not melhor_agente:
        # Fallback: pega o primeiro disponivel mesmo sem GPS
        melhor_agente = agentes_disponiveis[0]
        menor_distancia = 0.0

    despacho = Despacho(
        id_emergencia=emergencia.id,
        id_agente=melhor_agente.id,
        status="a_caminho",
    )
    melhor_agente.status = "em_atendimento"
    emergencia.status = "em_atendimento"

    db.add(despacho)
    db.commit()
    db.refresh(despacho)

    # Inicia simulação de movimento do agente
    ultima_pos_agente = (
        db.query(PosicaoGPS)
        .filter(PosicaoGPS.id_agente == melhor_agente.id)
        .order_by(PosicaoGPS.timestamp.desc())
        .first()
    )
    if ultima_pos_agente:
        duracao_sim = 120
        _sim_info[despacho.id] = {"start": time.time(), "duracao": duracao_sim}
        t = threading.Thread(
            target=_simular_movimento,
            args=(despacho.id, melhor_agente.id,
                  ultima_pos_agente.lat, ultima_pos_agente.lon,
                  emergencia.lat, emergencia.lon,
                  duracao_sim),
            daemon=True,
        )
        t.start()

    usuario = db.query(Usuario).filter(Usuario.id == emergencia.id_usuario).first()
    if usuario and usuario.push_token:
        enviar_push(
            usuario.push_token,
            "Viatura despachada!",
            f"Agente {melhor_agente.nome} a caminho ({round(menor_distancia, 1)} km)",
        )

    return despacho, melhor_agente, menor_distancia


# ──────────────────────────── POST /despacho ──────────────────────

@app.post("/despacho", response_model=DespachoResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def criar_despacho(dados: DespachoCreate, db: Session = Depends(get_db)):
    emergencia = db.query(Emergencia).filter(
        Emergencia.id == dados.id_emergencia
    ).first()
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia nao encontrada")

    resultado = _executar_despacho(emergencia, db)
    if resultado is None:
        raise HTTPException(status_code=409, detail="Nenhum agente disponivel")

    despacho, melhor_agente, menor_distancia = resultado
    return DespachoResponse(
        id=despacho.id,
        id_emergencia=despacho.id_emergencia,
        id_agente=despacho.id_agente,
        status=despacho.status,
        created_at=despacho.created_at,
        distancia_km=round(menor_distancia, 2),
        agente_nome=melhor_agente.nome,
    )


# ──────────────────────────── PATCH /despacho/{id}/status ─────────

@app.patch(
    "/despacho/{despacho_id}/status",
    response_model=DespachoResponse,
    dependencies=[Depends(verificar_api_key)],
)
def atualizar_status_despacho(
    despacho_id: int,
    dados: DespachoStatusUpdate,
    db: Session = Depends(get_db),
):
    if dados.status not in DESPACHO_STATUS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Status invalido. Valores aceitos: {', '.join(sorted(DESPACHO_STATUS_VALIDOS))}",
        )

    despacho = db.query(Despacho).filter(Despacho.id == despacho_id).first()
    if not despacho:
        raise HTTPException(status_code=404, detail="Despacho nao encontrado")

    despacho.status = dados.status

    # Se finalizado, liberar o agente
    if dados.status == "finalizado":
        agente = db.query(Agente).filter(Agente.id == despacho.id_agente).first()
        if agente:
            agente.status = "disponivel"
        emergencia = db.query(Emergencia).filter(
            Emergencia.id == despacho.id_emergencia
        ).first()
        if emergencia:
            emergencia.status = "finalizada"

    db.commit()

    # Push notification para o cidadao
    emergencia = db.query(Emergencia).filter(Emergencia.id == despacho.id_emergencia).first()
    if emergencia:
        usuario = db.query(Usuario).filter(Usuario.id == emergencia.id_usuario).first()
        if usuario and usuario.push_token:
            msgs = {
                "a_caminho": ("Viatura a caminho!", "O agente esta se deslocando ate voce."),
                "no_local": ("Agente chegou!", "O agente esta no local da ocorrencia."),
                "finalizado": ("Atendimento concluido", "Sua ocorrencia foi finalizada."),
            }
            title, body = msgs.get(dados.status, ("Atualizacao", f"Status: {dados.status}"))
            enviar_push(usuario.push_token, title, body)
    db.refresh(despacho)
    return despacho


# ──────────────────────────── POST /posicao ───────────────────────

@app.post("/posicao", response_model=PosicaoResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def registrar_posicao(dados: PosicaoCreate, db: Session = Depends(get_db)):
    agente = db.query(Agente).filter(Agente.id == dados.id_agente).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")

    posicao = PosicaoGPS(**dados.model_dump())
    db.add(posicao)
    db.commit()
    db.refresh(posicao)
    return posicao


# ──────────────────────────── POST /triagem (IA) ──────────────────

TRIAGEM_SYSTEM_PROMPT = """Voce e um especialista em triagem de emergencias urbanas no Brasil.
Recebera dados de uma ocorrencia e deve retornar APENAS um JSON valido (sem markdown, sem texto extra) com exatamente estes campos:

{
  "gravidade": <inteiro de 1 a 5, onde 1=leve e 5=critico>,
  "recurso_sugerido": "<um dentre: viatura_PM, ambulancia_SAMU, bombeiro>",
  "briefing": "<exatamente 2 frases curtas para o agente em campo>"
}

Criterios de gravidade:
1 - Ocorrencia leve, sem risco a vida (ex: perturbacao do sossego)
2 - Ocorrencia moderada, baixo risco (ex: furto sem violencia)
3 - Ocorrencia seria, risco potencial (ex: acidente de transito com feridos leves)
4 - Ocorrencia grave, risco alto (ex: incendio em area residencial, assalto a mao armada)
5 - Ocorrencia critica, risco iminente de morte (ex: tiroteio ativo, desabamento, parada cardiaca)

Criterios de recurso:
- viatura_PM: crimes, seguranca publica, patrulhamento
- ambulancia_SAMU: emergencias medicas, acidentes com feridos
- bombeiro: incendios, salvamentos, desastres naturais"""


@app.post("/triagem", response_model=TriagemResponse, dependencies=[Depends(verificar_api_key)])
def triagem_ia(dados: TriagemRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY nao configurada no servidor",
        )

    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"Tipo: {dados.tipo}\n"
        f"Localizacao: lat={dados.latitude}, lon={dados.longitude}\n"
        f"Horario: {dados.horario}\n"
        f"Descricao: {dados.descricao}"
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=TRIAGEM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
        resultado = json.loads(raw_text)

        return TriagemResponse(
            gravidade=resultado["gravidade"],
            recurso_sugerido=resultado["recurso_sugerido"],
            briefing=resultado["briefing"],
            tipo=dados.tipo,
            latitude=dados.latitude,
            longitude=dados.longitude,
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail=f"Resposta da IA nao e JSON valido: {raw_text}",
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro na API Claude: {e.message}",
        )


# ──────────────────────────── Dashboard estático ──────────────────

_dashboard_dir = Path(__file__).resolve().parent.parent / "dashboard"
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
