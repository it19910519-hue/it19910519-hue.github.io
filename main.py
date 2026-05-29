import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import config
# Импортируем готовый "пакет" всех роутеров
from handlers import all_routers 
from database.db_manager import init_db, add_user

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def main():
    # 1. Инициализация БД
    await init_db()
    
    # 2. Регистрация администратора
    if config.admin_id:
        await add_user(user_id=config.admin_id, username="SuperAdmin", role="admin")
        logging.info(f"Администратор {config.admin_id} успешно зарегистрирован/обновлен.")
    
    # 3. Настройка бота и диспетчера
    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher()
    
    # 4. Подключение всех роутеров одной командой
    dp.include_router(all_routers)
    logging.info("Все роутеры (user, admin, chef, courier, stats) успешно подключены.")
    
    # 5. Запуск
    logging.info("Запуск бота AXIOMA...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен пользователем.")