import pytest
from datetime import date
from app.logic import calcular_relatorio_geral, calcular_ranking_dias, calcular_lucro_por_produto
from app.models import Venda, Produto

# --- Dados de Teste ---

@pytest.fixture
def vendas_de_exemplo():
    """Fornece uma lista de Vendas para usar nos testes."""
    return [
        Venda(data=date(2025, 7, 1), produto_id=1, tipo_venda="feira", total=150.0, custo_func=20, custo_copos=5, dia_semana="Tuesday", lucro=125.0),
        Venda(data=date(2025, 7, 1), produto_id=2, tipo_venda="feira", total=50.0, custo_func=10, custo_copos=2, dia_semana="Tuesday", lucro=38.0),
        Venda(data=date(2025, 7, 2), produto_id=1, tipo_venda="feira", total=250.0, custo_func=20, custo_copos=10, dia_semana="Wednesday", lucro=220.0),
        Venda(data=date(2025, 7, 3), produto_id=1, tipo_venda="boleto", total=0.0, custo_boleto=5.0, dia_semana="Thursday", lucro=-5.0),
    ]

@pytest.fixture
def produtos_de_exemplo():
    """Fornece uma lista de Produtos para usar nos testes."""
    return [
        Produto(id=1, nome="Chopp Pilsen"),
        Produto(id=2, nome="Chopp IPA"),
    ]

# --- Testes da Lógica ---

def test_calcular_relatorio_geral_com_dados(vendas_de_exemplo):
    """Testa o cálculo do relatório geral com uma lista de vendas."""
    report = calcular_relatorio_geral(vendas_de_exemplo)
    
    assert report is not None
    assert report["receita_bruta"] == 450.00  # 150 + 50 + 250 (boleto é ignorado)
    assert report["gasto_funcionarios"] == 50.00 # 20 + 10 + 20
    assert report["gasto_copos"] == 17.00 # 5 + 2 + 10
    assert report["gasto_boleto"] == 5.00
    assert report["receita_liquida"] == 378.00 # 450 - 50 - 17 - 5
    assert report["dias_registrados"] == 2 # Dias 1 e 2 (dia 3 é boleto)

def test_calcular_relatorio_geral_lista_vazia():
    """Testa o cálculo do relatório com uma lista vazia de vendas."""
    report = calcular_relatorio_geral([])
    assert report is None

def test_calcular_ranking_dias(vendas_de_exemplo):
    """Testa o cálculo do ranking de dias mais movimentados."""
    ranking = calcular_ranking_dias(vendas_de_exemplo)
    
    assert ranking is not None
    assert len(ranking) == 3
    assert ranking[0] == ("Wednesday", 250.0) # Dia mais forte
    assert ranking[1] == ("Tuesday", 200.0) # 150 + 50
    assert ranking[2] == ("Thursday", 0.0)

def test_calcular_lucro_por_produto(vendas_de_exemplo, produtos_de_exemplo):
    """Testa o cálculo de lucro por produto."""
    lucro = calcular_lucro_por_produto(vendas_de_exemplo, produtos_de_exemplo)

    assert lucro is not None
    assert len(lucro) == 2
    assert lucro[0] == ("Chopp Pilsen", 345.0) # 125 + 220
    assert lucro[1] == ("Chopp IPA", 38.0)
