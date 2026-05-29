from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):

    # =========================
    # TELEGRAM
    # =========================
    bot_token: SecretStr
    admin_id: int

    # =========================
    # DATABASE
    # =========================
    database_url: str = "sqlite+aiosqlite:///axioma.db"

    # =========================
    # WEB APP
    # =========================
    web_app_url: str = "https://it19910519-hue.github.io/"

    # =========================
    # PAYMENT INFO
    # =========================
    payment_card: str = "4441 1111 2222 3333"
    payment_receiver: str = "AXIOMA"
    mono_jar_url: str = "https://send.monobank.ua/jar/XXXXXXXX"

    # =========================
    # DEFAULT ORDER SETTINGS
    # =========================
    order_comment_default: str = "Web App заказ"

    # =========================
    # LOGGING
    # =========================
    log_level: str = "INFO"

    # =========================
    # Pydantic settings
    # =========================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


config = Config()
