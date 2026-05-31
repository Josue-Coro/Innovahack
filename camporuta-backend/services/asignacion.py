import math
from sqlalchemy.orm import Session
from sqlalchemy import or_
import models

def get_prioridad_peso(prioridad: str) -> int:
    p = (prioridad or "").lower()
    if p == "alta": return 3
    if p == "media": return 2
    if p == "baja": return 1
    return 2 # por defecto media

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def auto_asignar_pdvs(db: Session):
    # 1. Obtener PDVs sin asignar, ordenados por prioridad
    # SQLAlchemy sorting using CASE or python-side sorting.
    # We will do python-side sorting for simplicity since dataset is small.
    unassigned_pdvs = db.query(models.PuntoDeVenta).filter(
        models.PuntoDeVenta.id_reponedor_asignado == None,
        models.PuntoDeVenta.activo == True
    ).all()
    
    if not unassigned_pdvs:
        return {"asignados": 0, "detalle": []}
        
    # Ordenar por prioridad (Alta primero)
    unassigned_pdvs.sort(key=lambda p: get_prioridad_peso(p.prioridad), reverse=True)
    
    # 2. Cargar Reponedores Activos
    reponedores = db.query(models.Usuario).filter(
        models.Usuario.id_rol == 3,
        models.Usuario.activo == True
    ).all()
    
    if not reponedores:
        return {"error": "No hay reponedores activos para asignar."}
        
    # 3. Construir estado actual de cada reponedor (Centro de gravedad y Calendario)
    dias_semana = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    
    estado_reps = {}
    for rep in reponedores:
        # Obtener PDVs actuales
        pdvs_actuales = db.query(models.PuntoDeVenta).filter(
            models.PuntoDeVenta.id_reponedor_asignado == rep.id_usuario,
            models.PuntoDeVenta.activo == True
        ).all()
        
        # Calendario base
        calendario = {dia: 0 for dia in dias_semana}
        sum_lat = 0.0
        sum_lon = 0.0
        count_geo = 0
        
        for p in pdvs_actuales:
            if p.atiende_lunes: calendario["lunes"] += 1
            if p.atiende_martes: calendario["martes"] += 1
            if p.atiende_miercoles: calendario["miercoles"] += 1
            if p.atiende_jueves: calendario["jueves"] += 1
            if p.atiende_viernes: calendario["viernes"] += 1
            if p.atiende_sabado: calendario["sabado"] += 1
            if p.atiende_domingo: calendario["domingo"] += 1
            
            if p.latitud is not None and p.longitud is not None:
                sum_lat += float(p.latitud)
                sum_lon += float(p.longitud)
                count_geo += 1
                
        lat_cg = None
        lon_cg = None
        
        if count_geo > 0:
            lat_cg = sum_lat / count_geo
            lon_cg = sum_lon / count_geo
        else:
            # Fallback a la posición del perfil
            perfil = rep.perfil_reponedor
            if perfil and perfil.lat_actual is not None and perfil.lon_actual is not None:
                lat_cg = float(perfil.lat_actual)
                lon_cg = float(perfil.lon_actual)
        
        estado_reps[rep.id_usuario] = {
            "lat_cg": lat_cg,
            "lon_cg": lon_cg,
            "calendario": calendario,
            "count_geo": count_geo,
            "sum_lat": sum_lat,
            "sum_lon": sum_lon
        }
        
    # 4. Proceso de asignación Greedy
    asignados_info = []
    
    for pdv in unassigned_pdvs:
        pdv_lat = float(pdv.latitud) if pdv.latitud else 0.0
        pdv_lon = float(pdv.longitud) if pdv.longitud else 0.0
        
        # Encontrar el reponedor más cercano
        mejor_rep_id = None
        mejor_dist = float('inf')
        
        for rep_id, est in estado_reps.items():
            if est["lat_cg"] is not None and est["lon_cg"] is not None:
                dist = calcular_distancia(pdv_lat, pdv_lon, est["lat_cg"], est["lon_cg"])
            else:
                # Si el reponedor no tiene CG (es completamente nuevo y sin GPS), asignamos dist = 0 para darle prioridad
                dist = 0.0 
                
            if dist < mejor_dist:
                mejor_dist = dist
                mejor_rep_id = rep_id
                
        if not mejor_rep_id:
            # Fallback si nadie tiene ubicación (muy raro), tomamos el primero
            mejor_rep_id = reponedores[0].id_usuario
            
        # Asignar Reponedor
        pdv.id_reponedor_asignado = mejor_rep_id
        
        # Asignar Días según frecuencia
        frecuencia = pdv.frecuencia_semanal or 1
        est = estado_reps[mejor_rep_id]
        
        # Ordenar días del reponedor de menor carga a mayor carga
        dias_ordenados = sorted(est["calendario"].items(), key=lambda x: x[1])
        
        # Limpiar banderas de atención del PDV por seguridad
        pdv.atiende_lunes = False
        pdv.atiende_martes = False
        pdv.atiende_miercoles = False
        pdv.atiende_jueves = False
        pdv.atiende_viernes = False
        pdv.atiende_sabado = False
        pdv.atiende_domingo = False
        
        # Tomar los N días menos ocupados
        dias_elegidos = [d[0] for d in dias_ordenados[:frecuencia]]
        
        for dia in dias_elegidos:
            if dia == "lunes": pdv.atiende_lunes = True
            elif dia == "martes": pdv.atiende_martes = True
            elif dia == "miercoles": pdv.atiende_miercoles = True
            elif dia == "jueves": pdv.atiende_jueves = True
            elif dia == "viernes": pdv.atiende_viernes = True
            elif dia == "sabado": pdv.atiende_sabado = True
            elif dia == "domingo": pdv.atiende_domingo = True
            
            # Actualizar calendario local
            est["calendario"][dia] += 1
            
        # Actualizar Centro de Gravedad local
        est["sum_lat"] += pdv_lat
        est["sum_lon"] += pdv_lon
        est["count_geo"] += 1
        est["lat_cg"] = est["sum_lat"] / est["count_geo"]
        est["lon_cg"] = est["sum_lon"] / est["count_geo"]
        
        asignados_info.append({
            "pdv_id": pdv.id_pdv,
            "nombre": pdv.nombre_pdv,
            "reponedor_id": mejor_rep_id,
            "dias_asignados": dias_elegidos
        })
        
    db.commit()
    
    return {
        "asignados": len(asignados_info),
        "detalle": asignados_info
    }
