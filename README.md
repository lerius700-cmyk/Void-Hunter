# VOID HUNTER

> Vertical shmup. 8-bit pixel art with Metal Slug-grade juice.
> Star Fox 64 inspired. **120 FPS lock. Windowed 320×480 portrait.**

## 🎮 ¿Quieres JUGAR?

<div align="center">

### 👉 [⬇️ Descargar VoidHunter v1.1.6 para Windows (279 MB)](https://github.com/lerius700-cmyk/Void-Hunter/releases/download/v1.1.6/VoidHunter-v1.1.6-win64.zip) 👈

</div>

**Pasos:** descarga el ZIP → extrae en cualquier carpeta → doble click a `void-hunter.exe`  
**Si Windows SmartScreen pregunta:** *More info* → *Run anyway* (no tenemos cert de firma todavía)  
**Controles:** `WASD` / flechas = mover · `Click` / `Espacio` = disparar · `P` = pausa · `ESC` = salir

📜 [Todos los releases + notas de versión](https://github.com/lerius700-cmyk/Void-Hunter/releases) · [Notas de v1.1.6](https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.1.6)

---

A 5-minute arcade run through Act 1, fighting 8 enemy archetypes, 4 bosses
with multi-phase patterns, a sub-boss dart, 3 weapon paths, 9 flight
formations, bezier-curve flight paths, leader-follower squadrons, a
roguelike mode with seed/RNG/level-gen, 24 procedural SFX, 2 streaming
BGM tracks, and 25+ visual juice systems. Built in Pygame 2.6, zero
heavy dependencies (no numpy, no scipy — stdlib math only).

**Status:** 🚧 **In-progress product.** **v1.0.0** es el último release
público (→ [Releases](https://github.com/lerius700-cmyk/Void-Hunter/releases)).
Polishing en curso (galaxy scroll, sub-boss visibility, HUD layout, neon
propulsion). Ver [ROADMAP.md](./ROADMAP.md).

---

## Quick start

```bash
# Run from source
python main.py --easy

# Run the roguelike mode
python main.py --easy --roguelike 42

# Build a Windows .exe (one-time)
pyinstaller build.spec --noconfirm
# → dist/void-hunter/void-hunter.exe
```

**Download releases:** [releases/](./releases/) (v1.0 + v1.1)

---

## What you can do

- 🎮 **Shoot** — LMB rapid fire, hold to charge plasma
- 🚀 **Dash** — single click = dash, hold = propulsion (Tron trail)
- 💣 **Bombs → Missiles** — homing missiles, B/L key
- ✈️ **9 flight formations** — V, line, diamond, square, wedge, circle, triangle, half-V, custom
- 📈 **Bezier flight paths** — S-curves, waypoint zigzags, hybrid multi-segment
- 👥 **Leader-follower squadrons** — Star Fox style "follow the leader"
- 🎲 **Roguelike mode** — `--roguelike <seed>` for deterministic procedural runs
- 🏆 **5+ minute run** — Act 1 with 4 wave types, sub-boss dart, GOLIATH final boss

---

## Project layout

```
void-hunter/
├── main.py                  # entry point + CLI (--easy, --roguelike, --scale)
├── smoke.py                 # 11-gate smoke test (run before commit)
├── build.spec               # PyInstaller spec for .exe builds
├── pyproject.toml           # pytest config
├── requirements.txt         # pygame only
├── requirements-dev.txt     # pytest, mypy, ruff
│
├── src/                     # game source (28k LOC, 118 .py files)
│   ├── audio/               # 24 SFX synth + 2 streaming BGM
│   ├── core/                # settings, scene_manager, event_bus
│   ├── entities/            # player, enemies (8 types), boss (4), projectile
│   ├── movement/            # BezierPath, WaypointPath, HybridPath, PathFollower
│   │                        # FlightFormation (9 presets), FormationPathSpec
│   ├── roguelike/           # seed, RNG, level_gen, formation_gen, telemetry, replay
│   ├── systems/             # wave_manager, particle_engine, scoring, theme
│   ├── ui/                  # gameplay_runtime (5.7k LOC), scenes, HUD, galaxy bg
│   └── utils/               # math, paths, logging
│
├── tests/                   # 1024 tests, 100% passing
│
├── tools/                   # development utilities
│   ├── capture/             # screenshot capture scripts
│   ├── build/               # asset pipeline (galaxy split, etc.)
│   ├── analysis/            # SFX spectral analysis
│   ├── sprite/              # sprite_forge (procedural sprite generator)
│   └── playtest_out/        # current session captures (gitignored)
│
├── Assets/                  # bundled with the .exe
│   ├── background/          # galaxy_strip.png (640×5760), 3 panels
│   ├── sprites/             # 83-sprite atlas (player, enemies, bosses)
│   └── *.wav                # 2 streaming BGM tracks
│
├── docs/                    # documentation
│   ├── design/              # GDD
│   ├── references/          # Star Fox 64 reference images
│   ├── CHANGELOG_v1.x.md    # full version history
│   ├── USER_PROMPTS_CHECKLIST.md
│   └── ...
│
├── releases/                # 27 zips (v1.0 → v1.27) — gitignored
├── archive/                 # legacy content (kept, gitignored)
│   ├── _legacy_builds/      # 10 archive_* folders from old PyInstaller builds
│   ├── _legacy_data/        # data/, .cleanup_backup/
│   ├── _legacy_references/  # Referencias/, source PNGs
│   ├── _legacy_screenshots/ # 156 historical playtest PNGs
│   ├── _legacy_scripts/     # debug scripts, COMMIT_MSG_*.txt, tools/_legacy/
│   └── _legacy_v1_0/        # archive_dist_void_hunter_v1.0
│
└── dist/                    # .exe build output (gitignored)
    └── void-hunter/void-hunter.exe
```

---

## Architecture highlights

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the full breakdown.

**13 major systems** (each with its own BLOQUE history):

| # | System | Where | Lines |
|---|---|---|---|
| 1 | **FlightFormations** (9 presets) | `src/movement/formation.py` | 212 |
| 2 | **Bezier Curves** (BezierPath, WaypointPath, HybridPath, PathFollower) | `src/movement/` | 381 |
| 3 | **Flight Paths** (procedural by seed) | `src/movement/spec.py` | 60 |
| 4 | **Leader Following** (squadron + time_offset) | `src/entities/enemies/enemy.py` | inline |
| 5 | **ROGUELIKE** (seed, RNG, level gen, formation gen, telemetry, replay) | `src/roguelike/` | 1,540 |
| 6 | **Boss FSM** (HYDRA, PHANTOM, NEMESIS, GOLIATH) | `src/entities/bosses/` | varies |
| 7 | **Weapon system** (3 paths × 3 levels) | `src/entities/weapons/` | varies |
| 8 | **Player FSM** (7 states) | `src/entities/player/` | varies |
| 9 | **Tron trail** (continuous polyline, 3x damage) | `src/entities/player/` | varies |
| 10 | **HUD system** (score, HP, bombs, overheat, tech) | `src/ui/hud.py` | 404 |
| 11 | **Music + SFX** (24 SFX + 2 streaming) | `src/audio/` | 1,420 |
| 12 | **Visual juice** (25+ systems) | various | varies |
| 13 | **Star Fox style** (portrait, reticle, sprites) | `src/ui/` | varies |

---

## Development

```bash
# Run tests
python -m pytest tests/

# Run with headless rendering (no window)
SDL_VIDEODRIVER=dummy python main.py --easy

# Capture a frame
python tools/capture/capture_sub_boss.py
# → tools/playtest_out/sub_boss_v1.26.png

# Build the .exe
pyinstaller build.spec --noconfirm
```

**Quality gates:**
- 1,024 / 1,024 tests passing (29s)
- 0 numpy/scipy imports
- Internal coordinates 320×480
- Windowed mode (never fullscreen, never terminal)

---

## Roadmap

See [docs/ROADMAP.md](./docs/ROADMAP.md). TL;DR:

- **Now**: visual polish (galaxy scroll, sub-boss visibility, HUD)
- **Next**: gameplay depth (more bosses, act 2, leader-follower polish)
- **Later**: leaderboards, Steam release, achievements, multiplayer

---

## Credits

- **Engine:** Python 3.11 + Pygame 2.6.1 (SDL 2.28.4)
- **Inspiration:** Star Fox 64, Metal Slug, Galaga
- **Audio:** synthesized (no external SFX), 2 streaming BGM tracks
- **Total LOC:** 28,066 (118 Python files, including tests)
- **Status:** in-progress product, v1.27 is the last released version

---

*Last updated: 2026-08-17*
