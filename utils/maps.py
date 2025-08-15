"""
Сервис для работы с картами OSM Static Maps
"""

import requests
import os
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import io
from config import Config

class MapService:
    """Сервис для работы с картами"""
    
    def __init__(self):
        self.base_url = Config.OSM_STATIC_MAPS_URL
        self.width = Config.MAP_WIDTH
        self.height = Config.MAP_HEIGHT
        self.zoom = Config.MAP_ZOOM
        
        # Создаем папку для кэша карт
        self.cache_dir = "static/images/maps"
        os.makedirs(self.cache_dir, exist_ok=True)

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Геокодирование адреса (преобразование адреса в координаты)
        Использует Nominatim OpenStreetMap API.
        """
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 0,
            'extratags': 0,
            'namedetails': 0
        }
        headers = {
            'User-Agent': 'RaiTaxiBot/1.0 (https://github.com/your-username/raitaxi)' # Replace with actual repo URL
        }
        try:
            response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка геокодирования адреса '{address}': {e}")
            return None
        except ValueError as e:
            print(f"Ошибка парсинга ответа геокодера: {e}")
            return None
    
    def get_static_map(self, center_lat: float, center_lon: float,
                       markers: list = None, routes: list = None) -> Optional[bytes]:
        """
        Получение статической карты
        
        Args:
            center_lat, center_lon: координаты центра карты
            markers: список маркеров [(lat, lon, color, label), ...]
            routes: список маршрутов [(lat1, lon1, lat2, lon2), ...]
        
        Returns:
            Изображение карты в формате bytes или None при ошибке
        """
        try:
            # Формируем параметры запроса
            params = {
                'center': f"{center_lat},{center_lon}",
                'zoom': self.zoom,
                'size': f"{self.width}x{self.height}",
                'maptype': 'mapnik',  # Стандартная карта OSM
                'format': 'png'
            }
            
            # Добавляем маркеры
            if markers:
                marker_params = []
                for lat, lon, color, label in markers:
                    marker_str = f"{color},{lat},{lon}"
                    if label:
                        marker_str += f",{label}"
                    marker_params.append(marker_str)
                
                params['markers'] = marker_params
            
            # Добавляем маршруты (если поддерживаются)
            if routes:
                route_params = []
                for lat1, lon1, lat2, lon2 in routes:
                    route_str = f"{lat1},{lon1},{lat2},{lon2}"
                    route_params.append(route_str)
                
                params['routes'] = route_params
            
            # Выполняем запрос
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            print(f"Ошибка получения карты: {e}")
            return None
    
    def create_simple_map(self, pickup_lat: float, pickup_lon: float,
                         destination_lat: float = None, destination_lon: float = None,
                         driver_lat: float = None, driver_lon: float = None) -> Optional[bytes]:
        """
        Создание простой карты с маркерами
        
        Args:
            pickup_lat, pickup_lon: координаты точки отправления
            destination_lat, destination_lon: координаты точки назначения
            driver_lat, driver_lon: координаты водителя
        
        Returns:
            Изображение карты в формате bytes
        """
        # Определяем центр карты
        if destination_lat and destination_lon:
            # Центр между точками отправления и назначения
            center_lat = (pickup_lat + destination_lat) / 2
            center_lon = (pickup_lon + destination_lon) / 2
        else:
            center_lat, center_lon = pickup_lat, pickup_lon
        
        # Формируем маркеры
        markers = [
            (pickup_lat, pickup_lon, 'red', 'A'),  # Точка отправления
        ]
        
        if destination_lat and destination_lon:
            markers.append((destination_lat, destination_lon, 'green', 'B'))  # Точка назначения
        
        if driver_lat and driver_lon:
            markers.append((driver_lat, driver_lon, 'blue', '🚗'))  # Водитель
        
        # Получаем карту
        map_data = self.get_static_map(center_lat, center_lon, markers=markers)
        
        if map_data:
            # Добавляем дополнительную информацию на карту
            return self.add_map_overlay(map_data, pickup_lat, pickup_lon, 
                                      destination_lat, destination_lon)
        
        return map_data
    
    def add_map_overlay(self, map_data: bytes, pickup_lat: float, pickup_lon: float,
                        destination_lat: float = None, destination_lon: float = None) -> bytes:
        """
        Добавление дополнительной информации на карту
        
        Args:
            map_data: исходное изображение карты
            pickup_lat, pickup_lon: координаты точки отправления
            destination_lat, destination_lon: координаты точки назначения
        
        Returns:
            Изображение с наложенной информацией
        """
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(map_data))
            draw = ImageDraw.Draw(image)
            
            # Простой шрифт (если доступен)
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Добавляем информацию о координатах
            info_text = f"Откуда: {pickup_lat:.4f}, {pickup_lon:.4f}"
            draw.text((10, 10), info_text, fill='black', font=font)
            
            if destination_lat and destination_lon:
                info_text2 = f"Куда: {destination_lat:.4f}, {destination_lon:.4f}"
                draw.text((10, 30), info_text2, fill='black', font=font)
            
            # Добавляем логотип Рай-Такси
            logo_text = "🚗 Рай-Такси"
            draw.text((10, image.height - 30), logo_text, fill='red', font=font)
            
            # Сохраняем в bytes
            output = io.BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()
            
        except Exception as e:
            print(f"Ошибка добавления оверлея: {e}")
            return map_data
    
    def get_map_url(self, lat: float, lon: float, zoom: int = None) -> str:
        """
        Получение URL для карты
        
        Args:
            lat, lon: координаты
            zoom: уровень зума
        
        Returns:
            URL карты
        """
        if zoom is None:
            zoom = self.zoom
        
        return f"{self.base_url}?center={lat},{lon}&zoom={zoom}&size={self.width}x{self.height}&maptype=mapnik"
    
    def calculate_optimal_zoom(self, pickup_lat: float, pickup_lon: float,
                              destination_lat: float = None, destination_lon: float = None) -> int:
        """
        Расчет оптимального уровня зума для отображения маршрута
        
        Args:
            pickup_lat, pickup_lon: координаты точки отправления
            destination_lat, destination_lon: координаты точки назначения
        
        Returns:
            Оптимальный уровень зума
        """
        if not destination_lat or not destination_lon:
            return 15  # Для одной точки
        
        # Рассчитываем расстояние
        from services.price_calculator import PriceCalculator
        distance = PriceCalculator.calculate_distance(
            pickup_lat, pickup_lon, destination_lat, destination_lon
        )
        
        # Определяем зум в зависимости от расстояния
        if distance < 1:
            return 16  # Очень близко
        elif distance < 5:
            return 15  # Близко
        elif distance < 20:
            return 14  # Средне
        elif distance < 50:
            return 13  # Далеко
        else:
            return 12  # Очень далеко
    
    def save_map_to_cache(self, map_data: bytes, filename: str) -> str:
        """
        Сохранение карты в кэш
        
        Args:
            map_data: данные карты
            filename: имя файла
        
        Returns:
            Путь к сохраненному файлу
        """
        try:
            filepath = os.path.join(self.cache_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(map_data)
            return filepath
        except Exception as e:
            print(f"Ошибка сохранения карты в кэш: {e}")
            return ""
    
    def clear_cache(self, max_age_hours: int = 24):
        """
        Очистка старых файлов кэша
        
        Args:
            max_age_hours: максимальный возраст файлов в часах
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        print(f"Удален старый файл кэша: {filename}")
        except Exception as e:
            print(f"Ошибка очистки кэша: {e}")
