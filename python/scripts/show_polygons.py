import sys
from pathlib import Path

import numpy as np
import folium

# чтобы видеть src/*
sys.path.append(str(Path(__file__).parent.parent))

from src.preprocessing.land_sea_mask import create_land_sea_mask
from src.visualization.map_plotter import plot_route_on_map
from config.coastline_simple import KOLA_POLYGON, KANIN_POLYGON


# Порты, просто как опорные точки на карте
START_PORT = (69.04, 33.05)   # Мурманск
END_PORT   = (69.30, 36.50)   # Вход в Кольский залив / Островной


def main():
    print("=== ВИЗУАЛИЗАЦИЯ ПОЛИГОНОВ СУША/МОРЕ ===")

    # 1. Задаём окно по широте/долготе вокруг Кольского
    lat_min, lat_max = 68.0, 70.5
    lon_min, lon_max = 31.5, 38.0

    # 2. Строим регулярную сетку (та же логика, что для маски)
    print("→ Создаю сетку координат...")
    lats = np.linspace(lat_min, lat_max, 250)
    lons = np.linspace(lon_min, lon_max, 250)

    # 3. Строим маску суши/моря
    print("→ Строю маску суша/море по полигонам...")
    land_mask = create_land_sea_mask(lats, lons)

    # 4. Делаем простой «фиктивный» маршрут: прямая между портами
    dummy_route = [START_PORT, END_PORT]

    # 5. Папка для вывода
    output_dir = Path(__file__).parent.parent / "output" / "debug_polygons"
    output_dir.mkdir(parents=True, exist_ok=True)
    map_file = output_dir / "polygons_map.html"

    # 6. Рисуем карту с клеточной маской (красные квадраты)
    print("→ Рисую карту c land_mask...")
    m = plot_route_on_map(
        route=dummy_route,
        start_port=START_PORT,
        end_port=END_PORT,
        output_file=None,       # пока не сохраняем, ещё добавим полигоны
        land_mask=land_mask,
        lats=lats,
        lons=lons,
    )

    # 7. Добавляем исходные полигоны как линии поверх маски
    print("→ Добавляю полигоны KOLA_POLYGON и KANIN_POLYGON...")

    poly_layer = folium.FeatureGroup(name="📐 Полигоны coastline_simple", show=True)

    # KOLA_POLYGON и KANIN_POLYGON у тебя уже обёрнуты в список [ ... ]
    def normalize_polygons(poly_obj):
        polys = []
        if not isinstance(poly_obj, list) or len(poly_obj) == 0:
            return polys

        # вариант 1: список точек [(lat, lon), ...]
        if isinstance(poly_obj[0], tuple) or (
            isinstance(poly_obj[0], list) and len(poly_obj[0]) == 2
        ):
            polys.append(poly_obj)
        # вариант 2: список полигонов [[(lat, lon), ...], [...]]
        else:
            for p in poly_obj:
                if isinstance(p, list) and len(p) > 0:
                    polys.append(p)
        return polys

    kola_polys = normalize_polygons(KOLA_POLYGON)
    kanin_polys = normalize_polygons(KANIN_POLYGON)

    print(f"→ Полигонов Кольский: {len(kola_polys)}")
    print(f"→ Полигонов Канин:   {len(kanin_polys)}")

    for poly, name, color in [
        *[(p, "KOLA_POLYGON", "yellow") for p in kola_polys],
        *[(p, "KANIN_POLYGON", "orange") for p in kanin_polys],
    ]:
        if not poly:
            continue  # пропускаем пустые

        folium.PolyLine(
            locations=[(lat, lon) for (lat, lon) in poly],
            color=color,
            weight=3,
            opacity=0.9,
            tooltip=name,
        ).add_to(poly_layer)

    poly_layer.add_to(m)

    # Обновляем контрол слоёв и сохраняем карту
    folium.LayerControl(position="topright").add_to(m)

    m.save(str(map_file))
    print(f"✓ Карта с полигонами сохранена: {map_file}")
    print("  Открой этот HTML в браузере и смотри, где именно проходят полигоны.")


if __name__ == "__main__":
    main()
