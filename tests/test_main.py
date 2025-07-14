import pytest
from datetime import date, datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models import Produto, Venda

@patch("app.main.RequestValidator.validate", return_value=True)
def test_get_report_data_calculo_correto(mock_validate, client: TestClient, session: Session):
    produto_teste = Produto(id=1, nome="Chopp Teste", preco_venda_litro=20.0,
                            preco_venda_barril_fechado=500.0, volume_litros=50)
    session.add(produto_teste)
    session.commit()

    vendas = [
        Venda(data=date(2025, 7, 1), produto_id=1, tipo_venda="feira", total=150.0, dia_semana="Tuesday", lucro=125.0),
        Venda(data=date(2025, 7, 2), produto_id=1, tipo_venda="feira", total=250.0, dia_semana="Wednesday", lucro=220.0),
    ]
    session.add_all(vendas)
    session.commit()

    with patch("dateparser.parse") as mock_date:
        mock_date.return_value = datetime(2025, 7, 15)
        response = client.post("/whatsapp/webhook", data={"Body": "relatorio julho 2025"})

    assert response.status_code == 200
    assert "Receita bruta: R$ 400.00" in response.text
    assert "Dias registrados: 2" in response.text

@patch("app.main.RequestValidator.validate", return_value=True)
def test_webhook_relatorio_sem_dados(mock_validate, client: TestClient):
    with patch("dateparser.parse") as mock_date:
        mock_date.return_value = datetime(2025, 8, 15)
        response = client.post("/whatsapp/webhook", data={"Body": "relatorio agosto 2025"})

    assert response.status_code == 200
    assert "Nenhum registro de vendas encontrado para 8/2025" in response.text
