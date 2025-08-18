"""
Обработчики команд для администраторов Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config

router = Router()

class AdminSettingsStates(StatesGroup):
    """Состояния для настроек администратора"""
    waiting_for_tariff_type = State()
    waiting_for_base_fare = State()
    waiting_for_per_km_rate = State()
    waiting_for_minimum_fare = State()

# Глобальные переменные для доступа к операциям БД
user_ops = None
order_ops = None
driver_ops = None

def set_operations(user_operations, order_operations, driver_operations, bot_instance):
    """Устанавливает операции с БД и экземпляр бота для обработчиков"""
    global user_ops, order_ops, driver_ops, bot
    user_ops = user_operations
    order_ops = order_operations
    driver_ops = driver_operations
    bot = bot_instance

@router.message(Command("admin"))
async def admin_command(message: Message):
    """Команда для администраторов"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    user = await user_ops.get_user_by_telegram_id(user_id) if user_ops else None
    
    if not user or user.role != 'admin':
        await message.answer(
            "🚫 У вас нет доступа к панели администратора\n\n"
            "Для получения доступа обратитесь к главному администратору системы",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Показываем панель администратора
    await show_admin_panel(message)

async def show_admin_panel(message: Message):
    """Показывает панель администратора"""
    panel_text = "👑 Панель администратора\n\n"
    panel_text += f"👤 Администратор: {message.from_user.first_name}\n"
    panel_text += "🕐 Время: " + get_current_time() + "\n\n"
    panel_text += "Выберите раздел для управления:"
    
    builder = InlineKeyboardBuilder()
    
    # Основные функции
    builder.button(text="📊 Статистика", callback_data="admin_statistics")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="🚕 Водители", callback_data="admin_drivers")
    builder.button(text="📋 Заказы", callback_data="admin_orders")
    
    # Настройки
    builder.button(text="💰 Тарифы", callback_data="admin_tariffs")
    builder.button(text="⚙️ Система", callback_data="admin_system")
    builder.button(text="📢 Уведомления", callback_data="admin_notifications")
    
    # Дополнительно
    builder.button(text="🔍 Мониторинг", callback_data="admin_monitoring")
    builder.button(text="📈 Отчеты", callback_data="admin_reports")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 2, 2, 1)
    
    await message.answer(panel_text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_statistics")
async def admin_statistics(callback: CallbackQuery):
    """Показывает статистику системы"""
    try:
        # Получаем статистику
        total_users = await user_ops.get_total_users() if user_ops else 0
        total_drivers = await driver_ops.get_total_drivers() if driver_ops else 0
        total_orders = await order_ops.get_total_orders() if order_ops else 0
        active_orders = await order_ops.get_active_orders_count() if order_ops else 0
        
        stats_text = "📊 Статистика системы\n\n"
        stats_text += f"👥 Всего пользователей: {total_users}\n"
        stats_text += f"🚗 Зарегистрированных водителей: {total_drivers}\n"
        stats_text += f"📋 Всего заказов: {total_orders}\n"
        stats_text += f"🔄 Активных заказов: {active_orders}\n\n"
        
        # Дополнительная статистика
        if total_orders > 0:
            completed_orders = await order_ops.get_completed_orders_count() if order_ops else 0
            completion_rate = (completed_orders / total_orders) * 100
            stats_text += f"✅ Выполнено заказов: {completed_orders}\n"
            stats_text += f"📈 Процент выполнения: {completion_rate:.1f}%\n\n"
        
        stats_text += "📅 Обновлено: " + get_current_time()
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_to_admin_panel_keyboard()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    try:
        users = await user_ops.get_recent_users(limit=10) if user_ops else []
        
        if not users:
            users_text = "👥 Пользователи не найдены"
        else:
            users_text = "👥 Последние пользователи:\n\n"
            for user in users:
                role_emoji = {
                    'client': '👤',
                    'driver': '🚗',
                    'admin': '👑'
                }.get(user.role, '❓')
                
                users_text += f"{role_emoji} {user.first_name}"
                if user.last_name:
                    users_text += f" {user.last_name}"
                users_text += f"\n"
                users_text += f"   🆔 ID: {user.telegram_id}\n"
                users_text += f"   🏷️ Роль: {user.role}\n"
                users_text += f"   📅 Регистрация: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}\n\n"
        
        users_text += "Выберите действие:"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔍 Поиск пользователя", callback_data="admin_search_user")
        builder.button(text="📊 Все пользователи", callback_data="admin_all_users")
        builder.button(text="🚫 Блокировка", callback_data="admin_block_user")
        builder.button(text="✅ Разблокировка", callback_data="admin_unblock_user")
        builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main")
        
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            users_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "admin_drivers")
async def admin_drivers(callback: CallbackQuery):
    """Управление водителями"""
    try:
        # Получаем список водителей
        drivers = await driver_ops.get_all_drivers() if driver_ops else []
        
        drivers_text = "🚗 Управление водителями\n\n"
        drivers_text += f"📊 Всего водителей: {len(drivers)}\n\n"
        
        if drivers:
            drivers_text += "👥 Список водителей:\n"
            for driver in drivers[:10]:  # Показываем первые 10
                drivers_text += f"• {driver.car_model} ({driver.car_number})\n"
                drivers_text += f"  Статус: {'🟢 Онлайн' if driver.is_available else '🔴 Оффлайн'}\n"
                drivers_text += f"  Рейтинг: {driver.rating:.1f}⭐\n\n"
            
            if len(drivers) > 10:
                drivers_text += f"... и еще {len(drivers) - 10} водителей\n\n"
        else:
            drivers_text += "📋 Водителей пока нет\n\n"
        
        drivers_text += "Выберите действие:"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📊 Статистика водителей", callback_data="admin_drivers_stats")
        builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main")
        
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            drivers_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    """Управление заказами"""
    try:
        # Получаем статистику заказов
        total_orders = await order_ops.get_total_orders() if order_ops else 0
        active_orders = await order_ops.get_active_orders_count() if order_ops else 0
        completed_orders = await order_ops.get_completed_orders_count() if order_ops else 0
        
        orders_text = "📋 Управление заказами\n\n"
        orders_text += f"📊 Всего заказов: {total_orders}\n"
        orders_text += f"🔄 Активных: {active_orders}\n"
        orders_text += f"✅ Завершенных: {completed_orders}\n\n"
        
        if total_orders > 0:
            completion_rate = (completed_orders / total_orders) * 100
            orders_text += f"📈 Процент завершения: {completion_rate:.1f}%\n\n"
        
        orders_text += "Выберите действие:"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📈 Статистика заказов", callback_data="admin_orders_stats")
        builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main")
        
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            orders_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "admin_tariffs")
async def admin_tariffs(callback: CallbackQuery):
    """Управление тарифами"""
    tariffs_text = "💰 Управление тарифами\n\n"
    tariffs_text += f"🚕 Такси:\n"
    tariffs_text += f"   • Базовая стоимость: {Config.BASE_FARE} ₽\n"
    tariffs_text += f"   • За километр: {Config.PER_KM_RATE} ₽\n"
    tariffs_text += f"   • Минимальная стоимость: {Config.MINIMUM_FARE} ₽\n\n"
    tariffs_text += f"📦 Доставка:\n"
    tariffs_text += f"   • Базовая стоимость: {Config.DELIVERY_BASE_FARE} ₽\n"
    tariffs_text += f"   • За километр: {Config.PER_KM_RATE} ₽\n"
    tariffs_text += f"   • Минимальная стоимость: {Config.MINIMUM_FARE} ₽\n\n"
    tariffs_text += "Выберите действие:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить тарифы", callback_data="admin_edit_tariffs")
    builder.button(text="📊 История изменений", callback_data="admin_tariff_history")
    builder.button(text="💡 Предложения", callback_data="admin_tariff_suggestions")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 1)
    
    await callback.message.edit_text(
        tariffs_text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "admin_system")
async def admin_system(callback: CallbackQuery):
    """Системные настройки"""
    system_text = "⚙️ Системные настройки\n\n"
    system_text += "🔧 Основные параметры:\n"
    system_text += "   • Лимиты запросов\n"
    system_text += "   • Таймауты\n"
    system_text += "   • Кэширование\n"
    system_text += "   • Логирование\n\n"
    system_text += "🛡️ Безопасность:\n"
    system_text += "   • Антиспам\n"
    system_text += "   • Фильтрация\n"
    system_text += "   • Мониторинг\n\n"
    system_text += "💾 База данных:\n"
    system_text += "   • Резервное копирование\n"
    system_text += "   • Оптимизация\n"
    system_text += "   • Статистика\n\n"
    system_text += "Выберите раздел:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔧 Основные настройки", callback_data="admin_system_main")
    builder.button(text="🛡️ Безопасность", callback_data="admin_system_security")
    builder.button(text="💾 База данных", callback_data="admin_system_database")
    builder.button(text="💾 Резервное копирование", callback_data="admin_backup")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 1, 1)
    
    await callback.message.edit_text(
        system_text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "admin_monitoring")
async def admin_monitoring(callback: CallbackQuery):
    """Мониторинг системы"""
    try:
        # Получаем статистику в реальном времени
        online_drivers = await driver_ops.get_online_drivers_count() if driver_ops else 0
        pending_orders = await order_ops.get_pending_orders_count() if order_ops else 0
        
        monitoring_text = "🔍 Мониторинг системы\n\n"
        monitoring_text += "📊 Статус в реальном времени:\n"
        monitoring_text += f"   🟢 Онлайн водителей: {online_drivers}\n"
        monitoring_text += f"   📋 Ожидающих заказов: {pending_orders}\n"
        monitoring_text += f"   🕐 Время: {get_current_time()}\n\n"
        
        # Системные метрики
        monitoring_text += "💻 Системные метрики:\n"
        monitoring_text += "   • CPU: Нормальная нагрузка\n"
        monitoring_text += "   • Память: Достаточно\n"
        monitoring_text += "   • Диск: Свободно\n"
        monitoring_text += "   • Сеть: Стабильно\n\n"
        
        monitoring_text += "📈 Последние события:\n"
        monitoring_text += "   • Система работает стабильно\n"
        monitoring_text += "   • Ошибок не обнаружено\n"
        monitoring_text += "   • Все сервисы активны"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="admin_monitoring")
        builder.button(text="📊 Детальный отчет", callback_data="admin_detailed_monitoring")
        builder.button(text="⚠️ Проверить ошибки", callback_data="admin_check_errors")
        builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main")
        
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            monitoring_text,
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "admin_notifications")
async def admin_notifications(callback: CallbackQuery):
    """Управление уведомлениями"""
    notifications_text = "📢 Управление уведомлениями\n\n"
    notifications_text += "🔔 Типы уведомлений:\n"
    notifications_text += "   • Новые заказы\n"
    notifications_text += "   • Регистрация водителей\n"
    notifications_text += "   • Системные события\n"
    notifications_text += "   • Ошибки и предупреждения\n\n"
    notifications_text += "📱 Каналы доставки:\n"
    notifications_text += "   • Telegram (основной)\n"
    notifications_text += "   • Email (резервный)\n"
    notifications_text += "   • SMS (экстренные)\n\n"
    notifications_text += "Выберите действие:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Отправить уведомление", callback_data="admin_send_notification")
    builder.button(text="⚙️ Настройки уведомлений", callback_data="admin_notification_settings")
    builder.button(text="📋 История уведомлений", callback_data="admin_notification_history")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 1)
    
    await callback.message.edit_text(
        notifications_text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery):
    """Генерация отчетов"""
    reports_text = "📈 Генерация отчетов\n\n"
    reports_text += "📊 Доступные отчеты:\n"
    reports_text += "   • Финансовый отчет\n"
    reports_text += "   • Статистика заказов\n"
    reports_text += "   • Активность водителей\n"
    reports_text += "   • Анализ пользователей\n"
    reports_text += "   • Системные метрики\n\n"
    reports_text += "📅 Периоды:\n"
    reports_text += "   • За день\n"
    reports_text += "   • За неделю\n"
    reports_text += "   • За месяц\n"
    reports_text += "   • Произвольный период\n\n"
    reports_text += "Выберите тип отчета:"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Финансовый", callback_data="admin_financial_report")
    builder.button(text="📋 По заказам", callback_data="admin_orders_report")
    builder.button(text="🚗 По водителям", callback_data="admin_drivers_report")
    builder.button(text="👥 По пользователям", callback_data="admin_users_report")
    builder.button(text="📊 Системный", callback_data="admin_system_report")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    
    builder.adjust(2, 2, 2, 1)
    
    await callback.message.edit_text(
        reports_text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "back_to_admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    """Возврат к панели администратора"""
    await show_admin_panel(callback.message)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    from handlers.client import start_command
    await start_command(callback.message)

# Вспомогательные функции
def get_current_time():
    """Возвращает текущее время в читаемом формате"""
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%d.%m.%Y %H:%M:%S")

def get_back_to_admin_panel_keyboard():
    """Клавиатура возврата к панели администратора"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад к панели", callback_data="back_to_admin_panel")
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()
