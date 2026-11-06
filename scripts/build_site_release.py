#!/usr/bin/env python3
"""Package firmware, bridge and original project media after a successful build."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ENVIRONMENT = "esp32_pc_control_deck"
FIRMWARE_NAME = "esp32-pc-control-deck.bin"
BRIDGE_NAME = "PC-Control-Deck-PC-Bridge.zip"
BRIDGE_FILES = (
    "config.example.json",
    "control_deck_bridge.py",
    "requirements.txt",
    "run_windows.bat",
    "run_linux_macos.sh",
    "install_autostart_windows.ps1",
    "uninstall_autostart_windows.ps1",
)
MEDIA_FILES = (
    "ESP32_PC_Control_Deck.jpg",
    "control-deck-demo.gif",
)
# SHA-256 of the synthetic placeholders that appeared in earlier draft archives.
# Rejecting these avoids presenting sample graphics as real photos or video.
BAD_MEDIA_HASHES = {
    "82251bff91c463f67402b21d5d21bd665771945443648c806c22778ff32c18f0",
    "bbefc92546574bd5e402dc3c68a79cb26e178e95101665c890ebfeb39eaa0117",
}


def required_file(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Missing or empty file: {path}")
    return path


def read_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    found = re.search(r'\[\s*"firmware"\s*\]\s*=\s*"([0-9A-Za-z._+-]+)"', text)
    return found.group(1) if found else "main"


def valid_media(filename: str, content: bytes) -> bool:
    if not content or hashlib.sha256(content).hexdigest() in BAD_MEDIA_HASHES:
        return False
    if filename.lower().endswith(".jpg"):
        return len(content) > 3000 and content.startswith(b"\xff\xd8\xff")
    if filename.lower().endswith(".gif"):
        return len(content) > 3000 and content.startswith((b"GIF87a", b"GIF89a"))
    return False


def media_bytes(source: Path, filename: str) -> bytes:
    relative = Path("docs/media") / filename
    relative_posix = relative.as_posix()
    current = source / relative
    if current.is_file():
        content = current.read_bytes()
        if valid_media(filename, content):
            return content
        print(f"Ignored placeholder or invalid current media: {relative}", file=sys.stderr)

    # A full repository replacement is still a normal Git commit. The user's
    # existing real media remain in Git history even if absent from the ZIP.
    # The current checkout should contain the media. Git history is a fallback.
    commits = subprocess.run(
        ["git", "-C", str(source), "rev-list", "HEAD", "--", relative_posix],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if commits.returncode == 0:
        for rev in commits.stdout.splitlines():
            result = subprocess.run(
                ["git", "-C", str(source), "show", f"{rev}:{relative_posix}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0 and valid_media(filename, result.stdout):
                print(f"Recovered original {filename} from Git commit {rev[:8]}")
                return result.stdout
    raise FileNotFoundError(
        f"Real media '{relative}' not found in the checkout or Git history. "
        "Keep the original file in docs/media or commit it before publishing. "
        "Synthetic placeholder files are intentionally not accepted."
    )


MAX_CLOUDFLARE_ASSET_BYTES = 25 * 1024 * 1024


def write_demo_gif(source_bytes: bytes, destination: Path) -> None:
    """Publish the optimized real-device GIF without rebuilding media on Cloudflare."""
    if len(source_bytes) > MAX_CLOUDFLARE_ASSET_BYTES:
        raise ValueError("GIF exceeds the 25 MiB asset limit; optimize docs/media/control-deck-demo.gif before publishing")
    destination.write_bytes(source_bytes)


def copy_media(source: Path, output: Path) -> None:
    target = output / "media"
    target.mkdir(parents=True, exist_ok=True)
    for filename in MEDIA_FILES:
        content = media_bytes(source, filename)
        destination = target / filename
        if filename.lower().endswith(".gif"):
            write_demo_gif(content, destination)
        else:
            destination.write_bytes(content)


def find_boot_app0() -> Path:
    roots = [Path.home() / ".platformio" / "packages", Path.home() / ".platformio"]
    matches = []
    for root in roots:
        if root.exists():
            matches.extend(root.glob("framework-arduinoespressif32/tools/partitions/boot_app0.bin"))
            if not matches:
                matches.extend(root.rglob("boot_app0.bin"))
            if matches:
                break
    if not matches:
        raise FileNotFoundError("boot_app0.bin was not found in the installed Arduino ESP32 framework")
    return required_file(matches[0])


def validate_segments(segments):
    if [x for x, _ in segments] != [0x1000, 0x8000, 0xE000, 0x10000]:
        raise ValueError("Unexpected ESP32 flash offsets")
    for (offset, path), boundary in zip(segments, [0x8000, 0xE000, 0x10000, 0x400000]):
        if offset + path.stat().st_size > boundary:
            raise ValueError(f"Flash segment at {hex(offset)} overlaps another segment: {path}")


def merge_firmware(segments, destination: Path):
    cmd = [sys.executable, "-m", "esptool", "--chip", "esp32", "merge_bin",
           "-o", str(destination), "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB"]
    for offset, path in segments:
        cmd.extend((hex(offset), str(path)))
    subprocess.run(cmd, check=True)
    required_file(destination)
    if destination.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Firmware exceeds the ESP32-WROOM-32 4 MB flash capacity")


def bundle_bridge(source: Path, destination: Path):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for filename in BRIDGE_FILES:
            archive.write(required_file(source / "host" / filename), f"PC-Control-Deck/host/{filename}")
        archive.writestr("PC-Control-Deck/README-FIRST.txt", (
            "ESP32 PC Control Deck - PC bridge\n\n"
            "The ESP32 firmware does not monitor your computer by itself.\n"
            "Install Python 3 on your computer and keep the bridge running.\n\n"
            "Windows: Extract this ZIP, then run host\\run_windows.bat.\n"
            "macOS/Linux: Extract this ZIP, then run sh host/run_linux_macos.sh.\n"
            "Edit host/config.json locally for your macros and serial port.\n"
            "Project: https://github.com/lepczynski-cloud/ESP32-PC-Control-Deck\n"
        ))


def assemble(source: Path, output: Path, commit: str, boot_override: Path = None):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected a 40-character Git SHA")
    build = source / ".pio" / "build" / ENVIRONMENT
    segments = [
        (0x1000, required_file(build / "bootloader.bin")),
        (0x8000, required_file(build / "partitions.bin")),
        (0xE000, required_file(boot_override) if boot_override else find_boot_app0()),
        (0x10000, required_file(build / "firmware.bin")),
    ]
    validate_segments(segments)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source / "site", output)
    copy_media(source, output)
    firmware_dir = output / "firmware"
    firmware_dir.mkdir()
    image = firmware_dir / FIRMWARE_NAME
    merge_firmware(segments, image)
    version = f"{read_version(source / 'src/main.cpp')}+{commit[:8]}"
    manifest = {
        "name": "ESP32 PC Control Deck (Elecrow 2.8-inch)",
        "version": version,
        "builds": [{"chipFamily": "ESP32", "parts": [{"path": FIRMWARE_NAME, "offset": 0}]}],
    }
    info = {
        "name": "ESP32 PC Control Deck", "version": version,
        "firmware_version": read_version(source / "src/main.cpp"),
        "commit": commit, "chip_family": "ESP32", "file": FIRMWARE_NAME,
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "size_bytes": image.stat().st_size,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (firmware_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (firmware_dir / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    downloads = output / "downloads"
    downloads.mkdir()
    bundle_bridge(source, downloads / BRIDGE_NAME)
    print(f"Built website from commit {commit[:8]}: {version}")
    print(f"Firmware SHA-256: {info['sha256']}")
    return manifest, info


def main():
    parser = argparse.ArgumentParser(description="Generate the ESP32 PC Control Deck website release")
    parser.add_argument("--source", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path(".pio/site-output"))
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    assemble(args.source.resolve(), args.output.resolve(), args.commit)


if __name__ == "__main__":
    main()
