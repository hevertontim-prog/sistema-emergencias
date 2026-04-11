import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { atualizarDespacho, buscarTriagem } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Atendimento'>;

const STEPS = [
  { status: 'a_caminho', label: '🚑 A CAMINHO', color: colors.primary },
  { status: 'no_local', label: '📍 NO LOCAL', color: '#8b5cf6' },
  { status: 'finalizado', label: '✅ FINALIZADO', color: colors.success },
];

export default function AtendimentoScreen({ route, navigation }: Props) {
  const { despachoId, agenteId, lat, lon, nome } = route.params;
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [triagem, setTriagem] = useState<string | null>(null);
  const [triagemLoading, setTriagemLoading] = useState(false);

  async function handleAvancar() {
    const step = STEPS[currentStep];
    setLoading(true);
    try {
      await atualizarDespacho(despachoId, step.status);
      if (currentStep < STEPS.length - 1) {
        setCurrentStep(currentStep + 1);
      } else {
        Alert.alert('Concluído', 'Atendimento finalizado com sucesso!', [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      }
    } catch (err: any) {
      Alert.alert('Erro', err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleTriagem() {
    setTriagemLoading(true);
    try {
      const res = await buscarTriagem(`Emergencia no local ${lat.toFixed(4)}, ${lon.toFixed(4)}. Agente ${nome} respondendo.`);
      setTriagem(res.triagem || res.briefing || JSON.stringify(res));
    } catch (err: any) {
      Alert.alert('Erro', err.message);
    } finally {
      setTriagemLoading(false);
    }
  }

  const step = STEPS[currentStep];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Atendimento</Text>
      <Text style={styles.protocolo}>Despacho #{despachoId}</Text>

      <View style={styles.mapContainer}>
        <iframe
          style={{ width: '100%', height: '100%', border: 'none', borderRadius: 12 } as any}
          srcDoc={`
            <!DOCTYPE html>
            <html><head>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>html,body,#map{margin:0;height:100%}</style>
            </head><body><div id="map"></div><script>
              var map = L.map('map').setView([${lat},${lon}],15);
              L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
                attribution:'OSM'
              }).addTo(map);
              L.circleMarker([${lat},${lon}],{radius:12,color:'#ef4444',fillColor:'#ef4444',fillOpacity:0.8})
                .addTo(map).bindPopup('Cidadao').openPopup();
            </script></body></html>
          `}
        />
      </View>

      <View style={styles.stepsRow}>
        {STEPS.map((s, i) => (
          <View key={s.status} style={[styles.stepDot, {
            backgroundColor: i <= currentStep ? s.color : '#1e293b'
          }]}>
            <Text style={styles.stepText}>{i < currentStep ? '✓' : i + 1}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity
        style={[styles.actionBtn, { backgroundColor: step.color }]}
        onPress={handleAvancar}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.actionText}>{step.label}</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity style={styles.triagemBtn} onPress={handleTriagem} disabled={triagemLoading}>
        {triagemLoading ? (
          <ActivityIndicator color={colors.primary} />
        ) : (
          <Text style={styles.triagemBtnText}>🤖 Solicitar Triagem IA</Text>
        )}
      </TouchableOpacity>

      {triagem && (
        <View style={styles.triagemBox}>
          <Text style={styles.triagemTitle}>Triagem IA:</Text>
          <Text style={styles.triagemText}>{triagem}</Text>
        </View>
      )}

      <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>← Voltar aos chamados</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 20, paddingTop: 50 },
  title: { color: colors.text, fontSize: 24, fontWeight: 'bold' },
  protocolo: { color: colors.textSecondary, fontSize: 14, marginTop: 2 },
  mapContainer: { height: 200, marginTop: 16, borderRadius: 12, overflow: 'hidden' },
  stepsRow: { flexDirection: 'row', justifyContent: 'center', gap: 16, marginTop: 20 },
  stepDot: {
    width: 40, height: 40, borderRadius: 20,
    justifyContent: 'center', alignItems: 'center',
  },
  stepText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  actionBtn: {
    padding: 18, borderRadius: 12, alignItems: 'center', marginTop: 20,
  },
  actionText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  triagemBtn: {
    backgroundColor: colors.surface, padding: 14, borderRadius: 12,
    alignItems: 'center', marginTop: 12,
  },
  triagemBtnText: { color: colors.primary, fontSize: 16, fontWeight: '600' },
  triagemBox: {
    backgroundColor: colors.surface, padding: 14, borderRadius: 12, marginTop: 12,
    borderLeftWidth: 3, borderLeftColor: colors.primary,
  },
  triagemTitle: { color: colors.primary, fontWeight: 'bold', marginBottom: 6 },
  triagemText: { color: colors.text, fontSize: 14, lineHeight: 20 },
  backBtn: { padding: 14, alignItems: 'center', marginTop: 12 },
  backText: { color: colors.textSecondary, fontSize: 15 },
});
