# STELLAR HORIZON v1.0.0 — Project Report

> Horizontal 16-bit space shooter built on Void-Hunter's movement
> library. First public release.

## What it is

**Stellar Horizon** is a horizontal scrolling shooter (`480x270`
internal, scaled 4x to `1920x1080`) that reuses Void-Hunter's
bezier-path movement, particle engine, audio synthesis, and event
bus. One act (6 waves + 1 boss), six enemy types, ten weapons, one
boss with a full action state machine and 4-frame animation set,
and a Starfox-64-style power-up ring system (silver / gold with
stack-based max-life extension).

The whole thing runs at 120 FPS with `pygame.SCALED`, 16-bit pixel
art, MIDI music, and 30+ procedural SFX.

## Project layout

```
stellar_horizon/
├── main.py                  # CLI entry (--check, --duration N)
├── settings.py              # Display + pool sizes
├── smoke.py                 # 11 quality gates
├── audio/                   # MIDI + SFX (synth, sfx, thrusters)
├── core/                    # game loop, scene manager, clock
├── entities/                # player, enemies, boss, bullets, powerups
├── scenes/                  # title, gameplay, game over
├── ui/                      # HUD, backgrounds, animated sprite, mountains
├── waves/                   # wave data + bezier paths
├── fx/                      # particles, bullet VFX, dust, screen shake
├── assets/                  # sprites, backgrounds, MIDI
├── tests/                   # 22 test files
├── tools/                   # visual capture + asset processing
└── docs/                    # this report, design specs, release notes
```

## Architecture essentials

- **Fixed-timestep loop** at 120 FPS (`FIXED_DT = 1/120`, with a
  `DT_CLAMP` safety net for dropped frames). The frame loop reads
  `now` *before* ticking so the accumulator never collapses.
- **Scene manager** with `TitleScene → GameplayScene → GameOverScene`,
  cleanly separated by state. The boss fight is folded into
  `GameplayScene` (not a separate scene) so the HUD + power-up +
  thruster systems stay live during the fight.
- **Entity pools** (player bullets 32, enemy bullets 64, particles
  600) with the bullet pool **never filtered** — player spawns by
  finding the first dead slot, so a filtered list would shrink
  the pool to zero and break new shots.
- **Animated sprite sheets** (6 frames per entity at 12 FPS for
  ships/enemies, **8 FPS for the boss**). Single-frame laser
  sprites + code-driven VFX (alpha pulse, scale pulse, halo) for
  the 10 weapons.
- **Code-driven bullet VFX** (`fx/bullet_vfx.py`): per-weapon
  animation parameters in a `WEAPON_VFX_PARAMS` table — no
  AI-generated 6-frame strips for the lasers because round / heart
  shapes rendered inconsistently across frames.

## What's in v1.0.0

### Boss (Asteroid Guardian)

- **600 HP** (10x the prototype's 60) split across 2 phases
  (300/300 threshold). Each phase has its own cycle timing.
- **State machine** with 5 actions: `IDLE_PATROL → TELEGRAPH →
  CHARGE → RETREAT → COOLDOWN`. Phase 2 runs the same cycle with
  tighter timers.
- **Charge attack** with telegraph line: the boss aligns its Y
  with the player, paints a pulsing red line for 1.2s, then
  dashes at 250 px/s with yellow/orange thruster particles. All
  boss damage (contact + bullets) is 2 hearts per hit.
- **4-frame animation** (IDLE, TELEGRAPH, CHARGE, DYING) at
  8 FPS with 6 frames each. Each frame is AI-generated; the
  legacy "boss" sheet is kept as a fallback.
- **Hit-streak ring drop**: 50% chance to drop a silver ring on
  20 hits within 7 seconds. Streak resets on timeout or on the
  player taking boss damage.

### Power-up rings (Starfox-64 style)

- **Silver rings** heal 1 life, drop at 10% from any enemy kill.
- **Gold rings** heal 2 lives, drop at 5%, and count toward the
  gold stack: every 3 golds = +3 max lives (3 → 6 → 9 max).
- **Magneto pickup** at 30 px radius (no button press).
- **Lifetime 15 s + 3 s fade-out** so they don't linger forever.
- **Code-rendered** (no AI) for crispness at the 10 px scale.

### HUD

- **9 heart slots** (filled = current life, outline = unused cap)
  + **2 gold ring slots** showing the stack count.
- 10-icon weapon selector strip with the active weapon
  highlighted in yellow.
- Boss HP bar with quarter ticks.
- PTS score, wave indicator, enemy counter.

### Audio

- **MIDI music** with `midi_player.py` and 4 placeholder tracks
  (title, act1, boss, game_over).
- **30+ SFX** synthesized by `src/audio/synth.py` (shoot,
  shoot_charged, hit, explode_small/medium/boss, bomb,
  boss_warning, thruster_*, etc.).
- **Per-ship thruster loops** with dynamic compression
  (`1/sqrt(N)` per active ship) and a 7-channel cap.
- **MIDI pause/resume** on scene transitions (the lowpass test
  verifies continuous music across pause/resume).

## Test coverage

| Suite | Count | Pass rate |
|---|---|---|
| Boss tests (action cycle, hit-streak, damage) | 22 | 100% |
| PowerUp tests (magneto, lifetime, fade, drops) | 16 | 100% |
| Player tests (lives, gold stacks, take_hit) | 22 | 100% |
| HUD tests (hearts, gold stack, weapon strip) | 9 | 100% |
| Bullet VFX tests (per-weapon animation) | 12 | 100% |
| Thruster tests (per-ship loops, compression) | 24 | 100% |
| Animation + sparks tests | 9 | 100% |
| All other tests (waves, enemy, scene, fx, etc.) | 128 | 100% |
| **Total** | **239** | **100%** |
| Smoke gates (settings, movement, boss, HUD, etc.) | 11/11 | 100% |

Note: `test_scenes_gameplay.py` and `test_midi_player.py` require
the optional `mido` dependency. They run cleanly when `mido` is
installed; otherwise they're skipped without affecting the rest
of the suite.

## Stats

| Metric | Count |
|---|---|
| Game source files (non-test) | 39 |
| Test files | 22 |
| Total Python LOC | 6,165 |
| Game-only LOC (excl. tests) | 3,938 |
| Total repo files (excl. caches / playtest) | 260 |
| Sprite sheets (player, enemies, boss) | 32 |
| Single-frame weapon sprites | 10 |
| Boss animation sheets | 4 (IDLE, TELEGRAPH, CHARGE, DYING) |
| Boss animation FPS | 8 |
| MIDI tracks | 4 (title, act1, boss, game_over) |
| SFX in catalog | 30+ |
| Tooling scripts | 8 (capture, sprite processing, etc.) |

## How to run

```bash
# From the repo root (D:\AI\void-hunter):
$env:PYTHONPATH = 'D:\AI\void-hunter'

# Smoke test (~5 seconds, 11 gates)
python -m stellar_horizon.smoke

# Play the game
python -m stellar_horizon.main

# Play for N seconds then quit (good for screenshots)
python -m stellar_horizon.main --duration 60

# Validate imports + settings
python -m stellar_horizon.main --check

# Full test suite
python -m pytest stellar_horizon/tests/ -v
```

Or use the launchers in the project root:

```bash
.\stellar_horizon\run.bat    # or run.ps1
```

## Controls

- **WASD / Arrows** — move the ship
- **Space** — fire
- **1-9, 0** — switch weapon (1 = yellow plasma, 0 = rainbow)
- **Esc / window close** — quit

## Spec / design references

- `stellar_horizon/docs/superpowers/specs/2026-08-15-stellar-horizon-design.md`
- `stellar_horizon/docs/superpowers/plans/2026-08-15-stellar-horizon-phase1.md`
- `stellar_horizon/tools/playtest_out/` — visual smoke captures
  (boss states, ring pickups, HUD renders, contact sheets)

## Known limitations

- The 4 boss animations are static sprite sheets — there's no
  procedural animation on top. We considered code-driven scale /
  rotation pulses on the IDLE sheet but the static version reads
  cleanly at the 48 px size.
- The Starlord-64 pickup radius (30 px) is hard-coded. If we
  scale the playfield up later we'll need to make it relative.
- The star/mountain parallax scenery is 3 layers of static
  perlin noise — no real-time per-star animation.
- Boss has only 1 entry path. A second phase-2 entry that comes
  from a different angle would add variety.
- Test runs of `test_scenes_gameplay` and `test_midi_player`
  require `mido` (`pip install mido`).

## Roadmap (next likely additions)

- **Phase 2 entry** for the boss (re-entry from a new angle when
  HP drops below 300).
- **Beam / spread attack** in phase 2 (the telegraph code path
  is already there, just not wired to fire).
- **Endless mode** beyond act 1 with escalating difficulty.
- **More weapons** (the 10-weapon roster is locked but the
  `WEAPON_VFX_PARAMS` table can grow).
- **Soundtrack** (replace the placeholder MIDIs with a real
  soundtrack).
