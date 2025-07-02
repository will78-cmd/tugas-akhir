#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include <SPI.h>
#include <LoRa.h>

#define WIFI_SSID "KOS PUTRA"
#define WIFI_PASSWORD "K0S54LS4"
#define API_KEY ""
#define DATABASE_URL "https://tugas-akhir-8ec00-default-rtdb.asia-southeast1.firebasedatabase.app/"
#define USER_EMAIL "dhanw70@gmail.com"
#define USER_PASSWORD "Wildan78"
#define PRIVATE_KEY ""
#define LORA_SS 5
#define LORA_RST 14
#define LORA_DIO0 2
#define BUZZER_PIN 27

FirebaseData fbdo;
FirebaseData streamFbdo;
FirebaseAuth auth;
FirebaseConfig config;

String lastManual = "";
String lastOtomatis = "";

void setupLoRa() {
  delay(2000);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("Gagal memulai LoRa");
    while (1);
  }
  Serial.println("LoRa Siap");
}

void streamCallback(FirebaseStream data) {
  String path = data.dataPath();
  String value = data.stringData();

  Serial.println("Perubahan Firebase: " + path + " => " + value);

  if (path == "/pompa/manual" && value != lastManual) {
    lastManual = value;
    if (value == "on" || value == "off") {
      LoRa.beginPacket();
      LoRa.print(value);
      LoRa.endPacket();
    }
  }

  if (path == "/pompa/otomatis" && value != lastOtomatis) {
    lastOtomatis = value;
    if (value == "aktif") {
      LoRa.beginPacket();
      LoRa.print("auto_on");
      LoRa.endPacket();
    } else if (value == "nonaktif") {
      LoRa.beginPacket();
      LoRa.print("auto_off");
      LoRa.endPacket();
    }
  }
}

void streamTimeoutCallback(bool timeout) {
  if (timeout) {
    Serial.println("Stream timeout, mencoba ulang...");
  }
}

void setup() {
  delay(3000);
  Serial.begin(115200);
  Serial.println("Memulai setup...");
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("WiFi tersambung");

  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  while (auth.token.uid == "") {
    delay(1000);
  }

  if (!Firebase.RTDB.beginStream(&streamFbdo, "/pompa")) {
    Serial.printf("Gagal stream: %s\n", streamFbdo.errorReason().c_str());
  }
  Firebase.RTDB.setStreamCallback(&streamFbdo, streamCallback, streamTimeoutCallback);

  setupLoRa();
}

void beepPendekDuaKali() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(1000);
    digitalWrite(BUZZER_PIN, LOW);
    delay(1000);
  }
}

void beepPanjang() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(5000);
  digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String data = "";
    while (LoRa.available()) {
      data += (char)LoRa.read();
    }
    Serial.println("Data LoRa: " + data);

    if (data.startsWith("api:")) {
      String apiStatus = data.substring(4);
      Firebase.RTDB.setString(&fbdo, "/sensor/api", apiStatus);
      Firebase.RTDB.setString(&fbdo, "/notif/kebakaran", apiStatus);
      if (lastOtomatis == "aktif") {
        if (apiStatus == "iya") beepPanjang();
        else if (apiStatus == "mungkin") beepPendekDuaKali();
      }
    } else if (data.startsWith("asap:")) {
      String asap = data.substring(5);
      Firebase.RTDB.setString(&fbdo, "/sensor/asap", asap);
    } else if (data.startsWith("suhu:")) {
      String suhu = data.substring(5);
      Firebase.RTDB.setString(&fbdo, "/sensor/suhu", suhu);
    } else if (data.startsWith("tanah:")) {
      String tanah = data.substring(6);
      Firebase.RTDB.setString(&fbdo, "/sensor/tanah", tanah);
      Firebase.RTDB.setInt(&fbdo, "/notif/tanah", tanah.toInt());
    } else if (data.startsWith("pompa:")) {
      String pompa = data.substring(6);
      Firebase.RTDB.setString(&fbdo, "/sensor/pompa", pompa);
    } else if (data.indexOf("api:") != -1) {
      // Format lengkap
      int idxApi = data.indexOf("api:");
      int idxAsap = data.indexOf(",asap:");
      int idxSuhu = data.indexOf(",suhu:");
      int idxTanah = data.indexOf(",tanah:");
      int idxRelay = data.indexOf(",relay:");

      if (idxApi >= 0 && idxAsap >= 0 && idxSuhu >= 0 && idxTanah >= 0 && idxRelay >= 0) {
        String api = data.substring(idxApi + 4, idxAsap);
        String asap = data.substring(idxAsap + 6, idxSuhu);
        String suhu = data.substring(idxSuhu + 6, idxTanah);
        String tanah = data.substring(idxTanah + 7, idxRelay);
        String relay = data.substring(idxRelay + 7);

        Firebase.RTDB.setString(&fbdo, "/sensor/api", api);
        Firebase.RTDB.setString(&fbdo, "/sensor/asap", asap);
        Firebase.RTDB.setString(&fbdo, "/sensor/suhu", suhu);
        Firebase.RTDB.setString(&fbdo, "/sensor/tanah", tanah);
        Firebase.RTDB.setString(&fbdo, "/pompa/status", relay);

        Firebase.RTDB.setString(&fbdo, "/notif/kebakaran", api);
        Firebase.RTDB.setInt(&fbdo, "/notif/tanah", tanah.toInt());

        if (lastOtomatis == "aktif") {
          if (api == "iya") beepPanjang();
          else if (api == "mungkin") beepPendekDuaKali();
        }
      }
    }
  }
}
