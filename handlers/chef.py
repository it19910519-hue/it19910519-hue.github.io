import logging
from html import escape
from datetime import datetime

from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import (
    InlineKeyboardBuilder
)

from database.db_manager import (
    get_orders_by_status,
    start_cooking_order,
    ready_for_delivery_order,
    get_order_by_id,
    get_user_role,
    update_order_cooking_time,
    aiosqlite,
    DB_PATH
)

chef_router = Router()
logger = logging.getLogger(__name__)

# =========================================================
# HELPERS
# =========================================================

def safe(text: str):
    if not text:
        return "Нет"
    return escape(str(text))


async def is_chef(user_id: int):
    # Железный пропуск для тебя, чтобы панель работала всегда, пока настраиваешь роли
    if user_id == 917744746:
        return True
    role = await get_user_role(user_id)
    return role in ["chef", "admin"]


async def get_client_id_by_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


def build_order_text(order):
    priority = "🟢"
    if order.get("priority") == "high":
        priority = "🔴"

    return (
        f"{priority} <b>Заказ №{order['id']}</b>\n\n"
        f"🍕 <b>Состав:</b>\n{safe(order['items'])}\n\n"
        f"📝 <b>Комментарий:</b>\n{safe(order['comment'])}\n\n"
        f"💰 <b>Сумма:</b> {order.get('total_price', 0)} грн\n"
        f"🕒 <b>Создан:</b> {order.get('created_at', '-')}"
    )


async def notify_client(bot, client_id: int, text: str):
    try:
        await bot.send_message(
            chat_id=client_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.exception(e)


# =========================================================
# CHEF PANEL
# =========================================================

@chef_router.message(F.text == "🧑‍🍳 Панель Повара")
async def chef_main_menu(message: Message):
    if not await is_chef(message.from_user.id):
        return

    pending = await get_orders_by_status("pending")
    cooking = await get_orders_by_status("cooking")

    builder = InlineKeyboardBuilder()
    builder.button(text=f"📥 Новые ({len(pending)})", callback_data="chef_new_orders")
    builder.button(text=f"🍳 Готовятся ({len(cooking)})", callback_data="chef_current_cooking")
    builder.button(text="📊 Статистика кухни", callback_data="chef_stats")
    builder.adjust(1)

    await message.answer(
        "🧑‍🍳 <b>Панель кухни AXIOMA</b>\n\n"
        "Здесь отображаются заказы,\n"
        "которые нужно приготовить.",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )


# =========================================================
# NEW ORDERS
# =========================================================

@chef_router.callback_query(F.data == "chef_new_orders")
async def show_new_orders(callback: CallbackQuery):
    if not await is_chef(callback.from_user.id):
        return

    orders = await get_orders_by_status("pending")

    if not orders:
        await callback.message.answer("📭 Новых заказов нет")
        await callback.answer()
        return

    await callback.message.answer(
        f"📥 <b>Новые заказы ({len(orders)})</b>",
        parse_mode=ParseMode.HTML
    )

    for order in orders:
        builder = InlineKeyboardBuilder()
        builder.button(text="👨‍🍳 Начать готовить", callback_data=f"chef_cook_{order['id']}")
        builder.adjust(1)

        await callback.message.answer(
            build_order_text(order),
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )
    await callback.answer()


# =========================================================
# START COOKING
# =========================================================

@chef_router.callback_query(F.data.startswith("chef_cook_"))
async def chef_start_cooking(callback: CallbackQuery):
    if not await is_chef(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[2])
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    if order["status"] != "pending":
        await callback.answer("⚠️ Заказ уже взят")
        return

    await start_cooking_order(order_id)
    cooking_started = datetime.now().strftime("%H:%M:%S")
    await update_order_cooking_time(order_id, cooking_started)

    logger.info(f"Chef started cooking order {order_id}")

    client_id = await get_client_id_by_order(order_id)
    if client_id:
        await notify_client(
            callback.bot,
            client_id,
            f"👨‍🍳 <b>Ваш заказ №{order_id}</b>\n\nуже начали готовить!"
        )

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Готово", callback_data=f"chef_ready_{order_id}")
    builder.adjust(1)

    await callback.message.answer(
        f"🍳 <b>Заказ №{order_id}</b>\n\n"
        f"переведен в готовку.\n\n"
        f"🕒 Время старта: {cooking_started}",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )

    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# =========================================================
# CURRENT COOKING
# =========================================================

@chef_router.callback_query(F.data == "chef_current_cooking")
async def show_current_cooking(callback: CallbackQuery):
    if not await is_chef(callback.from_user.id):
        return

    orders = await get_orders_by_status("cooking")

    if not orders:
        await callback.message.answer("🤷‍♂️ Сейчас ничего не готовится")
        await callback.answer()
        return

    await callback.message.answer(
        f"🍳 <b>Сейчас готовится:</b>\n{len(orders)} заказ(ов)",
        parse_mode=ParseMode.HTML
    )

    for order in orders:
        builder = InlineKeyboardBuilder()
        builder.button(text="📦 Передать курьеру", callback_data=f"chef_ready_{order['id']}")
        builder.adjust(1)

        text = (
            f"🍳 <b>Заказ №{order['id']}</b>\n\n"
            f"🍕 {safe(order['items'])}\n\n"
            f"🕒 Начато: {safe(order.get('cooking_started_at'))}"
        )

        await callback.message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )
    await callback.answer()


# =========================================================
# ORDER READY
# =========================================================

@chef_router.callback_query(F.data.startswith("chef_ready_"))
async def chef_order_ready(callback: CallbackQuery):
    if not await is_chef(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[2])
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    if order["status"] != "cooking":
        await callback.answer("⚠️ Заказ уже обработан")
        return

    await ready_for_delivery_order(order_id)
    logger.info(f"Chef completed order {order_id}")

    client_id = await get_client_id_by_order(order_id)
    if client_id:
        await notify_client(
            callback.bot,
            client_id,
            f"📦 <b>Ваш заказ №{order_id}</b>\n\nприготовлен и передан курьеру!"
        )

    await callback.message.answer(
        f"🎉 <b>Заказ №{order_id}</b>\n\nготов и отправлен курьеру.",
        parse_mode=ParseMode.HTML
    )

    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


# =========================================================
# CHEF STATS
# =========================================================

@chef_router.callback_query(F.data == "chef_stats")
async def chef_stats(callback: CallbackQuery):
    if not await is_chef(callback.from_user.id):
        return

    pending = await get_orders_by_status("pending")
    cooking = await get_orders_by_status("cooking")
    ready = await get_orders_by_status("ready_for_delivery")

    text = (
        "📊 <b>Статистика кухни</b>\n\n"
        f"📥 Новых заказов: {len(pending)}\n"
        f"🍳 Готовятся: {len(cooking)}\n"
        f"📦 Готовы: {len(ready)}"
    )

    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()