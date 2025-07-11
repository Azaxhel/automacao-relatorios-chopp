from sqlmodel import SQLModel, Field, Relationship
from datetime import date
from typing import List, Optional

class Produto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    preco_venda_litro: float
    preco_venda_barril_fechado: float
    volume_litros: float # Adicionado para calcular a baixa de estoque corretamente

    # Relacionamentos para o SQLAlchemy entender as ligações
    movimentos: List["MovimentoEstoque"] = Relationship(back_populates="produto")
    vendas: List["Venda"] = Relationship(back_populates="produto")

class MovimentoEstoque(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tipo_movimento: str  # 'entrada', 'saida_manual', 'saida_venda', 'saida_venda_barril'
    quantidade: float      # Número de barris (pode ser float para vendas parciais)
    custo_unitario: Optional[float] = None # Custo por barril (na entrada)
    data_movimento: date

    produto_id: int = Field(foreign_key="produto.id")
    produto: Produto = Relationship(back_populates="movimentos")

class Venda(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    data: date
    dia_semana: str
    tipo_venda: str # 'copo' ou 'barril'
    total: Optional[float] = None
    cartao: Optional[float] = None
    dinheiro: Optional[float] = None
    pix: Optional[float] = None
    custo_func: Optional[float] = None
    custo_copos: Optional[float] = None
    custo_boleto: Optional[float] = None
    lucro: float
    observacoes: Optional[str] = None
    quantidade_barris_vendidos: Optional[float] = None # Para vendas de barril fechado
    preco_venda_litro_registrado: Optional[float] = None # Preço por litro no momento da venda

    produto_id: Optional[int] = Field(default=None, foreign_key="produto.id")
    produto: Optional[Produto] = Relationship(back_populates="vendas")