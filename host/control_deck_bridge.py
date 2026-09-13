#!/usr/bin/env python3
"""ESP32 PC Control Deck host bridge.

The bridge collects local PC telemetry and sends it to an Elecrow 2.8-inch
ESP32 display through the board's CH340 USB serial connection. It also maps
six touch buttons to locally configured actions.

No Wi-Fi, Bluetooth, cloud account, API key, or browser credential is needed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import psutil
import serial
from serial.tools import list_ports

try:
    from pynput.keyboard import Controller as KeyboardController, Key, KeyCode
except Exception:
    KeyboardController = None
    Key = None
    KeyCode = None

APP_VERSION = "0.3.2"
PROTOCOL_PREFIX = "DD:"
PROTOCOL_VERSION = 3
CH340_VIDS = {0x1A86}
LOG_FILE: Path | None = None


def log(message: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    if LOG_FILE is not None:
        try:
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("The configuration root must be a JSON object")
    return data


def platform_key() -> str:
    return {
        "Windows": "windows",
        "Linux": "linux",
        "Darwin": "macos",
    }.get(platform.system(), "default")


def resolve_platform_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return value.get(platform_key(), value.get("default"))


def expand_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return os.path.expanduser(os.path.expandvars(value))


def choose_serial_port(configured: str) -> str | None:
    if configured and configured.lower() != "auto":
        return configured

    ports = list(list_ports.comports())
    if not ports:
        return None

    preferred: list[str] = []
    for port in ports:
        description = (port.description or "").upper()
        manufacturer = (port.manufacturer or "").upper()
        if (
            port.vid in CH340_VIDS
            or "CH340" in description
            or "CH340" in manufacturer
            or "USB-SERIAL" in description
        ):
            preferred.append(port.device)

    if len(preferred) == 1:
        return preferred[0]
    if preferred:
        log("Multiple CH340-like serial ports found: " + ", ".join(preferred))
        return preferred[0]

    return None


def safe_number(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
    except (TypeError, ValueError):
        return None
    return round(numeric, digits)


def disk_path_from_config(config: dict[str, Any]) -> str:
    configured = str(config.get("disk_path", "auto"))
    if configured.lower() != "auto":
        return configured
    if platform.system() == "Windows":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


def read_cpu_temp_psutil() -> float | None:
    """Read a CPU temperature where psutil exposes sensors (mainly POSIX)."""
    function = getattr(psutil, "sensors_temperatures", None)
    if function is None:
        return None
    try:
        sensors = function(fahrenheit=False) or {}
    except Exception:
        return None

    preferred: list[float] = []
    fallback: list[float] = []
    for entries in sensors.values():
        for entry in entries:
            current = getattr(entry, "current", None)
            if current is None:
                continue
            try:
                current = float(current)
            except (TypeError, ValueError):
                continue
            if not 0 < current < 130:
                continue
            label = (getattr(entry, "label", "") or "").lower()
            if any(token in label for token in ("package", "tctl", "tdie", "cpu")):
                preferred.append(current)
            else:
                fallback.append(current)
    values = preferred or fallback
    return max(values) if values else None


def parse_numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return safe_number(float(value), 2)
    if value is None:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


@dataclass(frozen=True)
class TemperatureSensor:
    value: float
    label: str
    sensor_id: str
    context: str


class LibreHardwareMonitorHttpReader:
    """Read temperatures from LibreHardwareMonitor's local data.json tree."""

    def __init__(self, enabled: bool, url: str, timeout: float = 0.5):
        self.enabled = enabled
        self.url = url
        self.timeout = timeout
        self._reachable: bool | None = None
        self._logged_sources: dict[str, str] = {}

    @staticmethod
    def _walk(node: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[dict[str, Any], tuple[str, ...]]]:
        if not isinstance(node, dict):
            return
        text = str(node.get("Text", "") or "")
        next_path = path + ((text,) if text else ())
        yield node, next_path
        for child in node.get("Children") or []:
            yield from LibreHardwareMonitorHttpReader._walk(child, next_path)

    @staticmethod
    def _is_temperature_node(node: dict[str, Any], context: str) -> bool:
        node_type = str(node.get("Type", "") or "").lower()
        sensor_id = str(node.get("SensorId", "") or "").lower()
        text = str(node.get("Text", "") or "").lower()
        return (
            node_type == "temperature"
            or "/temperature/" in sensor_id
            or "temperatures" in context
            or "temperature" in text
        )

    @staticmethod
    def _temperature_sensors(data: Any) -> list[TemperatureSensor]:
        sensors: list[TemperatureSensor] = []
        for node, path in LibreHardwareMonitorHttpReader._walk(data):
            if "Value" not in node:
                continue
            context = " ".join(path).lower()
            if not LibreHardwareMonitorHttpReader._is_temperature_node(node, context):
                continue

            value = parse_numeric(node.get("Value"))
            if value is None or not 0 < value < 130:
                continue

            sensors.append(
                TemperatureSensor(
                    value=value,
                    label=str(node.get("Text", "Temperature") or "Temperature"),
                    sensor_id=str(node.get("SensorId", "") or ""),
                    context=" > ".join(path),
                )
            )
        return sensors

    @staticmethod
    def _score(sensor: TemperatureSensor, kind: str) -> int | None:
        sensor_id = sensor.sensor_id.lower()
        label = sensor.label.lower()
        context = sensor.context.lower()
        haystack = " ".join((sensor_id, label, context))

        if kind == "cpu":
            identity = any(
                token in haystack
                for token in (
                    "amdcpu",
                    "intelcpu",
                    "/cpu/",
                    "amd ryzen",
                    "intel core",
                    "processor",
                )
            )
            if not identity:
                return None
            score = 20
            if "cpu package" in label or "package" in label:
                score += 100
            elif "tctl" in label or "tdie" in label:
                score += 90
            elif "core average" in label:
                score += 80
            elif "core max" in label or "maximum" in label:
                score += 60
            elif "core" in label:
                score += 20
            return score

        if kind == "gpu":
            if not any(
                token in haystack
                for token in ("nvidiagpu", "atigpu", "intelgpu", "/gpu/", "graphics")
            ):
                return None
            score = 20
            if "gpu core" in label or label == "core":
                score += 70
            if "gpu package" in label or "package" in label:
                score += 60
            if "hot spot" in label or "hotspot" in label:
                score += 30
            return score

        if kind == "disk":
            if not any(
                token in haystack
                for token in ("/hdd/", "/storage/", "nvme", "ssd", "disk", "drive")
            ):
                return None
            score = 20
            if "composite" in label:
                score += 60
            if label in {"temperature", "drive temperature"}:
                score += 50
            return score

        if kind == "system":
            if not any(
                token in haystack
                for token in ("/lpc/", "motherboard", "mainboard", "super i/o", "superio", "chipset")
            ):
                return None
            score = 10
            if "motherboard" in label or "mainboard" in label or "system" in label:
                score += 60
            if "ambient" in label:
                score += 45
            if "pch" in label or "chipset" in label:
                score += 25
            if "vrm" in label:
                score += 15
            return score

        return None

    @classmethod
    def _select(cls, sensors: list[TemperatureSensor], kind: str) -> TemperatureSensor | None:
        candidates: list[tuple[int, TemperatureSensor]] = []
        for sensor in sensors:
            score = cls._score(sensor, kind)
            if score is not None:
                candidates.append((score, sensor))
        if not candidates:
            return None
        best_score = max(score for score, _ in candidates)
        best = [sensor for score, sensor in candidates if score == best_score]
        return max(best, key=lambda item: item.value)

    def _fetch(self) -> Any:
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": f"ESP32-PC-Control-Deck/{APP_VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    def _log_source(self, kind: str, sensor: TemperatureSensor | None) -> None:
        identity = "none" if sensor is None else f"{sensor.label} [{sensor.sensor_id}]"
        if self._logged_sources.get(kind) == identity:
            return
        self._logged_sources[kind] = identity
        if sensor is not None:
            log(f"Temperature source {kind}: {identity}")

    def read(self) -> dict[str, float | None]:
        result: dict[str, float | None] = {
            "cpu_temp": None,
            "gpu_temp": None,
            "disk_temp": None,
            "system_temp": None,
        }
        if not self.enabled:
            return result

        try:
            data = self._fetch()
            if self._reachable is not True:
                log("LibreHardwareMonitor web server detected")
            self._reachable = True

            sensors = self._temperature_sensors(data)
            for kind, result_key in (
                ("cpu", "cpu_temp"),
                ("gpu", "gpu_temp"),
                ("disk", "disk_temp"),
                ("system", "system_temp"),
            ):
                selected = self._select(sensors, kind)
                self._log_source(kind, selected)
                if selected is not None:
                    result[result_key] = selected.value
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            if self._reachable is None:
                log(
                    "Additional temperatures unavailable. On Windows, run "
                    "LibreHardwareMonitor and enable Remote Web Server > Run."
                )
            self._reachable = False
        except Exception as exc:
            if self._reachable is not False:
                log(f"LibreHardwareMonitor read error: {exc}")
            self._reachable = False
        return result

    def print_temperature_sensors(self) -> int:
        if not self.enabled:
            print("LibreHardwareMonitor integration is disabled in config.json")
            return 2
        try:
            sensors = self._temperature_sensors(self._fetch())
        except Exception as exc:
            print(f"Could not read {self.url}: {exc}", file=sys.stderr)
            return 2

        if not sensors:
            print("No temperature sensors were found in the LibreHardwareMonitor JSON tree.")
            return 1

        print(f"Temperature sensors from {self.url}:\n")
        for sensor in sensors:
            print(f"{sensor.value:6.1f} C  {sensor.label}")
            print(f"          id: {sensor.sensor_id or '(not provided)'}")
            print(f"        path: {sensor.context}\n")
        return 0


def read_nvidia_gpu() -> dict[str, float | None]:
    result: dict[str, float | None] = {
        "gpu": None,
        "vram": None,
        "gpu_temp": None,
        "vram_used_gb": None,
        "vram_total_gb": None,
    }
    executable = shutil.which("nvidia-smi")
    if not executable:
        return result

    command = [
        executable,
        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return result

        fields = [item.strip() for item in completed.stdout.strip().splitlines()[0].split(",")]
        if len(fields) < 4:
            return result

        gpu = float(fields[0])
        used_mib = float(fields[1])
        total_mib = float(fields[2])
        temperature = float(fields[3])
        result["gpu"] = gpu
        result["vram"] = used_mib * 100.0 / total_mib if total_mib > 0 else None
        result["gpu_temp"] = temperature
        result["vram_used_gb"] = used_mib / 1024.0
        result["vram_total_gb"] = total_mib / 1024.0
    except Exception:
        pass
    return result


@dataclass
class Counters:
    time: float
    net_sent: int
    net_recv: int
    disk_read: int
    disk_write: int


def current_counters() -> Counters:
    network = psutil.net_io_counters()
    disk = psutil.disk_io_counters()
    return Counters(
        time=time.monotonic(),
        net_sent=int(network.bytes_sent if network else 0),
        net_recv=int(network.bytes_recv if network else 0),
        disk_read=int(disk.read_bytes if disk else 0),
        disk_write=int(disk.write_bytes if disk else 0),
    )


def get_stats(
    previous: Counters,
    disk_path: str,
    lhm: LibreHardwareMonitorHttpReader,
) -> tuple[dict[str, Any], Counters]:
    current = current_counters()
    elapsed = max(0.001, current.time - previous.time)

    try:
        disk_used = psutil.disk_usage(disk_path).percent
    except Exception:
        disk_used = None

    memory = psutil.virtual_memory()
    gib = 1024.0 ** 3
    ram_total_gb = memory.total / gib
    ram_used_gb = (memory.total - memory.available) / gib

    nvidia = read_nvidia_gpu()
    lhm_stats = lhm.read()
    psutil_cpu_temp = read_cpu_temp_psutil()
    cpu_temp = psutil_cpu_temp if psutil_cpu_temp is not None else lhm_stats.get("cpu_temp")
    gpu_temp = nvidia.get("gpu_temp")
    if gpu_temp is None:
        gpu_temp = lhm_stats.get("gpu_temp")

    now = datetime.now()
    clock_seconds = now.hour * 3600 + now.minute * 60 + now.second

    payload = {
        "type": "stats",
        "cpu": safe_number(psutil.cpu_percent(interval=None), 1),
        "ram": safe_number(memory.percent, 1),
        "ram_used_gb": safe_number(ram_used_gb, 1),
        "ram_total_gb": safe_number(ram_total_gb, 1),
        "gpu": safe_number(nvidia.get("gpu"), 1),
        "vram": safe_number(nvidia.get("vram"), 1),
        "vram_used_gb": safe_number(nvidia.get("vram_used_gb"), 1),
        "vram_total_gb": safe_number(nvidia.get("vram_total_gb"), 1),
        "cpu_temp": safe_number(cpu_temp, 1),
        "gpu_temp": safe_number(gpu_temp, 1),
        "system_temp": safe_number(lhm_stats.get("system_temp"), 1),
        "disk_temp": safe_number(lhm_stats.get("disk_temp"), 1),
        "disk_used": safe_number(disk_used, 1),
        "disk_read_mbs": safe_number(
            max(0, current.disk_read - previous.disk_read) / elapsed / 1_000_000.0,
            2,
        ),
        "disk_write_mbs": safe_number(
            max(0, current.disk_write - previous.disk_write) / elapsed / 1_000_000.0,
            2,
        ),
        "net_down_mbps": safe_number(
            max(0, current.net_recv - previous.net_recv) * 8.0 / elapsed / 1_000_000.0,
            2,
        ),
        "net_up_mbps": safe_number(
            max(0, current.net_sent - previous.net_sent) * 8.0 / elapsed / 1_000_000.0,
            2,
        ),
        "clock": now.strftime("%H:%M"),
        "clock_seconds": clock_seconds,
    }
    return payload, current


def macro_packet(config: dict[str, Any]) -> dict[str, Any]:
    macros: list[dict[str, Any]] = []
    for item in config.get("macros", []):
        try:
            macro_id = int(item.get("id"))
        except Exception:
            continue
        if 1 <= macro_id <= 6:
            macros.append(
                {
                    "id": macro_id,
                    "label": str(item.get("label", f"MACRO {macro_id}"))[:22],
                }
            )
    return {"type": "config", "macros": macros}


def keyboard_key(token: str):
    if Key is None or KeyCode is None:
        raise RuntimeError("pynput is not available")
    token = token.strip().lower()
    mapping = {
        "ctrl": Key.ctrl,
        "control": Key.ctrl,
        "alt": Key.alt,
        "shift": Key.shift,
        "cmd": Key.cmd,
        "win": Key.cmd,
        "windows": Key.cmd,
        "enter": Key.enter,
        "return": Key.enter,
        "esc": Key.esc,
        "escape": Key.esc,
        "tab": Key.tab,
        "space": Key.space,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "home": Key.home,
        "end": Key.end,
        "page_up": Key.page_up,
        "page_down": Key.page_down,
        "volume_up": Key.media_volume_up,
        "volume_down": Key.media_volume_down,
        "volume_mute": Key.media_volume_mute,
        "media_play_pause": Key.media_play_pause,
        "media_next": Key.media_next,
        "media_previous": Key.media_previous,
    }
    if token in mapping:
        return mapping[token]
    if token.startswith("f") and token[1:].isdigit() and hasattr(Key, token):
        return getattr(Key, token)
    if len(token) == 1:
        return KeyCode.from_char(token)
    raise ValueError(f"Unsupported key token: {token}")


def send_hotkey(specification: str) -> None:
    if KeyboardController is None:
        raise RuntimeError("pynput is not installed or available")
    controller = KeyboardController()
    keys = [keyboard_key(item) for item in specification.split("+") if item.strip()]
    for key in keys:
        controller.press(key)
    for key in reversed(keys):
        controller.release(key)


def type_text(text: str) -> None:
    if KeyboardController is None:
        raise RuntimeError("pynput is not installed or available")
    KeyboardController().type(text)


def url_reachable(url: str, timeout: float = 0.6) -> bool:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": f"ControlDeck/{APP_VERSION}"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= int(response.status) < 500
    except Exception:
        return False


def start_process(
    command_value: Any,
    working_directory: Any = None,
    hidden: bool = False,
    new_console: bool = False,
) -> subprocess.Popen[Any]:
    command_value = resolve_platform_value(command_value)
    working_directory = resolve_platform_value(working_directory)
    if not command_value:
        raise ValueError("No command is configured for this operating system")

    cwd = expand_text(working_directory) if working_directory else None
    if cwd and not Path(str(cwd)).exists():
        raise FileNotFoundError(f"Working directory does not exist: {cwd}")

    shell = isinstance(command_value, str)
    if isinstance(command_value, list):
        command: Any = [str(expand_text(item)) for item in command_value]
    else:
        command = str(expand_text(command_value))

    creationflags = 0
    startupinfo = None
    stdout: Any = None
    stderr: Any = None
    if platform.system() == "Windows":
        if hidden:
            creationflags |= subprocess.CREATE_NO_WINDOW
            stdout = subprocess.DEVNULL
            stderr = subprocess.DEVNULL
        elif new_console:
            creationflags |= subprocess.CREATE_NEW_CONSOLE
        if hidden:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

    return subprocess.Popen(
        command,
        shell=shell,
        cwd=str(cwd) if cwd else None,
        creationflags=creationflags,
        startupinfo=startupinfo,
        stdout=stdout,
        stderr=stderr,
    )


def execute_macro(config: dict[str, Any], macro_id: int) -> None:
    item = next(
        (macro for macro in config.get("macros", []) if int(macro.get("id", -1)) == macro_id),
        None,
    )
    if item is None:
        log(f"Macro {macro_id}: not configured")
        return

    action = str(item.get("action", "none")).lower()
    label = str(item.get("label", f"Macro {macro_id}"))
    log(f"Macro {macro_id} pressed: {label}")

    try:
        if action == "none":
            return
        if action == "url":
            value = resolve_platform_value(item.get("value"))
            if not value:
                raise ValueError("No URL configured")
            webbrowser.open(str(value))
            return
        if action == "hotkey":
            send_hotkey(str(resolve_platform_value(item.get("value"))))
            return
        if action == "text":
            type_text(str(resolve_platform_value(item.get("value"))))
            return
        if action in {"command", "service"}:
            health_url = str(item.get("health_url", "") or "").strip()
            if action == "service" and health_url and url_reachable(health_url):
                log(f"{label} is already running: {health_url}")
                return
            process = start_process(
                item.get("value"),
                working_directory=item.get("working_directory"),
                hidden=bool(item.get("hidden", False)),
                new_console=bool(item.get("new_console", False)),
            )
            log(f"Started {label} (PID {process.pid})")
            return
        raise ValueError(f"Unsupported macro action: {action}")
    except Exception as exc:
        log(f"Macro {macro_id} failed: {exc}")


def encode_frame(obj: dict[str, Any]) -> bytes:
    payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
    return f"{PROTOCOL_PREFIX}{payload}\n".encode("ascii")


def send_json(serial_port: serial.Serial, obj: dict[str, Any]) -> None:
    serial_port.write(encode_frame(obj))
    serial_port.flush()


def parse_frame(text: str) -> dict[str, Any] | None:
    if text.startswith(PROTOCOL_PREFIX):
        payload = text[len(PROTOCOL_PREFIX) :]
    elif text.startswith("{"):
        payload = text
    else:
        return None
    try:
        message = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return message if isinstance(message, dict) else None


def build_lhm_reader(config: dict[str, Any]) -> LibreHardwareMonitorHttpReader:
    lhm_config = config.get("librehardwaremonitor", {}) or {}
    return LibreHardwareMonitorHttpReader(
        enabled=bool(lhm_config.get("enabled", True)),
        url=str(lhm_config.get("url", "http://127.0.0.1:8085/data.json")),
        timeout=float(lhm_config.get("timeout_seconds", 0.5)),
    )


def run(config: dict[str, Any]) -> None:
    baud = int(config.get("baud", 115200))
    interval = max(0.5, float(config.get("interval_seconds", 2.0)))
    disk_path = disk_path_from_config(config)
    lhm = build_lhm_reader(config)

    psutil.cpu_percent(interval=None)
    previous = current_counters()
    configured_port = str(config.get("serial_port", "auto"))

    while True:
        port = choose_serial_port(configured_port)
        if not port:
            log("Control Deck CH340 not found. Retrying...")
            time.sleep(2.0)
            continue

        try:
            log(f"Opening {port} at {baud} baud")
            with serial.Serial(port, baud, timeout=0.05, write_timeout=1) as serial_port:
                time.sleep(2.0)
                serial_port.reset_input_buffer()
                serial_port.reset_output_buffer()

                send_json(serial_port, macro_packet(config))
                last_send = 0.0
                receive_buffer = bytearray()

                while True:
                    now = time.monotonic()
                    if now - last_send >= interval:
                        payload, previous = get_stats(previous, disk_path, lhm)
                        send_json(serial_port, payload)
                        last_send = now

                    chunk = serial_port.read(256)
                    if chunk:
                        receive_buffer.extend(chunk)
                        while b"\n" in receive_buffer:
                            raw, _, remainder = receive_buffer.partition(b"\n")
                            receive_buffer = bytearray(remainder)
                            text = raw.decode("utf-8", errors="replace").strip()
                            if not text:
                                continue

                            message = parse_frame(text)
                            if message is None:
                                continue

                            message_type = message.get("type")
                            if message_type == "macro":
                                execute_macro(config, int(message.get("id", 0)))
                            elif message_type == "hello":
                                protocol = message.get("protocol", "?")
                                firmware = message.get("firmware", "?")
                                log(
                                    f"Connected to {message.get('device', 'ESP32')} "
                                    f"firmware {firmware}, protocol {protocol}"
                                )
                                if protocol != PROTOCOL_VERSION:
                                    log(
                                        f"Warning: bridge protocol {PROTOCOL_VERSION} "
                                        f"!= device protocol {protocol}"
                                    )
                                send_json(serial_port, macro_packet(config))
                            elif message_type == "error":
                                log(
                                    f"ESP protocol error: {message.get('code', 'unknown')} "
                                    f"({message.get('detail', '')})"
                                )
                            elif message_type not in {"pong", "rebooting"}:
                                log(f"ESP: {message}")

                    time.sleep(0.01)
        except (serial.SerialException, OSError) as exc:
            log(f"Serial disconnected: {exc}")
            time.sleep(2.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="ESP32 PC Control Deck host bridge")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.json")),
        help="Path to config.json",
    )
    parser.add_argument(
        "--list-temperatures",
        action="store_true",
        help="List temperature sensors exposed by LibreHardwareMonitor and exit",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    if not config_path.exists():
        example = Path(__file__).with_name("config.example.json")
        print(
            f"Config not found: {config_path}\nCopy {example.name} to config.json and edit it.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    config = load_config(config_path)

    global LOG_FILE
    log_name = str(config.get("log_file", "control-deck.log") or "").strip()
    if log_name:
        LOG_FILE = (config_path.parent / log_name).resolve()

    if args.list_temperatures:
        raise SystemExit(build_lhm_reader(config).print_temperature_sensors())

    log(f"PC Control Deck Bridge {APP_VERSION} on {platform.system()} {platform.release()}")
    run(config)


if __name__ == "__main__":
    main()
