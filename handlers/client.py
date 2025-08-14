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
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['taxi'], callback_data="order_taxi")
    builder.button(text=Config.BUTTONS['delivery'], callback_data="order_delivery")
    builder.button(text=Config.BUTTONS['my_orders'], callback_data="my_orders")
    builder.button(text=Config.BUTTONS['profile'], callback_data="profile")
    builder.button(text=Config.BUTTONS['help'], callback_data="help")
    
    builder.adjust(2, 2, 1)
    
    await message.answer(
        Config.MESSAGES['welcome'],
        reply_markup=builder.as_markup()
    )

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

# Вспомогательные функции для клавиатур
def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    return builder.as_markup()

def get_location_keyboard():
    """Клавиатура для отправки местоположения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Отправить местоположение", callback_data="send_location")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    return builder.as_markup()

def get_confirm_keyboard():
    """Клавиатура подтверждения заказа"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отмена", callback_data="cancel_order")
    return builder.as_markup()

def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text=Config.BUTTONS['taxi'], callback_data="order_taxi")
    builder.button(text=Config.BUTTONS['delivery'], callback_data="order_delivery")
    builder.button(text=Config.BUTTONS['my_orders'], callback_data="my_orders")
    builder.button(text=Config.BUTTONS['profile'], callback_data="profile")
    builder.button(text=Config.BUTTONS['help'], callback_data="help")
    builder.adjust(2, 2, 1)
    return builder.as_markup()
