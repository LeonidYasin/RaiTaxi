#!/data/data/com.termux/files/usr/bin/bash

echo "🚗 Установка бота Рай-Такси в Termux..."
echo "=================================="

# Обновляем систему
echo "📦 Обновление системы..."
pkg update -y && pkg upgrade -y

# Устанавливаем необходимые пакеты
echo "📦 Установка необходимых пакетов..."
pkg install -y python git sqlite

# Проверяем версию Python
python_version=$(python --version 2>&1)
echo "🐍 Установлена версия Python: $python_version"

# Устанавливаем pip если не установлен
if ! command -v pip &> /dev/null; then
    echo "📦 Установка pip..."
    pkg install -y python-pip
fi

# Устанавливаем Python зависимости
echo "📦 Установка Python зависимостей..."
pip install aiogram python-dotenv requests pillow aiofiles asyncio-throttle

# Создаем рабочую директорию
echo "📁 Создание рабочей директории..."
cd ~
mkdir -p raitaxi
cd raitaxi

# Клонируем проект (если есть git репозиторий)
# echo "📥 Клонирование проекта..."
# git clone https://github.com/your-username/raitaxi.git .

# Создаем структуру проекта
echo "📁 Создание структуры проекта..."
mkdir -p database handlers services utils static/images/maps

# Создаем файл конфигурации
echo "⚙️ Создание файла конфигурации..."
cat > .env << EOF
# Токен вашего Telegram бота (получите у @BotFather)
BOT_TOKEN=your_bot_token_here

# Настройки базы данных
DATABASE_PATH=taxi.db

# Настройки карт (OSM Static Maps)
OSM_STATIC_MAPS_URL=https://staticmap.openstreetmap.de/staticmap.php

# Настройки тарифов (в рублях)
BASE_FARE=100
PER_KM_RATE=15
MINIMUM_FARE=50
DELIVERY_BASE_FARE=80

# Настройки безопасности
MAX_REQUESTS_PER_MINUTE=30
MAX_REQUESTS_PER_HOUR=300

# Настройки логирования
LOG_LEVEL=INFO
LOG_FILE=taxi_bot.log

# Настройки кэширования
CACHE_TTL=3600
MAX_CACHE_SIZE=100

# Настройки уведомлений
NOTIFICATION_TIMEOUT=30
DRIVER_SEARCH_TIMEOUT=120
EOF

echo "✅ Файл .env создан"
echo "⚠️  Не забудьте отредактировать .env и добавить токен вашего бота!"

# Создаем скрипт автозапуска
echo "📱 Создание скрипта автозапуска..."
cat > ~/.bashrc << 'EOF'
# Автозапуск бота Рай-Такси
if [ -d ~/raitaxi ]; then
    echo "🚗 Рай-Такси готов к запуску!"
    echo "Для запуска выполните: cd ~/raitaxi && python main.py"
fi
EOF

# Создаем скрипт запуска
cat > ~/raitaxi/start.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/raitaxi
echo "🚗 Запуск бота Рай-Такси..."
python main.py
EOF

chmod +x ~/raitaxi/start.sh

# Создаем скрипт остановки
cat > ~/raitaxi/stop.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "🛑 Остановка бота Рай-Такси..."
pkill -f "python main.py"
echo "✅ Бот остановлен"
EOF

chmod +x ~/raitaxi/stop.sh

# Создаем скрипт перезапуска
cat > ~/raitaxi/restart.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "🔄 Перезапуск бота Рай-Такси..."
cd ~/raitaxi
./stop.sh
sleep 2
./start.sh
EOF

chmod +x ~/raitaxi/restart.sh

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📁 Проект находится в: ~/raitaxi"
echo ""
echo "📋 Доступные команды:"
echo "   cd ~/raitaxi/start.sh  - запуск бота"
echo "   cd ~/raitaxi/stop.sh   - остановка бота"
echo "   cd ~/raitaxi/restart.sh - перезапуск бота"
echo ""
echo "⚠️  ВАЖНО: Отредактируйте файл .env и добавьте токен вашего бота!"
echo "   nano ~/raitaxi/.env"
echo ""
echo "🚀 Для запуска выполните:"
echo "   cd ~/raitaxi && python main.py"
echo ""
echo "📚 Документация: README.md"
