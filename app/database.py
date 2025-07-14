# app/database.py

from typing import Generator
from sqlmodel import create_engine, SQLModel, Session
import os

_engine = None

def init_engine(database_url: str) -> None:
    global _engine
    if _engine is not None:
        return  # Evita recriar

    kwargs = {"echo": False}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    _engine = create_engine(database_url, **kwargs)

def get_engine():
    if _engine is None:
        raise RuntimeError("Engine não foi inicializado.")
    return _engine

def get_session() -> Generator[Session, None, None]:
    engine = get_engine()
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

def drop_db_and_tables():
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
