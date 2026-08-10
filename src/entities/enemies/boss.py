"""Boss entity — 4 bosses with 4-phase FSM (BLOQUE 9).

Per GDD §5:
  - GOLIATH (Act 1 sub-boss, 32x18, 2 phases, 800 HP)
  - HYDRA   (Act 2 sub-boss, 36x20, 3 phases including enraged, 1400 HP)
  - PHANTOM (Act 3a sub-boss, 40x22, 2 phases, 2000 HP)
  - NEMESIS (Act 3b final, 48x28, 4 phases including DESESPERACIÓN, 5000 HP)

Phase transitions: full-screen flash 2f + shake trauma 0.5 + radial sparks
+ hitstop 6 + BGM section change. Hitbox: 70% forgiving.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W
from src.systems.pool import Pool


class BossId(Enum):
    GOLIATH = "goliath"
    HYDRA = "hydra"
    PHANTOM = "phantom"
    NEMESIS = "nemesis"


# Per-boss config
@dataclass(frozen=True)
class _BossConfig:
    name: str
    width: int
    height: int
    max_hp: int
    score: int
    color: tuple[int, int, int]
    speed: float          # px/s
    # Phase thresholds (HP%): 1->2, 2->3, 3->4
    phase_thresholds: tuple[float, ...]
    # Anchor position (x=center, y=where it sits)
    anchor_x: float
    anchor_y: float
    attack_cooldown_s: float


BOSS_CONFIGS: dict[BossId, _BossConfig] = {
    BossId.GOLIATH: _BossConfig(
        name="GOLIATH", width=32, height=18, max_hp=400, score=5000,
        color=(200, 200, 220), speed=30.0,
        phase_thresholds=(0.66,),
        anchor_x=INTERNAL_W / 2, anchor_y=80.0,
        attack_cooldown_s=1.5,
    ),
    BossId.HYDRA: _BossConfig(
        name="HYDRA", width=36, height=20, max_hp=700, score=8000,
        color=(180, 100, 220), speed=20.0,
        phase_thresholds=(0.66, 0.33),
        anchor_x=INTERNAL_W / 2, anchor_y=70.0,
        attack_cooldown_s=1.4,
    ),
    BossId.PHANTOM: _BossConfig(
        name="PHANTOM", width=40, height=22, max_hp=1000, score=12000,
        color=(120, 80, 220), speed=70.0,
        phase_thresholds=(0.66,),
        anchor_x=INTERNAL_W / 2, anchor_y=80.0,
        attack_cooldown_s=2.0,
    ),
    BossId.NEMESIS: _BossConfig(
        name="NEMESIS", width=48, height=28, max_hp=2500, score=20000,
        color=(255, 200, 80), speed=0.0,
        phase_thresholds=(0.75, 0.50, 0.25),
        anchor_x=INTERNAL_W / 2, anchor_y=60.0,
        attack_cooldown_s=2.5,
    ),
}


@dataclass
class Boss:
    """Single boss instance."""
    active: bool = False
    id: BossId = BossId.GOLIATH
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    hp: int = 1
    max_hp: int = 1
    phase: int = 1
    fire_cd: float = 0.0
    # Movement oscillation (sine)
    move_t: float = 0.0
    # Arena shrink (NEMESIS P4)
    arena_shrink_pct: float = 0.0
    # BGM tempo multiplier
    bgm_tempo_mult: float = 1.0
    # Hitbox shrink (NEMESIS P4: 50%)
    hitbox_factor: float = 0.7
    # Output events
    on_phase_transition: int = 0  # 0 = none; otherwise new phase number
    on_attack: int = 0  # attack index fired this frame
    on_death: bool = False
    # Internal
    _phase_reported: int = 1

    def on_spawn(self) -> None:
        self.on_phase_transition = 0
        self.on_attack = 0
        self.on_death = False
        self._phase_reported = 1
        self.move_t = 0.0
        self.arena_shrink_pct = 0.0
        self.bgm_tempo_mult = 1.0
        self.hitbox_factor = 0.7
        self.vx = 0.0
        self.vy = 0.0

    def on_release(self) -> None:
        pass

    def hitbox(self) -> pygame.Rect:
        cfg = BOSS_CONFIGS[self.id]
        w = int(cfg.width * self.hitbox_factor)
        h = int(cfg.height * self.hitbox_factor)
        return pygame.Rect(int(self.x - w // 2), int(self.y - h // 2), w, h)

    def apply_damage(self, amount: int) -> bool:
        """Returns True if this hit was lethal."""
        if not self.active:
            return False
        self.hp = max(0, self.hp - amount)
        # Check phase transition
        self._check_phase()
        if self.hp <= 0:
            self.on_death = True
            return True
        return False

    def _check_phase(self) -> None:
        """Compute current phase from HP% and emit transition event if changed.

        Phase = 1 + (count of thresholds the current HP% is at or below).
        Full HP → phase 1; HP <= last threshold → phase 1 + N.
        """
        if self.max_hp <= 0:
            return
        pct = self.hp / self.max_hp
        cfg = BOSS_CONFIGS[self.id]
        crossed = sum(1 for t in cfg.phase_thresholds if pct <= t)
        new_phase = 1 + crossed
        if new_phase != self._phase_reported:
            self._phase_reported = new_phase
            self.phase = new_phase
            self.on_phase_transition = new_phase
            # NEMESIS P4 special: arena shrink + tempo up + hitbox reduction
            if self.id == BossId.NEMESIS and new_phase == 4:
                self.arena_shrink_pct = 0.20
                self.bgm_tempo_mult = 1.20
                self.hitbox_factor = 0.5

    def update(self, dt: float) -> None:
        """Advance movement, fire cooldown, attack selection."""
        if dt <= 0.0:
            return
        # Sine oscillation around anchor
        cfg = BOSS_CONFIGS[self.id]
        if cfg.speed > 0.0:
            self.move_t += dt
            self.x = cfg.anchor_x + math.sin(self.move_t * 0.5) * 80.0
        # Fire cooldown
        if self.fire_cd > 0.0:
            self.fire_cd -= dt

    def select_attack(self) -> int:
        """Pick an attack from the phase's pool. Returns attack index (0..7).

        Attack catalog (8 patterns per GDD §5):
          0 = aimed
          1 = 3-spread
          2 = 5-spread
          3 = ring
          4 = spiral
          5 = laser beam
          6 = charge-and-release
          7 = wall-of-bullets
        """
        if self.fire_cd > 0.0:
            return -1
        cfg = BOSS_CONFIGS[self.id]
        # BLOQUE 52: attack 8 = "spear throw", only handled for GOLIATH
        # in _spawn_boss_attack. For other bosses, attack 8 is a no-op
        # so we exclude it from their pools.
        if self.id == BossId.GOLIATH:
            # Phase pools
            if self.phase == 1:
                pool = [0, 1, 8]  # aimed, 3-spread, spear throw
            elif self.phase == 2:
                pool = [0, 1, 3, 8]  # + ring + spear throw (more variety)
            else:
                pool = [0, 1, 3, 8]
        else:
            # Phase pools (original)
            if self.phase == 1:
                pool = [0, 1]  # aimed, 3-spread
            elif self.phase == 2:
                pool = [0, 1, 3]  # + ring
            elif self.phase == 3:
                pool = [1, 2, 3, 4, 5]  # most patterns
            else:  # phase 4 (NEMESIS only)
                pool = [0, 1, 2, 3, 4, 5, 6, 7]  # all 8
        # Pseudo-random selection based on phase + move_t (deterministic for tests)
        import random
        rng = random.Random(int(self.move_t * 10) + self.phase * 100)
        idx = rng.choice(pool)
        self.fire_cd = cfg.attack_cooldown_s
        self.on_attack = idx
        return idx


class BossPool:
    """Pool of Boss instances. Capacity 4 (one of each kind)."""

    def __init__(self) -> None:
        self._pool: Pool[Boss] = Pool(Boss, 4)

    @property
    def pool(self) -> Pool[Boss]:
        return self._pool

    @property
    def active_count(self) -> int:
        return self._pool.active_count

    def spawn(self, boss_id: BossId) -> Boss | None:
        b = self._pool.acquire()
        if b is None:
            return None
        b.on_spawn()
        b.id = boss_id
        cfg = BOSS_CONFIGS[boss_id]
        b.x = cfg.anchor_x
        b.y = cfg.anchor_y
        b.max_hp = cfg.max_hp
        b.hp = cfg.max_hp
        b.phase = 1
        b._phase_reported = 1
        b.fire_cd = 0.0
        b.active = True
        return b

    def release(self, b: Boss) -> None:
        self._pool.release(b)

    def release_all(self) -> None:
        self._pool.release_all()
