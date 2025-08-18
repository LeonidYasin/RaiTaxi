"""
Обработчики команд для водителей Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from utils.validators import DataValidator

router = Router()

class DriverRegistrationStates(StatesGroup):
    """Состояния для регистрации водителя"""
    waiting_for_car_model = State()
    waiting_for_car_number = State()
    waiting_for_license = State()
    waiting_for_phone = State() # New state for phone number collection
    confirming_registration = State()

class DriverOrderStates(StatesGroup):
    """Состояния для работы с заказами"""
    viewing_orders = State()
    order_details = State()

# Глобальные переменные для доступа к операциям БД и боту
user_ops = None
order_ops = None
driver_ops = None
bot = None

def set_operations(user_operations, order_operations, driver_operations, bot_instance):
    """Устанавливает операции с БД и экземпляр бота для обработчиков"""
    global user_ops, order_ops, driver_ops, bot
    user_ops = user_operations
    order_ops = order_operations
    driver_ops = driver_operations
    bot = bot_instance

@router.message(Command("driver"))
async def driver_command(message: Message):
    """Команда для водителей"""
    user_id = message.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id) if user_ops else None
        
        if not user_db_id:
            await message.answer(
                "❌ Ошибка: пользователь не найден в базе данных",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        # Проверяем, зарегистрирован ли водитель
        driver = await driver_ops.get_driver_by_user_id(user_db_id) if driver_ops else None
        
        if driver:
            # Водитель уже зарегистрирован - показываем панель
            await show_driver_panel(message, driver)
        else:
            # Водитель не зарегистрирован - предлагаем регистрацию
            await show_driver_registration(message)
            
    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )

async def show_driver_panel(message: Message, driver):
    """Показывает панель водителя"""
    status_emoji = "🟢" if driver.is_available else "🔴"
    status_text = "Доступен" if driver.is_available else "Недоступен"
    
    panel_text = f"🚗 Панель водителя\n\n"
    panel_text += f"👤 {message.from_user.first_name}\n"
    panel_text += f"🚙 {driver.car_model} ({driver.car_number})\n"
    panel_text += f"📊 Статус: {status_emoji} {status_text}\n"
    panel_text += f"⭐ Рейтинг: {driver.rating:.1f}\n"
    panel_text += f"🚕 Поездок: {driver.total_trips}\n"
    panel_text += f"💰 Заработок: {driver.total_earnings:.0f} ₽\n\n"
    panel_text += "Выберите действие:"
    
    builder = InlineKeyboardBuilder()
    
    if driver.is_available:
        builder.button(text="🔴 Стать недоступным", callback_data="driver_offline")
        builder.button(text="📋 Доступные заказы", callback_data="view_available_orders")
    else:
        builder.button(text="🟢 Стать доступным", callback_data="driver_online")
    
    builder.button(text="📊 Мои заказы", callback_data="driver_my_orders")
    builder.button(text="💰 Финансы", callback_data="driver_finances")
    builder.button(text="⚙️ Настройки", callback_data="driver_settings")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 1, 1)
    
    await message.answer(panel_text, reply_markup=builder.as_markup())

async def show_driver_registration(message: Message):
    """Показывает форму регистрации водителя"""
    registration_text = "🚗 Регистрация водителя\n\n"
    registration_text += "Для работы в сервисе Рай-Такси необходимо:\n"
    registration_text += "• Ввести данные автомобиля\n"
    registration_text += "• Указать номер водительского удостоверения\n"
    registration_text += "• Подтвердить информацию\n\n"
    registration_text += "Начнем регистрацию?"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать регистрацию", callback_data="start_driver_registration")
    builder.button(text="❌ Отмена", callback_data="back_to_main")
    
    await message.answer(registration_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "start_driver_registration")
async def start_driver_registration(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс регистрации водителя"""
    await state.set_state(DriverRegistrationStates.waiting_for_car_model)
    
    await callback.message.edit_text(
        "🚙 Введите модель и марку автомобиля:\n\n"
        "Например: Toyota Camry, Lada Granta, Hyundai Solaris",
        reply_markup=get_cancel_keyboard()
    )

@router.message(DriverRegistrationStates.waiting_for_car_model)
async def handle_car_model(message: Message, state: FSMContext):
    """Обрабатывает ввод модели автомобиля"""
    car_model = message.text.strip()
    
    # Простая валидация модели автомобиля
    if len(car_model) < 3:
        await message.answer(
            "❌ Слишком короткое название модели\n"
            "Введите полное название модели и марки автомобиля",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if len(car_model) > 50:
        await message.answer(
            "❌ Слишком длинное название модели\n"
            "Введите более короткое название",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(car_model=car_model)
    await state.set_state(DriverRegistrationStates.waiting_for_car_number)
    
    await message.answer(
        "🚗 Введите номер автомобиля:\n\n"
        "Например: А123БВ77, М777ММ77",
        reply_markup=get_cancel_keyboard()
    )

@router.message(DriverRegistrationStates.waiting_for_car_number)
async def handle_car_number(message: Message, state: FSMContext):
    """Обрабатывает ввод номера автомобиля"""
    car_number = message.text.strip().upper()
    
    # Валидация номера автомобиля
    is_valid, error_msg = DataValidator.validate_car_number(car_number)
    if not is_valid:
        await message.answer(
            f"❌ {error_msg}\n\n"
            "Введите номер в формате: А123БВ77, М777ММ77",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(car_number=car_number)
    await state.set_state(DriverRegistrationStates.waiting_for_license)
    
    await message.answer(
        "📋 Введите номер водительского удостоверения:\n\n"
        "Например: 77 АА 123456",
        reply_markup=get_cancel_keyboard()
    )

@router.message(DriverRegistrationStates.waiting_for_license)
async def handle_license(message: Message, state: FSMContext):
    """Обрабатывает ввод номера водительского удостоверения"""
    license_number = message.text.strip()
    
    # Простая валидация номера ВУ
    if len(license_number) < 8:
        await message.answer(
            "❌ Слишком короткий номер ВУ\n"
            "Введите полный номер водительского удостоверения",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if len(license_number) > 20:
        await message.answer(
            "❌ Слишком длинный номер ВУ\n"
            "Введите корректный номер",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(license_number=license_number)
    await state.set_state(DriverRegistrationStates.waiting_for_phone)
    
    await message.answer(
        "📞 Пожалуйста, поделитесь своим номером телефона, чтобы клиенты могли с вами связаться.",
        reply_markup=get_phone_request_keyboard()
    )

@router.message(DriverRegistrationStates.waiting_for_phone, F.contact)
async def handle_driver_phone_number(message: Message, state: FSMContext):
    """Обрабатывает полученный номер телефона водителя"""
    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    
    await user_ops.update_user_phone(user_id, phone_number)
    
    # Now proceed to confirmation
    data = await state.get_data()
    
    confirm_text = "📋 Подтвердите данные регистрации:\n\n"
    confirm_text += f"🚙 Автомобиль: {data['car_model']}\n"
    confirm_text += f"🚗 Номер: {data['car_number']}\n"
    confirm_text += f"📋 ВУ: {data['license_number']}\n"
    confirm_text += f"📞 Телефон: {phone_number}\n\n"
    confirm_text += "Все верно?"
    
    await state.set_state(DriverRegistrationStates.confirming_registration)
    await message.answer(confirm_text, reply_markup=get_confirm_registration_keyboard())

@router.message(DriverRegistrationStates.waiting_for_phone, F.text)
async def handle_driver_phone_number_text(message: Message, state: FSMContext):
    """Обрабатывает введенный номер телефона водителя (если пользователь не использовал кнопку)"""
    phone_number = message.text.strip()
    
    # Простая валидация номера телефона
    if not phone_number.startswith('+') or len(phone_number) < 10:
        await message.answer(
            "❌ Пожалуйста, введите корректный номер телефона, начиная с '+' (например, +79123456789), или используйте кнопку 'Поделиться номером телефона'.",
            reply_markup=get_phone_request_keyboard()
        )
        return
    
    user_id = message.from_user.id
    await user_ops.update_user_phone(user_id, phone_number)
    
    # Now proceed to confirmation
    data = await state.get_data()
    
    confirm_text = "📋 Подтвердите данные регистрации:\n\n"
    confirm_text += f"🚙 Автомобиль: {data['car_model']}\n"
    confirm_text += f"🚗 Номер: {data['car_number']}\n"
    confirm_text += f"📋 ВУ: {data['license_number']}\n"
    confirm_text += f"📞 Телефон: {phone_number}\n\n"
    confirm_text += "Все верно?"
    
    await state.set_state(DriverRegistrationStates.confirming_registration)
    await message.answer(confirm_text, reply_markup=get_confirm_registration_keyboard())

@router.callback_query(F.data == "confirm_driver_registration")
async def confirm_driver_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждает регистрацию водителя"""
    data = await state.get_data()
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.message.edit_text(
                "❌ Ошибка: пользователь не найден в базе данных",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()
            return
        
        # Создаем водителя в базе данных
        driver = await driver_ops.create_driver(
            user_id=user_db_id,
            car_model=data['car_model'],
            car_number=data['car_number'],
            license_number=data['license_number']
        )
        
        if driver:
            # Обновляем роль пользователя на 'driver' (используем telegram_id)
            await user_ops.update_user_role(user_id, 'driver')
            
            await callback.message.edit_text(
                "✅ Регистрация водителя успешно завершена!\n\n"
                "Теперь вы можете:\n"
                "• Просматривать доступные заказы\n"
                "• Принимать заказы\n"
                "• Управлять своим статусом\n\n"
                "Используйте команду /driver для доступа к панели",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка регистрации. Попробуйте позже.",
                reply_markup=get_main_menu_keyboard()
            )
    
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка регистрации: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    """Отменяет регистрацию водителя"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Регистрация отменена\n\n"
        "Вы можете зарегистрироваться позже командой /driver",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "driver_online")
async def driver_online(callback: CallbackQuery):
    """Делает водителя доступным"""
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return
        
        await driver_ops.update_driver_availability(user_db_id, True)
        await callback.answer("🟢 Вы стали доступным для заказов!")
        
        # Обновляем сообщение
        driver = await driver_ops.get_driver_by_user_id(user_db_id)
        await show_driver_panel(callback.message, driver)
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "driver_offline")
async def driver_offline(callback: CallbackQuery):
    """Делает водителя недоступным"""
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return
        
        await driver_ops.update_driver_availability(user_db_id, False)
        await callback.answer("🔴 Вы стали недоступным для заказов!")
        
        # Обновляем сообщение
        driver = await driver_ops.get_driver_by_user_id(user_db_id)
        await show_driver_panel(callback.message, driver)
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "view_available_orders")
async def view_available_orders(callback: CallbackQuery):
    """Показывает доступные заказы"""
    try:
        orders = await order_ops.get_available_orders()
        
        if not orders:
            await callback.message.edit_text(
                "📋 Доступных заказов пока нет\n\n"
                "Ожидайте новых заказов или проверьте позже",
                reply_markup=get_back_to_driver_panel_keyboard()
            )
            return
        
        orders_text = "📋 Доступные заказы:\n\n"
        for order in orders[:5]:  # Показываем первые 5 заказов
            orders_text += f"🚕 Заказ #{order.id}\n"
            orders_text += f"📍 Откуда: {order.pickup_address or 'Координаты'}\n"
            if order.destination_address:
                orders_text += f"🎯 Куда: {order.destination_address}\n"
            orders_text += f"💰 Стоимость: {order.price:.0f} ₽\n"
            orders_text += f"📏 Расстояние: {order.distance:.1f} км\n\n"
        
        if len(orders) > 5:
            orders_text += f"... и еще {len(orders) - 5} заказов\n\n"
        
        orders_text += "Выберите заказ для принятия:"
        
        builder = InlineKeyboardBuilder()
        
        # Кнопки для заказов
        for order in orders[:5]:
            builder.button(
                text=f"🚕 #{order.id} - {order.price:.0f}₽", 
                callback_data=f"take_order_{order.id}"
            )
        
        builder.button(text="🔄 Обновить", callback_data="view_available_orders")
        builder.button(text="⬅️ Назад", callback_data="back_to_driver_panel")
        
        builder.adjust(1)  # По одной кнопке в строке
        
        await callback.message.edit_text(orders_text, reply_markup=builder.as_markup())
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("driver_accept_order_"))
async def driver_accept_order(callback: CallbackQuery):
    """Обрабатывает принятие заказа водителем"""
    try:
        order_id = int(callback.data.split("_")[3])
        user_id = callback.from_user.id
        
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        if not user_db_id:
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return
        
        success = await order_ops.assign_driver_to_order(order_id, user_db_id)
        
        if success:
            await callback.answer("✅ Заказ принят!")
            order = await order_ops.get_order_by_id(order_id)
            client_user = await user_ops.get_user_by_id(order.client_id)
            driver_user = await user_ops.get_user_by_id(user_db_id) # Get driver's user object
            
            driver_phone = driver_user.phone if driver_user else "Не указан"
            
            if client_user and client_user.telegram_id:
                client_message_text = (
                    f"✅ Ваш заказ #{order.id} принят водителем!\n\n"
                    f"🚗 Водитель: {driver_user.first_name} ({driver_user.username or 'без username'})\n"
                    f"📞 Телефон водителя: {driver_phone}\n"
                    f"🚙 Автомобиль: {driver.car_model} ({driver.car_number})\n\n"
                    "Водитель скоро свяжется с вами."
                )
                builder = InlineKeyboardBuilder()
                builder.button(text="📞 Позвонить водителю", url=f"tel:{driver_phone}")
                await bot.send_message(
                    chat_id=client_user.telegram_id,
                    text=client_message_text,
                    reply_markup=builder.as_markup()
                )
            
            # Обновляем сообщение для водителя
            await callback.message.edit_text(
                f"✅ Вы приняли заказ #{order.id}!\n\n"
                f"📍 Откуда: {order.pickup_address or f'{order.pickup_lat:.4f}, {order.pickup_lon:.4f}'}\n"
                f"🎯 Куда: {order.destination_address or f'{order.destination_lat:.4f}, {order.destination_lon:.4f}'}\n"
                f"💰 Стоимость: {order.price:.0f} ₽\n"
                f"📏 Расстояние: {order.distance:.1f} км\n\n"
                f"📞 Телефон клиента: {client_user.phone if client_user else 'Не указан'}\n\n"
                "📱 Свяжитесь с клиентом для уточнения деталей."
            )
            # Optionally, update driver's availability to busy
            await driver_ops.update_driver_availability(user_db_id, False) # Driver is now busy
            
        else:
            await callback.answer("❌ Заказ уже принят другим водителем или отменен.", show_alert=True)
            await callback.message.edit_text(
                "❌ Этот заказ уже недоступен.",
                reply_markup=get_back_to_driver_panel_keyboard()
            )
            
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID заказа", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка при принятии заказа: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("driver_reject_order_"))
async def driver_reject_order(callback: CallbackQuery):
    """Обрабатывает отказ водителя от заказа"""
    try:
        order_id = int(callback.data.split("_")[3])
        user_id = callback.from_user.id
        
        # Просто уведомляем водителя, что заказ не принят
        await callback.answer("❌ Вы отказались от заказа.")
        await callback.message.edit_text(
            f"Вы отказались от заказа #{order_id}.",
            reply_markup=get_back_to_driver_panel_keyboard()
        )
        
        # В find_and_assign_driver будет логика перенаправления на другого водителя
        # Здесь мы просто обновляем статус заказа, чтобы он снова стал "new" или "searching_driver"
        # для возможности предложить его другому водителю.
        # Однако, если мы хотим, чтобы find_and_assign_driver продолжил поиск,
        # то не нужно менять статус здесь, а просто позволить таймауту сработать.
        # Для простоты, пока не меняем статус здесь.
        
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID заказа", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка при отказе от заказа: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("take_order_"))
async def take_order(callback: CallbackQuery):
    """
    Этот обработчик остался от предыдущей логики "доступных заказов".
    Его можно удалить или переиспользовать, если "view_available_orders"
    будет предлагать заказы, которые еще не были предложены через "find_and_assign_driver".
    Пока что, он дублирует функционал driver_accept_order.
    """
    await callback.answer("Используйте кнопки 'Принять' или 'Отказаться' в уведомлении о новом заказе.")
    # Можно перенаправить на driver_accept_order или driver_reject_order
    # Например:
    # order_id = int(callback.data.split("_")[2])
    # await driver_accept_order(callback) # Или driver_reject_order

@router.callback_query(F.data == "driver_my_orders")
async def driver_my_orders(callback: CallbackQuery):
    """Показывает заказы водителя"""
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return
        
        orders = await order_ops.get_driver_orders(user_db_id, limit=10)
        
        if not orders:
            await callback.message.edit_text(
                "📋 У вас пока нет заказов\n\n"
                "Принимайте заказы, чтобы они появились здесь",
                reply_markup=get_back_to_driver_panel_keyboard()
            )
            return
        
        orders_text = "📋 Ваши заказы:\n\n"
        for order in orders:
            status_emoji = {
                'driver_assigned': '🚗',
                'in_progress': '🚀',
                'completed': '✅',
                'cancelled': '❌'
            }.get(order.status, '❓')
            
            orders_text += f"{status_emoji} Заказ #{order.id}\n"
            orders_text += f"   Статус: {order.status}\n"
            orders_text += f"   💰 {order.price:.0f} ₽\n"
            orders_text += f"   📅 {order.created_at.strftime('%d.%m %H:%M') if order.created_at else 'Неизвестно'}\n\n"
        
        await callback.message.edit_text(
            orders_text,
            reply_markup=get_back_to_driver_panel_keyboard()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "driver_finances")
async def driver_finances(callback: CallbackQuery):
    """Показывает финансовую информацию водителя"""
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
            return
        
        driver = await driver_ops.get_driver_by_user_id(user_db_id)
        
        if not driver:
            await callback.answer("❌ Водитель не найден", show_alert=True)
            return
        
        finance_text = "💰 Финансовая информация\n\n"
        finance_text += f"💳 Общий заработок: {driver.total_earnings:.0f} ₽\n"
        finance_text += f"🚕 Всего поездок: {driver.total_trips}\n"
        finance_text += f"⭐ Рейтинг: {driver.rating:.1f}\n"
        finance_text += f"📊 Средний чек: {driver.total_earnings / max(driver.total_trips, 1):.0f} ₽\n\n"
        finance_text += "💡 Рейтинг влияет на приоритет получения заказов"
        
        await callback.message.edit_text(
            finance_text,
            reply_markup=get_back_to_driver_panel_keyboard()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "driver_settings")
async def driver_settings(callback: CallbackQuery):
    """Показывает настройки водителя"""
    settings_text = "⚙️ Настройки водителя\n\n"
    settings_text += "🔔 Уведомления:\n"
    settings_text += "• Новые заказы\n"
    settings_text += "• Изменения статуса\n"
    settings_text += "• Финансовые отчеты\n\n"
    settings_text += "📱 Дополнительные настройки\n"
    settings_text += "будут доступны в следующих версиях"
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_back_to_driver_panel_keyboard()
    )

@router.callback_query(F.data == "back_to_driver_panel")
async def back_to_driver_panel(callback: CallbackQuery):
    """Возврат к панели водителя"""
    user_id = callback.from_user.id
    
    try:
        # Получаем ID пользователя из БД
        user_db_id = await user_ops.get_user_id_by_telegram_id(user_id)
        
        if not user_db_id:
            await callback.message.edit_text(
                "❌ Ошибка: пользователь не найден",
                reply_markup=get_main_menu_keyboard()
            )
            return
        
        driver = await driver_ops.get_driver_by_user_id(user_db_id) if driver_ops else None
        
        if driver:
            await show_driver_panel(callback.message, driver)
        else:
            await callback.message.edit_text(
                "❌ Ошибка: водитель не найден",
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    from handlers.client import start_command
    await start_command(callback.message)

# Вспомогательные функции для клавиатур
def get_phone_request_keyboard():
    """Клавиатура для запроса номера телефона"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Поделиться номером телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_registration")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_confirm_registration_keyboard():
    """Клавиатура подтверждения регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_driver_registration")
    builder.button(text="❌ Отмена", callback_data="back_to_main")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_back_to_driver_panel_keyboard():
    """Клавиатура возврата к панели водителя"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад к панели", callback_data="back_to_driver_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()
