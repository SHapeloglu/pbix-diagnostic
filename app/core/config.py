from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://pbixuser:sifre@localhost/pbixdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "/home/pbixapp/app/uploads"
    RESULTS_DIR: str = "/home/pbixapp/app/results"
    MAX_UPLOAD_MB: int = 512
    CELERY_WORKERS: int = 3  # gercek sunucu: 4 cekirdek / 8 GB (eskiden 8 vCPU/30 GB varsayilmisti)
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

PLANS = {
    "free":     {"price": 0,  "quota_monthly": 3},
    "starter":  {"price": 1,  "quota_monthly": 10},
    "pro":      {"price": 9,  "quota_monthly": 50},
    "business": {"price": 19, "quota_monthly": 200},
}
