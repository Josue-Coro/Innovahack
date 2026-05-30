import os
import pandas as pd
from database import SessionLocal
import models

def seed_database():
    excel_path = "INFORMACION_DE_DATOS_TRADICIONAL_LA_PAZ_rev.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Error: El archivo '{excel_path}' no se encuentra en el directorio actual.")
        return
        
    print(f"Leyendo archivo Excel: {excel_path}...")
    
    try:
        # Read the excel sheet with requested params:
        # sheet='CLIENT. TRADE LP', header=1, skiprows=[0]
        # header=1 indicates the 2nd row is the header, and skiprows=[0] skips the 1st row.
        df = pd.read_excel(
            excel_path, 
            sheet_name="CLIENT. TRADE LP", 
            header=1, 
            skiprows=[0]
        )
    except Exception as e:
        print(f"Error al leer el archivo Excel: {e}")
        return

    # Keep only the first 18 columns to align with renamed column headers
    df = df.iloc[:, :18]
    
    df.columns = [
        "Nro", "MERCADO", "CATEGORIA", "CODIGO", "CLIENTE", "LATITUD", 
        "LONGITUD", "SUPERVISOR", "REPONEDOR", "TIEMPO_VISITA_MIN", 
        "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", 
        "FRECUENCIA_SEMANAL", "FRECUENCIA_MENSUAL"
    ]

    db = SessionLocal()
    pdv_count = 0

    print("Iniciando inserción de PDVs en la base de datos...")
    
    for index, row in df.iterrows():
        # Check if the code or name is missing, skip empty lines
        if pd.isna(row["CODIGO"]) or pd.isna(row["CLIENTE"]):
            continue

        try:
            codigo_str = str(row["CODIGO"]).strip()
            # Clean floating numbers in code string (e.g., "123.0" -> "123")
            if codigo_str.endswith(".0"):
                codigo_str = codigo_str[:-2]

            # Check if PDV already exists to prevent duplicate key constraint errors
            existing = db.query(models.PDV).filter(models.PDV.codigo == codigo_str).first()
            if existing:
                continue

            # Map the boolean days using pd.notna() as requested
            dias_atencion = {
                "lunes": bool(pd.notna(row["LUNES"])),
                "martes": bool(pd.notna(row["MARTES"])),
                "miercoles": bool(pd.notna(row["MIERCOLES"])),
                "jueves": bool(pd.notna(row["JUEVES"])),
                "viernes": bool(pd.notna(row["VIERNES"])),
                "sabado": bool(pd.notna(row["SABADO"])),
                "domingo": False
            }

            def clean_int(val):
                try:
                    return int(float(val)) if pd.notna(val) else None
                except (ValueError, TypeError):
                    return None

            def clean_float(val):
                try:
                    # Replace comma decimal separator if present
                    if isinstance(val, str):
                        val = val.replace(",", ".")
                    return float(val) if pd.notna(val) else 0.0
                except (ValueError, TypeError):
                    return 0.0

            pdv = models.PDV(
                codigo=codigo_str,
                nombre=str(row["CLIENTE"]).strip(),
                latitud=clean_float(row["LATITUD"]),
                longitud=clean_float(row["LONGITUD"]),
                categoria=str(row["CATEGORIA"]).strip() if pd.notna(row["CATEGORIA"]) else None,
                mercado=str(row["MERCADO"]).strip() if pd.notna(row["MERCADO"]) else None,
                supervisor=str(row["SUPERVISOR"]).strip() if pd.notna(row["SUPERVISOR"]) else None,
                reponedor_asignado=str(row["REPONEDOR"]).strip() if pd.notna(row["REPONEDOR"]) else None,
                tiempo_estimado_min=clean_int(row["TIEMPO_VISITA_MIN"]),
                dias_atencion=dias_atencion,
                frecuencia_semanal=clean_int(row["FRECUENCIA_SEMANAL"]),
                frecuencia_mensual=clean_int(row["FRECUENCIA_MENSUAL"])
            )

            db.add(pdv)
            db.commit()
            pdv_count += 1
            
        except Exception as e:
            db.rollback()
            print(f"Error insertando fila {index + 1} (Código: {row.get('CODIGO')}): {e}")

    db.close()
    print(f"Cargados {pdv_count} PDVs exitosamente")

if __name__ == "__main__":
    seed_database()
