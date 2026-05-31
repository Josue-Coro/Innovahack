from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from database import get_db
import models
import schemas
from routers.websocket import manager

router = APIRouter(prefix="/usuarios", tags=["GPS"])

# Zona horaria de Bolivia (UTC-4)
BOLIVIA_TZ = timezone(timedelta(hours=-4))

@router.post("/{id_usuario}/gps", status_code=status.HTTP_201_CREATED)
async def update_gps_location(id_usuario: int, gps_data: schemas.GPSLocationCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario existe y es reponedor (asumiendo rol 3 = reponedor, o simplemente si tiene un perfil)
    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si el celular envía su propia hora, la convertimos a Bolivia
    if gps_data.timestamp:
        if gps_data.timestamp.tzinfo:
            hora_guardar = gps_data.timestamp.astimezone(BOLIVIA_TZ).replace(tzinfo=None)
        else:
            hora_guardar = gps_data.timestamp
    else:
        hora_guardar = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)

    # 2. Guardar en el histórico (posiciones_gps)
    nueva_posicion = models.PosicionGPS(
        id_reponedor=id_usuario,
        latitud=gps_data.latitud,
        longitud=gps_data.longitud,
        precision_m=gps_data.precision_m,
        velocidad_kmh=gps_data.velocidad_kmh,
        nivel_bateria=gps_data.nivel_bateria,
        timestamp=hora_guardar
    )
    db.add(nueva_posicion)

    # 3. Actualizar la última posición en perfiles_reponedor
    perfil = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_usuario == id_usuario).first()
    if not perfil:
        perfil = models.PerfilReponedor(id_usuario=id_usuario)
        db.add(perfil)
        
    perfil.lat_actual = gps_data.latitud
    perfil.lon_actual = gps_data.longitud
    if gps_data.nivel_bateria is not None:
        perfil.bateria_actual = gps_data.nivel_bateria
    perfil.online = True
    perfil.ultima_conexion = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)
    db.add(perfil)
    
    db.commit()

    # 4. Disparar evento al supervisor en tiempo real a través del WebSocket (Opcional pero muy útil)
    # Convertimos los datos al formato interno del websocket
    data_ws = {
        "lat": gps_data.latitud,
        "lon": gps_data.longitud,
        "bateria_actual": gps_data.nivel_bateria,
        "timestamp": hora_guardar.isoformat()
    }
    
    # Esto también actualizará el estado interno del websocket memory y avisará al supervisor
    await manager.update_reponedor_state(str(id_usuario), data_ws)

    return {"message": "Ubicación GPS actualizada exitosamente"}

@router.get("/reponedores/ultimas-ubicaciones", response_model=list[schemas.ReponedorUltimaUbicacion])
async def get_ultimas_ubicaciones(db: Session = Depends(get_db)):
    # Trae TODOS los usuarios reponedores (rol 3) y hace un LEFT JOIN con su perfil
    resultados = db.query(
        models.Usuario, models.PerfilReponedor
    ).outerjoin(
        models.PerfilReponedor, models.Usuario.id_usuario == models.PerfilReponedor.id_usuario
    ).filter(
        models.Usuario.id_rol == 3
    ).all()

    def format_bolivia_date(dt):
        if not dt:
            return None
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        dias  = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        hora_12 = dt.strftime("%I:%M").lstrip("0") or "12:00"
        am_pm   = "p.m." if dt.hour >= 12 else "a.m."
        return f"{hora_12} {am_pm} {dias[dt.weekday()]}, {dt.day} de {meses[dt.month]} de {dt.year} (GMT-4) Hora en Bolivia"

    respuesta = []
    for usuario, perfil in resultados:
        uc = perfil.ultima_conexion if perfil else None
        respuesta.append({
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "lat_actual": float(perfil.lat_actual) if perfil and perfil.lat_actual is not None else None,
            "lon_actual": float(perfil.lon_actual) if perfil and perfil.lon_actual is not None else None,
            "bateria_actual": perfil.bateria_actual if perfil else None,
            "online": perfil.online if perfil else False,
            "ultima_conexion": uc.replace(tzinfo=BOLIVIA_TZ) if uc else None,
            "ultima_conexion_formateada": format_bolivia_date(uc),
        })
    return respuesta

@router.get("/{id_usuario}/gps", response_model=list[schemas.GPSLocationResponse])
async def get_historial_gps(
    id_usuario: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(get_db)
):
    """
    Devuelve el historial GPS de un reponedor en un rango de fechas.
    - fecha_inicio: YYYY-MM-DD (por defecto: hoy)
    - fecha_fin:    YYYY-MM-DD (por defecto: mismo día que fecha_inicio)
    """

    def parse_fecha(f: str, label: str):
        try:
            return datetime.strptime(f, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Formato de {label} inválido. Use YYYY-MM-DD")

    hoy = datetime.now(BOLIVIA_TZ).date()

    inicio_date = parse_fecha(fecha_inicio, "fecha_inicio") if fecha_inicio else hoy
    fin_date    = parse_fecha(fecha_fin,    "fecha_fin")    if fecha_fin    else inicio_date

    if fin_date < inicio_date:
        raise HTTPException(status_code=400, detail="fecha_fin no puede ser anterior a fecha_inicio")

    inicio_dt = datetime.combine(inicio_date, datetime.min.time())
    fin_dt    = datetime.combine(fin_date,    datetime.max.time().replace(microsecond=0))

    puntos = db.query(models.PosicionGPS).filter(
        models.PosicionGPS.id_reponedor == id_usuario,
        models.PosicionGPS.timestamp >= inicio_dt,
        models.PosicionGPS.timestamp <= fin_dt
    ).order_by(models.PosicionGPS.timestamp.asc()).all()

    def format_bolivia_date(dt: datetime) -> str:
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        
        dia_semana = dias[dt.weekday()]
        dia = dt.day
        mes = meses[dt.month]
        anio = dt.year
        
        hora_12 = dt.strftime("%I:%M").lstrip("0")
        am_pm = "p.m." if dt.hour >= 12 else "a.m."
        
        return f"{hora_12} {am_pm} {dia_semana}, {dia} de {mes} de {anio} (GMT-4) Hora en Bolivia"

    resultado = []
    for p in puntos:
        resultado.append({
            "latitud": p.latitud,
            "longitud": p.longitud,
            "velocidad_kmh": p.velocidad_kmh,
            "nivel_bateria": p.nivel_bateria,
            "timestamp": p.timestamp.replace(tzinfo=BOLIVIA_TZ),
            "fecha_formateada": format_bolivia_date(p.timestamp)
        })

    return resultado
