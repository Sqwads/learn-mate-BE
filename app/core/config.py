import os
from pydantic_settings import BaseSettings

from dotenv import load_dotenv

load_dotenv()  # load .env file

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str
    USE_REAL_JWT: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
