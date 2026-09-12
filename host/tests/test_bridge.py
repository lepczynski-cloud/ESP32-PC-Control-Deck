import importlib.util
import json
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
