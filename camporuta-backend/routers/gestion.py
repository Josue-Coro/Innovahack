from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas

router = APIRouter(tags=["Gestion"])

# ============================================================
# POSICIONES GPS
# ============================================================
@router.get("/gps/", response_model=List[schemas.PosicionGPS])
def listar_posiciones_gps(id_reponedor: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.PosicionGPS)
    if id_reponedor is not None:
        q = q.filter(models.PosicionGPS.id_reponedor == id_reponedor)
    return q.order_by(models.PosicionGPS.timestamp.desc()).limit(100).all()

@router.post("/gps/", response_model=schemas.PosicionGPS, status_code=status.HTTP_201_CREATED)
def registrar_posicion_gps(gps: schemas.PosicionGPSCreate, db: Session = Depends(get_db)):
    db_gps = models.PosicionGPS(**gps.model_dump())
    db.add(db_gps)
    db.commit()
    db.refresh(db_gps)
    return db_gps


# ============================================================
# INCIDENCIAS
# ============================================================
@router.get("/incidencias/", response_model=List[schemas.Incidencia])
def listar_incidencias(
    resuelta: Optional[bool] = None,
    id_reponedor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Incidencia)
    if resuelta is not None:
        q = q.filter(models.Incidencia.resuelta == resuelta)
    if id_reponedor is not None:
        q = q.filter(models.Incidencia.id_reponedor == id_reponedor)
    return q.order_by(models.Incidencia.creado_en.desc()).all()

@router.post("/incidencias/", response_model=schemas.Incidencia, status_code=status.HTTP_201_CREATED)
def crear_incidencia(incidencia: schemas.IncidenciaCreate, db: Session = Depends(get_db)):
    db_inc = models.Incidencia(**incidencia.model_dump())
    db.add(db_inc)
    db.commit()
    db.refresh(db_inc)
    return db_inc

@router.put("/incidencias/{inc_id}", response_model=schemas.Incidencia)
def actualizar_incidencia(inc_id: int, inc_upd: schemas.IncidenciaUpdate, db: Session = Depends(get_db)):
    db_inc = db.query(models.Incidencia).filter(models.Incidencia.id_incidencia == inc_id).first()
    if not db_inc:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    for key, value in inc_upd.model_dump(exclude_unset=True).items():
        setattr(db_inc, key, value)
    db.commit()
    db.refresh(db_inc)
    return db_inc


# ============================================================
# REDISTRIBUCIONES SUGERIDAS
# ============================================================
@router.get("/redistribuciones/", response_model=List[schemas.RedistribucionSugerida])
def listar_redistribuciones(estado: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.RedistribucionSugerida)
    if estado:
        q = q.filter(models.RedistribucionSugerida.estado == estado)
    return q.order_by(models.RedistribucionSugerida.creado_en.desc()).all()

@router.post("/redistribuciones/", response_model=schemas.RedistribucionSugerida, status_code=status.HTTP_201_CREATED)
def crear_redistribucion(red: schemas.RedistribucionSugeridaCreate, db: Session = Depends(get_db)):
    db_red = models.RedistribucionSugerida(**red.model_dump())
    db.add(db_red)
    db.commit()
    db.refresh(db_red)
    return db_red

@router.put("/redistribuciones/{red_id}", response_model=schemas.RedistribucionSugerida)
def actualizar_redistribucion(red_id: int, red_upd: schemas.RedistribucionSugeridaUpdate, db: Session = Depends(get_db)):
    db_red = db.query(models.RedistribucionSugerida).filter(models.RedistribucionSugerida.id_redistribucion == red_id).first()
    if not db_red:
        raise HTTPException(status_code=404, detail="Redistribucion no encontrada")
    for key, value in red_upd.model_dump(exclude_unset=True).items():
        setattr(db_red, key, value)
    db.commit()
    db.refresh(db_red)
    return db_red


# ============================================================
# KPIS DIARIOS
# ============================================================
@router.get("/kpis/", response_model=List[schemas.KPIDiario])
def listar_kpis(id_reponedor: Optional[int] = None, fecha: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.KPIDiario)
    if id_reponedor:
        q = q.filter(models.KPIDiario.id_reponedor == id_reponedor)
    if fecha:
        q = q.filter(models.KPIDiario.fecha == fecha)
    return q.order_by(models.KPIDiario.fecha.desc()).limit(100).all()

@router.post("/kpis/", response_model=schemas.KPIDiario, status_code=status.HTTP_201_CREATED)
def crear_kpi(kpi: schemas.KPIDiarioCreate, db: Session = Depends(get_db)):
    db_kpi = models.KPIDiario(**kpi.model_dump())
    db.add(db_kpi)
    db.commit()
    db.refresh(db_kpi)
    return db_kpi

@router.put("/kpis/{kpi_id}", response_model=schemas.KPIDiario)
def actualizar_kpi(kpi_id: int, kpi_upd: schemas.KPIDiarioUpdate, db: Session = Depends(get_db)):
    db_kpi = db.query(models.KPIDiario).filter(models.KPIDiario.id_kpi == kpi_id).first()
    if not db_kpi:
        raise HTTPException(status_code=404, detail="KPI no encontrado")
    for key, value in kpi_upd.model_dump(exclude_unset=True).items():
        setattr(db_kpi, key, value)
    db.commit()
    db.refresh(db_kpi)
    return db_kpi


# ============================================================
# NOTIFICACIONES
# ============================================================
@router.get("/notificaciones/", response_model=List[schemas.Notificacion])
def listar_notificaciones(
    id_supervisor: Optional[int] = None,
    id_reponedor: Optional[int] = None,
    leida: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Notificacion)
    if id_supervisor is not None:
        q = q.filter(models.Notificacion.id_supervisor == id_supervisor)
    if id_reponedor is not None:
        q = q.filter(models.Notificacion.id_reponedor == id_reponedor)
    if leida is not None:
        q = q.filter(models.Notificacion.leida == leida)
    return q.order_by(models.Notificacion.creado_en.desc()).all()

@router.post("/notificaciones/", response_model=schemas.Notificacion, status_code=status.HTTP_201_CREATED)
def crear_notificacion(notif: schemas.NotificacionCreate, db: Session = Depends(get_db)):
    db_notif = models.Notificacion(**notif.model_dump())
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif

@router.put("/notificaciones/{notif_id}", response_model=schemas.Notificacion)
def actualizar_notificacion(notif_id: int, notif_upd: schemas.NotificacionUpdate, db: Session = Depends(get_db)):
    db_notif = db.query(models.Notificacion).filter(models.Notificacion.id_notificacion == notif_id).first()
    if not db_notif:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    for key, value in notif_upd.model_dump(exclude_unset=True).items():
        setattr(db_notif, key, value)
    db.commit()
    db.refresh(db_notif)
    return db_notif
