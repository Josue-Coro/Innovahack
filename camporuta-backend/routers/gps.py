from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
import models
import schemas
from routers.websocket import manager

router = APIRouter(prefix="/usuarios", tags=["GPS"])

@router.post("/{id_usuario}/gps", status_code=status.HTTP_201_CREATED)
async def update_gps_location(id_usuario: int, gps_data: schemas.GPSLocationCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario existe y es reponedor (asumiendo rol 3 = reponedor, o simplemente si tiene un perfil)
    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2. Guardar en el histórico (posiciones_gps)
    nueva_posicion = models.PosicionGPS(
        id_reponedor=id_usuario,
        latitud=gps_data.latitud,
        longitud=gps_data.longitud,
        precision_m=gps_data.precision_m,
        velocidad_kmh=gps_data.velocidad_kmh,
        nivel_bateria=gps_data.nivel_bateria,
        timestamp=gps_data.timestamp or datetime.utcnow()
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
        perfil.ultima_conexion = datetime.utcnow()
        db.add(perfil)
    
    db.commit()

    # 4. Disparar evento al supervisor en tiempo real a través del WebSocket (Opcional pero muy útil)
    # Convertimos los datos al formato interno del websocket
    data_ws = {
        "lat": gps_data.latitud,
        "lon": gps_data.longitud,
        "bateria_actual": gps_data.nivel_bateria,
        "timestamp": gps_data.timestamp.isoformat() if gps_data.timestamp else datetime.utcnow().isoformat()
    }
    
    # Esto también actualizará el estado interno del websocket memory y avisará al supervisor
    await manager.update_reponedor_state(str(id_usuario), data_ws)

    return {"message": "Ubicación GPS actualizada exitosamente"}
