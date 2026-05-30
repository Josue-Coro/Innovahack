from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas

router = APIRouter(tags=["Catalogo"])

# ============================================================
# CATEGORIAS CLIENTE
# ============================================================

@router.get("/categorias-cliente/", response_model=List[schemas.CategoriaCliente])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(models.CategoriaCliente).order_by(models.CategoriaCliente.nombre).all()


@router.get("/categorias-cliente/{categoria_id}", response_model=schemas.CategoriaCliente)
def obtener_categoria(categoria_id: int, db: Session = Depends(get_db)):
    c = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == categoria_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return c


@router.post("/categorias-cliente/", response_model=schemas.CategoriaCliente, status_code=status.HTTP_201_CREATED)
def crear_categoria(categoria: schemas.CategoriaClienteCreate, db: Session = Depends(get_db)):
    db_c = models.CategoriaCliente(**categoria.model_dump())
    db.add(db_c)
    db.commit()
    db.refresh(db_c)
    return db_c


@router.put("/categorias-cliente/{categoria_id}", response_model=schemas.CategoriaCliente)
def actualizar_categoria(categoria_id: int, categoria_upd: schemas.CategoriaClienteUpdate, db: Session = Depends(get_db)):
    db_c = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == categoria_id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    for key, value in categoria_upd.model_dump(exclude_unset=True).items():
        setattr(db_c, key, value)
    db.commit()
    db.refresh(db_c)
    return db_c


@router.delete("/categorias-cliente/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(categoria_id: int, db: Session = Depends(get_db)):
    db_c = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == categoria_id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    db.delete(db_c)
    db.commit()
    return None


# ============================================================
# PUNTOS DE VENTA (PDV)
# ============================================================

@router.get("/pdvs/", response_model=List[schemas.PuntoDeVenta])
def listar_pdvs(
    id_mercado: Optional[int] = None,
    id_categoria: Optional[int] = None,
    id_reponedor_asignado: Optional[int] = None,
    id_supervisor: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.PuntoDeVenta)
    if id_mercado is not None:
        q = q.filter(models.PuntoDeVenta.id_mercado == id_mercado)
    if id_categoria is not None:
        q = q.filter(models.PuntoDeVenta.id_categoria == id_categoria)
    if id_reponedor_asignado is not None:
        q = q.filter(models.PuntoDeVenta.id_reponedor_asignado == id_reponedor_asignado)
    if id_supervisor is not None:
        q = q.filter(models.PuntoDeVenta.id_supervisor == id_supervisor)
        
    return q.order_by(models.PuntoDeVenta.nombre_pdv).all()


@router.get("/pdvs/{pdv_id}", response_model=schemas.PuntoDeVenta)
def obtener_pdv(pdv_id: int, db: Session = Depends(get_db)):
    p = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == pdv_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    return p


@router.post("/pdvs/", response_model=schemas.PuntoDeVenta, status_code=status.HTTP_201_CREATED)
def crear_pdv(pdv: schemas.PuntoDeVentaCreate, db: Session = Depends(get_db)):
    db_p = models.PuntoDeVenta(**pdv.model_dump())
    db.add(db_p)
    db.commit()
    db.refresh(db_p)
    return db_p


@router.put("/pdvs/{pdv_id}", response_model=schemas.PuntoDeVenta)
def actualizar_pdv(pdv_id: int, pdv_upd: schemas.PuntoDeVentaUpdate, db: Session = Depends(get_db)):
    db_p = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == pdv_id).first()
    if not db_p:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    for key, value in pdv_upd.model_dump(exclude_unset=True).items():
        setattr(db_p, key, value)
    db.commit()
    db.refresh(db_p)
    return db_p


@router.delete("/pdvs/{pdv_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pdv(pdv_id: int, db: Session = Depends(get_db)):
    db_p = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == pdv_id).first()
    if not db_p:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    db.delete(db_p)
    db.commit()
    return None


# ============================================================
# MICRO TAREAS
# ============================================================

@router.get("/micro-tareas/", response_model=List[schemas.MicroTarea])
def listar_micro_tareas(id_categoria: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.MicroTarea)
    if id_categoria is not None:
        q = q.filter(models.MicroTarea.id_categoria == id_categoria)
    return q.order_by(models.MicroTarea.orden).all()


@router.get("/micro-tareas/{tarea_id}", response_model=schemas.MicroTarea)
def obtener_micro_tarea(tarea_id: int, db: Session = Depends(get_db)):
    t = db.query(models.MicroTarea).filter(models.MicroTarea.id_micro_tarea == tarea_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Micro Tarea no encontrada")
    return t


@router.post("/micro-tareas/", response_model=schemas.MicroTarea, status_code=status.HTTP_201_CREATED)
def crear_micro_tarea(tarea: schemas.MicroTareaCreate, db: Session = Depends(get_db)):
    db_t = models.MicroTarea(**tarea.model_dump())
    db.add(db_t)
    db.commit()
    db.refresh(db_t)
    return db_t


@router.put("/micro-tareas/{tarea_id}", response_model=schemas.MicroTarea)
def actualizar_micro_tarea(tarea_id: int, tarea_upd: schemas.MicroTareaUpdate, db: Session = Depends(get_db)):
    db_t = db.query(models.MicroTarea).filter(models.MicroTarea.id_micro_tarea == tarea_id).first()
    if not db_t:
        raise HTTPException(status_code=404, detail="Micro Tarea no encontrada")
    for key, value in tarea_upd.model_dump(exclude_unset=True).items():
        setattr(db_t, key, value)
    db.commit()
    db.refresh(db_t)
    return db_t


@router.delete("/micro-tareas/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_micro_tarea(tarea_id: int, db: Session = Depends(get_db)):
    db_t = db.query(models.MicroTarea).filter(models.MicroTarea.id_micro_tarea == tarea_id).first()
    if not db_t:
        raise HTTPException(status_code=404, detail="Micro Tarea no encontrada")
    db.delete(db_t)
    db.commit()
    return None
