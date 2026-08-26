# BLOQUE 58.59 — Cinematic Videos (Title + Zoom)

**Date:** 2026-08-25
**Status:** DESIGN — approved by user
**Author:** Mavis
**BLOQUE scope:** 58.59
**GitHub:** `https://github.com/lerius700-cmyk/Void-Hunter`

---

## 1. Problem

The current `TitleScene` (`src/ui/scenes.py:140`) runs a procedural demo loop with ships, bullets, and explosions over a black starfield. The "VOID HUNTER" logo is plain white pygame text. The visual is functional but flat — no atmosphere, no logo reveal, no sense of "cinematic".

There is no transition cinematic between TITLE and ACT_INTRO; the game jumps directly to "ACT 1 — GOLIATH AWAITS".

The player ship is iconic (Star Fox 64 Arwing-style) but appears only at gameplay scale. A close-up reveal of the ship at the start of a run would reinforce identity and "this is your ride".

User request (Lerius, 2026-08-25, in Spanish): "crea un video en pixel art para la pantalla de inicio (donde dice press start) de este juego. tambien crea un video pixel art de la nave del jugador donde se vea de cerca, y la camara se vaya alejando hasta llegar a la distancia en donde esta el gameplay."

User also requested: "2 videos standalone, 2 videos in-game" — so the same two videos are produced in two formats (standalone marketing + in-game integration).

## 2. Goal

Produce **4 video deliverables** + integrate 2 of them into the game:

| ID | Concept | Format | Use |
|----|---------|--------|-----|
| V1-S | Title screen background | mp4 9:16 (1080×1920) standalone | TikTok / Reels / portfolio |
| V1-G | Title screen background | sprite-sheet PNG 240×360 (2:3) | in-game, replaces TitleScene background |
| V2-S | Ship_01 close-up dolly-back to gameplay | mp4 9:16 (1080×1920) standalone | TikTok / Reels / portfolio |
| V2-G | Same dolly-back | sprite-sheet PNG 240×360 (2:3) | in-game, new CinematicScene between TITLE and ACT_INTRO |

**Locked design decisions** (from brainstorming Q&A):
- **Style:** modern detailed pixel art + neon glow (cinematic). Matches `ship_01_base.png` aesthetic + "Keep Kept" reference (cyberpunk neon humanoid + floating door).
- **Technique:** hybrid. Backgrounds = procedural pixel art with PIL (asteroids, nebula, starfield, parallax). Ship = real game sprite from `Assets/sprites/player_ships/ship_01/idle/` + `propulsion/` (8 rotation frames). Final pixel grid enforced via downscale + `PIL.Image.NEAREST`.
- **Title content (V1):** logo reveal (píxel-disolve 0-4s) → ambient phase (4-7.5s) → demo loop (7.5-12s, seamless back to ambient).
- **Zoom content (V2):** ship_01 close-up center, slow continuous dolly back over 10s, nebula → asteroids → planet layers fade in progressively, ends with ship in gameplay position.
- **Ship featured:** `ship_01` (Arwing cyan) in all 4 videos.
- **Standalone format:** 9:16 vertical 1080×1920 (TikTok/Reels).
- **In-game integration:** full integration + tests + .exe rebuild.
- **Iteration order:** standalone first (V1-S draft → user validates look & feel → V2-S → user validates → then V1-G + V2-G + integration + tests + .exe).

## 3. Architecture

### 3.1 Tool pipeline (new module `tools/video_gen/`)

```
tools/video_gen/
├── common/
│   ├── __init__.py
│   ├── palette.py            # PALETTE_VOID constants + glow helpers
│   ├── pixel_grid.py         # enforce_pixel_grid(img, target_w, target_h)
│   ├── effects.py            # chromatic_aberration, scanline, glow_halo
│   ├── ship_overlay.py       # blit_ship_01(surface, cx, cy, scale, anim_phase, t)
│   └── composition.py        # compose_frame(bg, ship_layer, fx, frame_index)
├── gen_v1_title.py           # V1-S + V1-G frame generation
├── gen_v2_zoom.py            # V2-S + V2-G frame generation
├── encode_mp4.py             # PNG-sequence → H.264 mp4 (ffmpeg)
├── build_spritesheet.py      # PNG sequence → sprite-sheet + manifest.json
├── preview_frames.py         # extract key frames as PNG stills to tools/playtest_out/
└── README.md                 # how to run the pipeline
```

### 3.2 In-game integration (modified/new code)

```
src/ui/
├── video_player.py           # NEW: sprite-sheet player (~80 LOC)
├── title_scene.py            # SIMPLIFY: background = VideoPlayer(V1-G) + text overlay
├── cinematic_scene.py        # NEW: CinematicScene plays V2-G, then ACT_INTRO
└── (existing) ...
src/core/
├── scene_manager.py          # MODIFY: add GameState.CINEMATIC, register transitions
└── (existing) ...
src/audio/
└── music.py                  # MODIFY: add play_cinematic_sting() (1.5s procedural sting)
```

### 3.3 Storage (new assets, no changes to existing)

```
Assets/video/
├── title/
│   ├── frames/frame_0000.png ... frame_0359.png   # V1-G, 360 frames @ 30 FPS = 12s
│   ├── title_sheet.png                            # horizontal sprite-sheet (V1-G loaded as one)
│   └── manifest.json                              # {fps:30, frame_count:360, w:240, h:360}
└── zoom/
    ├── frames/frame_0000.png ... frame_0299.png   # V2-G, 300 frames @ 30 FPS = 10s
    ├── zoom_sheet.png
    └── manifest.json

release/videos/
├── void_hunter_title_v1_standalone.mp4            # V1-S, 1080×1920
└── void_hunter_zoom_v1_standalone.mp4             # V2-S, 1080×1920
```

PyInstaller `_find_assets_dir()` (existing in `src/ui/scenes.py:97`) resolves `Assets/video/` correctly both in dev and in the bundled .exe.

### 3.4 `VideoPlayer` API (new module)

```python
class VideoPlayer:
    def __init__(self, frames_dir: Path, fps: int, loop: bool = False) -> None
    def play(self) -> None
    def update(self, dt: float) -> None          # advance frame based on dt
    def draw(self, target: Surface) -> None      # blit current frame, scaled to target
    def is_finished(self) -> bool                # True iff non-loop and last frame shown
    def get_progress(self) -> float              # 0.0-1.0
    def reset(self) -> None                      # rewind to frame 0
```

### 3.5 Scene state machine (modified)

Current TITLE → ACT_INTRO transition is direct. New flow:
- `TITLE` → on any key → `CINEMATIC`
- `CINEMATIC` → on video_finished (after 10s) → `ACT_INTRO`
- `CINEMATIC` → on ESC key → skip directly to `ACT_INTRO` (user override)

`GameState` enum gets `CINEMATIC` (added between `TITLE` and `ACT_INTRO`).

## 4. Content specifications

### 4.1 V1 timeline (12s @ 30 FPS = 360 frames)

| Frame | t (s) | Content |
|-------|-------|---------|
| 0-29 | 0.0-1.0 | Black + stars, no other elements. Silent anticipation. |
| 30-59 | 1.0-2.0 | ship_01 silhouette enters from left (scale 2x, fast). |
| 60-89 | 2.0-3.0 | "V" forms (pixel dissolve, each pixel has 1-3 frame random delay). |
| 75-104 | 2.5-3.5 | "VOID" complete, "HUNTER" begins dissolving in. |
| 105-119 | 3.5-4.0 | "VOID HUNTER" complete, single glow pulse. |
| 119 | 4.0 | Brief chromatic aberration flash (2 frames). Logo stable. |
| 120-134 | 4.0-4.5 | "PRESS ANY KEY" fades in below logo. |
| 120-224 | 4.0-7.5 | **Ambient phase.** Ship_01 enters from left, does slow arc, exits right. 1-2 asteroids drift. Nebula behind. Loop seam at end (cross-fade 6 frames). |
| 225-359 | 7.5-12.0 | **Demo loop.** Ship_01 + 1 enemy ship. Bullets, explosion, hitstop, 6-frame cross-fade back to ambient. Seamless loop with the ambient. |

### 4.2 V2 timeline (10s @ 30 FPS = 300 frames)

| Frame | t (s) | Content |
|-------|-------|---------|
| 0-59 | 0.0-2.0 | Stars-only black bg. Ship_01 close-up center, scale ~3x. Slight idle bob. `player_propulsion/frame_0.png` rotated. |
| 60-104 | 2.0-3.5 | Nebula layer fades in (parallax back-1). Ship scale reduces. |
| 105-149 | 3.5-5.0 | Asteroids start drifting (parallax mid-1). |
| 150-194 | 5.0-6.5 | Planet/void anomaly fades in (parallax far-1). |
| 195-239 | 6.5-8.0 | Ship continues dolly back. All 3 parallax layers visible. |
| 240-284 | 8.0-9.5 | Ship near gameplay position (scale 1x). Background rich. |
| 285-299 | 9.5-10.0 | Final 8-frame ease-out. Ship lands in gameplay position. Frame 300 = exact "ready to play" frame. |

Camera motion: continuous slow dolly back, no cuts. Easing: ease-out cubic in last 1.5s. Parallax: 3 layers at different speeds (back slowest, mid faster, foreground fastest).

### 4.3 TitleScene modifications

Remove procedural demo (`_draw_demo_ships`, `_draw_demo_bullets`, `_draw_demo_explosions`, ship-flying logic in `update()`). New flow:
- `__init__`: create `VideoPlayer(Assets/video/title/manifest.json, loop=True)`
- `on_enter`: `video_player.play()` + `music.play_title_music()` (existing, unchanged)
- `update`: `video_player.update(dt)` + input handling (any key → `transition_to(CINEMATIC)`)
- `draw`: `video_player.draw(target)` + render "VOID HUNTER" text + "PRESS ANY KEY" + "C: CREDITS"

"PRESS ANY KEY TO START" stays hidden during the logo reveal (0-4s), fades in at 4s, then blinks as before.

### 4.4 CinematicScene (new)

- `on_enter`: `video_player.play(loop=False)` + `music.play_cinematic_sting()`
- `update`: `video_player.update(dt)` + if `is_finished()` → cross-fade to gameplay BGM + `transition_to(ACT_INTRO)`
- `draw`: `video_player.draw(target)` (full screen, no overlay)
- ESC key skips to `ACT_INTRO` immediately

## 5. Audio strategy

| Version | Audio approach | Implementation |
|---------|----------------|----------------|
| V1-S standalone | mp4 SILENT | TikTok/Reels prefer user-music. No audio track. |
| V1-G in-game | Existing `pantalla_principal.wav` BGM (unchanged) | Already plays in `TitleScene.on_enter()`. Video is silent. |
| V2-S standalone | mp4 with audio (procedural sting from `src/audio/synth.py` + ambient swell) | New sting: 1.5s impact + 8.5s slow swell. Generated as WAV, muxed into mp4 by ffmpeg. |
| V2-G in-game | Same procedural sting via `music.play_cinematic_sting()` + cross-fade to gameplay BGM at end | New method in `src/audio/music.py` reusing existing synth infrastructure. |

Sting design: square+noise ADSR with lowpass sweep (matches `boss_warning` style from `src/audio/synth.py`).

## 6. Tests

New pytest files in `tests/`:

| File | Validates |
|------|-----------|
| `test_video_player.py` | VideoPlayer load, advance, FPS, loop/non-loop, is_finished |
| `test_video_assets.py` | manifest.json exists, valid JSON, frame_count matches files |
| `test_title_scene_with_video.py` | TitleScene init with video present doesn't crash |
| `test_cinematic_scene.py` | CinematicScene transitions to ACT_INTRO when video_finished |
| `test_scene_manager_cinematic_state.py` | GameState.CINEMATIC exists, TITLE→CINEMATIC→ACT_INTRO registered |
| `test_video_mp4_export.py` | release/videos/*.mp4 exist, >0 bytes, expected duration (ffprobe) |
| `test_pixel_grid_consistency.py` | Every frame is exact dimensions (240×360) RGBA |

Target: 7 new tests + 1,171 existing = 1,178 / 1,178 pass.

## 7. Acceptance criteria

- [ ] **V1-S** — mp4 9:16 1080×1920 30 FPS 12s, logo dissolve legible, demo loop seamless, neon palette, no broken pixel grid
- [ ] **V2-S** — mp4 9:16 1080×1920 30 FPS 10s, dolly continuous (no cuts), ship_01 recognizable, rich background at end
- [ ] **V1-G** — sprite-sheet 240×360 30 FPS 12s loop, plays in TitleScene, "PRESS ANY KEY" visible after reveal, transitions to CINEMATIC on any key
- [ ] **V2-G** — sprite-sheet 240×360 30 FPS 10s one-shot, plays in CinematicScene, transitions to ACT_INTRO at end
- [ ] **Tests** — 7 new + 1,171 existing = 1,178 / 1,178 pass
- [ ] **Build .exe** — `pyinstaller build.spec --clean -y` exit 0, title + cinematic visible in `.exe`
- [ ] **Visual evidence** — user explicitly confirms each deliverable with frame PNG (per profile: "visual changes need explicit frame evidence")

## 8. Iteration loop

```
Per video:
  1. Generate draft (lower fidelity: 720p standalone or 240×360 in-game)
  2. Deliver PNG stills of key frames + mp4 preview
  3. User reviews visually, marks adjustments
  4. Iterate, re-deliver
  5. "Listo" → next video
```

## 9. Risks & honest assessment

- **#1 Pixel grid consistency:** if backgrounds have anti-aliasing, ship looks "stuck on top". Mitigation: enforced `PIL.Image.NEAREST` final pass.
- **#2 Loop seamlessness:** demo end → ambient start. Mitigation: 6-frame cross-fade; verified by `title_video_loop_seam.png`.
- **#3 Procedural sting quality:** if sting is bad, V2-G feels worse than silent. Mitigation: keep it simple (3 notes + swell, like existing `boss_warning` SFX).
- **#4 Build regression:** any code change can break existing 1,171 tests. Mitigation: run `pytest tests/ -q` after every code change.
- **NOT recommended:** doing all 4 versions in parallel. Standalone first, validate, then replicate to in-game.

## 10. Dependencies

- Python 3.11+, Pillow, numpy (already in `requirements.txt`)
- ffmpeg on PATH (for `encode_mp4.py` and `test_video_mp4_export.py`)
- PyInstaller (already in `requirements-dev.txt`)
- Optional: mcode-tools / video-creater (WanVideoWrapper) — NOT used for this BLOQUE; all backgrounds are procedural with PIL for determinism. Can be added in a future BLOQUE for richer keyframes.

## 11. What we do NOT do (per user preferences)

- ❌ Auto-commit / auto-zip / auto-version after each change — user decides.
- ❌ Assume "listo" = "compiló" — require explicit frame PNG approval.
- ❌ Modify the existing BGM `pantalla_principal.wav` or any existing audio.

## 12. Execution order

1. Write this spec → commit (this document).
2. Set up `tools/video_gen/` infrastructure.
3. **Phase A** — V1-S draft (8-12s @ 720p standalone) + key frame PNGs. User validates.
4. Iterate V1-S until "listo".
5. **Phase B** — V2-S draft (8-10s @ 720p standalone) + key frame PNGs. User validates.
6. Iterate V2-S until "listo".
7. **Phase C** — Produce full-res 1080×1920 mp4s for V1-S and V2-S.
8. **Phase D** — Convert to in-game sprite-sheets (240×360, same content) for V1-G and V2-G.
9. **Phase E** — Integrate: write `src/ui/video_player.py`, simplify `TitleScene`, add `CinematicScene`, add `CINEMATIC` state to `scene_manager.py`, add `play_cinematic_sting()` to `music.py`.
10. **Phase F** — Write 7 new pytest tests.
11. **Phase G** — Run full test suite (1,178 / 1,178 pass). Build .exe. User validates the .exe.

---
END OF DESIGN
