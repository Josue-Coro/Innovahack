import math
import random
import logging
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

def euclidean_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

def k_means(points, k=6, max_iters=50):
    """
    Agrupa los PDVs geográficamente en K zonas.
    points: lista de dicts [{'id': int, 'lat': float, 'lon': float}]
    Retorna un diccionario {id_pdv: cluster_index}
    """
    if len(points) == 0:
        return {}
    if len(points) <= k:
        return {p['id']: i for i, p in enumerate(points)}

    # Inicializar centroides aleatoriamente seleccionando K puntos
    centroids = random.sample(points, k)
    centroids = [{'lat': c['lat'], 'lon': c['lon']} for c in centroids]

    assignments = {}

    for _ in range(max_iters):
        # Asignar cada punto al centroide más cercano
        clusters = [[] for _ in range(k)]
        new_assignments = {}
        for p in points:
            min_dist = float('inf')
            best_k = 0
            for i, c in enumerate(centroids):
                dist = euclidean_distance(p['lat'], p['lon'], c['lat'], c['lon'])
                if dist < min_dist:
                    min_dist = dist
                    best_k = i
            clusters[best_k].append(p)
            new_assignments[p['id']] = best_k

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Recalcular centroides
        for i in range(k):
            if not clusters[i]:
                continue
            avg_lat = sum(p['lat'] for p in clusters[i]) / len(clusters[i])
            avg_lon = sum(p['lon'] for p in clusters[i]) / len(clusters[i])
            centroids[i] = {'lat': avg_lat, 'lon': avg_lon}

    return assignments

def auto_asignar_dias_reponedor(id_reponedor: int, db: Session):
    """
    Usa clustering para dividir la ciudad en 6 zonas y las reparte de Lunes a Sábado.
    Respeta la frecuencia semanal.
    """
    pdvs = db.query(models.PuntoDeVenta).filter(
        models.PuntoDeVenta.id_reponedor_asignado == id_reponedor,
        models.PuntoDeVenta.activo == True
    ).all()

    if not pdvs:
        return 0

    points = []
    for pdv in pdvs:
        if pdv.latitud and pdv.longitud:
            points.append({
                'id': pdv.id_pdv,
                'lat': float(pdv.latitud),
                'lon': float(pdv.longitud)
            })

    # Dividimos en 6 zonas (Lunes a Sábado)
    k = min(6, len(points))
    assignments = k_means(points, k=k)

    # Días de la semana en base de datos
    attr_dias = [
        "atiende_lunes", "atiende_martes", "atiende_miercoles", 
        "atiende_jueves", "atiende_viernes", "atiende_sabado"
    ]

    for pdv in pdvs:
        if pdv.id_pdv not in assignments:
            continue
            
        cluster_idx = assignments[pdv.id_pdv] # de 0 a 5
        frecuencia = pdv.frecuencia_semanal if pdv.frecuencia_semanal and pdv.frecuencia_semanal > 0 else 1

        # Limpiar días anteriores
        pdv.atiende_lunes = False
        pdv.atiende_martes = False
        pdv.atiende_miercoles = False
        pdv.atiende_jueves = False
        pdv.atiende_viernes = False
        pdv.atiende_sabado = False
        pdv.atiende_domingo = False

        # Asignar el día principal
        setattr(pdv, attr_dias[cluster_idx], True)

        # Si la frecuencia es 2, le asignamos otro día alejado (+3 días)
        if frecuencia >= 2:
            segundo_dia = (cluster_idx + 3) % 6
            setattr(pdv, attr_dias[segundo_dia], True)

        # Si la frecuencia es 3, le asignamos (+2 y +4 días)
        if frecuencia >= 3:
            pdv.atiende_lunes = False
            pdv.atiende_martes = False
            pdv.atiende_miercoles = False
            pdv.atiende_jueves = False
            pdv.atiende_viernes = False
            pdv.atiende_sabado = False
            # Lunes, Miercoles, Viernes (0, 2, 4) o Martes, Jueves, Sabado (1, 3, 5)
            base = cluster_idx % 2
            setattr(pdv, attr_dias[base], True)
            setattr(pdv, attr_dias[base + 2], True)
            setattr(pdv, attr_dias[base + 4], True)

    db.commit()
    return len(pdvs)
