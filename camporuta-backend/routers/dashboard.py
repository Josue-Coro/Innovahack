from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import models
import schemas
from database import get_db
from services.feedback import get_metricas_dia
from datetime import datetime, date, timedelta
import io
import csv
from fastapi.responses import StreamingResponse
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary for weather cache
weather_cache = {}

# WMO Weather interpretation codes
def get_weather_description(code: int) -> str:
    wmo_codes = {
        0: "Cielo despejado",
        1: "Principalmente despejado",
        2: "Parcialmente nublado",
        3: "Cubierto",
        45: "Niebla",
        48: "Niebla de escarcha depositada",
        51: "Llovizna ligera",
        53: "Llovizna moderada",
        55: "Llovizna densa",
        56: "Llovizna helada ligera",
        57: "Llovizna helada densa",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia fuerte",
        66: "Lluvia helada ligera",
        67: "Lluvia helada fuerte",
        71: "Nevada ligera",
        73: "Nevada moderada",
        75: "Nevada fuerte",
        77: "Granos de nieve",
        80: "Lluvia ligera con chubascos",
        81: "Lluvia moderada con chubascos",
        82: "Lluvia violenta con chubascos",
        85: "Chubascos de nieve ligeros",
        86: "Chubascos de nieve fuertes",
        95: "Tormenta ligera o moderada",
        96: "Tormenta con granizo ligero",
        97: "Tormenta con granizo fuerte"
    }
    return wmo_codes.get(code, "Condiciones desconocidas")

def parse_date(fecha_str: str) -> date:
    try:
        return datetime.strptime(fecha_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

router = APIRouter(
    tags=["Dashboard"]
)

# 1. Existing metrics endpoint
@router.get("/dashboard/metrics", response_model=schemas.DashboardMetrics)
def obtener_metricas(db: Session = Depends(get_db)):
    total_rutas = db.query(models.Ruta.id_ruta).count()
    total_visitas = db.query(models.Visita.id_visita).count()

    visitas_completadas = db.query(models.Visita.id_visita).filter(models.Visita.estado == "completada").count()
    visitas_pendientes = db.query(models.Visita.id_visita).filter(models.Visita.estado == "pendiente").count()
    visitas_canceladas = db.query(models.Visita.id_visita).filter(models.Visita.estado == "cancelada").count()

    promedio_calificacion = 0.0  # Feedback table deprecated in v3.0
    
    eficiencia = 0.0
    if total_visitas > 0:
        eficiencia = (visitas_completadas / total_visitas) * 100.0

    return schemas.DashboardMetrics(
        total_rutas=total_rutas,
        total_visitas=total_visitas,
        visitas_completadas=visitas_completadas,
        visitas_pendientes=visitas_pendientes,
        visitas_canceladas=visitas_canceladas,
        promedio_calificacion=round(promedio_calificacion, 2),
        eficiencia_ruta_pct=round(eficiencia, 2)
    )

# 2. Dashboard KPIs for a specific date
@router.get("/dashboard/metricas/{fecha}")
def metricas_dashboard(fecha: str, db: Session = Depends(get_db)):
    fecha_parsed = parse_date(fecha)
    
    visitas = db.query(models.Visita).filter(models.Visita.fecha == fecha_parsed).all()
    
    if not visitas:
        return {
            "total_asignados": 0,
            "total_completados": 0,
            "cobertura_por_supervisor": {},
            "cobertura_por_mercado": {},
            "top_reponedores_eficientes": [],
            "pdvs_no_visitados": [],
            "tiempo_promedio_categoria": {
                "MAYORISTA": {"real": 0.0, "estimado": 0.0},
                "MINORISTA": {"real": 0.0, "estimado": 0.0},
                "DETALLISTA": {"real": 0.0, "estimado": 0.0}
            }
        }
    
    total_asignados = len(visitas)
    total_completados = sum(1 for v in visitas if v.estado == "completada")
    
    supervisor_counts = {}
    mercado_counts = {}
    reponedor_visits = {}
    pdvs_no_visitados = []
    
    categoria_times = {
        "MAYORISTA": {"real": [], "estimado": []},
        "MINORISTA": {"real": [], "estimado": []},
        "DETALLISTA": {"real": [], "estimado": []}
    }
    
    for v in visitas:
        is_completed = (v.estado == "completada")
        pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == v.id_pdv).first()
        
        # Supervisor
        sup_name = "SIN_SUPERVISOR"
        if pdv and pdv.id_supervisor:
            sup_user = db.query(models.Usuario).filter(models.Usuario.id_usuario == pdv.id_supervisor).first()
            if sup_user:
                sup_name = sup_user.nombre
                
        if sup_name not in supervisor_counts:
            supervisor_counts[sup_name] = {"total": 0, "completadas": 0}
        supervisor_counts[sup_name]["total"] += 1
        if is_completed:
            supervisor_counts[sup_name]["completadas"] += 1
            
        # Mercado/Zona
        merc_name = "SIN_MERCADO"
        if pdv and pdv.id_mercado:
            merc = db.query(models.Mercado).filter(models.Mercado.id_mercado == pdv.id_mercado).first()
            if merc:
                merc_name = merc.nombre
                
        if merc_name not in mercado_counts:
            mercado_counts[merc_name] = {"total": 0, "completadas": 0}
        mercado_counts[merc_name]["total"] += 1
        if is_completed:
            mercado_counts[merc_name]["completadas"] += 1
            
        # Reponedor
        rep_name = "SIN_REPONEDOR"
        rep_user = db.query(models.Usuario).filter(models.Usuario.id_usuario == v.id_reponedor).first()
        if rep_user:
            rep_name = rep_user.nombre
            
        if rep_name not in reponedor_visits:
            reponedor_visits[rep_name] = []
        reponedor_visits[rep_name].append((v, pdv))
        
        # PDVs no visitados
        if not is_completed:
            pdvs_no_visitados.append({
                "pdv_codigo": pdv.codigo_gv if pdv else f"VISITA_{v.id_visita}",
                "pdv_nombre": pdv.nombre_pdv if (pdv and pdv.nombre_pdv) else (pdv.direccion if pdv else "Sin Nombre"),
                "latitud": float(pdv.latitud) if pdv else 0.0,
                "longitud": float(pdv.longitud) if pdv else 0.0
            })
            
        # Tiempos promedio por categoría (solo para visitas completadas)
        if is_completed and pdv and pdv.id_categoria:
            cat_obj = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == pdv.id_categoria).first()
            if cat_obj:
                cat_name = cat_obj.nombre.upper().strip()
                if cat_name in categoria_times:
                    t_real = 0.0
                    if v.hora_salida and v.hora_llegada:
                        t_real = (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
                    elif v.duracion_real_min is not None:
                        t_real = float(v.duracion_real_min)
                        
                    t_est = float(pdv.tiempo_visita_min) if pdv.tiempo_visita_min else 0.0
                    categoria_times[cat_name]["real"].append(t_real)
                    categoria_times[cat_name]["estimado"].append(t_est)
                
    # Calculate coverage percentages
    cobertura_por_supervisor = {}
    for sup, counts in supervisor_counts.items():
        cobertura_por_supervisor[sup] = round((counts["completadas"] / counts["total"]) * 100.0, 2)
        
    cobertura_por_mercado = {}
    for merc, counts in mercado_counts.items():
        cobertura_por_mercado[merc] = round((counts["completadas"] / counts["total"]) * 100.0, 2)
        
    # Calculate efficiency for each reponedor
    reponedor_eff = []
    for rep, items in reponedor_visits.items():
        if rep == "SIN_REPONEDOR":
            continue
        tot_vis = len(items)
        comp_vis = sum(1 for v, p in items if v.estado == "completada")
        
        tot_real = 0.0
        for v, p in items:
            if v.estado == "completada":
                if v.hora_salida and v.hora_llegada:
                    tot_real += (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
                elif v.duracion_real_min is not None:
                    tot_real += v.duracion_real_min
                    
        tot_est = sum((p.tiempo_visita_min if p else 0.0) for v, p in items)
        
        cobertura_ratio = comp_vis / tot_vis if tot_vis > 0 else 0.0
        if tot_real > 0:
            time_factor = min(1.0, tot_est / tot_real)
        else:
            time_factor = 1.0 if tot_vis == 0 else 0.0
            
        eff = round((cobertura_ratio * time_factor) * 100.0, 2)
        reponedor_eff.append({
            "reponedor_id": rep,
            "eficiencia": eff
        })
        
    top_reponedores = sorted(reponedor_eff, key=lambda x: x["eficiencia"], reverse=True)[:3]
    
    # Calculate average times by category
    tiempo_promedio_categoria = {}
    for cat, times in categoria_times.items():
        tiempo_promedio_categoria[cat] = {
            "real": round(sum(times["real"]) / len(times["real"]), 2) if times["real"] else 0.0,
            "estimado": round(sum(times["estimado"]) / len(times["estimado"]), 2) if times["estimado"] else 0.0
        }
        
    return {
        "total_asignados": total_asignados,
        "total_completados": total_completados,
        "cobertura_por_supervisor": cobertura_por_supervisor,
        "cobertura_por_mercado": cobertura_por_mercado,
        "top_reponedores_eficientes": top_reponedores,
        "pdvs_no_visitados": pdvs_no_visitados,
        "tiempo_promedio_categoria": tiempo_promedio_categoria
    }

# 3. Individual reponedor metrics and visits for a specific date
@router.get("/dashboard/reponedor/{reponedor_id}/{fecha}")
def metricas_reponedor(reponedor_id: int, fecha: str, db: Session = Depends(get_db)):
    fecha_parsed = parse_date(fecha)
    
    # Get metrics using existing service
    metricas = get_metricas_dia(fecha_parsed, reponedor_id, db)
    
    # Get visits for this reponedor on this date
    visitas = db.query(models.Visita).filter(
        models.Visita.fecha == fecha_parsed,
        models.Visita.id_reponedor == reponedor_id
    ).order_by(models.Visita.id_visita.asc()).all()
    
    lista_visitas = []
    desviaciones = []
    
    for v in visitas:
        pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == v.id_pdv).first()
        t_real = 0.0
        if v.estado == "completada":
            if v.hora_salida and v.hora_llegada:
                t_real = (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
            elif v.duracion_real_min is not None:
                t_real = float(v.duracion_real_min)
                
        t_est = float(pdv.tiempo_visita_min) if pdv else 0.0
        
        lista_visitas.append({
            "visita_id": v.id_visita,
            "cliente_nombre": pdv.nombre_pdv if pdv else "Sin Nombre",
            "estado": v.estado,
            "tiempo_real_min": round(t_real, 2),
            "tiempo_estimado_min": t_est
        })
        
        # Deviation per PDV
        if v.estado == "completada" and pdv:
            desviacion = t_real - t_est
            desviaciones.append({
                "pdv_codigo": pdv.codigo_gv,
                "pdv_nombre": pdv.nombre_pdv,
                "desviacion_min": round(desviacion, 2)
            })
            
    return {
        "metricas": metricas,
        "visitas": lista_visitas,
        "desviaciones": desviaciones
    }

# 4. Export visits of a specific date to CSV
@router.get("/reporte/exportar/{fecha}")
def exportar_reporte(fecha: str, db: Session = Depends(get_db)):
    fecha_parsed = parse_date(fecha)
    
    visitas = db.query(models.Visita).filter(models.Visita.fecha == fecha_parsed).all()
    
    def generate():
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',')
        
        # Write CSV Headers
        writer.writerow([
            "reponedor", "pdv_codigo", "pdv_nombre", "categoria", "mercado",
            "hora_inicio", "hora_fin", "tiempo_real_min", "tiempo_estimado_min",
            "desviacion_min", "estado", "notas"
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        
        for v in visitas:
            rep_user = db.query(models.Usuario).filter(models.Usuario.id_usuario == v.id_reponedor).first()
            pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == v.id_pdv).first()
            
            t_real = None
            if v.estado == "completada":
                if v.hora_salida and v.hora_llegada:
                    t_real = (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
                elif v.duracion_real_min is not None:
                    t_real = float(v.duracion_real_min)
            
            t_est = float(pdv.tiempo_visita_min) if pdv else None
            
            desviacion = None
            if t_real is not None and t_est is not None:
                desviacion = round(t_real - t_est, 2)
                
            cat_name = ""
            if pdv and pdv.id_categoria:
                cat_obj = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == pdv.id_categoria).first()
                if cat_obj:
                    cat_name = cat_obj.nombre
                    
            merc_name = ""
            if pdv and pdv.id_mercado:
                merc_obj = db.query(models.Mercado).filter(models.Mercado.id_mercado == pdv.id_mercado).first()
                if merc_obj:
                    merc_name = merc_obj.nombre
                    
            writer.writerow([
                rep_user.nombre if rep_user else "",
                pdv.codigo_gv if pdv else "",
                (pdv.nombre_pdv if pdv else "Sin Nombre") or "",
                cat_name,
                merc_name,
                v.hora_llegada.strftime("%H:%M:%S") if v.hora_llegada else "",
                v.hora_salida.strftime("%H:%M:%S") if v.hora_salida else "",
                round(t_real, 2) if t_real is not None else "",
                t_est if t_est is not None else "",
                desviacion if desviacion is not None else "",
                v.estado or "",
                v.notas or ""
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
    headers = {
        "Content-Disposition": f"attachment; filename=reporte_{fecha}.csv"
    }
    return StreamingResponse(generate(), media_type="text/csv", headers=headers)

# 5. Weather forecast for a specific location (with 30-min cache)
@router.get("/clima/{lat}/{lon}")
async def consultar_clima(lat: float, lon: float):
    cache_key = (round(lat, 4), round(lon, 4))
    now = datetime.now()
    
    if cache_key in weather_cache:
        cached = weather_cache[cache_key]
        if now - cached["timestamp"] < timedelta(minutes=30):
            logger.info(f"Returning cached weather for coordinates {cache_key}")
            return cached["data"]
            
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation,temperature_2m,weathercode"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Error de comunicación con Open-Meteo API")
                
            data = response.json()
            current = data.get("current", {})
            temp = current.get("temperature_2m", 0.0)
            precip = current.get("precipitation", 0.0)
            wcode = current.get("weathercode", 0)
            desc = get_weather_description(wcode)
            
            result = {
                "temperatura": temp,
                "precipitacion": precip,
                "descripcion": desc
            }
            
            # Cache response
            weather_cache[cache_key] = {
                "data": result,
                "timestamp": now
            }
            
            return result
    except Exception as e:
        logger.error(f"Error querying weather: {e}")
        raise HTTPException(status_code=500, detail=f"No se pudo consultar el clima: {str(e)}")
