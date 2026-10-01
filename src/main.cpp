#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <TFT_eSPI.h>
#include <math.h>

namespace {
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr int SCREEN_W = 320;
constexpr int SCREEN_H = 240;
constexpr int BACKLIGHT_PIN = 27;
constexpr uint32_t STALE_AFTER_MS = 15000;
constexpr uint32_t TOUCH_DEBOUNCE_MS = 300;
constexpr char PROTOCOL_PREFIX[] = "DD:";
constexpr size_t PROTOCOL_PREFIX_LEN = 3;
constexpr uint8_t PROTOCOL_VERSION = 3;

constexpr uint16_t C_BG = 0x0841;
constexpr uint16_t C_PANEL = 0x1082;
constexpr uint16_t C_PANEL_2 = 0x18C3;
constexpr uint16_t C_TEXT = 0xFFFF;
constexpr uint16_t C_MUTED = 0xAD55;
constexpr uint16_t C_ACCENT = 0x07FF;
constexpr uint16_t C_GOOD = 0x07E0;
constexpr uint16_t C_WARN = 0xFFE0;
constexpr uint16_t C_BAD = 0xF800;
constexpr uint16_t C_BAR_BG = 0x2945;

TFT_eSPI tft;
Preferences prefs;

enum class Page : uint8_t { Monitor, Macros };
Page page = Page::Monitor;

struct Stats {
  float cpu = NAN;
  float ram = NAN;
  float gpu = NAN;
  float vram = NAN;
  float cpuTemp = NAN;
  float gpuTemp = NAN;
  float systemTemp = NAN;
  float diskTemp = NAN;
  float ramUsedGB = NAN;
  float ramTotalGB = NAN;
  float vramUsedGB = NAN;
  float vramTotalGB = NAN;
  float diskUsed = NAN;
  float diskReadMBs = NAN;
  float diskWriteMBs = NAN;
  float netDownMbps = NAN;
  float netUpMbps = NAN;
  uint32_t clockSecondsAtSync = 0;
  uint32_t clockSyncMs = 0;
  uint32_t lastUpdateMs = 0;
  bool clockValid = false;
  bool everUpdated = false;
} stats;

String macroLabels[6] = {
    "CHATGPT", "OLLAMA", "VOICE SERVER", "TERMINAL", "TASK MANAGER", "LOCK PC"};
String serialLine;
uint32_t lastTouchMs = 0;
bool fullRedrawRequested = true;
bool statsDirty = true;

float clampPct(float value) {
  if (isnan(value)) return 0.0f;
  if (value < 0.0f) return 0.0f;
  if (value > 100.0f) return 100.0f;
  return value;
}

String fmtValue(float value, unsigned int decimals = 0) {
  if (isnan(value)) return "--";
  return String(value, decimals);
}

uint16_t usageColor(float value) {
  if (isnan(value)) return C_MUTED;
  if (value < 70.0f) return C_GOOD;
  if (value < 90.0f) return C_WARN;
  return C_BAD;
}

bool parseClockText(const char *text, uint32_t &secondsOfDay) {
  if (!text || text[0] < '0' || text[0] > '9' || text[1] < '0' ||
      text[1] > '9' || text[2] != ':' || text[3] < '0' || text[3] > '9' ||
      text[4] < '0' || text[4] > '9') {
    return false;
  }

  const int hour = (text[0] - '0') * 10 + (text[1] - '0');
  const int minute = (text[3] - '0') * 10 + (text[4] - '0');
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return false;

  secondsOfDay = static_cast<uint32_t>(hour * 3600 + minute * 60);
  return true;
}

String currentClockText() {
  if (!stats.clockValid) return "--:--";

  const uint32_t elapsedSeconds = (millis() - stats.clockSyncMs) / 1000UL;
  const uint32_t secondsOfDay =
      (stats.clockSecondsAtSync + elapsedSeconds) % 86400UL;
  const uint32_t hour = secondsOfDay / 3600UL;
  const uint32_t minute = (secondsOfDay % 3600UL) / 60UL;

  char buffer[6];
  snprintf(buffer, sizeof(buffer), "%02lu:%02lu",
           static_cast<unsigned long>(hour),
           static_cast<unsigned long>(minute));
  return String(buffer);
}

String memoryText(float usedGB, float totalGB) {
  if (isnan(usedGB) || isnan(totalGB) || totalGB <= 0.0f) return "MEM N/A";
  const unsigned int totalDecimals = totalGB >= 10.0f ? 0U : 1U;
  return String(usedGB, 1) + "/" + String(totalGB, totalDecimals) + "G";
}

void drawHeaderStatic(const String &title) {
  tft.fillRect(0, 0, SCREEN_W, 28, C_PANEL);
  tft.setTextDatum(ML_DATUM);
  tft.setTextColor(C_TEXT, C_PANEL);
  tft.drawString(title, 8, 14, 2);
}

void drawHeaderDynamic() {
  const bool stale =
      stats.everUpdated && (millis() - stats.lastUpdateMs > STALE_AFTER_MS);
  uint16_t statusColor = C_MUTED;
  if (stats.everUpdated) statusColor = stale ? C_WARN : C_GOOD;

  // USB state has its own fixed area.
  tft.fillRect(168, 0, 62, 28, C_PANEL);
  tft.fillCircle(178, 14, 4, statusColor);
  tft.setTextDatum(ML_DATUM);
  tft.setTextColor(C_MUTED, C_PANEL);
  tft.drawString("USB", 187, 14, 1);

  // Right-align the clock in a wider fixed area. This makes it easier to see
  // on the 320x240 display and avoids overlap with the USB status text.
  tft.fillRect(230, 0, 90, 28, C_PANEL);
  tft.setTextDatum(MR_DATUM);
  tft.setTextColor(stats.clockValid ? C_TEXT : C_WARN, C_PANEL);
  tft.drawString(currentClockText(), 314, 14, 2);
}

void drawMetricStatic(const char *label, int y) {
  constexpr int barX = 54;
  constexpr int barW = 123;
  constexpr int barH = 13;

  tft.setTextDatum(ML_DATUM);
  tft.setTextColor(C_TEXT, C_BG);
  tft.drawString(label, 8, y + 7, 2);
  tft.fillRoundRect(barX, y, barW, barH, 3, C_BAR_BG);
}

void drawMetricDynamic(float value, const String &auxText, uint16_t auxColor,
                       uint8_t auxFont, int y) {
  constexpr int barX = 54;
  constexpr int barW = 123;
  constexpr int barH = 13;

  tft.fillRoundRect(barX, y, barW, barH, 3, C_BAR_BG);
  const int fillW = static_cast<int>((barW - 2) * clampPct(value) / 100.0f);
  if (fillW > 0) {
    tft.fillRoundRect(barX + 1, y + 1, fillW, barH - 2, 2,
                      usageColor(value));
  }

  tft.fillRect(181, y - 2, 139, 18, C_BG);

  tft.setTextDatum(MR_DATUM);
  tft.setTextColor(usageColor(value), C_BG);
  tft.drawString(fmtValue(value) + "%", 228, y + 7, 2);

  tft.setTextColor(auxColor, C_BG);
  tft.drawString(auxText, 314, y + 7, auxFont);
}

void drawInfoBoxStatic(int x, int y, int w, int h, const String &title) {
  tft.fillRoundRect(x, y, w, h, 5, C_PANEL_2);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_MUTED, C_PANEL_2);
  tft.drawString(title, x + 6, y + 5, 2);
}

void drawInfoBoxDynamic(int x, int y, int w, int h, const String &line1,
                        const String &line2) {
  tft.fillRect(x + 5, y + 20, w - 10, h - 25, C_PANEL_2);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_TEXT, C_PANEL_2);
  tft.drawString(line1, x + 6, y + 22, 2);
  tft.setTextColor(C_MUTED, C_PANEL_2);
  tft.drawString(line2, x + 6, y + 43, 1);
}

void drawFooter(Page selected) {
  constexpr int y = 212;
  constexpr int h = 28;
  constexpr int w = 160;

  tft.fillRect(0, y, SCREEN_W, h, C_PANEL);

  tft.fillRect(0, y, w, h, selected == Page::Monitor ? C_ACCENT : C_PANEL);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(selected == Page::Monitor ? TFT_BLACK : C_TEXT,
                   selected == Page::Monitor ? C_ACCENT : C_PANEL);
  tft.drawString("PC MONITOR", 80, y + h / 2, 2);

  tft.fillRect(w, y, w, h, selected == Page::Macros ? C_ACCENT : C_PANEL);
  tft.setTextColor(selected == Page::Macros ? TFT_BLACK : C_TEXT,
                   selected == Page::Macros ? C_ACCENT : C_PANEL);
  tft.drawString("CONTROLS", 240, y + h / 2, 2);
}

void drawMonitorDynamic() {
  drawHeaderDynamic();

  String cpuAux = "TEMP N/A";
  uint16_t cpuAuxColor = C_MUTED;
  uint8_t cpuAuxFont = 1;
  if (!isnan(stats.cpuTemp)) {
    cpuAux = String(stats.cpuTemp, 0) + "C";
    cpuAuxColor = C_TEXT;
    cpuAuxFont = 2;
  } else if (!isnan(stats.systemTemp)) {
    cpuAux = "SYS " + String(stats.systemTemp, 0) + "C";
    cpuAuxColor = C_WARN;
  }

  String gpuAux = "TEMP N/A";
  uint16_t gpuAuxColor = C_MUTED;
  uint8_t gpuAuxFont = 1;
  if (!isnan(stats.gpuTemp)) {
    gpuAux = String(stats.gpuTemp, 0) + "C";
    gpuAuxColor = C_TEXT;
    gpuAuxFont = 2;
  }

  drawMetricDynamic(stats.cpu, cpuAux, cpuAuxColor, cpuAuxFont, 38);
  drawMetricDynamic(stats.ram, memoryText(stats.ramUsedGB, stats.ramTotalGB),
                    C_MUTED, 1, 61);
  drawMetricDynamic(stats.gpu, gpuAux, gpuAuxColor, gpuAuxFont, 84);
  drawMetricDynamic(stats.vram,
                    memoryText(stats.vramUsedGB, stats.vramTotalGB), C_MUTED,
                    1, 107);

  const String net1 = "D " + fmtValue(stats.netDownMbps, 1) + " Mb/s";
  const String net2 = "U " + fmtValue(stats.netUpMbps, 1) + " Mb/s";
  drawInfoBoxDynamic(8, 137, 148, 66, net1, net2);

  const String disk1 = "USED " + fmtValue(stats.diskUsed, 0) + "%";
  String disk2 = "R " + fmtValue(stats.diskReadMBs, 1) + " W " +
                 fmtValue(stats.diskWriteMBs, 1);
  if (!isnan(stats.diskTemp)) {
    disk2 += " T" + String(stats.diskTemp, 0) + "C";
  } else {
    disk2 += " MB/s";
  }
  drawInfoBoxDynamic(164, 137, 148, 66, disk1, disk2);
}

void drawMonitorFull() {
  tft.fillScreen(C_BG);
  drawHeaderStatic("PC CONTROL DECK");

  drawMetricStatic("CPU", 38);
  drawMetricStatic("RAM", 61);
  drawMetricStatic("GPU", 84);
  drawMetricStatic("VRAM", 107);

  drawInfoBoxStatic(8, 137, 148, 66, "NETWORK");
  drawInfoBoxStatic(164, 137, 148, 66, "DISK");
  drawFooter(Page::Monitor);
  drawMonitorDynamic();
}

void splitMacroLabel(const String &label, String &line1, String &line2) {
  String normalized = label;
  normalized.trim();
  const int newlineIndex = normalized.indexOf('\n');
  if (newlineIndex >= 0) {
    line1 = normalized.substring(0, newlineIndex);
    line2 = normalized.substring(newlineIndex + 1);
    line1.trim();
    line2.trim();
    return;
  }

  if (normalized.length() <= 11) {
    line1 = normalized;
    line2 = "";
    return;
  }

  int bestSpace = -1;
  int bestDistance = 999;
  const int middle = normalized.length() / 2;
  for (int i = 1; i < static_cast<int>(normalized.length()) - 1; ++i) {
    if (normalized.charAt(i) == ' ') {
      const int distance = abs(i - middle);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestSpace = i;
      }
    }
  }

  if (bestSpace > 0) {
    line1 = normalized.substring(0, bestSpace);
    line2 = normalized.substring(bestSpace + 1);
  } else {
    line1 = normalized.substring(0, 10);
    line2 = normalized.substring(10);
  }
  line1.trim();
  line2.trim();
}

void drawMacroButton(uint8_t id, int x, int y, int w, int h) {
  tft.fillRoundRect(x, y, w, h, 7, C_PANEL_2);
  tft.drawRoundRect(x, y, w, h, 7, C_ACCENT);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(C_MUTED, C_PANEL_2);
  tft.drawString(String(id), x + 5, y + 4, 1);

  String line1;
  String line2;
  splitMacroLabel(macroLabels[id - 1], line1, line2);

  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(C_TEXT, C_PANEL_2);
  if (line2.length() == 0) {
    tft.drawString(line1, x + w / 2, y + h / 2 - 2, 2);
  } else {
    tft.drawString(line1, x + w / 2, y + h / 2 - 12, 2);
    tft.drawString(line2, x + w / 2, y + h / 2 + 7, 2);
  }
}

void drawMacrosFull() {
  tft.fillScreen(C_BG);
  drawHeaderStatic("AI & PC CONTROLS");
  drawHeaderDynamic();

  constexpr int gap = 7;
  constexpr int x0 = 8;
  constexpr int y0 = 36;
  constexpr int bw = 96;
  constexpr int bh = 78;

  for (int i = 0; i < 6; ++i) {
    const int col = i % 3;
    const int row = i / 3;
    drawMacroButton(i + 1, x0 + col * (bw + gap), y0 + row * (bh + gap),
                    bw, bh);
  }
  drawFooter(Page::Macros);
}

void renderFull() {
  if (page == Page::Monitor) {
    drawMonitorFull();
  } else {
    drawMacrosFull();
  }
  fullRedrawRequested = false;
  statsDirty = false;
}

void sendFrame(JsonDocument &doc) {
  Serial.print(PROTOCOL_PREFIX);
  serializeJson(doc, Serial);
  Serial.println();
}

void sendSimpleFrame(const char *type) {
  JsonDocument doc;
  doc["type"] = type;
  sendFrame(doc);
}

void sendMacro(uint8_t id) {
  JsonDocument doc;
  doc["type"] = "macro";
  doc["id"] = id;
  sendFrame(doc);
}

void flashMacro(uint8_t id) {
  const int index = id - 1;
  constexpr int gap = 7;
  constexpr int x0 = 8;
  constexpr int y0 = 36;
  constexpr int bw = 96;
  constexpr int bh = 78;
  const int col = index % 3;
  const int row = index / 3;
  const int x = x0 + col * (bw + gap);
  const int y = y0 + row * (bh + gap);

  tft.drawRoundRect(x + 1, y + 1, bw - 2, bh - 2, 7, C_GOOD);
  delay(60);
  drawMacroButton(id, x, y, bw, bh);
}

void handleTouch() {
  if (millis() - lastTouchMs < TOUCH_DEBOUNCE_MS) return;

  uint16_t x = 0;
  uint16_t y = 0;
  if (!tft.getTouch(&x, &y)) return;
  lastTouchMs = millis();

  if (y >= 212) {
    const Page requested = (x < 160) ? Page::Monitor : Page::Macros;
    if (requested != page) {
      page = requested;
      fullRedrawRequested = true;
    }
    return;
  }

  if (page != Page::Macros || y < 36 || y >= 199) return;

  constexpr int gap = 7;
  constexpr int x0 = 8;
  constexpr int y0 = 36;
  constexpr int bw = 96;
  constexpr int bh = 78;

  for (int i = 0; i < 6; ++i) {
    const int col = i % 3;
    const int row = i / 3;
    const int bx = x0 + col * (bw + gap);
    const int by = y0 + row * (bh + gap);
    if (x >= bx && x < bx + bw && y >= by && y < by + bh) {
      flashMacro(i + 1);
      sendMacro(i + 1);
      return;
    }
  }
}

float readFloat(JsonVariantConst value, float fallback = NAN) {
  if (value.isNull()) return fallback;
  return value.as<float>();
}

void syncClock(JsonDocument &doc) {
  if (!doc["clock_seconds"].isNull()) {
    const int32_t seconds = doc["clock_seconds"].as<int32_t>();
    if (seconds >= 0 && seconds < 86400) {
      stats.clockSecondsAtSync = static_cast<uint32_t>(seconds);
      stats.clockSyncMs = millis();
      stats.clockValid = true;
      return;
    }
  }

  const char *clockText = doc["clock"] | nullptr;
  uint32_t secondsOfDay = 0;
  if (parseClockText(clockText, secondsOfDay)) {
    stats.clockSecondsAtSync = secondsOfDay;
    stats.clockSyncMs = millis();
    stats.clockValid = true;
  }
}

void handleStats(JsonDocument &doc) {
  stats.cpu = readFloat(doc["cpu"]);
  stats.ram = readFloat(doc["ram"]);
  stats.gpu = readFloat(doc["gpu"]);
  stats.vram = readFloat(doc["vram"]);
  stats.cpuTemp = readFloat(doc["cpu_temp"]);
  stats.gpuTemp = readFloat(doc["gpu_temp"]);
  stats.systemTemp = readFloat(doc["system_temp"]);
  stats.diskTemp = readFloat(doc["disk_temp"]);
  stats.ramUsedGB = readFloat(doc["ram_used_gb"]);
  stats.ramTotalGB = readFloat(doc["ram_total_gb"]);
  stats.vramUsedGB = readFloat(doc["vram_used_gb"]);
  stats.vramTotalGB = readFloat(doc["vram_total_gb"]);
  stats.diskUsed = readFloat(doc["disk_used"]);
  stats.diskReadMBs = readFloat(doc["disk_read_mbs"]);
  stats.diskWriteMBs = readFloat(doc["disk_write_mbs"]);
  stats.netDownMbps = readFloat(doc["net_down_mbps"]);
  stats.netUpMbps = readFloat(doc["net_up_mbps"]);
  syncClock(doc);

  stats.lastUpdateMs = millis();
  stats.everUpdated = true;
  statsDirty = true;
}

void handleConfig(JsonDocument &doc) {
  JsonArrayConst macros = doc["macros"].as<JsonArrayConst>();
  bool labelsChanged = false;

  for (JsonObjectConst item : macros) {
    const int id = item["id"] | 0;
    const char *label = item["label"] | "";
    if (id < 1 || id > 6 || !label || label[0] == '\0') continue;

    String next(label);
    if (next.length() > 22) next = next.substring(0, 22);
    if (macroLabels[id - 1] != next) {
      macroLabels[id - 1] = next;
      labelsChanged = true;
    }
  }

  if (labelsChanged && page == Page::Macros) {
    fullRedrawRequested = true;
  }
}

void processSerialLine(const String &line) {
  bool framed = false;
  String payload;
  if (line.startsWith(PROTOCOL_PREFIX)) {
    if (line.length() <= PROTOCOL_PREFIX_LEN) return;
    payload = line.substring(PROTOCOL_PREFIX_LEN);
    framed = true;
  } else if (line.startsWith("{")) {
    payload = line;
  } else {
    return;
  }

  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    if (framed) {
      JsonDocument errorDoc;
      errorDoc["type"] = "error";
      errorDoc["code"] = "invalid_json";
      errorDoc["detail"] = error.c_str();
      sendFrame(errorDoc);
    }
    return;
  }

  const char *type = doc["type"] | "";
  if (strcmp(type, "stats") == 0) {
    handleStats(doc);
  } else if (strcmp(type, "config") == 0) {
    handleConfig(doc);
  } else if (strcmp(type, "ping") == 0) {
    sendSimpleFrame("pong");
  } else if (strcmp(type, "recalibrate") == 0) {
    prefs.remove("touchcal");
    sendSimpleFrame("rebooting");
    delay(100);
    ESP.restart();
  }
}

void pollSerial() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      serialLine.trim();
      processSerialLine(serialLine);
      serialLine = "";
    } else if (c != '\r') {
      if (serialLine.length() < 2048) {
        serialLine += c;
      } else {
        serialLine = "";
      }
    }
  }
}

void setupTouchCalibration() {
  uint16_t calData[5] = {0};
  prefs.begin("deskdeck", false);
  const size_t length = prefs.getBytesLength("touchcal");

  if (length == sizeof(calData)) {
    prefs.getBytes("touchcal", calData, sizeof(calData));
    tft.setTouch(calData);
    return;
  }

  tft.fillScreen(TFT_BLACK);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString("FIRST START", SCREEN_W / 2, 28, 4);
  tft.drawString("Touch calibration", SCREEN_W / 2, 66, 2);
  tft.drawString("Use the stylus and touch", SCREEN_W / 2, 92, 2);
  tft.drawString("the marked corners.", SCREEN_W / 2, 114, 2);
  delay(1200);

  tft.calibrateTouch(calData, TFT_MAGENTA, TFT_BLACK, 15);
  tft.setTouch(calData);
  prefs.putBytes("touchcal", calData, sizeof(calData));
}
}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  serialLine.reserve(2048);

  pinMode(BACKLIGHT_PIN, OUTPUT);
  digitalWrite(BACKLIGHT_PIN, HIGH);

  tft.init();
  tft.setRotation(1);
  setupTouchCalibration();
  renderFull();

  JsonDocument hello;
  hello["type"] = "hello";
  hello["device"] = "ESP32 PC Control Deck";
  hello["firmware"] = "0.3.3";
  hello["protocol"] = PROTOCOL_VERSION;
  sendFrame(hello);
}

void loop() {
  pollSerial();
  handleTouch();

  if (fullRedrawRequested) {
    renderFull();
  } else if (statsDirty) {
    if (page == Page::Monitor) {
      drawMonitorDynamic();
    } else {
      drawHeaderDynamic();
    }
    statsDirty = false;
  }

  static uint32_t lastHeaderRefresh = 0;
  if (millis() - lastHeaderRefresh >= 1000) {
    lastHeaderRefresh = millis();
    drawHeaderDynamic();
  }

  delay(8);
}
