#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>

#define LORA_SS 5
#define LORA_RST 14
#define LORA_DIO0 2
#define RELAY_PIN 27
#define FIRE_SENSOR_PIN 33
#define MQ2_SENSOR_PIN 26
#define DHTPIN 4
#define DHTTYPE DHT11
#define SOIL_SENSOR_PIN 25

DHT dht(DHTPIN, DHTTYPE);

bool modeOtomatis = false;
bool modeManual = false;
bool pengirimanAktif = true;
bool relayAktifKarenaKebakaran = false;
int lastRelayState = LOW;

unsigned long lastSendTime = 0;
const unsigned long interval = 1000;

void setup() {
  delay(3000);
  Serial.begin(115200);
  while (!Serial);
  Serial.println("Memulai setup...");

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  Serial.println("Relay diset LOW");

  pinMode(FIRE_SENSOR_PIN, INPUT);
  pinMode(MQ2_SENSOR_PIN, INPUT);
  dht.begin();

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  delay(1000);
  if (!LoRa.begin(433E6)) {
    Serial.println("Gagal memulai LoRa");
    while (1);
  }
  Serial.println("LoRa siap menerima dan mengirim");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "pause") {
      pengirimanAktif = false;
      Serial.println("Pengiriman LoRa dihentikan");
    } else if (cmd == "resume") {
      pengirimanAktif = true;
      Serial.println("Pengiriman LoRa dilanjutkan");
    }
  }

  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String msg = "";
    while (LoRa.available()) {
      msg += (char)LoRa.read();
    }
    Serial.println("Pesan diterima: " + msg);

    if (msg == "on") {
      modeManual = true;
      modeOtomatis = false;
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("Mode manual - Relay ON");
    } else if (msg == "off") {
      modeManual = true;
      modeOtomatis = false;
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("Mode manual - Relay OFF");
    } else if (msg == "auto_on") {
      modeOtomatis = true;
      modeManual = false;
      Serial.println("Mode otomatis AKTIF");
    } else if (msg == "auto_off") {
      modeOtomatis = false;
      modeManual = false;
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("Mode otomatis NONAKTIF - Relay OFF");
    }
  }

  int fireDigital = digitalRead(FIRE_SENSOR_PIN);
  int asapDigital = digitalRead(MQ2_SENSOR_PIN);
  float suhuC = dht.readTemperature();
  int soilRaw = analogRead(SOIL_SENSOR_PIN);
  int kelembabanTanah = map(soilRaw, 4095, 0, 0, 100);

  Serial.println("Sensor:");
  Serial.println("  - Api: " + String(fireDigital == LOW ? "iya" : "tidak"));
  Serial.println("  - Asap: " + String(asapDigital == HIGH ? "iya" : "tidak"));
  Serial.println("  - Suhu: " + String(suhuC, 1) + "C");
  Serial.println("  - Tanah: " + String(kelembabanTanah) + "%");

  String statusApi = (fireDigital == LOW) ? "iya" : "tidak";

  if (modeOtomatis) {
    bool deteksiAsap = fireDigital == LOW;

    if (statusApi) {
      statusApi = "iya";
      digitalWrite(RELAY_PIN, HIGH);
      relayAktifKarenaKebakaran = true;
      Serial.println("Kebakaran! Relay ON");
    } else if (relayAktifKarenaKebakaran && fireDigital == HIGH) {
      digitalWrite(RELAY_PIN, LOW);
      relayAktifKarenaKebakaran = false;
      Serial.println("Api padam. Relay dimatikan otomatis");
    } else {
      statusApi = statusApi ? "mungkin" : "tidak";
      digitalWrite(RELAY_PIN, LOW);
      relayAktifKarenaKebakaran = false;
      Serial.println("Status: " + statusApi + " - Relay OFF");
    }

    if (pengirimanAktif) kirimLoRa(statusApi);
  }

  if (kelembabanTanah < 50) {
    if (pengirimanAktif) kirimLoRa("kering");
  } else if (kelembabanTanah > 70) {
    if (pengirimanAktif) kirimLoRa("lembab");
  } else {
    if (pengirimanAktif) kirimLoRa("ideal");
  }

  if (millis() - lastSendTime > interval) {
    lastSendTime = millis();
    String data = "api:" + String(fireDigital == LOW ? "iya" : "tidak") +
                  ",asap:" + String(asapDigital == HIGH ? "iya" : "tidak") +
                  ",suhu:" + String(suhuC, 1) + "C" +
                  ",tanah:" + String(kelembabanTanah) + "%" +
                  ",relay:" + String(digitalRead(RELAY_PIN) ? "on" : "off");
    if (pengirimanAktif) {
      kirimLoRa(data);
      Serial.println("Data lengkap dikirim: " + data);
    }
  }

  int currentRelayState = digitalRead(RELAY_PIN);
  if (currentRelayState != lastRelayState) {
    lastRelayState = currentRelayState;
    String statusPompa = currentRelayState == HIGH ? "pompa:on" : "pompa:off";
    if (pengirimanAktif) {
      kirimLoRa(statusPompa);
      Serial.println("Status pompa dikirim: " + statusPompa);
    }
  }

  delay(2000);
}

void kirimLoRa(String pesan) {
  Serial.println("LoRa kirim: " + pesan);
  LoRa.beginPacket();
  LoRa.print(pesan);
  LoRa.endPacket();
}
