export type RootStackParamList = {
  Login: undefined;
  Home: { cpf: string; nome: string; userId: number };
  Acompanhamento: { emergenciaId: number; lat: number; lon: number; nome: string };
};
