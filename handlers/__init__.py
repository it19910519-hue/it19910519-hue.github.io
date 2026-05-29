from aiogram import Router

from .admin_panel import admin_router
from .chef import chef_router
from .courier import courier_router
from .user import user_router


all_routers = Router()

all_routers.include_router(admin_router)
all_routers.include_router(chef_router)
all_routers.include_router(courier_router)
all_routers.include_router(user_router)
