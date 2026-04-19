import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Alert,
  ActivityIndicator, Platform, ScrollView,
} from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { atualizarDespacho, buscarTriagem, buscarAcompanhamento, AcompanhamentoData } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Atendimento'>;

const STEPS = [
  { status: 'a_caminho', label: '🚑 A CAMINHO',  color: colors.primary },
  { status: 'no_local',  label: '📍 NO LOCAL',   color: '#8b5cf6' },
  { status: 'finalizado',label: '✅ FINALIZADO', color: colors.success },
];

const TIPO_ICON: Record<string, string> = {
  policia: '🚔', ambulancia: '🚑', bombeiro: '🚒',
};

function formatEta(segundos: number): string {
  if (segundos <= 0) return 'Chegando!';
  const min = Math.floor(segundos / 60);
  const seg = segundos % 60;
  if (min === 0) return `${seg}s`;
  return seg === 0 ? `${min} min` : `${min} min ${seg}s`;
}

function AgentMap({
  emergLat, emergLon, iframeRef,
}: {
  emergLat: number;
  emergLon: number;
  iframeRef: React.RefObject<HTMLIFrameElement>;
}) {
  const html = `<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"><\/script>
<style>html,body,#map{margin:0;padding:0;height:100%;width:100%;background:#1a1a2e}</style>
</head><body>
<div id="map"></div>
<script>
var map = L.map('map',{zoomControl:false}).setView([${emergLat},${emergLon}],14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'OSM'}).addTo(map);
var emergIcon = L.divIcon({html:'<div style="font-size:30px;filter:drop-shadow(0 0 6px #ef4444)">🔴<\/div>',iconSize:[32,32],iconAnchor:[16,16],className:''});
L.marker([${emergLat},${emergLon}],{icon:emergIcon}).addTo(map).bindPopup('Ocorrência').openPopup();
var agenteIcon = L.divIcon({html:'<div style="font-size:30px;filter:drop-shadow(0 0 4px #3b82f6)">📍<\/div>',iconSize:[36,36],iconAnchor:[18,18],className:''});
var agenteMarker = null;
var rotaLayer = null;
var rotaHalo = null;
window.addEventListener('message',function(e){
  if(!e.data) return;
  if(e.data.type==='UPDATE_AGENTE'){
    var ll=[e.data.lat,e.data.lon];
    if(!agenteMarker){
      agenteMarker=L.marker(ll,{icon:agenteIcon}).addTo(map).bindPopup('Você');
    } else {
      agenteMarker.setLatLng(ll);
    }
    if(e.data.fit && agenteMarker){
      map.fitBounds([[${emergLat},${emergLon}],ll],{padding:[30,30]});
    }
  } else if(e.data.type==='UPDATE_ROTA'){
    if(rotaLayer){ map.removeLayer(rotaLayer); rotaLayer=null; }
    if(rotaHalo){ map.removeLayer(rotaHalo); rotaHalo=null; }
    if(e.data.coords && e.data.coords.length>1){
      rotaHalo = L.polyline(e.data.coords,{color:'#1e3a8a',weight:9,opacity:0.35}).addTo(map);
      rotaLayer = L.polyline(e.data.coords,{
        color:'#3b82f6', weight:5, opacity:0.85,
        lineCap:'round', lineJoin:'round',
      }).addTo(map);
    }
  }
});
<\/script>
</body></html>`;

  if (Platform.OS !== 'web') {
    return (
      <View style={styles.mapContainer}>
        <Text style={{ color: colors.textSecondary, textAlign: 'center' }}>
          Ocorrência: {emergLat.toFixed(4)}, {emergLon.toFixed(4)}
        </Text>
      </View>
    );
  }

  return (
    <iframe
      ref={iframeRef as any}
      srcDoc={html}
      style={{ width: '100%', height: '100%', border: 'none', borderRadius: 12 } as any}
    />
  );
}

export default function AtendimentoScreen({ route, navigation }: Props) {
  const { despachoId, emergenciaId, agenteId, lat, lon, nome } = route.params;
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [triagem, setTriagem] = useState<string | null>(null);
  const [triagemLoading, setTriagemLoading] = useState(false);
  const [dados, setDados] = useState<AcompanhamentoData | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const firstUpdate = useRef(true);

  async function fetchRota(agLat: number, agLon: number) {
    try {
      const url = `https://router.project-osrm.org/route/v1/driving/${agLon},${agLat};${lon},${lat}?overview=full&geometries=geojson`;
      const r = await fetch(url);
      if (!r.ok) return;
      const j = await r.json();
      const coords = j?.routes?.[0]?.geometry?.coordinates;
      if (!coords || !iframeRef.current?.contentWindow) return;
      const latlngs = coords.map((c: number[]) => [c[1], c[0]]);
      iframeRef.current.contentWindow.postMessage(
        { type: 'UPDATE_ROTA', coords: latlngs },
        '*'
      );
    } catch {}
  }

  useEffect(() => {
    async function poll() {
      try {
        const d = await buscarAcompanhamento(emergenciaId);
        setDados(d);
        if (d.agente_lat && d.agente_lon && iframeRef.current?.contentWindow) {
          iframeRef.current.contentWindow.postMessage(
            { type: 'UPDATE_AGENTE', lat: d.agente_lat, lon: d.agente_lon, fit: firstUpdate.current },
            '*'
          );
          firstUpdate.current = false;
          fetchRota(d.agente_lat, d.agente_lon);
        }
      } catch {}
    }
    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [emergenciaId]);

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
      const res = await buscarTriagem(
        `Emergencia no local ${lat.toFixed(4)}, ${lon.toFixed(4)}. Agente ${nome} respondendo.`
      );
      setTriagem(res.triagem || res.briefing || JSON.stringify(res));
    } catch (err: any) {
      Alert.alert('Erro', err.message);
    } finally {
      setTriagemLoading(false);
    }
  }

  const step = STEPS[currentStep];
  const tipoIcon = TIPO_ICON[dados?.tipo_recurso || ''] || '🚨';

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      <Text style={styles.title}>Atendimento</Text>
      <Text style={styles.protocolo}>Despacho #{despachoId} · Ocorrência #{emergenciaId}</Text>

      {/* ETA para o agente */}
      {dados?.eta_segundos !== null && dados?.eta_segundos !== undefined && (
        <View style={styles.etaBox}>
          <Text style={styles.etaIcon}>{tipoIcon}</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.etaLabel}>Tempo restante de deslocamento</Text>
            <Text style={[styles.etaValor, dados.eta_segundos <= 30 && { color: '#10b981' }]}>
              {formatEta(dados.eta_segundos)}
            </Text>
          </View>
          {dados.distancia_km !== null && (
            <Text style={styles.etaDist}>{dados.distancia_km} km</Text>
          )}
        </View>
      )}

      <View style={styles.mapContainer}>
        <AgentMap emergLat={lat} emergLon={lon} iframeRef={iframeRef} />
      </View>

      <View style={styles.stepsRow}>
        {STEPS.map((s, i) => (
          <View key={s.status} style={[styles.stepDot, {
            backgroundColor: i <= currentStep ? s.color : '#1e293b',
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
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.actionText}>{step.label}</Text>
        }
      </TouchableOpacity>

      <TouchableOpacity style={styles.triagemBtn} onPress={handleTriagem} disabled={triagemLoading}>
        {triagemLoading
          ? <ActivityIndicator color={colors.primary} />
          : <Text style={styles.triagemBtnText}>🤖 Solicitar Triagem IA</Text>
        }
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: 20, paddingTop: 50 },
  title: { color: colors.text, fontSize: 24, fontWeight: 'bold' },
  protocolo: { color: colors.textSecondary, fontSize: 13, marginTop: 2 },
  etaBox: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: colors.surface, borderRadius: 14, padding: 14,
    marginTop: 16, borderWidth: 1, borderColor: '#3b82f6',
  },
  etaIcon: { fontSize: 30 },
  etaLabel: { color: colors.textSecondary, fontSize: 11 },
  etaValor: { color: '#a78bfa', fontSize: 20, fontWeight: 'bold' },
  etaDist: { color: colors.textSecondary, fontSize: 13 },
  mapContainer: { height: 220, marginTop: 16, borderRadius: 12, overflow: 'hidden' },
  stepsRow: { flexDirection: 'row', justifyContent: 'center', gap: 16, marginTop: 20 },
  stepDot: { width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  stepText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  actionBtn: { padding: 18, borderRadius: 12, alignItems: 'center', marginTop: 20 },
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
