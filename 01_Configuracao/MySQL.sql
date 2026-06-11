-- ============================================================
-- BANCO DE DADOS IoT - SENAI
-- Versão: MySQL  (atualização v3.4.2)
-- ============================================================

CREATE DATABASE IF NOT EXISTS GJP;
USE GJP;

-- ============================================================
-- TABELA: dispositivos
-- ============================================================
CREATE TABLE IF NOT EXISTS dispositivos (
    id_dispositivo  INT          PRIMARY KEY AUTO_INCREMENT,
    mac_address     VARCHAR(25)  NOT NULL UNIQUE,
    local_disp      VARCHAR(50)  DEFAULT 'Laboratorio SENAI',
    ultima_conexao  DATETIME     DEFAULT NULL
);

-- ============================================================
-- TABELA: leituras
-- ============================================================
CREATE TABLE IF NOT EXISTS leituras (
    id_leitura      INT           PRIMARY KEY AUTO_INCREMENT,
    id_dispositivo  INT           NOT NULL,
    temperatura     DECIMAL(5,2)  NOT NULL,
    umidade         DECIMAL(5,2)  NOT NULL,
    potenciometro   INT           DEFAULT 0,
    rotacao         INT           DEFAULT 0,
    data_hora       DATETIME      DEFAULT NOW(),
    FOREIGN KEY (id_dispositivo) REFERENCES dispositivos(id_dispositivo)
);

-- ============================================================
-- TABELA: usuario
-- Hierarquia: Operador < Supervisor < Admin < Dev
-- Coluna apelido: opcional, exibida no lugar do nome completo quando preenchida
-- ============================================================
CREATE TABLE IF NOT EXISTS usuario (
    id      INT            PRIMARY KEY AUTO_INCREMENT,
    nome    VARCHAR(100)   NOT NULL,
    login   VARCHAR(50)    NOT NULL UNIQUE,
    senha   VARCHAR(255) NOT NULL,
    perfil  VARCHAR(20)    NOT NULL,
    apelido VARCHAR(80)    DEFAULT NULL, -- apelido é opcional, fica vazio (NULL) até o usuário definir um
    CHECK (perfil IN ('Operador', 'Supervisor', 'Admin', 'Dev')) -- CHECK serve para garantir que não seja adicionado outro cargo que não existe
);

-- ============================================================
-- TABELA: alertas_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS alertas_logs (
    id_log    INT          PRIMARY KEY AUTO_INCREMENT,
    nivel     ENUM('INFO', 'ALERTA', 'ERRO') NOT NULL,
    mensagem  TEXT         NOT NULL,
    wifi_rssi INT          DEFAULT 0,
    data_hora DATETIME     DEFAULT NOW()
);

-- ============================================================
-- TABELA: logs_acesso
-- Registra todas as tentativas de login (sucesso e falha).
-- ============================================================
CREATE TABLE IF NOT EXISTS logs_acesso (
    id_log      INT          PRIMARY KEY AUTO_INCREMENT,
    login       VARCHAR(50)  NOT NULL,
    sucesso     TINYINT   NOT NULL,
    ip_origem   VARCHAR(45)  DEFAULT NULL, -- DEFAULT NULL pois o IP pode não estar disponível em alguns casos (ex: proxy)
    data_hora   DATETIME     DEFAULT NOW()
);