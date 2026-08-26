# tools/video_gen — Video generation pipeline

BLOQUE 58.59. Generates the four cinematic videos for Void Hunter:

| ID | Format | Output |
|----|--------|--------|
| V1-S | 9:16 1080×1920 mp4 | `release/videos/void_hunter_title_v1_1080x1920.mp4` |
| V2-S | 9:16 1080×1920 mp4 | `release/videos/void_hunter_zoom_v1_1080x1920.mp4` |
| V1-G | 240×360 PNG sequence | `Assets/video/title/frames/frame_*.png` (loopable) |
| V2-G | 240×360 PNG sequence | `Assets/video/zoom/frames/frame_*.png` (one-shot) |

## Quick start

```bash
# From project root, with venv active:
.venv/Scripts/python.exe tools/video_gen/gen_v1_title.py
.venv/Scripts/python.py gen_v2_zoom.py

# Encode the in-game frames to mp4 standalone:
.venv/Scripts/python.exe tools/video_gen/encode_mp4.py \
    output/frames/v1_draft2 \
    release/videos/void_hunter_title_v1_540x960.mp4 540 960 30

# Extract key frames for review:
.venv/Scripts/python.exe tools/video_gen/preview_frames.py \
    output/frames/v1_draft2 \
    output/preview 30 v1_draft2
```

## Module structure

- `common/palette.py` — neon cyan/magenta/rose palette
- `common/effects.py` — chroma key, glow halo, scanlines, vignette, starfield
- `common/pixel_font.py` — 5×7 pixel font (used for the logo dissolve)
- `common/pixel_grid.py` — enforce pixel grid via LANCZOS downscale + NEAREST upscale
- `common/ship_overlay.py` — blits ship_01 with auto-chroma-key (sprite ships have a dark-gray background baked in)
- `common/composition.py` — nebula, asteroid, planet, pixel text draw helpers
- `gen_v1_title.py` — V1 generator (12s, 360 frames @ 30 FPS)
- `gen_v2_zoom.py` — V2 generator (10s, 300 frames @ 30 FPS)
- `encode_mp4.py` — ffmpeg wrapper, PNG sequence → H.264 mp4
- `build_spritesheet.py` — PNG sequence → horizontal sprite-sheet PNG (TBD)
- `preview_frames.py` — extract key frames to PNGs in `output/preview/`

## How the videos integrate into the game

The PNG sequences at `Assets/video/title/frames/` and `Assets/video/zoom/frames/`
are loaded by `src/ui/video_player.py` (VideoPlayer class). TitleScene uses
the title video as its background; CinematicScene plays the zoom video
between TITLE and ACT_INTRO. ESC skips the cinematic.

When PyInstaller bundles the game, the PNG sequences are included via
`build.spec`'s `datas=[...]` section (search for `BLOQUE 58.59`).

## Why procedural pixel art (not AI video)?

We considered AI video (Wan / Kling / Sora). Pure AI gen is bad at:
- Enforcing a strict pixel grid (everything comes out anti-aliased)
- Matching the exact in-game ship sprite pixel-for-pixel
- Seamless looping

Procedural PIL gives us deterministic, pixel-perfect, 100% controllable
output. The user can iterate on a single frame and the whole video
re-generates consistently.

## Customizing

- **Palette** — edit `common/palette.py` (PALETTE_VOID dict)
- **Ship** — change `_SHIP_01_DIR` in `common/ship_overlay.py` to any other
  `Assets/sprites/player_ships/ship_NN/`
- **Text** — `common/pixel_font.py` has all chars needed for "VOID HUNTER"
  + "PRESS ANY KEY TO START" + "C: CREDITS"; add more as needed
- **Timing** — the timeline constants in `gen_v1_title.py` and
  `gen_v2_zoom.py` are clear and self-documenting
