from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    cpf = Column(String(11), unique=True, nullable=False)
    nome = Column(String(100), nullable=False)
    push_token = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    emergencias = relationship("Emergencia", back_populates="usuario")


class Emergencia(Base):
    __tablename__ = "emergencias"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    tipo = Column(String(50), nullable=False)
    gravidade = Column(Integer, nullable=False)
    status = Column(String(20), default="aberta")
    descricao = Column(String(500), nullable=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="emergencias")
    despachos = relationship("Despacho", back_populates="emergencia")


class Agente(Base):
    __tablename__ = "agentes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    matricula = Column(String(20), unique=True, nullable=False)
    tipo_recurso = Column(String(50), nullable=False)
    status = Column(String(20), default="disponivel")

    viaturas = relationship("Viatura", back_populates="agente")
    despachos = relationship("Despacho", back_populates="agente")
    posicoes = relationship("PosicaoGPS", back_populates="agente")


class Viatura(Base):
    __tablename__ = "viaturas"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), unique=True, nullable=False)
    tipo = Column(String(50), nullable=False)
    id_agente = Column(Integer, ForeignKey("agentes.id"), nullable=False)

    agente = relationship("Agente", back_populates="viaturas")


class Despacho(Base):
    __tablename__ = "despachos"

    id = Column(Integer, primary_key=True, index=True)
    id_emergencia = Column(Integer, ForeignKey("emergencias.id"), nullable=False)
    id_agente = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    status = Column(String(20), default="pendente")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    emergencia = relationship("Emergencia", back_populates="despachos")
    agente = relationship("Agente", back_populates="despachos")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    ator = Column(String(100), nullable=False)
    acao = Column(String(50), nullable=False)
    entidade = Column(String(50), nullable=True)
    entidade_id = Column(Integer, nullable=True)
    detalhe = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PosicaoGPS(Base):
    __tablename__ = "posicoes_gps"

    id = Column(Integer, primary_key=True, index=True)
    id_agente = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    agente = relationship("Agente", back_populates="posicoes")
