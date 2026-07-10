"""Popula o banco com dados de exemplo para testes."""
from datetime import datetime, timedelta

from app.database import SessionLocal, engine, Base
from app.models import (
    Usuario, Agente, Viatura, PosicaoGPS, Emergencia, Despacho,
)

Base.metadata.create_all(bind=engine)

# Coordenadas reais de Brasilia
AGENTES_BRASILIA = [
    # nome, matricula, tipo_recurso, placa, tipo_viatura, lat, lon
    ("Ricardo PM - Asa Sul", "PM001", "policia", "ABC1D23", "viatura_policial",
     -15.8267, -47.9218),  # Asa Sul
    ("Fernanda SAMU - Asa Norte", "SAMU001", "ambulancia", "XYZ9F87", "ambulancia",
     -15.7469, -47.8828),  # Asa Norte
    ("Lucas BM - Taguatinga", "BM001", "bombeiro", "QWE4R56", "caminhao_bombeiro",
     -15.8362, -48.0558),  # Taguatinga
    ("Mariana PM - Ceilandia", "PM002", "policia", "JKL3M78", "viatura_policial",
     -15.8120, -48.1084),  # Ceilandia
    ("Carlos SAMU - Gama", "SAMU002", "ambulancia", "RST5U90", "ambulancia",
     -15.9593, -48.0464),  # Gama
]


def seed_emergencias_demo(db):
    """Cria emergencias de demonstracao se a tabela estiver vazia.
    Idempotente: nao faz nada se ja existir qualquer emergencia."""
    if db.query(Emergencia).count() > 0:
        return

    usuarios = db.query(Usuario).order_by(Usuario.id).all()
    if not usuarios:
        return

    def usuario_id(i):
        return usuarios[i % len(usuarios)].id

    agente1 = db.query(Agente).filter(Agente.matricula == "PM001").first()
    agente2 = db.query(Agente).filter(Agente.matricula == "SAMU001").first()

    agora = datetime.now()

    # --- 2 ABERTAS ---
    ab1 = Emergencia(
        lat=-15.8395, lon=-48.0263, tipo="medica", gravidade=4,
        status="aberta", descricao="Acidente de transito na EPTG",
        id_usuario=usuario_id(0),
    )
    ab2 = Emergencia(
        lat=-15.8055, lon=-48.1120, tipo="bombeiro", gravidade=4,
        status="aberta", descricao="Incendio em residencia - Ceilandia QNN 14",
        id_usuario=usuario_id(1),
    )
    db.add_all([ab1, ab2])

    # --- 2 EM_ATENDIMENTO com despacho vinculado ---
    at1 = Emergencia(
        lat=-15.8267, lon=-47.9218, tipo="policia", gravidade=4,
        status="em_atendimento", descricao="Violencia domestica - Asa Sul",
        id_usuario=usuario_id(2),
    )
    at2 = Emergencia(
        lat=-15.8362, lon=-48.0558, tipo="medica", gravidade=5,
        status="em_atendimento", descricao="Dor toracica - Taguatinga",
        id_usuario=usuario_id(0),
    )
    db.add_all([at1, at2])
    db.flush()

    if agente1:
        db.add(Despacho(
            id_emergencia=at1.id, id_agente=agente1.id, status="a_caminho",
        ))
        agente1.status = "em_atendimento"
    if agente2:
        db.add(Despacho(
            id_emergencia=at2.id, id_agente=agente2.id, status="a_caminho",
        ))
        agente2.status = "em_atendimento"

    # --- 1 FINALIZADA (criada ha 2h) ---
    fin = Emergencia(
        lat=-15.7280, lon=-47.8730, tipo="bombeiro", gravidade=2,
        status="finalizada", descricao="Queda de arvore - Lago Norte",
        id_usuario=usuario_id(1),
    )
    fin.created_at = agora - timedelta(hours=2)
    db.add(fin)

    db.commit()
    print("Emergencias demo criadas: 2 abertas, 2 em atendimento, 1 finalizada.")


def seed():
    db = SessionLocal()
    try:
        if db.query(Usuario).count() == 0:
            # Usuarios
            u1 = Usuario(cpf="12345678901", nome="Joao Silva")
            u2 = Usuario(cpf="98765432100", nome="Maria Souza")
            u3 = Usuario(cpf="11122233344", nome="Ana Oliveira")
            db.add_all([u1, u2, u3])
            db.flush()

            # Agentes + Viaturas + Posicoes GPS
            for nome, mat, tipo_rec, placa, tipo_viat, lat, lon in AGENTES_BRASILIA:
                agente = Agente(
                    nome=nome, matricula=mat,
                    tipo_recurso=tipo_rec, status="disponivel",
                )
                db.add(agente)
                db.flush()

                viatura = Viatura(placa=placa, tipo=tipo_viat, id_agente=agente.id)
                db.add(viatura)

                posicao = PosicaoGPS(id_agente=agente.id, lat=lat, lon=lon)
                db.add(posicao)

            db.commit()
            print("Seed concluido com sucesso! 3 usuarios, 5 agentes em Brasilia.")
        else:
            print("Banco ja possui usuarios, pulando seed base.")

        # Emergencias de demonstracao (idempotente por conta propria)
        seed_emergencias_demo(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
