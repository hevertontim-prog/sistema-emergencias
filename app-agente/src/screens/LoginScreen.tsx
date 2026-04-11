import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const [matricula, setMatricula] = useState('');
  const [nome, setNome] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!matricula.trim() || !nome.trim()) return;
    setLoading(true);
    try {
      const agenteId = parseInt(matricula) || 1;
      navigation.replace('Chamados', { agenteId, nome: nome.trim() });
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
        placeholder="Matrícula"
        placeholderTextColor={colors.textSecondary}
        value={matricula}
        onChangeText={setMatricula}
        keyboardType="numeric"
      />
      <TextInput
        style={styles.input}
        placeholder="Nome completo"
        placeholderTextColor={colors.textSecondary}
        value={nome}
        onChangeText={setNome}
      />

      <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
        {loading ? (
          <ActivityIndicator color={colors.text} />
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
  button: {
    backgroundColor: colors.primary, padding: 16, borderRadius: 12,
    alignItems: 'center', marginTop: 8,
  },
  buttonText: { color: colors.text, fontSize: 18, fontWeight: 'bold' },
});
