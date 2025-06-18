from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import Response
from sqlmodel import Session, select
from datetime import date
from twilio.twiml.messaging_response import MessagingResponse
from app.database import engine
from app.models import Venda

app = FastAPI(title="API Trailer de Chopp")

@app.get("/relatorio/")
def relatorio_endpoint(
    mes: int = Query(..., ge=1, le=12),
    ano: int = Query(..., ge=2000)
):
    """
    Gera relatório para o mês/ano solicitado.
    """
    # Define período
    try: 
        inicio = date(ano, mes, 1)
    except ValueError:
        raise HTTPException(status_code=400, detail=f'Mês inválido: {mes}')
    fim = date(ano + (mes == 12), (mes % 12) + 1, 1)

    with Session(engine) as sess:
        vendas = sess.exec(select(Venda).where(Venda.data >= inicio, Venda.data < fim)).all()
    
    if not vendas:
        raise HTTPException(status_code=404, detail=f"Nenhum registro para {ano}-{mes:02d}")

    receita_bruta = sum(v.total for v in vendas)
    gasto_func = sum(v.custo_func for v in vendas)
    gasto_copos = sum(v.custo_copos for v in vendas)
    gasto_boleto = sum(v.custo_boleto for v in vendas)
    gasto_total = gasto_func + gasto_copos + gasto_boleto
    receita_liquida = receita_bruta - gasto_total
    media_vendas = receita_bruta / len(vendas)

    return {
        "mes": f"{ano}-{mes:02d}",
        "receita_bruta": round(receita_bruta, 2),
        "receita_liquida": round(receita_liquida, 2),
        "media_vendas": round(media_vendas, 2),
        "gasto_funcionarios": round(gasto_func, 2),
        "gasto_copos": round(gasto_copos, 2),
        "gasto_boleto": round(gasto_boleto, 2),
        "dias_registrados": len(vendas)
    }

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, body: str = Form(..., alias="Body")):
    """
    Webhook para receber mensagens WhatsApp via Twilio.
    """
    text = body.strip().lower()
    parts = text.replace('relatório', 'relatorio').lower().split()

    # tenta extrair mes e ano
    if len(parts) >= 3 and parts[0] == 'relatorio':

        try: 
            mes = int(parts[1])
        except:
            import calendar
            try:
                mes = list(calendar.month_name).index(parts[1].capitalize())
            except ValueError:
                mes=None
        try:
            ano = int(parts[2])
        except ValueError:
            ano = None
    else:
        mes = ano = None

    resp = MessagingResponse()

    if not mes or not ano:
        resp.message("Formato inválido. Use: relatorio <mes> <ano>. Ex: relatorio 5 2025")
        return Response(content=str(resp), media_type="application/xml")
    
    # gerar relatório internamente chamando a função
    try:
        report = relatorio_endpoint(mes=mes, ano=ano)
    except HTTPException as e:
        resp.message(e.detail)
        return Response(content=str(resp), media_type="applicatio/xml")
    
    # formata texto de resposta
    text_reply = (
        f"Relatório {report['mes']}\n"
        f"Receita bruta: R$ {report['receita_bruta']:.2f}\n"
        f"Receita líquida: R$ {report['receita_liquida']:.2f}\n"
        f"Média vendas: R$ {report['media_vendas']:.2f}\n"
        f"Gastos - Func.: R$ {report['gasto_funcionarios']:.2f}\n"
        f"Copos: R$ {report['gasto_copos']:.2f}\n"
        f"Boleto: R$ {report['gasto_boleto']:.2f}\n"
        f"Dias registrados: {report['dias_registrados']}"
    )
    resp.message(text_reply)
    return Response(content=str(resp), media_type="application/xml")
