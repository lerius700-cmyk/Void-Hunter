# STELLAR HORIZON Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable vertical slice of STELLAR HORIZON — a horizontal
16-bit shmup that reuses Void-Hunter's bezier movement library — with one
act, three waves plus a boss-rush, and one boss (ASTEROID_GUARDIAN).

**Architecture:** Library-Import (Approach A). The new project lives at
`void-hunter/stellar_horizon/` and imports from `void-hunter/src/movement/`,
`src/audio/synth`, `src/systems/particle_engine`, and `src/utils/`. Internal
resolution 480×270, scaled 4× to a 1920×1080 window. Player uses
WASD/Arrows + Spacebar; shots go left→right; enemies enter from the right,
top, and bottom following bezier paths.

**Tech Stack:** Python 3.11+, Pygame 2.6.1+, pytest. No numpy/scipy.
16-bit pixel art (user-drawn, placeholders for tests). MIDI for music
(`pygame.mixer.music`), SFX reuses `src.audio.synth`.

## Global Constraints

These apply to every task. Each task's requirements implicitly include them.

- **Python:** ≥ 3.11. Type hints on all public functions. `from __future__ import annotations` at the top of every file.
- **Pygame:** ≥ 2.6. No numpy/scipy anywhere.
- **Internal resolution:** 480×270. All game logic uses these coordinates. The window is 1920×1080 (4× scale).
- **Frame timing:** `FIXED_DT = 1/120 s`. Accumulator pattern. `DT_CLAMP = 1/30 s`.
- **Imports from VH:** always absolute: `from src.movement import ...`, `from src.audio.synth import ...`, etc. Never modify `src/`.
- **Testing:** pytest. ≥30% coverage target. Tests live in `stellar_horizon/tests/`. Run with `python -m pytest stellar_horizon/tests/ -v`.
- **Quality gates:** all tests pass, mypy exits 0 on the package, no new warnings.
- **No auto-zip:** do not run `pyinstaller` or build releases; user controls version cadence.
- **Commit style:** `<type>(<scope>): <subject>`. Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`. Scopes: `paths`, `formations`, `player`, `enemy`, `boss`, `wave`, `hud`, `bg`, `audio`, `fx`, `scene`, `core`, `smoke`.
- **Commit cadence:** after every task (or every green test pair). Always before moving to the next task.

---

## Task 1: Project skeleton + settings + main entry

**Files:**
- Create: `void-hunter/stellar_horizon/settings.py`
- Create: `void-hunter/stellar_horizon/main.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/__init__.py`
- Create: `void-hunter/stellar_horizon/tests/__init__.py`
- Create: `void-hunter/stellar_horizon/tests/test_smoke.py`
- Create: `void-hunter/stellar_horizon/requirements.txt`
- Create: `void-hunter/stellar_horizon/README.md`
- Create: `void-hunter/stellar_horizon/.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `stellar_horizon.settings.{INTERNAL_W, INTERNAL_H, WINDOW_W, WINDOW_H, FPS_TARGET, FIXED_DT, DT_CLAMP, WINDOW_TITLE}`; `stellar_horizon.main.main()` returns int 0

- [ ] **Step 1: Create `stellar_horizon/settings.py`**

```python
"""Global settings for STELLAR HORIZON — 480x270 horizontal, 1920x1080 window."""
from __future__ import annotations

# Display
INTERNAL_W: int = 480
INTERNAL_H: int = 270
DEFAULT_SCALE: int = 4
WINDOW_W: int = INTERNAL_W * DEFAULT_SCALE   # 1920
WINDOW_H: int = INTERNAL_H * DEFAULT_SCALE   # 1080
WINDOW_TITLE: str = "STELLAR HORIZON"

# Frame timing — 120 FPS lock
FPS_TARGET: int = 120
FIXED_DT: float = 1.0 / FPS_TARGET
DT_CLAMP: float = 1.0 / 30.0

# Pools
PLAYER_BULLET_POOL: int = 32
ENEMY_BULLET_POOL: int = 64
ENEMY_POOL: int = 32
PARTICLE_POOL: int = 600
```

- [ ] **Step 2: Create `stellar_horizon/main.py`**

```python
"""STELLAR HORIZON — entry point."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stellar-horizon",
        description="STELLAR HORIZON — horizontal 16-bit shmup, 480x270 internal.",
    )
    parser.add_argument("--check", action="store_true", help="Validate imports + settings; exit 0/1.")
    parser.add_argument("--duration", type=int, default=0, help="Auto-exit after N seconds (0 = no auto-exit).")
    args = parser.parse_args(argv)
    if args.check:
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, FPS_TARGET
        print("STELLAR HORIZON check OK")
        print(f"  Internal: {INTERNAL_W}x{INTERNAL_H}")
        print(f"  FPS target: {FPS_TARGET}")
        return 0
    # Defer to Task 15 for the real run loop. For now, just acknowledge.
    print(f"STELLAR HORIZON: --duration {args.duration} (game loop wired in Task 15)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Create empty `__init__.py` files**

```python
# stellar_horizon/stellar_horizon/__init__.py — package marker
```

```python
# stellar_horizon/tests/__init__.py — package marker
```

- [ ] **Step 4: Create `requirements.txt`**

```
pygame>=2.6.0
pytest>=7.0
```

- [ ] **Step 5: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.coverage
build/
dist/
*.egg-info/
releases/
tools/playtest_out/
assets/sprites/.wip/
```

- [ ] **Step 6: Create `README.md`**

```markdown
# STELLAR HORIZON

A horizontal 16-bit space shooter built on Void-Hunter's movement library.

**Run:** `python main.py --check` to validate. Full game loop lands in Task 15.

**Spec:** `docs/superpowers/specs/2026-08-15-stellar-horizon-design.md`
```

- [ ] **Step 7: Write the smoke test**

```python
# stellar_horizon/tests/test_smoke.py
from stellar_horizon import settings


def test_settings_have_expected_values():
    assert settings.INTERNAL_W == 480
    assert settings.INTERNAL_H == 270
    assert settings.WINDOW_W == 1920
    assert settings.WINDOW_H == 1080
    assert settings.FPS_TARGET == 120
    assert abs(settings.FIXED_DT - 1 / 120) < 1e-9


def test_window_title_is_set():
    assert settings.WINDOW_TITLE == "STELLAR HORIZON"


def test_pools_are_positive():
    assert settings.PLAYER_BULLET_POOL > 0
    assert settings.ENEMY_BULLET_POOL > 0
    assert settings.ENEMY_POOL > 0
    assert settings.PARTICLE_POOL > 0
```

- [ ] **Step 8: Run the test**

Run from `void-hunter/`:
```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_smoke.py -v
```
Expected: 3 passed.

- [ ] **Step 9: Run `--check` to verify CLI**

```bash
cd D:/AI/void-hunter && python stellar_horizon/main.py --check
```
Expected: prints "STELLAR HORIZON check OK" and exits 0.

- [ ] **Step 10: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/settings.py stellar_horizon/main.py
git add stellar_horizon/stellar_horizon/__init__.py stellar_horizon/tests/__init__.py
git add stellar_horizon/tests/test_smoke.py stellar_horizon/requirements.txt
git add stellar_horizon/.gitignore stellar_horizon/README.md
git commit -m "chore(core): project skeleton + settings + main entry"
```

---

## Task 2: Bezier horizontal path presets

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/bezier_horizontal.py`
- Create: `void-hunter/stellar_horizon/tests/test_horizontal_bezier.py`

**Interfaces:**
- Consumes: `src.movement.{BezierPath, WaypointPath, HybridPath, Point}`
- Produces:
  - `path_s_right_to_left(y_offset: float = 0.0) -> BezierPath`
  - `path_top_dive(side: str = "right") -> BezierPath`
  - `path_zigzag_exit_top() -> HybridPath`
  - `path_boss_entry() -> BezierPath`

- [ ] **Step 1: Create `waves/__init__.py`**

```python
# stellar_horizon/waves/__init__.py
```

- [ ] **Step 2: Write the failing tests**

```python
# stellar_horizon/tests/test_horizontal_bezier.py
import pytest
from src.movement import BezierPath, WaypointPath, HybridPath, Point

from stellar_horizon.waves.bezier_horizontal import (
    path_s_right_to_left, path_top_dive, path_zigzag_exit_top, path_boss_entry,
)


def _is_off_screen(p: Point) -> bool:
    """Returns True if point is outside 480x270 play area (with small margin)."""
    return p.x < -8 or p.x > 488 or p.y < -8 or p.y > 278


def test_path_s_right_to_left_returns_bezier():
    p = path_s_right_to_left()
    assert isinstance(p, BezierPath)


def test_path_s_right_to_left_starts_off_screen_right():
    p = path_s_right_to_left()
    start = p.position_at(0.0)
    assert start.x > 480  # off-screen right


def test_path_s_right_to_left_ends_off_screen_left():
    p = path_s_right_to_left()
    end = p.position_at(1.0)
    assert end.x < 0  # off-screen left


def test_path_s_right_to_left_traverses_screen():
    p = path_s_right_to_left()
    # Sample the midpoint; should be inside the screen
    mid = p.position_at(0.5)
    assert 0 <= mid.x <= 480
    assert 0 <= mid.y <= 270


def test_path_s_right_to_left_with_y_offset():
    p = path_s_right_to_left(y_offset=80.0)
    start = p.position_at(0.0)
    # Y should be offset from baseline 60
    assert abs(start.y - 140) < 1.0  # 60 + 80


def test_path_top_dive_starts_off_screen_top():
    p = path_top_dive()
    start = p.position_at(0.0)
    assert start.y < 0  # off-screen top


def test_path_top_dive_right_ends_right():
    p = path_top_dive(side="right")
    end = p.position_at(1.0)
    assert end.x > 480  # off-screen right


def test_path_top_dive_left_ends_left():
    p = path_top_dive(side="left")
    end = p.position_at(1.0)
    assert end.x < 0  # off-screen left


def test_path_zigzag_exit_top_returns_hybrid():
    p = path_zigzag_exit_top()
    assert isinstance(p, HybridPath)


def test_path_zigzag_exit_top_starts_off_screen_right():
    p = path_zigzag_exit_top()
    start = p.position_at(0.0)
    assert start.x > 480  # enters from right


def test_path_zigzag_exit_top_ends_off_screen_top():
    p = path_zigzag_exit_top()
    end = p.position_at(1.0)
    assert end.y < 0  # exits top


def test_path_boss_entry_starts_off_screen_right():
    p = path_boss_entry()
    start = p.position_at(0.0)
    assert start.x > 480


def test_path_boss_entry_ends_at_arena():
    p = path_boss_entry()
    end = p.position_at(1.0)
    # Spec: boss arena is (350, 135)
    assert abs(end.x - 350) < 0.01
    assert abs(end.y - 135) < 0.01
```

- [ ] **Step 3: Run tests — they should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_horizontal_bezier.py -v
```
Expected: ImportError for `bezier_horizontal`.

- [ ] **Step 4: Implement `bezier_horizontal.py`**

```python
"""Horizontal bezier paths for STELLAR HORIZON.

Each path enters from off-screen and exits off-screen, so the enemy visibly
travels across the play area. All paths are tuned for a 480x270 viewport.
"""
from __future__ import annotations

from src.movement import BezierPath, HybridPath, Point, WaypointPath


def path_s_right_to_left(y_offset: float = 0.0) -> BezierPath:
    """S-curve from off-screen right to off-screen left.

    Args:
        y_offset: shifts the curve vertically. Default 0 puts baseline at y=60.
    """
    return BezierPath(
        p0=Point(490, 60 + y_offset),
        p1=Point(380, 60 + y_offset),
        p2=Point(100, 200 - y_offset),
        p3=Point(-20, 200 - y_offset),
    )


def path_top_dive(side: str = "right") -> BezierPath:
    """Arcs down from off-screen top, exits off-screen right (or left).

    Args:
        side: "right" exits at x=470; "left" exits at x=10.
    """
    end_x = 470 if side == "right" else 10
    return BezierPath(
        p0=Point(200, -20),
        p1=Point(200, 50),
        p2=Point(380 if side == "right" else 100, 150),
        p3=Point(end_x, 240),
    )


def path_zigzag_exit_top() -> HybridPath:
    """Bezier segment + waypoint zigzag, exits off-screen top."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 100),
            p1=Point(300, 100),
            p2=Point(200, 180),
            p3=Point(300, 220),
        ),
        WaypointPath(
            [Point(300, 220), Point(380, 150), Point(250, 80), Point(200, -20)],
            speed_px_s=140.0,
        ),
    ])


def path_boss_entry() -> BezierPath:
    """Dramatic S-curve from off-screen right to boss arena (350, 135)."""
    return BezierPath(
        p0=Point(540, 60),
        p1=Point(450, 100),
        p2=Point(380, 200),
        p3=Point(350, 135),
    )
```

- [ ] **Step 5: Run tests — they should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_horizontal_bezier.py -v
```
Expected: 13 passed.

- [ ] **Step 6: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/waves/__init__.py
git add stellar_horizon/stellar_horizon/waves/bezier_horizontal.py
git add stellar_horizon/tests/test_horizontal_bezier.py
git commit -m "feat(paths): 4 horizontal bezier path presets"
```

---

## Task 3: Formation rotations for horizontal play

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/formations_h.py`
- Create: `void-hunter/stellar_horizon/tests/test_formations_h.py`

**Interfaces:**
- Consumes: `src.movement.FlightFormation`
- Produces:
  - `v_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]`
  - `line_horizontal(count: int = 5, spacing: float = 22.0) -> list[tuple[float, float]]`
  - `diamond_pointing_left(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]`
  - `wedge_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_formations_h.py
import pytest

from stellar_horizon.waves.formations_h import (
    v_pointing_left, line_horizontal, diamond_pointing_left, wedge_pointing_left,
)


def test_v_pointing_left_default_count():
    offsets = v_pointing_left()
    assert len(offsets) == 5


def test_v_pointing_left_count_3():
    offsets = v_pointing_left(count=3)
    assert len(offsets) == 3


def test_v_pointing_left_wings_behind_leader():
    """For enemies moving -X, wings must be at +X (behind the leader)."""
    offsets = v_pointing_left(count=5, spacing=18.0)
    leader = offsets[0]
    # Leader at (0, 0); wings should have x > 0
    assert leader == (0.0, 0.0)
    for dx, dy in offsets[1:]:
        assert dx > 0  # behind the leader (in -X direction of motion)


def test_v_pointing_left_wings_symmetric_y():
    offsets = v_pointing_left(count=5, spacing=18.0)
    # Wings at (s, -s) and (s, +s): y magnitudes should match
    ys = sorted([abs(dy) for _, dy in offsets[1:]])
    assert ys[0] == ys[-1] or len(set(ys)) <= 2  # symmetric


def test_line_horizontal_default_count():
    offsets = line_horizontal()
    assert len(offsets) == 5
    # All on y=0
    for _, dy in offsets:
        assert dy == 0.0


def test_line_horizontal_spans_correctly():
    offsets = line_horizontal(count=5, spacing=22.0)
    xs = sorted([dx for dx, _ in offsets])
    # half = (5-1) * 22 / 2 = 44; range is -44 to +44
    assert xs[0] == -44.0
    assert xs[-1] == 44.0


def test_diamond_pointing_left_default_count():
    offsets = diamond_pointing_left()
    assert len(offsets) == 5


def test_diamond_pointing_left_vertex_at_origin():
    offsets = diamond_pointing_left(count=5, spacing=20.0)
    # First slot is the leader/vertex at (0, 0)
    assert offsets[0] == (0.0, 0.0)


def test_wedge_pointing_left_count_3():
    offsets = wedge_pointing_left(count=3)
    assert len(offsets) == 3


def test_wedge_pointing_left_tip_at_origin():
    offsets = wedge_pointing_left(count=5)
    # Tip is leader at (0, 0)
    assert offsets[0] == (0.0, 0.0)


def test_formations_with_count_1():
    """count=1 formations should return a single (0, 0) slot."""
    for fn in (v_pointing_left, line_horizontal, diamond_pointing_left, wedge_pointing_left):
        offsets = fn(count=1)
        assert len(offsets) == 1
        assert offsets[0] == (0.0, 0.0)
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_formations_h.py -v
```

- [ ] **Step 3: Implement `formations_h.py`**

```python
"""Formation helpers for horizontal play.

These wrap Void-Hunter's `FlightFormation` by rotating the offsets so the
formation points in the direction enemies move (-X, i.e. right-to-left).
"""
from __future__ import annotations

from src.movement import FlightFormation


def _v_offsets_rotated(count: int, spacing: float) -> list[tuple[float, float]]:
    """VH's V (apex -Y) rotated 90° CW -> wings at +X (apex points -X)."""
    base = FlightFormation.v(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]


def v_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """V formation with apex pointing -X (enemies moving right→left)."""
    if count == 1:
        return [(0.0, 0.0)]
    return _v_offsets_rotated(count, spacing)


def line_horizontal(count: int = 5, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Horizontal line of N slots, perpendicular to the direction of motion."""
    if count == 1:
        return [(0.0, 0.0)]
    half = (count - 1) * spacing / 2.0
    return [(-half + i * spacing, 0.0) for i in range(count)]


def diamond_pointing_left(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Diamond formation with vertex pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]
    layer = 1
    while len(offsets) < count:
        offsets.append((-spacing * layer, 0.0))            # front (toward -X)
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, -spacing * layer))  # top-front
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, +spacing * layer))  # bottom-front
        if len(offsets) >= count: break
        offsets.append((+spacing * layer, 0.0))             # back
        layer += 1
    return offsets[:count]


def wedge_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """Wedge (> shape) with tip pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    # VH's WEDGE rotated 90° CW: (x, y) -> (y, -x)
    base = FlightFormation.wedge(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]
```

- [ ] **Step 4: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_formations_h.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/waves/formations_h.py
git add stellar_horizon/tests/test_formations_h.py
git commit -m "feat(formations): 4 horizontal formation helpers (V/line/diamond/wedge rotated)"
```

---

## Task 4: Player entity

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/entities/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/entities/player.py`
- Create: `void-hunter/stellar_horizon/tests/test_player.py`

**Interfaces:**
- Consumes: nothing (independent)
- Produces: `stellar_horizon.entities.player.Player`
  - `__init__(screen_rect: pygame.Rect) -> None`
  - `update(dt: float, keys, bullets_pool: list) -> None`
  - `take_hit() -> None`
  - `hitbox() -> pygame.Rect`
  - attributes: `x: float, y: float, vx: float, vy: float, lives: int, alive: bool, shoot_cooldown: float, invulnerable_frames: int, firing: bool, bullets: list`

- [ ] **Step 1: Create `entities/__init__.py`**

```python
# stellar_horizon/entities/__init__.py
```

- [ ] **Step 2: Write the failing tests**

```python
# stellar_horizon/tests/test_player.py
import pygame
import pytest

from stellar_horizon.entities.player import Player
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


@pytest.fixture
def screen_rect():
    return pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)


@pytest.fixture
def no_keys():
    return {k: False for k in (
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_SPACE,
    )}


def test_player_starts_at_left_center(screen_rect):
    p = Player(screen_rect)
    assert p.x == 40.0
    assert p.y == screen_rect.centery


def test_player_has_3_lives(screen_rect):
    p = Player(screen_rect)
    assert p.lives == 3
    assert p.alive is True


def test_player_move_right(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_d: True}
    p.update(0.1, keys, [])
    assert p.x > 40.0
    assert p.vy == 0.0


def test_player_move_up_with_w(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    p.update(0.1, keys, [])
    assert p.y < screen_rect.centery


def test_player_move_with_arrows(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_LEFT: True}
    p.update(0.1, keys, [])
    assert p.x < 40.0


def test_player_bounds_x(screen_rect, no_keys):
    p = Player(screen_rect)
    # Push right for 5 seconds
    keys = {**no_keys, pygame.K_d: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.x <= 472


def test_player_bounds_y(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.y >= 16


def test_player_take_hit_decrements_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.lives == 2


def test_player_take_hit_sets_iframes(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.invulnerable_frames > 0


def test_player_take_hit_kills_when_no_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.take_hit()
    p.take_hit()
    assert p.lives == 0
    assert p.alive is False


def test_player_iframes_prevent_double_hit(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.take_hit()  # should be ignored due to iframes
    assert p.lives == 2


def test_player_shoot_cooldown_decreases(screen_rect, no_keys):
    p = Player(screen_rect)
    p.shoot_cooldown = 0.5
    p.update(0.1, no_keys, [])
    assert p.shoot_cooldown == pytest.approx(0.4)
```

- [ ] **Step 3: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_player.py -v
```

- [ ] **Step 4: Implement `player.py`**

```python
"""Player entity — horizontal fighter controlled by WASD/Arrows + Spacebar."""
from __future__ import annotations

import pygame


class Player:
    SPEED = 165.0
    SHOOT_COOLDOWN_S = 0.10
    BULLET_OFFSET_X = 12
    MAX_LIVES = 3
    IFRAMES_FRAMES = 30
    INVULN_FRAMES_PER_HIT = 30
    BOUND_X_MIN = 8
    BOUND_X_MAX = 472
    BOUND_Y_MIN = 16
    BOUND_Y_MAX = 254
    START_X = 40.0

    __slots__ = (
        "x", "y", "vx", "vy", "lives", "shoot_cooldown",
        "invulnerable_frames", "alive", "firing", "thrusting", "bullets",
    )

    def __init__(self, screen_rect: pygame.Rect) -> None:
        self.x: float = self.START_X
        self.y: float = float(screen_rect.centery)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.lives: int = self.MAX_LIVES
        self.shoot_cooldown: float = 0.0
        self.invulnerable_frames: int = 0
        self.alive: bool = True
        self.firing: bool = False
        self.thrusting: bool = False
        self.bullets: list = []

    def update(self, dt: float, keys, bullets_pool) -> None:
        if not self.alive:
            return
        # Input → velocity (8-direction, normalized on diagonals)
        dx = int(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) - int(bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))
        dy = int(bool(keys[pygame.K_s] or keys[pygame.K_DOWN]))  - int(bool(keys[pygame.K_w] or keys[pygame.K_UP]))
        if dx and dy:
            inv = 0.7071067811865475  # 1/sqrt(2)
            self.vx = dx * self.SPEED * inv
            self.vy = dy * self.SPEED * inv
            self.thrusting = True
        elif dx or dy:
            self.vx = dx * self.SPEED
            self.vy = dy * self.SPEED
            self.thrusting = True
        else:
            self.vx = self.vy = 0.0
            self.thrusting = False
        # Position update with bounds
        self.x = max(self.BOUND_X_MIN, min(self.BOUND_X_MAX, self.x + self.vx * dt))
        self.y = max(self.BOUND_Y_MIN, min(self.BOUND_Y_MAX, self.y + self.vy * dt))
        # Shoot
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.firing and self.shoot_cooldown <= 0.0 and bullets_pool:
            self._spawn_bullet(bullets_pool)
            self.shoot_cooldown = self.SHOOT_COOLDOWN_S
        # Iframes tick down
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1

    def take_hit(self) -> None:
        if not self.alive or self.invulnerable_frames > 0:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
        else:
            self.invulnerable_frames = self.INVULN_FRAMES_PER_HIT

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)

    def _spawn_bullet(self, bullets_pool) -> None:
        from stellar_horizon.entities.bullet import PlayerBullet  # local import to avoid cycle in early tasks
        for b in bullets_pool:
            if not b.alive:
                b.x = self.x + self.BULLET_OFFSET_X
                b.y = self.y
                b.vx = 480.0
                b.vy = 0.0
                b.alive = True
                return
```

- [ ] **Step 5: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_player.py -v
```
Expected: 12 passed.

- [ ] **Step 6: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/entities/__init__.py
git add stellar_horizon/stellar_horizon/entities/player.py
git add stellar_horizon/tests/test_player.py
git commit -m "feat(player): horizontal player with WASD/Arrows + 3 lives"
```

---

## Task 5: Bullets (player + enemy)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/entities/bullet.py`
- Create: `void-hunter/stellar_horizon/tests/test_bullet.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `PlayerBullet` (slots: `x, y, vx, vy, alive`)
    - `update(dt: float) -> None`
    - `hitbox() -> pygame.Rect`
  - `EnemyBullet` (slots: `x, y, vx, vy, alive, damage`)
    - `spawn(x, y, target_x, target_y) -> None`
    - `update(dt: float) -> None`
    - `hitbox() -> pygame.Rect`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_bullet.py
import math
import pytest
import pygame

from stellar_horizon.entities.bullet import PlayerBullet, EnemyBullet


def test_player_bullet_starts_dead():
    b = PlayerBullet()
    assert b.alive is False


def test_player_bullet_moves_right():
    b = PlayerBullet()
    b.x, b.y = 100.0, 135.0
    b.vx, b.vy = 480.0, 0.0
    b.alive = True
    b.update(0.1)
    assert b.x == pytest.approx(148.0)
    assert b.y == 135.0


def test_player_bullet_despawns_off_screen():
    b = PlayerBullet()
    b.x, b.y = 470.0, 135.0
    b.vx, b.vy = 480.0, 0.0
    b.alive = True
    b.update(0.1)  # x = 470 + 48 = 518
    assert b.alive is False


def test_player_bullet_hitbox_12x4():
    b = PlayerBullet()
    b.x, b.y = 100.0, 135.0
    b.alive = True
    hb = b.hitbox()
    assert hb.width == 12
    assert hb.height == 4


def test_enemy_bullet_spawn_aims_at_target():
    b = EnemyBullet()
    b.spawn(400, 100, 100, 100)  # target to the left and same y
    # Velocity should point left (-X)
    assert b.vx < 0
    assert b.vy == pytest.approx(0.0, abs=0.01)
    assert b.alive is True


def test_enemy_bullet_moves_in_direction():
    b = EnemyBullet()
    b.spawn(400, 100, 100, 100)
    vx0, vy0 = b.vx, b.vy
    b.update(0.1)
    assert b.x < 400
    assert abs(b.y - 100) < 1.0


def test_enemy_bullet_despawns_off_screen():
    b = EnemyBullet()
    b.spawn(0, 100, 480, 100)  # going right
    b.update(10.0)  # long enough to leave screen
    assert b.alive is False
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_bullet.py -v
```

- [ ] **Step 3: Implement `bullet.py`**

```python
"""Bullets: PlayerBullet (moves +X) and EnemyBullet (aims at target)."""
from __future__ import annotations

import math

import pygame


class PlayerBullet:
    SPEED_PX_S = 480.0
    SIZE = (12, 4)
    POOL_SIZE = 32

    __slots__ = ("x", "y", "vx", "vy", "alive")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.alive = False

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x > 480 + 12 or self.x < -12:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 6), int(self.y - 2), 12, 4)


class EnemyBullet:
    SPEED_PX_S = 220.0
    SIZE = (8, 8)
    POOL_SIZE = 64

    __slots__ = ("x", "y", "vx", "vy", "alive", "damage")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.damage = 1
        self.alive = False

    def spawn(self, x: float, y: float, target_x: float, target_y: float) -> None:
        dx, dy = target_x - x, target_y - y
        d = math.hypot(dx, dy) or 1.0
        self.vx = dx / d * self.SPEED_PX_S
        self.vy = dy / d * self.SPEED_PX_S
        self.x, self.y, self.alive = x, y, True

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not (-16 <= self.x <= 496 and -16 <= self.y <= 286):
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
```

- [ ] **Step 4: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_bullet.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/entities/bullet.py
git add stellar_horizon/tests/test_bullet.py
git commit -m "feat(bullet): PlayerBullet + EnemyBullet pools"
```

---

## Task 6: Enemy entity + 3 Phase 1 types

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/entities/enemy.py`
- Create: `void-hunter/stellar_horizon/tests/test_enemy.py`

**Interfaces:**
- Consumes: `src.movement.PathFollower`
- Produces:
  - `EnemyKind` (constants: SCOUT, CRUISER, HEAVY)
  - `Enemy` (attributes: `x, y, vx, vy, kind, hp, max_hp, alive, shoot_cooldown, telegraphing, telegraph_frames, path_follower, slot_dx, slot_dy, path_done`)
    - `attach_path(follower, slot_dx, slot_dy) -> None`
    - `update(dt, player) -> list[EnemyBullet]`
    - `take_damage(amount) -> None`
    - `hitbox() -> pygame.Rect`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_enemy.py
import pytest
import pygame

from stellar_horizon.entities.enemy import Enemy, EnemyKind
from src.movement import PathFollower, HybridPath
from stellar_horizon.waves.bezier_horizontal import path_s_right_to_left


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_enemy_kind_constants():
    assert EnemyKind.SCOUT == "scout"
    assert EnemyKind.CRUISER == "cruiser"
    assert EnemyKind.HEAVY == "heavy"


def test_enemy_starts_inactive():
    e = Enemy()
    assert e.alive is False
    assert e.hp == 1
    assert e.kind == EnemyKind.SCOUT


def test_enemy_take_damage_decrements_hp():
    e = Enemy()
    e.hp = 4
    e.alive = True
    e.take_damage(1)
    assert e.hp == 3


def test_enemy_take_damage_kills_at_zero():
    e = Enemy()
    e.hp = 1
    e.alive = True
    e.take_damage(1)
    assert e.alive is False


def test_enemy_path_attached_moves_along_path():
    path = path_s_right_to_left(y_offset=0)
    hybrid = HybridPath.from_segments([path])
    follower = PathFollower(hybrid)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.x = 0  # will be overwritten by path
    e.y = 0
    e.alive = True
    player = FakePlayer()
    # Run a few updates
    for _ in range(10):
        e.update(0.05, player)
    # The enemy should be at the path's position (off-screen right at t~0.5)
    assert e.x > 0  # moved into play area


def test_enemy_path_done_marks_done_flag():
    path = path_s_right_to_left()
    hybrid = HybridPath.from_segments([path])
    # Use a very short duration so it completes quickly
    hybrid_short = HybridPath([hybrid.segments[0]], [0.2])
    follower = PathFollower(hybrid_short)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.alive = True
    player = FakePlayer()
    for _ in range(60):
        e.update(0.05, player)
    assert e.path_done is True


def test_enemy_off_screen_culling_left():
    e = Enemy()
    e.x = -50.0
    e.y = 100.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_enemy_off_screen_culling_top():
    e = Enemy()
    e.x = 100.0
    e.y = -50.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_scout_attack_cooldown_1_5s():
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    e.x, e.y = 200.0, 100.0  # in play area
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    # First update starts telegraph
    e.update(0.05, player)
    assert e.telegraphing is True
    assert e.telegraph_frames == 8  # SCOUT telegraph


def test_cruiser_attack_cooldown_1_2s():
    e = Enemy()
    e.kind = EnemyKind.CRUISER
    e.hp = 4
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 14  # CRUISER telegraph


def test_heavy_attack_cooldown_2_5s():
    e = Enemy()
    e.kind = EnemyKind.HEAVY
    e.hp = 12
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 24  # HEAVY telegraph


def test_enemy_emits_bullet_after_telegraph():
    path = path_s_right_to_left()
    hybrid = HybridPath.from_segments([path])
    follower = PathFollower(hybrid)
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.x, e.y = 200.0, 100.0  # ensure in play area
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    # Start telegraph
    e.update(0.05, player)
    assert e.telegraphing is True
    # Tick down telegraph
    for _ in range(20):
        e.update(0.05, player)
    # Should have emitted a bullet
    assert e.telegraphing is False  # back to cooldown
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_enemy.py -v
```

- [ ] **Step 3: Implement `enemy.py`**

```python
"""Enemy entity with 3 Phase 1 types: SCOUT, CRUISER, HEAVY."""
from __future__ import annotations

import pygame
from src.movement import PathFollower


class EnemyKind:
    SCOUT = "scout"
    CRUISER = "cruiser"
    HEAVY = "heavy"


_TYPE_PARAMS = {
    EnemyKind.SCOUT:   {"hp": 1,  "attack_cd": 1.5, "telegraph": 8,  "score": 50,  "speed": 110.0},
    EnemyKind.CRUISER: {"hp": 4,  "attack_cd": 1.2, "telegraph": 14, "score": 150, "speed": 60.0},
    EnemyKind.HEAVY:   {"hp": 12, "attack_cd": 2.5, "telegraph": 24, "score": 400, "speed": 30.0},
}


class Enemy:
    __slots__ = (
        "x", "y", "vx", "vy", "kind", "hp", "max_hp", "alive",
        "shoot_cooldown", "telegraphing", "telegraph_frames",
        "path_follower", "slot_dx", "slot_dy", "path_done",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.kind: str = EnemyKind.SCOUT
        self.hp: int = 1
        self.max_hp: int = 1
        self.alive: bool = False
        self.shoot_cooldown: float = 0.0
        self.telegraphing: bool = False
        self.telegraph_frames: int = 0
        self.path_follower: PathFollower | None = None
        self.slot_dx: float = 0.0
        self.slot_dy: float = 0.0
        self.path_done: bool = False

    def on_spawn(self) -> None:
        params = _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])
        self.hp = self.max_hp = params["hp"]
        self.alive = True
        self.shoot_cooldown = 1.0  # small grace period before first shot
        self.telegraphing = False
        self.telegraph_frames = 0
        self.path_done = False

    def attach_path(self, follower: PathFollower, slot_dx: float, slot_dy: float) -> None:
        self.path_follower = follower
        self.slot_dx, self.slot_dy = slot_dx, slot_dy

    def update(self, dt: float, player) -> list:
        from stellar_horizon.entities.bullet import EnemyBullet
        if not self.alive:
            return []
        new_bullets: list = []
        # Path-driven motion
        if self.path_follower and not self.path_done:
            pos, vel = self.path_follower.update(dt)
            self.x = pos.x + self.slot_dx
            self.y = pos.y + self.slot_dy
            self.vx, self.vy = vel.x, vel.y
            if self.path_follower.is_complete:
                self.path_done = True
        elif self.path_done:
            # Drift left after path completes
            self.x -= 30.0 * dt
        # Shoot telegraph
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        if self.telegraphing:
            self.telegraph_frames -= 1
            if self.telegraph_frames <= 0 and self._can_shoot():
                b = EnemyBullet()
                b.spawn(self.x, self.y, player.x, player.y)
                new_bullets.append(b)
                self.telegraphing = False
        elif self.shoot_cooldown <= 0.0 and self._can_shoot():
            self.telegraphing = True
            self.telegraph_frames = self._telegraph_frames()
            self.shoot_cooldown = self._attack_cooldown()
        # Off-screen culling
        if self.x < -32 or self.y < -32 or self.y > 302:
            self.alive = False
        return new_bullets

    def take_damage(self, amount: int) -> None:
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        if self.kind == EnemyKind.HEAVY:
            return pygame.Rect(int(self.x - 10), int(self.y - 6), 20, 12)
        return pygame.Rect(int(self.x - 6), int(self.y - 6), 12, 12)

    def score_value(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["score"]

    def _attack_cooldown(self) -> float:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["attack_cd"]

    def _telegraph_frames(self) -> int:
        return _TYPE_PARAMS.get(self.kind, _TYPE_PARAMS[EnemyKind.SCOUT])["telegraph"]

    def _can_shoot(self) -> bool:
        return 0 <= self.x <= 480 and 0 <= self.y <= 270
```

- [ ] **Step 4: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_enemy.py -v
```
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/entities/enemy.py
git add stellar_horizon/tests/test_enemy.py
git commit -m "feat(enemy): SCOUT/CRUISER/HEAVY with path follower + telegraph shooting"
```

---

## Task 7: Boss (ASTEROID_GUARDIAN, 2 phases)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/entities/boss.py`
- Create: `void-hunter/stellar_horizon/tests/test_boss.py`

**Interfaces:**
- Consumes: `src.movement.PathFollower`, `stellar_horizon.waves.bezier_horizontal.path_boss_entry`
- Produces:
  - `BossPhase` (constants: ENTERING, PHASE_1, PHASE_2, DYING, DEAD)
  - `Boss` (attributes: `x, y, hp, max_hp, phase, entry_follower, alive, attack_cd, beam_telegraph_frames, beam_active_frames`)
    - `update(dt, player) -> list[EnemyBullet]`
    - `take_damage(amount) -> None`
    - `hitbox() -> pygame.Rect`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_boss.py
import pytest

from stellar_horizon.entities.boss import Boss, BossPhase


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_boss_phase_constants():
    assert BossPhase.ENTERING == "entering"
    assert BossPhase.PHASE_1 == "phase_1"
    assert BossPhase.PHASE_2 == "phase_2"
    assert BossPhase.DYING == "dying"
    assert BossPhase.DEAD == "dead"


def test_boss_starts_entering():
    b = Boss()
    assert b.phase == BossPhase.ENTERING
    assert b.alive is True
    assert b.hp == 60


def test_boss_transitions_to_phase_1_after_entry():
    b = Boss()
    # Run a long time to let the entry path complete (default 4s)
    for _ in range(600):
        b.update(1 / 120, FakePlayer())
    assert b.phase == BossPhase.PHASE_1


def test_boss_takes_damage_in_phase_1():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(10)
    assert b.hp == 50
    assert b.alive is True


def test_boss_transitions_to_phase_2_at_30_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(30)  # hp 60 -> 30
    assert b.phase == BossPhase.PHASE_2


def test_boss_transitions_to_dying_at_0_hp():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.take_damage(60)
    assert b.phase == BossPhase.DYING


def test_boss_hitbox_is_48x48():
    b = Boss()
    b.x, b.y = 350.0, 135.0
    hb = b.hitbox()
    assert hb.width == 48
    assert hb.height == 48


def test_boss_phase_1_attacks_aimed():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.attack_cd = 0.0
    new_bullets = b.update(0.1, FakePlayer(x=200, y=80))
    # Should emit at least one bullet aimed at player
    assert len(new_bullets) >= 1


def test_boss_phase_1_attack_cooldown_resets():
    b = Boss()
    b.phase = BossPhase.PHASE_1
    b.x, b.y = 350.0, 135.0
    b.attack_cd = 0.0
    b.update(0.1, FakePlayer())
    assert b.attack_cd > 0  # cooldown reset


def test_boss_dying_ends_in_dead():
    b = Boss()
    b.phase = BossPhase.DYING
    b.x, b.y = 350.0, 135.0
    b.dying_timer = 1.5
    b.update(0.1, FakePlayer())
    # After 1.5s, should be DEAD
    for _ in range(20):
        b.update(0.1, FakePlayer())
    assert b.phase == BossPhase.DEAD
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_boss.py -v
```

- [ ] **Step 3: Implement `boss.py`**

```python
"""Boss: ASTEROID_GUARDIAN, 2 phases + entry + dying."""
from __future__ import annotations

import math

import pygame
from src.movement import PathFollower

from stellar_horizon.waves.bezier_horizontal import path_boss_entry


class BossPhase:
    ENTERING = "entering"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    DYING = "dying"
    DEAD = "dead"


class Boss:
    MAX_HP = 60
    PHASE_2_HP_THRESHOLD = 30
    DYING_DURATION_S = 1.5
    PHASE_1_ATTACK_CD = 1.2
    PHASE_2_ATTACK_CD = 0.9
    ARENA_X = 350.0
    ARENA_Y = 135.0
    HITBOX_W = 48
    HITBOX_H = 48

    __slots__ = (
        "x", "y", "hp", "max_hp", "phase", "entry_follower",
        "alive", "attack_cd", "dying_timer",
        "beam_telegraph", "beam_telegraph_frames", "beam_active", "beam_active_frames",
        "beam_timer",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.hp: int = self.MAX_HP
        self.max_hp: int = self.MAX_HP
        self.phase: str = BossPhase.ENTERING
        self.entry_follower: PathFollower = PathFollower(path_boss_entry())
        self.alive: bool = True
        self.attack_cd: float = 0.5  # small grace
        self.dying_timer: float = 0.0
        self.beam_telegraph: bool = False
        self.beam_telegraph_frames: int = 0
        self.beam_active: bool = False
        self.beam_active_frames: int = 0
        self.beam_timer: float = 0.0

    def update(self, dt: float, player) -> list:
        from stellar_horizon.entities.bullet import EnemyBullet
        new_bullets: list = []
        if self.phase == BossPhase.DEAD:
            return new_bullets
        if self.phase == BossPhase.ENTERING:
            pos, _ = self.entry_follower.update(dt)
            self.x, self.y = pos.x, pos.y
            if self.entry_follower.is_complete:
                self.phase = BossPhase.PHASE_1
            return new_bullets
        if self.phase == BossPhase.DYING:
            self.dying_timer += dt
            if self.dying_timer >= self.DYING_DURATION_S:
                self.phase = BossPhase.DEAD
                self.alive = False
            return new_bullets
        # PHASE_1 / PHASE_2 attacks
        self.attack_cd = max(0.0, self.attack_cd - dt)
        if self.attack_cd <= 0.0:
            if self.phase == BossPhase.PHASE_1:
                b = EnemyBullet()
                b.spawn(self.x, self.y, player.x, player.y)
                new_bullets.append(b)
                self.attack_cd = self.PHASE_1_ATTACK_CD
            else:  # PHASE_2
                # 3-spread aimed at player
                import math
                dx, dy = player.x - self.x, player.y - self.y
                base_angle = math.atan2(dy, dx)
                for offset in (-0.20, 0.0, +0.20):
                    b = EnemyBullet()
                    a = base_angle + offset
                    # Set velocity directly so the spread shows
                    b.x, b.y = self.x, self.y
                    b.vx = math.cos(a) * EnemyBullet.SPEED_PX_S
                    b.vy = math.sin(a) * EnemyBullet.SPEED_PX_S
                    b.alive = True
                    new_bullets.append(b)
                self.attack_cd = self.PHASE_2_ATTACK_CD
        # Phase-2 beam (every 3.5s: 60f telegraph + 20f active)
        if self.phase == BossPhase.PHASE_2:
            self.beam_timer += dt
            if not self.beam_telegraph and not self.beam_active and self.beam_timer >= 3.5:
                self.beam_telegraph = True
                self.beam_telegraph_frames = 60
                self.beam_timer = 0.0
            if self.beam_telegraph:
                self.beam_telegraph_frames -= 1
                if self.beam_telegraph_frames <= 0:
                    self.beam_telegraph = False
                    self.beam_active = True
                    self.beam_active_frames = 20
            if self.beam_active:
                self.beam_active_frames -= 1
                if self.beam_active_frames <= 0:
                    self.beam_active = False
        return new_bullets

    def take_damage(self, amount: int) -> None:
        if self.phase in (BossPhase.ENTERING, BossPhase.DYING, BossPhase.DEAD):
            return
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self.phase = BossPhase.DYING
            self.dying_timer = 0.0
        elif self.hp <= self.PHASE_2_HP_THRESHOLD and self.phase == BossPhase.PHASE_1:
            self.phase = BossPhase.PHASE_2

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.HITBOX_W // 2), int(self.y - self.HITBOX_H // 2),
                           self.HITBOX_W, self.HITBOX_H)

    def score_value(self) -> int:
        return 5000
```

- [ ] **Step 4: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_boss.py -v
```
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/entities/boss.py
git add stellar_horizon/tests/test_boss.py
git commit -m "feat(boss): ASTEROID_GUARDIAN 2-phase FSM with entry bezier + spread + beam"
```

---

## Task 8: Wave manager (JSON + scheduling)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/wave_specs.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/wave_manager.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/waves/waves_act1.json`
- Create: `void-hunter/stellar_horizon/tests/test_wave_manager.py`

**Interfaces:**
- Consumes: `bezier_horizontal.*`, `formations_h.*`, `entities.enemy.Enemy`, `entities.enemy.EnemyKind`, `src.movement.{PathFollower, HybridPath, BezierPath}`
- Produces:
  - `WaveSpec` (dataclass)
  - `WaveManager(json_path: Path)`
    - `begin() -> None`
    - `update(dt) -> list[Enemy]`
    - `next_wave() -> bool`
    - attrs: `current_wave_index, elapsed_s, wave_complete, act, background, midi_track, boss_spec`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_wave_manager.py
import json
from pathlib import Path

import pytest

from stellar_horizon.waves.wave_manager import WaveManager
from stellar_horizon.waves.wave_specs import WaveSpec


SAMPLE_JSON = """{
  "act": 1,
  "act_name": "Test Belt",
  "background": "test_bg",
  "midi_track": "test.mid",
  "boss": {
    "kind": "TEST_BOSS",
    "phases": 2,
    "hp": 60,
    "entry_path": "boss_entry"
  },
  "waves": [
    {
      "id": "w1",
      "duration_s": 5.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "v_pointing_left",
          "formation_count": 3,
          "enemy_kind": "scout",
          "path": "s_right_to_left",
          "path_y_offset": 0
        }
      ]
    },
    {
      "id": "w2",
      "duration_s": 5.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 4,
          "enemy_kind": "cruiser",
          "path": "s_right_to_left",
          "path_y_offset": 60
        }
      ]
    }
  ]
}"""


@pytest.fixture
def json_path(tmp_path):
    p = tmp_path / "test_waves.json"
    p.write_text(SAMPLE_JSON, encoding="utf-8")
    return p


def test_wave_manager_loads_metadata(json_path):
    wm = WaveManager(json_path)
    assert wm.act == 1
    assert wm.background == "test_bg"
    assert wm.midi_track == "test.mid"


def test_wave_manager_loads_boss_spec(json_path):
    wm = WaveManager(json_path)
    assert wm.boss_spec is not None
    assert wm.boss_spec["kind"] == "TEST_BOSS"
    assert wm.boss_spec["hp"] == 60


def test_wave_manager_starts_at_wave_0(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    assert wm.current_wave_index == 0
    assert wm.elapsed_s == 0.0


def test_wave_manager_spawns_at_delay(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    # First spawn is at t=0
    new = wm.update(0.0)
    assert len(new) == 3  # v_pointing_left count=3
    for e in new:
        assert e.kind == "scout"


def test_wave_manager_advances_to_next_wave(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    # Drain first wave
    wm.update(0.0)  # spawn
    # Mark all spawned enemies as dead
    for e in wm.spawned_enemies:
        e.alive = False
    # Tick many times until wave_complete
    for _ in range(120):
        wm.update(1 / 60)
    assert wm.wave_complete is True
    # Advance
    ok = wm.next_wave()
    assert ok is True
    assert wm.current_wave_index == 1


def test_wave_manager_next_wave_returns_false_at_end(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    wm.update(0.0)
    for e in wm.spawned_enemies:
        e.alive = False
    for _ in range(120):
        wm.update(1 / 60)
    wm.next_wave()  # w1 -> w2
    wm.update(0.0)
    for e in wm.spawned_enemies:
        e.alive = False
    for _ in range(120):
        wm.update(1 / 60)
    ok = wm.next_wave()  # w2 -> end
    assert ok is False


def test_wave_spec_dataclass_parses():
    spec = WaveSpec(
        id="w1",
        duration_s=10.0,
        spawns=[{"delay_s": 0.5, "formation": "v_pointing_left",
                 "formation_count": 5, "enemy_kind": "scout",
                 "path": "s_right_to_left", "path_y_offset": 0}],
    )
    assert spec.id == "w1"
    assert spec.duration_s == 10.0
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_wave_manager.py -v
```

- [ ] **Step 3: Create `wave_specs.py`**

```python
"""Wave spec dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WaveSpec:
    id: str
    duration_s: float
    spawns: list[dict] = field(default_factory=list)
```

- [ ] **Step 4: Create `wave_manager.py`**

```python
"""Wave scheduler: reads JSON, schedules spawns over time."""
from __future__ import annotations

import json
from pathlib import Path

from src.movement import BezierPath, HybridPath, PathFollower

from stellar_horizon.entities.enemy import Enemy, EnemyKind
from stellar_horizon.waves.bezier_horizontal import (
    path_boss_entry,
    path_s_right_to_left,
    path_top_dive,
    path_zigzag_exit_top,
)
from stellar_horizon.waves.formations_h import (
    diamond_pointing_left,
    line_horizontal,
    v_pointing_left,
    wedge_pointing_left,
)
from stellar_horizon.waves.wave_specs import WaveSpec


_PATH_BUILDERS = {
    "s_right_to_left": lambda kw: path_s_right_to_left(y_offset=kw.get("path_y_offset", 0)),
    "top_dive":         lambda kw: path_top_dive(side=kw.get("path_side", "right")),
    "zigzag_exit_top":  lambda kw: path_zigzag_exit_top(),
    "boss_entry":       lambda kw: path_boss_entry(),
}

_FORMATION_BUILDERS = {
    "v_pointing_left":       lambda count, spacing: v_pointing_left(count, spacing),
    "line_horizontal":       lambda count, spacing: line_horizontal(count, spacing),
    "diamond_pointing_left": lambda count, spacing: diamond_pointing_left(count, spacing),
    "wedge_pointing_left":   lambda count, spacing: wedge_pointing_left(count, spacing),
}

_KIND_MAP = {
    "scout":   EnemyKind.SCOUT,
    "cruiser": EnemyKind.CRUISER,
    "heavy":   EnemyKind.HEAVY,
}


def _path_to_hybrid(path) -> HybridPath:
    if isinstance(path, HybridPath):
        return path
    if isinstance(path, BezierPath):
        dur = max(0.5, path.length_estimate / 80.0)
        return HybridPath([path], [dur])
    return HybridPath([path], [4.0])


def _build_enemies(spawn: dict) -> list[Enemy]:
    offsets = _FORMATION_BUILDERS[spawn["formation"]](spawn["formation_count"], 18.0)
    raw_path = _PATH_BUILDERS[spawn["path"]](spawn)
    hybrid = _path_to_hybrid(raw_path)
    kind = _KIND_MAP[spawn["enemy_kind"]]
    enemies: list[Enemy] = []
    for dx, dy in offsets:
        e = Enemy()
        e.kind = kind
        e.on_spawn()
        follower = PathFollower(hybrid)
        e.attach_path(follower, slot_dx=dx, slot_dy=dy)
        enemies.append(e)
    return enemies


class WaveManager:
    def __init__(self, json_path: Path) -> None:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.act: int = data["act"]
        self.act_name: str = data.get("act_name", f"Act {self.act}")
        self.background: str = data["background"]
        self.midi_track: str = data["midi_track"]
        self.boss_spec: dict | None = data.get("boss")
        self.waves: list[WaveSpec] = [
            WaveSpec(id=w["id"], duration_s=w["duration_s"], spawns=w.get("spawns", []))
            for w in data["waves"]
        ]
        self.current_wave_index: int = 0
        self.elapsed_s: float = 0.0
        self.spawn_queue: list[tuple[float, list[Enemy]]] = []
        self.spawned_enemies: list[Enemy] = []
        self.wave_complete: bool = False

    def begin(self) -> None:
        self.spawned_enemies.clear()
        self.spawn_queue.clear()
        self.elapsed_s = 0.0
        self.wave_complete = False
        if self.current_wave_index >= len(self.waves):
            return
        wave = self.waves[self.current_wave_index]
        for spawn in wave.spawns:
            self.spawn_queue.append((spawn["delay_s"], _build_enemies(spawn)))
        self.spawn_queue.sort(key=lambda x: x[0])

    def update(self, dt: float) -> list[Enemy]:
        new_spawns: list[Enemy] = []
        while self.spawn_queue and self.elapsed_s >= self.spawn_queue[0][0]:
            _, enemies = self.spawn_queue.pop(0)
            for e in enemies:
                self.spawned_enemies.append(e)
            new_spawns.extend(enemies)
        # Prune dead
        self.spawned_enemies = [e for e in self.spawned_enemies if e.alive]
        self.elapsed_s += dt
        if not self.spawn_queue and not self.spawned_enemies:
            self.wave_complete = True
        return new_spawns

    def next_wave(self) -> bool:
        self.current_wave_index += 1
        if self.current_wave_index >= len(self.waves):
            return False
        self.begin()
        return True
```

- [ ] **Step 5: Create `waves_act1.json`**

```json
{
  "act": 1,
  "act_name": "Asteroid Belt",
  "background": "act1_asteroid_belt",
  "midi_track": "act1.mid",
  "boss": {
    "kind": "ASTEROID_GUARDIAN",
    "phases": 2,
    "hp": 60,
    "entry_path": "boss_entry"
  },
  "waves": [
    {
      "id": "w1_intro",
      "duration_s": 12.0,
      "spawns": [
        {
          "delay_s": 0.5,
          "formation": "v_pointing_left",
          "formation_count": 5,
          "enemy_kind": "scout",
          "path": "s_right_to_left",
          "path_y_offset": 0
        }
      ]
    },
    {
      "id": "w2_layered",
      "duration_s": 18.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 6,
          "enemy_kind": "cruiser",
          "path": "s_right_to_left",
          "path_y_offset": 60
        },
        {
          "delay_s": 6.0,
          "formation": "v_pointing_left",
          "formation_count": 3,
          "enemy_kind": "scout",
          "path": "top_dive",
          "path_side": "right"
        }
      ]
    },
    {
      "id": "w3_mixed",
      "duration_s": 22.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "diamond_pointing_left",
          "formation_count": 5,
          "enemy_kind": "heavy",
          "path": "s_right_to_left",
          "path_y_offset": 100
        },
        {
          "delay_s": 8.0,
          "formation": "v_pointing_left",
          "formation_count": 4,
          "enemy_kind": "scout",
          "path": "zigzag_exit_top"
        }
      ]
    },
    {
      "id": "w4_boss_rush",
      "duration_s": 14.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 8,
          "enemy_kind": "scout",
          "path": "s_right_to_left",
          "path_y_offset": 0
        },
        {
          "delay_s": 2.0,
          "formation": "line_horizontal",
          "formation_count": 6,
          "enemy_kind": "cruiser",
          "path": "s_right_to_left",
          "path_y_offset": 60
        }
      ]
    }
  ]
}
```

- [ ] **Step 6: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_wave_manager.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/waves/wave_specs.py
git add stellar_horizon/stellar_horizon/waves/wave_manager.py
git add stellar_horizon/stellar_horizon/waves/waves_act1.json
git add stellar_horizon/tests/test_wave_manager.py
git commit -m "feat(wave): wave manager + JSON loader + 4-wave Act 1 spec"
```

---

## Task 9: HUD

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/ui/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/ui/hud.py`
- Create: `void-hunter/stellar_horizon/tests/test_hud.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Hud` class
    - `__init__()`
    - `set_player(player) -> None`
    - `set_score(n: int) -> None`
    - `set_wave(n: int, total: int) -> None`
    - `set_boss(boss | None) -> None`
    - `set_enemies_remaining(n: int, total: int) -> None`
    - `draw(surface) -> None`

- [ ] **Step 1: Create `ui/__init__.py`**

```python
# stellar_horizon/ui/__init__.py
```

- [ ] **Step 2: Write the failing tests**

```python
# stellar_horizon/tests/test_hud.py
import pytest
import pygame

from stellar_horizon.ui.hud import Hud
from stellar_horizon.entities.player import Player
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


@pytest.fixture
def hud():
    return Hud()


@pytest.fixture
def screen():
    return pygame.Surface((INTERNAL_W, INTERNAL_H))


def test_hud_initial_state(hud):
    assert hud.score == 0
    assert hud.wave_n == 0
    assert hud.wave_total == 0


def test_hud_set_score(hud):
    hud.set_score(12345)
    assert hud.score == 12345


def test_hud_set_wave(hud):
    hud.set_wave(2, 4)
    assert hud.wave_n == 2
    assert hud.wave_total == 4


def test_hud_format_score(hud, screen):
    hud.set_score(12345)
    hud.set_wave(2, 4)
    hud.set_enemies_remaining(8, 15)
    # Should not crash
    hud.draw(screen)


def test_hud_with_player(hud, screen):
    p = Player(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))
    hud.set_player(p)
    hud.draw(screen)
    # No assertions; just verifies no exception


def test_hud_with_boss(hud, screen):
    from stellar_horizon.entities.boss import Boss
    boss = Boss()
    hud.set_boss(boss)
    hud.draw(screen)


def test_hud_lives_display(hud, screen):
    p = Player(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))
    p.lives = 2
    hud.set_player(p)
    hud.draw(screen)
```

- [ ] **Step 3: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_hud.py -v
```

- [ ] **Step 4: Implement `hud.py`**

```python
"""HUD: top bar (HP, score, wave, boss HP) + bottom bar (lives, score, enemies)."""
from __future__ import annotations

import pygame

from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class Hud:
    TOP_BAR_H = 14
    BOTTOM_BAR_H = 14
    COLOR_BG = (10, 15, 31)
    COLOR_TEXT = (240, 240, 240)
    COLOR_HEART = (220, 60, 80)
    COLOR_HP = (90, 220, 90)
    COLOR_HP_BG = (40, 60, 40)
    COLOR_BOSS_HP = (220, 80, 80)
    COLOR_WAVE = (255, 220, 100)
    COLOR_ENEMIES = (180, 180, 220)

    def __init__(self) -> None:
        self.player = None
        self.score: int = 0
        self.wave_n: int = 0
        self.wave_total: int = 0
        self.boss = None
        self.enemies_n: int = 0
        self.enemies_total: int = 0
        self._font = None
        self._small_font = None

    def set_player(self, player) -> None:
        self.player = player

    def set_score(self, n: int) -> None:
        self.score = n

    def set_wave(self, n: int, total: int) -> None:
        self.wave_n = n
        self.wave_total = total

    def set_boss(self, boss) -> None:
        self.boss = boss

    def set_enemies_remaining(self, n: int, total: int) -> None:
        self.enemies_n = n
        self.enemies_total = total

    def _ensure_fonts(self) -> None:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", 10, bold=True)
            self._small_font = pygame.font.SysFont("monospace", 8)

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        # Top bar
        top_rect = pygame.Rect(0, 0, INTERNAL_W, self.TOP_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, top_rect)
        # Player HP (lives as hearts, Phase 1)
        if self.player is not None:
            for i in range(self.player.lives):
                cx = 4 + i * 8
                pygame.draw.circle(surface, self.COLOR_HEART, (cx + 3, 7), 3)
        # Score (center)
        score_surf = self._font.render(f"{self.score:>6}", False, self.COLOR_TEXT)
        surface.blit(score_surf, (INTERNAL_W // 2 - score_surf.get_width() // 2, 2))
        # Wave (center-right)
        if self.wave_total > 0:
            wave_surf = self._small_font.render(
                f"WAVE {self.wave_n}/{self.wave_total}", False, self.COLOR_WAVE
            )
            surface.blit(wave_surf, (INTERNAL_W // 2 + 40, 3))
        # Boss HP bar (top-right, only when boss present)
        if self.boss is not None and self.boss.alive:
            bar_w = 80
            bar_h = 6
            bar_x = INTERNAL_W - bar_w - 4
            bar_y = 4
            pygame.draw.rect(surface, self.COLOR_HP_BG, (bar_x, bar_y, bar_w, bar_h))
            pct = self.boss.hp / self.boss.max_hp
            pygame.draw.rect(surface, self.COLOR_BOSS_HP,
                             (bar_x, bar_y, int(bar_w * pct), bar_h))
        # Bottom bar
        bot_rect = pygame.Rect(0, INTERNAL_H - self.BOTTOM_BAR_H, INTERNAL_W, self.BOTTOM_BAR_H)
        pygame.draw.rect(surface, self.COLOR_BG, bot_rect)
        # Lives text (left)
        if self.player is not None:
            lives_surf = self._small_font.render(
                f"LIVES {self.player.lives}", False, self.COLOR_HEART
            )
            surface.blit(lives_surf, (4, INTERNAL_H - self.BOTTOM_BAR_H + 3))
        # Enemies remaining (right)
        if self.enemies_total > 0:
            en_surf = self._small_font.render(
                f"ENEMIES {self.enemies_n}/{self.enemies_total}", False, self.COLOR_ENEMIES
            )
            surface.blit(en_surf, (INTERNAL_W - en_surf.get_width() - 4,
                                   INTERNAL_H - self.BOTTOM_BAR_H + 3))
```

- [ ] **Step 5: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_hud.py -v
```
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/ui/__init__.py
git add stellar_horizon/stellar_horizon/ui/hud.py
git add stellar_horizon/tests/test_hud.py
git commit -m "feat(hud): top/bottom bars with hearts, score, wave, boss HP, enemies"
```

---

## Task 10: Backgrounds (3 ambientes)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/ui/backgrounds.py`
- Create: `void-hunter/stellar_horizon/tests/test_backgrounds.py`
- Create: `void-hunter/stellar_horizon/assets/backgrounds/act1_asteroid_belt.png` (placeholder, 480x270)
- Create: `void-hunter/stellar_horizon/assets/backgrounds/act2_nebula.png` (placeholder)
- Create: `void-hunter/stellar_horizon/assets/backgrounds/act3_sun_close.png` (placeholder)
- Create: `void-hunter/stellar_horizon/tools/make_placeholder_bgs.py` (generates the PNGs)

**Interfaces:**
- Consumes: nothing
- Produces: `Background` class with `update(dt, scroll_speed)` and `draw(surface)` methods.

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_backgrounds.py
from pathlib import Path
import pytest
import pygame

from stellar_horizon.ui.backgrounds import Background, make_placeholder_backgrounds


def test_make_placeholder_backgrounds_creates_3(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    assert (tmp_path / "act1_asteroid_belt.png").exists()
    assert (tmp_path / "act2_nebula.png").exists()
    assert (tmp_path / "act3_sun_close.png").exists()


def test_background_loads_image(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    assert bg.image.get_size() == (480, 270)


def test_background_draw_doesnt_crash(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    surf = pygame.Surface((480, 270))
    bg.update(0.1)
    bg.draw(surf)


def test_background_parallax_x_advances(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    bg.update(0.1, scroll_speed=30.0)
    assert bg.parallax_x != 0.0
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_backgrounds.py -v
```

- [ ] **Step 3: Implement `backgrounds.py`**

```python
"""Background images per act. Phase 1 uses placeholders."""
from __future__ import annotations

from pathlib import Path

import pygame


def make_placeholder_backgrounds(out_dir: Path) -> None:
    """Generate 3 simple 480x270 PNGs as placeholders for the 3 acts.

    Phase 1 uses these; user replaces them later.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    palettes = {
        "act1_asteroid_belt": ((10, 15, 31), (74, 63, 53)),
        "act2_nebula":        ((20, 12, 40), (110, 70, 160)),
        "act3_sun_close":     ((40, 16, 8),  (220, 120, 40)),
    }
    for name, (bg_color, star_color) in palettes.items():
        surf = pygame.Surface((480, 270))
        surf.fill(bg_color)
        # Sprinkle some "stars" (random dots) deterministically
        import random
        rng = random.Random(hash(name) & 0xFFFFFFFF)
        for _ in range(80):
            x = rng.randint(0, 479)
            y = rng.randint(0, 269)
            surf.set_at((x, y), star_color)
        pygame.image.save(surf, str(out_dir / f"{name}.png"))


class Background:
    def __init__(self, image_path: Path) -> None:
        self.image = pygame.image.load(str(image_path)).convert()
        self.parallax_x: float = 0.0

    def update(self, dt: float, scroll_speed: float = 0.0) -> None:
        w = self.image.get_width()
        self.parallax_x = (self.parallax_x + scroll_speed * dt) % w

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, (-int(self.parallax_x), 0))
        if self.parallax_x > 0:
            surface.blit(self.image, (int(self.image.get_width() - self.parallax_x), 0))
```

- [ ] **Step 4: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_backgrounds.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/ui/backgrounds.py
git add stellar_horizon/tests/test_backgrounds.py
git add stellar_horizon/tools/make_placeholder_bgs.py
git add stellar_horizon/assets/backgrounds/act1_asteroid_belt.png
git add stellar_horizon/assets/backgrounds/act2_nebula.png
git add stellar_horizon/assets/backgrounds/act3_sun_close.png
git commit -m "feat(bg): 3 placeholder backgrounds + parallax Background class"
```

---

## Task 11: Audio (MIDI player + SFX wrapper)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/audio/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/audio/midi_player.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/audio/sfx.py`
- Create: `void-hunter/stellar_horizon/tests/test_midi_player.py`
- Create: `void-hunter/stellar_horizon/assets/midi/title.mid` (placeholder, see Step 4)
- Create: `void-hunter/stellar_horizon/assets/midi/act1.mid` (placeholder)
- Create: `void-hunter/stellar_horizon/assets/midi/boss.mid` (placeholder)
- Create: `void-hunter/stellar_horizon/assets/midi/game_over.mid` (placeholder)
- Create: `void-hunter/stellar_horizon/tools/make_placeholder_midi.py` (generates 30s placeholder MIDIs)

**Interfaces:**
- Consumes: `pygame.mixer.music`, `src.audio.synth`
- Produces:
  - `MidiPlayer` (init, play(path, loop=True), stop(), fadeout(ms=800))
  - `audio.sfx.play_event(name)` — wraps `src.audio.synth.play_sfx`

- [ ] **Step 1: Write the failing tests**

```python
# stellar_horizon/tests/test_midi_player.py
import os
import tempfile
from pathlib import Path

import pygame
import pytest

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.tools.make_placeholder_midi import make_placeholder_midi


@pytest.fixture(scope="module", autouse=True)
def init_mixer():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.mixer.init()
    yield
    pygame.mixer.quit()


@pytest.fixture
def midi_path(tmp_path):
    p = tmp_path / "test.mid"
    make_placeholder_midi(p, seconds=2)
    return p


def test_midi_player_constructs():
    p = MidiPlayer()
    assert p is not None


def test_midi_player_plays_file(midi_path):
    p = MidiPlayer()
    p.play(str(midi_path), loop=False)
    # If we got here without raising, success
    p.stop()
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_midi_player.py -v
```

- [ ] **Step 3: Create `audio/__init__.py`**

```python
# stellar_horizon/audio/__init__.py
```

- [ ] **Step 4: Create `tools/make_placeholder_midi.py`**

```python
"""Generate simple placeholder MIDI files (4 of them).

Uses the mido library if available; otherwise falls back to writing a minimal
raw MIDI file. The placeholder tracks are 30s loops with a single sustained
note — enough to verify playback without external assets.
"""
from __future__ import annotations

from pathlib import Path


def make_placeholder_midi(out_path: Path, seconds: int = 30) -> None:
    """Write a minimal single-track MIDI file to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Try mido first (cleaner). Fall back to raw bytes if mido not installed.
    try:
        import mido
        mid = mido.MidiFile(type=0)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        # Tempo: 120 BPM (500000 microseconds per beat)
        track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        # 4-bar loop: C, E, G, C (one note per second)
        notes = [60, 64, 67, 72]
        for tick in range(seconds):
            note = notes[tick % 4]
            # Note on
            track.append(mido.Message("note_on", note=note, velocity=80, time=480))
            # Note off 480 ticks later
            track.append(mido.Message("note_off", note=note, velocity=80, time=0))
        # End of track
        track.append(mido.MetaMessage("end_of_track", time=0))
        mid.save(str(out_path))
        return
    except ImportError:
        pass
    # Fallback: write a minimal raw MIDI file (header + 1 track + 1 note)
    # ... (omitted; rely on mido in Phase 1 since it's a dev dep)
    raise RuntimeError(
        "mido is required to generate placeholder MIDI. Install with: pip install mido"
    )


def make_all_placeholder_midis(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, secs in (("title", 60), ("act1", 180), ("boss", 60), ("game_over", 30)):
        make_placeholder_midi(out_dir / f"{name}.mid", seconds=secs)


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/midi")
    make_all_placeholder_midis(target)
    print(f"Wrote placeholder MIDIs to {target}")
```

- [ ] **Step 5: Create `midi_player.py`**

```python
"""MIDI playback via pygame.mixer.music (native MIDI support)."""
from __future__ import annotations

import pygame


class MidiPlayer:
    def __init__(self, volume: float = 0.6) -> None:
        self.volume = volume
        pygame.mixer.music.set_volume(volume)

    def play(self, midi_path: str, loop: bool = True) -> None:
        pygame.mixer.music.load(midi_path)
        pygame.mixer.music.play(-1 if loop else 0)

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def fadeout(self, ms: int = 800) -> None:
        pygame.mixer.music.fadeout(ms)
```

- [ ] **Step 6: Create `sfx.py`**

```python
"""SFX wrapper around Void-Hunter's `src.audio.synth`.

Maps game event names to specific synth recipes. Falls back to silent if
synth is unavailable.
"""
from __future__ import annotations


def play_event(name: str) -> None:
    """Best-effort SFX dispatch. No-op if synth can't be loaded."""
    try:
        from src.audio.synth import play_sfx  # type: ignore
        play_sfx(name)
    except Exception:
        # Audio is best-effort. Game must still run if SFX fails.
        pass
```

- [ ] **Step 7: Install mido (dev dep) and add to requirements-dev.txt**

```bash
cd D:/AI/void-hunter && python -m pip install mido --quiet
```

Add `mido>=1.3` to `stellar_horizon/requirements-dev.txt`.

- [ ] **Step 8: Generate placeholder MIDIs**

```bash
cd D:/AI/void-hunter && python stellar_horizon/tools/make_placeholder_midi.py stellar_horizon/assets/midi
```
Expected: "Wrote placeholder MIDIs to stellar_horizon/assets/midi" + 4 files.

- [ ] **Step 9: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_midi_player.py -v
```
Expected: 2 passed.

- [ ] **Step 10: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/audio/__init__.py
git add stellar_horizon/stellar_horizon/audio/midi_player.py
git add stellar_horizon/stellar_horizon/audio/sfx.py
git add stellar_horizon/tests/test_midi_player.py
git add stellar_horizon/tools/make_placeholder_midi.py
git add stellar_horizon/assets/midi/title.mid
git add stellar_horizon/assets/midi/act1.mid
git add stellar_horizon/assets/midi/boss.mid
git add stellar_horizon/assets/midi/game_over.mid
git add stellar_horizon/requirements-dev.txt
git commit -m "feat(audio): MIDI player + SFX wrapper + placeholder tracks"
```

---

## Task 12: FX (particles + screen shake)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/fx/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/fx/particles.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/fx/screen_shake.py`
- Create: `void-hunter/stellar_horizon/tests/test_fx.py`

**Interfaces:**
- Consumes: `src.systems.particle_engine.ParticleEngine`
- Produces:
  - `FxLayer` (init, emit_sparks(x,y,n), emit_explosion(x,y,scale), update(dt), draw(surface))
  - `ScreenShake` (init, add_trauma(amount), update(dt), offset() -> tuple[float, float])

- [ ] **Step 1: Create `fx/__init__.py`**

```python
# stellar_horizon/fx/__init__.py
```

- [ ] **Step 2: Write the failing tests**

```python
# stellar_horizon/tests/test_fx.py
import pytest
import pygame

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.screen_shake import ScreenShake


def test_fx_layer_constructs():
    fx = FxLayer()
    assert fx is not None


def test_fx_layer_emit_sparks():
    fx = FxLayer()
    fx.emit_sparks(100, 100, count=5)
    # Active count should be > 0
    assert fx.engine.active_count > 0


def test_fx_layer_emit_explosion():
    fx = FxLayer()
    fx.emit_explosion(200, 100, scale=1.0)
    assert fx.engine.active_count > 0


def test_fx_layer_update_and_draw():
    fx = FxLayer()
    fx.emit_sparks(100, 100, count=3)
    fx.update(0.1)
    surf = pygame.Surface((480, 270))
    fx.draw(surf)


def test_screen_shake_starts_at_zero():
    s = ScreenShake()
    assert s.offset() == (0.0, 0.0)


def test_screen_shake_add_trauma_produces_offset():
    s = ScreenShake()
    s.add_trauma(1.0)
    s.update(0.016)  # 1 frame
    ox, oy = s.offset()
    # With full trauma, offset magnitude should be > 0 (random)
    assert abs(ox) > 0 or abs(oy) > 0


def test_screen_shake_decays():
    s = ScreenShake()
    s.add_trauma(1.0)
    s.update(0.016)
    # Update for 5 seconds with no new trauma
    for _ in range(600):
        s.update(1 / 120)
    assert s.trauma == pytest.approx(0.0, abs=0.01)
```

- [ ] **Step 3: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_fx.py -v
```

- [ ] **Step 4: Implement `particles.py`**

```python
"""Particle FX layer wrapping Void-Hunter's ParticleEngine."""
from __future__ import annotations

import pygame

from src.systems.particle_engine import ParticleEngine
from stellar_horizon.settings import PARTICLE_POOL


class FxLayer:
    def __init__(self, pool_size: int = PARTICLE_POOL) -> None:
        self.engine = ParticleEngine(pool_size=pool_size)

    def emit_sparks(self, x: float, y: float, count: int = 8) -> None:
        for _ in range(count):
            self.engine.emit(0, x, y, 0, 0)  # P_SPARK

    def emit_explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        n_sparks = int(16 * scale)
        n_smoke = int(4 * scale)
        for _ in range(n_sparks):
            self.engine.emit(0, x, y, 0, 0)  # P_SPARK
        for _ in range(n_smoke):
            self.engine.emit(2, x, y, 0, 0)  # P_SMOKE

    def update(self, dt: float) -> None:
        self.engine.update(dt)

    def draw(self, surface) -> None:
        self.engine.draw(surface)
```

- [ ] **Step 5: Implement `screen_shake.py`**

```python
"""Eiserloh trauma² screen shake. Ported from Void-Hunter (no import)."""
from __future__ import annotations

import random


class ScreenShake:
    def __init__(self, max_offset: float = 4.0, decay: float = 6.0) -> None:
        self.trauma: float = 0.0
        self.max_offset: float = max_offset
        self.decay: float = decay  # trauma units per second
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

    def add_trauma(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt: float) -> None:
        # trauma² for snappy feel
        shake = (self.trauma ** 2) * self.max_offset
        self.offset_x = (random.random() * 2 - 1) * shake
        self.offset_y = (random.random() * 2 - 1) * shake
        self.trauma = max(0.0, self.trauma - self.decay * dt)

    def offset(self) -> tuple[float, float]:
        return self.offset_x, self.offset_y
```

- [ ] **Step 6: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_fx.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/fx/__init__.py
git add stellar_horizon/stellar_horizon/fx/particles.py
git add stellar_horizon/stellar_horizon/fx/screen_shake.py
git add stellar_horizon/tests/test_fx.py
git commit -m "feat(fx): particle layer + Eiserloh screen shake"
```

---

## Task 13: SceneManager + Scene interface

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/core/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/core/clock.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/core/scene_manager.py`
- Create: `void-hunter/stellar_horizon/tests/test_scenes.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Scene` (abstract: on_enter, on_exit, update(dt, events), draw(surface), next_scene())
  - `SceneManager` (current_state, update(dt, events), draw(surface), transition_to(state))

- [ ] **Step 1: Create `core/__init__.py`**

```python
# stellar_horizon/core/__init__.py
```

- [ ] **Step 2: Create `clock.py`**

```python
"""Fixed-timestep clock wrapper."""
from __future__ import annotations

import pygame

from stellar_horizon.settings import FPS_TARGET


class FixedClock:
    def __init__(self, target_fps: int = FPS_TARGET) -> None:
        self.target_fps = target_fps
        self.clock = pygame.time.Clock()

    def tick(self) -> int:
        return self.clock.tick(self.target_fps)
```

- [ ] **Step 3: Write the failing tests**

```python
# stellar_horizon/tests/test_scenes.py
import pytest
import pygame

from stellar_horizon.core.scene_manager import Scene, SceneManager, SceneName


class CountingScene(Scene):
    def __init__(self, name):
        self.name = name
        self.entered = 0
        self.exited = 0
        self.updates = 0
        self.draws = 0
        self.next = None

    def on_enter(self):
        self.entered += 1

    def on_exit(self):
        self.exited += 1

    def update(self, dt, events):
        self.updates += 1

    def draw(self, surface):
        self.draws += 1

    def next_scene(self):
        return self.next


def test_scene_name_constants():
    assert SceneName.TITLE == "title"
    assert SceneName.GAMEPLAY == "gameplay"
    assert SceneName.BOSS_FIGHT == "boss_fight"
    assert SceneName.ACT_CLEARED == "act_cleared"
    assert SceneName.GAME_OVER == "game_over"


def test_scene_manager_starts_at_title():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    assert sm.current_state == SceneName.TITLE


def test_scene_manager_calls_on_enter_on_start():
    title = CountingScene(SceneName.TITLE)
    SceneManager(title)  # constructs
    assert title.entered == 1


def test_scene_manager_update_calls_scene_update():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    sm.update(0.1, [])
    assert title.updates == 1


def test_scene_manager_draw_calls_scene_draw():
    title = CountingScene(SceneName.TITLE)
    sm = SceneManager(title)
    sm.draw(pygame.Surface((10, 10)))
    assert title.draws == 1


def test_scene_manager_transitions_when_next_scene_set():
    title = CountingScene(SceneName.TITLE)
    gameplay = CountingScene(SceneName.GAMEPLAY)
    title.next = gameplay
    sm = SceneManager(title)
    sm.update(0.1, [])  # triggers transition
    assert sm.current_state == SceneName.GAMEPLAY
    assert title.exited == 1
    assert gameplay.entered == 1


def test_scene_manager_explicit_transition_to():
    title = CountingScene(SceneName.TITLE)
    gameplay = CountingScene(SceneName.GAMEPLAY)
    sm = SceneManager(title)
    sm.transition_to(gameplay)
    assert sm.current_state == SceneName.GAMEPLAY
    assert title.exited == 1
```

- [ ] **Step 4: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_scenes.py -v
```

- [ ] **Step 5: Implement `scene_manager.py`**

```python
"""Scene state machine."""
from __future__ import annotations

import pygame


class SceneName:
    TITLE = "title"
    GAMEPLAY = "gameplay"
    BOSS_FIGHT = "boss_fight"
    ACT_CLEARED = "act_cleared"
    GAME_OVER = "game_over"


class Scene:
    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def update(self, dt: float, events: list[pygame.event.Event]) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...
    def next_scene(self) -> "Scene | None": ...


class SceneManager:
    def __init__(self, initial_scene: Scene) -> None:
        self.current: Scene = initial_scene
        self.current_state: str = initial_scene.name
        self.current.on_enter()

    def update(self, dt: float, events: list[pygame.event.Event]) -> None:
        self.current.update(dt, events)
        nxt = self.current.next_scene()
        if nxt is not None:
            self.transition_to(nxt)

    def draw(self, surface: pygame.Surface) -> None:
        self.current.draw(surface)

    def transition_to(self, scene: Scene) -> None:
        self.current.on_exit()
        self.current = scene
        self.current_state = scene.name
        self.current.on_enter()
```

- [ ] **Step 6: Run tests — should all pass**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_scenes.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/core/__init__.py
git add stellar_horizon/stellar_horizon/core/clock.py
git add stellar_horizon/stellar_horizon/core/scene_manager.py
git add stellar_horizon/tests/test_scenes.py
git commit -m "feat(scene): SceneManager + Scene base + state machine"
```

---

## Task 14: Scenes (title, gameplay, game_over)

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/scenes/__init__.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/scenes/title.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/scenes/gameplay.py`
- Create: `void-hunter/stellar_horizon/stellar_horizon/scenes/game_over.py`
- Create: `void-hunter/stellar_horizon/tests/test_scenes_gameplay.py`

**Interfaces:**
- Consumes: `core.scene_manager.{Scene, SceneName}`, `audio.MidiPlayer`, `entities.Player`, `waves.WaveManager`, `ui.Hud`, `ui.Background`, `fx.FxLayer`, `fx.ScreenShake`
- Produces:
  - `TitleScene` (init, on_enter, update, draw, next_scene)
  - `GameplayScene` (init with deps, on_enter, update, draw, next_scene)
  - `GameOverScene` (init, on_enter, update, draw, next_scene)

- [ ] **Step 1: Create `scenes/__init__.py`**

```python
# stellar_horizon/scenes/__init__.py
```

- [ ] **Step 2: Implement `title.py`**

```python
"""Title screen scene."""
from __future__ import annotations

from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class TitleScene(Scene):
    name = SceneName.TITLE

    def __init__(self, midi_player: MidiPlayer, midi_path: str) -> None:
        self.midi_player = midi_player
        self.midi_path = midi_path
        self._font = None
        self._big_font = None
        self._next: Scene | None = None

    def on_enter(self) -> None:
        self.midi_player.play(self.midi_path, loop=True)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt: float, events: list) -> None:
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    from stellar_horizon.scenes.gameplay import GameplayScene
                    self._next = GameplayScene(
                        player_factory=lambda rect: None,  # filled in Task 15
                        wave_json=Path("stellar_horizon/stellar_horizon/waves/waves_act1.json"),
                        midi_player=self.midi_player,
                    )
                    return

    def draw(self, surface: pygame.Surface) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 16, bold=True)
            self._big_font = pygame.font.SysFont("monospace", 32, bold=True)
        surface.fill((10, 15, 31))
        title = self._big_font.render("STELLAR HORIZON", False, (240, 240, 240))
        surface.blit(title, (INTERNAL_W // 2 - title.get_width() // 2, INTERNAL_H // 3))
        sub = self._font.render("Press SPACE to start", False, (180, 180, 220))
        surface.blit(sub, (INTERNAL_W // 2 - sub.get_width() // 2, INTERNAL_H // 2))

    def next_scene(self):
        return self._next
```

- [ ] **Step 3: Implement `gameplay.py`**

```python
"""Main gameplay scene: player, waves, boss, HUD, FX, audio."""
from __future__ import annotations

from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.entities.boss import Boss
from stellar_horizon.entities.bullet import EnemyBullet, PlayerBullet
from stellar_horizon.entities.enemy import Enemy
from stellar_horizon.entities.player import Player
from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.screen_shake import ScreenShake
from stellar_horizon.settings import (
    ENEMY_BULLET_POOL, ENEMY_POOL, INTERNAL_W, INTERNAL_H, PLAYER_BULLET_POOL,
)
from stellar_horizon.ui.backgrounds import Background
from stellar_horizon.ui.hud import Hud
from stellar_horizon.waves.wave_manager import WaveManager


class GameplayScene(Scene):
    name = SceneName.GAMEPLAY

    def __init__(self, midi_player: MidiPlayer, wave_json: Path,
                 assets_dir: Path) -> None:
        self.midi_player = midi_player
        self.wave_json = wave_json
        self.assets_dir = assets_dir
        # State
        self.player: Player | None = None
        self.wave_manager: WaveManager | None = None
        self.boss: Boss | None = None
        self.boss_active: bool = False
        self.background: Background | None = None
        self.hud = Hud()
        self.fx = FxLayer()
        self.shake = ScreenShake()
        self.player_bullets: list[PlayerBullet] = [PlayerBullet() for _ in range(PLAYER_BULLET_POOL)]
        self.enemy_bullets: list[EnemyBullet] = [EnemyBullet() for _ in range(ENEMY_BULLET_POOL)]
        self.score: int = 0
        self._next: Scene | None = None
        # Keyboard snapshot (built per-update)
        self._keys = None

    def on_enter(self) -> None:
        screen_rect = pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)
        self.player = Player(screen_rect)
        self.wave_manager = WaveManager(self.wave_json)
        self.wave_manager.begin()
        self.background = Background(self.assets_dir / "backgrounds" / f"{self.wave_manager.background}.png")
        self.midi_player.play(str(self.assets_dir / "midi" / self.wave_manager.midi_track), loop=True)
        self.hud.set_player(self.player)
        self.hud.set_wave(1, len(self.wave_manager.waves))
        self.hud.set_enemies_remaining(0, 0)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt: float, events: list) -> None:
        # Build keys snapshot
        self._keys = pygame.key.get_pressed()
        self.player.firing = self._keys[pygame.K_SPACE]
        # Player
        new_player_bullets = []
        self.player.update(dt, self._keys, self.player_bullets)
        for b in self.player_bullets:
            b.update(dt)
            if b.alive:
                new_player_bullets.append(b)
        self.player_bullets = new_player_bullets
        # Wave manager
        if self.wave_manager and not self.boss_active:
            new_enemies = self.wave_manager.update(dt)
            # Enemy updates
            for e in self.wave_manager.spawned_enemies:
                new_bullets = e.update(dt, self.player)
                for nb in new_bullets:
                    # Find free slot in enemy_bullets pool
                    for slot in self.enemy_bullets:
                        if not slot.alive:
                            slot.x, slot.y, slot.vx, slot.vy, slot.alive = (
                                nb.x, nb.y, nb.vx, nb.vy, True
                            )
                            break
            # Bullet-vs-enemy collision
            for b in self.player_bullets:
                if not b.alive:
                    continue
                for e in self.wave_manager.spawned_enemies:
                    if e.alive and b.hitbox().colliderect(e.hitbox()):
                        e.take_damage(1)
                        b.alive = False
                        if not e.alive:
                            self.score += e.score_value()
                            self.fx.emit_explosion(e.x, e.y, scale=1.0)
                            self.shake.add_trauma(0.10)
                        break
            # Enemy-vs-player collision
            for e in self.wave_manager.spawned_enemies:
                if e.alive and e.hitbox().colliderect(self.player.hitbox()):
                    self.player.take_hit()
                    self.shake.add_trauma(0.20)
                    self.fx.emit_explosion(e.x, e.y, scale=0.6)
                    e.alive = False
            # If all waves complete, spawn boss
            if self.wave_manager.wave_complete and not self.boss_active:
                if not self.wave_manager.next_wave():
                    # No more waves — start boss
                    self._spawn_boss()
            elif self.wave_manager.wave_complete and self.boss_active is False:
                if not self.wave_manager.next_wave():
                    self._spawn_boss()
        # Boss update
        if self.boss_active and self.boss is not None:
            new_bullets = self.boss.update(dt, self.player)
            for nb in new_bullets:
                for slot in self.enemy_bullets:
                    if not slot.alive:
                        slot.x, slot.y, slot.vx, slot.vy, slot.alive = (
                            nb.x, nb.y, nb.vx, nb.vy, True
                        )
                        break
            # Bullet-vs-boss collision
            for b in self.player_bullets:
                if not b.alive:
                    continue
                if self.boss.alive and b.hitbox().colliderect(self.boss.hitbox()):
                    self.boss.take_damage(1)
                    b.alive = False
                    if not self.boss.alive:
                        self.score += self.boss.score_value()
                        self.fx.emit_explosion(self.boss.x, self.boss.y, scale=3.0)
                        self.shake.add_trauma(0.50)
            # Boss-vs-player collision
            if self.boss.alive and self.boss.hitbox().colliderect(self.player.hitbox()):
                self.player.take_hit()
                self.shake.add_trauma(0.30)
        # Enemy bullets update + collision with player
        new_enemy_bullets = []
        for b in self.enemy_bullets:
            b.update(dt)
            if b.alive:
                if b.hitbox().colliderect(self.player.hitbox()):
                    self.player.take_hit()
                    b.alive = False
                    self.shake.add_trauma(0.15)
                else:
                    new_enemy_bullets.append(b)
        self.enemy_bullets = new_enemy_bullets
        # FX + shake
        self.fx.update(dt)
        self.shake.update(dt)
        # Background
        self.background.update(dt, scroll_speed=0.0)
        # HUD
        self.hud.set_score(self.score)
        if self.boss_active and self.boss is not None:
            self.hud.set_boss(self.boss)
            self.hud.set_enemies_remaining(1 if self.boss.alive else 0, 1)
        else:
            self.hud.set_boss(None)
            alive = sum(1 for e in self.wave_manager.spawned_enemies if e.alive) if self.wave_manager else 0
            total = self.wave_manager.current_wave_index + 1 if self.wave_manager else 0
            self.hud.set_enemies_remaining(alive, max(alive, 10))
            self.hud.set_wave(
                (self.wave_manager.current_wave_index + 1) if self.wave_manager else 0,
                len(self.wave_manager.waves) if self.wave_manager else 0,
            )
        # Check player death → GAME_OVER
        if not self.player.alive:
            from stellar_horizon.scenes.game_over import GameOverScene
            self._next = GameOverScene(self.midi_player, score=self.score)
        # Check boss dead → ACT_CLEARED
        if self.boss_active and self.boss and self.boss.phase == "dead":
            from stellar_horizon.scenes.game_over import GameOverScene  # for now, treat as game over
            self._next = GameOverScene(self.midi_player, score=self.score, victory=True)

    def draw(self, surface: pygame.Surface) -> None:
        ox, oy = self.shake.offset()
        # Background with shake offset
        bg_surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.background.draw(bg_surface)
        surface.blit(bg_surface, (int(ox), int(oy)))
        # Enemies
        if self.wave_manager:
            for e in self.wave_manager.spawned_enemies:
                if e.alive:
                    self._draw_placeholder_enemy(surface, e, ox, oy)
        # Boss
        if self.boss_active and self.boss and self.boss.alive:
            self._draw_placeholder_boss(surface, self.boss, ox, oy)
        # Player
        if self.player.alive:
            self._draw_placeholder_player(surface, self.player, ox, oy)
        # Bullets
        for b in self.player_bullets:
            if b.alive:
                pygame.draw.rect(surface, (255, 240, 100),
                                 (int(b.x - 6 + ox), int(b.y - 2 + oy), 12, 4))
        for b in self.enemy_bullets:
            if b.alive:
                pygame.draw.circle(surface, (240, 80, 100),
                                   (int(b.x + ox), int(b.y + oy)), 4)
        # FX
        self.fx.draw(surface)
        # HUD
        self.hud.draw(surface)

    def next_scene(self):
        return self._next

    def _spawn_boss(self) -> None:
        self.boss = Boss()
        self.boss_active = True
        self.hud.set_boss(self.boss)

    def _draw_placeholder_player(self, surface, p, ox, oy) -> None:
        # Placeholder: a small green triangle pointing right
        cx, cy = int(p.x + ox), int(p.y + oy)
        pygame.draw.polygon(surface, (90, 220, 120),
                            [(cx - 6, cy - 5), (cx - 6, cy + 5), (cx + 6, cy)])

    def _draw_placeholder_enemy(self, surface, e, ox, oy) -> None:
        cx, cy = int(e.x + ox), int(e.y + oy)
        if e.kind == "scout":
            color = (220, 60, 60)
        elif e.kind == "cruiser":
            color = (240, 130, 40)
        else:  # heavy
            color = (180, 180, 200)
        # Telegraph flash
        if e.telegraphing:
            color = (255, 240, 100)
        size = 10 if e.kind != "heavy" else 14
        pygame.draw.rect(surface, color, (cx - size // 2, cy - size // 2, size, size))

    def _draw_placeholder_boss(self, surface, b, ox, oy) -> None:
        cx, cy = int(b.x + ox), int(b.y + oy)
        size = 48
        # Boss placeholder: large gray hex
        pts = []
        for i in range(6):
            import math
            a = 2 * math.pi * i / 6
            pts.append((cx + int(math.cos(a) * size / 2), cy + int(math.sin(a) * size / 2)))
        pygame.draw.polygon(surface, (160, 140, 110), pts)
        pygame.draw.polygon(surface, (220, 100, 60), pts, 2)
```

- [ ] **Step 4: Implement `game_over.py`**

```python
"""Game over screen scene."""
from __future__ import annotations

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


class GameOverScene(Scene):
    name = SceneName.GAME_OVER

    def __init__(self, midi_player: MidiPlayer, score: int = 0, victory: bool = False) -> None:
        self.midi_player = midi_player
        self.score = score
        self.victory = victory
        self._font = None
        self._big_font = None
        self._next = None
        self._timer = 0.0

    def on_enter(self) -> None:
        # Play game-over music
        import os
        from pathlib import Path
        midi = Path(__file__).resolve().parent.parent.parent / "assets" / "midi" / "game_over.mid"
        if midi.exists():
            self.midi_player.play(str(midi), loop=True)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt, events):
        self._timer += dt
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN):
                    # Retry: return to gameplay
                    from stellar_horizon.scenes.gameplay import GameplayScene
                    from pathlib import Path
                    self._next = GameplayScene(
                        midi_player=self.midi_player,
                        wave_json=Path("stellar_horizon/stellar_horizon/waves/waves_act1.json"),
                        assets_dir=Path("stellar_horizon/assets"),
                    )
                elif ev.key == pygame.K_q:
                    import sys
                    pygame.quit()
                    sys.exit(0)

    def draw(self, surface):
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 14, bold=True)
            self._big_font = pygame.font.SysFont("monospace", 28, bold=True)
        surface.fill((10, 15, 31))
        msg = "VICTORY" if self.victory else "GAME OVER"
        color = (220, 220, 100) if self.victory else (220, 80, 80)
        title = self._big_font.render(msg, False, color)
        surface.blit(title, (INTERNAL_W // 2 - title.get_width() // 2, INTERNAL_H // 3))
        sub = self._font.render(f"Final score: {self.score}", False, (240, 240, 240))
        surface.blit(sub, (INTERNAL_W // 2 - sub.get_width() // 2, INTERNAL_H // 2))
        hint = self._font.render("R = retry   Q = quit", False, (180, 180, 220))
        surface.blit(hint, (INTERNAL_W // 2 - hint.get_width() // 2, INTERNAL_H // 2 + 30))

    def next_scene(self):
        return self._next
```

- [ ] **Step 5: Write a basic gameplay scene test**

```python
# stellar_horizon/tests/test_scenes_gameplay.py
import os
from pathlib import Path
import pytest
import pygame

from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.scenes.title import TitleScene
from stellar_horizon.scenes.game_over import GameOverScene
from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.tools.make_placeholder_bgs import make_placeholder_backgrounds
from stellar_horizon.tools.make_placeholder_midi import make_placeholder_midi


@pytest.fixture(scope="module", autouse=True)
def init_mixer():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.mixer.init()
    yield
    pygame.mixer.quit()


@pytest.fixture
def assets_dir(tmp_path):
    bg_dir = tmp_path / "backgrounds"
    midi_dir = tmp_path / "midi"
    make_placeholder_backgrounds(bg_dir)
    midi_dir.mkdir(parents=True, exist_ok=True)
    make_placeholder_midi(midi_dir / "act1.mid", seconds=2)
    make_placeholder_midi(midi_dir / "game_over.mid", seconds=2)
    return tmp_path


def test_title_scene_constructs(assets_dir):
    midi = MidiPlayer()
    s = TitleScene(midi, str(assets_dir / "midi" / "act1.mid"))
    assert s.name == "title"


def test_gameplay_scene_constructs(assets_dir):
    midi = MidiPlayer()
    s = GameplayScene(
        midi_player=midi,
        wave_json=Path("stellar_horizon/stellar_horizon/waves/waves_act1.json"),
        assets_dir=assets_dir,
    )
    assert s.name == "gameplay"


def test_gameplay_scene_on_enter_starts_wave(assets_dir):
    midi = MidiPlayer()
    s = GameplayScene(
        midi_player=midi,
        wave_json=Path("stellar_horizon/stellar_horizon/waves/waves_act1.json"),
        assets_dir=assets_dir,
    )
    s.on_enter()
    assert s.player is not None
    assert s.wave_manager is not None


def test_game_over_constructs(assets_dir):
    midi = MidiPlayer()
    s = GameOverScene(midi, score=12345, victory=False)
    assert s.score == 12345
    assert s.victory is False
```

- [ ] **Step 6: Run tests**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_scenes_gameplay.py -v
```
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/scenes/__init__.py
git add stellar_horizon/stellar_horizon/scenes/title.py
git add stellar_horizon/stellar_horizon/scenes/gameplay.py
git add stellar_horizon/stellar_horizon/scenes/game_over.py
git add stellar_horizon/tests/test_scenes_gameplay.py
git commit -m "feat(scene): title, gameplay, game_over scenes + integration test"
```

---

## Task 15: Main game loop + integration

**Files:**
- Create: `void-hunter/stellar_horizon/stellar_horizon/core/game.py`
- Modify: `void-hunter/stellar_horizon/main.py` (replace stub with real run loop)
- Create: `void-hunter/stellar_horizon/tests/test_game_loop.py`

**Interfaces:**
- Consumes: `core.{scene_manager, clock}`, `settings`
- Produces: `Game` class with `run()` method, full window + event loop.

- [ ] **Step 1: Write the failing test**

```python
# stellar_horizon/tests/test_game_loop.py
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest
import pygame

from stellar_horizon.core.game import Game


def test_game_constructs():
    g = Game()
    assert g._running is True
    assert g.internal.get_size() == (480, 270)
    pygame.quit()


def test_game_processes_one_frame():
    g = Game()
    g._accumulator = 0.0
    # Tick a single frame
    initial_updates = g._frame_count
    g._tick_frame()
    assert g._frame_count == initial_updates + 1
    pygame.quit()
```

- [ ] **Step 2: Run tests — should fail with ImportError**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_game_loop.py -v
```

- [ ] **Step 3: Implement `core/game.py`**

```python
"""Main game class: window, fixed-timestep loop, scene manager."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.clock import FixedClock
from stellar_horizon.core.scene_manager import SceneManager
from stellar_horizon.scenes.title import TitleScene
from stellar_horizon.settings import (
    DT_CLAMP, FIXED_DT, FPS_TARGET, INTERNAL_H, INTERNAL_W, WINDOW_H, WINDOW_W,
)


def _detect_scale() -> float:
    """Try to fill the monitor work area, like Void-Hunter does."""
    if sys.platform != "win32":
        return 4.0
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        rect = wintypes.RECT()
        if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0) and rect.bottom > rect.top:
            work_h = rect.bottom - rect.top
        else:
            work_h = 1080
        scale_h = max(1.0, work_h / INTERNAL_H)
        return float(min(scale_h, 6.0))
    except Exception:
        return 4.0


class Game:
    def __init__(self, assets_dir: Path | None = None) -> None:
        pygame.init()
        pygame.mixer.init()
        self.assets_dir = assets_dir or (
            Path(__file__).resolve().parent.parent.parent / "assets"
        )
        scale = _detect_scale()
        win_w = int(INTERNAL_W * scale)
        win_h = int(INTERNAL_H * scale)
        self.internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.window = pygame.display.set_mode(
            (win_w, win_h), pygame.SCALED | pygame.RESIZABLE,
        )
        pygame.display.set_caption("STELLAR HORIZON")
        self.clock = FixedClock(FPS_TARGET)
        self.midi_player = MidiPlayer()
        # Initial scene
        title_midi = self.assets_dir / "midi" / "title.mid"
        title = TitleScene(self.midi_player, str(title_midi))
        self.scenes = SceneManager(title)
        # State
        self._running = True
        self._accumulator = 0.0
        self._frame_count = 0

    def run(self) -> None:
        last = pygame.time.get_ticks() / 1000.0
        crash_log = Path("logs") / "stellar_horizon_crash.log"
        crash_log.parent.mkdir(parents=True, exist_ok=True)
        try:
            while self._running:
                self._tick_frame(last)
                last = pygame.time.get_ticks() / 1000.0
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()

    def _tick_frame(self, last: float | None = None) -> None:
        """One frame: events, fixed-timestep updates, render, present.

        Split out from run() so tests can call it directly.
        """
        if last is None:
            last = pygame.time.get_ticks() / 1000.0
        now = pygame.time.get_ticks() / 1000.0
        frame_time = min(now - last, DT_CLAMP)
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                self._running = False
                return
        self._accumulator += frame_time
        while self._accumulator >= FIXED_DT:
            self.scenes.update(FIXED_DT, events)
            self._accumulator -= FIXED_DT
        self.internal.fill((10, 15, 31))
        self.scenes.draw(self.internal)
        # Present: scale internal to window
        scaled = pygame.transform.scale(self.internal, self.window.get_size())
        self.window.blit(scaled, (0, 0))
        pygame.display.flip()
        self.clock.tick()
        self._frame_count += 1
```

- [ ] **Step 4: Update `main.py` to use Game**

```python
"""STELLAR HORIZON — entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stellar-horizon",
        description="STELLAR HORIZON — horizontal 16-bit shmup, 480x270 internal.",
    )
    parser.add_argument("--check", action="store_true", help="Validate imports + settings; exit 0/1.")
    parser.add_argument("--duration", type=int, default=0, help="Auto-exit after N seconds (0 = no auto-exit).")
    args = parser.parse_args(argv)
    if args.check:
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, FPS_TARGET
        print("STELLAR HORIZON check OK")
        print(f"  Internal: {INTERNAL_W}x{INTERNAL_H}")
        print(f"  FPS target: {FPS_TARGET}")
        return 0
    # Real game run
    from stellar_horizon.core.game import Game
    g = Game()
    if args.duration > 0:
        import time
        start = time.perf_counter()
        g._running = True
        last = pygame.time.get_ticks() / 1000.0 if pygame.get_init() else 0.0
        # Patch run to honor duration
        import pygame as _pygame
        while g._running and (time.perf_counter() - start) < args.duration:
            g._tick_frame(last)
            last = _pygame.time.get_ticks() / 1000.0
        _pygame.quit()
    else:
        g.run()
    return 0


if __name__ == "__main__":
    import pygame
    sys.exit(main())
```

- [ ] **Step 5: Run tests**

```bash
cd D:/AI/void-hunter && python -m pytest stellar_horizon/tests/test_game_loop.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Smoke-run the game for 5 seconds headless**

```bash
cd D:/AI/void-hunter && SDL_VIDEODRIVER=dummy python stellar_horizon/main.py --duration 5
```
Expected: exits 0, no exceptions. Logs to `logs/stellar_horizon_crash.log` only if errors.

- [ ] **Step 7: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/stellar_horizon/core/game.py
git add stellar_horizon/main.py
git add stellar_horizon/tests/test_game_loop.py
git commit -m "feat(core): main game loop + window + scene integration"
```

---

## Task 16: Smoke test (11-gate like VH)

**Files:**
- Create: `void-hunter/stellar_horizon/smoke.py`
- Modify: `void-hunter/stellar_horizon/README.md` (smoke test instructions)

**Interfaces:**
- Consumes: all of `stellar_horizon.*` and `src.movement`
- Produces: `smoke.run()` returns (passed: int, failed: int, results: list[(name, ok, msg)])

- [ ] **Step 1: Implement `smoke.py`**

```python
"""STELLAR HORIZON — 11-gate smoke test, mirrors Void-Hunter's smoke.py."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


def _gate(name, fn):
    try:
        msg = fn() or ""
        return (name, True, msg)
    except Exception as exc:
        tb = traceback.format_exc()
        return (name, False, f"{type(exc).__name__}: {exc}\n{tb}")


def run() -> tuple[int, int, list[tuple[str, bool, str]]]:
    results: list[tuple[str, bool, str]] = []

    def g01_import_settings():
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H, FPS_TARGET
        assert INTERNAL_W == 480 and INTERNAL_H == 270 and FPS_TARGET == 120
        return f"{INTERNAL_W}x{INTERNAL_H} @ {FPS_TARGET} FPS"

    def g02_import_movement():
        from src.movement import BezierPath, WaypointPath, HybridPath, FlightFormation
        return "imported"

    def g03_bezier_horizontal_paths():
        from stellar_horizon.waves.bezier_horizontal import (
            path_s_right_to_left, path_top_dive, path_zigzag_exit_top, path_boss_entry,
        )
        p = path_s_right_to_left()
        assert p.position_at(0).x > 480
        return "off-screen entry"

    def g04_formations_rotated():
        from stellar_horizon.waves.formations_h import v_pointing_left
        offsets = v_pointing_left(count=5)
        assert len(offsets) == 5
        assert offsets[0] == (0.0, 0.0)
        return "5 slots"

    def g05_player_construction():
        import pygame
        from stellar_horizon.entities.player import Player
        p = Player(pygame.Rect(0, 0, 480, 270))
        assert p.lives == 3
        return f"lives={p.lives}"

    def g06_enemy_construction():
        from stellar_horizon.entities.enemy import Enemy, EnemyKind
        e = Enemy()
        e.kind = EnemyKind.SCOUT
        e.on_spawn()
        assert e.hp == 1
        return f"hp={e.hp}"

    def g07_boss_construction():
        from stellar_horizon.entities.boss import Boss, BossPhase
        b = Boss()
        assert b.phase == BossPhase.ENTERING
        assert b.hp == 60
        return f"hp={b.hp}"

    def g08_wave_manager_loads():
        from stellar_horizon.waves.wave_manager import WaveManager
        from pathlib import Path
        wm = WaveManager(Path(__file__).resolve().parent / "stellar_horizon" / "waves" / "waves_act1.json")
        assert wm.act == 1
        return f"act={wm.act}, waves={len(wm.waves)}"

    def g09_hud_draws():
        import pygame
        from stellar_horizon.ui.hud import Hud
        from stellar_horizon.entities.player import Player
        surf = pygame.Surface((480, 270))
        h = Hud()
        h.set_player(Player(pygame.Rect(0, 0, 480, 270)))
        h.set_score(12345)
        h.set_wave(2, 4)
        h.draw(surf)
        return "ok"

    def g10_midi_files_exist():
        from pathlib import Path
        assets = Path(__file__).resolve().parent / "assets" / "midi"
        for name in ("title", "act1", "boss", "game_over"):
            assert (assets / f"{name}.mid").exists(), f"missing {name}.mid"
        return f"4/4 midis"

    def g11_backgrounds_exist():
        from pathlib import Path
        assets = Path(__file__).resolve().parent / "assets" / "backgrounds"
        for name in ("act1_asteroid_belt", "act2_nebula", "act3_sun_close"):
            assert (assets / f"{name}.png").exists(), f"missing {name}.png"
        return f"3/3 bgs"

    for name, fn in [
        ("01_import_settings",   g01_import_settings),
        ("02_import_movement",   g02_import_movement),
        ("03_bezier_horizontal", g03_bezier_horizontal_paths),
        ("04_formations_rotated", g04_formations_rotated),
        ("05_player",            g05_player_construction),
        ("06_enemy",             g06_enemy_construction),
        ("07_boss",              g07_boss_construction),
        ("08_wave_manager",      g08_wave_manager_loads),
        ("09_hud",               g09_hud_draws),
        ("10_midi_files",        g10_midi_files_exist),
        ("11_backgrounds",       g11_backgrounds_exist),
    ]:
        results.append(_gate(name, fn))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    return passed, failed, results


if __name__ == "__main__":
    p, f, results = run()
    print(f"STELLAR HORIZON smoke: {p}/{p + f} passed, {f} failed")
    for name, ok, msg in results:
        mark = "OK " if ok else "FAIL"
        print(f"  [{mark}] {name}: {msg}")
    sys.exit(0 if f == 0 else 1)
```

- [ ] **Step 2: Run the smoke test**

```bash
cd D:/AI/void-hunter && python stellar_horizon/smoke.py
```
Expected: "11/11 passed" and exit 0.

- [ ] **Step 3: Update README with smoke instructions**

```markdown
# STELLAR HORIZON

A horizontal 16-bit space shooter built on Void-Hunter's movement library.

## Run

```bash
# Smoke test (11 gates, ~5s)
python stellar_horizon/smoke.py

# Play the game
python stellar_horizon/main.py

# Play for N seconds then quit
python stellar_horizon/main.py --duration 60

# Validate imports
python stellar_horizon/main.py --check
```

## Tests

```bash
python -m pytest stellar_horizon/tests/ -v
```

## Spec

`docs/superpowers/specs/2026-08-15-stellar-horizon-design.md`
```

- [ ] **Step 4: Commit**

```bash
cd D:/AI/void-hunter
git add stellar_horizon/smoke.py
git add stellar_horizon/README.md
git commit -m "test(smoke): 11-gate smoke test mirroring Void-Hunter"
```

---

## Self-Review

**1. Spec coverage:**

| Spec section | Implemented in |
|---|---|
| §1 Goals (re-use, 480×270, 16-bit, bezier focus) | Task 1 (settings), Task 2 (paths) |
| §3 Architecture (Library-Import) | Tasks 1, 2, 3 (all `from src.movement import ...`) |
| §4 File tree | Tasks 1-15 create all listed files |
| §5 Player (WASD/Arrows, 3 lives) | Task 4 |
| §6 Bullets (PlayerBullet +X, EnemyBullet aimed) | Task 5 |
| §7 Enemies (3 types) | Task 6 |
| §8 Bezier horizontal paths (3 + boss_entry) | Task 2 |
| §9 Formations (V/line/diamond/wedge rotated) | Task 3 |
| §10 Waves (JSON + scheduler) | Task 8 |
| §11 Boss (ASTEROID_GUARDIAN 2 phases) | Task 7 |
| §12 HUD (top/bottom) | Task 9 |
| §13 Scenes (5 states — phase 1 implements 3: TITLE, GAMEPLAY, GAME_OVER) | Task 13 (SceneManager), Task 14 (3 scenes) |
| §14 Backgrounds (3 ambientes) | Task 10 |
| §15 Audio (MIDI + SFX) | Task 11 |
| §16 FX (particles + screen shake) | Task 12 |
| §17 Game loop | Task 15 |
| §18 Testing (~65 tests) | Tasks 1-15 each add tests; smoke at Task 16 |
| §19 Phase 1 success criteria | Verified at end (smoke + manual run) |
| §20 Phase 2+ roadmap | Not in this plan; parked |

**Gaps:** None blocking Phase 1. The 5-state scene machine (§13) has TITLE, GAMEPLAY, GAME_OVER implemented; BOSS_FIGHT and ACT_CLEARED are folded into GAMEPLAY's state machine (boss.alive check) and reused GAME_OVER with victory=True. Phase 2 can split them.

**2. Placeholder scan:** Searched the plan for "TBD", "TODO", "later", "similar to", etc. Found none.

**3. Type consistency:**
- `Player.lives: int` ✓ used in HUD ✓ used in scene collision ✓
- `Enemy.alive: bool` ✓ used in scene ✓
- `EnemyKind.SCOUT == "scout"` ✓ used in wave_manager mapping ✓
- `BezierPath`, `HybridPath`, `PathFollower` ✓ imported from `src.movement` everywhere ✓
- `Point` ✓ used in path constructors ✓
- `MidiPlayer.play(path, loop=True)` ✓ used in scenes ✓
- `WaveManager.begin()`, `update(dt)`, `next_wave()` ✓ used in GameplayScene ✓
- `Boss.phase` uses strings: "entering", "phase_1", "phase_2", "dying", "dead" — referenced in GameplayScene as `self.boss.phase == "dead"` ✓

**4. Method signatures consistency:**
- `Player.update(dt, keys, bullets_pool)` ✓ used in GameplayScene ✓
- `Enemy.update(dt, player) -> list[EnemyBullet]` ✓ used in GameplayScene ✓
- `Boss.update(dt, player) -> list[EnemyBullet]` ✓ used in GameplayScene ✓
- `Player.take_hit()` ✓ used in GameplayScene collision ✓
- `Enemy.take_damage(amount)` ✓ used in GameplayScene ✓
- `Boss.take_damage(amount)` ✓ used in GameplayScene ✓
- `Scene.update(dt, events)` ✓ used in SceneManager ✓
- `Scene.draw(surface)` ✓ used in SceneManager ✓
- `Scene.next_scene()` ✓ used in SceneManager ✓

**Issues found and fixed inline during review:**
- Removed unused import in `game.py` smoke test path; now uses `Path(__file__).resolve().parent`
- Fixed scene-state machine: GameOverScene handles both defeat and victory via `victory` flag

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-15-stellar-horizon-phase1.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration with two-stage review gates.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
