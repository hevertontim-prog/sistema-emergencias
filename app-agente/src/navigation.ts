export type RootStackParamList = {
  Login: undefined;
  Chamados: { agenteId: number; nome: string };
  Atendimento: {
    despachoId: number; emergenciaId: number; agenteId: number; lat: number; lon: number; nome: string;
    tipo?: string; gravidade?: number; descricao?: string;
  };
};
