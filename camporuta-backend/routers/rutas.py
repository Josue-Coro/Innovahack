from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas
from services.optimizador import optimizar_ruta_db
from routers.websocket import manager

router = APIRouter(
    prefix="/rutas",
    tags=["Rutas"]
)

@router.get("/", response_model=List[schemas.Ruta])
async def obtener_rutas(db: Session = Depends(get_db)):
    rutas = db.query(models.Ruta).order_by(models.Ruta.creado_en.desc()).all()
    return rutas

@router.get("/{ruta_id}", response_model=schemas.RutaWithPuntos)
async def obtener_ruta(ruta_id: int, db: Session = Depends(get_db)):
    ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return ruta

@router.post("/", response_model=schemas.Ruta, status_code=status.HTTP_201_CREATED)
async def crear_ruta(ruta: schemas.RutaCreate, db: Session = Depends(get_db)):
    db_ruta = models.Ruta(**ruta.model_dump())
    db.add(db_ruta)
    db.commit()
    db.refresh(db_ruta)
    return db_ruta

@router.put("/{ruta_id}", response_model=schemas.Ruta)
async def actualizar_ruta(ruta_id: int, ruta_upd: schemas.RutaUpdate, db: Session = Depends(get_db)):
    db_ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not db_ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    
    for key, value in ruta_upd.model_dump(exclude_unset=True).items():
        setattr(db_ruta, key, value)
    
    db.commit()
    db.refresh(db_ruta)
    
    # Broadcast route update to all websocket clients
    await manager.broadcast({
        "type": "RUTA_ACTUALIZADA",
        "payload": {
            "id_ruta": db_ruta.id_ruta, 
            "id_reponedor": db_ruta.id_reponedor, 
            "fecha": str(db_ruta.fecha),
            "estado": db_ruta.estado
        }
    })
    
    return db_ruta

@router.delete("/{ruta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_ruta(ruta_id: int, db: Session = Depends(get_db)):
    db_ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not db_ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    
    db.delete(db_ruta)
    db.commit()
    
    # Broadcast route deletion to all websocket clients
    await manager.broadcast({
        "type": "RUTA_ELIMINADA",
        "payload": {"id_ruta": ruta_id}
    })
    return None

@router.post("/{ruta_id}/optimizar", response_model=schemas.RutaWithPuntos)
async def optimizar_ruta(ruta_id: int, db: Session = Depends(get_db)):
    db_ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not db_ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    
    db_ruta = optimizar_ruta_db(db_ruta, db)
    
    # Broadcast optimized route update
    puntos_payload = []
    for rp in sorted(db_ruta.ruta_puntos, key=lambda x: x.orden):
        pdv = rp.pdv
        puntos_payload.append({
            "id_ruta_punto": rp.id_ruta_punto,
            "codigo_gv": pdv.codigo_gv if pdv else "SIN_CODIGO",
            "nombre_pdv": pdv.nombre_pdv if pdv else "Sin Nombre",
            "orden": rp.orden,
            "latitud": float(pdv.latitud) if pdv else 0.0,
            "longitud": float(pdv.longitud) if pdv else 0.0
        })

    await manager.broadcast({
        "type": "RUTA_OPTIMIZADA",
        "payload": {
            "id_ruta": db_ruta.id_ruta,
            "id_reponedor": db_ruta.id_reponedor,
            "puntos": puntos_payload
        }
    })
    
    return db_ruta
