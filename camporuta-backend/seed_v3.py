import os
import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

def seed_puntos_de_venta():
    excel_path = "INFORMACION_DE_DATOS_TRADICIONAL_LA_PAZ_rev.xlsx"
    if not os.path.exists(excel_path):
        print(f"Error: El archivo Excel '{excel_path}' no se encuentra en el directorio actual.")
        return
        
    db = SessionLocal()
    
    try:
        print("Cargando mapeos de base de datos...")
        # 1. Markets mapping
        mercados = db.query(models.Mercado).all()
        mercados_map = {m.nombre.strip().upper(): m.id_mercado for m in mercados}
        
        # 2. Categories mapping
        categorias = db.query(models.CategoriaCliente).all()
        categorias_map = {c.nombre.strip().upper(): c.id_categoria for c in categorias}
        
        # 3. Users mapping (Supervisores & Reponedores)
        usuarios = db.query(models.Usuario).all()
        usuarios_map = {u.nombre.strip().upper(): u.id_usuario for u in usuarios}
        
        print(f"Leyendo archivo Excel: {excel_path}...")
        df = pd.read_excel(
            excel_path, 
            sheet_name="CLIENT. TRADE LP", 
            header=1, 
            skiprows=[0]
        )
        
        # Keep only first 18 columns
        df = df.iloc[:, :18]
        df.columns = [
            "Nro", "MERCADO", "CATEGORIA", "CODIGO", "CLIENTE", "LATITUD", 
            "LONGITUD", "SUPERVISOR", "REPONEDOR", "TIEMPO_VISITA_MIN", 
            "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", 
            "FRECUENCIA_SEMANAL", "FRECUENCIA_MENSUAL"
        ]
        
        print("Iniciando inserción de Puntos de Venta (PDVs)...")
        pdv_count = 0
        
        for index, row in df.iterrows():
            codigo_raw = row["CODIGO"]
            cliente_raw = row["CLIENTE"]
            
            if pd.isna(codigo_raw) or pd.isna(cliente_raw):
                continue
                
            codigo_str = str(codigo_raw).strip()
            nombre_str = str(cliente_raw).strip()
            
            # Clean coordinate floats
            def clean_float(val):
                try:
                    if isinstance(val, str):
                        val = val.replace(",", ".")
                    return float(val) if pd.notna(val) else 0.0
                except (ValueError, TypeError):
                    return 0.0
                    
            def clean_int(val):
                try:
                    return int(float(val)) if pd.notna(val) else 0
                except (ValueError, TypeError):
                    return 0
            
            # Casing matches
            mercado_name = str(row["MERCADO"]).strip().upper() if pd.notna(row["MERCADO"]) else ""
            categoria_name = str(row["CATEGORIA"]).strip().upper() if pd.notna(row["CATEGORIA"]) else ""
            supervisor_name = str(row["SUPERVISOR"]).strip().upper() if pd.notna(row["SUPERVISOR"]) else ""
            reponedor_name = str(row["REPONEDOR"]).strip().upper() if pd.notna(row["REPONEDOR"]) else ""
            
            # Lookup FKs
            id_mercado = mercados_map.get(mercado_name)
            id_categoria = categorias_map.get(categoria_name)
            id_supervisor = usuarios_map.get(supervisor_name)
            id_reponedor = usuarios_map.get(reponedor_name)
            
            # Day indicators: True if contains "x" or "X"
            def check_day(val):
                if pd.isna(val):
                    return False
                return str(val).strip().lower() == "x"
                
            atiende_lunes = check_day(row["LUNES"])
            atiende_martes = check_day(row["MARTES"])
            atiende_miercoles = check_day(row["MIERCOLES"])
            atiende_jueves = check_day(row["JUEVES"])
            atiende_viernes = check_day(row["VIERNES"])
            atiende_sabado = check_day(row["SABADO"])
            atiende_domingo = False  # Not in excel sheet columns
            
            tiempo_visita_min = clean_int(row["TIEMPO_VISITA_MIN"])
            if tiempo_visita_min <= 0:
                # Default fallback if missing
                tiempo_visita_min = 20
                
            pdv = models.PuntoDeVenta(
                codigo_gv=codigo_str,
                codigo_interno=codigo_str,
                nombre_pdv=nombre_str,
                direccion=f"Mercado {row['MERCADO']}" if pd.notna(row["MERCADO"]) else "Dirección no especificada",
                id_mercado=id_mercado,
                id_categoria=id_categoria,
                id_supervisor=id_supervisor,
                id_reponedor_asignado=id_reponedor,
                latitud=clean_float(row["LATITUD"]),
                longitud=clean_float(row["LONGITUD"]),
                tiempo_visita_min=tiempo_visita_min,
                prioridad="media",
                atiende_lunes=atiende_lunes,
                atiende_martes=atiende_martes,
                atiende_miercoles=atiende_miercoles,
                atiende_jueves=atiende_jueves,
                atiende_viernes=atiende_viernes,
                atiende_sabado=atiende_sabado,
                atiende_domingo=atiende_domingo,
                frecuencia_semanal=clean_int(row["FRECUENCIA_SEMANAL"]),
                frecuencia_mensual=clean_int(row["FRECUENCIA_MENSUAL"]),
                tiempo_promedio_min=float(tiempo_visita_min),
                recalibrar=False
            )
            
            db.add(pdv)
            pdv_count += 1
            
        db.commit()
        print(f"Cargados {pdv_count} Puntos de Venta (PDVs) exitosamente en la base de datos v3.0!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding PDVs: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # We must make sure models are mapped before running, but we'll run this script once models.py is updated.
    seed_puntos_de_venta()
