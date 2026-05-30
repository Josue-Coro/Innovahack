from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=List[schemas.Rol])
def listar_roles(db: Session = Depends(get_db)):
    return db.query(models.Rol).all()


@router.get("/{rol_id}", response_model=schemas.Rol)
def obtener_rol(rol_id: int, db: Session = Depends(get_db)):
    rol = db.query(models.Rol).filter(models.Rol.id_rol == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.post("/", response_model=schemas.Rol, status_code=status.HTTP_201_CREATED)
def crear_rol(rol: schemas.RolCreate, db: Session = Depends(get_db)):
    db_rol = models.Rol(**rol.model_dump())
    db.add(db_rol)
    db.commit()
    db.refresh(db_rol)
    return db_rol


@router.put("/{rol_id}", response_model=schemas.Rol)
def actualizar_rol(rol_id: int, rol_upd: schemas.RolUpdate, db: Session = Depends(get_db)):
    db_rol = db.query(models.Rol).filter(models.Rol.id_rol == rol_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    for key, value in rol_upd.model_dump(exclude_unset=True).items():
        setattr(db_rol, key, value)
    db.commit()
    db.refresh(db_rol)
    return db_rol


@router.delete("/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rol(rol_id: int, db: Session = Depends(get_db)):
    db_rol = db.query(models.Rol).filter(models.Rol.id_rol == rol_id).first()
    if not db_rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    db.delete(db_rol)
    db.commit()
    return None
