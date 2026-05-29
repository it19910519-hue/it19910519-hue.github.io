import logging
import re
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
from aiogram.fsm.context import FSMContext

from database.db_manager import (
    get_orders_by_status,
    get_order_by_id,
    get_user_role,
    start_delivery_order,
    complete_order_delivery,
    assign_order_to_courier,
    get_courier_active_orders_count,
    get_courier_total_earnings,
    update_order_delivery_time,
    get_courier_delivered_orders_details,
    aiosqlite,
    DB_PATH
)

courier_router = Router()
logger = logging.getLogger(__name__)

# Твой реальный ID Администратора
ADMIN_ID = 917744746


# =========================================================
# HELPERS
# =========================================================

def safe(text):
    if not text:
        return "Нет"
    return escape(str(text))


async def is_courier(user_id: int):
    # Железный пропуск для тебя, чтобы панель работала всегда
    if user_id == ADMIN_ID:
        return True
    role = await get_user_role(user_id)
    return role in ["courier", "admin"]


async def get_client_id_by_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM orders WHERE id = ?", (order_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def notify_client(bot, client_id: int, text: str):
    try:
        await bot.send_message(
            chat_id=client_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.exception(e)


def extract_coords(address_string):
    if not address_string:
        return None
    match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', address_string)
    if match:
        return match.group(1), match.group(2)
    return None


def build_order_card(order):
    try:
        order_id = order['id'] if 'id' in order else order.get('id', '?')
        customer_name = order['customer_name'] if 'customer_name' in order else order.get('customer_name', 'Клиент')
        items = order['items'] if 'items' in order else order.get('items', 'Не указано')
        total_price = order['total_price'] if 'total_price' in order else order.get('total_price', 0)
        raw_address = order['address'] if 'address' in order else order.get('address', 'Нет адреса')
        phone = order['phone'] if 'phone' in order else order.get('phone', 'Нет телефона')
        comment = order['comment'] if 'comment' in order else order.get('comment', 'Нет комментария')
    except Exception:
        order_id = order[0] if hasattr(order, '__getitem__') else '?'
        customer_name = 'Клиент'
        items = 'Заказ'
        total_price = 0
        raw_address = 'Адрес'
        phone = ''
        comment = ''

    if " | Детали: " in str(raw_address):
        try:
            _, details_part = str(raw_address).split(" | Детали: ", 1)
            address_text = f"{safe(details_part)}"
        except:
            address_text = f"{safe(raw_address)}"
    elif "http" in str(raw_address):
        address_text = f"По координатам"
    else:
        address_text = f"{safe(raw_address)}"

    raw_phone = str(phone).strip()

    return (
        f"📦 <b>Заказ №{order_id}</b>\n\n"
        f"👤 <b>Клиент:</b> {safe(customer_name)}\n\n"
        f"🍕 <b>Состав:</b>\n{safe(items)}\n\n"
        f"💰 <b>Сумма:</b> {total_price} грн\n\n"
        f"🏠 <b>Адрес доставки (нажми для копирования):</b>\n<code>{address_text}</code>\n\n"
        f"📱 <b>Телефон:</b> <code>{safe(raw_phone)}</code>\n\n"
        f"📝 <b>Комментарий:</b> {safe(comment)}"
    )


def build_courier_order_keyboard(order, order_id, is_active=True):
    builder = InlineKeyboardBuilder()
    
    try:
        phone_val = order['phone'] if 'phone' in order else order.get('phone', '')
    except:
        phone_val = ''
        
    raw_phone = "".join(filter(str.isdigit, str(phone_val)))
    if raw_phone:
        formatted_phone = raw_phone if raw_phone.startswith("38") else f"38{raw_phone}" if raw_phone.startswith("0") else raw_phone
        builder.row(InlineKeyboardButton(text="💬 Написать клиенту в ТГ", url=f"https://t.me/+{formatted_phone}"))

    try:
        address_val = order['address'] if 'address' in order else order.get('address', '')
    except:
        address_val = ''
        
    coords = extract_coords(str(address_val))
    if coords:
        lat, lon = coords
        google_maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
        waze_url = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
        
        builder.row(
            InlineKeyboardButton(text="🌍 Google Maps", url=google_maps_url),
            InlineKeyboardButton(text="🚙 Waze", url=waze_url)
        )
    
    if is_active:
        builder.row(InlineKeyboardButton(text="✅ Заказ доставлен", callback_data=f"courier_confirm_complete_{order_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🛵 Взять заказ", callback_data=f"courier_confirm_take_{order_id}"))
        
    return builder.as_markup()


def build_confirmation_keyboard(action_type, order_id):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, уверен", callback_data=f"courier_yes_{action_type}_{order_id}"),
        InlineKeyboardButton(text="❌ Нет (Назад)", callback_data=f"courier_back_to_{action_type}_{order_id}")
    )
    return builder.as_markup()


# =========================================================
# MAIN PANEL
# =========================================================

@courier_router.message(F.text == "🛵 Панель Курьера")
async def courier_panel(message: Message):
    user_role = await get_user_role(message.from_user.id)
    print(f"✈️ ХЭНДЛЕР КУРЬЕРА СРАБОТАЛ! ID: {message.from_user.id}, Роль из БД: {user_role}")

    if not await is_courier(message.from_user.id):
        print(f"❌ Доступ отклонен для ID: {message.from_user.id} (Не курьер и не админ)")
        return

    ready_orders = await get_orders_by_status("ready_for_delivery")
    active_orders = await get_orders_by_status("delivering")
    my_active_count = len([o for o in active_orders if o.get("courier_id") == message.from_user.id])

    builder = InlineKeyboardBuilder()
    builder.button(text=f"📦 Доступные ({len(ready_orders)})", callback_data="courier_available_orders")
    builder.button(text=f"🛵 Мои доставки ({my_active_count})", callback_data="courier_my_orders")
    builder.button(text="📊 Моя статистика", callback_data="courier_stats")
    
    if message.from_user.id == ADMIN_ID:
        builder.button(text="🧹 Сбросить зависшие доставки", callback_data="courier_force_clear_all_debts")
        
    builder.button(text="❌ Выйти в меню", callback_data="courier_exit_to_main")
    builder.adjust(1)

    await message.answer(
        "🛵 <b>Панель Курьера AXIOMA</b>\n\nЗдесь отображаются заказы, готовые к доставке.",
        parse_mode=ParseMode.HTML,
        reply_markup=builder.as_markup()
    )


@courier_router.callback_query(F.data == "courier_force_clear_all_debts")
async def courier_force_clear_all_debts(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status = 'delivered' WHERE status = 'delivering'")
            await db.commit()
            
        await callback.message.answer("⚙️ <b>База данных успешно очищена!</b>\nВсе заказы со статусом 'В доставке' переведены в 'Доставлено'.")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка очистки БД: {e}")
    await callback.answer()


# =========================================================
# AVAILABLE ORDERS
# =========================================================

@courier_router.callback_query(F.data == "courier_available_orders")
async def show_available_orders(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        await callback.answer("❌ У вас нет прав курьера", show_alert=True)
        return

    orders = await get_orders_by_status("ready_for_delivery")
    
    if not orders:
        await callback.message.answer("📦 На данный момент нет доступных заказов для доставки.")
        await callback.answer()
        return

    for order in orders:
        order_id = order['id'] if 'id' in order else order.get('id', '?')
        text = build_order_card(order)
        reply_markup = build_courier_order_keyboard(order, order_id, is_active=False)
        
        await callback.message.answer(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    await callback.answer()


# =========================================================
# CONFIRM STAGES
# =========================================================

@courier_router.callback_query(F.data.startswith("courier_confirm_"))
async def courier_confirm_action(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    parts = callback.data.split("_")
    action_type = parts[2]
    order_id = int(parts[3])

    if action_type == "take":
        text = f"❓ <b>Вы уверены, что хотите ВЗЯТЬ заказ №{order_id} в доставку?</b>"
    else:
        text = f"❓ <b>Вы уверены, что заказ №{order_id} успешно ДОСТАВЛЕН клиенту?</b>"

    await callback.message.edit_reply_markup(
        reply_markup=build_confirmation_keyboard(action_type, order_id)
    )
    await callback.answer()


@courier_router.callback_query(F.data.startswith("courier_back_to_"))
async def courier_back_to_order(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    parts = callback.data.split("_")
    action_type = parts[3]
    order_id = int(parts[4])

    order = await get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    is_active = (action_type == "complete")
    await callback.message.edit_reply_markup(
        reply_markup=build_courier_order_keyboard(order, order_id, is_active=is_active)
    )
    await callback.answer("Действие отменено")


# =========================================================
# REAL TAKE
# =========================================================

@courier_router.callback_query(F.data.startswith("courier_yes_take_"))
async def courier_take_order(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[3])
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    if order["status"] != "ready_for_delivery":
        await callback.answer("⚠️ Заказ уже забрали")
        return

    courier_id = callback.from_user.id
    await assign_order_to_courier(order_id, courier_id)
    await start_delivery_order(order_id)

    delivery_started = datetime.now().strftime("%H:%M:%S")
    await update_order_delivery_time(order_id, delivery_started)

    client_id = await get_client_id_by_order(order_id)
    if client_id:
        await notify_client(
            callback.bot,
            client_id,
            f"🛵 <b>Заказ №{order_id}</b> передан курьеру и уже едет к вам!"
        )

    updated_order = await get_order_by_id(order_id) or order
    reply_markup = build_courier_order_keyboard(updated_order, order_id, is_active=True)

    await callback.message.answer(
        f"🛵 <b>Вы взяли заказ №{order_id}</b>\n🕒 <b>Время выезда:</b> {delivery_started}\n\n{build_order_card(updated_order)}",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer("Заказ взят в работу!")


# =========================================================
# MY ACTIVE ORDERS
# =========================================================

@courier_router.callback_query(F.data == "courier_my_orders")
async def courier_my_orders(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    courier_id = callback.from_user.id
    orders = await get_orders_by_status("delivering")
    my_orders = [o for o in orders if o.get("courier_id") == courier_id]

    if not my_orders:
        await callback.message.answer("📭 У вас нет активных доставок")
        await callback.answer()
        return

    await callback.message.answer(
        f"🛵 <b>Ваши текущие доставки:</b>\n{len(my_orders)} шт.",
        parse_mode=ParseMode.HTML
    )

    for order in my_orders:
        reply_markup = build_courier_order_keyboard(order, order['id'], is_active=True)
        await callback.message.answer(
            build_order_card(order),
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    await callback.answer()


# =========================================================
# REAL COMPLETE
# =========================================================

@courier_router.callback_query(F.data.startswith("courier_yes_complete_"))
async def courier_complete_order(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[3])
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден")
        return

    if order["status"] != "delivering":
        await callback.answer("⚠️ Заказ уже завершен")
        return

    await complete_order_delivery(order_id)
    logger.info(f"Order {order_id} completed")

    client_id = await get_client_id_by_order(order_id)
    if client_id:
        await notify_client(
            callback.bot,
            client_id,
            f"🎉 <b>Заказ №{order_id}</b> успешно доставлен!\n\nСпасибо за заказ ❤️"
        )

    await callback.message.answer(
        f"✅ <b>Заказ №{order_id}</b> успешно доставлен.",
        parse_mode=ParseMode.HTML
    )

    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer("Заказ успешно закрыт!")


# =========================================================
# COURIER STATS
# =========================================================

@courier_router.callback_query(F.data == "courier_stats")
async def courier_stats(callback: CallbackQuery):
    if not await is_courier(callback.from_user.id):
        return

    courier_id = callback.from_user.id
    
    active_orders = await get_courier_active_orders_count(courier_id)
    earnings = await get_courier_total_earnings(courier_id)
    delivered_orders = await get_courier_delivered_orders_details(courier_id)

    text = (
        "📊 <b>Статистика Курьера</b>\n\n"
        f"🛵 Активных доставок сейчас: {active_orders}\n"
        f"💰 Общий заработок: {earnings} грн\n"
        f"✅ Выполнено заказов: {len(delivered_orders)} шт.\n"
        "---------------------------------------\n"
        "📜 <b>Список выполненных локаций:</b>\n"
        "(Нажми на адрес, чтобы скопировать для 2ГИС)\n\n"
    )

    if delivered_orders:
        for index, order in enumerate(delivered_orders, start=1):
            order_id = order['id']
            raw_address = order['address'] or 'Нет адреса'
            
            if " | Детали: " in str(raw_address):
                try:
                    _, address_text = str(raw_address).split(" | Детали: ", 1)
                except:
                    address_text = str(raw_address)
            else:
                address_text = str(raw_address)
                
            text += f"{index}. 📦 <b>Заказ №{order_id}</b>\n🏠 <code>{escape(address_text)}</code>\n\n"
    else:
        text += "📭 Вы пока не выполнили ни одного заказа."

    await callback.message.answer(text, parse_mode=ParseMode.HTML)
    await callback.answer()


# =========================================================
# ADMIN / FORCE COMMANDS
# =========================================================

@courier_router.message(F.text.startswith("/force_complete_"))
async def force_complete_order(message: Message):
    if message.from_user.id != ADMIN_ID: 
        return
        
    try:
        order_id = int(message.text.split("_")[2])
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status = 'delivered' WHERE id = ?", (order_id,))
            await db.commit()
        await message.answer(f"⚙️ Тестовый заказ №{order_id} принудительно переведен в статус 'Доставлен'!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при сбросе: {e}")


@courier_router.message(F.text == "/clean_my_courier")
async def clean_courier_state(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: 
        return
        
    await state.clear()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE orders SET status = 'delivered' WHERE courier_id = ? AND status = 'delivering'", 
                (message.from_user.id,)
            )
            await db.commit()
        await message.answer("🧹 Все стейты очищены, доставки в БД переведены в 'Доставлено'!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при очистке БД: {e}")