# CampoRuta v3.0 — Documentación API para Frontend

## URL Base

```
https://TU-APP.onrender.com
```

> Reemplazar `TU-APP` con el nombre de tu servicio en Render.
> La documentación interactiva (Swagger) está en: `https://TU-APP.onrender.com/docs`

---

## Verificar que el backend está activo

```
GET /
```

**Respuesta:**
```json
{
  "status": "ok",
  "proyecto": "CampoRuta",
  "version": "3.0.0"
}
```

---

---

# 1. RUTAS

Prefijo: `/rutas`

---

### 1.1 Obtener todas las rutas

```
GET /rutas/
```

**No requiere body.** Retorna todas las rutas ordenadas por fecha de creación (más recientes primero).

**Respuesta:** Array de rutas
```json
[
  {
    "id_ruta": 1,
    "id_reponedor": 5,
    "id_supervisor": 2,
    "fecha": "2026-05-30",
    "estado": "pendiente",
    "distancia_km_estimada": 12.5,
    "duracion_min_estimada": 180,
    "distancia_km_real": null,
    "duracion_min_real": null,
    "hora_inicio_real": null,
    "hora_fin_real": null,
    "creado_en": "2026-05-30T10:00:00",
    "actualizado_en": "2026-05-30T10:00:00"
  }
]
```

---

### 1.2 Obtener una ruta con sus puntos (paradas)

```
GET /rutas/{ruta_id}
```

**Respuesta:** La ruta con el array `ruta_puntos` que incluye los PDVs
```json
{
  "id_ruta": 1,
  "id_reponedor": 5,
  "id_supervisor": 2,
  "fecha": "2026-05-30",
  "estado": "pendiente",
  "creado_en": "2026-05-30T10:00:00",
  "actualizado_en": "2026-05-30T10:00:00",
  "ruta_puntos": [
    {
      "id_ruta_punto": 10,
      "id_ruta": 1,
      "id_pdv": 3,
      "orden": 1,
      "hora_estimada_llegada": null,
      "estado": "pendiente",
      "pdv": {
        "id_pdv": 3,
        "codigo_gv": "GV001",
        "nombre_pdv": "Tienda Don Juan",
        "direccion": "Calle Comercio #123",
        "latitud": -16.5,
        "longitud": -68.15,
        "tiempo_visita_min": 20,
        "prioridad": "alta"
      }
    }
  ]
}
```

---

### 1.3 Crear una ruta

```
POST /rutas/
```

**Body (JSON):**
```json
{
  "id_reponedor": 5,
  "id_supervisor": 2,
  "fecha": "2026-06-01",
  "estado": "pendiente"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id_reponedor` | int | **Sí** | ID del reponedor asignado |
| `id_supervisor` | int | No | ID del supervisor |
| `fecha` | string | **Sí** | Fecha de la ruta (YYYY-MM-DD) |
| `estado` | string | No | `"pendiente"` / `"en_progreso"` / `"completada"` (default: `"pendiente"`) |

**Respuesta:** `201 Created` + la ruta creada

---

### 1.4 Actualizar una ruta

```
PUT /rutas/{ruta_id}
```

**Body (JSON):** Solo enviar los campos que quieres actualizar
```json
{
  "estado": "en_progreso",
  "hora_inicio_real": "2026-05-30T08:30:00"
}
```

---

### 1.5 Eliminar una ruta

```
DELETE /rutas/{ruta_id}
```

**No requiere body.** Respuesta: `204 No Content`

---

### 1.6 Optimizar ruta (calcular camino más corto)

```
POST /rutas/{ruta_id}/optimizar
```

**No requiere body.** El backend reordena las paradas usando el algoritmo de vecino más cercano (TSP) para encontrar la ruta más corta.

**Respuesta:** La ruta con las paradas reordenadas
```json
{
  "id_ruta": 1,
  "ruta_puntos": [
    { "id_ruta_punto": 10, "orden": 1, "pdv": { "nombre_pdv": "Tienda A", "latitud": -16.50, "longitud": -68.15 } },
    { "id_ruta_punto": 12, "orden": 2, "pdv": { "nombre_pdv": "Tienda B", "latitud": -16.51, "longitud": -68.13 } },
    { "id_ruta_punto": 11, "orden": 3, "pdv": { "nombre_pdv": "Tienda C", "latitud": -16.52, "longitud": -68.12 } }
  ]
}
```

**Ejemplo JavaScript:**
```javascript
const response = await fetch('https://TU-APP.onrender.com/rutas/1/optimizar', {
  method: 'POST'
});
const rutaOptimizada = await response.json();
// rutaOptimizada.ruta_puntos ya viene ordenado por distancia óptima
```

---

---

# 2. VISITAS

Prefijo: `/visitas`

---

### 2.1 Obtener visitas de una ruta

```
GET /visitas/ruta/{ruta_id}
```

**Respuesta:** Array de visitas ordenadas por el orden de la parada
```json
[
  {
    "id_visita": 1,
    "id_ruta_punto": 10,
    "id_reponedor": 5,
    "id_pdv": 3,
    "fecha": "2026-05-30",
    "hora_llegada": null,
    "hora_salida": null,
    "duracion_real_min": null,
    "estado": "pendiente",
    "motivo_no_visita": null,
    "quiebre_de_stock": false,
    "clima_descripcion": null,
    "temperatura_c": null,
    "notas": null,
    "foto_url": null,
    "lat_registro": null,
    "lon_registro": null,
    "creado_en": "2026-05-30T10:00:00",
    "actualizado_en": "2026-05-30T10:00:00"
  }
]
```

---

### 2.2 Crear una visita en una ruta

```
POST /visitas/ruta/{ruta_id}
```

**Body (JSON):**
```json
{
  "id_reponedor": 5,
  "id_pdv": 3,
  "fecha": "2026-05-30",
  "estado": "pendiente",
  "notas": "Cliente nuevo",
  "lat_registro": -16.5,
  "lon_registro": -68.15
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `id_reponedor` | int | **Sí** | ID del reponedor |
| `id_pdv` | int | **Sí** | ID del punto de venta |
| `fecha` | string | **Sí** | Fecha (YYYY-MM-DD) |
| `estado` | string | No | `"pendiente"` / `"completada"` / `"cancelada"` / `"omitida"` |
| `motivo_no_visita` | string | No | Razón si no se visitó |
| `quiebre_de_stock` | bool | No | `true` si hay quiebre de stock |
| `clima_descripcion` | string | No | Ej: `"Lluvia ligera"` |
| `temperatura_c` | float | No | Temperatura al momento |
| `notas` | string | No | Observaciones |
| `foto_url` | string | No | URL de foto tomada |
| `lat_registro` | float | No | Latitud GPS al registrar |
| `lon_registro` | float | No | Longitud GPS al registrar |

---

### 2.3 Actualizar una visita

```
PUT /visitas/{visita_id}
```

**Body (JSON):** Solo los campos que cambian
```json
{
  "estado": "completada",
  "hora_llegada": "2026-05-30T09:15:00",
  "hora_salida": "2026-05-30T09:35:00",
  "notas": "Atendido sin problemas"
}
```

---

### 2.4 Eliminar una visita

```
DELETE /visitas/{visita_id}
```

**Respuesta:** `204 No Content`

---

### 2.5 Registrar tiempo real de una visita (feedback loop)

```
POST /visitas/{visita_id}/registrar_tiempo
```

**Body (JSON):**
```json
{
  "tiempo_real_min": 25.5
}
```

Este endpoint:
- Marca la visita como `"completada"`
- Calcula la desviación vs el tiempo estimado del PDV
- Si la desviación es >30%, marca el PDV para recalibración
- Actualiza el promedio móvil de tiempos del PDV
- Guarda en historial_tiempos_pdv

**Ejemplo JavaScript:**
```javascript
// Cuando el reponedor termina una visita
const response = await fetch('https://TU-APP.onrender.com/visitas/42/registrar_tiempo', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tiempo_real_min: 25.5 })
});
const visitaActualizada = await response.json();
```

---

### 2.6 Importar visitas desde archivo Excel/CSV

```
POST /visitas/ruta/{ruta_id}/importar
```

**Body:** `multipart/form-data` con un archivo `.csv` o `.xlsx`

**Columnas requeridas en el archivo:**
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `cliente_nombre` | string | Nombre del cliente/PDV |
| `direccion` | string | Dirección del PDV |
| `latitud` | float | Latitud GPS |
| `longitud` | float | Longitud GPS |

**Ejemplo JavaScript:**
```javascript
const formData = new FormData();
formData.append('file', archivoExcel); // File object del input

const response = await fetch('https://TU-APP.onrender.com/visitas/ruta/1/importar', {
  method: 'POST',
  body: formData
  // NO poner Content-Type, el browser lo pone automáticamente con boundary
});
const visitasCreadas = await response.json();
```

---

---

# 3. DASHBOARD Y MÉTRICAS

---

### 3.1 Métricas generales (sin filtro de fecha)

```
GET /dashboard/metrics
```

**Respuesta:**
```json
{
  "total_rutas": 15,
  "total_visitas": 120,
  "visitas_completadas": 85,
  "visitas_pendientes": 30,
  "visitas_canceladas": 5,
  "promedio_calificacion": 0.0,
  "eficiencia_ruta_pct": 70.83
}
```

---

### 3.2 Métricas completas por fecha

```
GET /dashboard/metricas/{fecha}
```

- `fecha` formato: `YYYY-MM-DD` (ej: `2026-05-30`)

**Respuesta:**
```json
{
  "total_asignados": 50,
  "total_completados": 35,
  "cobertura_por_supervisor": {
    "Carlos Pérez": 80.0,
    "María López": 65.0
  },
  "cobertura_por_mercado": {
    "Mercado Lanza": 90.0,
    "Mercado Rodriguez": 70.0,
    "SIN_MERCADO": 50.0
  },
  "top_reponedores_eficientes": [
    { "reponedor_id": "Juan Mamani", "eficiencia": 95.5 },
    { "reponedor_id": "Pedro Quispe", "eficiencia": 88.3 },
    { "reponedor_id": "Ana Torres", "eficiencia": 82.1 }
  ],
  "pdvs_no_visitados": [
    {
      "pdv_codigo": "GV001",
      "pdv_nombre": "Tienda Don Juan",
      "latitud": -16.5,
      "longitud": -68.15
    }
  ],
  "tiempo_promedio_categoria": {
    "MAYORISTA": { "real": 35.2, "estimado": 30.0 },
    "MINORISTA": { "real": 18.5, "estimado": 20.0 },
    "DETALLISTA": { "real": 12.0, "estimado": 15.0 }
  }
}
```

> **Nota para el mapa:** Usa el array `pdvs_no_visitados` con `latitud`/`longitud` para pintar los PDVs pendientes en el mapa.

---

### 3.3 Métricas individuales de un reponedor por fecha

```
GET /dashboard/reponedor/{reponedor_id}/{fecha}
```

- `reponedor_id`: ID numérico del usuario reponedor
- `fecha`: formato `YYYY-MM-DD`

**Respuesta:**
```json
{
  "metricas": {
    "cobertura_pct": 80.0,
    "tiempos_por_categoria": {
      "MAYORISTA": { "promedio_real": 32.0, "promedio_estimado": 30.0 },
      "MINORISTA": { "promedio_real": 18.0, "promedio_estimado": 20.0 }
    },
    "mayores_desviaciones": [
      { "codigo": "GV005", "nombre": "Tienda Lola", "desviacion_min": 15.0 }
    ],
    "eficiencia": 85.5
  },
  "visitas": [
    {
      "visita_id": 12,
      "cliente_nombre": "Tienda Don Juan",
      "estado": "completada",
      "tiempo_real_min": 25.0,
      "tiempo_estimado_min": 20.0
    },
    {
      "visita_id": 13,
      "cliente_nombre": "Kiosco María",
      "estado": "pendiente",
      "tiempo_real_min": 0,
      "tiempo_estimado_min": 15.0
    }
  ],
  "desviaciones": [
    {
      "pdv_codigo": "GV001",
      "pdv_nombre": "Tienda Don Juan",
      "desviacion_min": 5.0
    }
  ]
}
```

---

### 3.4 Exportar reporte CSV del día

```
GET /reporte/exportar/{fecha}
```

**Descarga directa** de un archivo CSV. Ideal para botón "Descargar Reporte".

**Columnas del CSV:**
`reponedor, pdv_codigo, pdv_nombre, categoria, mercado, hora_inicio, hora_fin, tiempo_real_min, tiempo_estimado_min, desviacion_min, estado, notas`

**Ejemplo JavaScript:**
```javascript
// Descargar CSV
const fecha = '2026-05-30';
const link = document.createElement('a');
link.href = `https://TU-APP.onrender.com/reporte/exportar/${fecha}`;
link.download = `reporte_${fecha}.csv`;
link.click();
```

---

### 3.5 Consultar clima en una ubicación

```
GET /clima/{lat}/{lon}
```

- `lat`: Latitud (ej: `-16.5`)
- `lon`: Longitud (ej: `-68.15`)

**Respuesta:**
```json
{
  "temperatura": 18.5,
  "precipitacion": 0.0,
  "descripcion": "Parcialmente nublado"
}
```

> El backend cachea las respuestas por 30 minutos para no saturar la API externa.

**Ejemplo JavaScript:**
```javascript
const response = await fetch('https://TU-APP.onrender.com/clima/-16.5/-68.15');
const clima = await response.json();
// clima.temperatura → 18.5
// clima.descripcion → "Parcialmente nublado"
```

---

---

# 4. WEBSOCKET (Tiempo Real)

Prefijo: `/ws`

> **Protocolo:** `wss://` en producción (Render), `ws://` en local

---

### 4.1 WebSocket del Reponedor (app móvil)

```
wss://TU-APP.onrender.com/ws/reponedor/{reponedor_id}
```

**El reponedor ENVÍA** su ubicación GPS cada pocos segundos:
```json
{
  "lat": -16.5000,
  "lon": -68.1500,
  "timestamp": "2026-05-30T09:15:00",
  "pdv_actual": "GV001"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `lat` | float | Latitud actual |
| `lon` | float | Longitud actual |
| `timestamp` | string | Hora del dispositivo |
| `pdv_actual` | string | Código del PDV que está visitando (o vacío) |

**El reponedor RECIBE** broadcasts del sistema:
```json
{
  "type": "RUTA_OPTIMIZADA",
  "payload": { ... }
}
```

**Ejemplo JavaScript (React Native / Web):**
```javascript
const ws = new WebSocket('wss://TU-APP.onrender.com/ws/reponedor/5');

ws.onopen = () => {
  console.log('Conectado al backend');
  
  // Enviar ubicación cada 10 segundos
  setInterval(() => {
    navigator.geolocation.getCurrentPosition((pos) => {
      ws.send(JSON.stringify({
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        timestamp: new Date().toISOString(),
        pdv_actual: pdvActualId || ""
      }));
    });
  }, 10000);
};

ws.onmessage = (event) => {
  const mensaje = JSON.parse(event.data);
  
  switch (mensaje.type) {
    case 'RUTA_OPTIMIZADA':
      // Actualizar mapa con nueva ruta
      actualizarMapa(mensaje.payload.puntos);
      break;
    case 'VISITA_CREADA':
      // Nueva visita asignada
      break;
  }
};

ws.onclose = () => {
  console.log('Desconectado — reconectar...');
  // Implementar reconexión automática
};
```

---

### 4.2 WebSocket del Supervisor (dashboard web)

```
wss://TU-APP.onrender.com/ws/supervisor/{supervisor_id}
```

**El supervisor NO envía datos**, solo mantiene la conexión abierta.

**El supervisor RECIBE** actualizaciones de ubicación de sus reponedores:
```json
{
  "reponedores": [
    {
      "id": "5",
      "lat": -16.5000,
      "lon": -68.1500,
      "estado": "activo",
      "pdv_actual": "GV001",
      "ultimo_update": "2026-05-30T09:15:00"
    },
    {
      "id": "6",
      "lat": -16.4800,
      "lon": -68.1200,
      "estado": "sin_señal",
      "pdv_actual": "",
      "ultimo_update": "Nunca"
    }
  ]
}
```

| Estado del reponedor | Significado |
|---------------------|-------------|
| `"activo"` | Enviando GPS en los últimos 5 minutos |
| `"sin_señal"` | Sin actualización por más de 5 minutos |
| `"desconectado"` | WebSocket cerrado |

**Ejemplo JavaScript (Dashboard Web):**
```javascript
const ws = new WebSocket('wss://TU-APP.onrender.com/ws/supervisor/2');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // data.reponedores → array con ubicación de cada reponedor
  data.reponedores.forEach(rep => {
    actualizarMarkerEnMapa(rep.id, rep.lat, rep.lon, rep.estado);
  });
};
```

---

### Tipos de broadcast que pueden llegar por WebSocket

Estos mensajes llegan tanto a reponedores como supervisores conectados:

| Tipo | Cuándo se dispara | Payload |
|------|-------------------|---------|
| `RUTA_ACTUALIZADA` | Se actualiza una ruta | `{ id_ruta, id_reponedor, fecha, estado }` |
| `RUTA_ELIMINADA` | Se elimina una ruta | `{ id_ruta }` |
| `RUTA_OPTIMIZADA` | Se optimiza una ruta | `{ id_ruta, id_reponedor, puntos: [...] }` |
| `VISITA_CREADA` | Se crea una visita | `{ id_visita, id_ruta_punto, id_pdv }` |
| `VISITA_ACTUALIZADA` | Se actualiza una visita | `{ id_visita, id_ruta_punto, estado }` |
| `VISITA_ELIMINADA` | Se elimina una visita | `{ id_visita, id_ruta_punto }` |
| `VISITA_COMPLETADA` | Se registra tiempo real | `{ id_visita, duracion_real_min, estado }` |
| `VISITAS_IMPORTADAS` | Se importa archivo Excel | `{ ruta_id, cantidad }` |

---

---

# 5. CATÁLOGOS BASE (CRUDs)

Para la administración del sistema (ABM), existen endpoints CRUD estándar (`GET`, `POST`, `PUT`, `DELETE`) para las siguientes entidades. Todos respetan el mismo formato:

* `GET /entidad/` — Listar todos (soporta query params para filtrar)
* `GET /entidad/{id}` — Obtener uno específico
* `POST /entidad/` — Crear uno nuevo
* `PUT /entidad/{id}` — Actualizar
* `DELETE /entidad/{id}` — Eliminar

### Entidades disponibles:

| Prefijo URL | Descripción | Filtros GET disponibles |
|-------------|-------------|-------------------------|
| `/roles/` | Roles del sistema | - |
| `/departamentos/` | Departamentos de Bolivia | - |
| `/ciudades/` | Ciudades / Municipios | `?id_departamento=X` |
| `/mercados/` | Mercados | `?id_ciudad=X` |
| `/usuarios/` | Usuarios (admin, supervisores, reponedores) | `?id_rol=X`, `?id_supervisor=X`, `?activo=true/false` |
| `/perfiles-reponedor/` | Configuración específica de reponedores | endpoint extra: `GET /perfiles-reponedor/usuario/{id}` |
| `/sesiones/` | Sesiones activas (solo GET, POST, DELETE) | `?id_usuario=X` |
| `/categorias-cliente/` | Categorías (Mayorista, Minorista, etc) | - |
| `/pdvs/` | Puntos de Venta (Clientes) | `?id_mercado=X`, `?id_categoria=X`, `?id_supervisor=X`, `?id_reponedor_asignado=X` |
| `/micro-tareas/` | Tareas por categoría de PDV | `?id_categoria=X` |
| `/gps/` | Posiciones GPS (solo POST y GET) | `?id_reponedor=X` |
| `/incidencias/` | Incidencias (problemas en PDVs) | `?resuelta=true/false`, `?id_reponedor=X` |
| `/redistribuciones/`| Redistribuciones sugeridas | `?estado=X` |
| `/kpis/` | KPIs diarios por reponedor | `?id_reponedor=X`, `?fecha=YYYY-MM-DD` |
| `/notificaciones/` | Alertas del sistema | `?id_supervisor=X`, `?id_reponedor=X`, `?leida=true/false` |

> **🔐 Nota sobre Creación de Usuarios:**
> Al hacer un `POST /usuarios/` o `PUT /usuarios/{id}`, debes enviar el campo `"password"` en **texto plano**. El backend se encarga automáticamente de encriptarlo (Bcrypt) antes de guardarlo en la base de datos.
>
> **Ejemplo de POST /usuarios/:**
> ```json
> {
>   "id_rol": 3,
>   "id_ciudad": 1,
>   "nombre": "Juan Reponedor",
>   "email": "juan@venado.bo",
>   "telefono": "77712345",
>   "id_supervisor": 2,
>   "activo": true,
>   "password": "mi_password_seguro123"
> }
> ```

---

# 6. AUTENTICACIÓN (LOGIN)

El backend expone un endpoint específico para el inicio de sesión. 

```http
POST /login
```

**Body (JSON):**
```json
{
  "email": "juan@venado.bo",
  "password": "mi_password_seguro123"
}
```

**Respuesta Exitosa (200 OK):**
```json
{
  "token": "4f5a... (UUID del Token de Sesión)",
  "usuario": {
    "id_usuario": 1,
    "nombre": "Juan Reponedor",
    "email": "juan@venado.bo",
    "id_rol": 3,
    "activo": true
    // ... otros datos del usuario
  },
  "rol": "reponedor"
}
```
> **Nota para el Frontend:** El `token` que devuelve el endpoint de login se guarda automáticamente en la base de datos en la tabla de sesiones con una expiración de 30 días. Actualmente las rutas no exigen el token en los headers de forma estricta, pero el frontend puede guardarlo en `localStorage` para mantener la sesión del usuario viva e identificarlo.

---
c

# 7. RASTREO GPS Y BATERÍA

Para que la aplicación móvil reporte la ubicación actual del reponedor en background o cuando pierde conexión al WebSocket, se debe usar este endpoint.

```http
POST /usuarios/{id_usuario}/gps
```

**Body (JSON):**
```json
{
  "latitud": -16.536786,
  "longitud": -68.046968,
  "precision_m": 12.5,
  "velocidad_kmh": 4.2,
  "nivel_bateria": 85,
  "timestamp": "2023-10-25T14:30:00Z"
}
```
*Nota:* `precision_m`, `velocidad_kmh`, `nivel_bateria` y `timestamp` son opcionales, pero **se recomienda fuertemente enviar el `nivel_bateria`** para que el supervisor vea el celular del reponedor en vivo.

**Respuesta Exitosa (201 Created):**
```json
{
  "message": "Ubicación GPS actualizada exitosamente"
}
```

> **¡Importante para WebSockets!**
> Si estás usando la conexión en vivo `ws://.../ws/reponedor/{id}`, también puedes enviar el campo `"nivel_bateria": 85` en el JSON que mandas por el socket para actualizar el panel del supervisor al instante.

---

# 8. RESUMEN RÁPIDO DE TODOS LOS ENDPOINTS (Cheat Sheet)

### Endpoints Principales (Operación Diaria)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/rutas/` | Listar todas las rutas |
| `GET` | `/rutas/{id}` | Obtener ruta con paradas |
| `POST` | `/rutas/` | Crear ruta |
| `PUT` | `/rutas/{id}` | Actualizar ruta |
| `DELETE` | `/rutas/{id}` | Eliminar ruta |
| `POST` | `/rutas/{id}/optimizar` | Optimizar orden de paradas (TSP) |
| `GET` | `/visitas/ruta/{ruta_id}` | Listar visitas de una ruta |
| `POST` | `/visitas/ruta/{ruta_id}` | Crear visita |
| `PUT` | `/visitas/{id}` | Actualizar visita |
| `DELETE` | `/visitas/{id}` | Eliminar visita |
| `POST` | `/visitas/{id}/registrar_tiempo` | Registrar tiempo real (feedback) |
| `POST` | `/visitas/ruta/{id}/importar` | Importar visitas desde Excel/CSV |
| `GET` | `/dashboard/metrics` | Métricas generales |
| `GET` | `/dashboard/metricas/{fecha}` | KPIs del día completo |
| `GET` | `/dashboard/reponedor/{id}/{fecha}` | Métricas individuales por reponedor |
| `GET` | `/reporte/exportar/{fecha}` | Descargar CSV del día |
| `GET` | `/clima/{lat}/{lon}` | Consultar clima |
| `WS` | `/ws/reponedor/{id}` | WebSocket del reponedor |
| `WS` | `/ws/supervisor/{id}` | WebSocket del supervisor |

### Endpoints CRUD de Mantenimiento
*(Todos incluyen GET, POST, PUT, DELETE a menos que se indique lo contrario)*

| Dominio | Endpoints Base |
|---------|----------------|
| **Usuarios** | `/usuarios/`, `/roles/`, `/perfiles-reponedor/`, `/sesiones/` |
| **Geografía**| `/departamentos/`, `/ciudades/`, `/mercados/` |
| **Catálogo** | `/categorias-cliente/`, `/pdvs/`, `/micro-tareas/` |
| **Gestión**  | `/incidencias/`, `/redistribuciones/`, `/kpis/`, `/notificaciones/` |
| **Tracker**  | `/gps/` *(Solo POST/GET)* |

---

# 7. EJEMPLO COMPLETO — Flujo del Reponedor

```javascript
const BASE = 'https://TU-APP.onrender.com';

// 1. Obtener la ruta del día
const rutaRes = await fetch(`${BASE}/rutas/1`);
const ruta = await rutaRes.json();
// ruta.ruta_puntos → lista de paradas con PDVs

// 2. Optimizar la ruta (el backend calcula el camino más corto)
const optRes = await fetch(`${BASE}/rutas/1/optimizar`, { method: 'POST' });
const rutaOptimizada = await optRes.json();
// Ahora ruta_puntos viene en el orden óptimo

// 3. Conectar WebSocket para enviar GPS
const ws = new WebSocket(`wss://TU-APP.onrender.com/ws/reponedor/5`);

// 4. Cuando el reponedor llega a un PDV y termina
await fetch(`${BASE}/visitas/42/registrar_tiempo`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tiempo_real_min: 22 })
});

// 5. Consultar clima en la ubicación actual
const climaRes = await fetch(`${BASE}/clima/-16.5/-68.15`);
const clima = await climaRes.json();
// clima.descripcion → "Parcialmente nublado"
```

---

# 8. CÓDIGOS DE ERROR COMUNES

| Código | Significado |
|--------|-------------|
| `200` | OK — Operación exitosa |
| `201` | Created — Recurso creado exitosamente |
| `204` | No Content — Eliminado exitosamente |
| `400` | Bad Request — Datos inválidos o formato de fecha incorrecto (usar YYYY-MM-DD) |
| `404` | Not Found — Ruta, visita, pdv o recurso no encontrado |
| `500` | Internal Server Error — Error del servidor |
| `502` | Bad Gateway — Error con API externa (clima) |

**Formato de error:**
```json
{
  "detail": "PDV no encontrado"
}
```
