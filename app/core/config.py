from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized application configuration (# NFR-BE-2 Security)."""

    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")
    SQLALCHEMY_DATABASE_URI: Optional[str] = Field(None, env="SQLALCHEMY_DATABASE_URI")

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OPENAI_API_KEY: str = ""

    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"

    MEDIA_STORAGE: str = "local"  # "local" or "s3"
    MEDIA_LOCAL_DIR: str = "media/menu"
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = ""

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    FORCE_HTTPS: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SQLALCHEMY_DATABASE_URI:
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL must be provided")
            self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL
        if not self.DATABASE_URL:
            self.DATABASE_URL = self.SQLALCHEMY_DATABASE_URI


settings = Settings()
