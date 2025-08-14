"""
Обработчики команд для водителей Рай-Такси
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.operations import UserOperations, OrderOperations, DriverOperations
from config import Config

router = Router()

class DriverHandlers:
    """Обработчики для водителей"""
    
    def __init__(self, user_ops: UserOperations, order_ops: OrderOperations, driver_ops: DriverOperations):
        self.user_ops = user_ops
        self.order_ops = order_ops
        self.driver_ops = driver_ops
    
    # Здесь будут обработчики для водителей
    # Пока оставляем заглушку

# Заглушка для роутера
@router.message(Command("driver"))
async def driver_command(message: Message):
    """Команда для водителей (заглушка)"""
    await message.answer("🚗 Функции для водителей находятся в разработке")
