"""
Операции с базой данных Рай-Такси
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import User, Driver, Order, Location, Price, DatabaseManager
from config import Config

class UserOperations:
    """Операции с пользователями"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_user(self, telegram_id: int, username: str, first_name: str, 
                         last_name: str = None, phone: str = None) -> User:
        """Создание нового пользователя"""
        query = '''
            INSERT INTO users (telegram_id, username, first_name, last_name, phone)
            VALUES (?, ?, ?, ?, ?)
        '''
        cursor = await self.db.execute(query, (telegram_id, username, first_name, last_name, phone))
        await self.db.commit()
        
        return await self.get_user_by_telegram_id(telegram_id)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        query = 'SELECT * FROM users WHERE telegram_id = ?'
        cursor = await self.db.execute(query, (telegram_id,))
        row = cursor.fetchone()
        
        if row:
            return User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                phone=row['phone'],
                role=row['role'],
                rating=row['rating'],
                total_orders=row['total_orders'],
                created_at=datetime.fromisoformat(row['created_at']),
                is_active=bool(row['is_active'])
            )
        return None
    
    async def update_user_role(self, telegram_id: int, role: str) -> bool:
        """Обновление роли пользователя"""
        query = 'UPDATE users SET role = ? WHERE telegram_id = ?'
        await self.db.execute(query, (role, telegram_id))
        await self.db.commit()
        return True
    
    async def get_all_users(self) -> List[User]:
        """Получение всех пользователей"""
        query = 'SELECT * FROM users ORDER BY created_at DESC'
        cursor = await self.db.execute(query)
        users = []
        
        for row in cursor.fetchall():
            users.append(User(
                id=row['id'],
                telegram_id=row['telegram_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                phone=row['phone'],
                role=row['role'],
                rating=row['rating'],
                total_orders=row['total_orders'],
                created_at=datetime.fromisoformat(row['created_at']),
                is_active=bool(row['is_active'])
            ))
        
        return users

class DriverOperations:
    """Операции с водителями"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_driver(self, user_id: int, car_model: str, car_number: str, 
                           license_number: str) -> Driver:
        """Создание нового водителя"""
        query = '''
            INSERT INTO drivers (user_id, car_model, car_number, license_number)
            VALUES (?, ?, ?, ?)
        '''
        cursor = await self.db.execute(query, (user_id, car_model, car_number, license_number))
        await self.db.commit()
        
        return await self.get_driver_by_user_id(user_id)
    
    async def get_driver_by_user_id(self, user_id: int) -> Optional[Driver]:
        """Получение водителя по ID пользователя"""
        query = 'SELECT * FROM drivers WHERE user_id = ?'
        cursor = await self.db.execute(query, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return Driver(
                id=row['id'],
                user_id=row['user_id'],
                car_model=row['car_model'],
                car_number=row['car_number'],
                license_number=row['license_number'],
                is_available=bool(row['is_available']),
                current_location_lat=row['current_location_lat'],
                current_location_lon=row['current_location_lon'],
                rating=row['rating'],
                total_trips=row['total_trips'],
                total_earnings=row['total_earnings'],
                created_at=datetime.fromisoformat(row['created_at'])
            )
        return None
    
    async def update_driver_location(self, user_id: int, lat: float, lon: float) -> bool:
        """Обновление местоположения водителя"""
        query = '''
            UPDATE drivers 
            SET current_location_lat = ?, current_location_lon = ?
            WHERE user_id = ?
        '''
        await self.db.execute(query, (lat, lon, user_id))
        await self.db.commit()
        return True
    
    async def get_available_drivers(self) -> List[Driver]:
        """Получение доступных водителей"""
        query = '''
            SELECT d.* FROM drivers d
            JOIN users u ON d.user_id = u.id
            WHERE d.is_available = 1 AND u.is_active = 1
        '''
        cursor = await self.db.execute(query)
        drivers = []
        
        for row in cursor.fetchall():
            drivers.append(Driver(
                id=row['id'],
                user_id=row['user_id'],
                car_model=row['car_model'],
                car_number=row['car_number'],
                license_number=row['license_number'],
                is_available=bool(row['is_available']),
                current_location_lat=row['current_location_lat'],
                current_location_lon=row['current_location_lon'],
                rating=row['rating'],
                total_trips=row['total_trips'],
                total_earnings=row['total_earnings'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return drivers

class OrderOperations:
    """Операции с заказами"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def create_order(self, client_id: int, order_type: str, pickup_lat: float,
                          pickup_lon: float, pickup_address: str, 
                          destination_lat: float = None, destination_lon: float = None,
                          destination_address: str = None, description: str = None,
                          price: float = 0.0, distance: float = None) -> Order:
        """Создание нового заказа"""
        query = '''
            INSERT INTO orders (
                client_id, order_type, status, pickup_lat, pickup_lon, pickup_address,
                destination_lat, destination_lon, destination_address, description,
                price, distance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor = await self.db.execute(query, (
            client_id, order_type, 'new', pickup_lat, pickup_lon, pickup_address,
            destination_lat, destination_lon, destination_address, description,
            price, distance
        ))
        await self.db.commit()
        
        return await self.get_order_by_id(cursor.lastrowid)
    
    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Получение заказа по ID"""
        query = 'SELECT * FROM orders WHERE id = ?'
        cursor = await self.db.execute(query, (order_id,))
        row = cursor.fetchone()
        
        if row:
            return Order(
                id=row['id'],
                client_id=row['client_id'],
                driver_id=row['driver_id'],
                order_type=row['order_type'],
                status=row['status'],
                pickup_lat=row['pickup_lat'],
                pickup_lon=row['pickup_lon'],
                pickup_address=row['pickup_address'],
                destination_lat=row['destination_lat'],
                destination_lon=row['destination_lon'],
                destination_address=row['destination_address'],
                description=row['description'],
                price=row['price'],
                distance=row['distance'],
                created_at=datetime.fromisoformat(row['created_at']),
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                cancelled_at=datetime.fromisoformat(row['cancelled_at']) if row['cancelled_at'] else None,
                cancellation_reason=row['cancellation_reason']
            )
        return None
    
    async def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновление статуса заказа"""
        query = 'UPDATE orders SET status = ? WHERE id = ?'
        await self.db.execute(query, (status, order_id))
        await self.db.commit()
        return True
    
    async def assign_driver(self, order_id: int, driver_id: int) -> bool:
        """Назначение водителя на заказ"""
        query = '''
            UPDATE orders 
            SET driver_id = ?, status = 'driver_assigned'
            WHERE id = ?
        '''
        await self.db.execute(query, (driver_id, order_id))
        await self.db.commit()
        return True
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Order]:
        """Получение заказов пользователя"""
        query = '''
            SELECT * FROM orders 
            WHERE client_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        '''
        cursor = await self.db.execute(query, (user_id, limit))
        orders = []
        
        for row in cursor.fetchall():
            orders.append(Order(
                id=row['id'],
                client_id=row['client_id'],
                driver_id=row['driver_id'],
                order_type=row['order_type'],
                status=row['status'],
                pickup_lat=row['pickup_lat'],
                pickup_lon=row['pickup_lon'],
                pickup_address=row['pickup_address'],
                destination_lat=row['destination_lat'],
                destination_lon=row['destination_lon'],
                destination_address=row['destination_address'],
                description=row['description'],
                price=row['price'],
                distance=row['distance'],
                created_at=datetime.fromisoformat(row['created_at']),
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                cancelled_at=datetime.fromisoformat(row['cancelled_at']) if row['cancelled_at'] else None,
                cancellation_reason=row['cancellation_reason']
            ))
        
        return orders
    
    async def get_available_orders(self) -> List[Order]:
        """Получение доступных заказов для водителей"""
        query = '''
            SELECT * FROM orders 
            WHERE status = 'new' OR status = 'searching_driver'
            ORDER BY created_at ASC
        '''
        cursor = await self.db.execute(query)
        orders = []
        
        for row in cursor.fetchall():
            orders.append(Order(
                id=row['id'],
                client_id=row['client_id'],
                driver_id=row['driver_id'],
                order_type=row['order_type'],
                status=row['status'],
                pickup_lat=row['pickup_lat'],
                pickup_lon=row['pickup_lon'],
                pickup_address=row['pickup_address'],
                destination_lat=row['destination_lat'],
                destination_lon=row['destination_lon'],
                destination_address=row['destination_address'],
                description=row['description'],
                price=row['price'],
                distance=row['distance'],
                created_at=datetime.fromisoformat(row['created_at']),
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                cancelled_at=datetime.fromisoformat(row['cancelled_at']) if row['cancelled_at'] else None,
                cancellation_reason=row['cancellation_reason']
            ))
        
        return orders
