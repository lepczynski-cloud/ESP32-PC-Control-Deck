# Original photo and demonstration

This project has two real media assets in the existing Git history:

- `ESP32_PC_Control_Deck.jpg`
- `control-deck-demo.gif`

The build copies the original assets to the static site at `/media/`.
If the source files are absent after a full replacement, CI searches earlier commits for the originals. It rejects the old placeholder files.

If you add new photos or a new GIF later, commit them here using the same filenames. They will automatically replace the website media on the next successful deployment.
