import asyncio
import logging
import sys

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config

# Роутеры
from handlers import all_routers

# База данных
from database.db_manager import (
    init_db,
    add_user
)

# =========================================
# ЛОГИРОВАНИЕ
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# =========================================
# MAIN
# =========================================

async def main():

    logger.info("Запуск AXIOMA BOT...")

    # =====================================
    # ИНИЦИАЛИЗАЦИЯ БД
    # =====================================

    try:

        await init_db()

        logger.info(
            "База данных успешно подключена"
        )

    except Exception as e:

        logger.error(
            f"Ошибка БД: {e}"
        )

        return

    # =====================================
    # РЕГИСТРАЦИЯ ADMIN
    # =====================================

    try:

        if config.admin_id:

            await add_user(
                user_id=config.admin_id,
                username="SuperAdmin",
                role=config.admin_role
            )

            logger.info(
                f"Администратор "
                f"{config.admin_id} "
                f"зарегистрирован"
            )

    except Exception as e:

        logger.error(
            f"Ошибка регистрации admin: {e}"
        )

    # =====================================
    # BOT
    # =====================================

    bot = Bot(

        token=config.bot_token.get_secret_value(),

        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # =====================================
    # DISPATCHER
    # =====================================

    dp = Dispatcher()

    # =====================================
    # РОУТЕРЫ
    # =====================================

    dp.include_router(all_routers)

    logger.info(
        "Роутеры успешно подключены"
    )

    # =====================================
    # УДАЛЕНИЕ WEBHOOK
    # =====================================

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "Webhook удален"
    )

    # =====================================
    # СТАРТ БОТА
    # =====================================

    logger.info(
        "AXIOMA BOT успешно запущен 🚀"
    )

    try:

        await dp.start_polling(
            bot,
            skip_updates=True
        )

    finally:

        await bot.session.close()

        logger.info(
            "Сессия бота закрыта"
        )

# =========================================
# START
# =========================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.warning(
            "Бот остановлен вручную"
        )

    except SystemExit:

        logger.warning(
            "SystemExit"
        )

    except Exception as e:

        logger.error(
            f"Критическая ошибка: {e}"
        )
