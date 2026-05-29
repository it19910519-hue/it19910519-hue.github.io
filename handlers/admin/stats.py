import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)
stats_router = Router(name="stats_router")


@stats_router.callback_query(F.data == "admin_full_stats")
async def show_full_stats(callback: CallbackQuery):
    await callback.answer("Загрузка статистики...", show_alert=True)
