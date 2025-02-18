import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_default_secret")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "your_default_refresh_secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    BASE_URL = os.getenv("BASE_URL")
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 10
    RESET_TOKEN_EXPIRE_MINUTES: int = 10
    MAX_EMAIL_RETRIES: int = 3

settings = Settings()