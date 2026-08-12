# data/sfx/ — Star Fox-inspired cinematic SFX (pending integration)

This folder contains procedurally-rendered SFX WAVs (pure stdlib,
no numpy/scipy) using the Star Fox DNA: sub-bass weight, punchy
transients, reverb for size, soft saturation for warmth, multiple
layers for density. These **replace** the existing 8-bit procedural
SFX in `src/audio/synth.py` and **add** 5 new ones for state
transitions that were missing entirely.

## Status: PENDING REVIEW (iter 2)

Iter 1 was 16-bit Mega Drive style. User said it was "horrible".
Iter 2 re-oriented to cinematic Star Fox / rail-shooter.

Listen to each one and tell me:
- **"listo"** → I (or another agent) integrate them
- **"[name] más [direction]"** → I re-render that one
- **"otra dirección"** → I throw out the approach and start over

## File naming convention

Each WAV filename = the SFX catalog slot it represents, e.g.:

| WAV | SFX catalog slot | Status |
| --- | --- | --- |
| `warning_boss.wav`     | `warning_boss`     | NEW — replaces `boss_warning` call in BossIntroScene |
| `warning_miniboss.wav` | `warning_miniboss` | NEW — replaces `boss_warning` call in SubBossIntroScene |
| `propulsion.wav`       | `propulsion`       | NEW — engine hum during PROPULSION state (shift held) |
| `enemy_shoot.wav`      | `enemy_shoot`      | NEW — every enemy attack pattern (8 catalog attacks) |
| `engine_hum.wav`       | `engine_hum`       | NEW — engine hum during MOVE/IDLE (GDD §9, was missing) |

The five filenames match exactly the keys that need to be added to
`SFX_CATALOG` in `src/audio/synth.py`. See `MANIFEST.md` for the
explicit mapping + call sites in the gameplay code.

## Companion files

- `MANIFEST.md` — explicit mapping WAV → catalog slot → call site
- `INTEGRATION.md` — step-by-step for the agent that wires these into the engine
- `REPORT.md` — technical report (current iter: Star Fox DNA; spectral centroid, peak, etc.)
- `_RENDER_REPORT_OLD.md` — deprecated, iter 1 only kept for diff

## Source code

The recipes that generated these WAVs are in:
- `src/audio/synth_16bit.py` — expanded procedural engine (wavetable,
  FM, multi-voice, filters, bit-crush, reverb comb, soft saturation,
  ADSR, WAV writer)
- `src/audio/sfx_16bit_recipes.py` — the 5 SFX recipes

Re-render with: `python tools/render_sfx_previews.py`
Re-analyze with: `python tools/spectral_analyze.py`
