# Changelog

All notable changes to this project are documented here.

## [0.4.0] - 2026-10-01

### Added

- Official macOS and Linux quick-start instructions and troubleshooting guide.
- `--list-ports` diagnostic command for visible serial devices and automatic selection.
- macOS recognition for `/dev/cu.wchusbserial*` and `/dev/cu.usbserial*` devices even when USB metadata is incomplete.
- Linux recognition for common `/dev/ttyUSB*` CH340 devices and a permission hint for access errors.
- `--setup-only` mode in `run_linux_macos.sh`.
- Automated tests for Windows, macOS and Linux serial-port selection and platform configuration.

### Changed

- Improved `run_linux_macos.sh` with Python version checks, clearer setup errors, dependency-change detection and argument forwarding.
- macOS now prefers the non-blocking `/dev/cu.*` port over the matching `/dev/tty.*` port.
- LibreHardwareMonitor remains enabled by default on Windows and is disabled by default on macOS and Linux.
- Host bridge version increased to 0.4.0. Firmware protocol remains version 3 and firmware 0.3.3 stays compatible.

### Compatibility

- Windows launcher, Windows macro commands and firmware behavior are unchanged.

## [0.3.3] - 2026-09-13

### Fixed

- Fixed README media rendering by using Markdown image syntax for the project JPG and demo GIF.
- Added repository placeholder media files so the README does not show broken images before real media is added.
- Added Git attributes for JPG and GIF binary files.
- Updated release and publishing notes to version 0.3.3.

## [0.3.2] - 2026-09-12

### Changed

- Renamed the PlatformIO environment to `esp32_pc_control_deck`.
- Updated all build and upload commands to use `pio run -e esp32_pc_control_deck`.
- Added explicit target-device information for the Elecrow 2.8-inch ESP32 Solo Miner LCD Display.
- Added the Elecrow product page to README and hardware documentation.
- Prepared a clean public repository package for `ESP32-PC-Control-Deck`.
- Removed the GitHub Actions workflow from the default package to keep the first public release simple.
- Replaced private local voice-server paths with placeholder paths in public examples.
- Updated repository links to `https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck`.
- Kept documentation in plain English and ASCII-only formatting.

### Fixed

- Made the header clock area wider and right-aligned to improve visibility on the display.
- Cleaned minor duplicate literals in the host bridge temperature dictionary.

## [0.3.0] - 2026-08-26

### Added

- Project name: ESP32 PC Control Deck.
- Default ChatGPT, Ollama and local voice-server controls on the top macro row.
- `service` macro action with an optional health endpoint to avoid duplicate service processes.
- Ollama health check through `http://127.0.0.1:11434/api/tags`.
- RAM and VRAM used/total values.
- Optional motherboard/system and SSD/NVMe temperatures.
- `--list-temperatures` diagnostic command.
- Two-line labels for longer touch-control names.
- Publishing guide and media placeholders.

### Fixed

- Clock not appearing in the right side of the header.
- Clock now uses seconds since midnight and advances locally on the ESP32.
- LibreHardwareMonitor parsing no longer requires a `Type` field on every sensor leaf.
- Temperature discovery now recognizes sensor IDs containing `/temperature/` and parent temperature categories.
- RAM and VRAM rows no longer display meaningless temperature placeholders.

### Changed

- Serial protocol version increased to 3.
- Monitor layout now uses contextual right-side values.
- Default controls are ChatGPT, Ollama, Voice Server, Terminal, Task Manager and Lock PC.
- Firmware PlatformIO environment renamed to `esp32_pc_control_deck`.
- Host bridge renamed to `control_deck_bridge.py`.

## [0.2.0] - 2026-08-22

### Added

- PC clock field in the header.
- Optional Windows temperature support through the local LibreHardwareMonitor web server.
- `text` macro action.
- Media-key support.
- Windows startup helper scripts.
- Versioned `DD:` serial framing protocol.

### Fixed

- Full-screen redraw on every telemetry update.
- Full-screen redraw on the macro page.
- `ERR JSON InvalidInput` caused by unrelated serial text.

## [0.1.1] - 2026-08-22

- Matched the TFT pinout and PlatformIO environment to the Elecrow board used by the Pocket Arcade project.
- Fixed the ambiguous Arduino `String(float, decimals)` compilation error.

## [0.1.0] - 2026-08-20

- Initial USB PC monitor and six-button macro prototype.
