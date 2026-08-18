"""Boss: ASTEROID_GUARDIAN with full mobility + 10x HP + ram charge attack.

Boss state model has two layers:

  * BossPhase  — broad progression driven by HP (ENTERING -> PHASE_1 ->
    PHASE_2 -> DYING -> DEAD). Same constants as before, but thresholds
    scale to the new 600 HP total.
  * BossAction — the boss's per-frame behavior inside a phase. Cycles
    IDLE_PATROL -> TELEGRAPH -> CHARGE -> RETREAT -> COOLDOWN -> IDLE.
    Telegraph aligns the boss's Y with the player and paints a bright
    line so the player knows the ram is coming. Charge dashes at 250
    px/s with thruster particles trailing behind. Retreat eases the
    boss back to the arena center. Cooldown is a short breathing room
    before the next cycle.

The boss deals 2 hearts per hit to the player (contact AND bullets)
to justify the 9-life max after collecting gold rings.

Boss ring drop (silver, 50% chance on 20 hits within 7s) is handled
by hit_streak tracking here; the gameplay scene calls
`on_player_damaged()` whenever the player takes damage from the boss
so the streak resets.
"""
from __future__ import annotations

import math
import random

import pygame
from src.movement import HybridPath, PathFollower

from stellar_horizon.waves.bezier_horizontal import path_boss_entry


class BossPhase:
    ENTERING = "entering"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    DYING = "dying"
    DEAD = "dead"


class BossAction:
    IDLE_PATROL = "idle_patrol"
    TELEGRAPH = "telegraph"
    CHARGE = "charge"
    RETREAT = "retreat"
    COOLDOWN = "cooldown"


class Boss:
    MAX_HP = 600
    PHASE_2_HP_THRESHOLD = 300
    DYING_DURATION_S = 1.5

    # Damage the boss deals to the player — both contact and bullets.
    DAMAGE_TO_PLAYER = 2

    # Charge cycle timing (seconds) — phase 2 is faster.
    PHASE_1_IDLE_S = 2.5
    PHASE_1_TELEGRAPH_S = 1.2
    PHASE_1_CHARGE_S = 0.5
    PHASE_1_RETREAT_S = 0.8
    PHASE_1_COOLDOWN_S = 5.0
    PHASE_2_IDLE_S = 1.5
    PHASE_2_TELEGRAPH_S = 1.0
    PHASE_2_CHARGE_S = 0.5
    PHASE_2_RETREAT_S = 0.7
    PHASE_2_COOLDOWN_S = 4.0
    # Charge movement speed (pixels/second). At 250 px/s the boss
    # crosses ~125 px in 0.5s — fast enough to threaten, slow enough
    # to dodge.
    CHARGE_SPEED_PX_S = 250.0
    # Retreat movement speed.
    RETREAT_SPEED_PX_S = 120.0
    # Telegraph align speed (smooth Y snap toward player).
    TELEGRAPH_ALIGN_PX_S = 90.0
    # Idle patrol speed.
    PATROL_SPEED_PX_S = 60.0

    # Bullet cadence during the whole cycle (telegraph + charge).
    BULLET_INTERVAL_S = 0.4

    # Boss ring drop (silver) — 50% chance on 20 hits within 7s.
    HIT_STREAK_THRESHOLD = 20
    HIT_STREAK_WINDOW_S = 7.0
    RING_DROP_CHANCE = 0.5

    # Arena bounds for boss movement.
    ARENA_X_MIN = 280.0
    ARENA_X_MAX = 450.0
    ARENA_Y_MIN = 80.0
    ARENA_Y_MAX = 180.0
    ARENA_CENTER_X = 350.0
    ARENA_CENTER_Y = 135.0

    HITBOX_W = 48
    HITBOX_H = 48

    __slots__ = (
        "x", "y", "hp", "max_hp", "phase", "entry_follower",
        "alive", "attack_cd", "dying_timer",
        # Beam (kept for backward compatibility — existing PHASE_2
        # visual stays).
        "beam_telegraph", "beam_telegraph_frames", "beam_active", "beam_active_frames",
        "beam_timer",
        # New action state machine.
        "action", "action_timer", "patrol_phase", "charge_target_x", "charge_target_y",
        "bullet_cd",
        # Hit streak for boss ring drop.
        "hit_streak", "hit_streak_start_time", "_now",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.hp: int = self.MAX_HP
        self.max_hp: int = self.MAX_HP
        self.phase: str = BossPhase.ENTERING
        self.entry_follower: PathFollower = PathFollower(HybridPath.from_segments([path_boss_entry()]))
        self.alive: bool = True
        self.attack_cd: float = 0.5
        self.dying_timer: float = 0.0
        self.beam_telegraph: bool = False
        self.beam_telegraph_frames: int = 0
        self.beam_active: bool = False
        self.beam_active_frames: int = 0
        self.beam_timer: float = 0.0
        # New state machine.
        self.action: str = BossAction.IDLE_PATROL
        self.action_timer: float = 0.0
        self.patrol_phase: float = 0.0
        self.charge_target_x: float = 0.0
        self.charge_target_y: float = 0.0
        self.bullet_cd: float = 0.0
        # Hit streak.
        self.hit_streak: int = 0
        self.hit_streak_start_time: float = 0.0
        # Scene time, written by update() so hit_streak can use it.
        self._now: float = 0.0

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
                # Seed patrol phase with a random offset so two boss
                # runs in a row don't trace the exact same path.
                self.patrol_phase = random.uniform(0.0, math.tau)
            return new_bullets
        if self.phase == BossPhase.DYING:
            self.dying_timer += dt
            if self.dying_timer >= self.DYING_DURATION_S:
                self.phase = BossPhase.DEAD
                self.alive = False
            return new_bullets
        # PHASE_1 / PHASE_2 — run the action cycle.
        # Cache scene time.
        self._now += dt
        is_phase2 = (self.phase == BossPhase.PHASE_2)
        # Decrement bullet cooldown and the active action timer.
        self.bullet_cd = max(0.0, self.bullet_cd - dt)
        self.action_timer -= dt
        # Per-action behavior.
        if self.action == BossAction.IDLE_PATROL:
            # Patrol the arena with a Lissajous-ish loop so the boss
            # feels alive even when not attacking.
            self.patrol_phase += dt * 0.9
            tx = self.ARENA_CENTER_X + math.sin(self.patrol_phase) * 70.0
            ty = self.ARENA_CENTER_Y + math.cos(self.patrol_phase * 0.7) * 30.0
            self._move_toward(tx, ty, self.PATROL_SPEED_PX_S, dt)
            if self.action_timer <= 0.0:
                self._enter_action(BossAction.TELEGRAPH)
        elif self.action == BossAction.TELEGRAPH:
            # Align Y to player, keep X inside arena. Stop shooting
            # (we wait for CHARGE), so telegraph is the visual warning.
            tx = max(self.ARENA_X_MIN,
                     min(self.ARENA_X_MAX, self.x))
            ty = max(self.ARENA_Y_MIN,
                     min(self.ARENA_Y_MAX, player.y))
            self._move_toward(tx, ty, self.TELEGRAPH_ALIGN_PX_S, dt)
            # 1 bullet per BULLET_INTERVAL_S during telegraph (warn
            # shots).
            if self.bullet_cd <= 0.0:
                b = self._spawn_aimed_bullet(player)
                if b is not None:
                    new_bullets.append(b)
                self.bullet_cd = self.BULLET_INTERVAL_S
            if self.action_timer <= 0.0:
                self._enter_action(BossAction.CHARGE)
        elif self.action == BossAction.CHARGE:
            # Charge at the player's last known position. We capture
            # the target on entry so a moving player has to dodge the
            # boss's committed dash, not the boss tracking them.
            if self.charge_target_x == 0.0 and self.charge_target_y == 0.0:
                self.charge_target_x = player.x
                self.charge_target_y = max(self.ARENA_Y_MIN,
                                           min(self.ARENA_Y_MAX, player.y))
            # Move toward the captured target at CHARGE_SPEED.
            self._move_toward(self.charge_target_x, self.charge_target_y,
                              self.CHARGE_SPEED_PX_S, dt)
            # Bullets during the dash (kept at 1/0.4s so the player
            # still has to dodge both).
            if self.bullet_cd <= 0.0:
                b = self._spawn_aimed_bullet(player)
                if b is not None:
                    new_bullets.append(b)
                self.bullet_cd = self.BULLET_INTERVAL_S
            if self.action_timer <= 0.0:
                self._enter_action(BossAction.RETREAT)
        elif self.action == BossAction.RETREAT:
            # Move back to arena center at RETREAT_SPEED.
            self._move_toward(self.ARENA_CENTER_X, self.ARENA_CENTER_Y,
                              self.RETREAT_SPEED_PX_S, dt)
            if self.action_timer <= 0.0:
                # Clear the charge target so the next CHARGE
                # re-captures the player's position.
                self.charge_target_x = 0.0
                self.charge_target_y = 0.0
                self._enter_action(BossAction.COOLDOWN)
        elif self.action == BossAction.COOLDOWN:
            # Just float; gentle drift.
            self.patrol_phase += dt * 0.3
            tx = self.ARENA_CENTER_X + math.sin(self.patrol_phase) * 25.0
            ty = self.ARENA_CENTER_Y + math.cos(self.patrol_phase * 0.5) * 12.0
            self._move_toward(tx, ty, self.PATROL_SPEED_PX_S, dt)
            if self.action_timer <= 0.0:
                self._enter_action(BossAction.IDLE_PATROL)
        # Phase 2 beam attack — kept from the original design (rare
        # extra hazard). Cooldown is shorter in phase 2.
        if is_phase2:
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

    def _enter_action(self, action: str) -> None:
        """Transition to a new action state and reset its timer."""
        self.action = action
        is_phase2 = (self.phase == BossPhase.PHASE_2)
        if action == BossAction.IDLE_PATROL:
            self.action_timer = self.PHASE_2_IDLE_S if is_phase2 else self.PHASE_1_IDLE_S
        elif action == BossAction.TELEGRAPH:
            self.action_timer = self.PHASE_2_TELEGRAPH_S if is_phase2 else self.PHASE_1_TELEGRAPH_S
        elif action == BossAction.CHARGE:
            self.action_timer = self.PHASE_2_CHARGE_S if is_phase2 else self.PHASE_1_CHARGE_S
        elif action == BossAction.RETREAT:
            self.action_timer = self.PHASE_2_RETREAT_S if is_phase2 else self.PHASE_1_RETREAT_S
        elif action == BossAction.COOLDOWN:
            self.action_timer = self.PHASE_2_COOLDOWN_S if is_phase2 else self.PHASE_1_COOLDOWN_S
        # Reset bullet cooldown so the first shot after each
        # transition fires after BULLET_INTERVAL_S, not immediately.
        self.bullet_cd = self.BULLET_INTERVAL_S

    def _move_toward(self, tx: float, ty: float, speed: float, dt: float) -> None:
        """Move toward (tx, ty) at the given speed, clamped to the arena."""
        dx = tx - self.x
        dy = ty - self.y
        d = math.hypot(dx, dy)
        if d < 1e-3:
            return
        step = speed * dt
        if step >= d:
            self.x, self.y = tx, ty
        else:
            self.x += dx / d * step
            self.y += dy / d * step
        # Clamp to arena in case the target was outside (e.g. a
        # telegraph align point).
        self.x = max(self.ARENA_X_MIN, min(self.ARENA_X_MAX, self.x))
        self.y = max(self.ARENA_Y_MIN, min(self.ARENA_Y_MAX, self.y))

    def _spawn_aimed_bullet(self, player) -> "EnemyBullet | None":
        """Spawn a damage=2 aimed bullet at the player."""
        from stellar_horizon.entities.bullet import EnemyBullet
        b = EnemyBullet()
        b.spawn(self.x, self.y, player.x, player.y)
        b.damage = self.DAMAGE_TO_PLAYER
        return b

    def take_damage(self, amount: int) -> None:
        if self.phase in (BossPhase.ENTERING, BossPhase.DYING, BossPhase.DEAD):
            return
        self.hp = max(0, self.hp - amount)
        # Hit streak tracking for the boss ring drop.
        if self.hit_streak == 0:
            self.hit_streak_start_time = self._now
        self.hit_streak += 1
        if self.hp == 0:
            self.phase = BossPhase.DYING
            self.dying_timer = 0.0
        elif self.hp <= self.PHASE_2_HP_THRESHOLD and self.phase == BossPhase.PHASE_1:
            self.phase = BossPhase.PHASE_2
            # Reset cycle on phase change so the new phase's faster
            # timers take over cleanly.
            self._enter_action(BossAction.IDLE_PATROL)

    def on_player_damaged(self) -> None:
        """Called by the gameplay scene when the player takes damage
        from the boss (any source: contact, bullet). Resets the
        hit-streak so the player has to land 20 hits in a row again.
        """
        self.hit_streak = 0
        self.hit_streak_start_time = self._now

    def should_drop_ring(self) -> bool:
        """Return True if the boss should drop a silver ring right now.

        Trigger: 20+ hits within 7 seconds. Returns True once and only
        once per qualifying streak (the caller must reset the streak
        if it does drop).
        """
        if self.hit_streak < self.HIT_STREAK_THRESHOLD:
            return False
        # The hit_streak threshold check above guarantees we have a
        # valid streak (the first hit set hit_streak_start_time).
        if (self._now - self.hit_streak_start_time) > self.HIT_STREAK_WINDOW_S:
            # Window expired — reset and require another 20 hits.
            self.hit_streak = 0
            return False
        return True

    def consume_ring_drop(self) -> bool:
        """Roll the 50% drop chance and, if it succeeds, consume the
        streak so it doesn't fire twice. Returns True on success.
        """
        if not self.should_drop_ring():
            return False
        roll = random.random() < self.RING_DROP_CHANCE
        # Always reset the streak after a qualifying window so the
        # next ring requires a fresh 20-in-7.
        self.hit_streak = 0
        return roll

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.HITBOX_W // 2), int(self.y - self.HITBOX_H // 2),
                           self.HITBOX_W, self.HITBOX_H)

    def score_value(self) -> int:
        return 5000
