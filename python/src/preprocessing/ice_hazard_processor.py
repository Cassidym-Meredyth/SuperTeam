import numpy as np
from typing import Dict, List, Tuple
from config.ice_hazard_zones import ICE_HAZARD_ZONES, ICE_POINT_HAZARDS


def point_in_polygon(point: Tuple[float, float],
                     polygon: List[Tuple[float, float]]) -> bool:
    """Проверка, находится ли точка внутри полигона (Ray casting algorithm)"""
    x, y = point
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def haversine_distance(coord1: Tuple[float, float],
                       coord2: Tuple[float, float]) -> float:
    """Расстояние между точками в км"""
    R = 6371
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c


def get_ice_conditions_at_point(lat: float, lon: float) -> Dict:
    """Получение ледовых условий в точке на основе статических зон"""

    point = (lat, lon)
    ice_data = {
        'concentration': 0.0,
        'thickness': 0.0,
        'severity': 'none',
        'zone_name': 'open_water'
    }

    # Проверка полигональных зон
    for zone in ICE_HAZARD_ZONES:
        if point_in_polygon(point, zone['coordinates']):
            # Если точка в нескольких зонах, берем максимальную опасность
            if zone['ice_concentration'] > ice_data['concentration']:
                ice_data['concentration'] = zone['ice_concentration']
                ice_data['thickness'] = zone['ice_thickness']
                ice_data['severity'] = zone['severity']
                ice_data['zone_name'] = zone['name']

    # Проверка точечных опасностей
    for hazard in ICE_POINT_HAZARDS:
        hazard_point = (hazard['lat'], hazard['lon'])
        distance = haversine_distance(point, hazard_point)

        if distance <= hazard['radius_km']:
            # Увеличение концентрации льда пропорционально близости
            proximity_factor = 1 - (distance / hazard['radius_km'])
            additional_ice = 0.5 * proximity_factor

            ice_data['concentration'] = min(1.0,
                                            ice_data['concentration'] + additional_ice)
            ice_data['thickness'] = max(ice_data['thickness'],
                                        0.6 * proximity_factor)
            if ice_data['severity'] == 'none':
                ice_data['severity'] = hazard['severity']

    return ice_data


def create_ice_grid(lats: np.ndarray, lons: np.ndarray) -> Dict:
    """Создание сетки ледовых условий для всей акватории"""

    ice_grid = {
        'concentration': np.zeros((len(lats), len(lons))),
        'thickness': np.zeros((len(lats), len(lons))),
        'severity': np.empty((len(lats), len(lons)), dtype=object)
    }

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            conditions = get_ice_conditions_at_point(lat, lon)
            ice_grid['concentration'][i, j] = conditions['concentration']
            ice_grid['thickness'][i, j] = conditions['thickness']
            ice_grid['severity'][i, j] = conditions['severity']

    return ice_grid