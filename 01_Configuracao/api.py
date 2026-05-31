"""
API IoT - SENAI v3.3
Correções e adições em relação à v3.2:
  - CORRIGIDO: docstring solta após o yield no lifespan (virou comentário)
  - CORRIGIDO: asyncio importado duas vezes (removida duplicata)
  - RESTAURADO: print de confirmação quando banco conecta com sucesso
  - ADICIONADO: registro de logs_acesso no /login (sucesso e falha)
                Exigência da Etapa 4 — seções 4.2.1 e 4.3.1
  - ADICIONADO: rota GET /tabela/logs_acesso (Admin apenas)
  - ADICIONADO: IP de origem capturado nos logs de acesso
"""

import os
import uuid
import urllib
import asyncio
import warnings
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
import uvicorn
from dotenv import load_dotenv

# Google Sheets — importação opcional.
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_DISPONIVEL = True
except ImportError:
    SHEETS_DISPONIVEL = False

# override=True garante que o .env tem prioridade sobre variáveis já definidas no Windows.
load_dotenv(override=True)

# ======================================================
# ⚙️  MODO DO BANCO
# ======================================================
DB_MODE = os.getenv("DB_MODE", "mysql").strip().lower()

# ======================================================
# 🗄️  ENGINE DO BANCO
# ======================================================
_engine_error: str = ""

def criar_engine():
    """
    Cria a conexão com o banco baseado em DB_MODE.
    MySQL: usa MYSQL_URL do .env.
    SQL Server: detecta autenticação Windows (sem user/pass) ou SQL (com user/pass).
    """
    if DB_MODE == "mysql":
        url = os.getenv("MYSQL_URL")
        if not url:
            raise RuntimeError("MYSQL_URL não definida no .env")
        return create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)

    elif DB_MODE == "sqlserver":
        server = os.getenv("SQLSERVER_SERVER", r".\SQLEXPRESS")
        db     = os.getenv("SQLSERVER_DB", "GJP")
        user   = os.getenv("SQLSERVER_USER", "")
        pwd    = os.getenv("SQLSERVER_PASS", "")

        if not user:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={db};Trusted_Connection=yes;"
            )
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
    engine = criar_engine()
    print(f"✅ Banco conectado: {DB_MODE.upper()}")
except Exception as e:
    engine = None
    _engine_error = str(e)
    print(f"❌ Falha ao conectar banco: {e}")


# ======================================================
# 🔀  HELPER: SQL COMPATÍVEL COM AMBOS OS BANCOS
# ======================================================
def sql(mysql_q: str, ss_q: str) -> str:
    """Retorna a query correta para o banco ativo (MySQL ou SQL Server)."""
    return mysql_q if DB_MODE == "mysql" else ss_q


# ======================================================
# 📝  QUERIES SQL
# ======================================================

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

# — Logs de acesso (Etapa 4 — seção 4.2.1 e 4.3.1) —
# Registra TODA tentativa de login: sucesso (1) e falha (0).
# sucesso é BIT no SQL Server e TINYINT(1) no MySQL — ambos aceitam 0/1 como inteiro.
Q_INSERT_LOG_ACESSO = sql(
    "INSERT INTO logs_acesso (login, sucesso, ip_origem, data_hora) VALUES (:login, :sucesso, :ip, NOW())",
    "INSERT INTO logs_acesso (login, sucesso, ip_origem, data_hora) VALUES (:login, :sucesso, :ip, GETDATE())"
)
Q_LOGS_ACESSO = sql(
    "SELECT login, sucesso, ip_origem, data_hora FROM logs_acesso ORDER BY data_hora DESC LIMIT :n",
    "SELECT TOP (:n) login, sucesso, ip_origem, data_hora FROM logs_acesso ORDER BY data_hora DESC"
)

# — Usuários —
Q_LOGIN = sql(
    "SELECT nome, perfil FROM usuario WHERE login = :login AND senha = AES_ENCRYPT(:senha, :chave)",
    "SELECT nome, perfil FROM usuario WHERE login = :login AND senha = HASHBYTES('SHA2_256', :senha)"
)
Q_INSERT_USUARIO = sql(
    "INSERT INTO usuario (nome, login, senha, perfil) VALUES (:nome, :login, AES_ENCRYPT(:senha, :chave), :perfil)",
    "INSERT INTO usuario (nome, login, senha, perfil) VALUES (:nome, :login, HASHBYTES('SHA2_256', :senha), :perfil)"
)
Q_LISTAR_USUARIOS = "SELECT id, nome, login, perfil FROM usuario ORDER BY perfil, nome"

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
aba_leituras = aba_alertas = aba_usuarios = None

if SHEETS_DISPONIVEL:
    try:
        scope    = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds    = ServiceAccountCredentials.from_json_keyfile_name(
                       os.getenv("GOOGLE_CREDS_FILE", "credenciais.json"), scope)
        gclient  = gspread.authorize(creds)
        planilha = gclient.open(os.getenv("GOOGLE_SHEET_NAME", "Planilha de dados"))
        aba_leituras = planilha.worksheet("leituras")
        aba_alertas  = planilha.worksheet("alertas")
        aba_usuarios = planilha.worksheet("usuarios")
        print("✅ Google Sheets conectado.")
    except Exception as e:
        print(f"⚠️  Sheets indisponível: {e}")


# ======================================================
# 🔐  SISTEMA DE SESSÃO
# ======================================================
sessoes: dict[str, dict] = {}

def criar_sessao(nome: str, perfil: str) -> str:
    token = str(uuid.uuid4())
    sessoes[token] = {"nome": nome, "perfil": perfil}
    return token

def obter_sessao(x_session: str = Header(None)) -> dict:
    if not x_session or x_session not in sessoes:
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login novamente.")
    return sessoes[x_session]

def exigir_perfil(*perfis_permitidos: str):
    def verificar(sessao: dict = Depends(obter_sessao)):
        if sessao["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Perfis permitidos: {list(perfis_permitidos)}"
            )
        return sessao
    return verificar


# ======================================================
# 🛠️  HELPERS
# ======================================================
def salvar_alerta(nivel: str, mensagem: str, rssi: int = 0):
    """Salva alerta no banco e no Sheets. Falha silenciosamente em ambos."""
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
    """
    Registra tentativa de login na tabela logs_acesso.
    Chamada tanto em logins bem-sucedidos quanto em falhas.
    Exigência da Etapa 4 — seções 4.2.1 (registro de acessos) e 4.3.1 (tabela de logs).
    Falha silenciosamente para não bloquear o fluxo de login.
    """
    if not engine:
        return
    try:
        with engine.connect() as conn:
            conn.execute(
                text(Q_INSERT_LOG_ACESSO),
                {"login": login_tentativa, "sucesso": 1 if sucesso else 0, "ip": ip}
            )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Erro ao registrar log de acesso: {e}")


async def monitorar_conexoes():
    """
    Task assíncrona que verifica a cada 5 segundos se algum Arduino parou de responder.
    Se um dispositivo ficar mais de 30s sem contato e estava online → gera alerta.
    O try/except interno garante que um erro pontual não mata o loop inteiro.
    """
    while True:
        try:
            agora = datetime.now()
            for mac, info in list(ultimos_contatos.items()):
                tempo_sem_contato = (agora - info["horario"]).total_seconds()
                if tempo_sem_contato > 30 and info["status"] == "online":
                    salvar_alerta("ALERTA", f"Arduino '{mac}' parou de responder!")
                    ultimos_contatos[mac]["status"] = "offline"
                    print(f"❌ ALERTA: Arduino {mac} offline")
        except Exception as e:
            print(f"⚠️ Erro no monitoramento de conexões: {e}")
        await asyncio.sleep(5)


# ======================================================
# 🔁  LIFECYCLE
# ======================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tudo antes do yield roda no startup
    # Inicia o monitoramento de dispositivos em background
    asyncio.create_task(monitorar_conexoes())
    print("🔍 Monitoramento de conexões iniciado.")
    yield
    # Tudo após o yield rodaria no shutdown (nada necessário por ora)


# ======================================================
# 🚀  FASTAPI
# ======================================================
app = FastAPI(title="API IoT - SENAI", version="3.3", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN  = os.getenv("API_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY_DB")

ultimos_contatos: dict = {}


# ======================================================
# 📦  MODELOS PYDANTIC
# ======================================================
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


# ======================================================
# 🛣️  ROTAS PÚBLICAS
# ======================================================

@app.get("/hora")
async def fornecer_hora():
    return {"datahora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}


@app.get("/status")
async def status_api():
    return {
        "api":             "online",
        "banco":           DB_MODE,
        "banco_conectado": engine is not None,
        "banco_erro":      _engine_error if engine is None else None,
        "sheets_conectado": aba_leituras is not None,
    }


@app.post("/login")
async def login(req: LoginRequest, request: Request):
    """
    Autentica o usuário e registra a tentativa em logs_acesso.
    O IP de origem é capturado para rastreabilidade (Etapa 4, seção 4.2.1).
    """
    ip = request.client.host if request.client else "desconhecido"

    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

    try:
        with engine.connect() as conn:
            res = conn.execute(
                text(Q_LOGIN),
                {"login": req.login, "senha": req.senha, "chave": SECRET_KEY}
            ).fetchone()

        if res:
            token = criar_sessao(res[0], res[1])
            registrar_acesso(req.login, sucesso=True, ip=ip)
            print(f"✅ Login: '{req.login}' ({res[1]}) — IP: {ip}")
            return {"nome": res[0], "perfil": res[1], "session_token": token}

        # Usuário não encontrado ou senha errada
        registrar_acesso(req.login, sucesso=False, ip=ip)
        print(f"⚠️  Login falhou: '{req.login}' — IP: {ip}")
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao autenticar")


@app.post("/logout")
async def logout(x_session: str = Header(None)):
    if x_session and x_session in sessoes:
        del sessoes[x_session]
    return {"status": "deslogado"}


# ======================================================
# 🛣️  ROTA DO ARDUINO
# ======================================================

@app.post("/dados")
async def receber_dados(payload: ESPPayload, x_token: str = Header(None)):
    if x_token != API_TOKEN:
        salvar_alerta("ERRO", f"Token inválido recebido de: {payload.device}", payload.wifi_rssi)
        raise HTTPException(status_code=401, detail="Token inválido")

    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

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
            res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            if not res:
                conn.execute(text(Q_INSERT_DISPOSITIVO), {"m": mac, "l": "Laboratorio SENAI"})
                conn.commit()
                res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            id_disp = res[0]
            conn.execute(text(Q_INSERT_LEITURA), {"id": id_disp, "t": temp, "u": umid, "pot": pot, "rot": rot})
            conn.execute(text(Q_UPDATE_ULTIMA_CONEXAO), {"id": id_disp})
            conn.commit()
            st_banco = "✅ Sucesso"
    except Exception as e:
        print(f"⚠️  Erro no banco ao receber dados: {e}")

    if aba_leituras:
        try:
            aba_leituras.append_row([agora_str, mac, temp, umid, payload.wifi_rssi])
            st_sheets = "✅ Sucesso"
        except Exception as e:
            st_sheets = f"⚠️  {e}"

    if mac in ultimos_contatos and ultimos_contatos[mac]["status"] == "offline":
        salvar_alerta("INFO", f"Arduino {mac} voltou a operar.", payload.wifi_rssi)

    ultimos_contatos[mac] = {
        "id": id_disp, "local": "Laboratorio SENAI",
        "horario": agora, "status": "online",
        "temperatura": temp, "umidade": umid, "rssi": payload.wifi_rssi,
    }

    print(f"\n{'─'*50}")
    print(f"  💾 Banco ({DB_MODE}): {st_banco}  📊 Sheets: {st_sheets}")
    print(f"  🌡️  {temp}°C  💧 {umid}%  📶 {payload.wifi_rssi} dBm  🤖 {mac}")
    print(f"{'─'*50}")

    return {"status": "recebido", "id": id_disp}


# ======================================================
# 🛣️  ROTAS DO DASHBOARD
# ======================================================

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


@app.get("/tabela/alertas")
async def tabela_alertas(
    n: int = 20,
    sessao: dict = Depends(exigir_perfil("Supervisor", "Admin"))
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
async def tabela_usuarios(sessao: dict = Depends(exigir_perfil("Admin"))):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_LISTAR_USUARIOS)).fetchall()
        return [{"id": r[0], "nome": r[1], "login": r[2], "perfil": r[3]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tabela/dispositivos")
async def tabela_dispositivos(
    sessao: dict = Depends(exigir_perfil("Supervisor", "Admin"))
):
    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(Q_DISPOSITIVOS)).fetchall()
        return [
            {"id": r[0], "mac": r[1], "local": r[2],
             "ultima_conexao": r[3].strftime("%d/%m/%Y %H:%M:%S") if r[3] else "—"}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tabela/logs_acesso")
async def tabela_logs_acesso(
    n: int = 50,
    sessao: dict = Depends(exigir_perfil("Admin"))
):
    """
    Retorna histórico de tentativas de login.
    Acesso restrito a Admin — contém IPs e logins tentados.
    Exigência da Etapa 4 — seção 4.2.1 (registro de acessos ao sistema).
    """
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


@app.post("/cadastrar_usuario")
async def cadastrar_usuario(
    usuario: NovoUsuario,
    sessao: dict = Depends(exigir_perfil("Supervisor", "Admin"))
):
    perfis_validos = {"Operador", "Supervisor", "Admin"}
    if usuario.perfil not in perfis_validos:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {perfis_validos}")

    if sessao["perfil"] == "Supervisor" and usuario.perfil == "Admin":
        raise HTTPException(status_code=403, detail="Supervisores não podem criar Admins.")

    if not engine:
        raise HTTPException(status_code=503, detail="Banco indisponível")

    try:
        with engine.connect() as conn:
            conn.execute(
                text(Q_INSERT_USUARIO),
                {"nome": usuario.nome, "login": usuario.login,
                 "senha": usuario.senha, "chave": SECRET_KEY, "perfil": usuario.perfil}
            )
            conn.commit()

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

    except Exception as e:
        print(f"Erro ao cadastrar usuário '{usuario.login}': {e}")
        raise HTTPException(status_code=400, detail="Login já existe ou erro no banco.")


# ======================================================
# 🚀  INICIALIZAÇÃO
# ======================================================
if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    print("\n" + "="*52)
    print(f"  🚀 API IoT SENAI v3.3 — Banco: {DB_MODE.upper()}")
    print("="*52 + "\n")

    config = uvicorn.Config(app, host="0.0.0.0", port=5000, log_level="error")
    srv    = uvicorn.Server(config)

    async def main():
        await srv.serve()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 API finalizada.")