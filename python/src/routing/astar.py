"""
A* алгоритм маршрутизации, использует маску суши/моря
"""
from src.routing.cost_function import calculate_edge_cost_with_static_ice
from typing import Tuple, List, Dict
import numpy as np
import heapq


def a_star_route_planning(start_coord, end_coord, ice_data, ship_params, land_mask, resolution=0.1, lats=None, lons=None):
    if lats is None or lons is None:
        print("❌ lats/lons не переданы!")
        # Можно сконструировать по исходному окну, если нужно

    def coord_to_grid(lat, lon):
        i = int(np.argmin(np.abs(lats - lat)))
        j = int(np.argmin(np.abs(lons - lon)))
        return i, j

    def grid_to_coord(i, j):
        lat = lats[i]
        lon = lons[j]
        return lat, lon

    start_i, start_j = coord_to_grid(start_coord[0], start_coord[1])
    end_i, end_j = coord_to_grid(end_coord[0], end_coord[1])

    print(f"land_mask[start]:", land_mask[start_i, start_j], "| start_i, start_j:", start_i, start_j)
    print(f"land_mask[end]:", land_mask[end_i, end_j], "| end_i, end_j:", end_i, end_j)

    # A* поиск
    open_set = []
    heapq.heappush(open_set, (0, start_i, start_j))

    came_from = {}
    g_score = {(start_i, start_j): 0}
    f_score = {(start_i, start_j): np.sqrt((end_i - start_i) ** 2 + (end_j - start_j) ** 2)}

    closed_set = set()
    visited = 0

    while open_set:
        _, current_i, current_j = heapq.heappop(open_set)

        if (current_i, current_j) == (end_i, end_j):
            # Найден путь!
            path = []
            current = (current_i, current_j)
            while current in came_from:
                path.append(grid_to_coord(current[0], current[1]))
                current = came_from[current]
            path.append(start_coord)
            path.reverse()
            print(f"  ✓ Путь найден за {visited} итераций ({len(path)} точек)")
            return path

        if (current_i, current_j) in closed_set:
            continue

        closed_set.add((current_i, current_j))
        visited += 1

        # Соседи (8 направлений)
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ni, nj = current_i + di, current_j + dj

            # Границы сетки
            if ni < 0 or ni >= land_mask.shape[0] or nj < 0 or nj >= land_mask.shape[1]:
                continue

            # Суша - не проходим
            if land_mask[ni, nj]:
                continue

            if (ni, nj) in closed_set:
                continue

            # Стоимость хода
            tentative_g = g_score[(current_i, current_j)] + calculate_edge_cost_with_static_ice(
                current=(current_i, current_j),
                neighbor=(ni, nj),
                lats=lats,
                lons=lons,
                ice_data=ice_data,
                ship_params=ship_params,
                land_mask=land_mask
            )

            if (ni, nj) not in g_score or tentative_g < g_score[(ni, nj)]:
                came_from[(ni, nj)] = (current_i, current_j)
                g_score[(ni, nj)] = tentative_g
                h = np.sqrt((end_i - ni) ** 2 + (end_j - nj) ** 2)
                f_score[(ni, nj)] = tentative_g + h
                heapq.heappush(open_set, (f_score[(ni, nj)], ni, nj))

        if visited % 1000 == 0:
            print(f"    Обработано: {visited} ячеек...")

    print(f"  ⚠️  Путь не найден за {visited} итераций")
    return [(start_coord[0], start_coord[1]), (end_coord[0], end_coord[1])]
