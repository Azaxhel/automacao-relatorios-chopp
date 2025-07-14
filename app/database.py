from sqlmodel import create_engine, SQLModel, Session
import os

# A variável do engine agora é privada e gerenciada pelas funções.
_engine = None

def get_engine():
    """Retorna a instância do engine. Lança um erro se não for inicializado."""
    if _engine is None:
        raise RuntimeError("Database engine has not been initialized. Call init_engine() first.")
    return _engine

def init_engine(database_url: str):
    """Inicializa o engine do banco de dados com a URL fornecida."""
    global _engine
    if _engine is not None:
        return

    kwargs = {"echo": False} # Desligando o echo para testes mais limpos
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}

    _engine = create_engine(database_url, **kwargs)

def get_session() -> Session:
    """Gera uma nova sessão do banco de dados a partir do engine inicializado."""
    engine = get_engine()
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Cria todas as tabelas definidas nos modelos SQLModel."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)