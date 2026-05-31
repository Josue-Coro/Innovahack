from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter(tags=["Productos"])

# ============================================================
# CATEGORIAS DE PRODUCTOS
# ============================================================

@router.get("/categorias-productos/", response_model=List[schemas.CategoriaProducto])
def listar_categorias_productos(db: Session = Depends(get_db)):
    return db.query(models.CategoriaProducto).all()

@router.post("/categorias-productos/", response_model=schemas.CategoriaProducto, status_code=status.HTTP_201_CREATED)
def crear_categoria_producto(categoria: schemas.CategoriaProductoCreate, db: Session = Depends(get_db)):
    db_cat = models.CategoriaProducto(**categoria.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.put("/categorias-productos/{cat_id}", response_model=schemas.CategoriaProducto)
def actualizar_categoria_producto(cat_id: int, categoria_upd: schemas.CategoriaProductoUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(models.CategoriaProducto).filter(models.CategoriaProducto.id_categoria_producto == cat_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    for key, value in categoria_upd.model_dump(exclude_unset=True).items():
        setattr(db_cat, key, value)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/categorias-productos/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria_producto(cat_id: int, db: Session = Depends(get_db)):
    db_cat = db.query(models.CategoriaProducto).filter(models.CategoriaProducto.id_categoria_producto == cat_id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    db.delete(db_cat)
    db.commit()
    return None

# ============================================================
# PRODUCTOS
# ============================================================

@router.get("/productos/", response_model=List[schemas.Producto])
def listar_productos(id_categoria: int = None, db: Session = Depends(get_db)):
    q = db.query(models.Producto)
    if id_categoria:
        q = q.filter(models.Producto.id_categoria_producto == id_categoria)
    return q.all()

@router.get("/productos/{prod_id}", response_model=schemas.Producto)
def obtener_producto(prod_id: int, db: Session = Depends(get_db)):
    prod = db.query(models.Producto).filter(models.Producto.id_producto == prod_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod

@router.post("/productos/", response_model=schemas.Producto, status_code=status.HTTP_201_CREATED)
def crear_producto(producto: schemas.ProductoCreate, db: Session = Depends(get_db)):
    db_prod = models.Producto(**producto.model_dump())
    db.add(db_prod)
    db.commit()
    db.refresh(db_prod)
    return db_prod

@router.put("/productos/{prod_id}", response_model=schemas.Producto)
def actualizar_producto(prod_id: int, prod_upd: schemas.ProductoUpdate, db: Session = Depends(get_db)):
    db_prod = db.query(models.Producto).filter(models.Producto.id_producto == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in prod_upd.model_dump(exclude_unset=True).items():
        setattr(db_prod, key, value)
    db.commit()
    db.refresh(db_prod)
    return db_prod

@router.delete("/productos/{prod_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(prod_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(models.Producto).filter(models.Producto.id_producto == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(db_prod)
    db.commit()
    return None
