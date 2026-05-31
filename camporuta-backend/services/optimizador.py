import math
from sqlalchemy.orm import Session
import models
import logging

logger = logging.getLogger(__name__)

# Mapa de prioridad a peso numerico
PRIORIDAD_PESO = {"alta": 3, "media": 2, "baja": 1}

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia euclidiana simple entre dos puntos (lat/lon)."""
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def _obtener_tiempo_ema(db: Session, id_pdv: int, fallback_min: float = 15.0) -> float:
    """Devuelve el tiempo promedio EMA del PDV, o el fallback si no hay datos."""
    metrica = db.query(models.MetricaPdv).filter(
        models.MetricaPdv.id_pdv == id_pdv
    ).first()
    if metrica and metrica.visitas_contadas > 0:
        return float(metrica.tiempo_promedio_min)
    return fallback_min


def _costo_heuristico(
    lat_actual: float, lon_actual: float,
    lat_dest: float, lon_dest: float,
    prioridad: str, tiempo_ema_min: float
) -> float:
    """
    Calcula el costo heuristico para ir al siguiente nodo.
    Formula: Costo = (Distancia / log(Prioridad + 1)) + (TiempoOperativo * Factor)

    - Dividir por log(prioridad+1) hace que los PDVs de alta prioridad tengan un
      costo efectivo MENOR, por lo que son preferidos en la seleccion.
    - Sumar el tiempo operativo penaliza los nodos que tomaran mucho tiempo al final
      del dia (evita acumular tiendas pesadas al cierre).
    """
    dist = calcular_distancia(lat_actual, lon_actual, lat_dest, lon_dest)
    peso = PRIORIDAD_PESO.get(str(prioridad).lower(), 2)

    # Penalizacion logaritmica: mayor prioridad -> menor divisor -> menor costo -> preferido
    costo_distancia = dist / math.log(peso + 1)

    # Factor de tiempo operativo (0.0001 para normalizar respecto a las coordenadas)
    factor_tiempo = 0.0001
    costo_tiempo = tiempo_ema_min * factor_tiempo

    return costo_distancia + costo_tiempo


def optimizar_ruta_db(
    ruta: models.Ruta,
    db: Session,
    lat_inicio: float = None,
    lon_inicio: float = None
) -> models.Ruta:
    """
    Optimiza el orden de las paradas (RutaPunto) de una ruta usando el
    algoritmo heuristico de vecino mas cercano, con penalizacion logaritmica
    por prioridad del PDV y tiempo operativo historico (EMA).

    La respuesta de la ruta mantiene exactamente la misma estructura JSON que antes.
    """
    puntos = ruta.ruta_puntos
    if not puntos or len(puntos) <= 1:
        return ruta

    # Construir lista de candidatos
    data = []
    for p in puntos:
        pdv = p.pdv
        if not pdv:
            continue
        tiempo_ema = _obtener_tiempo_ema(db, p.id_pdv, fallback_min=float(pdv.tiempo_visita_min or 15))
        data.append({
            "id_ruta_punto": p.id_ruta_punto,
            "latitud": float(pdv.latitud),
            "longitud": float(pdv.longitud),
            "prioridad": pdv.prioridad or "media",
            "tiempo_ema_min": tiempo_ema,
            "punto_obj": p,
        })

    if not data:
        return ruta

    ruta_optima = []
    restantes = list(range(len(data)))

    # Punto de partida
    if lat_inicio is not None and lon_inicio is not None:
        lat_ult, lon_ult = lat_inicio, lon_inicio
    else:
        primer_idx = restantes.pop(0)
        ruta_optima.append(primer_idx)
        lat_ult = data[primer_idx]["latitud"]
        lon_ult = data[primer_idx]["longitud"]

    # Greedy TSP con costo heuristico logaritmico
    while restantes:
        mejor_costo = float("inf")
        mejor_idx = -1

        for idx in restantes:
            costo = _costo_heuristico(
                lat_ult, lon_ult,
                data[idx]["latitud"], data[idx]["longitud"],
                data[idx]["prioridad"],
                data[idx]["tiempo_ema_min"]
            )
            if costo < mejor_costo:
                mejor_costo = costo
                mejor_idx = idx

        ruta_optima.append(mejor_idx)
        restantes.remove(mejor_idx)
        lat_ult = data[mejor_idx]["latitud"]
        lon_ult = data[mejor_idx]["longitud"]

    # Escribir el nuevo orden en la BD
    for orden_nuevo, idx in enumerate(ruta_optima):
        punto_obj = data[idx]["punto_obj"]
        punto_obj.orden = orden_nuevo + 1
        db.add(punto_obj)

    db.commit()
    db.refresh(ruta)

    logger.info(
        f"Ruta {ruta.id_ruta} optimizada (logaritmica+EMA). "
        f"Total paradas: {len(ruta_optima)}"
    )
    return ruta
