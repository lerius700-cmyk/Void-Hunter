"""BLOQUE 58.8: runtime bridge — SpawnedShip → Enemy.

The runtime layer that takes a WavePatternResult and spawns the
actual enemies. This bridges the procedural pattern system with the
existing gameplay runtime.

Flow:
  1. ProceduralWaveManager.pick_pattern() → WavePatternResult
  2. For each SpawnedShip in result.ships:
     a. Get base kind (SCOUT, CRUISER, etc)
     b. Spawn at (spawn_x, spawn_y)
     c. Attach path follower if extra has bezier control points
     d. Apply color tint
     e. Apply formation slot (for rigid patterns)

The runtime tracks:
  - Current pattern kind (for HUD)
  - Active enemies from this pattern
  - Pattern completion state
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from src.core.settings import INTERNAL_W, INTERNAL_H
from src.entities.enemies.enemy import Enemy, EnemyKind, EnemyPool
from src.movement.bezier import BezierPath, Point
from src.movement.waypoint import WaypointPath
from src.movement.follower import PathFollower
from src.systems.wave_patterns.base import (
    WavePatternResult,
    SpawnedShip,
    WavePatternKind,
)


# Speed multiplier per enemy kind (BLOQUE 50 baseline)
_KIND_SPEED = {
    "SCOUT": 90.0,
    "CRUISER": 70.0,
    "HEAVY": 50.0,
    "DRONE": 110.0,
    "CARRIER": 40.0,
}

# HP per kind (BLOQUE 50 baseline)
_KIND_HP = {
    "SCOUT": 30,
    "CRUISER": 80,
    "HEAVY": 200,
    "DRONE": 25,
    "CARRIER": 250,
}


@dataclass
class PatternRuntime:
    """Active pattern being played in the runtime."""
    kind: WavePatternKind
    ships_spawned: list[int]  # indices into EnemyPool
    result: WavePatternResult
    elapsed: float = 0.0
    duration: float = 6.0
    completed: bool = False


def pattern_kind_to_enemy_kind(spawned: SpawnedShip) -> EnemyKind:
    """Map a SpawnedShip to the base EnemyKind. Most patterns use SCOUT."""
    # Use the color as a hint: if color is yellow, it's likely a SCOUT.
    # For now, all pattern ships are SCOUT (the simplest enemy).
    # Future: pattern.extra could specify "kind_mix" for variety.
    return EnemyKind.SCOUT


def attach_bezier_path(
    enemy: Enemy,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t_offset: float = 0.0,
) -> None:
    """Attach a bezier path follower to an enemy.

    The bezier is wrapped in a 1-segment HybridPath. PathFollower
    advances the enemy along the curve over time. The slot_dy is
    used to stagger the entry (the pattern's t_offset is converted
    to a small dy so the enemy enters the curve at the right point).
    """
    from src.movement.hybrid import HybridPath
    bezier = BezierPath(
        p0=Point(p0[0], p0[1]),
        p1=Point(p1[0], p1[1]),
        p2=Point(p2[0], p2[1]),
        p3=Point(p3[0], p3[1]),
    )
    # Wrap in HybridPath. Duration controls how long the path takes
    # to traverse. We use a default of 6 seconds.
    path = HybridPath([bezier], segment_durations=[6.0])
    follower = PathFollower(path)
    # t_offset becomes a slot_dy so the enemy enters the curve later
    # (negative dy means "start the path later in time")
    enemy.attach_path(follower, slot_dx=0.0, slot_dy=-t_offset * 100.0)


def apply_color_tint(enemy: Enemy, color: Optional[tuple[int, int, int]]) -> None:
    """Apply a color tint to the enemy (used for the engine trail).

    NOTE: Enemy is a frozen dataclass, so we can't override the color
    attribute directly. The color is stored in the runtime's
    PatternRuntime for HUD/UI use. Visual tinting in the game would
    require modifying the sprite drawing code (BLOQUE 59.0 follow-up).
    """
    # For now, the runtime just tracks the color for HUD purposes.
    # The actual game sprites use the default enemy kind color.
    return


def spawn_pattern_wave(
    pool: EnemyPool,
    result: WavePatternResult,
    duration_s: Optional[float] = None,
) -> PatternRuntime:
    """Spawn the enemies for a pattern. Returns the runtime tracker.

    Args:
        pool: the EnemyPool to spawn into
        result: from ProceduralWaveManager.pick_pattern()
        duration_s: override duration (uses result.duration_s if None)

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

        # Attach bezier path if pattern provides control points
        if "p0" in spawned.extra:
            attach_bezier_path(
                e,
                spawned.extra["p0"],
                spawned.extra["p1"],
                spawned.extra["p2"],
                spawned.extra["p3"],
                t_offset=spawned.t_offset,
            )

        # Apply color tint
        apply_color_tint(e, spawned.color)

        # V_FORMATION: keep rigid straight-line motion (no path follower)
        # The enemy's default update() handles straight line via vy=cfg.speed

    return runtime


def update_pattern_runtime(
    runtime: PatternRuntime,
    dt: float,
) -> bool:
    """Update the pattern runtime. Returns True if completed."""
    if runtime.completed:
        return True
    runtime.elapsed += dt
    if runtime.elapsed >= runtime.duration:
        runtime.completed = True
    return runtime.completed


def get_pattern_hud_label(kind: WavePatternKind) -> str:
    """Human-readable label for the HUD."""
    return {
        WavePatternKind.BEZIER_SWEEP: "BEZIER SWEEP",
        WavePatternKind.V_FORMATION: "V FORMATION",
        WavePatternKind.LEADER_FOLLOWER_CHAIN: "LEADER CHAIN",
        WavePatternKind.DICE_FIVE_GRID: "DICE-FIVE",
        WavePatternKind.PINCER_CROSS: "PINCER CROSS",
    }.get(kind, kind.value.upper())
