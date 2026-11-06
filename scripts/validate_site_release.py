#!/usr/bin/env python3
"""Validate the complete static release before a Cloudflare deployment."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

MAX_WORKERS_ASSET = 25 * 1024 * 1024


def validate(root: Path, commit: str) -> None:
    root = root.resolve()
    info = json.loads((root / 'firmware/build-info.json').read_text())
    manifest = json.loads((root / 'firmware/manifest.json').read_text())
    assert info['commit'] == commit, 'Build commit does not match source commit'
    build = manifest['builds'][0]
    assert build['chipFamily'] == 'ESP32'
    part = build['parts'][0]
    assert part['offset'] == 0 and part['path'] == info['file']
    firmware = root / 'firmware' / part['path']
    assert firmware.stat().st_size > 64 * 1024
    assert hashlib.sha256(firmware.read_bytes()).hexdigest() == info['sha256']
    assert (root / 'media/ESP32_PC_Control_Deck.jpg').read_bytes().startswith(b'\xff\xd8\xff')
    assert (root / 'media/control-deck-demo.gif').read_bytes().startswith((b'GIF87a', b'GIF89a'))
    assert (root / 'index.html').is_file()
    assert (root / 'vendor/esp-web-tools.js').stat().st_size > 20000
    pc = root / 'downloads/PC-Control-Deck-PC-Bridge.zip'
    with zipfile.ZipFile(pc) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert any(n.endswith('/host/control_deck_bridge.py') for n in names)
        assert not any(n.endswith('config.json') and not n.endswith('config.example.json') for n in names)
    for path in root.rglob('*'):
        if path.is_file():
            assert path.stat().st_size <= MAX_WORKERS_ASSET, f'Cloudflare 25 MiB asset limit exceeded: {path}'
    assert not (root / 'host/config.json').exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--commit', required=True)
    args = ap.parse_args()
    validate(args.root, args.commit)
    print('Release verified for', args.commit[:8])


if __name__ == '__main__':
    main()
