# Publishing guide

Repository URL:

```text
https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck
```

## GitHub description

```text
USB-connected ESP32 PC monitor and touch control deck for system telemetry, ChatGPT, Ollama, local voice services and configurable macros.
```

## Suggested topics

```text
esp32
platformio
clion
elecrow
pc-monitor
system-monitor
cyberdeck
macropad
ollama
local-ai
python
pyserial
psutil
librehardwaremonitor
tft-espi
ili9341
xpt2046
usb-serial
```

## Push the initial code

Run these commands from the extracted project directory:

```bash
git init
git add .
git commit -m "Initial release: ESP32 PC Control Deck"
git branch -M main
git remote add origin https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck.git
git push -u origin main
```

If the remote is already configured:

```bash
git remote -v
git add .
git commit -m "Initial release: ESP32 PC Control Deck"
git push -u origin main
```

## First release

Tag:

```text
v0.3.1
```

Release title:

```text
ESP32 PC Control Deck v0.3.1
```

Suggested release notes:

```text
First public release of ESP32 PC Control Deck.

Highlights:
- flicker-free CPU, RAM, GPU, VRAM, network and disk monitoring
- PC-synchronized clock in the display header
- contextual RAM and VRAM values
- temperature fallbacks through LibreHardwareMonitor
- ChatGPT, Ollama and local voice-server controls
- configurable URL, command, service, hotkey and text actions
- USB-only operation with no Wi-Fi or Bluetooth requirement
```

Create and push the tag:

```bash
git tag -a v0.3.1 -m "ESP32 PC Control Deck v0.3.1"
git push origin v0.3.1
```

## Add the YouTube video and GIF

In `README.md`, replace:

```text
PASTE_YOUTUBE_VIDEO_URL_HERE
```

Place the animated demo at:

```text
docs/media/control-deck-demo.gif
```

Then enable the GIF Markdown block in `README.md`.
