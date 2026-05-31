import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
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
  TextInput,
  Animated,
  LayoutAnimation,
  Platform,
  UIManager,
  Image,
} from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import * as Location from 'expo-location';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import api from '../services/apiClient';
import { useAuthStore, getReponedorId } from '../services/authStore';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';
import { registrarPosicionGpsSafe, LOCATION_TASK_NAME } from '../services/gpsService';

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function StatusPill({ estado }) {
  const color = useMemo(() => {
    const s = String(estado ?? '').toLowerCase();
    if (s.includes('pend')) return '#F59E0B';
    if (s.includes('progreso') || s.includes('ejec')) return '#3B82F6';
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

// Enable LayoutAnimation on Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

export default function HomeRouteScreen({ navigation }) {
  const usuario = useAuthStore((s) => s.usuario);
  const idReponedor = getReponedorId(usuario);
  const isDarkMode = useAuthStore((s) => s.isDarkMode);
  const toggleTheme = useAuthStore((s) => s.toggleTheme);
  const logout = useAuthStore((s) => s.logout);
  const insets = useSafeAreaInsets();

  const themeColors = {
    bg: isDarkMode ? '#0F1115' : '#F3F4F6',
    text: isDarkMode ? '#F9FAFB' : '#111827',
    cardBg: isDarkMode ? '#1F2937' : '#FFFFFF',
    textMuted: isDarkMode ? '#9CA3AF' : '#6B7280',
    menuBg: isDarkMode ? '#1F2937' : '#FFFFFF',
    inputBg: isDarkMode ? '#1F2937' : '#E5E7EB',
  };

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [ruta, setRuta] = useState(null);
  const [visitasByPdv, setVisitasByPdv] = useState({});
  const [error, setError] = useState(null);
  const [sendingGpsOnce, setSendingGpsOnce] = useState(false);
  const [gpsOk, setGpsOk] = useState(null);
  const [gpsIntervalActive, setGpsIntervalActive] = useState(false);
  const [puntosExtra, setPuntosExtra] = useState([]);
  const [viewMode, setViewMode] = useState('list');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [menuVisible, setMenuVisible] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(-10)).current;
  const [currentLocation, setCurrentLocation] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === 'granted') {
          const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          setCurrentLocation(loc.coords);
        }
      } catch (e) {
        console.log('Error pidiendo permisos de ubicacion', e);
      }
    })();
  }, []);

  const loadRoute = useCallback(async () => {
    if (!idReponedor) {
      setError('No se encontró el ID del reponedor');
      setLoading(false);
      return;
    }
    setError(null);
    try {
      const [rutasRes, pdvsRes] = await Promise.all([
        api.get(endpoints.rutas),
        api.get(`${endpoints.pdvs}?id_reponedor_asignado=${idReponedor}`)
      ]);

      const pdvs = pdvsRes?.data ?? [];
      const fakePoints = pdvs.map((p, index) => ({
        id_ruta_punto: `temp-${p.id_pdv}`,
        orden: index + 1,
        estado: 'pendiente',
        pdv: p,
        id_pdv: p.id_pdv
      }));
      setPuntosExtra(fakePoints);

      const rutaResumen = pickReponedorRoute(rutasRes?.data ?? [], idReponedor);

      if (!rutaResumen?.id_ruta) {
        setRuta(null);
        setVisitasByPdv({});
        if (!fakePoints.length) {
          setError('No tienes ruta ni puntos de venta asignados hoy.');
        }
        return;
      }

      const [detalleRes, visitasRes] = await Promise.all([
        api.get(endpoints.rutaById(rutaResumen.id_ruta)),
        api.get(endpoints.visitasByRuta(rutaResumen.id_ruta)),
      ]);

      const detalle = detalleRes?.data ?? null;
      setRuta(detalle);

      const map = {};
      for (const v of visitasRes?.data ?? []) {
        if (v.id_pdv != null) map[v.id_pdv] = v;
      }
      setVisitasByPdv(map);
    } catch (e) {
      setError(getApiError(e, 'Error al cargar la ruta o PDVs'));
    }
  }, [idReponedor]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      await loadRoute();
      if (mounted) setLoading(false);
    })();
    return () => { mounted = false; };
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
      await api.post(endpoints.generarRutaDia);
      
      // Fetch the newly created route for this user to get its ID
      const resRuta = await api.get(endpoints.rutaActiva(idReponedor));
      const newRouteId = resRuta?.data?.id_ruta;
      
      if (newRouteId) {
        // Optimize it silently
        await api.post(endpoints.optimizarRuta(newRouteId));
      }
      
      await loadRoute();
    } catch (e) {
      setError(getApiError(e, 'Error al generar o optimizar rutas del día'));
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
    Alert.alert('Enviado', 'Tu ubicación actual ha sido enviada al servidor.');
  }

  async function toggleGps() {
    if (!idReponedor) return;
    if (gpsIntervalActive) {
      try {
        await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);
      } catch (e) {}
      setGpsIntervalActive(false);
      return;
    }
    
    // Solicitamos permiso estricto para segundo plano
    const { status } = await Location.requestBackgroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permiso Denegado', 'Para usar el monitoreo en segundo plano, debes ir a Ajustes y seleccionar "Permitir todo el tiempo".');
      return;
    }

    try {
      await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
        accuracy: Location.Accuracy.High,
        timeInterval: 60000,
        distanceInterval: 10,
        showsBackgroundLocationIndicator: true,
        foregroundService: {
          notificationTitle: 'CampoRuta',
          notificationBody: 'Enviando ubicación a la base central',
          notificationColor: '#3B82F6',
        }
      });
      setGpsIntervalActive(true);
      Alert.alert('Monitoreo Activado', 'Tu posición se enviará automáticamente incluso con el teléfono bloqueado.');
    } catch (e) {
      Alert.alert('Error', 'No se pudo iniciar el servicio en segundo plano.');
    }
  }

  function toggleMenu() {
    if (menuVisible) {
      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 0, duration: 150, useNativeDriver: true }),
        Animated.timing(slideAnim, { toValue: -10, duration: 150, useNativeDriver: true }),
      ]).start(() => setMenuVisible(false));
    } else {
      setMenuVisible(true);
      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 1, duration: 200, useNativeDriver: true }),
        Animated.timing(slideAnim, { toValue: 0, duration: 200, useNativeDriver: true }),
      ]).start();
    }
  }

  function handleLogout() {
    toggleMenu();
    Alert.alert(
      'Cerrar Sesión',
      '¿Estás seguro de que deseas cerrar tu sesión actual?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Salir', style: 'destructive', onPress: logout }
      ]
    );
  }

  function handleFeature(name) {
    toggleMenu();
    if (name === 'Tema') {
      LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
      toggleTheme();
    } else if (name === 'Mi perfil') {
      navigation.navigate('Profile');
    } else if (name === 'Ajustes') {
      navigation.navigate('Settings');
    }
  }

  const rawPoints = ruta?.ruta_puntos ?? [];
  const points = rawPoints.filter(p => {
    if (!searchQuery) return true;
    const lowerQ = searchQuery.toLowerCase();
    const codigo = p.pdv?.codigo_pdv?.toLowerCase() || '';
    const nombre = p.pdv?.nombre_pdv?.toLowerCase() || '';
    return codigo.includes(lowerQ) || nombre.includes(lowerQ);
  });

  const rawExtra = puntosExtra ?? [];
  const filteredExtra = rawExtra.filter(p => {
    if (!searchQuery) return true;
    const lowerQ = searchQuery.toLowerCase();
    const codigo = p.pdv?.codigo_pdv?.toLowerCase() || '';
    const nombre = p.pdv?.nombre_pdv?.toLowerCase() || '';
    return codigo.includes(lowerQ) || nombre.includes(lowerQ);
  });

  function getDistance(lat1, lon1, lat2, lon2) {
    if (!lat1 || !lon1 || !lat2 || !lon2) return 999999;
    const R = 6371e3;
    const rad = Math.PI / 180;
    const dLat = (lat2 - lat1) * rad;
    const dLon = (lon2 - lon1) * rad;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  let allPoints = [...points, ...filteredExtra];

  if (currentLocation) {
    allPoints.forEach(p => {
      p.distancia = getDistance(currentLocation.latitude, currentLocation.longitude, p.pdv?.latitud, p.pdv?.longitud);
    });
    // Ordenar: primero los que no están completados y están a <= 100m, luego el resto
    allPoints.sort((a, b) => {
      const aEstado = a.estado ?? visitasByPdv[a.id_pdv]?.estado ?? 'pendiente';
      const bEstado = b.estado ?? visitasByPdv[b.id_pdv]?.estado ?? 'pendiente';
      
      const aCerca = aEstado !== 'completada' && a.distancia <= 100;
      const bCerca = bEstado !== 'completada' && b.distancia <= 100;
      
      if (aCerca && !bCerca) return -1;
      if (!aCerca && bCerca) return 1;
      return (a.distancia || 999999) - (b.distancia || 999999);
    });
  }

  const initials = usuario?.nombre ? usuario.nombre.substring(0, 2).toUpperCase() : 'AV';

  return (
    <View style={[styles.container, { paddingTop: insets.top, backgroundColor: themeColors.bg }]}>
      
      {/* TopBar */}
      <View style={[styles.topBar, { backgroundColor: themeColors.bg, justifyContent: 'space-between' }]}>
        <View style={[styles.logoContainer, { backgroundColor: 'transparent' }]}>
          <Image source={require('../../assets/logo.png')} style={{ width: 60, height: 40, resizeMode: 'contain' }} />
        </View>

        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Pressable style={styles.bellButton}>
            <Ionicons name="notifications-outline" size={24} color={themeColors.text} />
            <View style={styles.bellBadge} />
          </Pressable>

          <Pressable style={styles.avatarBtn} onPress={toggleMenu}>
            <Text style={styles.avatarText}>{initials}</Text>
          </Pressable>
        </View>
      </View>

      {/* Menu Overlay */}
      {menuVisible && (
        <Pressable style={styles.menuOverlay} onPress={toggleMenu}>
          <Animated.View style={[styles.dropdownMenu, { top: insets.top + 60, opacity: fadeAnim, transform: [{ translateY: slideAnim }], backgroundColor: themeColors.menuBg }]}>
            <Pressable style={styles.menuItem} onPress={() => handleFeature('Mi perfil')}>
              <Ionicons name="person-outline" size={18} color={themeColors.textMuted} style={styles.menuIcon} />
              <Text style={[styles.menuItemText, { color: themeColors.text }]}>Mi perfil</Text>
            </Pressable>
            <Pressable style={styles.menuItem} onPress={() => handleFeature('Ajustes')}>
              <Ionicons name="settings-outline" size={18} color={themeColors.textMuted} style={styles.menuIcon} />
              <Text style={[styles.menuItemText, { color: themeColors.text }]}>Ajustes</Text>
            </Pressable>
            <Pressable style={styles.menuItem} onPress={() => handleFeature('Tema')}>
              <Ionicons name={isDarkMode ? "sunny-outline" : "moon-outline"} size={18} color={themeColors.textMuted} style={styles.menuIcon} />
              <Text style={[styles.menuItemText, { color: themeColors.text }]}>{isDarkMode ? "Tema Claro" : "Tema Oscuro"}</Text>
            </Pressable>
            <View style={[styles.menuDivider, { backgroundColor: isDarkMode ? '#374151' : '#E5E7EB' }]} />
            <Pressable style={styles.menuItem} onPress={handleLogout}>
              <Ionicons name="log-out-outline" size={18} color="#EF4444" style={styles.menuIcon} />
              <Text style={[styles.menuItemText, { color: '#EF4444' }]}>Cerrar Sesión</Text>
            </Pressable>
          </Animated.View>
        </Pressable>
      )}

      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={[styles.headerTitle, { color: themeColors.text }]}>Hola, {usuario?.nombre ?? 'Reponedor'}</Text>
          <Text style={[styles.headerSub, { color: themeColors.textMuted }]}>
            {ruta
              ? `Ruta #${ruta.id_ruta} · Progreso: ${allPoints.filter(p => p.estado === 'completada').length}/${allPoints.length}`
              : 'Sin ruta activa'}
          </Text>
        </View>

        <View style={styles.actionsRow}>
          <Pressable
            style={[styles.actionBtn, gpsIntervalActive ? styles.actionBtnActive : null]}
            onPress={toggleGps}
          >
            <Ionicons name={gpsIntervalActive ? "stop-circle" : "navigate"} size={18} color={gpsIntervalActive ? "#EF4444" : themeColors.textMuted} />
            <Text style={[styles.actionBtnText, gpsIntervalActive ? { color: '#EF4444' } : { color: themeColors.textMuted }]}>
              {gpsIntervalActive ? 'Detener GPS' : 'Iniciar GPS'}
            </Text>
          </Pressable>
          
          <Pressable style={styles.actionBtn} onPress={generarRutasDia} disabled={loading}>
            {loading ? <ActivityIndicator size="small" color="#10B981" /> : <Ionicons name="refresh-circle" size={18} color="#10B981" />}
            <Text style={[styles.actionBtnText, { color: themeColors.textMuted }]}>Generar Ruta</Text>
          </Pressable>

          <Pressable style={styles.actionBtn} onPress={fetchMisPdvs} disabled={loading}>
             <Ionicons name="list" size={18} color="#3B82F6" />
             <Text style={[styles.actionBtnText, { color: themeColors.textMuted }]}>Mis PDVs</Text>
          </Pressable>
        </View>

        {gpsOk ? (
          <Text style={[styles.gpsSuccess, { color: themeColors.textMuted }]}>
            Último envío: {gpsOk.latitud.toFixed(5)}, {gpsOk.longitud.toFixed(5)} · {gpsOk.precision_m} m
          </Text>
        ) : null}
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        {loading ? (
          <View style={styles.loadingWrap}>
            <ActivityIndicator size="large" color="#3B82F6" />
            <Text style={[styles.loadingText, { color: themeColors.textMuted }]}>Cargando paradas...</Text>
          </View>
        ) : (
          <View style={styles.mainArea}>
            <View style={[styles.mainSearchContainer, { backgroundColor: themeColors.inputBg }]}>
              <Ionicons name="search" size={18} color={themeColors.textMuted} />
              <TextInput
                style={[styles.mainSearchInput, { color: themeColors.text }]}
                placeholder="Buscar mercado, código..."
                placeholderTextColor={themeColors.textMuted}
                value={searchQuery}
                onChangeText={setSearchQuery}
              />
              {searchQuery.length > 0 && (
                <Pressable onPress={() => setSearchQuery('')}>
                  <Ionicons name="close-circle" size={18} color={themeColors.textMuted} />
                </Pressable>
              )}
            </View>

            <View style={[styles.viewModeToggleRow, { backgroundColor: themeColors.inputBg }]}>
              <Pressable 
                style={[styles.toggleBtn, viewMode === 'list' && [styles.toggleBtnActive, { backgroundColor: isDarkMode ? '#374151' : '#FFFFFF' }]]}
                onPress={() => setViewMode('list')}
              >
                <Ionicons name="list" size={16} color={viewMode === 'list' ? (isDarkMode ? '#fff' : '#000') : themeColors.textMuted} />
                <Text style={[styles.toggleBtnText, { color: themeColors.textMuted }, viewMode === 'list' && [styles.toggleBtnTextActive, { color: isDarkMode ? '#fff' : '#000' }]]}>Lista</Text>
              </Pressable>
              <Pressable 
                style={[styles.toggleBtn, viewMode === 'map' && [styles.toggleBtnActive, { backgroundColor: isDarkMode ? '#374151' : '#FFFFFF' }]]}
                onPress={() => setViewMode('map')}
              >
                <Ionicons name="map" size={16} color={viewMode === 'map' ? (isDarkMode ? '#fff' : '#000') : themeColors.textMuted} />
                <Text style={[styles.toggleBtnText, { color: themeColors.textMuted }, viewMode === 'map' && [styles.toggleBtnTextActive, { color: isDarkMode ? '#fff' : '#000' }]]}>Mapa</Text>
              </Pressable>
            </View>

            {viewMode === 'map' ? (
              <View style={[styles.mapContainer, { borderColor: isDarkMode ? '#374151' : '#E5E7EB' }]}>
                <MapView
                  style={styles.map}
                  showsUserLocation={true}
                  showsMyLocationButton={true}
                  initialRegion={{
                    latitude: allPoints[0]?.pdv?.latitud ?? -16.5,
                    longitude: allPoints[0]?.pdv?.longitud ?? -68.15,
                    latitudeDelta: 0.05,
                    longitudeDelta: 0.05,
                  }}
                >
                  {allPoints.map((item, index) => {
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
                          strokeColor="#3B82F6"
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
                data={allPoints}
                keyExtractor={(item, idx) => String(item?.id_ruta_punto ?? item?.id_pdv ?? idx)}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={themeColors.text} />}
                contentContainerStyle={allPoints.length ? { paddingBottom: 24 } : styles.emptyList}
                ListEmptyComponent={
                  <Text style={[styles.emptyText, { color: themeColors.textMuted }]}>
                    {ruta ? 'La ruta no tiene paradas asignadas.' : 'Pide a tu supervisor que te asigne una ruta o presiona "Mis PDVs".'}
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
                      style={({ pressed }) => [styles.card, { backgroundColor: themeColors.cardBg, borderColor: isDarkMode ? '#374151' : '#E5E7EB' }, pressed && styles.cardPressed]}
                      onPress={() => {
                        navigation.navigate('VisitExecution', {
                          visitaId,
                          idReponedor,
                          pdv,
                          orden: item?.orden ?? index + 1,
                          estadoVisita: estado,
                        });
                      }}
                    >
                      <View style={styles.cardTop}>
                        <Text style={[styles.cardOrder, { backgroundColor: isDarkMode ? '#374151' : '#E5E7EB', color: themeColors.text }]}>{item?.orden ?? index + 1}</Text>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.cardTitle, { color: themeColors.text }]} numberOfLines={1}>
                            {codigo ? `${codigo} · ` : ''}{nombre}
                          </Text>
                          {item.distancia != null && estado !== 'completada' && item.distancia <= 100 && (
                            <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}>
                              <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#10B981', marginRight: 6 }} />
                              <Text style={{ color: '#10B981', fontSize: 12, fontWeight: '700' }}>Cerca ({Math.round(item.distancia)}m) - Puedes Iniciar</Text>
                            </View>
                          )}
                        </View>
                        <StatusPill estado={estado} />
                        <Ionicons name="chevron-forward" size={18} color={themeColors.textMuted} />
                      </View>
                      <Text style={[styles.cardAddress, { color: themeColors.textMuted }]}>{direccion}</Text>
                      {item?.hora_estimada_llegada && (
                        <Text style={[styles.cardTime, { color: themeColors.textMuted }]}>
                          <Ionicons name="time-outline" size={12} color={themeColors.textMuted} /> LLegada estimada: {String(item.hora_estimada_llegada).slice(0, 5)}
                        </Text>
                      )}
                    </Pressable>
                  );
                }}
              />
            )}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F1115' },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1F2937',
    zIndex: 10,
  },
  logoContainer: {
    width: 36,
    height: 36,
    backgroundColor: '#fff',
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  logoText: {
    color: '#0F1115',
    fontWeight: '900',
    fontSize: 20,
    fontStyle: 'italic',
  },
  searchContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1F2937',
    borderRadius: 999,
    paddingHorizontal: 12,
    height: 38,
    marginRight: 16,
  },
  searchInput: {
    flex: 1,
    color: '#fff',
    fontSize: 14,
    marginLeft: 8,
  },
  bellButton: {
    padding: 6,
    marginRight: 12,
  },
  bellBadge: {
    position: 'absolute',
    top: 6,
    right: 8,
    width: 8,
    height: 8,
    backgroundColor: '#EF4444',
    borderRadius: 4,
  },
  avatarBtn: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: '#3B82F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 14,
  },
  mainSearchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    height: 48,
    borderRadius: 12,
    marginBottom: 12,
  },
  mainSearchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 16,
  },
  menuOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 20,
  },
  dropdownMenu: {
    position: 'absolute',
    top: 60,
    right: 16,
    backgroundColor: '#1F2937',
    borderRadius: 16,
    paddingVertical: 8,
    minWidth: 180,
    shadowColor: '#000',
    shadowOpacity: 0.5,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 5,
    borderWidth: 1,
    borderColor: '#374151',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  menuIcon: {
    marginRight: 12,
  },
  menuItemText: {
    color: '#F9FAFB',
    fontSize: 15,
    fontWeight: '500',
  },
  menuDivider: {
    height: 1,
    backgroundColor: '#374151',
    marginVertical: 4,
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  header: { marginBottom: 16 },
  headerTitle: { fontSize: 22, fontWeight: '900', color: '#fff' },
  headerSub: { color: '#9CA3AF', fontSize: 13, marginTop: 4 },
  actionsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
  },
  actionBtn: {
    flex: 1,
    backgroundColor: '#1F2937',
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: 6,
    borderWidth: 1,
    borderColor: '#374151',
  },
  actionBtnActive: {
    borderColor: '#EF4444',
    backgroundColor: '#450a0a',
  },
  actionBtnText: {
    color: '#D1D5DB',
    fontWeight: '700',
    fontSize: 13,
  },
  gpsSuccess: { color: '#10B981', fontSize: 12, fontWeight: '600', marginBottom: 12 },
  errorText: { color: '#EF4444', fontWeight: '700', marginBottom: 12 },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10 },
  loadingText: { color: '#9CA3AF' },
  mainArea: { flex: 1 },
  viewModeToggleRow: {
    flexDirection: 'row',
    backgroundColor: '#1F2937',
    borderRadius: 10,
    padding: 4,
    marginBottom: 16,
  },
  toggleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  toggleBtnActive: { backgroundColor: '#374151' },
  toggleBtnText: { fontWeight: '700', color: '#9CA3AF', fontSize: 13 },
  toggleBtnTextActive: { color: '#fff' },
  mapContainer: { flex: 1, borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#374151', marginBottom: 16 },
  map: { width: '100%', height: '100%' },
  emptyList: { flexGrow: 1, justifyContent: 'center', paddingVertical: 40 },
  emptyText: { textAlign: 'center', color: '#9CA3AF', fontSize: 14 },
  card: {
    backgroundColor: '#1F2937',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#374151',
  },
  cardPressed: { opacity: 0.8, transform: [{ scale: 0.98 }] },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardOrder: {
    width: 28, height: 28, borderRadius: 14,
    backgroundColor: '#374151', color: '#D1D5DB',
    fontWeight: '800', textAlign: 'center', lineHeight: 28, fontSize: 13,
  },
  cardTitle: { fontSize: 15, fontWeight: '800', color: '#F3F4F6', flex: 1 },
  cardAddress: { marginTop: 8, color: '#9CA3AF', fontSize: 13 },
  cardTime: { fontSize: 12, color: '#6B7280', marginTop: 8, fontWeight: '600' },
  pill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, borderWidth: 1 },
  pillText: { fontWeight: '800', fontSize: 10 },
});
