"""
Обработчики команд для администраторов Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config

router = Router()

@router.message(Command("admin"))
async def admin_command(message: Message):
    """Команда для администраторов"""
    await message.answer(
        "👑 Панель администратора\n\n"
        "Функции для администраторов находятся в разработке.\n"
        "Скоро здесь появится возможность:\n"
        "• Просматривать статистику\n"
        "• Управлять пользователями\n"
        "• Настраивать тарифы\n"
        "• Модерировать заказы\n"
        "• Системные настройки",
        reply_markup=get_main_menu_keyboard()
    )

def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()
