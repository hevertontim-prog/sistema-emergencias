const API_URL = 'https://sistema-emergencias-production.up.railway.app';
const API_KEY = process.env.EXPO_PUBLIC_API_KEY;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY || '' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw Object.assign(new Error(body.detail || `Erro ${res.status}`), { status: res.status });
  }
  return res.json();
}

export async function listarFrota() {
  return request<any[]>('/frota');
}

export interface AgenteLogin {
  id: number;
  nome: string;
  matricula: string;
  tipo_recurso: string;
  status: string;
}

export function buscarAgentePorMatricula(matricula: string) {
  return request<AgenteLogin>(`/agentes/matricula/${encodeURIComponent(matricula)}`);
}

export async function buscarEmergencia(id: number) {
  return request<any>(`/emergencia/${id}`);
}

export async function atualizarDespacho(id: number, status: string) {
  return request<any>(`/despacho/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export async function enviarPosicao(agenteId: number, lat: number, lon: number) {
  return request<any>('/posicao', {
    method: 'POST',
    body: JSON.stringify({ id_agente: agenteId, latitude: lat, longitude: lon }),
  });
}

export async function buscarTriagem(descricao: string) {
  return request<any>('/triagem', {
    method: 'POST',
    body: JSON.stringify({ descricao }),
  });
}

export interface AcompanhamentoData {
  status: string;
  tipo?: string | null;
  gravidade?: number | null;
  descricao?: string | null;
  despacho_id: number | null;
  agente_nome: string | null;
  tipo_recurso: string | null;
  agente_lat: number | null;
  agente_lon: number | null;
  eta_segundos: number | null;
  distancia_km: number | null;
}

export function buscarAcompanhamento(emergenciaId: number) {
  return request<AcompanhamentoData>(`/emergencia/${emergenciaId}/acompanhamento`);
}
