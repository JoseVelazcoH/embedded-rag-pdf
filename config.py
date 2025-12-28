from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    IS_PRODUCTION: bool = False
    INNGEST_API_BASE: str = "http://127.0.0.1:8288/v1"

settings = Settings()
