"""
Упрощенная функция стоимости для тестирования
"""

import numpy as np
from typing import Tuple, Dict
from src.utils.geo_utils import haversine_distance, grid_to_coord


def calculate_edge_cost_with_static_ice(current: Tuple[int, int],
                                        neighbor: Tuple[int, int],
                                        lats: np.ndarray,
                                        lons: np.ndarray,
                                        ice_data: Dict,
                                        ship_params: Dict,
                                        land_mask: np.ndarray = None) -> float:
    """
    Упрощенная функция стоимости:
    - Суша = бесконечная стоимость
    - Вода = расстояние / скорость
    """

    # 1. ПРОВЕРКА СУШИ - самое важное!
    if land_mask is not None:
        if land_mask[neighbor]:
            return float('inf')  # Суша - непроходимо

    # 2. Расчет расстояния
    current_coord = grid_to_coord(current, lats, lons)
    neighbor_coord = grid_to_coord(neighbor, lats, lons)
    distance_km = haversine_distance(current_coord, neighbor_coord)

    # 3. Базовая скорость (без учета льда пока)
    base_speed = ship_params.get('open_water_speed', 15)  # узлы

    # 4. Время в часах
    time_hours = distance_km / (base_speed * 1.852)  # 1 узел = 1.852 км/ч

    # 5. Можно добавить учет льда (опционально)
    ice_penalty = 1.0

    # Проверяем, есть ли лед в этой точке
    neighbor_lat, neighbor_lon = neighbor_coord

    for zone in ice_data.get('zones', []):
        if is_point_in_ice_zone(neighbor_lat, neighbor_lon, zone):
            # Увеличиваем стоимость в зависимости от ледовитости
            ice_concentration = zone.get('ice_concentration', 0.5)
            ice_thickness = zone.get('ice_thickness', 0.5)

            # Простой штраф: чем больше льда, тем выше стоимость
            ice_penalty = 1.0 + (ice_concentration * 2.0)  # 1.0 до 3.0x

            # Если лед слишком толстый для судна
            max_ice = ship_params.get('max_ice_thickness', 1.5)
            if ice_thickness > max_ice:
                ice_penalty *= 2.0  # Двойной штраф

            break

    return time_hours * ice_penalty


def is_point_in_ice_zone(lat: float, lon: float, zone: Dict) -> bool:
    """Проверяет, находится ли точка в ледовой зоне"""
    coords = zone.get('coordinates', [])
    if len(coords) < 3:
        return False

    # Простая проверка по прямоугольнику
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
