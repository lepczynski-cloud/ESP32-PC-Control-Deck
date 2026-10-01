import importlib.util
import json
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import patch
from typing import Optional

import types

if "serial" not in sys.modules:
    serial_stub = types.ModuleType("serial")
    serial_stub.SerialException = OSError
    serial_stub.Serial = object
    tools_stub = types.ModuleType("serial.tools")
    list_ports_stub = types.ModuleType("serial.tools.list_ports")
    list_ports_stub.comports = lambda: []
    tools_stub.list_ports = list_ports_stub
    serial_stub.tools = tools_stub
    sys.modules["serial"] = serial_stub
    sys.modules["serial.tools"] = tools_stub
    sys.modules["serial.tools.list_ports"] = list_ports_stub

from pathlib import Path

BRIDGE_PATH = Path(__file__).resolve().parents[1] / "control_deck_bridge.py"
SPEC = importlib.util.spec_from_file_location("control_deck_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
sys.modules["control_deck_bridge"] = bridge
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


class TemperatureParsingTests(unittest.TestCase):
    def setUp(self):
        self.sample = {
            "Text": "Sensor",
            "Children": [
                {
                    "Text": "AMD Ryzen 9 5900X",
                    "Children": [
                        {
                            "Text": "Temperatures",
                            "Children": [
                                {
                                    "Text": "CPU Package",
                                    "Value": "57.0 C",
                                    "SensorId": "/amdcpu/0/temperature/0",
                                    "Children": [],
                                },
                                {
                                    "Text": "Core Average",
                                    "Value": "52.0 C",
                                    "SensorId": "/amdcpu/0/temperature/1",
                                    "Children": [],
                                },
                            ],
                        }
                    ],
                },
                {
                    "Text": "NVIDIA GeForce",
                    "Children": [
                        {
                            "Text": "Temperatures",
                            "Children": [
                                {
                                    "Text": "GPU Core",
                                    "Value": "48.0 C",
                                    "SensorId": "/nvidiagpu/0/temperature/0",
                                    "Children": [],
                                }
                            ],
                        }
                    ],
                },
                {
                    "Text": "Samsung NVMe",
                    "Children": [
                        {
                            "Text": "Temperatures",
                            "Children": [
                                {
                                    "Text": "Composite",
                                    "Value": "41.0 C",
                                    "SensorId": "/storage/nvme/0/temperature/0",
                                    "Children": [],
                                }
                            ],
                        }
                    ],
                },
                {
                    "Text": "ASUS Mainboard",
                    "Children": [
                        {
                            "Text": "Temperatures",
                            "Children": [
                                {
                                    "Text": "Motherboard",
                                    "Value": "34.0 C",
                                    "SensorId": "/lpc/nct/0/temperature/0",
                                    "Children": [],
                                }
                            ],
                        }
                    ],
                },
            ],
        }

    def test_selects_expected_temperature_sources(self):
        sensors = bridge.LibreHardwareMonitorHttpReader._temperature_sensors(self.sample)
        expected = {
            "cpu": ("CPU Package", 57.0),
            "gpu": ("GPU Core", 48.0),
            "disk": ("Composite", 41.0),
            "system": ("Motherboard", 34.0),
        }
        for kind, (label, value) in expected.items():
            selected = bridge.LibreHardwareMonitorHttpReader._select(sensors, kind)
            self.assertIsNotNone(selected)
            self.assertEqual(label, selected.label)
            self.assertEqual(value, selected.value)


class ProtocolTests(unittest.TestCase):
    def test_frame_encoding(self):
        frame = bridge.encode_frame({"type": "stats", "clock_seconds": 3600})
        self.assertEqual(b'DD:{"type":"stats","clock_seconds":3600}\n', frame)

    def test_default_top_row(self):
        config_path = Path(__file__).resolve().parents[1] / "config.example.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        labels = [item["label"] for item in bridge.macro_packet(config)["macros"]]
        self.assertEqual(["ChatGPT", "Ollama", "Voice Server"], labels[:3])


@dataclass
class FakePort:
    device: str
    description: str = ""
    manufacturer: str = ""
    vid: Optional[int] = None
    pid: Optional[int] = None
    product: str = ""
    interface: str = ""
    hwid: str = ""


class SerialPortSelectionTests(unittest.TestCase):
    def test_explicit_port_is_never_replaced(self):
        selected = bridge.choose_serial_port("/dev/cu.manual", [])
        self.assertEqual("/dev/cu.manual", selected)

    def test_macos_prefers_callout_device_over_tty_device(self):
        ports = [
            FakePort(
                "/dev/tty.wchusbserial1420",
                description="USB2.0-Serial",
                manufacturer="wch.cn",
                vid=0x1A86,
                pid=0x7523,
            ),
            FakePort(
                "/dev/cu.wchusbserial1420",
                description="USB2.0-Serial",
                manufacturer="wch.cn",
                vid=0x1A86,
                pid=0x7523,
            ),
        ]
        with patch.object(bridge.platform, "system", return_value="Darwin"):
            with patch.object(bridge, "log"):
                selected = bridge.choose_serial_port("auto", ports)
        self.assertEqual("/dev/cu.wchusbserial1420", selected)

    def test_macos_recognizes_usbserial_without_vid_metadata(self):
        ports = [
            FakePort("/dev/cu.Bluetooth-Incoming-Port", description="Bluetooth-Incoming-Port"),
            FakePort("/dev/cu.usbserial-110", description="USB Serial"),
        ]
        with patch.object(bridge.platform, "system", return_value="Darwin"):
            selected = bridge.choose_serial_port("auto", ports)
        self.assertEqual("/dev/cu.usbserial-110", selected)

    def test_linux_recognizes_ttyusb_without_vid_metadata(self):
        ports = [
            FakePort("/dev/ttyS0", description="serial"),
            FakePort("/dev/ttyUSB0", description="USB2.0-Serial"),
        ]
        with patch.object(bridge.platform, "system", return_value="Linux"):
            selected = bridge.choose_serial_port("auto", ports)
        self.assertEqual("/dev/ttyUSB0", selected)

    def test_windows_keeps_original_first_match_behavior(self):
        ports = [
            FakePort("COM7", description="USB-SERIAL CH340", vid=0x1A86),
            FakePort("COM9", description="USB-SERIAL CH340", vid=0x1A86),
        ]
        with patch.object(bridge.platform, "system", return_value="Windows"):
            with patch.object(bridge, "log"):
                selected = bridge.choose_serial_port("auto", ports)
        self.assertEqual("COM7", selected)


class PlatformConfigurationTests(unittest.TestCase):
    def setUp(self):
        config_path = Path(__file__).resolve().parents[1] / "config.example.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8"))

    def test_librehardwaremonitor_stays_enabled_on_windows(self):
        with patch.object(bridge.platform, "system", return_value="Windows"):
            reader = bridge.build_lhm_reader(self.config)
        self.assertTrue(reader.enabled)

    def test_librehardwaremonitor_is_disabled_by_default_on_linux_and_macos(self):
        for system in ("Linux", "Darwin"):
            with self.subTest(system=system):
                with patch.object(bridge.platform, "system", return_value=system):
                    reader = bridge.build_lhm_reader(self.config)
                self.assertFalse(reader.enabled)

    def test_platform_specific_macro_values_are_resolved(self):
        terminal = next(item for item in self.config["macros"] if item["id"] == 4)
        with patch.object(bridge.platform, "system", return_value="Darwin"):
            self.assertEqual(
                ["open", "-a", "Terminal"],
                bridge.resolve_platform_value(terminal["value"]),
            )
        with patch.object(bridge.platform, "system", return_value="Linux"):
            self.assertEqual(
                ["x-terminal-emulator"],
                bridge.resolve_platform_value(terminal["value"]),
            )

    def test_windows_default_macro_commands_remain_unchanged(self):
        expected = {
            2: ["ollama", "serve"],
            3: ["cmd.exe", "/c", "C:\\Path\\To\\START_VOICE_SERVER.cmd"],
            4: ["wt.exe"],
            5: ["taskmgr.exe"],
            6: ["rundll32.exe", "user32.dll,LockWorkStation"],
        }
        with patch.object(bridge.platform, "system", return_value="Windows"):
            actual = {
                item["id"]: bridge.resolve_platform_value(item.get("value"))
                for item in self.config["macros"]
                if item["id"] in expected
            }
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
