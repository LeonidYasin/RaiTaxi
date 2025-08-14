"""
Валидация данных для Рай-Такси
"""

import re
from typing import Tuple, Optional

class DataValidator:
    """Класс для валидации данных"""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
        """
        Валидация географических координат
        
        Args:
            lat: широта
            lon: долгота
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return False, "Координаты должны быть числами"
        
        if lat < -90 or lat > 90:
            return False, "Широта должна быть в диапазоне от -90 до 90"
        
        if lon < -180 or lon > 180:
            return False, "Долгота должна быть в диапазоне от -180 до 180"
        
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """
        Валидация номера телефона
        
        Args:
            phone: номер телефона
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not phone:
            return False, "Номер телефона не может быть пустым"
        
        # Убираем все символы кроме цифр
        digits_only = re.sub(r'\D', '', phone)
        
        # Проверяем длину (7-15 цифр)
        if len(digits_only) < 7 or len(digits_only) > 15:
            return False, "Номер телефона должен содержать от 7 до 15 цифр"
        
        return True, ""
    
    @staticmethod
    def validate_car_number(car_number: str) -> Tuple[bool, str]:
        """
        Валидация номера автомобиля
        
        Args:
            car_number: номер автомобиля
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not car_number:
            return False, "Номер автомобиля не может быть пустым"
        
        # Убираем пробелы и приводим к верхнему регистру
        car_number = car_number.strip().upper()
        
        # Проверяем несколько форматов российских номеров
        patterns = [
            r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$',  # А123БВ77, М777ММ77
            r'^[АВЕКМНОРСТУХ]\d{2}[АВЕКМНОРСТУХ]{2}\d{2,3}$',  # А12БВ77, М77ММ77
            r'^\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$',  # 123БВ77, 777ММ77
            r'^[АВЕКМНОРСТУХ]{2}\d{3}\d{2,3}$',  # АБ12377, ММ77777
        ]
        
        for pattern in patterns:
            if re.match(pattern, car_number):
                return True, ""
        
        return False, "Неверный формат номера автомобиля. Примеры: А123БВ77, М777ММ77, 123БВ77"
    
    @staticmethod
    def validate_price(price: float) -> Tuple[bool, str]:
        """
        Валидация цены
        
        Args:
            price: цена
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not isinstance(price, (int, float)):
            return False, "Цена должна быть числом"
        
        if price < 0:
            return False, "Цена не может быть отрицательной"
        
        if price > 10000:
            return False, "Цена слишком высокая"
        
        return True, ""
    
    @staticmethod
    def validate_distance(distance: float) -> Tuple[bool, str]:
        """
        Валидация расстояния
        
        Args:
            distance: расстояние в километрах
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not isinstance(distance, (int, float)):
            return False, "Расстояние должно быть числом"
        
        if distance < 0:
            return False, "Расстояние не может быть отрицательным"
        
        if distance > 1000:
            return False, "Расстояние слишком большое"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Валидация имени пользователя
        
        Args:
            username: имя пользователя
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not username:
            return False, "Имя пользователя не может быть пустым"
        
        # Проверяем длину
        if len(username) < 3 or len(username) > 30:
            return False, "Имя пользователя должно содержать от 3 до 30 символов"
        
        # Проверяем допустимые символы
        pattern = r'^[a-zA-Z0-9_]+$'
        if not re.match(pattern, username):
            return False, "Имя пользователя может содержать только буквы, цифры и знак подчеркивания"
        
        return True, ""
    
    @staticmethod
    def validate_order_description(description: str) -> Tuple[bool, str]:
        """
        Валидация описания заказа
        
        Args:
            description: описание заказа
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not description:
            return False, "Описание заказа не может быть пустым"
        
        if len(description) < 5 or len(description) > 500:
            return False, "Описание заказа должно содержать от 5 до 500 символов"
        
        return True, ""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Очистка текста от потенциально опасных символов
        
        Args:
            text: исходный текст
        
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
        
        # Убираем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Обрезаем пробелы в начале и конце
        text = text.strip()
        
        return text
    
    @staticmethod
    def validate_rating(rating: int) -> Tuple[bool, str]:
        """
        Валидация рейтинга
        
        Args:
            rating: рейтинг (1-5)
        
        Returns:
            Tuple[валидно, сообщение_об_ошибке]
        """
        if not isinstance(rating, int):
            return False, "Рейтинг должен быть целым числом"
        
        if rating < 1 or rating > 5:
            return False, "Рейтинг должен быть от 1 до 5"
        
        return True, ""
