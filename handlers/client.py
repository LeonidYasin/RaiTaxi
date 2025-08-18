"""
Обработчики команд для клиентов Рай-Такси
"""

from aiogram import Router, F, Bot
import io
import asyncio
import time
from aiogram.types import Message, CallbackQuery, Location, ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.operations import UserOperations, OrderOperations
from services.price_calculator import PriceCalculator
from utils.maps import MapService
from utils.rate_limiter import TaxiOrderLimiter, DeliveryOrderLimiter
from config import Config

router = Router()

class TaxiOrderStates(StatesGroup):
    """Состояния для заказа такси"""
    waiting_for_pickup = State()
    waiting_for_destination = State()
    confirming_order = State()
    searching_for_driver = State()

class DeliveryOrderStates(StatesGroup):
    """Состояния для заказа доставки"""
    waiting_for_description = State()
    waiting_for_pickup = State()
    waiting_for_destination = State()
    confirming_order = State()

# Глобальные переменные для доступа к операциям БД
user_ops = None
order_ops = None

def set_operations(user_operations: UserOperations, order_operations: OrderOperations, bot_instance: Bot):
    """Устанавливает операции с БД и экземпляр бота для обработчиков"""
    global user_ops, order_ops, bot
    user_ops = user_operations
    order_ops = order_operations
    bot = bot_instance

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработка команды /start"""
    user = message.from_user
    
    # Проверяем, существует ли пользователь
    existing_user = await user_ops.get_user_by_telegram_id(user.id)
    
    if not existing_user:
        # Создаем нового пользователя
        await user_ops.create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    
    # Проверяем, является ли пользователь водителем
    user_db_id = await user_ops.get_user_id_by_telegram_id(user.id)
    is_driver = False
    if user_db_id:
        from database.operations import DriverOperations
        driver_ops = DriverOperations(user_ops.db)
        driver = await driver_ops.get_driver_by_user_id(user_db_id)
        is_driver = driver is not None
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['taxi'], callback_data="order_taxi")
    builder.button(text=Config.BUTTONS['delivery'], callback_data="order_delivery")
    builder.button(text=Config.BUTTONS['my_orders'], callback_data="my_orders")
    builder.button(text=Config.BUTTONS['profile'], callback_data="profile")
    
    # Показываем кнопку "Стать водителем" только если пользователь еще не водитель
    if not is_driver:
        builder.button(text=Config.BUTTONS['become_driver'], callback_data="become_driver")
    else:
        builder.button(text=Config.BUTTONS['driver_panel'], callback_data="driver_panel")
    
    builder.button(text=Config.BUTTONS['help'], callback_data="help")
    
    builder.adjust(2, 2, 1, 1)
    
    # Выбираем сообщение в зависимости от статуса водителя
    if is_driver:
        welcome_message = Config.MESSAGES['welcome']
    else:
        welcome_message = Config.MESSAGES['welcome_with_driver_invite']
    
    await message.answer(
        welcome_message,
        reply_markup=builder.as_markup()
    )

@router.message(Command("help"))
async def help_command(message: Message):
    """Обработка команды /help"""
    await show_help(message)

@router.message(Command("profile"))
async def profile_command(message: Message):
    """Обработка команды /profile"""
    await show_profile(message)

@router.message(Command("my_orders"))
async def my_orders_command(message: Message):
    """Обработка команды /my_orders"""
    await show_my_orders(message)

@router.message(Command("taxi"))
async def taxi_command(message: Message):
    """Обработка команды /taxi"""
    # Создаем заглушку для state, так как это команда, а не callback
    await message.answer(
        "🚕 Для заказа такси используйте кнопку 'Заказать такси' в главном меню",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("delivery"))
async def delivery_command(message: Message):
    """Обработка команды /delivery"""
    # Создаем заглушку для state, так как это команда, а не callback
    await message.answer(
        "📦 Для заказа доставки используйте кнопку 'Заказать доставку' в главном меню",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("driver"))
async def driver_command(message: Message):
    """Обработка команды /driver"""
    # Создаем заглушку для state, так как это команда, а не callback
    await message.answer(
        "🚗 Для регистрации водителя используйте кнопку 'Стать водителем' в главном меню",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("admin"))
async def admin_command(message: Message):
    """Обработка команды /admin"""
    # Создаем заглушку для state, так как это команда, а не callback
    await message.answer(
        "👑 Для доступа к панели администратора используйте кнопку 'Панель администратора' в главном меню",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("menu"))
async def menu_command(message: Message):
    """Обработка команды /menu - возврат в главное меню"""
    await start_command(message)

@router.message(Command("info"))
async def info_command(message: Message):
    """Обработка команды /info - информация о боте"""
    info_text = "🚗 Рай-Такси - Ваш соседский водитель!\n\n"
    info_text += "✨ Особенности:\n"
    info_text += "• 🚕 Быстрое такси по району\n"
    info_text += "• 📦 Доставка продуктов и лекарств\n"
    info_text += "• 🏠 Работаем в вашем районе\n"
    info_text += "• 💰 Прозрачные цены\n"
    info_text += "• ⭐ Надежные водители\n\n"
    info_text += "📱 Команды:\n"
    info_text += "• /start - Главное меню\n"
    info_text += "• /taxi - Заказать такси\n"
    info_text += "• /delivery - Заказать доставку\n"
    info_text += "• /driver - Стать водителем\n"
    info_text += "• /help - Справка\n"
    info_text += "• /menu - Главное меню\n\n"
    info_text += "💡 Для заказа используйте кнопки в главном меню!"
    
    await message.answer(info_text, reply_markup=get_main_menu_keyboard())

@router.message(Command("about"))
async def about_command(message: Message):
    """Обработка команды /about - о проекте"""
    about_text = "🚗 О проекте Рай-Такси\n\n"
    about_text += "🎯 Миссия:\n"
    about_text += "Создать удобный сервис такси и доставки для малых городов России\n\n"
    about_text += "💡 Философия:\n"
    about_text += "• 🏠 Соседский подход\n"
    about_text += "• 🚗 Комфорт важнее скорости\n"
    about_text += "• 💰 Справедливые цены\n"
    about_text += "• ⭐ Надежность и качество\n\n"
    about_text += "🌍 Территория:\n"
    about_text += "Работаем в малых городах и поселках России\n\n"
    about_text += "📱 Технологии:\n"
    about_text += "• Telegram Bot API\n"
    about_text += "• Python + SQLite\n"
    about_text += "• Локальный сервер\n"
    about_text += "• Без облачных зависимостей\n\n"
    about_text += "🔄 Версия: 1.0.0\n"
    about_text += "📅 2025 год"
    
    await message.answer(about_text, reply_markup=get_main_menu_keyboard())

@router.message(Command("support"))
async def support_command(message: Message):
    """Обработка команды /support - поддержка"""
    support_text = "🆘 Поддержка Рай-Такси\n\n"
    support_text += "📞 Способы связи:\n"
    support_text += "• 💬 Telegram: @admin_username\n"
    support_text += "• 📧 Email: support@raitaxi.ru\n"
    support_text += "• 📱 Телефон: +7 (XXX) XXX-XX-XX\n\n"
    support_text += "❓ Частые вопросы:\n"
    support_text += "• Как заказать такси? - /help\n"
    support_text += "• Как стать водителем? - /driver\n"
    support_text += "• Где работает сервис? - /info\n\n"
    support_text += "🚨 Экстренная помощь:\n"
    support_text += "• Проблемы с заказом\n"
    support_text += "• Жалобы на водителя\n"
    support_text += "• Технические сбои\n\n"
    support_text += "⏰ Время работы:\n"
    support_text += "• Пн-Вс: 24/7\n"
    support_text += "• Ответ в течение 1 часа"
    
    await message.answer(support_text, reply_markup=get_main_menu_keyboard())

@router.message(Command("status"))
async def status_command(message: Message):
    """Обработка команды /status - статус системы"""
    try:
        # Получаем базовую статистику
        total_users = await user_ops.get_total_users() if user_ops else 0
        total_drivers = 0
        if user_ops:
            from database.operations import DriverOperations
            driver_ops = DriverOperations(user_ops.db)
            total_drivers = await driver_ops.get_total_drivers()
        
        status_text = "📊 Статус системы Рай-Такси\n\n"
        status_text += "🟢 Система работает\n"
        status_text += f"👥 Пользователей: {total_users}\n"
        status_text += f"🚗 Водителей: {total_drivers}\n"
        status_text += "🕐 Время: " + get_current_time() + "\n\n"
        status_text += "💻 Сервер: Android (Termux)\n"
        status_text += "🗄️ База данных: SQLite\n"
        status_text += "🌐 Интернет: Активно\n"
        status_text += "🔒 Безопасность: Включена\n\n"
        status_text += "✅ Все сервисы работают нормально"
        
        await message.answer(status_text, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка получения статуса: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )

# Вспомогательные функции
def get_current_time():
    """Возвращает текущее время в читаемом формате"""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%d.%m.%Y %H:%M:%S")

async def show_help(message: Message):
    """Показать справку"""
    help_text = "❓ Справка по использованию бота\n\n"
    help_text += "🚕 Заказ такси:\n"
    help_text += "1. Нажмите 'Заказать такси'\n"
    help_text += "2. Отправьте ваше местоположение\n"
    help_text += "3. Отправьте место назначения\n"
    help_text += "4. Подтвердите заказ\n\n"
    help_text += "📦 Заказ доставки:\n"
    help_text += "1. Нажмите 'Заказать доставку'\n"
    help_text += "2. Опишите что нужно доставить\n"
    help_text += "3. Укажите адреса\n"
    help_text += "4. Подтвердите заказ\n\n"
    help_text += "📋 Мои заказы - просмотр истории заказов\n"
    help_text += "👤 Профиль - информация о вас\n\n"
    help_text += "💡 Для отправки местоположения используйте кнопку 📍"
    
    await message.answer(help_text, reply_markup=get_main_menu_keyboard())

async def show_profile(message: Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    user = await user_ops.get_user_by_telegram_id(user_id) if user_ops else None
    
    if not user:
        await message.answer(
            "❌ Пользователь не найден",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    profile_text = f"👤 Профиль пользователя\n\n"
    profile_text += f"🆔 ID: {user.telegram_id}\n"
    profile_text += f"👤 Имя: {user.first_name}\n"
    if user.last_name:
        profile_text += f"📝 Фамилия: {user.last_name}\n"
    if user.username:
        profile_text += f"🔗 Username: @{user.username}\n"
    profile_text += f"⭐ Рейтинг: {user.rating:.1f}\n"
    profile_text += f"📦 Всего заказов: {user.total_orders}\n"
    profile_text += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}"
    
    await message.answer(profile_text, reply_markup=get_main_menu_keyboard())

async def show_my_orders(message: Message):
    """Показать заказы пользователя"""
    user_id = message.from_user.id
    orders = await order_ops.get_user_orders(user_id, limit=10) if order_ops else []
    
    if not orders:
        await message.answer(
            "📋 У вас пока нет заказов.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Формируем список заказов
    orders_text = "📋 Ваши последние заказы:\n\n"
    for order in orders:
        status_emoji = {
            'new': '🆕',
            'searching_driver': '🔍',
            'driver_assigned': '🚗',
            'in_progress': '🚀',
            'completed': '✅',
            'cancelled': '❌'
        }.get(order.status, '❓')
        
        orders_text += f"{status_emoji} Заказ #{order.id} - {order.status}\n"
        if order.price:
            from services.price_calculator import PriceCalculator
            orders_text += f"💰 Стоимость: {PriceCalculator.format_price(order.price)}\n"
        orders_text += "\n"
    
    await message.answer(orders_text, reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data == "order_taxi")
async def order_taxi_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки заказа такси"""
    user_id = callback.from_user.id
    
    # Проверяем лимиты
    limiter = TaxiOrderLimiter()
    allowed, message = limiter.is_allowed(user_id)
    if not allowed:
        await callback.answer(message, show_alert=True)
        return
    
    await state.set_state(TaxiOrderStates.waiting_for_pickup)
    
    await callback.message.answer(
        Config.MESSAGES['taxi_order'],
        reply_markup=get_location_keyboard()
    )
    await callback.message.answer(
        "Или отмените заказ:",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(F.data == "order_delivery")
async def order_delivery_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки заказа доставки"""
    user_id = callback.from_user.id
    
    # Проверяем лимиты
    limiter = DeliveryOrderLimiter()
    allowed, message = limiter.is_allowed(user_id)
    if not allowed:
        await callback.answer(message, show_alert=True)
        return
    
    await state.set_state(DeliveryOrderStates.waiting_for_description)
    
    await callback.message.edit_text(
        Config.MESSAGES['delivery_order'],
        reply_markup=get_cancel_keyboard()
    )

@router.message(TaxiOrderStates.waiting_for_pickup, F.location)
async def handle_pickup_location(message: Message, state: FSMContext):
    """Обработка местоположения отправления"""
    location = message.location
    
    map_service = MapService()
    pickup_address = map_service.reverse_geocode_coords(location.latitude, location.longitude)
    
    await state.update_data(
        pickup_lat=location.latitude,
        pickup_lon=location.longitude,
        pickup_address=pickup_address if pickup_address else "Неизвестный адрес"
    )
    
    await state.set_state(TaxiOrderStates.waiting_for_destination)
    
    await message.answer(
        Config.MESSAGES['destination_needed'],
        reply_markup=get_cancel_keyboard()
    )

@router.message(TaxiOrderStates.waiting_for_pickup, F.text)
async def handle_pickup_address(message: Message, state: FSMContext):
    """Обработка адреса отправления (с геокодированием)"""
    map_service = MapService()
    geocoded_location = map_service.geocode_address(message.text)

    if geocoded_location:
        pickup_lat, pickup_lon = geocoded_location
        await state.update_data(
            pickup_lat=pickup_lat,
            pickup_lon=pickup_lon,
            pickup_address=message.text # Store the text address as well
        )
        await state.set_state(TaxiOrderStates.waiting_for_destination)
        
        map_service = MapService()
        map_data = map_service.create_simple_map(pickup_lat, pickup_lon)
        if map_data:
            await message.answer_photo(
                InputFile(io.BytesIO(map_data)),
                caption=Config.MESSAGES['destination_needed'],
                reply_markup=get_cancel_keyboard()
            )
        else:
            await message.answer(
                Config.MESSAGES['destination_needed'],
                reply_markup=get_cancel_keyboard()
            )
    else:
        print(f"DEBUG: Geocoding failed for pickup address: '{message.text}'") # Add debug print
        await state.update_data(pickup_address="Неизвестно") # Ensure pickup_address is always set
        await message.answer(
            "❌ Не удалось определить местоположение по адресу отправления. Пожалуйста, попробуйте еще раз, введя более точный адрес, или отправьте ваше местоположение с помощью кнопки.",
            reply_markup=get_location_keyboard()
        )
        await message.answer(
            "Или отмените заказ:",
            reply_markup=get_cancel_keyboard()
        )

@router.message(TaxiOrderStates.waiting_for_destination, F.location)
async def handle_destination_location(message: Message, state: FSMContext):
    """Обработка местоположения назначения"""
    location = message.location
    
    # Получаем данные о точке отправления
    data = await state.get_data()
    pickup_lat = data.get('pickup_lat')
    pickup_lon = data.get('pickup_lon')
    
    if not pickup_lat or not pickup_lon:
        await message.answer("❌ Ошибка: не найдена точка отправления. Попробуйте заново.")
        await state.clear()
        return
    
    map_service = MapService()
    destination_address = map_service.reverse_geocode_coords(location.latitude, location.longitude)
    
    # Рассчитываем расстояние и цену
    distance = PriceCalculator.calculate_distance(
        pickup_lat, pickup_lon,
        location.latitude, location.longitude
    )
    
    price = PriceCalculator.calculate_taxi_price(distance)
    
    # Сохраняем данные о назначении
    await state.update_data(
        destination_lat=location.latitude,
        destination_lon=location.longitude,
        destination_address=destination_address if destination_address else "Неизвестный адрес",
        distance=distance,
        price=price
    )
    
    await state.set_state(TaxiOrderStates.confirming_order)
    
    # Показываем подтверждение заказа
    map_service = MapService()
    map_data = map_service.create_simple_map(
        data['pickup_lat'], data['pickup_lon'],
        location.latitude, location.longitude # Use location.latitude, location.longitude here
    )

    confirmation_text = (
        f"🚕 Подтвердите заказ такси:\n\n"
        f"📍 Откуда: {data.get('pickup_address', 'Указанное местоположение')}\n"
        f"🎯 Куда: {destination_address if destination_address else 'Указанное местоположение'}\n"
        f"📏 Расстояние: {PriceCalculator.format_distance(distance)}\n"
        f"💰 Стоимость: {PriceCalculator.format_price(price)}"
    )

    if map_data:
        await message.answer_photo(
            InputFile(io.BytesIO(map_data)),
            caption=confirmation_text,
            reply_markup=get_confirm_keyboard()
        )
    else:
        await message.answer(
            confirmation_text,
            reply_markup=get_confirm_keyboard()
        )

@router.message(TaxiOrderStates.waiting_for_destination, F.text)
async def handle_destination_address(message: Message, state: FSMContext):
    """Обработка адреса назначения (с геокодированием)"""
    destination_address = message.text
    
    data = await state.get_data()
    pickup_lat = data.get('pickup_lat')
    pickup_lon = data.get('pickup_lon')
    
    if not pickup_lat or not pickup_lon:
        await message.answer("❌ Ошибка: не найдена точка отправления. Попробуйте заново.")
        await state.clear()
        return
    
    map_service = MapService()
    geocoded_location = map_service.geocode_address(destination_address)

    if geocoded_location:
        destination_lat, destination_lon = geocoded_location
    else:
        print(f"DEBUG: Geocoding failed for destination address: '{destination_address}'") # Add debug print
        await message.answer(
            "❌ Не удалось определить местоположение по адресу назначения. Пожалуйста, попробуйте еще раз, введя более точный адрес.",
            reply_markup=get_cancel_keyboard()
        )
        return # Stop processing if geocoding fails
    
    price, distance = PriceCalculator.calculate_taxi_price(
        pickup_lat, pickup_lon,
        destination_lat, destination_lon
    )
    
    await state.update_data(
        destination_address=destination_address,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        distance=distance,
        price=price
    )
    
    await state.set_state(TaxiOrderStates.confirming_order)
    
    map_service = MapService()
    map_data = map_service.create_simple_map(
        data['pickup_lat'], data['pickup_lon'],
        destination_lat, destination_lon
    )

    confirmation_text = (
        f"🚕 Подтвердите заказ такси:\n\n"
        f"📍 Откуда: {data.get('pickup_address', 'Указанное местоположение')}\n"
        f"🎯 Куда: {destination_address}\n"
        f"📏 Расстояние: {PriceCalculator.format_distance(distance)}\n"
        f"💰 Стоимость: {PriceCalculator.format_price(price)}"
    )

    if map_data:
        await message.answer_photo(
            InputFile(io.BytesIO(map_data)),
            caption=confirmation_text,
            reply_markup=get_confirm_keyboard()
        )
    else:
        await message.answer(
            confirmation_text,
            reply_markup=get_confirm_keyboard()
        )

@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Подтверждение заказа"""
    data = await state.get_data()
    
    # Создаем заказ в базе данных
    order = await order_ops.create_order(
        client_id=callback.from_user.id,
        order_type='taxi',
        pickup_lat=data['pickup_lat'],
        pickup_lon=data['pickup_lon'],
        pickup_address=data.get('pickup_address'), # Add pickup_address
        destination_lat=data.get('destination_lat'),
        destination_lon=data.get('destination_lon'),
        destination_address=data.get('destination_address'), # Add destination_address
        price=data['price'],
        distance=data['distance']
    )
    
    if order:
        await callback.message.edit_text(
            Config.MESSAGES['order_created'],
            reply_markup=get_main_menu_keyboard()
        )
        
        # Запускаем процесс поиска и назначения водителя
        await state.set_state(TaxiOrderStates.searching_for_driver)
        await find_and_assign_driver(callback.message, order.id, state)
        
    else:
        await callback.message.edit_text(
            "❌ Ошибка создания заказа. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заказа"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Заказ отменен.",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "my_orders")
async def show_my_orders(callback: CallbackQuery, state: FSMContext):
    """Показать заказы пользователя"""
    # Очищаем состояние FSM перед показом заказов
    if state:
        await state.clear()
    user_id = callback.from_user.id
    orders = await order_ops.get_user_orders(user_id, limit=10)
    
    if not orders:
        await callback.message.edit_text(
            "📋 У вас пока нет заказов.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Формируем список заказов
    orders_text = "📋 Ваши последние заказы:\n\n"
    for order in orders:
        status_emoji = {
            'new': '🆕',
            'searching_driver': '🔍',
            'driver_assigned': '🚗',
            'in_progress': '🚀',
            'completed': '✅',
            'cancelled': '❌'
        }.get(order.status, '❓')
        
        orders_text += f"{status_emoji} Заказ #{order.id} - {order.status}\n"
        if order.price:
            from services.price_calculator import PriceCalculator
            orders_text += f"💰 Стоимость: {PriceCalculator.format_price(order.price)}\n"
        orders_text += "\n"
    
    await callback.message.edit_text(
        orders_text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    """Показать профиль пользователя"""
    # Очищаем состояние FSM перед показом профиля
    if state:
        await state.clear()
    user_id = callback.from_user.id
    user = await user_ops.get_user_by_telegram_id(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    profile_text = f"👤 Профиль пользователя\n\n"
    profile_text += f"🆔 ID: {user.telegram_id}\n"
    profile_text += f"👤 Имя: {user.first_name}\n"
    if user.last_name:
        profile_text += f"📝 Фамилия: {user.last_name}\n"
    if user.username:
        profile_text += f"🔗 Username: @{user.username}\n"
    profile_text += f"⭐ Рейтинг: {user.rating:.1f}\n"
    profile_text += f"📦 Всего заказов: {user.total_orders}\n"
    profile_text += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}"
    
    await callback.message.edit_text(
        profile_text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery, state: FSMContext):
    """Показать справку"""
    # Очищаем состояние FSM перед показом справки
    if state:
        await state.clear()
    help_text = "❓ Справка по использованию бота\n\n"
    help_text += "🚕 Заказ такси:\n"
    help_text += "1. Нажмите 'Заказать такси'\n"
    help_text += "2. Отправьте ваше местоположение\n"
    help_text += "3. Отправьте место назначения\n"
    help_text += "4. Подтвердите заказ\n\n"
    help_text += "📦 Заказ доставки:\n"
    help_text += "1. Нажмите 'Заказать доставку'\n"
    help_text += "2. Опишите что нужно доставить\n"
    help_text += "3. Укажите адреса\n"
    help_text += "4. Подтвердите заказ\n\n"
    help_text += "📋 Мои заказы - просмотр истории заказов\n"
    help_text += "👤 Профиль - информация о вас\n\n"
    help_text += "💡 Для отправки местоположения используйте кнопку 📍"
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    # Очищаем состояние FSM перед возвратом в главное меню
    if state:
        await state.clear()
    await start_command(callback.message)

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    # Очищаем состояние FSM перед возвратом в главное меню
    if state:
        await state.clear()
    await start_command(callback.message)
    await callback.answer()

@router.callback_query(F.data == "become_driver")
async def become_driver_callback(callback: CallbackQuery, state: FSMContext):
    """Приглашение стать водителем"""
    # Очищаем состояние FSM перед показом приглашения
    if state:
        await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать регистрацию", callback_data="start_driver_registration")
    builder.button(text="📋 Узнать больше", callback_data="driver_info")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1, 1, 1)
    
    await callback.message.edit_text(
        Config.MESSAGES['driver_invite'],
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "driver_info")
async def driver_info_callback(callback: CallbackQuery, state: FSMContext):
    """Подробная информация о работе водителем"""
    # Очищаем состояние FSM перед показом информации
    if state:
        await state.clear()
    info_text = "🚗 Подробная информация о работе водителем\n\n"
    info_text += "📋 Требования:\n"
    info_text += "• Водительское удостоверение категории B\n"
    info_text += "• Собственный автомобиль в исправном состоянии\n"
    info_text += "• Страховка ОСАГО\n\n"
    info_text += "💰 Доходы:\n"
    info_text += "• 70-80% от стоимости заказа\n"
    info_text += "• Без скрытых комиссий\n"
    info_text += "• Выплаты каждый день\n\n"
    info_text += "⏰ График:\n"
    info_text += "• Работайте когда хотите\n"
    info_text += "• Включайте/выключайте приложение\n"
    info_text += "• Никаких обязательств\n\n"
    info_text += "🎯 Территория:\n"
    info_text += "• Работа в своем районе\n"
    info_text += "• Знакомые маршруты\n"
    info_text += "• Минимум времени в дороге"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать регистрацию", callback_data="start_driver_registration")
    builder.button(text="⬅️ Назад", callback_data="become_driver")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1, 1, 1)
    
    await callback.message.edit_text(
        info_text,
        reply_markup=builder.as_markup()
    )




@router.callback_query(F.data == "back_to_order")
async def back_to_order_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат к заказу"""
    await callback.answer("⬅️ Возвращаемся к заказу")
    # Здесь можно добавить логику возврата к предыдущему шагу заказа
    await callback.message.edit_text(
        "⬅️ Возвращаемся к заказу...",
        reply_markup=get_cancel_keyboard()
    )

async def find_and_assign_driver(message: Message, order_id: int, state: FSMContext):
    """
    Находит доступных водителей и отправляет им запрос на принятие заказа.
    """
    await message.answer("🔍 Ищем ближайшего водителя...")
    
    order = await order_ops.get_order_by_id(order_id)
    if not order:
        await message.answer("❌ Заказ не найден. Попробуйте создать новый.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    # Обновляем статус заказа на "searching_driver"
    await order_ops.update_order_status(order_id, Config.ORDER_STATUSES['searching_driver'])

    # Получаем доступных водителей
    from database.operations import DriverOperations
    driver_ops = DriverOperations(user_ops.db) # Assuming user_ops.db is accessible
    available_drivers = await driver_ops.get_available_drivers()

    if not available_drivers:
        await message.answer("😔 К сожалению, сейчас нет доступных водителей. Попробуйте позже.", reply_markup=get_main_menu_keyboard())
        await order_ops.update_order_status(order_id, Config.ORDER_STATUSES['cancelled'])
        await state.clear()
        return

    # Сортируем водителей по расстоянию до точки отправления (простая эвристика)
    # В реальном приложении здесь была бы более сложная логика с учетом трафика и т.д.
    def sort_by_distance(driver):
        if driver.current_location_lat and driver.current_location_lon:
            return PriceCalculator.calculate_distance(
                order.pickup_lat, order.pickup_lon,
                driver.current_location_lat, driver.current_location_lon
            )
        return float('inf') # Отправляем водителей без координат в конец списка

    available_drivers.sort(key=sort_by_distance)

    # Отправляем запрос водителям по очереди
    for driver in available_drivers:
        driver_user = await user_ops.get_user_by_id(driver.user_id) # Assuming get_user_by_id exists
        if not driver_user or not driver_user.telegram_id:
            continue

        offer_text = (
            f"🔔 Новый заказ #{order.id}!\n\n"
            f"📍 Откуда: {order.pickup_address or f'{order.pickup_lat:.4f}, {order.pickup_lon:.4f}'}\n"
            f"🎯 Куда: {order.destination_address or f'{order.destination_lat:.4f}, {order.destination_lon:.4f}'}\n"
            f"📏 Расстояние: {PriceCalculator.format_distance(order.distance)}\n"
            f"💰 Стоимость: {PriceCalculator.format_price(order.price)}\n\n"
            "Принять заказ?"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Принять", callback_data=f"driver_accept_order_{order.id}")
        builder.button(text="❌ Отказаться", callback_data=f"driver_reject_order_{order.id}")
        
        try:
            await bot.send_message(
                chat_id=driver_user.telegram_id,
                text=offer_text,
                reply_markup=builder.as_markup()
            )
            await message.answer(f"➡️ Запрос отправлен водителю {driver_user.first_name} ({driver.car_model}). Ожидаем ответа...")
            
            # Ждем ответа водителя (например, 30 секунд)
            # В реальном приложении здесь будет более сложная логика с таймаутами и очередями
            await asyncio.sleep(Config.NOTIFICATION_TIMEOUT)
            
            # Проверяем статус заказа после ожидания
            updated_order = await order_ops.get_order_by_id(order_id)
            if updated_order.status == Config.ORDER_STATUSES['driver_assigned']:
                await message.answer(f"✅ Водитель {driver_user.first_name} принял ваш заказ!")
                await state.clear()
                return # Заказ принят, выходим
            elif updated_order.status == Config.ORDER_STATUSES['cancelled']:
                await message.answer("❌ Заказ был отменен водителем или истек срок ожидания.", reply_markup=get_main_menu_keyboard())
                await state.clear()
                return
            else:
                await message.answer(f"Водитель {driver_user.first_name} не ответил или отказался. Ищем дальше...")

        except Exception as e:
            print(f"Ошибка отправки запроса водителю {driver_user.telegram_id}: {e}")
            await message.answer(f"❌ Не удалось связаться с водителем {driver_user.first_name}. Ищем другого...")
            continue # Пробуем следующего водителя

    # Если ни один водитель не принял заказ
    await message.answer("😔 К сожалению, ни один водитель не смог принять ваш заказ. Попробуйте позже.", reply_markup=get_main_menu_keyboard())
    await order_ops.update_order_status(order_id, Config.ORDER_STATUSES['cancelled'])
    await state.clear()

# Вспомогательные функции для клавиатур
def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel_order")
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()

def get_location_keyboard():
    """Клавиатура для отправки местоположения"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить текущее местоположение", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_confirm_keyboard():
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['confirm'], callback_data="confirm_order")
    builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel_order")
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()

def get_back_keyboard():
    """Клавиатура с кнопкой назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['back'], callback_data="back_to_order")
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()

def get_main_menu_keyboard():
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()
