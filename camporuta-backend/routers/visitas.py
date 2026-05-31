from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import pandas as pd
import io
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import math

from database import get_db
import models
import schemas
from routers.websocket import manager
from services.feedback import registrar_tiempo_real, analizar_comentario

# Zona horaria de Bolivia (UTC-4)
BOLIVIA_TZ = timezone(timedelta(hours=-4))

def calcular_distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000  # radio de la Tierra en metros
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _generar_tareas_visita(db: Session, visita: models.Visita):
    # Verificamos si ya existen tareas (por si acaso)
    existentes = db.query(models.VisitaTarea).filter(models.VisitaTarea.id_visita == visita.id_visita).count()
    if existentes > 0:
        return
    
    pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == visita.id_pdv).first()
    if not pdv or not pdv.id_categoria:
        return
    
    micro_tareas = db.query(models.MicroTarea).filter(
        models.MicroTarea.id_categoria == pdv.id_categoria,
        models.MicroTarea.activo == True
    ).all()
    
    for mt in micro_tareas:
        vt = models.VisitaTarea(
            id_visita=visita.id_visita,
            id_micro_tarea=mt.id_micro_tarea
        )
        db.add(vt)
    db.commit()

router = APIRouter(
    prefix="/visitas",
    tags=["Visitas"]
)

class RegistrarTiempoRequest(BaseModel):
    tiempo_real_min: float

@router.get("/ruta/{ruta_id}", response_model=List[schemas.Visita])
async def obtener_visitas_por_ruta(ruta_id: int, db: Session = Depends(get_db)):
    visitas = db.query(models.Visita).join(
        models.RutaPunto, models.Visita.id_ruta_punto == models.RutaPunto.id_ruta_punto
    ).filter(
        models.RutaPunto.id_ruta == ruta_id
    ).order_by(models.RutaPunto.orden.asc()).all()
    return visitas

@router.post("/ruta/{ruta_id}", response_model=schemas.Visita, status_code=status.HTTP_201_CREATED)
async def crear_visita(ruta_id: int, visita: schemas.VisitaCreate, db: Session = Depends(get_db)):
    # Check if route exists
    ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
        
    # Check or create RutaPunto
    rp = db.query(models.RutaPunto).filter(
        models.RutaPunto.id_ruta == ruta_id,
        models.RutaPunto.id_pdv == visita.id_pdv
    ).first()
    
    if not rp:
        max_orden = db.query(func.max(models.RutaPunto.orden)).filter(
            models.RutaPunto.id_ruta == ruta_id
        ).scalar() or 0
        rp = models.RutaPunto(
            id_ruta=ruta_id,
            id_pdv=visita.id_pdv,
            orden=max_orden + 1,
            estado=visita.estado
        )
        db.add(rp)
        db.flush()

    db_visita = models.Visita(
        id_ruta_punto=rp.id_ruta_punto,
        id_reponedor=visita.id_reponedor,
        id_pdv=visita.id_pdv,
        fecha=visita.fecha,
        estado=visita.estado,
        motivo_no_visita=visita.motivo_no_visita,
        quiebre_de_stock=visita.quiebre_de_stock,
        clima_descripcion=visita.clima_descripcion,
        temperatura_c=visita.temperatura_c,
        notas=visita.notas,
        foto_url=visita.foto_url,
        lat_registro=visita.lat_registro,
        lon_registro=visita.lon_registro
    )
    
    db.add(db_visita)
    db.commit()
    db.refresh(db_visita)
    
    # Broadcast creation
    await manager.broadcast({
        "type": "VISITA_CREADA",
        "payload": {
            "id_visita": db_visita.id_visita, 
            "id_ruta_punto": rp.id_ruta_punto, 
            "id_pdv": db_visita.id_pdv
        }
    })
    
    return db_visita


@router.post("/libre", response_model=schemas.Visita, status_code=status.HTTP_201_CREATED)
async def crear_visita_libre(visita: schemas.VisitaCreate, db: Session = Depends(get_db)):
    """
    Crea una visita libre, es decir, a un punto de venta que no necesariamente está en la ruta del día.
    No requiere un id_ruta. El id_ruta_punto quedará en nulo.
    """
    db_visita = models.Visita(
        id_ruta_punto=None,
        id_reponedor=visita.id_reponedor,
        id_pdv=visita.id_pdv,
        fecha=visita.fecha,
        estado=visita.estado,
        motivo_no_visita=visita.motivo_no_visita,
        quiebre_de_stock=visita.quiebre_de_stock,
        clima_descripcion=visita.clima_descripcion,
        temperatura_c=visita.temperatura_c,
        notas=visita.notas,
        foto_url=visita.foto_url,
        lat_registro=visita.lat_registro,
        lon_registro=visita.lon_registro
    )
    
    db.add(db_visita)
    db.commit()
    db.refresh(db_visita)
    
    _generar_tareas_visita(db, db_visita)
    
    # Broadcast creation
    await manager.broadcast({
        "type": "VISITA_CREADA_LIBRE",
        "payload": {
            "id_visita": db_visita.id_visita, 
            "id_pdv": db_visita.id_pdv
        }
    })
    
    return db_visita

@router.put("/{visita_id}", response_model=schemas.Visita)
async def actualizar_visita(visita_id: int, visita_upd: schemas.VisitaUpdate, db: Session = Depends(get_db)):
    db_visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not db_visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
        
    for key, value in visita_upd.model_dump(exclude_unset=True).items():
        setattr(db_visita, key, value)
        
    # Sync with RutaPunto if estado changed
    if visita_upd.estado and db_visita.id_ruta_punto:
        rp = db.query(models.RutaPunto).filter(models.RutaPunto.id_ruta_punto == db_visita.id_ruta_punto).first()
        if rp:
            rp.estado = visita_upd.estado
            db.add(rp)
            
    db.commit()
    db.refresh(db_visita)
    
    # Broadcast update
    await manager.broadcast({
        "type": "VISITA_ACTUALIZADA",
        "payload": {
            "id_visita": db_visita.id_visita, 
            "id_ruta_punto": db_visita.id_ruta_punto, 
            "estado": db_visita.estado
        }
    })
    
    return db_visita

@router.delete("/{visita_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_visita(visita_id: int, db: Session = Depends(get_db)):
    db_visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not db_visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
        
    id_ruta_punto = db_visita.id_ruta_punto
    db.delete(db_visita)
    db.commit()
    
    # Broadcast deletion
    await manager.broadcast({
        "type": "VISITA_ELIMINADA",
        "payload": {"id_visita": visita_id, "id_ruta_punto": id_ruta_punto}
    })
    
    return None

@router.post("/ruta/{ruta_id}/importar", response_model=List[schemas.Visita])
async def importar_visitas(
    ruta_id: int, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # Verify route exists
    ruta = db.query(models.Ruta).filter(models.Ruta.id_ruta == ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
        
    contents = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use CSV o Excel (.xlsx).")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el archivo: {str(e)}")
        
    required_cols = {"cliente_nombre", "direccion", "latitud", "longitud"}
    df.columns = [c.lower().strip() for c in df.columns]
    if not required_cols.issubset(df.columns):
        raise HTTPException(
            status_code=400, 
            detail=f"Columnas requeridas faltantes. Deben ser: {', '.join(required_cols)}"
        )
        
    db_visitas = []
    cat = db.query(models.CategoriaCliente).first()
    id_cat = cat.id_categoria if cat else None
    
    for i, row in df.iterrows():
        # Find or create PDV
        codigo_gv = f"GV_IMP_{int(datetime.utcnow().timestamp())}_{i}"
        pdv = models.PuntoDeVenta(
            codigo_gv=codigo_gv,
            nombre_pdv=str(row["cliente_nombre"]),
            direccion=str(row["direccion"]),
            latitud=float(row["latitud"]),
            longitud=float(row["longitud"]),
            tiempo_visita_min=20,
            id_categoria=id_cat,
            id_supervisor=ruta.id_supervisor,
            id_reponedor_asignado=ruta.id_reponedor,
            prioridad="media"
        )
        db.add(pdv)
        db.flush()
        
        # Create RutaPunto
        rp = models.RutaPunto(
            id_ruta=ruta_id,
            id_pdv=pdv.id_pdv,
            orden=i + 1,
            estado="pendiente"
        )
        db.add(rp)
        db.flush()
        
        # Create Visita
        db_visita = models.Visita(
            id_ruta_punto=rp.id_ruta_punto,
            id_reponedor=ruta.id_reponedor,
            id_pdv=pdv.id_pdv,
            fecha=ruta.fecha,
            estado="pendiente"
        )
        db.add(db_visita)
        db_visitas.append(db_visita)
        
    db.commit()
    
    for v in db_visitas:
        db.refresh(v)
        
    await manager.broadcast({
        "type": "VISITAS_IMPORTADAS",
        "payload": {
            "ruta_id": ruta_id,
            "cantidad": len(db_visitas)
        }
    })
    
    return db_visitas

@router.post("/{visita_id}/registrar_tiempo", response_model=schemas.Visita)
async def endpoint_registrar_tiempo_real(
    visita_id: int,
    req: RegistrarTiempoRequest,
    db: Session = Depends(get_db)
):
    try:
        visita = registrar_tiempo_real(visita_id, req.tiempo_real_min, db)
        await manager.broadcast({
            "type": "VISITA_COMPLETADA",
            "payload": {
                "id_visita": visita.id_visita,
                "duracion_real_min": req.tiempo_real_min,
                "estado": visita.estado
            }
        })
        return visita
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{visita_id}/iniciar", response_model=schemas.Visita)
async def iniciar_visita(
    visita_id: int,
    req: schemas.CheckInRequest,
    db: Session = Depends(get_db)
):
    visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
        
    if visita.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"La visita ya no está pendiente (Estado: {visita.estado})")

    # Obtener el PDV
    pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == visita.id_pdv).first()
    if not pdv:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado")

    # Calcular distancia
    distancia = calcular_distancia_metros(req.latitud_actual, req.longitud_actual, pdv.latitud, pdv.longitud)
    
    # Tolerancia de 100 metros
    if distancia > 100:
        raise HTTPException(
            status_code=400, 
            detail=f"Estás demasiado lejos del punto de venta ({distancia:.0f} metros). Acércate a menos de 100m para hacer Check-In."
        )

    # Actualizar la visita
    visita.hora_llegada = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)
    visita.estado = "en_curso"
    
    # Sincronizar estado en RutaPunto si existe
    if visita.id_ruta_punto:
        rp = db.query(models.RutaPunto).filter(models.RutaPunto.id_ruta_punto == visita.id_ruta_punto).first()
        if rp:
            rp.estado = "en_curso"
            db.add(rp)

    db.add(visita)
    db.commit()
    db.refresh(visita)
    
    _generar_tareas_visita(db, visita)

    # Notificar WebSocket
    await manager.broadcast({
        "type": "VISITA_ACTUALIZADA",
        "payload": {
            "id_visita": visita.id_visita, 
            "id_ruta_punto": visita.id_ruta_punto, 
            "estado": visita.estado,
            "distancia_iniciada_m": int(distancia)
        }
    })

    return visita

@router.post("/{visita_id}/finalizar", response_model=schemas.Visita)
async def finalizar_visita(
    visita_id: int,
    req: schemas.CheckInRequest,
    db: Session = Depends(get_db)
):
    visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
        
    if visita.estado != "en_curso":
        raise HTTPException(status_code=400, detail="La visita no está en progreso, por lo que no se puede finalizar.")

    # Validar distancia de salida (100 metros)
    pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == visita.id_pdv).first()
    if pdv:
        distancia = calcular_distancia_metros(req.latitud_actual, req.longitud_actual, pdv.latitud, pdv.longitud)
        if distancia > 100:
            raise HTTPException(
                status_code=400, 
                detail=f"Debes estar cerca de la tienda para finalizar la visita. Estás a {int(distancia)} metros (Max: 100m)."
            )

    hora_actual = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)
    visita.hora_salida = hora_actual
    visita.estado = "completada"

    # Calcular duración exacta
    if visita.hora_llegada:
        # Calcular los minutos transcurridos
        diferencia = hora_actual - visita.hora_llegada
        minutos = int(diferencia.total_seconds() / 60)
        visita.duracion_real_min = minutos
        
    # Sincronizar estado en RutaPunto
    if visita.id_ruta_punto:
        rp = db.query(models.RutaPunto).filter(models.RutaPunto.id_ruta_punto == visita.id_ruta_punto).first()
        if rp:
            rp.estado = "completada"
            db.add(rp)

    db.add(visita)
    db.commit()
    db.refresh(visita)

    # Notificar WebSocket
    await manager.broadcast({
        "type": "VISITA_COMPLETADA",
        "payload": {
            "id_visita": visita.id_visita, 
            "duracion_real_min": visita.duracion_real_min,
            "estado": visita.estado
        }
    })

    return visita

@router.get("/{visita_id}/tareas", response_model=List[schemas.VisitaTareaConDetalle])
async def obtener_tareas_visita(visita_id: int, db: Session = Depends(get_db)):
    visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    
    from sqlalchemy.orm import joinedload
    tareas = db.query(models.VisitaTarea).options(joinedload(models.VisitaTarea.micro_tarea)).filter(models.VisitaTarea.id_visita == visita_id).all()
    return tareas

@router.post("/{visita_id}/tareas/batch", response_model=List[schemas.VisitaTarea])
async def batch_completar_tareas(visita_id: int, ids_tareas: List[int], db: Session = Depends(get_db)):
    tareas = db.query(models.VisitaTarea).filter(
        models.VisitaTarea.id_visita == visita_id,
        models.VisitaTarea.id_visita_tarea.in_(ids_tareas)
    ).all()
    
    for tarea in tareas:
        tarea.completada = True
        tarea.hora_fin = datetime.now(BOLIVIA_TZ).replace(tzinfo=None)
        if not tarea.hora_inicio:
            tarea.hora_inicio = tarea.hora_fin
            
    db.commit()
    return db.query(models.VisitaTarea).filter(models.VisitaTarea.id_visita == visita_id).all()
