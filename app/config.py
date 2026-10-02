"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Groq API Configuration
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    groq_fallback_model: str = "llama-3.1-8b-instant"
    
    # MongoDB Configuration
    mongodb_uri: str
    
    # JWT Authentication Configuration
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_days: int = 7
    
    # CORS Configuration
    frontend_origin: str = "http://localhost:3000"
    # Comma-separated list of allowed origins for production (e.g., "https://app.vercel.app,https://app2.vercel.app")
    allowed_origins: str = ""
    
    # Rate Limiting
    max_audio_seconds: int = 90
    max_questions_per_session: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
