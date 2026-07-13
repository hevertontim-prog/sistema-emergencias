import json
import os
import httpx
import threading
import time
from datetime import datetime, timezone
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
from app.models import Emergencia, Agente, Usuario, Despacho, PosicaoGPS, AuditLog, Operador, Viatura
from app.schemas import (
    UsuarioCreate, UsuarioResponse, PushTokenUpdate,
    EmergenciaCreate, EmergenciaResponse,
    AgenteFrota,
    DespachoCreate, DespachoResponse, DespachoStatusUpdate,
    PosicaoCreate, PosicaoResponse,
    TriagemRequest, TriagemResponse,
    OcorrenciaManualCreate, OcorrenciaManualResponse, AuditLogResponse,
    AgenteCreate, AgenteResponse, ViaturaCreate, ViaturaResponse,
    OperadorCreate, OperadorResponse,
)

Base.metadata.create_all(bind=engine)


def _garantir_colunas_novas():
    """Base.metadata.create_all so cria tabelas que ainda nao existem — nao
    adiciona colunas novas a tabelas ja existentes (ex: producao com Postgres
    persistente). Sem Alembic, entao colunas adicionadas apos o primeiro
    deploy de uma tabela precisam ser registradas aqui (aditivo, idempotente)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE agentes ADD COLUMN IF NOT EXISTS push_token VARCHAR(200)"))
            conn.commit()
        elif engine.dialect.name == "sqlite":
            colunas = [row[1] for row in conn.execute(text("PRAGMA table_info(agentes)"))]
            if "push_token" not in colunas:
                conn.execute(text("ALTER TABLE agentes ADD COLUMN push_token VARCHAR(200)"))
                conn.commit()


_garantir_colunas_novas()

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


def registrar_auditoria(db: Session, ator: str, acao: str, entidade: str = None,
                        entidade_id: int = None, detalhe: str = None):
    """Grava um evento na trilha de auditoria. Nunca derruba a operacao principal."""
    try:
        db.add(AuditLog(ator=ator, acao=acao, entidade=entidade,
                        entidade_id=entidade_id, detalhe=detalhe))
        db.commit()
    except Exception:
        db.rollback()


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


# ──────────────────────────── PUT /agente/{id}/push-token ─────────

@app.put("/agente/{agente_id}/push-token", dependencies=[Depends(verificar_api_key)])
def salvar_push_token_agente(agente_id: int, dados: PushTokenUpdate, db: Session = Depends(get_db)):
    agente = db.query(Agente).filter(Agente.id == agente_id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    agente.push_token = dados.push_token
    db.commit()
    return {"ok": True}


# ──────────────────────────── POST /emergencia ────────────────────

@app.post("/emergencia", response_model=EmergenciaResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def criar_emergencia(dados: EmergenciaCreate, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == dados.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    tipo = dados.tipo
    gravidade = dados.gravidade
    briefing_triagem = None
    origem_triagem = None

    if dados.descricao and gravidade is None:
        resultado_ia = _triar_com_ia(dados.tipo, dados.descricao, dados.lat, dados.lon)
        if resultado_ia:
            gravidade = resultado_ia["gravidade"]
            tipo = RECURSO_IA_PARA_TIPO.get(resultado_ia["recurso_sugerido"], dados.tipo)
            briefing_triagem = resultado_ia["briefing"]
            origem_triagem = ("triagem_ia", resultado_ia)
        else:
            gravidade = 3
            origem_triagem = ("triagem_ia_fallback", None)
    elif gravidade is None:
        gravidade = 3

    emergencia = Emergencia(
        lat=dados.lat, lon=dados.lon, tipo=tipo, gravidade=gravidade,
        descricao=dados.descricao, id_usuario=dados.id_usuario,
    )
    db.add(emergencia)
    db.commit()
    db.refresh(emergencia)

    registrar_auditoria(
        db, f"cidadao:{usuario.nome}", "criar_emergencia", "emergencia", emergencia.id,
        f"tipo={emergencia.tipo} gravidade={emergencia.gravidade}",
    )

    if origem_triagem:
        acao, resultado_ia = origem_triagem
        if acao == "triagem_ia":
            registrar_auditoria(
                db, f"app_cidadao:{usuario.nome}", "triagem_ia", "emergencia", emergencia.id,
                f"G{resultado_ia['gravidade']} · {resultado_ia['recurso_sugerido']} · "
                f"{resultado_ia['briefing'][:120]}",
            )
        else:
            registrar_auditoria(
                db, f"app_cidadao:{usuario.nome}", "triagem_ia_fallback", "emergencia", emergencia.id,
                "IA indisponível — despacho com gravidade padrão 3",
            )

    # Auto-despacho: tenta atribuir agente mais proximo. Se nao houver, segue como aberta.
    try:
        _executar_despacho(emergencia, db, briefing=briefing_triagem)
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
        return AcompanhamentoResponse(
            status=emergencia.status, tipo=emergencia.tipo,
            gravidade=emergencia.gravidade, descricao=emergencia.descricao,
        )

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
        tipo=emergencia.tipo,
        gravidade=emergencia.gravidade,
        descricao=emergencia.descricao,
        despacho_id=despacho.id,
        agente_nome=agente.nome if agente else None,
        tipo_recurso=agente.tipo_recurso if agente else None,
        agente_lat=ultima_pos.lat if ultima_pos else None,
        agente_lon=ultima_pos.lon if ultima_pos else None,
        eta_segundos=eta,
        distancia_km=dist,
    )


# ──────────────────────── PATCH /emergencia/{id}/finalizar ────────

@app.patch("/emergencia/{emergencia_id}/finalizar", response_model=EmergenciaResponse, dependencies=[Depends(verificar_api_key)])
def finalizar_emergencia(emergencia_id: int, db: Session = Depends(get_db), x_operador: str = Header(None)):
    """Finaliza uma ocorrencia direto pelo painel do gestor, com ou sem despacho
    ativo (cobre tanto 'aberta' aguardando agente quanto 'em_atendimento').
    Libera o agente se houver despacho em andamento."""
    emergencia = db.query(Emergencia).filter(Emergencia.id == emergencia_id).first()
    if not emergencia:
        raise HTTPException(status_code=404, detail="Emergencia nao encontrada")
    if emergencia.status == "finalizada":
        return emergencia

    despacho_ativo = (
        db.query(Despacho)
        .filter(Despacho.id_emergencia == emergencia_id, Despacho.status != "finalizado")
        .order_by(Despacho.id.desc())
        .first()
    )
    if despacho_ativo:
        despacho_ativo.status = "finalizado"
        agente = db.query(Agente).filter(Agente.id == despacho_ativo.id_agente).first()
        if agente:
            agente.status = "disponivel"

    emergencia.status = "finalizada"
    db.commit()

    registrar_auditoria(
        db, f"operador:{x_operador or 'nao_informado'}", "finalizar_emergencia",
        "emergencia", emergencia.id,
        f"finalizado manualmente pelo painel" + (f" (despacho #{despacho_ativo.id} liberado)" if despacho_ativo else ""),
    )

    db.refresh(emergencia)
    return emergencia


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
            "descricao": e.descricao,
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
    "bombeiro": "bombeiro",
    "incendio": "bombeiro",
}

def _executar_despacho(emergencia: Emergencia, db: Session, briefing: Optional[str] = None) -> Optional[Tuple[Despacho, Agente, float]]:
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

    registrar_auditoria(
        db, "sistema", "despacho_automatico", "despacho", despacho.id,
        f"agente={melhor_agente.nome} ({melhor_agente.tipo_recurso}) -> "
        f"emergencia #{emergencia.id} ({round(menor_distancia, 2)} km)",
    )

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

    if melhor_agente.push_token:
        detalhe = (briefing or emergencia.descricao or "").strip()
        corpo = f"{detalhe[:100]} · maps: {emergencia.lat},{emergencia.lon}" if detalhe \
            else f"maps: {emergencia.lat},{emergencia.lon}"
        enviar_push(
            melhor_agente.push_token,
            f"🚨 Despacho G{emergencia.gravidade} — {emergencia.tipo}",
            corpo,
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

    registrar_auditoria(
        db, f"agente:{despacho.id_agente}", "atualizar_status_despacho",
        "despacho", despacho.id, f"status={dados.status}",
    )

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


# ──────────────────────────── POST /ocorrencias/manual ────────────

CPF_ENTRADA_MANUAL = "00000000000"

RECURSO_IA_PARA_TIPO = {"viatura_PM": "policia", "ambulancia_SAMU": "medica", "bombeiro": "bombeiro"}

@app.post("/ocorrencias/manual", response_model=OcorrenciaManualResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def criar_ocorrencia_manual(dados: OcorrenciaManualCreate, db: Session = Depends(get_db)):
    """Entrada manual de ocorrencia pelo operador da central (telefone/radio).
    Vincula ao usuario sentinela 'Entrada Manual' e dispara o despacho automatico.
    Se a gravidade nao vier preenchida, a IA faz a triagem (fallback: gravidade 3
    se a IA estiver indisponivel — o despacho nunca trava por isso)."""
    usuario = db.query(Usuario).filter(Usuario.cpf == CPF_ENTRADA_MANUAL).first()
    if not usuario:
        usuario = Usuario(cpf=CPF_ENTRADA_MANUAL, nome="Entrada Manual")
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    tipo = dados.tipo
    gravidade = dados.gravidade

    if gravidade is None:
        resultado_ia = _triar_com_ia(dados.tipo, dados.descricao or "", dados.lat, dados.lon)
        if resultado_ia:
            gravidade = resultado_ia["gravidade"]
            tipo = RECURSO_IA_PARA_TIPO.get(resultado_ia["recurso_sugerido"], dados.tipo)
            triagem_info = {**resultado_ia, "origem": "ia"}
        else:
            gravidade = 3
            triagem_info = {
                "gravidade": 3,
                "recurso_sugerido": TIPO_EMERGENCIA_PARA_RECURSO.get(dados.tipo, dados.tipo),
                "briefing": "IA indisponível — despacho com gravidade padrão 3",
                "origem": "fallback",
            }
    else:
        triagem_info = {
            "gravidade": gravidade,
            "recurso_sugerido": TIPO_EMERGENCIA_PARA_RECURSO.get(dados.tipo, dados.tipo),
            "briefing": "",
            "origem": "manual",
        }

    emergencia = Emergencia(
        lat=dados.lat, lon=dados.lon, tipo=tipo, gravidade=gravidade,
        descricao=dados.descricao, id_usuario=usuario.id,
    )
    db.add(emergencia)
    db.commit()
    db.refresh(emergencia)

    registrar_auditoria(
        db, f"operador:{dados.operador or 'nao_informado'}", "criar_ocorrencia_manual",
        "emergencia", emergencia.id,
        f"tipo={tipo} gravidade={gravidade} solicitante={dados.nome_solicitante or '-'}",
    )
    if triagem_info["origem"] == "ia":
        registrar_auditoria(
            db, "sistema", "triagem_ia", "emergencia", emergencia.id,
            f"G{triagem_info['gravidade']} · {triagem_info['recurso_sugerido']} · "
            f"{triagem_info['briefing'][:120]}",
        )
    elif triagem_info["origem"] == "fallback":
        registrar_auditoria(
            db, "sistema", "triagem_ia_fallback", "emergencia", emergencia.id,
            "IA indisponível — despacho com gravidade padrão 3",
        )

    despacho_info = None
    try:
        resultado_despacho = _executar_despacho(emergencia, db, briefing=triagem_info.get("briefing") or None)
        db.refresh(emergencia)
        if resultado_despacho:
            _, melhor_agente, menor_distancia = resultado_despacho
            despacho_info = {
                "agente_nome": melhor_agente.nome,
                "tipo_recurso": melhor_agente.tipo_recurso,
                "distancia_km": round(menor_distancia, 2),
            }
    except Exception:
        pass

    return OcorrenciaManualResponse(
        id=emergencia.id, lat=emergencia.lat, lon=emergencia.lon, tipo=emergencia.tipo,
        gravidade=emergencia.gravidade, status=emergencia.status, id_usuario=emergencia.id_usuario,
        created_at=emergencia.created_at, descricao=emergencia.descricao,
        triagem=triagem_info, despacho=despacho_info,
    )


# ──────────────────────────── GET /auditoria ──────────────────────

@app.get("/auditoria", response_model=list[AuditLogResponse])
def listar_auditoria(limit: int = 100, db: Session = Depends(get_db)):
    """Trilha de auditoria (mais recentes primeiro)."""
    return (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )


# ──────────────────────────── Cadastros ───────────────────────────

TIPOS_RECURSO_VALIDOS = {"policia", "ambulancia", "bombeiro"}

def _ator_operador(x_operador: str = None) -> str:
    return f"operador:{x_operador or 'nao_informado'}"


@app.post("/agentes", response_model=AgenteResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def cadastrar_agente(dados: AgenteCreate, db: Session = Depends(get_db),
                     x_operador: str = Header(None)):
    """Cadastra agente (e opcionalmente a viatura junto). Sem lat/lon o agente
    fica sem posicao GPS e NAO e escolhido pelo despacho automatico."""
    if dados.tipo_recurso not in TIPOS_RECURSO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"tipo_recurso invalido. Valores aceitos: {', '.join(sorted(TIPOS_RECURSO_VALIDOS))}",
        )
    if db.query(Agente).filter(Agente.matricula == dados.matricula).first():
        raise HTTPException(status_code=409, detail="Matricula ja cadastrada")
    if dados.placa_viatura and db.query(Viatura).filter(Viatura.placa == dados.placa_viatura).first():
        raise HTTPException(status_code=409, detail="Placa ja cadastrada")

    agente = Agente(nome=dados.nome, matricula=dados.matricula,
                    tipo_recurso=dados.tipo_recurso, status="disponivel")
    db.add(agente)
    db.commit()
    db.refresh(agente)

    if dados.lat is not None and dados.lon is not None:
        db.add(PosicaoGPS(id_agente=agente.id, lat=dados.lat, lon=dados.lon))
        db.commit()

    if dados.placa_viatura:
        db.add(Viatura(placa=dados.placa_viatura,
                       tipo=dados.tipo_viatura or dados.tipo_recurso,
                       id_agente=agente.id))
        db.commit()

    registrar_auditoria(
        db, _ator_operador(x_operador), "cadastrar_agente", "agente", agente.id,
        f"nome={dados.nome} matricula={dados.matricula} tipo={dados.tipo_recurso} "
        f"gps={'sim' if dados.lat is not None else 'nao'} viatura={dados.placa_viatura or '-'}",
    )
    return agente


@app.get("/agentes", response_model=list[AgenteResponse])
def listar_agentes(db: Session = Depends(get_db)):
    return db.query(Agente).all()


@app.post("/viaturas", response_model=ViaturaResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def cadastrar_viatura(dados: ViaturaCreate, db: Session = Depends(get_db),
                      x_operador: str = Header(None)):
    agente = db.query(Agente).filter(Agente.id == dados.id_agente).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    if db.query(Viatura).filter(Viatura.placa == dados.placa).first():
        raise HTTPException(status_code=409, detail="Placa ja cadastrada")

    viatura = Viatura(placa=dados.placa, tipo=dados.tipo, id_agente=dados.id_agente)
    db.add(viatura)
    db.commit()
    db.refresh(viatura)

    registrar_auditoria(
        db, _ator_operador(x_operador), "cadastrar_viatura", "viatura", viatura.id,
        f"placa={dados.placa} tipo={dados.tipo} agente={agente.nome}",
    )
    return viatura


@app.post("/operadores", response_model=OperadorResponse, status_code=201, dependencies=[Depends(verificar_api_key)])
def cadastrar_operador(dados: OperadorCreate, db: Session = Depends(get_db),
                       x_operador: str = Header(None)):
    if db.query(Operador).filter(Operador.matricula == dados.matricula).first():
        raise HTTPException(status_code=409, detail="Matricula ja cadastrada")

    operador = Operador(nome=dados.nome, matricula=dados.matricula, ativo=1)
    db.add(operador)
    db.commit()
    db.refresh(operador)

    registrar_auditoria(
        db, _ator_operador(x_operador), "cadastrar_operador", "operador", operador.id,
        f"nome={dados.nome} matricula={dados.matricula}",
    )
    return operador


@app.get("/operadores", response_model=list[OperadorResponse])
def listar_operadores(db: Session = Depends(get_db)):
    return db.query(Operador).filter(Operador.ativo == 1).all()


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


def _chamar_ia_triagem(tipo: str, descricao: str, lat: float, lon: float) -> dict:
    """Chama a IA de triagem e retorna o dict parseado ({gravidade, recurso_sugerido, briefing}).
    Pode levantar excecao (sem API key, JSON invalido, erro da API Claude) — quem precisa
    de uma chamada que nunca falha usa `_triar_com_ia`."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY nao configurada no servidor")

    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"Tipo: {tipo}\n"
        f"Localizacao: lat={lat}, lon={lon}\n"
        f"Horario: {datetime.now(timezone.utc).isoformat()}\n"
        f"Descricao: {descricao}"
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=TRIAGEM_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = next((b.text for b in response.content if b.type == "text"), "")
    resultado = json.loads(raw_text)

    return {
        "gravidade": resultado["gravidade"],
        "recurso_sugerido": resultado["recurso_sugerido"],
        "briefing": resultado["briefing"],
    }


def _triar_com_ia(tipo: str, descricao: str, lat: float, lon: float) -> Optional[dict]:
    """Wrapper que nunca levanta excecao — usado no fluxo de despacho, onde a IA
    indisponivel nao pode travar a criacao da ocorrencia."""
    try:
        return _chamar_ia_triagem(tipo, descricao, lat, lon)
    except Exception:
        return None


@app.post("/triagem", response_model=TriagemResponse, dependencies=[Depends(verificar_api_key)])
def triagem_ia(dados: TriagemRequest):
    try:
        resultado = _chamar_ia_triagem(dados.tipo, dados.descricao, dados.latitude, dados.longitude)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Resposta da IA nao e JSON valido")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Erro na API Claude: {e.message}")

    return TriagemResponse(
        gravidade=resultado["gravidade"],
        recurso_sugerido=resultado["recurso_sugerido"],
        briefing=resultado["briefing"],
        tipo=dados.tipo,
        latitude=dados.latitude,
        longitude=dados.longitude,
    )


# ──────────────────────────── Dashboard estático ──────────────────

_dashboard_dir = Path(__file__).resolve().parent.parent / "dashboard"
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
