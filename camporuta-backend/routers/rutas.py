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

@router.post("/generar-dia", status_code=status.HTTP_201_CREATED)
async def generar_rutas_dia(db: Session = Depends(get_db)):
    """
    Genera las rutas del día actual para todos los reponedores.
    Basado en los PDVs asignados que atienden hoy.
    """
    from datetime import datetime, timedelta, timezone, date
    from services.openrouteservice import get_directions
    
    BOLIVIA_TZ = timezone(timedelta(hours=-4))
    hoy = datetime.now(BOLIVIA_TZ)
    dia_semana = hoy.weekday() # 0 = Lunes, 6 = Domingo
    
    dias_attr = [
        "atiende_lunes", "atiende_martes", "atiende_miercoles", 
        "atiende_jueves", "atiende_viernes", "atiende_sabado", "atiende_domingo"
    ]
    attr_hoy = dias_attr[dia_semana]

    # Encontrar reponedores activos
    reponedores = db.query(models.Usuario).filter(models.Usuario.id_rol == 3, models.Usuario.activo == True).all()
    
    rutas_creadas = []
    
    for rep in reponedores:
        # Buscar PDVs asignados a este reponedor que se deben visitar hoy
        filtro_pdv = {
            "id_reponedor_asignado": rep.id_usuario,
            "activo": True,
            attr_hoy: True
        }
        pdvs_hoy = db.query(models.PuntoDeVenta).filter_by(**filtro_pdv).all()
        
        if not pdvs_hoy:
            continue
            
        # Eliminar ruta existente para hoy si existe (para sobreescribir)
        ruta_existente = db.query(models.Ruta).filter_by(
            id_reponedor=rep.id_usuario, 
            fecha=hoy.date()
        ).first()
        
        if ruta_existente:
            puntos_ids = [p.id_ruta_punto for p in db.query(models.RutaPunto).filter_by(id_ruta=ruta_existente.id_ruta).all()]
            if puntos_ids:
                db.query(models.Visita).filter(models.Visita.id_ruta_punto.in_(puntos_ids)).delete(synchronize_session=False)
            db.query(models.RutaPunto).filter_by(id_ruta=ruta_existente.id_ruta).delete(synchronize_session=False)
            db.delete(ruta_existente)
            db.flush()
            
        # Crear la ruta vacía
        nueva_ruta = models.Ruta(
            id_reponedor=rep.id_usuario,
            fecha=hoy.date(),
            estado="pendiente"
        )
        db.add(nueva_ruta)
        db.flush() # Para obtener id_ruta
        
        # Obtener ubicación actual del reponedor (si existe)
        perfil = db.query(models.PerfilReponedor).filter_by(id_usuario=rep.id_usuario).first()
        lat_inicio = float(perfil.lat_actual) if perfil and perfil.lat_actual is not None else None
        lon_inicio = float(perfil.lon_actual) if perfil and perfil.lon_actual is not None else None

        # Asignar PDVs a la nueva ruta
        for idx, pdv in enumerate(pdvs_hoy):
            ruta_punto = models.RutaPunto(
                id_ruta=nueva_ruta.id_ruta,
                id_pdv=pdv.id_pdv,
                orden=idx + 1
            )
            db.add(ruta_punto)
        
        db.flush()
        
        # Optimizar ruta pasando la ubicación del reponedor
        nueva_ruta = optimizar_ruta_db(nueva_ruta, db, lat_inicio, lon_inicio)
        
        # Generar polyline y tiempos con OpenRouteService
        puntos_ordenados = sorted(nueva_ruta.ruta_puntos, key=lambda x: x.orden)
        coordenadas = [[float(rp.pdv.longitud), float(rp.pdv.latitud)] for rp in puntos_ordenados if rp.pdv]
        
        # Si tenemos la ubicación del reponedor, insertarla al inicio de la ruta ORS
        if lat_inicio is not None and lon_inicio is not None:
            coordenadas.insert(0, [lon_inicio, lat_inicio])
            
        polyline, dist, dur, duraciones = await get_directions(coordenadas)
        
        nueva_ruta.polyline_json = polyline
        nueva_ruta.distancia_km_estimada = dist
        nueva_ruta.duracion_min_estimada = int(dur)
        
        # Asignar ETA y crear Visitas
        # Asumimos que inicia a las 8:00 AM (esto puede venir de la DB o config)
        hora_inicio_ruta = datetime.combine(hoy, time(8, 0))
        hora_actual_eta = hora_inicio_ruta
        
        for idx, rp in enumerate(puntos_ordenados):
            if duraciones and len(duraciones) > 0:
                if lat_inicio is not None and lon_inicio is not None:
                    # Como insertamos la ubicación del usuario, los duraciones tienen un tramo extra al inicio
                    minutos_viaje = duraciones[idx] if idx < len(duraciones) else 5.0
                    
                    if idx > 0:
                        pdv_anterior = puntos_ordenados[idx-1].pdv
                        tiempo_visita = pdv_anterior.tiempo_visita_min if pdv_anterior and pdv_anterior.tiempo_visita_min else 15
                    else:
                        tiempo_visita = 0 # El primer viaje desde la casa del reponedor no tiene visita previa
                        
                    hora_actual_eta += timedelta(minutes=minutos_viaje + tiempo_visita)
                    rp.hora_estimada_llegada = hora_actual_eta.time()
                else:
                    if idx == 0:
                        rp.hora_estimada_llegada = hora_actual_eta.time()
                    else:
                        # Si ORS truncó la ruta a 50 puntos, usamos 5 min como fallback para los excedentes
                        if (idx - 1) < len(duraciones):
                            minutos_viaje = duraciones[idx - 1]
                        else:
                            minutos_viaje = 5.0
                            
                        # Sumar tiempo de viaje + tiempo de visita en el PDV anterior
                        pdv_anterior = puntos_ordenados[idx-1].pdv
                        tiempo_visita = pdv_anterior.tiempo_visita_min if pdv_anterior and pdv_anterior.tiempo_visita_min else 15
                        
                        hora_actual_eta += timedelta(minutes=minutos_viaje + tiempo_visita)
                        rp.hora_estimada_llegada = hora_actual_eta.time()
                        
            # Generar la Visita en estado pendiente (fuera de los ifs de lat_inicio)
            visita = models.Visita(
                id_ruta_punto=rp.id_ruta_punto,
                id_pdv=rp.id_pdv,
                id_reponedor=rep.id_usuario,
                estado="pendiente",
                fecha=hoy.date()
            )
            db.add(visita)
        
        db.commit()
        rutas_creadas.append(nueva_ruta.id_ruta)
        
    return {"message": f"Se generaron {len(rutas_creadas)} rutas para hoy.", "rutas_generadas": rutas_creadas}

@router.post("/reponedor/{id_reponedor}/auto-asignar-dias", status_code=status.HTTP_200_OK)
async def auto_asignar_dias(id_reponedor: int, db: Session = Depends(get_db)):
    """
    Agrupa los PDVs de un reponedor usando K-Means y les asigna 
    automáticamente los días de visita de Lunes a Sábado, respetando la frecuencia.
    """
    from services.clustering import auto_asignar_dias_reponedor
    
    reponedor = db.query(models.Usuario).filter(
        models.Usuario.id_usuario == id_reponedor,
        models.Usuario.id_rol == 3
    ).first()
    
    if not reponedor:
        raise HTTPException(status_code=404, detail="Reponedor no encontrado o no es de rol Reponedor")
        
    cantidad = auto_asignar_dias_reponedor(id_reponedor, db)
    
    return {"message": f"Se reasignaron los días para {cantidad} PDVs de forma automática y balanceada."}
