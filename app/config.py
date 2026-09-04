from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./telegram_pulse.db"
    CHANNELS: str = "durov,telegram"
    FETCH_INTERVAL: int = 300

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()