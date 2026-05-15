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
<img width="484" height="814" alt="imagem 1" src="https://github.com/user-attachments/assets/9e86d9b7-9171-43b2-9f81-b977caf06bfa" />
<img width="530" height="353" alt="imagem 2" src="https://github.com/user-attachments/assets/229ce266-4517-4959-867a-ec9b5b7ac14e" />
<img width="676" height="358" alt="imagem 3" src="https://github.com/user-attachments/assets/7b0a927e-c3a5-47db-8f85-f095c97c4d46" />
<img width="674" height="419" alt="imagem 4" src="https://github.com/user-attachments/assets/6a917496-4070-46a2-b69e-3c37d583f298" />
<img width="381" height="194" alt="imagem 5" src="https://github.com/user-attachments/assets/a24457ac-9d2f-47a2-b4c1-97784abdd937" />
<img width="539" height="278" alt="imagem 6" src="https://github.com/user-attachments/assets/515ea4a8-ddbd-433d-9757-7f3699d353dd" />
<img width="542" height="612" alt="imagem 7" src="https://github.com/user-attachments/assets/866b7024-6689-47d6-be19-fc500f00e9e2" />

## ⚠️ Problemas encontrados
Descrever erros e soluções
02_Investigacao_Pinos/  
Arquivo sugerido:  investigacao.md

Conteúdo esperado:

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
