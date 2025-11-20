import folium
import pandas as pd
from typing import List, Tuple
from pathlib import Path
import numpy as np


def plot_route_on_map(route: List[Tuple[float, float]],
                      start_port: Tuple[float, float],
                      end_port: Tuple[float, float],
                      output_file: str = None,
                      land_mask: np.ndarray = None,
                      lats: np.ndarray = None,
                      lons: np.ndarray = None) -> folium.Map:
    """
    Создает интерактивную карту с маршрутом корабля

    Parameters:
    -----------
    route : список координат маршрута [(lat, lon), ...]
    start_port : координаты начального порта (lat, lon)
    end_port : координаты конечного порта (lat, lon)
    output_file : путь для сохранения HTML файла
    land_mask : маска суша/море для визуализации запретных зон
    lats, lons : массивы координат сетки

    Returns:
    --------
    folium.Map объект
    """

    # Вычисление центра карты
    avg_lat = sum(coord[0] for coord in route) / len(route)
    avg_lon = sum(coord[1] for coord in route) / len(route)

    # Создание карты
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=5,
        tiles='OpenStreetMap'
    )

    # Добавление альтернативных слоев карты
    folium.TileLayer('CartoDB positron', name='Светлая карта').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Темная карта').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Спутник',
        overlay=False,
        control=True
    ).add_to(m)

    # === ВИЗУАЛИЗАЦИЯ ЗАПРЕТНЫХ ЗОН (СУША) ===
    if land_mask is not None and lats is not None and lons is not None:
        print("  Отрисовка запретных зон (суша)...")

        # Создаем группу для запретных зон
        land_zones = folium.FeatureGroup(name='🚫 Запретные зоны (суша)', show=True)

        # Находим все точки суши и группируем их
        land_points = []
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                if land_mask[i, j]:
                    land_points.append((lat, lon))

        # Рисуем запретные зоны как полупрозрачные прямоугольники
        # Группируем близкие точки для оптимизации
        step = max(1, len(lats) // 50)  # Уменьшаем количество для производительности

        for i in range(0, len(lats) - step, step):
            for j in range(0, len(lons) - step, step):
                # Проверяем, есть ли суша в этом квадрате
                has_land = False
                for di in range(step):
                    for dj in range(step):
                        if i + di < len(lats) and j + dj < len(lons):
                            if land_mask[i + di, j + dj]:
                                has_land = True
                                break
                    if has_land:
                        break

                if has_land:
                    # Создаем прямоугольник для этой зоны
                    lat_min = lats[i]
                    lat_max = lats[min(i + step, len(lats) - 1)]
                    lon_min = lons[j]
                    lon_max = lons[min(j + step, len(lons) - 1)]

                    bounds = [
                        [lat_min, lon_min],
                        [lat_max, lon_max]
                    ]

                    folium.Rectangle(
                        bounds=bounds,
                        color='red',
                        fill=True,
                        fillColor='red',
                        fillOpacity=0.3,
                        weight=1,
                        opacity=0.5,
                        popup='Запретная зона (суша)',
                        tooltip='Непроходимая зона'
                    ).add_to(land_zones)

        land_zones.add_to(m)
        print(f"  ✓ Отрисовано запретных зон: ~{len(land_points)} точек")

    # === МАРШРУТ КОРАБЛЯ ===
    route_layer = folium.FeatureGroup(name='🚢 Маршрут корабля', show=True)

    folium.PolyLine(
        locations=route,
        color='#0066FF',
        weight=4,
        opacity=0.9,
        popup='<b>Оптимальный морской маршрут</b><br>Мурманск → Архангельск',
        tooltip='Маршрут корабля'
    ).add_to(route_layer)

    route_layer.add_to(m)

    # === ПОРТЫ ===
    ports_layer = folium.FeatureGroup(name='⚓ Порты', show=True)

    # Мурманск
    folium.Marker(
        location=start_port,
        popup=f'''<b>🚢 Порт Мурманск</b><br>
                  <b>Старт маршрута</b><br>
                  Координаты: {start_port[0]:.4f}°N, {start_port[1]:.4f}°E''',
        tooltip='Мурманск (Старт)',
        icon=folium.Icon(color='green', icon='anchor', prefix='fa')
    ).add_to(ports_layer)

    # Архангельск
    folium.Marker(
        location=end_port,
        popup=f'''<b>🚢 Порт Архангельск</b><br>
                  <b>Финиш маршрута</b><br>
                  Координаты: {end_port[0]:.4f}°N, {end_port[1]:.4f}°E''',
        tooltip='Архангельск (Финиш)',
        icon=folium.Icon(color='red', icon='anchor', prefix='fa')
    ).add_to(ports_layer)

    ports_layer.add_to(m)

    # === КЛЮЧЕВЫЕ ТОЧКИ МАРШРУТА ===
    waypoints_layer = folium.FeatureGroup(name='📍 Ключевые точки', show=False)

    key_points = [
        (route[len(route) // 4], 'Баренцево море'),
        (route[len(route) // 2], 'Горло Белого моря'),
        (route[3 * len(route) // 4], 'Белое море'),
    ]

    for coord, label in key_points:
        folium.CircleMarker(
            location=coord,
            radius=5,
            color='blue',
            fill=True,
            fillColor='lightblue',
            fillOpacity=0.7,
            popup=f'<b>{label}</b><br>{coord[0]:.4f}°N, {coord[1]:.4f}°E',
            tooltip=label
        ).add_to(waypoints_layer)

    waypoints_layer.add_to(m)

    # === КОНТРОЛЬ СЛОЕВ ===
    folium.LayerControl(position='topright').add_to(m)

    # === ИНСТРУМЕНТЫ ===
    from folium.plugins import MeasureControl, Fullscreen, MousePosition

    MeasureControl(
        position='topleft',
        primary_length_unit='kilometers',
        secondary_length_unit='miles',
        primary_area_unit='sqkilometers'
    ).add_to(m)

    Fullscreen(position='topright').add_to(m)

    MousePosition(
        position='bottomleft',
        separator=' | ',
        prefix='Координаты:',
        lat_formatter="function(num) {return L.Util.formatNum(num, 4) + '°N';}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 4) + '°E';}"
    ).add_to(m)

    # Сохранение карты
    if output_file:
        m.save(output_file)
        print(f"✓ Карта сохранена: {output_file}")

    return m


def export_route_to_formats(route: List[Tuple[float, float]],
                            output_dir: Path):
    """Экспорт маршрута в различные форматы"""

    # CSV формат
    df = pd.DataFrame(route, columns=['latitude', 'longitude'])
    df['point_number'] = range(1, len(route) + 1)
    csv_file = output_dir / 'route_coordinates.csv'
    df.to_csv(csv_file, index=False)
    print(f"✓ CSV экспорт: {csv_file}")

    # GeoJSON формат
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in route]
                },
                "properties": {
                    "name": "Маршрут Мурманск-Архангельск",
                    "description": "Оптимальный морской маршрут через Баренцево и Белое моря",
                    "vessel_route": True
                }
            }
        ]
    }

    import json
    geojson_file = output_dir / 'route.geojson'
    with open(geojson_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"✓ GeoJSON экспорт: {geojson_file}")

    # KML формат
    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Морской маршрут Мурманск-Архангельск</name>
    <description>Оптимальный маршрут через Баренцево и Белое моря</description>
    <Style id="routeStyle">
      <LineStyle>
        <color>ff0066ff</color>
        <width>4</width>
      </LineStyle>
    </Style>
    <Placemark>
      <name>Маршрут корабля</name>
      <styleUrl>#routeStyle</styleUrl>
      <LineString>
        <extrude>0</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>
{chr(10).join([f"          {lon},{lat},0" for lat, lon in route])}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

    kml_file = output_dir / 'route.kml'
    with open(kml_file, 'w', encoding='utf-8') as f:
        f.write(kml_content)
    print(f"✓ KML экспорт: {kml_file}")
