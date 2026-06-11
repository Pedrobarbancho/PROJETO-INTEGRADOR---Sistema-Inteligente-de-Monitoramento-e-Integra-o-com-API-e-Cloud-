-- ============================================================
-- BANCO DE DADOS IoT - SENAI
-- Versão: SQL Server (v3.4.2 — bcrypt)
-- ============================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'GJP')
    CREATE DATABASE GJP;
GO

USE GJP;
GO

-- ============================================================
-- TABELA: dispositivos
-- Registra cada ESP8266/Arduino pela MAC address
-- ============================================================
CREATE TABLE dispositivos (
    id_dispositivo  INT          PRIMARY KEY IDENTITY(1,1),
    mac_address     VARCHAR(25)  NOT NULL UNIQUE,
    local_disp      VARCHAR(50)  DEFAULT 'Laboratorio SENAI',
    ultima_conexao  DATETIME     DEFAULT NULL
);

-- ============================================================
-- TABELA: leituras
-- Uma linha por envio do sensor
-- ============================================================
CREATE TABLE leituras (
    id_leitura      INT           PRIMARY KEY IDENTITY(1,1),
    id_dispositivo  INT           NOT NULL,
    temperatura     DECIMAL(5,2)  NOT NULL,
    umidade         DECIMAL(5,2)  NOT NULL,
    potenciometro   INT           DEFAULT 0,
    rotacao         INT           DEFAULT 0,
    data_hora       DATETIME      DEFAULT GETDATE(),
    FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id_dispositivo)
);

-- ============================================================
-- TABELA: usuario
-- Hierarquia: Operador < Supervisor < Admin < Dev
-- Senhas armazenadas como hash bcrypt (unidirecional, gerado pela API)
-- Coluna apelido: opcional, exibida no lugar do nome completo quando preenchida
-- ============================================================
CREATE TABLE usuario (
    id      INT          PRIMARY KEY IDENTITY(1,1),
    nome    VARCHAR(100) NOT NULL,
    login   VARCHAR(50)  NOT NULL UNIQUE,
    senha   VARCHAR(255) NOT NULL, -- hash bcrypt, ex: $2b$12$...
    perfil  VARCHAR(20)  NOT NULL,
    apelido VARCHAR(80)  DEFAULT NULL, -- opcional, fica NULL até o usuário definir
    CHECK (perfil IN ('Operador', 'Supervisor', 'Admin', 'Dev'))
);

-- ============================================================
-- TABELA: alertas_logs
-- SQL Server não tem ENUM, usa VARCHAR + CHECK CONSTRAINT
-- ============================================================
CREATE TABLE alertas_logs (
    id_log    INT           PRIMARY KEY IDENTITY(1,1),
    nivel     VARCHAR(10)   NOT NULL CHECK (nivel IN ('INFO', 'ALERTA', 'ERRO')),
    mensagem  NVARCHAR(MAX) NOT NULL,
    wifi_rssi INT           DEFAULT 0,
    data_hora DATETIME      DEFAULT GETDATE()
);

-- ============================================================
-- TABELA: logs_acesso
-- Registra todas as tentativas de login (sucesso e falha)
-- ============================================================
CREATE TABLE logs_acesso (
    id_log      INT          PRIMARY KEY IDENTITY(1,1),
    login       VARCHAR(50)  NOT NULL,
    sucesso     BIT          NOT NULL, -- 1 = sucesso, 0 = falha
    ip_origem   VARCHAR(45)  DEFAULT NULL, -- DEFAULT NULL pois o IP pode não estar disponível em alguns casos (ex: proxy)
    data_hora   DATETIME     DEFAULT GETDATE()
);

-- ============================================================
-- USUÁRIO INICIAL (execute uma vez após criar as tabelas)
-- A senha deve ser gerada como hash bcrypt pela API ou por script Python:
--   import bcrypt
--   print(bcrypt.hashpw(b'senha_inicial', bcrypt.gensalt()).decode())
-- Cole o hash gerado no lugar de '$2b$12$HASH_AQUI'
-- ============================================================
-- INSERT INTO usuario (nome, login, senha, perfil)
-- VALUES ('Administrador', 'admin', '$2b$12$HASH_AQUI', 'Admin');

-- INSERT INTO usuario (nome, login, senha, perfil)
-- VALUES ('Dev GJP', 'dev', '$2b$12$HASH_AQUI', 'Dev');

-- ============================================================
-- CONSULTAS ÚTEIS PARA DEBUG
-- ============================================================

-- Últimas 10 leituras:
-- SELECT TOP 10 d.mac_address, l.temperatura, l.umidade, l.data_hora
-- FROM leituras l JOIN dispositivos d ON l.id_dispositivo = d.id_dispositivo
-- ORDER BY l.data_hora DESC;

-- Usuários cadastrados (sem expor senha):
-- SELECT id, nome, login, perfil, apelido FROM usuario;

-- Tentativas de login:
-- SELECT TOP 20 login, sucesso, ip_origem, data_hora FROM logs_acesso ORDER BY data_hora DESC;

-- Alertas recentes:
-- SELECT TOP 20 nivel, mensagem, data_hora FROM alertas_logs ORDER BY data_hora DESC;