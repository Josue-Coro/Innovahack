import os
import httpx
import logging
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
ORS_API_KEY = os.getenv("ORS_API_KEY")

async def get_directions(coordinates: List[List[float]]) -> Tuple[Dict[str, Any], float, float, List[float]]:
    """
    Llama a OpenRouteService para obtener la ruta óptima por calles dado un arreglo de coordenadas ordenadas.
    coordinates: [[lon, lat], [lon, lat], ...]
    
    Retorna:
    - polyline: Un string codificado o diccionario con la geometría (depende del formato, usamos geojson).
    - distancia_total_km: Distancia total del recorrido.
    - duracion_total_min: Duración total en minutos.
    - duraciones_tramos_min: Lista con la duración en minutos de cada tramo (entre punto i y punto i+1).
    """
    if not ORS_API_KEY:
        logger.warning("ORS_API_KEY no configurada. Simulando ruta lineal.")
        return None, 0.0, 0.0, [0.0] * (len(coordinates) - 1)

    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json; charset=utf-8'
    }
    body = {
        "coordinates": coordinates,
        "instructions": False
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers, timeout=15.0)
            response.raise_for_status()
            
            data = response.json()
            
            if "features" not in data or len(data["features"]) == 0:
                raise ValueError("ORS no devolvió rutas válidas.")

            # Extraemos la ruta principal
            ruta_feature = data["features"][0]
            
            # Polyline GeoJSON format
            polyline_json = ruta_feature["geometry"]
            
            # Propiedades (resumen)
            properties = ruta_feature["properties"]
            summary = properties["summary"]
            distancia_total_km = summary["distance"] / 1000.0
            duracion_total_min = summary["duration"] / 60.0
            
            # Tramos individuales para los ETAs
            segments = properties["segments"]
            duraciones_tramos_min = [seg["duration"] / 60.0 for seg in segments]

            return polyline_json, distancia_total_km, duracion_total_min, duraciones_tramos_min
            
    except Exception as e:
        logger.error(f"Error al consultar OpenRouteService: {e}")
        return None, 0.0, 0.0, [0.0] * (len(coordinates) - 1)
