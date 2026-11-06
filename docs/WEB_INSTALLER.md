# Website, browser installer and automatic builds

The project website uses static HTML, CSS and JavaScript. Cloudflare Workers Builds compiles the exact `main` revision, packages ESP32 firmware and the PC bridge, and deploys static assets in one operation. No application server is involved. No manual PlatformIO build, release upload or generated Git branch is needed.

## Cloudflare build configuration

Connect the repository `lepczynski-cloud/ESP32-PC-Control-Deck` to **Cloudflare Workers** using Git integration (not Cloudflare Pages). The settings are the same type used by CrowPanel Rotary Buddy.

| Cloudflare setting | Value |
| --- | --- |
| Project type | Workers / Static Assets |
| Worker name | `esp32-pc-control-deck` |
| Git repository | `lepczynski-cloud/ESP32-PC-Control-Deck` |
| Production branch | `main` |
| Root directory | Leave blank (repository root) |
| Build command | `bash scripts/build_pages.sh` |
| Deploy command | `npx wrangler deploy` |
| Build output | Declared in `wrangler.jsonc` as `./dist` (not a dashboard field) |
| Domain | `esp32-pc-control-deck.lepczynski.it` |
| Python | `.python-version` pins Python 3.12 |

The `wrangler.jsonc` and `package.json` files are already configured. Do not add an output directory to the deploy command. The build script installs its own Python virtual environment and builds the ESP Web Tools bundle, the firmware and the site. The deploy command publishes only after the build step has succeeded.

## One-time setup

1. Keep the current GitHub repository and original `docs/media/ESP32_PC_Control_Deck.jpg` and `docs/media/control-deck-demo.gif`. Replace the repository contents with this archive, but do not delete the `.git` folder or erase history.
2. Commit and push to `main`. The repo contains `scripts/build_pages.sh`, `wrangler.jsonc`, and `package.json`. You do not need GitHub Actions or a `cloudflare-pages` branch.
3. In the [Cloudflare dashboard](https://dash.cloudflare.com/), open **Workers & Pages**, create or configure a **Worker** connected to your GitHub repository. Select `main`, root directory blank, build command `bash scripts/build_pages.sh` and deploy command `npx wrangler deploy`.
4. Cloudflare Workers Builds provides a build image with Python, Node.js and npm. The script installs PlatformIO, esptool and Pillow in an isolated Python environment; no credentials or API keys need to be committed. The build may take several minutes the first time because it downloads ESP32 toolchains.
5. After the successful deployment, open your Worker's **Settings > Domains & Routes** and add custom domain `esp32-pc-control-deck.lepczynski.it` (the zone must be in Cloudflare). Make sure there is no conflicting active Pages custom domain or Worker route with that hostname. The dashboard may create the required DNS record automatically.
6. Open `https://esp32-pc-control-deck.lepczynski.it/` in Chrome or Edge. Check that the original hardware photo, animated demo and firmware version are visible. Download the bridge ZIP and test firmware flashing over USB with the supported Elecrow ESP32 board.

The custom domain and Git connection require one-time Cloudflare dashboard action. Subsequent pushes to `main` are automatic.

### Migrating from the old GitHub Actions + Pages configuration

The old architecture used GitHub Actions to publish a `cloudflare-pages` branch, followed by Cloudflare Pages Git integration. This version replaces that pipeline. The GitHub Actions workflow was removed from the repo. If an old Pages project is already deployed for the same domain, remove its custom-domain binding before adding the domain to the new Worker. You can keep the old Pages project until the Worker deployment has been tested on its `workers.dev` address. Do not enable both pipelines for the same hostname.

## Release consistency

`bash scripts/build_pages.sh` obtains the current SHA from `git rev-parse HEAD`, runs Python tests, bundles the browser installer library locally, compiles the `esp32_pc_control_deck` PlatformIO environment, combines the bootloader, partitions and firmware into a single image, and publishes the whole output into `dist/`. The firmware manifest references the merged binary at offset 0. The Python bridge ZIP comes from the same checkout and excludes `host/config.json`. The SHA and firmware digest are checked before deployment.

Only the latest **successful** build is deployed. If firmware, bundling, tests or asset validation fail, the build command exits with a nonzero code and Wrangler is not run. The previous live deployment stays active.

Cloudflare Workers Static Assets has a limit of 25 MiB for an individual file. The real GIF in `docs/media/control-deck-demo.gif` is larger than that, so the build automatically generates a reduced-resolution GIF from the original for the website only. The original media remain unchanged in Git and the README.

## Browsers and hardware

The installer supports the Elecrow 2.8-inch ESP32-WROOM-32 touchscreen with CH340 serial and requires a data-capable USB cable, HTTPS and Chrome or Edge with Web Serial on a desktop computer. Close any serial monitor and the Python PC bridge before flashing. After installation the user must run the **separate PC bridge** for telemetry and touch macros; Web Serial cannot install or configure that desktop software.

## Privacy and security

- No passwords, OpenAI keys or tokens are stored on ESP32.
- No personal `host/config.json` or local logs are committed or included in PC bridge downloads.
- The firmware, installer library, static images and download ZIP are served through the same Cloudflare Worker domain. There is no runtime CDN, server, or analytics backend.
- Only the local PC bridge executes configured commands; ESP32 sends numeric macro IDs over USB.

## Developer checks

```sh
python -m unittest discover -s host/tests -v
python -m unittest discover -s scripts/tests -v
node --check site/app.js
```

The full production build is performed by Workers Builds. A local unit test does not prove successful ESP32 flashing: verify the first installation on real hardware before widely sharing the link.
