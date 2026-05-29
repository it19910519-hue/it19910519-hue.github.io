import logging
import json
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

# Импорты из других файлов проекта
from database.db_manager import add_user, create_order, get_user_role
from .keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
user_router = Router()

WEB_APP_BASE_URL = "https://it19910519-hue.github.io/"

# --- START ---
@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Очищаем любое состояние при старте
    await state.clear()
    
    # Добавляем пользователя в базу
    await add_user(
        user_id=message.from_user.id, 
        username=message.from_user.username or "User", 
        role="user"
    )
    
    # Проверяем роль для показа кнопок управления
    role = await get_user_role(message.from_user.id)
    keyboard = get_main_keyboard() if role in ["admin", "chef", "courier"] else None
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍕 Открыть меню AXIOMA", web_app=WebAppInfo(url=WEB_APP_BASE_URL))]
    ])
    
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}! Добро пожаловать в AXIOMA.", 
        reply_markup=inline_kb
    )
    
    if keyboard:
        await message.answer("🛠 Для вас доступны панели управления:", reply_markup=keyboard)

# --- WEB APP DATA ---
@user_router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    # 1. Проверка на наличие данных
    if not message.web_app_data or not message.web_app_data.data:
        logger.error(f"Пользователь {message.from_user.id} отправил пустые web_app_data")
        await message.answer("⚠️ Ошибка: данные заказа не получены. Попробуйте еще раз.")
        return

    raw_data = message.web_app_data.data
    logger.info(f"Получены данные от Web App для пользователя {message.from_user.id}: {raw_data}")
    
    try:
        data = json.loads(raw_data)
        items = data.get('items', [])
        total = data.get('total', 0)
        
        if not items:
            await message.answer("🛒 Ваша корзина пуста. Добавьте товары перед заказом.")
            return

        items_str = "\n".join([f"• {i['title']} x{i['count']}" for i in items])
        
        # Создание заказа в БД
        order_id = await create_order(
            user_id=message.from_user.id,
            customer_name=message.from_user.full_name,
            address="Не указан",
            items=items_str,
            total_price=float(total),
            comment="Web App заказ",
            phone=message.from_user.username or "Нет"
        )
        
        if order_id:
            await message.answer(
                f"🎉 **Заказ №{order_id} успешно принят!**\n\n"
                f"🍕 **Состав:**\n{items_str}\n\n"
                f"💰 **К оплате:** {total} грн",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Заказ {order_id} успешно записан в БД.")
        else:
            raise Exception("Ошибка записи в базу данных")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при создании заказа: {e}")
        await message.answer("❌ Произошла ошибка при оформлении заказа. Попробуйте позже.")