import httpx
import logging
from sqlalchemy.orm import Session
import models
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

async def analizar_comentario(comentario: str) -> str:
    """
    Analiza el sentimiento de un comentario de feedback.
    Simula la llamada a un servicio externo de NLP utilizando HTTPX.
    """
    if not comentario or len(comentario.strip()) == 0:
        return "NEUTRAL"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://httpbin.org/get", params={"text": comentario})
            if response.status_code == 200:
                logger.info("External sentiment service responded successfully.")
                texto = comentario.lower()
                positivas = ["bueno", "excelente", "rápido", "rapido", "amable", "perfecto", "gracias"]
                negativas = ["malo", "lento", "tarde", "demorado", "grosero", "dañado", "roto"]
                
                if any(p in texto for p in positivas):
                    return "POSITIVO"
                elif any(n in texto for n in negativas):
                    return "NEGATIVO"
                
            return "NEUTRAL"
            
    except Exception as e:
        logger.error(f"Error calling external sentiment API via HTTPX: {e}")
        return "NEUTRAL"

def registrar_tiempo_real(visita_id: int, tiempo_real_min: float, db: Session) -> models.Visita:
    """
    Guarda el tiempo real de la visita (simulando hora_llegada y hora_salida),
    calcula la desviación vs tiempo estimado del PDV,
    actualiza el promedio móvil de tiempo real por PDV,
    registra el historial y marca si requiere recalibración (>30%).
    """
    # 1. Buscar la visita
    visita = db.query(models.Visita).filter(models.Visita.id_visita == visita_id).first()
    if not visita:
        raise ValueError(f"Visita con id {visita_id} no encontrada")
    
    # 2. Guardar el tiempo real simulando llegada y salida
    if not visita.hora_llegada:
        visita.hora_llegada = datetime.utcnow()
    visita.hora_salida = visita.hora_llegada + timedelta(minutes=float(tiempo_real_min))
    visita.estado = "completada"
    
    # 3. Buscar el PDV asociado
    pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == visita.id_pdv).first()
    if pdv:
        # Calcular desviación
        tiempo_estimado = pdv.tiempo_visita_min if pdv.tiempo_visita_min else 0
        if tiempo_estimado > 0:
            desviacion = abs(tiempo_real_min - tiempo_estimado) / tiempo_estimado
        else:
            desviacion = 0.0
            
        # Si la desviación supera el 30%, marca el PDV como "recalibrar"
        if desviacion > 0.30:
            pdv.recalibrar = True
            
        # Actualiza promedio móvil del tiempo real por PDV
        # nuevo_promedio = 0.7 * tiempo_historico + 0.3 * tiempo_nuevo
        tiempo_historico = pdv.tiempo_promedio_min if pdv.tiempo_promedio_min is not None else float(pdv.tiempo_visita_min)
        nuevo_promedio = 0.7 * tiempo_historico + 0.3 * tiempo_real_min
        pdv.tiempo_promedio_min = nuevo_promedio

        # 4. Crear registro en historial_tiempos_pdv
        hist = models.HistorialTiempoPDV(
            id_pdv=pdv.id_pdv,
            id_categoria=pdv.id_categoria,
            id_reponedor=visita.id_reponedor,
            fecha=visita.fecha,
            dia_semana=visita.fecha.isoweekday(),  # 1=lun ... 7=dom
            tiempo_real_min=int(tiempo_real_min),
            tiempo_estimado_min=pdv.tiempo_visita_min,
            clima=visita.clima_descripcion,
            habia_quiebre=visita.quiebre_de_stock
        )
        db.add(hist)
        
    db.commit()
    db.refresh(visita)
    if pdv:
        db.refresh(pdv)
    return visita

def sugerir_redistribucion(fecha: Union[str, date, datetime], db: Session) -> List[Dict[str, Any]]:
    """
    Compara la carga real de los reponedores del mismo supervisor en la fecha especificada.
    Si un reponedor tiene más del 20% de sobrecarga vs otro del mismo supervisor,
    genera sugerencias de redistribución de PDVs y las guarda en la tabla redistribuciones_sugeridas.
    """
    # Parsear fecha
    if isinstance(fecha, str):
        fecha_parsed = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()
    elif isinstance(fecha, datetime):
        fecha_parsed = fecha.date()
    else:
        fecha_parsed = fecha

    # 1. Obtener todas las rutas del día
    rutas = db.query(models.Ruta).filter(models.Ruta.fecha == fecha_parsed).all()
    if not rutas:
        return []

    # 2. Calcular carga real y planificada por reponedor
    reponedor_data = {}
    for r in rutas:
        rep = db.query(models.Usuario).filter(models.Usuario.id_usuario == r.id_reponedor).first()
        if not rep:
            continue

        # Carga real: suma de duracion_real_min de visitas completadas
        visitas = db.query(models.Visita).filter(
            models.Visita.id_reponedor == rep.id_usuario,
            models.Visita.fecha == fecha_parsed,
            models.Visita.estado == "completada"
        ).all()
        
        carga_real = 0.0
        for v in visitas:
            # We can use hora_salida and hora_llegada difference to be safe
            if v.hora_salida and v.hora_llegada:
                dur = (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
                carga_real += dur
            elif v.duracion_real_min is not None:
                carga_real += v.duracion_real_min

        # Carga planificada: suma de tiempo_visita_min de todos los puntos de la ruta
        puntos = db.query(models.RutaPunto).filter(models.RutaPunto.id_ruta == r.id_ruta).all()
        carga_planificada = 0.0
        pdvs_ruta = []
        for p in puntos:
            pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == p.id_pdv).first()
            if pdv:
                carga_planificada += pdv.tiempo_visita_min
                pdvs_ruta.append(pdv)

        reponedor_data[rep.id_usuario] = {
            "usuario": rep,
            "carga_real": carga_real,
            "carga_planificada": carga_planificada,
            "pdvs": pdvs_ruta,
            "id_supervisor": rep.id_supervisor
        }

    # 3. Agrupar por supervisor
    supervisor_groups = {}
    for rep_id, data in reponedor_data.items():
        sup_id = data["id_supervisor"]
        if not sup_id:
            continue
        if sup_id not in supervisor_groups:
            supervisor_groups[sup_id] = []
        supervisor_groups[sup_id].append(data)

    sugerencias_ret = []

    # 4. Comparar y generar sugerencias
    for sup_id, reps in supervisor_groups.items():
        if len(reps) < 2:
            continue

        for i in range(len(reps)):
            for j in range(len(reps)):
                if i == j:
                    continue
                data_A = reps[i]
                data_B = reps[j]

                carga_A = data_A["carga_real"]
                carga_B = data_B["carga_real"]

                # Si A tiene >20% de sobrecarga vs B (y B tiene carga > 0)
                if carga_B > 0 and carga_A > 1.2 * carga_B:
                    dif_objetivo = (carga_A - carga_B) / 2.0

                    # Ordenar PDVs de A de menor a mayor tiempo estimado
                    pdvs_A_ordenados = sorted(data_A["pdvs"], key=lambda x: x.tiempo_visita_min)
                    
                    pdvs_a_mover = []
                    tiempo_acumulado = 0.0

                    for pdv in pdvs_A_ordenados:
                        if (tiempo_acumulado + pdv.tiempo_visita_min) <= dif_objetivo:
                            pdvs_a_mover.append(pdv)
                            tiempo_acumulado += pdv.tiempo_visita_min

                    # Forzar al menos un PDV si corresponde
                    if not pdvs_a_mover and pdvs_A_ordenados:
                        pdv = pdvs_A_ordenados[0]
                        pdvs_a_mover.append(pdv)
                        tiempo_acumulado = pdv.tiempo_visita_min

                    if pdvs_a_mover:
                        # Guardar sugerencias en la base de datos
                        for pdv in pdvs_a_mover:
                            # Evitar duplicados para la misma fecha, origen, destino y pdv
                            existente = db.query(models.RedistribucionSugerida).filter(
                                models.RedistribucionSugerida.fecha_para == fecha_parsed,
                                models.RedistribucionSugerida.id_reponedor_origen == data_A["usuario"].id_usuario,
                                models.RedistribucionSugerida.id_reponedor_destino == data_B["usuario"].id_usuario,
                                models.RedistribucionSugerida.id_pdv == pdv.id_pdv
                            ).first()

                            if not existente:
                                sug_db = models.RedistribucionSugerida(
                                    fecha_para=fecha_parsed,
                                    id_reponedor_origen=data_A["usuario"].id_usuario,
                                    id_reponedor_destino=data_B["usuario"].id_usuario,
                                    id_pdv=pdv.id_pdv,
                                    motivo="sobrecarga_tiempo",
                                    motivo_detalle=f"Sobrecarga de {data_A['usuario'].nombre} ({int(carga_A)} min) vs {data_B['usuario'].nombre} ({int(carga_B)} min)",
                                    ahorro_tiempo_min=int(pdv.tiempo_visita_min),
                                    estado="pendiente"
                                )
                                db.add(sug_db)

                        db.commit()

                        sugerencias_ret.append({
                            "reponedor_origen": data_A["usuario"].nombre,
                            "reponedor_destino": data_B["usuario"].nombre,
                            "pdvs_a_mover": [p.codigo_gv for p in pdvs_a_mover],
                            "ahorro_tiempo_min": int(tiempo_acumulado)
                        })

    return sugerencias_ret

def get_metricas_dia(fecha: Union[str, date, datetime], reponedor_id_or_obj: Any, db: Session) -> Dict[str, Any]:
    """
    Retorna métricas operativas del día para un reponedor específico.
    """
    # Parsear fecha
    if isinstance(fecha, str):
        fecha_parsed = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()
    elif isinstance(fecha, datetime):
        fecha_parsed = fecha.date()
    else:
        fecha_parsed = fecha

    # Resolver id_reponedor
    if hasattr(reponedor_id_or_obj, 'id_usuario'):
        id_reponedor = reponedor_id_or_obj.id_usuario
    elif isinstance(reponedor_id_or_obj, int) or (isinstance(reponedor_id_or_obj, str) and reponedor_id_or_obj.isdigit()):
        id_reponedor = int(reponedor_id_or_obj)
    else:
        # Buscar por nombre o email
        usuario = db.query(models.Usuario).filter(
            (models.Usuario.nombre == str(reponedor_id_or_obj)) | 
            (models.Usuario.email == str(reponedor_id_or_obj))
        ).first()
        if usuario:
            id_reponedor = usuario.id_usuario
        else:
            return {
                "cobertura_pct": 0.0,
                "tiempos_por_categoria": {},
                "mayores_desviaciones": [],
                "eficiencia": 0.0
            }

    # 1. Obtener visitas del reponedor en el día
    visitas = db.query(models.Visita).filter(
        models.Visita.fecha == fecha_parsed,
        models.Visita.id_reponedor == id_reponedor
    ).all()

    if not visitas:
        return {
            "cobertura_pct": 0.0,
            "tiempos_por_categoria": {},
            "mayores_desviaciones": [],
            "eficiencia": 0.0
        }

    total_visitas = len(visitas)
    completadas = 0
    tiempos_cat = {}
    desviaciones = []
    
    total_real = 0.0
    total_estimado = 0.0

    for v in visitas:
        pdv = db.query(models.PuntoDeVenta).filter(models.PuntoDeVenta.id_pdv == v.id_pdv).first()
        if not pdv:
            continue
            
        t_est = pdv.tiempo_visita_min or 0
        total_estimado += t_est
        
        is_completed = (v.estado == "completada")
        if is_completed:
            completadas += 1
            t_real = 0.0
            if v.hora_salida and v.hora_llegada:
                t_real = (v.hora_salida - v.hora_llegada).total_seconds() / 60.0
            elif v.duracion_real_min is not None:
                t_real = float(v.duracion_real_min)
                
            total_real += t_real
            
            # Agrupar por categoría
            cat_obj = db.query(models.CategoriaCliente).filter(models.CategoriaCliente.id_categoria == pdv.id_categoria).first()
            cat = cat_obj.nombre if cat_obj else "Sin Categoria"
            if cat not in tiempos_cat:
                tiempos_cat[cat] = {"real": [], "estimado": []}
            tiempos_cat[cat]["real"].append(t_real)
            tiempos_cat[cat]["estimado"].append(t_est)
            
            # Calcular desviación absoluta
            desv = abs(t_real - t_est)
            desviaciones.append({
                "codigo": pdv.codigo_gv,
                "nombre": pdv.nombre_pdv or pdv.direccion or f"PDV_{pdv.id_pdv}",
                "desviacion_min": desv
            })

    # Calcular % cobertura
    cobertura_pct = (completadas / total_visitas) * 100.0 if total_visitas > 0 else 0.0

    # Calcular tiempos promedio por categoría
    tiempos_por_categoria = {}
    for cat, values in tiempos_cat.items():
        tiempos_por_categoria[cat] = {
            "promedio_real": sum(values["real"]) / len(values["real"]) if values["real"] else 0.0,
            "promedio_estimado": sum(values["estimado"]) / len(values["estimado"]) if values["estimado"] else 0.0
        }

    # Ordenar mayores desviaciones desc y tomar las top 5
    mayores_desviaciones = sorted(desviaciones, key=lambda x: x["desviacion_min"], reverse=True)[:5]

    # Calcular eficiencia
    cobertura_ratio = completadas / total_visitas if total_visitas > 0 else 0.0
    if total_real > 0:
        time_factor = min(1.0, total_estimado / total_real)
    else:
        time_factor = 1.0 if total_visitas == 0 else 0.0
        
    eficiencia = (cobertura_ratio * time_factor) * 100.0

    return {
        "cobertura_pct": round(cobertura_pct, 2),
        "tiempos_por_categoria": tiempos_por_categoria,
        "mayores_desviaciones": mayores_desviaciones,
        "eficiencia": round(eficiencia, 2)
    }
