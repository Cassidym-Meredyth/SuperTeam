"""
Маска из Natural Earth (config/ne_10m_land.json)
"""

import numpy as np
import json
import os
from typing import Tuple, List


PORTS = {
    'murmansk': {'coord': (69.04, 33.05), 'radius': 0.4},
    'kola': {'coord': (69.33, 36.50), 'radius': 0.4}
}

NE_POLYGONS = []


def is_near_port(lat: float, lon: float) -> bool:
    for port_data in PORTS.values():
        dist = np.sqrt((lat - port_data['coord'][0])**2 + (lon - port_data['coord'][1])**2)
        if dist <= port_data['radius']:
            return True
    return False


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting algorithm"""
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


def load_natural_earth():
    """Загружает ne_10m_land.json из config/"""
    global NE_POLYGONS

    # Ищем файл относительно текущего скрипта
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_file = os.path.join(base_dir, "config", "ne_10m_land.json")

    if not os.path.exists(json_file):
        print(f"❌ Файл не найден: {json_file}")
        return False

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✓ Natural Earth загружен: {json_file}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

    # Окно вокруг Кольского
    min_lat, max_lat = 68.0, 70.5
    min_lon, max_lon = 31.5, 38.0

    count = 0
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        geom_type = geom.get("type")

        if geom_type == "Polygon":
            coords = geom.get("coordinates", [])
            if coords and len(coords[0]) > 2:
                ring = coords[0]
                latlons = [(coord[1], coord[0]) for coord in ring]  # исправлено!
                if any(min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
                       for lat, lon in latlons):
                    NE_POLYGONS.append(latlons)
                    count += 1

        elif geom_type == "MultiPolygon":
            for polygon in geom.get("coordinates", []):
                if polygon and len(polygon[0]) > 2:
                    ring = polygon[0]
                    latlons = [(coord[1], coord[0]) for coord in ring]  # исправлено!
                    if any(min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
                           for lat, lon in latlons):
                        NE_POLYGONS.append(latlons)
                        count += 1

    print(f"✓ Загружено {count} полигонов суши")
    return True


def point_in_ne_polygons(lat: float, lon: float) -> bool:
    """Точка в полигонах Natural Earth"""
    if not NE_POLYGONS:
        return False
    pt = (lat, lon)
    for poly in NE_POLYGONS:
        if len(poly) > 2 and point_in_polygon(pt, poly):
            return True
    return False


# Загружаем при импорте
if not load_natural_earth():
    print("⚠️  Маска будет работать без Natural Earth")


def create_land_sea_mask(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """True = СУША, False = ВОДА"""

    mask = np.zeros((len(lats), len(lons)), dtype=bool)

    print(f"  Построение маски из Natural Earth")
    if NE_POLYGONS:
        print(f"     Полигонов суши: {len(NE_POLYGONS)}")
    else:
        print(f"     ⚠️  Полигоны не загружены!")

    total_points = len(lats) * len(lons)
    processed = 0

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            # Порты = ВОДА
            if is_near_port(lat, lon):
                mask[i, j] = False
            # Natural Earth = СУША
            elif point_in_ne_polygons(lat, lon):
                mask[i, j] = True
            # Остальное = ВОДА
            else:
                mask[i, j] = False

            processed += 1
            if processed % max(1, total_points // 10) == 0:
                progress = (processed / total_points) * 100
                print(f"    {progress:.0f}%")

    land = mask.sum()
    water = (~mask).sum()
    print(f"  ✓ Суша: {land} ({land/total_points*100:.1f}%)")
    print(f"  ✓ Вода: {water} ({water/total_points*100:.1f}%)")

    return mask
