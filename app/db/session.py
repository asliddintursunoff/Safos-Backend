from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

# Detect if SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Only for SQLite
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,   # drop dead connections instead of failing the request
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
