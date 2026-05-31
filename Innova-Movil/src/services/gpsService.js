import * as Location from 'expo-location';
import * as Battery from 'expo-battery';
import api from './apiClient';
import { endpoints } from '../constants/api';
import { getApiError } from '../utils/apiError';

export async function registrarPosicionGps(idReponedor) {
  if (!idReponedor) {
    throw new Error('No se encontró el ID del reponedor');
  }

  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') {
    throw new Error('Permiso de ubicación denegado. Actívalo en ajustes del teléfono.');
  }

  const pos = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.High,
  });

  const speedMs = pos.coords.speed;
  const velocidadKmh =
    speedMs != null && !Number.isNaN(speedMs) ? Math.round(speedMs * 3.6 * 10) / 10 : 0;

  let nivelBateria = null;
  try {
    const level = await Battery.getBatteryLevelAsync();
    if (level != null) nivelBateria = Math.round(level * 100);
  } catch (e) {
    // ignore
  }

  const body = {
    latitud: pos.coords.latitude,
    longitud: pos.coords.longitude,
    precision_m: pos.coords.accuracy ?? 0,
    velocidad_kmh: velocidadKmh,
    nivel_bateria: nivelBateria ?? undefined,
    timestamp: new Date().toISOString(),
  };

  const res = await api.post(endpoints.gpsUsuario(idReponedor), body);
  return { body, response: res?.data };
}

export async function registrarPosicionGpsSafe(idReponedor) {
  try {
    const result = await registrarPosicionGps(idReponedor);
    return { ok: true, ...result };
  } catch (error) {
    return { ok: false, message: getApiError(error, 'No se pudo enviar la posición GPS') };
  }
}
