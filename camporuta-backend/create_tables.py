from database import engine, Base
import models  # Import models to ensure they are registered on the Base metadata

def create_tables():
    print("Creando tablas en la base de datos de Supabase...")
    Base.metadata.create_all(engine)
    print("Tablas creadas exitosamente")

if __name__ == "__main__":
    create_tables()
