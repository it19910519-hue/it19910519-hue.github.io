from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Нажмите для отмены")

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура для сотрудников."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👑 Админ Панель"))
    builder.row(
        KeyboardButton(text="🧑‍🍳 Панель Повара"),
        KeyboardButton(text="🛵 Панель Курьера")
    )
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите панель управления")