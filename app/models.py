from sqlmodel import SQLModel, Field, Relationship
from datetime import date
from typing import List, Optional

class Produto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    preco_venda_litro: float
    preco_venda_barril_fechado: float

    # Relacionamentos para o SQLAlchemy entender as ligações
    movimentos: List["MovimentoEstoque"] = Relationship(back_populates="produto")
    vendas: List["Venda"] = Relationship(back_populates="produto")

class MovimentoEstoque(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo_movimento: str  # 'entrada', 'saida_manual', 'ajuste_perda'
    quantidade: int      # NÃºmero de barris
    custo_unitario: Optional[float] = None # Custo por barril (na entrada)
    data_movimento: date

    produto_id: int = Field(foreign_key="produto.id")
    produto: Produto = Relationship(back_populates="movimentos")

class Venda(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    data: date
    dia_semana: str
    total: float
    cartao: float
    dinheiro: float
    pix: float
    custo_func: float
    custo_copos: float
    custo_boleto: float
    lucro: float
    observacoes: Optional[str] = None

    produto_id: Optional[int] = Field(default=None, foreign_key="produto.id")
    produto: Optional[Produto] = Relationship(back_populates="vendas")
