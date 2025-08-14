import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """Конфигурация бота Рай-Такси"""
    
    # Основные настройки
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_NAME = "Рай-Такси 🚗"
    BOT_DESCRIPTION = "Ваш соседский водитель уже в пути! Заказ такси и доставки в малых городах России."
    
    # База данных
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'taxi.db')
    
    # Карты
    OSM_STATIC_MAPS_URL = os.getenv('OSM_STATIC_MAPS_URL', 
                                   'https://staticmap.openstreetmap.de/staticmap.php')
    MAP_WIDTH = 600
    MAP_HEIGHT = 400
    MAP_ZOOM = 14
    
    # Тарифы (в рублях)
    BASE_FARE = int(os.getenv('BASE_FARE', 100))
    PER_KM_RATE = int(os.getenv('PER_KM_RATE', 15))
    MINIMUM_FARE = int(os.getenv('MINIMUM_FARE', 50))
    DELIVERY_BASE_FARE = int(os.getenv('DELIVERY_BASE_FARE', 80))
    
    # Безопасность
    MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', 30))
    MAX_REQUESTS_PER_HOUR = int(os.getenv('MAX_REQUESTS_PER_HOUR', 300))
    
    # Логирование
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'taxi_bot.log')
    
    # Кэширование
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
    MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', 100))
    
    # Уведомления
    NOTIFICATION_TIMEOUT = int(os.getenv('NOTIFICATION_TIMEOUT', 30))
    DRIVER_SEARCH_TIMEOUT = int(os.getenv('DRIVER_SEARCH_TIMEOUT', 120))
    
    # Роли пользователей
    USER_ROLES = {
        'client': 'client',
        'driver': 'driver', 
        'admin': 'admin'
    }
    
    # Статусы заказов
    ORDER_STATUSES = {
        'new': 'new',
        'searching_driver': 'searching_driver',
        'driver_assigned': 'driver_assigned',
        'in_progress': 'in_progress',
        'completed': 'completed',
        'cancelled': 'cancelled'
    }
    
    # Типы заказов
    ORDER_TYPES = {
        'taxi': 'taxi',
        'delivery': 'delivery'
    }
    
    # Сообщения
    MESSAGES = {
        'welcome': "🚗 Добро пожаловать в Рай-Такси!\n\n"
                  "Ваш соседский водитель уже в пути! 🚀\n\n"
                  "Выберите, что вам нужно:",
        
        'taxi_order': "🚕 Заказ такси\n\n"
                     "Отправьте ваше текущее местоположение или введите адрес:",
        
        'delivery_order': "📦 Заказ доставки\n\n"
                         "Что вы хотите заказать?",
        
        'location_needed': "📍 Пожалуйста, отправьте ваше местоположение или введите адрес.",
        
        'destination_needed': "🎯 Куда едем? Отправьте адрес назначения:",
        
        'order_created': "✅ Заказ создан! Ищем водителя...",
        
        'driver_found': "🚗 Водитель найден! Ожидайте.",
        
        'order_completed': "🎉 Поездка завершена! Оцените водителя.",
        
        'error_occurred': "❌ Произошла ошибка. Попробуйте позже.",
        
        'access_denied': "🚫 У вас нет доступа к этой функции.",
        
        'rate_limit_exceeded': "⏰ Слишком много запросов. Подождите немного."
    }
    
    # Кнопки
    BUTTONS = {
        'taxi': '🚕 Заказать такси',
        'delivery': '📦 Заказать доставку',
        'my_orders': '📋 Мои заказы',
        'profile': '👤 Профиль',
        'help': '❓ Помощь',
        'cancel': '❌ Отмена',
        'confirm': '✅ Подтвердить',
        'back': '⬅️ Назад'
    }
    
    @classmethod
    def validate(cls):
        """Проверка корректности конфигурации"""
        print(f"🔍 Диагностика BOT_TOKEN:")
        print(f"   Значение: '{cls.BOT_TOKEN}'")
        print(f"   Тип: {type(cls.BOT_TOKEN)}")
        print(f"   Длина: {len(cls.BOT_TOKEN) if cls.BOT_TOKEN else 0}")
        
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")
        
        # Проверяем формат токена (должен содержать двоеточие и быть достаточно длинным)
        if ':' not in cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 20:
            raise ValueError(f"Неверный формат BOT_TOKEN: должен содержать двоеточие и быть длиной минимум 20 символов")
        
        print(f"✅ BOT_TOKEN прошел валидацию")
        return True
