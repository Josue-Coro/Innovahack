import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_rutas_dia():
    db = SessionLocal()
    try:
        # Reponedores a los que les asignaremos ruta
        reponedores_ids = [30, 4]
        fecha_hoy = date.today()
        
        # Traer todos los PDVs activos
        todos_pdvs = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.activo == True).all()
        if not todos_pdvs:
            logger.error("No hay PDVs en la base de datos para asignar rutas.")
            return

        for id_rep in reponedores_ids:
            # Check if user exists
            usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_rep).first()
            if not usuario:
                logger.warning(f"Usuario {id_rep} no existe, saltando...")
                continue
                
            # Verificar si ya tiene ruta hoy
            ruta_existente = db.query(models.Ruta).filter(
                models.Ruta.id_reponedor == id_rep,
                models.Ruta.fecha == fecha_hoy
            ).first()
            
            if ruta_existente:
                logger.info(f"El reponedor {id_rep} ya tiene una ruta para hoy. Eliminandola para recrear...")
                db.delete(ruta_existente)
                db.commit()

            # Seleccionar entre 5 y 8 PDVs aleatorios
            cantidad_pdvs = random.randint(5, 8)
            pdvs_seleccionados = random.sample(todos_pdvs, min(cantidad_pdvs, len(todos_pdvs)))
            
            # 1. Crear la Ruta
            nueva_ruta = models.Ruta(
                id_reponedor=id_rep,
                id_supervisor=usuario.id_supervisor,
                fecha=fecha_hoy,
                estado="pendiente",
                distancia_km_estimada=random.uniform(2.5, 8.0),
                duracion_min_estimada=sum([p.tiempo_visita_min for p in pdvs_seleccionados]) + (len(pdvs_seleccionados)*10),
                creado_en=datetime.utcnow()
            )
            db.add(nueva_ruta)
            db.commit() # Commit para obtener el id_ruta
            db.refresh(nueva_ruta)
            
            # 2. Crear los RutaPuntos
            hora_llegada = datetime.strptime("08:00", "%H:%M")
            for idx, pdv in enumerate(pdvs_seleccionados):
                # Calcular hora estimada sumando tiempos
                hora_str = hora_llegada.time()
                
                rp = models.RutaPunto(
                    id_ruta=nueva_ruta.id_ruta,
                    id_pdv=pdv.id_pdv,
                    orden=idx + 1,
                    hora_estimada_llegada=hora_str,
                    estado="pendiente"
                )
                db.add(rp)
                
                # Siguiente hora de llegada (tiempo en PDV + 15 min traslado)
                minutos_suma = pdv.tiempo_visita_min + 15
                hora_llegada = hora_llegada + timedelta(minutes=minutos_suma)
                
            db.commit()
            logger.info(f"Ruta creada exitosamente para Reponedor {id_rep} con {len(pdvs_seleccionados)} paradas.")
            
    except Exception as e:
        logger.error(f"Error generando datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_rutas_dia()
