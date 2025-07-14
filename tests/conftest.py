# tests/conftest.py

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.database import init_engine, get_engine, get_session
from app import models  # importa os modelos para registrar no metadata

@pytest.fixture(scope="session")
def test_db_url():
    # Cria um arquivo temporário para o banco SQLite
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_url = f"sqlite:///{temp_db.name}"
    os.environ["DATABASE_URL"] = db_url
    return db_url

@pytest.fixture(scope="session")
def engine(test_db_url):
    init_engine(test_db_url)
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
    # Não dropa as tabelas aqui para facilitar múltiplos testes que compartilham o schema

@pytest.fixture
def client(session):
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
