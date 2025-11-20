import numpy as np
from typing import Tuple


def haversine_distance(coord1: Tuple[float, float],
                       coord2: Tuple[float, float]) -> float:
    """Расчет расстояния между двумя координатами в км"""
    R = 6371
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c


def grid_to_coord(grid_pos: Tuple[int, int],
                  lats: np.ndarray,
                  lons: np.ndarray) -> Tuple[float, float]:
    """Преобразует индексы сетки в географические координаты"""
    return (lats[grid_pos[0]], lons[grid_pos[1]])


def coord_to_grid(coord: Tuple[float, float],
                  lats: np.ndarray,
                  lons: np.ndarray) -> Tuple[int, int]:
    """Преобразует географические координаты в индексы сетки"""
    lat_idx = np.argmin(np.abs(lats - coord[0]))
    lon_idx = np.argmin(np.abs(lons - coord[1]))
    return (lat_idx, lon_idx)
