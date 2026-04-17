const API_URL = 'http://localhost:8006';

export interface Usuario {
  id: number;
  cpf: string;
  nome: string;
  created_at: string;
}

export interface EmergenciaResponse {
  id: number;
  lat: number;
  lon: number;
  tipo: string;
  gravidade: number;
  status: string;
  id_usuario: number;
  created_at: string;
}

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

export function criarUsuario(cpf: string, nome: string) {
  return request<Usuario>('/usuario', {
    method: 'POST',
    body: JSON.stringify({ cpf, nome }),
  });
}

export function criarEmergencia(
  lat: number,
  lon: number,
  tipo: string,
  gravidade: number,
  id_usuario: number,
) {
  return request<EmergenciaResponse>('/emergencia', {
    method: 'POST',
    body: JSON.stringify({ lat, lon, tipo, gravidade, id_usuario }),
  });
}

export function salvarPushToken(userId: number, push_token: string) {
  return request<any>(`/usuario/${userId}/push-token`, {
    method: 'PUT',
    body: JSON.stringify({ push_token }),
  });
}

export async function despachar(id_emergencia: number) {
  return request<any>('/despacho', {
    method: 'POST',
    body: JSON.stringify({ id_emergencia }),
  });
}

export async function buscarEmergencia(id: number) {
  return request<any>(`/emergencia/${id}`);
}

export async function buscarFrota() {
  return request<any[]>('/frota');
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
