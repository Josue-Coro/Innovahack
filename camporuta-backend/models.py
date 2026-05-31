from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Time, ForeignKey, JSON, DateTime, Numeric, FetchedValue
from sqlalchemy.orm import relationship, backref
from database import Base
from datetime import datetime

class Rol(Base):
    __tablename__ = "roles"

    id_rol = Column(Integer, primary_key=True)
    nombre = Column(String(30), unique=True, nullable=False)
    descripcion = Column(String)
    permisos = Column(JSON, default=dict)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="rol")


class Departamento(Base):
    __tablename__ = "departamentos"

    id_departamento = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    codigo_iso = Column(String(5))
    capital = Column(String(80))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    ciudades = relationship("Ciudad", back_populates="departamento")


class Ciudad(Base):
    __tablename__ = "ciudades"

    id_ciudad = Column(Integer, primary_key=True)
    id_departamento = Column(Integer, ForeignKey("departamentos.id_departamento"), nullable=False)
    nombre = Column(String(100), nullable=False)
    latitud_centro = Column(Numeric(10, 8))
    longitud_centro = Column(Numeric(11, 8))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    departamento = relationship("Departamento", back_populates="ciudades")
    usuarios = relationship("Usuario", back_populates="ciudad")
    mercados = relationship("Mercado", back_populates="ciudad")


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True)
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=False)
    id_ciudad = Column(Integer, ForeignKey("ciudades.id_ciudad"))
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(20))
    avatar_url = Column(String(500))
    id_supervisor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    ciudad = relationship("Ciudad", back_populates="usuarios")
    
    # Self-referential relationship for supervisor hierarchy
    supervisor = relationship("Usuario", remote_side=[id_usuario], backref="reponedores")
    
    perfil_reponedor = relationship("PerfilReponedor", uselist=False, back_populates="usuario")
    sesiones = relationship("Sesion", back_populates="usuario", cascade="all, delete-orphan")


class PerfilReponedor(Base):
    __tablename__ = "perfiles_reponedor"

    id_perfil_reponedor = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), unique=True, nullable=False)
    tipo_vehiculo = Column(String(30), default="a_pie")
    capacidad_maxima_visitas_dia = Column(Integer, default=15)
    lat_actual = Column(Numeric(10, 8))
    lon_actual = Column(Numeric(11, 8))
    online = Column(Boolean, default=False)
    bateria_actual = Column(Integer)
    ultima_conexion = Column(DateTime)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="perfil_reponedor")


class Sesion(Base):
    __tablename__ = "sesiones"

    id_sesion = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)
    refresh_token = Column(String(500), unique=True)
    dispositivo = Column(String(100))
    ip_address = Column(String(45))
    user_agent = Column(String)
    expira_en = Column(DateTime, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="sesiones")


class CategoriaCliente(Base):
    __tablename__ = "categorias_cliente"

    id_categoria = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    criterio_clasificacion = Column(String(200))
    tiempo_promedio_visita_min = Column(Integer)
    perfil_atencion = Column(String)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    puntos_de_venta = relationship("PuntoDeVenta", back_populates="categoria")
    micro_tareas = relationship("MicroTarea", back_populates="categoria")


class Mercado(Base):
    __tablename__ = "mercados"

    id_mercado = Column(Integer, primary_key=True)
    id_ciudad = Column(Integer, ForeignKey("ciudades.id_ciudad"), nullable=False)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(200))
    latitud = Column(Numeric(10, 8))
    longitud = Column(Numeric(11, 8))
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    ciudad = relationship("Ciudad", back_populates="mercados")
    puntos_de_venta = relationship("PuntoDeVenta", back_populates="mercado")


class PuntoDeVenta(Base):
    __tablename__ = "puntos_de_venta"

    id_pdv = Column(Integer, primary_key=True)
    codigo_gv = Column(String(20), unique=True, nullable=False)
    codigo_interno = Column(String(50))
    nombre_pdv = Column(String(150))
    direccion = Column(String(250))
    id_mercado = Column(Integer, ForeignKey("mercados.id_mercado"))
    id_categoria = Column(Integer, ForeignKey("categorias_cliente.id_categoria"))
    id_supervisor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_reponedor_asignado = Column(Integer, ForeignKey("usuarios.id_usuario"))
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    tiempo_visita_min = Column(Integer, nullable=False)
    prioridad = Column(String(10), default="media")
    ventana_horaria_inicio = Column(Time, default="08:00")
    ventana_horaria_fin = Column(Time, default="18:00")
    nombre_contacto = Column(String(100))
    telefono_contacto = Column(String(20))
    notas_especiales = Column(String)
    atiende_lunes = Column(Boolean, default=False)
    atiende_martes = Column(Boolean, default=False)
    atiende_miercoles = Column(Boolean, default=False)
    atiende_jueves = Column(Boolean, default=False)
    atiende_viernes = Column(Boolean, default=False)
    atiende_sabado = Column(Boolean, default=False)
    atiende_domingo = Column(Boolean, default=False)
    frecuencia_semanal = Column(Integer)
    frecuencia_mensual = Column(Integer)
    
    # Adiciones para el loop de feedback
    tiempo_promedio_min = Column(Float)
    recalibrar = Column(Boolean, default=False, nullable=False)
    
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mercado = relationship("Mercado", back_populates="puntos_de_venta")
    categoria = relationship("CategoriaCliente", back_populates="puntos_de_venta")
    supervisor_rel = relationship("Usuario", foreign_keys=[id_supervisor])
    reponedor_rel = relationship("Usuario", foreign_keys=[id_reponedor_asignado])
    ruta_puntos = relationship("RutaPunto", back_populates="pdv", cascade="all, delete-orphan")
    visitas = relationship("Visita", back_populates="pdv", cascade="all, delete-orphan")


class MicroTarea(Base):
    __tablename__ = "micro_tareas"

    id_micro_tarea = Column(Integer, primary_key=True)
    id_categoria = Column(Integer, ForeignKey("categorias_cliente.id_categoria"))
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String)
    orden = Column(Integer)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    categoria = relationship("CategoriaCliente", back_populates="micro_tareas")
    visita_tareas = relationship("VisitaTarea", back_populates="micro_tarea", cascade="all, delete-orphan")


class Ruta(Base):
    __tablename__ = "rutas"

    id_ruta = Column(Integer, primary_key=True)
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_supervisor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    fecha = Column(Date, nullable=False)
    estado = Column(String(30), default="pendiente")
    distancia_km_estimada = Column(Numeric(8, 2))
    duracion_min_estimada = Column(Integer)
    distancia_km_real = Column(Numeric(8, 2))
    duracion_min_real = Column(Integer)
    hora_inicio_real = Column(DateTime)
    hora_fin_real = Column(DateTime)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    supervisor = relationship("Usuario", foreign_keys=[id_supervisor])
    ruta_puntos = relationship("RutaPunto", back_populates="ruta", cascade="all, delete-orphan")


class RutaPunto(Base):
    __tablename__ = "ruta_puntos"

    id_ruta_punto = Column(Integer, primary_key=True)
    id_ruta = Column(Integer, ForeignKey("rutas.id_ruta", ondelete="CASCADE"), nullable=False)
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"), nullable=False)
    orden = Column(Integer, nullable=False)
    hora_estimada_llegada = Column(Time)
    estado = Column(String(30), default="pendiente")

    ruta = relationship("Ruta", back_populates="ruta_puntos")
    pdv = relationship("PuntoDeVenta", back_populates="ruta_puntos")
    visitas = relationship("Visita", back_populates="ruta_punto", cascade="all, delete-orphan")


class Visita(Base):
    __tablename__ = "visitas"

    id_visita = Column(Integer, primary_key=True)
    id_ruta_punto = Column(Integer, ForeignKey("ruta_puntos.id_ruta_punto"))
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"), nullable=False)
    fecha = Column(Date, nullable=False)
    hora_llegada = Column(DateTime)
    hora_salida = Column(DateTime)
    
    # Generated column read-only from Python
    duracion_real_min = Column(Integer, server_default=FetchedValue())
    
    estado = Column(String(30), default="pendiente")
    motivo_no_visita = Column(String(100))
    quiebre_de_stock = Column(Boolean, default=False)
    clima_descripcion = Column(String(50))
    temperatura_c = Column(Numeric(4, 1))
    notas = Column(String)
    foto_url = Column(String(500))
    lat_registro = Column(Float)
    lon_registro = Column(Float)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ruta_punto = relationship("RutaPunto", back_populates="visitas")
    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    pdv = relationship("PuntoDeVenta", back_populates="visitas")
    visita_tareas = relationship("VisitaTarea", back_populates="visita", cascade="all, delete-orphan")
    incidencias = relationship("Incidencia", back_populates="visita", cascade="all, delete-orphan")


class VisitaTarea(Base):
    __tablename__ = "visita_tareas"

    id_visita_tarea = Column(Integer, primary_key=True)
    id_visita = Column(Integer, ForeignKey("visitas.id_visita", ondelete="CASCADE"), nullable=False)
    id_micro_tarea = Column(Integer, ForeignKey("micro_tareas.id_micro_tarea"), nullable=False)
    hora_inicio = Column(DateTime)
    hora_fin = Column(DateTime)
    duracion_min = Column(Integer, server_default=FetchedValue())
    completada = Column(Boolean, default=False)
    notas = Column(String)

    visita = relationship("Visita", back_populates="visita_tareas")
    micro_tarea = relationship("MicroTarea", back_populates="visita_tareas")


class PosicionGPS(Base):
    __tablename__ = "posiciones_gps"

    id_posicion = Column(Integer, primary_key=True)
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    precision_m = Column(Numeric(6, 1))
    velocidad_kmh = Column(Numeric(5, 1))
    nivel_bateria = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    
    @property
    def fecha_formateada(self):
        if not self.timestamp:
            return None
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        dt = self.timestamp
        dia_semana = dias[dt.weekday()]
        hora_12 = dt.strftime("%I:%M").lstrip("0")
        if not hora_12: hora_12 = "12:00"
        am_pm = "p.m." if dt.hour >= 12 else "a.m."
        return f"{hora_12} {am_pm} {dia_semana}, {dt.day} de {meses[dt.month]} de {dt.year} (GMT-4) Hora en Bolivia"


class Incidencia(Base):
    __tablename__ = "incidencias"

    id_incidencia = Column(Integer, primary_key=True)
    id_visita = Column(Integer, ForeignKey("visitas.id_visita"))
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"), nullable=False)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(String)
    foto_url = Column(String(500))
    latitud = Column(Float)
    longitud = Column(Float)
    resuelta = Column(Boolean, default=False)
    id_resuelto_por = Column(Integer, ForeignKey("usuarios.id_usuario"))
    resuelta_en = Column(DateTime)
    notas_resolucion = Column(String)
    creado_en = Column(DateTime, default=datetime.utcnow)

    visita = relationship("Visita", back_populates="incidencias")
    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    pdv = relationship("PuntoDeVenta", foreign_keys=[id_pdv])
    resuelto_por = relationship("Usuario", foreign_keys=[id_resuelto_por])


class HistorialTiempoPDV(Base):
    __tablename__ = "historial_tiempos_pdv"

    id_historial = Column(Integer, primary_key=True)
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"), nullable=False)
    id_categoria = Column(Integer, ForeignKey("categorias_cliente.id_categoria"))
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha = Column(Date, nullable=False)
    dia_semana = Column(Integer)
    tiempo_real_min = Column(Integer, nullable=False)
    tiempo_estimado_min = Column(Integer)
    diferencia_min = Column(Integer, server_default=FetchedValue())
    clima = Column(String(50))
    habia_quiebre = Column(Boolean, default=False)

    pdv = relationship("PuntoDeVenta")
    categoria = relationship("CategoriaCliente")
    reponedor = relationship("Usuario")


class RedistribucionSugerida(Base):
    __tablename__ = "redistribuciones_sugeridas"

    id_redistribucion = Column(Integer, primary_key=True)
    fecha_para = Column(Date, nullable=False)
    id_reponedor_origen = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_reponedor_destino = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"), nullable=False)
    motivo = Column(String(50))
    motivo_detalle = Column(String)
    ahorro_tiempo_min = Column(Integer)
    ahorro_km = Column(Numeric(6, 2))
    estado = Column(String(30), default="pendiente")
    id_aprobado_por = Column(Integer, ForeignKey("usuarios.id_usuario"))
    aprobada_en = Column(DateTime)
    motivo_rechazo = Column(String)
    creado_en = Column(DateTime, default=datetime.utcnow)

    reponedor_origen = relationship("Usuario", foreign_keys=[id_reponedor_origen])
    reponedor_destino = relationship("Usuario", foreign_keys=[id_reponedor_destino])
    pdv = relationship("PuntoDeVenta")
    aprobado_por = relationship("Usuario", foreign_keys=[id_aprobado_por])


class KPIDiario(Base):
    __tablename__ = "kpis_diarios"

    id_kpi = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_supervisor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    total_pdvs_asignados = Column(Integer, default=0)
    total_pdvs_visitados = Column(Integer, default=0)
    total_pdvs_omitidos = Column(Integer, default=0)
    porcentaje_cobertura = Column(Numeric(5, 2), server_default=FetchedValue())
    tiempo_total_campo_min = Column(Integer, default=0)
    tiempo_total_traslado_min = Column(Integer, default=0)
    tiempo_total_atencion_min = Column(Integer, default=0)
    distancia_planificada_km = Column(Numeric(8, 2))
    distancia_real_km = Column(Numeric(8, 2))
    quiebres_stock_encontrados = Column(Integer, default=0)
    incidencias_reportadas = Column(Integer, default=0)
    fotos_tomadas = Column(Integer, default=0)
    desviacion_tiempo_min = Column(Integer)
    desviacion_km = Column(Numeric(6, 2))
    creado_en = Column(DateTime, default=datetime.utcnow)

    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    supervisor = relationship("Usuario", foreign_keys=[id_supervisor])


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id_notificacion = Column(Integer, primary_key=True)
    id_supervisor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_reponedor = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_pdv = Column(Integer, ForeignKey("puntos_de_venta.id_pdv"))
    tipo = Column(String(50), nullable=False)
    mensaje = Column(String, nullable=False)
    urgencia = Column(String(20), default="normal")
    leida = Column(Boolean, default=False)
    leida_en = Column(DateTime)
    creado_en = Column(DateTime, default=datetime.utcnow)

    supervisor = relationship("Usuario", foreign_keys=[id_supervisor])
    reponedor = relationship("Usuario", foreign_keys=[id_reponedor])
    pdv = relationship("PuntoDeVenta")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id_audit = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    accion = Column(String(20), nullable=False)
    tabla_afectada = Column(String(100))
    registro_id = Column(Integer)
    datos_anteriores = Column(JSON)
    datos_nuevos = Column(JSON)
    ip_address = Column(String(45))
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")
