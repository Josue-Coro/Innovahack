import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environmental variables from .env (local dev only; on Render use env vars)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env file")

# SQLAlchemy synchronous engine
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT", "production") == "development",
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections every 30 min (important for Supabase pooler)
    pool_pre_ping=True,  # Test connections before use to avoid stale connections
)

# Synchronous sessionmaker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base class for models
Base = declarative_base()

# FastAPI Dependency for db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
