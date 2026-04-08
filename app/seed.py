"""Popula o banco com dados de exemplo para testes."""
from app.database import SessionLocal, engine, Base
from app.models import Usuario, Agente, Viatura, PosicaoGPS

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


def seed():
    db = SessionLocal()
    try:
        if db.query(Usuario).count() > 0:
            print("Banco ja possui dados, pulando seed.")
            return

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
    finally:
        db.close()


if __name__ == "__main__":
    seed()
