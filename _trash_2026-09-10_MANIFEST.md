# Trash 2026-09-10 — Void Hunter

**Date:** 2026-09-10 (BLOQUE 71+71.1+71.2 release prep)
**Action:** Moved (NOT deleted) 41 transient/ad-hoc files to `_trash_2026-09-10/`.
**Reason:** Working tree had 264 dirty files accumulated from BLOQUE 64-69 (GOLIATH redesign, ship redesign, BOSS tester, ribbon weapon, tiles, diagnostic 1-offs, status files). The substantive work (BLOQUE 71+71.1+71.2 asteroid/powerup hit feedback) is already committed. These are leftovers from WIP experiments and one-off debug scripts.

## What was kept (NOT moved)

| Category | Path | Notes |
|----------|------|-------|
| GOLIATH redesign pipeline | `tools/redesign_bosses/` | 14 files (01b/02b/02c/01d/02d/03d pipeline + specs + helpers) |
| Ship redesign pipeline | `tools/redesign_ships/` | 3 entries (11 .py + 16 prototype PNGs in _proto_v1/_proto_v2) |
| BOSS tester tool | `tools/boss_tester/` | 10 files (live_demo, tour, scene, main, tests) |
| Ribbon weapon tool | `tools/ribbon_weapon/` | 10 files (color_grade, generate, postprocess, procedural_ribbon) |
| Tiles generator | `tools/tiles/` | 4 files (generate_tiles.py, ai_gen, output) |
| BLOQUE 64 captures | `tools/playtest_out/` | 6 PNGs (gitignored but tracked for visual evidence) |
| Pre-existing release script | `tools/create_v1_3_0_release.py` | Template for v1.4.0 clone |
| Pre-existing test | `tests/test_bloque_64_goliath.py` | Modified, pre-existing failure (out of BLOQUE 71 scope) |
| WIP ribbon test | `tests/test_procedural_ribbon.py` | For ribbon_weapon (uncommitted) |
| BLOQUE 61-63 plans | `docs/superpowers/plans/2026-09-08-*` | 4 plans (asteroid overhaul, top-down ship, mine-asteroid, act1 tiles integration) |
| Act1 tiles specs | `docs/superpowers/specs/2026-09-08-act1-tiles-*` | 2 specs (design + prompt weapon) |
| Prompts directory | `docs/superpowers/prompts/` | New (uncommitted) |
| GOLIATH prototype variants | `Assets/sprites/bosses/goliath_proto*/`, `goliath/_base/`, `redesign/`, `_backup_*/` | WIP, future redesign base renders |
| Player sprite sheets | `Assets/sprites/player_ships/` | Used by build_sprite_sheet tool |

## What was moved (41 files)

### `root_files/` (14 files — status reports + junk from repo root)

| File | Size | Notes |
|------|------|-------|
| `final_status.txt` | - | Ad-hoc status output |
| `status.txt` | - | Ad-hoc status output |
| `status_after.txt` | - | Ad-hoc status output |
| `status_enemies.txt` | - | Enemy state dump |
| `status_enemies2.txt` | - | Enemy state dump (2) |
| `status_player.txt` | - | Player state dump |
| `status_redesign.txt` | - | Redesign status output |
| `to_delete.txt` | - | A literal "to delete" list (meta) |
| `show.txt` | - | Ad-hoc output capture |
| `staged.txt` | - | Ad-hoc staged diff output |
| `run_bosstester.bat` | - | Windows batch launcher for boss_tester |
| `_pytest_full.txt` | - | Full pytest log |
| `_pytest_tmp.txt` | - | Temp pytest log |
| `_trash_test_yellow_line_b69.py` | - | BLOQUE 69 leftover test (name says it all) |

### `tools_diagnostics/` (23 files — one-off diagnostic scripts)

| File | Notes |
|------|-------|
| `_audit_goliath_quality.py` | GOLIATH quality audit |
| `_audit_row_widths.py` | Sprite row width audit |
| `_check_64d_pilot.py` | 64D pilot check |
| `_check_boss_state.py` | Boss state inspection |
| `_compose_sources_preview.py` | Source preview composer |
| `_debug_hashes_archive.py` | Hash debug |
| `_delete_phase1_bases.py` | Phase1 base cleanup |
| `_fix_changelog_used.py` | CHANGELOG fixup |
| `_make_64d_partial_strip.py` | 64D partial strip |
| `_make_64d_strips.py` | 64D strips |
| `_make_clean_preview.py` | Clean preview generator |
| `_smoke_check.py` | Smoke check |
| `_stage_64d_cleanup.py` | 64D cleanup staging |
| `diag_goliath_alpha.py` | GOLIATH alpha channel diagnostic |
| `diag_goliath_bbox.py` | GOLIATH bbox diagnostic |
| `diag_goliath_visual.py` | GOLIATH visual diagnostic |
| `diag_user_view.py` | User view diagnostic |
| `check_3_workers.py` | 3 workers check |
| `check_imports.py` | Import check |
| `check_rng.py` | RNG check |
| `check_sheets.py` | Sprite sheet check |
| `verify_2575.py` | 2575 verify (specific frame) |
| `verify_gameplay_spawn.py` | Gameplay spawn verify |

### `tools_capture/` (4 files — BLOQUE 64C visual capture scripts)

| File | Notes |
|------|-------|
| `_gif_inspect.py` | GIF inspection helper |
| `capture_bloque_64c_anim_gifs.py` | BLOQUE 64C animation GIFs |
| `capture_bloque_64c_motion_strips.py` | BLOQUE 64C motion strips |
| `capture_bloque_64c_v2_cycle.py` | BLOQUE 64C v2 cycle capture |

## How to recover

If any of these are needed back, just `Move-Item` from `_trash_2026-09-10/` back to the original path:

```powershell
# Example: restore _audit_goliath_quality.py
Move-Item _trash_2026-09-10/tools_diagnostics/_audit_goliath_quality.py tools/_audit_goliath_quality.py
```

## When to delete

Safe to `rm -rf _trash_2026-09-10/` after the v1.4.0 release is published and confirmed working
(roughly 2-3 days post-release, assuming no critical bugs surface that need a rollback to a diagnostic).
