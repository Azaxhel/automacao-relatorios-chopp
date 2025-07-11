import os
from sqlmodel import create_engine, SQLModel

# Lê a URL do banco de dados da variável de ambiente
# Se não existir, usa o SQLite local como padrão
DATABASE_URL = os.getenv("DATABASE_URL")

# O `connect_args` é específico do SQLite e não é necessário para o PostgreSQL
kwargs = {"echo": True}
if DATABASE_URL.startswith("sqlite"):
    kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **kwargs)

def init_db():
    SQLModel.metadata.create_all(engine)
    