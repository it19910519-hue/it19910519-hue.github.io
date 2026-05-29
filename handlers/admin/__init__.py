from aiogram import Router
from .stats import stats_router

admin_router = Router(name="admin_router")
admin_router.include_routers(stats_router)