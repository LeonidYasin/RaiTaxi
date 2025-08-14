# 🚀 Оптимизация Рай-Такси для слабых Android-устройств

## 📱 Требования к устройству

### Минимальные требования:
- **Android**: 7.0+ (API 24)
- **RAM**: 2GB
- **Хранилище**: 5GB свободного места
- **Процессор**: Qualcomm Snapdragon 430 или аналогичный

### Рекомендуемые требования:
- **Android**: 9.0+ (API 28)
- **RAM**: 4GB+
- **Хранилище**: 10GB+ свободного места
- **Процессор**: Qualcomm Snapdragon 660+ или аналогичный

## ⚡ Оптимизация производительности

### 1. Настройка Python

#### Оптимизация интерпретатора:
```bash
# В Termux создайте файл ~/.pythonrc
echo "import sys" > ~/.pythonrc
echo "sys.setrecursionlimit(1000)" >> ~/.pythonrc
echo "import gc" >> ~/.pythonrc
echo "gc.set_threshold(700, 10, 10)" >> ~/.pythonrc
```

#### Установка оптимизированных версий:
```bash
# Установка PyPy для лучшей производительности (опционально)
pkg install pypy
pip install --upgrade pip setuptools wheel
```

### 2. Оптимизация базы данных

#### Настройка SQLite:
```python
# В database/models.py добавьте:
import sqlite3

# Оптимизация для слабых устройств
sqlite3.enable_callback_tracebacks(False)
sqlite3.threadsafety = 1

# В DatabaseManager.connect():
self.connection.execute("PRAGMA journal_mode = WAL")
self.connection.execute("PRAGMA synchronous = NORMAL")
self.connection.execute("PRAGMA cache_size = 1000")
self.connection.execute("PRAGMA temp_store = MEMORY")
```

#### Индексы для оптимизации:
```sql
-- Создайте дополнительные индексы
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_type_status ON orders(order_type, status);
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);
```

### 3. Оптимизация памяти

#### Ограничение размера изображений:
```python
# В utils/maps.py
from PIL import Image

def optimize_image(image_data: bytes, max_size: tuple = (400, 300)) -> bytes:
    """Оптимизация изображения для слабых устройств"""
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Изменяем размер если изображение слишком большое
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Сжимаем изображение
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        print(f"Ошибка оптимизации изображения: {e}")
        return image_data
```

#### Кэширование с ограничением:
```python
# В utils/cache.py
import time
from collections import OrderedDict

class MemoryCache:
    """Простой кэш в памяти с ограничением размера"""
    
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def get(self, key: str):
        """Получение значения из кэша"""
        if key in self.cache:
            # Перемещаем в конец (LRU)
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        return None
    
    def set(self, key: str, value, ttl: int = 3600):
        """Установка значения в кэш"""
        if len(self.cache) >= self.max_size:
            # Удаляем самый старый элемент
            self.cache.popitem(last=False)
        
        self.cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
    
    def cleanup(self):
        """Очистка просроченных элементов"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.cache.items()
            if data['expires'] < current_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
```

### 4. Оптимизация сети

#### Умная система повторных попыток:
```python
# В utils/network.py
import asyncio
import aiohttp
from typing import Optional

class SmartRetry:
    """Умная система повторных попыток для слабых соединений"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def request(self, session: aiohttp.ClientSession, url: str, 
                     method: str = 'GET', **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Выполнение запроса с повторными попытками"""
        
        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status < 500:  # Не повторяем для клиентских ошибок
                        return response
                    
                    # Серверная ошибка - повторяем
                    if attempt < self.max_retries - 1:
                        delay = self.base_delay * (2 ** attempt)  # Экспоненциальная задержка
                        await asyncio.sleep(delay)
                        continue
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"Ошибка сети после {self.max_retries} попыток: {e}")
                    return None
        
        return None
```

#### Сжатие данных:
```python
# В utils/compression.py
import gzip
import zlib

def compress_data(data: bytes, algorithm: str = 'gzip') -> bytes:
    """Сжатие данных для экономии трафика"""
    try:
        if algorithm == 'gzip':
            return gzip.compress(data, compresslevel=6)
        elif algorithm == 'zlib':
            return zlib.compress(data, level=6)
        else:
            return data
    except Exception:
        return data

def decompress_data(data: bytes, algorithm: str = 'gzip') -> bytes:
    """Распаковка сжатых данных"""
    try:
        if algorithm == 'gzip':
            return gzip.decompress(data)
        elif algorithm == 'zlib':
            return zlib.decompress(data)
        else:
            return data
    except Exception:
        return data
```

## 🔧 Настройка Termux

### 1. Оптимизация системы

#### Создайте файл `~/.bashrc`:
```bash
# Оптимизация для слабых устройств
export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Ограничение использования памяти
ulimit -v 1048576  # 1GB виртуальной памяти

# Приоритет процесса
renice -n 10 $$

# Автозапуск с оптимизацией
if [ -d ~/raitaxi ]; then
    echo "🚗 Рай-Такси оптимизирован для слабых устройств"
fi
```

### 2. Настройка cron для автоматической очистки

```bash
# Установка cron
pkg install cronie

# Редактирование cron
crontab -e

# Добавьте строки:
# Очистка кэша каждые 6 часов
0 */6 * * * cd ~/raitaxi && python -c "from utils.maps import MapService; MapService().clear_cache()"

# Перезапуск бота каждые 12 часов (если нужно)
0 */12 * * * cd ~/raitaxi && ./restart.sh

# Очистка логов старше 7 дней
0 2 * * 0 find ~/raitaxi -name "*.log" -mtime +7 -delete
```

### 3. Мониторинг ресурсов

#### Создайте скрипт мониторинга `~/raitaxi/monitor.sh`:
```bash
#!/data/data/com.termux/files/usr/bin/bash

echo "📊 Мониторинг ресурсов Рай-Такси"
echo "================================"

# Использование памяти
echo "💾 Память:"
free -h 2>/dev/null || echo "Команда free недоступна"

# Использование диска
echo "💿 Диск:"
df -h ~/raitaxi

# Процессы Python
echo "🐍 Процессы Python:"
ps aux | grep python | grep -v grep

# Размер базы данных
if [ -f ~/raitaxi/taxi.db ]; then
    echo "🗄️ Размер БД:"
    ls -lh ~/raitaxi/taxi.db
fi

# Размер логов
echo "📝 Размер логов:"
du -sh ~/raitaxi/*.log 2>/dev/null || echo "Логи не найдены"

# Размер кэша карт
if [ -d ~/raitaxi/static/images/maps ]; then
    echo "🗺️ Размер кэша карт:"
    du -sh ~/raitaxi/static/images/maps
fi
```

chmod +x ~/raitaxi/monitor.sh

## 📱 Оптимизация для конкретных устройств

### 1. Очень слабые устройства (1-2GB RAM)

```python
# В config.py уменьшите лимиты
MAX_REQUESTS_PER_MINUTE = 15  # Вместо 30
MAX_REQUESTS_PER_HOUR = 150   # Вместо 300
CACHE_TTL = 1800              # Вместо 3600 (30 минут)
MAX_CACHE_SIZE = 30           # Вместо 100

# В utils/maps.py уменьшите размеры карт
MAP_WIDTH = 400   # Вместо 600
MAP_HEIGHT = 300  # Вместо 400
```

### 2. Устройства с медленным интернетом

```python
# В utils/maps.py увеличьте таймауты
TIMEOUT = 30  # Вместо 10 секунд

# В main.py добавьте задержки между запросами
await asyncio.sleep(0.1)  # 100ms между запросами
```

### 3. Устройства с ограниченным хранилищем

```python
# Автоматическая очистка старых данных
async def cleanup_old_data():
    """Очистка старых данных для экономии места"""
    try:
        # Удаляем заказы старше 30 дней
        thirty_days_ago = datetime.now() - timedelta(days=30)
        await self.db.execute(
            "DELETE FROM orders WHERE created_at < ?",
            (thirty_days_ago,)
        )
        
        # Удаляем старые геолокации
        await self.db.execute(
            "DELETE FROM locations WHERE timestamp < ?",
            (thirty_days_ago,)
        )
        
        # Очищаем кэш карт
        self.map_service.clear_cache(max_age_hours=12)
        
        logger.info("Очистка старых данных завершена")
        
    except Exception as e:
        logger.error(f"Ошибка очистки данных: {e}")
```

## 🚨 Решение проблем

### 1. Бот зависает или работает медленно

```bash
# Проверьте использование ресурсов
~/raitaxi/monitor.sh

# Перезапустите бота
cd ~/raitaxi && ./restart.sh

# Очистите кэш
cd ~/raitaxi && python -c "from utils.maps import MapService; MapService().clear_cache()"
```

### 2. Нехватка памяти

```bash
# Очистите кэш Termux
pkg clean

# Перезапустите Termux
exit
# Запустите заново

# Уменьшите лимиты в config.py
```

### 3. Медленная работа базы данных

```bash
# Оптимизируйте базу данных
cd ~/raitaxi
sqlite3 taxi.db "VACUUM;"
sqlite3 taxi.db "ANALYZE;"
```

## 📈 Мониторинг производительности

### Создайте скрипт `~/raitaxi/performance.py`:

```python
#!/usr/bin/env python3
"""
Мониторинг производительности Рай-Такси
"""

import psutil
import sqlite3
import os
import time
from datetime import datetime

def get_system_stats():
    """Получение статистики системы"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu': cpu_percent,
        'memory_percent': memory.percent,
        'memory_available': memory.available // (1024**3),  # GB
        'disk_percent': disk.percent,
        'disk_free': disk.free // (1024**3)  # GB
    }

def get_database_stats():
    """Получение статистики базы данных"""
    try:
        conn = sqlite3.connect('taxi.db')
        cursor = conn.cursor()
        
        # Размер базы данных
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        db_size = (page_count * page_size) // (1024**2)  # MB
        
        # Количество записей
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders;")
        orders_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM drivers;")
        drivers_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'db_size_mb': db_size,
            'users_count': users_count,
            'orders_count': orders_count,
            'drivers_count': drivers_count
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    """Главная функция"""
    print(f"📊 Мониторинг производительности - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Системная статистика
    sys_stats = get_system_stats()
    print("💻 Система:")
    print(f"   CPU: {sys_stats['cpu']}%")
    print(f"   Память: {sys_stats['memory_percent']}% (доступно: {sys_stats['memory_available']}GB)")
    print(f"   Диск: {sys_stats['disk_percent']}% (свободно: {sys_stats['disk_free']}GB)")
    
    # Статистика базы данных
    db_stats = get_database_stats()
    if 'error' not in db_stats:
        print("\n🗄️ База данных:")
        print(f"   Размер: {db_stats['db_size_mb']}MB")
        print(f"   Пользователей: {db_stats['users_count']}")
        print(f"   Заказов: {db_stats['orders_count']}")
        print(f"   Водителей: {db_stats['drivers_count']}")
    else:
        print(f"\n❌ Ошибка БД: {db_stats['error']}")
    
    # Размер файлов проекта
    print("\n📁 Файлы проекта:")
    try:
        for root, dirs, files in os.walk('.'):
            total_size = sum(os.path.getsize(os.path.join(root, name)) for name in files)
            if total_size > 0:
                print(f"   {root}: {total_size // 1024}KB")
    except Exception as e:
        print(f"   Ошибка сканирования: {e}")

if __name__ == "__main__":
    main()
```

## 🎯 Заключение

Следуя этим рекомендациям, вы сможете запустить Рай-Такси даже на очень слабых Android-устройствах. Основные принципы оптимизации:

1. **Минимизация использования памяти** - ограничение кэша, сжатие данных
2. **Оптимизация базы данных** - правильные индексы, периодическая очистка
3. **Умная работа с сетью** - повторные попытки, сжатие, таймауты
4. **Мониторинг ресурсов** - отслеживание использования памяти и диска
5. **Автоматическая очистка** - удаление старых данных и кэша

Регулярно используйте скрипт мониторинга для отслеживания производительности и своевременного выявления проблем.
