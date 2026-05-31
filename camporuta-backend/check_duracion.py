from database import SessionLocal
from models import Visita

db = SessionLocal()
visita = db.query(Visita).filter(Visita.estado == 'completada').first()
if visita:
    print(f"Visita {visita.id_visita}: llegada={visita.hora_llegada}, salida={visita.hora_salida}, duracion={visita.duracion_real_min}")
else:
    print("No completada found")
