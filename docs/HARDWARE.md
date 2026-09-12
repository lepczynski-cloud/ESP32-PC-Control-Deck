# Hardware notes

ESP32 PC Control Deck targets the Elecrow 2.8-inch ESP32 touch display/miner board based on the classic ESP32-WROOM-32 module.

## Display and touch pinout

The PlatformIO configuration matches the working pinout used by the CrowPanel Pocket Arcade project on the same board:

| Function | GPIO |
| --- | ---: |
| TFT MISO | 4 |
| TFT MOSI | 13 |
| TFT SCLK | 14 |
| TFT CS | 15 |
| TFT DC | 2 |
| TFT RST | -1 |
| Backlight | 27 |
| Touch CS | 33 |

The display uses ILI9341 and the resistive touch controller uses XPT2046.

## Orientation

The firmware uses landscape rotation:

```cpp
tft.setRotation(1);
```

This produces a 320x240 interface with the USB connector on the right side of the tested device.

## USB behavior

The board uses a classic ESP32-WROOM-32 and a CH340 USB-to-UART bridge. The USB-C connection provides:

- power,
- firmware upload,
- serial PC telemetry,
- serial touch-control events.

It does not expose the ESP32 as a native USB HID keyboard. The local host bridge receives a small macro ID from the ESP32 and performs the configured action on the computer.

A future hardware version could add an RP2040 or another native-USB microcontroller for true HID operation without the host bridge.
