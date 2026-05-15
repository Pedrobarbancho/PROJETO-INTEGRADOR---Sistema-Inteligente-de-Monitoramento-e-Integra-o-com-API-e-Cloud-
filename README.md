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
(Preencher ao longo do projeto)
01_Configuracao/
Arquivo sugerido:  configuracao.md

Conteúdo esperado:

# 🖥️ Configuração do Ambiente

## ⚙️ Configurações realizadas
- Adição da URL do ESP8266
- Instalação do pacote
- Seleção da placa
- Configuração da porta

## 🧪 Teste realizado
Descrever o teste (ex: blink)

## 📸 Evidências
(prints aqui ou link)

## ⚠️ Problemas encontrados
Descrever erros e soluções
02_Investigacao_Pinos/  
Arquivo sugerido:  investigacao.md

Conteúdo esperado:

# 🔌 Investigação das Portas

## 🌐 Fontes utilizadas
- Link 1
- Link 2

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

## 📊 Regras definidas
| Condição | Estado | Ação |

## 🔄 Fluxo
Entrada → Processamento → Decisão → Ação → API

## 🧩 Variáveis
- Temperatura
- Umidade
- Rotação

## 💡 Justificativas
Explicar decisões do grupo

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

## v1.0
- Configuração inicial

## v1.1
- Investigação de pinos
- Identificação de erro no pino D3

## v1.2
- Alteração de pino devido a falha

## v2.0
- Definição da lógica do sistema

---
## 📌 Melhorias realizadas
Descrever mudanças importantes

## 🚨 Problemas e soluções
Explicar erros e como foram corrigidos
