import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, Pressable, ActivityIndicator, Alert } from 'react-native';
import * as Location from 'expo-location';
import api from '../services/apiClient';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';

export default function VisitExecutionScreen({ route, navigation }) {
  const { visitaId, pdv, orden, estadoVisita: initialEstado } = route.params ?? {};
  const [submitting, setSubmitting] = useState(false);
  const [estadoVisita, setEstadoVisita] = useState(initialEstado ?? 'pendiente');

  const codigo = useMemo(() => pdv?.codigo_gv ?? '—', [pdv]);
  const nombre = useMemo(() => pdv?.nombre_pdv ?? 'PDV', [pdv]);
  const direccion = useMemo(() => pdv?.direccion ?? '—', [pdv]);

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
    if (!visitaId || submitting) return;
    setSubmitting(true);
    try {
      const payload = await getLocation();
      if (!payload) {
        setSubmitting(false);
        return;
      }
      
      await api.post(endpoints.iniciarVisita(visitaId), payload);
      Alert.alert('Check-In Exitoso', 'La visita ha iniciado. Registra el tiempo restante y finaliza cuando termines.');
      setEstadoVisita('en_progreso');
    } catch (e) {
      Alert.alert('No puedes iniciar', getApiError(e, 'No se pudo iniciar la visita'));
    } finally {
      setSubmitting(false);
    }
  }

  async function checkOut() {
    if (!visitaId || submitting) return;
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

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        {orden != null ? (
          <>
            <Text style={styles.label}>Parada</Text>
            <Text style={styles.value}>#{orden}</Text>
          </>
        ) : null}

        <Text style={styles.label}>Código</Text>
        <Text style={styles.value}>{String(codigo)}</Text>

        <Text style={styles.label}>Nombre</Text>
        <Text style={styles.value}>{String(nombre)}</Text>

        <Text style={styles.label}>Dirección</Text>
        <Text style={styles.value}>{String(direccion)}</Text>
      </View>

      {estadoVisita === 'pendiente' && (
        <>
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
        </>
      )}

      {estadoVisita === 'en_progreso' && (
        <>
          <Pressable
            style={[styles.button, styles.buttonEnd, submitting ? styles.buttonDisabled : null]}
            onPress={checkOut}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Finalizar visita (Check-Out)</Text>
            )}
          </Pressable>
          <Text style={styles.hint}>No olvides presionar antes de irte de la tienda.</Text>
        </>
      )}
      
      {estadoVisita === 'completada' && (
        <Text style={styles.completedText}>Visita Completada ✅</Text>
      )}

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 16, justifyContent: 'space-between' },
  card: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 16,
    backgroundColor: '#FAFAFA',
    gap: 10,
  },
  label: { color: '#6B7280', fontWeight: '800', fontSize: 12 },
  value: { fontSize: 16, fontWeight: '900', color: '#111827' },
  button: {
    height: 48,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 14,
  },
  buttonStart: { backgroundColor: '#2563EB' },
  buttonEnd: { backgroundColor: '#DC2626' },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '900', fontSize: 15 },
  hint: { color: '#6B7280', fontSize: 12, marginTop: 10, textAlign: 'center' },
  completedText: { color: '#10B981', fontSize: 16, fontWeight: '800', textAlign: 'center', marginTop: 20 },
});
