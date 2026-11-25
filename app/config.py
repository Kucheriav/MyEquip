import os
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")


class Config(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    PASSWORD_SALT: str
    BOT_API_KEY: str = ""
    # Auth settings
    SECRET_KEY: str = "dev-secret-change-me"
    AUTH_ENABLED: bool = False
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Web UI: mark the session cookie Secure when served over HTTPS
    WEB_COOKIE_SECURE: bool = False
    # File logging
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 14
    LOG_SLOW_MS: int = 500
    # Trust X-Forwarded-For (only enable behind nginx/Caddy)
    TRUST_PROXY: bool = False
    # Uploaded photos (kept outside the database; back up this folder too)
    DATA_DIR: str = "data"
    PHOTO_MAX_MB: int = 5
    PHOTO_MAX_PER_ITEM: int = 12

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    )

    def get_db_url(self):
        s = f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return s

    def get_salt(self):
        return self.PASSWORD_SALT

    def get_bot_api(self):
        if not self.BOT_API_KEY:
            logger.warning("BOT_API_KEY is not set in .env")
            return None
        return self.BOT_API_KEY

config = Config()