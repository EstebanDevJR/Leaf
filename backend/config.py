from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./leaf.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    ollama_num_ctx: int = 8192
    groq_api_key: str = ""
    groq_voice_model: str = "llama-3.3-70b-versatile"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    debug: bool = False


settings = Settings()
