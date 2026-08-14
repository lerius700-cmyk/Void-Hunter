"""FormationPathSpec \u2014 bridges FlightFormation + HybridPath into spawnable enemies (BLOQUE 58.6x).

A spec is a recipe: "spawn N enemies, each following the same HybridPath
but offset by the formation's slot, with a stagger between them."

It is the unit that the roguelike wave generator emits. The runtime then
calls `spec.build()` to materialize a list of ready-to-spawn Enemies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.entities.enemies.enemy import Enemy
from src.entities.enemies.enemy import EnemyKind
from src.movement.follower import PathFollower
from src.movement.formation import FlightFormation
from src.movement.hybrid import HybridPath


@dataclass
class FormationPathSpec:
    """One formation/path combo ready to spawn.

    Args:
        formation:   the shape (V, line, diamond, \u2026)
        path:        the motion path the formation's center follows
        enemy_kind:  what kind of enemy each slot is
        spawn_interval_s: time between successive slot spawns (stagger)
        spawn_t0_s:  global time offset (default 0; useful for chaining)
    """

    formation: FlightFormation
    path: HybridPath
    enemy_kind: Optional[EnemyKind] = None
    spawn_interval_s: float = 0.15
    spawn_t0_s: float = 0.0
    # Optional per-slot stagger override (advanced; defaults to spawn_interval_s * i)
    spawn_stagger: list[float] = field(default_factory=list)

    def build(self) -> list[Enemy]:
        """Materialize one Enemy per slot, each with a fresh PathFollower.

        The returned Enemies are not yet `active=True`; the wave manager
        is expected to flip `active` when it spawns them at the right time.
        """
        n = self.formation.count
        if self.spawn_stagger and len(self.spawn_stagger) != n:
            raise ValueError(
                f"spawn_stagger length ({len(self.spawn_stagger)}) != "
                f"formation count ({n})"
            )
        enemies: list[Enemy] = []
        for i, (dx, dy) in enumerate(self.formation.offsets):
            e = Enemy()
            e.on_spawn()
            e.kind = self.enemy_kind if self.enemy_kind is not None else EnemyKind.SCOUT
            # Path follower: each slot gets its OWN follower (so the
            # enemy can advance independently and not interfere with
            # formation-center timing).
            follower = PathFollower(self.path)
            e.attach_path(follower, slot_dx=dx, slot_dy=dy)
            enemies.append(e)
        return enemies

    def spawn_timestamps(self) -> list[float]:
        """The t0 (relative to wave start) when each slot should spawn."""
        n = self.formation.count
        if self.spawn_stagger:
            return [self.spawn_t0_s + s for s in self.spawn_stagger]
        return [self.spawn_t0_s + i * self.spawn_interval_s for i in range(n)]
