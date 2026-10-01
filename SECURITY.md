# Security

## Local-first design

ESP32 PC Control Deck is intentionally local-first:

- no Wi-Fi is required,
- no Bluetooth is required,
- no cloud service is required by the bridge,
- no API key, password, browser cookie, or account credential is stored on the ESP32,
- telemetry and touch events use the USB serial connection.

## Action execution

The ESP32 sends only a numeric macro ID from 1 to 6. It does not send a command path or arbitrary shell text.

The host bridge maps the ID to an action in the local `host/config.json` file. That file can open URLs, execute commands, start services, type text, and send hotkeys.

Treat `host/config.json` as executable local configuration:

- add only commands you trust,
- verify paths before enabling autostart,
- do not commit private local paths or secrets unless intentionally public,
- do not use configuration files from unknown sources,
- keep `host/config.json` out of Git; it is ignored by default.

## Local HTTP checks

The default configuration can make read-only requests to:

- LibreHardwareMonitor at `http://127.0.0.1:8085/data.json` on Windows,
- Ollama at `http://127.0.0.1:11434/api/tags` when the Ollama button is used.

Do not change these to untrusted remote endpoints without understanding the privacy and network implications.

## Reporting a vulnerability

Use GitHub private vulnerability reporting for security issues. Avoid publishing exploit details in a public issue before a fix is available.
