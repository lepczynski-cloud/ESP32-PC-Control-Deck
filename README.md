# ESP32 PC Control Deck

A small ESP32 touchscreen that monitors your computer and runs six configurable shortcuts over a single USB cable. Built for the Elecrow 2.8-inch ESP32 Solo Miner LCD Display.

**Website and browser installer:** https://esp32-pc-control-deck.lepczynski.it/  
**Full demo video:** https://www.youtube.com/watch?v=16eqHU4j9Fk  
**Repository:** https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck

[![ESP32 PC Control Deck on a desk](https://esp32-pc-control-deck.lepczynski.it/media/ESP32_PC_Control_Deck.jpg)](https://esp32-pc-control-deck.lepczynski.it/)

## What it does

**PC monitor:** live CPU, RAM, GPU and VRAM usage, network download/upload, disk occupancy and activity, PC clock, and temperatures where sensors are available. NVIDIA GPU monitoring uses `nvidia-smi`. Windows CPU and drive temperatures can optionally come from LibreHardwareMonitor.

**Touch macros:** ChatGPT, local Ollama, voice server, terminal, system monitor / Task Manager, and lock PC. Button labels and actions are configured locally in `host/config.json` and can be changed without editing the ESP32 firmware.

[![Actual ESP32 PC Control Deck demo](https://esp32-pc-control-deck.lepczynski.it/media/control-deck-demo.gif)](https://www.youtube.com/watch?v=16eqHU4j9Fk)

The USB-C connector on this classic ESP32-WROOM-32 board connects through a **CH340 USB-to-UART bridge**. It does not behave as a native USB HID keyboard. Instead, the display sends numeric macro IDs to a trusted Python program running on the computer.

## Flash from your browser

**No local PlatformIO toolchain is needed to install the firmware.**

1. Open **https://esp32-pc-control-deck.lepczynski.it/** using desktop **Chrome or Edge** over HTTPS.
2. Connect the supported Elecrow 2.8-inch ESP32 display using a USB data cable.
3. Close the PC bridge and any serial monitor. Only one program can access the serial port at a time.
4. Choose **Flash latest firmware**, select the CH340 port and follow the install prompts.
5. After the board reboots, calibrate the touch screen if prompted.
6. Download and run the **PC bridge** from the same website. Flashing firmware alone does not enable PC telemetry or macros.

The firmware is built by **GitHub Actions from the current `main` commit**. The page serves the most recent **successful** build. If a build fails, the previously published working installer remains available. The site, manifest, merged firmware and PC bridge download are published together. See [Website deployment](docs/WEB_INSTALLER.md).

**Supported hardware:** [Elecrow 2 PACK 2.8-inch ESP32 Solo Miner LCD Display](https://www.elecrow.com/2-8inch-esp32-miner-lcd-display-2pcs-cryptocurrency-solo-miner-with-1000kh-s-hashrate.html), ESP32-WROOM-32-N4, 4 MB flash, ILI9341V 320 x 240 TFT, XPT2046 resistive touch and CH340 serial.

## PC bridge: required after flashing

The firmware receives data from the computer. You must also install **Python 3** and keep the bridge running on the computer for monitoring and macros. The bridge uses USB only, not Wi-Fi or Bluetooth.

Download the [PC bridge package](https://esp32-pc-control-deck.lepczynski.it/downloads/PC-Control-Deck-PC-Bridge.zip) and extract it before starting.

### Windows

Run `host\run_windows.bat` from the extracted folder. The first run creates a Python virtual environment, installs dependencies, copies the example config to `host/config.json` and starts the bridge.

For autostart after Windows login, run once from the extracted project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\host\install_autostart_windows.ps1
```

To remove the autostart shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\host\uninstall_autostart_windows.ps1
```

### macOS / Linux

Run from the extracted project folder:

```sh
sh host/run_linux_macos.sh
```

To list serial ports:

```sh
sh host/run_linux_macos.sh --list-ports
```

Some shortcuts and temperature sensors depend on your desktop environment and operating system. On Linux you may need permission to access `/dev/ttyUSB0`. See [macOS and Linux notes](docs/LINUX_MACOS.md).

### Configure macros and sensors

Edit the local `host/config.json` file, which is copied from `host/config.example.json`. Set your voice server launch script, adjust buttons and configure your serial port if auto-detection fails. Do **not** commit personal `host/config.json` files. No account credentials or secrets are stored on the ESP32.

On Windows you can optionally start [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) and enable **Options > Remote Web Server > Run**. The bridge can read local sensor data from `http://127.0.0.1:8085/data.json`.

## How it works

```text
Windows / macOS / Linux
  Python bridge: system telemetry + configured macros
                 |  USB serial via CH340
                 |
Elecrow ESP32: PC monitor screen + six touch buttons
```

The ESP32 handles display and touch input. The PC bridge handles system data and launches trusted, locally configured actions. The protocol consists of newline-delimited JSON messages prefixed with `DD:`. See [Protocol](docs/PROTOCOL.md), [Hardware](docs/HARDWARE.md), [Macros](docs/MACROS.md) and [Temperatures](docs/TEMPERATURES.md).

## Developer build (optional)

The website handles normal firmware installation without needing a build environment. For changing firmware, use PlatformIO or CLion:

```sh
pio run -e esp32_pc_control_deck
pio run -t upload -e esp32_pc_control_deck
```

## Automatic website and firmware releases

The repository contains the static site in `site/`, its build script in `scripts/`, and a GitHub Actions workflow in `.github/workflows/`.

Every successful push to `main`:

1. Runs Python tests and builds the firmware using `platformio.ini`.
2. Packages a merged ESP32 binary, ESP Web Tools manifest, build metadata and the PC bridge from that **same commit**.
3. Publishes the entire site to the generated `cloudflare-pages` branch.
4. Triggers Cloudflare Pages to host the new release automatically, after a one-time Git integration setup.

There is no application server, backend or API key in the firmware. The browser installer uses the open source ESP Web Tools client library, bundled during GitHub Actions and hosted locally by Cloudflare Pages alongside the firmware. No separate installer server or runtime CDN is required. See [deployment instructions](docs/WEB_INSTALLER.md).

## More projects

- [M5Stack Touch Control Deck](https://m5stack-touch-control-deck.lepczynski.it/)
- [CrowPanel Rotary Buddy](https://crowpanel-rotary-buddy.lepczynski.it/)
- [Admin Pocket Toolkit](https://admintoolkit.lepczynski.it/)
- [CrowPanel Pocket Arcade](https://github.com/lepczynski-cloud/crowpanel-pocket-arcade)
- [FreeDOOM on ESP32](https://github.com/lepczynski-cloud/crowpanel-freedoom)
- [Scratch to HTML Converter](https://sbtohtml.lepczynski.it/)

## License and disclosure

Source code: MIT, see [LICENSE](LICENSE). Third-party case designs retain their own licenses. The display was originally provided by Elecrow for review; this was not a paid sponsorship. See [SECURITY.md](SECURITY.md) for security notes.
