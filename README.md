# VOID HUNTER

> Vertical shmup. 8-bit pixel art with Metal Slug-grade juice.
> Star Fox 64 inspired. **120 FPS lock. Windowed 320×480 portrait.**

## 🎮 ¿Quieres JUGAR?

<div align="center">

### 👉 [⬇️ Descargar VoidHunter v1.4.0 para Windows (381 MB)](https://github.com/lerius700-cmyk/Void-Hunter/releases/download/v1.4.0/void-hunter.exe) 👈

</div>

**Pasos:** descarga el `.exe` (onefile, ~381 MB porque trae Python + pygame + todos los assets dentro) → doble click (no necesita instalación, no necesita ZIP, no necesita carpeta `_internal/`)
**Si Windows SmartScreen pregunta:** *More info* → *Run anyway* (no tenemos cert de firma todavía)
**Controles:** `WASD` / flechas = mover · `Click` / `Espacio` = disparar · `P` = pausa · `ESC` = salir

📜 [Todos los releases + notas de versión](https://github.com/lerius700-cmyk/Void-Hunter/releases) · [Notas de v1.4.0](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0)

---

A 5-minute arcade run through Act 1, fighting 8 enemy archetypes, 4 bosses
with multi-phase patterns, a sub-boss dart, 3 weapon paths, 9 flight
formations, bezier-curve flight paths, leader-follower squadrons (with HP
scaling tied to boss proximity), a roguelike mode with seed/RNG/level-gen,
25 procedural SFX, 2 streaming BGM tracks, 4 cinematic videos, an in-game
sprite-sheet & video gallery, MINE-ASTEROID stealth enemies (25% spawn),
and 25+ visual juice systems. Built in
Pygame 2.6, stdlib only (no numpy, no scipy — math only).

**Status:** 🚧 **In-progress product.** **v1.4.0** es el último release
público (→ [Releases](https://github.com/lerius700-cmyk/Void-Hunter/releases)).
Polishing en curso. Ver [ROADMAP.md](./docs/arch/ROADMAP.md).

---

## 🆕 Qué hay de nuevo en v1.4.0 (BLOQUE 71 + 71.1 + 71.2)

- **BLOQUE 71 — Shape-aware 70% white hit flash.** Todos los asteroides, MINE-ASTEROIDs y enemigos (SCOUT/CRUISER/HEAVY) ahora hacen un flash blanco al recibir impacto, pero **shape-aware**: en lugar de un cuadrado blanco encima, se overlay una silueta blanca al 70% que respeta la forma del sprite original (preserva el detalle debajo).
- **BLOQUE 71.2 — Fix del bug "blancuscas".** En v1.3.0 los enemigos se quedaban blancos permanentes después de recibir un solo impacto. La causa: el `hit_timer` solo se decrementaba en la rama MINE-ASTEROID de `Enemy.update()`. Fix: el decremento se movió al top de `update()`, así todos los enemy kinds parpadean y se recuperan correctamente.
- **MINE-ASTEROID feature completo** (BLOQUE 64-70): 25% spawn rate, variant-aware camouflage (5 tipos de asteroide), closed-state immunity, se abre al cruzar y=120 (primer cuarto), dispara 3 balas en abanico a 1Hz continuo en estado `open3`.
- **Defensive `NoneType` guard** en `_level1_chain` para que `GameplayRuntime()` no rompa cuando se construye directamente en tests.
- **25 procedural SFX** (+1 nuevo: `asteroid_hit` para feedback de impacto en asteroides).

Históricamente, v1.4.0 también incluye todo el trabajo de:
- **BLOQUE 70** — fix del bug "100% mines" (Asteroid NameError silenciado por main loop)
- **BLOQUE 68-69** — MINE-ASTEROID first-quarter trigger (y=120) + static asteroids fix
- **BLOQUE 66-67** — MINE-ASTEROID continuous 1Hz fire + variant-aware camouflage
- **BLOQUE 64.A-B** — asteroide 64×64 indestructible + GOLIATH 6-animation borderless sprite-sheet
- **BLOQUE 62** — Full top-down ship pass (8 ships, no 3/4 angle)
- **BLOQUE 58.59 + 58.60** — 4 videos cinemáticos + galería in-game

---

## Quick start

```bash
# Run from source (default mode = procedural patterns)
python main.py

# Run the roguelike mode with a seed
python main.py --roguelike 42

# Build a Windows .exe (one-time)
pyinstaller build.spec --noconfirm
# → dist/void-hunter.exe
```

**Download releases:** [releases/](https://github.com/lerius700-cmyk/Void-Hunter/releases) (v1.0 → v1.4.0)

---

## What you can do

- 🎮 **Shoot** — LMB rapid fire, hold to charge plasma
- 🚀 **Dash** — single click = dash, hold = propulsion (Tron trail)
- 💣 **Bombs → Missiles** — homing missiles, B/L key
- ✈️ **9 flight formations** — V, line, diamond, square, wedge, circle, triangle, half-V, custom
- 📈 **Bezier flight paths** — S-curves, waypoint zigzags, hybrid multi-segment
- 👥 **Leader-follower squadrons** — Star Fox style, leaders now scale 3→5 HP by wave
- 🎲 **Roguelike mode** — `--roguelike <seed>` for deterministic procedural runs
- 💣 **MINE-ASTEROID stealth enemies** — 25% de spawns, se camuflan como asteroides, abren al cruzar y=120
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
├── src/                     # game source (~24.3k LOC, 86 .py files)
│   ├── audio/               # 25 SFX synth + 2 streaming BGM
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
│                            # (25 pre-existing headless flakes unrelated to current work)
│
├── tools/                   # development utilities
│   ├── capture/             # screenshot capture scripts
│   ├── redesign_bosses/     # GOLIATH sprite generation pipeline
│   ├── redesign_ships/      # ship sprite generation pipeline
│   ├── ribbon_weapon/       # procedural ribbon weapon generator
│   ├── tiles/               # tile background generator
│   ├── boss_tester/         # interactive boss testing tool
│   ├── video_gen/           # procedural video pipeline (PIL + ffmpeg)
│   ├── build_sprite_sheet.py
│   ├── create_v*_*_release.py  # GitHub release scripts
│   └── playtest_out/        # session captures (gitignored)
│
├── Assets/                  # bundled with the .exe
│   ├── background/          # galaxy_panel_*.png, galaxy_sprite_*.png
│   ├── sprites/             # 5 ship spritesheets, enemy atlas, VFX, GOLIATH 64.B
│   ├── video/               # 4 cinematic video PNG sequences (in-game)
│   ├── sounds/              # procedural .wav (25 SFX)
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
│   ├── void-hunter.exe
│   └── VoidHunter-v1.4.0-win64.zip
│
└── _trash_2026-09-10/       # 41 transient files from release prep (safe to rm)
```

---

## Architecture highlights

See [docs/arch/ARCHITECTURE.md](./docs/arch/ARCHITECTURE.md) for the full breakdown.

**16+ major systems** (each with its own BLOQUE history):

| # | System | Where | BLOQUE |
|---|---|---|---|
| 1 | **FlightFormations** (9 presets) | `src/movement/formation.py` | 58.x |
| 2 | **Bezier Curves** (BezierPath, WaypointPath, HybridPath) | `src/movement/` | 58.x |
| 3 | **Leader Following** (squadron + HP scaling) | `src/entities/enemies/enemy.py` | 58.next |
| 4 | **ROGUELIKE** (seed, RNG, level gen, formation gen, replay) | `src/roguelike/` | 58.0–58.62 |
| 5 | **Procedural patterns** (5 base + 4275 COMPOSED) | `src/systems/wave_patterns/` | 58.8, 58.9, 58.next |
| 6 | **Boss FSM** (HYDRA, PHANTOM, NEMESIS, GOLIATH) | `src/entities/bosses/` | 50, 58.x, 64.B |
| 7 | **MINE-ASTEROID stealth** (variant camo + 1Hz fire) | `src/entities/enemies/mine_asteroid.py` | 63-70 |
| 8 | **Player FSM** (7 states) | `src/entities/player/` | 58.x |
| 9 | **Tron trail** (continuous polyline, 3x damage) | `src/entities/player/` | 58.7aa |
| 10 | **Hit feedback** (shape-aware 70% white flash) | `src/entities/asteroid.py` | 71, 71.1, 71.2 |
| 11 | **HUD system** (score, HP, bombs, overheat, tech) | `src/ui/hud.py` | 58.7ab |
| 12 | **Music + SFX** (25 SFX + 2 streaming + lowpass pause) | `src/audio/` | 58.14, 71 |
| 13 | **Visual juice** (25+ systems) | various | 58.x |
| 14 | **Star Fox style** (portrait, reticle, sprites) | `src/ui/` | 58.x |
| 15 | **Cinematic videos** (4 videos, in-game + standalone) | `src/ui/video_player.py`, `tools/video_gen/` | 58.59, 58.60 |
| 16 | **In-game gallery** (sprite sheets + videos) | `src/ui/gallery_scene.py` | 58.60 |
| 17 | **Galaxy strip** (4 variants, deterministic per act) | `src/systems/parallax.py` | 58.15, 58.62 |

---

## Development

```bash
# Run tests (headless)
SDL_VIDEODRIVER=dummy python -m pytest tests/ -q

# Run with headless rendering (no window)
SDL_VIDEODRIVER=dummy python main.py --easy

# Capture a frame
python tools/capture/capture_sub_boss.py
# → tools/playtest_out/sub_boss_v1.40.png

# Build the .exe (onefile mode: single 381 MB .exe, no _internal/ folder)
pyinstaller build.spec --clean --noconfirm
# → dist/void-hunter.exe (~381 MB; self-extracts to tempdir on launch)
```

**Quality gates:**
- 1,630 / 1,630 tests passing on the current code paths
  (~25 pre-existing failures: pygame uninit in `test_asteroid_sprites.py`, sub_boss order-dependent, Lissajous, GOLIATH frame duplicates from BLOQUE 64.B strategy — all predate v1.4.0)
- 0 numpy/scipy imports in the game runtime (numpy allowed only in `apply_lowpass_to_wav` for the pause lowpass, per BLOQUE 58.14)
- Internal coordinates 320×480; display scaling done in `Game._present()`
- Windowed mode (never fullscreen, never terminal)

---

## Roadmap

See [docs/arch/ROADMAP.md](./docs/arch/ROADMAP.md). TL;DR:

- **Now (v1.5.0):** BLOQUE 72 — 4-weapon powerup system (thick shot A, laser S, flamethrower D, double blue laser F) + RMB + mouse wheel cycling
- **Next:** gameplay depth (more bosses, act 2, leader-follower polish)
- **Later:** leaderboards, Steam release, achievements, multiplayer

---

## Credits

- **Engine:** Python 3.11 + Pygame 2.6.1 (SDL 2.28.4)
- **Inspiration:** Star Fox 64, Metal Slug, Galaga
- **Audio:** synthesized (no external SFX), 2 streaming BGM tracks
- **Total LOC:** ~42k (24,295 in `src/` + 17,497 in `tests/`, 86 + 38 = 124 Python files)
- **Latest release:** [v1.4.0](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0) — 2026-09-10

---

*Last updated: 2026-09-10*
