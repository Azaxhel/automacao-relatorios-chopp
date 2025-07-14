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

    # --- Lógica de Upsert: Atualiza ou Insere ---
    # O ETL legado do sheets trata apenas de vendas de 'feira'.
    # A chave para uma venda única do ETL é (data, produto_id, tipo_venda='feira')
    registros_atualizados = 0
    registros_inseridos = 0

    with Session(engine) as sess:
        for _, row in df.iterrows():
            data_venda = row["data"]
            if pd.isna(data_venda):
                continue

            # Procura por uma venda de 'feira' existente para a mesma data e produto
            venda_existente = sess.exec(
                select(Venda).where(
                    Venda.data == data_venda, 
                    Venda.produto_id == pilsen_id,
                    Venda.tipo_venda == 'feira' # Chave para vendas do ETL
                )
            ).first()

            if venda_existente:
                # Se existe, atualiza os campos
                venda_existente.dia_semana = row.get("dia_da_semana")
                venda_existente.total = row.get("total", 0.0)
                venda_existente.cartao = row.get("cartao", 0.0)
                venda_existente.dinheiro = row.get("dinheiro", 0.0)
                venda_existente.pix = row.get("pix", 0.0)
                venda_existente.custo_func = row.get("custo_func", 0.0)
                venda_existente.custo_copos = row.get("custo_copos", 0.0)
                venda_existente.custo_boleto = row.get("custo_boleto", 0.0)
                venda_existente.lucro = row.get("lucro", 0.0)
                venda_existente.observacoes = row.get("observacoes")
                sess.add(venda_existente)
                registros_atualizados += 1
            else:
                # Se não existe, cria uma nova venda do tipo 'feira'
                nova_venda = Venda(
                    data=data_venda,
                    dia_semana=row.get("dia_da_semana"),
                    tipo_venda='feira', # Define o tipo para vendas do ETL
                    total=row.get("total", 0.0),
                    cartao=row.get("cartao", 0.0),
                    dinheiro=row.get("dinheiro", 0.0),
                    pix=row.get("pix", 0.0),
                    custo_func=row.get("custo_func", 0.0),
                    custo_copos=row.get("custo_copos", 0.0),
                    custo_boleto=row.get("custo_boleto", 0.0),
                    lucro=row.get("lucro", 0.0),
                    observacoes=row.get("observacoes"),
                    produto_id=pilsen_id
                )
                sess.add(nova_venda)
                registros_inseridos += 1
        
        sess.commit()

    print(f"ETL concluído. Registros de 'feira' inseridos: {registros_inseridos}. Registros atualizados: {registros_atualizados}.")

if __name__ == "__main__":
    load()