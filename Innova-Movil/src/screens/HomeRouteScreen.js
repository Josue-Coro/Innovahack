import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  Modal,
  RefreshControl,
  Alert,
} from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import { Ionicons } from '@expo/vector-icons';
import api from '../services/apiClient';
import { useAuthStore, getReponedorId } from '../services/authStore';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';
import { registrarPosicionGpsSafe } from '../services/gpsService';

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function StatusPill({ estado }) {
  const color = useMemo(() => {
    const s = String(estado ?? '').toLowerCase();
    if (s.includes('pend')) return '#F59E0B';
    if (s.includes('progreso') || s.includes('ejec')) return '#2563EB';
    if (s.includes('complet')) return '#10B981';
    return '#6B7280';
  }, [estado]);

  return (
    <View style={[styles.pill, { backgroundColor: `${color}22`, borderColor: `${color}55` }]}>
      <Text style={[styles.pillText, { color }]}>{String(estado ?? '—')}</Text>
    </View>
  );
}

function pickReponedorRoute(rutas, idReponedor) {
  const mine = (rutas ?? []).filter((r) => r.id_reponedor === idReponedor);
  if (!mine.length) return null;
  const hoy = todayIso();
  return mine.find((r) => r.fecha === hoy) ?? mine[0];
}

export default function HomeRouteScreen({ navigation }) {
  const usuario = useAuthStore((s) => s.usuario);
  const idReponedor = getReponedorId(usuario);

  // GPS solo se activa cuando el usuario lo decide desde los botones.

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [ruta, setRuta] = useState(null);
  const [visitasByPdv, setVisitasByPdv] = useState({});
  const [error, setError] = useState(null);
  const [sendingGpsOnce, setSendingGpsOnce] = useState(false);
  const [sendingGpsAuto, setSendingGpsAuto] = useState(false);
  const [gpsOk, setGpsOk] = useState(null);
  const [gpsIntervalActive, setGpsIntervalActive] = useState(false);
  const [gpsIntervalId, setGpsIntervalId] = useState(null);
  const [puntosExtra, setPuntosExtra] = useState([]);
  const [viewMode, setViewMode] = useState('list');


  const loadRoute = useCallback(async () => {
    if (!idReponedor) {
      setError('No se encontró el ID del reponedor');
      setLoading(false);
      return;
    }

    setError(null);
    try {
      const rutasRes = await api.get(endpoints.rutas);
      const rutaResumen = pickReponedorRoute(rutasRes?.data ?? [], idReponedor);

      if (!rutaResumen?.id_ruta) {
        setRuta(null);
        setVisitasByPdv({});
        setError('No tienes ruta asignada para hoy');
        return;
      }

      const [detalleRes, visitasRes] = await Promise.all([
        api.get(endpoints.rutaById(rutaResumen.id_ruta)),
        api.get(endpoints.visitasByRuta(rutaResumen.id_ruta)),
      ]);

      const detalle = detalleRes?.data ?? null;
      console.log('=== RUTA CARGADA ===');
      console.log('ID Ruta:', detalle?.id_ruta);
      console.log('Tiene Polyline?:', !!detalle?.polyline_json);
      setRuta(detalle);

      const map = {};
      for (const v of visitasRes?.data ?? []) {
        if (v.id_pdv != null) map[v.id_pdv] = v;
      }
      setVisitasByPdv(map);
    } catch (e) {
      setError(getApiError(e, 'Error al cargar la ruta'));
    }
  }, [idReponedor]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      await loadRoute();
      if (mounted) setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, [loadRoute]);

  async function onRefresh() {
    setRefreshing(true);
    await loadRoute();
    setRefreshing(false);
  }

  async function optimizeRoute() {
    if (!ruta?.id_ruta || optimizing) return;
    setOptimizing(true);
    setError(null);
    try {
      const res = await api.post(endpoints.optimizarRuta(ruta.id_ruta));
      const payload = res?.data;
      if (payload?.ruta_puntos) {
        setRuta((prev) => ({ ...(prev ?? {}), ...payload }));
      } else {
        await loadRoute();
      }
    } catch (e) {
      setError(getApiError(e, 'Error al optimizar'));
    } finally {
      setOptimizing(false);
    }
  }

  async function generarRutasDia() {
    setLoading(true);
    setError(null);
    try {
      console.log('--- Iniciando generación de rutas en servidor ---');
      const res = await api.post(endpoints.generarRutaDia);
      console.log('Rutas generadas. Respuesta backend:', res?.data);
      Alert.alert('Éxito', 'Rutas generadas. Refrescando mapa...');
      await loadRoute();
    } catch (e) {
      console.log('Error al generar rutas:', e);
      setError(getApiError(e, 'Error al generar rutas del día'));
    } finally {
      setLoading(false);
    }
  }

  async function fetchMisPdvs() {
    if (!idReponedor) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`${endpoints.pdvs}?id_reponedor_asignado=${idReponedor}`);
      const pdvs = res?.data ?? [];
      if (!pdvs.length) {
        setError('No tienes puntos de venta asignados.');
      } else {
        // Mappear PDVs a formato de ruta_puntos para que se rendericen en la lista
        const fakePoints = pdvs.map((p, index) => ({
          id_ruta_punto: `temp-${p.id_pdv}`,
          orden: index + 1,
          estado: 'pendiente',
          pdv: p,
          id_pdv: p.id_pdv
        }));
        setPuntosExtra(fakePoints);
      }
    } catch (e) {
      setError(getApiError(e, 'Error al cargar PDVs asignados'));
    } finally {
      setLoading(false);
    }
  }

  // Envia la ubicacion una unica vez (boton verde)
  async function enviarUnaVez() {
    if (!idReponedor) return;
    setSendingGpsOnce(true);
    setError(null);
    const result = await registrarPosicionGpsSafe(idReponedor);
    setSendingGpsOnce(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    setGpsOk(result.body);
  }

  // Envia en segundo plano (para el intervalo automatico - NO toca sendingGpsOnce)
  async function enviarAutoBackground() {
    if (!idReponedor) return;
    setSendingGpsAuto(true);
    const result = await registrarPosicionGpsSafe(idReponedor);
    setSendingGpsAuto(false);
    if (result.ok) setGpsOk(result.body);
  }

  async function toggleGps() {
    if (!idReponedor) return;

    if (gpsIntervalActive) {
      if (gpsIntervalId) clearInterval(gpsIntervalId);
      setGpsIntervalId(null);
      setGpsIntervalActive(false);
      return;
    }

    setGpsIntervalActive(true);
    enviarAutoBackground(); // usa su propio estado, no interfiere con el boton verde
    const id = setInterval(() => {
      enviarAutoBackground();
    }, 60000);
    setGpsIntervalId(id);
    
    Alert.alert(
      'Monitoreo Activado',
      'Tu posición se enviará automáticamente cada minuto.'
    );
  }

  const points = ruta?.ruta_puntos ?? [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Hola, {usuario?.nombre ?? 'Reponedor'}</Text>
        <Text style={styles.headerSub}>
          {ruta
            ? `Ruta #${ruta.id_ruta} · ${ruta.fecha ?? todayIso()} · ${ruta.estado ?? '—'}`
            : 'Sin ruta activa'}
        </Text>
      </View>

      <Pressable
        style={[styles.gpsButton, gpsIntervalActive ? {backgroundColor: '#DC2626'} : {}]}
        onPress={toggleGps}
        disabled={!idReponedor}
      >
        <View style={styles.gpsButtonInner}>
          {sendingGpsAuto ? <ActivityIndicator size="small" color="#fff" /> : <Ionicons name={gpsIntervalActive ? "stop-circle" : "navigate"} size={20} color="#fff" />}
          <Text style={styles.gpsButtonText}>
            {gpsIntervalActive ? 'Detener monitoreo automático' : 'Activar envío automático GPS'}
          </Text>
        </View>
      </Pressable>

      <Pressable
        style={[styles.gpsButton, {backgroundColor: '#059669'}]}
        onPress={async () => {
          await enviarUnaVez();
          if (!sendingGpsOnce) {
            Alert.alert('Enviado', 'Tu ubicación actual ha sido enviada al servidor.');
          }
        }}
        disabled={!idReponedor || sendingGpsOnce}
      >
        <View style={styles.gpsButtonInner}>
          {sendingGpsOnce ? <ActivityIndicator size="small" color="#fff" /> : <Ionicons name="location" size={20} color="#fff" />}
          <Text style={styles.gpsButtonText}>Mandar ubicación (una vez)</Text>
        </View>
      </Pressable>

      {!ruta?.id_ruta && (
        <View style={{ flexDirection: 'row', gap: 10, marginBottom: 12 }}>
          <Pressable style={[styles.verRutasButton, { flex: 1, marginBottom: 0 }]} onPress={fetchMisPdvs} disabled={loading}>
            <Text style={styles.verRutasButtonText}>Ver rutas (Mis PDVs)</Text>
          </Pressable>
          
          <Pressable
            style={[styles.optimizeButton, { flex: 1, marginBottom: 0, backgroundColor: '#8B5CF6' }]}
            onPress={generarRutasDia}
            disabled={loading}
          >
            <Text style={styles.optimizeButtonText}>
              {loading ? 'Cargando...' : 'Autogenerar ORS'}
            </Text>
          </Pressable>
        </View>
      )}

      {gpsOk ? (
        <Text style={styles.gpsSuccess}>
          Último envío: {gpsOk.latitud.toFixed(5)}, {gpsOk.longitud.toFixed(5)} · {gpsOk.precision_m} m
        </Text>
      ) : null}

      {ruta?.id_ruta ? (
        <View style={{ flexDirection: 'row', gap: 10, marginBottom: 12 }}>
          <Pressable
            style={[styles.optimizeButton, { flex: 1, marginBottom: 0, backgroundColor: '#8B5CF6' }]}
            onPress={generarRutasDia}
            disabled={optimizing}
          >
            <Text style={styles.optimizeButtonText}>
              {optimizing ? 'Generando...' : 'Autogenerar ORS'}
            </Text>
          </Pressable>

          <Pressable
            style={[styles.optimizeButton, { flex: 1, marginBottom: 0 }]}
            onPress={optimizeRoute}
            disabled={optimizing}
          >
            <Text style={styles.optimizeButtonText}>
              {optimizing ? 'Optimizando...' : 'Optimizar Orden'}
            </Text>
          </Pressable>
        </View>
      ) : null}

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" />
          <Text style={styles.loadingText}>Cargando paradas...</Text>
        </View>
      ) : (
        <>
          <View style={styles.viewModeToggleRow}>
            <Pressable 
              style={[styles.toggleBtn, viewMode === 'list' && styles.toggleBtnActive]}
              onPress={() => setViewMode('list')}
            >
              <Ionicons name="list" size={18} color={viewMode === 'list' ? '#fff' : '#6B7280'} />
              <Text style={[styles.toggleBtnText, viewMode === 'list' && styles.toggleBtnTextActive]}>Lista</Text>
            </Pressable>
            <Pressable 
              style={[styles.toggleBtn, viewMode === 'map' && styles.toggleBtnActive]}
              onPress={() => setViewMode('map')}
            >
              <Ionicons name="map" size={18} color={viewMode === 'map' ? '#fff' : '#6B7280'} />
              <Text style={[styles.toggleBtnText, viewMode === 'map' && styles.toggleBtnTextActive]}>Mapa</Text>
            </Pressable>
          </View>

          {viewMode === 'map' ? (
            <View style={styles.mapContainer}>
              <MapView
                style={styles.map}
                showsUserLocation={true}
                showsMyLocationButton={true}
                initialRegion={{
                  latitude: (ruta?.id_ruta ? points : puntosExtra)[0]?.pdv?.latitud ?? -16.5,
                  longitude: (ruta?.id_ruta ? points : puntosExtra)[0]?.pdv?.longitud ?? -68.15,
                  latitudeDelta: 0.05,
                  longitudeDelta: 0.05,
                }}
              >
                {(ruta?.id_ruta ? points : puntosExtra).map((item, index) => {
                  const pdv = item?.pdv;
                  if (!pdv?.latitud || !pdv?.longitud) return null;
                  return (
                    <Marker
                      key={item?.id_ruta_punto ?? item?.id_pdv ?? index}
                      coordinate={{ latitude: pdv.latitud, longitude: pdv.longitud }}
                      title={pdv.nombre_pdv}
                      description={pdv.direccion}
                    />
                  );
                })}
                {(() => {
                  let polyObj = null;
                  try {
                    if (typeof ruta?.polyline_json === 'string') {
                      polyObj = JSON.parse(ruta.polyline_json);
                    } else {
                      polyObj = ruta?.polyline_json;
                    }
                  } catch (e) {
                    console.log('Error parsing polyline', e);
                  }

                  if (polyObj && polyObj.coordinates && Array.isArray(polyObj.coordinates)) {
                    return (
                      <Polyline
                        coordinates={polyObj.coordinates.map(coord => ({
                          latitude: coord[1],
                          longitude: coord[0]
                        }))}
                        strokeColor="#2563EB"
                        strokeWidth={5}
                      />
                    );
                  }
                  return null;
                })()}
              </MapView>
            </View>
          ) : (
            <FlatList
              data={ruta?.id_ruta ? points : puntosExtra}
          keyExtractor={(item, idx) =>
            String(item?.id_ruta_punto ?? item?.id_pdv ?? idx)
          }
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          contentContainerStyle={(ruta?.id_ruta ? points.length : puntosExtra.length) ? { paddingBottom: 24 } : styles.emptyList}
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              {ruta ? 'La ruta no tiene paradas asignadas.' : 'Pide a tu supervisor que te asigne una ruta o presiona "Ver rutas".'}
            </Text>
          }
          renderItem={({ item, index }) => {
            const pdv = item?.pdv ?? {};
            const nombre = pdv.nombre_pdv ?? 'PDV';
            const direccion = pdv.direccion ?? '—';
            const codigo = pdv.codigo_gv ?? '';
            const estado = item?.estado ?? visitasByPdv[item?.id_pdv]?.estado;
            const visita = visitasByPdv[item?.id_pdv];
            const visitaId = visita?.id_visita;

            return (
              <Pressable
                style={styles.card}
                onPress={() => {
                  if (!visitaId) {
                    setError('No hay visita registrada para esta parada. Contacta a tu supervisor.');
                    return;
                  }
                  navigation.navigate('VisitExecution', {
                    visitaId,
                    pdv,
                    orden: item?.orden ?? index + 1,
                    estadoVisita: estado,
                  });
                }}
              >
                <View style={styles.cardTop}>
                  <Text style={styles.cardOrder}>{item?.orden ?? index + 1}</Text>
                  <Text style={styles.cardTitle} numberOfLines={1}>
                    {codigo ? `${codigo} · ` : ''}
                    {nombre}
                  </Text>
                  <StatusPill estado={estado} />
                </View>
                <Text style={styles.cardAddress}>{direccion}</Text>
                {item?.hora_estimada_llegada && (
                  <Text style={{ fontSize: 13, color: '#4B5563', marginTop: 4, fontWeight: 'bold' }}>
                    <Ionicons name="time-outline" size={14} color="#4B5563" /> Llegada estimada: {String(item.hora_estimada_llegada).slice(0, 5)}
                  </Text>
                )}
              </Pressable>
            );
          }}
        />
        )}
        </>
      )}

      <Modal transparent visible={optimizing} animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <ActivityIndicator size="large" />
            <Text style={styles.modalText}>Optimizando ruta...</Text>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 16 },
  header: { gap: 4, marginBottom: 12 },
  headerTitle: { fontSize: 20, fontWeight: '800' },
  headerSub: { color: '#6B7280', fontSize: 13 },
  gpsButton: {
    height: 48,
    borderRadius: 14,
    backgroundColor: '#2563EB',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  gpsButtonDisabled: { opacity: 0.7 },
  gpsButtonInner: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  gpsButtonText: { color: '#fff', fontWeight: '800', fontSize: 15 },
  gpsSuccess: {
    fontSize: 12,
    color: '#059669',
    fontWeight: '600',
    marginBottom: 10,
  },
  optimizeButton: {
    height: 48,
    borderRadius: 14,
    backgroundColor: '#111827',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  optimizeButtonText: { color: '#fff', fontWeight: '800', fontSize: 15 },
  verRutasButton: {
    height: 48,
    borderRadius: 14,
    backgroundColor: '#10B981',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  verRutasButtonText: { color: '#fff', fontWeight: '800', fontSize: 15 },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10 },
  loadingText: { color: '#6B7280' },
  emptyList: { flexGrow: 1, justifyContent: 'center', paddingVertical: 40 },
  emptyText: { textAlign: 'center', color: '#6B7280', fontSize: 14 },
  card: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
    backgroundColor: '#FAFAFA',
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  cardOrder: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#EEF2FF',
    color: '#3730A3',
    fontWeight: '800',
    textAlign: 'center',
    lineHeight: 28,
    fontSize: 13,
  },
  cardTitle: { fontSize: 15, fontWeight: '800', flex: 1 },
  cardAddress: { marginTop: 8, color: '#374151' },
  pill: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, borderWidth: 1 },
  pillText: { fontWeight: '800', fontSize: 11 },
  errorText: { color: '#DC2626', fontWeight: '700', marginBottom: 10 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.35)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCard: {
    width: '80%',
    maxWidth: 360,
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 18,
    alignItems: 'center',
    gap: 12,
  },
  modalText: { fontWeight: '800', color: '#111827' },
  viewModeToggleRow: {
    flexDirection: 'row',
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    padding: 4,
    marginBottom: 12,
  },
  toggleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 10,
    gap: 8,
  },
  toggleBtnActive: {
    backgroundColor: '#2563EB',
  },
  toggleBtnText: {
    fontWeight: '700',
    color: '#6B7280',
  },
  toggleBtnTextActive: {
    color: '#fff',
  },
  mapContainer: {
    flex: 1,
    borderRadius: 16,
    overflow: 'hidden',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  map: {
    width: '100%',
    height: '100%',
  },
});
