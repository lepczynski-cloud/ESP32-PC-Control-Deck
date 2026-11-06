'use strict';
document.documentElement.classList.add('js');

const byId = (id) => document.getElementById(id);
byId('year').textContent = String(new Date().getFullYear());

if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    }
  }, { threshold: 0.08, rootMargin: '0px 0px -25px 0px' });
  document.querySelectorAll('.reveal').forEach((node) => revealObserver.observe(node));
} else {
  document.querySelectorAll('.reveal').forEach((node) => node.classList.add('visible'));
}

const installStatus = byId('install-status');
const installer = byId('installer-container');
const firmwareVersion = byId('firmware-version');
const firmwareCommit = byId('firmware-commit');
const firmwareDownload = byId('download-firmware');
const bridgeDownload = byId('download-bridge');

const getJson = async (path) => {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return response.json();
};

async function elementAvailable() {
  if (!window.customElements) return false;
  return Promise.race([
    customElements.whenDefined('esp-web-install-button').then(() => true),
    new Promise((resolve) => setTimeout(() => resolve(false), 6500))
  ]);
}

async function checkFirmware() {
  try {
    const [info, manifest] = await Promise.all([
      getJson('/firmware/build-info.json'),
      getJson('/firmware/manifest.json')
    ]);
    const build = manifest.builds && manifest.builds[0];
    const part = build && build.parts && build.parts[0];
    if (info.chip_family !== 'ESP32' || !/^[0-9a-f]{40}$/.test(info.commit || '') ||
        !/^[\w.+-]+$/.test(info.version || '') || info.file !== 'esp32-pc-control-deck.bin' ||
        info.size_bytes < 65536 || !/^[0-9a-f]{64}$/.test(info.sha256 || '') ||
        manifest.version !== info.version || build.chipFamily !== 'ESP32' ||
        build.parts.length !== 1 || part.path !== info.file || part.offset !== 0) {
      throw new Error('Firmware metadata and manifest do not match');
    }

    firmwareVersion.textContent = info.version;
    firmwareCommit.textContent = info.commit.slice(0, 10);
    firmwareDownload.href = '/firmware/' + info.file;
    firmwareDownload.hidden = false;

    if (!window.isSecureContext || !('serial' in navigator)) {
      installStatus.textContent = 'Firmware is available. Use a supported desktop Chrome or Edge browser over HTTPS to flash over USB.';
      return;
    }
    if (await elementAvailable()) {
      installer.hidden = false;
      installStatus.textContent = 'Ready. Connect the Elecrow ESP32, close serial monitors and choose your CH340 port.';
    } else {
      installStatus.textContent = 'Firmware is ready, but the browser installer did not load. Use the binary download or refresh the page.';
    }
  } catch (error) {
    installer.hidden = true;
    firmwareDownload.hidden = true;
    firmwareVersion.textContent = 'Unavailable';
    firmwareCommit.textContent = 'Not deployed';
    installStatus.textContent = 'Firmware is not available in this deployment: ' + error.message + '. Check the Cloudflare build and assets.';
  }
}

async function checkBridge() {
  try {
    const response = await fetch('/downloads/PC-Control-Deck-PC-Bridge.zip', { method: 'GET', headers: { Range: 'bytes=0-3' }, cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await response.body?.cancel();
  } catch (error) {
    bridgeDownload.href = 'https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck/archive/refs/heads/main.zip';
    bridgeDownload.textContent = 'Download project from GitHub ↗';
    bridgeDownload.removeAttribute('download');
    bridgeDownload.title = `Bridge package not found (${error.message}); download repository instead.`;
  }
}

byId('play-video').addEventListener('click', () => {
  const frame = byId('video-frame');
  const iframe = document.createElement('iframe');
  iframe.src = 'https://www.youtube-nocookie.com/embed/16eqHU4j9Fk?autoplay=1&rel=0';
  iframe.title = 'ESP32 PC Control Deck full project walkthrough';
  iframe.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; web-share';
  iframe.allowFullscreen = true;
  iframe.referrerPolicy = 'strict-origin-when-cross-origin';
  frame.replaceChildren(iframe);
});

checkFirmware();
checkBridge();
