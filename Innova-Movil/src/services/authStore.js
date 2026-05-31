import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setAuthToken } from './apiClient';

const STORAGE_KEY = 'camporuta.auth';

export const useAuthStore = create((set) => ({
  token: null,
  usuario: null,
  rol: null,
  isHydrated: false,

  hydrate: async () => {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        const rol = parsed.rol ?? null;
        const usuario = parsed.usuario ?? null;
        if (rol === 'reponedor' && parsed.token) {
          set({ token: parsed.token, usuario, rol });
          setAuthToken(parsed.token);
        } else {
          await AsyncStorage.removeItem(STORAGE_KEY);
          setAuthToken(null);
        }
      }
    } finally {
      set({ isHydrated: true });
    }
  },

  loginSuccess: async ({ token, usuario, rol }) => {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ token, usuario, rol }));
    setAuthToken(token);
    set({ token, usuario, rol });
  },

  logout: async () => {
    await AsyncStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    set({ token: null, usuario: null, rol: null });
  },
}));

export function getReponedorId(usuario) {
  return usuario?.id_usuario ?? null;
}
