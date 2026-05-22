"""
API IoT - SENAI v3.1
Correções aplicadas em relação à v3:
  - SQL Server: suporte real a autenticação Windows (Trusted_Connection) e usuário/senha
  - potenciometro e rotacao agora são salvos no banco
  - ultima_conexao dos dispositivos é atualizada a cada leitura
  - dados_recentes retorna o dispositivo com leitura mais recente (não o último inserido)
  - cadastrar_usuario agora loga exceções para facilitar debug
  - monitorar_conexoes tem tratamento de erro para não morrer silenciosamente
"""

import os
import uuid
import urllib
import asyncio
import warnings
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import uvicorn
from dotenv import load_dotenv

# Google Sheets — importação opcional.
# Se o pacote não estiver instalado, o sistema continua funcionando sem Sheets.
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    SHEETS_DISPONIVEL = True
except ImportError:
    SHEETS_DISPONIVEL = False

# override=True é crítico: sem ele, variáveis de ambiente já existentes no
# Windows têm prioridade sobre o .env — causava o bug do "Access denied for root".
load_dotenv(override=True)
print("URL LIDA:", os.getenv("MYSQL_URL"))

# ======================================================
# ⚙️  MODO DO BANCO
# ======================================================
# Lê do .env. Se não definido, usa MySQL como padrão.
# Valores válidos: "mysql" ou "sqlserver"
DB_MODE = os.getenv("DB_MODE", "mysql")


# ======================================================
# 🗄️  ENGINE DO BANCO
# ======================================================
def criar_engine():
    """
    Cria a conexão com o banco de dados baseado em DB_MODE.

    Para MySQL: usa a URL completa do .env (mais simples).
    Para SQL Server: detecta automaticamente se deve usar
      - Autenticação Windows (Trusted_Connection=yes) → sem usuário/senha no .env
      - Autenticação SQL (usuário/senha explícitos) → com SQLSERVER_USER e SQLSERVER_PASS

    Por que dois modos para SQL Server?
    No SENAI, o SQL Server Express usa autenticação Windows — o sistema operacional
    já autentica o usuário, então não precisa de senha. Em casa ou em produção,
    normalmente se usa usuário/senha explícitos.
    O código detecta qual usar baseado na presença de SQLSERVER_USER no .env.
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

        # Se não tiver usuário no .env → usa autenticação Windows (modo SENAI)
        # Se tiver usuário → usa autenticação SQL com usuário/senha
        if not user:
            # Autenticação Windows integrada (Trusted_Connection=yes)
            # Funciona no SENAI porque o Windows já sabe quem você é.
            # Requer pyodbc + driver ODBC da Microsoft instalado no sistema.
            # Para verificar os drivers disponíveis, rode:
            #   python -c "import pyodbc; print(pyodbc.drivers())"
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};DATABASE={db};Trusted_Connection=yes;"
            )
        else:
            # Autenticação SQL explícita com usuário e senha
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
    print(f"❌ Falha ao conectar banco: {e}")


# ======================================================
# 🔀  HELPER: SQL COMPATÍVEL COM AMBOS OS BANCOS
# ======================================================
def sql(mysql_q: str, ss_q: str) -> str:
    """
    Retorna a query correta para o banco ativo.
    MySQL e SQL Server têm sintaxes diferentes em vários pontos:
      - NOW()      vs  GETDATE()        (data/hora atual)
      - LIMIT n    vs  TOP n (no SELECT)(limitar resultados)
      - AES_ENCRYPT vs HASHBYTES        (criptografia de senhas)
    Essa função centraliza essa escolha para não espalhar ifs pelo código.
    """
    return mysql_q if DB_MODE == "mysql" else ss_q


# ======================================================
# 📝  QUERIES SQL
# ======================================================

# — Dispositivos (Arduino) —
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
# Corrigido: agora inclui potenciometro e rotacao, que antes eram recebidos mas não salvos.
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
# MySQL usa LIMIT no final; SQL Server usa TOP no início do SELECT.
Q_LEITURAS_RECENTES = sql(
    """SELECT d.mac_address, l.temperatura, l.umidade, l.data_hora
       FROM leituras l
       JOIN dispositivos d ON l.id_dispositivo = d.id_dispositivo
       ORDER BY l.data_hora DESC
       LIMIT :n""",
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
# Funciona assim:
#   1. Usuário faz POST /login com login+senha
#   2. API valida no banco, gera um UUID aleatório (session_token)
#   3. Armazena em memória: sessoes[token] = {nome, perfil}
#   4. Retorna o token para o frontend
#   5. Frontend salva no sessionStorage e manda em todo request como header X-Session
#   6. API valida o header em cada rota protegida via Depends(obter_sessao)
#
# Limitação conhecida e aceita: reiniciar a API apaga todas as sessões.
# Em produção real, sessões ficam num banco ou Redis. Aqui, memória basta.
sessoes: dict[str, dict] = {}

def criar_sessao(nome: str, perfil: str) -> str:
    token = str(uuid.uuid4())
    sessoes[token] = {"nome": nome, "perfil": perfil}
    return token

def obter_sessao(x_session: str = Header(None)) -> dict:
    """
    Dependência do FastAPI: valida o header X-Session e retorna os dados do usuário.
    Usado com Depends(obter_sessao) nas rotas protegidas.
    Se o token não existir ou for inválido, retorna 401.
    """
    if not x_session or x_session not in sessoes:
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login novamente.")
    return sessoes[x_session]

def exigir_perfil(*perfis_permitidos: str):
    """
    Dependência com verificação de perfil.
    Uso: Depends(exigir_perfil("Supervisor", "Admin"))
    Primeiro valida a sessão, depois verifica se o perfil tem permissão.
    Se não tiver, retorna 403 (autenticado, mas sem autorização).
    """
    def verificar(sessao: dict = Depends(obter_sessao)):
        if sessao["perfil"] not in perfis_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado. Perfis permitidos: {list(perfis_permitidos)}"
            )
        return sessao
    return verificar


# ======================================================
# 🚀  FASTAPI
# ======================================================
app = FastAPI(title="API IoT - SENAI", version="3.1")

# CORS: permite que o HTML aberto diretamente no navegador (file://) chame a API.
# allow_origins=["*"] é aceitável em rede local/escola.
# Em produção, trocar pelo endereço real do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN  = os.getenv("API_TOKEN")   # usado pelo Arduino no header X-Token
SECRET_KEY = os.getenv("SECRET_KEY_DB")  # chave AES para senhas no MySQL

# Armazena o último contato de cada dispositivo em memória.
# Chave: MAC address | Valor: dict com horario, temperatura, umidade, rssi, status
ultimos_contatos: dict = {}


# ======================================================
# 📦  MODELOS PYDANTIC
# ======================================================
# Pydantic valida automaticamente o JSON recebido.
# Se o Arduino mandar um campo com tipo errado, a API retorna 422 automaticamente.

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
    nome: str
    login: str
    senha: str
    perfil: str

class LoginRequest(BaseModel):
    login: str
    senha: str


# ======================================================
# 🛠️  HELPERS
# ======================================================
def salvar_alerta(nivel: str, mensagem: str, rssi: int = 0):
    """Salva um alerta no banco e no Sheets. Falha silenciosamente em ambos."""
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

async def monitorar_conexoes():
    """
    Task assíncrona que roda em paralelo com a API.
    A cada 5 segundos, verifica se algum Arduino parou de enviar dados.
    Se um dispositivo ficou mais de 30s sem contato e estava online → gera alerta.

    Por que try/except no loop?
    Tasks assíncronas morrem silenciosamente se lançarem uma exceção.
    O try/except garante que um erro pontual não mate o monitoramento inteiro.
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
# 🛣️  ROTAS PÚBLICAS (sem autenticação)
# ======================================================

@app.get("/hora")
async def fornecer_hora():
    return {"datahora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}


@app.get("/status")
async def status_api():
    return {
        "api": "online",
        "banco": DB_MODE,
        "banco_conectado": engine is not None,
        "sheets_conectado": aba_leituras is not None,
    }


@app.post("/login")
async def login(req: LoginRequest):
    # ─── ATALHO DEV — REMOVER ANTES DE APRESENTAR ───────────────────────────
    if req.login == "admin" and req.senha == "123":
        token = criar_sessao("Desenvolvedor", "Admin")
        return {"nome": "Desenvolvedor", "perfil": "Admin", "session_token": token}
    # ────────────────────────────────────────────────────────────────────────

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
            # Retorna nome, perfil E session_token — o frontend precisa salvar os três
            return {"nome": res[0], "perfil": res[1], "session_token": token}

        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao autenticar")


# ======================================================
# 🛣️  ROTA DO ARDUINO (protegida por API_TOKEN no header X-Token)
# ======================================================

@app.post("/dados")
async def receber_dados(payload: ESPPayload, x_token: str = Header(None)):
    """
    Recebe os dados do Arduino (ESP8266).
    Autenticação: header X-Token com o API_TOKEN do .env.
    Isso é separado do sistema de sessão — o Arduino não faz login,
    ele só manda um token fixo que foi programado nele.
    """
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
            # Verifica se o Arduino já está cadastrado (pela MAC address)
            res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            if not res:
                # Primeiro contato desse Arduino — cadastra automaticamente
                conn.execute(text(Q_INSERT_DISPOSITIVO), {"m": mac, "l": "Laboratorio SENAI"})
                conn.commit()
                res = conn.execute(text(Q_SELECT_DISPOSITIVO), {"m": mac}).fetchone()

            id_disp = res[0]

            # Salva a leitura — agora com potenciometro e rotacao também
            conn.execute(text(Q_INSERT_LEITURA), {
                "id": id_disp, "t": temp, "u": umid, "pot": pot, "rot": rot
            })

            # Atualiza ultima_conexao do dispositivo — antes nunca era atualizado
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

    # Se o Arduino estava offline e voltou, gera alerta de retorno
    if mac in ultimos_contatos and ultimos_contatos[mac]["status"] == "offline":
        salvar_alerta("INFO", f"Arduino {mac} voltou a operar.", payload.wifi_rssi)

    # Atualiza o estado em memória para o dashboard em tempo real
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
# 🛣️  ROTAS DO DASHBOARD (protegidas por sessão)
# ======================================================

@app.get("/dados_recentes")
async def dados_recentes(sessao: dict = Depends(obter_sessao)):
    """
    Retorna o dado mais recente em tempo real — usado pelos cards do dashboard.
    Qualquer perfil logado pode acessar.

    Corrigido: antes usava [-1] (último inserido no dict), agora usa max() pelo horario
    para pegar o dado mais recente de verdade, independente da ordem de inserção.
    """
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


@app.post("/cadastrar_usuario")
async def cadastrar_usuario(
    usuario: NovoUsuario,
    sessao: dict = Depends(exigir_perfil("Supervisor", "Admin"))
):
    """
    Cria um novo usuário no sistema.
    Supervisor pode criar Operador e Supervisor.
    Admin pode criar qualquer perfil.

    A autorização vem do header X-Session (token de sessão), não do X-Token do Arduino.
    Isso é importante: o Arduino e o usuário humano usam mecanismos de autenticação
    completamente separados.
    """
    perfis_validos = {"Operador", "Supervisor", "Admin"}
    if usuario.perfil not in perfis_validos:
        raise HTTPException(status_code=400, detail=f"Perfil inválido. Use: {perfis_validos}")

    # Supervisor não pode criar Admin
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
                pass  # Sheets falha silenciosamente

        return {
            "status": "sucesso",
            "mensagem": f"Usuário '{usuario.login}' criado com perfil '{usuario.perfil}'."
        }

    except Exception as e:
        # Corrigido: antes engolia o erro sem logar. Agora imprime para debug.
        print(f"Erro ao cadastrar usuário '{usuario.login}': {e}")
        raise HTTPException(status_code=400, detail="Login já existe ou erro no banco.")


# ======================================================
# 🚀  INICIALIZAÇÃO
# ======================================================
if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    print("\n" + "="*52)
    print(f"  🚀 API IoT SENAI v3.1 — Banco: {DB_MODE.upper()}")
    print("="*52 + "\n")

    config = uvicorn.Config(app, host="0.0.0.0", port=5000, log_level="error")
    srv    = uvicorn.Server(config)

    async def main():
        asyncio.create_task(monitorar_conexoes())
        await srv.serve()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 API finalizada.")
