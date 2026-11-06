# Website, Web Serial installer and automatic releases

The project website uses static HTML, CSS and JavaScript. GitHub Actions builds firmware and publishes a complete static release. Cloudflare Pages hosts the generated branch. **You do not need to build firmware or upload binaries manually after setup.**

## Deployment settings

| Field | Value |
| --- | --- |
| Source repository | `lepczynski-cloud/ESP32-PC-Control-Deck` |
| Source branch | `main` |
| GitHub Actions workflow | `.github/workflows/publish-web-installer.yml` |
| Generated branch | `cloudflare-pages` |
| Cloudflare Pages project | `esp32-pc-control-deck` |
| Custom domain | `esp32-pc-control-deck.lepczynski.it` |
| Framework preset | `None` |
| Cloudflare build command | leave blank, or `exit 0` if mandatory |
| Cloudflare output directory | `.` (root of generated branch) |
| Web installer manifest | `/firmware/manifest.json` |
| Merged firmware image | `/firmware/esp32-pc-control-deck.bin` |
| PC bridge package | `/downloads/PC-Control-Deck-PC-Bridge.zip` |

## One-time setup

1. **Back up the current GitHub repository.** Keep its history and existing real `docs/media/ESP32_PC_Control_Deck.jpg` and `docs/media/control-deck-demo.gif` files. Do not recreate the repository or force-push an unrelated orphan history.
2. Replace the repository files on the existing `main` branch with this package and commit normally. Preserve original media if uploading via Git; the workflow also knows how to recover these two files from earlier commits in the same Git history.
3. Visit [GitHub Actions](https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck/actions). Wait for the **Build firmware and publish web installer** workflow to pass. It may require **Settings > Actions > General > Workflow permissions > Read and write permissions**, depending on repository policy. Its job uses the built-in `GITHUB_TOKEN`, not a personal access token.
4. The successful workflow creates `cloudflare-pages`. Never edit this generated branch manually. Build failures stop before publishing.
5. In [Cloudflare](https://dash.cloudflare.com/), open **Workers & Pages** and create a **Pages** project connected to GitHub. Select `lepczynski-cloud/ESP32-PC-Control-Deck`.
6. Select **production branch `cloudflare-pages`**, framework **None**, root directory blank, build command blank (`exit 0` if required) and output directory `.`. Deploy.
7. In the Pages project, use **Custom domains > Set up a domain** to add `esp32-pc-control-deck.lepczynski.it`. When `lepczynski.it` is in the same Cloudflare account, Cloudflare normally creates the necessary DNS entry. Otherwise, follow the CNAME value shown by Cloudflare. You do not need a separate hosting server.
8. Open `https://esp32-pc-control-deck.lepczynski.it/`, verify the real project photo and GIF, then check that the firmware version is displayed and the PC bridge ZIP is downloadable.

## How the release stays in sync

The workflow checks out the full Git history, tests Python, bundles ESP Web Tools locally and builds the `esp32_pc_control_deck` PlatformIO environment from the triggering `main` commit. A Python release script combines bootloader, partition data and firmware into a **single ESP32 image**. ESP Web Tools installs that image at address `0x0` for the target ESP32-WROOM-32 board. It also builds the PC bridge ZIP from the same checkout, writes the Git SHA to `build-info.json`, verifies the output and only then publishes.

The installer serves the **latest successfully built release**. A failed build leaves the previous website and firmware intact. There is no need for Cloudflare to compile firmware. Do not edit the generated branch.

## Real photo and GIF

The public source repository already had these files before the site was added:

- `docs/media/ESP32_PC_Control_Deck.jpg`
- `docs/media/control-deck-demo.gif`

This package does **not** include mock images. If either media file is missing after replacing the source tree, the workflow looks for the last real file in the existing Git history. It rejects the known placeholder files from the early development ZIPs. The resulting website serves the real files locally from `/media/`, so it does not hotlink them from GitHub. If the history is unavailable or contains only placeholders, publication stops with an explicit error. Restore the original images in `docs/media/` and commit them to fix the error.

The README embeds the published Cloudflare media URL, so it will display after the first successful website deployment.

## Browser and hardware requirements

The firmware installer is intended only for the original Elecrow 2.8-inch ESP32-WROOM-32 display with CH340 USB serial. It uses ESP Web Tools and the browser's Web Serial support, available in compatible desktop Chrome/Edge browsers over HTTPS. It does not install the computer bridge. The user must separately install Python 3, download the PC bridge package and run its launcher.

Web Serial flashing is a hardware operation. Close serial monitors and the PC bridge first; the USB serial port cannot be used by two programs simultaneously. Use a data-capable cable and confirm that the board matches the documented pinout.

## Security and deployment notes

- No Cloudflare token, PAT, API key or secret is stored in this repository.
- GitHub Actions uses `GITHUB_TOKEN` with `contents: write` to publish the generated branch.
- The user-provided `host/config.json` is excluded from source control and bridge downloads.
- ESP Web Tools is bundled during GitHub Actions and served from the same Cloudflare Pages domain as the installer. No runtime CDN or backend server is required. The browser still downloads the static firmware files over HTTPS.
- The generated media, downloads and firmware are served through Cloudflare Pages after deployment.
- Set the Pages production branch to `cloudflare-pages`, not `main`.
- Verify GitHub branch protection and Actions permissions if the release branch cannot be created.

## Testing

From the repository root:

```sh
python -m unittest discover -s host/tests -v
python -m unittest discover -s scripts/tests -v
node --check site/app.js
```

A successful GitHub workflow performs the actual ESP32 build. A local test without PlatformIO cannot prove that flashing will work on the physical device. Verify the first installation on your hardware before sharing the installer publicly.

## Installer JavaScript

GitHub Actions installs the verified `esp-web-tools@10.4.0` library and bundles its browser entry with esbuild. The generated site hosts `/vendor/esp-web-tools.js` itself. The source repository does not need a checked-in `node_modules/` folder. Third-party license details are included in the generated site when available.
