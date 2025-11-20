import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import numpy as np
from src.preprocessing.ice_hazard_processor import create_ice_grid
from src.preprocessing.land_sea_mask import create_land_sea_mask
from src.routing.astar import a_star_route_planning
from src.utils.geo_utils import haversine_distance, coord_to_grid
from src.visualization.map_plotter import plot_route_on_map, export_route_to_formats

# Координаты портов
START_PORT = (69.04, 33.05)  # Мурманск
END_PORT = (64.55, 40.49)  # Вход в Кольский залив (район Островного)

MIN_LAT, MAX_LAT = 63.0, 71.0
MIN_LON, MAX_LON = 31.0, 44.0

lats = np.linspace(MIN_LAT, MAX_LAT, 400)  # можно 250, но 400 будет плавнее
lons = np.linspace(MIN_LON, MAX_LON, 400)

land_mask = create_land_sea_mask(lats, lons)

# Параметры судна
ship_params = {
    'ice_class': 7,
    'open_water_speed': 15,
    'light_ice_speed': 10,
    'heavy_ice_speed': 5,
    'max_ice_thickness': 1.5
}


def main():
    print("=== Система оптимизации маршрута: Мурманск → Архангельск ===\n")

    # Создание сетки координат
    print("Создание сетки координат...")

    # Создание маски суша/море
    print("\nСоздание маски суша/море...")
    land_mask = create_land_sea_mask(lats, lons)

    print(f"Маска создана: {land_mask.shape}")
    print(f"Суша: {land_mask.sum()} точек")
    print(f"Вода: {(~land_mask).sum()} точек")

    # Загрузка ледовых зон
    print("\nЗагрузка ледовых зон...")
    ice_data = {}  # или загрузите реальные данные

    # Поиск маршрута
    print("\nПоиск оптимального маршрута...")
    route = a_star_route_planning(
        start_coord=START_PORT,
        end_coord=END_PORT,
        ice_data=ice_data,
        ship_params=ship_params,
        land_mask=land_mask,
        resolution=0.1,
        lats=lats,
        lons=lons
    )

    if route:
        print(f"\n✓ Маршрут найден!")
        print(f"  Количество точек маршрута: {len(route)}")
        print(f"  Начало: {route[0]}")
        print(f"  Конец: {route[-1]}")

        # Расчет общей длины
        total_distance = sum(
            haversine_distance(route[i], route[i + 1])
            for i in range(len(route) - 1)
        )
        print(f"  Общая длина маршрута: {total_distance:.2f} км")

        # Оценка времени
        avg_speed = 12
        time_hours = total_distance / (avg_speed * 1.852)
        print(f"  Расчетное время в пути: {time_hours:.1f} часов ({time_hours / 24:.1f} дней)")

        # Создание директории для результатов
        output_dir = Path(__file__).parent.parent / "output" / "routes"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Сохранение текстового файла
        save_route_txt(route, total_distance, time_hours, output_dir)

        # Создание интерактивной карты
        print("\n📍 Создание интерактивной карты...")
        map_file = output_dir / "route_map.html"
        plot_route_on_map(
            route=route,
            start_port=START_PORT,
            end_port=END_PORT,
            output_file=str(map_file),
        )

        print(f"✓ Интерактивная карта создана: {map_file}")

        # Экспорт в разные форматы
        print("\n📦 Экспорт маршрута в форматы...")
        export_route_to_formats(route, output_dir)

        print("\n✅ Все файлы успешно созданы!")
        print(f"📂 Результаты находятся в: {output_dir}")

    else:
        print("\n✗ Маршрут не найден.")



def save_route_txt(route, distance, time, output_dir):
    """Сохранение маршрута в текстовый файл"""
    output_file = output_dir / "murmansk_arkhangelsk_route.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== Оптимальный маршрут: Мурманск → Архангельск ===\n\n")
        f.write(f"Общая длина: {distance:.2f} км\n")
        f.write(f"Расчетное время: {time:.1f} часов ({time / 24:.1f} дней)\n")
        f.write(f"Количество точек: {len(route)}\n\n")
        f.write("Координаты маршрута (Широта, Долгота):\n")
        for i, (lat, lon) in enumerate(route, 1):
            f.write(f"{i}. {lat:.4f}, {lon:.4f}\n")

    print(f"✓ Текстовый файл сохранен: {output_file}")


if __name__ == "__main__":
    main()
