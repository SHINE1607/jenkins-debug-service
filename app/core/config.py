import os
from typing import Any, List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings  #ignore 
from functools import lru_cache
import logging
import google.generativeai as genai
# Force load from .env file first
load_dotenv(override=True)  # Add override=True

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "public")  # Default to public schema if not specified
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")  # Default to dev if not specified
    DB_NAME: str = os.getenv("DB_NAME", "jenkins_debug")
    DB_ENDPOINT: str = os.getenv("DB_ENDPOINT", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")  # Default PostgreSQL port

    
    @property
    def BACKEND_URL(self):
        if self.ENVIRONMENT == "prod":
            return os.getenv("BACKEND_URL")
        else:
            return "http://localhost:8000"

    def DB_CONNECTION_STRING(self, environment: str = None):
        if environment is None:
            environment = self.ENVIRONMENT
            
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_ENDPOINT}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CORS_ORIGINS(self):
        if self.ENVIRONMENT == "prod":
            return [    
                "http://127.0.0.1:3000",         
                "http://127.0.0.1:8000",         
            ]
        else:
            return [
                "http://localhost:3000",
                "http://localhost:8000"
            ]

@lru_cache()
def get_settings():
    return Settings()

@lru_cache()
def get_logger():
    logging.basicConfig(level=logging.DEBUG)
    return logging.getLogger(__name__)

@lru_cache()
def get_model():
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return genai.GenerativeModel('gemini-2.0-flash')


settings = get_settings()
logger = get_logger()
