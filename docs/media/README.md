# Original project media

These are the original files used by the GitHub README and project website:

- `ESP32_PC_Control_Deck.jpg`
- `control-deck-demo.gif`

Both files show the actual hardware. Keep their filenames unchanged when replacing them.

The GIF is larger than the 25 MiB file limit for Cloudflare Workers static assets. During the website build, `scripts/build_site_release.py` creates a smaller animated copy in `dist/media/control-deck-demo.gif`. The original file in this directory is never modified. The photo is copied unchanged.

Commit any replacement photo or GIF to this directory. A successful Cloudflare build then republishes it automatically with the current firmware version and PC bridge package.
