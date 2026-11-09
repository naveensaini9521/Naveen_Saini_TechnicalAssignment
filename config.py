import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Flask ----
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    # ---- MySQL ----
    # Example: mysql+pymysql://root:password@localhost:3306/sales_inventory
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:admin@localhost:3306/sales_inventory",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # reconnect after MySQL idle timeouts
        "pool_recycle": 280,     # < MySQL wait_timeout (default 28800 is fine, but safe)
    }

    # ---- Session ----
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    """Used by pytest — swap MySQL for in-memory SQLite for speed."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}