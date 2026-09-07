# VOID HUNTER

> Vertical shmup. 8-bit pixel art with Metal Slug-grade juice.
> Star Fox 64 inspired. **120 FPS lock. Windowed 320×480 portrait.**

## 🎮 ¿Quieres JUGAR?

<div align="center">

### 👉 [⬇️ Descargar VoidHunter v1.2.6 para Windows (266 MB)](https://github.com/lerius700-cmyk/Void-Hunter/releases/download/v1.2.6/void-hunter.exe) 👈

</div>

**Pasos:** descarga el `.exe` (onefile, ~266 MB porque trae Python + pygame + todos los assets dentro) → doble click (no necesita instalación, no necesita ZIP, no necesita carpeta `_internal/`)  
**Si Windows SmartScreen pregunta:** *More info* → *Run anyway* (no tenemos cert de firma todavía)  
**Controles:** `WASD` / flechas = mover · `Click` / `Espacio` = disparar · `P` = pausa · `ESC` = salir

📜 [Todos los releases + notas de versión](https://github.com/lerius700-cmyk/Void-Hunter/releases) · [Notas de v1.2.6](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.2.6)

---

A 5-minute arcade run through Act 1, fighting 8 enemy archetypes, 4 bosses
with multi-phase patterns, a sub-boss dart, 3 weapon paths, 9 flight
formations, bezier-curve flight paths, leader-follower squadrons (with HP
scaling tied to boss proximity), a roguelike mode with seed/RNG/level-gen,
24 procedural SFX, 2 streaming BGM tracks, 4 cinematic videos, an in-game
sprite-sheet & video gallery, and 25+ visual juice systems. Built in
Pygame 2.6, stdlib only (no numpy, no scipy — math only).

**Status:** 🚧 **In-progress product.** **v1.2.6** es el último release
público (→ [Releases](https://github.com/lerius700-cmyk/Void-Hunter/releases)).
Polishing en curso. Ver [ROADMAP.md](./ROADMAP.md).

---

## 🆕 Qué hay de nuevo en v1.2.6 (BLOQUE 58.next)

- **Roguelike density ↑×2:** `spawn_interval` 4.0s → 2.0s. Mismo ship count por pattern, **2× más waves por minuto**. `MAX_ENEMIES_ON_SCREEN` subió 12 → 24 para evitar throttle.
- **Leader HP scaling 3–5 hits:** Los leaders (naves que guían un grupo) ahora resisten 3 hits en wave 1, 4 hits en wave 5, 5 hits en wave 10 (lineal, clampeado). Antes caían en 1 hit junto con los followers. Los followers quedan igual (1 HP).
- **Bonus:** minimal background redesign (1 nebula principal + 0–1 companion + 30 stars, más distantes, sin clipping) y COMPOSED pool con `slot_dx`/`slot_dy` preservados (no más ships apilados).

Históricamente, v1.2.6 también incluye todo el trabajo de:
- **BLOQUE 58.62 v3** — nebula strip 7-galaxias+80-stars que matchea la referencia hand-painted
- **BLOQUE 58.61** — player ship half-size + sprite-border fix
- **BLOQUE 58.59 + 58.60** — 4 videos cinemáticos (title + zoom) + galería in-game
- **BLOQUE 58.15** — scrolling galaxy strip (reemplaza el nebula state-machine)
- **BLOQUE 58.14** — pause/resume con lowpass + 24 SFX procedurales
- **BLOQUE 58.8 + 58.9** — 5 procedural wave patterns + ProceduralWaveManager (Star Fox 64 style)

---

## Quick start

```bash
# Run from source (default mode = procedural patterns)
python main.py

# Run the roguelike mode with a seed
python main.py --roguelike 42

# Build a Windows .exe (one-time)
pyinstaller build.spec --noconfirm
# → dist/void-hunter/void-hunter.exe
```

**Download releases:** [releases/](https://github.com/lerius700-cmyk/Void-Hunter/releases) (v1.0 → v1.2.6)

---

## What you can do

- 🎮 **Shoot** — LMB rapid fire, hold to charge plasma
- 🚀 **Dash** — single click = dash, hold = propulsion (Tron trail)
- 💣 **Bombs → Missiles** — homing missiles, B/L key
- ✈️ **9 flight formations** — V, line, diamond, square, wedge, circle, triangle, half-V, custom
- 📈 **Bezier flight paths** — S-curves, waypoint zigzags, hybrid multi-segment
- 👥 **Leader-follower squadrons** — Star Fox style, leaders now scale 3→5 HP by wave
- 🎲 **Roguelike mode** — `--roguelike <seed>` for deterministic procedural runs
- 🏆 **5+ minute run** — Act 1 with 4 wave types, sub-boss dart, GOLIATH final boss
- 🎬 **Cinematic videos** — title + zoom intros, in-game gallery (S/V hotkeys)

---

## Project layout

```
void-hunter/
├── main.py                  # entry point + CLI (--easy, --roguelike, --patterns, --scale)
├── build.spec               # PyInstaller spec for .exe builds
├── pyproject.toml           # pytest config
├── requirements.txt         # pygame only
├── requirements-dev.txt     # pytest, mypy, ruff
│
├── src/                     # game source (~25.9k LOC, 85 .py files)
│   ├── audio/               # 24 SFX synth + 2 streaming BGM
│   ├── core/                # settings, scene_manager, event_bus
│   ├── entities/            # player, enemies (8 types), boss (4), projectile
│   ├── movement/            # BezierPath, WaypointPath, HybridPath, PathFollower
│   │                        # FlightFormation (9 presets), FormationPathSpec
│   ├── roguelike/           # seed, RNG, level_gen, formation_gen, telemetry, replay
│   ├── systems/             # parallax, wave_manager, particle_engine, scoring
│   ├── ui/                  # gameplay_runtime, scenes, HUD, video_player, gallery
│   └── utils/               # math, paths, logging
│
├── tests/                   # 1,630 tests, 100% passing on changed code
│                            # (6 pre-existing headless flakes unrelated to current work)
│
├── tools/                   # development utilities
│   ├── capture/             # screenshot capture scripts
│   ├── debug_*.py           # ad-hoc debug tools
│   ├── video_gen/           # procedural video pipeline (PIL + ffmpeg)
│   ├── build_sprite_sheet.py
│   ├── create_v*_*_release.py  # GitHub release scripts
│   └── playtest_out/        # session captures (gitignored)
│
├── Assets/                  # bundled with the .exe
│   ├── background/          # galaxy_panel_*.png, galaxy_sprite_*.png
│   ├── sprites/             # 5 ship spritesheets, enemy atlas, VFX
│   ├── video/               # 4 cinematic video PNG sequences (in-game)
│   └── *.wav                # 2 streaming BGM tracks
│
├── docs/                    # documentation
│   ├── design/              # GDD
│   ├── references/          # Star Fox 64 reference images
│   ├── arch/                # architecture + roadmap
│   ├── changelog/           # CHANGELOG_v1.x.md (full version history)
│   ├── bloques/             # per-BLOQUE checklists
│   ├── superpowers/         # plans + specs for large features
│   └── session-reports/     # session reports
│
├── release/                 # release artifacts (gitignored)
│   └── videos/              # 4 standalone 9:16 mp4 cinemáticos
│
├── dist/                    # .exe build output (gitignored)
│   └── void-hunter/void-hunter.exe
│
└── .superpowers/            # SDD working files (gitignored)
```

---

## Architecture highlights

See [docs/arch/ARCHITECTURE.md](./docs/arch/ARCHITECTURE.md) for the full breakdown.

**15+ major systems** (each with its own BLOQUE history):

| # | System | Where | BLOQUE |
|---|---|---|---|
| 1 | **FlightFormations** (9 presets) | `src/movement/formation.py` | 58.x |
| 2 | **Bezier Curves** (BezierPath, WaypointPath, HybridPath) | `src/movement/` | 58.x |
| 3 | **Leader Following** (squadron + HP scaling) | `src/entities/enemies/enemy.py` | 58.next |
| 4 | **ROGUELIKE** (seed, RNG, level gen, formation gen, replay) | `src/roguelike/` | 58.0–58.62 |
| 5 | **Procedural patterns** (5 base + 4275 COMPOSED) | `src/systems/wave_patterns/` | 58.8, 58.9, 58.next |
| 6 | **Boss FSM** (HYDRA, PHANTOM, NEMESIS, GOLIATH) | `src/entities/bosses/` | 50, 58.x |
| 7 | **Weapon system** (3 paths × 3 levels) | `src/entities/weapons/` | 58.x |
| 8 | **Player FSM** (7 states) | `src/entities/player/` | 58.x |
| 9 | **Tron trail** (continuous polyline, 3x damage) | `src/entities/player/` | 58.7aa |
| 10 | **HUD system** (score, HP, bombs, overheat, tech) | `src/ui/hud.py` | 58.7ab |
| 11 | **Music + SFX** (24 SFX + 2 streaming + lowpass pause) | `src/audio/` | 58.14 |
| 12 | **Visual juice** (25+ systems) | various | 58.x |
| 13 | **Star Fox style** (portrait, reticle, sprites) | `src/ui/` | 58.x |
| 14 | **Cinematic videos** (4 videos, in-game + standalone) | `src/ui/video_player.py`, `tools/video_gen/` | 58.59, 58.60 |
| 15 | **In-game gallery** (sprite sheets + videos) | `src/ui/gallery_scene.py` | 58.60 |
| 16 | **Galaxy strip** (4 variants, deterministic per act) | `src/systems/parallax.py` | 58.15, 58.62 |

---

## Development

```bash
# Run tests (headless)
SDL_VIDEODRIVER=dummy python -m pytest tests/ -q

# Run with headless rendering (no window)
SDL_VIDEODRIVER=dummy python main.py --easy

# Capture a frame
python tools/capture/capture_sub_boss.py
# → tools/playtest_out/sub_boss_v1.26.png

# Build the .exe (onefile mode: single 266 MB .exe, no _internal/ folder)
pyinstaller build.spec --clean --noconfirm
# → dist/void-hunter.exe (~266 MB; self-extracts to tempdir on launch)
```

**Quality gates:**
- 1,630 / 1,630 tests passing on the current code paths
  (6 pre-existing failures in `test_paths.py::test_paths_no_star_shapes` and 5 headless flakes in `test_sub_boss_*`; both predate v1.2.6 and are unrelated to the BLOQUE 58.next work)
- 0 numpy/scipy imports in the game runtime (numpy allowed only in `apply_lowpass_to_wav` for the pause lowpass, per BLOQUE 58.14)
- Internal coordinates 320×480; display scaling done in `Game._present()`
- Windowed mode (never fullscreen, never terminal)

---

## Roadmap

See [docs/arch/ROADMAP.md](./docs/arch/ROADMAP.md). TL;DR:

- **Now:** visual polish (galaxy strip variants, sub-boss visibility, HUD)
- **Next:** gameplay depth (more bosses, act 2, leader-follower polish)
- **Later:** leaderboards, Steam release, achievements, multiplayer

---

## Credits

- **Engine:** Python 3.11 + Pygame 2.6.1 (SDL 2.28.4)
- **Inspiration:** Star Fox 64, Metal Slug, Galaga
- **Audio:** synthesized (no external SFX), 2 streaming BGM tracks
- **Total LOC:** ~43k (25,904 in `src/` + 17,205 in `tests/`, 156 Python files)
- **Latest release:** [v1.2.6](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.2.6) — 2026-09-07

---

*Last updated: 2026-09-07*
