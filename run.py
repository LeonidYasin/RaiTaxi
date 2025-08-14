#!/usr/bin/env python3
"""
Скрипт для быстрого запуска бота Рай-Такси
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from main import RaiTaxiBot

async def run_bot():
    """Запуск бота"""
    print("🚗 Запуск бота Рай-Такси...")
    
    try:
        bot = RaiTaxiBot()
        await bot.start_polling()
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_bot())
