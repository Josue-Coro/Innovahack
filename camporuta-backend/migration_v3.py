import os
import sys
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine

DDL_SQL = """
-- Extensiones
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Roles
CREATE TABLE roles (
    id_rol        SERIAL PRIMARY KEY,
    nombre        VARCHAR(30) UNIQUE NOT NULL,
    descripcion   TEXT,
    permisos      JSONB DEFAULT '{}',
    activo        BOOLEAN DEFAULT TRUE,
    creado_en     TIMESTAMP DEFAULT NOW()
);

-- 2. Departamentos
CREATE TABLE departamentos (
    id_departamento  SERIAL PRIMARY KEY,
    nombre           VARCHAR(50) UNIQUE NOT NULL,
    codigo_iso       VARCHAR(5),
    capital          VARCHAR(80),
    activo           BOOLEAN DEFAULT TRUE,
    creado_en        TIMESTAMP DEFAULT NOW()
);

-- 3. Ciudades
CREATE TABLE ciudades (
    id_ciudad        SERIAL PRIMARY KEY,
    id_departamento  INT NOT NULL REFERENCES departamentos(id_departamento),
    nombre           VARCHAR(100) NOT NULL,
    latitud_centro   DECIMAL(10,8),
    longitud_centro  DECIMAL(11,8),
    activo           BOOLEAN DEFAULT TRUE,
    creado_en        TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_departamento, nombre)
);

CREATE INDEX idx_ciudades_depto ON ciudades(id_departamento);

-- 4. Usuarios
CREATE TABLE usuarios (
    id_usuario     SERIAL PRIMARY KEY,
    id_rol         INT NOT NULL REFERENCES roles(id_rol),
    id_ciudad      INT REFERENCES ciudades(id_ciudad),
    nombre         VARCHAR(100) NOT NULL,
    email          VARCHAR(150) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    telefono       VARCHAR(20),
    avatar_url     VARCHAR(500),
    id_supervisor  INT REFERENCES usuarios(id_usuario),
    activo         BOOLEAN DEFAULT TRUE,
    creado_en      TIMESTAMP DEFAULT NOW(),
    actualizado_en TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_usuarios_rol        ON usuarios(id_rol);
CREATE INDEX idx_usuarios_supervisor  ON usuarios(id_supervisor);
CREATE INDEX idx_usuarios_ciudad      ON usuarios(id_ciudad);

-- 5. Perfiles Reponedor
CREATE TABLE perfiles_reponedor (
    id_perfil_reponedor       SERIAL PRIMARY KEY,
    id_usuario                INT UNIQUE NOT NULL REFERENCES usuarios(id_usuario),
    tipo_vehiculo             VARCHAR(30) DEFAULT 'a_pie' CHECK (tipo_vehiculo IN ('a_pie','moto','auto','bicicleta')),
    capacidad_maxima_visitas_dia INT DEFAULT 15,
    lat_actual                DECIMAL(10,8),
    lon_actual                DECIMAL(11,8),
    online                    BOOLEAN DEFAULT FALSE,
    ultima_conexion           TIMESTAMP,
    creado_en                 TIMESTAMP DEFAULT NOW(),
    actualizado_en            TIMESTAMP DEFAULT NOW()
);

-- 6. Sesiones
CREATE TABLE sesiones (
    id_sesion       SERIAL PRIMARY KEY,
    id_usuario      INT NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    token           VARCHAR(500) UNIQUE NOT NULL,
    refresh_token   VARCHAR(500) UNIQUE,
    dispositivo     VARCHAR(100),
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    expira_en       TIMESTAMP NOT NULL,
    creado_en       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sesiones_usuario ON sesiones(id_usuario);
CREATE INDEX idx_sesiones_expira  ON sesiones(expira_en);

-- 7. Categorias Cliente
CREATE TABLE categorias_cliente (
    id_categoria                SERIAL PRIMARY KEY,
    nombre                      VARCHAR(50) UNIQUE NOT NULL,
    criterio_clasificacion      VARCHAR(200),
    tiempo_promedio_visita_min  INT,
    perfil_atencion             TEXT,
    activo                      BOOLEAN DEFAULT TRUE,
    creado_en                   TIMESTAMP DEFAULT NOW()
);

-- 8. Mercados
CREATE TABLE mercados (
    id_mercado    SERIAL PRIMARY KEY,
    id_ciudad     INT NOT NULL REFERENCES ciudades(id_ciudad),
    nombre        VARCHAR(100) NOT NULL,
    direccion     VARCHAR(200),
    latitud       DECIMAL(10,8),
    longitud      DECIMAL(11,8),
    activo        BOOLEAN DEFAULT TRUE,
    creado_en     TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_ciudad, nombre)
);

CREATE INDEX idx_mercados_ciudad ON mercados(id_ciudad);

-- 9. Puntos de Venta
CREATE TABLE puntos_de_venta (
    id_pdv                 SERIAL PRIMARY KEY,
    codigo_gv              VARCHAR(20) UNIQUE NOT NULL,
    codigo_interno         VARCHAR(50),
    nombre_pdv             VARCHAR(150),
    direccion              VARCHAR(250),
    id_mercado             INT REFERENCES mercados(id_mercado),
    id_categoria           INT REFERENCES categorias_cliente(id_categoria),
    id_supervisor          INT REFERENCES usuarios(id_usuario),
    id_reponedor_asignado  INT REFERENCES usuarios(id_usuario),
    latitud                DECIMAL(10,8) NOT NULL,
    longitud               DECIMAL(11,8) NOT NULL,
    tiempo_visita_min      INT NOT NULL,
    prioridad              VARCHAR(10) DEFAULT 'media' CHECK (prioridad IN ('alta','media','baja')),
    ventana_horaria_inicio TIME DEFAULT '08:00',
    ventana_horaria_fin    TIME DEFAULT '18:00',
    nombre_contacto        VARCHAR(100),
    telefono_contacto      VARCHAR(20),
    notas_especiales       TEXT,
    atiende_lunes          BOOLEAN DEFAULT FALSE,
    atiende_martes         BOOLEAN DEFAULT FALSE,
    atiende_miercoles      BOOLEAN DEFAULT FALSE,
    atiende_jueves         BOOLEAN DEFAULT FALSE,
    atiende_viernes        BOOLEAN DEFAULT FALSE,
    atiende_sabado         BOOLEAN DEFAULT FALSE,
    atiende_domingo        BOOLEAN DEFAULT FALSE,
    frecuencia_semanal     INT,
    frecuencia_mensual     INT,
    tiempo_promedio_min    DECIMAL(6,2),
    recalibrar             BOOLEAN DEFAULT FALSE,
    activo                 BOOLEAN DEFAULT TRUE,
    creado_en              TIMESTAMP DEFAULT NOW(),
    actualizado_en         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pdv_ubicacion    ON puntos_de_venta(latitud, longitud);
CREATE INDEX idx_pdv_categoria    ON puntos_de_venta(id_categoria);
CREATE INDEX idx_pdv_reponedor    ON puntos_de_venta(id_reponedor_asignado);
CREATE INDEX idx_pdv_mercado      ON puntos_de_venta(id_mercado);
CREATE INDEX idx_pdv_supervisor   ON puntos_de_venta(id_supervisor);

-- 10. Micro-Tareas
CREATE TABLE micro_tareas (
    id_micro_tarea  SERIAL PRIMARY KEY,
    id_categoria    INT REFERENCES categorias_cliente(id_categoria),
    nombre          VARCHAR(150) NOT NULL,
    descripcion     TEXT,
    orden           INT,
    activo          BOOLEAN DEFAULT TRUE,
    creado_en       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_micro_tareas_cat ON micro_tareas(id_categoria);

-- 11. Rutas
CREATE TABLE rutas (
    id_ruta                SERIAL PRIMARY KEY,
    id_reponedor           INT NOT NULL REFERENCES usuarios(id_usuario),
    id_supervisor          INT REFERENCES usuarios(id_usuario),
    fecha                  DATE NOT NULL,
    estado                 VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_curso','completada','cancelada')),
    distancia_km_estimada  DECIMAL(8,2),
    duracion_min_estimada  INT,
    distancia_km_real      DECIMAL(8,2),
    duracion_min_real      INT,
    hora_inicio_real       TIMESTAMP,
    hora_fin_real          TIMESTAMP,
    creado_en              TIMESTAMP DEFAULT NOW(),
    actualizado_en         TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_reponedor, fecha)
);

CREATE INDEX idx_rutas_reponedor ON rutas(id_reponedor);
CREATE INDEX idx_rutas_fecha     ON rutas(fecha);
CREATE INDEX idx_rutas_estado    ON rutas(estado);

-- 12. Ruta Puntos
CREATE TABLE ruta_puntos (
    id_ruta_punto           SERIAL PRIMARY KEY,
    id_ruta                 INT NOT NULL REFERENCES rutas(id_ruta) ON DELETE CASCADE,
    id_pdv                  INT NOT NULL REFERENCES puntos_de_venta(id_pdv),
    orden                   INT NOT NULL,
    hora_estimada_llegada   TIME,
    estado                  VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_curso','completada','omitida'))
);

CREATE INDEX idx_ruta_puntos_ruta ON ruta_puntos(id_ruta);

-- 13. Visitas
CREATE TABLE visitas (
    id_visita           SERIAL PRIMARY KEY,
    id_ruta_punto       INT REFERENCES ruta_puntos(id_ruta_punto),
    id_reponedor        INT NOT NULL REFERENCES usuarios(id_usuario),
    id_pdv              INT NOT NULL REFERENCES puntos_de_venta(id_pdv),
    fecha               DATE NOT NULL,
    hora_llegada        TIMESTAMP,
    hora_salida         TIMESTAMP,
    duracion_real_min   INT GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (hora_salida - hora_llegada)) / 60) STORED,
    estado              VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN ('pendiente','en_curso','completada','no_visitada')),
    motivo_no_visita    VARCHAR(100) CHECK (motivo_no_visita IS NULL OR motivo_no_visita IN ('cerrado','sin_tiempo','acceso_bloqueado','reagendado','otro')),
    quiebre_de_stock    BOOLEAN DEFAULT FALSE,
    clima_descripcion   VARCHAR(50),
    temperatura_c       DECIMAL(4,1),
    notas               TEXT,
    foto_url            VARCHAR(500),
    lat_registro        DECIMAL(10,8),
    lon_registro        DECIMAL(11,8),
    creado_en           TIMESTAMP DEFAULT NOW(),
    actualizado_en      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_visitas_fecha      ON visitas(fecha);
CREATE INDEX idx_visitas_reponedor  ON visitas(id_reponedor);
CREATE INDEX idx_visitas_pdv        ON visitas(id_pdv);
CREATE INDEX idx_visitas_estado     ON visitas(estado);

-- 14. Visita Tareas
CREATE TABLE visita_tareas (
    id_visita_tarea  SERIAL PRIMARY KEY,
    id_visita        INT NOT NULL REFERENCES visitas(id_visita) ON DELETE CASCADE,
    id_micro_tarea   INT NOT NULL REFERENCES micro_tareas(id_micro_tarea),
    hora_inicio      TIMESTAMP,
    hora_fin         TIMESTAMP,
    duracion_min     INT GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (hora_fin - hora_inicio)) / 60) STORED,
    completada       BOOLEAN DEFAULT FALSE,
    notas            TEXT
);

CREATE INDEX idx_visita_tareas_visita ON visita_tareas(id_visita);

-- 15. Posiciones GPS
CREATE TABLE posiciones_gps (
    id_posicion   SERIAL PRIMARY KEY,
    id_reponedor  INT NOT NULL REFERENCES usuarios(id_usuario),
    latitud       DECIMAL(10,8) NOT NULL,
    longitud      DECIMAL(11,8) NOT NULL,
    precision_m   DECIMAL(6,1),
    velocidad_kmh DECIMAL(5,1),
    timestamp     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gps_reponedor ON posiciones_gps(id_reponedor);
CREATE INDEX idx_gps_timestamp ON posiciones_gps(timestamp);

-- 16. Incidencias
CREATE TABLE incidencias (
    id_incidencia   SERIAL PRIMARY KEY,
    id_visita       INT REFERENCES visitas(id_visita),
    id_reponedor    INT NOT NULL REFERENCES usuarios(id_usuario),
    id_pdv          INT NOT NULL REFERENCES puntos_de_venta(id_pdv),
    tipo            VARCHAR(50) NOT NULL CHECK (tipo IN ('quiebre_stock','cliente_cerrado','acceso_bloqueado','producto_danado','problema_exhibidor','otro')),
    descripcion     TEXT,
    foto_url        VARCHAR(500),
    latitud         DECIMAL(10,8),
    longitud        DECIMAL(11,8),
    resuelta        BOOLEAN DEFAULT FALSE,
    id_resuelto_por INT REFERENCES usuarios(id_usuario),
    resuelta_en     TIMESTAMP,
    notas_resolucion TEXT,
    creado_en       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_incidencias_tipo     ON incidencias(tipo);
CREATE INDEX idx_incidencias_resuelta ON incidencias(resuelta);
CREATE INDEX idx_incidencias_pdv      ON incidencias(id_pdv);

-- 17. Historial Tiempos PDV
CREATE TABLE historial_tiempos_pdv (
    id_historial        SERIAL PRIMARY KEY,
    id_pdv              INT NOT NULL REFERENCES puntos_de_venta(id_pdv),
    id_categoria        INT REFERENCES categorias_cliente(id_categoria),
    id_reponedor        INT NOT NULL REFERENCES usuarios(id_usuario),
    fecha               DATE NOT NULL,
    dia_semana          INT CHECK (dia_semana BETWEEN 1 AND 7),
    tiempo_real_min     INT NOT NULL,
    tiempo_estimado_min INT,
    diferencia_min      INT GENERATED ALWAYS AS (tiempo_real_min - tiempo_estimado_min) STORED,
    clima               VARCHAR(50),
    habia_quiebre       BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_historial_pdv       ON historial_tiempos_pdv(id_pdv);
CREATE INDEX idx_historial_fecha     ON historial_tiempos_pdv(fecha);
CREATE INDEX idx_historial_dia       ON historial_tiempos_pdv(dia_semana);
CREATE INDEX idx_historial_categoria ON historial_tiempos_pdv(id_categoria);

-- 18. Redistribuciones Sugeridas
CREATE TABLE redistribuciones_sugeridas (
    id_redistribucion      SERIAL PRIMARY KEY,
    fecha_para             DATE NOT NULL,
    id_reponedor_origen    INT REFERENCES usuarios(id_usuario),
    id_reponedor_destino   INT REFERENCES usuarios(id_usuario),
    id_pdv                 INT NOT NULL REFERENCES puntos_de_venta(id_pdv),
    motivo                 VARCHAR(50) CHECK (motivo IN ('sobrecarga_tiempo','salto_geografico','ausencia_reponedor','optimizacion','otro')),
    motivo_detalle         TEXT,
    ahorro_tiempo_min      INT,
    ahorro_km              DECIMAL(6,2),
    estado                 VARCHAR(30) DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobada','rechazada')),
    id_aprobado_por        INT REFERENCES usuarios(id_usuario),
    aprobada_en            TIMESTAMP,
    motivo_rechazo         TEXT,
    creado_en              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_redistrib_fecha  ON redistribuciones_sugeridas(fecha_para);
CREATE INDEX idx_redistrib_estado ON redistribuciones_sugeridas(estado);

-- 19. KPIs Diarios
CREATE TABLE kpis_diarios (
    id_kpi                       SERIAL PRIMARY KEY,
    fecha                        DATE NOT NULL,
    id_reponedor                 INT NOT NULL REFERENCES usuarios(id_usuario),
    id_supervisor                INT REFERENCES usuarios(id_usuario),
    total_pdvs_asignados         INT DEFAULT 0,
    total_pdvs_visitados         INT DEFAULT 0,
    total_pdvs_omitidos          INT DEFAULT 0,
    porcentaje_cobertura         DECIMAL(5,2) GENERATED ALWAYS AS (
                                     CASE WHEN total_pdvs_asignados > 0
                                     THEN ROUND(total_pdvs_visitados * 100.0 / total_pdvs_asignados, 2)
                                     ELSE 0 END
                                 ) STORED,
    tiempo_total_campo_min       INT DEFAULT 0,
    tiempo_total_traslado_min    INT DEFAULT 0,
    tiempo_total_atencion_min    INT DEFAULT 0,
    distancia_planificada_km     DECIMAL(8,2),
    distancia_real_km            DECIMAL(8,2),
    quiebres_stock_encontrados   INT DEFAULT 0,
    incidencias_reportadas       INT DEFAULT 0,
    fotos_tomadas                INT DEFAULT 0,
    desviacion_tiempo_min        INT,
    desviacion_km                DECIMAL(6,2),
    creado_en                    TIMESTAMP DEFAULT NOW(),
    UNIQUE(id_reponedor, fecha)
);

CREATE INDEX idx_kpis_fecha       ON kpis_diarios(fecha);
CREATE INDEX idx_kpis_reponedor   ON kpis_diarios(id_reponedor);
CREATE INDEX idx_kpis_supervisor  ON kpis_diarios(id_supervisor);

-- 20. Notificaciones
CREATE TABLE notificaciones (
    id_notificacion  SERIAL PRIMARY KEY,
    id_supervisor    INT REFERENCES usuarios(id_usuario),
    id_reponedor     INT REFERENCES usuarios(id_usuario),
    id_pdv           INT REFERENCES puntos_de_venta(id_pdv),
    tipo             VARCHAR(50) NOT NULL CHECK (tipo IN ('retraso','sin_movimiento','pdv_omitido','quiebre_stock','incidencia','ruta_completada','redistribucion_pendiente','sistema')),
    mensaje          TEXT NOT NULL,
    urgencia         VARCHAR(20) DEFAULT 'normal' CHECK (urgencia IN ('baja','normal','alta','critica')),
    leida            BOOLEAN DEFAULT FALSE,
    leida_en         TIMESTAMP,
    creado_en        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notif_supervisor ON notificaciones(id_supervisor);
CREATE INDEX idx_notif_leida      ON notificaciones(leida);
CREATE INDEX idx_notif_urgencia   ON notificaciones(urgencia);
CREATE INDEX idx_notif_creado     ON notificaciones(creado_en DESC);

-- 21. Log de Auditoría
CREATE TABLE audit_log (
    id_audit         SERIAL PRIMARY KEY,
    id_usuario       INT REFERENCES usuarios(id_usuario),
    accion           VARCHAR(20) NOT NULL CHECK (accion IN ('INSERT','UPDATE','DELETE','LOGIN','LOGOUT')),
    tabla_afectada   VARCHAR(100),
    registro_id      INT,
    datos_anteriores JSONB,
    datos_nuevos     JSONB,
    ip_address       VARCHAR(45),
    creado_en        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_usuario  ON audit_log(id_usuario);
CREATE INDEX idx_audit_tabla    ON audit_log(tabla_afectada);
CREATE INDEX idx_audit_fecha    ON audit_log(creado_en DESC);

-- Vistas
CREATE VIEW v_pdvs_completo AS
SELECT
    p.id_pdv,
    p.codigo_gv,
    p.codigo_interno,
    p.nombre_pdv,
    p.direccion,
    m.nombre          AS mercado,
    c.nombre          AS ciudad,
    d.nombre          AS departamento,
    cat.nombre        AS categoria,
    p.prioridad,
    p.latitud,
    p.longitud,
    p.tiempo_visita_min,
    p.ventana_horaria_inicio,
    p.ventana_horaria_fin,
    sup.nombre        AS supervisor,
    rep.nombre        AS reponedor,
    p.atiende_lunes, p.atiende_martes, p.atiende_miercoles,
    p.atiende_jueves, p.atiende_viernes, p.atiende_sabado,
    p.atiende_domingo,
    p.frecuencia_semanal,
    p.frecuencia_mensual,
    p.notas_especiales
FROM puntos_de_venta p
JOIN mercados m             ON p.id_mercado   = m.id_mercado
JOIN ciudades c             ON m.id_ciudad    = c.id_ciudad
JOIN departamentos d        ON c.id_departamento = d.id_departamento
JOIN categorias_cliente cat ON p.id_categoria = cat.id_categoria
LEFT JOIN usuarios sup      ON p.id_supervisor = sup.id_usuario
LEFT JOIN usuarios rep      ON p.id_reponedor_asignado = rep.id_usuario
WHERE p.activo = TRUE;

CREATE VIEW v_cobertura_diaria AS
SELECT
    u.nombre AS reponedor,
    ru.fecha,
    COUNT(rp.id_ruta_punto)                                          AS total_puntos,
    COUNT(CASE WHEN rp.estado = 'completada' THEN 1 END)            AS completados,
    COUNT(CASE WHEN rp.estado = 'pendiente'  THEN 1 END)            AS pendientes,
    COUNT(CASE WHEN rp.estado = 'omitida'    THEN 1 END)            AS omitidos,
    ROUND(
        COUNT(CASE WHEN rp.estado = 'completada' THEN 1 END) * 100.0
        / NULLIF(COUNT(rp.id_ruta_punto), 0), 1
    ) AS porcentaje_cobertura
FROM rutas ru
JOIN usuarios u       ON ru.id_reponedor = u.id_usuario
JOIN ruta_puntos rp   ON ru.id_ruta      = rp.id_ruta
GROUP BY u.nombre, ru.fecha;

CREATE VIEW v_tiempos_reales_categoria AS
SELECT
    cat.nombre AS categoria,
    h.dia_semana,
    ROUND(AVG(h.tiempo_real_min), 1)      AS tiempo_promedio_real,
    ROUND(AVG(h.tiempo_estimado_min), 1)  AS tiempo_promedio_estimado,
    ROUND(AVG(h.diferencia_min), 1)       AS desviacion_promedio,
    COUNT(h.id_historial)                 AS total_registros
FROM historial_tiempos_pdv h
JOIN categorias_cliente cat ON h.id_categoria = cat.id_categoria
GROUP BY cat.nombre, h.dia_semana
ORDER BY cat.nombre, h.dia_semana;

CREATE VIEW v_incidencias_abiertas AS
SELECT
    i.id_incidencia,
    i.tipo,
    i.descripcion,
    p.codigo_gv,
    m.nombre AS mercado,
    c.nombre AS ciudad,
    d.nombre AS departamento,
    u.nombre AS reponedor,
    i.creado_en,
    ROUND(EXTRACT(EPOCH FROM (NOW() - i.creado_en)) / 3600, 1) AS horas_abiertas
FROM incidencias i
JOIN puntos_de_venta p  ON i.id_pdv       = p.id_pdv
JOIN mercados m         ON p.id_mercado   = m.id_mercado
JOIN ciudades c         ON m.id_ciudad    = c.id_ciudad
JOIN departamentos d    ON c.id_departamento = d.id_departamento
JOIN usuarios u         ON i.id_reponedor = u.id_usuario
WHERE i.resuelta = FALSE
ORDER BY i.creado_en ASC;

CREATE VIEW v_ranking_reponedores AS
SELECT
    u.nombre AS reponedor,
    c.nombre AS ciudad,
    COUNT(k.id_kpi)                                AS dias_registrados,
    ROUND(AVG(k.porcentaje_cobertura), 1)          AS cobertura_promedio,
    ROUND(AVG(k.distancia_real_km), 1)             AS km_promedio_dia,
    SUM(k.quiebres_stock_encontrados)              AS total_quiebres,
    SUM(k.incidencias_reportadas)                  AS total_incidencias,
    ROUND(AVG(k.desviacion_tiempo_min), 0)         AS desviacion_tiempo_promedio
FROM kpis_diarios k
JOIN usuarios u      ON k.id_reponedor = u.id_usuario
LEFT JOIN ciudades c ON u.id_ciudad    = c.id_ciudad
GROUP BY u.nombre, c.nombre
ORDER BY cobertura_promedio DESC;

CREATE VIEW v_resumen_departamento AS
SELECT
    d.nombre AS departamento,
    COUNT(DISTINCT p.id_pdv)                       AS total_pdvs,
    COUNT(DISTINCT p.id_reponedor_asignado)        AS total_reponedores,
    COUNT(DISTINCT m.id_mercado)                   AS total_mercados,
    COUNT(DISTINCT c.id_ciudad)                    AS total_ciudades
FROM departamentos d
LEFT JOIN ciudades c           ON d.id_departamento = c.id_departamento
LEFT JOIN mercados m           ON c.id_ciudad       = m.id_ciudad
LEFT JOIN puntos_de_venta p    ON m.id_mercado      = p.id_mercado AND p.activo = TRUE
GROUP BY d.nombre
ORDER BY total_pdvs DESC;
"""

SEED_SQL = """
-- 1. Roles
INSERT INTO roles (nombre, descripcion) VALUES
('admin',       'Administrador del sistema con acceso total'),
('supervisor',  'Supervisa reponedores, aprueba redistribuciones, resuelve incidencias'),
('reponedor',   'Ejecuta rutas, registra visitas, reporta incidencias en campo');

-- 2. Departamentos
INSERT INTO departamentos (nombre, codigo_iso, capital) VALUES
('La Paz',       'BO-L', 'Nuestra Señora de La Paz'),
('Cochabamba',   'BO-C', 'Cochabamba'),
('Santa Cruz',   'BO-S', 'Santa Cruz de la Sierra'),
('Oruro',        'BO-O', 'Oruro'),
('Potosí',       'BO-P', 'Potosí'),
('Tarija',       'BO-T', 'Tarija'),
('Chuquisaca',   'BO-H', 'Sucre'),
('Beni',         'BO-B', 'Trinidad'),
('Pando',        'BO-N', 'Cobija');

-- 3. Ciudades
INSERT INTO ciudades (id_departamento, nombre, latitud_centro, longitud_centro) VALUES
(1, 'La Paz',       -16.50000000, -68.15000000),
(1, 'El Alto',      -16.50944444, -68.19055556),
(1, 'Viacha',       -16.65000000, -68.30000000),
(1, 'Copacabana',   -16.16666667, -69.08333333),
(2, 'Cochabamba',   -17.39389000, -66.15694000),
(2, 'Quillacollo',  -17.39250000, -66.28028000),
(2, 'Sacaba',       -17.40167000, -66.03833000),
(2, 'Tiquipaya',    -17.33750000, -66.21667000),
(3, 'Santa Cruz de la Sierra', -17.78333333, -63.18194444),
(3, 'Montero',      -17.33888889, -63.25055556),
(3, 'Warnes',       -17.51388889, -63.16805556),
(3, 'La Guardia',   -17.88333333, -63.33333333),
(4, 'Oruro',        -17.96250000, -67.11500000),
(4, 'Huanuni',      -18.28333333, -66.83333333),
(5, 'Potosí',       -19.58888889, -65.75333333),
(5, 'Llallagua',    -18.41666667, -66.58333333),
(5, 'Villazón',     -22.08333333, -65.72222222),
(6, 'Tarija',       -21.53549000, -64.72956000),
(6, 'Yacuiba',      -22.01666667, -63.68333333),
(6, 'Bermejo',      -22.73333333, -64.33333333),
(7, 'Sucre',        -19.04472222, -65.25972222),
(7, 'Monteagudo',   -19.80000000, -63.95000000),
(8, 'Trinidad',     -14.83416667, -64.90138889),
(8, 'Riberalta',    -11.00638889, -66.06611111),
(8, 'Guayaramerín', -10.82638889, -65.35583333),
(9, 'Cobija',       -11.02666667, -68.76916667);

-- 4. Categorías
INSERT INTO categorias_cliente (nombre, criterio_clasificacion, tiempo_promedio_visita_min, perfil_atencion) VALUES
('MAYORISTA',  'Más de Bs. 50,000 de compra', 28, 'Gestión intermedia; enfoque en volumen y rotación.'),
('MINORISTA',  'Más de Bs. 5,000 de compra',  23, 'Foco en capilaridad y orden de estantería básico.'),
('DETALLISTA', 'Más de Bs. 70 de compra',     14, 'Visitas rápidas de reposición puntual.');

-- 5. Usuarios - Supervisores
INSERT INTO usuarios (id_rol, id_ciudad, nombre, email, password_hash) VALUES
(2, 1, 'Supervisor 1', 'supervisor1@venado.bo', '$2b$10$placeholder_hash_1'),
(2, 1, 'Supervisor 2', 'supervisor2@venado.bo', '$2b$10$placeholder_hash_2'),
(2, 1, 'Supervisor 3', 'supervisor3@venado.bo', '$2b$10$placeholder_hash_3');

-- 6. Usuarios - Reponedores
INSERT INTO usuarios (id_rol, id_ciudad, nombre, email, password_hash, id_supervisor) VALUES
(3, 1, 'Reponedor 1',       'reponedor1@venado.bo',      '$2b$10$placeholder', 1),
(3, 1, 'Reponedor 2',       'reponedor2@venado.bo',      '$2b$10$placeholder', 1),
(3, 1, 'Reponedor 3',       'reponedor3@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 4',       'reponedor4@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 5',       'reponedor5@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 6',       'reponedor6@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 7',       'reponedor7@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 8',       'reponedor8@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 8 Apoyo', 'reponedor8apoyo@venado.bo', '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 9',       'reponedor9@venado.bo',      '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 10',      'reponedor10@venado.bo',     '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 11',      'reponedor11@venado.bo',     '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 12',      'reponedor12@venado.bo',     '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 13',      'reponedor13@venado.bo',     '$2b$10$placeholder', 2),
(3, 1, 'Reponedor 14',      'reponedor14@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 15',      'reponedor15@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 16',      'reponedor16@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 17',      'reponedor17@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 18',      'reponedor18@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 19',      'reponedor19@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 20',      'reponedor20@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 21',      'reponedor21@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 22',      'reponedor22@venado.bo',     '$2b$10$placeholder', 3),
(3, 1, 'Reponedor 23',      'reponedor23@venado.bo',     '$2b$10$placeholder', 3);

-- 7. Perfiles de Reponedor
INSERT INTO perfiles_reponedor (id_usuario, tipo_vehiculo, capacidad_maxima_visitas_dia) VALUES
( 4, 'a_pie', 15),
( 5, 'a_pie', 15),
( 6, 'a_pie', 15),
( 7, 'a_pie', 15),
( 8, 'a_pie', 15),
( 9, 'a_pie', 15),
(10, 'a_pie', 15),
(11, 'a_pie', 15),
(12, 'a_pie', 10),
(13, 'a_pie', 15),
(14, 'a_pie', 15),
(15, 'a_pie', 15),
(16, 'a_pie', 15),
(17, 'a_pie', 15),
(18, 'a_pie', 15),
(19, 'a_pie', 15),
(20, 'a_pie', 15),
(21, 'a_pie', 15),
(22, 'a_pie', 15),
(23, 'a_pie', 15),
(24, 'a_pie', 15),
(25, 'a_pie', 15),
(26, 'a_pie', 15),
(27, 'a_pie', 15);

-- 8. Mercados
INSERT INTO mercados (id_ciudad, nombre) VALUES
(1,'CHASQUIPAMPA'),   (1,'ALTO PAMPAHASI'), (1,'10 DE ENERO'),
(1,'SAN ANTONIO'),    (1,'KOLLASUYO'),      (1,'CRUCE DE VILLAS'),
(1,'VILLA ARMONIA'),  (1,'ACHIMANI'),       (1,'LOS PINOS'),
(1,'IRPAVI'),         (1,'OVEJUYO'),        (1,'YUNGAS'),
(1,'MIRAFLORES'),     (1,'VILLA EL CARMEN'),(1,'OBRAJES'),
(1,'ALTO OBRAJES'),   (1,'STRONGEST'),      (1,'BOLIVAR'),
(1,'VITA'),           (1,'OBELISCO'),       (1,'ARCE'),
(1,'SOPOCACHI'),      (1,'HINOJOSA'),       (1,'CAMACHO'),
(1,'ACHACHICALA'),    (1,'LANZA'),          (1,'SAN JOSE'),
(1,'RODRIGUEZ'),      (1,'VILLA FATIMA'),   (1,'GARCILASO'),
(1,'TEJAR');
"""

def run_migration():
    print("Dropping old views and tables...")
    drops = [
        "DROP VIEW IF EXISTS v_ranking_reponedores CASCADE",
        "DROP VIEW IF EXISTS v_incidencias_abiertas CASCADE",
        "DROP VIEW IF EXISTS v_tiempos_reales_categoria CASCADE",
        "DROP VIEW IF EXISTS v_cobertura_diaria CASCADE",
        "DROP VIEW IF EXISTS v_pdvs_completo CASCADE",
        "DROP VIEW IF EXISTS v_resumen_departamento CASCADE",
        "DROP TABLE IF EXISTS audit_log CASCADE",
        "DROP TABLE IF EXISTS notificaciones CASCADE",
        "DROP TABLE IF EXISTS kpis_diarios CASCADE",
        "DROP TABLE IF EXISTS redistribuciones_sugeridas CASCADE",
        "DROP TABLE IF EXISTS historial_tiempos_pdv CASCADE",
        "DROP TABLE IF EXISTS incidencias CASCADE",
        "DROP TABLE IF EXISTS posiciones_gps CASCADE",
        "DROP TABLE IF EXISTS visita_tareas CASCADE",
        "DROP TABLE IF EXISTS visitas CASCADE",
        "DROP TABLE IF EXISTS ruta_puntos CASCADE",
        "DROP TABLE IF EXISTS rutas CASCADE",
        "DROP TABLE IF EXISTS micro_tareas CASCADE",
        "DROP TABLE IF EXISTS puntos_de_venta CASCADE",
        "DROP TABLE IF EXISTS mercados CASCADE",
        "DROP TABLE IF EXISTS categorias_cliente CASCADE",
        "DROP TABLE IF EXISTS sesiones CASCADE",
        "DROP TABLE IF EXISTS perfiles_reponedor CASCADE",
        "DROP TABLE IF EXISTS usuarios CASCADE",
        "DROP TABLE IF EXISTS ciudades CASCADE",
        "DROP TABLE IF EXISTS departamentos CASCADE",
        "DROP TABLE IF EXISTS roles CASCADE",
        "DROP TABLE IF EXISTS feedback CASCADE",
        "DROP TABLE IF EXISTS visita CASCADE",
        "DROP TABLE IF EXISTS ruta CASCADE",
        "DROP TABLE IF EXISTS pdv CASCADE",
        "DROP TABLE IF EXISTS microtarea CASCADE",
        "DROP TABLE IF EXISTS metricadiaria CASCADE"
    ]
    
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            for drop_q in drops:
                connection.execute(text(drop_q))
            print("Old tables and views dropped successfully.")
            
            print("Creating v3.0 tables and views...")
            # Split the statements to run them cleanly
            # Filter empty statements
            statements = [s.strip() for s in DDL_SQL.split(";") if s.strip()]
            for statement in statements:
                connection.execute(text(statement))
            print("v3.0 tables and views created successfully.")
            
            print("Inserting initial seed data...")
            seed_statements = [s.strip() for s in SEED_SQL.split(";") if s.strip()]
            for statement in seed_statements:
                connection.execute(text(statement))
            
            trans.commit()
            print("Migration and initial seeding completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise e

if __name__ == "__main__":
    run_migration()
