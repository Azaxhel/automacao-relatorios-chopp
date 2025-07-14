import os
# PASSO 1: Configurar o ambiente de teste ANTES de qualquer importação da aplicação.
# Isso garante que qualquer módulo em 'app' que leia esta variável a verá com o valor de teste.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from datetime import date, datetime
from unittest.mock import patch

# Importar as funções de banco de dados que vamos usar/mockar
from app.database import get_session, create_db_and_tables, init_engine, get_engine # Importamos o engine para verificar

# Importar os modelos para criar dados de teste
from app.models import Venda, Produto

# A importação do app principal é movida para a fixture do cliente
# para garantir que aconteça após a configuração do ambiente.

@pytest.fixture(name="session")
def session_fixture():
    """
    Cria um banco de dados e tabelas em memória para cada sessão de teste.
    """
    # A função init_db() agora usará o engine criado a partir da variável de ambiente
    # que definimos no topo do arquivo.
    init_engine(os.environ['DATABASE_URL'])
    create_db_and_tables()
    
    # Cede uma sessão para o teste ser executado
    with Session(get_engine()) as session:
        yield session
    
    # Limpa o banco de dados após o teste
    SQLModel.metadata.drop_all(get_engine())

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Cria um cliente de teste para a aplicação FastAPI, 
    sobrescrevendo o gerenciamento de sessão para usar o banco de dados de teste.
    """
    # PASSO 2: Importar a aplicação AQUI, depois que o ambiente foi configurado.
    from app.main import app

    def get_session_override():
        """Substitui a dependência get_session para retornar a sessão de teste."""
        yield session

    # Aplicar a substituição da dependência
    app.dependency_overrides[get_session] = get_session_override
    
    # Criar e ceder o cliente de teste
    with TestClient(app) as client:
        yield client
    
    # Limpar a substituição após o teste
    app.dependency_overrides.clear()

# Teste de exemplo (mantido como referência, mas pode ser ajustado)
@patch('app.main.RequestValidator.validate', return_value=True)
def test_whatsapp_webhook_comando_ajuda(mock_validate, client: TestClient):
    """Testa se o comando 'ajuda' retorna a mensagem de ajuda corretamente."""
    response = client.post("/whatsapp/webhook", data={"Body": "ajuda"})
    assert response.status_code == 200
    # O XML escapa os caracteres < e >, então verificamos a versão escapada
    assert "Comandos disponíveis:" in response.text
    assert "Comandos disponíveis:" in response.text

@patch('app.main.RequestValidator.validate', return_value=True)
def test_get_report_data_calculo_correto(mock_validate, client: TestClient, session: Session):
    """Testa se a função get_report_data calcula a receita e os dias corretamente."""
    # Setup: Adicionar dados de teste
    produto_teste = Produto(id=1, nome="Chopp Teste", preco_venda_litro=20.0, preco_venda_barril_fechado=500.0, volume_litros=50)
    session.add(produto_teste)
    session.commit()

    vendas = [
        Venda(data=date(2025, 7, 1), produto_id=1, tipo_venda="feira", total=150.0, dia_semana=date(2025, 7, 1).strftime('%A'), lucro=150.0),
        Venda(data=date(2025, 7, 1), produto_id=1, tipo_venda="feira", total=50.0, dia_semana=date(2025, 7, 1).strftime('%A'), lucro=50.0), # Mesmo dia
        Venda(data=date(2025, 7, 2), produto_id=1, tipo_venda="feira", total=250.0, dia_semana=date(2025, 7, 2).strftime('%A'), lucro=250.0), # Outro dia
    ]
    session.add_all(vendas)
    session.commit()

    # Execução: Chamar o endpoint que usa get_report_data
    # Usamos um dateparser mockado para controlar a data do relatório
    with patch('dateparser.parse') as mock_dateparser:
        mock_dateparser.return_value = datetime(2025, 7, 15) # Simula "relatorio julho 2025"
        response = client.post("/whatsapp/webhook", data={"Body": "relatorio julho 2025"})

    # Verificação
    assert response.status_code == 200
    xml_response = response.text
    assert "Receita bruta: R$ 450.00" in xml_response
    # A lógica de dias registrados no main.py conta vendas, não dias únicos. Se precisar mudar, o teste falhará.
    # Atualizando: A lógica em main.py foi corrigida para contar dias únicos. O teste deve refletir isso.
    # Vamos assumir que a lógica em main.py é `len(set(v.data for v in vendas))`
    assert "Dias registrados: 2" in xml_response
