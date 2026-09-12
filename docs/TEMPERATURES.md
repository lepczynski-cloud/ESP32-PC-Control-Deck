# Temperature sources

Temperature availability depends on the operating system, hardware sensors, drivers, and monitoring software.

## GPU temperature

For NVIDIA GPUs, the bridge first uses `nvidia-smi` for:

- GPU utilization,
- VRAM used and total,
- GPU temperature.

If `nvidia-smi` does not provide a temperature, the bridge tries LibreHardwareMonitor.

## CPU temperature

On Linux and supported POSIX systems, the bridge first checks `psutil.sensors_temperatures()`.

On Windows, use LibreHardwareMonitor:

1. start LibreHardwareMonitor,
2. enable **Options -> Remote Web Server -> Run**,
3. confirm that `http://127.0.0.1:8085/data.json` opens locally,
4. start the Control Deck bridge.

The bridge scores CPU candidates in this order:

1. CPU Package,
2. Tctl/Tdie,
3. Core Average,
4. Core Max,
5. another CPU core temperature.

## Why v0.3 detects more sensors

Earlier code required every JSON sensor leaf to include:

```json
{"Type": "Temperature"}
```

LibreHardwareMonitor data can instead identify the sensor through a sensor ID such as:

```text
/amdcpu/0/temperature/0
```

or through a parent `Temperatures` category. Version 0.3 recognizes all three forms:

- explicit `Type`,
- `/temperature/` in `SensorId`,
- a temperature category in the JSON path.

## System fallback

When CPU temperature is unavailable but a motherboard/system sensor exists, the CPU row displays:

```text
SYS 34C
```

This is deliberately labeled as a system temperature and is not presented as the CPU package temperature.

## Storage temperature

When a supported SSD, NVMe drive, or disk sensor is found, the disk information box adds `TxxC` after read/write activity.

## List all detected sensors

With the bridge environment already installed:

```text
host\.venv\Scripts\python.exe host\control_deck_bridge.py --list-temperatures --config host\config.json
```

The command prints the value, label, sensor ID, and full JSON path for every detected temperature sensor.

The regular log also shows the selected source, for example:

```text
Temperature source cpu: CPU Package [/amdcpu/0/temperature/0]
Temperature source disk: Composite [/storage/nvme/0/temperature/0]
```

## When no temperature is available

The display uses contextual fallbacks instead of showing fake temperature placeholders on every row:

- CPU: `TEMP N/A` or a labeled `SYS xxC` fallback
- RAM: used/total memory
- GPU: `TEMP N/A`
- VRAM: used/total memory
- Disk: read/write throughput without a temperature suffix
