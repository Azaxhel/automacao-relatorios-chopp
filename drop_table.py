from app.database import engine, init_db
from sqlmodel import SQLModel, Session
from sqlalchemy import text

def drop_venda_table():
    print("Tentando conectar ao banco de dados...")
    try:
        # Garante que o banco de dados está inicializado (cria tabelas se não existirem)
        init_db()
        
        with Session(engine) as session:
            print("Conectado ao banco de dados. Excluindo tabela 'venda'...")
            session.execute(text("DROP TABLE IF EXISTS venda;"))
            session.commit()
            print("Tabela 'venda' excluída com sucesso (se existia).")
    except Exception as e:
        print(f"Erro ao excluir tabela: {e}")

if __name__ == "__main__":
    drop_venda_table()
