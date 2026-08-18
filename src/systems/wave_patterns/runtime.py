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
from src.movement.parallel_path import ParallelPathPair
from src.movement.orbital_path import OrbitalPath
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
    # BLOQUE 58.10: enemy ids that are the "leader" of their formation.
    # The draw layer highlights these with a glow ring.
    leader_enemy_ids: list[int] = field(default_factory=list)


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
    duration_s: float = 6.0,
) -> None:
    """Attach a bezier path follower to an enemy.

    The bezier is wrapped in a 1-segment HybridPath. PathFollower
    advances the enemy along the curve over time. The slot_dy is
    used to stagger the entry (the pattern's t_offset is converted
    to a small dy so the enemy enters the curve at the right point).

    BLOQUE 58.12: added `duration_s` parameter so patterns can override
    the default 6s with their own path duration.
    """
    from src.movement.hybrid import HybridPath
    bezier = BezierPath(
        p0=Point(p0[0], p0[1]),
        p1=Point(p1[0], p1[1]),
        p2=Point(p2[0], p2[1]),
        p3=Point(p3[0], p3[1]),
    )
    # Wrap in HybridPath. Duration controls how long the path takes
    # to traverse.
    path = HybridPath([bezier], segment_durations=[duration_s])
    follower = PathFollower(path, t_offset=t_offset)
    enemy.attach_path(follower, slot_dx=0.0, slot_dy=0.0)


def attach_multi_segment_path(
    enemy: Enemy,
    segments: list,
    segment_durations: list[float],
    t_offset: float = 0.0,
) -> None:
    """BLOQUE 58.12: attach a multi-segment HybridPath (compound bezier).

    Star Fox 64 enemy choreography often uses MULTIPLE chained bezier
    segments per ship (e.g., entry bezier + main sweep + exit swoop).
    This function attaches a HybridPath with N bezier segments.

    Args:
        enemy: the Enemy to attach the path to
        segments: list of (p0, p1, p2, p3) tuples (one per segment)
        segment_durations: list of float seconds (one per segment)
        t_offset: phase offset in seconds
    """
    from src.movement.hybrid import HybridPath
    beziers = []
    for seg in segments:
        p0, p1, p2, p3 = seg
        beziers.append(BezierPath(
            p0=Point(p0[0], p0[1]),
            p1=Point(p1[0], p1[1]),
            p2=Point(p2[0], p2[1]),
            p3=Point(p3[0], p3[1]),
        ))
    path = HybridPath(beziers, segment_durations=segment_durations)
    follower = PathFollower(path, t_offset=t_offset)
    enemy.attach_path(follower, slot_dx=0.0, slot_dy=0.0)


def attach_parallel_pair_path(
    enemy: Enemy,
    pair: ParallelPathPair,
    side: str,
    t_offset: float = 0.0,
) -> None:
    """BLOQUE 58.13: attach one of the two parallel paths to an enemy.

    Used by BEZIER_SWEEP and LEADER_FOLLOWER_CHAIN for SF64 pair dance.
    The ship follows either the top or the bottom path of the pair.
    """
    if side == "top":
        path = pair.get_top()
    elif side == "bot":
        path = pair.get_bot()
    else:
        raise ValueError(f"side must be 'top' or 'bot', got {side!r}")
    follower = PathFollower(path, t_offset=t_offset)
    enemy.attach_path(follower, slot_dx=0.0, slot_dy=0.0)


def attach_orbital_path(
    enemy: Enemy,
    orbital: OrbitalPath,
    t_offset: float = 0.0,
) -> None:
    """BLOQUE 58.13: attach an orbital path to an enemy.

    Used by OSCILLATING_BUTTERFLY. The ship orbits the center with the
    given phase offset.
    """
    follower = PathFollower(orbital.get_path(), t_offset=t_offset)
    enemy.attach_path(follower, slot_dx=0.0, slot_dy=0.0)


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

        # BLOQUE 58.10: track the leader enemy so the draw layer can
        # highlight it with a glow ring.
        if spawned.is_leader:
            runtime.leader_enemy_ids.append(id(e))

        # Attach bezier path if pattern provides control points
        if "p0" in spawned.extra:
            # BLOQUE 58.12: support custom path duration
            path_dur = spawned.extra.get("duration_s", 6.0)
            attach_bezier_path(
                e,
                spawned.extra["p0"],
                spawned.extra["p1"],
                spawned.extra["p2"],
                spawned.extra["p3"],
                t_offset=spawned.t_offset,
                duration_s=path_dur,
            )
        elif "segments" in spawned.extra:
            # BLOQUE 58.12: multi-segment path (compound bezier).
            # Used for more complex Star Fox 64 style choreography.
            segments = spawned.extra["segments"]
            seg_durs = spawned.extra.get("segment_durations", [3.0] * len(segments))
            attach_multi_segment_path(
                e, segments, seg_durs, t_offset=spawned.t_offset,
            )
        elif "parallel_pair" in spawned.extra:
            # BLOQUE 58.13: parallel pair path (BEZIER_SWEEP, LEADER_CHAIN)
            from src.systems.wave_patterns.runtime import attach_parallel_pair_path
            attach_parallel_pair_path(
                e,
                spawned.extra["parallel_pair"],
                spawned.extra.get("side", "top"),
                t_offset=spawned.t_offset,
            )
        elif "orbital" in spawned.extra:
            # BLOQUE 58.13: orbital path (OSCILLATING_BUTTERFLY)
            from src.systems.wave_patterns.runtime import attach_orbital_path
            attach_orbital_path(
                e,
                spawned.extra["orbital"],
                t_offset=spawned.t_offset,
            )

        # Apply color tint
        apply_color_tint(e, spawned.color)

        # V_FORMATION: keep rigid straight-line motion (no path follower)
        # The enemy's default update() handles straight line via vy=cfg.speed

    return runtime


def spawn_solo_ship(
    pool: EnemyPool,
    spawned: SpawnedShip,
) -> Optional[Enemy]:
    """BLOQUE 58.14.7: spawn a single enemy from a SoloEnemySpawner
    SpawnedShip record. Returns the Enemy or None if the pool is full.

    Unlike `spawn_pattern_wave`, this doesn't return a PatternRuntime
    because solo ships are independent (no shared duration, no
    pattern completion tracking). They're stragglers that just cross
    the screen and exit.

    The ship.extra dict is expected to carry `segments` and
    `segment_durations` keys (same format as composed patterns).
    """
    kind = pattern_kind_to_enemy_kind(spawned)
    e = pool.spawn(kind, spawned.spawn_x, spawned.spawn_y)
    if e is None:
        return None
    # Attach path follower if segments are provided
    if "segments" in spawned.extra:
        segments = spawned.extra["segments"]
        seg_durs = spawned.extra.get(
            "segment_durations", [4.0] * len(segments)
        )
        attach_multi_segment_path(
            e, segments, seg_durs, t_offset=spawned.t_offset,
        )
    apply_color_tint(e, spawned.color)
    return e


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
        WavePatternKind.OSCILLATING_BUTTERFLY: "BUTTERFLY",
    }.get(kind, kind.value.upper())


def draw_leader_glows(
    surface,
    runtime: "PatternRuntime | None",
    enemies_iter,
    time_s: float,
) -> None:
    """BLOQUE 58.10: Draw a pulsing glow ring around each leader enemy.

    Called from gameplay_runtime._draw_enemies() AFTER the enemies are
    drawn. The ring is drawn on the playfield so it's not clipped to
    the small sprite scratch surface.

    Args:
        surface: the playfield surface (320x480)
        runtime: the active PatternRuntime (or None)
        enemies_iter: iterable of live enemies (Enemy instances)
        time_s: current absolute time (for pulse animation)
    """
    if runtime is None or not runtime.leader_enemy_ids:
        return
    import math
    import pygame
    leader_ids = set(runtime.leader_enemy_ids)
    pulse = 0.5 + 0.5 * math.sin(time_s * 6.0)  # 0..1, ~1Hz pulse
    for e in enemies_iter:
        if id(e) not in leader_ids:
            continue
        # Pulsing ring radius 10..16, alpha 140..220
        radius = int(10 + pulse * 6)
        alpha = int(140 + pulse * 80)
        cx, cy = int(e.x), int(e.y)
        # Outer ring (cyan, bright)
        ring_surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surf, (140, 230, 255, alpha), (radius + 1, radius + 1), radius, width=2
        )
        surface.blit(ring_surf, (cx - radius - 1, cy - radius - 1))
        # Inner dot (white, small)
        dot_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (255, 255, 255, 220), (3, 3), 2)
        surface.blit(dot_surf, (cx - 3, cy - 3))
