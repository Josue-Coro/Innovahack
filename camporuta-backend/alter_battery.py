import logging
from sqlalchemy import text
from database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def alter_tables_for_battery():
    try:
        with engine.begin() as conn:
            # Add bateria_actual to perfiles_reponedor
            logger.info("Agregando bateria_actual a perfiles_reponedor...")
            conn.execute(text("ALTER TABLE perfiles_reponedor ADD COLUMN IF NOT EXISTS bateria_actual INTEGER;"))
            
            # Add nivel_bateria to posiciones_gps
            logger.info("Agregando nivel_bateria a posiciones_gps...")
            conn.execute(text("ALTER TABLE posiciones_gps ADD COLUMN IF NOT EXISTS nivel_bateria INTEGER;"))
            
            logger.info("Base de datos modificada exitosamente. Se agregaron las columnas de bateria.")
    except Exception as e:
        logger.error(f"Error alterando tablas: {e}")

if __name__ == "__main__":
    alter_tables_for_battery()
