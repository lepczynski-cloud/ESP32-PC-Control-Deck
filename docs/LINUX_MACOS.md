# macOS and Linux host bridge notes

The ESP32 firmware and USB serial protocol are operating system independent. The Python bridge supports basic system telemetry and configured shortcuts on Windows, macOS and Linux. Some sensors and application shortcuts depend on the host operating system.

## Start the bridge

Install Python 3 and use the extracted PC bridge folder:

```sh
sh host/run_linux_macos.sh
```

The script creates a local Python virtual environment, installs dependencies, copies the example configuration if needed and starts the bridge. The environment is reused on later runs.

To list available serial ports before starting:

```sh
sh host/run_linux_macos.sh --list-ports
```

Typical macOS port names include `/dev/cu.wchusbserial*` and `/dev/cu.usbserial*`. On Linux the common name is `/dev/ttyUSB0`. If detection fails, edit `host/config.json` and set `serial_port` to an exact device name.

On Linux you may need access to the relevant serial device group such as `dialout` or `uucp`. Log in again after changing group membership. Avoid running the bridge as root.

## Limitations

- `nvidia-smi` GPU data is only available when the command and a supported NVIDIA GPU are present.
- Linux can expose CPU temperatures through `psutil.sensors_temperatures()` when supported by the kernel.
- macOS usually does not expose CPU temperature through `psutil` without extra tools.
- On macOS keyboard automation can require Accessibility permission.
- Available terminal/system monitor commands and lock behavior vary by desktop environment.
- Set your voice server action path separately for each operating system in `host/config.json`.

The bridge does not require a cloud account or an external API.
