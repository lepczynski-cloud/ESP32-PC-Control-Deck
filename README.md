# ESP32 PC Control Deck

A small ESP32 touchscreen that monitors your computer and runs six configurable shortcuts over a single USB cable. Built for the Elecrow 2.8-inch ESP32 Solo Miner LCD Display.

**Website and browser installer:** https://esp32-pc-control-deck.lepczynski.it/  
**Full demo video:** https://www.youtube.com/watch?v=16eqHU4j9Fk  
**Repository:** https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck

[![ESP32 PC Control Deck on a desk](docs/media/ESP32_PC_Control_Deck.jpg)](https://esp32-pc-control-deck.lepczynski.it/)

## What it does

**PC monitor:** live CPU, RAM, GPU and VRAM usage, network download/upload, disk occupancy and activity, PC clock, and temperatures where sensors are available. NVIDIA GPU monitoring uses `nvidia-smi`. Windows CPU and drive temperatures can optionally come from LibreHardwareMonitor.

**Touch macros:** ChatGPT, local Ollama, voice server, terminal, system monitor / Task Manager, and lock PC. Button labels and actions are configured locally in `host/config.json` and can be changed without editing the ESP32 firmware.

[![Actual ESP32 PC Control Deck demo](docs/media/control-deck-demo.gif)](https://www.youtube.com/watch?v=16eqHU4j9Fk)

The USB-C connector on this classic ESP32-WROOM-32 board connects through a **CH340 USB-to-UART bridge**. It does not behave as a native USB HID keyboard. Instead, the display sends numeric macro IDs to a trusted Python program running on the computer.

## Flash from your browser

**No local PlatformIO toolchain is needed to install the firmware.**

1. Open **https://esp32-pc-control-deck.lepczynski.it/** using desktop **Chrome or Edge** over HTTPS.
2. Connect the supported Elecrow 2.8-inch ESP32 display using a USB data cable.
3. Close the PC bridge and any serial monitor. Only one program can access the serial port at a time.
4. Choose **Flash latest firmware**, select the CH340 port and follow the install prompts.
5. After the board reboots, calibrate the touch screen if prompted.
6. Download and run the **PC bridge** from the same website. Flashing firmware alone does not enable PC telemetry or macros.

The firmware is built by **Cloudflare Workers Builds directly from the `main` commit**. The page serves the most recent **successful** build. If a build fails, the previously published working installer remains available. The site, manifest, merged firmware and PC bridge download are published together. See [Website deployment](docs/WEB_INSTALLER.md).

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

This project uses Cloudflare Workers Builds with static assets. No separate hosting server, GitHub Actions, or manually generated firmware binaries are required. The build step is the same as the CrowPanel Rotary Buddy project:

```sh
bash scripts/build_pages.sh
```

The deploy step is:

```sh
npx wrangler deploy
```

A successful build runs the Python tests, compiles the actual PlatformIO firmware from the current Git revision, packages a merged ESP32 image and an ESP Web Tools manifest, builds a PC bridge download, and deploys everything together. The page displays the release version and commit ID. If the build fails, Cloudflare keeps serving the last successful deployment.

The original real GIF is kept intact in `docs/media/`; the build creates a smaller copy when needed because Cloudflare Workers has a 25 MiB limit per static asset. The website serves the photo and compressed version of the same demonstration locally. ESP Web Tools is bundled at build time; no CDN, API token in the device, or server-side application is necessary.

See [Cloudflare deployment](docs/WEB_INSTALLER.md) for the one-time Git connection and custom-domain steps.

## More projects

- [M5Stack Touch Control Deck](https://m5stack-touch-control-deck.lepczynski.it/)
- [CrowPanel Rotary Buddy](https://crowpanel-rotary-buddy.lepczynski.it/)
- [Admin Pocket Toolkit](https://admintoolkit.lepczynski.it/)
- [CrowPanel Pocket Arcade](https://github.com/lepczynski-cloud/crowpanel-pocket-arcade)
- [FreeDOOM on ESP32](https://github.com/lepczynski-cloud/crowpanel-freedoom)
- [Scratch to HTML Converter](https://sbtohtml.lepczynski.it/)

## License and disclosure

Source code: MIT, see [LICENSE](LICENSE). Third-party case designs retain their own licenses. The display was originally provided by Elecrow for review; this was not a paid sponsorship. See [SECURITY.md](SECURITY.md) for security notes.
