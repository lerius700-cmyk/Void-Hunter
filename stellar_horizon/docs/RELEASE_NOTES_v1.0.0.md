# STELLAR HORIZON v1.0.0

**First public release.** Horizontal 16-bit space shooter built on
Void-Hunter's movement library. 480x270 internal scaled 4x to
1920x1080, 120 FPS, single act with 6 waves + boss fight.

## Highlights

### Boss — Asteroid Guardian
- **600 HP** (10x prototype) across 2 phases (300/300).
- **5-action state machine**: `IDLE_PATROL → TELEGRAPH → CHARGE →
  RETREAT → COOLDOWN` (faster in phase 2).
- **Charge attack** with telegraph line and yellow/orange thruster
  trail. Dash at 250 px/s, dodgeable.
- **All boss damage = 2 hearts** (contact + bullets).
- **4-frame AI animation set** (IDLE, TELEGRAPH, CHARGE, DYING) at
  8 FPS, 6 frames each.
- **Hit-streak ring drop**: 50% chance on 20 hits within 7 s.
  Resets on timeout or on the player taking boss damage.

### Power-up rings (Starfox-64 style)
- Silver rings: +1 life, 10% enemy drop.
- Gold rings: +2 life, 5% drop, count toward the gold stack.
- **Stack system**: 3 golds = +3 max lives (3 → 6 → 9 max).
- Magneto pickup at 30 px (auto-collect, no button).
- 15 s lifetime + 3 s fade-out.
- Code-rendered at 10 px (no AI assets).

### HUD
- 9 heart slots (filled + outline) + 2 gold ring slots.
- 10-icon weapon selector strip.
- Boss HP bar with quarter ticks.
- PTS / wave / enemy counter.

### Audio
- MIDI music with 4 placeholder tracks.
- 30+ SFX from `src/audio/synth.py`.
- Per-ship thruster loops with dynamic compression.

## Stats

| Metric | Count |
|---|---|
| Tests | 239 (100% pass) |
| Smoke gates | 11/11 |
| Game source files | 39 |
| Test files | 22 |
| Python LOC | 6,165 (3,938 game code) |
| Sprite sheets | 32 (12 FPS) + 4 boss anims (8 FPS) |
| Weapon sprites | 10 single-frame |
| MIDI tracks | 4 |
| SFX | 30+ |

## How to run

```bash
$env:PYTHONPATH = 'D:\AI\void-hunter'
python -m stellar_horizon.smoke      # 5s, 11 gates
python -m stellar_horizon.main       # play
python -m pytest stellar_horizon/tests/  # 239 tests
```

Launchers: `stellar_horizon/run.bat` and `run.ps1`.

## Controls

- WASD / Arrows — move
- Space — fire
- 1-9, 0 — switch weapon

## Known limitations

- Boss animations are static (no procedural pulse on top).
- Single boss entry path; phase-2 re-entry not implemented yet.
- 2 of 24 test files require the optional `mido` dependency.

## Full report

See `docs/REPORT_v1.0.0.md` for architecture, file layout, per-test
breakdowns, and roadmap.
