import os
from etl.clean_data import clean_master
from etl.load_to_db import load

# Garante que os caminhos sejam relativos ao script
# Isso é importante para rodar em diferentes ambientes
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Iniciando processo de ETL...")
    
    # 1. Limpa os dados e gera o master.csv
    print("\nPasso 1: Limpando dados e gerando master.csv")
    clean_master()
    
    # 2. Carrega os dados do master.csv para o banco de dados
    print("\nPasso 2: Carregando dados para o banco de dados")
    load()
    
    print("\nProcesso de ETL concluído com sucesso!")
