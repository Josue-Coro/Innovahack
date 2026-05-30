from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date, time
from typing import List, Optional

# --- ROL SCHEMAS ---
class RolBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    permisos: dict = {}
    activo: bool = True

class Rol(RolBase):
    id_rol: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DEPARTAMENTO SCHEMAS ---
class DepartamentoBase(BaseModel):
    nombre: str
    codigo_iso: Optional[str] = None
    capital: Optional[str] = None
    activo: bool = True

class Departamento(DepartamentoBase):
    id_departamento: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- CIUDAD SCHEMAS ---
class CiudadBase(BaseModel):
    id_departamento: int
    nombre: str
    latitud_centro: Optional[float] = None
    longitud_centro: Optional[float] = None
    activo: bool = True

class Ciudad(CiudadBase):
    id_ciudad: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- USUARIO SCHEMAS ---
class UsuarioBase(BaseModel):
    id_rol: int
    id_ciudad: Optional[int] = None
    nombre: str
    email: str
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None
    id_supervisor: Optional[int] = None
    activo: bool = True

class Usuario(UsuarioBase):
    id_usuario: int
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PERFIL REPONEDOR SCHEMAS ---
class PerfilReponedorBase(BaseModel):
    id_usuario: int
    tipo_vehiculo: str = "a_pie"
    capacidad_maxima_visitas_dia: int = 15
    lat_actual: Optional[float] = None
    lon_actual: Optional[float] = None
    online: bool = False
    ultima_conexion: Optional[datetime] = None

class PerfilReponedor(PerfilReponedorBase):
    id_perfil_reponedor: int
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- CATEGORIA CLIENTE SCHEMAS ---
class CategoriaClienteBase(BaseModel):
    nombre: str
    criterio_clasificacion: Optional[str] = None
    tiempo_promedio_visita_min: Optional[int] = None
    perfil_atencion: Optional[str] = None
    activo: bool = True

class CategoriaCliente(CategoriaClienteBase):
    id_categoria: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- MERCADO SCHEMAS ---
class MercadoBase(BaseModel):
    id_ciudad: int
    nombre: str
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: bool = True

class Mercado(MercadoBase):
    id_mercado: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PUNTO DE VENTA (PDV) SCHEMAS ---
class PuntoDeVentaBase(BaseModel):
    codigo_gv: str
    codigo_interno: Optional[str] = None
    nombre_pdv: Optional[str] = None
    direccion: Optional[str] = None
    id_mercado: Optional[int] = None
    id_categoria: Optional[int] = None
    id_supervisor: Optional[int] = None
    id_reponedor_asignado: Optional[int] = None
    latitud: float
    longitud: float
    tiempo_visita_min: int
    prioridad: str = "media"
    ventana_horaria_inicio: time = time(8, 0)
    ventana_horaria_fin: time = time(18, 0)
    nombre_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    notas_especiales: Optional[str] = None
    atiende_lunes: bool = False
    atiende_martes: bool = False
    atiende_miercoles: bool = False
    atiende_jueves: bool = False
    atiende_viernes: bool = False
    atiende_sabado: bool = False
    atiende_domingo: bool = False
    frecuencia_semanal: Optional[int] = None
    frecuencia_mensual: Optional[int] = None
    tiempo_promedio_min: Optional[float] = None
    recalibrar: bool = False
    activo: bool = True

class PuntoDeVenta(PuntoDeVentaBase):
    id_pdv: int
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- MICRO TAREA SCHEMAS ---
class MicroTareaBase(BaseModel):
    id_categoria: Optional[int] = None
    nombre: str
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: bool = True

class MicroTarea(MicroTareaBase):
    id_micro_tarea: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- RUTA SCHEMAS ---
class RutaBase(BaseModel):
    id_reponedor: int
    id_supervisor: Optional[int] = None
    fecha: date
    estado: str = "pendiente"
    distancia_km_estimada: Optional[float] = None
    duracion_min_estimada: Optional[int] = None
    distancia_km_real: Optional[float] = None
    duracion_min_real: Optional[int] = None
    hora_inicio_real: Optional[datetime] = None
    hora_fin_real: Optional[datetime] = None

class RutaCreate(RutaBase):
    pass

class RutaUpdate(BaseModel):
    id_reponedor: Optional[int] = None
    id_supervisor: Optional[int] = None
    fecha: Optional[date] = None
    estado: Optional[str] = None
    distancia_km_estimada: Optional[float] = None
    duracion_min_estimada: Optional[int] = None
    distancia_km_real: Optional[float] = None
    duracion_min_real: Optional[int] = None
    hora_inicio_real: Optional[datetime] = None
    hora_fin_real: Optional[datetime] = None

class Ruta(RutaBase):
    id_ruta: int
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- RUTA PUNTO SCHEMAS ---
class RutaPuntoBase(BaseModel):
    id_ruta: int
    id_pdv: int
    orden: int
    hora_estimada_llegada: Optional[time] = None
    estado: str = "pendiente"

class RutaPunto(RutaPuntoBase):
    id_ruta_punto: int
    pdv: Optional[PuntoDeVenta] = None

    model_config = ConfigDict(from_attributes=True)

class RutaWithPuntos(Ruta):
    ruta_puntos: List[RutaPunto] = []

    model_config = ConfigDict(from_attributes=True)


# --- VISITA SCHEMAS ---
class VisitaBase(BaseModel):
    id_ruta_punto: Optional[int] = None
    id_reponedor: int
    id_pdv: int
    fecha: date
    hora_llegada: Optional[datetime] = None
    hora_salida: Optional[datetime] = None
    estado: str = "pendiente"
    motivo_no_visita: Optional[str] = None
    quiebre_de_stock: bool = False
    clima_descripcion: Optional[str] = None
    temperatura_c: Optional[float] = None
    notas: Optional[str] = None
    foto_url: Optional[str] = None
    lat_registro: Optional[float] = None
    lon_registro: Optional[float] = None

class VisitaCreate(VisitaBase):
    pass

class VisitaUpdate(BaseModel):
    id_ruta_punto: Optional[int] = None
    id_reponedor: Optional[int] = None
    id_pdv: Optional[int] = None
    fecha: Optional[date] = None
    hora_llegada: Optional[datetime] = None
    hora_salida: Optional[datetime] = None
    estado: Optional[str] = None
    motivo_no_visita: Optional[str] = None
    quiebre_de_stock: Optional[bool] = None
    clima_descripcion: Optional[str] = None
    temperatura_c: Optional[float] = None
    notas: Optional[str] = None
    foto_url: Optional[str] = None
    lat_registro: Optional[float] = None
    lon_registro: Optional[float] = None

class Visita(VisitaBase):
    id_visita: int
    duracion_real_min: Optional[int] = None
    creado_en: datetime
    actualizado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- VISITA TAREA SCHEMAS ---
class VisitaTareaBase(BaseModel):
    id_visita: int
    id_micro_tarea: int
    hora_inicio: Optional[datetime] = None
    hora_fin: Optional[datetime] = None
    completada: bool = False
    notas: Optional[str] = None

class VisitaTarea(VisitaTareaBase):
    id_visita_tarea: int
    duracion_min: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# --- INCIDENCIA SCHEMAS ---
class IncidenciaBase(BaseModel):
    id_visita: Optional[int] = None
    id_reponedor: int
    id_pdv: int
    tipo: str
    descripcion: Optional[str] = None
    foto_url: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    resuelta: bool = False
    id_resuelto_por: Optional[int] = None
    resuelta_en: Optional[datetime] = None
    notas_resolucion: Optional[str] = None

class Incidencia(IncidenciaBase):
    id_incidencia: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- REDISTRIBUCION SUGERIDA SCHEMAS ---
class RedistribucionSugeridaBase(BaseModel):
    fecha_para: date
    id_reponedor_origen: Optional[int] = None
    id_reponedor_destino: Optional[int] = None
    id_pdv: int
    motivo: Optional[str] = None
    motivo_detalle: Optional[str] = None
    ahorro_tiempo_min: Optional[int] = None
    ahorro_km: Optional[float] = None
    estado: str = "pendiente"
    id_aprobado_por: Optional[int] = None
    aprobada_en: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None

class RedistribucionSugerida(RedistribucionSugeridaBase):
    id_redistribucion: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- KPI DIARIO SCHEMAS ---
class KPIDiarioBase(BaseModel):
    fecha: date
    id_reponedor: int
    id_supervisor: Optional[int] = None
    total_pdvs_asignados: int = 0
    total_pdvs_visitados: int = 0
    total_pdvs_omitidos: int = 0
    tiempo_total_campo_min: int = 0
    tiempo_total_traslado_min: int = 0
    tiempo_total_atencion_min: int = 0
    distancia_planificada_km: Optional[float] = None
    distancia_real_km: Optional[float] = None
    quiebres_stock_encontrados: int = 0
    incidencias_reportadas: int = 0
    fotos_tomadas: int = 0
    desviacion_tiempo_min: Optional[int] = None
    desviacion_km: Optional[float] = None

class KPIDiario(KPIDiarioBase):
    id_kpi: int
    porcentaje_cobertura: Optional[float] = None
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- NOTIFICACION SCHEMAS ---
class NotificacionBase(BaseModel):
    id_supervisor: Optional[int] = None
    id_reponedor: Optional[int] = None
    id_pdv: Optional[int] = None
    tipo: str
    mensaje: str
    urgencia: str = "normal"
    leida: bool = False
    leida_en: Optional[datetime] = None

class Notificacion(NotificacionBase):
    id_notificacion: int
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)


# --- DASHBOARD KPI SCHEMAS ---
class DashboardMetrics(BaseModel):
    total_rutas: int
    total_visitas: int
    visitas_completadas: int
    visitas_pendientes: int
    visitas_canceladas: int
    promedio_calificacion: float
    eficiencia_ruta_pct: float


# ======================================================
# CREATE / UPDATE SCHEMAS (para CRUDs completos)
# ======================================================

# --- ROL ---
class RolCreate(RolBase):
    pass

class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    permisos: Optional[dict] = None
    activo: Optional[bool] = None

# --- DEPARTAMENTO ---
class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoUpdate(BaseModel):
    nombre: Optional[str] = None
    codigo_iso: Optional[str] = None
    capital: Optional[str] = None
    activo: Optional[bool] = None

# --- CIUDAD ---
class CiudadCreate(CiudadBase):
    pass

class CiudadUpdate(BaseModel):
    id_departamento: Optional[int] = None
    nombre: Optional[str] = None
    latitud_centro: Optional[float] = None
    longitud_centro: Optional[float] = None
    activo: Optional[bool] = None

# --- USUARIO ---
class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioUpdate(BaseModel):
    id_rol: Optional[int] = None
    id_ciudad: Optional[int] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None
    id_supervisor: Optional[int] = None
    activo: Optional[bool] = None
    password: Optional[str] = None

# --- PERFIL REPONEDOR ---
class PerfilReponedorCreate(PerfilReponedorBase):
    pass

class PerfilReponedorUpdate(BaseModel):
    tipo_vehiculo: Optional[str] = None
    capacidad_maxima_visitas_dia: Optional[int] = None
    lat_actual: Optional[float] = None
    lon_actual: Optional[float] = None
    online: Optional[bool] = None
    ultima_conexion: Optional[datetime] = None

# --- SESION ---
class SesionBase(BaseModel):
    id_usuario: int
    token: str
    refresh_token: Optional[str] = None
    dispositivo: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expira_en: datetime

class SesionCreate(SesionBase):
    pass

class Sesion(SesionBase):
    id_sesion: int
    creado_en: datetime
    model_config = ConfigDict(from_attributes=True)

# --- CATEGORIA CLIENTE ---
class CategoriaClienteCreate(CategoriaClienteBase):
    pass

class CategoriaClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    criterio_clasificacion: Optional[str] = None
    tiempo_promedio_visita_min: Optional[int] = None
    perfil_atencion: Optional[str] = None
    activo: Optional[bool] = None

# --- MERCADO ---
class MercadoCreate(MercadoBase):
    pass

class MercadoUpdate(BaseModel):
    id_ciudad: Optional[int] = None
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    activo: Optional[bool] = None

# --- PUNTO DE VENTA ---
class PuntoDeVentaCreate(PuntoDeVentaBase):
    pass

class PuntoDeVentaUpdate(BaseModel):
    codigo_gv: Optional[str] = None
    codigo_interno: Optional[str] = None
    nombre_pdv: Optional[str] = None
    direccion: Optional[str] = None
    id_mercado: Optional[int] = None
    id_categoria: Optional[int] = None
    id_supervisor: Optional[int] = None
    id_reponedor_asignado: Optional[int] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    tiempo_visita_min: Optional[int] = None
    prioridad: Optional[str] = None
    ventana_horaria_inicio: Optional[time] = None
    ventana_horaria_fin: Optional[time] = None
    nombre_contacto: Optional[str] = None
    telefono_contacto: Optional[str] = None
    notas_especiales: Optional[str] = None
    atiende_lunes: Optional[bool] = None
    atiende_martes: Optional[bool] = None
    atiende_miercoles: Optional[bool] = None
    atiende_jueves: Optional[bool] = None
    atiende_viernes: Optional[bool] = None
    atiende_sabado: Optional[bool] = None
    atiende_domingo: Optional[bool] = None
    frecuencia_semanal: Optional[int] = None
    frecuencia_mensual: Optional[int] = None
    tiempo_promedio_min: Optional[float] = None
    recalibrar: Optional[bool] = None
    activo: Optional[bool] = None

# --- MICRO TAREA ---
class MicroTareaCreate(MicroTareaBase):
    pass

class MicroTareaUpdate(BaseModel):
    id_categoria: Optional[int] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None

# --- RUTA PUNTO ---
class RutaPuntoCreate(RutaPuntoBase):
    pass

class RutaPuntoUpdate(BaseModel):
    id_pdv: Optional[int] = None
    orden: Optional[int] = None
    hora_estimada_llegada: Optional[time] = None
    estado: Optional[str] = None

# --- VISITA TAREA ---
class VisitaTareaCreate(VisitaTareaBase):
    pass

class VisitaTareaUpdate(BaseModel):
    hora_inicio: Optional[datetime] = None
    hora_fin: Optional[datetime] = None
    completada: Optional[bool] = None
    notas: Optional[str] = None

# --- POSICION GPS ---
class PosicionGPSBase(BaseModel):
    id_reponedor: int
    latitud: float
    longitud: float
    precision_m: Optional[float] = None
    velocidad_kmh: Optional[float] = None

class PosicionGPSCreate(PosicionGPSBase):
    pass

class PosicionGPS(PosicionGPSBase):
    id_posicion: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# --- INCIDENCIA ---
class IncidenciaCreate(IncidenciaBase):
    pass

class IncidenciaUpdate(BaseModel):
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    foto_url: Optional[str] = None
    resuelta: Optional[bool] = None
    id_resuelto_por: Optional[int] = None
    resuelta_en: Optional[datetime] = None
    notas_resolucion: Optional[str] = None

# --- HISTORIAL TIEMPOS PDV ---
class HistorialTiempoPDVBase(BaseModel):
    id_pdv: int
    id_categoria: Optional[int] = None
    id_reponedor: int
    fecha: date
    dia_semana: Optional[int] = None
    tiempo_real_min: int
    tiempo_estimado_min: Optional[int] = None
    clima: Optional[str] = None
    habia_quiebre: bool = False

class HistorialTiempoPDVCreate(HistorialTiempoPDVBase):
    pass

class HistorialTiempoPDV(HistorialTiempoPDVBase):
    id_historial: int
    diferencia_min: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# --- REDISTRIBUCION SUGERIDA ---
class RedistribucionSugeridaCreate(RedistribucionSugeridaBase):
    pass

class RedistribucionSugeridaUpdate(BaseModel):
    estado: Optional[str] = None
    id_aprobado_por: Optional[int] = None
    aprobada_en: Optional[datetime] = None
    motivo_rechazo: Optional[str] = None

# --- KPI DIARIO ---
class KPIDiarioCreate(KPIDiarioBase):
    pass

class KPIDiarioUpdate(BaseModel):
    total_pdvs_asignados: Optional[int] = None
    total_pdvs_visitados: Optional[int] = None
    total_pdvs_omitidos: Optional[int] = None
    tiempo_total_campo_min: Optional[int] = None
    tiempo_total_traslado_min: Optional[int] = None
    tiempo_total_atencion_min: Optional[int] = None
    distancia_planificada_km: Optional[float] = None
    distancia_real_km: Optional[float] = None
    quiebres_stock_encontrados: Optional[int] = None
    incidencias_reportadas: Optional[int] = None
    fotos_tomadas: Optional[int] = None
    desviacion_tiempo_min: Optional[int] = None
    desviacion_km: Optional[float] = None

# --- NOTIFICACION ---
class NotificacionCreate(NotificacionBase):
    pass

class NotificacionUpdate(BaseModel):
    leida: Optional[bool] = None
    leida_en: Optional[datetime] = None

# --- AUDIT LOG ---
class AuditLogBase(BaseModel):
    id_usuario: Optional[int] = None
    accion: str
    tabla_afectada: Optional[str] = None
    registro_id: Optional[int] = None
    datos_anteriores: Optional[dict] = None
    datos_nuevos: Optional[dict] = None
    ip_address: Optional[str] = None

class AuditLog(AuditLogBase):
    id_audit: int
    creado_en: datetime
    model_config = ConfigDict(from_attributes=True)

# --- LOGIN (AUTH) ---
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    usuario: Usuario
    rol: Optional[str] = None

class LogoutRequest(BaseModel):
    token: str

# --- GPS TRACKING ---
class GPSLocationCreate(BaseModel):
    latitud: float
    longitud: float
    precision_m: Optional[float] = None
    velocidad_kmh: Optional[float] = None
    nivel_bateria: Optional[int] = None
    timestamp: Optional[datetime] = None

class GPSLocationResponse(BaseModel):
    latitud: float
    longitud: float
    velocidad_kmh: Optional[float] = None
    nivel_bateria: Optional[int] = None
    timestamp: datetime
    fecha_formateada: str

    class Config:
        from_attributes = True

class ReponedorUltimaUbicacion(BaseModel):
    id_usuario: int
    nombre: str
    lat_actual: Optional[float] = None
    lon_actual: Optional[float] = None
    bateria_actual: Optional[int] = None
    online: bool
    ultima_conexion: Optional[datetime] = None

    class Config:
        from_attributes = True
