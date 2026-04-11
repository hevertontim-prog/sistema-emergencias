import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { criarUsuario } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const [cpf, setCpf] = useState('');
  const [nome, setNome] = useState('');
  const [loading, setLoading] = useState(false);

  function formatCpf(value: string) {
    const digits = value.replace(/\D/g, '').slice(0, 11);
    return digits
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  }

  async function handleLogin() {
    const cpfDigits = cpf.replace(/\D/g, '');
    if (cpfDigits.length !== 11) {
      Alert.alert('Erro', 'CPF deve ter 11 digitos');
      return;
    }
    if (nome.trim().length < 3) {
      Alert.alert('Erro', 'Informe seu nome completo');
      return;
    }
    setLoading(true);
    try {
      const usuario = await criarUsuario(cpfDigits, nome.trim());
      navigation.replace('Home', { cpf: cpfDigits, nome: nome.trim(), userId: usuario.id });
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao conectar ao servidor');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.header}>
        <Text style={styles.icon}>🚨</Text>
        <Text style={styles.title}>Emergencia Cidadao</Text>
        <Text style={styles.subtitle}>Sua seguranca em um toque</Text>
      </View>

      <View style={styles.form}>
        <Text style={styles.label}>CPF</Text>
        <TextInput
          style={styles.input}
          placeholder="000.000.000-00"
          placeholderTextColor={colors.textSecondary}
          keyboardType="numeric"
          value={cpf}
          onChangeText={(v) => setCpf(formatCpf(v))}
          maxLength={14}
        />

        <Text style={styles.label}>Nome completo</Text>
        <TextInput
          style={styles.input}
          placeholder="Seu nome"
          placeholderTextColor={colors.textSecondary}
          value={nome}
          onChangeText={setNome}
          autoCapitalize="words"
        />

        <TouchableOpacity style={[styles.button, loading && { opacity: 0.6 }]} onPress={handleLogin} disabled={loading}>
          <Text style={styles.buttonText}>{loading ? 'ENTRANDO...' : 'ENTRAR'}</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  icon: {
    fontSize: 64,
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: colors.text,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  form: {
    gap: 8,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 8,
  },
  input: {
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: colors.text,
  },
  button: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
});
