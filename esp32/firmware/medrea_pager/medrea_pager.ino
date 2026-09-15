/**
 * ============================================================================
 * MEDREA Pager Firmware - Vertical Slice 1
 * Post-Diagnosis Reconciliation + Clinical Alert System
 * 
 * Target Hardware: ESP32 + 128x64 SSD1306 SPI OLED
 * Pin Configuration (Confirmed physically working):
 *   GND -> GND
 *   VCC -> 3.3V
 *   D0  -> GPIO 18 (OLED_CLK)
 *   D1  -> GPIO 23 (OLED_MOSI)
 *   RES -> GPIO 4  (OLED_RESET)
 *   DC  -> GPIO 2  (OLED_DC)
 *   CS  -> GPIO 5  (OLED_CS)
 * ============================================================================
 */

#include <WiFi.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// Include local configuration (untracked)
#if __has_include("config.h")
  #include "config.h"
#else
  #warning "config.h not found. Using placeholder defaults. Copy config.h.example to config.h!"
  #define WIFI_SSID     "YOUR_WIFI_SSID"
  #define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
  #define BACKEND_HOST  "192.168.1.100"
  #define BACKEND_PORT  8000
  #define WS_PATH       "/ws/pager"
#endif

// ============================================================================
// OLED Configuration
// ============================================================================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define OLED_MOSI  23
#define OLED_CLK   18
#define OLED_RESET 4
#define OLED_DC    2
#define OLED_CS    5

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &SPI,
  OLED_DC,
  OLED_RESET,
  OLED_CS
);

// ============================================================================
// Client & State Machine
// ============================================================================
WebSocketsClient webSocket;

enum DeviceState {
  STATE_BOOT,
  STATE_CONNECTING_WIFI,
  STATE_CONNECTING_MEDREA,
  STATE_MEDREA_READY,
  STATE_ALERT_RECEIVED
};

DeviceState currentState = STATE_BOOT;

// Current active alert storage
struct AlertData {
  String type;
  String severity;
  String patientId;
  String message;
  String diagnosis;
  String medication;
  unsigned long receivedAt;
} activeAlert;

// Timing trackers
unsigned long lastStatusCheck = 0;
const unsigned long STATUS_CHECK_INTERVAL = 2000;

// ============================================================================
// Display Renderers
// ============================================================================

void renderBootScreen() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(18, 10);
  display.println("MEDREA");
  display.setTextSize(1);
  display.setCursor(16, 38);
  display.println("Clinical Pager v0.1");
  display.display();
}

void renderConnectingWiFi() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(18, 5);
  display.println("MEDREA");
  
  display.setTextSize(1);
  display.setCursor(10, 32);
  display.println("Connecting Wi-Fi...");
  display.setCursor(10, 46);
  display.print("SSID: ");
  display.println(WIFI_SSID);
  display.display();
}

void renderConnectingBackend() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(18, 5);
  display.println("MEDREA");
  
  display.setTextSize(1);
  display.setCursor(10, 30);
  display.println("Wi-Fi Connected");
  display.setCursor(10, 45);
  display.println("Connecting Server...");
  display.display();
}

void renderReadyScreen() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  
  // Header bar
  display.fillRect(0, 0, SCREEN_WIDTH, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.println("MEDREA ALERT SYSTEM");
  
  // Body status
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(4, 22);
  display.println("STATUS: STANDBY");
  display.setCursor(4, 34);
  display.println("Waiting for alerts...");
  display.setCursor(4, 50);
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.display();
}

void renderAlertScreen(const AlertData& alert) {
  display.clearDisplay();
  
  // Header with severity banner
  display.fillRect(0, 0, SCREEN_WIDTH, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.print("MEDREA [");
  display.print(alert.severity);
  display.println("]");
  
  // Content
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(2, 18);
  display.print("Pt: ");
  display.println(alert.patientId);
  
  display.setCursor(2, 30);
  // Truncate message if too long for one line
  if (alert.message.length() > 20) {
    display.println(alert.message.substring(0, 19) + ".");
  } else {
    display.println(alert.message);
  }
  
  if (alert.medication.length() > 0) {
    display.setCursor(2, 43);
    display.print("Rx: ");
    display.println(alert.medication);
  } else if (alert.diagnosis.length() > 0) {
    display.setCursor(2, 43);
    display.print("Dx: ");
    display.println(alert.diagnosis);
  }
  
  display.setCursor(2, 55);
  display.println("Status: Action Req");
  
  display.display();
}

// ============================================================================
// Future Acknowledgment Hook (Prepared for Step 2 / Hardware extension)
// ============================================================================
void sendAcknowledgment(const String& patientId, const String& status = "ACKNOWLEDGED") {
  StaticJsonDocument<200> ackDoc;
  ackDoc["type"] = "ALERT_ACK";
  ackDoc["patient_id"] = patientId;
  ackDoc["status"] = status;
  ackDoc["device_ip"] = WiFi.localIP().toString();

  String payload;
  serializeJson(ackDoc, payload);
  webSocket.sendTXT(payload);
  Serial.print("[WS] Sent acknowledgment: ");
  Serial.println(payload);
}

// ============================================================================
// WebSocket Event Handler
// ============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected from MEDREA backend");
      if (currentState != STATE_ALERT_RECEIVED) {
        currentState = STATE_CONNECTING_MEDREA;
        renderConnectingBackend();
      }
      break;

    case WStype_CONNECTED:
      Serial.printf("[WS] Connected to: %s%s\n", BACKEND_HOST, WS_PATH);
      if (currentState != STATE_ALERT_RECEIVED) {
        currentState = STATE_MEDREA_READY;
        renderReadyScreen();
      }
      break;

    case WStype_TEXT: {
      Serial.printf("[WS] Received payload: %s\n", payload);
      
      // Parse JSON Alert
      StaticJsonDocument<512> doc;
      DeserializationError error = deserializeJson(doc, payload, length);
      
      if (error) {
        Serial.print(F("[JSON] Parse failed: "));
        Serial.println(error.f_str());
        return;
      }
      
      const char* msgType = doc["type"] | "";
      if (strcmp(msgType, "MEDREA_ALERT") == 0) {
        activeAlert.type = msgType;
        activeAlert.severity = (const char*)(doc["severity"] | "HIGH");
        activeAlert.patientId = (const char*)(doc["patient_id"] | "UNKNOWN");
        activeAlert.message = (const char*)(doc["message"] | "Clinical Alert");
        activeAlert.diagnosis = (const char*)(doc["diagnosis"] | "");
        activeAlert.medication = (const char*)(doc["medication"] | "");
        activeAlert.receivedAt = millis();
        
        currentState = STATE_ALERT_RECEIVED;
        renderAlertScreen(activeAlert);
        
        Serial.println("[ALERT] Display updated for incoming clinical alert");
      }
      break;
    }

    case WStype_BIN:
    case WStype_ERROR:
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
    case WStype_PING:
    case WStype_PONG:
      break;
  }
}

// ============================================================================
// Setup
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n--- MEDREA PAGER INITIALIZING ---");

  // Start SPI for OLED
  SPI.begin(OLED_CLK, -1, OLED_MOSI, OLED_CS);

  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC)) {
    Serial.println("OLED initialization failed!");
    while (true) {
      delay(1000);
    }
  }

  // Display boot screen
  currentState = STATE_BOOT;
  renderBootScreen();
  delay(1200);

  // Connect to Wi-Fi
  currentState = STATE_CONNECTING_WIFI;
  renderConnectingWiFi();
  
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // Connect to MEDREA WebSocket backend
  currentState = STATE_CONNECTING_MEDREA;
  renderConnectingBackend();

  Serial.printf("Connecting to MEDREA backend: ws://%s:%d%s\n", BACKEND_HOST, BACKEND_PORT, WS_PATH);
  webSocket.begin(BACKEND_HOST, BACKEND_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

// ============================================================================
// Loop
// ============================================================================
void loop() {
  // Service WebSocket network loop
  webSocket.loop();

  // Monitor Wi-Fi connection health
  unsigned long now = millis();
  if (now - lastStatusCheck >= STATUS_CHECK_INTERVAL) {
    lastStatusCheck = now;

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WiFi] Lost connection, reconnecting...");
      WiFi.reconnect();
    }
  }
}
