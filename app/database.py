import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Para usar PostgreSQL, defina a variavel de ambiente DATABASE_URL:
#   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/emergencias_db"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./emergencias.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
