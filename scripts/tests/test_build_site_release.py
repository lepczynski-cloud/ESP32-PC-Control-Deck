import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_site_release.py"
spec = importlib.util.spec_from_file_location("web_build", SCRIPT)
web_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_build)

JPEG_SAMPLE = b"\xff\xd8\xff\xe0" + b"J" * 5000
GIF_SAMPLE = b"GIF89a" + b"G" * 5000
COMMIT = "a" * 40


class WebReleaseTests(unittest.TestCase):
    def test_firmware_version_from_hello(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "main.cpp"
            f.write_text('hello["firmware"] = "0.3.3";', encoding="utf-8")
            self.assertEqual(web_build.read_version(f), "0.3.3")

    def test_flash_offsets_and_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "too-big.bin"
            f.write_bytes(b"X" * 40000)
            with self.assertRaises(ValueError):
                web_build.validate_segments([(0x1000, f), (0x8000, f), (0xE000, f), (0x10000, f)])

    def test_merged_image_is_4mb_dio_and_correct_offsets(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            parts = []
            for n in range(4):
                f = folder / f"{n}.bin"
                f.write_bytes(b"TEST" * 100)
                parts.append(f)
            segments = list(zip([0x1000, 0x8000, 0xE000, 0x10000], parts))
            out = folder / "merged.bin"

            def fake_run(cmd, check):
                self.assertTrue(check)
                self.assertIn("merge_bin", cmd)
                self.assertEqual(cmd[cmd.index("--flash_mode") + 1], "dio")
                for offset, path in segments:
                    self.assertEqual(cmd[cmd.index(hex(offset)) + 1], str(path))
                out.write_bytes(b"A" * 80000)

            with patch.object(web_build.subprocess, "run", side_effect=fake_run):
                web_build.merge_firmware(segments, out)

    def test_current_real_media(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "docs" / "media"
            media.mkdir(parents=True)
            (media / "ESP32_PC_Control_Deck.jpg").write_bytes(JPEG_SAMPLE)
            (media / "control-deck-demo.gif").write_bytes(GIF_SAMPLE)
            self.assertEqual(web_build.media_bytes(root, "ESP32_PC_Control_Deck.jpg"), JPEG_SAMPLE)
            self.assertEqual(web_build.media_bytes(root, "control-deck-demo.gif"), GIF_SAMPLE)

    def test_media_recovered_from_git_history(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            def git(*args):
                subprocess.run(["git", *args], cwd=source, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            git("init")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.org")
            media = source / "docs/media"
            media.mkdir(parents=True)
            photo = media / "ESP32_PC_Control_Deck.jpg"
            photo.write_bytes(JPEG_SAMPLE)
            gif = media / "control-deck-demo.gif"
            gif.write_bytes(GIF_SAMPLE)
            git("add", ".")
            git("commit", "-m", "Original photos")
            photo.unlink()
            gif.unlink()
            git("add", "-u")
            git("commit", "-m", "Replace source tree")
            self.assertEqual(web_build.media_bytes(source, photo.name), JPEG_SAMPLE)
            self.assertEqual(web_build.media_bytes(source, gif.name), GIF_SAMPLE)

    def test_full_published_site_is_self_contained(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            (source / "site").mkdir(parents=True)
            (source / "site/index.html").write_text("<title>test</title>", encoding="utf-8")
            (source / "src").mkdir()
            (source / "src/main.cpp").write_text('hello["firmware"] = "0.3.3";', encoding="utf-8")
            (source / "docs/media").mkdir(parents=True)
            (source / "docs/media/ESP32_PC_Control_Deck.jpg").write_bytes(JPEG_SAMPLE)
            (source / "docs/media/control-deck-demo.gif").write_bytes(GIF_SAMPLE)
            (source / "host").mkdir()
            for filename in web_build.BRIDGE_FILES:
                (source / "host" / filename).write_text("file content", encoding="utf-8")
            (source / "host/config.json").write_text("SECRET_LOCAL_PATH")
            build = source / ".pio/build" / web_build.ENVIRONMENT
            build.mkdir(parents=True)
            for filename in ("bootloader.bin", "partitions.bin", "firmware.bin"):
                (build / filename).write_bytes(b"B" * 1024)
            boot = Path(temp) / "boot_app0.bin"
            boot.write_bytes(b"A" * 1024)
            target = Path(temp) / "out"
            with patch.object(web_build, "merge_firmware", side_effect=lambda seg, out: out.write_bytes(b"X" * 80000)):
                manifest, info = web_build.assemble(source, target, COMMIT, boot_override=boot)
            self.assertEqual(manifest["builds"][0]["parts"][0]["offset"], 0)
            self.assertEqual(info["commit"], COMMIT)
            self.assertEqual((target / "media/ESP32_PC_Control_Deck.jpg").read_bytes(), JPEG_SAMPLE)
            self.assertEqual((target / "media/control-deck-demo.gif").read_bytes(), GIF_SAMPLE)
            with __import__("zipfile").ZipFile(target / "downloads" / web_build.BRIDGE_NAME) as z:
                self.assertIsNone(z.testzip())
                self.assertFalse(any(name.endswith("/config.json") for name in z.namelist()))


if __name__ == "__main__":
    unittest.main()
