# Publishing the project

Repository: https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck

Website: https://esp32-pc-control-deck.lepczynski.it/

## GitHub About

Description:

> USB-powered ESP32 PC monitor and touchscreen macro deck. Flash the firmware directly from your browser and run a local PC bridge for CPU/GPU stats and shortcuts.

Website: `https://esp32-pc-control-deck.lepczynski.it/`

Topics:

`esp32`, `platformio`, `elecrow`, `pc-monitor`, `system-monitor`, `macropad`, `cyberdeck`, `usb-serial`, `ollama`, `local-ai`, `python`, `pyserial`, `tft-espi`, `ili9341`, `xpt2046`, `cloudflare-pages`, `esp-web-tools`

## Full repository replacement

Use a normal commit on the existing `main` branch. Do not recreate the repository with a new unrelated Git history. It is recommended to keep the real JPG and GIF in `docs/media/` untouched. If those source files are missing after replacement, the CI workflow can restore them from earlier Git commits to the static site. It will reject placeholder media and fail when real media are unavailable.

Upload the entire replacement package, including hidden `.github/workflows/`, the `site/` folder, the `scripts/` folder, `host/`, `src/` and the documentation.

Use `git add -A`, commit, and push to `main`. The GitHub Actions workflow builds and publishes automatically. Do not manually upload firmware binaries or modify `cloudflare-pages`.

For one-time Cloudflare Pages setup, use [WEB_INSTALLER.md](WEB_INSTALLER.md).

## Website deployment

The generated `cloudflare-pages` branch contains the latest successfully built firmware, PC bridge and a locally bundled ESP Web Tools installer from the same source commit. The live site is then automatically deployed by Cloudflare Pages Git integration.

The user must still install the small Python PC bridge after flashing; this cannot be done by the web firmware installer.

## Media and video

The website serves the real image and GIF through Cloudflare Pages:

- `/media/ESP32_PC_Control_Deck.jpg`
- `/media/control-deck-demo.gif`

Full video: https://www.youtube.com/watch?v=16eqHU4j9Fk

The device was provided by Elecrow for review. It was not a paid sponsorship.
