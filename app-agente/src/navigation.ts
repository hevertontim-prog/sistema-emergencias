export type RootStackParamList = {
  Login: undefined;
  Chamados: { agenteId: number; nome: string };
  Atendimento: { despachoId: number; agenteId: number; lat: number; lon: number; nome: string };
};
