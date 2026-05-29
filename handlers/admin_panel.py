import logging
from html import escape
from typing import Optional

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUser,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder,
    ReplyKeyboardBuilder
)

from config import config

from database.db_manager import (
    get_users_count,
    get_users_by_role,
    add_product,
    get_all_products,
    update_user_role,
    get_admin_sales_stats,
    get_orders_count_by_status,
    delete_product,
    get_product_by_id
)

logger = logging.getLogger(__name__)
admin_router = Router(name="admin_router")

PRODUCTS_PER_PAGE = 5
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000
MAX_CATEGORY_LENGTH = 50

SUPER_ADMIN_IDS = {
    917744746
}


class AddProductData(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_category = State()
    waiting_for_stock = State()
    waiting_for_photo = State()


class PromoteStaffData(StatesGroup):
    waiting_for_courier = State()
    waiting_for_chef = State()


def safe(text: Optional[str]) -> str:
    if not text:
        return ""
    return escape(str(text))


def is_admin(user_id: int) -> bool:
    if user_id in SUPER_ADMIN_IDS:
        return True

    return user_id == config.admin_id


# =========================================================
# КЛАВИАТУРЫ (ИСПРАВЛЕНО РАЗДЕЛЕНИЕ)
# =========================================================

# ОБЩАЯ клавиатура: возвращаем её курьерам и поварам, чтобы они видели свои панели!
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👑 Админ Панель"))
    builder.row(
        KeyboardButton(text="🧑‍🍳 Панель Повара"),
        KeyboardButton(text="🛵 Панель Курьера")
    )
    return builder.as_markup(resize_keyboard=True)


# АДМИНСКАЯ клавиатура: выдается тебе при отмене или успешном действии (без лишних панелей)
def get_only_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="👑 Админ Панель"))
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )


async def validate_text(
    message: Message,
    min_length: int = 2,
    max_length: int = 1000
):
    if not message.text:
        await message.answer("❌ Отправьте text")
        return None

    text = message.text.strip()

    if len(text) < min_length:
        await message.answer(f"❌ Минимум {min_length} символа")
        return None

    if len(text) > max_length:
        await message.answer(f"❌ Максимум {max_length} символов")
        return None

    return text


async def safe_edit_message(callback: CallbackQuery, text: str, builder=None):
    try:
        await callback.message.edit_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup() if builder else None
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logger.exception(e)


# =========================================================
# CANCEL FSM
# =========================================================

@admin_router.message(F.text == "❌ Отмена")
async def cancel_fsm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Действие отменено",
        reply_markup=get_only_admin_keyboard() # Админу возвращаем только его кнопку
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@admin_router.message(Command("admin"))
@admin_router.message(F.text == "👑 Админ Панель")
async def cmd_admin(message: Message, state: FSMContext):

    if not is_admin(message.from_user.id):
        return

    await state.clear()

    try:
        users = await get_users_count()
        total_sales = await get_admin_sales_stats()

        pending = await get_orders_count_by_status("ready_for_delivery")
        delivering = await get_orders_count_by_status("delivering")

        active_orders = pending + delivering

        builder = InlineKeyboardBuilder()

        builder.button(
            text="➕ Добавить товар",
            callback_data="admin_add_product"
        )

        builder.button(
            text="📦 Список товаров",
            callback_data="admin_products_0"
        )

        builder.button(
            text="📊 Полная статистика",
            callback_data="admin_full_stats"
        )

        builder.row(
            InlineKeyboardButton(
                text="🛵 Назначить курьера",
                callback_data="admin_add_courier"
            ),
            InlineKeyboardButton(
                text="🧑‍🍳 Назначить повара",
                callback_data="admin_add_chef"
            )
        )

        text = (
            f"🛠️ <b>Панель AXIOMA</b>\n\n"
            f"👥 Пользователей: {users}\n"
            f"📦 Активных заказов: {active_orders}\n"
            f"💰 Выручка: {total_sales} грн"
        )

        await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )

    except Exception as e:
        logger.exception(e)
        await message.answer(
            "❌ Ошибка загрузки админ панели"
        )


# =========================================================
# CALLBACK ХЭНДЛЕРЫ ДЛЯ АДМИН ПАНЕЛИ
# =========================================================

@admin_router.callback_query(F.data == "admin_add_product")
async def start_add_product(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddProductData.waiting_for_title)
    await callback.message.answer("📝 Введите название товара:", reply_markup=get_cancel_keyboard())
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_products_"))
async def list_products(callback: CallbackQuery):
    # Здесь должен быть твой код вывода списка товаров
    # Если его нет, бот будет писать "is not handled"
    await callback.answer("Функция в разработке или не подключена")

@admin_router.callback_query(F.data == "admin_full_stats")
async def show_full_stats(callback: CallbackQuery):
    await callback.answer("Загрузка статистики...", show_alert=True)


# =========================================================
# ADD COURIER (НАЗНАЧЕНИЕ КУРЬЕРА)
# =========================================================

@admin_router.callback_query(F.data == "admin_add_courier")
async def start_add_courier(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    # Уникальный request_id = 1 для курьера
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="👤 Выбрать курьера",
                    request_user=KeyboardButtonRequestUser(request_id=1, user_is_bot=False)
                )
            ],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "📇 Нажмите на кнопку ниже, чтобы выбрать человека для назначения <b>курьером</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await state.set_state(PromoteStaffData.waiting_for_courier)
    await callback.answer()


# Хэндлер ловит ТОЛЬКО курьера по request_id == 1
@admin_router.message(PromoteStaffData.waiting_for_courier, F.user_shared.request_id == 1)
async def process_add_courier(message: Message, state: FSMContext):
    user_id = message.user_shared.user_id

    await update_user_role(user_id=user_id, new_role="courier")
    logger.info(f"Admin promoted {user_id} to courier")

    await message.answer(
        f"✅ Пользователь успешно назначен курьером!",
        parse_mode=ParseMode.HTML,
        reply_markup=get_only_admin_keyboard() # Возвращаем админу чистую админку
    )
    await state.clear()


# =========================================================
# ADD CHEF (НАЗНАЧЕНИЕ ПОВАРА)
# =========================================================

@admin_router.callback_query(F.data == "admin_add_chef")
async def start_add_chef(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    # Уникальный request_id = 2 для повара
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="👤 Выбрать повара",
                    request_user=KeyboardButtonRequestUser(request_id=2, user_is_bot=False)
                )
            ],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.answer(
        "📇 Нажмите на кнопку ниже, чтобы выбрать человека для назначения <b>поваром</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await state.set_state(PromoteStaffData.waiting_for_chef)
    await callback.answer()


# Хэндлер ловит ТОЛЬКО повара по request_id == 2
@admin_router.message(PromoteStaffData.waiting_for_chef, F.user_shared.request_id == 2)
async def process_add_chef(message: Message, state: FSMContext):
    user_id = message.user_shared.user_id

    await update_user_role(user_id=user_id, new_role="chef")
    logger.info(f"Admin promoted {user_id} to chef")

    await message.answer(
        f"✅ Пользователь успешно назначен поваром!",
        parse_mode=ParseMode.HTML,
        reply_markup=get_only_admin_keyboard() # Возвращаем админу чистую админку
    )
    await state.clear()
