from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas
from utils.auth import get_password_hash

router = APIRouter(tags=["Usuarios"])

# ============================================================
# USUARIOS
# ============================================================

@router.get("/usuarios/", response_model=List[schemas.Usuario])
def listar_usuarios(
    id_rol: Optional[int] = None,
    id_supervisor: Optional[int] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Usuario)
    if id_rol is not None:
        q = q.filter(models.Usuario.id_rol == id_rol)
    if id_supervisor is not None:
        q = q.filter(models.Usuario.id_supervisor == id_supervisor)
    if activo is not None:
        q = q.filter(models.Usuario.activo == activo)
    return q.order_by(models.Usuario.nombre).all()


@router.get("/usuarios/{usuario_id}", response_model=schemas.Usuario)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    u = db.query(models.Usuario).filter(models.Usuario.id_usuario == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return u


@router.post("/usuarios/", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    usuario_data = usuario.model_dump()
    password = usuario_data.pop("password")
    usuario_data["password_hash"] = get_password_hash(password)
    
    db_u = models.Usuario(**usuario_data)
    db.add(db_u)
    db.commit()
    db.refresh(db_u)
    return db_u


@router.put("/usuarios/{usuario_id}", response_model=schemas.Usuario)
def actualizar_usuario(usuario_id: int, usuario_upd: schemas.UsuarioUpdate, db: Session = Depends(get_db)):
    db_u = db.query(models.Usuario).filter(models.Usuario.id_usuario == usuario_id).first()
    if not db_u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    for key, value in usuario_upd.model_dump(exclude_unset=True).items():
        if key == "password":
            setattr(db_u, "password_hash", get_password_hash(value))
        else:
            setattr(db_u, key, value)
            
    db.commit()
    db.refresh(db_u)
    return db_u


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    db_u = db.query(models.Usuario).filter(models.Usuario.id_usuario == usuario_id).first()
    if not db_u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(db_u)
    db.commit()
    return None


# ============================================================
# PERFILES DE REPONEDOR
# ============================================================

@router.get("/perfiles-reponedor/", response_model=List[schemas.PerfilReponedor])
def listar_perfiles(db: Session = Depends(get_db)):
    return db.query(models.PerfilReponedor).all()


@router.get("/perfiles-reponedor/{perfil_id}", response_model=schemas.PerfilReponedor)
def obtener_perfil(perfil_id: int, db: Session = Depends(get_db)):
    p = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_perfil_reponedor == perfil_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return p


@router.get("/perfiles-reponedor/usuario/{usuario_id}", response_model=schemas.PerfilReponedor)
def obtener_perfil_por_usuario(usuario_id: int, db: Session = Depends(get_db)):
    p = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_usuario == usuario_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Perfil no encontrado para este usuario")
    return p


@router.post("/perfiles-reponedor/", response_model=schemas.PerfilReponedor, status_code=status.HTTP_201_CREATED)
def crear_perfil(perfil: schemas.PerfilReponedorCreate, db: Session = Depends(get_db)):
    db_p = models.PerfilReponedor(**perfil.model_dump())
    db.add(db_p)
    db.commit()
    db.refresh(db_p)
    return db_p


@router.put("/perfiles-reponedor/{perfil_id}", response_model=schemas.PerfilReponedor)
def actualizar_perfil(perfil_id: int, perfil_upd: schemas.PerfilReponedorUpdate, db: Session = Depends(get_db)):
    db_p = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_perfil_reponedor == perfil_id).first()
    if not db_p:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    for key, value in perfil_upd.model_dump(exclude_unset=True).items():
        setattr(db_p, key, value)
    db.commit()
    db.refresh(db_p)
    return db_p


@router.delete("/perfiles-reponedor/{perfil_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    db_p = db.query(models.PerfilReponedor).filter(models.PerfilReponedor.id_perfil_reponedor == perfil_id).first()
    if not db_p:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    db.delete(db_p)
    db.commit()
    return None


# ============================================================
# SESIONES
# ============================================================

@router.get("/sesiones/", response_model=List[schemas.Sesion])
def listar_sesiones(id_usuario: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(models.Sesion)
    if id_usuario is not None:
        q = q.filter(models.Sesion.id_usuario == id_usuario)
    return q.order_by(models.Sesion.creado_en.desc()).all()


@router.get("/sesiones/{sesion_id}", response_model=schemas.Sesion)
def obtener_sesion(sesion_id: int, db: Session = Depends(get_db)):
    s = db.query(models.Sesion).filter(models.Sesion.id_sesion == sesion_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return s


@router.post("/sesiones/", response_model=schemas.Sesion, status_code=status.HTTP_201_CREATED)
def crear_sesion(sesion: schemas.SesionCreate, db: Session = Depends(get_db)):
    db_s = models.Sesion(**sesion.model_dump())
    db.add(db_s)
    db.commit()
    db.refresh(db_s)
    return db_s


@router.delete("/sesiones/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_sesion(sesion_id: int, db: Session = Depends(get_db)):
    db_s = db.query(models.Sesion).filter(models.Sesion.id_sesion == sesion_id).first()
    if not db_s:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    db.delete(db_s)
    db.commit()
    return None
