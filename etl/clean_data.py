from pathlib import Path
import pandas as pd

SHEETS_XLSX_URL = (
    "https://docs.google.com/spreadsheets/d/10n60nd4cLS5iRk3gz31q6UG80OWJSvYeDC0JW6wLDpc/export?format=xlsx")

def clean_master(output_path="master.csv"):
    # Le todas as abas do sheets
    all_sheets: dict[str, pd.DataFrame] = pd.read_excel(
        SHEETS_XLSX_URL,
        sheet_name=None
    )

     # DEBUG: mostra quais abas vieram e seus tamanhos
    print("Abas lidas do Sheets:", list(all_sheets.keys()))
    for aba, df in all_sheets.items():
        print(f" - {aba!r}: {df.shape[0]} linhas, {df.shape[1]} colunas")

# Filtra só as abas que interessam 
    dfs = []
    for aba, df in all_sheets.items():
        if not aba.lower().startswith("registros_"):
            continue
        df.columns = (
            df.columns
                .str.strip()
                .str.normalize("NFKD")
                .str.encode("ascii", errors="ignore")
                .str.decode("utf-8")
                .str.lower()
                .str.replace(r"\s+", "_", regex=True) 
    )
            
    # renomeia as colunas necessarias
        df = df.rename(columns={
        "vendas_total_feira": "total",
        "cartao_feira": "cartao",
        "dinheiro_feira": "dinheiro",
        "pix_feira": "pix",
        "lucro_feira": "lucro",
        "boleto_klaro": "custo_boleto",
        "custo_funcionarios": "custo_func"})
    
        dfs.append(df)

    # concatena num único dataframe
    if not dfs:
        print('nenhuma aba ded registros encontrada')
        return
    
    master = pd.concat(dfs, ignore_index=True)
    print("Concatenei:", master.shape[0], "linhas de", len(dfs), "abas.")

    # Trata a data de forma genérica
    master["data"] = pd.to_datetime(master["data"], dayfirst=True, errors="coerce")
    
    # Se necessário, descarta linhas sem data válida
    master = master.dropna(subset=["data"])

     # Tratamento de numéricos 
    campos_num = [
        "total", "cartao", "dinheiro", "pix", "lucro",
        "custo_func", "custo_copos", "custo_boleto"
    ]

    def parse_num(s):
        # se for NaN do pandas, já zera
        if pd.isna(s):
            return 0.0
        # se for int ou float _não_ NaN, retorna direto
        if isinstance(s, (int, float)):
            return float(s)
        # senão, é string: remove milhar e ajusta vírgula
        s = str(s).strip().replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0
        

    for col in campos_num:
        master[col] = master[col].apply(parse_num)

    # exporta o csv limpo
    out = Path(__file__).parent.parent / output_path
    master.to_csv(out, index=False)
    print(f'Master salvo em {out!s} com {len(master)} registros.')

if __name__ == "__main__":
    clean_master()
    
