# MEDREA ESP32 Pager Documentation

## Overview
The MEDREA Pager is a dedicated hardware client designed for clinical staff. In this first vertical slice, the pager connects to local Wi-Fi, establishes a persistent duplex WebSocket connection to the MEDREA backend, and displays incoming post-diagnosis reconciliation flags on an SPI-driven SSD1306 128x64 OLED display.

---

## Hardware Configuration

### Verified Pinout
The display utilizes 4-wire hardware SPI on the ESP32:

```text
ESP32 Dev Module                      SSD1306 SPI OLED (128x64)
+----------------+                    +----------------+
|            GND |------------------->| GND            |
|           3.3V |------------------->| VCC            |
|        GPIO 18 |------------------->| D0 (CLK/SCK)   |
|        GPIO 23 |------------------->| D1 (MOSI/DATA) |
|         GPIO 4 |------------------->| RES (RESET)    |
|         GPIO 2 |------------------->| DC  (A0/CMD)   |
|         GPIO 5 |------------------->| CS  (CHIP SEL) |
+----------------+                    +----------------+
```

---

## State Machine & UI Progression

The firmware operates on a non-blocking state machine in `medrea_pager.ino`:

```text
+-------------------+
|    STATE_BOOT     | ---> Displays "MEDREA Clinical Pager v0.1"
+-------------------+
          |
          v
+-------------------+
|  CONNECTING_WIFI  | ---> Connects to Wi-Fi AP (SSID from config.h)
+-------------------+
          |
          v
+-------------------+
| CONNECTING_MEDREA | ---> Connects to ws://<HOST>:<PORT>/ws/pager
+-------------------+
          |
          v
+-------------------+
|   MEDREA_READY    | ---> Inverted status header, standby message & IP
+-------------------+
          |
    (WebSocket Event)
          v
+-------------------+
|  ALERT_RECEIVED   | ---> High-contrast alert view with severity badge,
+-------------------+      Patient ID, clinical conflict, and Rx details.
```

---

## WebSocket Protocol Specification

### Outbound Alert Packet (Backend -> ESP32)
Delivered as a raw JSON text frame over `/ws/pager`:

```json
{
  "type": "MEDREA_ALERT",
  "severity": "HIGH",
  "patient_id": "P1042",
  "message": "Potential medication conflict",
  "diagnosis": "Bacterial infection",
  "medication": "Amoxicillin",
  "timestamp": "2026-09-15T01:00:00Z"
}
```

- **`type`**: Must be `"MEDREA_ALERT"` for the pager parser to accept.
- **`severity`**: `"LOW"`, `"MEDIUM"`, or `"HIGH"`.
- **`patient_id`**: String identifier (e.g., `"P1042"`).
- **`message`**: Concise summary rendered on the display body.
- **`diagnosis`** / **`medication`**: Displayed under `Dx:` or `Rx:` line.

### Inbound Acknowledgment Packet (ESP32 -> Backend)
Prepared in the firmware architecture for future physical acknowledge buttons:

```json
{
  "type": "ALERT_ACK",
  "patient_id": "P1042",
  "status": "ACKNOWLEDGED",
  "device_ip": "192.168.1.150",
  "timestamp": "2026-09-15T01:00:15Z"
}
```

---

## Required Libraries
Install the following via Arduino IDE:
1. `Adafruit SSD1306`
2. `Adafruit GFX Library`
3. `WebSockets` by Markus Sattler (`Links2004/arduinoWebSockets`)
4. `ArduinoJson` by Benoît Blanchon

---

## Configuration & Flashing
1. Copy `esp32/firmware/medrea_pager/config.h.example` to `config.h`.
2. Enter local Wi-Fi credentials and your computer's local LAN IP.
3. Open `esp32/firmware/medrea_pager/medrea_pager.ino` in Arduino IDE.
4. Select board **ESP32 Dev Module**, choose the USB COM port, and upload.
