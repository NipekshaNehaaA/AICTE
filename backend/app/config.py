"""
Configuration settings for AICTE Approval Workflow Automation & Compliance System.
"""

import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "AICTE Approval & Compliance Automation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Database
    ENV: str = os.getenv("ENV", "development")
    _default_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aicte_dev.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
    
    # JWT Auth & Security
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "aicte_sih26262_super_secure_key_2026_jwt_token_sign")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Brute-force Lockout Policy
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # Synthetic Data Configuration
    SYNTHETIC_DATA_LABEL: str = "Synthetic Data (Modelled for Demo / Hackathon PS SIH26262)"
    SLA_CONFIG_NOTE: str = "Sample value, configurable pending APH 2024-27 compilation"

settings = Settings()
