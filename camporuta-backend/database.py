import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environmental variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env file")

# SQLAlchemy synchronous engine
engine = create_engine(
    DATABASE_URL,
    echo=True  # Helpful for tracking queries in a hackathon development environment
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
