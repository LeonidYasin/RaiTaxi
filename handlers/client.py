"""
Обработчики команд для клиентов Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Location
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

class DeliveryOrderStates(StatesGroup):
    """Состояния для заказа доставки"""
    waiting_for_description = State()
    waiting_for_pickup = State()
    waiting_for_destination = State()
    confirming_order = State()

# Глобальные переменные для доступа к операциям БД
user_ops = None
order_ops = None

def set_operations(user_operations: UserOperations, order_operations: OrderOperations):
    """Устанавливает операции с БД для обработчиков"""
    global user_ops, order_ops
    user_ops = user_operations
    order_ops = order_operations

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
    await order_taxi_callback(message, None)

@router.message(Command("delivery"))
async def delivery_command(message: Message):
    """Обработка команды /delivery"""
    await order_delivery_callback(message, None)

@router.message(Command("driver"))
async def driver_command(message: Message):
    """Обработка команды /driver"""
    from handlers.driver import driver_command as driver_cmd
    await driver_cmd(message)

@router.message(Command("admin"))
async def admin_command(message: Message):
    """Обработка команды /admin"""
    from handlers.admin import admin_command as admin_cmd
    await admin_cmd(message)

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
    
    await callback.message.edit_text(
        Config.MESSAGES['taxi_order'],
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
    
    await state.update_data(
        pickup_lat=location.latitude,
        pickup_lon=location.longitude
    )
    
    await state.set_state(TaxiOrderStates.waiting_for_destination)
    
    await message.answer(
        Config.MESSAGES['destination_needed'],
        reply_markup=get_cancel_keyboard()
    )

@router.message(TaxiOrderStates.waiting_for_pickup, F.text)
async def handle_pickup_address(message: Message, state: FSMContext):
    """Обработка адреса отправления (пока упрощенно)"""
    # В реальном приложении здесь должен быть геокодер
    await message.answer(
        "📍 Пожалуйста, отправьте ваше местоположение, нажав на кнопку 📍",
        reply_markup=get_location_keyboard()
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
        distance=distance,
        price=price
    )
    
    await state.set_state(TaxiOrderStates.confirming_order)
    
    # Показываем подтверждение заказа
    await message.answer(
        f"🚕 Подтвердите заказ такси:\n\n"
        f"📍 Откуда: {data.get('pickup_address', 'Указанное местоположение')}\n"
        f"🎯 Куда: {message.text or 'Указанное местоположение'}\n"
        f"📏 Расстояние: {PriceCalculator.format_distance(distance)}\n"
        f"💰 Стоимость: {PriceCalculator.format_price(price)}",
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
        destination_lat=data.get('destination_lat'),
        destination_lon=data.get('destination_lon'),
        price=data['price'],
        distance=data['distance']
    )
    
    if order:
        await callback.message.edit_text(
            Config.MESSAGES['order_created'],
            reply_markup=get_main_menu_keyboard()
        )
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
async def show_my_orders(callback: CallbackQuery):
    """Показать заказы пользователя"""
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
            orders_text += f"💰 Стоимость: {PriceCalculator.format_price(order.price)}\n"
        orders_text += "\n"
    
    await callback.message.edit_text(
        orders_text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
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
async def show_help(callback: CallbackQuery):
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
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await start_command(callback.message)

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await start_command(callback.message)
    await callback.answer()

@router.callback_query(F.data == "become_driver")
async def become_driver_callback(callback: CallbackQuery):
    """Приглашение стать водителем"""
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
async def driver_info_callback(callback: CallbackQuery):
    """Подробная информация о работе водителем"""
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

@router.callback_query(F.data == "driver_panel")
async def driver_panel_callback(callback: CallbackQuery):
    """Переход к панели водителя"""
    from handlers.driver import driver_command
    await driver_command(callback.message)
    await callback.answer()

@router.callback_query(F.data == "start_driver_registration")
async def start_driver_registration_callback(callback: CallbackQuery):
    """Переход к регистрации водителя"""
    from handlers.driver import start_driver_registration
    await start_driver_registration(callback, None)  # state будет установлен в driver.py
    await callback.answer()

@router.callback_query(F.data == "send_location")
async def send_location_callback(callback: CallbackQuery):
    """Обработка нажатия кнопки отправки местоположения"""
    await callback.answer("📍 Пожалуйста, отправьте ваше местоположение, используя кнопку 📍 в Telegram")
    await callback.message.edit_text(
        "📍 Пожалуйста, отправьте ваше местоположение, используя кнопку 📍 в Telegram",
        reply_markup=get_cancel_keyboard()
    )

@router.callback_query(F.data == "back_to_order")
async def back_to_order_callback(callback: CallbackQuery):
    """Возврат к заказу"""
    await callback.answer("⬅️ Возвращаемся к заказу")
    # Здесь можно добавить логику возврата к предыдущему шагу заказа
    await callback.message.edit_text(
        "⬅️ Возвращаемся к заказу...",
        reply_markup=get_cancel_keyboard()
    )

# Вспомогательные функции для клавиатур
def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel_order")
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()

def get_location_keyboard():
    """Клавиатура для отправки местоположения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Отправить местоположение", callback_data="send_location")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    builder.button(text=Config.BUTTONS['main_menu'], callback_data="main_menu")
    return builder.as_markup()

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
