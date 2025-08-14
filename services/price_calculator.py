"""
Калькулятор цен для Рай-Такси
"""

import math
from typing import Tuple, Optional
from config import Config

class PriceCalculator:
    """Калькулятор стоимости поездок и доставки"""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Расчет расстояния между двумя точками (формула гаверсинуса)
        Возвращает расстояние в километрах
        """
        # Радиус Земли в километрах
        R = 6371
        
        # Переводим координаты в радианы
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Разности координат
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Формула гаверсинуса
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        
        # Округляем до 2 знаков после запятой
        return round(distance, 2)
    
    @staticmethod
    def calculate_taxi_price(pickup_lat: float, pickup_lon: float,
                           destination_lat: float, destination_lon: float,
                           base_fare: float = None, per_km_rate: float = None,
                           minimum_fare: float = None) -> Tuple[float, float]:
        """
        Расчет стоимости поездки на такси
        
        Args:
            pickup_lat, pickup_lon: координаты точки отправления
            destination_lat, destination_lon: координаты точки назначения
            base_fare: базовая стоимость (по умолчанию из конфига)
            per_km_rate: стоимость за километр (по умолчанию из конфига)
            minimum_fare: минимальная стоимость (по умолчанию из конфига)
        
        Returns:
            Tuple[цена, расстояние_в_км]
        """
        # Используем значения по умолчанию из конфига
        if base_fare is None:
            base_fare = Config.BASE_FARE
        if per_km_rate is None:
            per_km_rate = Config.PER_KM_RATE
        if minimum_fare is None:
            minimum_fare = Config.MINIMUM_FARE
        
        # Рассчитываем расстояние
        distance = PriceCalculator.calculate_distance(
            pickup_lat, pickup_lon, destination_lat, destination_lon
        )
        
        # Рассчитываем стоимость
        price = base_fare + (distance * per_km_rate)
        
        # Проверяем минимальную стоимость
        if price < minimum_fare:
            price = minimum_fare
        
        # Округляем до целых рублей
        price = round(price)
        
        return price, distance
    
    @staticmethod
    def calculate_delivery_price(pickup_lat: float, pickup_lon: float,
                               destination_lat: float, destination_lon: float,
                               item_weight: float = 1.0, is_urgent: bool = False,
                               base_fare: float = None, per_km_rate: float = None,
                               minimum_fare: float = None) -> Tuple[float, float]:
        """
        Расчет стоимости доставки
        
        Args:
            pickup_lat, pickup_lon: координаты точки отправления
            destination_lat, destination_lon: координаты точки назначения
            item_weight: вес товара в кг
            is_urgent: срочная доставка
            base_fare: базовая стоимость (по умолчанию из конфига)
            per_km_rate: стоимость за километр (по умолчанию из конфига)
            minimum_fare: минимальная стоимость (по умолчанию из конфига)
        
        Returns:
            Tuple[цена, расстояние_в_км]
        """
        # Используем значения по умолчанию из конфига
        if base_fare is None:
            base_fare = Config.DELIVERY_BASE_FARE
        if per_km_rate is None:
            per_km_rate = Config.PER_KM_RATE
        if minimum_fare is None:
            minimum_fare = Config.MINIMUM_FARE
        
        # Рассчитываем расстояние
        distance = PriceCalculator.calculate_distance(
            pickup_lat, pickup_lon, destination_lat, destination_lon
        )
        
        # Рассчитываем базовую стоимость
        price = base_fare + (distance * per_km_rate)
        
        # Добавляем коэффициент за вес
        weight_multiplier = 1.0
        if item_weight > 5:
            weight_multiplier = 1.2
        elif item_weight > 10:
            weight_multiplier = 1.5
        elif item_weight > 20:
            weight_multiplier = 2.0
        
        price *= weight_multiplier
        
        # Добавляем коэффициент за срочность
        if is_urgent:
            price *= 1.5
        
        # Проверяем минимальную стоимость
        if price < minimum_fare:
            price = minimum_fare
        
        # Округляем до целых рублей
        price = round(price)
        
        return price, distance
    
    @staticmethod
    def estimate_waiting_time(distance: float, traffic_condition: str = 'normal') -> int:
        """
        Оценка времени ожидания водителя
        
        Args:
            distance: расстояние в километрах
            traffic_condition: состояние дорог ('good', 'normal', 'bad')
        
        Returns:
            Время ожидания в минутах
        """
        # Базовое время (минуты)
        base_time = 5
        
        # Время на дорогу (примерно 2 минуты на км в городе)
        travel_time = distance * 2
        
        # Коэффициент загруженности дорог
        traffic_multipliers = {
            'good': 0.8,
            'normal': 1.0,
            'bad': 1.5
        }
        
        multiplier = traffic_multipliers.get(traffic_condition, 1.0)
        
        total_time = (base_time + travel_time) * multiplier
        
        # Округляем до целых минут
        return round(total_time)
    
    @staticmethod
    def format_price(price: float) -> str:
        """Форматирование цены для отображения"""
        return f"{price:.0f} ₽"
    
    @staticmethod
    def format_distance(distance: float) -> str:
        """Форматирование расстояния для отображения"""
        if distance < 1:
            return f"{distance * 1000:.0f} м"
        else:
            return f"{distance:.1f} км"
    
    @staticmethod
    def format_time(minutes: int) -> str:
        """Форматирование времени для отображения"""
        if minutes < 60:
            return f"{minutes} мин"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} ч"
            else:
                return f"{hours} ч {remaining_minutes} мин"
