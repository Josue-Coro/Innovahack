import React, { useState, useEffect, useMemo } from 'react';
import { View, Text, StyleSheet, FlatList, Pressable, TextInput, ActivityIndicator, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../services/apiClient';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';

export default function DeliveryScreen({ route, navigation }) {
  const { visitaId, idReponedor, idPdv, onDeliveryComplete } = route.params;
  
  const [productos, setProductos] = useState([]);
  const [cart, setCart] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchProductos();
  }, []);

  async function fetchProductos() {
    setLoading(true);
    try {
      const res = await api.get(endpoints.productos);
      setProductos(res?.data ?? []);
    } catch (e) {
      console.log('Error cargando productos', e);
    } finally {
      setLoading(false);
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
    const items = Object.entries(cart).filter(([_, cant]) => cant > 0);
    if (items.length === 0) {
      Alert.alert('Atención', 'No has seleccionado ningún producto para entregar.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        id_visita: visitaId,
        id_reponedor: idReponedor,
        id_pdv: idPdv,
        productos: items.map(([id_prod, cantidad]) => ({
          id_producto: parseInt(id_prod, 10),
          cantidad_entregada: cantidad
        }))
      };
      
      await api.post(endpoints.entregas, payload);
      Alert.alert('Éxito', 'Entrega guardada exitosamente.');
      if (onDeliveryComplete) {
        onDeliveryComplete();
      }
      navigation.goBack();
    } catch (e) {
      Alert.alert('Error', getApiError(e, 'No se pudo guardar la entrega.'));
    } finally {
      setSubmitting(false);
    }
  }

  // Filtrado y ordenamiento:
  // 1. Coincidir con la búsqueda (nombre o SKU).
  // 2. Elementos con cantidad > 0 van primero.
  const filteredAndSortedProductos = useMemo(() => {
    let result = productos;
    if (search.trim()) {
      const lowerSearch = search.toLowerCase();
      result = result.filter(p => 
        (p.nombre_producto || '').toLowerCase().includes(lowerSearch) ||
        (p.sku || '').toLowerCase().includes(lowerSearch)
      );
    }

    result.sort((a, b) => {
      const aQty = cart[a.id_producto] || 0;
      const bQty = cart[b.id_producto] || 0;
      
      // Si a tiene y b no, a va primero
      if (aQty > 0 && bQty === 0) return -1;
      // Si b tiene y a no, b va primero
      if (bQty > 0 && aQty === 0) return 1;
      
      // De lo contrario, orden alfabético
      return (a.nombre_producto || '').localeCompare(b.nombre_producto || '');
    });

    return result;
  }, [productos, search, cart]);

  const ProductoItem = React.memo(({ item, qty, onModify }) => {
    const isSelected = qty > 0;
    return (
      <View style={[styles.productRow, isSelected && styles.productRowSelected]}>
        <View style={styles.productInfo}>
          <Text style={styles.productName}>{item.nombre_producto}</Text>
          <Text style={styles.productStock}>Stock disp: {item.stock_actual}</Text>
        </View>
        
        <View style={styles.counterWrap}>
          <Pressable style={styles.counterBtn} onPress={() => onModify(item.id_producto, -1)}>
            <Ionicons name="remove" size={20} color="#EF4444" />
          </Pressable>
          <Text style={[styles.counterVal, isSelected && { fontWeight: 'bold', color: '#10B981' }]}>{qty}</Text>
          <Pressable style={styles.counterBtn} onPress={() => onModify(item.id_producto, 1)}>
            <Ionicons name="add" size={20} color="#10B981" />
          </Pressable>
        </View>
      </View>
    );
  }, (prev, next) => prev.qty === next.qty && prev.item.id_producto === next.item.id_producto);

  const renderProducto = ({ item }) => {
    return <ProductoItem item={item} qty={cart[item.id_producto] || 0} onModify={modifyCart} />;
  };

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <Ionicons name="search" size={20} color="#9CA3AF" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar producto por nombre o SKU..."
          value={search}
          onChangeText={setSearch}
        />
        {search.length > 0 && (
          <Pressable onPress={() => setSearch('')}>
            <Ionicons name="close-circle" size={20} color="#9CA3AF" />
          </Pressable>
        )}
      </View>

      {loading ? (
        <ActivityIndicator style={{ flex: 1 }} size="large" color="#3B82F6" />
      ) : (
        <FlatList
          data={filteredAndSortedProductos}
          keyExtractor={p => String(p.id_producto)}
          renderItem={renderProducto}
          contentContainerStyle={{ paddingBottom: 20 }}
          ListEmptyComponent={<Text style={styles.emptyText}>No se encontraron productos.</Text>}
        />
      )}

      <View style={styles.bottomActions}>
        <Pressable 
          style={[styles.buttonSave, submitting && styles.buttonDisabled]} 
          onPress={confirmarEntrega}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Confirmar y Guardar Entrega</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    height: 48
  },
  searchIcon: { marginRight: 8 },
  searchInput: { flex: 1, height: '100%', fontSize: 16 },
  productRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  productRowSelected: {
    borderColor: '#10B981',
    backgroundColor: '#F0FDF4',
  },
  productInfo: { flex: 1, paddingRight: 12 },
  productName: { fontSize: 16, fontWeight: '600', color: '#111827', marginBottom: 4 },
  productStock: { fontSize: 13, color: '#6B7280' },
  counterWrap: { flexDirection: 'row', alignItems: 'center' },
  counterBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  counterVal: { width: 30, textAlign: 'center', fontSize: 16, fontWeight: '600' },
  bottomActions: { padding: 16, backgroundColor: '#fff', borderTopWidth: 1, borderColor: '#E5E7EB' },
  buttonSave: {
    backgroundColor: '#10B981',
    height: 52,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  emptyText: { textAlign: 'center', color: '#6B7280', marginTop: 20 },
});
