# macOS and Linux host bridge

Version 0.4.0 adds an officially documented macOS and Linux launcher path while keeping the Windows launcher and Windows actions unchanged.

The ESP32 firmware does not need a platform-specific build. The same USB serial protocol is used on Windows, macOS and Linux. An existing display running firmware 0.3.3 with protocol 3 is compatible with host bridge 0.4.0.

## Correct way to start it

From the repository root:

```bash
chmod +x host/run_linux_macos.sh
./host/run_linux_macos.sh
```

Or, without changing the executable bit:

```bash
sh host/run_linux_macos.sh
```

From inside the `host` directory:

```bash
./run_linux_macos.sh
```

The launcher is a shell script. These commands are incorrect:

```text
cd host/run_linux_macos.sh
python3 run_linux_macos.sh
```

`cd` accepts a directory, not a file. Passing a shell script to Python makes Python try to parse shell syntax and produces a `SyntaxError`.

## What the launcher does

On the first run, `run_linux_macos.sh`:

1. finds `python3` or the executable selected through `PYTHON_BIN`;
2. verifies Python 3.9 or newer;
3. creates `host/.venv`;
4. installs the packages from `host/requirements.txt`;
5. creates `host/config.json` from the public example when needed;
6. starts `control_deck_bridge.py`.

Later runs reuse the virtual environment. Dependencies are installed again only if the requirements change or a required package is missing.

To prepare the environment without starting the long-running bridge:

```bash
./host/run_linux_macos.sh --setup-only
```

## Check USB serial detection

Connect the display and run:

```bash
./host/run_linux_macos.sh --list-ports
```

The command prints every visible serial device, its description, manufacturer and USB VID:PID, followed by the port selected for the Control Deck.

The bridge recognizes the CH340/CH341 identifiers and common WCH/QinHeng descriptions. It also recognizes common device names when macOS or Linux does not expose USB metadata.

Typical ports:

```text
macOS: /dev/cu.wchusbserial1420
macOS: /dev/cu.usbserial-110
Linux: /dev/ttyUSB0
```

On macOS, `/dev/cu.*` is preferred over the matching `/dev/tty.*` device. If no new port appears after connecting the display, verify that the USB-C cable or adapter supports data and reconnect the device before changing the configuration.

If automatic selection does not work, edit the ignored local file `host/config.json`:

```json
{
  "serial_port": "/dev/cu.wchusbserial1420"
}
```

Keep the rest of the configuration unchanged.

## Linux permissions

If the log contains `Permission denied` for `/dev/ttyUSB0`, inspect the owner and group:

```bash
ls -l /dev/ttyUSB0
```

On many Debian and Ubuntu systems the group is `dialout`. Add the current user and then sign out and sign in again:

```bash
sudo usermod -aG dialout "$USER"
```

Other distributions may use a different group, such as `uucp`. Use the group shown by `ls -l` instead of assuming one name.

If virtual environment creation fails on Debian or Ubuntu, install the distribution package that provides it:

```bash
sudo apt install python3-venv
```

## macOS notes

A current Python 3 installation is required. The launcher uses `python3`; it never tries the obsolete `python` command.

The default URL and command actions do not require Accessibility permission. Custom `hotkey` and `text` actions use `pynput`; macOS may ask you to allow the terminal or Python host under System Settings > Privacy & Security > Accessibility.

The default Lock PC action runs:

```text
pmset displaysleepnow
```

This sleeps the displays. Whether waking requires a password depends on the macOS lock-screen settings.

## What telemetry is available

| Metric | Windows | macOS | Linux |
| --- | --- | --- | --- |
| CPU and RAM usage | Yes | Yes | Yes |
| RAM used/total | Yes | Yes | Yes |
| Network traffic | Yes | Yes | Yes |
| Disk usage and I/O | Yes | Yes | Yes |
| NVIDIA GPU/VRAM through `nvidia-smi` | Yes | Usually unavailable | Yes, when NVIDIA drivers provide `nvidia-smi` |
| CPU temperature | LibreHardwareMonitor | Usually unavailable | Available when exposed through `psutil` |
| Extra board/storage temperatures | LibreHardwareMonitor | Not enabled by default | Not enabled by default |

Unavailable values are sent as `null` and the display shows its existing `N/A` fallback. No firmware change is required.

## Default buttons on macOS and Linux

- ChatGPT opens the default browser.
- Ollama checks the local API and starts `ollama serve` when needed.
- Voice Server is intentionally unconfigured on macOS and Linux until a local command is added to `host/config.json`.
- Terminal opens Terminal.app on macOS and `x-terminal-emulator` on Linux.
- Task Manager opens Activity Monitor on macOS and `gnome-system-monitor` on Linux.
- Lock PC uses `pmset displaysleepnow` on macOS and `loginctl lock-session` on Linux.

Linux desktop environments differ. If `x-terminal-emulator`, `gnome-system-monitor` or `loginctl` is unavailable, replace only the Linux command in `host/config.json` with the equivalent installed on that computer.

## Stop the bridge

When it runs in a terminal, press:

```text
Ctrl+C
```

The local environment and configuration remain in `host/.venv` and `host/config.json` for the next run.
