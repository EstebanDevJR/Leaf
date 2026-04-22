from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./leaf.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3"
    ollama_vision_model: str = "moondream"
    debug: bool = False


settings = Settings()
