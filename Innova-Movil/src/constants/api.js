export const API_BASE_URL = 'https://innovahack-gcrh.onrender.com';

export const endpoints = {
  health: '/',
  login: '/login',
  rutas: '/rutas/',
  rutaById: (rutaId) => `/rutas/${rutaId}`,
  optimizarRuta: (rutaId) => `/rutas/${rutaId}/optimizar`,
  visitasByRuta: (rutaId) => `/visitas/ruta/${rutaId}`,
  registrarTiempo: (visitaId) => `/visitas/${visitaId}/registrar_tiempo`,
  iniciarVisita: (visitaId) => `/visitas/${visitaId}/iniciar`,
  iniciarVisitaLibre: '/visitas/libre',
  finalizarVisita: (visitaId) => `/visitas/${visitaId}/finalizar`,
  gps: '/gps/',
  gpsUsuario: (idUsuario) => `/usuarios/${idUsuario}/gps`,
  gpsBatch: (idUsuario) => `/usuarios/${idUsuario}/gps/batch`,
  pdvs: '/pdvs/',
  productos: '/productos/',
  entregas: '/entregas/',
  generarRutaDia: '/rutas/generar-dia',
  wsReponedor: (idReponedor) => {
    const base = API_BASE_URL.replace(/^http/, 'ws');
    return `${base}/ws/reponedor/${idReponedor}`;
  },
};
