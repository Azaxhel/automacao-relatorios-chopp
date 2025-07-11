from pathlib import Path
import pandas as pd
from sqlalchemy import delete
from sqlmodel import Session, select
from app.database import engine, init_db
from app.models import Venda, Produto # Importa Produto

# Caminho para o CSV mestre
BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_CSV = BASE_DIR / "master.csv"

def load():
    # Inicializa o banco (cria tabelas se não existirem)
    init_db()

    # Busca o ID do produto "Chopp Pilsen 50L"
    pilsen_id = None
    with Session(engine) as sess:
        pilsen_produto = sess.exec(select(Produto).where(Produto.nome == "Chopp Pilsen 50L")).first()
        if pilsen_produto:
            pilsen_id = pilsen_produto.id
        else:
            print("Erro: Produto 'Chopp Pilsen 50L' não encontrado no banco de dados. Por favor, cadastre-o primeiro.")
            return # Aborta a carga se o produto não for encontrado

    # Lê o CSV mestre com parse de datas
    df = pd.read_csv(MASTER_CSV, parse_dates=["data"])
    # Converte para datetime.date
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    # --- Apaga todas as vendas para as datas deste CSV ---
    datas = df["data"].dropna().unique().tolist()
    with Session(engine) as sess:
        # Apaga vendas associadas ao produto Pilsen para as datas do CSV
        stmt = delete(Venda).where(Venda.data.in_(datas), Venda.produto_id == pilsen_id)
        sess.exec(stmt)
        sess.commit()

    # --- Insere tudo de novo ---
    with Session(engine) as sess:
        for _, row in df.iterrows():
            venda = Venda(
                data=row["data"],
                dia_semana=row.get("dia_da_semana"),
                total=row.get("total", 0.0),
                cartao=row.get("cartao", 0.0),
                dinheiro=row.get("dinheiro", 0.0),
                pix=row.get("pix", 0.0),
                custo_func=row.get("custo_func", 0.0),
                custo_copos=row.get("custo_copos", 0.0),
                custo_boleto=row.get("custo_boleto", 0.0),
                lucro=row.get("lucro", 0.0),
                observacoes=row.get("observacoes"),
                produto_id=pilsen_id # Associa ao produto Pilsen
            )
            sess.add(venda)
        sess.commit()

    print(f"{len(df)} registros recarregados para {len(datas)} dias.")

if __name__ == "__main__":
    load()