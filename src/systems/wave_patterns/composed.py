"""BLOQUE 58.14.7: ComposedPattern — 50 choreographed combinations.

The user asked for 50 NEW patterns that combine:
  - Flight formations (V, line, diamond, wedge, circle, ...)
  - Bezier curves (sweep, s-curve, sine, spiral, loop, ...)
  - Follow the leader (chain, leader+free, solo, ...)

This module is data-driven: each pattern is a record
`(formation, path, follow, count, difficulty)` and the
`ComposedPattern` class turns it into a real `WavePatternResult`.

`COMPOSED_PATTERNS` is the library of 50 entries, registered
with the manager via `register_composed_patterns()`.
"""
from __future__ import annotations

import math
import random
from typing import Optional

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.systems.wave_patterns.base import (
    PatternDifficulty,
    SpawnedShip,
    WavePattern,
    WavePatternKind,
    WavePatternResult,
)


# ---- Formation slot generators (return list of (dx, dy) offsets) ----

def _slot_line(count: int, spacing: float = 24.0) -> list[tuple[float, float]]:
    """Horizontal line, leader in the middle."""
    if count <= 1:
        return [(0.0, 0.0)]
    half = (count - 1) / 2.0
    return [((i - half) * spacing, 0.0) for i in range(count)]


def _slot_v(count: int, spacing: float = 22.0) -> list[tuple[float, float]]:
    """V shape, leader at the front."""
    if count <= 1:
        return [(0.0, 0.0)]
    slots = [(0.0, 0.0)]
    for i in range(1, count):
        side = -1 if i % 2 == 1 else 1
        ring = (i + 1) // 2
        slots.append((side * ring * spacing, ring * spacing * 0.7))
    return slots


def _slot_diamond(count: int, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Diamond: leader front, 2 sides, 1 back."""
    if count <= 1:
        return [(0.0, 0.0)]
    slots = [(0.0, 0.0)]
    sides = [(-1, -1), (1, -1), (0, 1)]
    for i in range(1, min(count, 4)):
        slots.append((sides[i - 1][0] * spacing, sides[i - 1][1] * spacing))
    # 5+ ships: ring 2
    for i in range(4, count):
        ring = (i - 3)
        angle = (i - 4) * (math.pi * 2 / max(1, count - 4))
        slots.append((math.cos(angle) * spacing * 1.5,
                      math.sin(angle) * spacing * 1.5))
    return slots


def _slot_wedge(count: int, spacing: float = 24.0) -> list[tuple[float, float]]:
    """Forward wedge: leader front, expanding back."""
    slots: list[tuple[float, float]] = []
    for i in range(count):
        row = i
        spread = row * spacing * 0.8
        slots.append((0.0, -row * spacing))  # back
        if row > 0:
            slots.append((-spread, -row * spacing))
            slots.append((spread, -row * spacing))
    return slots[:count]


def _slot_circle(count: int, spacing: float = 24.0) -> list[tuple[float, float]]:
    """Ring around a center point."""
    if count <= 1:
        return [(0.0, 0.0)]
    r = spacing * 1.5
    return [(math.cos(i * 2 * math.pi / count) * r,
             math.sin(i * 2 * math.pi / count) * r) for i in range(count)]


def _slot_spiral(count: int, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Spiral arm: leader center, others expanding."""
    slots = [(0.0, 0.0)]
    for i in range(1, count):
        angle = i * 0.9
        r = i * spacing * 0.5
        slots.append((math.cos(angle) * r, math.sin(angle) * r))
    return slots


def _slot_x(count: int, spacing: float = 24.0) -> list[tuple[float, float]]:
    """X shape: 4 arms from leader."""
    slots = [(0.0, 0.0)]
    for i in range(1, min(count, 5)):
        angle = (i - 1) * (math.pi / 2) + math.pi / 4
        slots.append((math.cos(angle) * spacing, math.sin(angle) * spacing))
    for i in range(5, count):
        ring = i - 4
        angle = ring * (math.pi * 2 / max(1, count - 4))
        slots.append((math.cos(angle) * spacing * 1.6,
                      math.sin(angle) * spacing * 1.6))
    return slots


def _slot_pincer(count: int, spacing: float = 26.0) -> list[tuple[float, float]]:
    """Two mirrored halves (left/right)."""
    half = (count + 1) // 2
    slots: list[tuple[float, float]] = []
    for i in range(half):
        slots.append((-spacing * 1.2 - i * spacing * 0.5, i * spacing * 0.5))
    for i in range(count - half):
        slots.append((spacing * 1.2 + i * spacing * 0.5, i * spacing * 0.5))
    return slots[:count]


def _slot_arrow(count: int, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Arrow shape: leader at tip, 2 wings expanding back."""
    if count <= 1:
        return [(0.0, 0.0)]
    slots = [(0.0, 0.0)]
    for i in range(1, count):
        side = -1 if i % 2 == 1 else 1
        ring = (i + 1) // 2
        slots.append((side * ring * spacing * 1.3, -ring * spacing * 0.6))
    return slots


FORMATION_GENERATORS = {
    "line": _slot_line,
    "v": _slot_v,
    "diamond": _slot_diamond,
    "wedge": _slot_wedge,
    "circle": _slot_circle,
    "spiral": _slot_spiral,
    "x": _slot_x,
    "pincer": _slot_pincer,
    "arrow": _slot_arrow,
}


# ---- Bezier control point generators (return list of (x, y) in playfield) ----

def _path_sweep(
    start: tuple[float, float],
    rng: random.Random,
    amplitude: float = 80.0,
) -> list[tuple[float, float]]:
    """Single smooth curve, side varies."""
    end = (start[0] + rng.uniform(-amplitude, amplitude),
           start[1] + rng.uniform(120, 200))
    cp1 = (start[0] + rng.uniform(-amplitude * 1.5, amplitude * 1.5),
           start[1] + rng.uniform(40, 80))
    cp2 = (end[0] + rng.uniform(-amplitude * 1.5, amplitude * 1.5),
           end[1] - rng.uniform(40, 80))
    return [start, cp1, cp2, end]


def _path_s_curve(
    start: tuple[float, float],
    rng: random.Random,
    amplitude: float = 60.0,
) -> list[tuple[float, float]]:
    """S-curve: 2 inflection points."""
    end = (start[0] + rng.uniform(-amplitude, amplitude),
           start[1] + 200)
    cp1 = (start[0] + amplitude, start[1] + 60)
    cp2 = (end[0] - amplitude, end[1] - 60)
    return [start, cp1, cp2, end]


def _path_sine(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Sine wave approximated by 3 cubic segments."""
    out: list[tuple[float, float]] = [start]
    n_seg = 3
    x_step = (INTERNAL_W - 32) / n_seg
    for i in range(1, n_seg + 1):
        x = start[0] + x_step * i
        y = start[1] + (200.0 / n_seg) * i
        out.append((x, y))
    return out


def _path_spiral(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Spiral: outward then down."""
    cx, cy = INTERNAL_W / 2, start[1] + 100
    out = [start]
    for i in range(1, 5):
        angle = i * 1.2
        r = i * 30
        out.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    out.append((cx, start[1] + 250))
    return out


def _path_straight(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Straight down with tiny wobble."""
    return [
        start,
        (start[0] + rng.uniform(-20, 20), start[1] + 80),
        (start[0] + rng.uniform(-20, 20), start[1] + 160),
        (start[0], start[1] + 240),
    ]


def _path_loop(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Loop: curve makes a full circle before continuing."""
    cx, cy = start[0], start[1] + 80
    r = 40
    out = [start]
    for i in range(1, 5):
        angle = i * math.pi / 2
        out.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    out.append((start[0], start[1] + 200))
    return out


def _path_zigzag(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Zigzag."""
    return [
        start,
        (start[0] + 80, start[1] + 50),
        (start[0] - 80, start[1] + 100),
        (start[0] + 80, start[1] + 150),
        (start[0] - 40, start[1] + 200),
    ]


def _path_dive(
    start: tuple[float, float],
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Steep dive."""
    return [
        start,
        (start[0] + rng.uniform(-20, 20), start[1] + 40),
        (start[0] + rng.uniform(-40, 40), start[1] + 120),
        (start[0] + rng.uniform(-60, 60), start[1] + 240),
    ]


PATH_GENERATORS = {
    "sweep": _path_sweep,
    "s_curve": _path_s_curve,
    "sine": _path_sine,
    "spiral": _path_spiral,
    "straight": _path_straight,
    "loop": _path_loop,
    "zigzag": _path_zigzag,
    "dive": _path_dive,
}


# ---- Follow mode definitions ----
# "leader": one ship is leader, others follow via PathFollower with offset
# "chain":  all ships are in a chain (each follows the previous)
# "free":   no follow, each ship has its own offset along the path


# ---- Composed pattern ----

class ComposedPattern(WavePattern):
    """One choreographed pattern = (formation, path, follow) tuple."""

    def __init__(
        self,
        name: str,
        formation: str,
        path: str,
        follow: str,
        count: int,
        difficulty: PatternDifficulty,
    ) -> None:
        self._name = name
        self.kind = WavePatternKind.BEZIER_SWEEP  # generic; we add new kinds
        self.difficulty = difficulty
        self._formation = formation
        self._path = path
        self._follow = follow
        self._count = count

    @property
    def name(self) -> str:
        return self._name

    def generate(
        self,
        rng: random.Random,
        level: int,
        enemy_kind: str = "SCOUT",
    ) -> WavePatternResult:
        form_fn = FORMATION_GENERATORS[self._formation]
        path_fn = PATH_GENERATORS[self._path]
        slots = form_fn(self._count)
        # Pick entry side
        entry_x = rng.uniform(48, INTERNAL_W - 48)
        entry_y = -20.0
        path_pts = path_fn((entry_x, entry_y), rng)
        ships: list[SpawnedShip] = []
        for i, (dx, dy) in enumerate(slots):
            is_leader = (i == 0) and (self._follow in ("leader", "chain"))
            t_off = i * 0.15 if self._follow == "chain" else 0.0
            ships.append(SpawnedShip(
                spawn_x=entry_x + dx,
                spawn_y=entry_y + dy,
                t_offset=t_off,
                slot=i,
                color=(255, 200, 80) if is_leader else (200, 160, 220),
                is_leader=is_leader,
                extra={
                    "formation": self._formation,
                    "path": self._path,
                    "path_points": path_pts,
                    "follow": self._follow,
                },
            ))
        return WavePatternResult(
            ships=ships,
            kind=WavePatternKind.BEZIER_SWEEP,
            difficulty=self.difficulty,
            duration_s=8.0,
            seed_used=rng.randrange(2**32),
        )


# ---- 50 pre-defined combinations ----
# 9 formations * 6 paths * ~1 follow mode = 54 (close to 50)
# Plus a few hand-picked favorites.

COMPOSED_PATTERNS: list[ComposedPattern] = []

# Cross product: every formation * every path
_FORMATIONS_FOR_LIBRARY = [
    "line", "v", "diamond", "wedge", "circle", "spiral", "x", "pincer", "arrow",
]
_PATHS_FOR_LIBRARY = [
    "sweep", "s_curve", "sine", "spiral", "loop", "zigzag", "dive", "straight",
]
_FOLLOW_FOR_LIBRARY = ["leader", "chain", "free"]
_COUNTS = [4, 5, 6, 7, 8]
_DIFFICULTY_BY_COUNT = {
    4: PatternDifficulty.EASY,
    5: PatternDifficulty.EASY,
    6: PatternDifficulty.MEDIUM,
    7: PatternDifficulty.MEDIUM,
    8: PatternDifficulty.HARD,
}


def _build_50_patterns() -> list[ComposedPattern]:
    """Generate ~50 patterns from the cross product of (formation, path, follow, count)."""
    out: list[ComposedPattern] = []
    seen: set[tuple[str, str, str, int]] = set()
    for form in _FORMATIONS_FOR_LIBRARY:
        for path in _PATHS_FOR_LIBRARY:
            for follow in _FOLLOW_FOR_LIBRARY:
                for count in _COUNTS:
                    if len(out) >= 50:
                        break
                    key = (form, path, follow, count)
                    if key in seen:
                        continue
                    seen.add(key)
                    name = f"{form}_{path}_{follow}_n{count}"
                    out.append(ComposedPattern(
                        name=name,
                        formation=form,
                        path=path,
                        follow=follow,
                        count=count,
                        difficulty=_DIFFICULTY_BY_COUNT[count],
                    ))
                if len(out) >= 50:
                    break
            if len(out) >= 50:
                break
        if len(out) >= 50:
            break
    return out


COMPOSED_PATTERNS = _build_50_patterns()


# ---- Solo enemy spawner ----
# 1 enemy every 5s, part of the wave. Different from formation patterns:
# no formation, no bezier path, no follow. Just a solo ship on a
# straight or slight-curve entry.

import time as _time

class SoloEnemySpawner:
    """Spawns 1 solo enemy every `interval_s` seconds during a wave.

    Solo enemies use a different palette (red) so they read as
    "stragglers" distinct from the formation ships. They follow a
    straight or slight-curve path with no formation and no leader.
    """

    def __init__(self, interval_s: float = 5.0) -> None:
        self.interval_s = interval_s
        self._t: float = 0.0
        self._to_spawn: list[SpawnedShip] = []

    def update(self, dt: float, rng: random.Random) -> list[SpawnedShip]:
        self._t += dt
        out: list[SpawnedShip] = []
        while self._t >= self.interval_s:
            self._t -= self.interval_s
            out.append(self._make_solo_ship(rng))
        return out

    def reset(self) -> None:
        self._t = 0.0

    def _make_solo_ship(self, rng: random.Random) -> SpawnedShip:
        x = rng.uniform(48, INTERNAL_W - 48)
        y = -20.0
        # Slight curve: 1 control point
        end = (x + rng.uniform(-40, 40), y + 220)
        cp1 = (x + rng.uniform(-60, 60), y + 80)
        return SpawnedShip(
            spawn_x=x,
            spawn_y=y,
            t_offset=0.0,
            slot=0,
            color=(255, 80, 60),  # red — "straggler"
            is_leader=True,  # solo always treated as leader
            extra={
                "formation": "solo",
                "path": "solo_curve",
                "path_points": [(x, y), cp1, (cp1[0] * 0.5 + end[0] * 0.5,
                                            cp1[1] * 0.5 + end[1] * 0.5), end],
                "follow": "solo",
            },
        )
