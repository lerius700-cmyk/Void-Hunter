# tools/_legacy/

**Archived BLOQUE 47-53 capture / debug scripts.** Moved here on
BLOQUE 58.34 cleanup. They are not deleted — git history is intact,
the files are just out of the way so `tools/` is readable.

## Why

`tools/sprite_forge.py` (BLOQUE 58.33) is the unified replacement
for all 20+ `capture_*.py` and `bloque*_capture.py` scripts. The
test/diagnostic scripts (`playtest.py`, `test_level1*.py`, etc.)
were one-off debug helpers from earlier BLOQUEs.

## What's here

- `capture_*.py` (20 files) — superseded by `sprite_forge.py`
- `bloque*_capture.py` (8 files) — historical per-BLOQUE polish captures
- `playtest*.py`, `test_level1*.py`, `test_respawn.py` — manual smoke
- `diag_5s.py`, `inspect_states.py`, `aimed_log.py`, `quick_log.py` —
  ad-hoc debug helpers
- `smoke_*.py`, `static_bot_test.py`, `smart_bot.py` — bot tests
- `level1_*.py`, `visualize_scenes.py`, `upscale_pngs.py`,
  `dash_test.py`, `boss_kill_test.py` — one-off diagnostic tools

## When to bring something back

If you find yourself rewriting one of these for a real need, copy
it back to `tools/` and update. Otherwise, leave them archived.

Don't commit changes to files in this folder — they are intentionally
frozen historical artifacts. If you must edit, document the BLOQUE.
