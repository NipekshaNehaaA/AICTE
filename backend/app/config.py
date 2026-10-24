"""
Configuration settings for AICTE Approval Workflow Automation & Compliance System.
"""

import os
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "AICTE Approval & Compliance Automation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Database
    ENV: str = os.getenv("ENV", "development")
    _default_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aicte_dev.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
    
    # JWT Auth & Security
    # Primary secret env var: JWT_SECRET (with fallback to JWT_SECRET_KEY / SECRET_KEY)
    SECRET_KEY: str = Field(
        default_factory=lambda: (
            os.getenv("JWT_SECRET")
            or os.getenv("JWT_SECRET_KEY")
            or os.getenv("SECRET_KEY", "aicte-cryptographic-signing-key-secret-2026")
        )
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Demonstration & Evaluation Mode (defaults to false; off in production)
    DEMO_MODE: bool = Field(
        default_factory=lambda: (
            os.getenv("EVALUATOR_MODE", "false").lower() in ("true", "1", "yes")
            or os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
        )
    )
    EVALUATOR_MODE: bool = Field(
        default_factory=lambda: (
            os.getenv("EVALUATOR_MODE", "false").lower() in ("true", "1", "yes")
            or os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
        )
    )
    
    # Brute-force Lockout Policy
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # Storage Configuration (Local Disk or MinIO S3)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local") # 'local' or 'minio'
    STORAGE_LOCAL_DIR: str = os.getenv(
        "STORAGE_LOCAL_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_data")
    )
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(15 * 1024 * 1024))) # 15 MB
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "aicte_minio_admin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "aicte_minio_secure_pass_2026")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "aicte-documents")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

    # Real Alert Channels (SMTP & WhatsApp)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "1025"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@aicte-india.org")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "false").lower() in ("true", "1", "yes")

    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    # Synthetic Data Configuration
    SYNTHETIC_DATA_LABEL: str = "Synthetic Data (Modelled for Demo / Hackathon PS SIH26262)"
    SLA_CONFIG_NOTE: str = "Sample value, configurable pending APH 2024-27 compilation"

settings = Settings()
