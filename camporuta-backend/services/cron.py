import asyncio
import logging
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from routers.rutas import generar_rutas_dia

logger = logging.getLogger(__name__)

BOLIVIA_TZ = timezone(timedelta(hours=-4))


def _cerrar_visitas_pendientes(db):
    """
    Cierra todas las visitas que quedaron en estado 'pendiente' del dia actual,
    cambiandolas a 'no_realizada'.
    """
    import models
    hoy = datetime.now(BOLIVIA_TZ).date()
    pendientes = db.query(models.Visita).filter(
        models.Visita.estado == "pendiente",
        models.Visita.fecha == hoy
    ).all()

    if not pendientes:
        logger.info("CRON: No hay visitas pendientes para cerrar hoy.")
        return 0

    for v in pendientes:
        v.estado = "no_realizada"
        if v.id_ruta_punto:
            rp = db.query(models.RutaPunto).filter(
                models.RutaPunto.id_ruta_punto == v.id_ruta_punto
            ).first()
            if rp:
                rp.estado = "no_realizada"
    db.commit()
    logger.info(f"CRON: {len(pendientes)} visitas marcadas como 'no_realizada'.")
    return len(pendientes)


async def run_daily_cron():
    while True:
        try:
            ahora = datetime.now(BOLIVIA_TZ)

            # --- CIERRE DE VISITAS: 23:55 ---
            proxima_cierre = ahora.replace(hour=23, minute=55, second=0, microsecond=0)
            if ahora >= proxima_cierre:
                proxima_cierre += timedelta(days=1)
            segundos_cierre = (proxima_cierre - ahora).total_seconds()

            # --- GENERACION DE RUTAS: 06:00 ---
            proxima_generacion = ahora.replace(hour=6, minute=0, second=0, microsecond=0)
            if ahora >= proxima_generacion:
                proxima_generacion += timedelta(days=1)
            segundos_generacion = (proxima_generacion - ahora).total_seconds()

            # Ejecutar lo que ocurra primero
            segundos_espera = min(segundos_cierre, segundos_generacion)
            proxima_tarea = "cierre" if segundos_cierre < segundos_generacion else "generacion"
            logger.info(f"CRON: Proxima tarea: {proxima_tarea} en {int(segundos_espera)}s")

            await asyncio.sleep(segundos_espera)

            db = SessionLocal()
            try:
                if proxima_tarea == "cierre":
                    logger.info("CRON: Cerrando visitas pendientes del dia...")
                    _cerrar_visitas_pendientes(db)
                else:
                    logger.info("CRON: Iniciando generacion automatica de rutas del dia...")
                    res = await generar_rutas_dia(db)
                    logger.info(f"CRON: Generacion completada. Resultado: {res}")
            except Exception as e:
                logger.error(f"CRON: Error en tarea '{proxima_tarea}': {e}")
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("CRON cancelado.")
            break
        except Exception as e:
            logger.error(f"CRON: Error inesperado en el loop principal: {e}")
            await asyncio.sleep(60)
