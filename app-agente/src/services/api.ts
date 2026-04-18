const API_URL = 'https://sistema-emergencias-production.up.railway.app';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${res.status}`);
  }
  return res.json();
}

export async function listarFrota() {
  return request<any[]>('/frota');
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
