from pydantic import BaseModel
from datetime import datetime


# --- Usuario ---
class UsuarioCreate(BaseModel):
    cpf: str
    nome: str


class UsuarioResponse(BaseModel):
    id: int
    cpf: str
    nome: str

    model_config = {"from_attributes": True}


class PushTokenUpdate(BaseModel):
    push_token: str


# --- Emergencia ---
class EmergenciaCreate(BaseModel):
    lat: float
    lon: float
    tipo: str
    gravidade: int
    id_usuario: int


class EmergenciaResponse(BaseModel):
    id: int
    lat: float
    lon: float
    tipo: str
    gravidade: int
    status: str
    id_usuario: int
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Frota ---
class ViaturaFrota(BaseModel):
    id: int
    placa: str
    tipo: str

    model_config = {"from_attributes": True}


class AgenteFrota(BaseModel):
    id: int
    nome: str
    matricula: str
    tipo_recurso: str
    status: str
    viaturas: list[ViaturaFrota]
    despacho_id: int | None = None
    emergencia_id: int | None = None

    model_config = {"from_attributes": True}


# --- Despacho ---
class DespachoCreate(BaseModel):
    id_emergencia: int


class DespachoResponse(BaseModel):
    id: int
    id_emergencia: int
    id_agente: int
    status: str
    created_at: datetime
    distancia_km: float | None = None
    agente_nome: str | None = None

    model_config = {"from_attributes": True}


class DespachoStatusUpdate(BaseModel):
    status: str


# --- Posicao GPS ---
class PosicaoCreate(BaseModel):
    id_agente: int
    lat: float
    lon: float


class PosicaoResponse(BaseModel):
    id: int
    id_agente: int
    lat: float
    lon: float
    timestamp: datetime

    model_config = {"from_attributes": True}


# --- Triagem (IA) ---
class TriagemRequest(BaseModel):
    tipo: str
    latitude: float
    longitude: float
    horario: str
    descricao: str


class TriagemResponse(BaseModel):
    gravidade: int
    recurso_sugerido: str
    briefing: str
    tipo: str
    latitude: float
    longitude: float
