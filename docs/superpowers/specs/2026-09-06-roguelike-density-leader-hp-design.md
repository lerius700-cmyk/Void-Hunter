# 2026-09-06 — Roguelike Density + Leader HP Scaling

**Date:** 2026-09-06
**Status:** DESIGN — approved by user (sections 1-6, 2026-09-06)
**Author:** Mavis
**GitHub:** `https://github.com/lerius700-cmyk/Void-Hunter`

---

## 1. Problem

The current roguelike (default mode per GDD) is "too sparse" for the user:

1. **Patterns only happen occasionally.** A new wave starts every 4 seconds (`spawn_interval=4.0` in `src/core/game.py:276`). On a 6-second wave, the player has 2 seconds of "between waves" silence. The user wants "much more frequent" waves — more action, less downtime.

2. **Leaders are not differentiated from followers.** All SCOUT-kind enemies have 30 HP (`runtime.py:52 _KIND_HP = {... "SCOUT": 30, ...}`). A leader takes 1 bullet to kill at the top weapon tier (L3 does 8 damage per beam tick, SCOUT 30 HP ≈ 4 ticks). The user wants the leader to feel "tankier" — closer to the boss, the leader takes more hits.

3. **Variety of patterns is unclear to the user.** The user said "implement all the patterns" — but BLOQUE 58.next already created 4275 COMPOSED patterns (10 formations × 15 paths × 3 follows × 5 counts), and `ProceduralWaveManager` already randomizes by seed. We need to confirm this system meets the user's expectation rather than rewrite it.

User request (Lerius, 2026-09-06, in Spanish): "Crea un plan de accion para implementar todas los patterns que tenemos he irlos variando aleatoriamente para que sea un roguelike. duplica la cantidad de naves enemigas. y has que las naves lideres (las que lideran el grupo) tengan que ser golpeadas 3-5 veces (entre mas cerca al jefe en cuanto a tiempo. mas vida)."

User clarification (same conversation, follow-up): "la idea no es que aparezcan tantas naves, pero si que salgan mucho mas seguido." — the "duplica la cantidad" was reinterpreted: not more ships per pattern, but waves spawn more often (same count per pattern, half the interval).

## 2. Goal

Three changes, one spec:

1. **Confirm the roguelike pattern system** (item #1) — document the existing 4275-pattern pool + wave manager so the user sees the system is already in place. No code changes.

2. **Halve the wave spawn interval** (item #2) — `spawn_interval=4.0` → `2.0` in `src/core/game.py:276`. Same per-pattern ship counts, twice as many waves per minute. The cap on enemies-on-screen (`MAX_ENEMIES_ON_SCREEN` in `gameplay_runtime.py:1442`) will throttle the effective rate if needed.

3. **Leader HP scales with wave proximity to boss** (item #3) — a leader in wave 1 takes 3 hits to kill (90 HP), a leader in wave 10 takes 5 hits to kill (150 HP), linear interpolation between. Followers stay at 30 HP (unchanged).

## 3. Non-Goals

- **No changes to per-pattern ship counts** (V_FORMATION still 5-9, BEZIER_SWEEP still 3-5 pairs, etc.). The user explicitly clarified this in the follow-up.
- **No changes to the 4 bosses** (GOLIATH, HYDRA, PHANTOM, NEMESIS). They are separate entities with their own HP system.
- **No changes to the Sub-boss (Wolfen dart, BLOQUE 50)**. Out of scope.
- **No changes to pattern formations or paths.** Only the timing knob (item #2) and the leader HP scaling (item #3).
- **No changes to player damage, weapon tiers, or fire rate.** The "3-5 hits" is measured in HP multiplier (3×-5× SCOUT_HP), not literal player bullets.
- **No visual HP bar for leaders.** The existing glow ring is the visual indicator; "takes more hits" is the feedback.
- **No new patterns or formations.** The 4275-pattern pool is the system.
- **No rebalance of difficulty beyond what's listed.** If the user finds the game overpowering after these changes, that's a follow-up, not this spec.

## 4. Design

### Item #1 — Roguelike pattern system (CONFIRMATION, no code change)

The system the user described already exists:

- **6 base patterns** in `src/systems/wave_patterns/`:
  - `bezier_sweep.py` — pair dance on bezier
  - `v_formation.py` — rigid V
  - `leader_chain.py` — leader + history queue
  - `dice_grid.py` — 5 ships dice-5
  - `pincer_cross.py` — mirror beziers from sides
  - `oscillating_butterfly.py` — orbital circle
- **10 formations + 7 paths in COMPOSED** = 4275 pre-defined combinations in `src/systems/wave_patterns/composed.py` (line 568 `COMPOSED_PATTERNS = _build_all_patterns()`).
- **`ProceduralWaveManager`** randomizes by seed in `src/core/game.py:276`: `seed=self._patterns_seed, floor=1, spawn_interval=4.0`.
- **Default mode is roguelike** per `CLAUDE.md` GDD: "Default mode = `--roguelike`".
- **Each run with a different seed = different wave order, different formations, different paths.**

The variety is inherent; the manager picks from the 4275-pattern pool based on floor, weight, and seed. No code change is needed for this item. The spec just documents what already exists.

### Item #2 — Wave spawn interval (1 line change)

**File:** `src/core/game.py:276`
**Change:** `spawn_interval=4.0` → `spawn_interval=2.0`

**Rationale:**
- Current: 1 wave every 4 seconds = 15 waves/minute
- Proposed: 1 wave every 2 seconds = 30 waves/minute
- The user said "mucho mas seguido" — 2.0s is "much more" without being spam.
- 1.0s would be 60 waves/minute — almost certainly too fast (player reaction time).
- 2.0s is the conservative middle ground.

**Synergy with item #3:** Faster waves means more leaders per minute. The HP scaling becomes more visible to the player because they encounter more leaders per run.

**Constraint:** `MAX_ENEMIES_ON_SCREEN` cap (in `gameplay_runtime.py:1442`) will throttle the effective rate if the cap is hit. Need to verify the cap value when implementing (noted as an open question in §8).

### Item #3 — Leader HP scaling (linear 3-5 hits by wave)

**Formula:**

```python
def _leader_hits_at_wave(wave_idx: int) -> int:
    """Wave 1 (idx=0) = 3 hits, wave 10 (idx=9) = 5 hits, linear, clamped.

    The 'wave_idx' is the GLOBAL wave counter, not per-floor. Matches
    `self._wave_idx` in `gameplay_runtime.py:274`:
        self._wave_idx: int = (act - 1) * 6  # act 1 starts at wave 0
    """
    raw = 3 + (wave_idx * 2.0) / 9.0
    return max(3, min(5, round(raw)))
```

| wave_idx (global) | wave # (display) | hits | leader HP (SCOUT_HP=30) |
|---:|---:|---:|---:|
| 0 | 1 | 3 | 90 |
| 2 | 3 | 3 | 90 |
| 3 | 4 | 4 | 120 |
| 5 | 6 | 4 | 120 |
| 7 | 8 | 5 | 150 |
| 9 | 10 | 5 | 150 |
| 20+ | 11+ | 5 (clamped) | 150 (clamped) |

**Why "hits" not "HP multiplier":** The user said "tengan que ser golpeadas 3-5 veces" — 3 to 5 times. The actual HP value is `SCOUT_HP * hits` = 90, 120, or 150. The visual "3-5 hits" is approximate at the dominant weapon tier (L3, 8 damage per tick): a leader at wave 10 takes 150/8 ≈ 19 ticks to kill. This is a "tanky" feel, not literally "5 bullets". The intent of the user is "leader feels tanky", not "literal 5 bullets to kill".

**Application:** in `runtime.py:spawn_pattern_wave`, after each `e = pool.spawn(...)`, if `spawned.is_leader` is True, set `e.hp = _KIND_HP["SCOUT"] * _leader_hits_at_wave(current_wave_idx)`. The followers keep `e.hp = _KIND_HP["SCOUT"]` = 30 (unchanged).

**Visual indicator:** none added. The existing `draw_leader_glows` (`runtime.py:340`) glow ring is the visual cue. The player sees the leader take more hits before exploding. If the user wants a HP bar, that's a follow-up.

**Reverse safety:** `spawn_pattern_wave` gains a parameter `current_wave_idx: int = 0`. If the caller doesn't pass it, default is 0 = wave 1 = 3 hits. Existing callers that don't pass the param keep working. The new behavior is opt-in at the call site.

## 5. Architecture (where changes go)

### Change 1 — `src/core/game.py:276`

```python
# BEFORE
seed=self._patterns_seed, floor=1, spawn_interval=4.0,
# AFTER
seed=self._patterns_seed, floor=1, spawn_interval=2.0,
```

One line. Zero cascade. The wave manager already respects the knob.

### Change 2 — `src/systems/wave_patterns/runtime.py`

Add a new pure function near the top of the module (after imports, before `pattern_kind_to_enemy_kind`):

```python
def _leader_hits_at_wave(wave_idx: int) -> int:
    """BLOQUE 58.next: leader HP scaling.

    Wave 1 (idx=0) = 3 hits, wave 10 (idx=9) = 5 hits, linear, clamped.
    Returns the number of player hits a leader needs to be killed.
    """
    raw = 3 + (wave_idx * 2.0) / 9.0
    return max(3, min(5, round(raw)))
```

Modify `spawn_pattern_wave` (line 197) to add a parameter and apply the HP:

```python
def spawn_pattern_wave(
    pool: EnemyPool,
    result: WavePatternResult,
    duration_s: Optional[float] = None,
    current_wave_idx: int = 0,  # NEW, default 0 = wave 1 for backward compat
) -> PatternRuntime:
    ...
    for spawned in result.ships:
        ...
        e = pool.spawn(kind, spawned.spawn_x, spawned.spawn_y)
        if e is None:
            continue
        ...
        # BLOQUE 58.next: leader HP scales with wave proximity to boss.
        if spawned.is_leader:
            hits = _leader_hits_at_wave(current_wave_idx)
            e.hp = _KIND_HP["SCOUT"] * hits
        # (followers keep default HP from the pool = _KIND_HP["SCOUT"] = 30)
```

### Change 3 — `src/ui/gameplay_runtime.py` (or wherever `spawn_pattern_wave` is called)

Find the call site of `spawn_pattern_wave` and pass `current_wave_idx=self._wave_idx`. If the call site is in `core/game.py`, propagate from there.

**Data flow:**

```
self._wave_idx  (gameplay_runtime.py:274, global wave counter)
    └─ passed to spawn_pattern_wave(current_wave_idx=self._wave_idx)
         └─ for each spawned.is_leader:
              e.hp = SCOUT_HP * _leader_hits_at_wave(self._wave_idx)
```

## 6. Testing Strategy

Three layers, proportional to the change (1 line + ~20 lines new code).

### Layer 1 — Unit (pure function)

`tests/test_wave_patterns.py`, new class `TestLeaderHPScaling`:

| Test | Asserts |
|---|---|
| `test_hits_at_wave_1_is_3` | `_leader_hits_at_wave(0) == 3` |
| `test_hits_at_wave_5_is_4` | `_leader_hits_at_wave(4) == 4` |
| `test_hits_at_wave_10_is_5` | `_leader_hits_at_wave(9) == 5` |
| `test_hits_beyond_wave_10_clamps_to_5` | `_leader_hits_at_wave(20) == 5` |
| `test_hits_below_wave_1_clamps_to_3` | `_leader_hits_at_wave(-5) == 3` |
| `test_hits_scales_linearly_between_anchors` | wave_idx=0..9 → 3,3,3,4,4,4,4,5,5,5 |
| `test_hp_formula_is_hits_times_scout_hp` | wave_idx=0 → 90, =4 → 120, =9 → 150 |

~50 LOC. No pygame, no scene, no enemy pool. Table-driven.

### Layer 2 — Integration (`spawn_pattern_wave` end-to-end)

`tests/test_wave_patterns.py` or new `tests/test_leader_spawn.py`:

| Test | Asserts |
|---|---|
| `test_spawn_with_wave_idx_0_gives_leader_90_hp` | spawn COMPOSED with leader at wave 1 → leader.hp == 90 |
| `test_spawn_with_wave_idx_9_gives_leader_150_hp` | same pattern at wave 10 → leader.hp == 150 |
| `test_followers_unchanged_at_30_hp` | non-leader ships → hp == 30 |
| `test_default_wave_idx_0_is_backward_compat` | call without param → leader.hp == 90 (default 0) |
| `test_each_pattern_kind_respects_formula` | BEZIER_SWEEP, V_FORMATION, COMPOSED — all apply |

~80 LOC. Needs pygame dummy + EnemyPool. Headless.

### Layer 3 — Visual verification (capture scripts)

`tools/playtest_out/_capture_leader_hp_scaling.py` (new):

1. Generate V_FORMATION with 1 leader at wave 1 and wave 10 (same seed, same level).
2. Render the leader with a mini HP bar overlay (3/3 vs 5/5) for visual proof.
3. Output: `tools/playtest_out/leader_hp_wave1_vs_wave10.png` (side-by-side panels).

`tools/playtest_out/_capture_wave_frequency.py` (new):

1. Run 10 seconds of gameplay at spawn_interval=4.0 (baseline).
2. Run 10 seconds at spawn_interval=2.0 (proposed).
3. Same seed, same level, same floor.
4. Output: 2 PNG strips showing the playfield at t=0, 2, 4, 6, 8, 10s. Player can count waves per strip.

`tools/playtest_out/_capture_roguelike_variety.py` (DEFERRED — out of scope for this spec):

If the user wants to see the variety proof after the main spec is done, this can be added as a follow-up. Not required to call this spec "done".

### Regression baseline

The 6 pre-existing failures stay exactly the same:
- 1× `tests/test_paths.py::test_paths_no_star_shapes`
- 5× `tests/test_sub_boss_*.py` (headless flakes)

If new failures appear, it's a regression introduced by this spec. Investigate.

## 7. Acceptance Criteria

| # | Criterion | Verified by |
|---|---|---|
| 1 | `spawn_interval=2.0` in `src/core/game.py:276` | `git diff` shows the change |
| 2 | `_leader_hits_at_wave(0) == 3`, `(9) == 5`, `(20) == 5` | unit tests pass |
| 3 | `spawn_pattern_wave` with `current_wave_idx=4` produces a leader with `hp=120` | integration test passes |
| 4 | Followers stay at `hp=30` | integration test passes |
| 5 | No new test regressions (the 6 pre-existing fails are still the only fails) | `pytest tests/ -q` |
| 6 | `tools/playtest_out/leader_hp_wave1_vs_wave10.png` shows leader HP difference | user confirms visually |
| 7 | `tools/playtest_out/wave_freq_*.png` shows 2x more waves at interval=2.0 vs 4.0 | user confirms visually |
| 8 | Default `current_wave_idx=0` does not break any existing test | existing tests pass |

## 8. Open Questions / Risks

### Q1 — `MAX_ENEMIES_ON_SCREEN` cap value (item #2)

**Risk:** if the cap is too low (e.g., 12), the faster spawn interval will be throttled. The effective wave-per-second rate might not be 2x.

**Action when implementing:** look up the value. If it's a problem, either:
- (a) Raise the cap to accommodate the new rhythm
- (b) Keep the cap and accept the throttle as a "natural difficulty curve"
- (c) Ask the user

The user should be informed of the cap's behavior before implementation, in case they want option (a) or (c).

### Q2 — "3-5 hits" interpretation (item #3)

**Risk:** at weapon L1 (1 damage/bullet), a leader with 90 HP takes 90 bullets. That's NOT "3 hits". The user's "3-5 hits" can only be measured as an HP multiplier (3x-5x SCOUT) at a reference weapon tier.

**Action when implementing:** state this in the spec clearly (already done in §4). If the user wants literal "3 bullets to kill", the implementation would need a different formula (e.g., `leader_hp = player_weapon_damage * (3-5)`) and would depend on the player's current weapon. That's significantly more complex and is a follow-up if the user wants it.

### Q3 — Bosses excluded from HP scaling (item #3)

**Risk:** the user might want the 4 bosses (GOLIATH, HYDRA, PHANTOM, NEMESIS) to also have HP scaling. Currently they don't.

**Action when implementing:** confirm with the user that bosses are out of scope. If they're in scope, this spec needs an extension. Document the choice in the implementation PR.

### Q4 — Difficulty curve

**Risk:** faster waves + 3-5× leader HP = significantly harder game. The user might find it overpowering.

**Action when implementing:** this is a tuning concern, not a design defect. The spec delivers what the user asked for. If the user finds it overpowering in playtest, we adjust the constants (spawn_interval back to 3.0, or leader hits to 2-4 instead of 3-5). This is a one-line revert.

### Q5 — Wave counter: GLOBAL vs PER-FLOOR (item #3)

**Risk:** the formula in §4 uses the **global** wave counter (`self._wave_idx = (act - 1) * 6` in `gameplay_runtime.py:274`). The user's phrase "más cerca al jefe en cuanto a tiempo" is ambiguous:

- **(a) Closer to the FINAL boss** (NEMESIS at the end of the run): global counter is correct. Wave 1 = far from final boss = 3 hits. Wave 10+ = close to final boss = 5 hits.
- **(b) Closer to the CURRENT floor's boss** (GOLIATH/HYDRA/PHANTOM per floor): per-floor counter is needed. Wave 1 of each floor = far from current floor's boss = 3 hits. Wave 5 of each floor = close to current floor's boss = 5 hits.

**Default assumption:** (a) global, because the formula in §4 was approved by the user with the linear 3-5 mapping. (a) makes the difficulty curve go up monotonically across the entire run, which is the "more roguelike" feel.

**Action when implementing:** the call site in `gameplay_runtime.py` is the place to make this choice:
- For (a): pass `self._wave_idx` directly.
- For (b): compute the per-floor wave counter (e.g., `self._wave_idx % waves_per_floor`) and pass that. Need to find `waves_per_floor` in the codebase.

**Confirm with the user during implementation** before wiring up the call site. If (b), the formula might need adjustment (each floor has 5-6 waves, not 10).

## 9. Rollback Plan

The change set is small. Reverse-safe defaults mean the new code path is opt-in.

- **Item #2 (spawn_interval):** revert the 1 line in `src/core/game.py:276` (`2.0` → `4.0`). 5 seconds.
- **Item #3 (leader HP):**
  - The default `current_wave_idx=0` means if the call site is NOT updated, all leaders still get 3 hits (90 HP) — same as if the spec is fully applied at wave 1.
  - To fully revert: revert `_leader_hits_at_wave` (delete the function) and the HP assignment in `spawn_pattern_wave` (delete the `if spawned.is_leader:` block). ~10 lines.
  - Alternative: don't pass `current_wave_idx` in the call site. All leaders get 3 hits regardless of wave.
- **Tests:** delete the `TestLeaderHPScaling` class and the integration tests. ~150 LOC. Zero impact on other tests.
- **Capture scripts:** delete the 3 new files in `tools/playtest_out/`. Zero impact.

## 10. Out of Scope (deferred)

These are explicitly NOT part of this spec. If the user wants them, separate specs:

- Boss HP scaling (GOLIATH/HYDRA/PHANTOM/NEMESIS)
- Sub-boss HP scaling (Wolfen dart)
- Per-pattern difficulty (some patterns always harder than others)
- Player damage scaling (so L1 also takes 3-5 hits to kill leaders — see §8 Q2)
- Visual HP bar for leaders
- Audio cue when leader is "tanky" (low-pitch hum, etc.)
- Roguelike meta-progression (perks between runs, unlockables, etc.)
