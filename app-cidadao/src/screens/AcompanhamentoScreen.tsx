import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Platform } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { colors } from '../theme';
import { buscarAcompanhamento, AcompanhamentoData } from '../services/api';
import { RootStackParamList } from '../navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Acompanhamento'>;

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  aberta:         { label: 'AGUARDANDO VIATURA',  color: '#f59e0b' },
  despachada:     { label: 'VIATURA DESPACHADA',  color: '#3b82f6' },
  em_atendimento: { label: 'A CAMINHO',           color: '#8b5cf6' },
  no_local:       { label: 'NO LOCAL',            color: '#f97316' },
  concluida:      { label: 'CONCLUÍDA',           color: '#10b981' },
};

const TIPO_ICON: Record<string, string> = {
  policia:    '🚔',
  ambulancia: '🚑',
  bombeiro:   '🚒',
};

function formatEta(segundos: number): string {
  if (segundos <= 0) return 'Chegando agora!';
  const min = Math.floor(segundos / 60);
  const seg = segundos % 60;
  if (min === 0) return `${seg}s`;
  return seg === 0 ? `${min} min` : `${min} min ${seg}s`;
}

function LeafletMap({
  lat, lon, tipoRecurso, iframeRef,
}: {
  lat: number;
  lon: number;
  tipoRecurso: string | null;
  iframeRef: React.RefObject<HTMLIFrameElement>;
}) {
  const icon = TIPO_ICON[tipoRecurso || ''] || '🚨';

  const html = `<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"><\/script>
<style>html,body,#map{margin:0;padding:0;height:100%;width:100%;background:#1a1a2e}</style>
</head><body>
<div id="map"></div>
<script>
var map = L.map('map',{zoomControl:false}).setView([${lat},${lon}],14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'OSM'}).addTo(map);
var emergIcon = L.divIcon({html:'<div style="font-size:30px;filter:drop-shadow(0 0 6px #ef4444)">🔴<\/div>',iconSize:[32,32],iconAnchor:[16,16],className:''});
L.marker([${lat},${lon}],{icon:emergIcon}).addTo(map).bindPopup('Sua localização').openPopup();
var viaturaIcon = L.divIcon({html:'<div style="font-size:30px;filter:drop-shadow(0 0 4px #3b82f6)">${icon}<\/div>',iconSize:[36,36],iconAnchor:[18,18],className:''});
var viaturaMarker = null;
var rotaLayer = null;
window.addEventListener('message',function(e){
  if(!e.data) return;
  if(e.data.type==='UPDATE_VIATURA'){
    var ll=[e.data.lat,e.data.lon];
    if(!viaturaMarker){
      viaturaMarker=L.marker(ll,{icon:viaturaIcon}).addTo(map).bindPopup('Viatura');
    } else {
      viaturaMarker.setLatLng(ll);
    }
  } else if(e.data.type==='UPDATE_ROTA'){
    if(rotaLayer){ map.removeLayer(rotaLayer); rotaLayer=null; }
    if(e.data.coords && e.data.coords.length>1){
      rotaLayer = L.polyline(e.data.coords,{
        color:'#3b82f6', weight:5, opacity:0.85,
        lineCap:'round', lineJoin:'round',
      }).addTo(map);
      // halo
      L.polyline(e.data.coords,{color:'#1e3a8a',weight:9,opacity:0.35}).addTo(rotaLayer);
      if(e.data.fit){
        map.fitBounds(rotaLayer.getBounds(),{padding:[30,30]});
      }
    }
  }
});
<\/script>
</body></html>`;

  if (Platform.OS !== 'web') {
    return (
      <View style={styles.mapFallback}>
        <Text style={{ color: colors.textSecondary }}>Mapa: {lat.toFixed(4)}, {lon.toFixed(4)}</Text>
      </View>
    );
  }

  return (
    <iframe
      ref={iframeRef as any}
      srcDoc={html}
      style={{ width: '100%', height: 300, border: 'none', borderRadius: 12 } as any}
    />
  );
}

export default function AcompanhamentoScreen({ route, navigation }: Props) {
  const { emergenciaId, lat, lon, nome } = route.params;
  const [dados, setDados] = useState<AcompanhamentoData | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const rotaFitRef = useRef(false);

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
        { type: 'UPDATE_ROTA', coords: latlngs, fit: !rotaFitRef.current },
        '*'
      );
      rotaFitRef.current = true;
    } catch {}
  }

  useEffect(() => {
    async function poll() {
      try {
        const d = await buscarAcompanhamento(emergenciaId);
        setDados(d);
        if (d.agente_lat && d.agente_lon && iframeRef.current?.contentWindow) {
          iframeRef.current.contentWindow.postMessage(
            { type: 'UPDATE_VIATURA', lat: d.agente_lat, lon: d.agente_lon },
            '*'
          );
          fetchRota(d.agente_lat, d.agente_lon);
        }
      } catch {}
    }
    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [emergenciaId]);

  const status = dados?.status || 'aberta';
  const info = STATUS_LABELS[status] || STATUS_LABELS.aberta;
  const temViatura = !!dados?.agente_lat;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Acompanhamento</Text>
      <Text style={styles.protocolo}>Protocolo #{emergenciaId}</Text>

      <View style={[styles.badge, { backgroundColor: info.color }]}>
        <Text style={styles.badgeText}>{info.label}</Text>
      </View>

      {/* ETA panel */}
      {temViatura && dados?.eta_segundos !== null && dados?.eta_segundos !== undefined && (
        <View style={styles.etaBox}>
          <Text style={styles.etaIcon}>
            {TIPO_ICON[dados.tipo_recurso || ''] || '🚨'}
          </Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.etaAgente}>{dados.agente_nome}</Text>
            <Text style={styles.etaLabel}>Chegada estimada</Text>
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
        <LeafletMap
          lat={lat}
          lon={lon}
          tipoRecurso={dados?.tipo_recurso || null}
          iframeRef={iframeRef}
        />
      </View>

      <View style={styles.infoBox}>
        <Text style={styles.infoText}>
          {status === 'aberta'         && 'Aguardando despacho de viatura...'}
          {status === 'despachada'     && 'Viatura despachada! Acompanhe no mapa.'}
          {status === 'em_atendimento' && 'Viatura a caminho da sua localização!'}
          {status === 'no_local'       && 'Agente chegou ao local!'}
          {status === 'concluida'      && 'Atendimento concluído.'}
        </Text>
      </View>

      <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
        <Text style={styles.backBtnText}>Voltar</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 20, paddingTop: 50, paddingBottom: 40 },
  title: { color: colors.text, fontSize: 24, fontWeight: 'bold' },
  protocolo: { color: colors.textSecondary, fontSize: 16, marginTop: 4 },
  badge: {
    alignSelf: 'flex-start', paddingHorizontal: 16, paddingVertical: 8,
    borderRadius: 20, marginTop: 16,
  },
  badgeText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
  etaBox: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: colors.surface, borderRadius: 14, padding: 16,
    marginTop: 16, borderWidth: 1, borderColor: '#3b82f6',
  },
  etaIcon: { fontSize: 36 },
  etaAgente: { color: colors.textSecondary, fontSize: 12 },
  etaLabel: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
  etaValor: { color: '#a78bfa', fontSize: 22, fontWeight: 'bold' },
  etaDist: { color: colors.textSecondary, fontSize: 13 },
  mapContainer: { marginTop: 16, borderRadius: 12, overflow: 'hidden', height: 300 },
  mapFallback: {
    height: 300, backgroundColor: colors.surface, borderRadius: 12,
    justifyContent: 'center', alignItems: 'center',
  },
  infoBox: {
    backgroundColor: colors.surface, padding: 16, borderRadius: 12,
    marginTop: 16, borderWidth: 1, borderColor: colors.border,
  },
  infoText: { color: colors.text, fontSize: 16, textAlign: 'center' },
  backBtn: {
    backgroundColor: colors.primary, padding: 16, borderRadius: 12,
    marginTop: 16, alignItems: 'center',
  },
  backBtnText: { color: colors.text, fontSize: 16, fontWeight: 'bold' },
});
