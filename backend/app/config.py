from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    nemotron_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    database_url: str = "sqlite:///./mindjournal.db"

    class Config:
        env_file = ".env"

settings = Settings()
