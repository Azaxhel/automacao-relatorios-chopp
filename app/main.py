import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import Response, HTMLResponse
from sqlmodel import Session, select
from datetime import date
from collections import Counter
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = FastAPI(title="API Trailer de Chopp")

# Obtém o Auth Token do Twilio das variáveis de ambiente
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Inicializa o validador de requisições do Twilio
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# --- Endpoints do Formulário Web ---

@app.get("/", response_class=HTMLResponse)
async def get_registration_form():
    """
    Serve a página HTML com o formulário de registro.
    """
    try:
        with open("app/templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Arquivo de formulário não encontrado.")

@app.post("/registrar_venda", response_class=HTMLResponse)
async def register_venda(
    data: date = Form(...),
    total: float = Form(...),
    cartao: float = Form(...),
    dinheiro: float = Form(...),
    pix: float = Form(...),
    custo_func: float = Form(...),
    custo_copos: float = Form(...),
    custo_boleto: float = Form(...),
):
    """
    Recebe os dados do formulário e salva no banco de dados.
    """
    nova_venda = Venda(
        data=data,
        total=total,
        cartao=cartao,
        dinheiro=dinheiro,
        pix=pix,
        custo_func=custo_func,
        custo_copos=custo_copos,
        custo_boleto=custo_boleto,
        dia_semana=data.strftime('%A') # Salva o dia da semana
    )
    
    with Session(engine) as sess:
        sess.add(nova_venda)
        sess.commit()

    return HTMLResponse(content="<h1>Registro salvo com sucesso!</h1><p><a href='/'>Registrar outra venda</a></p>")

# --- Lógica de Relatórios ---

def get_report_data(inicio: date, fim: date):
    """
    Busca e calcula os dados de um relatório para um período específico.
    """
    with Session(engine) as sess:
        vendas = sess.exec(select(Venda).where(Venda.data >= inicio, Venda.data < fim)).all()
    
    if not vendas:
        return None

    receita_bruta = sum(v.total for v in vendas)
    gasto_func = sum(v.custo_func for v in vendas)
    gasto_copos = sum(v.custo_copos for v in vendas)
    gasto_boleto = sum(v.custo_boleto for v in vendas)
    gasto_total = gasto_func + gasto_copos + gasto_boleto
    receita_liquida = receita_bruta - gasto_total
    media_vendas = receita_bruta / len(vendas)

    return {
        "receita_bruta": round(receita_bruta, 2),
        "receita_liquida": round(receita_liquida, 2),
        "media_vendas": round(media_vendas, 2),
        "gasto_funcionarios": round(gasto_func, 2),
        "gasto_copos": round(gasto_copos, 2),
        "gasto_boleto": round(gasto_boleto, 2),
        "dias_registrados": len(vendas),
    }

def get_dias_movimento(inicio: date, fim: date):
    """
    Busca e calcula os dias da semana mais lucrativos em um período.
    """
    with Session(engine) as sess:
        vendas = sess.exec(select(Venda.dia_semana, Venda.total).where(Venda.data >= inicio, Venda.data < fim)).all()
    
    if not vendas:
        return None

    faturamento_por_dia = Counter()
    for dia_semana, total in vendas:
        if dia_semana:
            faturamento_por_dia[dia_semana] += total
    
    return faturamento_por_dia.most_common()

# --- Webhook do WhatsApp ---

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, body: str = Form(..., alias="Body")):
    """
    Webhook para receber mensagens WhatsApp via Twilio.
    """
    # Validação da requisição do Twilio
    # O Twilio envia o URL completo da requisição no cabeçalho 'X-Twilio-Signature'
    # e os parâmetros do formulário no corpo da requisição.
    # Precisamos reconstruir o URL e os parâmetros para validar.
    url = str(request.url)
    form_params = await request.form()
    
    # Converte os ImmutableMultiDict para um dicionário simples
    form_params_dict = {key: value for key, value in form_params.items()}

    # Obtém a assinatura do Twilio do cabeçalho da requisição
    twilio_signature = request.headers.get('X-Twilio-Signature', '')

    if not validator.validate(url, form_params_dict, twilio_signature):
        # Se a validação falhar, retorna um erro 403 Forbidden
        raise HTTPException(status_code=403, detail="Assinatura Twilio inválida.")

    text = body.strip().lower().replace('relatório', 'relatorio')
    parts = text.split()
    command = " ".join(parts[:2]) if len(parts) > 1 else parts[0] if parts else ""
    
    resp = MessagingResponse()

    if command == "relatorio":
        try:
            mes = int(parts[1])
            ano = int(parts[2])
            
            # Busca relatório do mês atual
            inicio_atual = date(ano, mes, 1)
            fim_atual = date(ano + (mes == 12), (mes % 12) + 1, 1)
            report = get_report_data(inicio_atual, fim_atual)

            if not report:
                raise HTTPException(status_code=404, detail=f"Nenhum registro para {mes}/{ano}")

            # Lógica para tendência
            mes_anterior = mes - 1 if mes > 1 else 12
            ano_anterior = ano if mes > 1 else ano - 1
            inicio_anterior = date(ano_anterior, mes_anterior, 1)
            report_anterior = get_report_data(inicio_anterior, inicio_atual)

            tendencia_str = ""
            if report_anterior:
                rec_liq_atual = report['receita_liquida']
                rec_liq_anterior = report_anterior['receita_liquida']
                if rec_liq_anterior > 0:
                    variacao = (rec_liq_atual / rec_liq_anterior) - 1
                    tendencia_str = f"\n📈 Tendência: {variacao:.2%} em relação ao mês anterior."
                else:
                    tendencia_str = "\n📈 Tendência: N/A (mês anterior sem receita)."
            else:
                tendencia_str = "\n📈 Tendência: N/A (sem dados do mês anterior)."

            text_reply = (
                f"🧾 Relatório {mes}/{ano}\n"
                f"--------------------------\n"
                f"Receita bruta: R$ {report['receita_bruta']:.2f}\n"
                f"Receita líquida: R$ {report['receita_liquida']:.2f}\n"
                f"Média por dia: R$ {report['media_vendas']:.2f}\n"
                f"--------------------------\n"
                f"Gastos Totais: R$ {(report['gasto_funcionarios'] + report['gasto_copos'] + report['gasto_boleto']):.2f}\n"
                f"--------------------------\n"
                f"Dias registrados: {report['dias_registrados']}"
                f"{tendencia_str}"
            )
            resp.message(text_reply)

        except (ValueError, IndexError):
            resp.message("Formato inválido. Use: relatorio <mês> <ano>")
        except HTTPException as e:
            resp.message(e.detail)

    elif command == "relatorio anual":
        try:
            ano = int(parts[2])
            inicio = date(ano, 1, 1)
            fim = date(ano + 1, 1, 1)
            report = get_report_data(inicio, fim)

            if not report:
                raise HTTPException(status_code=404, detail=f"Nenhum registro para o ano {ano}")

            text_reply = (
                f"🗓️ Relatório Anual {ano}\n"
                f"--------------------------\n"
                f"Receita bruta: R$ {report['receita_bruta']:.2f}\n"
                f"Receita líquida: R$ {report['receita_liquida']:.2f}\n"
                f"Média por dia: R$ {report['media_vendas']:.2f}\n"
                f"Dias registrados: {report['dias_registrados']}"
            )
            resp.message(text_reply)
        except (ValueError, IndexError):
            resp.message("Formato inválido. Use: relatorio anual <ano>")
        except HTTPException as e:
            resp.message(e.detail)

    elif command == "comparar":
        try:
            mes1, ano1 = int(parts[1]), int(parts[2])
            mes2, ano2 = int(parts[3]), int(parts[4])

            inicio1 = date(ano1, mes1, 1)
            fim1 = date(ano1 + (mes1 == 12), (mes1 % 12) + 1, 1)
            report1 = get_report_data(inicio1, fim1)

            inicio2 = date(ano2, mes2, 1)
            fim2 = date(ano2 + (mes2 == 12), (mes2 % 12) + 1, 1)
            report2 = get_report_data(inicio2, fim2)

            if not report1:
                resp.message(f"Não há dados para o primeiro período ({mes1}/{ano1}) para comparar.")
            elif not report2:
                resp.message(f"Não há dados para o segundo período ({mes2}/{ano2}) para comparar.")
            else:
                rec_liq1, rec_liq2 = report1['receita_liquida'], report2['receita_liquida']
                variacao = f"{((rec_liq2 / rec_liq1) - 1):.2%}" if rec_liq1 > 0 else "N/A"
                
                text_reply = (
                    f"📊 Comparativo: {mes1}/{ano1} vs {mes2}/{ano2}\n"
                    f"--------------------------\n"
                    f"Receita Líquida:\n"
                    f"  - {mes1}/{ano1}: R$ {rec_liq1:.2f}\n"
                    f"  - {mes2}/{ano2}: R$ {rec_liq2:.2f}\n"
                    f"  - Variação: {variacao}"
                )
                resp.message(text_reply)
        except (ValueError, IndexError):
            resp.message("Formato inválido. Use: comparar <m1> <a1> <m2> <a2>")

    elif command == "melhores dias":
        try:
            mes, ano = int(parts[2]), int(parts[3])
            inicio = date(ano, mes, 1)
            fim = date(ano + (mes == 12), (mes % 12) + 1, 1)
            ranking = get_dias_movimento(inicio, fim)

            if not ranking:
                resp.message(f"Não há dados de vendas para {mes}/{ano}.")
            else:
                reply_lines = [f"🏆 Melhores Dias de {mes}/{ano} 🏆"]
                for i, (dia, total) in enumerate(ranking):
                    reply_lines.append(f"{i+1}. {dia.capitalize()}: R$ {total:.2f}")
                resp.message("\n".join(reply_lines))
        except (ValueError, IndexError):
            resp.message("Formato inválido. Use: melhores dias <mês> <ano>")

    elif command == "ajuda":
        text_reply = (
            "Comandos disponíveis:\n"
            "1. `relatorio <mês> <ano>`\n"
            "2. `relatorio anual <ano>`\n"
            "3. `comparar <m1> <a1> <m2> <a2>`\n"
            "4. `melhores dias <mês> <ano>`\n"
            "5. `ajuda`"
        )
        resp.message(text_reply)

    else:
        resp.message("Comando não reconhecido. Digite `ajuda` para ver as opções.")

    return Response(content=str(resp), media_type="application/xml")