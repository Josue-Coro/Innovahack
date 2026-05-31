import { useEffect, useRef } from 'react';
import * as Location from 'expo-location';
import * as Battery from 'expo-battery';

import { useAuthStore, getReponedorId } from './authStore';
import api from './apiClient';
import { endpoints } from '../constants/api';

function safeStringify(payload) {
  try {
    return JSON.stringify(payload);
  } catch {
    return '{}';
  }
}

async function batteryPercent() {
  const level = await Battery.getBatteryLevelAsync().catch(() => null);
  if (level == null) return null;
  return Math.round(level * 100);
}

export function useTrackingLocation({ intervalMs = 10000, pdvActual = '' } = {}) {
  const usuario = useAuthStore((s) => s.usuario);
  const isHydrated = useAuthStore((s) => s.isHydrated);
  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const isRunningRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    const idReponedor = getReponedorId(usuario);
    if (!idReponedor) return undefined;

    async function sendGpsHttp(lat, lon, nivelBateria) {
      try {
        await api.post(endpoints.gpsUsuario(idReponedor), {
          latitud: lat,
          longitud: lon,
          nivel_bateria: nivelBateria ?? undefined,
          timestamp: new Date().toISOString(),
        });
      } catch {
        // ignore
      }
    }

    async function start() {
      if (!isHydrated || isRunningRef.current) return;
      isRunningRef.current = true;

      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        isRunningRef.current = false;
        return;
      }

      const ws = new WebSocket(endpoints.wsReponedor(idReponedor));
      wsRef.current = ws;

      const tick = async () => {
        if (cancelled) return;
        try {
          const pos = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const nivelBateria = await batteryPercent();
          const payload = {
            lat,
            lon,
            timestamp: new Date().toISOString(),
            pdv_actual: pdvActual || '',
            nivel_bateria: nivelBateria ?? undefined,
          };

          if (ws.readyState === WebSocket.OPEN) {
            ws.send(safeStringify(payload));
          } else {
            await sendGpsHttp(lat, lon, nivelBateria);
          }
        } catch {
          // ignore
        }
      };

      ws.onopen = () => {
        if (cancelled) return;
        tick();
        timerRef.current = setInterval(tick, intervalMs);
      };

      ws.onclose = () => {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        if (!cancelled) {
          timerRef.current = setInterval(tick, intervalMs);
        }
      };

      ws.onerror = () => {
        if (!timerRef.current && !cancelled) {
          timerRef.current = setInterval(tick, intervalMs);
        }
      };
    }

    start();

    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
      if (wsRef.current) wsRef.current.close();
      wsRef.current = null;
      isRunningRef.current = false;
    };
  }, [usuario, isHydrated, intervalMs, pdvActual]);
}
