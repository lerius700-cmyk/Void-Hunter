# Roguelike Density + Leader HP Scaling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make waves spawn twice as often (item #2) and make leader ships take 3-5 player hits based on wave proximity to boss (item #3), per the approved spec. Item #1 (roguelike pattern variety) requires no code change.

**Architecture:** Two small code changes (1 line in `src/core/game.py:276` for the interval, ~20 lines in `src/systems/wave_patterns/runtime.py` for the leader HP function + parameter) plus 1 call-site wiring line in `src/ui/gameplay_runtime.py`. The leader HP is computed by a new pure function `_leader_hits_at_wave(wave_idx)` that returns 3-5 (clamped), and the leader's HP is set to `SCOUT_HP * hits` (90/120/150). Backward-compatible: existing callers that don't pass `current_wave_idx` get the default value 0 (wave 1 = 3 hits = 90 HP).

**Tech Stack:** Python 3.11, pygame 2.6, pytest 9.1.1, stdlib only. No new dependencies.

**Spec:** [`docs/superpowers/specs/2026-09-06-roguelike-density-leader-hp-design.md`](../specs/2026-09-06-roguelike-density-leader-hp-design.md)

---

## Global Constraints

- **Profile:** Lite (per `CLAUDE.md`); no numpy/scipy in runtime
- **Coordinate convention:** +x right, +y down; 320×480 internal playfield (not used in this plan)
- **Default mode = `--roguelike`** (BLOQUE 58); `--patterns 1` is for tests
- **Commits with BLOQUE prefix:** `feat: BLOQUE N` / `fix: BLOQUE N` / `chore: BLOQUE N` (per `CLAUDE.md`)
- **No auto zip build / no version label** unless user asks (per user memory 2026-08-14)
- **Test convention:** tests in `tests/test_*.py`, `pytest -q` from project root
- **Test environment:** `$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'` for headless tests
- **Backward compat for `spawn_pattern_wave`:** the new `current_wave_idx` param defaults to 0; existing tests that don't pass it keep working
- **Bosses (GOLIATH/HYDRA/PHANTOM/NEMESIS) are EXCLUDED** — they are separate entities, not spawned by `spawn_pattern_wave`
- **Sub-boss (Wolfen dart, BLOQUE 50) is EXCLUDED** — also separate
- **No new test regressions:** the 6 pre-existing failures (1× `test_paths_no_star_shapes` + 5× `sub_boss_*`) must remain the only failures
- **Doc language:** technical docs in English; user-facing strings in Spanish (per `CLAUDE.md`)

---

## File Structure

### Modified files
- `src/core/game.py` — line 276, `spawn_interval=4.0` → `2.0`
- `src/systems/wave_patterns/runtime.py` — add `_leader_hits_at_wave` function; modify `spawn_pattern_wave` signature + body
- `src/ui/gameplay_runtime.py` — pass `current_wave_idx` at the call site of `spawn_pattern_wave`
- `tests/test_wave_patterns.py` — add `TestLeaderHPScaling` class (7 tests)
- `tests/test_wave_patterns.py` — add 5 integration tests for `spawn_pattern_wave(current_wave_idx=...)`
- `tests/test_wave_patterns.py` — add 1 test for `spawn_interval=2.0` knob
- `docs/changelog/CHANGELOG_v1.x.md` — add a new entry for this BLOQUE

### New files (gitignored, in `tools/playtest_out/`)
- `tools/playtest_out/_capture_leader_hp_scaling.py` — renders leader with mini HP bar at wave 1 vs wave 10
- `tools/playtest_out/_capture_wave_frequency.py` — renders playfield at 0/2/4/6/8/10s with interval=4.0 vs 2.0

### New artifacts (gitignored, in `tools/playtest_out/`)
- `leader_hp_wave1_vs_wave10.png` — side-by-side panels showing leader HP difference
- `wave_freq_4s.png` + `wave_freq_2s.png` — strip of playfield at 6 timestamps

---

## Task 1: Verify spec open questions (research only, no code change)

**Files:**
- Read: `src/ui/gameplay_runtime.py` (search for `MAX_ENEMIES_ON_SCREEN`, `waves_per_floor`, `wave_idx`)
- Read: `src/systems/wave_patterns/runtime.py` (find call site of `spawn_pattern_wave`)
- Read: `src/core/game.py:270-290` (where `spawn_interval=4.0` is used)
- Write: report in your final task response (no file write)

**Why first:** Spec §8 flags Q1 (`MAX_ENEMIES_ON_SCREEN` value) and Q5 (GLOBAL vs PER-FLOOR `wave_idx`) as open questions. The answer to Q5 determines how Task 5 wires the call site. Q1 is a known risk for item #2 pacing.

- [ ] **Step 1: Find `MAX_ENEMIES_ON_SCREEN` value**

Run: `Select-String -Path src/ui/gameplay_runtime.py -Pattern "MAX_ENEMIES_ON_SCREEN" -SimpleMatch | Select-Object LineNumber, Line`

Report: the line + value (likely a number like 24, 32, 64).

- [ ] **Step 2: Find per-floor wave counter logic**

Run: `Select-String -Path src/ui/gameplay_runtime.py -Pattern "waves_per_floor|WAVES_PER_FLOOR|_waves_per_floor" -SimpleMatch | Select-Object LineNumber, Line`

Report: whether there's an existing constant, or how waves are counted per floor.

- [ ] **Step 3: Find `spawn_pattern_wave` call site(s)**

Run: `Select-String -Path src/ -Pattern "spawn_pattern_wave" -SimpleMatch -Recurse | Select-Object Path, LineNumber`

Report: all files that call `spawn_pattern_wave`. Task 5 will modify these.

- [ ] **Step 4: Report findings**

Output a short summary:
- `MAX_ENEMIES_ON_SCREEN = <N>` (Q1 answer — flag if <20 because item #2 may be throttled)
- `waves_per_floor` = <N or "per-floor counter not found, defaulting to GLOBAL">
- Call sites: `<file:line>` for each

**No code change in this task. No commit.**

---

## Task 2: Halve wave spawn interval (item #2)

**Files:**
- Modify: `src/core/game.py:276`
- Test: `tests/test_wave_patterns.py` (add 1 new test method)

**Interfaces:**
- Consumes: nothing
- Produces: `spawn_interval=2.0` in the `ProceduralWaveManager` constructor call

- [ ] **Step 1: Write the failing test**

Append this method to the `TestProceduralWaveManager` class in `tests/test_wave_patterns.py` (find the class definition around line 816):

```python
    def test_game_uses_spawn_interval_2s(self) -> None:
        """BLOQUE 58.next: spawn_interval changed from 4.0 to 2.0.
        Item #2 of the roguelike density spec."""
        import re
        from pathlib import Path
        game_path = Path("src/core/game.py")
        text = game_path.read_text(encoding="utf-8")
        # Find the spawn_interval= in the wave manager construction
        m = re.search(r"spawn_interval\s*=\s*([\d.]+)", text)
        assert m is not None, "spawn_interval not found in src/core/game.py"
        assert float(m.group(1)) == 2.0, (
            f"Expected spawn_interval=2.0, got {m.group(1)}"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_wave_patterns.py::TestProceduralWaveManager::test_game_uses_spawn_interval_2s -v
```

Expected: FAIL with "Expected spawn_interval=2.0, got 4.0" (or similar)

- [ ] **Step 3: Modify `src/core/game.py:276`**

Change:
```python
seed=self._patterns_seed, floor=1, spawn_interval=4.0,
```
to:
```python
seed=self._patterns_seed, floor=1, spawn_interval=2.0,
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/game.py tests/test_wave_patterns.py
git commit -m "feat: BLOQUE 58.next halve wave spawn interval 4s to 2s

Item #2 of the 2026-09-06 roguelike density spec. Same per-pattern
ship counts, 2x waves per minute. The MAX_ENEMIES_ON_SCREEN cap
may throttle the effective rate if hit (verified in Task 1)."
```

---

## Task 3: `_leader_hits_at_wave` pure function (TDD, item #3 unit)

**Files:**
- Modify: `src/systems/wave_patterns/runtime.py` (add new function after the imports, before `pattern_kind_to_enemy_kind`)
- Test: `tests/test_wave_patterns.py` (add new class `TestLeaderHPScaling` with 7 methods)

**Interfaces:**
- Consumes: nothing
- Produces: `runtime._leader_hits_at_wave(wave_idx: int) -> int` — returns 3, 4, or 5 (clamped)

- [ ] **Step 1: Write the failing test class**

Append this class to `tests/test_wave_patterns.py` (at the end of the file, before any module-level code):

```python
class TestLeaderHPScaling:
    """BLOQUE 58.next item #3: leader HP scales with wave proximity to boss.

    Wave 1 (idx=0) = 3 hits, wave 10 (idx=9) = 5 hits, linear, clamped.
    See docs/superpowers/specs/2026-09-06-roguelike-density-leader-hp-design.md
    """

    def test_hits_at_wave_1_is_3(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        assert _leader_hits_at_wave(0) == 3

    def test_hits_at_wave_4_is_4(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        assert _leader_hits_at_wave(4) == 4

    def test_hits_at_wave_10_is_5(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        assert _leader_hits_at_wave(9) == 5

    def test_hits_beyond_wave_10_clamps_to_5(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        assert _leader_hits_at_wave(20) == 5
        assert _leader_hits_at_wave(100) == 5

    def test_hits_below_wave_1_clamps_to_3(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        assert _leader_hits_at_wave(-5) == 3

    def test_hits_scales_linearly_between_anchors(self) -> None:
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        # wave_idx 0..9 -> 3,3,3,4,4,4,4,5,5,5
        # raw = 3 + wave_idx * 2/9, rounded, clamped to [3, 5]
        expected = [3, 3, 3, 4, 4, 4, 4, 5, 5, 5]
        actual = [_leader_hits_at_wave(i) for i in range(10)]
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_hp_formula_is_hits_times_scout_hp(self) -> None:
        """Leader HP = SCOUT_HP (30) * hits."""
        from src.systems.wave_patterns.runtime import _KIND_HP
        from src.systems.wave_patterns.runtime import _leader_hits_at_wave
        scout_hp = _KIND_HP["SCOUT"]
        for wave_idx, expected_hits in [(0, 3), (4, 4), (9, 5), (20, 5)]:
            assert scout_hp * _leader_hits_at_wave(wave_idx) == scout_hp * expected_hits
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_wave_patterns.py::TestLeaderHPScaling -v
```

Expected: All 7 tests FAIL with "cannot import name '_leader_hits_at_wave'" (or similar)

- [ ] **Step 3: Implement the function**

In `src/systems/wave_patterns/runtime.py`, add this function AFTER the imports (around line 41, after the `KIND_HP` block) and BEFORE `def pattern_kind_to_enemy_kind` (line 75):

```python
def _leader_hits_at_wave(wave_idx: int) -> int:
    """BLOQUE 58.next: leader HP scaling with wave proximity to boss.

    Wave 1 (idx=0) = 3 hits, wave 10 (idx=9) = 5 hits, linear, clamped.
    The 'hits' value is multiplied by SCOUT_HP (30) to get the leader's
    actual HP value (90/120/150).

    The wave_idx is the GLOBAL wave counter, matching
    `self._wave_idx` in gameplay_runtime.py. See the spec's open
    question Q5 for the GLOBAL vs PER-FLOOR discussion.

    Args:
        wave_idx: 0-based global wave index.

    Returns:
        Integer in [3, 5] — number of player hits to kill a leader.
    """
    raw = 3 + (wave_idx * 2.0) / 9.0
    return max(3, min(5, round(raw)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same pytest command. Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/systems/wave_patterns/runtime.py tests/test_wave_patterns.py
git commit -m "feat: BLOQUE 58.next add _leader_hits_at_wave pure function

Item #3 of the 2026-09-06 spec. Linear interpolation 3 hits at
wave 1, 5 hits at wave 10, clamped to [3, 5]. Pure function for
testability. Used by spawn_pattern_wave in Task 4."
```

---

## Task 4: `spawn_pattern_wave` accepts `current_wave_idx` and applies leader HP (TDD integration)

**Files:**
- Modify: `src/systems/wave_patterns/runtime.py` (modify `spawn_pattern_wave` signature + body)
- Test: `tests/test_wave_patterns.py` (add 4 integration tests)

**Interfaces:**
- Consumes: `runtime._leader_hits_at_wave(wave_idx) -> int` (from Task 3)
- Produces: `runtime.spawn_pattern_wave(pool, result, duration_s=None, current_wave_idx=0) -> PatternRuntime` — the new `current_wave_idx` param defaults to 0 for backward compat; each leader enemy's `e.hp` is set to `_KIND_HP["SCOUT"] * _leader_hits_at_wave(current_wave_idx)`

- [ ] **Step 1: Write the failing integration tests**

Append this class to `tests/test_wave_patterns.py`:

```python
class TestSpawnLeaderHP:
    """BLOQUE 58.next item #3: spawn_pattern_wave applies scaled HP to leaders.

    Integration test: spawn a COMPOSED pattern with a leader, verify the
    leader enemy has the correct HP for the given current_wave_idx.
    Followers stay at SCOUT_HP (30). Default current_wave_idx=0 keeps
    backward compat with existing tests.
    """

    def _spawn_with_wave(self, wave_idx: int):
        """Helper: spawn a V_FORMATION at the given wave_idx, return (enemies, runtime)."""
        from src.entities.enemies.enemy import EnemyPool
        from src.systems.wave_patterns.runtime import spawn_pattern_wave
        from src.systems.wave_patterns.v_formation import VFormationPattern
        import random
        pool = EnemyPool(capacity=16)
        result = VFormationPattern().generate(random.Random(42), level=3)
        runtime = spawn_pattern_wave(pool, result, current_wave_idx=wave_idx)
        enemies = [e for e in pool.enemies if e.alive]
        return enemies, runtime

    def test_leader_has_90_hp_at_wave_1(self) -> None:
        enemies, _ = self._spawn_with_wave(0)
        leader = next(e for e in enemies if e.is_leader)
        assert leader.hp == 90, f"Expected 90, got {leader.hp}"

    def test_leader_has_150_hp_at_wave_10(self) -> None:
        enemies, _ = self._spawn_with_wave(9)
        leader = next(e for e in enemies if e.is_leader)
        assert leader.hp == 150, f"Expected 150, got {leader.hp}"

    def test_followers_unchanged_at_30_hp(self) -> None:
        enemies, _ = self._spawn_with_wave(9)
        followers = [e for e in enemies if not e.is_leader]
        assert len(followers) > 0
        for f in followers:
            assert f.hp == 30, f"Follower hp={f.hp}, expected 30"

    def test_default_wave_idx_0_is_backward_compat(self) -> None:
        """Call without current_wave_idx: leader gets 90 HP (default 0 = wave 1)."""
        from src.entities.enemies.enemy import EnemyPool
        from src.systems.wave_patterns.runtime import spawn_pattern_wave
        from src.systems.wave_patterns.v_formation import VFormationPattern
        import random
        pool = EnemyPool(capacity=16)
        result = VFormationPattern().generate(random.Random(42), level=3)
        # NOTE: no current_wave_idx arg
        spawn_pattern_wave(pool, result)
        enemies = [e for e in pool.enemies if e.alive]
        leader = next(e for e in enemies if e.is_leader)
        assert leader.hp == 90
```

> **Note:** the `Enemy.is_leader` field must exist. If it doesn't, the engineer should add it as a public attribute to the `Enemy` dataclass (default `False`) and set it to `True` in the leader detection path. Add this as a small in-task sub-step if needed.

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_wave_patterns.py::TestSpawnLeaderHP -v
```

Expected: FAIL. Most likely failure: "spawn_pattern_wave() got an unexpected keyword argument 'current_wave_idx'" or "Enemy has no attribute 'is_leader'".

- [ ] **Step 3: Add `current_wave_idx` parameter to `spawn_pattern_wave`**

In `src/systems/wave_patterns/runtime.py`, modify the `spawn_pattern_wave` function (around line 197) — change the signature and add the leader HP application:

```python
def spawn_pattern_wave(
    pool: EnemyPool,
    result: WavePatternResult,
    duration_s: Optional[float] = None,
    current_wave_idx: int = 0,  # BLOQUE 58.next: leader HP scaling
) -> PatternRuntime:
    """Spawn the enemies for a pattern. Returns the runtime tracker.

    Args:
        pool: the EnemyPool to spawn into
        result: from ProceduralWaveManager.pick_pattern()
        duration_s: override duration (uses result.duration_s if None)
        current_wave_idx: BLOQUE 58.next — global wave index (0-based).
            Used to scale leader HP: wave 1=3 hits (90 HP), wave 10=5
            hits (150 HP). Default 0 = wave 1 (backward compat).

    Returns:
        PatternRuntime with spawn tracking
    """
    if duration_s is None:
        duration_s = result.duration_s

    runtime = PatternRuntime(
        kind=result.kind,
        ships_spawned=[],
        result=result,
        elapsed=0.0,
        duration=duration_s,
    )

    for spawned in result.ships:
        kind = pattern_kind_to_enemy_kind(spawned)
        e = pool.spawn(kind, spawned.spawn_x, spawned.spawn_y)
        if e is None:
            continue  # pool exhausted
        runtime.ships_spawned.append(id(e))

        # BLOQUE 58.10: track the leader enemy so the draw layer can
        # highlight it with a glow ring.
        if spawned.is_leader:
            runtime.leader_enemy_ids.append(id(e))
            # BLOQUE 58.next: leader HP scales with wave proximity to boss.
            # Wave 1=3 hits (90 HP), wave 10=5 hits (150 HP). Followers
            # keep the default SCOUT_HP from the pool (30).
            hits = _leader_hits_at_wave(current_wave_idx)
            e.hp = _KIND_HP["SCOUT"] * hits

        # ... rest of the function unchanged (path attachment, color tint, etc.)
```

- [ ] **Step 4: Ensure `Enemy.is_leader` exists**

If the integration test failed because `Enemy` has no `is_leader` attribute, add it to `src/entities/enemies/enemy.py`:

In the `Enemy` dataclass (around line 60-90), add the field:
```python
@dataclass(frozen=True)
class Enemy:
    # ... existing fields ...
    is_leader: bool = False
```

- [ ] **Step 5: Run tests to verify they pass**

Run the same pytest command. Expected: All 4 tests PASS.

- [ ] **Step 6: Run full wave_patterns suite to verify no regressions**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_wave_patterns.py -q
```

Expected: All tests in `test_wave_patterns.py` pass (no new failures).

- [ ] **Step 7: Commit**

```bash
git add src/systems/wave_patterns/runtime.py src/entities/enemies/enemy.py tests/test_wave_patterns.py
git commit -m "feat: BLOQUE 58.next apply scaled HP to leaders in spawn_pattern_wave

Item #3 of the 2026-09-06 spec. New current_wave_idx parameter
(default 0 = backward compat). Leader enemies get HP = SCOUT_HP *
_leader_hits_at_wave(current_wave_idx). Followers unchanged at 30.

Adds Enemy.is_leader field for downstream consumers."
```

---

## Task 5: Wire call site — pass `current_wave_idx` from `gameplay_runtime.py`

**Files:**
- Modify: `<call site file>:<call site line>` (from Task 1 Step 3 finding)
- Test: existing integration tests (no new test, but re-run to verify)

**Interfaces:**
- Consumes: `gameplay_runtime._wave_idx` (the global wave counter, or per-floor counter per Task 1 Q5 answer)
- Produces: `spawn_pattern_wave(pool, result, current_wave_idx=self._wave_idx)` at the call site

- [ ] **Step 1: Read Task 1 report — confirm call site location and Q5 answer**

If Task 1 reported:
- **Q5 answer = (a) GLOBAL:** pass `current_wave_idx=self._wave_idx` directly.
- **Q5 answer = (b) PER-FLOOR:** pass `current_wave_idx=(self._wave_idx % <waves_per_floor>)` using the constant from Task 1 Step 2.

Default to (a) if Q5 was unresolved — the spec approves this default.

- [ ] **Step 2: Add the `current_wave_idx` argument at the call site**

In the file identified in Task 1 Step 3, find the call to `spawn_pattern_wave`. The existing call is something like:
```python
runtime = spawn_pattern_wave(self._pool, result, duration_s=...)
```

Change to:
```python
runtime = spawn_pattern_wave(
    self._pool, result,
    duration_s=...,
    current_wave_idx=self._wave_idx,  # BLOQUE 58.next: leader HP scaling
)
```

(Adjust the `self.` prefix if the class is named differently.)

- [ ] **Step 3: Run full test suite to verify no regressions**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 6 pre-existing failures (1× `test_paths_no_star_shapes` + 5× `sub_boss_*`). No new failures.

- [ ] **Step 4: Add CHANGELOG entry**

Open `docs/changelog/CHANGELOG_v1.x.md` (or the root `CHANGELOG.md` if there's no v1.x). Find the latest BLOQUE 58 entry. Add a new entry:

```markdown
### BLOQUE 58.next — Roguelike density + leader HP scaling (2026-09-06)

- **Item #1:** Confirmed the existing 4275-pattern COMPOSED pool + ProceduralWaveManager is the roguelike variety system. No code change.
- **Item #2:** Wave spawn interval halved: `spawn_interval=4.0` → `2.0` in `src/core/game.py:276`. Same per-pattern ship counts, 2x waves per minute.
- **Item #3:** Leader HP scales with wave proximity to boss. New pure function `_leader_hits_at_wave(wave_idx)` returns 3-5 (linear, clamped). New `current_wave_idx` parameter in `spawn_pattern_wave` defaults to 0 (backward compat). Leader HP = `SCOUT_HP * hits` = 90/120/150 at wave 1/5/10. Followers unchanged at 30 HP.
```

- [ ] **Step 5: Commit**

```bash
git add <call site file> docs/changelog/CHANGELOG_v1.x.md
git commit -m "feat: BLOQUE 58.next wire current_wave_idx to spawn_pattern_wave

Item #3 of the 2026-09-06 spec. <Q5 answer summary>. CHANGELOG entry."
```

---

## Task 6: Visual capture scripts (item #2 + #3 visual verification)

**Files:**
- Create: `tools/playtest_out/_capture_leader_hp_scaling.py`
- Create: `tools/playtest_out/_capture_wave_frequency.py`
- Test: visual artifacts only (no automated test)

**Interfaces:**
- Consumes: `runtime.spawn_pattern_wave` (from Task 4), `composed.ComposedPattern` for variety
- Produces: PNG files in `tools/playtest_out/` (gitignored)

- [ ] **Step 1: Write `_capture_leader_hp_scaling.py`**

Create `tools/playtest_out/_capture_leader_hp_scaling.py`:

```python
"""Capture visual proof of the leader HP scaling (BLOQUE 58.next item #3).

Renders a V_FORMATION at wave 1 (3 hits = 90 HP leader) and wave 10
(5 hits = 150 HP leader) side-by-side, with a mini HP bar overlay on
the leader so the difference is obvious to the eye.
"""
import os
import sys
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
import pygame

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.enemies.enemy import EnemyPool
from src.systems.wave_patterns.runtime import spawn_pattern_wave, _KIND_HP
from src.systems.wave_patterns.v_formation import VFormationPattern


def render_with_leader_hp_bar(wave_idx: int) -> pygame.Surface:
    """Render a V_FORMATION at the given wave_idx with a HP bar on the leader."""
    pool = EnemyPool(capacity=16)
    result = VFormationPattern().generate(random.Random(42), level=3)
    spawn_pattern_wave(pool, result, current_wave_idx=wave_idx)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((0, 0, 0))
    for e in pool.enemies:
        if not e.alive:
            continue
        # Ship dot (yellow if leader, white otherwise)
        color = (255, 220, 80) if e.is_leader else (180, 180, 200)
        pygame.draw.circle(surf, color, (int(e.x), int(e.y)), 6)
        # HP bar above leader
        if e.is_leader:
            max_hp = _KIND_HP["SCOUT"] * 5  # always show as 5-cell bar
            filled = int((e.hp / max_hp) * 30)
            bar_y = int(e.y) - 16
            pygame.draw.rect(surf, (60, 60, 60), (int(e.x) - 15, bar_y, 30, 4))
            pygame.draw.rect(surf, (80, 220, 120), (int(e.x) - 15, bar_y, filled, 4))
    return surf


def main() -> int:
    pygame.init()
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)
    surf_w1 = render_with_leader_hp_bar(0)
    surf_w10 = render_with_leader_hp_bar(9)
    panel_w, panel_h = INTERNAL_W, INTERNAL_H
    label_h = 30
    mosaic = pygame.Surface((panel_w * 2, panel_h + label_h))
    mosaic.fill((20, 20, 20))
    font = pygame.font.SysFont("Consolas", 16, bold=True)
    # Border + panel wave 1
    pygame.draw.rect(mosaic, (60, 60, 60), (0, label_h, panel_w, panel_h), 2)
    mosaic.blit(surf_w1, (0, label_h))
    mosaic.blit(font.render("WAVE 1 — 3 hits (90 HP)", True, (255, 255, 255)), (4, 6))
    # Border + panel wave 10
    pygame.draw.rect(mosaic, (60, 60, 60), (panel_w, label_h, panel_w, panel_h), 2)
    mosaic.blit(surf_w10, (panel_w, label_h))
    mosaic.blit(font.render("WAVE 10 — 5 hits (150 HP)", True, (255, 255, 255)), (panel_w + 4, 6))
    out_path = out_dir / "leader_hp_wave1_vs_wave10.png"
    pygame.image.save(mosaic, str(out_path))
    print(f"saved -> {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the capture script**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe tools/playtest_out/_capture_leader_hp_scaling.py
```

Expected output: `saved -> leader_hp_wave1_vs_wave10.png`. Verify the file exists with `Get-Item tools/playtest_out/leader_hp_wave1_vs_wave10.png`.

- [ ] **Step 3: Write `_capture_wave_frequency.py`**

Create `tools/playtest_out/_capture_wave_frequency.py`:

```python
"""Capture visual proof of the wave frequency change (BLOQUE 58.next item #2).

Spawns N waves at the given interval and renders the playfield at
6 timestamps. Same seed for both intervals — the difference is the
NUMBER of waves that have started by each timestamp.

Output: tools/playtest_out/wave_freq_<interval>s.png — 6 panels
showing the playfield at t=0, 2, 4, 6, 8, 10 seconds.
"""
import os
import sys
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
import pygame

from src.core.settings import INTERNAL_W, INTERNAL_H


def render_at_timestamps(spawn_interval: float, timestamps=(0, 2, 4, 6, 8, 10)) -> list[pygame.Surface]:
    """Simulate N=10 waves at the given interval, return playfield surfaces at each timestamp."""
    # Simplified simulation: each wave spawns a few ships at random positions
    # The exact positions don't matter — we just want to count how many ships
    # are on screen at each timestamp.
    from src.entities.enemies.enemy import EnemyPool
    from src.systems.wave_patterns.v_formation import VFormationPattern
    from src.systems.wave_patterns.runtime import spawn_pattern_wave

    pool = EnemyPool(capacity=128)
    surfaces = []
    rng = random.Random(42)
    # Stash all spawned enemies + their spawn times
    spawned: list[tuple[float, object]] = []  # (spawn_time, enemy)
    # Spawn 10 waves at the given interval
    for wave_idx in range(10):
        t_spawn = wave_idx * spawn_interval
        result = VFormationPattern().generate(rng, level=3)
        # Capture the just-spawned enemies by snapshotting pool size
        size_before = len([e for e in pool.enemies if e.alive])
        spawn_pattern_wave(pool, result, current_wave_idx=0)
        size_after = len([e for e in pool.enemies if e.alive])
        # The newly spawned enemies are the last (size_after - size_before)
        # Mark them with their spawn time
        # (For simplicity, we just snapshot the count and reuse positions at capture time)
        spawned.append((t_spawn, list(pool.enemies)))
    # Render at each timestamp
    for t in timestamps:
        surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
        surf.fill((0, 0, 0))
        n_visible = 0
        for t_spawn, enemies in spawned:
            # Wave lasts 6 seconds. Visible if t - t_spawn < 6.
            if 0 <= t - t_spawn < 6.0:
                for e in enemies:
                    if not e.alive:
                        continue
                    n_visible += 1
                    # Apply a simple downward motion: y += 60 px/s
                    y = e.y + 60 * (t - t_spawn)
                    if 0 <= y < INTERNAL_H:
                        pygame.draw.circle(
                            surf, (180, 180, 200), (int(e.x), int(y)), 4
                        )
        # Count text in the corner
        font = pygame.font.SysFont("Consolas", 14, bold=True)
        count_surf = font.render(f"t={t:2d}s  ships={n_visible}", True, (255, 255, 100))
        surf.blit(count_surf, (4, 4))
        surfaces.append(surf)
    return surfaces


def main() -> int:
    pygame.init()
    out_dir = PROJECT_ROOT / "tools" / "playtest_out"
    out_dir.mkdir(exist_ok=True)
    for interval in (4.0, 2.0):
        panels = render_at_timestamps(interval)
        panel_w, panel_h = INTERNAL_W, INTERNAL_H
        label_h = 20
        # 3 cols x 2 rows
        cols, rows = 3, 2
        mosaic = pygame.Surface((panel_w * cols, (panel_h + label_h) * rows))
        mosaic.fill((20, 20, 20))
        font = pygame.font.SysFont("Consolas", 14, bold=True)
        for i, surf in enumerate(panels):
            col = i % cols
            row = i // cols
            x = col * panel_w
            y = row * (panel_h + label_h) + label_h
            pygame.draw.rect(mosaic, (60, 60, 60), (x, y, panel_w, panel_h), 2)
            mosaic.blit(surf, (x, y))
        title = font.render(
            f"spawn_interval={interval}s — 6 timestamps, same seed", True, (255, 255, 255)
        )
        mosaic.blit(title, (4, 2))
        out_path = out_dir / f"wave_freq_{interval:.1f}s.png"
        pygame.image.save(mosaic, str(out_path))
        print(f"saved -> {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the wave frequency capture**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe tools/playtest_out/_capture_wave_frequency.py
```

Expected output: 2 lines, `saved -> wave_freq_4.0s.png` and `saved -> wave_freq_2.0s.png`. Verify both files exist.

- [ ] **Step 5: Commit (capture scripts only, NOT the PNG outputs)**

```bash
git add tools/playtest_out/_capture_leader_hp_scaling.py tools/playtest_out/_capture_wave_frequency.py
git commit -m "chore: BLOQUE 58.next add visual capture scripts for items 2 and 3

Generates tools/playtest_out/leader_hp_wave1_vs_wave10.png and
wave_freq_{4.0,2.0}s.png for user visual verification."
```

---

## Task 7: Final regression run + user visual verification

**Files:** none modified, but the user reviews the visual artifacts

- [ ] **Step 1: Run full test suite**

Run:
```powershell
$env:SDL_VIDEODRIVER='dummy'; $env:SDL_AUDIODRIVER='dummy'
& D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 6 pre-existing failures (1× `test_paths_no_star_shapes` + 5× `sub_boss_*`). **No new failures.**

If new failures appear, investigate. The most likely cause: `Enemy.is_leader` was added in Task 4 but some other code path (e.g., `pool.spawn`) needs to also set it. Or the `current_wave_idx` plumbing in Task 5 broke an existing call site.

- [ ] **Step 2: User visual verification**

Open these PNGs for the user:
- `tools/playtest_out/leader_hp_wave1_vs_wave10.png` — should show leader with 3-cell HP bar (wave 1) vs 5-cell HP bar (wave 10).
- `tools/playtest_out/wave_freq_4.0s.png` vs `wave_freq_2.0s.png` — the 2.0s strip should have ~2x more ships per timestamp.

If the user says "listo" or "OK", move to Step 3. If they want changes, iterate (e.g., adjust constants like `spawn_interval=1.5` or hit range `[2, 4]` instead of `[3, 5]`).

- [ ] **Step 3: Final summary report**

Write a short summary to the user:
- 2 commits made: (spawn_interval + tests) and (leader HP + tests + call site)
- 6 pre-existing test failures, 0 new ones
- 2 visual artifacts produced
- CHANGELOG entry added
- (If user wants) rebuild the .exe

Do NOT auto-rebuild the .exe. Per user memory 2026-08-14, the user controls release cadence. Ask if they want a rebuild.

---

## Self-Review (post-write)

**1. Spec coverage:**

| Spec section | Covered by |
|---|---|
| §2 Goal: confirm roguelike | Task 1 (research only) + spec doc itself |
| §2 Goal: halve spawn_interval | Task 2 |
| §2 Goal: leader HP linear 3-5 | Tasks 3, 4, 5 |
| §3 Non-Goals: no ship count changes | not in plan (correct — non-goal) |
| §3 Non-Goals: no boss changes | noted in global constraints |
| §4 Design formulas | Tasks 3, 4 |
| §5 Architecture | Tasks 2, 4, 5 |
| §6 Testing 3 layers | Task 3 (unit) + Task 4 (integration) + Task 6 (visual) |
| §7 Acceptance criteria | Task 7 (regression) + visual artifacts |
| §8 Open questions Q1, Q5 | Task 1 (research) + Task 5 (decision) |
| §9 Rollback plan | implicit (each commit is reversible; default 0 keeps backward compat) |
| §10 Out of scope | not in plan (correct) |

**2. Placeholder scan:** No TBDs, no "implement later", no "similar to Task N". All code is concrete.

**3. Type consistency:** `current_wave_idx: int = 0` is the same type in Task 3 (function consumes `wave_idx: int`), Task 4 (parameter), and Task 5 (passes `self._wave_idx` which is `int`). `_KIND_HP["SCOUT"]` is consistent across Tasks 3 and 4. `Enemy.is_leader` is added in Task 4 and used by Task 6's capture script.

**4. Gaps found:** none.
