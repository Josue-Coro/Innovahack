import logging
from datetime import datetime, timedelta, date, time
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_gps_history():
    db = SessionLocal()
    try:
        # Reponedores y centro base (Santa Cruz)
        usuarios_ids = [30, 4]
        lat_base = -17.78333333
        lon_base = -63.18194444
        
        # Fecha de hoy
        fecha_hoy = date.today()
        # Horario laboral: 08:00 AM a 16:00 PM (8 horas)
        hora_inicio = datetime.combine(fecha_hoy, time(8, 0))
        
        total_minutos = 8 * 60
        intervalo_min = 5
        pasos = total_minutos // intervalo_min
        
        for id_rep in usuarios_ids:
            # Borrar histórico de hoy para evitar duplicados si corremos varias veces
            db.query(models.PosicionGPS).filter(
                models.PosicionGPS.id_reponedor == id_rep,
                models.PosicionGPS.timestamp >= hora_inicio,
                models.PosicionGPS.timestamp <= hora_inicio + timedelta(hours=24)
            ).delete()
            db.commit()

            lat_actual = lat_base
            lon_actual = lon_base
            bateria_actual = 100.0
            
            logger.info(f"Generando recorrido para usuario ID: {id_rep}")
            
            puntos_insertados = 0
            for i in range(pasos + 1):
                timestamp_punto = hora_inicio + timedelta(minutes=i*intervalo_min)
                
                # Simular movimiento: Desplazamiento máximo de aprox. 50-100 metros por cada 5 min
                # 0.0001 grados son ~11 metros
                variacion_lat = random.uniform(-0.0005, 0.0005)
                variacion_lon = random.uniform(-0.0005, 0.0005)
                
                lat_actual += variacion_lat
                lon_actual += variacion_lon
                
                # Simular batería: Drena entre 0.5% y 1.2% cada 5 minutos
                bateria_drenaje = random.uniform(0.5, 1.2)
                bateria_actual = max(0.0, bateria_actual - bateria_drenaje)
                
                # Velocidad y precisión aleatoria
                velocidad = random.uniform(0.0, 30.0) if i % 3 != 0 else 0.0  # a veces está quieto
                precision = random.uniform(3.0, 15.0)
                
                pos = models.PosicionGPS(
                    id_reponedor=id_rep,
                    latitud=lat_actual,
                    longitud=lon_actual,
                    precision_m=round(precision, 1),
                    velocidad_kmh=round(velocidad, 1),
                    nivel_bateria=int(bateria_actual),
                    timestamp=timestamp_punto
                )
                db.add(pos)
                puntos_insertados += 1
            
            db.commit()
            logger.info(f"Éxito: {puntos_insertados} puntos de GPS insertados para el ID {id_rep}.")

    except Exception as e:
        logger.error(f"Error generando datos GPS: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_gps_history()
