from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(tags=["Geografia"])

# ============================================================
# DEPARTAMENTOS
# ============================================================

@router.get("/departamentos/", response_model=List[schemas.Departamento])
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(models.Departamento).order_by(models.Departamento.nombre).all()


@router.get("/departamentos/{depto_id}", response_model=schemas.Departamento)
def obtener_departamento(depto_id: int, db: Session = Depends(get_db)):
    d = db.query(models.Departamento).filter(models.Departamento.id_departamento == depto_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return d


@router.post("/departamentos/", response_model=schemas.Departamento, status_code=status.HTTP_201_CREATED)
def crear_departamento(dep: schemas.DepartamentoCreate, db: Session = Depends(get_db)):
    db_dep = models.Departamento(**dep.model_dump())
    db.add(db_dep)
    db.commit()
    db.refresh(db_dep)
    return db_dep


@router.put("/departamentos/{depto_id}", response_model=schemas.Departamento)
def actualizar_departamento(depto_id: int, dep_upd: schemas.DepartamentoUpdate, db: Session = Depends(get_db)):
    db_dep = db.query(models.Departamento).filter(models.Departamento.id_departamento == depto_id).first()
    if not db_dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    for key, value in dep_upd.model_dump(exclude_unset=True).items():
        setattr(db_dep, key, value)
    db.commit()
    db.refresh(db_dep)
    return db_dep


@router.delete("/departamentos/{depto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_departamento(depto_id: int, db: Session = Depends(get_db)):
    db_dep = db.query(models.Departamento).filter(models.Departamento.id_departamento == depto_id).first()
    if not db_dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    db.delete(db_dep)
    db.commit()
    return None


# ============================================================
# CIUDADES
# ============================================================

@router.get("/ciudades/", response_model=List[schemas.Ciudad])
def listar_ciudades(id_departamento: int = None, db: Session = Depends(get_db)):
    q = db.query(models.Ciudad)
    if id_departamento:
        q = q.filter(models.Ciudad.id_departamento == id_departamento)
    return q.order_by(models.Ciudad.nombre).all()


@router.get("/ciudades/{ciudad_id}", response_model=schemas.Ciudad)
def obtener_ciudad(ciudad_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Ciudad).filter(models.Ciudad.id_ciudad == ciudad_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    return c


@router.post("/ciudades/", response_model=schemas.Ciudad, status_code=status.HTTP_201_CREATED)
def crear_ciudad(ciudad: schemas.CiudadCreate, db: Session = Depends(get_db)):
    db_c = models.Ciudad(**ciudad.model_dump())
    db.add(db_c)
    db.commit()
    db.refresh(db_c)
    return db_c


@router.put("/ciudades/{ciudad_id}", response_model=schemas.Ciudad)
def actualizar_ciudad(ciudad_id: int, ciudad_upd: schemas.CiudadUpdate, db: Session = Depends(get_db)):
    db_c = db.query(models.Ciudad).filter(models.Ciudad.id_ciudad == ciudad_id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    for key, value in ciudad_upd.model_dump(exclude_unset=True).items():
        setattr(db_c, key, value)
    db.commit()
    db.refresh(db_c)
    return db_c


@router.delete("/ciudades/{ciudad_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_ciudad(ciudad_id: int, db: Session = Depends(get_db)):
    db_c = db.query(models.Ciudad).filter(models.Ciudad.id_ciudad == ciudad_id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")
    db.delete(db_c)
    db.commit()
    return None


# ============================================================
# MERCADOS
# ============================================================

@router.get("/mercados/", response_model=List[schemas.Mercado])
def listar_mercados(id_ciudad: int = None, db: Session = Depends(get_db)):
    q = db.query(models.Mercado)
    if id_ciudad:
        q = q.filter(models.Mercado.id_ciudad == id_ciudad)
    return q.order_by(models.Mercado.nombre).all()


@router.get("/mercados/{mercado_id}", response_model=schemas.Mercado)
def obtener_mercado(mercado_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Mercado).filter(models.Mercado.id_mercado == mercado_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mercado no encontrado")
    return m


@router.post("/mercados/", response_model=schemas.Mercado, status_code=status.HTTP_201_CREATED)
def crear_mercado(mercado: schemas.MercadoCreate, db: Session = Depends(get_db)):
    db_m = models.Mercado(**mercado.model_dump())
    db.add(db_m)
    db.commit()
    db.refresh(db_m)
    return db_m


@router.put("/mercados/{mercado_id}", response_model=schemas.Mercado)
def actualizar_mercado(mercado_id: int, mercado_upd: schemas.MercadoUpdate, db: Session = Depends(get_db)):
    db_m = db.query(models.Mercado).filter(models.Mercado.id_mercado == mercado_id).first()
    if not db_m:
        raise HTTPException(status_code=404, detail="Mercado no encontrado")
    for key, value in mercado_upd.model_dump(exclude_unset=True).items():
        setattr(db_m, key, value)
    db.commit()
    db.refresh(db_m)
    return db_m


@router.delete("/mercados/{mercado_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_mercado(mercado_id: int, db: Session = Depends(get_db)):
    db_m = db.query(models.Mercado).filter(models.Mercado.id_mercado == mercado_id).first()
    if not db_m:
        raise HTTPException(status_code=404, detail="Mercado no encontrado")
    db.delete(db_m)
    db.commit()
    return None
