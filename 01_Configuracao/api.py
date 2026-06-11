# --- SISTEMA E UTILITÁRIOS ---
import os
import uuid
import bcrypt
import asyncio
import warnings
import urllib
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# --- GOOGLE SHEETS ---
# Importação opcional — se não instalado, SHEETS_DISPONIVEL = False
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_DISPONIVEL = True
except ImportError:
    SHEETS_DISPONIVEL = False

# --- API (FASTAPI) ---
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from collections import deque

# --- BANCO DE DADOS ---
from sqlalchemy import create_engine, text

# override=True garante que o .env tem prioridade sobre variáveis já definidas no Windows.
load_dotenv(override=True)

# ======================================================
# ⚙️  MODO DO BANCO
# ======================================================
#DB_MODE so verfica qual sql vai usar
DB_MODE = os.getenv("DB_MODE", "mysql").strip().lower()

# ======================================================
# 🗄️  ENGINE DO BANCO
# ======================================================
_engine_error: str = ""

# cria uma conexao com banco baseado em DB_MODE
def criar_engine():

    #conexao com mySQL
    if DB_MODE == "mysql":
        url = os.getenv("MYSQL_URL")
        if not url:
            raise RuntimeError("MYSQL_URL não definida no .env")
        return create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)

    #conexao com SQL server
    elif DB_MODE == "sqlserver":
        server = os.getenv("SQLSERVER_SERVER", r".\SQLEXPRESS")
        db     = os.getenv("SQLSERVER_DB", "GJP")
        user   = os.getenv("SQLSERVER_USER", "")
        pwd    = os.getenv("SQLSERVER_PASS", "")

        #sem usuario: auteticação windows (máquina da já está logada)
        if not user:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={db};Trusted_Connection=yes;"
            )
        #com usuário: autenticação SQL com login e senha
        else:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={db};"
                f"UID={user};PWD={pwd};"
            )

        params = urllib.parse.quote_plus(conn_str)
        return create_engine(
            f"mssql+pyodbc:///?odbc_connect={params}",
            connect_args={"timeout": 5},
            pool_pre_ping=True
        )

    raise RuntimeError(f"DB_MODE inválido: '{DB_MODE}'. Use 'mysql' ou 'sqlserver'.")


try:
    engine = criar_engine() #tenta conectar
    print(f"✅ Banco conectado: {DB_MODE.upper()}")
except Exception as e:
    engine = None #se falhar, API sobe mesmo assim mas sem banco
    _engine_error = str(e) #guarda o erro pra mostrar no /status
    print(f"❌ Falha ao conectar banco: {e}")


# ======================================================
# 🔀  HELPER: SQL COMPATÍVEL COM AMBOS OS BANCOS
# ======================================================
def sql(mysql_q: str, ss_q: str) -> str:
    #retorna a query correta para cada tipo sql
    return mysql_q if DB_MODE == "mysql" else ss_q


# ======================================================
# 📝  QUERIES SQL
# ======================================================

#resumo: as queries SQL são os comandos pré-definidos que a API executa no banco dependendo da operação solicitada

# — Dispositivos —
Q_INSERT_DISPOSITIVO = (
    "INSERT INTO dispositivos (mac_address, local_disp) VALUES (:m, :l)"
)
Q_SELECT_DISPOSITIVO = (
    "SELECT id_dispositivo FROM dispositivos WHERE mac_address = :m"
)
Q_UPDATE_ULTIMA_CONEXAO = sql(
    "UPDATE dispositivos SET ultima_conexao = NOW() WHERE id_dispositivo = :id",
    "UPDATE dispositivos SET ultima_conexao = GETDATE() WHERE id_dispositivo = :id"
)

# — Leituras —
Q_INSERT_LEITURA = sql(
    """INSERT INTO leituras
       (id_dispositivo, temperatura, umidade, potenciometro, rotacao, data_hora)
       VALUES (:id, :t, :u, :pot, :rot, NOW())""",
    """INSERT INTO leituras
       (id_dispositivo, temperatura, umidade, potenciometro, rotacao, data_hora)
       VALUES (:id, :t, :u, :pot, :rot, GETDATE())"""
)

# — Alertas —
Q_INSERT_ALERTA = sql(
    "INSERT INTO alertas_logs (nivel, mensagem, wifi_rssi, data_hora) VALUES (:nivel, :msg, :rssi, NOW())",
    "INSERT INTO alertas_logs (nivel, mensagem, wifi_rssi, data_hora) VALUES (:nivel, :msg, :rssi, GETDATE())"
)

# — Logs de acesso —
Q_INSERT_LOG_ACESSO = sql(
    "INSERT INTO logs_acesso (login, sucesso, ip_origem, data_hora) VALUES (:login, :sucesso, :ip, NOW())",
    "INSERT INTO logs_acesso (login, sucesso, ip_origem, data_hora) VALUES (:login, :sucesso, :ip, GETDATE())"
)
Q_LOGS_ACESSO = sql(
    "SELECT login, sucesso, ip_origem, data_hora FROM logs_acesso ORDER BY data_hora DESC LIMIT :n",
    "SELECT TOP (:n) login, sucesso, ip_origem, data_hora FROM logs_acesso ORDER BY data_hora DESC"
)

# — Usuários —
# apelido incluído nas queries — coluna nullable, retorna NULL se ainda não definido
# bcrypt: busca só pelo login — verificação da senha é feita em Python
Q_LOGIN = "SELECT nome, perfil, apelido, senha FROM usuario WHERE login = :login"
# bcrypt: a senha já chega como hash gerado em Python (:senha_hash), o banco só armazena texto
Q_INSERT_USUARIO = "INSERT INTO usuario (nome, login, senha, perfil) VALUES (:nome, :login, :senha_hash, :perfil)"
Q_LISTAR_USUARIOS = "SELECT id, nome, login, perfil, apelido FROM usuario ORDER BY perfil, nome"
Q_ATUALIZAR_APELIDO = "UPDATE usuario SET apelido = :apelido WHERE login = :login"
Q_DELETAR_USUARIO   = "DELETE FROM usuario WHERE id = :id"
Q_BUSCAR_USUARIO_ID = "SELECT login, perfil FROM usuario WHERE id = :id"


# — Dashboard —
Q_LEITURAS_RECENTES = sql(
    """SELECT d.mac_address, l.temperatura, l.umidade, l.data_hora
       FROM leituras l
       JOIN dispositivos d ON l.id_dispositivo = d.id_dispositivo
       ORDER BY l.data_hora DESC LIMIT :n""",
    """SELECT TOP (:n) d.mac_address, l.temperatura, l.umidade, l.data_hora
       FROM leituras l
       JOIN dispositivos d ON l.id_dispositivo = d.id_dispositivo
       ORDER BY l.data_hora DESC"""
)
Q_ALERTAS_RECENTES = sql(
    "SELECT nivel, mensagem, wifi_rssi, data_hora FROM alertas_logs ORDER BY data_hora DESC LIMIT :n",
    "SELECT TOP (:n) nivel, mensagem, wifi_rssi, data_hora FROM alertas_logs ORDER BY data_hora DESC"
)
Q_DISPOSITIVOS = "SELECT id_dispositivo, mac_address, local_disp, ultima_conexao FROM dispositivos"


# ======================================================
# 📊  GOOGLE SHEETS
# ======================================================

# defenie o cabeçalho
CABECALHOS = {
    "leituras": ["Data/Hora", "Dispositivo", "Temperatura (°C)", "Umidade (%)", "Status"],
    "alertas":  ["Data/Hora", "Nível", "Mensagem", "RSSI"],
    "usuarios":    ["Data/Hora", "Nome", "Login", "Perfil"],
    "logs_acesso": ["Data/Hora", "Login", "Sucesso", "IP"]
}

# CORREÇÃO: inicializar como None ANTES do bloco condicional.
# Sem isso, qualquer rota que referencie aba_leituras antes do Sheets conectar
# causa NameError porque a variável nunca foi declarada no escopo global.

#iniciar como None
aba_leituras    = None
aba_alertas     = None
aba_usuarios    = None
aba_logs_acesso = None

def _garantir_cabecalho(aba, cabecalho_esperado):
    # Verifica se o cabeçalho existe, se não, insere
    try:
        primeira_linha = aba.row_values(1)
        if primeira_linha != cabecalho_esperado:
            aba.insert_row(cabecalho_esperado, index=1)
            print(f"📋 Cabeçalho configurado na aba '{aba.title}'")
    except Exception as e:
        print(f"⚠️ Erro ao verificar cabeçalho em '{aba.title}': {e}")

def conectar_google_sheets():
    #Faz a conexão inicial e retorna as abas prontas para uso
    if not SHEETS_DISPONIVEL:
        print("⚠️  gspread não instalado — Google Sheets desativado.")
        return None
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = os.getenv("GOOGLE_CREDS_FILE", "credenciais.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        gclient = gspread.authorize(creds)
        planilha_nome = os.getenv("GOOGLE_SHEET_NAME", "Planilha de dados")
        planilha = gclient.open(planilha_nome)
        abas = {}
        for nome_aba, cabecalho in CABECALHOS.items():
            aba = planilha.worksheet(nome_aba)
            _garantir_cabecalho(aba, cabecalho)
            abas[nome_aba] = aba
        print("✅ Google Sheets conectado.")
        return abas
    except Exception as e:
        print(f"❌ Erro Google Sheets: {e}")
        return None

# organiza as abas da planilha
dict_abas = conectar_google_sheets()

if dict_abas:
    aba_leituras    = dict_abas.get("leituras")
    aba_alertas     = dict_abas.get("alertas")
    aba_usuarios    = dict_abas.get("usuarios")
    aba_logs_acesso = dict_abas.get("logs_acesso")


# ======================================================
# 🔐  SISTEMA DE SESSÃO
# ======================================================
sessoes: dict[str, dict] = {}

#cria um UUID/token para sessão que o usuario fez
def criar_sessao(nome: str, perfil: str, login: str, apelido: str | None) -> str:
    token = str(uuid.uuid4())
    sessoes[token] = {"nome": nome, "perfil": perfil, "login": login, "apelido": apelido}
    return token

# recebe o token e verifica se ele existe na sessão ativa
def obter_sessao(x_session: str = Header(None)) -> dict:
    if not x_session or x_session not in sessoes:
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login novamente.")
    return sessoes[x_session]

#verfica o perfil do usuario se ele tem permissão
def exigir_perfil(*perfis_permitidos: str):
    def verificar(sessao: dict = Depends(obter_sessao)):
        if sessao["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Perfis permitidos: {list(perfis_permitidos)}"
            )
        return sessao
    return verificar

# Helpers de hierarquia para não repetir listas em todo lugar
PERFIS_SUPERVISOR_ACIMA = ("Supervisor", "Admin", "Dev") # perfis com acesso de supervisor ou acima
PERFIS_ADMIN_ACIMA      = ("Admin", "Dev")               # perfis com acesso de admin ou acima
PERFIS_DEV_APENAS       = ("Dev",)                       # acesso exclusivo do dev
PERFIS_TODOS            = ("Operador", "Supervisor", "Admin", "Dev") # qualquer perfil logado


# ======================================================
# 🛠️  HELPERS
# ======================================================

# funções de apoio: salvam dados no banco e no Sheets, e monitoram os arduinos

def salvar_alerta(nivel: str, mensagem: str, rssi: int = 0):
    # Salva alerta no banco e no Sheets. Falha silenciosamente em ambos
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(text(Q_INSERT_ALERTA), {"nivel": nivel, "msg": mensagem, "rssi": rssi})
                conn.commit()
        except Exception as e:
            print(f"⚠️  Erro ao salvar alerta no banco: {e}")
    if aba_alertas:
        try:
            aba_alertas.append_row([agora_str, nivel, mensagem, f"{rssi} dBm"])
        except Exception as e:
            print(f"⚠️  Erro ao salvar alerta no Sheets: {e}")


def registrar_acesso(login_tentativa: str, sucesso: bool, ip: str):
    
    #Registra tentativa de login na tabela logs_acesso e no Sheets.
    #Falha silenciosamente para não bloquear o fluxo de login.

    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    if engine:
        try:
            with engine.connect() as conn:
                conn.execute(
                    text(Q_INSERT_LOG_ACESSO),
                    {"login": login_tentativa, "sucesso": 1 if sucesso else 0, "ip": ip}
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️  Erro ao registrar log de acesso: {e}")
    if aba_logs_acesso:
        try:
            aba_logs_acesso.append_row([
                agora_str,
                login_tentativa,
                "Sim" if sucesso else "Não",
                ip
            ])
        except Exception as e:
            print(f"⚠️  Erro ao gravar log de acesso no Sheets: {e}")


async def monitorar_conexoes():
    
    #verifica a cada 5 segundos se algum Arduino parou de responder.
    #Se um dispositivo ficar mais de 30s sem contato e estava online gera alerta.
    
    while True:
        try:
            agora = datetime.now()
            for mac, info in list(ultimos_contatos.items()):
                tempo_sem_contato = (agora - info["horario"]).total_seconds()
                if tempo_sem_contato > 30 and info["status"] == "online":
                    salvar_alerta("ALERTA", f"Arduino '{mac}' parou de responder!")
                    ultimos_contatos[mac]["status"] = "offline"
                    _log(f"❌ ALERTA: Arduino {mac} offline")
        except Exception as e:
            print(f"⚠️ Erro no monitoramento de conexões: {e}")
        await asyncio.sleep(5)


# ======================================================
# 🔁  LIFECYCLE
# ======================================================

# inicializa a API e inicia o monitoramento de conexões em segundo plano
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(monitorar_conexoes())
    _log("🔍 Monitoramento de conexões iniciado.")
    yield


# ======================================================
# 🚀  FASTAPI
# ======================================================

# inicializa a API, configura CORS, carrega o token e prepara o buffer de logs

app = FastAPI(title="API IoT - SENAI", version="3.4.2", lifespan=lifespan)

#configura o CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #define o domínio do site
    allow_methods=["*"],
    allow_headers=["*"],
)

'''o CORS está aberto porque a API roda em rede local. Em produção na internet, 
restringiríamos o allow_origins para aceitar só do domínio do nosso site.'''

#carrega o token do arduino do .env
API_TOKEN  = os.getenv("API_TOKEN")

#guarda o último contato de cada Arduino para o monitoramento detectar quedas
ultimos_contatos: dict = {}

# guarda as últimas 500 mensagens do terminal para exibir na rota /terminal/logs
_log_buffer: deque = deque(maxlen=500)
_log_counter: int  = 0

#grava a mensagem no buffer
def _log(msg: str):
    global _log_counter
    _log_counter += 1
    ts = datetime.now().strftime("%H:%M:%S")
    _log_buffer.append({"id": _log_counter, "ts": ts, "msg": msg})
    print(msg)


# ======================================================
# 📦  MODELOS PYDANTIC
# ======================================================

# define o formato e os tipos esperados dos dados recebidos pela API

class Sensores(BaseModel):
    temperatura: float
    umidade: float
    rotacao: int = 0
    potenciometro: int = 0

class Entradas(BaseModel):
    botao1: bool = False
    botao2: bool = False
    ir_recebido: bool = False

class ESPPayload(BaseModel):
    device: str
    timestamp_ms: int
    sensores: Sensores
    entradas: Entradas
    status: str = "ok"
    wifi_rssi: int = 0

class NovoUsuario(BaseModel):
    nome:   str = Field(min_length=1, max_length=100)
    login:  str = Field(min_length=3, max_length=50)
    senha:  str = Field(min_length=4, max_length=128)
    perfil: str = Field(min_length=1, max_length=20)

class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=128)

class AtualizarPerfil(BaseModel):
    apelido: str = Field(max_length=80)


# ======================================================
# 🛣️  ROTAS PÚBLICAS
# ======================================================

#retorna a data e hora atual formatado
@app.get("/hora")
async def fornecer_hora():
    return {"datahora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

#retorna o estado geral da API
@app.get("/status")
async def status_api():
    return {
        "api":              "online",
        "versao":           "3.4.2",
        "banco":            DB_MODE,
        "banco_conectado":  engine is not None,
        "banco_erro":       _engine_error if engine is None else None,
        "sheets_conectado": aba_leituras is not None,
    }


@app.post("/login")
async def login(req: LoginRequest, request: Request):
    """
    Autentica o usuário e registra a tentativa em logs_acesso.
    Retorna apelido além de nome/perfil/token — o dashboard exibe o apelido se definido.
    """
    #pega o IP de quem esta tentando logar
    ip = request.client.host if request.client else "desconhecido"

    #mostra se o banco esta off
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

    # execute Q_login e busca o usuario pelo login
    try:
        with engine.connect() as conn:
            res = conn.execute(
                text(Q_LOGIN),
                {"login": req.login}
            ).fetchone()

        # se achar o usuario, verfica a senha com bcrypy
        if res:
            nome, perfil, apelido, senha_hash = res[0], res[1], res[2], res[3]
            senha_correta = bcrypt.checkpw(req.senha.encode(), senha_hash.encode())
        else:
            senha_correta = False

        #cria a sessão se der tudo certo
        if res and senha_correta:
            #retorna o token
            token = criar_sessao(nome, perfil, req.login, apelido)
            #registra aecesso como suscesso
            registrar_acesso(req.login, sucesso=True, ip=ip)
            _log(f"✅ Login: '{req.login}' ({perfil}) — IP: {ip}")
            return {
                "nome":          nome,
                "perfil":        perfil,
                "apelido":       apelido or "",
                "session_token": token
            }
        # parte se a sessão der errado
        registrar_acesso(req.login, sucesso=False, ip=ip)
        _log(f"⚠️  Login falhou: '{req.login}' — IP: {ip}")
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao autenticar")

# remove o token da sessão ativa, impedindo qualquer acesso futuro com ele
@app.post("/logout")
async def logout(x_session: str = Header(None)):
    if x_session and x_session in sessoes:
        del sessoes[x_session]
    return {"status": "deslogado"}


# ======================================================
# 🛣️  ROTA DO ARDUINO
# ======================================================

@app.post("/dados")
#valia se o token esta correto
async def receber_dados(payload: ESPPayload, x_token: str = Header(None)):
    if x_token != API_TOKEN:
        #se der erro, nem continua e salva o alerta
        salvar_alerta("ERRO", f"Token inválido recebido de: {payload.device}", payload.wifi_rssi)
        raise HTTPException(status_code=401, detail="Token inválido")

    #se o banco tiver off, vai dá erro 503 "Banco indisponível"
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

    #pega os dados o arduino enviou e coloca em variaveis seperados pra usar depois
    agora     = datetime.now()
    agora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
    mac       = payload.device
    temp      = payload.sensores.temperatura
    umid      = payload.sensores.umidade
    pot       = payload.sensores.potenciometro
    rot       = payload.sensores.rotacao
    id_disp   = None
    st_banco  = "⚪ Falhou"
    st_sheets = "⚪ Desativado"

    
    try:
        with engine.connect() as conn:
            #se dispositivo ja existe, apenas continua
            res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            #se não, cadastra novo
            if not res:
                conn.execute(text(Q_INSERT_DISPOSITIVO), {"m": mac, "l": "Laboratorio SENAI"})
                conn.commit()
                res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            # salva as leituras
            id_disp = res[0]
            conn.execute(text(Q_INSERT_LEITURA), {"id": id_disp, "t": temp, "u": umid, "pot": pot, "rot": rot})
            conn.execute(text(Q_UPDATE_ULTIMA_CONEXAO), {"id": id_disp})
            conn.commit()
            st_banco = "✅ Sucesso"
    except Exception as e:
        print(f"⚠️  Erro no banco ao receber dados: {e}")

    #salvar no google sheets
    if aba_leituras:
        try:
            aba_leituras.append_row([agora_str, mac, temp, umid, payload.wifi_rssi])
            st_sheets = "✅ Sucesso"
        except Exception as e:
            st_sheets = f"⚠️  {e}" # mostra qual é o erro o {e}
    
    # verfique se o arduino voltou online
    if mac in ultimos_contatos and ultimos_contatos[mac]["status"] == "offline":
        salvar_alerta("INFO", f"Arduino {mac} voltou a operar.", payload.wifi_rssi)

    # aqui atualiza estado do arduino em memoria
    ultimos_contatos[mac] = {
        "id": id_disp, "local": "Laboratorio SENAI",
        "horario": agora, "status": "online",
        "temperatura": temp, "umidade": umid, "rssi": payload.wifi_rssi,
    }

    _log(f"📡 Dados | {mac} | {temp}°C {umid}% {payload.wifi_rssi}dBm | Banco:{st_banco} Sheets:{st_sheets}")

    # retorna confirmação
    return {"status": "recebido", "id": id_disp}


# ======================================================
# 🛣️  ROTAS DO DASHBOARD
# ======================================================
# ela ler a memoria (ultimo_contato), pega o dispositivo com horario mais recente e retorna status, temperatura e etc, para atualizar mais rapido possivel.
@app.get("/dados_recentes")
async def dados_recentes(sessao: dict = Depends(obter_sessao)):
    if not ultimos_contatos:
        return {"online": False}
    ultimo = max(ultimos_contatos.values(), key=lambda x: x["horario"])
    return {
        "online":      ultimo["status"] == "online",
        "temperatura": ultimo.get("temperatura", 0),
        "umidade":     ultimo.get("umidade", 0),
        "rssi":        ultimo.get("rssi", 0),
        "horario":     ultimo["horario"].strftime("%d/%m/%Y %H:%M:%S"),
    }


@app.get("/tabela/leituras")
# execute Q_LEITURAS_RECENTES no banco e retorna as ultimas 20 leituras formatadas.
async def tabela_leituras(n: int = 20, sessao: dict = Depends(obter_sessao)):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_LEITURAS_RECENTES), {"n": n}).fetchall()
        return [
            {"mac": r[0], "temperatura": float(r[1]), "umidade": float(r[2]),
             "data_hora": r[3].strftime("%d/%m/%Y %H:%M:%S")}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# mesma logica da tabela leituras.
@app.get("/tabela/alertas")
async def tabela_alertas(
    n: int = 20,
    sessao: dict = Depends(exigir_perfil(*PERFIS_SUPERVISOR_ACIMA))
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_ALERTAS_RECENTES), {"n": n}).fetchall()
        return [
            {"nivel": r[0], "mensagem": r[1], "rssi": r[2],
             "data_hora": r[3].strftime("%d/%m/%Y %H:%M:%S")}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tabela/usuarios")
#lista todos os usuarios cadastrados, supervisor ou acima pode ver
async def tabela_usuarios(
    sessao: dict = Depends(exigir_perfil(*PERFIS_SUPERVISOR_ACIMA))
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_LISTAR_USUARIOS)).fetchall()
        return [{"id": r[0], "nome": r[1], "login": r[2], "perfil": r[3], "apelido": r[4] or ""} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# lista todos os arduinos cadasrados com id, mac, local e ultima conexao
@app.get("/tabela/dispositivos")
async def tabela_dispositivos(
    sessao: dict = Depends(exigir_perfil(*PERFIS_SUPERVISOR_ACIMA))
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_DISPOSITIVOS)).fetchall()
        return [
            {"id": r[0], "mac": r[1], "local": r[2],
             # se nunca conectou, mostra '-' no lugar da data. é uma proteção se o arduino for cadastro manual no banco
             "ultima_conexao": r[3].strftime("%d/%m/%Y %H:%M:%S") if r[3] else "—"}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# lista tentativas de login com ip, sucesso ou falha e horario.
@app.get("/tabela/logs_acesso")
async def tabela_logs_acesso(
    n: int = 50,
    # apenas os cargos admin e dev pode ter acesso
    sessao: dict = Depends(exigir_perfil(*PERFIS_ADMIN_ACIMA))
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_LOGS_ACESSO), {"n": n}).fetchall()
        return [
            {
                "login":     r[0],
                "sucesso":   bool(r[1]),
                "ip_origem": r[2] or "—",
                "data_hora": r[3].strftime("%d/%m/%Y %H:%M:%S")
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# cadastra novos usuarios
@app.post("/cadastrar_usuario")
async def cadastrar_usuario(
    usuario: NovoUsuario,
    # apenas os cargos supervisor ou cima pode ter acesso
    sessao: dict = Depends(exigir_perfil(*PERFIS_SUPERVISOR_ACIMA))
):
    perfis_validos = {"Operador", "Supervisor", "Admin", "Dev"}
    if usuario.perfil not in perfis_validos:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {perfis_validos}")

    # Regras de quem pode criar quem:
    # Supervisor: só Operador e Supervisor
    # Admin: Operador, Supervisor, Admin
    # Dev: pode criar qualquer um incluindo Dev
    perfil_quem_cria = sessao["perfil"]
    if perfil_quem_cria == "Supervisor" and usuario.perfil in ("Admin", "Dev"):
        raise HTTPException(status_code=403, detail="Supervisores só podem criar Operadores e Supervisores.")
    if perfil_quem_cria == "Admin" and usuario.perfil == "Dev":
        raise HTTPException(status_code=403, detail="Apenas Dev pode criar outro Dev.")

    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

    try:
        # bcrypt: gera o hash da senha antes de salvar, o banco nunca vê a senha em texto
        senha_hash = bcrypt.hashpw(usuario.senha.encode(), bcrypt.gensalt()).decode()

        #salva no banco
        with engine.connect() as conn:
            conn.execute(
                text(Q_INSERT_USUARIO),
                {"nome": usuario.nome, "login": usuario.login,
                 "senha_hash": senha_hash, "perfil": usuario.perfil}
            )
            conn.commit()
        
        #salva na planilha
        if aba_usuarios:
            try:
                agora_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                aba_usuarios.append_row([agora_str, usuario.nome, usuario.login, usuario.perfil])
            except Exception:
                pass

        return {
            "status": "sucesso",
            "mensagem": f"Usuário '{usuario.login}' criado com perfil '{usuario.perfil}'."
        }

    # erro de cadastrar
    except Exception as e:
        print(f"Erro ao cadastrar usuário '{usuario.login}': {e}")
        raise HTTPException(status_code=400, detail="Login já existe ou erro no banco.")

# permite os usuarios atualizar o próprio apelido
# ele não escolhe quem atualiza, só o proprio
@app.patch("/perfil")
async def atualizar_perfil(
    dados: AtualizarPerfil,
    sessao: dict = Depends(obter_sessao)
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            conn.execute(
                text(Q_ATUALIZAR_APELIDO),
                {"apelido": dados.apelido.strip() or None, "login": sessao["login"]}
            )
            conn.commit()
        # Atualiza também na sessão em memória para refletir imediatamente
        sessoes_ativas = [k for k, v in sessoes.items() if v.get("login") == sessao["login"]]
        for token in sessoes_ativas:
            sessoes[token]["apelido"] = dados.apelido.strip() or None
        return {"status": "sucesso", "apelido": dados.apelido.strip() or ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ======================================================
# 🗑️  DELETAR USUÁRIO (Dev only)
# ======================================================

#o dev consegue deletar usuarios no proprio site
@app.delete("/usuario/{id_usuario}")
async def deletar_usuario(
    id_usuario: int,
    # apenas dev pode deletar
    sessao: dict = Depends(exigir_perfil(*PERFIS_DEV_APENAS))
):

    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            row = conn.execute(text(Q_BUSCAR_USUARIO_ID), {"id": id_usuario}).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Usuário não encontrado.")
            login_alvo, perfil_alvo = row[0], row[1]
            # aqui evita o dev delata a sua propria conta
            if login_alvo == sessao["login"]:
                raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta.")
            conn.execute(text(Q_DELETAR_USUARIO), {"id": id_usuario})
            conn.commit()
        _log(f"🗑️  Usuário '{login_alvo}' ({perfil_alvo}) deletado por Dev '{sessao['login']}'")
        return {"status": "sucesso", "mensagem": f"Usuário '{login_alvo}' removido."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# 📟  TERMINAL DE LOGS (Dev only)
# ======================================================

# uma aba para dev ver o terminal no site
@app.get("/terminal/logs")
async def terminal_logs(
    desde: int = 0,
    # apenas dev pode ver a aba
    sessao: dict = Depends(exigir_perfil(*PERFIS_DEV_APENAS))
):

    linhas = [l for l in _log_buffer if l["id"] > desde]
    return {"linhas": linhas}

# ======================================================
# 🧹  LIMPEZA DO SHEETS
# ======================================================

# um botão de limpeza da planilha
def _executar_limpeza(manter: int, aba_especifica: str = None) -> dict:
    resultado = {}
    todas_abas = [
        ("leituras",    aba_leituras),
        ("alertas",     aba_alertas),
        ("usuarios",    aba_usuarios),
        ("logs_acesso", aba_logs_acesso)
    ]
    # monta uma lista de abas para limpar
    lista_abas = [(n, a) for n, a in todas_abas if aba_especifica is None or n == aba_especifica]
    for nome, aba in lista_abas:
        # se não conectar na aba, apenas continua sem ela
        if aba is None:
            resultado[nome] = {"status": "aba não conectada"}
            continue
        try:
            # conta quantas linhas tem
            total_linhas = len(aba.col_values(1))
            total_dados  = total_linhas - 1  # desconta cabeçalho

            # se total de linhas for menor ou igual, vai manter igual
            if total_dados <= manter:
                resultado[nome] = {"removidas": 0, "mantidas": total_dados, "status": "sem alteração"}
                continue
            
            #se não vai deletar as linhas mais antigas
            quantidade_para_remover = total_dados - manter
            aba.delete_rows(2, 1 + quantidade_para_remover)
            resultado[nome] = {"removidas": quantidade_para_remover, "mantidas": manter, "status": "ok"}
            print(f"🧹 Sheets '{nome}': {quantidade_para_remover} linhas removidas.")
        except Exception as e:
            print(f"❌ Erro ao limpar aba {nome}: {e}")
            resultado[nome] = {"status": f"erro: {str(e)}"}
    return resultado


@app.post("/sheets/limpar")
#chama a função de cima
async def limpar_sheets(
    manter: int = 100,
    aba: str = None,
    # apenas admin e dev podem delatar os dados
    sessao: dict = Depends(exigir_perfil(*PERFIS_ADMIN_ACIMA))
):
    if not aba_leituras:
        raise HTTPException(status_code=503, detail="Google Sheets não está conectado.")
    if manter < 1:
        raise HTTPException(status_code=400, detail="O parâmetro 'manter' deve ser >= 1.")

    abas_validas = {"leituras", "alertas", "usuarios", "logs_acesso"}
    if aba and aba not in abas_validas:
        raise HTTPException(status_code=400, detail=f"Aba inválida. Use: {abas_validas}")

    resultado = _executar_limpeza(manter, aba_especifica=aba)
    return {"status": "concluido", "detalhes": resultado}


# ======================================================
# 🚀  INICIALIZAÇÃO
# ======================================================
#apenas inicia o api, o famoso "menu inicial"
if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    print("\n" + "="*52)
    print(f"  🚀 API IoT SENAI v3.4.2 — Banco: {DB_MODE.upper()}")
    print("="*52 + "\n")

    config = uvicorn.Config(app, host="0.0.0.0", port=5000, log_level="error")
    srv    = uvicorn.Server(config)

    async def main():
        await srv.serve()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 API finalizada.")