"""
Система защиты от спама для Рай-Такси
"""

import time
from typing import Dict, Tuple
from collections import defaultdict
from config import Config

class RateLimiter:
    """Система ограничения количества запросов"""
    
    def __init__(self):
        self.requests_per_minute = Config.MAX_REQUESTS_PER_MINUTE
        self.requests_per_hour = Config.MAX_REQUESTS_PER_HOUR
        
        # Хранилище запросов: {user_id: [(timestamp, action), ...]}
        self.user_requests = defaultdict(list)
        
        # Очистка старых записей каждые 10 минут
        self.last_cleanup = time.time()
        self.cleanup_interval = 600
    
    def is_allowed(self, user_id: int, action: str = "default") -> Tuple[bool, str]:
        """
        Проверка, разрешен ли запрос
        
        Args:
            user_id: ID пользователя
            action: тип действия
        
        Returns:
            Tuple[разрешено, сообщение_об_ошибке]
        """
        current_time = time.time()
        
        # Периодическая очистка старых записей
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests()
            self.last_cleanup = current_time
        
        # Получаем список запросов пользователя
        user_requests = self.user_requests[user_id]
        
        # Удаляем старые записи (старше часа)
        user_requests = [req for req in user_requests if current_time - req[0] < 3600]
        self.user_requests[user_id] = user_requests
        
        # Проверяем ограничение в минуту
        minute_ago = current_time - 60
        requests_last_minute = len([req for req in user_requests if req[0] > minute_ago])
        
        if requests_last_minute >= self.requests_per_minute:
            return False, f"Слишком много запросов в минуту. Подождите немного."
        
        # Проверяем ограничение в час
        hour_ago = current_time - 3600
        requests_last_hour = len([req for req in user_requests if req[0] > hour_ago])
        
        if requests_last_hour >= self.requests_per_hour:
            return False, f"Слишком много запросов в час. Подождите немного."
        
        # Запрос разрешен, добавляем в историю
        self.user_requests[user_id].append((current_time, action))
        
        return True, ""
    
    def _cleanup_old_requests(self):
        """Очистка старых записей"""
        current_time = time.time()
        cutoff_time = current_time - 3600  # Удаляем записи старше часа
        
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                req for req in self.user_requests[user_id] 
                if req[0] > cutoff_time
            ]
            
            # Удаляем пользователей без запросов
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        current_time = time.time()
        user_requests = self.user_requests[user_id]
        
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        requests_last_minute = len([req for req in user_requests if req[0] > minute_ago])
        requests_last_hour = len([req for req in user_requests if req[0] > hour_ago])
        
        return {
            'requests_last_minute': requests_last_minute,
            'requests_last_hour': requests_last_hour,
            'limit_per_minute': self.requests_per_minute,
            'limit_per_hour': self.requests_per_hour,
            'can_make_request': requests_last_minute < self.requests_per_minute and 
                               requests_last_hour < self.requests_per_hour
        }
    
    def reset_user_limits(self, user_id: int):
        """Сброс ограничений для пользователя"""
        if user_id in self.user_requests:
            del self.user_requests[user_id]
    
    def get_system_stats(self) -> Dict:
        """Получение общей статистики системы"""
        current_time = time.time()
        total_users = len(self.user_requests)
        
        # Подсчитываем общее количество запросов за последний час
        total_requests_last_hour = 0
        for user_requests in self.user_requests.values():
            hour_ago = current_time - 3600
            requests_last_hour = len([req for req in user_requests if req[0] > hour_ago])
            total_requests_last_hour += requests_last_hour
        
        return {
            'total_users': total_users,
            'total_requests_last_hour': total_requests_last_hour,
            'requests_per_minute_limit': self.requests_per_minute,
            'requests_per_hour_limit': self.requests_per_hour
        }

class ActionRateLimiter:
    """Специализированный ограничитель для конкретных действий"""
    
    def __init__(self, action_name: str, max_requests: int, time_window: int):
        """
        Args:
            action_name: название действия
            max_requests: максимальное количество запросов
            time_window: временное окно в секундах
        """
        self.action_name = action_name
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> Tuple[bool, str]:
        """Проверка разрешения для конкретного действия"""
        current_time = time.time()
        cutoff_time = current_time - self.time_window
        
        # Очищаем старые записи
        self.requests[user_id] = [
            req for req in self.requests[user_id] if req > cutoff_time
        ]
        
        # Проверяем лимит
        if len(self.requests[user_id]) >= self.max_requests:
            remaining_time = self.time_window - (current_time - self.requests[user_id][0])
            return False, f"Слишком много запросов {self.action_name}. Подождите {int(remaining_time)} сек."
        
        # Добавляем запрос
        self.requests[user_id].append(current_time)
        return True, ""

# Специализированные ограничители для разных действий
class TaxiOrderLimiter(ActionRateLimiter):
    """Ограничитель для заказов такси"""
    def __init__(self):
        super().__init__("заказов такси", 5, 300)  # 5 заказов за 5 минут

class DeliveryOrderLimiter(ActionRateLimiter):
    """Ограничитель для заказов доставки"""
    def __init__(self):
        super().__init__("заказов доставки", 3, 300)  # 3 заказа за 5 минут

class LocationUpdateLimiter(ActionRateLimiter):
    """Ограничитель для обновления местоположения"""
    def __init__(self):
        super().__init__("обновлений местоположения", 10, 60)  # 10 обновлений в минуту
