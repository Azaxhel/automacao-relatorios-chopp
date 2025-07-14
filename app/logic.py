from typing import List, Dict, Optional
from app.models import Venda, Produto, MovimentoEstoque
from datetime import date
from collections import Counter

def calcular_relatorio_geral(vendas: List[Venda]) -> Optional[Dict]:
    """
    Calcula os dados de um relatório com base em uma lista de vendas.
    Esta função é pura e não depende de banco de dados.
    """
    if not vendas:
        return None

    receita_bruta = sum(float(v.total or 0.0) for v in vendas if v.tipo_venda != 'boleto')
    gasto_func = sum(float(v.custo_func or 0.0) for v in vendas)
    gasto_copos = sum(float(v.custo_copos or 0.0) for v in vendas)
    gasto_boleto = sum(float(v.custo_boleto or 0.0) for v in vendas)
    
    gasto_total = gasto_func + gasto_copos + gasto_boleto
    receita_liquida = receita_bruta - gasto_total
    
    vendas_validas_para_media = [v for v in vendas if v.tipo_venda != 'boleto']
    media_vendas = 0.0
    if len(vendas_validas_para_media) > 0:
        media_vendas = receita_bruta / len(vendas_validas_para_media)

    return {
        "receita_bruta": round(receita_bruta, 2),
        "receita_liquida": round(receita_liquida, 2),
        "media_vendas": round(media_vendas, 2),
        "gasto_funcionarios": round(gasto_func, 2),
        "gasto_copos": round(gasto_copos, 2),
        "gasto_boleto": round(gasto_boleto, 2),
        "dias_registrados": len(set(v.data for v in vendas if v.tipo_venda != 'boleto')),
    }

def calcular_ranking_dias(vendas: List[Venda]) -> Optional[list]:
    """
    Calcula os dias da semana mais lucrativos com base em uma lista de vendas.
    """
    if not vendas:
        return None

    faturamento_por_dia = Counter()
    for venda in vendas:
        if venda.dia_semana and venda.total is not None:
            faturamento_por_dia[venda.dia_semana] += venda.total
    
    return faturamento_por_dia.most_common()

def calcular_lucro_por_produto(vendas: List[Venda], produtos: List[Produto]) -> Optional[list]:
    """
    Calcula o lucro por produto com base em listas de vendas e produtos.
    """
    if not vendas:
        return None

    produto_map = {p.id: p.nome for p in produtos}
    lucro_por_produto = Counter()
    for venda in vendas:
        if venda.produto_id and venda.lucro is not None and venda.tipo_venda != "boleto":
            if venda.produto_id in produto_map:
                lucro_por_produto[produto_map[venda.produto_id]] += venda.lucro

    return lucro_por_produto.most_common()
