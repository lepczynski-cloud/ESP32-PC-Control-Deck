'use strict';

const byId = id => document.getElementById(id);
byId('year').textContent = String(new Date().getFullYear());

const animationTargets = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }
  }, { threshold: 0.1, rootMargin: '0px 0px -26px 0px' });
  for (const target of animationTargets) observer.observe(target);
} else {
  for (const target of animationTargets) target.classList.add('is-visible');
}

const status = byId('install-status');
const installer = byId('installer-container');
const version = byId('firmware-version');
const commit = byId('firmware-commit');
const download = byId('download-firmware');
const bridge = byId('download-bridge');

async function installerReady() {
  if (!window.customElements) return false;
  return Promise.race([
    window.customElements.whenDefined('esp-web-install-button').then(() => true),
    new Promise(resolve => setTimeout(() => resolve(false), 8000))
  ]);
}

async function checkLatestBuild() {
  try {
    const response = await fetch('/firmware/build-info.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (data.chip_family !== 'ESP32' || !/^[\w.+-]+$/.test(data.version || '') || !/^[0-9a-f]{40}$/.test(data.commit || '') || data.file !== 'esp32-pc-control-deck.bin') {
      throw new Error('Unexpected firmware metadata');
    }
    version.textContent = data.version;
    commit.textContent = data.commit.slice(0, 8);
    download.href = '/firmware/' + data.file;
    download.hidden = false;

    if (!window.isSecureContext || !('serial' in navigator)) {
      status.textContent = 'Firmware is ready. Flashing from the page requires desktop Chrome or Edge over HTTPS.';
      return;
    }
    if (await installerReady()) {
      installer.hidden = false;
      status.textContent = 'Ready. Connect the supported Elecrow board and close other apps using its COM port.';
    } else {
      status.textContent = 'Firmware is ready, but the browser installer could not load. You can download the binary below.';
    }
  } catch (error) {
    version.textContent = 'Not published';
    commit.textContent = 'Waiting for build';
    status.textContent = 'The browser installer will be available after the first successful GitHub Actions build.';
    installer.hidden = true;
    download.hidden = true;
  }
}

async function checkPCBridge() {
  try {
    const response = await fetch('/downloads/PC-Control-Deck-PC-Bridge.zip', { method: 'HEAD', cache: 'no-store' });
    if (!response.ok) throw new Error('PC bridge unavailable');
    bridge.href = '/downloads/PC-Control-Deck-PC-Bridge.zip';
    bridge.setAttribute('download', 'PC-Control-Deck-PC-Bridge.zip');
  } catch (error) {
    bridge.href = 'https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck/archive/refs/heads/main.zip';
    bridge.textContent = 'Download full project';
  }
}

checkLatestBuild();
checkPCBridge();
