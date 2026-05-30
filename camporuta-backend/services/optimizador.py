import pandas as pd
import math
from sqlalchemy.orm import Session
import models
import logging

logger = logging.getLogger(__name__)

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distancia euclidiana simple entre dos puntos (lat/lon).
    """
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def optimizar_ruta_db(ruta: models.Ruta, db: Session) -> models.Ruta:
    """
    Optimiza el orden de las paradas (RutaPunto) de una ruta utilizando un algoritmo heurístico de vecino más cercano.
    Usa Pandas para estructurar los datos y calcular la secuencia óptima.
    """
    puntos = ruta.ruta_puntos
    if not puntos or len(puntos) <= 1:
        # Nada que optimizar o solo hay una parada
        return ruta

    # Cargar coordenadas en un DataFrame de Pandas
    data = []
    for p in puntos:
        pdv = p.pdv
        if not pdv:
            continue
        data.append({
            "id": p.id_ruta_punto,
            "latitud": float(pdv.latitud),
            "longitud": float(pdv.longitud),
            "punto_obj": p
        })

    if not data:
        return ruta

    df = pd.DataFrame(data)

    # Algoritmo de vecino más cercano (Greedy TSP)
    # Iniciamos en el primer punto de la lista
    ruta_optima_indices = [0]
    indices_restantes = list(range(1, len(df)))

    while indices_restantes:
        ultimo_idx = ruta_optima_indices[-1]
        lat_ult = df.loc[ultimo_idx, "latitud"]
        lon_ult = df.loc[ultimo_idx, "longitud"]

        mejor_dist = float("inf")
        mejor_idx = -1

        for idx in indices_restantes:
            lat_dest = df.loc[idx, "latitud"]
            lon_dest = df.loc[idx, "longitud"]
            dist = calcular_distancia(lat_ult, lon_ult, lat_dest, lon_dest)
            if dist < mejor_dist:
                mejor_dist = dist
                mejor_idx = idx

        ruta_optima_indices.append(mejor_idx)
        indices_restantes.remove(mejor_idx)

    # Actualizar la columna 'orden' de las paradas en la base de datos
    for orden_nuevo, idx in enumerate(ruta_optima_indices):
        punto_obj = df.loc[idx, "punto_obj"]
        punto_obj.orden = orden_nuevo + 1  # 1-indexed for stops
        db.add(punto_obj)

    db.commit()
    db.refresh(ruta)
    
    logger.info(f"Ruta {ruta.id_ruta} optimizada exitosamente. Total paradas ordenadas: {len(puntos)}")
    return ruta
