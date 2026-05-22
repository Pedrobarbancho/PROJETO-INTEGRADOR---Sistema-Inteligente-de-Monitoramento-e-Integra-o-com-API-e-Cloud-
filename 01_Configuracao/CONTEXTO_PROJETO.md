# CONTEXTO DO PROJETO — IoT SENAI
> Documento gerado para continuação em nova sessão de IA.
> Leia este arquivo inteiro antes de responder qualquer pergunta sobre o projeto.

---

## 1. VISÃO GERAL

Projeto integrador do curso **Cibersistemas para Automação** no SENAI Guarulhos (SP).
Desenvolvido solo por um aluno em aprendizado. Sem Arduino disponível fora do laboratório.

**Objetivo:** pipeline completo de dados IoT:
```
ESP8266 (sensor) → API Python → MySQL / SQL Server → Dashboard Web
                                       ↓
                               Google Sheets (espelho)
```

---

## 2. HARDWARE

- **Microcontrolador:** NodeMCU ESP8266
- **Placa de sensores:** HY-302
- **Sensores ativos:** temperatura, umidade, rotação (encoder), potenciômetro, botões, receptor IR
- **Protocolo:** HTTP POST com JSON via Wi-Fi
- **Autenticação do hardware:** header `X-Token` com `API_TOKEN` do `.env`

**Payload enviado pelo ESP8266:**
```json
{
  "device": "AA:BB:CC:DD:EE:FF",
  "timestamp_ms": 123456789,
  "sensores": { "temperatura": 25.3, "umidade": 60.1, "rotacao": 0, "potenciometro": 512 },
  "entradas":  { "botao1": false, "botao2": false, "ir_recebido": false },
  "status": "ok",
  "wifi_rssi": -65
}
```

---

## 3. STACK TECNOLÓGICA

| Camada | Tecnologia | Observação |
|---|---|---|
| Backend | Python + FastAPI | Arquivo único `api.py` |
| ORM/SQL | SQLAlchemy + text() | Queries SQL puras, sem ORM |
| MySQL driver | PyMySQL | `mysql+pymysql://` |
| SQL Server driver | pymssql (preferido) | sem driver de sistema; fallback pyodbc |
| Sheets | gspread + oauth2client | Service account JSON |
| Config | python-dotenv | `load_dotenv(override=True)` — CRÍTICO |
| Servidor | Uvicorn | porta 5000 |
| Frontend | HTML + CSS + JS puro | sem frameworks |
| Fontes | Share Tech Mono + Barlow | via Google Fonts |

**Restrição de ambiente:** PCs do SENAI sem privilégio de admin. Nada que exija instalação de sistema (sem XAMPP). Tudo via `pip install`.

---

## 4. ESTRUTURA DE ARQUIVOS

```
projeto/
├── api.py               ← Backend principal (versão 3 — a mais atual)
├── .env                 ← Credenciais (NUNCA versionar)
├── credenciais.json     ← Service account Google (NUNCA versionar)
├── banco.sql            ← Script de criação do banco (MySQL + notas SQL Server)
├── index.html           ← Página de login
└── dashboard.html       ← Painel principal com abas por perfil
```

> `script.js` e `style.css` separados existem mas são legados — o código atual está inline nos HTMLs.

---

## 5. BANCO DE DADOS

### Tabelas (MySQL — com equivalentes SQL Server comentados no banco.sql)

```sql
dispositivos  (id_dispositivo, mac_address, local_disp, ultima_conexao)
leituras      (id_leitura, id_dispositivo, temperatura, umidade, potenciometro, rotacao, data_hora)
usuario       (id, nome, login, senha VARBINARY, perfil)
alertas_logs  (id_log, nivel ENUM, mensagem, wifi_rssi, data_hora)
```

**Atenção:** coluna corrigida de `mac_addres` (typo antigo) para `mac_address`.

### Senhas
- **MySQL:** `AES_ENCRYPT(senha, SECRET_KEY_DB)` — chave vem do `.env`
- **SQL Server:** `HASHBYTES('SHA2_256', senha)` — sem chave externa

### Troca de banco
No `.env`, adicionar/mudar:
```env
DB_MODE=mysql       # ou "sqlserver"
```
A API detecta automaticamente e usa as queries certas. A função `sql(mysql_q, ss_q)` retorna a query certa para o banco ativo.

---

## 6. ARQUIVO `.env` (estrutura atual)

```env
# SEGURANÇA
API_TOKEN=Token_super_secreta123          # enviado pelo ESP8266 no header X-Token
SECRET_KEY_DB=9fK2xL8#Qw7mNp4!ZrT6vBc1@Hs8YeD5   # chave AES para senhas MySQL

# MYSQL
MYSQL_URL=mysql+pymysql://root:SENHA@localhost:3306/GJP

# SQL SERVER (descomentado quando necessário)
# DB_MODE=sqlserver
# SQLSERVER_SERVER=.\SQLEXPRESS
# SQLSERVER_DB=GJP
# SQLSERVER_USER=sa
# SQLSERVER_PASS=senha

# GOOGLE SHEETS
GOOGLE_CREDS_FILE=credenciais.json
GOOGLE_SHEET_NAME=Planilha de dados
```

**CRÍTICO:** `load_dotenv(override=True)` — sem o `override=True`, variáveis já existentes no sistema Windows são ignoradas e o `.env` não tem efeito.

---

## 7. ROTAS DA API

### Públicas (sem autenticação)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/status` | Healthcheck — retorna banco ativo e status Sheets |
| GET | `/hora` | Data/hora atual |
| POST | `/login` | Autentica e retorna `session_token` |

### ESP8266 (autenticadas por `X-Token: API_TOKEN`)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/dados` | Recebe payload do sensor, salva no banco e Sheets |

### Dashboard (autenticadas por `X-Session: session_token`)
| Método | Rota | Perfis permitidos |
|---|---|---|
| GET | `/dados_recentes` | Todos |
| GET | `/tabela/leituras` | Todos |
| GET | `/tabela/alertas` | Supervisor, Admin |
| GET | `/tabela/dispositivos` | Supervisor, Admin |
| GET | `/tabela/usuarios` | Admin |
| POST | `/cadastrar_usuario` | Supervisor (só Operador/Supervisor), Admin (todos) |

---

## 8. SISTEMA DE SESSÃO

- No login, a API gera um UUID (`uuid.uuid4()`) e armazena em memória: `sessoes: dict[str, dict]`
- O frontend salva em `sessionStorage` (some ao fechar o navegador — intencional)
- Cada requisição protegida manda `X-Session: <token>` no header
- **Limitação conhecida:** reiniciar a API apaga todas as sessões → usuário precisa fazer login de novo
- Isso é aceitável para o projeto escolar; em produção real usaria banco ou Redis

### Dependências FastAPI reutilizáveis
```python
obter_sessao()          # valida sessão, retorna dict {nome, perfil}
exigir_perfil(*perfis)  # valida sessão + verifica perfil mínimo
```

---

## 9. RBAC — PERMISSÕES POR PERFIL

| Funcionalidade | Operador | Supervisor | Admin |
|---|---|---|---|
| Ver dados ao vivo | ✅ | ✅ | ✅ |
| Ver tabela leituras | ✅ (sem MAC) | ✅ | ✅ |
| Ver alertas | ❌ | ✅ | ✅ |
| Ver dispositivos | ❌ | ✅ | ✅ |
| Ver usuários | ❌ | ❌ | ✅ |
| Criar Operador | ❌ | ✅ | ✅ |
| Criar Supervisor | ❌ | ✅ | ✅ |
| Criar Admin | ❌ | ❌ | ✅ |

**Dupla proteção:** restrição no backend (Python retorna 403) **e** no frontend (aba/opção não aparece).

---

## 10. GOOGLE SHEETS

- **Função:** espelho de dados, não fonte primária
- **Autenticação:** service account (`credenciais.json`) — arquivo sensível, não versionar
- **Abas esperadas na planilha:** `leituras`, `alertas`, `usuarios`
- **Nome da planilha:** configurado em `GOOGLE_SHEET_NAME` no `.env`
- **Falha silenciosa:** se Sheets estiver indisponível, a API continua funcionando normalmente
- **Login NÃO usa Sheets** — autenticação é 100% pelo banco SQL (decisão de segurança)

---

## 11. SEGURANÇA IMPLEMENTADA

| Medida | Onde | Detalhe |
|---|---|---|
| Token do hardware | ESP8266 → API | Header `X-Token`; token inválido gera alerta no banco |
| Senhas criptografadas | MySQL | `AES_ENCRYPT` com chave do `.env` |
| Senhas hash | SQL Server | `HASHBYTES('SHA2_256')` |
| Sessão por UUID | Login → Dashboard | Token gerado no servidor, salvo no `sessionStorage` |
| Perfis no backend | Todas rotas protegidas | Frontend pode ser burlado; backend é a barreira real |
| Sem token no frontend | Dashboard | Remoção do `API_TOKEN` do JS — era o maior risco |
| `.env` separado | Config | Nunca versionar; `override=True` garante leitura correta |
| Credenciais fora do código | `credenciais.json` | Referenciado por path, não hardcoded |

### Vulnerabilidades conhecidas e aceitas (projeto escolar)
- Sessões em memória (sem persistência)
- `allow_origins=["*"]` no CORS (aceitável em rede local)
- Atalho dev `admin/123` ainda no código (remover antes de apresentar)
- Atalho `Ctrl+Shift+L` no `index.html` (remover antes de apresentar)

---

## 12. FRONTEND

### Design
- Tema industrial/técnico — coerente com IoT
- Paleta: fundo `#0a0e14`, superfície `#111820`, accent ciano `#00d4ff`, verde `#00ff9d`
- Grid de fundo decorativo com CSS
- Fontes: `Share Tech Mono` (dados/labels) + `Barlow` (textos)

### Fluxo de navegação
```
index.html (login)
    ↓ POST /login → salva session_token, nome, perfil no sessionStorage
dashboard.html
    ↓ abas visíveis dependem do perfil
    ↓ todas as requisições levam X-Session no header
    ↓ se 401 → redireciona para login automaticamente
```

### Abas do dashboard
- **Ao Vivo** — cards de temperatura, umidade, RSSI (atualiza a cada 3s)
- **Leituras** — tabela com últimas 30 leituras
- **Alertas** — Supervisor/Admin
- **Dispositivos** — Supervisor/Admin
- **Usuários** — Admin (inclui formulário de cadastro)

---

## 13. ERROS JÁ RESOLVIDOS

| Erro | Causa | Solução |
|---|---|---|
| `Access denied for user 'root'` | `.env` não era carregado (variável do sistema tinha prioridade) | `load_dotenv(override=True)` |
| `mac_addres` (typo) | Erro de digitação no SQL original | Corrigido para `mac_address` em todos os arquivos |
| `CHAVE_MESTRA = os.getenv(...)` no `.env` | Python dentro de arquivo de configuração | Removido; variável lida normalmente no código |
| Sessão inválida após reiniciar API | Sessões em memória são apagadas no restart | Comportamento esperado; usuário refaz login |
| Token do frontend exposto | `API_TOKEN` hardcoded no JS do dashboard | Substituído por sistema de sessão UUID |
| Login pelo Sheets com senha em texto puro | Sheets não criptografa | Login migrado 100% para MySQL/SQL Server |

---

## 14. O QUE AINDA FALTA

### Prioritário (antes da apresentação)
- [ ] Criar usuário Admin inicial no banco (INSERT com AES_ENCRYPT)
- [ ] Remover atalho dev `admin/123` da API
- [ ] Remover atalho `Ctrl+Shift+L` do `index.html`
- [ ] Revogar e regenerar chave do `credenciais.json` do Google (foi exposta em conversa)
- [ ] Testar com Arduino físico no SENAI
- [ ] Testar troca `DB_MODE=sqlserver` com SQL Server do SENAI

### Desejável
- [ ] Tela de erro amigável quando API está offline
- [ ] Paginação nas tabelas (hoje mostra últimos 30)
- [ ] Gráfico de histórico de temperatura/umidade
- [ ] Logout automático por inatividade

### Fora do escopo (não fazer agora)
- Sincronização simultânea MySQL + SQL Server (risco de inconsistência, complexidade desnecessária)
- Sessões persistentes no banco (Redis seria o correto — fora do ambiente escolar)

---

## 15. COMO RODAR O PROJETO

```bash
# 1. Instalar dependências
pip install fastapi uvicorn sqlalchemy pymysql pymssql gspread oauth2client python-dotenv

# 2. Garantir que o banco GJP existe e as tabelas foram criadas (banco.sql)

# 3. Preencher o .env com as credenciais reais

# 4. Rodar a API
python api.py

# 5. Abrir index.html no navegador
# Login dev (remover depois): admin / 123
# Atalho dev: Ctrl+Shift+L no index.html
```

**Amanhã no SENAI (SQL Server):**
```env
DB_MODE=sqlserver
SQLSERVER_SERVER=.\SQLEXPRESS
SQLSERVER_DB=GJP
```
```bash
pip install pymssql   # tenta primeiro
# se falhar: pip install pyodbc (requer driver ODBC no sistema)
```

---

## 16. ESTADO ATUAL DO SISTEMA

- ✅ API funcionando localmente com MySQL
- ✅ Login autenticando pelo banco
- ✅ Dashboard com abas por perfil
- ✅ RBAC implementado (backend + frontend)
- ✅ Google Sheets como espelho (falha silenciosamente se indisponível)
- ✅ Sistema de sessão sem expor API_TOKEN no frontend
- ⚠️  Sessão some ao reiniciar API (comportamento conhecido, aceitável)
- ⏳ Sem teste com Arduino físico (Arduino fica no SENAI)
- ⏳ SQL Server não testado (será testado amanhã no SENAI)
- ❌ Chave do Google ainda precisa ser revogada e regenerada
