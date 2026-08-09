# VOID HUNTER

> Vertical shmup. 8-bit pixel art with Metal Slug-grade juice. **120 FPS lock.**

A 25-minute arcade run through three acts of a collapsing void, fighting 8 enemy
archetypes, 4 bosses with 4-phase patterns, 3 weapon paths, 6 visual themes,
24 procedural SFX and 4 BGM tracks. Built in Pygame 2.6+, zero external
dependencies (no numpy, no scipy — everything on `array.array` and `math`).

**Status:** `BLOQUE 0` — bootstrap. Spec is final; implementation in progress.

---

## Quick start

```powershell
python -m pip install -r requirements-dev.txt
python main.py --check       # validate imports + scene wiring
python main.py --profile     # run with FPS overlay (BLOQUE 14+)
python main.py                # play (BLOQUE 14+)
```

## Controls (BLOQUE 33)

| Action     | Keyboard | Gamepad |
| ---------- | -------- | ------- |
| Move WASD  | `W`/`A`/`S`/`D` (world-relative) | Stick |
| Aim        | Mouse (360° yaw)  | Right stick |
| Shoot      | `LMB` (hold = charge, release = fire) | `X` |
| Dash       | `Shift` (left, one-shot)  | `Y` |
| Bomb       | `L`      | `B`     |
| Pause      | `Esc`    | Start   |
| FPS overlay| `F1`     | —       |

Legacy keys: `J` still fires (testing), `K` is now free for future use.

## CLI flags

| Flag                 | Effect                                                 |
| -------------------- | ------------------------------------------------------ |
| `--check`            | Validate imports + scene wiring; exit 0/1              |
| `--profile`          | Run with FPS overlay                                   |
| `--act N`            | Start at act N (1, 2, or 3)                            |
| `--boss NAME`        | Fight boss (goliath, hydra, phantom, nemesis)          |
| `--debug`            | Enable debug HUD                                       |
| `--stress SPEC`      | Stress test: `1500particles 400bullets`                |
| `--duration SECS`    | Profile/stress duration (default 30)                   |
| `--validate-waves`   | Validate the 18 wave JSON scripts                      |

## Spec

The full GDD + Technical Spec lives at `docs/design/void-hunter-gdd.md`
(14 sections, ~19k words, BLOQUE 0..17 execution plan). The GDD is the source
of truth; this README is the dev cheatsheet.

## Architecture

```
void-hunter/
├── main.py                  # entry, CLI flags
├── src/
│   └── core/                # game loop, scene stack, input, event bus, settings
│       └── settings.py      # all constants (single source of truth)
├── tests/                   # pytest, coverage gate 35%
├── docs/design/             # GDD
├── pyproject.toml           # mypy strict, pytest, coverage config
└── requirements*.txt
```

## Performance target

- **Normal gameplay:** 120 FPS lock (8.33ms/frame budget).
- **Stress (1500 particles + 400 bullets + boss + shake):** 90 FPS minimum.
- **Zero allocations per frame** in `update()`/`draw()` of any system.
- **Single `target.blits()` batch** per frame in `ParticleEngine.draw()` and
  in `GameplayScene.draw()`.

## Quality gates

```powershell
pytest -q                                                          # tests
pytest --cov=src/ --cov-fail-under=35                               # coverage gate
mypy src/                                                          # mypy strict 0 errors
rg 'pygame\.Surface\(' src/systems/                                 # 0 matches outside init
rg 'import motor' src/                                             # 0 matches (soberanía)
```

## License

MIT.
