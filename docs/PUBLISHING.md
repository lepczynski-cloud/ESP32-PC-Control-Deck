# Publishing guide

Repository URL:

```text
https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck
```

## GitHub description

```text
Cross-platform USB-connected ESP32 system monitor and touch control deck for Windows, macOS and Linux.
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
macos
linux
cross-platform
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

## Release 0.4.0

Tag:

```text
v0.4.0
```

Release title:

```text
ESP32 PC Control Deck v0.4.0
```

Suggested release notes:

```text
Cross-platform host bridge release for ESP32 PC Control Deck.

Highlights:
- official Windows, macOS and Linux host support
- unchanged Windows launcher and Windows macro behavior
- improved macOS CH340 detection with /dev/cu.* preference
- improved Linux /dev/ttyUSB* detection and permission guidance
- new --list-ports serial diagnostic
- safer run_linux_macos.sh setup and dependency checks
- platform-aware LibreHardwareMonitor defaults
- 12 automated host tests
- existing firmware 0.3.3 remains compatible through protocol version 3
```

Create and push the tag:

```bash
git tag -a v0.4.0 -m "ESP32 PC Control Deck v0.4.0"
git push origin v0.4.0
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
