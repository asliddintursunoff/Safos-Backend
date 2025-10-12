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
        DATABASE_URL
        # No connect_args for Postgres
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
