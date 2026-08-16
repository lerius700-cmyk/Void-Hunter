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
