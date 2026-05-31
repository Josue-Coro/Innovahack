import React, { useMemo, useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, Alert, FlatList, Image } from 'react-native';
import * as Location from 'expo-location';
import api from '../services/apiClient';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';
import { Ionicons } from '@expo/vector-icons';

export default function VisitExecutionScreen({ route, navigation }) {
  const { visitaId: initialVisitaId, idReponedor, pdv, orden, estadoVisita: initialEstado } = route.params ?? {};
  
  const [visitaId, setVisitaId] = useState(initialVisitaId);
  const [submitting, setSubmitting] = useState(false);
  const [estadoVisita, setEstadoVisita] = useState(initialEstado ?? 'pendiente');
  
  // Catálogo de productos y carrito
  const [productos, setProductos] = useState([]);
  const [cart, setCart] = useState({});
  const [loadingProductos, setLoadingProductos] = useState(false);
  const [entregado, setEntregado] = useState(false); // Flag para obligar a enviar antes del checkout

  const codigo = useMemo(() => pdv?.codigo_gv ?? '—', [pdv]);
  const nombre = useMemo(() => pdv?.nombre_pdv ?? 'PDV', [pdv]);
  const direccion = useMemo(() => pdv?.direccion ?? '—', [pdv]);

  // Cargar productos si estamos en progreso
  useEffect(() => {
    if (estadoVisita === 'en_curso') {
      fetchProductos();
    }
  }, [estadoVisita]);

  async function fetchProductos() {
    setLoadingProductos(true);
    try {
      const res = await api.get(endpoints.productos);
      setProductos(res?.data ?? []);
    } catch (e) {
      console.log('Error cargando productos', e);
    } finally {
      setLoadingProductos(false);
    }
  }

  async function getLocation() {
    let { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Error', 'Se requieren permisos de ubicación para marcar la visita.');
      return null;
    }
    const loc = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.High,
    });
    return {
      latitud_actual: loc.coords.latitude,
      longitud_actual: loc.coords.longitude,
    };
  }

  async function checkIn() {
    if (submitting) return;
    setSubmitting(true);
    try {
      const payload = await getLocation();
      if (!payload) {
        setSubmitting(false);
        return;
      }
      
      if (!visitaId) {
        // Puntos extra: no tienen visita, creamos una Libre
        const librePayload = {
          id_reponedor: idReponedor,
          id_pdv: pdv.id_pdv,
          fecha: new Date().toISOString().split('T')[0],
          estado: 'en_curso',
          lat_registro: payload.latitud_actual,
          lon_registro: payload.longitud_actual,
        };
        const res = await api.post(endpoints.iniciarVisitaLibre, librePayload);
        setVisitaId(res.data.id_visita);
      } else {
        // Punto de ruta: iniciamos su visita
        await api.post(endpoints.iniciarVisita(visitaId), payload);
      }
      
      Alert.alert('Check-In Exitoso', 'La visita ha iniciado. Marca los productos entregados.');
      setEstadoVisita('en_curso');
    } catch (e) {
      Alert.alert('No puedes iniciar', getApiError(e, 'No se pudo iniciar la visita'));
    } finally {
      setSubmitting(false);
    }
  }

  function modifyCart(idProducto, amount) {
    setCart(prev => {
      const current = prev[idProducto] || 0;
      const next = Math.max(0, current + amount);
      return { ...prev, [idProducto]: next };
    });
  }

  async function confirmarEntrega() {
    if (!visitaId) return;
    const items = Object.entries(cart).filter(([_, cant]) => cant > 0);
    if (items.length === 0) {
      Alert.alert('Atención', 'No has seleccionado ningún producto para entregar.');
      return;
    }

    setSubmitting(true);
    try {
      // Mandar una entrega por cada producto
      for (const [id_prod, cantidad] of items) {
        await api.post(endpoints.entregas, {
          id_visita: visitaId,
          id_producto: parseInt(id_prod, 10),
          cantidad: cantidad
        });
      }
      setEntregado(true);
      Alert.alert('Éxito', 'Entrega guardada y stock descontado.');
    } catch (e) {
      Alert.alert('Error', getApiError(e, 'No se pudo guardar la entrega.'));
    } finally {
      setSubmitting(false);
    }
  }

  async function checkOut() {
    if (!visitaId || submitting) return;
    
    const items = Object.entries(cart).filter(([_, cant]) => cant > 0);
    if (items.length > 0 && !entregado) {
      Alert.alert('Falta Guardar', 'Has marcado productos para entregar pero no has presionado "Confirmar Entrega".');
      return;
    }

    setSubmitting(true);
    try {
      const payload = await getLocation();
      if (!payload) {
        setSubmitting(false);
        return;
      }

      await api.post(endpoints.finalizarVisita(visitaId), payload);
      Alert.alert('Check-Out Exitoso', 'Visita completada correctamente.');
      setEstadoVisita('completada');
      navigation.goBack();
    } catch (e) {
      Alert.alert('No puedes finalizar', getApiError(e, 'No se pudo finalizar la visita'));
    } finally {
      setSubmitting(false);
    }
  }

  const renderProducto = ({ item }) => {
    const qty = cart[item.id_producto] || 0;
    return (
      <View style={styles.productRow}>
        <View style={styles.productInfo}>
          <Text style={styles.productName}>{item.nombre}</Text>
          <Text style={styles.productStock}>Stock disp: {item.stock_disponible}</Text>
        </View>
        
        <View style={styles.counterWrap}>
          <Pressable style={styles.counterBtn} onPress={() => modifyCart(item.id_producto, -1)}>
            <Ionicons name="remove" size={20} color="#EF4444" />
          </Pressable>
          <Text style={styles.counterVal}>{qty}</Text>
          <Pressable style={styles.counterBtn} onPress={() => modifyCart(item.id_producto, 1)}>
            <Ionicons name="add" size={20} color="#10B981" />
          </Pressable>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        {orden != null ? (
          <View style={styles.row}>
            <Text style={styles.label}>Parada</Text>
            <Text style={styles.value}>#{orden}</Text>
          </View>
        ) : null}
        
        <View style={styles.row}>
          <Text style={styles.label}>Código</Text>
          <Text style={styles.value}>{String(codigo)}</Text>
        </View>
        
        <View style={styles.row}>
          <Text style={styles.label}>Nombre</Text>
          <Text style={styles.value} numberOfLines={1}>{String(nombre)}</Text>
        </View>
      </View>

      {estadoVisita === 'pendiente' && (
        <View style={styles.actionWrap}>
          <Pressable
            style={[styles.button, styles.buttonStart, submitting ? styles.buttonDisabled : null]}
            onPress={checkIn}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Iniciar visita (Check-In)</Text>
            )}
          </Pressable>
          <Text style={styles.hint}>Debes estar en la tienda para hacer Check-In.</Text>
        </View>
      )}

      {estadoVisita === 'en_curso' && (
        <View style={styles.deliveryContainer}>
          <Text style={styles.sectionTitle}>Productos a entregar</Text>
          
          {loadingProductos ? (
            <ActivityIndicator style={{marginTop: 20}} />
          ) : (
            <FlatList
              data={productos}
              keyExtractor={p => String(p.id_producto)}
              renderItem={renderProducto}
              contentContainerStyle={{ paddingBottom: 20 }}
            />
          )}

          <View style={styles.bottomActions}>
            <Pressable 
              style={[styles.button, styles.buttonSave, submitting ? styles.buttonDisabled : null]} 
              onPress={confirmarEntrega}
              disabled={submitting || entregado}
            >
              <Text style={styles.buttonText}>{entregado ? 'Entrega Confirmada ✅' : 'Confirmar Entrega'}</Text>
            </Pressable>

            <Pressable
              style={[styles.button, styles.buttonEnd, submitting ? styles.buttonDisabled : null]}
              onPress={checkOut}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Check-Out y Salir</Text>
              )}
            </Pressable>
          </View>
        </View>
      )}
      
      {estadoVisita === 'completada' && (
        <View style={styles.actionWrap}>
          <Text style={styles.completedText}>Visita Completada ✅</Text>
        </View>
      )}

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FAFAFA', padding: 16 },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {width: 0, height: 4},
    elevation: 3,
    marginBottom: 20
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  label: { color: '#6B7280', fontSize: 13, fontWeight: '600' },
  value: { fontSize: 15, fontWeight: '800', color: '#111827', flex: 1, textAlign: 'right' },
  actionWrap: { flex: 1, justifyContent: 'center' },
  button: {
    height: 52,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 14,
  },
  buttonStart: { backgroundColor: '#3B82F6' },
  buttonSave: { backgroundColor: '#10B981', marginTop: 10 },
  buttonEnd: { backgroundColor: '#EF4444', marginTop: 10 },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  hint: { color: '#6B7280', fontSize: 13, marginTop: 12, textAlign: 'center' },
  completedText: { color: '#10B981', fontSize: 18, fontWeight: '800', textAlign: 'center' },
  
  deliveryContainer: { flex: 1 },
  sectionTitle: { fontSize: 18, fontWeight: '900', color: '#1F2937', marginBottom: 10 },
  productRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    backgroundColor: '#fff', 
    padding: 12, 
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB'
  },
  productInfo: { flex: 1 },
  productName: { fontSize: 15, fontWeight: '700', color: '#1F2937' },
  productStock: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  counterWrap: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F3F4F6', borderRadius: 8, padding: 4 },
  counterBtn: { padding: 6, backgroundColor: '#fff', borderRadius: 6, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  counterVal: { width: 30, textAlign: 'center', fontWeight: '800', fontSize: 16 },
  bottomActions: { borderTopWidth: 1, borderColor: '#E5E7EB', paddingTop: 10, marginTop: 10 }
});
