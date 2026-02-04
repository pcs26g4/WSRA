# database/connection.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings
import logging

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = getattr(settings, "DATABASE_URL", "").strip()

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Check your .env or environment variables."
    )

# Fix accidental inclusion of key name
if SQLALCHEMY_DATABASE_URL.startswith("DATABASE_URL="):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "DATABASE_URL=", "", 1
    ).strip()

# SQLAlchemy 1.4+ compatibility
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,      # checks dead connections
    pool_size=10,
    max_overflow=20,
    echo=False               # set True only for debugging
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
