from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db_manager import get_users_count, get_admin_sales_stats

# Создаем отдельный роутер для статистики
stats_router = Router(name="stats_router")

@stats_router.callback_query(F.data == "admin_full_stats")
async def show_full_stats(callback: CallbackQuery):
    # Получаем данные
    users = await get_users_count()
    sales = await get_admin_sales_stats()
    
    # Формируем сообщение
    text = (
        f"📊 <b>Полная статистика:</b>\n\n"
        f"👥 Всего пользователей: {users}\n"
        f"💰 Всего продаж: {sales} грн"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()