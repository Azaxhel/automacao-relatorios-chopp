from sqlmodel import SQLModel, Field
from datetime import date

class Venda(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    data: date
    dia_semana: str
    total: float
    cartao: float
    dinheiro: float
    pix: float
    custo_func: float
    custo_copos: float
    custo_boleto: float
    lucro: float # Novo campo para lucro
    observacoes: str | None = None