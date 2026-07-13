import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from './theme';

type Props = { children: React.ReactNode };
type State = { hasError: boolean };

/**
 * Extensões de navegador (tradutores, bloqueadores de ads, etc.) as vezes
 * mexem no DOM por fora do React e derrubam a arvore inteira com um
 * "removeChild"/NotFoundError sem relacao com o app em si. Sem boundary,
 * isso deixa a tela inteira em branco pro cidadao em pleno atendimento
 * de emergencia — por isso capturamos e oferecemos recarregar.
 */
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.warn('ErrorBoundary capturou um erro:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Text style={styles.icon}>⚠️</Text>
          <Text style={styles.title}>Ops, algo deu errado</Text>
          <Text style={styles.subtitle}>
            Tente recarregar a página. Se o problema persistir, verifique se
            alguma extensão do navegador está interferindo.
          </Text>
          <TouchableOpacity
            style={styles.button}
            onPress={() => {
              this.setState({ hasError: false });
              if (typeof window !== 'undefined') window.location.reload();
            }}
          >
            <Text style={styles.buttonText}>Recarregar</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  icon: { fontSize: 48, marginBottom: 16 },
  title: { color: colors.text, fontSize: 20, fontWeight: 'bold', marginBottom: 8 },
  subtitle: { color: colors.textSecondary, fontSize: 14, textAlign: 'center', marginBottom: 24 },
  button: { backgroundColor: colors.primary, paddingHorizontal: 24, paddingVertical: 14, borderRadius: 12 },
  buttonText: { color: colors.text, fontSize: 16, fontWeight: 'bold' },
});
