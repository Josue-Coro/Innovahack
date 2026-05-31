from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(tags=["Entregas"])

@router.get("/entregas/pdv/{id_pdv}", response_model=List[schemas.Entrega])
def listar_entregas_pdv(id_pdv: int, db: Session = Depends(get_db)):
    """Lista el historial de entregas de un punto de venta específico"""
    entregas = db.query(models.Entrega).filter(models.Entrega.id_pdv == id_pdv).order_by(models.Entrega.fecha_hora_entrega.desc()).all()
    return entregas

@router.post("/entregas/", response_model=schemas.Entrega, status_code=status.HTTP_201_CREATED)
def registrar_entrega(entrega: schemas.EntregaCreate, db: Session = Depends(get_db)):
    """
    Registra una entrega de productos durante una visita.
    Descuenta automáticamente el stock general de la bodega.
    """
    # 1. Crear el registro maestro de la entrega
    db_entrega = models.Entrega(
        id_visita=entrega.id_visita,
        id_reponedor=entrega.id_reponedor,
        id_pdv=entrega.id_pdv,
        notas=entrega.notas
    )
    db.add(db_entrega)
    db.flush() # Obtenemos id_entrega
    
    # 2. Procesar cada producto entregado
    for prod_entrega in entrega.productos:
        # Buscar producto en la base de datos
        db_prod = db.query(models.Producto).filter(models.Producto.id_producto == prod_entrega.id_producto).with_for_update().first()
        
        if not db_prod:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Producto ID {prod_entrega.id_producto} no encontrado")
            
        # Verificar stock si es necesario (opcional, por ahora permitimos stock negativo si hubo error de inventario)
        # if db_prod.stock_actual < prod_entrega.cantidad_entregada:
        #     db.rollback()
        #     raise HTTPException(status_code=400, detail=f"Stock insuficiente para {db_prod.nombre_producto}")
            
        # Descontar stock general
        db_prod.stock_actual -= prod_entrega.cantidad_entregada
        
        # Registrar detalle de entrega
        detalle = models.EntregaProducto(
            id_entrega=db_entrega.id_entrega,
            id_producto=prod_entrega.id_producto,
            cantidad_entregada=prod_entrega.cantidad_entregada
        )
        db.add(detalle)
        
    db.commit()
    db.refresh(db_entrega)
    return db_entrega
