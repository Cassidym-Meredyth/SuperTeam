import os
import json
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon

# Путь к Land-полигону
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
land_json_path = os.path.join(base_dir, "config", "ne_10m_land.geojson")

def load_land_polygons(land_json_path):
    polys = []
    with open(land_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            coords = [tuple(pair) for pair in geom["coordinates"][0]]  # [lon, lat]
            polys.append(Polygon(coords))
        elif geom["type"] == "MultiPolygon":
            for subpoly in geom["coordinates"]:
                coords = [tuple(pair) for pair in subpoly[0]]
                polys.append(Polygon(coords))
    print(f"✓ Загружено суши-полигонов: {len(polys)}")
    return MultiPolygon(polys)

# Загружаем Land-полигоны один раз
LAND_POLYGON = load_land_polygons(land_json_path)

def is_land_point(lat, lon):
    pt = Point(lon, lat)
    return LAND_POLYGON.contains(pt)

def create_land_sea_mask(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    mask = np.zeros((len(lats), len(lons)), dtype=bool)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            mask[i, j] = is_land_point(lat, lon)
    print(f"✓ Маска по Land: Суша {mask.sum()}, Вода {(~mask).sum()}")
    return mask
