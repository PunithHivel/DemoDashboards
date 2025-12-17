import os
from pathlib import Path
from typing import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


def _manual_load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue
        key, _, value = cleaned.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            os.environ[key] = value  # Always set/override from .env file


_manual_load_dotenv()


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

    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/insightly",
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
