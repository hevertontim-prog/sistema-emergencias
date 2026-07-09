"""Popula o banco com um cenario de demonstracao realista em Brasilia.

Idempotente: verifica por descricao antes de inserir (rodar 2x nao duplica).
Uso: python scripts/seed_demo.py  (ou `railway run python scripts/seed_demo.py`)
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine, Base
from app.models import Usuario, Agente, Emergencia, Despacho

Base.metadata.create_all(bind=engine)

USUARIO_DEMO_CPF = "00000000000"
USUARIO_DEMO_NOME = "Cidadão Demo"


def _get_or_create_usuario_demo(db):
    usuario = db.query(Usuario).filter(Usuario.cpf == USUARIO_DEMO_CPF).first()
    if usuario:
        return usuario
    usuario = Usuario(cpf=USUARIO_DEMO_CPF, nome=USUARIO_DEMO_NOME)
    db.add(usuario)
    db.flush()
    return usuario


def _criar_emergencia_se_nova(db, agora, usuario, descricao, tipo, gravidade, status, lat, lon, criada_ha_min):
    existente = db.query(Emergencia).filter(Emergencia.descricao == descricao).first()
    if existente:
        print(f"Ja existe, pulando: {descricao[:60]}...")
        return None
    emergencia = Emergencia(
        lat=lat, lon=lon, tipo=tipo, gravidade=gravidade, status=status,
        id_usuario=usuario.id, descricao=descricao,
        created_at=agora - timedelta(minutes=criada_ha_min),
    )
    db.add(emergencia)
    db.flush()
    print(f"Criada: {descricao[:60]}...")
    return emergencia


def _criar_despacho(db, agora, emergencia, agente_id, status, despachado_ha_min, liberar_agente=False):
    agente = db.query(Agente).filter(Agente.id == agente_id).first()
    if not agente:
        print(f"  Agente id={agente_id} nao encontrado, pulando despacho.")
        return
    despacho = Despacho(
        id_emergencia=emergencia.id, id_agente=agente.id, status=status,
        created_at=agora - timedelta(minutes=despachado_ha_min),
    )
    agente.status = "disponivel" if liberar_agente else "em_atendimento"
    db.add(despacho)


def seed_demo():
    agora = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        usuario = _get_or_create_usuario_demo(db)

        _criar_emergencia_se_nova(
            db, agora, usuario,
            descricao="Acidente de trânsito com vítima presa nas ferragens, EPTG altura de Águas Claras",
            tipo="medica", gravidade=4, status="aberta",
            lat=-15.8395, lon=-48.0263, criada_ha_min=4,
        )

        _criar_emergencia_se_nova(
            db, agora, usuario,
            descricao="Princípio de incêndio em residência, Ceilândia Norte QNN 14",
            tipo="bombeiro", gravidade=4, status="aberta",
            lat=-15.8055, lon=-48.1120, criada_ha_min=2,
        )

        e3 = _criar_emergencia_se_nova(
            db, agora, usuario,
            descricao="Ocorrência de violência doméstica, Asa Sul SQS 308",
            tipo="policia", gravidade=3, status="em_atendimento",
            lat=-15.8115, lon=-47.9010, criada_ha_min=18,
        )
        if e3:
            _criar_despacho(db, agora, e3, agente_id=1, status="a_caminho", despachado_ha_min=15)

        e4 = _criar_emergencia_se_nova(
            db, agora, usuario,
            descricao="Idoso com dor torácica, Taguatinga Centro",
            tipo="medica", gravidade=4, status="em_atendimento",
            lat=-15.8330, lon=-48.0570, criada_ha_min=25,
        )
        if e4:
            _criar_despacho(db, agora, e4, agente_id=2, status="a_caminho", despachado_ha_min=22)

        e5 = _criar_emergencia_se_nova(
            db, agora, usuario,
            descricao="Queda de árvore bloqueando via, Lago Norte",
            tipo="bombeiro", gravidade=3, status="finalizada",
            lat=-15.7305, lon=-47.8630, criada_ha_min=120,
        )
        if e5:
            _criar_despacho(db, agora, e5, agente_id=3, status="finalizado",
                             despachado_ha_min=115, liberar_agente=True)

        db.commit()
        print("Seed demo concluido.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
