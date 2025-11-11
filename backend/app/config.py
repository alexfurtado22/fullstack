# app/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- ImageKit ---
    IMAGEKIT_PRIVATE_KEY: str
    IMAGEKIT_PUBLIC_KEY: str
    IMAGEKIT_URL_ENDPOINT: str

    # --- JWT ---
    JWT_SECRET: str  # 🔐 New secure secret for JWTs

    # --- Environment ---
    ENVIRONMENT: str = "production"  # Add this line

    # --- 2. ADD MAIL SETTINGS ---
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    # --------------------------

    # Environment file location
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Settings()
