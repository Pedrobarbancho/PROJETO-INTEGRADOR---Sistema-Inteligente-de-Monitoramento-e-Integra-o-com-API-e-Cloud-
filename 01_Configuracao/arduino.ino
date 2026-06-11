// --- BIBLIOTECAS ---
#include <ESP8266WiFi.h> // permite que ESP8266 conecta na rede
#include <ESP8266HTTPClient.h> // permite o ESP8266 fazer requisições HTTP para a API
#include <WiFiClient.h> // gerencia a conexão de rede em si
#include <ArduinoJson.h> // monta e lê JSON
#include <DHT.h> // biblioteca do sensor DHT11, lê temperatura e umidade
#include "config.h" //arquivo do próprio projeto com as credenciais

// --- PINOS ---
#define BOTAO1 D0   
#define BOTAO2 D1   
#define BUZZER D5
#define DHTPIN D2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE); // define o modelo do sensor

// --- CONFIG ---
const char* ssid = WIFI_SSID; // nome da rede
const char* password = WIFI_PASS; // senha da rede
String servidor = "192.168.0.105"; // IP da maquina que esta rodado o API
const char* apiToken = TOKEN_API; // token do API
String localAparelho = "Laboratorio SENAI"; // local onde o arduino esta

bool wifiAtivo = false; // aqui fica se a wifi foi ligado ou não
unsigned long tempoAnterior = 0; // serve como cronometro, ele vai usar para enviar os dados exato 5 segs
String erroAtual = "";  // serve para todos os erros atual aparece no serial

// --- FUNÇÃO: PEGAR DATA/HORA ---
String obterDataHoraServidor() {
  // serve como segurança quando o wifi não estiver conectado
  if (WiFi.status() != WL_CONNECTED) return "Sem WiFi";
  WiFiClient client; 
  HTTPClient http;
  //cria um URL para o arduino consiga ver as horas
  String url = "http://" + servidor + ":5000/hora";
  http.begin(client, url); // serve como ela se "preparar" ppara enviar a requisição no URL de cima
  int httpCode = http.GET(); // envia o pedido de GET e guarda a resposta do "site"
  // serve mostrar "Erro servidor" como valor padrão caso a requisição falhe
  String resultado = "Erro servidor";
  // codigo 200 significa que conectou com sucesso
  if (httpCode == 200) {
    JsonDocument doc; // guarda os dados tipo JSON na memoria
    deserializeJson(doc, http.getString()); // pega os dados que o servidor mandou e converte em JSON
    // serve para procurara a data/hora no JSON que foi convertida
    resultado = doc["datahora"].as<String>();
  }
  http.end(); // finalizado a conexao
  return resultado; // retorna com data/hora
}

// --- FUNÇÃO: ENVIAR DADOS E GERAR RELATÓRIO ---
void processarCiclo() {
  // coleta os dados fisico (Temperatura, Umidade e a Hora da outra função)
  float t = dht.readTemperature();
  float u = dht.readHumidity();
  String dataHora = obterDataHoraServidor();
  erroAtual = ""; 

  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;
    // prepara a conexao com a rota /dados e define que vai enviar um JSON seguro
    String url = "http://" + servidor + ":5000/dados";
    http.begin(client, url);
    http.setTimeout(20000); // se a API demorar mais de 20 segundos, disiste
    http.addHeader("Content-Type", "application/json"); // avisa que esta enviando dado JSON
    http.addHeader("x-token", apiToken); // envia o token para o API aceitar os dados 

    // junta tudo no arquivo JSON
    JsonDocument doc;
    doc["device"] = WiFi.macAddress(); // Pega o endereço MAC da placa do ESP
    doc["timestamp_ms"] = millis();
    // coleta os dados do DHT11
    JsonObject sensores = doc["sensores"].to<JsonObject>();
    sensores["temperatura"] = isnan(t) ? 0 : t;
    sensores["umidade"] = isnan(u) ? 0 : u;
    sensores["rotacao"] = 0; // sensor não esta sendo usado ainda
    sensores["potenciometro"] = 0; // sensor não esta sendo usado ainda
    // verfica e envia o estado dos botões
    JsonObject entradas = doc["entradas"].to<JsonObject>();
    entradas["botao1"] = (digitalRead(BOTAO1) == LOW);
    entradas["botao2"] = (digitalRead(BOTAO2) == LOW);
    entradas["ir_recebido"] = false;
    doc["status"] = "Ativo";
    doc["wifi_rssi"] = WiFi.RSSI(); // envia a força do sinal do wifi

    // transforma o arquivo em texto e manda POST no API
    String jsonString;
    serializeJson(doc, jsonString); // converte o JSON em texto
    int httpCode = http.POST(jsonString); // envia os dados e guarda a resposta

    if (httpCode != 200) {
      erroAtual = "HTTP Erro: " + String(httpCode); // se não for sucesso / 200, guarda o erro
    }
    http.end(); // fecha a conexão
  }

  // faz um "print" do relatorio no serial
  Serial.println("\n==============================");
  Serial.print("local: "); Serial.println(localAparelho);
  Serial.print("temperatura: "); Serial.print(t); Serial.println(" °C");
  Serial.print("umidade: "); Serial.print(u); Serial.println(" %");
  Serial.print("data / hora: "); Serial.println(dataHora);
  if (erroAtual != "") { Serial.print("erro: "); Serial.println(erroAtual); }
  Serial.println("==============================");
}

void setup() {
  Serial.begin(115200); // define a velocidade de comunicação do Serial em 115200 baud
  pinMode(BOTAO1, INPUT_PULLUP); // Configura os botões
  pinMode(BOTAO2, INPUT_PULLUP);
  pinMode(BUZZER, OUTPUT); // Configura o Buzzer como uma saída de sinal
  dht.begin(); // Inicializa o sensor de temperatura/umidade
  // Mensagens iniciais na tela do computador
  Serial.println("\n[SISTEMA INICIADO]");
  Serial.println("STATUS: WIFI OFF");
  Serial.println("Pressione BOTAO1 para conectar...");
}

void loop() {
  // Se o Wi-Fi estiver ativo, verifica se já se passaram 5 segundos desde o último envio
  if (wifiAtivo) {
    // millis() conta o tempo em milissegundos desde que a placa ligou. 
    // Essa conta garante que o ciclo rode de 5000 em 5000 ms (5 segundos) sem travar a placa
    if (millis() - tempoAnterior > 5000) { 
      processarCiclo(); // Executa toda aquela função de envio lá de cima
      tempoAnterior = millis(); // Reinicia o cronômetro
    }
  }
}
  // LIGAR
  // BOTAO1 serve para ligar o wifi
  if (digitalRead(BOTAO1) == LOW && !wifiAtivo) {
    Serial.print("\nConectando WiFi");
    WiFi.begin(ssid, password);
    int contador = 0;
    while (WiFi.status() != WL_CONNECTED && contador < 20) { 
      delay(500); Serial.print("."); contador++;
    }

    if(WiFi.status() == WL_CONNECTED) {
      wifiAtivo = true;
      Serial.println("\n✅ WiFi Ativo!");
      processarCiclo();
    } else {
      Serial.println("\n❌ Erro ao conectar.");
    }
  }

  // DESCONECTAR
  //BOTAO2 serve para desligar o wifi
  if (digitalRead(BOTAO2) == LOW && wifiAtivo)
    WiFi.disconnect();
    wifiAtivo = false;