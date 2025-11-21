import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import numpy as np
import json
from shapely.geometry import Polygon, Point
from src.preprocessing.land_sea_mask import create_land_sea_mask
from src.routing.astar import a_star_route_planning
from src.utils.geo_utils import haversine_distance
from src.visualization.map_plotter import plot_route_on_map, export_route_to_formats

# Координаты портов (общие для всех сценариев)
START_PORT = (69.04, 33.05)        # Мурманск
END_PORT = (71.3219, 72.29)        # Сабетта

# Окно координат
MIN_LAT, MAX_LAT = 62.0, 78.0
MIN_LON, MAX_LON = 28.0, 80.0
lats = np.linspace(MIN_LAT, MAX_LAT, 1000)
lons = np.linspace(MIN_LON, MAX_LON, 1200)

# Промежуточные точки для каждого месяца/ограничения
month_scenarios = {
    'nov': {
        'mask_file': '../config/novice.geojson',
        'waypoints': [
            (64.8, 39.8),          # Архангельск
            (70.9, 56.8),
            (72.0, 68.1)
        ],
    },
    'march': {
        'mask_file': '../config/march.geojson',
        'waypoints': [
            (65.2, 40.1),          # Смещённая точка (лед ушёл к востоку)
            (73, 51),
            (77.27, 66.35),
            (77.5, 70.66)
        ],
    },
    'july': {
        'mask_file': '../config/july.geojson',
        'waypoints': [
            (65.0, 39.9),
            (70.8, 62.8),
            (72.3, 69.2)
        ],
    },
    # Расширяй при необходимости
}

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

def load_restriction_mask(json_file, lats, lons):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    polygons = [Polygon(feature['geometry']['coordinates'][0]) for feature in data['features']]
    mask = np.zeros((len(lats), len(lons)), dtype=bool)
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            pt = Point(lon, lat)
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
    print("=== Система оптимизации морского маршрута по месяцам ===\n")
    land_mask = create_land_sea_mask(lats, lons)

    for month, config in month_scenarios.items():
        print(f"--- Маршрут для месяца: {month.upper()} ---")
        restriction_mask = load_restriction_mask(config['mask_file'], lats, lons)
        print(f"Ограниченные зоны: {restriction_mask.sum()} (True = запрет прохода)")
        ice_data = {}

        # Формируем список навигационных точек в нужном порядке
        raw_points = [START_PORT] + config['waypoints'] + [END_PORT]
        points = [nearest_sea_point(*pt, lats, lons, land_mask) for pt in raw_points]
        print("Маршрутные морские точки:")
        for idx, pt in enumerate(points):
            print(f"  {idx+1}. {pt}")

        # Построить маршрут по сегментам
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
            print(f"\n✓ Маршрут найден за {month}! Кол-во точек: {len(route_full)}")
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

            output_dir = Path(__file__).parent.parent / f"output/routes_{month}"
            output_dir.mkdir(parents=True, exist_ok=True)
            save_route_txt(route_full, total_distance, time_hours, output_dir, month)

            print("\n📍 Создание интерактивной карты...")
            map_file = output_dir / "route_map.html"
            plot_route_on_map(
                route=route_full,
                start_port=points[0],
                end_port=points[-1],
                output_file=str(map_file),
                land_mask=(land_mask | restriction_mask),
                lats=lats,
                lons=lons
            )
            print(f"✓ Карта создана (месяц '{month}')")

            print("\n📦 Экспорт маршрута...")
            export_route_to_formats(route_full, output_dir)
            print("✅ Маршрут для месяца сохранён!\n")
        else:
            print(f"\n✗ Маршрут для месяца {month} не найден — скорректируй ограничения/точки или расширь окно.\n")

def save_route_txt(route, distance, time, output_dir, month):
    output_file = output_dir / f"route_{month}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"=== Оптимальный маршрут ({month.upper()}): через индивидуальные порты ===\n\n")
        f.write(f"Длина: {distance:.2f} км\n")
        f.write(f"Время: {time:.1f} ч ({time / 24:.1f} дн)\n")
        f.write(f"Точек: {len(route)}\n\n")
        f.write("Координаты маршрута:\n")
        for i, (lat, lon) in enumerate(route, 1):
            f.write(f"{i}. {lat:.4f}, {lon:.4f}\n")
    print(f"✓ TXT сохранён: {output_file}")

if __name__ == "__main__":
    main()
