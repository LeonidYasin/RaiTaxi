"""
Обработчики команд для водителей Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config

router = Router()

@router.message(Command("driver"))
async def driver_command(message: Message):
    """Команда для водителей"""
    await message.answer(
        "🚗 Панель водителя\n\n"
        "Функции для водителей находятся в разработке.\n"
        "Скоро здесь появится возможность:\n"
        "• Просматривать доступные заказы\n"
        "• Принимать заказы\n"
        "• Обновлять статус поездки\n"
        "• Вести учет заработка",
        reply_markup=get_main_menu_keyboard()
    )

def get_main_menu_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Главное меню", callback_data="back_to_main")
    return builder.as_markup()
