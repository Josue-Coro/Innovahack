from database import SessionLocal
from models import Visita
from datetime import datetime

db = SessionLocal()
try:
    visita = db.query(Visita).filter(Visita.estado == 'pendiente').first()
    if visita:
        print("Found pending visita:", visita.id_visita)
        visita.estado = 'en_curso'
        visita.hora_llegada = datetime.now()
        db.commit()

        # Simulate checkout
        visita.estado = 'completada'
        visita.hora_salida = datetime.now()
        visita.duracion_real_min = 15
        db.commit()
        print("Success! duracion:", visita.duracion_real_min)
except Exception as e:
    import traceback
    traceback.print_exc()
