from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import config

engine = create_engine(config.get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Session:
    return SessionLocal()
