import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Location from 'expo-location';
import { colors } from '../theme';
import { listarFrota, buscarEmergencia, enviarPosicao } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Chamados'>;

type Chamado = {
  despachoId: number;
  emergenciaId: number;
  status: string;
  lat: number;
  lon: number;
  tipo: string;
};

export default function ChamadosScreen({ route, navigation }: Props) {
  const { agenteId, nome } = route.params;
  const [chamados, setChamados] = useState<Chamado[]>([]);
  const [loading, setLoading] = useState(true);
  const gpsRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchChamados();
    const interval = setInterval(fetchChamados, 5000);
    startGPS();
    return () => {
      clearInterval(interval);
      if (gpsRef.current) clearInterval(gpsRef.current);
    };
  }, []);

  async function startGPS() {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return;

    gpsRef.current = setInterval(async () => {
      try {
        const loc = await Promise.race([
          Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
          new Promise<never>((_, rej) => setTimeout(() => rej('timeout'), 5000)),
        ]);
        await enviarPosicao(agenteId, loc.coords.latitude, loc.coords.longitude);
      } catch {}
    }, 10000);
  }

  async function fetchChamados() {
    try {
      const frota = await listarFrota();
      const meus = frota.filter((f: any) => f.id === agenteId && f.despacho_id);
      const lista: Chamado[] = [];
      for (const item of meus) {
        try {
          const em = await buscarEmergencia(item.emergencia_id);
          lista.push({
            despachoId: item.despacho_id,
            emergenciaId: em.id,
            status: em.status,
            lat: em.lat ?? em.latitude,
            lon: em.lon ?? em.longitude,
            tipo: em.tipo || 'emergencia',
          });
        } catch {}
      }
      setChamados(lista);
    } catch {} finally {
      setLoading(false);
    }
  }

  function handleChamado(item: Chamado) {
    navigation.navigate('Atendimento', {
      despachoId: item.despachoId,
      emergenciaId: item.emergenciaId,
      agenteId,
      lat: item.lat,
      lon: item.lon,
      nome,
    });
  }

  const statusColor: Record<string, string> = {
    aberta: colors.warning,
    despachada: colors.primary,
    em_atendimento: '#8b5cf6',
    concluida: colors.success,
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Chamados</Text>
          <Text style={styles.subtitle}>Agente: {nome} (#{agenteId})</Text>
        </View>
        <TouchableOpacity onPress={() => navigation.replace('Login')}>
          <Text style={styles.logout}>Sair</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.gpsBar}>
        <Text style={styles.gpsText}>📡 GPS ativo — posição enviada a cada 10s</Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={colors.primary} style={{ marginTop: 40 }} />
      ) : chamados.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>📋</Text>
          <Text style={styles.emptyText}>Nenhum chamado no momento</Text>
          <Text style={styles.emptyHint}>Atualizando automaticamente...</Text>
        </View>
      ) : (
        <FlatList
          data={chamados}
          keyExtractor={(item) => String(item.despachoId)}
          contentContainerStyle={{ paddingBottom: 20 }}
          renderItem={({ item }) => (
            <TouchableOpacity style={styles.card} onPress={() => handleChamado(item)}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>🚨 Protocolo #{item.emergenciaId}</Text>
                <View style={[styles.badge, { backgroundColor: statusColor[item.status] || colors.warning }]}>
                  <Text style={styles.badgeText}>{item.status.toUpperCase()}</Text>
                </View>
              </View>
              <Text style={styles.cardInfo}>Tipo: {item.tipo}</Text>
              <Text style={styles.cardInfo}>📍 {item.lat.toFixed(4)}, {item.lon.toFixed(4)}</Text>
              <Text style={styles.cardAction}>Toque para atender →</Text>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, paddingTop: 50 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20 },
  title: { color: colors.text, fontSize: 24, fontWeight: 'bold' },
  subtitle: { color: colors.textSecondary, fontSize: 14, marginTop: 2 },
  logout: { color: colors.danger, fontSize: 16 },
  gpsBar: { backgroundColor: colors.surface, marginHorizontal: 20, marginTop: 12, padding: 10, borderRadius: 8 },
  gpsText: { color: colors.success, fontSize: 13, textAlign: 'center' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyIcon: { fontSize: 48 },
  emptyText: { color: colors.text, fontSize: 18, marginTop: 12 },
  emptyHint: { color: colors.textSecondary, fontSize: 14, marginTop: 4 },
  card: {
    backgroundColor: colors.surface, marginHorizontal: 20, marginTop: 12,
    padding: 16, borderRadius: 12, borderLeftWidth: 4, borderLeftColor: colors.warning,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { color: colors.text, fontSize: 16, fontWeight: 'bold' },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  cardInfo: { color: colors.textSecondary, fontSize: 14, marginTop: 6 },
  cardAction: { color: colors.primary, fontSize: 14, marginTop: 10, fontWeight: '600' },
});
