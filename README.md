# Bot de Relatórios - Trailer de Chopp 

Este projeto é um bot em Python + FastAPI que processa dados de vendas (em planilhas CSV) e responde automaticamente via WhatsApp com relatórios financeiros, ideal para pequenos negócios.

Tecnologias Usadas
- Python
- FastAPI
- Twilio (WhatsApp)
- Pandas (ETL dos dados)
- SQLite (armazenamento)
- Scripts .bat (automação no Windows)

## Como Funciona?
1. O usuário envia uma mensagem como `relatorio 5 2025` no WhatsApp.
2. O bot processa os dados de vendas daquele mês.
3. Ele responde automaticamente com lucros, gastos e formas de pagamento.

## Segurança:
Por motivos de privacidade, os dados reais não foram incluídos no repositório.

Utilize os arquivos fictícios da pasta `dados_exemplo/` para testes.

## Como Rodar
1. Instale as dependências:
```
pip install -r requirements.txt
```
2. Execute `run_all.bat` no Windows (ou adapte os comandos manualmente).
3. Configure sua conta Twilio para receber as mensagens no WhatsApp.

---

**Este projeto foi desenvolvido para automatizar os relatórios de vendas do trailer de chopp da minha família.**