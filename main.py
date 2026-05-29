import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from config import config

# Импортируем главный объединенный роутер всех обработчиков
from handlers import all_routers

from database.db_manager import init_db, add_user

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

BOT_TOKEN = config.bot_token.get_secret_value()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    # 1. Инициализируем таблицы базы данных
    await init_db()
    
    # 2. АВТО-АДМИН: проверяем главного админа в БД
    try:
        if config.admin_id:
            await add_user(user_id=config.admin_id, username="SuperAdmin", role="admin")
            logging.info(f"Права главного администратора для ID {config.admin_id} успешно проверены в БД.")
    except Exception as e:
        logging.error(f"Не удалось автоматически выдать права админа: {e}")
    
    # 3. Подключаем главный объединенный роутер всех обработчиков
    dp.include_router(all_routers)
    
    logging.info("Асинхронное ядро AXIOMA и база данных запущены...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())