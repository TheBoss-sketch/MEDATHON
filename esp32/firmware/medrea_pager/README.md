# MEDREA Pager Firmware (ESP32)

Physical clinical alert pager for doctors and clinical staff, receiving real-time diagnostic flags and medication alerts over WebSocket and rendering them on a 128x64 SSD1306 SPI OLED display.

## Pinout Configuration (SSD1306 SPI OLED)

| OLED Pin | ESP32 GPIO | Description |
|---|---|---|
| **GND** | GND | Ground |
| **VCC** | 3.3V | Power (3.3V) |
| **D0** | GPIO 18 | SPI Clock (`OLED_CLK`) |
| **D1** | GPIO 23 | SPI MOSI / Data (`OLED_MOSI`) |
| **RES** | GPIO 4 | Display Reset (`OLED_RESET`) |
| **DC** | GPIO 2 | Data / Command select (`OLED_DC`) |
| **CS** | GPIO 5 | Chip Select (`OLED_CS`) |

## Required Arduino Libraries
Install these via the **Arduino IDE Library Manager** (`Tools -> Manage Libraries...`):
1. **Adafruit SSD1306** by Adafruit
2. **Adafruit GFX Library** by Adafruit
3. **WebSockets** by Markus Sattler (`Links2004/arduinoWebSockets`)
4. **ArduinoJson** by Benoît Blanchon (version 6.x or 7.x)

## Setup & Flashing Instructions

1. Copy the configuration template:
   ```bash
   cp config.h.example config.h
   ```
2. Open `config.h` and configure:
   - `WIFI_SSID`: Your local Wi-Fi SSID
   - `WIFI_PASSWORD`: Your local Wi-Fi password
   - `BACKEND_HOST`: The local IPv4 address of your computer running the FastAPI backend (e.g., `192.168.1.50`). **Do not use `localhost`**, as ESP32 is a separate network node.
   - `BACKEND_PORT`: `8000`
   - `WS_PATH`: `"/ws/pager"`
3. Open `medrea_pager.ino` in Arduino IDE.
4. Select board: **ESP32 Dev Module** (or your specific ESP32 board).
5. Select the appropriate COM port.
6. Upload the sketch and open Serial Monitor at **115200 baud**.

## State Flow
1. **BOOT**: Displays MEDREA boot banner.
2. **CONNECTING TO WIFI**: Connects to the designated Wi-Fi AP.
3. **CONNECTING TO MEDREA**: Connects to `ws://<BACKEND_HOST>:8000/ws/pager`.
4. **MEDREA READY**: Device enters standby mode, ready to receive clinical alerts.
5. **ALERT RECEIVED**: Parses incoming `MEDREA_ALERT` JSON and renders High/Medium/Low priority banners and clinical reconciliation notes.
