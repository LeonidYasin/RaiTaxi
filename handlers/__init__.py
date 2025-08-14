"""
Обработчики команд для Рай-Такси
"""

# Импортируем только роутеры
from .client import router as client_router
from .driver import router as driver_router
from .admin import router as admin_router

__all__ = [
    'client_router',
    'driver_router',
    'admin_router'
]
