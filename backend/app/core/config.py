import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/app_db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production-min32chars")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

settings = Settings()
