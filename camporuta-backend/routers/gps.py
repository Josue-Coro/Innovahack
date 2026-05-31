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

    respuesta = []
    for usuario, perfil in resultados:
        respuesta.append({
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "lat_actual": perfil.lat_actual if perfil else None,
            "lon_actual": perfil.lon_actual if perfil else None,
            "bateria_actual": perfil.bateria_actual if perfil else None,
            "online": perfil.online if perfil else False,
            "ultima_conexion": perfil.ultima_conexion if perfil else None
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

    resultado = []
    for p in puntos:
        resultado.append({
            "latitud": p.latitud,
            "longitud": p.longitud,
            "velocidad_kmh": p.velocidad_kmh,
            "nivel_bateria": p.nivel_bateria,
            "timestamp": p.timestamp
        })

    return resultado


@router.post("/{id_usuario}/gps/batch", status_code=status.HTTP_201_CREATED)
async def update_gps_location_batch(id_usuario: int, gps_data_list: list[schemas.GPSLocationCreate], db: Session = Depends(get_db)):
    """
    Recibe múltiples posiciones GPS en una sola petición.
    Ideal para sincronizar registros guardados offline en SQLite.
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not gps_data_list:
        return {"message": "No hay datos para procesar"}

    nuevas_posiciones = []
    ultima_posicion = None

    for gps_data in gps_data_list:
        if gps_data.timestamp:
            if gps_data.timestamp.tzinfo:
                hora_guardar = gps_data.timestamp.astimezone(BOLIVIA_TZ).replace(tzinfo=None)
            else:
                hora_guardar = gps_data.timestamp
        else:
            hora_guardar = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)

        nueva_posicion = models.PosicionGPS(
            id_reponedor=id_usuario,
            latitud=gps_data.latitud,
            longitud=gps_data.longitud,
            precision_m=gps_data.precision_m,
            velocidad_kmh=gps_data.velocidad_kmh,
            nivel_bateria=gps_data.nivel_bateria,
            timestamp=hora_guardar
        )
        nuevas_posiciones.append(nueva_posicion)
        
        # Mantener un registro de la última posición recibida para actualizar el perfil
        if ultima_posicion is None or hora_guardar > ultima_posicion.timestamp:
            ultima_posicion = nueva_posicion

    db.bulk_save_objects(nuevas_posiciones)

    if ultima_posicion:
        perfil = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_usuario == id_usuario).first()
        if not perfil:
            perfil = models.PerfilReponedor(id_usuario=id_usuario)
            db.add(perfil)
            
        perfil.lat_actual = ultima_posicion.latitud
        perfil.lon_actual = ultima_posicion.longitud
        if ultima_posicion.nivel_bateria is not None:
            perfil.bateria_actual = ultima_posicion.nivel_bateria
        perfil.online = True
        perfil.ultima_conexion = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)
        db.add(perfil)
    
    db.commit()

    return {"message": f"{len(nuevas_posiciones)} posiciones sincronizadas correctamente"}
