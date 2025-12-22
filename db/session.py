import os
from pathlib import Path
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _build_database_url() -> str:
    """
    Returns the database URL from the .env file or a sensible default.
    Keeping it in a helper makes it easier to override in tests.
    """
    env_username = os.getenv("username")
    env_password = os.getenv("password")
    database_name = os.getenv("engine")
    host = os.getenv("host")
    port = os.getenv("port", "5432")

    if env_username and env_password and database_name and host:
        return (
            "postgresql+psycopg2://"
            f"{quote_plus(env_username)}:{quote_plus(env_password)}@"
            f"{host}:{port}/{database_name}"
        )

    env_database_url = os.getenv("DATABASE_URL")

    if env_database_url:
        return env_database_url

    raise RuntimeError(
        "DATABASE_URL is not configured. Set username/password/engine/host "
        "or define DATABASE_URL in the environment."
    )


DATABASE_URL = _build_database_url()
engine: Engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db_session() -> Generator:
    """
    FastAPI dependency/utility that yields a SQLAlchemy session and
    ensures the transaction is committed or rolled back safely.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
