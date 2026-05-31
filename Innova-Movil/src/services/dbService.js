import * as SQLite from 'expo-sqlite';

// Singleton instance
let db = null;

export const getDb = async () => {
  if (!db) {
    db = await SQLite.openDatabaseAsync('innovadb.sqlite');
    await initDb();
  }
  return db;
};

export const initDb = async () => {
  const dbInstance = await getDb();
  await dbInstance.execAsync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS offline_gps (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      id_reponedor INTEGER NOT NULL,
      latitud REAL NOT NULL,
      longitud REAL NOT NULL,
      precision_m REAL,
      velocidad_kmh REAL,
      nivel_bateria INTEGER,
      timestamp TEXT NOT NULL
    );
  `);
};
