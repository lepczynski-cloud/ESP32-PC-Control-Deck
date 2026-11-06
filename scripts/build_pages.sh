#!/usr/bin/env bash
# Build and validate the site, firmware and bridge from the current Git commit.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required by the Cloudflare build image." >&2
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required to package ESP Web Tools." >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "A Git checkout is required to identify the source commit." >&2
  exit 1
fi

COMMIT="$(git rev-parse HEAD)"
if [[ ! "$COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Could not determine the source revision." >&2
  exit 1
fi

# Do not deploy files left by another revision.
rm -rf dist site/vendor .venv-build
python3 -m venv .venv-build
PYTHON="$(pwd)/.venv-build/bin/python"
PIO="$(pwd)/.venv-build/bin/pio"
"$PYTHON" -m pip install --disable-pip-version-check --upgrade pip
"$PYTHON" -m pip install --disable-pip-version-check 'platformio>=6.1,<7' 'esptool>=4.7,<5' 'Pillow>=11,<13'
"$PYTHON" -m pip install --disable-pip-version-check -r host/requirements.txt
"$PYTHON" -m unittest discover -s host/tests -v
"$PYTHON" -m unittest discover -s scripts/tests -v

# Pin the Node tools in package.json; run install on the build server, not on the device.
npm install --include=dev --no-audit --no-fund
mkdir -p site/vendor
./node_modules/.bin/esbuild node_modules/esp-web-tools/dist/web/install-button.js \
  --bundle --format=esm --platform=browser --target=es2022 --minify \
  --outfile=site/vendor/esp-web-tools.js
if [[ -f node_modules/esp-web-tools/LICENSE ]]; then
  cp node_modules/esp-web-tools/LICENSE site/vendor/ESP-WEB-TOOLS-LICENSE.txt
fi
node --check site/app.js

"$PIO" run -e esp32_pc_control_deck
"$PYTHON" scripts/build_site_release.py --source . --output dist --commit "$COMMIT"
"$PYTHON" scripts/validate_site_release.py --root dist --commit "$COMMIT"

echo "Ready to deploy source revision ${COMMIT:0:8} using npx wrangler deploy"
