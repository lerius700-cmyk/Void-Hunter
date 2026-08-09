"""Player ship with 7-state FSM (BLOQUE 6).

States: IDLE, MOVE, SHOOT, CHARGE (build+fire), DASH, HIT, DEAD.

Transitions (per GDD §2):
  - IDLE -> MOVE    (input lateral)
  - MOVE -> IDLE    (input released + 0.05s settle)
  - IDLE/MOVE -> SHOOT  (fire input + cd_ready, 0.10s timer)
  - SHOOT/IDLE -> CHARGE  (hold > 0.5s, builds L1/L2/L3 at 0.5/1.0/1.5s)
  - CHARGE -> IDLE  (release + fire 0.20s anim, or 1.5s timeout -> SHOOT)
  - any -> DASH     (dash input, 0.18s, i-frames)
  - any -> HIT      (take_damage, 0.30s, 60f invuln)
  - HIT -> DEAD     (lives=0)
  - DEAD -> respawn (1.20s) -> IDLE (1s invuln) or game_over
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame

from src.core.settings import (
    INTERNAL_H,
    INTERNAL_W,
    PLAYER_BOMBS,
    PLAYER_BOMBS_MAX,
    PLAYER_DASH_DURATION_S,
    PLAYER_DASH_IFRAMES,
    PLAYER_DASH_SPEED,
    PLAYER_DEATH_DURATION_S,
    PLAYER_FIRE_COOLDOWN_S,
    PLAYER_INVULN_FRAMES,
    PLAYER_LIVES,
    PLAYER_NOSE_LERP_PER_S,
    PLAYER_RESPAWN_INVULN_S,
    PLAYER_SPEED,
)


class PlayerState(Enum):
    IDLE = "idle"
    MOVE = "move"
    SHOOT = "shoot"
    CHARGE = "charge"
    DASH = "dash"
    HIT = "hit"
    DEAD = "dead"


# Charge thresholds (seconds)
CHARGE_L1_S = 0.5
CHARGE_L2_S = 1.0
CHARGE_L3_S = 1.5
CHARGE_TIMEOUT_S = 1.5
CHARGE_FIRE_ANIM_S = 0.20

# Settle time when releasing lateral input
MOVE_SETTLE_S = 0.05

# Hit duration
HIT_DURATION_S = 0.30
HITSTOP_FRAMES_ON_HIT = 3


@dataclass
class Player:
    """Player ship entity. State, position, velocity, lives, bombs."""
    # Position
    x: float = INTERNAL_W / 2
    y: float = INTERNAL_H - 60
    vx: float = 0.0
    vy: float = 0.0
    # Tilt
    tilt: float = 0.0  # degrees, target; current is computed
    current_tilt: float = 0.0
    # BLOQUE 32: nose angle (rotation of the ship's "trompa")
    # 360° rotation, world-relative movement (WASD is screen-space).
    # Driven by mouse position; only updates target while moving (BLOQUE 32
    # "rotate-while-moving" design — keeps the ship stable when stopped
    # so the player can stand their ground without the nose drifting).
    nose_angle: float = 0.0  # target angle in degrees, 0..360 (0 = up, 90 = right)
    current_nose_angle: float = 0.0  # smoothed angle for rendering
    # State
    state: PlayerState = PlayerState.IDLE
    state_timer: float = 0.0
    # Charge
    charge_time: float = 0.0
    # Dash
    dash_dir_x: float = 0.0
    dash_dir_y: float = -1.0  # default upward
    dash_iframes_left: int = 0
    # Hit
    invuln_frames: int = 0
    # Lifecycle
    lives: int = PLAYER_LIVES
    bombs: int = PLAYER_BOMBS
    bombs_max: int = PLAYER_BOMBS_MAX
    hp: int = 3
    hp_max: int = 3
    # Fire cooldown
    fire_cd: float = 0.0
    # Death/respawn
    death_timer: float = 0.0
    respawn_invuln: float = 0.0
    # After-image trail
    afterimage: list[tuple[float, float, float]] = field(default_factory=list)  # (x, y, age)
    AFTERIMAGE_LIFE = 0.13  # seconds
    # Inputs (set externally each frame)
    input_left: bool = False
    input_right: bool = False
    input_up: bool = False
    input_down: bool = False
    input_fire: bool = False
    input_dash: bool = False
    input_bomb: bool = False
    # Output signals (consumed by WeaponSystem etc.)
    wants_to_shoot: bool = False
    wants_to_charge_release: bool = False
    wants_to_dash: bool = False
    wants_to_bomb: bool = False
    # Damage received this frame (set by collision system)
    damage_taken: int = 0
    # HP system
    is_dead: bool = False
    is_game_over: bool = False
    # Internal: charge-firing flag (set when release happens mid-charge)
    _charge_fired: bool = False

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def reset(self) -> None:
        """Full reset to spawn state. Used on game start / continue."""
        self.x = INTERNAL_W / 2
        self.y = INTERNAL_H - 60
        self.vx = 0.0
        self.vy = 0.0
        self.tilt = 0.0
        self.current_tilt = 0.0
        self.state = PlayerState.IDLE
        self.state_timer = 0.0
        self.charge_time = 0.0
        self.dash_iframes_left = 0
        self.invuln_frames = 0
        # BLOQUE 28: easy mode gives more lives + bombs
        import os as _os
        if _os.environ.get("VOID_HUNTER_EASY", "0") == "1":
            self.lives = 9
            self.bombs = 4
            self.bombs_max = 5
        else:
            self.lives = PLAYER_LIVES
            self.bombs = PLAYER_BOMBS
            self.bombs_max = PLAYER_BOMBS_MAX
        self.hp = 3
        self.hp_max = 3
        self.fire_cd = 0.0
        self.death_timer = 0.0
        self.respawn_invuln = 0.0
        self.afterimage.clear()
        self.wants_to_shoot = False
        self.wants_to_charge_release = False
        self.wants_to_dash = False
        self.wants_to_bomb = False
        self.damage_taken = 0
        self.is_dead = False
        self.is_game_over = False
        # BLOQUE 32: nose angle starts pointing up (0°)
        self.nose_angle = 0.0
        self.current_nose_angle = 0.0

    def take_damage(self, amount: int = 1) -> bool:
        """Apply damage if not in i-frames. Returns True if hit applied."""
        if self.invuln_frames > 0 or self.dash_iframes_left > 0:
            return False
        if self.state == PlayerState.DEAD:
            return False
        self.hp -= amount
        self.damage_taken = max(self.damage_taken, amount)
        return True

    @property
    def is_invulnerable(self) -> bool:
        return self.invuln_frames > 0 or self.dash_iframes_left > 0

    @property
    def hitbox(self) -> pygame.Rect:
        """Real hitbox = 70% of sprite (forgiving per GDD §5)."""
        return pygame.Rect(int(self.x - 9), int(self.y - 6), 18, 12)

    # -----------------------------------------------------------------------
    # Per-frame update
    # -----------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Advance FSM + position. Outputs `wants_to_*` flags for systems."""
        if dt <= 0.0:
            return
        # Always clamp (defensive: covers spawn at any position, debug overrides)
        self._clamp_position()
        # Reset per-frame outputs
        self.wants_to_shoot = False
        self.wants_to_charge_release = False
        self.wants_to_dash = False
        self.wants_to_bomb = False
        # Invuln countdown (always)
        if self.invuln_frames > 0:
            self.invuln_frames = max(0, self.invuln_frames - 1)
        if self.dash_iframes_left > 0:
            self.dash_iframes_left = max(0, self.dash_iframes_left - 1)
        # Fire cooldown
        if self.fire_cd > 0.0:
            self.fire_cd = max(0.0, self.fire_cd - dt)
        # Track charge_time when input_fire is held in IDLE/MOVE only.
        # Don't reset to 0 here — _update_idle / _update_charge own the
        # charge_time lifecycle.
        if self.input_fire and self.state in (PlayerState.IDLE, PlayerState.MOVE):
            self.charge_time += dt
        elif self.state in (PlayerState.IDLE, PlayerState.MOVE):
            # Released while in IDLE/MOVE → reset
            self.charge_time = 0.0
        # Afterimage decay
        if self.afterimage:
            new_trail: list[tuple[float, float, float]] = []
            for tx, ty, age in self.afterimage:
                new_age = age + dt
                if new_age < self.AFTERIMAGE_LIFE:
                    new_trail.append((tx, ty, new_age))
            self.afterimage = new_trail
        # BLOQUE 32: nose angle lerp (only when moving, per user spec)
        # When the player is moving, smoothly track nose_angle target.
        # When stopped, freeze (current_nose_angle stays where it is).
        moving = (self.state == PlayerState.MOVE
                  and (self.input_left or self.input_right
                       or self.input_up or self.input_down))
        if moving:
            # Lerp the current_nose_angle toward nose_angle, shortest path
            target = self.nose_angle
            cur = self.current_nose_angle
            diff = (target - cur + 540.0) % 360.0 - 180.0  # signed shortest
            step = PLAYER_NOSE_LERP_PER_S * dt
            if abs(diff) <= step:
                self.current_nose_angle = target
            else:
                self.current_nose_angle = (cur + (step if diff > 0 else -step)) % 360.0
        # State-specific update
        if self.state == PlayerState.IDLE:
            self._update_idle(dt)
        elif self.state == PlayerState.MOVE:
            self._update_move(dt)
        elif self.state == PlayerState.SHOOT:
            self._update_shoot(dt)
        elif self.state == PlayerState.CHARGE:
            self._update_charge(dt)
        elif self.state == PlayerState.DASH:
            self._update_dash(dt)
        elif self.state == PlayerState.HIT:
            self._update_hit(dt)
        elif self.state == PlayerState.DEAD:
            self._update_dead(dt)
        # Tilt smoothing
        self.current_tilt += (self.tilt - self.current_tilt) * min(1.0, dt * 12.0)
        # BLOQUE 29: nose angle smoothing
        if hasattr(self, "nose_angle"):
            self.current_nose_angle += (
                (self.nose_angle - self.current_nose_angle) * min(1.0, dt * 12.0)
            )
        # Apply damage if accumulated
        if self.damage_taken > 0 and self.state != PlayerState.DEAD:
            self._enter_hit()
            self.damage_taken = 0
        # State timer advance
        self.state_timer += dt

    # -----------------------------------------------------------------------
    # State updates
    # -----------------------------------------------------------------------
    def _update_idle(self, dt: float) -> None:
        # Dash takes priority over move (dash from idle)
        if self.input_dash:
            self._enter_dash()
            return
        # Bomb
        if self.input_bomb and self.bombs > 0:
            self._consume_bomb()
            return
        # Charge takes priority over shoot (held > 0.5s = charge)
        if self.input_fire and self.charge_time >= CHARGE_L1_S:
            self._enter_charge()
            return
        # BLOQUE 29: any directional input (W/A/S/D or arrows) → MOVE
        if self.input_left or self.input_right or self.input_up or self.input_down:
            self._enter_move()
            return
        # Fire input
        if self.input_fire:
            if self.fire_cd <= 0.0:
                self.wants_to_shoot = True
                self.fire_cd = PLAYER_FIRE_COOLDOWN_S
                self._enter_shoot()
            return
        # No input → stay
        self.vx = 0.0
        self.vy = 0.0
        self.tilt = 0.0
        # Always clamp (defensive)
        self._clamp_position()

    def _update_move(self, dt: float) -> None:
        # Dash takes priority
        if self.input_dash:
            self._enter_dash()
            return
        # Bomb
        if self.input_bomb and self.bombs > 0:
            self._consume_bomb()
            return
        # Charge before shoot
        if self.input_fire and self.charge_time >= CHARGE_L1_S:
            self._enter_charge()
            return
        # BLOQUE 32: world-relative movement.
        # WASD maps to screen-space axes regardless of ship facing.
        #   W = up screen, S = down, A = left, D = right.
        # Ship's facing is set by mouse (for aiming only).
        target_vx = 0.0
        target_vy = 0.0
        speed = PLAYER_SPEED
        # Compute desired velocity from WASD (screen-space)
        if self.input_left:
            target_vx -= speed
        if self.input_right:
            target_vx += speed
        if self.input_up:
            target_vy -= speed
        if self.input_down:
            target_vy += speed
        # BLOQUE 32: snappier acceleration for responsive feel
        accel = min(1.0, dt * 18.0)
        self.vx += (target_vx - self.vx) * accel
        self.vy += (target_vy - self.vy) * accel
        # Tilt: visual feedback based on horizontal speed (kept for visual juice)
        self.tilt = -15.0 if self.vx < -10 else (15.0 if self.vx > 10 else 0.0)
        # Position integration
        self.x += self.vx * dt
        self.y += self.vy * dt
        self._clamp_position()
        # Settle: if no direction input → back to IDLE
        if not (self.input_left or self.input_right or self.input_up or self.input_down):
            if self.state_timer >= MOVE_SETTLE_S:
                self._enter_idle()
                return
        # Fire (L1) — same as before
        if self.input_fire and self.fire_cd <= 0.0:
            self.wants_to_shoot = True
            self.fire_cd = PLAYER_FIRE_COOLDOWN_S
            self._enter_shoot()

    def _update_shoot(self, dt: float) -> None:
        """Brief state: recoil animation. Continues moving with reduced input."""
        # Maintain movement capability while in SHOOT (it's a sub-state)
        if self.input_left or self.input_right:
            self._enter_move()
            return
        # 0.10s after fire, return to idle
        if self.state_timer >= PLAYER_FIRE_COOLDOWN_S:
            self._enter_idle()
            return
        # Can dash out of shoot
        if self.input_dash:
            self._enter_dash()
            return

    def _update_charge(self, dt: float) -> None:
        # CHARGE engloba build (charge_time) + fire anim (post-release)
        if not self.input_fire and self.charge_time >= CHARGE_L1_S and not self._charge_fired:
            # Release: fire special shot
            self.wants_to_charge_release = True
            self._charge_fired = True
        if self._charge_fired:
            # Post-fire animation
            if self.state_timer >= CHARGE_FIRE_ANIM_S:
                self._enter_idle()
                return
        else:
            # Building up
            self.charge_time += dt
            if self.charge_time >= CHARGE_TIMEOUT_S and not self.input_fire:
                # Timeout without release → fall back to auto-fire L1
                self.wants_to_shoot = True
                self._enter_idle()
                return
        # Movement allowed during charge (with penalty)
        target_vx = 0.0
        if self.input_left:
            target_vx -= PLAYER_SPEED * 0.6
        if self.input_right:
            target_vx += PLAYER_SPEED * 0.6
        self.vx += (target_vx - self.vx) * min(1.0, dt * 8.0)
        self.x += self.vx * dt
        self._clamp_position()
        # Can dash
        if self.input_dash:
            self._enter_dash()
            return

    def _update_dash(self, dt: float) -> None:
        # Move in dash direction at high speed
        self.x += self.dash_dir_x * PLAYER_DASH_SPEED * dt
        self.y += self.dash_dir_y * PLAYER_DASH_SPEED * dt
        self._clamp_position()
        # After-image trail
        self.afterimage.append((self.x, self.y, 0.0))
        if len(self.afterimage) > 8:
            self.afterimage.pop(0)
        if self.state_timer >= PLAYER_DASH_DURATION_S:
            self._enter_idle()

    def _update_hit(self, dt: float) -> None:
        # Reduced movement
        self.vx *= 0.85
        self.x += self.vx * dt
        self._clamp_position()
        if self.state_timer >= HIT_DURATION_S:
            if self.hp <= 0:
                self.lives -= 1
                if self.lives < 0:
                    self.is_game_over = True
                self._enter_dead()
            else:
                self.invuln_frames = PLAYER_INVULN_FRAMES
                self._enter_idle()

    def _update_dead(self, dt: float) -> None:
        self.death_timer += dt
        if self.death_timer >= PLAYER_DEATH_DURATION_S:
            if self.is_game_over:
                return
            # Respawn
            self.x = INTERNAL_W / 2
            self.y = INTERNAL_H - 60
            self.vx = 0.0
            self.vy = 0.0
            self.hp = self.hp_max
            self.death_timer = 0.0
            self.respawn_invuln = PLAYER_RESPAWN_INVULN_S
            self._enter_idle()

    # -----------------------------------------------------------------------
    # State transitions
    # -----------------------------------------------------------------------
    def _enter_idle(self) -> None:
        self.state = PlayerState.IDLE
        self.state_timer = 0.0
        self.charge_time = 0.0
        self._charge_fired = False

    def _enter_move(self) -> None:
        self.state = PlayerState.MOVE
        self.state_timer = 0.0

    def _enter_shoot(self) -> None:
        self.state = PlayerState.SHOOT
        self.state_timer = 0.0

    def _enter_charge(self) -> None:
        self.state = PlayerState.CHARGE
        self.state_timer = 0.0
        self.charge_time = CHARGE_L1_S  # already exceeded L1 by check
        self._charge_fired = False

    def _enter_dash(self) -> None:
        """Enter DASH state with 8-way direction based on input.

        Direction priority:
          1. Active directional input (WASD or arrows when K is pressed)
          2. Last horizontal velocity (continues motion)
          3. UP (stationary, GDD default)

        Combinations give 8 directions:
          K alone          -> UP
          K + A/D          -> LEFT/RIGHT
          K + W            -> UP (same as K alone)
          K + S            -> DOWN (escape move)
          K + A + W        -> UP-LEFT
          K + A + S        -> DOWN-LEFT
          K + D + W        -> UP-RIGHT
          K + D + S        -> DOWN-RIGHT
        """
        self.state = PlayerState.DASH
        self.state_timer = 0.0
        self.dash_iframes_left = PLAYER_DASH_IFRAMES
        left = self.input_left
        right = self.input_right
        up = self.input_up
        down = self.input_down
        dx, dy = 0.0, 0.0
        if left and not right:
            dx = -1.0
        elif right and not left:
            dx = 1.0
        if up and not down:
            dy = -1.0
        elif down and not up:
            dy = 1.0
        # If no active directional input, fall back to vx
        if dx == 0.0 and dy == 0.0:
            if self.vx < -10.0:
                dx = -1.0
            elif self.vx > 10.0:
                dx = 1.0
            else:
                dx = 0.0
                dy = -1.0  # default UP per GDD
        # Normalize diagonal so dash distance is consistent
        if dx != 0.0 and dy != 0.0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv
        self.dash_dir_x = dx
        self.dash_dir_y = dy
        # Consume dash input (one-shot)
        self.input_dash = False

    def _enter_hit(self) -> None:
        self.state = PlayerState.HIT
        self.state_timer = 0.0
        self.invuln_frames = PLAYER_INVULN_FRAMES

    def _enter_dead(self) -> None:
        self.state = PlayerState.DEAD
        self.state_timer = 0.0
        self.death_timer = 0.0
        self.is_dead = True

    def _consume_bomb(self) -> None:
        self.bombs = max(0, self.bombs - 1)
        self.wants_to_bomb = True
        self.input_bomb = False  # consume input
        # Bombs are screen-wide clears; the consumer handles the effect.
        # We don't change state here — player stays in current state.

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------
    def _clamp_position(self) -> None:
        # 18x16 sprite. Allow center to reach the visible border edges
        # (9px from each side for half-sprite) so the ship can use the
        # entire 240x360 play area defined by the border frame.
        self.x = max(9, min(INTERNAL_W - 9, self.x))
        self.y = max(9, min(INTERNAL_H - 9, self.y))

    def get_charge_level(self) -> int:
        """Return 0/1/2/3 based on charge_time. 0 = not charging."""
        if self.state != PlayerState.CHARGE:
            return 0
        if self.charge_time >= CHARGE_L3_S:
            return 3
        if self.charge_time >= CHARGE_L2_S:
            return 2
        if self.charge_time >= CHARGE_L1_S:
            return 1
        return 0
