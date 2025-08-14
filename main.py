"""
Главный файл бота Рай-Такси
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import Config
from database.models import DatabaseManager
from database.operations import UserOperations, OrderOperations, DriverOperations
from handlers.client import ClientHandlers, router as client_router
from handlers.driver import DriverHandlers, router as driver_router
from handlers.admin import AdminHandlers, router as admin_router
from utils.rate_limiter import RateLimiter

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class RaiTaxiBot:
    """Основной класс бота Рай-Такси"""
    
    def __init__(self):
        """Инициализация бота"""
        # Проверяем конфигурацию
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            sys.exit(1)
        
        # Инициализируем бота и диспетчер
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
        # Инициализируем базу данных
        self.db_manager = DatabaseManager(Config.DATABASE_PATH)
        
        # Инициализируем операции с БД
        self.user_ops = UserOperations(self.db_manager)
        self.order_ops = OrderOperations(self.db_manager)
        self.driver_ops = DriverOperations(self.db_manager)
        
        # Инициализируем обработчики
        self.client_handlers = ClientHandlers(self.user_ops, self.order_ops)
        self.driver_handlers = DriverHandlers(self.user_ops, self.order_ops, self.driver_ops)
        self.admin_handlers = AdminHandlers(self.user_ops, self.order_ops, self.driver_ops)
        
        # Инициализируем систему защиты от спама
        self.rate_limiter = RateLimiter()
        
        # Регистрируем роутеры
        self._register_routers()
        
        # Инициализируем операции с БД для обработчиков
        from handlers.client import set_operations
        set_operations(self.user_ops, self.order_ops)
        
        # Регистрируем middleware
        self._register_middleware()
    
    def _register_routers(self):
        """Регистрация роутеров"""
        # Подключаем роутеры
        self.dp.include_router(client_router)
        self.dp.include_router(driver_router)
        self.dp.include_router(admin_router)
        
        logger.info("Роутеры зарегистрированы")
    
    def _register_middleware(self):
        """Регистрация middleware"""
        # Здесь можно добавить middleware для логирования, авторизации и т.д.
        pass
    
    async def on_startup(self, webhook_url: str = None):
        """Действия при запуске бота"""
        logger.info("🚗 Запуск бота Рай-Такси...")
        
        # Подключаемся к базе данных
        if await self.db_manager.connect():
            logger.info("✅ Подключение к базе данных установлено")
        else:
            logger.error("❌ Ошибка подключения к базе данных")
            return False
        
        # Устанавливаем webhook если указан
        if webhook_url:
            await self.bot.set_webhook(url=webhook_url)
            logger.info(f"🌐 Webhook установлен: {webhook_url}")
        
        # Отправляем сообщение о запуске (если есть админ)
        try:
            # Здесь можно добавить уведомление администратора о запуске
            pass
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о запуске: {e}")
        
        logger.info("🚀 Бот Рай-Такси успешно запущен!")
        return True
    
    async def on_shutdown(self):
        """Действия при остановке бота"""
        logger.info("🛑 Остановка бота Рай-Такси...")
        
        # Удаляем webhook
        await self.bot.delete_webhook()
        
        # Отключаемся от базы данных
        await self.db_manager.disconnect()
        
        # Закрываем сессию бота
        await self.bot.session.close()
        
        logger.info("✅ Бот Рай-Такси остановлен")
    
    async def start_polling(self):
        """Запуск бота в режиме polling"""
        try:
            await self.on_startup()
            
            # Запускаем polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
        finally:
            await self.on_shutdown()
    
    async def start_webhook(self, webhook_url: str, webhook_path: str = "/webhook"):
        """Запуск бота в режиме webhook"""
        try:
            await self.on_startup(webhook_url)
            
            # Создаем приложение aiohttp
            app = web.Application()
            
            # Настраиваем webhook
            webhook_handler = SimpleRequestHandler(
                dispatcher=self.dp,
                bot=self.bot
            )
            webhook_handler.register(app, path=webhook_path)
            
            # Запускаем приложение
            web.run_app(app, host="0.0.0.0", port=8000)
            
        except Exception as e:
            logger.error(f"Ошибка запуска webhook: {e}")
        finally:
            await self.on_shutdown()

async def main():
    """Главная функция"""
    # Создаем экземпляр бота
    bot = RaiTaxiBot()
    
    # Определяем режим запуска
    if len(sys.argv) > 1 and sys.argv[1] == "--webhook":
        # Запуск в режиме webhook
        webhook_url = sys.argv[2] if len(sys.argv) > 2 else "https://your-domain.com/webhook"
        await bot.start_webhook(webhook_url)
    else:
        # Запуск в режиме polling (по умолчанию)
        await bot.start_polling()

if __name__ == "__main__":
    try:
        # Запускаем бота
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
