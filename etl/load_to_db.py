from pathlib import Path
import pandas as pd
from sqlalchemy import delete
from sqlmodel import Session
from app.database import engine, init_db
from app.models import Venda

# Caminho para o CSV mestre
BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_CSV = BASE_DIR / "master.csv"

def load():
    # Inicializa o banco (cria tabelas se não existirem)
    init_db()

    # Lê o CSV mestre com parse de datas
    df = pd.read_csv(MASTER_CSV, parse_dates=["data"])
    # Converte para datetime.date
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    # --- Apaga todas as vendas para as datas deste CSV ---
    datas = df["data"].dropna().unique().tolist()
    with Session(engine) as sess:
        stmt = delete(Venda).where(Venda.data.in_(datas))
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
                observacoes=row.get("observacoes")
            )
            sess.add(venda)
        sess.commit()

    print(f"{len(df)} registros recarregados para {len(datas)} dias.")

if __name__ == "__main__":
    load()
