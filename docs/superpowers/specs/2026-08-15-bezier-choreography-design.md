# BLOQUE 58.13 — Bezier Choreography (Star Fox 64 Pair Dance)

**Date:** 2026-08-15
**Status:** DESIGN — pending user review
**Author:** Mavis
**BLOQUE scope:** 58.13
**GitHub:** `https://github.com/lerius700-cmyk/Void-Hunter`

---

## 1. Problem

The 4 bezier-based procedural wave patterns (BEZIER_SWEEP, OSCILLATING_BUTTERFLY,
LEADER_FOLLOWER_CHAIN, PINCER_CROSS) currently produce **single-file** motion:
ships follow one shared bezier with t_offset stagger, reading as a "comet trail"
or "snake line".

Frame-by-frame analysis of `Assets/Bezier curves.mp4` (Star Fox 64 — Aquas
level, 15.23s @ 60fps, 457 frames extracted @ 30fps to
`tools/bezier_frames_30fps_v3/frame_*.jpg`) shows the actual SF64 choreography
relies on **groups of ships in PAIRS side-by-side, sharing parallel paths**:

| SF64 observation | Frame evidence |
|---|---|
| Pair dance (most common) | frames 0360, 0380, 0400 — 2 ships side-by-side, same heading, same curve |
| Group sweep (4-6 ships in V/row) | frame 0105 — top half shows 6 fish in row, all moving same direction |
| Entry arc (curved entry, not straight) | frames 0425, 0435 — visible curve as ships enter |
| Leader trail (snake) | frame 0280 — leader + trailing ships |
| Pincer intersect (X crossing) | frame 0105 — left + right groups converging |
| Orbital breathing (round path) | frames 0400, 0425 — circular swirl visible |

The current patterns miss the "pair" / "parallel" signature. This BLOQUE
fixes that.

## 2. Goal

Make the 4 bezier-based patterns **read as Star Fox 64 choreography** when
seen in gameplay:
- Ships fly in **PAIRS** (side-by-side) or **groups of 2+ parallel paths**
- Curves are **more dramatic** (sharper arcs, orbital motion, X-crossing)
- Player can **predict** ship movement from the pattern label

**Out of scope:**
- DICE_FIVE_GRID and V_FORMATION (already work well, not touched)
- Adding new patterns
- Changing the runtime SpawnedShip / PatternRuntime schema
- Changing HUD or wave manager integration

## 3. Design (Option C — Mixta)

Two shared path helpers added in `src/movement/`. The 4 patterns opt-in to
whichever helper fits their choreography.

### 3.1 Shared helper: `ParallelPathPair`

File: `src/movement/parallel_path.py`

A `ParallelPathPair` produces **two HybridPath instances** sharing the same
segment structure but with control points offset perpendicular to motion
(vertical offset for horizontal-traveling beziers).

```python
class ParallelPathPair:
    """Two parallel HybridPath instances, vertical offset.

    Used for Star Fox 64 style "pair dance" — 2 ships fly side-by-side
    on parallel beziers, gap_px apart.

    Args:
        base_segments: list of (p0,p1,p2,p3) — centerline bezier control points
        base_durations: list of float seconds — one per segment
        gap_px: vertical offset between the two paths (default 14)
    """
    def __init__(self, base_segments, base_durations, gap_px=14): ...
    def get_top(self) -> HybridPath: ...
    def get_bot(self) -> HybridPath: ...
```

**Static offset** (not tangent-based): for the playfield scale (320×480) and
bezier shapes we use, a constant vertical offset is visually indistinguishable
from a true perpendicular offset and 10× simpler.

### 3.2 Shared helper: `OrbitalPath`

File: `src/movement/orbital_path.py`

A `OrbitalPath` is a 4-segment compound bezier that traces a full **orbital
breathing loop** around a center point. Used by OSCILLATING_BUTTERFLY.

```python
class OrbitalPath:
    """4-segment orbital path (figure-of-breathing).

    The path traces a rough circle around a center point using 4 cubic
    bezier segments. Each segment is a quarter of the orbit.

    Args:
        center: (cx, cy) — orbital center
        radius_x: horizontal radius of orbit
        radius_y: vertical radius of orbit
        duration_s: total time for one full orbit (default 6.0)
        rotation_deg: starting angle (default 0)
    """
    def __init__(self, center, radius_x, radius_y,
                 duration_s=6.0, rotation_deg=0): ...
    def get_path(self) -> HybridPath: ...
```

The 4 control-point sets produce a smooth quarter-circle approximation.
Visually ships look like they orbit a center, then snap back. (For exact
circular motion we would need arcs; bezier approximation is good enough
at this scale.)

### 3.3 Pattern changes

#### 3.3.1 BEZIER_SWEEP — Pair Dance (Parallel Paths)

**Before:** 1 wavy 3-segment bezier, 4-8 ships with t_offset stagger in a line.

**After:** 5 PAIRS of ships on 2 parallel paths (10 ships total at level 5+).
- Path A: original wavy 3-segment bezier (centerline)
- Path B: same bezier with all control points offset +14px down
- 5 pairs in sequence: each pair = (1 ship on A, 1 ship on B)
- t_offset between pairs: 0.12s (was 0.08s) — slightly more breathing room
- Pair colors: cyan + light-cyan, magenta + pink, etc. (slight variation within pair)
- Pair completes one full pattern in 6.0s
- Levels 1-2: 6 ships (3 pairs); Levels 3+: 10 ships (5 pairs)

**Visual:** Two parallel streams of ships "dancing" through the playfield in
synchronized pairs. Reads as a "comet pair" instead of a single comet.

#### 3.3.2 OSCILLATING_BUTTERFLY — Orbital Breathing

**Before:** 1 wavy bezier with vertical offset, 4-8 ships rippling up-down.

**After:** 6-8 ships distributed around a central orbit. Each ship is at a
different point on the orbital path, so the group looks like a swirling
constellation that "breathes" around the center.
- Center: random point in middle 60% of playfield
- radius_x: 100-140px, radius_y: 70-100px (slightly squashed for "butterfly wing" feel)
- Duration: 6.0s per orbit
- Ship count: 6 (level 1) → 8 (level 5+)
- t_offsets: evenly distributed (0.0, 0.75, 1.5, 2.25, 3.0, 3.75) → ships spread around the orbit
- Colors: rainbow gradient as today (rotating hues)

**Visual:** A breathing galaxy/butterfly — the group swirls around a center
point, expanding and contracting as it orbits. NOT the previous vertical
ripple.

#### 3.3.3 LEADER_FOLLOWER_CHAIN — 2 Parallel Snake Chains

**Before:** 1 leader + 4-7 history-queue followers. frequency 0.4-0.7.

**After:** 2 INDEPENDENT chains running in parallel, gap 14px.
- Each chain: 1 leader + 4 followers (5 ships per chain = 10 total)
- Frequency: 0.7-1.1 (was 0.4-0.7) — sharper snake curves
- Delay per follower: 0.06s (was 0.08s) — tighter chain
- Inter-chain offset: 0.04s between the two chains (so they don't move in perfect lockstep)
- Both chains share the same base bezier control points

**Visual:** Two snakes swimming side-by-side through the playfield, each
trailing 4 followers. Reads as "the enemy sends in two squadrons".

#### 3.3.4 PINCER_CROSS — X-Crossing Compound

**Before:** 2 mirror beziers, both groups exit on opposite sides. 5-8 ships
per side.

**After:** 2 groups, each with a 4-segment compound bezier that **crosses to
the opposite side**.
- Segment 1 (1.5s): entry bezier — group enters from its side, curves toward center
- Segment 2 (0.8s): **X-CROSS** — sharp bezier that takes the group to the OPPOSITE side
- Segment 3 (1.0s): cruise — group continues along the opposite side
- Segment 4 (1.5s): exit bezier — group exits the far edge
- **Frame-accurate timing:** both groups reach center at t=1.5s (the X moment)
- 5-7 ships per group, t_offset 0.04s between them
- After the cross: left group is on the right, right group is on the left
  (actual side swap — not a visual illusion)
- Colors: red/cyan for the two halves; both groups get a color flash at the
  X-moment to highlight the cross

**Visual:** Two pincers attack from opposite sides, meet in the middle in a
perfect X, then escape on the swapped sides. This is THE pincer signature move.

## 4. Files

### New files
- `src/movement/parallel_path.py` (~80 lines) — `ParallelPathPair`
- `src/movement/orbital_path.py` (~60 lines) — `OrbitalPath`
- `tests/test_bloque_58_13.py` (~250 lines) — 20+ new tests
- `docs/superpowers/specs/2026-08-15-bezier-choreography-design.md` (this file)

### Modified files
- `src/systems/wave_patterns/bezier_sweep.py` — switch to ParallelPathPair
- `src/systems/wave_patterns/oscillating_butterfly.py` — switch to OrbitalPath
- `src/systems/wave_patterns/leader_chain.py` — 2 parallel chains
- `src/systems/wave_patterns/pincer_cross.py` — 4-segment X-cross compound
- `src/systems/wave_patterns/runtime.py` — extend to attach ParallelPathPair
  and OrbitalPath (the existing `attach_multi_segment_path` already handles
  compound beziers; add thin wrappers for the new helpers)

## 5. Data Flow

```
Pattern.generate(rng, level) -> WavePatternResult
    ↓ for each ship
SpawnedShip(extra={"parallel_pair": PPP, "side": "top"/"bot", "t_offset": T})
    ↓ runtime
spawn_pattern_wave(pool, result)
    ↓ attach
attach_parallel_pair_path(enemy, PPP, side, t_offset)
    └→ enemy.attach_path(follower_for_path_top_or_bot, ...)
```

For OSCILLATING_BUTTERFLY:
```
SpawnedShip(extra={"orbital": OrbitalPath, "t_offset": T})
    ↓
attach_orbital_path(enemy, orbital, t_offset)
```

For PINCER_CROSS (multi-segment + X):
```
SpawnedShip(extra={"segments": [...4 segs...],
                   "segment_durations": [1.5, 0.8, 1.0, 1.5]})
    ↓
attach_multi_segment_path(enemy, segments, durations, t_offset)  # already exists
```

## 6. Testing Strategy

20 new tests in `tests/test_bloque_58_13.py`:

### 6.1 ParallelPathPair tests (5)
- `test_parallel_pair_top_bot_offset`: top and bot paths have correct vertical offset at t=0.5
- `test_parallel_pair_same_segments`: both paths have same segment count and durations
- `test_parallel_pair_gap_zero_equals_centerline`: gap_px=0 means top==bot
- `test_parallel_pair_durations_match_base`: durations pass through unchanged
- `test_parallel_pair_offset_signs`: top offset is -gap/2, bot is +gap/2

### 6.2 OrbitalPath tests (4)
- `test_orbital_path_returns_4_segments`: 4 segments (quarters of orbit)
- `test_orbital_path_segment_durations_sum_to_total`: durations add to duration_s
- `test_orbital_path_center_is_inside_quad`: midpoint of each segment is on the orbital circle
- `test_orbital_path_rotation_offset`: rotation_deg=90 rotates the orbit by 90°

### 6.3 BEZIER_SWEEP pair dance tests (3)
- `test_bezier_sweep_5_pairs`: 5 pairs (10 ships) at level 5+
- `test_bezier_sweep_pairs_share_extra`: 2 ships in a pair share same parallel_pair + t_offset
- `test_bezier_sweep_pair_color_variation`: pair colors are close but distinct

### 6.4 OSCILLATING_BUTTERFLY orbital tests (3)
- `test_butterfly_uses_orbital_path`: extra contains orbital key
- `test_butterfly_6_ships_distributed`: 6 ships at t_offsets spread over 6s
- `test_butterfly_center_in_middle_60_percent`: center cx,cy in [0.2*W, 0.8*W]×[0.2*H, 0.8*H]

### 6.5 LEADER_CHAIN parallel tests (3)
- `test_leader_chain_2_independent_chains`: 10 ships, 2 leader groups
- `test_leader_chain_higher_frequency`: frequency > 0.7 (was 0.4-0.7)
- `test_leader_chain_inter_chain_offset`: chain B starts 0.04s after chain A

### 6.6 PINCER_CROSS X-cross tests (2)
- `test_pincer_cross_4_segments_per_group`: each ship has 4-segment path
- `test_pincer_cross_groups_meet_at_t1_5`: both groups reach center x at segment 2

Total: 20 new tests. Suite goes from 1134 → ~1154.

### 6.7 Visual verification (manual, not in suite)
After implementation, capture screenshots of each pattern mid-flight:
- `tools/capture/capture_choreography_v1.13.py` produces 4 PNGs (one per pattern)
- Compare against the SF64 reference frames in `tools/bezier_frames_30fps_v3/`
- User reviews PNGs to confirm "reads as Star Fox 64"

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Parallel path looks like duplicate instead of pair | gap_px=14 is enough distance to read as 2 ships, not stacking |
| Orbital path is too tight / ships overlap | radius_x/y 100+/70+ keeps ships spread |
| X-cross looks wrong if timing off | Frame-accurate via shared duration_s=4.8s; tests assert groups meet at t=1.5 |
| 20 new tests miss a regression | Run full suite, must pass 1154/1154 |

## 8. Out of Scope (deferred)

- Color-tinting the enemy sprite (apply_color_tint is a no-op today — ships
  use kind color). Would require modifying the enemy draw path. Deferred to
  a future BLOQUE.
- Group-firing (PINCER ships shoot in unison at the X-moment). Out of scope;
  would need weapon integration changes.
- Asteroid integration with patterns (e.g. BEZIER_SWEEP avoids asteroids).
  Out of scope; asteroids drift independently.

## 9. Acceptance Criteria

- All 20 new tests pass
- Full test suite passes (1154/1154)
- Visual capture shows each of the 4 patterns reading as "SF64 choreography"
  when compared to reference frames
- No regression in DICE_FIVE_GRID or V_FORMATION (untouched)
- Pattern durations stay in 5.5-7.5s range (no pattern takes <4s or >9s)
- Bloom/visual polish: no change to existing enemy trail/sprite code
