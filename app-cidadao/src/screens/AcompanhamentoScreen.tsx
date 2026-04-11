import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Platform } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { buscarEmergencia, buscarFrota } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Acompanhamento'>;

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  aberta: { label: 'ABERTA', color: '#f59e0b' },
  despachada: { label: 'VIATURA DESPACHADA', color: '#3b82f6' },
  em_atendimento: { label: 'A CAMINHO', color: '#8b5cf6' },
  concluida: { label: 'CONCLUÍDA', color: '#10b981' },
};

function LeafletMap({ lat, lon, viatura }: { lat: number; lon: number; viatura: { lat: number; lon: number } | null }) {
  if (Platform.OS !== 'web') {
    return (
      <View style={styles.mapFallback}>
        <Text style={{ color: colors.textSecondary }}>Mapa: {lat.toFixed(4)}, {lon.toFixed(4)}</Text>
      </View>
    );
  }

  const html = `<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"><\/script>
<style>html,body,#map{margin:0;padding:0;height:100%;width:100%}</style>
</head><body>
<div id="map"></div>
<script>
var map=L.map('map').setView([${lat},${lon}],14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'OSM'}).addTo(map);
L.circleMarker([${lat},${lon}],{radius:12,color:'#ef4444',fillColor:'#ef4444',fillOpacity:0.9}).addTo(map).bindPopup('<b>Sua localização</b>').openPopup();
${viatura ? `L.marker([${viatura.lat},${viatura.lon}]).addTo(map).bindPopup('<b>Viatura</b>');` : ''}
</script>
</body></html>`;

  return (
    <iframe
      srcDoc={html}
      style={{ width: '100%', height: 300, border: 'none', borderRadius: 12 } as any}
    />
  );
}

export default function AcompanhamentoScreen({ route, navigation }: Props) {
  const { emergenciaId, lat, lon, nome } = route.params;
  const [status, setStatus] = useState('aberta');
  const [viatura, setViatura] = useState<{ lat: number; lon: number } | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    async function poll() {
      try {
        const em = await buscarEmergencia(emergenciaId);
        setStatus(em.status);
        const frota = await buscarFrota();
        const v = frota.find((f: any) => f.despacho_id === emergenciaId);
        if (v) setViatura({ lat: v.latitude, lon: v.longitude });
      } catch {}
    }
    poll();
    intervalRef.current = setInterval(poll, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [emergenciaId]);

  const info = STATUS_LABELS[status] || STATUS_LABELS.aberta;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Acompanhamento</Text>
      <Text style={styles.protocolo}>Protocolo #{emergenciaId}</Text>

      <View style={[styles.badge, { backgroundColor: info.color }]}>
        <Text style={styles.badgeText}>{info.label}</Text>
      </View>

      <View style={styles.mapContainer}>
        <LeafletMap lat={lat} lon={lon} viatura={viatura} />
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoText}>
          {status === 'aberta' && 'Aguardando despacho de viatura...'}
          {status === 'despachada' && 'Viatura despachada! Acompanhe no mapa.'}
          {status === 'em_atendimento' && 'Viatura a caminho da sua localizacao!'}
          {status === 'concluida' && 'Atendimento concluido.'}
        </Text>
      </View>

      <View style={styles.coordBox}>
        <Text style={styles.coordText}>Lat: {lat.toFixed(6)}  |  Lon: {lon.toFixed(6)}</Text>
      </View>

      <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
        <Text style={styles.backBtnText}>Voltar</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 20,
    paddingTop: 50,
    paddingBottom: 40,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: 'bold',
  },
  protocolo: {
    color: colors.textSecondary,
    fontSize: 16,
    marginTop: 4,
  },
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginTop: 16,
  },
  badgeText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  mapContainer: {
    marginTop: 16,
    borderRadius: 12,
    overflow: 'hidden',
    height: 300,
  },
  mapFallback: {
    height: 300,
    backgroundColor: colors.surface,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  infoBox: {
    backgroundColor: colors.surface,
    padding: 16,
    borderRadius: 12,
    marginTop: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  infoText: {
    color: colors.text,
    fontSize: 16,
    textAlign: 'center',
  },
  coordBox: {
    marginTop: 8,
    alignItems: 'center',
  },
  coordText: {
    color: colors.textSecondary,
    fontSize: 12,
  },
  backBtn: {
    backgroundColor: colors.primary,
    padding: 16,
    borderRadius: 12,
    marginTop: 16,
    alignItems: 'center',
  },
  backBtnText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
});
