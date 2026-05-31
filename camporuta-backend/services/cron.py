import asyncio
import logging
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from routers.rutas import generar_rutas_dia

logger = logging.getLogger(__name__)

async def run_daily_cron():
    BOLIVIA_TZ = timezone(timedelta(hours=-4))
    
    while True:
        try:
            ahora = datetime.now(BOLIVIA_TZ)
            # Próxima ejecución a las 06:00 AM
            proxima_ejecucion = ahora.replace(hour=6, minute=0, second=0, microsecond=0)
            
            if ahora >= proxima_ejecucion:
                # Si ya pasaron las 6 AM de hoy, programar para mañana a las 6 AM
                proxima_ejecucion += timedelta(days=1)
                
            segundos_espera = (proxima_ejecucion - ahora).total_seconds()
            logger.info(f"CRON: Durmiendo {segundos_espera} segundos hasta la próxima generación de rutas ({proxima_ejecucion})")
            
            await asyncio.sleep(segundos_espera)
            
            # Ejecutar generación
            logger.info("CRON: Iniciando generación automática de rutas de hoy...")
            
            # Necesitamos un session manager
            db = SessionLocal()
            try:
                # generar_rutas_dia toma un `Session`, por lo que pasamos la db.
                # También es async.
                res = await generar_rutas_dia(db)
                logger.info(f"CRON: Generación completada exitosamente. Resultado: {res}")
            except Exception as e:
                logger.error(f"CRON: Error generando rutas: {e}")
            finally:
                db.close()
                
        except asyncio.CancelledError:
            logger.info("CRON cancelado.")
            break
        except Exception as e:
            logger.error(f"CRON: Error inesperado en el loop principal: {e}")
            await asyncio.sleep(60) # Esperar un poco antes de reintentar
