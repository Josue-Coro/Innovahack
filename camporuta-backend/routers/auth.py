from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timedelta

from database import get_db
import models
import schemas
from utils.auth import verify_password

router = APIRouter(tags=["Auth"])

@router.post("/login", response_model=schemas.LoginResponse)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    # 1. Buscar usuario por email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == credentials.email).first()
    
    # 2. Verificar existencia y contraseña
    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas o usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not verify_password(credentials.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Generar token de sesión
    token = str(uuid.uuid4())
    
    # 4. Obtener nombre del rol
    rol = db.query(models.Rol).filter(models.Rol.id_rol == usuario.id_rol).first()
    rol_nombre = rol.nombre if rol else None
    
    # 5. Registrar la sesión en la base de datos
    expira_en = datetime.utcnow() + timedelta(days=30)
    db_sesion = models.Sesion(
        id_usuario=usuario.id_usuario,
        token_jwt=token,
        creado_en=datetime.utcnow(),
        expira_en=expira_en
    )
    db.add(db_sesion)
    db.commit()
    
    # 6. Retornar respuesta
    return {
        "token": token,
        "usuario": usuario,
        "rol": rol_nombre
    }
