import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Vibration,
  Platform,
  ScrollView,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Location from 'expo-location';
import { colors } from '../theme';
import { criarEmergencia } from '../services/api';
import { registrarPushToken } from '../services/notifications';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Home'>;

function MiniMap({ lat, lon }: { lat: number; lon: number }) {
  if (Platform.OS === 'web') {
    const src = `https://www.openstreetmap.org/export/embed.html?bbox=${lon - 0.01},${lat - 0.005},${lon + 0.01},${lat + 0.005}&layer=mapnik&marker=${lat},${lon}`;
    return (
      <iframe
        src={src}
        width="100%"
        height="200"
        style={{ border: 'none', borderRadius: 12 } as any}
      />
    );
  }
  return (
    <View style={{ height: 200, backgroundColor: colors.surface, borderRadius: 12, justifyContent: 'center', alignItems: 'center' }}>
      <Text style={{ color: colors.textSecondary, fontSize: 13 }}>
        Mapa: {lat.toFixed(4)}, {lon.toFixed(4)}
      </Text>
    </View>
  );
}

const TIPOS = [
  { tipo: 'policia', label: 'Emergência\nPolicial', icon: '🚔', color: '#3b82f6', colorDark: '#1d4ed8' },
  { tipo: 'medica', label: 'Emergência\nMédica', icon: '🚑', color: '#E63946', colorDark: '#B22D38' },
];

export default function HomeScreen({ route, navigation }: Props) {
  const { cpf, nome, userId } = route.params;
  const [loading, setLoading] = useState<string | null>(null);
  const [descricao, setDescricao] = useState('');
  const [lastEmergencia, setLastEmergencia] = useState<{
    id: number;
    status: string;
    lat: number;
    lon: number;
    tipo: string;
  } | null>(null);

  useEffect(() => {
    registrarPushToken(userId);
  }, [userId]);

  async function handleEmergencia(tipo: string) {
    setLoading(tipo);
    Vibration.vibrate(200);

    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      let lat = -15.7939, lon = -47.8828;
      if (status === 'granted') {
        try {
          const loc = await Promise.race([
            Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error('timeout')), 5000)
            ),
          ]);
          lat = loc.coords.latitude;
          lon = loc.coords.longitude;
        } catch {
          // timeout ou erro GPS — usa fallback Brasilia
        }
      }

      const emergencia = await criarEmergencia(lat, lon, tipo, userId, descricao.trim() || undefined);
      setLastEmergencia({ id: emergencia.id, status: emergencia.status, lat, lon, tipo });

      navigation.navigate('Acompanhamento', {
        emergenciaId: emergencia.id, lat, lon, nome,
      });
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao enviar emergencia');
    } finally {
      setLoading(null);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ flexGrow: 1 }}>
      <View style={styles.userBar}>
        <View>
          <Text style={styles.greeting}>Olá, {nome.split(' ')[0]}</Text>
          <Text style={styles.cpfText}>CPF: {cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.***.***-$4')}</Text>
        </View>
        <TouchableOpacity onPress={() => navigation.replace('Login')}>
          <Text style={styles.logout}>Sair</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.center}>
        <View style={styles.descricaoBlock}>
          <Text style={styles.descricaoLabel}>O que está acontecendo?</Text>
          <View style={styles.descricaoRow}>
            <TextInput
              style={styles.descricaoInput}
              placeholder="Descreva em poucas palavras — ajuda a IA a priorizar seu atendimento"
              placeholderTextColor={colors.textSecondary}
              value={descricao}
              onChangeText={(v) => setDescricao(v.slice(0, 300))}
              maxLength={300}
              multiline
              numberOfLines={3}
            />
            <View style={styles.micButton}>
              <Text style={styles.micIcon}>🎤</Text>
            </View>
          </View>
          <Text style={styles.micHint}>áudio: em breve</Text>
        </View>

        <Text style={styles.instruction}>Selecione o tipo de emergência</Text>

        <View style={styles.buttonsRow}>
          {TIPOS.map(({ tipo, label, icon, color, colorDark }) => {
            const isLoading = loading === tipo;
            const isDisabled = loading !== null;
            return (
              <TouchableOpacity
                key={tipo}
                style={[
                  styles.emergencyButton,
                  { backgroundColor: color, borderColor: colorDark, shadowColor: color },
                  isDisabled && styles.buttonDisabled,
                ]}
                onPress={() => handleEmergencia(tipo)}
                disabled={isDisabled}
                activeOpacity={0.7}
              >
                {isLoading ? (
                  <ActivityIndicator size="large" color="#fff" />
                ) : (
                  <>
                    <Text style={styles.emergencyIcon}>{icon}</Text>
                    <Text style={styles.emergencyText}>{label}</Text>
                  </>
                )}
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.hint}>Sua localização GPS será enviada automaticamente</Text>
      </View>

      {lastEmergencia && (
        <View style={styles.statusBar}>
          <Text style={styles.statusTitle}>Último chamado</Text>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Protocolo:</Text>
            <Text style={styles.statusValue}>#{lastEmergencia.id}</Text>
          </View>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Tipo:</Text>
            <Text style={styles.statusValue}>{lastEmergencia.tipo === 'policia' ? 'Policial' : 'Médica'}</Text>
          </View>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Status:</Text>
            <View style={styles.statusBadge}>
              <Text style={styles.statusBadgeText}>{lastEmergencia.status.toUpperCase()}</Text>
            </View>
          </View>
          <View style={{ marginTop: 12 }}>
            <MiniMap lat={lastEmergencia.lat} lon={lastEmergencia.lon} />
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: 24,
    paddingTop: 60,
  },
  userBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  greeting: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
  },
  cpfText: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 2,
  },
  logout: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: '600',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 32,
  },
  instruction: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 32,
  },
  descricaoBlock: {
    width: '100%',
    maxWidth: 420,
    marginBottom: 24,
  },
  descricaoLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  descricaoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  descricaoInput: {
    flex: 1,
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 14,
    color: colors.text,
    fontSize: 14,
    minHeight: 72,
    textAlignVertical: 'top',
  },
  micButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.4,
  },
  micIcon: {
    fontSize: 18,
  },
  micHint: {
    fontSize: 11,
    color: colors.textSecondary,
    textAlign: 'right',
    marginTop: 4,
  },
  buttonsRow: {
    flexDirection: 'row',
    gap: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emergencyButton: {
    width: 150,
    height: 170,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 16,
    borderWidth: 3,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  emergencyIcon: {
    fontSize: 44,
    marginBottom: 10,
  },
  emergencyText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    textAlign: 'center',
    lineHeight: 20,
  },
  hint: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 28,
  },
  statusBar: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 20,
    marginBottom: 32,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statusTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  statusLabel: {
    color: colors.textSecondary,
    fontSize: 14,
    marginRight: 8,
  },
  statusValue: {
    color: colors.accent,
    fontSize: 14,
    fontWeight: 'bold',
  },
  statusBadge: {
    backgroundColor: colors.success,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 8,
  },
  statusBadgeText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: 'bold',
  },
});
