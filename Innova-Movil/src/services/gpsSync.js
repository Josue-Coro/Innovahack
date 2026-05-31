import { getDb } from './dbService';
import api from './apiClient';
import { endpoints } from '../constants/api';

export const saveGpsOffline = async (gpsData) => {
  try {
    const db = await getDb();
    await db.runAsync(
      `INSERT INTO offline_gps (id_reponedor, latitud, longitud, precision_m, velocidad_kmh, nivel_bateria, timestamp)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        gpsData.id_reponedor,
        gpsData.latitud,
        gpsData.longitud,
        gpsData.precision_m,
        gpsData.velocidad_kmh,
        gpsData.nivel_bateria ?? null,
        gpsData.timestamp
      ]
    );
    console.log('[GPS Sync] Ubicación guardada localmente.');
  } catch (error) {
    console.error('[GPS Sync] Error guardando GPS offline:', error);
  }
};

let isSyncing = false;

export const syncOfflineGps = async () => {
  if (isSyncing) return;
  isSyncing = true;
  try {
    const db = await getDb();
    // Leer todas las ubicaciones ordenadas cronológicamente
    const rows = await db.getAllAsync('SELECT * FROM offline_gps ORDER BY id ASC');
    
    if (rows && rows.length > 0) {
      console.log(`[GPS Sync] Encontradas ${rows.length} ubicaciones pendientes. Intentando enviar...`);
      
      // Agrupar por id_reponedor (aunque usualmente será el mismo)
      const groups = {};
      rows.forEach(row => {
        if (!groups[row.id_reponedor]) groups[row.id_reponedor] = [];
        groups[row.id_reponedor].push(row);
      });

      for (const idReponedor of Object.keys(groups)) {
        const locations = groups[idReponedor];
        const payload = locations.map(loc => ({
          latitud: loc.latitud,
          longitud: loc.longitud,
          precision_m: loc.precision_m,
          velocidad_kmh: loc.velocidad_kmh,
          nivel_bateria: loc.nivel_bateria,
          timestamp: loc.timestamp
        }));

        try {
          await api.post(endpoints.gpsBatch(idReponedor), payload);
          // Si tiene éxito, borramos estas ubicaciones de la base de datos local
          const ids = locations.map(l => l.id).join(',');
          await db.runAsync(`DELETE FROM offline_gps WHERE id IN (${ids})`);
          console.log(`[GPS Sync] Sincronización exitosa. Borrados ${locations.length} registros.`);
        } catch (apiError) {
          console.log('[GPS Sync] Servidor inaccesible. Se intentará en el próximo ciclo.');
          // Si falla, paramos el ciclo para no abrumar al servidor con otros reponedores (si los hay)
          break; 
        }
      }
    }
  } catch (error) {
    console.error('[GPS Sync] Error en el proceso de sincronización:', error);
  } finally {
    isSyncing = false;
  }
};
