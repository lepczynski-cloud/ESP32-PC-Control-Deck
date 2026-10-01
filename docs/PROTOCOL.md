# USB serial protocol

ESP32 PC Control Deck v0.3 uses a small line-oriented protocol through the board's CH340 USB serial connection.

## Framing

Every application frame starts with `DD:` and ends with a newline:

```text
DD:{"type":"stats","cpu":18.2,"ram":61.7}\n
```

The prefix lets both sides ignore ESP32 ROM boot messages and unrelated serial output instead of attempting to parse them as JSON.

Default serial settings:

- 115200 baud
- 8 data bits
- no parity
- 1 stop bit

Protocol version: `3`.

The firmware still accepts a valid raw JSON line from earlier prototypes, but new clients should always use the `DD:` prefix.

## PC to ESP32

### `stats`

```json
{
  "type": "stats",
  "cpu": 18.2,
  "ram": 61.7,
  "ram_used_gb": 19.7,
  "ram_total_gb": 32.0,
  "gpu": 35.0,
  "vram": 48.0,
  "vram_used_gb": 5.8,
  "vram_total_gb": 12.0,
  "cpu_temp": 57.0,
  "gpu_temp": 52.0,
  "system_temp": 34.0,
  "disk_temp": 41.0,
  "disk_used": 71.0,
  "disk_read_mbs": 4.2,
  "disk_write_mbs": 1.3,
  "net_down_mbps": 23.4,
  "net_up_mbps": 2.1,
  "clock": "19:05",
  "clock_seconds": 68700
}
```

Unavailable sensor values are sent as JSON `null`.

`clock_seconds` is the local number of seconds since midnight on the PC. The ESP32 stores the value and advances it locally using `millis()`. The older `clock` string remains as a fallback.

### `config`

Updates the six touch-button labels:

```json
{
  "type": "config",
  "macros": [
    {"id": 1, "label": "ChatGPT"},
    {"id": 2, "label": "Ollama"},
    {"id": 3, "label": "Voice Server"}
  ]
}
```

Labels can contain up to 22 characters. The firmware wraps longer labels onto two lines.

### `ping`

The ESP32 replies with `pong`.

### `recalibrate`

Deletes the saved touch calibration and restarts the ESP32.

## ESP32 to PC

### `hello`

Sent after boot:

```json
{
  "type": "hello",
  "device": "ESP32 PC Control Deck",
  "firmware": "0.3.3",
  "protocol": 3
}
```

### `macro`

Sent when a control button is pressed:

```json
{"type":"macro","id":3}
```

The ESP32 sends only the numeric ID. The trusted action remains in the local `host/config.json` file.

### `error`

Used for malformed framed JSON. Unrelated serial text is ignored without returning an error.
