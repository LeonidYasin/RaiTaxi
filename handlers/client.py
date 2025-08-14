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

class ClientHandlers:
    """Обработчики для клиентов"""
    
    def __init__(self, user_ops: UserOperations, order_ops: OrderOperations):
        self.user_ops = user_ops
        self.order_ops = order_ops
        self.map_service = MapService()
        self.taxi_limiter = TaxiOrderLimiter()
        self.delivery_limiter = DeliveryOrderLimiter()
    
    @router.message(Command("start"))
    async def start_command(self, message: Message):
        """Обработка команды /start"""
        user = message.from_user
        
        # Проверяем, существует ли пользователь
        existing_user = await self.user_ops.get_user_by_telegram_id(user.id)
        
        if not existing_user:
            # Создаем нового пользователя
            await self.user_ops.create_user(
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
    async def order_taxi_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка нажатия кнопки заказа такси"""
        user_id = callback.from_user.id
        
        # Проверяем лимиты
        allowed, message = self.taxi_limiter.is_allowed(user_id)
        if not allowed:
            await callback.answer(message, show_alert=True)
            return
        
        await state.set_state(TaxiOrderStates.waiting_for_pickup)
        
        await callback.message.edit_text(
            Config.MESSAGES['taxi_order'],
            reply_markup=self._get_cancel_keyboard()
        )
    
    @router.callback_query(F.data == "order_delivery")
    async def order_delivery_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка нажатия кнопки заказа доставки"""
        user_id = callback.from_user.id
        
        # Проверяем лимиты
        allowed, message = self.delivery_limiter.is_allowed(user_id)
        if not allowed:
            await callback.answer(message, show_alert=True)
            return
        
        await state.set_state(DeliveryOrderStates.waiting_for_description)
        
        await callback.message.edit_text(
            Config.MESSAGES['delivery_order'],
            reply_markup=self._get_cancel_keyboard()
        )
    
    @router.message(TaxiOrderStates.waiting_for_pickup, F.location)
    async def handle_pickup_location(self, message: Message, state: FSMContext):
        """Обработка местоположения отправления"""
        location = message.location
        
        await state.update_data(
            pickup_lat=location.latitude,
            pickup_lon=location.longitude
        )
        
        await state.set_state(TaxiOrderStates.waiting_for_destination)
        
        await message.answer(
            Config.MESSAGES['destination_needed'],
            reply_markup=self._get_cancel_keyboard()
        )
    
    @router.message(TaxiOrderStates.waiting_for_pickup, F.text)
    async def handle_pickup_address(self, message: Message, state: FSMContext):
        """Обработка адреса отправления (пока упрощенно)"""
        # В реальном приложении здесь должен быть геокодер
        await message.answer(
            "📍 Пожалуйста, отправьте ваше местоположение, нажав на кнопку 📍",
            reply_markup=self._get_location_keyboard()
        )
    
    @router.message(TaxiOrderStates.waiting_for_destination, F.location)
    async def handle_destination_location(self, message: Message, state: FSMContext):
        """Обработка местоположения назначения"""
        location = message.location
        
        data = await state.get_data()
        pickup_lat = data['pickup_lat']
        pickup_lon = data['pickup_lon']
        
        # Рассчитываем стоимость
        price, distance = PriceCalculator.calculate_taxi_price(
            pickup_lat, pickup_lon, location.latitude, location.longitude
        )
        
        await state.update_data(
            destination_lat=location.latitude,
            destination_lon=location.longitude,
            price=price,
            distance=distance
        )
        
        await state.set_state(TaxiOrderStates.confirming_order)
        
        # Создаем карту
        map_data = self.map_service.create_simple_map(
            pickup_lat, pickup_lon, location.latitude, location.longitude
        )
        
        if map_data:
            await message.answer_photo(
                map_data,
                caption=self._format_order_confirmation(data, price, distance),
                reply_markup=self._get_confirm_order_keyboard()
            )
        else:
            await message.answer(
                self._format_order_confirmation(data, price, distance),
                reply_markup=self._get_confirm_order_keyboard()
            )
    
    @router.callback_query(F.data == "confirm_order")
    async def confirm_order_callback(self, callback: CallbackQuery, state: FSMContext):
        """Подтверждение заказа"""
        data = await state.get_data()
        user_id = callback.from_user.id
        
        try:
            # Создаем заказ в базе данных
            order = await self.order_ops.create_order(
                client_id=user_id,
                order_type='taxi',
                pickup_lat=data['pickup_lat'],
                pickup_lon=data['pickup_lon'],
                pickup_address="Указанное местоположение",
                destination_lat=data['destination_lat'],
                destination_lon=data['destination_lon'],
                destination_address="Указанное местоположение",
                price=data['price'],
                distance=data['distance']
            )
            
            # Обновляем статус заказа
            await self.order_ops.update_order_status(order.id, 'searching_driver')
            
            await callback.message.edit_text(
                f"✅ Заказ #{order.id} создан!\n\n"
                f"🚗 Ищем водителя...\n"
                f"💰 Стоимость: {PriceCalculator.format_price(data['price'])}\n"
                f"📏 Расстояние: {PriceCalculator.format_distance(data['distance'])}"
            )
            
            # Сбрасываем состояние
            await state.clear()
            
        except Exception as e:
            await callback.message.edit_text(
                "❌ Ошибка создания заказа. Попробуйте позже."
            )
            await state.clear()
    
    @router.callback_query(F.data == "cancel")
    async def cancel_callback(self, callback: CallbackQuery, state: FSMContext):
        """Отмена заказа"""
        await state.clear()
        
        builder = InlineKeyboardBuilder()
        builder.button(text=Config.BUTTONS['taxi'], callback_data="order_taxi")
        builder.button(text=Config.BUTTONS['delivery'], callback_data="order_delivery")
        builder.button(text=Config.BUTTONS['my_orders'], callback_data="my_orders")
        builder.button(text=Config.BUTTONS['profile'], callback_data="profile")
        builder.button(text=Config.BUTTONS['help'], callback_data="help")
        
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            "❌ Заказ отменен. Выберите действие:",
            reply_markup=builder.as_markup()
        )
    
    @router.callback_query(F.data == "my_orders")
    async def my_orders_callback(self, callback: CallbackQuery):
        """Показать заказы пользователя"""
        user_id = callback.from_user.id
        
        try:
            orders = await self.order_ops.get_user_orders(user_id, limit=5)
            
            if not orders:
                await callback.answer("У вас пока нет заказов", show_alert=True)
                return
            
            text = "📋 Ваши последние заказы:\n\n"
            for order in orders:
                status_emoji = {
                    'new': '🆕',
                    'searching_driver': '🔍',
                    'driver_assigned': '🚗',
                    'in_progress': '🚀',
                    'completed': '✅',
                    'cancelled': '❌'
                }
                
                text += f"{status_emoji.get(order.status, '❓')} Заказ #{order.id}\n"
                text += f"   Тип: {'🚕 Такси' if order.order_type == 'taxi' else '📦 Доставка'}\n"
                text += f"   Статус: {order.status}\n"
                text += f"   Цена: {PriceCalculator.format_price(order.price)}\n"
                text += f"   Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=self._get_back_keyboard()
            )
            
        except Exception as e:
            await callback.answer("Ошибка загрузки заказов", show_alert=True)
    
    def _get_cancel_keyboard(self):
        """Клавиатура с кнопкой отмены"""
        builder = InlineKeyboardBuilder()
        builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel")
        return builder.as_markup()
    
    def _get_location_keyboard(self):
        """Клавиатура с кнопкой отправки местоположения"""
        builder = InlineKeyboardBuilder()
        builder.button(text="📍 Отправить местоположение", callback_data="send_location")
        builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel")
        return builder.as_markup()
    
    def _get_confirm_order_keyboard(self):
        """Клавиатура подтверждения заказа"""
        builder = InlineKeyboardBuilder()
        builder.button(text=Config.BUTTONS['confirm'], callback_data="confirm_order")
        builder.button(text=Config.BUTTONS['cancel'], callback_data="cancel")
        return builder.as_markup()
    
    def _get_back_keyboard(self):
        """Клавиатура с кнопкой назад"""
        builder = InlineKeyboardBuilder()
        builder.button(text=Config.BUTTONS['back'], callback_data="back_to_main")
        return builder.as_markup()
    
    def _format_order_confirmation(self, data: dict, price: float, distance: float) -> str:
        """Форматирование подтверждения заказа"""
        return (
            f"🚕 Подтверждение заказа такси\n\n"
            f"📍 Откуда: {data['pickup_lat']:.4f}, {data['pickup_lon']:.4f}\n"
            f"🎯 Куда: {data['destination_lat']:.4f}, {data['destination_lon']:.4f}\n"
            f"💰 Стоимость: {PriceCalculator.format_price(price)}\n"
            f"📏 Расстояние: {PriceCalculator.format_distance(distance)}\n\n"
            f"Подтвердите заказ:"
        )
