import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
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

export default function HomeScreen({ route, navigation }: Props) {
  const { cpf, nome, userId } = route.params;
  const [loading, setLoading] = useState(false);
  const [lastEmergencia, setLastEmergencia] = useState<{
    id: number;
    status: string;
    lat: number;
    lon: number;
  } | null>(null);

  useEffect(() => {
    registrarPushToken(userId);
  }, [userId]);

  async function handleEmergencia() {
    setLoading(true);
    Vibration.vibrate(200);

    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      let lat = -15.7939, lon = -47.8828;
      if (status === 'granted') {
        try {
          const loc = await Promise.race([
            Location.getCurrentPositionAsync({
              accuracy: Location.Accuracy.Balanced,
            }),
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

      const emergencia = await criarEmergencia(lat, lon, 'emergencia_cidadao', 3, userId);
      // Backend ja faz auto-despacho dentro do POST /emergencia
      setLastEmergencia({ id: emergencia.id, status: emergencia.status, lat, lon });

      navigation.navigate('Acompanhamento', {
        emergenciaId: emergencia.id, lat, lon, nome,
      });
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao enviar emergencia');
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ flexGrow: 1 }}>
      <View style={styles.userBar}>
        <View>
          <Text style={styles.greeting}>Ola, {nome.split(' ')[0]}</Text>
          <Text style={styles.cpfText}>CPF: {cpf.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.***.***-$4')}</Text>
        </View>
        <TouchableOpacity onPress={() => navigation.replace('Login')}>
          <Text style={styles.logout}>Sair</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.center}>
        <Text style={styles.instruction}>
          Pressione o botao em caso de emergencia
        </Text>

        <TouchableOpacity
          style={[styles.emergencyButton, loading && styles.buttonDisabled]}
          onPress={handleEmergencia}
          disabled={loading}
          activeOpacity={0.7}
        >
          {loading ? (
            <ActivityIndicator size="large" color={colors.text} />
          ) : (
            <>
              <Text style={styles.emergencyIcon}>🚨</Text>
              <Text style={styles.emergencyText}>EMERGENCIA</Text>
            </>
          )}
        </TouchableOpacity>

        <Text style={styles.hint}>
          Sua localizacao GPS sera enviada automaticamente
        </Text>
      </View>

      {lastEmergencia && (
        <View style={styles.statusBar}>
          <Text style={styles.statusTitle}>Ultimo chamado</Text>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Protocolo:</Text>
            <Text style={styles.statusValue}>#{lastEmergencia.id}</Text>
          </View>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Status:</Text>
            <View style={styles.statusBadge}>
              <Text style={styles.statusBadgeText}>
                {lastEmergencia.status.toUpperCase()}
              </Text>
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
  emergencyButton: {
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 30,
    elevation: 20,
    borderWidth: 4,
    borderColor: colors.primaryDark,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  emergencyIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  emergencyText: {
    color: colors.text,
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2,
  },
  hint: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 24,
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
