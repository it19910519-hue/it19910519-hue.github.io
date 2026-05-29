import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from handlers import all_routers
from database.db_manager import init_db, add_user

# =========================
# Logging
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# =========================
# Main
# =========================
async def main():
    logger.info("Запуск AXIOMA BOT...")

    # --- Инициализация БД ---
    try:
        await init_db()
        logger.info("База данных успешно подключена")
    except Exception as e:
        logger.error(f"Ошибка подключения БД: {e}")
        return

    # --- Регистрация администратора ---
    try:
        if config.admin_id:
            await add_user(
                user_id=config.admin_id,
                username="SuperAdmin",
                role="admin"
            )
            logger.info(f"Администратор {config.admin_id} успешно зарегистрирован/обновлен")
    except Exception as e:
        logger.error(f"Ошибка регистрации admin: {e}")

    # --- Создание бота ---
    bot = Bot(
        token=config.bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # --- Диспетчер ---
    dp = Dispatcher()

    # --- Подключение всех роутеров ---
    dp.include_router(all_routers)
    logger.info("Все роутеры успешно подключены")

    # --- Удаление webhook (если был) ---
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook удален")

    # --- Старт polling ---
    logger.info("AXIOMA BOT успешно запущен 🚀")
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")


# =========================
# Entry point
# =========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Бот остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
