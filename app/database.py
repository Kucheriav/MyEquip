import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import config


logger = logging.getLogger("app.database")

DATABASE_URL = config.get_db_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session, commits on success
    and rolls back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_all_tables():
    """Create all tables declared by app.models (no-op if they exist)."""
    # Import models so that all tables are registered on Base.metadata
    import app.models  # noqa: F401

    logger.info("Creating database tables (if missing)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables are ready")
