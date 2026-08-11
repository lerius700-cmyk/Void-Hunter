# tools/playtest_out/_archive/

**Historical playtest PNGs from BLOQUE 47-58.** Moved here on
BLOQUE 58.34 cleanup. The active visual reference is now:

- `tools/playtest_out/forge/atlas_all.png` — combined atlas of all
  74 procedural sprites (current state, BLOQUE 58.33)
- `tools/playtest_out/forge/atlas_<category>.png` — per-category
  atlases (8 categories)
- `tools/playtest_out/forge/<category>/<sprite>.png` — individual
  sprites

## Why archived

- The `_archive/` folder had 229 PNGs spanning multiple BLOQUEs of
  visual iteration (`polish_01_idle.png` through `polish_58_*.png`,
  `boss_t0000..t0150.png`, `gameplay_t0000..t0570.png`, etc.)
- These are useful as a HISTORY of the visual evolution but they
  crowded the working directory and made it hard to find the
  current reference
- `sprite_forge.py` regenerates the current sprites in 2 seconds

## What's here

- `playtest_out_4x/` — 4x upscaled historical PNGs
- `visualize_out/` — scene visualizer outputs (all scenes, all sizes)
- `visualize_out_4x/` — 4x version
- `10min/`, `frames/`, `real_run/`, `state_frames/` — long-run captures
- `_debug_archive/` — Tron trail development PNGs (chain, body, core, etc.)

## Re-generating current sprites

```bash
python tools/sprite_forge.py                  # all categories
python tools/sprite_forge.py player enemies    # subset
python tools/sprite_forge.py --list           # see categories
```
