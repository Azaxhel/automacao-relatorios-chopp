import os
import secrets
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, Form, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import Response, HTMLResponse
from sqlmodel import Session, select
from app.database import engine, init_db # Importa o engine e a função init_db
from app.models import Venda, Produto, MovimentoEstoque # Importa os modelos Venda, Produto e MovimentoEstoque
from datetime import date, datetime # Importa datetime para MovimentoEstoque
from collections import Counter
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# DEBUG: Confirma se as variáveis de ambiente do formulário foram carregadas
print(f"--> Usuário do .env: {os.getenv('FORM_USER')}")
print(f"--> Senha do .env: {os.getenv('FORM_PASSWORD')}")

app = FastAPI(title="API Trailer de Chopp")

@app.on_event("startup")
def on_startup():
    init_db()

# --- Configuração de Segurança ---

# Obtém o Auth Token do Twilio das variáveis de ambiente
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# Credenciais para o formulário web
security = HTTPBasic()
FORM_USER = os.getenv("FORM_USER")
FORM_PASSWORD = os.getenv("FORM_PASSWORD")

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Valida as credenciais do usuário para o formulário.
    """
    correct_user = secrets.compare_digest(credentials.username, FORM_USER)
    correct_pass = secrets.compare_digest(credentials.password, FORM_PASSWORD)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Endpoints do Formulário Web ---

@app.get("/", response_class=HTMLResponse)
async def get_registration_form(username: str = Depends(get_current_username)):
    """
    Serve a página HTML com o formulário de registro (protegido por senha).
    """
    try:
        with open("app/templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Arquivo de formulário não encontrado.")

@app.post("/registrar_venda", response_class=HTMLResponse)
async def register_venda(
    data: date = Form(...),
    produto_id: int = Form(...),
    total: float = Form(...),
    cartao: float = Form(...),
    dinheiro: float = Form(...),
    pix: float = Form(...),
    custo_func: float = Form(...),
    custo_copos: float = Form(...),
    custo_boleto: float = Form(...),
    username: str = Depends(get_current_username) # Protege o endpoint
):
    """
    Recebe os dados do formulário e salva no banco de dados (protegido por senha).
    """
    with Session(engine) as sess:
        # Busca o produto para obter o volume por barril e o preco_venda_litro
        produto = sess.exec(select(Produto).where(Produto.id == produto_id)).first()
        if not produto:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")

        lucro = total - custo_func - custo_copos - custo_boleto
        nova_venda = Venda(
            data=data,
            produto_id=produto_id,
            total=total,
            cartao=cartao,
            dinheiro=dinheiro,
            pix=pix,
            custo_func=custo_func,
            custo_copos=custo_copos,
            custo_boleto=custo_boleto,
            lucro=lucro, # Adiciona o cálculo do lucro
            dia_semana=data.strftime('%A') # Salva o dia da semana
        )
        sess.add(nova_venda)
        sess.commit()
        sess.refresh(nova_venda)

        # Calcula a quantidade de litros vendidos e a quantidade de barris
        # Arredondamos para cima para garantir que o estoque seja baixado corretamente
        litros_vendidos = total / produto.preco_venda_litro
        barris_baixados = litros_vendidos / produto.volume_litros

        # Registra o movimento de saída por venda
        movimento_saida_venda = MovimentoEstoque(
            produto_id=produto_id,
            tipo_movimento="saida_venda",
            quantidade=barris_baixados, # Pode ser um float, representando barris parciais
            custo_unitario=None, # Não se aplica diretamente aqui
            data_movimento=data
        )
        sess.add(movimento_saida_venda)
        sess.commit()

    return HTMLResponse(content="<h1>Registro salvo com sucesso!</h1><p><a href='/'>Registrar outra venda</a></p>")

# --- Endpoints de Produtos ---

@app.post("/produtos", response_class=HTMLResponse)
async def create_produto(
    nome: str = Form(...),
    preco_venda_barril_fechado: float = Form(...),
    username: str = Depends(get_current_username)
):
    produto = Produto(
        nome=nome,
        preco_venda_litro=20.0, # Valor fixo
        preco_venda_barril_fechado=preco_venda_barril_fechado
    )
    with Session(engine) as sess:
        sess.add(produto)
        sess.commit()
        sess.refresh(produto)
    return HTMLResponse(content=f"<h1>Produto '{produto.nome}' cadastrado com sucesso!</h1><p><a href='/'>Voltar</a></p>")

@app.get("/produtos", response_model=list[Produto])
async def get_produtos(username: str = Depends(get_current_username)):
    with Session(engine) as sess:
        produtos = sess.exec(select(Produto)).all()
    return produtos

# --- Endpoints de Estoque ---

@app.post("/estoque/entrada", response_class=HTMLResponse)
async def register_entrada_estoque(
    produto_id: int = Form(...),
    quantidade: int = Form(...),
    custo_unitario: float = Form(...),
    data_movimento: date = Form(...),
    username: str = Depends(get_current_username)
):
    movimento = MovimentoEstoque(
        produto_id=produto_id,
        tipo_movimento="entrada",
        quantidade=quantidade,
        custo_unitario=custo_unitario,
        data_movimento=data_movimento
    )
    with Session(engine) as sess:
        sess.add(movimento)
        sess.commit()
        sess.refresh(movimento)
    return HTMLResponse(content=f"<h1>Entrada de {quantidade} barril(is) registrada com sucesso!</h1><p><a href='/'>Voltar</a></p>")

@app.post("/estoque/saida_manual", response_class=HTMLResponse)
async def register_saida_manual_estoque(
    produto_id: int = Form(...),
    quantidade: int = Form(...),
    data_movimento: date = Form(...),
    username: str = Depends(get_current_username)
):
    movimento = MovimentoEstoque(
        produto_id=produto_id,
        tipo_movimento="saida_manual",
        quantidade=quantidade,
        custo_unitario=None, # Saída manual não tem custo unitário associado diretamente
        data_movimento=data_movimento
    )
    with Session(engine) as sess:
        sess.add(movimento)
        sess.commit()
        sess.refresh(movimento)
    return HTMLResponse(content=f"<h1>Saída manual de {quantidade} barril(is) registrada com sucesso!</h1><p><a href='/'>Voltar</a></p>")

@app.get("/estoque", response_model=dict)
async def get_estoque_atual(username: str = Depends(get_current_username)):
    with Session(engine) as sess:
        # Calcula o estoque atual por produto
        # Soma as entradas e subtrai as saídas
        # Isso é uma simplificação, um sistema de estoque real seria mais complexo
        # e consideraria o volume em litros, não apenas barris.
        # Por enquanto, vamos considerar a quantidade de barris.

        produtos = sess.exec(select(Produto)).all()
        estoque_info = {}

        for produto in produtos:
            entradas = sess.exec(
                select(MovimentoEstoque.quantidade)
                .where(MovimentoEstoque.produto_id == produto.id, MovimentoEstoque.tipo_movimento == "entrada")
            ).all()
            saidas_manuais = sess.exec(
                select(MovimentoEstoque.quantidade)
                .where(MovimentoEstoque.produto_id == produto.id, MovimentoEstoque.tipo_movimento == "saida_manual")
            ).all()
            
            # TODO: Implementar a baixa automática por vendas (próximo passo)
            # Por enquanto, as vendas não afetam o estoque aqui.

            total_entradas = sum(entradas)
            total_saidas_manuais = sum(saidas_manuais)
            
            estoque_atual = total_entradas - total_saidas_manuais
            
            estoque_info[produto.nome] = {
                "quantidade_barris": estoque_atual,
                "volume_litros_total": estoque_atual * produto.volume_litros,
                "preco_venda_litro": produto.preco_venda_litro,
                "preco_venda_barril_fechado": produto.preco_venda_barril_fechado
            }
    return estoque_info

# --- Lógica de Relatórios ---

def get_report_data(inicio: date, fim: date):
    """
    Busca e calcula os dados de um relatório para um período específico.
    """
    with Session(engine) as sess:
        vendas = sess.exec(select(Venda).where(Venda.data >= inicio, Venda.data < fim)).all()
    
    if not vendas:
        return None

    # Garante que todos os valores são float, tratando None como 0.0
    receita_bruta = sum(float(v.total or 0.0) for v in vendas)
    gasto_func = sum(float(v.custo_func or 0.0) for v in vendas)
    gasto_copos = sum(float(v.custo_copos or 0.0) for v in vendas)
    gasto_boleto = sum(float(v.custo_boleto or 0.0) for v in vendas)
    
    gasto_total = gasto_func + gasto_copos + gasto_boleto
    receita_liquida = receita_bruta - gasto_total
    
    media_vendas = 0.0
    if len(vendas) > 0:
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
    # O Railway usa X-Forwarded-Proto para indicar o protocolo original (https)
    # e X-Forwarded-Host para o host original.
    original_protocol = request.headers.get("X-Forwarded-Proto", "http")
    original_host = request.headers.get("X-Forwarded-Host", request.url.netloc)
    url = f"{original_protocol}://{original_host}{request.url.path}"
    form_params = await request.form()
    
    # DEBUG: Loga a URL e os parâmetros recebidos
    print(f"DEBUG: Webhook URL recebida: {url}")
    print(f"DEBUG: Webhook Form Params recebidos: {form_params}")

    # Converte os ImmutableMultiDict para um dicionário simples
    form_params_dict = {key: value for key, value in form_params.items()}

    # Obtém a assinatura do Twilio do cabeçalho da requisição
    twilio_signature = request.headers.get('X-Twilio-Signature', '')

    if not validator.validate(url, form_params_dict, twilio_signature):
        # Se a validação falhar, retorna um erro 403 Forbidden
        raise HTTPException(status_code=403, detail="Assinatura Twilio inválida.")

    text = body.strip().lower().replace('relatório', 'relatorio')
    parts = text.split()
    
    resp = MessagingResponse()

    # Lógica de reconhecimento de comandos
    if not parts:
        resp.message("Comando não reconhecido. Digite `ajuda` para ver as opções.")
        return Response(content=str(resp), media_type="application/xml")

    # Tenta comandos de duas palavras primeiro
    if len(parts) >= 2:
        command_two_words = " ".join(parts[:2])
        if command_two_words == "relatorio anual":
            command = command_two_words
        elif command_two_words == "melhores dias":
            command = command_two_words
        else:
            command = parts[0] # Se não for comando de duas palavras, pega a primeira palavra
    else:
        command = parts[0] # Se for apenas uma palavra, pega ela mesma

    if command == "relatorio":
        try:
            mes = int(parts[1])
            ano = int(parts[2])
            
            # Busca relatório do mês atual
            inicio_atual = date(ano, mes, 1)
            fim_atual = date(ano + (mes == 12), (mes % 12) + 1, 1)
            report = get_report_data(inicio_atual, fim_atual)

            if not report:
                resp.message(f"Nenhum registro de vendas encontrado para {mes}/{ano}.")
                return Response(content=str(resp), media_type="application/xml")

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

            gastos_totais = report['gasto_funcionarios'] + report['gasto_copos'] + report['gasto_boleto']
            text_reply = (
                f"🧾 Relatório {mes}/{ano}\n"
                f"--------------------------\n"
                f"Receita bruta: R$ {report['receita_bruta']:.2f}\n"
                f"Receita líquida: R$ {report['receita_liquida']:.2f}\n"
                f"Média por dia: R$ {report['media_vendas']:.2f}\n"
                f"--------------------------\n"
                f"Gastos Detalhados:\n"
                f"  - Funcionários: R$ {report['gasto_funcionarios']:.2f}\n"
                f"  - Copos: R$ {report['gasto_copos']:.2f}\n"
                f"  - Boleto: R$ {report['gasto_boleto']:.2f}\n"
                f"Total de Gastos: R$ {gastos_totais:.2f}\n"
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
                # Dicionário para traduzir os dias da semana
                traducao_dias = {
                    'Monday': 'Segunda-feira',
                    'Tuesday': 'Terça-feira',
                    'Wednesday': 'Quarta-feira',
                    'Thursday': 'Quinta-feira',
                    'Friday': 'Sexta-feira',
                    'Saturday': 'Sábado',
                    'Sunday': 'Domingo'
                }
                reply_lines = [f"🏆 Melhores Dias de {mes}/{ano} 🏆"]
                for i, (dia, total) in enumerate(ranking):
                    dia_traduzido = traducao_dias.get(dia.capitalize(), dia)
                    reply_lines.append(f"{i+1}. {dia_traduzido}: R$ {total:.2f}")
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