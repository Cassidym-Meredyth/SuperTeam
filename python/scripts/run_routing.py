import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import numpy as np
from src.preprocessing.land_sea_mask import create_land_sea_mask
from src.routing.astar import a_star_route_planning
from src.utils.geo_utils import haversine_distance
from src.visualization.map_plotter import plot_route_on_map, export_route_to_formats

import json
from shapely.geometry import Polygon, Point

# Координаты портов (корректные!)
START_PORT = (69.04, 33.05)         # Мурманск
WAYPOINT_PORT = (64.8, 39.8)        # Архангельск
END_PORT = (69.4112, 65.6104)       # Баренцево море

# Окно координат
MIN_LAT, MAX_LAT = 62.0, 73.0
MIN_LON, MAX_LON = 28.0, 70.0

lats = np.linspace(MIN_LAT, MAX_LAT, 1000)
lons = np.linspace(MIN_LON, MAX_LON, 1200)

# Функция поиска ближайшей морской точки
def nearest_sea_point(lat, lon, lats, lons, land_mask):
    min_dist = float('inf')
    best = None
    for i in range(len(lats)):
        for j in range(len(lons)):
            if not land_mask[i, j]:
                d = np.hypot(lat - lats[i], lon - lons[j])
                if d < min_dist:
                    min_dist = d
                    best = (lats[i], lons[j])
    return best

# Новый --- ЗАГРУЗКА ОГРАНИЧЕННЫХ ЗОН --- (например, ледовые полигоны)
def load_restriction_mask(json_file, lats, lons):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    polygons = [Polygon(feature['geometry']['coordinates'][0]) for feature in data['features']]
    mask = np.zeros((len(lats), len(lons)), dtype=bool)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            pt = Point(lon, lat)   # geojson: (lon, lat)
            if any(poly.contains(pt) for poly in polygons):
                mask[i, j] = True
    return mask

ship_params = {
    'ice_class': 7,
    'open_water_speed': 15,
    'light_ice_speed': 10,
    'heavy_ice_speed': 5,
    'max_ice_thickness': 1.5
}

def main():
    print("=== Система оптимизации маршрута: Мурманск → Архангельск → точка на море ===\n")
    print("Создание сетки координат...")

    land_mask = create_land_sea_mask(lats, lons)
    print(f"Маска суши/море: {land_mask.shape} | Суша: {land_mask.sum()} | Вода: {(~land_mask).sum()}")

    # Загрузка доп. ограниченных зон (например, ледовые поля/запретные зоны)
    ICE_RESTRICTION_FILE = '../config/iceice.json'
    restriction_mask = load_restriction_mask(ICE_RESTRICTION_FILE, lats, lons)
    print(f"Ограниченных зон: {restriction_mask.sum()} (True = запрет прохода)")

    ice_data = {}

    # Найти ближайшие морские точки для каждой
    true_start = nearest_sea_point(*START_PORT, lats, lons, land_mask)
    true_waypoint = nearest_sea_point(*WAYPOINT_PORT, lats, lons, land_mask)
    true_end = nearest_sea_point(*END_PORT, lats, lons, land_mask)
    print(f"Старт по морю: {true_start}")
    print(f"Архангельск по морю: {true_waypoint}")
    print(f"Финиш по морю: {true_end}")

    # Построить маршрут по двум сегментам
    points = [true_start, true_waypoint, true_end]
    route_full = []
    for i in range(len(points) - 1):
        segment = a_star_route_planning(
            start_coord=points[i],
            end_coord=points[i + 1],
            ice_data=ice_data,
            ship_params=ship_params,
            land_mask=(land_mask | restriction_mask),
            resolution=0.05,
            lats=lats,
            lons=lons
        )
        if segment and len(segment) > 1:
            if i > 0:
                segment = segment[1:]
            route_full += segment

    if route_full and len(route_full) > 2:
        print(f"\n✓ Маршрут найден!")
        print(f"  Количество точек маршрута: {len(route_full)}")
        print(f"  Начало: {route_full[0]}")
        print(f"  Конец: {route_full[-1]}")

        total_distance = sum(
            haversine_distance(route_full[i], route_full[i + 1])
            for i in range(len(route_full) - 1)
        )
        print(f"  Длина маршрута: {total_distance:.2f} км")

        avg_speed = ship_params['open_water_speed']
        time_hours = total_distance / (avg_speed * 1.852)
        print(f"  Время в пути: {time_hours:.1f} часов ({time_hours / 24:.1f} дней)")

        output_dir = Path(__file__).parent.parent / "output" / "routes"
        output_dir.mkdir(parents=True, exist_ok=True)
        save_route_txt(route_full, total_distance, time_hours, output_dir)

        print("\n📍 Создание интерактивной карты...")
        map_file = output_dir / "route_map.html"
        plot_route_on_map(
            route=route_full,
            start_port=true_start,
            end_port=true_end,
            output_file=str(map_file),
            land_mask=(land_mask | restriction_mask),
            lats=lats,
            lons=lons
        )
        print(f"✓ Интерактивная карта создана: {map_file}")

        print("\n📦 Экспорт маршрута...")
        export_route_to_formats(route_full, output_dir)
        print("✅ Маршрут сохранён в output/routes/")
    else:
        print("\n✗ Маршрут не найден — проверь координаты/окно или ограничения/запретные зоны.")

def save_route_txt(route, distance, time, output_dir):
    output_file = output_dir / "murmansk_archangelsk_sea_route.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== Оптимальный маршрут: Мурманск → Архангельск → на море ===\n\n")
        f.write(f"Длина: {distance:.2f} км\n")
        f.write(f"Время: {time:.1f} ч ({time / 24:.1f} дн)\n")
        f.write(f"Точек: {len(route)}\n\n")
        f.write("Координаты маршрута:\n")
        for i, (lat, lon) in enumerate(route, 1):
            f.write(f"{i}. {lat:.4f}, {lon:.4f}\n")
    print(f"✓ TXT сохранён: {output_file}")

if __name__ == "__main__":
    main()
