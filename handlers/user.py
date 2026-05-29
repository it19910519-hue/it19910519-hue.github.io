import logging
import json
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from database.db_manager import add_user, create_order, get_user_role
from handlers.admin_panel import is_admin

# Инициализация
logger = logging.getLogger(__name__)
user_router = Router()
WEB_APP_BASE_URL = "https://it19910519-hue.github.io/"

# =========================================================
# КЛАВИАТУРЫ
# =========================================================

def get_admin_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👑 Админ Панель")
    return builder.as_markup(resize_keyboard=True)

def get_chef_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🧑‍🍳 Панель Повара")
    return builder.as_markup(resize_keyboard=True)

def get_courier_start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛵 Панель Курьера")
    return builder.as_markup(resize_keyboard=True)

# =========================================================
# ОБРАБОТЧИКИ
# =========================================================

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    
    # Регистрация пользователя
    try:
        await add_user(user_id=user_id, username=username, role="user")
    except Exception as e:
        logger.error(f"Ошибка регистрации пользователя: {e}")

    # Определяем клавиатуру
    if is_admin(user_id):
        user_reply_markup = get_admin_start_keyboard()
    else:
        role = await get_user_role(user_id)
        if role == "chef":
            user_reply_markup = get_chef_start_keyboard()
        elif role == "courier":
            user_reply_markup = get_courier_start_keyboard()
        else:
            user_reply_markup = ReplyKeyboardRemove()

    # Инлайн-кнопка для WebApp
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🍕 Открыть интерактивное меню",
                web_app=WebAppInfo(url=WEB_APP_BASE_URL)
            )
        ]
    ])
    
    await message.answer(
        f"👋 <b>Привет, {username}!</b>\n\nДобро пожаловать в <b>AXIOMA</b>.",
        parse_mode=ParseMode.HTML,
        reply_markup=user_reply_markup
    )
    await message.answer("🛒 Нажми кнопку ниже для оформления заказа:", reply_markup=inline_keyboard)

# ОБРАБОТЧИК ЗАКАЗОВ ИЗ MINI APP
@user_router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    data = message.web_app_data.data
    logger.info(f"Получены данные из Web App: {data}")
    
    try:
        order_data = json.loads(data) 
        items_list = order_data.get('items', [])
        total_price = order_data.get('total', 0)
        
        items_summary = ", ".join([f"{item['title']} x{item['count']}" for item in items_list])
        
        order_id = await create_order(
            user_id=message.from_user.id,
            customer_name=message.from_user.full_name or "Клиент",
            address="Адрес не указан",
            items=items_summary,
            total_price=float(total_price),
            comment="Web App заказ",
            phone=message.from_user.username or "Нет связи"
        )
        
        await message.answer(
            f"🎉 <b>Заказ №{order_id} успешно оформлен!</b>\n\n"
            f"🍕 <b>Состав:</b> {items_summary}\n"
            f"💰 <b>К оплате:</b> {total_price} грн",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Ошибка оформления заказа: {e}")
        await message.answer("⚠️ Произошла ошибка при обработке заказа. Попробуйте еще раз.")