# Touch controls and macros

The ESP32 sends one numeric macro ID to the host bridge. The bridge then runs the matching action from the local `host/config.json` file.

Commands, paths and URLs are not stored in the ESP32 firmware.

## Default layout

| ID | Label | Action |
| ---: | --- | --- |
| 1 | ChatGPT | Open ChatGPT in the default browser |
| 2 | Ollama | Check the local API and start Ollama when needed |
| 3 | Voice Server | Start a local voice-server script after you set its path |
| 4 | Terminal | Open a terminal |
| 5 | Task Manager | Open the system monitor |
| 6 | Lock PC | Lock the current session |

## Supported actions

### Open a URL

```json
{
  "id": 1,
  "label": "ChatGPT",
  "action": "url",
  "value": "https://chatgpt.com/"
}
```

### Start a command

A command can be a string or an argument array. Arrays avoid quoting problems and are recommended for Windows scripts.

```json
{
  "id": 3,
  "label": "Voice Server",
  "action": "command",
  "new_console": true,
  "value": {
    "windows": ["cmd.exe", "/c", "C:\\Path\\To\\START_VOICE_SERVER.cmd"]
  },
  "working_directory": {
    "windows": "C:\\Path\\To"
  }
}
```

Options:

- `hidden`: start without a visible console on Windows
- `new_console`: start in a separate console on Windows
- `working_directory`: process working directory

### Start a service only when it is unavailable

The `service` action checks `health_url` before starting the process.

```json
{
  "id": 2,
  "label": "Ollama",
  "action": "service",
  "health_url": "http://127.0.0.1:11434/api/tags",
  "hidden": true,
  "value": {
    "windows": ["ollama", "serve"],
    "linux": ["ollama", "serve"],
    "macos": ["ollama", "serve"]
  }
}
```

If the endpoint is already reachable, the bridge logs that the service is running and does not create a duplicate process.

### Send a hotkey

```json
{
  "id": 4,
  "label": "Mute",
  "action": "hotkey",
  "value": "volume_mute"
}
```

Examples:

- `ctrl+shift+esc`
- `win+r`
- `alt+f2`
- `volume_mute`
- `volume_up`
- `media_play_pause`

### Type text

```json
{
  "id": 5,
  "label": "Signature",
  "action": "text",
  "value": "Hello from ESP32 PC Control Deck"
}
```

## Platform-specific values

`value` and `working_directory` can contain per-platform entries:

```json
"value": {
  "windows": ["wt.exe"],
  "linux": ["x-terminal-emulator"],
  "macos": ["open", "-a", "Terminal"]
}
```

The public example keeps the Windows commands unchanged and provides separate Linux and macOS commands. Linux desktop environments use different terminal and system-monitor applications, so edit only the `linux` value when the default command is not installed.

On macOS, `hotkey` and `text` actions may require Accessibility permission for the terminal or Python host. URL and command actions do not use keyboard injection.

See `LINUX_MACOS.md` for the complete platform setup and troubleshooting guide.

## Security boundary

The display cannot submit an arbitrary command string. It can only submit an ID from 1 to 6. The bridge maps that ID to a command already present in the local ignored configuration file.

Treat `host/config.json` as executable local configuration and add only actions you trust.
