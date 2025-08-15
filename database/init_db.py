"""
Инициализация базы данных Рай-Такси
"""

import sqlite3
import os
from config import Config

def init_database():
    """Инициализация базы данных"""
    
    # Создаем папку для базы данных если её нет
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Подключаемся к базе данных
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Создаем таблицу пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT NOT NULL,
                last_name TEXT,
                phone TEXT,
                role TEXT DEFAULT 'client',
                rating REAL DEFAULT 0.0,
                total_orders INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Создаем таблицу водителей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                car_model TEXT NOT NULL,
                car_number TEXT NOT NULL,
                license_number TEXT NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                current_location_lat REAL,
                current_location_lon REAL,
                rating REAL DEFAULT 0.0,
                total_trips INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                driver_id INTEGER,
                order_type TEXT NOT NULL,
                status TEXT NOT NULL,
                pickup_lat REAL NOT NULL,
                pickup_lon REAL NOT NULL,
                pickup_address TEXT,
                destination_lat REAL,
                destination_lon REAL,
                destination_address TEXT,
                description TEXT,
                price REAL NOT NULL,
                distance REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                cancellation_reason TEXT,
                FOREIGN KEY (client_id) REFERENCES users (id),
                FOREIGN KEY (driver_id) REFERENCES drivers (id)
            )
        ''')
        
        # Создаем таблицу геолокаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу тарифов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_type TEXT NOT NULL,
                base_fare REAL NOT NULL,
                per_km_rate REAL NOT NULL,
                minimum_fare REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем индексы для оптимизации
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        
        # Вставляем базовые тарифы
        cursor.execute('''
            INSERT OR IGNORE INTO prices (service_type, base_fare, per_km_rate, minimum_fare)
            VALUES 
                ('taxi', ?, ?, ?),
                ('delivery', ?, ?, ?)
        ''', (
            Config.BASE_FARE, Config.PER_KM_RATE, Config.MINIMUM_FARE,
            Config.DELIVERY_BASE_FARE, Config.PER_KM_RATE, Config.MINIMUM_FARE
        ))
        
        # Подтверждаем изменения
        conn.commit()
        
        print("✅ База данных успешно инициализирована!")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚗 Инициализация базы данных Рай-Такси...")
    init_database()
    print("✨ Готово!")
