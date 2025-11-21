import numpy as np
import requests
import rasterio
from io import BytesIO
from typing import Dict, List, Tuple
from config.ice_hazard_zones import ICE_HAZARD_ZONES, ICE_POINT_HAZARDS


class PolarViewDataFetcher:
    """Класс для получения данных о ледовой обстановке с PolarView"""
    
    def __init__(self):
        self.base_url = "https://www.polarview.aq/images/105_S1arc_AMSR2/"
        self.latest_image_url = None
        
    def get_latest_ice_data_url(self) -> str:
        """Получение URL последнего доступного изображения льда"""
        try:
            # Получаем список доступных изображений
            # PolarView обычно использует именование по датам
            from datetime import datetime, timedelta
            
            # Пробуем получить данные за последние 7 дней
            for days_back in range(7):
                date = datetime.now() - timedelta(days=days_back)
                date_str = date.strftime("%Y%m%d")
                
                # Формируем URL для AMSR2 данных (Северное полушарие)
                potential_url = f"{self.base_url}{date_str}_north_AMSR2.png"
                
                # Проверяем доступность
                response = requests.head(potential_url, timeout=10)
                if response.status_code == 200:
                    self.latest_image_url = potential_url
                    return potential_url
                    
            # Если не нашли свежих данных, используем статические зоны как запасной вариант
            print("Warning: No recent PolarView data found, using static zones")
            return None
            
        except Exception as e:
            print(f"Error fetching PolarView URL: {e}")
            return None
    
    def download_ice_data(self) -> np.ndarray:
        """Загрузка и обработка данных о концентрации льда"""
        try:
            url = self.get_latest_ice_data_url()
            if url is None:
                return None
                
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Открываем изображение как растр
            with BytesIO(response.content) as buffer:
                with rasterio.open(buffer) as dataset:
                    # Читаем данные (предполагаем, что это одноканальное изображение)
                    ice_data = dataset.read(1)
                    
                    # Нормализуем значения концентрации льда (0-1)
                    # PolarView использует цветовую кодировку, где разные цвета соответствуют разной концентрации
                    ice_concentration = self._decode_polarview_colors(ice_data)
                    
                    return ice_concentration
                    
        except Exception as e:
            print(f"Error downloading ice data: {e}")
            return None
    
    def _decode_polarview_colors(self, image_data: np.ndarray) -> np.ndarray:
        """Декодирование цветовой карты PolarView в значения концентрации льда"""
        # PolarView использует стандартную цветовую карту для концентрации льда
        # Примерное соответствие (может потребоваться калибровка):
        # 0-15%: синие оттенки -> 0.0-0.15
        # 15-80%: зеленые/желтые оттенки -> 0.15-0.8  
        # 80-100%: красные/белые оттенки -> 0.8-1.0
        
        # Конвертируем RGB в градации серого и нормализуем
        if len(image_data.shape) == 3:  # RGB изображение
            gray = np.mean(image_data, axis=2)
        else:
            gray = image_data
            
        # Нормализация и нелинейное преобразование для лучшего соответствия
        normalized = gray.astype(np.float32) / 255.0
        
        # Эмпирическая калибровка (может потребоваться точная настройка)
        # Более темные пиксели = больше льда
        ice_concentration = 1.0 - normalized
        ice_concentration = np.clip(ice_concentration, 0.0, 1.0)
        
        return ice_concentration


def point_in_polygon(point: Tuple[float, float],
                     polygon: List[Tuple[float, float]]) -> bool:
    """Проверка, находится ли точка внутри полигона (Ray casting algorithm)"""
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


def haversine_distance(coord1: Tuple[float, float],
                       coord2: Tuple[float, float]) -> float:
    """Расстояние между точками в км"""
    R = 6371
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c


class IceDataProcessor:
    """Основной процессор для работы с ледовыми данными"""
    
    def __init__(self):
        self.polarview_fetcher = PolarViewDataFetcher()
        self.latest_ice_grid = None
        self.grid_lats = None
        self.grid_lons = None
        
    def initialize_ice_grid(self, lats: np.ndarray, lons: np.ndarray):
        """Инициализация сетки координат"""
        self.grid_lats = lats
        self.grid_lons = lons
        self.latest_ice_grid = None
        
    def get_ice_conditions_at_point(self, lat: float, lon: float) -> Dict:
        """Получение ледовых условий в точке с приоритетом спутниковых данных"""
        
        # Сначала пробуем получить спутниковые данные
        satellite_ice = self._get_satellite_ice_at_point(lat, lon)
        
        if satellite_ice is not None:
            return satellite_ice
            
        # Если спутниковых данных нет, используем статические зоны
        return self._get_static_ice_at_point(lat, lon)
    
    def _get_satellite_ice_at_point(self, lat: float, lon: float) -> Dict:
        """Получение данных со спутника для точки"""
        if self.latest_ice_grid is None:
            # Загружаем данные при первом обращении
            self._load_satellite_data()
            
        if self.latest_ice_grid is None:
            return None
            
        # Находим ближайшую точку в сетке
        lat_idx = np.argmin(np.abs(self.grid_lats - lat))
        lon_idx = np.argmin(np.abs(self.grid_lons - lon))
        
        concentration = self.latest_ice_grid['concentration'][lat_idx, lon_idx]
        thickness = self._estimate_thickness_from_concentration(concentration)
        severity = self._get_severity_from_concentration(concentration)
        
        return {
            'concentration': concentration,
            'thickness': thickness,
            'severity': severity,
            'zone_name': 'satellite_data',
            'data_source': 'polarview'
        }
    
    def _load_satellite_data(self):
        """Загрузка спутниковых данных"""
        print("Loading satellite ice data from PolarView...")
        ice_concentration = self.polarview_fetcher.download_ice_data()
        
        if ice_concentration is not None:
            # Создаем сетку для всего региона
            self.latest_ice_grid = {
                'concentration': ice_concentration,
                'thickness': self._estimate_thickness_from_concentration(ice_concentration)
            }
            print("Satellite data loaded successfully")
        else:
            print("Using static ice hazard zones as fallback")
    
    def _get_static_ice_at_point(self, lat: float, lon: float) -> Dict:
        """Резервный метод со статическими зонами"""
        point = (lat, lon)
        ice_data = {
            'concentration': 0.0,
            'thickness': 0.0,
            'severity': 'none',
            'zone_name': 'open_water',
            'data_source': 'static'
        }

        # Проверка полигональных зон
        for zone in ICE_HAZARD_ZONES:
            if point_in_polygon(point, zone['coordinates']):
                if zone['ice_concentration'] > ice_data['concentration']:
                    ice_data['concentration'] = zone['ice_concentration']
                    ice_data['thickness'] = zone['ice_thickness']
                    ice_data['severity'] = zone['severity']
                    ice_data['zone_name'] = zone['name']

        # Проверка точечных опасностей
        for hazard in ICE_POINT_HAZARDS:
            hazard_point = (hazard['lat'], hazard['lon'])
            distance = haversine_distance(point, hazard_point)

            if distance <= hazard['radius_km']:
                proximity_factor = 1 - (distance / hazard['radius_km'])
                additional_ice = 0.5 * proximity_factor

                ice_data['concentration'] = min(1.0,
                                                ice_data['concentration'] + additional_ice)
                ice_data['thickness'] = max(ice_data['thickness'],
                                            0.6 * proximity_factor)
                if ice_data['severity'] == 'none':
                    ice_data['severity'] = hazard['severity']

        return ice_data
    
    def _estimate_thickness_from_concentration(self, concentration: float) -> float:
        """Оценка толщины льда на основе концентрации"""
        # Эмпирическая зависимость (может потребоваться калибровка)
        if concentration < 0.1:
            return 0.0
        elif concentration < 0.3:
            return 0.1  # тонкий лед
        elif concentration < 0.7:
            return 0.3  # средний лед
        else:
            return 0.6  # толстый лед
    
    def _get_severity_from_concentration(self, concentration: float) -> str:
        """Определение уровня опасности по концентрации льда"""
        if concentration < 0.1:
            return 'none'
        elif concentration < 0.3:
            return 'low'
        elif concentration < 0.7:
            return 'medium'
        else:
            return 'high'


def create_ice_grid(lats: np.ndarray, lons: np.ndarray) -> Dict:
    """Создание сетки ледовых условий для всей акватории"""
    
    processor = IceDataProcessor()
    processor.initialize_ice_grid(lats, lons)
    
    ice_grid = {
        'concentration': np.zeros((len(lats), len(lons))),
        'thickness': np.zeros((len(lats), len(lons))),
        'severity': np.empty((len(lats), len(lons)), dtype=object),
        'data_source': np.empty((len(lats), len(lons)), dtype=object)
    }

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            conditions = processor.get_ice_conditions_at_point(lat, lon)
            ice_grid['concentration'][i, j] = conditions['concentration']
            ice_grid['thickness'][i, j] = conditions['thickness']
            ice_grid['severity'][i, j] = conditions['severity']
            ice_grid['data_source'][i, j] = conditions.get('data_source', 'unknown')

    return ice_grid


# Сохраняем обратную совместимость со старым кодом
def get_ice_conditions_at_point(lat: float, lon: float) -> Dict:
    """Совместимая версия функции для обратной совместимости"""
    processor = IceDataProcessor()
    return processor.get_ice_conditions_at_point(lat, lon)