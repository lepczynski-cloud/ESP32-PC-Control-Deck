# Publishing the project

Repository: https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck

Website: https://esp32-pc-control-deck.lepczynski.it/

## GitHub About

Description:

> USB-powered ESP32 PC monitor and touchscreen macro deck. Flash the firmware directly from your browser and run a local PC bridge for CPU/GPU stats and shortcuts.

Website: `https://esp32-pc-control-deck.lepczynski.it/`

Topics:

`esp32`, `platformio`, `elecrow`, `pc-monitor`, `system-monitor`, `macropad`, `cyberdeck`, `usb-serial`, `ollama`, `local-ai`, `python`, `pyserial`, `tft-espi`, `ili9341`, `xpt2046`, `cloudflare-workers`, `esp-web-tools`

## Full repository replacement

Replace the contents of the existing `main` branch with this repository, keeping the real JPG and GIF in `docs/media/`. Keep its existing Git history. Run `git add -A`, commit and push to `main`.

No GitHub Actions workflow or `cloudflare-pages` branch is needed. Cloudflare Workers Builds watches `main` directly, builds firmware with `bash scripts/build_pages.sh` and publishes the generated static assets with `npx wrangler deploy`. Do not edit the generated `dist/` directory or commit compiled binaries.

For the one-time Workers Git setup, follow [WEB_INSTALLER.md](WEB_INSTALLER.md). Firmware is published only after a full successful build. Users must still install the PC bridge to use system monitoring and touch macros.

## Media and video

The website serves the real image and GIF through Cloudflare Workers Static Assets:

- `/media/ESP32_PC_Control_Deck.jpg`
- `/media/control-deck-demo.gif`

Full video: https://www.youtube.com/watch?v=16eqHU4j9Fk

The device was provided by Elecrow for review. It was not a paid sponsorship.
