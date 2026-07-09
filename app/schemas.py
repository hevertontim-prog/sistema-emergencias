from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


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
    descricao: Optional[str] = None


class EmergenciaResponse(BaseModel):
    id: int
    lat: float
    lon: float
    tipo: str
    gravidade: int
    status: str
    id_usuario: int
    created_at: datetime
    descricao: Optional[str] = None

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
    viaturas: List[ViaturaFrota]
    despacho_id: Optional[int] = None
    emergencia_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

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
    distancia_km: Optional[float] = None
    agente_nome: Optional[str] = None

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


# --- Acompanhamento ---
class AcompanhamentoResponse(BaseModel):
    status: str
    despacho_id: Optional[int] = None
    agente_nome: Optional[str] = None
    tipo_recurso: Optional[str] = None
    agente_lat: Optional[float] = None
    agente_lon: Optional[float] = None
    eta_segundos: Optional[int] = None
    distancia_km: Optional[float] = None


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
