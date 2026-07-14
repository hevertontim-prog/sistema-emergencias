import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { RootStackParamList } from '../navigation';
import { buscarAgentePorMatricula } from '../services/api';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

// estado simples em memória (sem AsyncStorage — não é dependência do projeto ainda);
// lembra a última matrícula só durante a sessão atual do app, reseta em reload/restart.
let ultimaMatriculaDigitada = '';

export default function LoginScreen({ navigation }: Props) {
  const [matricula, setMatricula] = useState(ultimaMatriculaDigitada);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleLogin() {
    const valor = matricula.trim();
    if (!valor) return;
    ultimaMatriculaDigitada = valor;
    setErro(null);
    setLoading(true);
    try {
      const ag = await buscarAgentePorMatricula(valor);

      // TODO: registrar push token via PUT /agente/{id}/push-token quando
      // Platform !== 'web' — depende de expo-notifications, ainda não é
      // dependência do app-agente (não adicionar agora).

      navigation.replace('Chamados', { agenteId: ag.id, nome: ag.nome });
    } catch (e: any) {
      if (e?.status === 404) {
        setErro('Matrícula não cadastrada. Procure o gestor da central.');
      } else {
        setErro('Sem conexão com a central. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>🚑</Text>
      <Text style={styles.title}>SalvAI Agente</Text>
      <Text style={styles.subtitle}>Acesso para equipes de emergência</Text>

      <TextInput
        style={styles.input}
        placeholder="Ex.: PM001"
        placeholderTextColor={colors.textSecondary}
        value={matricula}
        onChangeText={(v) => { setMatricula(v); setErro(null); }}
        autoCapitalize="characters"
        autoCorrect={false}
      />

      {erro && <Text style={styles.erro}>{erro}</Text>}

      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        {loading ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator color={colors.text} />
            <Text style={styles.buttonText}>Verificando...</Text>
          </View>
        ) : (
          <Text style={styles.buttonText}>ENTRAR</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, justifyContent: 'center', padding: 32 },
  logo: { fontSize: 64, textAlign: 'center' },
  title: { color: colors.text, fontSize: 28, fontWeight: 'bold', textAlign: 'center', marginTop: 8 },
  subtitle: { color: colors.textSecondary, fontSize: 14, textAlign: 'center', marginBottom: 32 },
  input: {
    backgroundColor: colors.surface, color: colors.text, padding: 16,
    borderRadius: 12, fontSize: 16, marginBottom: 12,
    borderWidth: 1, borderColor: '#1e293b',
  },
  erro: {
    color: '#ef4444', fontSize: 13, textAlign: 'center', marginBottom: 12,
  },
  button: {
    backgroundColor: colors.primary, padding: 16, borderRadius: 12,
    alignItems: 'center', marginTop: 8,
  },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  buttonText: { color: colors.text, fontSize: 18, fontWeight: 'bold' },
});
