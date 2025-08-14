"""
Модели данных для базы Рай-Такси
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    phone: Optional[str]
    role: str = 'client'
    rating: float = 0.0
    total_orders: int = 0
    created_at: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Driver:
    """Модель водителя"""
    id: int
    user_id: int
    car_model: str
    car_number: str
    license_number: str
    is_available: bool = True
    current_location_lat: Optional[float] = None
    current_location_lon: Optional[float] = None
    rating: float = 0.0
    total_trips: int = 0
    total_earnings: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Order:
    """Модель заказа"""
    id: int
    client_id: int
    driver_id: Optional[int]
    order_type: str  # 'taxi' или 'delivery'
    status: str
    pickup_lat: float
    pickup_lon: float
    pickup_address: str
    destination_lat: Optional[float]
    destination_lon: Optional[float]
    destination_address: Optional[str]
    description: Optional[str]  # для доставки
    price: float
    distance: Optional[float]  # в км
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Location:
    """Модель геолокации"""
    id: int
    user_id: int
    latitude: float
    longitude: float
    address: Optional[str]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class Price:
    """Модель тарифов"""
    id: int
    service_type: str  # 'taxi' или 'delivery'
    base_fare: float
    per_km_rate: float
    minimum_fare: float
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    async def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return True
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    async def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Выполнение SQL запроса"""
        if not self.connection:
            await self.connect()
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor
    
    async def commit(self):
        """Подтверждение изменений"""
        if self.connection:
            self.connection.commit()
    
    async def rollback(self):
        """Откат изменений"""
        if self.connection:
            self.connection.rollback()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
