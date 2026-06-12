# 🚀 Projeto Integrador - IoT JEGP Corporation

## 👥 Integrantes
- pedro arthur
- gilberto alves
- julia lopes

## 📌 Descrição
Sistema de monitoramento inteligente utilizando ESP8266, API, banco de dados e integração com Google Sheets.

## 🎯 Objetivo
Desenvolver um sistema capaz de coletar, processar, armazenar e disponibilizar dados em tempo real.
---
## 🧩 Etapas do Projeto

### 01 - Configuração
Ambiente configurado e validado

### 02 - Investigação de Pinos
Levantamento e análise das portas do ESP8266

### 03 - Modelagem do Sistema
Definição das regras e comportamento do sistema

### 04 - Evidências
Registros visuais e testes realizados

### 05 - Atualizações
Controle de mudanças e evolução do projeto
---
## 🔁 Evolução do Projeto
Ver pasta: [05_Atualizacoes](https://github.com/Pedrobarbancho/PROJETO-INTEGRADOR---Sistema-Inteligente-de-Monitoramento-e-Integra-o-com-API-e-Cloud-/tree/main/05_Atualizacoes)
---
## 📸 Evidências
Ver pasta: [04_Evidencias](https://github.com/Pedrobarbancho/PROJETO-INTEGRADOR---Sistema-Inteligente-de-Monitoramento-e-Integra-o-com-API-e-Cloud-/tree/main/04_Evidencias)
---
## 🧠 Aprendizados
Ver pasta: [01_Configuracao](https://github.com/Pedrobarbancho/PROJETO-INTEGRADOR/tree/main/01_Configuracao)
---
# 🖥️ Configuração do Ambiente

## ⚙️ Configurações realizadas
- Adição da URL do ESP8266
- Instalação do pacote
- Seleção da placa
- Configuração da porta

## 🧪 Teste realizado
Descrever o teste (ex: blink)

## 📸 Evidências
<img width="484" height="814" alt="imagem 1" src="https://github.com/user-attachments/assets/9e86d9b7-9171-43b2-9f81-b977caf06bfa" />
<img width="530" height="353" alt="imagem 2" src="https://github.com/user-attachments/assets/229ce266-4517-4959-867a-ec9b5b7ac14e" />
<img width="676" height="358" alt="imagem 3" src="https://github.com/user-attachments/assets/7b0a927e-c3a5-47db-8f85-f095c97c4d46" />
<img width="674" height="419" alt="imagem 4" src="https://github.com/user-attachments/assets/6a917496-4070-46a2-b69e-3c37d583f298" />
<img width="381" height="194" alt="imagem 5" src="https://github.com/user-attachments/assets/a24457ac-9d2f-47a2-b4c1-97784abdd937" />
<img width="539" height="278" alt="imagem 6" src="https://github.com/user-attachments/assets/515ea4a8-ddbd-433d-9757-7f3699d353dd" />
<img width="542" height="612" alt="imagem 7" src="https://github.com/user-attachments/assets/866b7024-6689-47d6-be19-fc500f00e9e2" />

# 🔌 Investigação das Portas

## 🌐 Fontes utilizadas
- [link 1](https://embarcados.com.br/arduino-entradas-analogicas/)
- [link 2](https://embarcados.com.br/pinos-digitais-do-arduino/)
- [link 3](https://youtu.be/SYKx85uoBrw)
- [link 4](https://youtu.be/yehyUmUDJXc)
- [link 5](https://www.usinainfo.com.br/shieldsexpansores/shield-multifuncoes-hy-m302-para-arduino-)
- [link 6](https://arduino-esp8266.readthedocs.io/en/latest/)
- [link 7](https://docs.arduino.cc/)
- [link 8](https://developers.google.com/apps-script?hl=pt-br)
- [link 9](https://www.ibm.com/docs/pt-br/cics-ts/5.6.0?topic=support-internet-tcpip-http-concepts)
- [link 10](https://learn.microsoft.com/pt-br/viva/goals/gsheets-integration)
- [link 11](https://www.microsoft.com/pt-br/security/business/security-101/what-is-authentication)
- [link 12](https://www.ibm.com/br-pt/think/topics/rest-apis)
- [link 13](https://developer.mozilla.org/pt-BR/docs/Web/HTTP/Reference/Methods)
- [link 14](https://www.ibm.com/docs/pt-br/cics-ts/5.6.0?topic=programs-clientserver-model  )
- [link 15](https://www.dio.me/articles/o-que-sao-endpoints-e-rotas-de-uma-api)

## 🔍 Processo de investigação
Para este projeto, utilizamos o shield **HY-M302**. Como essa placa possui periféricos integrados, a investigação foi focada em descobrir quais GPIOs do ESP8266 controlam cada componente do shield.

Encontramos um guia fundamental no repositório de um usuário [snabel93](https://github.com/snabel93/Arduino-HY-M302), que forneceu a tabela de mapeamento de pinos correta para este modelo. Sem esse mapeamento, o uso de sensores como o LDR ou o LED RGB seria baseado em tentativa e erro.

**O que aprendemos com a referência:**

- **Pinos Ocupados:** Identificamos que os pinos **D5**, **D6**, **D7** e **D8** são geralmente usados para o LED RGB e o Buzzer no shield.
- **Leitura Analógica:** Confirmamos que o sensor de luz (LDR) e o Termistor compartilham a entrada analógica **A0**, dependendo dos jumpers da placa.
- **Pinos Livres:** Identificamos quais portas ainda estavam disponíveis para ex1pansão caso precisássemos conectar o Google Sheets para alertas externos.

## 📊 Tabela de resultados
| PINO (Shield) | CÓDIGO (ESP8266) | PODE USAR? | TIPO | RESTRIÇÃO | JUSTIFICATIVA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D2** | D0 – GPIO16 | SIM | ENTRADA | NENHUMA | Funciona perfeitamente |
| **D3** | D1 – GPIO 05 | SIM | ENTRADA | NENHUMA | Funciona perfeitamente |
| **D4** | D2 – GPIO 04 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **D6** | D3 – GPIO 0 | NÃO RECOMENDADO | SAÍDA | BOOT | Pode afetar a inicialização do ESP8266 |
| **D9** | D4 – GPIO 2 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **D13 & D5** | D5 – GPIO 14 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **D12** | D6 – GPIO 12 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **D10** | D7 – GPIO 13 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **D11** | D8 – GPIO 15 | SIM | SAÍDA | NENHUMA | Funciona perfeitamente |
| **NONE** | RX – GPIO 3 | SIM | SERIAL | NENHUMA | Comunicação Serial |
| **NONE** | TX – GPIO 1 | SIM | SERIAL | NENHUMA | Comunicação Serial |
| **A0** | A0 – ADC0 | SIM | ANALÓGICO | NENHUMA | Funciona perfeitamente |

## 🚨 Problemas encontrados
Não tivemos problemas graves no hardware. A única observação importante foi sobre os pinos **RX** e **TX**:

- **Identificação**: Notamos que esses pinos não possuem um código "D" (como D1, D2) na placa.
- **Decisão**: Decidimos não conectar nada neles para não atrapalhar o envio do código e o uso do Monitor Serial.
- **Conclusão**: Por serem pinos de comunicação, deixamos como **"NONE"** na tabela e focamos o uso nos outros pinos digitais que funcionaram perfeitamente.
# 🧠 Modelagem do Sistema

### 3. Configuração do Hardware (ESP8266)

1. Abra o arquivo `arduino.ino` na Arduino IDE.
2. Certifique-se de configurar as suas credenciais no arquivo de cabeçalho `config.h` (Rede WiFi e Token da API).
3. Ajuste a variável `String servidor = "IP_DA_SUA_MAQUINA";` com o IP local do computador que está rodando a API Python.
4. Faça o upload do código para a sua placa **NodeMCU ESP8266**.

---

### 4. Acesso ao Painel Web

1. Abra o arquivo `index.html` em qualquer navegador moderno.
2. Entre com uma das credenciais cadastradas pelo script de hash (Ex: login `admin`, senha `senha`).
3. O painel mudará automaticamente para o `dashboard.html`, exibindo os gráficos, sinal de WiFi da placa e terminal de auditoria em tempo real.

---

### 🔒 Níveis de Acesso e Segurança

O sistema implementa autenticação segura baseada em sessões com hashes **Bcrypt**. Os recursos críticos são protegidos conforme o nível do usuário:

| Cargo | Permissões |
|---|---|
| **Dev** | Acesso total irrestrito ao banco, migrações e deleções profundas de logs de sistema. |
| **Admin** | Permissão para visualização completa e acionamento de rotinas de higienização de planilhas. |
| **Supervisor** | Acesso analítico completo aos logs operacionais e auditoria de tentativas de login. |
| **Operador** | Visualização básica e exclusiva do Dashboard em tempo real (sem permissão de alteração). |

---

### 🗄️ Estrutura das Tabelas (Banco de Dados)

| Tabela | Descrição |
|---|---|
| `dispositivos` | Armazena os parâmetros físicos de identificação (MAC Address) e localização das placas IoT cadastradas. |
| `leituras` | Registro de série temporal contendo temperatura (°C), umidade (%), potenciômetro, rotações e carimbo de data/hora. |
| `usuario` | Dados cadastrais, logins exclusivos, hashes de senhas e atribuição de cargos de acesso. |
| `alertas_logs` | Histórico de auditoria técnica da estabilidade da rede WiFi (sinal RSSI) e avisos do sistema. |
| `logs_acesso` | Rastreamento preventivo de segurança registrando data, IP de origem e sucesso/falha de cada tentativa de login. |

## 📊 Regras Definidas

O sistema opera com uma lógica de estados baseada na interação do usuário com os botões físicos e no monitoramento climático.

| Condição | Estado | Ação / Comportamento |
| :--- | :--- | :--- |
| **Pressionar BOTAO1** | `Conectando` | Inicia conexão Wi-Fi e ativa o Servidor Web interno. |
| **Pressionar BOTAO2** | `Desconectado` | Desliga o Wi-Fi e interrompe o envio de dados para a API. |
| **Wi-Fi Conectado** | `Ativo` | Envia um JSON com leituras para o Python a cada 5 segundos. |
| **Erro no Sensor DHT** | `Falha` | Retorna valor `0` para temperatura/umidade e gera log de erro. |
| **Acesso ao IP do ESP** | `Web Server` | Renderiza uma página HTML com os dados do Laboratório SENAI. |
| **Requisição /hora** | `Sincronia` | Sincroniza o horário do sistema com o servidor backend Python. |

## 🧩 Estrutura do JSON

| Campo | Descrição | Exemplo de Valor |
| :--- | :--- | :--- |
| `device` | Endereço MAC único da placa | `AA:BB:CC:DD:EE:FF` |
| `temperatura` | Valor lido pelo sensor DHT11 | `25.5` |
| `umidade` | Valor lido pelo sensor DHT11 | `60.0` |
| `botao1` | Estado do botão de ligar | `true` ou `false` |
| `status` | Situação de operação do ESP | `Ativo` |

## 🔄 Fluxo

1. **Entrada:** Leitura do sensor DHT11 e estado dos botões pelo ESP8266.
2. **Processamento:** O ESP8266 monta o pacote JSON e faz a autenticação via Token.
3. **Transmissão:** Envio via HTTP POST para a API FastAPI (Python).
4. **Armazenamento:** O Python grava os dados no MySQL e atualiza o Google Sheets.
5. **Saída:** Visualização via Página Web local e Planilha Cloud.

## 🧩 Variáveis do Sistema
Para garantir o monitoramento completo, o sistema trabalha com as seguintes métricas:
- **Temperatura (°C):** Coletada via sensor DHT11 para controle climático.
- **Umidade (%):** Monitoramento da umidade relativa do ar.
- **Estado de Conexão:** Variável booleana que indica se o Wi-Fi e o Servidor Web estão ativos.
- **Interação Física:** Monitoramento dos estados dos Botões 1 (D0) e 2 (D1).
- **RSSI:** Nível de intensidade do sinal Wi-Fi para diagnóstico de rede.

## 💡 Justificativas
A escolha das tecnologias e da estrutura do projeto baseou-se em três pilares:

1. **Confiabilidade (Redundância):** A decisão de utilizar dois bancos de dados (MySQL e SQL Server) justifica-se pela necessidade de alta disponibilidade. Caso um servidor falhe, o sistema possui suporte para continuar a operação no outro, evitando perda de dados históricos.
2. **Segurança de Dados:** Diferente da versão inicial, a implementação de Headers com `x-token` foi essencial para simular um ambiente industrial real, onde apenas dispositivos autorizados podem enviar informações para a API.
3. **Usabilidade (QOL):** A criação de um Servidor Web dentro do próprio ESP8266 justifica-se pela facilidade de diagnóstico. O usuário pode verificar os dados em tempo real apenas acessando o IP da placa no navegador, sem depender de ferramentas externas.

## 04_Evidencias/  

Aqui ficam:
Fotos
Prints
Vídeos

Sugestão:
imagem1.jpg
teste_led.png
video_link.txt

## 05_Atualizacoes/
Arquivo sugerido:   atualizacoes.md

Conteúdo essencial:
# 🔁 Atualizações do Projeto

### V1.0 - Protótipo Inicial
- **Descrição:** Primeira integração entre Arduino, API, MySQL e Planilha.
- **Segurança:** Nenhuma segurança implementada (0% proteção).
- **Experiência:** Falta de funções de "QOL" (Quality of Life) para o usuário.
- **Problemas:** Erros fatais constantes, como ``HTTP Error -1``, quedas na API e conflitos de IPs.

### v2.0 Sistema Robusto
A v2 foi uma reestruturação total para resolver a instabilidade da versão anterior e trazer profissionalismo ao sistema.

#### Melhorias Realizadas:
- **Interface Web:** Criação de um site interno hospedado no ESP8266 para monitoramento local.
- **Segurança:** Implementação de autenticação via API Token para proteger os dados.
- **Backend Aprimorado:** Terminal da API mais "bonito" e detalhado, facilitando a vida do usuário na hora de monitorar os logs.
- **Redundância de Banco de Dados:** Agora o sistema suporta MySQL e SQL Server. Isso garante que, se um banco estiver fora do ar, o outro assume a função, mantendo o sistema online.
- **Estabilidade HTTP:** Correção dos erros de conexão e melhor tratamento de falhas.

#### 📊 Evolução Técnica

Abaixo, detalhamos como os problemas críticos da Versão 1.0 foram resolvidos na Versão 2.0.

| Problema Identificado (v1.0) | Causa Provável | Solução Implementada (v2.0) | Resultado Prático |
| :--- | :--- | :--- | :--- |
| **Erro HTTP -1** | Falha de conexão ou timeout da rede. | Validação de `WiFi.status()` antes de cada envio e tratamento de erro. | Conexão estável e sem travamentos no código. |
| **0% Segurança** | Dados abertos sem autenticação. | Inclusão de `x-token` no Header das requisições HTTP. | Sistema protegido contra envios externos não autorizados. |
| **Dificuldade de Monitoração** | Logs simples e pouco informativos. | Terminal Python (FastAPI) com logs visuais e Dashboard Web no ESP. | Facilidade total para o usuário acompanhar o sistema. |
| **Instabilidade de IPs** | IPs mudavam e o código perdia a rota. | Exibição do IP local no Serial e na página web dinâmica. | Acesso rápido ao site interno do dispositivo. |
| **Dependência do MySQL** | Se o banco caísse, o sistema parava. | Implementação de redundância com **MySQL + SQL Server**. | Alta disponibilidade: se um banco falhar, o outro assume. |
| **Falta de Controle Físico** | O sistema ligava sozinho sem comando. | Controle manual de conexão via **Botão 1** e **Botão 2**. | Maior controle do usuário sobre o consumo de rede e hardware. |
