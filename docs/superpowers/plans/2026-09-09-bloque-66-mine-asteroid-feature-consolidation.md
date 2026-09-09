# BLOQUE 66 — MINE-ASTEROID Feature Consolidation (25% spawn + 4-frame cycle + variant-aware camo)

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. Checkbox syntax for tracking.

**Goal:** Consolidate the asteroid-camouflage-ship feature into one coherent, fully-tested, fully-documented block. Three pillars: (1) 25% of obstacles are MINE-ASTEROID (ship), 75% are indestructible asteroids; (2) 4-frame opening animation (closed → open1 → open2 → open3); (3) variant-aware camouflage (MINE-closed state mirrors the same 5 asteroid variants the regulars use, so the disguise is real).

**Reference history:**
- BLOQUE 61 — 5 asteroid variants (round/elongated/spiked/hollowed/cracked) at 32×32
- BLOQUE 62 — top-down ship perspective (no 3/4 angle)
- BLOQUE 63 — `EnemyKind.MINE_ASTEROID` introduced; 5-state cycle (closed/opening/open/closing/death)
- BLOQUE 64.A — asteroids 32×32 → 64×64, indestructible, MINE HP=3
- BLOQUE 64.5 — spawn rate 1/8 → 1/4 (25%), open duration 0.3s → 1.0s
- BLOQUE 65 — 4-frame redesign (closed/open1/open2/open3) at 0.2s/0.2s/∞
- **BLOQUE 66 (this)** — fix the `mine_variant` gap: closed state now loads the correct variant sprite (was hardcoded to round)

**Tech stack:** Python 3.11, pygame 2.6, mcode-tools, pytest

---

## Current State (audit 2026-09-09 01:25 GMT-5)

| Pillar | Status | Where |
|---|---|---|
| 25% spawn rule | ✅ Implemented | `src/entities/enemies/enemy.py:74` — `MINE_SPAWN_FRACTION: float = 1.0 / 4.0` |
| 4 frames on disk | ✅ Implemented | `Assets/sprites/enemies/mine_asteroid/{closed,open1,open2,open,death}/frame_00..09.png` |
| State machine | ✅ Implemented | `src/entities/enemies/enemy.py:861 _update_mine_asteroid` — 4 states, 0.2s + 0.2s + ∞ |
| Vulnerability rules | ✅ Implemented | `src/entities/enemies/enemy.py:519` — closed = immune, open1/2/3 = vulnerable |
| Damage flash | ✅ Implemented | `src/entities/enemies/enemy.py:528` — 0.2s red flash per hit |
| Indestructible asteroids | ✅ Implemented | `src/entities/asteroid.py:113 hit()` — no-op, always returns False |
| 5 variants for regular asteroids | ✅ Implemented | `src/entities/asteroid.py:262 spawn_asteroid` — `variant = rng.randint(0, 4)` |
| **5 variants for MINE-closed state** | ❌ **GAP** | `src/entities/enemies/enemy.py:415 animation_path` — always loads `closed/frame_00.png` (= round) |
| Firing on open2→open3 | ✅ Implemented | `src/entities/enemies/enemy.py:917` — sets `on_fire = True`; `_fire_mine_bullets` called by integration site |
| Tests | ✅ 33/33 pass | `tests/test_mine_asteroid.py` |
| .exe built and running | ✅ | `dist/void-hunter.exe` PID 35664, 808 MB RAM, window 674×1011 visible |

**The gap (the only real work in BLOQUE 66):**

The `mine_variant` field is set at spawn time (`gameplay_runtime.py:1720` — `e.mine_variant = self._asteroid_rng.randint(0, 4)`) but never consulted by the render path. The closed state always shows the round variant, breaking the camouflage. A player who learns the 5 variants can spot a MINE_ASTEROID by waiting for a "round" variant among rotated regulars.

**Fix:** Make the closed-state sprite path use `mine_variant` to pick one of 5 variant sprites (round/elongated/spiked/hollowed/cracked). The intermediate states (open1/open2/open3) keep their hand-designed composites.

---

## File Structure

**Modify:**
- `src/entities/enemies/enemy.py` — `animation_path` uses `mine_variant` for closed state
- `tests/test_mine_asteroid.py` — add 3 tests for variant-aware closed state
- `docs/changelog/CHANGELOG_v1.x.md` — add BLOQUE 66 section
- `tools/playtest_out/` — capture variant comparison PNG (closed states 0-4 side by side)

**No new files.** No new sprite assets (we reuse the 5 existing asteroid variant PNGs from BLOQUE 64.A).

---

## Task 1: Implement variant-aware closed state (4 subtasks)

### Task 1.1: Update `animation_path` to use `mine_variant`

**File:** `src/entities/enemies/enemy.py:400-415`

**Change:** When `state == "closed"`, load `closed/frame_<mine_variant>.png` instead of `closed/frame_00.png`. Cap variant to `[0, 4]`. Fallback to frame_00.png for out-of-range.

**Before:**
```python
if state == "open3":
    return "enemies/mine_asteroid/open/frame_00.png"
return f"enemies/mine_asteroid/{state}/frame_00.png"
```

**After:**
```python
if state == "open3":
    return "enemies/mine_asteroid/open/frame_00.png"
if state == "closed":
    v = max(0, min(4, int(self.mine_variant)))
    return f"enemies/mine_asteroid/closed/frame_{v:02d}.png"
return f"enemies/mine_asteroid/{state}/frame_00.png"
```

### Task 1.2: Generate 5 closed-state variant PNGs

**Files:** `Assets/sprites/enemies/mine_asteroid/closed/frame_00..04.png`

**Source:** Copy from `Assets/sprites/asteroids/{round,elongated,spiked,hollowed,cracked}.png`.

| Closed frame | Source asteroid |
|---|---|
| frame_00.png | round.png |
| frame_01.png | elongated.png |
| frame_02.png | spiked.png |
| frame_03.png | hollowed.png |
| frame_04.png | cracked.png |

This is a byte-level copy (no transformation). The camo is real because the player can no longer distinguish a MINE_ASTEROID from a regular asteroid by variant.

### Task 1.3: Add 3 tests for variant-aware closed state

**File:** `tests/test_mine_asteroid.py`

```python
def test_closed_loads_variant_0_path(self):
    """BLOQUE 66: mine_variant=0 loads closed/frame_00.png (round)."""
    e = _make_mine(variant=0)
    e.mine_state = "closed"
    self.assertEqual(e.animation_path(), "enemies/mine_asteroid/closed/frame_00.png")

def test_closed_loads_variant_4_path(self):
    """BLOQUE 66: mine_variant=4 loads closed/frame_04.png (cracked)."""
    e = _make_mine(variant=4)
    e.mine_state = "closed"
    self.assertEqual(e.animation_path(), "enemies/mine_asteroid/closed/frame_04.png")

def test_closed_clamps_out_of_range_variant(self):
    """BLOQUE 66: variant > 4 clamps to 4 (cracked)."""
    e = _make_mine(variant=99)
    e.mine_state = "closed"
    self.assertEqual(e.animation_path(), "enemies/mine_asteroid/closed/frame_04.png")

def test_open1_open2_open3_ignore_variant(self):
    """BLOQUE 66: only closed uses mine_variant. Other states use frame_00."""
    for v in (0, 2, 4):
        e = _make_mine(variant=v)
        for st in ("open1", "open2"):
            e.mine_state = st
            self.assertEqual(e.animation_path(), f"enemies/mine_asteroid/{st}/frame_00.png")
        e.mine_state = "open3"
        self.assertEqual(e.animation_path(), "enemies/mine_asteroid/open/frame_00.png")
```

### Task 1.4: Capture variant comparison PNG

**File:** `tools/playtest_out/bloque_66_mine_asteroid_variants.png`

Use the existing capture script pattern (or write a tiny one-liner via PIL) to render the 5 closed-state sprites side by side with labels: `0:round`, `1:elongated`, `2:spiked`, `3:hollowed`, `4:cracked`.

---

## Task 2: Update CHANGELOG

**File:** `docs/changelog/CHANGELOG_v1.x.md`

Add section "## BLOQUE 66 — MINE-ASTEROID Feature Consolidation" with:
- 25% spawn rule preserved (BLOQUE 64.5)
- 4-frame cycle preserved (BLOQUE 65)
- Indestructible asteroids preserved (BLOQUE 64.A)
- **NEW:** variant-aware closed state (mine_variant now used in render path)
- 4 new tests
- Total MINE-ASTEROID tests: 33 + 4 = 37

---

## Task 3: Verification

- [ ] Step 3.1: `pytest tests/test_mine_asteroid.py -q` → 37/37 pass
- [ ] Step 3.2: `pytest tests/ -q` → no regressions (allow 6 pre-existing failures)
- [ ] Step 3.3: Rebuild `.exe` via `pyinstaller build.spec --noconfirm`
- [ ] Step 3.4: Launch + verify window appears
- [ ] Step 3.5: Commit + push to `origin/master`

---

## Acceptance Criteria

1. ✅ MINE_ASTEROID closed state loads one of 5 variant sprites (not always round)
2. ✅ Out-of-range variant clamps to 4 (cracked)
3. ✅ open1/open2/open3 still load frame_00.png (they're hand-designed composites)
4. ✅ All 33 existing MINE-ASTEROID tests still pass
5. ✅ 4 new tests pass
6. ✅ No regressions in the wider test suite
7. ✅ .exe rebuilt and launched
8. ✅ Capture `bloque_66_mine_asteroid_variants.png` shows 5 closed variants side by side

## Out of Scope

- GOLIATH animation fix (deferred per user "olvida lo de goliath")
- Re-touch of open1/open2 composites (worker composites vs pure AI gen — pending user choice)
- Powerup drop from regular asteroids (asteroids are indestructible; powerups come from MINE kills only)
- Bumping the title-screen "BLOQUE 60" text to "BLOQUE 66" (cosmetic; not requested)
