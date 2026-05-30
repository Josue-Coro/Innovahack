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

    # Manejar la hora (Dispositivo o Bolivia)
    if gps_data.timestamp:
        if gps_data.timestamp.tzinfo is not None:
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
    if perfil:
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
    # Trae los perfiles de los reponedores junto con su nombre de usuario
    resultados = db.query(
        models.PerfilReponedor, models.Usuario.nombre
    ).join(
        models.Usuario, models.Usuario.id_usuario == models.PerfilReponedor.id_usuario
    ).all()

    respuesta = []
    for perfil, nombre in resultados:
        respuesta.append({
            "id_usuario": perfil.id_usuario,
            "nombre": nombre,
            "lat_actual": perfil.lat_actual,
            "lon_actual": perfil.lon_actual,
            "bateria_actual": perfil.bateria_actual,
            "online": perfil.online,
            "ultima_conexion": perfil.ultima_conexion
        })
    return respuesta

@router.get("/{id_usuario}/gps", response_model=list[schemas.GPSLocationResponse])
async def get_historial_gps(id_usuario: int, fecha: str = None, db: Session = Depends(get_db)):
    # Si no se envía fecha, usamos la fecha de hoy en Bolivia
    if not fecha:
        fecha_obj = datetime.now(BOLIVIA_TZ).date()
    else:
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

    inicio_dia = datetime.combine(fecha_obj, datetime.min.time())
    fin_dia = inicio_dia + timedelta(days=1)

    puntos = db.query(models.PosicionGPS).filter(
        models.PosicionGPS.id_reponedor == id_usuario,
        models.PosicionGPS.timestamp >= inicio_dia,
        models.PosicionGPS.timestamp < fin_dia
    ).order_by(models.PosicionGPS.timestamp.asc()).all()

    return puntos
