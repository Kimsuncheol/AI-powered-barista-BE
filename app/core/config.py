from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PAYPAL_CLIENT_ID: str
    PAYPAL_CLIENT_SECRET: str
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
