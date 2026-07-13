const API_URL = 'https://sistema-emergencias-production.up.railway.app';
const API_KEY = process.env.EXPO_PUBLIC_API_KEY;

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
  descricao?: string | null;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY || '' },
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
  id_usuario: number,
  descricao?: string,
) {
  const body: Record<string, unknown> = { lat, lon, tipo, id_usuario };
  if (descricao) {
    body.descricao = descricao;
    // sem gravidade — o backend tria pela descricao (com fallback G3 se a IA falhar)
  } else {
    body.gravidade = 3;
  }
  return request<EmergenciaResponse>('/emergencia', {
    method: 'POST',
    body: JSON.stringify(body),
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
