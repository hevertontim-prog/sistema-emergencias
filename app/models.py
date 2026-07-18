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
    push_token = Column(String(200), nullable=True)

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


class Operador(Base):
    __tablename__ = "operadores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    matricula = Column(String(20), unique=True, nullable=False)
    ativo = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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


class ConfiguracaoDespacho(Base):
    """Painel de Soberania — a prefeitura calibra o quanto confia no despacho
    automático. Singleton (uma linha, id=1). Default = comportamento do MVP
    (autonomia total / despacho imediato), então ligar a feature é opt-in."""
    __tablename__ = "configuracao_despacho"

    id = Column(Integer, primary_key=True, index=True)
    # 1 = despacha na hora (comportamento atual do MVP). 0 = usa as regras abaixo.
    autonomia_total = Column(Integer, default=1)
    # Segundos que a sugestão fica pendente antes de auto-confirmar (0 = imediato).
    delay_segundos = Column(Integer, default=0)
    # Ocorrências com gravidade >= este valor despacham na hora mesmo sem autonomia total.
    gravidade_imediata_min = Column(Integer, default=4)
    # CSV de tipos de recurso que SEMPRE exigem confirmação manual (ex: "ambulancia").
    recursos_confirmacao_manual = Column(String(200), default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SugestaoDespacho(Base):
    """Despacho sugerido pela IA aguardando confirmação (manual ou por tempo).
    A emergência continua com status 'aberta' até a confirmação — os apps do
    cidadão/agente não veem estado novo, só o painel do gestor."""
    __tablename__ = "sugestoes_despacho"

    id = Column(Integer, primary_key=True, index=True)
    id_emergencia = Column(Integer, ForeignKey("emergencias.id"), nullable=False)
    id_agente_sugerido = Column(Integer, ForeignKey("agentes.id"), nullable=False)
    distancia_km = Column(Float, nullable=True)
    briefing = Column(String(500), nullable=True)
    # None = só confirmação manual (delay infinito); senão, instante do auto-confirm.
    expira_em = Column(DateTime, nullable=True)
    status = Column(String(20), default="pendente")  # pendente | confirmada | descartada
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
