"""Gameplay runtime — wires up Player + Weapon + Enemies + Bullets + HUD.

Single source of truth for what happens in GAMEPLAY and BOSS_FIGHT scenes.
Both scenes share the same combat loop: bullets fly, enemies spawn, hits
register, score updates, particles pop, HUD reflects state.

Why this is a separate module:
- scenes.py is for menu/transition scenes (Title, ActIntro, etc).
- This file is for the live action loop.
- Keeping them separate keeps scenes.py easy to read for the menu flow
  and makes the gameplay loop testable in isolation.

The runtime is intentionally stateful (one instance per scene) and updates
in fixed timesteps via Game's accumulator.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import pygame

from src.core.settings import (
    BOSS_FALLBACK_KILLS, BOSS_FALLBACK_TIMEOUT_S, BOSS_FAST_TRIGGER_S,
    INTERNAL_H, INTERNAL_W, FIXED_DT,
)
from src.entities.enemies import EnemyKind, EnemyPool, Enemy
from src.entities.enemies.boss import Boss, BossId, BossPool, BOSS_CONFIGS
from src.entities.boss_spear import BossSpear
from src.entities.player import Player, PlayerState
from src.systems.hitstop import Hitstop
from src.systems.parallax import ParallaxBackground
from src.systems.particle_engine import (
    P_DEBRIS, P_DUST, P_FIRE, P_FLASH, P_GLOW, P_ION, P_MUZZLE, P_SHRAPNEL,
    P_SMOKE, P_SPARK, ParticleEngine,
)
from src.systems.projectile import (
    BULLET_BOSS, BULLET_ENEMY, BULLET_PLAYER, BULLET_PLAYER_BEAM,
    BULLET_PLAYER_CHARGED,
    OWNER_BOSS, OWNER_ENEMY, OWNER_PLAYER, ProjectilePool,
)
from src.systems.scoring_system import ScoringSystem
from src.systems.screen_shake import ScreenShake
from src.systems.slowmo import SlowMo
from src.systems.weapon_system import WeaponLevel, WeaponPath, WeaponSystem
from src.ui.hud import HUD

if TYPE_CHECKING:
    from src.audio.synth import AudioEngine
    from src.systems.wave_manager import BossTrigger, WaveChain, WaveManager
    from src.ui.scenes import TransitionFn


# Wave spawn intervals (seconds) — how often to drop a new enemy during a wave
WAVE_SPAWN_INTERVAL_S = 0.9
# Max enemies alive at once during regular waves (BLOQUE 42: now sourced from
# settings.MAX_ENEMIES_ON_SCREEN so it stays in sync with the global cap).
from src.core.settings import MAX_ENEMIES_ON_SCREEN as WAVE_MAX_LIVE
# Score awarded per enemy archetype (mirrors ENEMY_CONFIGS)
_ENEMY_SCORE = {
    EnemyKind.SCOUT: 50, EnemyKind.CRUISER: 150, EnemyKind.HEAVY: 400,
    EnemyKind.KAMIKAZE: 200, EnemyKind.DRONE: 80, EnemyKind.SNIPER: 300,
    EnemyKind.TURRET: 250, EnemyKind.CARRIER: 800,
    EnemyKind.SUB_BOSS: 600,  # BLOQUE 50
}

# Particle kind by "explosion quality"
_BURST_KIND = {
    "spark": P_SPARK,
    "explosion": P_FIRE,
    "smoke": P_SMOKE,
    "shrapnel": P_SHRAPNEL,
    "debris": P_DEBRIS,
    "dust": P_DUST,
    "flash": P_FLASH,
    "muzzle": P_MUZZLE,
    "glow": P_GLOW,
    "ion": P_ION,
}

# Power-up types
POWERUP_BOMB = "bomb"
POWERUP_POWER = "power"
POWERUP_SCORE = "score"
POWERUP_1UP = "1up"
# BLOQUE 53c: gold ring (Star Fox). Heals on touch; 3 stacked doubles
# the player's max HP (one-time per run).
POWERUP_GOLD_RING = "gold_ring"

# Color the play-area frame uses (matches the parallax palette vibe)
_BORDER_COLOR = (60, 60, 90)
_BORDER_INNER = (140, 140, 180)


# ---------------------------------------------------------------------------
# Floating score popup
# ---------------------------------------------------------------------------
@dataclass
class ScorePopup:
    x: float
    y: float
    vy: float
    text: str
    color: tuple[int, int, int]
    life: float
    max_life: float


@dataclass
class PowerUp:
    x: float
    y: float
    vy: float
    kind: str
    life: float
    max_life: float
    color: tuple[int, int, int]


@dataclass
class Shockwave:
    x: float
    y: float
    radius: float
    max_radius: float
    life: float
    max_life: float


# BLOQUE 39: Homing missile spawned by the B key (replaces the L-key
# screen-clear bomb). Tracks the current mouse position, accelerates
# to top speed, rotates up to TURN_RATE_DEG_S, and explodes on first
# contact (enemy, boss, enemy bullet, or screen edge).
@dataclass
class HomingMissile:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0           # visual rotation (deg), 0=up
    speed: float = 0.0            # current speed
    life: float = 0.0             # elapsed time
    trail_timer: float = 0.0
    active: bool = True


class GameplayRuntime:
    """Owns the live action loop. One per GAMEPLAY or BOSS_FIGHT scene.

    Public API:
      __init__(transition_to, is_boss=False, act=1, audio=None)
      on_enter() / on_exit()
      update(dt)  — call from scene.update
      draw(target) — call from scene.draw
    """

    def __init__(self, transition_to: "TransitionFn", is_boss: bool = False, act: int = 1,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._is_boss = is_boss
        self._act = act
        self._audio = audio  # shared AudioEngine; may be None (muted)

        # Core
        self._player = Player()
        self._bg = ParallaxBackground(rng_seed=42 if not is_boss else 77)

        # Combat systems
        self._bullets = ProjectilePool(capacity=400)
        if is_boss:
            self._bullets.expand_for_boss()
        self._weapon = WeaponSystem()
        self._enemies = EnemyPool(capacity=64)
        self._scoring = ScoringSystem()
        self._particles = ParticleEngine(pool_size=512)
        self._hud = HUD()
        self._wave_mgr = self._build_wave_manager()
        self._bosses = BossPool()
        self._boss: Optional[Boss] = None
        if is_boss:
            self._spawn_boss_for_act()

        # Juice
        self._hitstop = Hitstop()
        self._shake = ScreenShake()
        self._slowmo = SlowMo()

        # Wave spawner state
        self._t: float = 0.0
        self._wave_spawn_timer: float = 0.0
        self._wave_idx: int = (act - 1) * 6  # act 1 starts at wave 0
        self._pending_wave_spawns: list[tuple[float, EnemyKind, float, float, bool, float]] = []
        self._is_wave_active: bool = True
        self._transition_pending: Optional[str] = None  # "boss_intro" or "act_cleared"
        # BLOQUE 48: chained wave system (level 1 mode redesign)
        self._level1_chain: Optional[WaveChain] = None
        self._level1_boss_trigger: Optional[BossTrigger] = None
        # BLOQUE 50: mid-wave sub-boss state. _sub_boss_alive=True while
        # the sub-boss enemy is in play. _sub_boss_intro_done prevents
        # the SUB_BOSS_INTRO scene from re-triggering while the sub-boss
        # is still alive.
        self._sub_boss_alive: bool = False
        self._sub_boss_intro_done: bool = False

        # Polish state
        self._score_popups: list[ScorePopup] = []
        self._powerups: list[PowerUp] = []
        self._enemy_flash: dict[int, float] = {}  # id(e) -> flash_timer
        self._boss_flash: dict[int, float] = {}  # BLOQUE 51: id(boss) -> flash_timer (hit feedback)
        # BLOQUE 52: GOLIATH spear throw state machine.
        # Phase: "ready" (spear in hand), "winding" (pulling back), "thrown" (no spear in hand)
        self._boss_spear_phase: str = "ready"
        self._boss_spear_phase_t: float = 0.0
        # Active spear projectiles (main + fragments)
        self._boss_spears: list[BossSpear] = []
        # BLOQUE 53a: GOLIATH shield charge + laser state.
        # 20 player bullets hitting the shield → boss fires a charged
        # laser for 1 second. After the laser ends, the counter resets
        # and the boss returns to its normal attack cycle.
        self._boss_shield_hits: int = 0
        self._boss_shield_laser_t: float = 0.0  # 0.0 = not firing; >0 = remaining seconds
        self._boss_shield_laser_duration: float = 1.0
        self._boss_shield_laser_damage_cooldown: dict[int, float] = {}
        self._shockwaves: list[Shockwave] = []  # expanding ring effects
        self._screen_flash: float = 0.0  # 0..1 alpha of white overlay (bomb)
        self._boss_entry_t: float = 0.0  # boss slides in on first 1.5s of fight
        self._dash_consumed: bool = False  # SFX dedup
        self._last_charge_level: int = 0
        self._death_exploded: bool = False
        # BLOQUE 37: continuous L3 laser state
        self._laser_active: bool = False
        self._laser_end_x: float = 0.0
        self._laser_end_y: float = 0.0
        self._laser_pulse_t: float = 0.0
        self._laser_damage_timer: float = 0.0
        self._laser_hit_cooldown: dict[int, float] = {}  # id(enemy) -> s remaining
        # BGM state
        self._bgm_started: bool = False
        # Player-state snapshot for transition SFX
        self._prev_player_state: PlayerState = PlayerState.IDLE
        # BLOQUE 29: mouse aiming state
        self._mouse_x: float = INTERNAL_W / 2
        self._mouse_y: float = INTERNAL_H / 2
        self._mouse_held: bool = False  # BLOQUE 30: LMB held state
        self._mouse_r_held: bool = False  # BLOQUE 34: RMB held state (rapid fire)
        # BLOQUE 39: active homing missiles (bomb B key)
        self._missiles: list[HomingMissile] = []
        # BLOQUE 43: perfect-score tracking
        self._enemies_spawned_total: int = 0   # cumulative across all waves
        self._enemies_escaped: int = 0         # left the screen alive (above the top edge)
        # BLOQUE 47: SQUADRON formation tracking — each squadron gets a unique
        # id so we can group leader + followers for choreographed movement.
        self._squadron_id_counter: int = 0
        # BLOQUE 47.1: cache the actual display size from pygame so the
        # mouse-to-internal scaling uses the real window dimensions, not
        # the default WINDOW_W x WINDOW_H (which is 960x1440 = 4x scale).
        # With --scale 3 the actual window is 720x1080, and using 960x1440
        # here would make the reticle land at only 75% of the mouse pos.
        surf = pygame.display.get_surface()
        if surf is not None:
            self._game_screen_size: tuple[int, int] = surf.get_size()
        else:
            from src.core.settings import WINDOW_H, WINDOW_W
            self._game_screen_size = (WINDOW_W, WINDOW_H)
        # BLOQUE 22: extra polish
        self._muzzle_flash: float = 0.0  # 0..1 alpha of muzzle flash overlay
        # BLOQUE 38: which input caused the most recent muzzle flash
        # ("lmb" → warm yellow, "rmb" → warm orange) so RMB rapid fire is
        # visually distinct from LMB single shots.
        self._muzzle_flash_source: str = "lmb"
        self._charge_release_flash: float = 0.0  # 0..1 full-screen flash on charge fire
        self._boss_death_stage: int = 0  # 0 = alive, 1..3 = multi-stage explosion frames
        self._boss_death_timer: float = 0.0  # time since death for staging
        self._charge_release_shock: bool = False  # spawn expanding ring on charge release
        self._boss_death_pos: tuple[float, float] = (0.0, 0.0)  # cached pos for staged burst
        # BLOQUE 24: more polish
        self._pickup_flash: float = 0.0  # 0..1 alpha of green pickup flash overlay
        self._speed_line_t: float = 0.0  # accumulator for speed line drift
        self._level_up_flash: float = 0.0  # brief flash when weapon levels up
        # BLOQUE 26: even more polish
        self._bomb_flash: float = 0.0  # 0..1 white flash on the player after bomb use

    def _play_sfx(self, name: str, volume: float = 1.0) -> None:
        if self._audio is not None:
            self._audio.play_sfx(name, volume)

    def _start_bgm(self, name: str) -> None:
        # BLOQUE 34: BGM disabled per user request (quítale la música de fondo).
        # SFX still plays. Mark as started to keep state consistent.
        self._bgm_started = True

    def _stop_bgm(self) -> None:
        if self._audio is not None:
            self._audio.stop_bgm()
        self._bgm_started = False

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _build_wave_manager(self) -> "WaveManager":
        from src.systems.wave_manager import WaveManager
        return WaveManager()

    def _emit_burst(self, x: float, y: float, count: int, kind: str = "spark",
                    color: tuple[int, int, int] | None = None) -> None:
        """Spawn a radial burst of particles at (x, y).

        BLOQUE 49: optional `color` parameter to override the default
        tint of the particle kind (used for orange laser-contact sparks).
        """
        kind_id = _BURST_KIND.get(kind, P_SPARK)
        for _ in range(count):
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(40.0, 120.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self._particles.emit(kind_id, x, y, vx, vy, color=color)

    def _spawn_boss_for_act(self) -> None:
        boss_id = {
            1: BossId.GOLIATH,
            2: BossId.HYDRA,
            3: BossId.NEMESIS,  # PHANTOM + NEMESIS: default to final
        }.get(self._act, BossId.GOLIATH)
        self._boss = self._bosses.spawn(boss_id)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def on_enter(self) -> None:
        # BLOQUE 50: detect "resume from SUB_BOSS_INTRO" — when we return
        # to GAMEPLAY after the sub-boss warning, the chain has
        # _sub_boss_pending=True and current_wave_idx is post-O2. In that
        # case we must NOT reset the chain (otherwise the level restarts
        # from O1 and the warning loop triggers every time O2 finishes).
        # We still clear bullets/particles/score-popups so the visual
        # feels like a fresh continuation rather than a hard cut.
        _resume_from_sub_boss = (
            self._level1_chain is not None
            and self._level1_chain.sub_boss_pending
        )
        if not _resume_from_sub_boss:
            self._player.reset()
            self._weapon.reset()
            self._scoring.reset()
        # Even on a sub-boss resume, we clear transient visual state so the
        # transition doesn't look like a hard cut (in-flight bullets, smoke
        # particles, score popups).
        self._bullets.release_all()
        self._enemies.release_all()
        self._particles.release_all()
        self._score_popups.clear()
        self._powerups.clear()
        self._enemy_flash.clear()
        self._boss_flash.clear()
        self._boss_spear_phase = "ready"
        self._boss_spear_phase_t = 0.0
        self._boss_spears = []
        # BLOQUE 53a: reset shield charge
        self._boss_shield_hits = 0
        self._boss_shield_laser_t = 0.0
        self._boss_shield_laser_damage_cooldown = {}
        self._shockwaves.clear()
        # BLOQUE 39: clear active homing missiles on scene enter
        self._missiles.clear()
        if not _resume_from_sub_boss:
            # BLOQUE 43: reset perfect-score tracking
            self._enemies_spawned_total = 0
            self._enemies_escaped = 0
            self._squadron_id_counter = 0  # BLOQUE 47: reset on each scene reset
            # BLOQUE 48: reset the chained wave system (only on fresh start)
            if self._level1_chain is not None:
                self._level1_chain.reset()
            # BLOQUE 50: reset sub-boss state (only on fresh start)
            self._sub_boss_alive = False
            self._sub_boss_intro_done = False
            self._screen_flash = 0.0
            # BLOQUE 22: reset polish state
            self._muzzle_flash = 0.0
            self._charge_release_flash = 0.0
            self._boss_death_stage = 0
            self._boss_death_timer = 0.0
            self._boss_death_pos = (0.0, 0.0)
            # BLOQUE 24: reset new polish state
            self._pickup_flash = 0.0
            self._speed_line_t = 0.0
            self._level_up_flash = 0.0
            # BLOQUE 26: reset bomb flash
            self._bomb_flash = 0.0
            # BLOQUE 29: reset mouse position
            self._mouse_x = INTERNAL_W / 2
            self._mouse_y = INTERNAL_H / 4
            self._mouse_held = False
            self._mouse_r_held = False
            self._t = 0.0
            self._wave_spawn_timer = 0.0
            self._is_wave_active = not self._is_boss
            self._transition_pending = None
            self._death_exploded = False
            self._last_charge_level = 0
            self._bgm_started = False
            self._boss_entry_t = 0.0
            if not self._is_boss:
                self._wave_mgr.start_wave(self._wave_idx)
                # BLOQUE 29: use level 1 queue (5 min, 100+ ships, 3 enemy types)
                if self._is_level1_mode():
                    self._populate_level1_queue()
                else:
                    self._populate_spawn_queue()
                self._start_bgm("act_normal")
            else:
                # Boss intro pose: player bottom-center, boss anchored
                self._player.x = INTERNAL_W / 2
                self._player.y = INTERNAL_H - 60
                if self._boss is not None:
                    cfg = BOSS_CONFIGS[self._boss.id]
                    self._boss.x = cfg.anchor_x
                    self._boss.y = cfg.anchor_y
                    self._boss.phase = 1
                    self._boss.hp = self._boss.max_hp
                self._start_bgm("boss_fight")
        else:
            # BLOQUE 50: on sub-boss resume, mark that we need to spawn the
            # sub-boss on the first frame. _sub_boss_alive starts False and
            # will be set to True in _update_enemies when the spawn happens.
            self._sub_boss_alive = False
            self._sub_boss_intro_done = True  # intro already played
            # Keep mouse, time, player position, score, etc. intact

    def on_exit(self) -> None:
        self._bullets.release_all()
        self._enemies.release_all()
        self._particles.release_all()
        self._bosses.release_all()
        self._stop_bgm()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def _read_input(self) -> None:
        keys = pygame.key.get_pressed()
        self._player.input_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self._player.input_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        self._player.input_up = keys[pygame.K_w] or keys[pygame.K_UP]
        self._player.input_down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        # BLOQUE 29: mouse aiming — read mouse position relative to internal coords
        # The display is 4x scaled from internal (240x360 → 960x1440).
        try:
            mouse_x_disp, mouse_y_disp = pygame.mouse.get_pos()
            # Get the internal rect (where the game is drawn on the display)
            display_w, display_h = self._game_screen_size
            scale_x = INTERNAL_W / display_w
            scale_y = INTERNAL_H / display_h
            self._mouse_x = mouse_x_disp * scale_x
            self._mouse_y = mouse_y_disp * scale_y
            # BLOQUE 34: mouse buttons — (left, middle, right)
            #   LMB (index 0) = charge shot
            #   RMB (index 2) = rapid fire (no charge)
            mouse_buttons = pygame.mouse.get_pressed()
            self._mouse_held = bool(mouse_buttons[0])
            self._mouse_r_held = bool(mouse_buttons[2])
        except (AttributeError, pygame.error):
            # No display yet (headless); use center
            self._mouse_x = INTERNAL_W / 2
            self._mouse_y = INTERNAL_H / 2
            self._mouse_held = False
            self._mouse_r_held = False
        # BLOQUE 34: shooting controls
        #   LMB held = input_fire (charge shot, release fires)
        #   RMB held = input_rapid_fire (continuous L1, no charge)
        # These are independent — you can RMB-spam while LMB charges.
        self._player.input_fire = self._mouse_held
        self._player.input_rapid_fire = self._mouse_r_held
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_LSHIFT:
                # BLOQUE 33: Shift left = dash (one-shot, consumed)
                self._player.input_dash = True
            elif event.key == pygame.K_l:
                # BLOQUE 39: L still triggers bomb (back-compat), but B
                # is the new primary key. Both routed to the same path.
                self._player.input_bomb = True
            elif event.key == pygame.K_b:
                # BLOQUE 39: B is the new bomb key (homing missile).
                self._player.input_bomb = True
            elif event.key == pygame.K_j:
                # Legacy: J also fires (for testing)
                self._player.input_fire = True
            elif event.key == pygame.K_ESCAPE:
                from src.core.scene_manager import GameState
                self._transition_to(GameState.PAUSE)

    def _update_nose_angle(self) -> None:
        """BLOQUE 32: compute ship's nose angle from mouse position — 360°.

        Convention (matches Player nose rendering):
          0° = pointing UP (nose at top of screen, default for shmup)
          90° = pointing RIGHT
          180° = pointing DOWN
          270° = pointing LEFT
        Mouse is "above" the ship when my < py in screen coordinates, so
        we use atan2(dx, -dy) which gives 0° when dx=0 and my<py.
        360° freedom: the ship can face and shoot in any direction. The
        actual rendering rotation will flip the sprite for angles >90°
        so the ship's "canopy" stays oriented correctly to the player.
        """
        import math
        px, py = self._player.x, self._player.y
        mx, my = self._mouse_x, self._mouse_y
        dx = mx - px
        dy = my - py
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            # Mouse over ship → keep current angle
            return
        # atan2(dx, -dy): 0° = up, 90° = right, 180° = down, -90° = left
        angle = math.degrees(math.atan2(dx, -dy)) % 360.0
        self._player.nose_angle = angle

    # ------------------------------------------------------------------
    # Firing
    # ------------------------------------------------------------------
    def _handle_firing(self, dt: float) -> None:
        # BLOQUE 37: L3 max charge is now a continuous laser (not discrete bullets)
        current_charge = self._player.get_charge_level()
        self._update_continuous_laser(dt, current_charge)
        # Charge release (player.wants_to_charge_release)
        if self._player.wants_to_charge_release:
            charge_level = self._player.get_charge_level()
            if charge_level == 0:
                charge_level = 1
            self._weapon.request_fire(charge_level=charge_level)
        # Normal fire
        elif self._player.wants_to_shoot:
            self._weapon.request_fire(charge_level=0)
        # BLOQUE 39: Bomb → spawn a homing missile (replaces screen-clear)
        if self._player.wants_to_bomb and self._player.bombs > 0:
            self._player._consume_bomb()
            self._scoring.on_bomb()
            self._spawn_homing_missile()
            self._play_sfx("bomb", volume=0.6)
        # Charge SFX: rising pitch as charge level increases
        if current_charge > self._last_charge_level:
            self._play_sfx("charge_loop", volume=0.5)
        self._last_charge_level = current_charge
        fire_now, special_now, charge_level = self._weapon.consume_pending()
        if fire_now or special_now:
            # BLOQUE 38: tag the shot with its source so the muzzle flash
            # can be tinted (RMB = orange, LMB = yellow) and the player
            # gets clear visual feedback about which input is firing.
            self._muzzle_flash_source = "rmb" if self._mouse_r_held else "lmb"
            self._spawn_player_bullet(charge_level=charge_level)
            if charge_level > 0:
                self._play_sfx("shoot_charged", volume=0.6)
                # BLOQUE 22: charge release = big visual punch
                self._charge_release_flash = 0.7
                self._charge_release_shock = True
                self._add_shockwave(self._player.x, self._player.y, 40.0)
                self._shake.add_trauma(0.15)
            else:
                self._play_sfx("shoot", volume=0.4)
            # BLOQUE 22: muzzle flash overlay (decays in update)
            self._muzzle_flash = 1.0 if charge_level == 0 else 1.6
        # Reset bomb output flag
        self._player.wants_to_bomb = False

    # ------------------------------------------------------------------
    # BLOQUE 37: continuous L3 plasma laser
    # ------------------------------------------------------------------
    def _update_continuous_laser(self, dt: float, current_charge: int) -> None:
        """L3 max charge while LMB held → render a continuous plasma beam
        that damages enemies in its path (no individual bullet spawns).

        Replaces the BLOQUE 30 discrete-beam approach (0.08s spawn loop).
        """
        from src.core.settings import (
            LASER_DAMAGE_PER_TICK, LASER_HIT_RADIUS_PX, LASER_MAX_RANGE_PX,
            LASER_SPARK_RATE_S, LASER_TICK_S,
        )
        should_be_active = (
            current_charge >= 3
            and self._player.state == PlayerState.CHARGE
            and self._mouse_held
        )
        if should_be_active and not self._laser_active:
            # Laser just turned on — start the held laser sound.
            self._play_sfx("laser_continuous", volume=0.55)
            self._laser_damage_timer = 0.0
            self._laser_hit_cooldown.clear()
        elif not should_be_active and self._laser_active:
            # Laser just turned off — short release tail.
            self._play_sfx("laser_end", volume=0.35)
        self._laser_active = should_be_active
        if not self._laser_active:
            # Cool down per-enemy hit timers even when laser is off (so
            # the next activation can re-hit the same enemy immediately).
            for k in list(self._laser_hit_cooldown.keys()):
                self._laser_hit_cooldown[k] -= dt
                if self._laser_hit_cooldown[k] <= 0.0:
                    del self._laser_hit_cooldown[k]
            return
        # Compute the beam endpoint: from muzzle, along nose direction, until
        # it leaves the play area (or hits max range).
        nose_rad = math.radians(self._player.nose_angle)
        muzzle_offset = 12.0
        bx = self._player.x + math.sin(nose_rad) * muzzle_offset
        by = self._player.y - math.cos(nose_rad) * muzzle_offset
        # Trace to the screen edge along nose direction.
        # For each axis, only the edge in the direction of travel can
        # give a positive t — picking the wrong edge yields t<0 which
        # would clamp the beam to length 0.
        dx = math.sin(nose_rad)
        dy = -math.cos(nose_rad)
        best_t = LASER_MAX_RANGE_PX
        if dx > 1e-4:
            best_t = min(best_t, (INTERNAL_W - bx) / dx)
        elif dx < -1e-4:
            best_t = min(best_t, (0 - bx) / dx)
        if dy > 1e-4:
            best_t = min(best_t, (INTERNAL_H - by) / dy)
        elif dy < -1e-4:
            best_t = min(best_t, (0 - by) / dy)
        best_t = max(0.0, best_t)
        self._laser_end_x = bx + dx * best_t
        self._laser_end_y = by + dy * best_t
        # Pulse timer (for shimmer along the beam)
        self._laser_pulse_t += dt
        # Tick-rate damage
        self._laser_damage_timer += dt
        if self._laser_damage_timer >= LASER_TICK_S:
            self._laser_damage_timer = 0.0
            self._laser_apply_damage(
                bx, by, dx, dy, best_t,
                LASER_HIT_RADIUS_PX, LASER_DAMAGE_PER_TICK,
            )
        # Decay per-enemy cooldowns
        for k in list(self._laser_hit_cooldown.keys()):
            self._laser_hit_cooldown[k] -= dt
            if self._laser_hit_cooldown[k] <= 0.0:
                del self._laser_hit_cooldown[k]
        # Ambient sparks along the beam (visual sizzle)
        self._laser_spark_timer = getattr(self, "_laser_spark_timer", 0.0)
        self._laser_spark_timer += dt
        if self._laser_spark_timer >= LASER_SPARK_RATE_S:
            self._laser_spark_timer = 0.0
            # Place a spark at a random point along the beam
            import random as _r
            t = _r.uniform(0.0, best_t)
            sx = bx + dx * t
            sy = by + dy * t
            self._emit_burst(sx, sy, count=1, kind="spark")

    def _laser_apply_damage(
        self, bx: float, by: float, dx: float, dy: float,
        t_max: float, radius: int, damage: int,
    ) -> None:
        """Apply damage to enemies (and boss) that the beam segment intersects."""
        # Enemies
        for e in self._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            if id(e) in self._laser_hit_cooldown:
                continue
            # Distance from point (e.x, e.y) to the segment (bx,by)-(bx+dx*t,by+dy*t)
            ex, ey = e.x, e.y
            # Project onto beam
            t_proj = (ex - bx) * dx + (ey - by) * dy
            if t_proj < 0.0:
                t_proj = 0.0
            elif t_proj > t_max:
                t_proj = t_max
            cx = bx + dx * t_proj
            cy = by + dy * t_proj
            ddx = ex - cx
            ddy = ey - cy
            if ddx * ddx + ddy * ddy <= (radius + 8) ** 2:
                # Inflate radius to match enemy size roughly.
                killed = e.apply_damage(damage)
                # BLOQUE 49: orange contact sparks (high-energy plasma
                # burning through enemy hull) + cyan shrapnel + smoke
                self._emit_burst(ex, ey, count=6, kind="spark",
                                  color=(255, 140, 40))
                self._emit_burst(ex, ey, count=3, kind="spark",
                                  color=(255, 200, 80))
                self._emit_burst(ex, ey, count=2, kind="shrapnel")
                self._emit_burst(ex, ey, count=1, kind="smoke")
                self._enemy_flash[id(e)] = 0.05
                self._laser_hit_cooldown[id(e)] = 0.10
                if killed:
                    self._on_enemy_killed(e)
        # Boss
        if self._is_boss and self._boss is not None and self._boss.active:
            if id(self._boss) in self._laser_hit_cooldown:
                return
            ex, ey = self._boss.x, self._boss.y
            t_proj = (ex - bx) * dx + (ey - by) * dy
            if t_proj < 0.0:
                t_proj = 0.0
            elif t_proj > t_max:
                t_proj = t_max
            cxp = bx + dx * t_proj
            cyp = by + dy * t_proj
            ddx = ex - cxp
            ddy = ey - cyp
            # Boss is large (~40px radius), so use a bigger slack.
            if ddx * ddx + ddy * ddy <= (radius + 24) ** 2:
                self._boss.hp -= damage
                self._laser_hit_cooldown[id(self._boss)] = 0.10
                # BLOQUE 51: hit feedback flash
                self._boss_flash[id(self._boss)] = 0.10
                # BLOQUE 49: orange plasma sparks on boss too
                self._emit_burst(cxp, cyp, count=4, kind="spark",
                                  color=(255, 140, 40))
                self._emit_burst(cxp, cyp, count=2, kind="spark",
                                  color=(255, 200, 80))
                # Phase change check
                cfg = BOSS_CONFIGS[self._boss.id]
                new_phase = 1
                for i, threshold in enumerate(cfg.phase_thresholds):
                    if self._boss.hp / self._boss.max_hp <= threshold:
                        new_phase = i + 2
                if new_phase != self._boss.phase:
                    self._boss.phase = new_phase
                    self._emit_burst(self._boss.x, self._boss.y, count=24, kind="explosion")
                    self._emit_burst(self._boss.x, self._boss.y, count=12, kind="spark")
                    self._add_shockwave(self._boss.x, self._boss.y, 50.0)
                    self._hitstop.trigger(6)
                    self._shake.add_trauma(0.5)
                    self._play_sfx("multiplier_up", volume=0.7)
                if self._boss.hp <= 0:
                    self._on_boss_killed()

    def _draw_continuous_laser(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 37: multi-layer plasma beam from muzzle to endpoint.

        Drawn on a per-pixel-alpha surface and blitted on top of the player,
        so the line is visible regardless of the parent surface's alpha mode.
        """
        if not self._laser_active:
            return
        import math as _m
        # Use the muzzle origin (not player center) for visual continuity
        nose_rad = _m.radians(self._player.nose_angle)
        muzzle_offset = 12.0
        bx = self._player.x + _m.sin(nose_rad) * muzzle_offset
        by = self._player.y - _m.cos(nose_rad) * muzzle_offset
        ex = self._laser_end_x
        ey = self._laser_end_y
        sx = int(bx) + ox
        sy = int(by) + oy
        sxe = int(ex) + ox
        sye = int(ey) + oy
        # Pulse modulation (0.85..1.0)
        pulse = 0.925 + 0.075 * _m.sin(self._laser_pulse_t * 18.0)
        # Render the beam on a per-pixel-alpha surface so widths and
        # alpha blend correctly even if `target` is a 24-bit surface.
        w, h = target.get_size()
        beam = pygame.Surface((w, h), pygame.SRCALPHA)
        # Layer 1: outer wide soft glow
        outer_w = int(14 * pulse)
        pygame.draw.line(
            beam,
            (110, 190, 240, 38),
            (sx, sy), (sxe, sye),
            outer_w,
        )
        # Layer 2: mid plasma core (more saturated)
        pygame.draw.line(
            beam,
            (140, 220, 255, 150),
            (sx, sy), (sxe, sye),
            max(1, int(7 * pulse)),
        )
        # Layer 3: bright inner highlight (cyan-white)
        pygame.draw.line(
            beam,
            (225, 245, 255, 220),
            (sx, sy), (sxe, sye),
            max(1, int(3 * pulse)),
        )
        # Bright tip glow at muzzle (where the beam emerges)
        pygame.draw.circle(beam, (200, 235, 255, 200), (sx, sy), 5)
        # Bright tip glow at endpoint
        pygame.draw.circle(beam, (180, 220, 250, 150), (sxe, sye), 4)
        target.blit(beam, (0, 0))

    def _spawn_player_bullet(self, charge_level: int = 0) -> None:
        spec = self._weapon.get_spec()
        # BLOQUE 32: bullets fire in the direction of the ship's nose.
        # 0° = up, 90° = right, 180° = down, 270° = left (360° freedom).
        nose_rad = math.radians(self._player.nose_angle)
        # Spawn bullet at the ship's nose tip (offset 12px in nose direction).
        muzzle_offset = 12.0
        bx = self._player.x + math.sin(nose_rad) * muzzle_offset
        by = self._player.y - math.cos(nose_rad) * muzzle_offset
        # BLOQUE 30: L3 max charge fires a beam — bigger muzzle flash + many particles
        is_beam = (charge_level >= 3)
        if is_beam:
            # Mega Man-style beam: lots of particles emanating from the muzzle
            self._emit_burst(bx, by - 2, count=12, kind="muzzle")
            self._emit_burst(bx, by - 2, count=6, kind="spark")
            self._emit_burst(bx, by - 2, count=4, kind="glow")
        else:
            self._emit_burst(bx, by - 2, count=3, kind="muzzle")
        # Bullet velocity in nose direction
        speed = spec.speed_mult * 480.0
        base_vx = math.sin(nose_rad) * speed
        base_vy = -math.cos(nose_rad) * speed
        # Single bullet or fan
        if spec.count == 1:
            # BLOQUE 30: L3 uses the BEAM bullet kind (bigger, more area)
            if is_beam:
                kind = BULLET_PLAYER_BEAM
            elif charge_level > 0:
                kind = BULLET_PLAYER_CHARGED
            else:
                kind = BULLET_PLAYER
            self._bullets.spawn(
                kind, bx, by, base_vx, base_vy,
                damage=spec.damage, owner=OWNER_PLAYER,
                pierce=spec.pierce, has_trail=spec.trail,
                trail_color=spec.color,
            )
        else:
            spread = math.radians(spec.spread_deg)
            for i in range(spec.count):
                # Symmetric spread around the nose direction
                if spec.count == 1:
                    a = 0.0
                else:
                    a = -spread / 2 + (spread * i / (spec.count - 1))
                vx = math.sin(nose_rad + a) * speed
                vy = -math.cos(nose_rad + a) * speed
                kind = BULLET_PLAYER_CHARGED if charge_level > 0 else BULLET_PLAYER
                self._bullets.spawn(
                    kind, bx, by, vx, vy,
                    damage=spec.damage, owner=OWNER_PLAYER,
                    pierce=spec.pierce, has_trail=spec.trail,
                    trail_color=spec.color,
                )

    # ------------------------------------------------------------------
    # BLOQUE 39: homing missile (bomb = B key)
    # ------------------------------------------------------------------
    def _spawn_homing_missile(self) -> None:
        """Spawn a homing missile at the player's nose aimed at the mouse."""
        from src.core.settings import MISSILE_LIFE_S
        # Initial direction = from player to mouse (so the missile starts
        # already flying toward the cursor). Fall back to nose_angle if the
        # mouse hasn't moved yet.
        dx = self._mouse_x - self._player.x
        dy = self._mouse_y - self._player.y
        if abs(dx) < 1e-3 and abs(dy) < 1e-3:
            nose_rad = math.radians(self._player.nose_angle)
            dx = math.sin(nose_rad)
            dy = -math.cos(nose_rad)
        # Normalize and set initial velocity
        dlen = math.sqrt(dx * dx + dy * dy)
        if dlen > 0:
            dx /= dlen
            dy /= dlen
        from src.core.settings import MISSILE_SPEED_PX_S
        m = HomingMissile(
            x=self._player.x,
            y=self._player.y,
            vx=dx * MISSILE_SPEED_PX_S * 0.5,  # start at half speed, accelerate
            vy=dy * MISSILE_SPEED_PX_S * 0.5,
            # Visual angle: 0°=up. atan2(dx, -dy) maps to the same convention.
            angle=math.degrees(math.atan2(dx, -dy)) % 360.0,
            speed=MISSILE_SPEED_PX_S * 0.5,
            life=0.0,
        )
        m._max_life = MISSILE_LIFE_S  # type: ignore[attr-defined]
        self._missiles.append(m)
        # Tiny muzzle-style burst at the player nose so the launch reads.
        self._emit_burst(self._player.x, self._player.y, count=6, kind="spark")

    def _update_missiles(self, dt: float) -> None:
        """BLOQUE 39: advance homing missiles, steer toward current mouse,
        collide with enemies/boss/enemy bullets/screen edge, then explode.
        """
        from src.core.settings import (
            MISSILE_ACCEL_PX_S2, MISSILE_BODY_RADIUS_PX,
            MISSILE_EXPLOSION_RADIUS_PX, MISSILE_LIFE_S, MISSILE_SPEED_PX_S,
            MISSILE_TRAIL_RATE_S, MISSILE_TURN_RATE_DEG_S,
        )
        if not self._missiles:
            return
        for m in self._missiles:
            if not m.active:
                continue
            m.life += dt
            if m.life >= MISSILE_LIFE_S:
                # Time out: explode in place (small).
                self._explode_missile(m, big=False)
                continue
            # Steer toward current mouse position (limit by TURN_RATE_DEG_S)
            tdx = self._mouse_x - m.x
            tdy = self._mouse_y - m.y
            tlen = math.sqrt(tdx * tdx + tdy * tdy)
            if tlen > 1e-3:
                tdx /= tlen
                tdy /= tlen
            # Current heading (normalized)
            if m.speed > 1e-3:
                hdx = m.vx / m.speed
                hdy = m.vy / m.speed
            else:
                hdx, hdy = tdx, tdy
            # Cross product to determine turn sign (2D)
            cross = hdx * tdy - hdy * tdx
            dot = hdx * tdx + hdy * tdy
            target_angle = math.degrees(math.atan2(tdx, -tdy)) % 360.0
            current_angle = m.angle
            # Shortest signed delta
            delta = (target_angle - current_angle + 540.0) % 360.0 - 180.0
            max_step = MISSILE_TURN_RATE_DEG_S * dt
            if abs(delta) <= max_step:
                new_angle = target_angle
            elif delta > 0:
                new_angle = current_angle + max_step
            else:
                new_angle = current_angle - max_step
            m.angle = new_angle % 360.0
            # New heading from the clamped angle
            new_rad = math.radians(m.angle)
            hdx2 = math.sin(new_rad)
            hdy2 = -math.cos(new_rad)
            # Accelerate
            m.speed = min(MISSILE_SPEED_PX_S, m.speed + MISSILE_ACCEL_PX_S2 * dt)
            m.vx = hdx2 * m.speed
            m.vy = hdy2 * m.speed
            # Move
            m.x += m.vx * dt
            m.y += m.vy * dt
            # Trail particles
            m.trail_timer += dt
            if m.trail_timer >= MISSILE_TRAIL_RATE_S:
                m.trail_timer = 0.0
                self._emit_burst(m.x, m.y, count=1, kind="smoke")
                self._emit_burst(m.x, m.y, count=1, kind="spark")
            # Collisions
            body_r = MISSILE_BODY_RADIUS_PX
            # Screen edge: explode on leaving the play area
            if (m.x < -body_r or m.x > INTERNAL_W + body_r
                    or m.y < -body_r or m.y > INTERNAL_H + body_r):
                self._explode_missile(m, big=False)
                continue
            # Enemies
            hit = False
            for e in self._enemies.pool:
                if not e.active or e.state.name == "DEAD":
                    continue
                dx = e.x - m.x
                dy = e.y - m.y
                if dx * dx + dy * dy <= (body_r + 14) ** 2:
                    self._explode_missile(m, big=True, hit_x=e.x, hit_y=e.y)
                    hit = True
                    break
            if hit:
                continue
            # Boss
            if self._is_boss and self._boss is not None and self._boss.active:
                dx = self._boss.x - m.x
                dy = self._boss.y - m.y
                if dx * dx + dy * dy <= (body_r + 24) ** 2:
                    self._explode_missile(m, big=True, hit_x=self._boss.x, hit_y=self._boss.y)
                    continue
            # Enemy bullets
            for p in self._bullets.pool:
                if not p.active or p.owner == OWNER_PLAYER:
                    continue
                dx = p.x - m.x
                dy = p.y - m.y
                if dx * dx + dy * dy <= (body_r + 4) ** 2:
                    p.active = False
                    self._bullets.pool.release(p)
                    self._explode_missile(m, big=False, hit_x=p.x, hit_y=p.y)
                    break

    def _explode_missile(self, m: HomingMissile, big: bool, hit_x: float = 0.0, hit_y: float = 0.0) -> None:
        """BLOQUE 39: missile detonation — damages enemies in radius, clears
        nearby enemy bullets, applies screen flash + shockwave + slowmo.
        """
        from src.core.settings import (
            MISSILE_EXPLOSION_DAMAGE, MISSILE_EXPLOSION_RADIUS_PX,
        )
        if not m.active:
            return
        m.active = False
        cx, cy = m.x, m.y
        if big:
            cx, cy = hit_x, hit_y
        rad = MISSILE_EXPLOSION_RADIUS_PX
        # Damage enemies in radius
        for e in self._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            dx = e.x - cx
            dy = e.y - cy
            if dx * dx + dy * dy <= rad * rad:
                killed = e.apply_damage(MISSILE_EXPLOSION_DAMAGE)
                self._emit_burst(e.x, e.y, count=8, kind="spark")
                self._emit_burst(e.x, e.y, count=4, kind="shrapnel")
                self._enemy_flash[id(e)] = 0.10
                if killed:
                    self._on_enemy_killed(e)
        # Damage boss in radius
        if self._is_boss and self._boss is not None and self._boss.active:
            dx = self._boss.x - cx
            dy = self._boss.y - cy
            if dx * dx + dy * dy <= rad * rad:
                self._boss.hp -= MISSILE_EXPLOSION_DAMAGE
                # BLOQUE 51: hit feedback flash
                self._boss_flash[id(self._boss)] = 0.10
                # BLOQUE 51: emit hit sparks on boss (was missing here)
                self._emit_burst(self._boss.x, self._boss.y, count=6, kind="spark",
                                  color=(255, 140, 40))
                # Phase change
                cfg = BOSS_CONFIGS[self._boss.id]
                new_phase = 1
                for i, threshold in enumerate(cfg.phase_thresholds):
                    if self._boss.hp / self._boss.max_hp <= threshold:
                        new_phase = i + 2
                if new_phase != self._boss.phase:
                    self._boss.phase = new_phase
                    self._emit_burst(self._boss.x, self._boss.y, count=24, kind="explosion")
                    self._emit_burst(self._boss.x, self._boss.y, count=12, kind="spark")
                    self._add_shockwave(self._boss.x, self._boss.y, 50.0)
                    self._hitstop.trigger(6)
                    self._shake.add_trauma(0.5)
                    self._play_sfx("multiplier_up", volume=0.7)
                if self._boss.hp <= 0:
                    self._on_boss_killed()
        # Clear enemy bullets in radius
        for p in self._bullets.pool:
            if not p.active or p.owner == OWNER_PLAYER:
                continue
            dx = p.x - cx
            dy = p.y - cy
            if dx * dx + dy * dy <= rad * rad:
                p.active = False
                self._bullets.pool.release(p)
        # Visual: shockwave, particles, screen flash, slowmo
        self._add_shockwave(cx, cy, max_radius=rad * 1.2)
        self._emit_burst(cx, cy, count=24, kind="explosion")
        self._emit_burst(cx, cy, count=12, kind="spark")
        self._emit_burst(cx, cy, count=10, kind="debris")
        self._screen_flash = max(self._screen_flash, 0.5)
        self._slowmo.trigger(0.6, 6)
        self._shake.add_trauma(0.35)
        self._hitstop.trigger(5)
        self._play_sfx("explode_medium", volume=0.7)

    def _draw_missiles(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 39: render each missile as a small triangle pointing
        along its travel direction, with a soft glow.
        """
        if not self._missiles:
            return
        w, h = target.get_size()
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        for m in self._missiles:
            if not m.active:
                continue
            # Visual triangle: tip at +nose, tail behind
            rad = math.radians(m.angle)
            tip_x = m.x + math.sin(rad) * 8
            tip_y = m.y - math.cos(rad) * 8
            left_x = m.x + math.sin(rad + math.radians(140)) * 5
            left_y = m.y - math.cos(rad + math.radians(140)) * 5
            right_x = m.x + math.sin(rad - math.radians(140)) * 5
            right_y = m.y - math.cos(rad - math.radians(140)) * 5
            # Outer glow (yellow-cyan)
            pygame.draw.polygon(layer, (255, 220, 120, 70), [
                (int(tip_x + ox), int(tip_y + oy)),
                (int(left_x + ox), int(left_y + oy)),
                (int(right_x + ox), int(right_y + oy)),
            ])
            # Inner solid
            inner = 0.55
            pygame.draw.polygon(layer, (255, 250, 220, 230), [
                (int(tip_x + ox), int(tip_y + oy)),
                (int(m.x + math.sin(rad + math.radians(140)) * 5 * inner + ox),
                 int(m.y - math.cos(rad + math.radians(140)) * 5 * inner + oy)),
                (int(m.x + math.sin(rad - math.radians(140)) * 5 * inner + ox),
                 int(m.y - math.cos(rad - math.radians(140)) * 5 * inner + oy)),
            ])
            # Bright tip
            pygame.draw.circle(layer, (255, 255, 255, 255),
                               (int(tip_x + ox), int(tip_y + oy)), 1)
        target.blit(layer, (0, 0))

    def _screen_clear_damage(self) -> None:
        """Bomb: kill all enemy bullets and damage visible enemies."""
        # Full-screen white flash (decreases over time)
        self._screen_flash = 1.0
        # BLOQUE 26: player also flashes white for a moment
        self._bomb_flash = 1.0
        # Clear enemy bullets
        for p in self._bullets.pool:
            if p.active and p.owner in (OWNER_ENEMY, OWNER_BOSS):
                p.active = False
                self._bullets.pool.release(p)
        # Damage all enemies
        for e in self._enemies.pool:
            if e.active and not e.is_mini:
                killed = e.apply_damage(400)
                if killed:
                    self._on_enemy_killed(e)
        # Shockwave ring expanding from player
        self._add_shockwave(self._player.x, self._player.y, 80.0)
    # ------------------------------------------------------------------
    # Enemies: spawn + update
    # ------------------------------------------------------------------
    def _populate_spawn_queue(self) -> None:
        if self._wave_idx >= len(self._wave_mgr.scripts):
            return
        script = self._wave_mgr.scripts[self._wave_idx]
        # BLOQUE 47: prefer explicit `formation` spec over legacy `mix`
        formation = self._wave_mgr.current_formation()
        if formation is not None:
            from src.systems.wave_manager import spawn_formation
            spawns = spawn_formation(formation)
            # Each enemy is spawned with a small stagger so they don't all
            # appear at the exact same frame. SQUADRON followers get an
            # extra delay equal to their time_offset_s.
            base_stagger = 0.12
            for i, sp in enumerate(spawns):
                try:
                    kind = EnemyKind(sp.kind)
                except ValueError:
                    continue
                stagger = i * base_stagger + sp.time_offset_s
                # Mark for squadron if needed
                is_squadron = formation.formation_type == "squadron"
                self._pending_wave_spawns.append((
                    stagger, kind, sp.x, sp.y, is_squadron,
                    sp.time_offset_s,
                ))
            return
        # Legacy `mix` path
        mix: dict[str, int] = script.get("mix", {})
        for kind_str, count in mix.items():
            try:
                kind = EnemyKind(kind_str)
            except ValueError:
                continue
            for _ in range(count):
                x = random.uniform(20, INTERNAL_W - 20)
                y = -10.0 - random.uniform(0, 60)
                self._pending_wave_spawns.append((0.0, kind, x, y, False, 0.0))
        random.shuffle(self._pending_wave_spawns)
        for i, item in enumerate(self._pending_wave_spawns):
            t = i * WAVE_SPAWN_INTERVAL_S
            self._pending_wave_spawns[i] = (t,) + item[1:]

    def _populate_level1_queue(self) -> None:
        """BLOQUE 48: chained wave system for level 1 mode.

        Replaces the BLOQUE 29 absolute-timestamp spawn loop with a
        chain of 4 waves that trigger the next one on completion (or
        max_duration timeout). Each wave has its own spawn cadence,
        max active count (8), and composition.

        Total ships: 27 (21 SCOUT + 4 CRUISER + 2 HEAVY).
        Score: 35 flat + 12 perfect = 47pt max.
        """
        from src.systems.wave_manager import WaveChain, BossTrigger
        from src.core.settings import MAX_ENEMIES_ON_SCREEN
        self._level1_chain = WaveChain(max_alive=MAX_ENEMIES_ON_SCREEN)
        self._level1_boss_trigger = BossTrigger()
        # Clear any leftover pending spawns (legacy mode)
        self._pending_wave_spawns = []

    def _spawn_pending(self, dt: float) -> None:
        if self._is_boss:
            return
        # BLOQUE 48: level 1 mode uses the chained WaveChain (not the
        # legacy _pending_wave_spawns list)
        if self._is_level1_mode() and self._level1_chain is not None:
            self._spawn_level1_enemies(dt)
            return
        self._wave_spawn_timer += dt
        remaining: list[tuple[float, EnemyKind, float, float, bool, float]] = []
        for item in self._pending_wave_spawns:
            # BLOQUE 47: 6-tuple with is_squadron + time_offset_s
            if len(item) == 6:
                when, kind, x, y, is_squadron, time_offset_s = item
            else:
                when, kind, x, y = item
                is_squadron = False
                time_offset_s = 0.0
            if self._wave_spawn_timer >= when and self._enemies.active_count < WAVE_MAX_LIVE:
                e = self._enemies.spawn(kind, x, y)
                if e is not None:
                    # BLOQUE 47: tag the enemy as a squadron member
                    if is_squadron:
                        e.squadron_id = self._squadron_id_counter
                        e.squadron_origin_x = float(x)
                        e.squadron_time_offset = float(time_offset_s)
                        # Only the first enemy of this squadron (offset 0)
                        # is the leader; the rest are followers
                        if time_offset_s <= 0.0:
                            self._squadron_id_counter += 1
                    self._wave_spawn_timer = 0.0
                    self._enemies_spawned_total += 1
            else:
                if len(item) == 6:
                    remaining.append(item)
                else:
                    remaining.append((when, kind, x, y, False, 0.0))
        self._pending_wave_spawns = remaining

    def _spawn_sub_boss(self) -> None:
        """BLOQUE 50: spawn the mid-wave sub-boss.

        Spawned near the top-center of the screen, drops in with the
        frenetic sine wobble from the SUB_BOSS config. The runtime
        handles the bullet pattern (it has fire_cooldown_s=0.4 — 2.5
        shots/s aimed at the player).
        """
        from src.entities.enemies.enemy import EnemyKind
        from src.core.settings import INTERNAL_W
        e = self._enemies.spawn(EnemyKind.SUB_BOSS, INTERNAL_W / 2, -16.0)
        if e is not None:
            self._sub_boss_alive = True
            self._sub_boss_intro_done = True
            # Mark with a flag so _on_enemy_killed knows to clear the
            # chain pending and award the sub-boss bonus score. We use
            # a simple attribute on the enemy.
            e._is_sub_boss_instance = True  # type: ignore[attr-defined]

    def _spawn_level1_enemies(self, dt: float) -> None:
        """BLOQUE 48: spawn one enemy per tick from the chained WaveChain.

        Respects:
          - spawn cadence per wave
          - density cap (8 simultaneous)
          - max duration per wave (advances to next on timeout)
        """
        from src.entities.enemies.enemy import EnemyKind
        chain = self._level1_chain
        assert chain is not None
        chain.tick(dt)
        if chain.waves_complete:
            return  # no more spawns
        if chain.current_wave_idx >= len(chain.wave_specs):
            return
        spec = chain.wave_specs[chain.current_wave_idx]
        # Find the next enemy to spawn (next index in the spec's enemies list)
        next_idx = chain._spawned_per_wave[chain.current_wave_idx]
        if next_idx >= len(spec["enemies"]):
            return  # this wave fully spawned; wait for next
        kind_str = spec["enemies"][next_idx]
        kind = EnemyKind[kind_str]
        # Try to spawn at top with formation-appropriate position
        x = self._level1_spawn_x(spec.get("formation", "line"), next_idx, len(spec["enemies"]))
        y = -10.0
        if chain.spawn(chain.current_wave_idx, x, y, kind_str):
            e = self._enemies.spawn(kind, x, y)
            if e is not None:
                # Mark the enemy with the wave_idx so kill() can decrement
                # the right counter. We use a simple approach: every enemy in
                # level 1 mode increments kills on kill (single source of truth).
                self._enemies_spawned_total += 1

    def _level1_spawn_x(self, formation: str, idx: int, total: int) -> float:
        """BLOQUE 48: formation-aware spawn X position for level 1 mode."""
        cx = INTERNAL_W / 2
        if formation == "diagonal":
            # Spread across the width, one per line of sight
            margin = 30.0
            if total <= 1:
                return cx
            step = (INTERNAL_W - 2 * margin) / max(1, total - 1)
            return margin + idx * step
        if formation == "v":
            # V: middle at top, wings angled down — but we spawn at y=-10,
            # so use horizontal V (wider than LINE)
            margin = 20.0
            if total <= 1:
                return cx
            step = (INTERNAL_W - 2 * margin) / max(1, total - 1)
            return margin + idx * step
        if formation == "line":
            # Horizontal line
            margin = 20.0
            if total <= 1:
                return cx
            step = (INTERNAL_W - 2 * margin) / max(1, total - 1)
            return margin + idx * step
        if formation == "diamond":
            # Diamond: 4 corners, center; with 6 ships, the order is
            # top, right, bottom, left, top-right, top-left (approx)
            if total <= 1:
                return cx
            step = (INTERNAL_W - 40.0) / max(1, total - 1)
            return 20.0 + idx * step
        return cx

    def _update_enemies(self, dt: float) -> None:
        # BLOQUE 47: SQUADRON path parameters — shared for all squadron members
        # in this scene. The leader sets the curve; followers replay it with delay.
        squadron_freq_hz = 0.4       # 0.4 Hz = 2.5s per cycle
        squadron_amplitude = 50.0    # px swing left-right
        squadron_y_speed = 50.0      # px/s downward (slower than pattern_speed
                                      # for more readable choreography)
        # BLOQUE 50: ensure the sub-boss is alive if the chain says so.
        # After SUB_BOSS_INTRO transitions back to GAMEPLAY, the first
        # _update_enemies tick spawns the sub-boss. The chain stays
        # paused (sub_boss_pending=True) until the sub-boss is killed.
        if (
            self._is_level1_mode()
            and self._level1_chain is not None
            and self._level1_chain.sub_boss_pending
            and not self._sub_boss_alive
        ):
            self._spawn_sub_boss()
        for e in self._enemies.pool:
            if not e.active:
                continue
            e.update(dt, self._player.x, self._player.y)
            # BLOQUE 47: SQUADRON path override
            if e.squadron_id >= 0:
                # Initialize age on first frame (start behind the leader by time_offset)
                if e.squadron_age == 0.0 and e.squadron_time_offset > 0.0:
                    e.squadron_age = -e.squadron_time_offset
                e.squadron_age += dt
                age = e.squadron_age
                # Path: sine-wave x over linear-falling y
                e.x = e.squadron_origin_x + math.sin(
                    age * squadron_freq_hz * 2.0 * math.pi
                ) * squadron_amplitude
                e.y = 16.0 + age * squadron_y_speed
            # Fire
            if e.on_fire:
                e.on_fire = False
                self._spawn_enemy_bullet(e)
            # Death
            if e.on_death:
                e.on_death = False
                self._on_enemy_killed(e)
            # Spawn mini (Drone / Carrier)
            if e.pending_spawn_count > 0:
                count = e.pending_spawn_count
                e.pending_spawn_count = 0
                for _ in range(count):
                    self._enemies.spawn(EnemyKind.DRONE, e.x + random.uniform(-8, 8), e.y + 4)
            # Offscreen cull
            if e.state.name == "DEAD" or e.y > INTERNAL_H + 30:
                # BLOQUE 43: count enemies that left the screen alive (escaped)
                if e.y > INTERNAL_H + 30 and e.state.name != "DEAD":
                    self._enemies_escaped += 1
                    # BLOQUE 48: also mark the chain as broken perfect
                    if self._is_level1_mode() and self._level1_chain is not None:
                        self._level1_chain.escape()
                self._enemies.release(e)
        # Boss
        if self._is_boss and self._boss is not None and self._boss.active:
            # Boss slides in from off-screen for first 1.5s
            self._boss_entry_t += dt
            if self._boss_entry_t < 1.5:
                # Override y position to slide from -50 to anchor_y
                from src.entities.enemies.boss import BOSS_CONFIGS
                cfg = BOSS_CONFIGS[self._boss.id]
                progress = min(1.0, self._boss_entry_t / 1.5)
                eased = 1.0 - (1.0 - progress) ** 3
                self._boss.y = -50 + (cfg.anchor_y - -50) * eased
            else:
                # Normal boss behavior (sine oscillation)
                self._boss.update(dt)
            # Boss attack selection (suppressed during entry)
            if self._boss_entry_t >= 0.8:
                attack = self._boss.select_attack()
                if attack >= 0:
                    self._spawn_boss_attack(attack)
            # Boss death
            if self._boss.hp <= 0:
                self._on_boss_killed()

    def _spawn_enemy_bullet(self, e: Enemy) -> None:
        from src.entities.enemies.enemy import ENEMY_CONFIGS
        cfg = ENEMY_CONFIGS[e.kind]
        if cfg.bullet_speed <= 0.0:
            return  # Kamikaze / Drone don't fire
        # Aimed shot (toward player)
        dx = self._player.x - e.x
        dy = self._player.y - e.y
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            return
        vx = (dx / dist) * cfg.bullet_speed
        vy = (dy / dist) * cfg.bullet_speed
        self._bullets.spawn(
            BULLET_ENEMY, e.x, e.y + 4, vx, vy,
            damage=cfg.fire_damage, owner=OWNER_ENEMY,
        )

    def _spawn_boss_attack(self, attack: int) -> None:
        if self._boss is None:
            return
        # BLOQUE 52: GOLIATH attack 8 = throw the giant's spear.
        # The spear has its own state machine (winding/thrown) and is
        # destructible by the player. The boss enters "winding" phase
        # for 0.3s, then the spear is spawned and the boss enters
        # "thrown" for 1.2s while the spear is in flight.
        if attack == 8 and self._boss.id == BossId.GOLIATH:
            self._start_goliath_spear_throw()
            return
        bx, by = self._boss.x, self._boss.y + 12
        if attack == 0:
            # Aimed
            dx = self._player.x - bx
            dy = self._player.y - by
            d = math.hypot(dx, dy)
            if d > 0.01:
                self._bullets.spawn(
                    BULLET_BOSS, bx, by, (dx/d) * 220, (dy/d) * 220,
                    damage=2, owner=OWNER_BOSS,
                )
        elif attack == 1:
            # 3-spread
            for ang in (-15.0, 0.0, 15.0):
                r = math.radians(ang)
                self._bullets.spawn(
                    BULLET_BOSS, bx, by,
                    math.sin(r) * 220, math.cos(r) * 220,
                    damage=1, owner=OWNER_BOSS,
                )
        elif attack == 3:
            # Ring
            for i in range(8):
                r = math.radians(i * 45.0)
                self._bullets.spawn(
                    BULLET_BOSS, bx, by,
                    math.sin(r) * 200, math.cos(r) * 200,
                    damage=1, owner=OWNER_BOSS,
                )

    def _start_goliath_spear_throw(self) -> None:
        """BLOQUE 52: begin the GOLIATH spear throw wind-up animation.

        Transitions _boss_spear_phase from "ready" → "winding". The
        _update_boss_spears tick will then advance the timer and
        spawn the actual spear projectile at the right moment.
        """
        # Only start a new throw if we're ready (not already winding/thrown)
        if self._boss_spear_phase != "ready":
            return
        self._boss_spear_phase = "winding"
        self._boss_spear_phase_t = 0.0

    def _spawn_boss_spear(self) -> None:
        """BLOQUE 52: spawn the main GOLIATH spear projectile.

        Fired at the end of the wind-up phase (0.3s after the throw
        started). The spear is aimed at the player and follows a
        serpentine path. 3 HP — player can shoot it down for bonus
        points, and on death it splits into 3 fragments in a cone.
        """
        if self._boss is None:
            return
        # Initial direction = toward player
        bx, by = self._boss.x, self._boss.y + 18  # boss hand height
        dx = self._player.x - bx
        dy = self._player.y - by
        d = math.hypot(dx, dy) or 1.0
        base_vx = dx / d
        base_vy = dy / d
        # Perpendicular (for the serpentine wave). Rotate 90° clockwise.
        # pygame y is down, so rotating (vx, vy) by -90° gives (vy, -vx).
        perp_vx = base_vy
        perp_vy = -base_vx
        spear = BossSpear(
            active=True,
            kind="main",
            is_main=True,
            x=bx, y=by,
            base_vx=base_vx, base_vy=base_vy,
            perp_vx=perp_vx, perp_vy=perp_vy,
            speed=160.0,
            wave_amp=18.0, wave_freq_hz=1.6,
            wave_amp_growth=10.0,
            hp=3, max_hp=3,
            damage=2,
            life=6.0, max_life=6.0,
        )
        self._boss_spears.append(spear)
        # SFX + small visual cue (white flash at the boss hand)
        self._emit_burst(bx, by, count=6, kind="spark", color=(255, 220, 160))

    def _split_spear(self, spear: BossSpear) -> None:
        """BLOQUE 52: when the main spear is destroyed, spawn 3 fragments
        in a 40° cone (20° left/right of the original direction).
        Fragments are smaller, faster, and only have 1 HP each.
        """
        if not spear.is_main:
            return
        # Mark the main spear as inactive (it's been "destroyed" —
        # _update_boss_spears will cull it from the list next tick).
        spear.active = False
        for offset_deg in (-20.0, 0.0, 20.0):
            # Rotate the base direction by offset_deg
            base_angle = math.atan2(spear.base_vy, spear.base_vx)
            frag_angle = base_angle + math.radians(offset_deg)
            frag_vx = math.cos(frag_angle)
            frag_vy = math.sin(frag_angle)
            # Perpendicular
            perp_vx = frag_vy
            perp_vy = -frag_vx
            frag = BossSpear(
                active=True,
                kind="fragment",
                is_main=False,
                x=spear.x, y=spear.y,
                base_vx=frag_vx, base_vy=frag_vy,
                perp_vx=perp_vx, perp_vy=perp_vy,
                speed=240.0,  # faster than the main spear
                wave_amp=4.0, wave_freq_hz=2.0,  # smaller wave
                wave_amp_growth=3.0,
                hp=1, max_hp=1,
                damage=1,
                life=2.5, max_life=2.5,
            )
            self._boss_spears.append(frag)
        # Player gets bonus points for destroying the main spear
        bonus = 500
        self._scoring.on_kill(bonus)
        self._score_popups.append(ScorePopup(
            x=spear.x, y=spear.y - 4, vy=-30.0,
            text=f"SPEAR +{bonus}", color=(255, 220, 140),
            life=1.4, max_life=1.4,
        ))

    def _update_boss_spears(self, dt: float) -> None:
        """BLOQUE 52: tick the GOLIATH spear state machine and update
        all in-flight spear projectiles (serpentine motion + lifetime).
        """
        # 1) State machine for the boss's hand-held spear
        if self._boss_spear_phase == "winding":
            self._boss_spear_phase_t += dt
            if self._boss_spear_phase_t >= 0.3:
                # Wind-up complete → spawn the spear, transition to "thrown"
                self._spawn_boss_spear()
                self._boss_spear_phase = "thrown"
                self._boss_spear_phase_t = 0.0
        elif self._boss_spear_phase == "thrown":
            self._boss_spear_phase_t += dt
            if self._boss_spear_phase_t >= 1.2:
                # Recovered: respawn the spear in the boss's hand
                self._boss_spear_phase = "ready"
                self._boss_spear_phase_t = 0.0
        # 2) Update all active spear projectiles
        alive: list[BossSpear] = []
        for s in self._boss_spears:
            s.update(dt)
            # Offscreen cull
            if s.active and -20 < s.x < INTERNAL_W + 20 and -20 < s.y < INTERNAL_H + 20:
                alive.append(s)
            elif s.active:
                s.active = False  # went off screen
        self._boss_spears = alive

    # ------------------------------------------------------------------
    # Collisions
    # ------------------------------------------------------------------
    def _handle_collisions(self) -> None:
        # Player bullets ↔ enemies
        for p in self._bullets.pool:
            if not p.active or p.owner != OWNER_PLAYER:
                continue
            pr = pygame.Rect(int(p.x) - 2, int(p.y) - 3, 4, 6)
            for e in self._enemies.pool:
                if not e.active or e.state.name == "DEAD":
                    continue
                if pr.colliderect(e.hitbox()):
                    killed = e.apply_damage(p.damage)
                    # Bigger impact burst (8 sparks instead of 3)
                    self._emit_burst(p.x, p.y, count=8, kind="spark")
                    self._emit_burst(p.x, p.y, count=3, kind="shrapnel")
                    # Hit feedback: flash white for 0.08s
                    self._enemy_flash[id(e)] = 0.08
                    if killed:
                        self._on_enemy_killed(e)
                    # Piercing bullets keep going until pierce_hits >= pierce
                    if p.pierce > 0 and p.pierce_hits < p.pierce:
                        p.pierce_hits += 1
                    else:
                        p.active = False
                        self._bullets.pool.release(p)
                        break
        # Player bullets ↔ boss
        if self._is_boss and self._boss is not None and self._boss.active:
            boss_hit = self._boss.hitbox()
            # BLOQUE 53a: check player bullets against the GOLIATH shield
            # FIRST (before the body) — if a bullet hits the shield, it
            # counts toward the shield charge instead of damaging the
            # boss. The shield is a circle on the boss's left side.
            if self._boss.id == BossId.GOLIATH and self._boss_spear_phase != "thrown":
                self._handle_shield_collisions()
            for p in self._bullets.pool:
                if not p.active or p.owner != OWNER_PLAYER:
                    continue
                pr = pygame.Rect(int(p.x) - 2, int(p.y) - 3, 4, 6)
                if pr.colliderect(boss_hit):
                    prev_hp = self._boss.hp
                    self._boss.hp -= p.damage
                    p.active = False
                    self._bullets.pool.release(p)
                    self._emit_burst(p.x, p.y, count=2, kind="spark")
                    # BLOQUE 51: hit feedback flash
                    self._boss_flash[id(self._boss)] = 0.08
                    # Check phase change
                    cfg = BOSS_CONFIGS[self._boss.id]
                    new_phase = 1
                    for i, threshold in enumerate(cfg.phase_thresholds):
                        if self._boss.hp / self._boss.max_hp <= threshold:
                            new_phase = i + 2
                    if new_phase != self._boss.phase:
                        self._boss.phase = new_phase
                        # BLOQUE 27: bigger phase change burst
                        self._emit_burst(self._boss.x, self._boss.y, count=24, kind="explosion")
                        self._emit_burst(self._boss.x, self._boss.y, count=12, kind="spark")
                        self._add_shockwave(self._boss.x, self._boss.y, 50.0)
                        self._hitstop.trigger(6)
                        self._shake.add_trauma(0.5)
                        self._play_sfx("multiplier_up", volume=0.7)
                    # Check death
                    if self._boss.hp <= 0:
                        self._on_boss_killed()
        # Enemy bullets ↔ player
        phb = self._player.hitbox
        for p in self._bullets.pool:
            if not p.active or p.owner == OWNER_PLAYER:
                continue
            pr = pygame.Rect(int(p.x) - 2, int(p.y) - 3, 4, 6)
            if pr.colliderect(phb):
                p.active = False
                self._bullets.pool.release(p)
                took = self._player.take_damage(p.damage)
                self._emit_burst(p.x, p.y, count=4, kind="spark")
                # BLOQUE 27: hit sparks ring around the player
                if took:
                    self._emit_burst(self._player.x, self._player.y, count=10, kind="spark")
                    self._emit_burst(self._player.x, self._player.y, count=4, kind="debris")
                self._shake.add_trauma(0.15)
                if took:
                    self._play_sfx("hit", volume=0.6)
                    self._hitstop.trigger(2)
        # Enemies ↔ player (Kamikaze / contact)
        for e in self._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            if e.hitbox().colliderect(phb):
                took = self._player.take_damage(1)
                # Kamikaze dies on contact
                if e.kind == EnemyKind.KAMIKAZE:
                    e.apply_damage(99)
                    self._on_enemy_killed(e)
                self._emit_burst(e.x, e.y, count=6, kind="spark")
                self._shake.add_trauma(0.2)
                if took:
                    self._play_sfx("hit", volume=0.6)
                    self._hitstop.trigger(2)
        # BLOQUE 52: GOLIATH spear collisions (player bullets → spear, spear → player)
        self._handle_spear_collisions(phb)

    def _handle_shield_collisions(self) -> None:
        """BLOQUE 53a: handle player bullets hitting GOLIATH's shield.

        The shield is a circle at the boss's left (offset -30 from boss
        center, +12 from boss top, radius 13). Player bullets that hit
        the shield circle are consumed and increment a charge counter.
        When the counter reaches 20, the boss fires a 1s charged laser.

        Bullets still pass through to the boss body if they miss the
        shield (handled by the regular boss collision code below).
        """
        if self._boss is None:
            return
        # If the laser is already firing, don't accumulate more charge
        if self._boss_shield_laser_t > 0.0:
            return
        # Compute shield position in world space (mirrors _draw_goliath
        # which centers the visual on the hitbox). The visual is centered
        # on (cx, cy) with vw=64, vh=60; the shield is at:
        #   shield_cx = boss.x - 30
        #   shield_cy = boss.y + 12
        #   shield_r = 13
        sx = self._boss.x - 30
        sy = self._boss.y + 12
        sr = 13
        shield_rect = pygame.Rect(int(sx - sr), int(sy - sr), sr * 2, sr * 2)
        for p in self._bullets.pool:
            if not p.active or p.owner != OWNER_PLAYER:
                continue
            pr = pygame.Rect(int(p.x) - 2, int(p.y) - 3, 4, 6)
            if pr.colliderect(shield_rect):
                p.active = False
                self._bullets.pool.release(p)
                self._boss_shield_hits += 1
                # Spark feedback on the shield
                self._emit_burst(p.x, p.y, count=3, kind="spark",
                                  color=(180, 200, 255))
                # If we've hit 20, fire the laser
                if self._boss_shield_hits >= 20:
                    self._start_shield_laser()
                break  # bullet can only hit one thing

    def _start_shield_laser(self) -> None:
        """BLOQUE 53a: trigger the 1s charged laser attack.

        The boss stops firing regular attacks for 1 second, the laser
        beam is rendered from the boss to the bottom of the screen,
        and any player contact deals heavy damage.
        """
        self._boss_shield_laser_t = self._boss_shield_laser_duration
        self._boss_shield_hits = 0  # reset counter
        # Visual + SFX cue (bright flash at the boss hand)
        if self._boss is not None:
            self._emit_burst(self._boss.x - 30, self._boss.y + 12,
                              count=20, kind="explosion")
            self._add_shockwave(self._boss.x - 30, self._boss.y + 12, 40.0)
        self._shake.add_trauma(0.4)
        self._play_sfx("explode_medium", volume=0.9)

    def _update_shield_laser(self, dt: float) -> None:
        """BLOQUE 53a: tick the shield laser duration + damage the
        player if they're in the beam path.
        """
        if self._boss_shield_laser_t <= 0.0:
            return
        if self._boss is None or not self._boss.active:
            self._boss_shield_laser_t = 0.0
            return
        # Decrement timer
        self._boss_shield_laser_t = max(0.0, self._boss_shield_laser_t - dt)
        # Check player collision with the laser beam
        # Beam: from shield position (boss.x-30, boss.y+12) straight
        # down to the bottom of the screen
        beam_x = self._boss.x - 30
        beam_top_y = self._boss.y + 12
        beam_width = 8
        beam_rect = pygame.Rect(
            int(beam_x - beam_width / 2),
            int(beam_top_y),
            beam_width,
            INTERNAL_H - int(beam_top_y) + 4,
        )
        if beam_rect.colliderect(self._player.hitbox):
            # Per-bullet damage (throttled so it's not instant death
            # at 60fps). Cooldown tracked per-frame, not per-bullet.
            took = self._player.take_damage(1)
            self._emit_burst(self._player.x, self._player.y,
                              count=4, kind="spark", color=(255, 100, 60))
            self._shake.add_trauma(0.18)
            if took:
                self._play_sfx("hit", volume=0.6)
                self._hitstop.trigger(1)

    def _handle_spear_collisions(self, phb: pygame.Rect) -> None:
        """BLOQUE 52: collision logic for boss spears.
        - Player bullets damage the spear; at HP=0, main spears split
          into 3 fragments, fragments just die.
        - The spear damages the player on contact (2 damage for main,
          1 for fragments).
        """
        if not self._boss_spears:
            return
        # Player bullets ↔ spears
        for p in self._bullets.pool:
            if not p.active or p.owner != OWNER_PLAYER:
                continue
            pr = pygame.Rect(int(p.x) - 2, int(p.y) - 3, 4, 6)
            for s in self._boss_spears:
                if not s.active:
                    continue
                cx, cy, w, h = s.hitbox()
                sr = pygame.Rect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
                if pr.colliderect(sr):
                    p.active = False
                    self._bullets.pool.release(p)
                    killed = s.apply_damage(1)
                    # Hit feedback
                    self._emit_burst(cx, cy, count=4, kind="spark",
                                      color=(255, 200, 120))
                    if killed:
                        # Explosion visual
                        self._emit_burst(cx, cy, count=10, kind="shrapnel")
                        self._emit_burst(cx, cy, count=6, kind="spark",
                                          color=(255, 160, 80))
                        self._add_shockwave(cx, cy, 24.0)
                        # Main spear splits into 3 fragments
                        if s.is_main:
                            self._split_spear(s)
                        break  # bullet can only hit one spear
        # Spears ↔ player
        for s in self._boss_spears:
            if not s.active:
                continue
            cx, cy, w, h = s.hitbox()
            sr = pygame.Rect(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
            if sr.colliderect(phb):
                # Spear damages player and stops
                took = self._player.take_damage(s.damage)
                self._emit_burst(s.x, s.y, count=8, kind="spark",
                                  color=(255, 100, 60))
                self._shake.add_trauma(0.25)
                if took:
                    self._play_sfx("hit", volume=0.6)
                    self._hitstop.trigger(2)
                # Main spear splits when blocked by player; fragments just die
                s.active = False
                if s.is_main:
                    self._split_spear(s)

    # ------------------------------------------------------------------
    # Kill handlers
    # ------------------------------------------------------------------
    def _on_enemy_killed(self, e: Enemy) -> None:
        score = _ENEMY_SCORE.get(e.kind, 50)
        # Element bonus: plasma bonus vs heavy/cruiser/turret/carrier
        element_bonus = e.kind.value in ("heavy", "cruiser", "turret", "carrier")
        awarded = self._scoring.on_kill(score, is_boss=False, is_element_bonus=element_bonus)
        # BLOQUE 50: sub-boss gets the SUB_BOSS_FLAT_SCORE bonus on top of
        # the regular score, and clearing the sub-boss resumes the chain.
        # BLOQUE 53d: in level 1 mode, the sub-boss drops a tech upgrade
        # (HP_BOOST_10 = +10% max HP).
        if e.kind == EnemyKind.SUB_BOSS:
            from src.core.settings import SUB_BOSS_FLAT_SCORE
            self._scoring.on_kill(SUB_BOSS_FLAT_SCORE)
            self._sub_boss_alive = False
            if self._is_level1_mode() and self._level1_chain is not None:
                self._level1_chain.clear_sub_boss_pending()
                # BLOQUE 53d: drop HP_BOOST_10 tech upgrade
                if "HP_BOOST_10" not in self._player.tech_upgrades:
                    self._player.add_tech_upgrade("HP_BOOST_10")
                    self._emit_burst(e.x, e.y, count=20, kind="spark",
                                      color=(120, 255, 180))
                    self._score_popups.append(ScorePopup(
                        x=e.x, y=e.y - 6, vy=-30.0,
                        text="HP+10%", color=(120, 255, 180),
                        life=1.4, max_life=1.4,
                    ))
                    self._play_sfx("multiplier_up", volume=0.8)
        # BLOQUE 53d: in level 1 mode, killing the LAST ship on a perfect
        # run drops the GOLIATH_SUMMON tech upgrade (summons a friendly
        # GOLIATH at the end of minute 1, i.e. second 59+).
        if (self._is_level1_mode()
                and self._level1_chain is not None
                and self._level1_chain.perfect
                and "GOLIATH_SUMMON" not in self._player.tech_upgrades
                and self._level1_chain.kills + 1 >= self._level1_chain.total_ships):
            self._player.add_tech_upgrade("GOLIATH_SUMMON")
            self._emit_burst(e.x, e.y, count=20, kind="spark",
                              color=(255, 200, 100))
            self._score_popups.append(ScorePopup(
                x=e.x, y=e.y - 6, vy=-30.0,
                text="GOLIATH SUMMON", color=(255, 220, 140),
                life=1.6, max_life=1.6,
            ))
            self._play_sfx("act_clear", volume=0.7)
        # BLOQUE 24: detect weapon level-up before/after on_kill
        level_before = self._weapon.level.value
        # Weapon XP
        self._weapon.on_kill(e.kind.value)
        if self._weapon.level.value > level_before:
            self._level_up_flash = 0.9
            self._emit_burst(self._player.x, self._player.y, count=16, kind="glow")
            self._play_sfx("multiplier_up", volume=0.8)
        # Particles — BLOQUE 25: more particles on tougher kills
        if e.kind in (EnemyKind.HEAVY, EnemyKind.CARRIER):
            self._emit_burst(e.x, e.y, count=32, kind="explosion")
            self._emit_burst(e.x, e.y, count=20, kind="shrapnel")
            self._emit_burst(e.x, e.y, count=12, kind="smoke")
            self._add_shockwave(e.x, e.y, 50.0)
        elif e.kind in (EnemyKind.CRUISER, EnemyKind.SNIPER, EnemyKind.TURRET):
            self._emit_burst(e.x, e.y, count=22, kind="explosion")
            self._emit_burst(e.x, e.y, count=10, kind="shrapnel")
            self._add_shockwave(e.x, e.y, 30.0)
        else:
            self._emit_burst(e.x, e.y, count=14, kind="explosion")
        # SFX
        if e.kind in (EnemyKind.HEAVY, EnemyKind.CARRIER):
            self._play_sfx("explode_medium", volume=0.7)
        else:
            self._play_sfx("explode_small", volume=0.5)
        # Score popup (floats up)
        self._score_popups.append(ScorePopup(
            x=e.x, y=e.y - 4, vy=-30.0,
            text=f"+{awarded}", color=(255, 240, 100),
            life=1.0, max_life=1.0,
        ))
        # Multiplier up SFX
        if self._scoring.on_max_multiplier:
            self._play_sfx("multiplier_up", volume=0.6)
            self._scoring.on_max_multiplier = False
        # Hitstop on tougher kills
        if e.kind in (EnemyKind.HEAVY, EnemyKind.CARRIER, EnemyKind.SNIPER):
            self._hitstop.trigger(3)
            self._shake.add_trauma(0.2)
        # Power-up drop
        if not self._is_boss:
            self._maybe_drop_powerup(e)
        # Wave progress
        if not self._is_boss:
            self._wave_mgr.current.kills += 1
            # BLOQUE 48: also tick the level 1 chain (single source of truth
            # for the new chained boss trigger). BLOQUE 50: sub-boss kills
            # are NOT counted in the chain (sub-boss is a separate challenge).
            if (
                self._is_level1_mode()
                and self._level1_chain is not None
                and e.kind != EnemyKind.SUB_BOSS
            ):
                self._level1_chain.kill()
            self._wave_mgr.on_wave_cleared = self._check_wave_cleared()
        # Free
        self._enemies.release(e)

    def _on_boss_killed(self) -> None:
        if self._boss is None:
            return
        # BLOQUE 28: mark this frame as a boss kill so _check_player_death
        # doesn't override the win transition with GAME_OVER if the player
        # also dies at the same time.
        self._boss_killed_this_frame = True
        # Cache boss position before we release the reference
        bx, by = self._boss.x, self._boss.y
        boss_id = self._boss.id
        score = BOSS_CONFIGS[boss_id].score
        self._scoring.on_kill(score, is_boss=True)
        self._scoring.on_boss_defeated(BOSS_CONFIGS[boss_id].name)
        # BLOQUE 22: multi-stage explosion (3 bursts staggered over 0.6s)
        # Stage 1 — immediate
        self._emit_burst(bx, by, count=48, kind="explosion")
        self._emit_burst(bx, by, count=24, kind="shrapnel")
        self._add_shockwave(bx, by, 100.0)
        # Stage timer drives subsequent bursts
        self._boss_death_stage = 1
        self._boss_death_timer = 0.0
        # Place a death_effect that we'll step in update
        # (Using a small object instead of more state)
        self._boss_death_pos = (bx, by)
        # Heavy hitstop + slow-mo on first stage
        self._hitstop.trigger(20)
        self._shake.add_trauma(0.8)
        self._slowmo.trigger(0.30, 30)
        # Full-screen flash (re-using _screen_flash for the bomb-style flash)
        self._screen_flash = 1.0
        self._play_sfx("explode_boss", volume=1.0)
        # Score popup
        self._score_popups.append(ScorePopup(
            x=bx, y=by - 8, vy=-40.0,
            text=f"+{score}", color=(255, 220, 100),
            life=2.0, max_life=2.0,
        ))
        self._bosses.release(self._boss)
        self._boss = None
        # Transition out
        from src.core.scene_manager import GameState
        if self._act >= 3:
            self._transition_to(GameState.VICTORY)
        else:
            self._transition_to(GameState.ACT_CLEARED)

    # ------------------------------------------------------------------
    # Wave state
    # ------------------------------------------------------------------
    def _check_wave_cleared(self) -> bool:
        if self._wave_idx >= len(self._wave_mgr.scripts):
            return False
        if self._wave_mgr.current.kills >= self._wave_mgr.scripts[self._wave_idx].get("kill_target", 0):
            return True
        return False

    def _is_level1_mode(self) -> bool:
        """BLOQUE 29: first level = 5 min OR 50 kills."""
        return (not self._is_boss
                and self._wave_idx == 0
                and self._act == 1)

    def _update_wave_state(self, dt: float) -> None:
        if self._is_boss:
            return
        self._wave_mgr.current.elapsed_s += dt
        # BLOQUE 48: level 1 mode uses the chained WaveChain + BossTrigger
        if self._is_level1_mode() and self._level1_chain is not None:
            self._update_level1_wave_state()
            return
        # Non-level1 mode: legacy wave script (kill_target + time_limit)
        if self._wave_mgr.current.kills >= self._wave_mgr.scripts[self._wave_idx].get("kill_target", 0):
            # Wave cleared — trigger boss intro or move on
            from src.core.scene_manager import GameState
            sub_boss = self._wave_mgr.scripts[self._wave_idx].get("sub_boss")
            if sub_boss is not None and (self._wave_idx % 6) == 5:
                # End of act → boss fight
                self._transition_to(GameState.BOSS_INTRO)
            else:
                # Next wave
                self._wave_idx += 1
                if self._wave_idx >= len(self._wave_mgr.scripts):
                    # All waves done → boss
                    self._transition_to(GameState.BOSS_INTRO)
                else:
                    self._wave_mgr.start_wave(self._wave_idx)
                    self._populate_spawn_queue()
        elif self._wave_mgr.current.elapsed_s > self._wave_mgr.scripts[self._wave_idx].get("time_limit_s", 60.0):
            # Time out: transition to boss anyway (lenient)
            from src.core.scene_manager import GameState
            self._transition_to(GameState.BOSS_INTRO)

    def _update_level1_wave_state(self) -> None:
        """BLOQUE 48: chain tick + boss trigger evaluation for level 1 mode.

        BLOQUE 50: also dispatches to SUB_BOSS_INTRO when the chain has
        just cleared a wave that triggers a mid-level sub-boss.

        BLOQUE 53d: at second 60, if the player has the GOLIATH_SUMMON
        tech upgrade, a friendly GOLIATH sweeps the remaining enemies
        and the boss fight is triggered immediately.
        """
        from src.core.scene_manager import GameState
        from src.core.settings import GOLIATH_SUMMON_AT_S
        chain = self._level1_chain
        trigger = self._level1_boss_trigger
        if chain is None or trigger is None:
            return
        # BLOQUE 50: sub-boss dispatch. If the chain is paused waiting for
        # a sub-boss to die and no sub-boss is alive yet, transition to
        # SUB_BOSS_INTRO. The sub-boss itself is spawned on the way back
        # to GAMEPLAY (see _spawn_sub_boss_on_resume).
        if chain.sub_boss_pending and not self._sub_boss_alive:
            self._transition_to(GameState.SUB_BOSS_INTRO)
            return
        # BLOQUE 53d: GOLIATH_SUMMON trigger. If the player has the
        # upgrade and the chain has been running for GOLIATH_SUMMON_AT_S
        # seconds, summon the friendly GOLIATH. This skips the rest of
        # the level and goes straight to the boss fight.
        if ("GOLIATH_SUMMON" in self._player.tech_upgrades
                and not getattr(self, "_goliath_summon_used", False)
                and chain.elapsed_s >= GOLIATH_SUMMON_AT_S
                and not chain.waves_complete):
            self._trigger_goliath_summon()
            return
        # Wave state is already advanced by _spawn_level1_enemies (tick).
        # Evaluate boss trigger using chain state.
        boss = trigger.evaluate(
            elapsed_s=chain.elapsed_s,
            waves_complete=chain.waves_complete,
            perfect=chain.perfect,
            kills=chain.kills,
        )
        if boss is not None:
            # Award perfect run bonus if applicable
            if chain.perfect:
                self._scoring.on_kill(0)  # placeholder; bonus added below
                from src.core.settings import PERFECT_RUN_BONUS
                self._scoring.on_kill(PERFECT_RUN_BONUS)
            self._transition_to(GameState.BOSS_INTRO)

    def _trigger_goliath_summon(self) -> None:
        """BLOQUE 53d: friendly GOLIATH sweeps remaining enemies.

        The friendly GOLIATH sweeps from the top of the screen downward,
        destroying every remaining enemy with a giant sword slash. After
        1.5s the boss fight is triggered. This is the player's reward
        for collecting the GOLIATH_SUMMON upgrade (dropped by the last
        ship on a perfect run).
        """
        from src.core.scene_manager import GameState
        from src.core.settings import PERFECT_RUN_BONUS
        self._goliath_summon_used = True
        # Big visual: friendly GOLIATH materializes at the top, then
        # a vertical sweep destroys all enemies.
        if self._boss is None:
            # Center "phantom" GOLIATH at top of screen for the sweep.
            sweep_x = INTERNAL_W // 2
            sweep_y = -10
        # Destroy all live enemies with a giant burst
        from src.entities.enemies.enemy import EnemyKind
        for e in self._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            # Big explosion at each enemy
            self._emit_burst(e.x, e.y, count=24, kind="explosion")
            self._emit_burst(e.x, e.y, count=14, kind="shrapnel")
            self._emit_burst(e.x, e.y, count=8, kind="spark",
                              color=(255, 220, 140))
            e.apply_damage(99)  # overkill — any enemy dies
        # Mark waves complete + perfect so boss trigger fires next tick
        if self._level1_chain is not None:
            self._level1_chain.waves_complete = True
        # Award the perfect bonus + a bonus for using GOLIATH_SUMMON
        self._scoring.on_kill(2000)
        # Big visual: screen flash + giant "GOLIATH" text overlay
        self._screen_flash = 1.0
        self._shake.add_trauma(0.7)
        self._hitstop.trigger(8)
        # Floating "GOLIATH" text at the player
        self._score_popups.append(ScorePopup(
            x=self._player.x, y=self._player.y - 16, vy=-60.0,
            text="GOLIATH SUMMONED!", color=(255, 220, 100),
            life=2.0, max_life=2.0,
        ))
        self._play_sfx("act_clear", volume=1.0)
        # Trigger the boss fight next frame (or via the boss trigger)
        self._transition_to(GameState.BOSS_INTRO)

    # ------------------------------------------------------------------
    # Player death
    # ------------------------------------------------------------------
    def _check_player_death(self) -> None:
        if not self._player.is_dead:
            return
        # BLOQUE 28: only trigger GAME_OVER when lives run out, not on every death.
        # Player can die and respawn while lives > 0.
        if self._player.lives >= 0:
            return
        # BLOQUE 28: if we just won the boss fight in the same frame,
        # don't override the ACT_CLEARED transition with GAME_OVER.
        if getattr(self, "_boss_killed_this_frame", False):
            return
        self._scoring.on_death()
        from src.core.scene_manager import GameState
        self._transition_to(GameState.GAME_OVER)

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return
        # BLOQUE 28: reset per-frame flags
        self._boss_killed_this_frame = False
        # BLOQUE 22: boss death stages advance even during hitstop so the
        # 3-stage explosion reads as a sequence instead of one frozen frame.
        self._update_boss_death_stages(dt)
        # Hitstop pauses game logic
        if self._hitstop.is_active:
            self._hitstop.update()
            return
        slowmo_factor = self._slowmo.get_factor()
        effective_dt = dt * slowmo_factor
        self._t += effective_dt
        prev_player_state = self._player.state
        self._read_input()
        # BLOQUE 29: compute nose angle from mouse position
        self._update_nose_angle()
        self._player.update(effective_dt)
        # Dash SFX: detect DASH entry
        if prev_player_state != PlayerState.DASH and self._player.state == PlayerState.DASH:
            self._play_sfx("dash", volume=0.5)
            self._emit_burst(self._player.x, self._player.y, count=6, kind="smoke")
        self._handle_firing(effective_dt)
        self._bullets.update(effective_dt)
        self._update_missiles(effective_dt)  # BLOQUE 39: homing missiles
        self._update_enemies(effective_dt)
        self._handle_collisions()
        self._spawn_pending(effective_dt)
        self._update_wave_state(effective_dt)
        self._update_score_popups(effective_dt)
        self._update_powerups(effective_dt)
        self._update_enemy_flash(effective_dt)
        self._update_shockwaves(effective_dt)
        # BLOQUE 52: tick GOLIATH spear state machine + spear projectiles
        self._update_boss_spears(effective_dt)
        # BLOQUE 53a: tick the shield laser timer + beam damage
        self._update_shield_laser(effective_dt)
        if self._screen_flash > 0.0:
            self._screen_flash = max(0.0, self._screen_flash - effective_dt * 2.5)
        # BLOQUE 22: muzzle flash + charge release flash decay
        if self._muzzle_flash > 0.0:
            self._muzzle_flash = max(0.0, self._muzzle_flash - effective_dt * 12.0)
        if self._charge_release_flash > 0.0:
            self._charge_release_flash = max(0.0, self._charge_release_flash - effective_dt * 4.0)
        # BLOQUE 24: pickup + level-up flash decay
        if self._pickup_flash > 0.0:
            self._pickup_flash = max(0.0, self._pickup_flash - effective_dt * 3.0)
        if self._level_up_flash > 0.0:
            self._level_up_flash = max(0.0, self._level_up_flash - effective_dt * 2.0)
        # BLOQUE 26: bomb flash decay (faster than screen flash)
        if self._bomb_flash > 0.0:
            self._bomb_flash = max(0.0, self._bomb_flash - effective_dt * 4.0)
        # BLOQUE 24: speed line drift accumulator
        self._speed_line_t += effective_dt
        # BLOQUE 26: continuous engine smoke + dash stars
        if not self._player.is_dead:
            self._emit_player_motion_particles(effective_dt)
        self._check_player_death_explosion()
        self._particles.update(effective_dt)
        self._hitstop.update()
        self._shake.update(effective_dt)
        self._slowmo.update()
        self._scoring.update(effective_dt)
        self._check_player_death()
        # Reset one-shot inputs
        self._player.input_fire = False
        self._player.input_dash = False
        self._player.input_bomb = False

    # ------------------------------------------------------------------
    # Score popups, powerups, flash timers
    # ------------------------------------------------------------------
    def _update_score_popups(self, dt: float) -> None:
        alive: list[ScorePopup] = []
        for p in self._score_popups:
            p.y += p.vy * dt
            p.life -= dt
            if p.life > 0.0:
                alive.append(p)
        self._score_popups = alive

    def _update_powerups(self, dt: float) -> None:
        """Power-ups drift down slowly; player touches to collect.

        BLOQUE 27: magnet effect — when player is within 50px, the power-up
        drifts toward the player instead of falling.
        """
        alive: list[PowerUp] = []
        phb = self._player.hitbox
        for p in self._powerups:
            p.y += p.vy * dt
            p.life -= dt
            if p.life <= 0.0 or p.y > INTERNAL_H + 10:
                continue
            # BLOQUE 27: magnet drift toward player
            if not self._player.is_dead:
                dx = self._player.x - p.x
                dy = self._player.y - p.y
                dist = math.hypot(dx, dy)
                if 0.01 < dist < 50.0:
                    pull = 80.0  # px/s toward player
                    p.x += (dx / dist) * pull * dt
                    p.y += (dy / dist) * pull * dt
                # Player pickup
                pr = pygame.Rect(int(p.x) - 4, int(p.y) - 4, 8, 8)
                if pr.colliderect(phb):
                    self._apply_powerup(p.kind)
                    self._play_sfx("powerup", volume=0.7)
                    self._emit_burst(p.x, p.y, count=8, kind="glow")
                    continue  # consumed
            alive.append(p)
        self._powerups = alive

    def _update_enemy_flash(self, dt: float) -> None:
        """Decay the per-enemy white-flash timer (hit feedback)."""
        if not self._enemy_flash:
            pass
        else:
            decayed: dict[int, float] = {}
            for eid, t in self._enemy_flash.items():
                t -= dt
                if t > 0.0:
                    decayed[eid] = t
            self._enemy_flash = decayed
        # BLOQUE 51: also decay the boss flash timer
        if self._boss_flash:
            decayed_b: dict[int, float] = {}
            for bid, t in self._boss_flash.items():
                t -= dt
                if t > 0.0:
                    decayed_b[bid] = t
            self._boss_flash = decayed_b

    def _emit_player_motion_particles(self, dt: float) -> None:
        """BLOQUE 26: continuous engine smoke + dash stars + low-HP smoke.

        Emits small smoke particles behind the engine at all times, more
        particles when dashing, and damage smoke when HP is critical.
        """
        from src.systems.particle_engine import P_DUST, P_SMOKE, P_SPARK
        px, py = self._player.x, self._player.y
        # Engine back: (px, py + 8) — same as flame origin
        ex, ey = px, py + 8
        # Throttle by frame: smoke every 4 frames when idle
        is_dash = self._player.state == PlayerState.DASH
        smoke_count = 1
        if is_dash:
            smoke_count = 3
        # Spawn rate throttle
        if int(self._t * 30) % (2 if is_dash else 5) != 0:
            return
        # Smoke spread
        spread = (random.random() - 0.5) * 3.0
        for _ in range(smoke_count):
            self._particles.emit(P_SMOKE, ex + spread, ey,
                                 vx=spread * 0.3, vy=15.0,
                                 life=0.4, radius=1.5)
        # Dash stars (bright sparks trailing)
        if is_dash:
            for _ in range(2):
                sx = ex + (random.random() - 0.5) * 6
                sy = ey + random.uniform(0, 6)
                self._particles.emit(P_SPARK, sx, sy,
                                      vx=-self._player.dash_dir_x * 30.0,
                                      vy=-self._player.dash_dir_y * 30.0,
                                      life=0.2, radius=1.0)
        # Low-HP damage smoke (separate, red-ish)
        if self._player.hp <= 1 and self._player.hp_max > 0 and int(self._t * 20) % 4 == 0:
            dsx = px + (random.random() - 0.5) * 10
            dsy = py - 4 + (random.random() - 0.5) * 4
            self._particles.emit(P_DUST, dsx, dsy,
                                  vx=(random.random() - 0.5) * 10.0,
                                  vy=-15.0, life=0.5, radius=1.5)

    def _add_shockwave(self, x: float, y: float, max_radius: float = 60.0) -> None:
        """Add an expanding ring shockwave (bomb/charged-shot visual)."""
        self._shockwaves.append(Shockwave(
            x=x, y=y, radius=2.0, max_radius=max_radius, life=0.5, max_life=0.5,
        ))

    def _update_shockwaves(self, dt: float) -> None:
        """Expand shockwaves over their lifetime."""
        if not self._shockwaves:
            return
        alive: list[Shockwave] = []
        for s in self._shockwaves:
            new_life = s.life - dt
            if new_life <= 0.0:
                continue
            new_radius = s.radius + dt * (s.max_radius / 0.5)
            alive.append(Shockwave(
                x=s.x, y=s.y, radius=new_radius,
                max_radius=s.max_radius, life=new_life, max_life=s.max_life,
            ))
        self._shockwaves = alive
        # BLOQUE 39: clean up inactive missiles
        self._missiles = [m for m in self._missiles if m.active]

    def _check_player_death_explosion(self) -> None:
        """One-shot multi-stage explosion when the player first dies.

        BLOQUE 23: 3-stage explosion — initial fire burst (stage 1, immediate),
        then expanding ring (stage 2, +0.15s), then smoke + debris (stage 3, +0.40s).
        """
        if self._player.is_dead and not self._death_exploded:
            self._death_exploded = True
            self._emit_burst(self._player.x, self._player.y, count=24, kind="explosion")
            self._emit_burst(self._player.x, self._player.y, count=16, kind="debris")
            self._emit_burst(self._player.x, self._player.y, count=12, kind="smoke")
            # BLOQUE 23: ring + screen flash
            self._add_shockwave(self._player.x, self._player.y, 60.0)
            self._hitstop.trigger(8)
            self._shake.add_trauma(0.5)
            self._play_sfx("explode_boss", volume=0.5)
            self._play_sfx("game_over", volume=0.7)

    def _update_boss_death_stages(self, dt: float) -> None:
        """BLOQUE 22: drive the 3-stage boss death explosion.

        Stage 1 (0s):    big initial burst + shockwave
        Stage 2 (0.15s): secondary burst + smaller ring
        Stage 3 (0.40s): tertiary burst + act-clear SFX
        """
        if self._boss_death_stage == 0:
            return
        self._boss_death_timer += dt
        bx, by = self._boss_death_pos
        if self._boss_death_stage == 1 and self._boss_death_timer >= 0.15:
            self._boss_death_stage = 2
            self._emit_burst(bx, by, count=32, kind="explosion")
            self._emit_burst(bx, by, count=16, kind="fire")
            self._add_shockwave(bx, by, 70.0)
            self._shake.add_trauma(0.4)
        elif self._boss_death_stage == 2 and self._boss_death_timer >= 0.40:
            self._boss_death_stage = 3
            self._emit_burst(bx, by, count=24, kind="smoke")
            self._emit_burst(bx, by, count=12, kind="debris")
            self._add_shockwave(bx, by, 50.0)
            self._play_sfx("act_clear", volume=0.8)

    def _maybe_drop_powerup(self, e: Enemy) -> None:
        """Roll for a power-up drop on enemy kill (per ENEMY_CONFIGS).

        BLOQUE 53c: gold rings have a separate fixed drop chance
        (GOLD_RING_DROP_CHANCE). They roll BEFORE the regular drop
        table so the player gets a steady supply.
        """
        from src.entities.enemies.enemy import ENEMY_CONFIGS
        from src.core.settings import GOLD_RING_DROP_CHANCE
        cfg = ENEMY_CONFIGS.get(e.kind)
        if cfg is None:
            return
        # BLOQUE 53c: gold ring drop (independent of the regular drop table)
        if random.random() < GOLD_RING_DROP_CHANCE:
            self._spawn_powerup(POWERUP_GOLD_RING, e.x, e.y)
        # Regular drop roll
        roll = random.random()
        # Power-up priority: bomb > 1up > power > score
        if roll < cfg.drop_bomb_pct and self._player.bombs_max > 0:
            self._spawn_powerup(POWERUP_BOMB, e.x, e.y)
        elif roll < cfg.drop_bomb_pct + cfg.drop_1up_pct and cfg.drop_1up_pct > 0:
            self._spawn_powerup(POWERUP_1UP, e.x, e.y)
        elif roll < cfg.drop_bomb_pct + cfg.drop_1up_pct + cfg.drop_powerup_pct:
            # Power-up means a small score pickup
            self._spawn_powerup(POWERUP_SCORE, e.x, e.y)

    def _spawn_powerup(self, kind: str, x: float, y: float) -> None:
        color_map = {
            POWERUP_BOMB: (255, 180, 80),
            POWERUP_GOLD_RING: (255, 220, 100),  # BLOQUE 53c
            POWERUP_POWER: (180, 220, 255),
            POWERUP_SCORE: (255, 240, 100),
            POWERUP_1UP: (120, 255, 180),
        }
        self._powerups.append(PowerUp(
            x=x, y=y, vy=40.0, kind=kind, life=8.0, max_life=8.0,
            color=color_map.get(kind, (255, 255, 255)),
        ))

    def _apply_powerup(self, kind: str) -> None:
        # BLOQUE 24: green pickup flash on every pickup
        self._pickup_flash = 0.6
        if kind == POWERUP_BOMB:
            self._player.bombs = min(self._player.bombs + 1, self._player.bombs_max)
            self._score_popups.append(ScorePopup(
                x=self._player.x, y=self._player.y - 16, vy=-40.0,
                text="BOMB +1", color=(255, 180, 80), life=1.2, max_life=1.2,
            ))
        elif kind == POWERUP_SCORE:
            self._scoring.on_kill(500)
            self._score_popups.append(ScorePopup(
                x=self._player.x, y=self._player.y - 16, vy=-40.0,
                text="+500", color=(255, 240, 100), life=1.2, max_life=1.2,
            ))
        elif kind == POWERUP_1UP:
            if self._player.lives < 9:
                self._player.lives += 1
            self._score_popups.append(ScorePopup(
                x=self._player.x, y=self._player.y - 16, vy=-40.0,
                text="1UP", color=(120, 255, 180), life=1.5, max_life=1.5,
            ))
        elif kind == POWERUP_POWER:
            # "Power" = score bonus in this simplified game
            self._scoring.on_kill(1000)
        elif kind == POWERUP_GOLD_RING:
            # BLOQUE 53c: Star Fox gold ring — heal + stack toward
            # one-time HP double. Visual feedback handled in the draw
            # and HUD layers.
            doubled = self._player.add_gold_ring()
            if doubled:
                # Big visual + score popup for the HP double event
                self._emit_burst(self._player.x, self._player.y,
                                  count=24, kind="explosion")
                self._emit_burst(self._player.x, self._player.y,
                                  count=16, kind="spark",
                                  color=(255, 220, 100))
                self._add_shockwave(self._player.x, self._player.y, 60.0)
                self._score_popups.append(ScorePopup(
                    x=self._player.x, y=self._player.y - 16, vy=-50.0,
                    text="HP x2 !", color=(255, 240, 120),
                    life=2.0, max_life=2.0,
                ))
                self._play_sfx("multiplier_up", volume=0.9)
                self._hitstop.trigger(4)
                self._shake.add_trauma(0.4)
            else:
                self._score_popups.append(ScorePopup(
                    x=self._player.x, y=self._player.y - 16, vy=-30.0,
                    text=f"+HP", color=(255, 220, 80),
                    life=0.8, max_life=0.8,
                ))
            self._score_popups.append(ScorePopup(
                x=self._player.x, y=self._player.y - 16, vy=-40.0,
                text="+1000", color=(180, 220, 255), life=1.2, max_life=1.2,
            ))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        # Background
        self._bg.draw(target)
        # BLOQUE 25: ambient drift particles in background
        self._draw_ambient_dust(target)
        # Shake offset
        shx_f, shy_f = self._shake.get_offset()
        shx, shy = int(shx_f), int(shy_f)
        # Player damage flash: red overlay right after taking a hit
        if self._player.invuln_frames > 60 - 8 and self._player.invuln_frames > 0 \
                and not self._player.is_dead:
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((255, 60, 40, 100))
            target.blit(flash, (0, 0))
        # Power-ups — BLOQUE 23: pulsing halo so they stand out
        # BLOQUE 53c: gold rings get a special swirling render
        for p in self._powerups:
            alpha = max(0, min(255, int(255 * (p.life / 2.0))))
            cx, cy = int(p.x) + shx, int(p.y) + shy
            if p.kind == POWERUP_GOLD_RING:
                # Special gold ring render — outer ring + inner core,
                # slowly spinning for that "collectible" feel
                pulse = 1.0 + 0.4 * math.sin(self._t * 4.0)
                outer_r = int(8 * pulse)
                # Outer glow
                glow = pygame.Surface((outer_r * 2 + 6, outer_r * 2 + 6), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 220, 100, max(0, alpha // 3)),
                                   (outer_r + 3, outer_r + 3), outer_r + 2)
                target.blit(glow, (cx - outer_r - 3, cy - outer_r - 3))
                # Ring body (just the outline)
                pygame.draw.circle(target, (255, 220, 100, alpha),
                                   (cx, cy), outer_r, 2)
                # Inner core (golden)
                pygame.draw.circle(target, (255, 240, 180, alpha),
                                   (cx, cy), outer_r // 2)
                # Sparkle (4 tiny dots rotating around the ring)
                for i in range(4):
                    a = self._t * 3.0 + i * (math.pi / 2)
                    spx = cx + int(math.cos(a) * (outer_r + 3))
                    spy = cy + int(math.sin(a) * (outer_r + 3))
                    pygame.draw.circle(target, (255, 255, 200, alpha),
                                       (spx, spy), 1)
                continue
            # Pulsing halo (radius oscillates with time)
            pulse = 1.0 + 0.5 * math.sin(self._t * 6.0)
            halo_r = int(7 * pulse)
            halo = pygame.Surface((halo_r * 2 + 4, halo_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(halo, (p.color[0], p.color[1], p.color[2], max(0, alpha // 2)),
                               (halo_r + 2, halo_r + 2), halo_r, 1)
            target.blit(halo, (cx - halo_r - 2, cy - halo_r - 2))
            # Solid square (the pickup body)
            rect = pygame.Rect(int(p.x) - 4 + shx, int(p.y) - 4 + shy, 8, 8)
            pu_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.rect(pu_surf, (p.color[0], p.color[1], p.color[2], alpha),
                             pu_surf.get_rect(), border_radius=2)
            target.blit(pu_surf, rect)
            # Inner white dot
            pygame.draw.rect(target, (255, 255, 255, alpha), (rect.x + 2, rect.y + 2, 4, 4))
        # Enemies
        for e in self._enemies.pool:
            if e.active:
                self._draw_enemy(target, e, shx, shy)
        # Boss
        if self._is_boss and self._boss is not None and self._boss.active:
            self._draw_boss(target, shx, shy)
        # BLOQUE 52: GOLIATH spear projectiles in flight
        for sp in self._boss_spears:
            if sp.active:
                self._draw_boss_spear(target, sp, shx, shy)
        # BLOQUE 53a: GOLIATH charged laser (drawn AFTER the boss so
        # the beam sits on top of everything)
        if self._boss_shield_laser_t > 0.0:
            self._draw_shield_laser(target, shx, shy)
        # Shockwaves (under bullets so they sit behind)
        for s in self._shockwaves:
            r = s.radius
            life_ratio = s.life / s.max_life if s.max_life > 0 else 0
            alpha = max(0, min(255, int(200 * life_ratio)))
            sx = int(s.x) + shx
            sy = int(s.y) + shy
            ring_surf = pygame.Surface((int(r * 2) + 4, int(r * 2) + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 255, 255, alpha),
                               (int(r) + 2, int(r) + 2), int(r), 2)
            target.blit(ring_surf, (sx - int(r) - 2, sy - int(r) - 2))
        # Bullets (with glow halo)
        self._draw_bullets_with_glow(target, shx, shy)
        # BLOQUE 39: homing missiles (drawn after bullets, before player)
        self._draw_missiles(target, shx, shy)
        # Player (only if not in DEAD state and not i-frames invisible)
        if not self._player.is_dead:
            self._draw_player(target, shx, shy)
        # BLOQUE 37: continuous L3 laser (drawn on top of player so it appears
        # to emerge from the muzzle).
        self._draw_continuous_laser(target, shx, shy)
        # BLOQUE 47: aim reticle (drawn last so it sits on top of everything)
        if not self._player.is_dead:
            self._draw_reticle(target, shx, shy)
        # BLOQUE 26: bomb flash overlay on the player
        if self._bomb_flash > 0.0:
            flash_alpha = int(220 * self._bomb_flash)
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            target.blit(flash, (0, 0))
        # Particles
        self._particles.draw(target, (shx, shy))
        # Score popups
        self._draw_score_popups(target, shx, shy)
        # Wave/act indicator (top-center, small)
        self._draw_wave_indicator(target)
        # Play-area frame (always on top so the border is visible)
        self._draw_play_area_frame(target)
        # HUD (BLOQUE 25: pass t for animations)
        self._hud.draw(target, self._player, self._weapon, self._scoring, t=self._t)
        # Screen flash (bomb) — drawn last, fades over time
        if self._screen_flash > 0.0:
            flash_alpha = int(200 * self._screen_flash)
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, flash_alpha))
            target.blit(flash, (0, 0))
        # BLOQUE 22: charge release flash (yellow-white overlay, fast decay)
        if self._charge_release_flash > 0.0:
            flash_alpha = int(180 * self._charge_release_flash)
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((255, 240, 180, flash_alpha))
            target.blit(flash, (0, 0))
        # BLOQUE 24: pickup flash (green overlay)
        if self._pickup_flash > 0.0:
            flash_alpha = int(120 * self._pickup_flash)
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((100, 255, 140, flash_alpha))
            target.blit(flash, (0, 0))
        # BLOQUE 24: level-up flash (cyan overlay, brief)
        if self._level_up_flash > 0.0:
            flash_alpha = int(160 * self._level_up_flash)
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((140, 220, 255, flash_alpha))
            target.blit(flash, (0, 0))
        # BLOQUE 24: speed lines when player moves fast (dashes / charge moves)
        if abs(self._player.vx) > 80.0 and self._player.state != PlayerState.DEAD:
            self._draw_speed_lines(target)

    def _draw_wave_indicator(self, target: pygame.Surface) -> None:
        """Show ACT/WAVE label in the top-center between HUD sections."""
        if self._is_boss:
            label = f"ACT {self._act} - BOSS"
        else:
            wave_in_act = (self._wave_idx % 6) + 1
            label = f"ACT {self._act} - WAVE {wave_in_act}/6"
        font = pygame.font.Font(None, 12)
        text = font.render(label, True, (200, 200, 220))
        # Place at top-center, below the HUD
        x = (target.get_width() - text.get_width()) // 2
        y = 22  # just below HP/bombs row
        # Background pill for legibility
        pill_w = text.get_width() + 8
        pill = pygame.Surface((pill_w, text.get_height() + 4), pygame.SRCALPHA)
        pygame.draw.rect(pill, (0, 0, 0, 160), pill.get_rect(), border_radius=2)
        target.blit(pill, (x - 4, y - 2))
        target.blit(text, (x, y))

    def _draw_play_area_frame(self, target: pygame.Surface) -> None:
        """Visible border around the 240x360 play area.

        Border position matches the player's clamp exactly: the player
        can move from (9, 9) to (231, 351), so the border sits at 0,0-240,360
        with a bright inner edge that defines the play area clearly.
        """
        w, h = target.get_size()
        # Outer dark border (4px — more prominent)
        pygame.draw.rect(target, _BORDER_COLOR, (0, 0, w, h), 4)
        # Inner light edge (2px — bright)
        pygame.draw.rect(target, _BORDER_INNER, (2, 2, w - 4, h - 4), 2)
        # Corner accents (6x6, very bright)
        for cx, cy in ((0, 0), (w - 6, 0), (0, h - 6), (w - 6, h - 6)):
            pygame.draw.rect(target, (220, 220, 255), (cx, cy, 6, 6))
            pygame.draw.rect(target, (140, 160, 220), (cx + 1, cy + 1, 4, 4))
        # BLOQUE 23: pulsing red border during boss entry (first 1.5s)
        if self._is_boss and self._boss_entry_t < 1.5:
            pulse_alpha = int(120 * (0.5 + 0.5 * math.sin(self._boss_entry_t * 16.0)))
            warn = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            # 4 red edge strips, 3px wide, pulsing
            pygame.draw.rect(warn, (255, 60, 60, pulse_alpha), (0, 0, w, 3))  # top
            pygame.draw.rect(warn, (255, 60, 60, pulse_alpha), (0, h - 3, w, 3))  # bottom
            pygame.draw.rect(warn, (255, 60, 60, pulse_alpha), (0, 0, 3, h))  # left
            pygame.draw.rect(warn, (255, 60, 60, pulse_alpha), (w - 3, 0, 3, h))  # right
            target.blit(warn, (0, 0))
        # Wall-hit indicator: thicker highlight when player touches
        if not self._player.is_dead:
            px, py = self._player.x, self._player.y
            if px < 12:  # left wall
                pygame.draw.rect(target, (255, 255, 255), (0, 0, 5, h), 2)
            if px > 228:  # right wall
                pygame.draw.rect(target, (255, 255, 255), (w - 5, 0, 5, h), 2)
            if py < 12:  # top wall
                pygame.draw.rect(target, (255, 255, 255), (0, 0, w, 5), 2)
            if py > 348:  # bottom wall
                pygame.draw.rect(target, (255, 255, 255), (0, h - 5, w, 5), 2)

    def _draw_bullets_with_glow(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """Draw bullets with a soft glow halo + trail behind each one.

        BLOQUE 22: bigger / brighter glows and longer trails so bullets read clearly
        against any background.
        """
        from src.systems.projectile import (
            BULLET_BOSS, BULLET_ENEMY, BULLET_PLAYER, BULLET_PLAYER_BEAM,
            BULLET_PLAYER_CHARGED,
        )
        # Outer halo (large, soft, very transparent)
        outer = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        # Inner glow (smaller, brighter)
        glow = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        # Trail pass: draw fading line segments behind each bullet
        trail = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        for p in self._bullets.pool:
            if not p.active:
                continue
            cx, cy = int(p.x) + ox, int(p.y) + oy
            # Glow color + radius by bullet kind
            if p.kind == BULLET_PLAYER:
                outer_color = (255, 200, 80, 30)
                glow_color = (255, 230, 120, 100)
                radius_outer = 9
                radius_glow = 5
                trail_color = (255, 220, 100, 200)
                trail_len = 0.06
                trail_w = 2
            elif p.kind == BULLET_PLAYER_CHARGED:
                outer_color = (255, 220, 150, 60)
                glow_color = (255, 250, 220, 160)
                radius_outer = 13
                radius_glow = 8
                trail_color = (255, 240, 200, 240)
                trail_len = 0.10
                trail_w = 3
            elif p.kind == BULLET_ENEMY:
                outer_color = (255, 60, 60, 30)
                glow_color = (255, 130, 130, 100)
                radius_outer = 9
                radius_glow = 5
                trail_color = (255, 100, 100, 200)
                trail_len = 0.05
                trail_w = 2
            elif p.kind == BULLET_BOSS:
                outer_color = (180, 80, 255, 35)
                glow_color = (220, 140, 255, 110)
                radius_outer = 11
                radius_glow = 7
                trail_color = (220, 120, 255, 220)
                trail_len = 0.07
                trail_w = 2
            else:
                outer_color = (255, 255, 255, 30)
                glow_color = (255, 255, 255, 100)
                radius_outer = 9
                radius_glow = 5
                trail_color = (255, 255, 255, 200)
                trail_len = 0.05
                trail_w = 2
            pygame.draw.circle(outer, outer_color, (cx, cy), radius_outer)
            pygame.draw.circle(glow, glow_color, (cx, cy), radius_glow)
            # Trail: a line from current position back along velocity
            tx = int(p.x - p.vx * trail_len) + ox
            ty = int(p.y - p.vy * trail_len) + oy
            pygame.draw.line(trail, trail_color, (cx, cy), (tx, ty), trail_w)
        target.blit(trail, (0, 0))
        target.blit(outer, (0, 0))
        target.blit(glow, (0, 0))
        # Solid bullets on top
        self._bullets.draw(target)
        # Tiny bright center dot for visibility
        center = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        for p in self._bullets.pool:
            if not p.active:
                continue
            cx, cy = int(p.x) + ox, int(p.y) + oy
            pygame.draw.circle(center, (255, 255, 255, 220), (cx, cy), 1)
        target.blit(center, (0, 0))

    def _draw_score_popups(self, target: pygame.Surface, ox: int, oy: int) -> None:
        font = pygame.font.Font(None, 14)
        for p in self._score_popups:
            alpha = max(0, min(255, int(255 * (p.life / p.max_life))))
            text = font.render(p.text, True, p.color)
            text.set_alpha(alpha)
            target.blit(text, (int(p.x) - text.get_width() // 2 + ox,
                                int(p.y) - text.get_height() // 2 + oy))

    def _draw_player(self, target: pygame.Surface, ox: int, oy: int) -> None:
        # Engine flame behind the ship — length scales with |vx|
        self._draw_engine_flame(target, ox, oy)
        # BLOQUE 30: bigger sprite for more Star Fox-style detail
        # Arwing-inspired: long body, big swept wings, twin wing-tip lasers
        surf = pygame.Surface((32, 24), pygame.SRCALPHA)
        # Center the 32x24 sprite around (16, 12)
        # Flicker iframes (every-other frame invisible during dash)
        if self._player.dash_iframes_left > 0 and (self._t * 30) % 2 < 1:
            pass  # still draw so the trail is visible
        # Ship body color (changes with charge level)
        body_color = (220, 240, 255)
        wing_color = (180, 200, 230)
        if self._player.state == PlayerState.CHARGE:
            level = self._player.get_charge_level()
            if level >= 3:
                body_color = (255, 255, 255)
                wing_color = (220, 220, 255)
            elif level >= 2:
                body_color = (200, 230, 255)
                wing_color = (160, 200, 240)
            elif level >= 1:
                body_color = (180, 220, 255)
                wing_color = (140, 190, 230)
        # ---- Arwing-style body (longer, sleeker) ----
        # Main fuselage: pointed nose → wider body → tapered tail
        pygame.draw.polygon(surf, body_color, [
            (16, 0),    # nose tip
            (13, 8),    # upper-left of body
            (11, 18),   # tail-left
            (16, 20),   # tail center
            (21, 18),   # tail-right
            (19, 8),    # upper-right of body
        ])
        # Belly highlight (lighter shade at the bottom of the fuselage)
        pygame.draw.polygon(surf, (180, 200, 230), [
            (13, 14), (19, 14), (16, 18),
        ])
        # ---- Big swept wings (Arwing-style) ----
        # Left wing: long sweep from fuselage tip down to bottom-left
        pygame.draw.polygon(surf, wing_color, [
            (13, 8),    # root (upper body)
            (10, 11),   # inner edge
            (0, 17),    # wingtip (far left)
            (0, 19),    # wingtip bottom
            (4, 20),    # back of wingtip
            (11, 14),   # trailing edge
        ])
        # Right wing (mirror)
        pygame.draw.polygon(surf, wing_color, [
            (19, 8),    # root
            (22, 11),   # inner edge
            (32, 17),   # wingtip (far right)
            (32, 19),   # wingtip bottom
            (28, 20),   # back of wingtip
            (21, 14),   # trailing edge
        ])
        # Wing leading edge highlight
        pygame.draw.line(surf, (240, 245, 255), (13, 8), (0, 17), 1)
        pygame.draw.line(surf, (240, 245, 255), (19, 8), (32, 17), 1)
        # ---- Cockpit (canopy) ----
        cockpit_color = (255, 100, 100)
        if self._player.state == PlayerState.CHARGE:
            level = self._player.get_charge_level()
            if level >= 3:
                cockpit_color = (255, 200, 255)
            elif level >= 2:
                cockpit_color = (255, 150, 200)
            elif level >= 1:
                cockpit_color = (255, 120, 150)
        # Hex canopy (Arwing-style bubble canopy)
        pygame.draw.polygon(surf, cockpit_color, [
            (14, 5), (18, 5), (19, 8), (16, 11), (13, 8),
        ])
        # Canopy highlight (white shine)
        pygame.draw.circle(surf, (255, 255, 255), (15, 6), 1)
        # ---- Wing-tip laser cannons (Star Fox detail) ----
        # Left laser barrel (red, port side)
        pygame.draw.rect(surf, (200, 80, 80), (1, 16, 3, 2))
        pygame.draw.rect(surf, (255, 120, 100), (0, 17, 2, 1))  # hot tip
        # Right laser barrel (green, starboard side)
        pygame.draw.rect(surf, (80, 200, 100), (28, 16, 3, 2))
        pygame.draw.rect(surf, (120, 255, 150), (30, 17, 2, 1))  # hot tip
        # ---- Wing tip lights (pulsing) ----
        red_pulse = 0.5 + 0.5 * math.sin(self._t * 6.0)
        green_pulse = 0.5 + 0.5 * math.sin(self._t * 6.0 + math.pi)
        red_color = (int(255 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)))
        green_color = (int(60 * (0.4 + 0.6 * green_pulse)),
                       int(255 * (0.4 + 0.6 * green_pulse)),
                       int(100 * (0.4 + 0.6 * green_pulse)))
        pygame.draw.circle(surf, red_color, (1, 13), 1)
        pygame.draw.circle(surf, green_color, (31, 13), 1)
        # ---- Twin engine exhausts (between body and wings) ----
        # Left engine intake
        pygame.draw.rect(surf, (40, 50, 70), (12, 16, 3, 2))
        # Right engine intake
        pygame.draw.rect(surf, (40, 50, 70), (17, 16, 3, 2))
        # Engine glow at the intakes (orange/red)
        pygame.draw.rect(surf, (255, 140, 60), (12, 18, 3, 1))
        pygame.draw.rect(surf, (255, 140, 60), (17, 18, 3, 1))
        # ---- Center stripe (Arwing signature) ----
        # Red accent stripe down the center of the body
        pygame.draw.line(surf, (255, 80, 80), (16, 6), (16, 16), 1)
        # ---- BLOQUE 35: sprite scale 0.75 (player 32x24 -> 24x18) ----
        # Hitbox stays at 18x12 (difficulty unchanged). Only the visual is
        # reduced. This makes ships and projectiles feel smaller in the
        # bigger playfield (BLOQUE 34: 320x480) without changing game balance.
        from src.core.settings import PLAYER_SPRITE_SCALE
        if PLAYER_SPRITE_SCALE != 1.0:
            scaled_w = max(1, int(surf.get_width() * PLAYER_SPRITE_SCALE))
            scaled_h = max(1, int(surf.get_height() * PLAYER_SPRITE_SCALE))
            surf = pygame.transform.scale(surf, (scaled_w, scaled_h))
        # ---- BLOQUE 29: combined tilt + nose angle ----
        rotated = pygame.transform.rotate(
            surf, -(self._player.current_tilt + self._player.current_nose_angle)
        )
        # Recenter after rotation
        rect = rotated.get_rect(center=(int(self._player.x + ox), int(self._player.y + oy)))
        target.blit(rotated, rect)
        # BLOQUE 25: Shield effect during respawn invulnerability
        if self._player.respawn_invuln > 0.0:
            self._draw_shield(target, ox, oy)
        # BLOQUE 22: muzzle flash overlay — bright oval at the player nose
        if self._muzzle_flash > 0.0:
            self._draw_muzzle_flash(target, ox, oy)
        # BLOQUE 49: charge aura + energy absorption particles
        if self._player.state == PlayerState.CHARGE:
            self._draw_charge_aura(target, ox, oy)
            # Estimate dt from frame time so absorption rate stays consistent
            # (called from draw so we don't have dt here)
            est_dt = 1.0 / 60.0
            self._emit_energy_absorption(est_dt)
        # Afterimage trail — bigger ghost matching the new 32x24 sprite
        for tx, ty, age in self._player.afterimage:
            alpha = max(0, int(255 * (1 - age / self._player.AFTERIMAGE_LIFE)))
            ghost = pygame.Surface((32, 24), pygame.SRCALPHA)
            # Simple silhouette of the new ship
            pygame.draw.polygon(ghost, (220, 240, 255, alpha), [
                (16, 0), (13, 8), (11, 18), (16, 20), (21, 18), (19, 8),
            ])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [
                (13, 8), (10, 11), (0, 17), (4, 20), (11, 14),
            ])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [
                (19, 8), (22, 11), (32, 17), (28, 20), (21, 14),
            ])
            target.blit(ghost, (int(tx - 16 + ox), int(ty - 12 + oy)))
        # Charge indicator: a ring around the player that fills as charge builds
        charge_level = self._player.get_charge_level()
        if self._player.state == PlayerState.CHARGE and charge_level > 0:
            self._draw_charge_indicator(target, charge_level, ox, oy)
        elif self._player.input_fire and self._player.charge_time > 0.1:
            # Building up — show dim ring
            progress = min(1.0, self._player.charge_time / 0.5)
            self._draw_charge_ring(target, progress, (180, 180, 200), ox, oy)

    def _draw_reticle(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 47: aim reticle — visual feedback for mouse position.

        Star Fox-style: small crosshair at the mouse cursor with a center
        dot and 4 tick marks. Color shifts to cyan when laser is active.
        """
        mx, my = int(self._mouse_x + ox), int(self._mouse_y + oy)
        # Clamp to play area (don't draw outside the borders)
        from src.core.settings import INTERNAL_W, INTERNAL_H
        if mx < 4 or mx > INTERNAL_W - 4 or my < 4 or my > INTERNAL_H - 4:
            return
        # Color: cyan when laser is active, otherwise warm yellow
        if self._player.state == PlayerState.CHARGE and self._player.get_charge_level() >= 3:
            color = (140, 220, 255)  # plasma cyan
            core_color = (220, 245, 255)
        else:
            color = (255, 240, 140)  # warm yellow
            core_color = (255, 255, 220)
        # Outer ring (subtle, for depth)
        pygame.draw.circle(target, (color[0] // 2, color[1] // 2, color[2] // 2), (mx, my), 8, 1)
        # 4 tick marks (cross pattern, 4px each direction, 2px gap)
        tick_len = 4
        gap = 2
        pygame.draw.line(target, color, (mx - gap - tick_len, my), (mx - gap, my), 1)
        pygame.draw.line(target, color, (mx + gap, my), (mx + gap + tick_len, my), 1)
        pygame.draw.line(target, color, (mx, my - gap - tick_len), (mx, my - gap), 1)
        pygame.draw.line(target, color, (mx, my + gap), (mx, my + gap + tick_len), 1)
        # Center dot
        pygame.draw.circle(target, core_color, (mx, my), 1)
        # Subtle pulsing outer ring
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)
        ring_r = int(6 + pulse * 2)
        ring_alpha = int(40 + pulse * 30)
        ring_surf = pygame.Surface((ring_r * 2 + 2, ring_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (color[0], color[1], color[2], ring_alpha),
                           (ring_r + 1, ring_r + 1), ring_r, 1)
        target.blit(ring_surf, (mx - ring_r - 1, my - ring_r - 1))

    def _draw_engine_flame(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """Draw an engine flame behind the player. Length scales with |vx|."""
        px, py = self._player.x + ox, self._player.y + oy
        speed = abs(self._player.vx)
        # Base length 4; max length 12 when at full speed
        length = 4 + min(8, speed / 130.0 * 8)
        # Flicker the flame width using a sin
        flicker = 1.0 + 0.4 * math.sin(self._t * 40.0)
        # Dash: longer flame
        if self._player.state == PlayerState.DASH:
            length *= 1.8
            flicker *= 1.5
        # Three flame segments (yellow, orange, red) for a layered look
        # Drawn behind the ship (y direction = +y, ship points -y)
        pygame.draw.polygon(target, (255, 240, 180), [
            (px - 1, py + 8),
            (px + 1, py + 8),
            (px, py + 8 + length * flicker * 1.1),
        ])
        pygame.draw.polygon(target, (255, 220, 80), [
            (px - 2, py + 8),
            (px + 2, py + 8),
            (px, py + 8 + length * flicker),
        ])
        pygame.draw.polygon(target, (255, 140, 60), [
            (px - 3, py + 8),
            (px + 3, py + 8),
            (px, py + 8 + length * flicker * 0.7),
        ])
        pygame.draw.polygon(target, (255, 80, 40), [
            (px - 1.5, py + 8),
            (px + 1.5, py + 8),
            (px, py + 8 + length * flicker * 0.4),
        ])
        # Thrust particles — small sparks trailing the flame
        # Spawn only when actually moving, throttled by frame counter
        if speed > 30.0 and int(self._t * 60) % 3 == 0:
            spread = (random.random() - 0.5) * 4.0
            spark_x = px + spread
            spark_y = py + 8 + length * flicker * 0.5
            # Tiny SPARK particle drifting further back
            from src.systems.particle_engine import P_SPARK
            self._particles.emit(P_SPARK, spark_x, spark_y,
                                  vx=spread * 5.0, vy=20.0,
                                  life=0.15, radius=1.0)

    def _draw_muzzle_flash(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 22: bright multi-layer flash at the player nose.

        Three concentric ovals: outer (warm yellow), middle (white), inner (pure white).
        Scales and fades with self._muzzle_flash.
        BLOQUE 38: tint is orange for RMB rapid fire, yellow for LMB.
        """
        # Position: nose of the ship — bigger sprite so adjust
        flash = self._muzzle_flash
        # Ship nose is at (player.x, player.y - 12) for the new bigger sprite
        cx = int(self._player.x + ox)
        cy = int(self._player.y - 12 + oy)
        # BLOQUE 38: source-dependent tint.
        if self._muzzle_flash_source == "rmb":
            outer_rgb = (255, 170, 80)    # warm orange
            mid_rgb = (255, 210, 150)
            inner_rgb = (255, 240, 220)
            ray_rgb = (255, 210, 140)
        else:
            outer_rgb = (255, 220, 100)   # warm yellow
            mid_rgb = (255, 240, 200)
            inner_rgb = (255, 255, 255)
            ray_rgb = (255, 255, 200)
        # Outer warm halo
        surf = pygame.Surface((28, 28), pygame.SRCALPHA)
        outer_alpha = int(min(255, 200 * flash))
        pygame.draw.circle(surf, (*outer_rgb, outer_alpha), (14, 14), 13)
        # Middle white core
        mid_alpha = int(min(255, 230 * flash))
        pygame.draw.circle(surf, (*mid_rgb, mid_alpha), (14, 14), 7)
        # Bright center
        inner_alpha = int(min(255, 255 * flash))
        pygame.draw.circle(surf, (*inner_rgb, inner_alpha), (12, 12), 3)
        # 4 directional rays
        for ang in (0, 90, 180, 270):
            r = math.radians(ang)
            rx1 = 14 + int(math.cos(r) * 7)
            ry1 = 14 + int(math.sin(r) * 7)
            rx2 = 14 + int(math.cos(r) * 14)
            ry2 = 14 + int(math.sin(r) * 14)
            pygame.draw.line(surf, (*ray_rgb, outer_alpha), (rx1, ry1), (rx2, ry2), 2)
        target.blit(surf, (cx - 14, cy - 14))

    def _draw_shield(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 25: glowing shield bubble around player during respawn invuln.

        Animated rotating arc + soft cyan ring.
        """
        cx = int(self._player.x + ox)
        cy = int(self._player.y + oy)
        # Outer soft ring
        ring = pygame.Surface((40, 40), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)
        outer_alpha = int(80 + 60 * pulse)
        pygame.draw.circle(ring, (100, 200, 255, outer_alpha), (20, 20), 18, 2)
        # Inner brighter ring
        pygame.draw.circle(ring, (200, 240, 255, 180), (20, 20), 14, 1)
        target.blit(ring, (cx - 20, cy - 20))
        # Rotating arc segments (3 arcs at different angles)
        arc_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        for i in range(3):
            base_angle = self._t * 4.0 + i * (2 * math.pi / 3)
            for j in range(8):
                a1 = base_angle + j * (math.pi / 24)
                a2 = base_angle + (j + 1) * (math.pi / 24)
                x1 = 20 + int(math.cos(a1) * 18)
                y1 = 20 + int(math.sin(a1) * 18)
                x2 = 20 + int(math.cos(a2) * 18)
                y2 = 20 + int(math.sin(a2) * 18)
                pygame.draw.line(arc_surf, (180, 230, 255, 200), (x1, y1), (x2, y2), 1)
        target.blit(arc_surf, (cx - 20, cy - 20))

    def _draw_ambient_dust(self, target: pygame.Surface) -> None:
        """BLOQUE 25: ambient drifting dust particles in the background.

        Small motes that drift slowly across the screen, wrapping at edges.
        Adds depth to the parallax without being distracting.
        """
        w, h = target.get_size()
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        n_motes = 18
        for i in range(n_motes):
            # Deterministic per-mote base position (so they don't all cluster)
            base_x = (i * 53 + 11) % w
            base_y = (i * 89 + 37) % h
            # Slow drift based on time
            drift_x = self._t * (8.0 + (i % 4) * 2.0) * 0.3
            drift_y = self._t * (5.0 + (i % 3) * 1.5) * 0.3
            x = (base_x + drift_x) % w
            y = (base_y + drift_y) % h
            # Color: faint blue-white motes
            intensity = 30 + (i % 3) * 20
            color = (intensity, intensity, intensity + 30, 100)
            if i % 4 == 0:
                # Bigger mote
                pygame.draw.circle(surf, color, (int(x), int(y)), 1)
            else:
                # Single pixel
                surf.set_at((int(x), int(y)), color)
        target.blit(surf, (0, 0))

    def _draw_speed_lines(self, target: pygame.Surface) -> None:
        """BLOQUE 24: motion streaks when player moves fast.

        Horizontal short lines drift backwards relative to player motion, giving
        a "fast movement" feel. Drawn above the player but below the HUD.
        """
        vx = self._player.vx
        if abs(vx) < 60.0:
            return
        surf = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        w, h = target.get_size()
        # 6-8 streaks at random y positions
        n = 8 if abs(vx) > 150.0 else 5
        # Each streak length scales with |vx|
        max_len = min(40, int(abs(vx) * 0.25))
        for i in range(n):
            # Pseudo-random y based on t + i (so it varies frame to frame)
            y = int(((i * 53 + self._speed_line_t * 80) % h))
            x_start = int(self._player.x + (vx * 0.1)) - max_len // 2
            x_end = x_start - int(vx * 0.05)  # stretch opposite of motion
            x_start = max(0, min(w - 1, x_start))
            x_end = max(0, min(w - 1, x_end))
            alpha = 80 if abs(vx) > 150 else 50
            pygame.draw.line(surf, (200, 220, 255, alpha), (x_start, y), (x_end, y), 1)
        target.blit(surf, (0, 0))

    def _draw_charge_indicator(self, target: pygame.Surface, level: int, ox: int, oy: int) -> None:
        """Bright pulsing ring around the player when fully charged."""
        color_map = {1: (180, 220, 255), 2: (220, 230, 255), 3: (255, 255, 255)}
        color = color_map.get(level, (180, 220, 255))
        # Pulsing alpha
        pulse = 128 + int(127 * math.sin(self._t * 12.0))
        ring_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (*color, pulse), (16, 16), 14, 2)
        target.blit(ring_surf, (int(self._player.x - 16 + ox),
                                 int(self._player.y - 16 + oy)))

    def _draw_charge_ring(self, target: pygame.Surface, progress: float,
                          color: tuple[int, int, int], ox: int, oy: int) -> None:
        """Dim partial ring while charge is building up."""
        ring_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Arc from -90deg clockwise
        rect = pygame.Rect(1, 1, 30, 30)
        start_angle = -math.pi / 2
        end_angle = start_angle + 2 * math.pi * progress
        # Draw arc as small line segments
        steps = 24
        for i in range(steps):
            t = i / steps
            a1 = start_angle + (end_angle - start_angle) * t
            a2 = start_angle + (end_angle - start_angle) * ((t + 1.0 / steps))
            x1 = 16 + math.cos(a1) * 14
            y1 = 16 + math.sin(a1) * 14
            x2 = 16 + math.cos(a2) * 14
            y2 = 16 + math.sin(a2) * 14
            pygame.draw.line(ring_surf, (*color, 200), (x1, y1), (x2, y2), 2)
        target.blit(ring_surf, (int(self._player.x - 16 + ox),
                                 int(self._player.y - 16 + oy)))

    def _draw_charge_aura(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 49: pulsating plasma aura around the player while charging.

        Visual feedback that the ship is gathering energy. Color shifts
        from cyan (L1) to bright white-cyan (L3 laser-ready). The aura
        pulses with charge time.
        """
        level = self._player.get_charge_level()
        if level == 0:
            return
        # Pulse rate increases with charge level
        pulse_rate = 4.0 + level * 2.0
        pulse = 0.5 + 0.5 * math.sin(self._t * pulse_rate)
        # Color by level
        if level >= 3:
            base_color = (140, 220, 255)
        elif level >= 2:
            base_color = (120, 200, 240)
        else:
            base_color = (100, 180, 220)
        # Outer aura ring
        aura_radius = int(18 + pulse * 6 + level * 2)
        aura_surf = pygame.Surface((aura_radius * 2 + 4, aura_radius * 2 + 4),
                                    pygame.SRCALPHA)
        # Multiple concentric rings for depth
        for i, alpha_mul in enumerate([0.7, 0.4, 0.2]):
            r = aura_radius - i * 3
            if r > 0:
                a = int(60 * alpha_mul * (0.6 + 0.4 * pulse))
                pygame.draw.circle(aura_surf, (*base_color, a),
                                   (aura_radius + 2, aura_radius + 2), r, 1)
        target.blit(aura_surf, (int(self._player.x - aura_radius - 2 + ox),
                                int(self._player.y - aura_radius - 2 + oy)))
        # Inner glow (brighter, smaller)
        glow_radius = int(10 + pulse * 3)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2),
                                   pygame.SRCALPHA)
        for r in range(glow_radius, 0, -2):
            t = 1.0 - r / glow_radius
            a = int(120 * t * (0.5 + 0.5 * pulse))
            pygame.draw.circle(glow_surf, (*base_color, a),
                               (glow_radius, glow_radius), r)
        target.blit(glow_surf, (int(self._player.x - glow_radius + ox),
                                int(self._player.y - glow_radius + oy)))

    def _emit_energy_absorption(self, dt: float) -> None:
        """BLOQUE 50a: diffuse energy absorption — particles spawn in a
        wider ring around the player (24-48px depending on charge level)
        with visible motion toward the ship, then FADE and SHRINK as they
        get absorbed. Reads as "the ship is pulling in energy", not a
        static aura.

        Each emission produces a mix of particle types:
          - outer ring: small fast sparks (P_SPARK, 0.30s life)
          - inner halo: larger wisps (P_GLOW, 0.45s life) for soft diffusion
        Particles get DARKER as they near the ship (alpha-fade via life),
        so the visual is "energy from outside, dissolving as it gets
        sucked in".
        """
        level = self._player.get_charge_level()
        if level == 0:
            return
        # Spawn count grows with charge. L3 laser pulls harder.
        is_laser_active = (self._laser_active and level >= 3)
        sparks_per_call = 3 + level * 2
        glows_per_call = 1 + level
        if is_laser_active:
            sparks_per_call = int(sparks_per_call * 1.5)
            glows_per_call = int(glows_per_call * 1.5)
        import random as _r
        px, py = self._player.x, self._player.y
        # Outer spawn ring (wider so the absorption has travel distance).
        # L1 = 24-32, L3 = 36-48 — clearly visible motion before absorption.
        outer_min = 22.0 + level * 6.0
        outer_max = outer_min + 10.0
        # Inner absorb ring (where the particle dies). Tight around the ship.
        absorb_ring = 4.0 + level
        # Color by level
        if level >= 3:
            color_spark = (180, 240, 255)
            color_glow = (140, 220, 255)
        elif level >= 2:
            color_spark = (150, 220, 250)
            color_glow = (110, 200, 240)
        else:
            color_spark = (110, 200, 240)
            color_glow = (90, 170, 220)
        # Outer sparks (sharp, fast)
        for _ in range(sparks_per_call):
            angle = _r.uniform(0.0, 2.0 * math.pi)
            # Spawn at a random radius in the outer ring band
            r = _r.uniform(outer_min, outer_max)
            sx = px + math.cos(angle) * r
            sy = py + math.sin(angle) * r
            # Aim toward the ship
            dx = px - sx
            dy = py - sy
            d = math.hypot(dx, dy) or 1.0
            # Speed varies — slower outer particles, faster near ship
            speed = 60.0 + (outer_max - r) * 2.0 + _r.uniform(-15.0, 15.0)
            vx = (dx / d) * speed
            vy = (dy / d) * speed
            # Life scales with travel distance (so the particle fades naturally
            # before reaching the ship). Average life ~ 0.3s.
            travel = (r - absorb_ring) / max(speed, 1.0)
            life = max(0.15, min(0.5, travel * _r.uniform(0.8, 1.2)))
            # Size starts small (will fade out before reaching ship)
            size = _r.uniform(1.5, 2.5)
            self._particles.emit(
                0,  # P_SPARK
                sx, sy, vx=vx, vy=vy,
                color=color_spark,
                life=life,
                radius=size,
            )
        # Inner halo (soft diffusion layer)
        for _ in range(glows_per_call):
            angle = _r.uniform(0.0, 2.0 * math.pi)
            # Glow spawns in a tighter band (closer to ship)
            r = _r.uniform(outer_min * 0.6, outer_min * 0.9)
            sx = px + math.cos(angle) * r
            sy = py + math.sin(angle) * r
            dx = px - sx
            dy = py - sy
            d = math.hypot(dx, dy) or 1.0
            # Slower speed — these are the "wisps" that linger
            speed = 30.0 + _r.uniform(-10.0, 10.0)
            vx = (dx / d) * speed
            vy = (dy / d) * speed
            self._particles.emit(
                9,  # P_GLOW (fuzzy halo, slow fade)
                sx, sy, vx=vx, vy=vy,
                color=color_glow,
                life=_r.uniform(0.35, 0.55),
                radius=_r.uniform(3.0, 5.0),
            )

    def _draw_enemy(self, target: pygame.Surface, e: Enemy, ox: int, oy: int) -> None:
        from src.entities.enemies.enemy import ENEMY_CONFIGS
        cfg = ENEMY_CONFIGS[e.kind]
        w, h = cfg.width, cfg.height
        cx = int(e.x + ox)
        cy = int(e.y + oy)
        # Telegraph (red flash) — skip for archetypes w/o telegraph
        if e.telegraph_timer > 0:
            color = (255, 100, 100)
        else:
            color = cfg.color
        # Hit feedback: white flash for ~0.08s after a hit
        flash_t = self._enemy_flash.get(id(e), 0.0)
        if flash_t > 0.0:
            color = (255, 255, 255)
        # Different shapes per kind (BLOQUE 30: more Star Fox-style detail)
        # BLOQUE 58.4: all enemy sprites redesigned in the Star Fox /
        # Star Wolf aesthetic. Silver military base + per-type color accent
        # + glowing cockpit. Gameplay (HP, speed, fire rate) is unchanged.
        if e.kind == EnemyKind.SCOUT:
            # BLOQUE 58.5: SCOUT nose-DOWN (flipped 180°). Sleek
            # Mono-Raptor dart with swept-back wings, cyan glowing canopy.
            # Engines at the TOP (back of ship), nose at the BOTTOM.
            silver = (170, 180, 195)
            silver_dark = (90, 100, 115)
            cyan = (80, 220, 240)
            # Body is a vertical dart, pointed at bottom
            body_top_y = cy - h // 2
            body_bot_y = cy + h // 2
            # Wings sweep back from shoulder (just below the top) going
            # UP-AND-OUT to the wing tips above the body. Forms a
            # small inverted V (^) silhouette.
            shoulder_y = body_top_y + 1
            wing_tip_y = shoulder_y - 1
            # Single-polygon silhouette: nose (bottom) -> right side
            # -> right shoulder -> right wing tip -> top of body -> left
            # wing tip -> left shoulder -> left side -> nose
            pygame.draw.polygon(target, silver, [
                (cx, body_bot_y),                 # nose (front, DOWN)
                (cx + 1, cy + 1),                 # right side
                (cx + 2, shoulder_y),             # right shoulder
                (cx + w // 2, wing_tip_y),         # right wing tip
                (cx, body_top_y - 1),             # top of body
                (cx - w // 2, wing_tip_y),         # left wing tip
                (cx - 2, shoulder_y),             # left shoulder
                (cx - 1, cy + 1),                 # left side
            ])
            # Wing leading-edge highlights (going up-and-out)
            wing_hi = (200, 210, 225)
            pygame.draw.line(target, wing_hi,
                             (cx + 2, shoulder_y), (cx + w // 2, wing_tip_y), 1)
            pygame.draw.line(target, wing_hi,
                             (cx - 2, shoulder_y), (cx - w // 2, wing_tip_y), 1)
            # Body panel detail (darker stripe)
            pygame.draw.line(target, silver_dark, (cx, body_top_y), (cx, body_bot_y - 1), 1)
            # Cyan glowing canopy (the "eye") in the body center
            pygame.draw.circle(target, cyan, (cx, cy), 2)
            pygame.draw.circle(target, (180, 240, 255), (cx, cy), 1)
            # Yellow exhaust at the TOP (back of ship)
            pygame.draw.rect(target, (255, 200, 80), (cx - 1, body_top_y - 1, 2, 1))
        elif e.kind == EnemyKind.CRUISER:
            # BLOQUE 58.5: CRUISER flipped 180° (delta wing nose-DOWN).
            # Silver base + green accent, twin side cannons, green eye.
            # Engines at the TOP, cannons at the BOTTOM, wings swept back.
            silver = (160, 170, 185)
            silver_dark = (85, 95, 110)
            green = (100, 220, 100)
            green_dark = (50, 140, 60)
            body_top_y = cy - h // 2
            body_bot_y = cy + h // 2
            # Delta wing body, pointed at bottom (nose DOWN)
            pygame.draw.polygon(target, silver, [
                (cx, body_bot_y),                # nose (front, DOWN)
                (cx + w // 3, body_top_y + 2),    # right leading edge
                (cx + w // 2, body_top_y + 3),    # right wing tip
                (cx + w // 2 - 1, body_top_y + 1),
                (cx + w // 2, body_top_y - 1),    # right engine mount
                (cx, body_top_y - 1),            # top of body
                (cx - w // 2, body_top_y - 1),    # left engine mount
                (cx - w // 2 + 1, body_top_y + 1),
                (cx - w // 2, body_top_y + 3),    # left wing tip
                (cx - w // 3, body_top_y + 2),    # left leading edge
            ])
            # Inner panel (darker, for depth)
            pygame.draw.polygon(target, silver_dark, [
                (cx, body_bot_y - 1),
                (cx + w // 4, body_top_y + 3),
                (cx + w // 4, body_top_y + 2),
                (cx, body_top_y + 1),
                (cx - w // 4, body_top_y + 2),
                (cx - w // 4, body_top_y + 3),
            ])
            # Wing leading-edge highlight (going from nose UP-AND-OUT to wing tip)
            wing_hi = (195, 205, 220)
            pygame.draw.line(target, wing_hi,
                             (cx, body_bot_y), (cx + w // 2, body_top_y - 1), 1)
            pygame.draw.line(target, wing_hi,
                             (cx, body_bot_y), (cx - w // 2, body_top_y - 1), 1)
            # Twin side cannons (green barrels pointing DOWN)
            pygame.draw.rect(target, green_dark, (cx - w // 3, cy - 1, 1, 3))
            pygame.draw.rect(target, green_dark, (cx + w // 3, cy - 1, 1, 3))
            # Green glowing eye in the body center
            pygame.draw.circle(target, green, (cx, cy + 1), 2)
            pygame.draw.circle(target, (200, 255, 200), (cx, cy + 1), 1)
            # Twin yellow engines at TOP (back of ship)
            pygame.draw.rect(target, (255, 200, 80), (cx - w // 3 - 1, body_top_y - 1, 2, 1))
            pygame.draw.rect(target, (255, 200, 80), (cx + w // 3 - 1, body_top_y - 1, 2, 1))
        elif e.kind == EnemyKind.HEAVY:
            # BLOQUE 58.5: HEAVY — Star Fox attack carrier flipped.
            # Engines at TOP (back of ship), weapons at BOTTOM (front).
            # Armored square with 4 corner turrets, red glowing core.
            silver = (150, 160, 175)
            silver_dark = (80, 90, 105)
            red = (220, 60, 70)
            red_dark = (130, 30, 35)
            # Main body (armored square)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.rect(target, silver, rect)
            # Inner darker panel for armor depth
            inner_rect = rect.inflate(-max(2, w // 4), -max(2, h // 4))
            pygame.draw.rect(target, silver_dark, inner_rect)
            # Border highlight
            pygame.draw.rect(target, (190, 200, 215), rect, 1)
            # 4 corner turrets (red)
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                tcx = cx + dx * (w // 2 - 2)
                tcy = cy + dy * (h // 2 - 2)
                pygame.draw.circle(target, silver_dark, (tcx, tcy), 2)
                pygame.draw.circle(target, red, (tcx, tcy), 1)
            # Central red glowing core (the "heart" of the carrier)
            pygame.draw.circle(target, red_dark, (cx, cy), 3)
            pygame.draw.circle(target, red, (cx, cy), 2)
            pygame.draw.circle(target, (255, 200, 200), (cx, cy), 1)
            # Central cannon barrel (red glowing, pointing DOWN toward player)
            pygame.draw.rect(target, red_dark, (cx - 1, cy + 1, 2, h // 2 - 2))
            pygame.draw.circle(target, red, (cx, cy + h // 2 - 1), 1)
            # Sensor lights at the BOTTOM (front of ship)
            pygame.draw.circle(target, (255, 80, 80), (cx - 3, cy + h // 2 - 2), 1)
            pygame.draw.circle(target, (80, 220, 100), (cx + 3, cy + h // 2 - 2), 1)
            # Twin yellow engines at the TOP (back of ship)
            pygame.draw.rect(target, (255, 200, 80), (cx - w // 4, cy - h // 2, 2, 1))
            pygame.draw.rect(target, (255, 200, 80), (cx + w // 4 - 2, cy - h // 2, 2, 1))
        elif e.kind == EnemyKind.KAMIKAZE:
            # BLOQUE 58.5: KAMIKAZE — aggressive diving triangle. Silver +
            # orange. Hot pulsing eye + exhaust at the TOP (back of ship),
            # nose pointing DOWN (the direction of motion).
            silver = (180, 130, 80)
            silver_dark = (110, 70, 30)
            orange = (255, 140, 50)
            orange_bright = (255, 220, 130)
            # Triangle pointing DOWN (nose at the bottom)
            pygame.draw.polygon(target, silver, [
                (cx - w // 2, cy - h // 2),     # top-left
                (cx + w // 2, cy - h // 2),     # top-right
                (cx, cy + h // 2),              # nose (DOWN)
            ])
            # Inner darker panel
            pygame.draw.polygon(target, silver_dark, [
                (cx - w // 3, cy - h // 2 + 1),
                (cx + w // 3, cy - h // 2 + 1),
                (cx, cy + h // 3),
            ])
            # Hot pulsing eye in the center (the kamikaze "brain")
            pulse = 200 + int(55 * math.sin(self._t * 8))
            pygame.draw.circle(target, (pulse, 80, 30), (cx, cy), 2)
            pygame.draw.circle(target, orange_bright, (cx, cy), 1)
            # Hot orange exhaust at the TOP (back of ship) — trail of fire
            pygame.draw.circle(target, orange, (cx - 1, cy - h // 2), 1)
            pygame.draw.circle(target, orange, (cx + 1, cy - h // 2), 1)
            pygame.draw.circle(target, (255, 255, 200), (cx, cy - h // 2 - 1), 1)
        elif e.kind == EnemyKind.SNIPER:
            # BLOQUE 58.4: SNIPER — anchored blue laser. Silver + blue.
            # Long horizontal body with a long laser cannon pointing down.
            silver = (160, 170, 190)
            silver_dark = (85, 95, 115)
            blue = (100, 160, 255)
            blue_bright = (180, 220, 255)
            # Main body (long horizontal bar)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.rect(target, silver, rect)
            # Inner darker panel
            inner_rect = rect.inflate(-2, -2)
            pygame.draw.rect(target, silver_dark, inner_rect)
            # Border highlight
            pygame.draw.rect(target, (195, 205, 220), rect, 1)
            # Blue glowing eye (the laser)
            pygame.draw.circle(target, blue, (cx, cy), 2)
            pygame.draw.circle(target, blue_bright, (cx, cy), 1)
            # Long blue laser cannon pointing down
            pygame.draw.rect(target, blue, (cx - 1, cy + h // 2, 2, 4))
            pygame.draw.circle(target, blue_bright, (cx, cy + h // 2 + 4), 1)
            # Side panels
            pygame.draw.rect(target, silver_dark, (cx - w // 3, cy - h // 2 + 1, 1, h - 2))
            pygame.draw.rect(target, silver_dark, (cx + w // 3, cy - h // 2 + 1, 1, h - 2))
        elif e.kind == EnemyKind.DRONE:
            # BLOQUE 58.4: DRONE — small autonomous silver octagon with
            # cyan center. Compact, minimal, scouts ahead.
            silver = (170, 180, 195)
            silver_dark = (90, 100, 115)
            cyan = (80, 220, 240)
            # Octagonal body
            import math as _m
            points = []
            for i in range(8):
                a = i * _m.pi / 4 + _m.pi / 8
                points.append((cx + int(_m.cos(a) * w / 2), cy + int(_m.sin(a) * h / 2)))
            pygame.draw.polygon(target, silver, points)
            # Inner darker octagon
            inner_pts = []
            for i in range(8):
                a = i * _m.pi / 4
                inner_pts.append((cx + int(_m.cos(a) * w / 4), cy + int(_m.sin(a) * h / 4)))
            pygame.draw.polygon(target, silver_dark, inner_pts)
            # Cyan glowing center
            pygame.draw.circle(target, cyan, (cx, cy), 1)
            pygame.draw.circle(target, (200, 240, 255), (cx, cy), 1)
        elif e.kind == EnemyKind.TURRET:
            # BLOQUE 58.4: TURRET — pink rotating base. Silver hex base
            # with a pink ring on top, 3-spoke cannons.
            silver = (170, 180, 195)
            silver_dark = (90, 100, 115)
            pink = (255, 100, 180)
            pink_bright = (255, 180, 220)
            # Hexagonal base
            import math as _m
            points = []
            for i in range(6):
                a = i * _m.pi / 3 + _m.pi / 6
                points.append((cx + int(_m.cos(a) * w / 2), cy + int(_m.sin(a) * h / 2)))
            pygame.draw.polygon(target, silver, points)
            # Inner hex
            inner_pts = []
            for i in range(6):
                a = i * _m.pi / 3
                inner_pts.append((cx + int(_m.cos(a) * w / 3), cy + int(_m.sin(a) * h / 3)))
            pygame.draw.polygon(target, silver_dark, inner_pts)
            # Rotating pink ring (3 spokes)
            angle = self._t * 3
            for spoke in range(3):
                a = angle + spoke * (2 * _m.pi / 3)
                ex = cx + int(_m.cos(a) * w / 3)
                ey = cy + int(_m.sin(a) * h / 3)
                pygame.draw.line(target, pink, (cx, cy), (ex, ey), 1)
                pygame.draw.circle(target, pink_bright, (ex, ey), 1)
            # Pink glowing center
            pygame.draw.circle(target, pink, (cx, cy), 2)
            pygame.draw.circle(target, pink_bright, (cx, cy), 1)
        elif e.kind == EnemyKind.SUB_BOSS:
            # BLOQUE 58.6.1: SUB_BOSS — V silhouette (cierra el arco).
            # User feedback: "el diseño esta bien, pero cierra el arco, para
            # que parezca mas una V en vez de un [U]". The fangs now angle
            # DOWN-AND-INWARD so the two fang tips converge at a point at
            # the BOTTOM-CENTER, forming a clean V (apex at bottom). The
            # arc closes because the open U-shape becomes a closed V.
            # Keeps all the menacing features from BLOQUE 58.6:
            # pink/magenta venom fang tips, cyan eye, silver body, red
            # accent stripes, sharp pointed nose at the BOTTOM (which is
            # also the V apex, where the two fangs meet).
            wolf_base = (160, 170, 185)  # silver body
            wolf_dark = (80, 90, 105)
            wolf_red = (220, 50, 60)
            cyan_eye = (80, 220, 240)
            pink_fang = (255, 100, 180)  # venom/maligno fang tip color
            pink_fang_bright = (255, 200, 230)
            wolf_engine = (255, 180, 60)
            # Subtle vertical bob (2 Hz, ±1 px) for warp-thrust feel
            bob = int(round(math.sin(self._t * 2.0 * math.pi) * 1.0))
            cy_b = cy + bob
            # Engine pulse: brightness varies 0.7..1.0 (6 Hz)
            engine_pulse = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(self._t * 6.0))
            # Eye pulse: 3 Hz for menacing "scanning" feel
            eye_pulse = 0.85 + 0.15 * math.sin(self._t * 3.0)
            # Layout (top to bottom of the sprite):
            #   1. 2 FANGS angling OUTWARD-AND-DOWNWARD, CONVERGING at the
            #      bottom-center (the "cierra el arco" feature — V apex)
            #   2. Wings on the sides, swept back (Star Wolf style)
            #   3. Engines at the top (back of ship, pulsing)
            #   4. Central body with menacing cyan eye
            #   5. Sharp pointed nose at the BOTTOM (also the V apex)
            body_top_y = cy_b - h // 2
            body_bot_y = cy_b + h // 2
            shoulder_y = body_top_y + 2
            mid_wing_y = cy_b - 1
            wing_tip_dx = w
            wing_tip_y = shoulder_y - 1
            # 1) 2 SHARP FANGS angling OUTWARD-AND-DOWNWARD, CONVERGING at
            #    the bottom-center. The two fang tips meet 1 pixel apart at
            #    (cx, body_bot_y + 1) — the V apex. This closes the open
            #    U-shape of the previous design into a clean V.
            fang_tip_y = body_bot_y + 1   # V apex: just below the nose
            fang_tip_x_l = cx - 1         # left fang converges slightly left of center
            fang_tip_x_r = cx + 1         # right fang converges slightly right of center
            # Left fang: from upper-left, angling DOWN-AND-INWARD to the V apex
            pygame.draw.polygon(target, wolf_base, [
                (cx - 2, body_top_y + 1),                # base inner top
                (cx - 4, body_top_y),                    # base outer top (widest)
                (fang_tip_x_l, fang_tip_y),              # sharp tip (V apex, left)
                (cx - 2, body_bot_y - 1),                # base bottom (at nose level)
            ])
            # Right fang: mirror, converging at the same V apex
            pygame.draw.polygon(target, wolf_base, [
                (cx + 2, body_top_y + 1),
                (cx + 4, body_top_y),
                (fang_tip_x_r, fang_tip_y),
                (cx + 2, body_bot_y - 1),
            ])
            # Red Star Wolf accent stripe along fang leading edge
            pygame.draw.line(target, wolf_red,
                             (cx - 3, body_top_y + 1),
                             (fang_tip_x_l, fang_tip_y - 1), 1)
            pygame.draw.line(target, wolf_red,
                             (cx + 3, body_top_y + 1),
                             (fang_tip_x_r, fang_tip_y - 1), 1)
            # Pink/magenta fang TIPS at the V apex (the "venom" / "maligno" color)
            pygame.draw.circle(target, pink_fang, (fang_tip_x_l, fang_tip_y), 1)
            pygame.draw.circle(target, pink_fang, (fang_tip_x_r, fang_tip_y), 1)
            pygame.draw.circle(target, pink_fang_bright,
                               (fang_tip_x_l, fang_tip_y), 1)
            pygame.draw.circle(target, pink_fang_bright,
                               (fang_tip_x_r, fang_tip_y), 1)
            # 2) WINGS behind the fangs (swept back, Star Wolf style)
            # Left wing
            pygame.draw.polygon(target, wolf_base, [
                (cx - 1, shoulder_y),
                (cx - 4, shoulder_y - 1),
                (cx - wing_tip_dx, wing_tip_y),
                (cx - wing_tip_dx, wing_tip_y + 2),
                (cx - 2, mid_wing_y),
            ])
            # Right wing
            pygame.draw.polygon(target, wolf_base, [
                (cx + 1, shoulder_y),
                (cx + 4, shoulder_y - 1),
                (cx + wing_tip_dx, wing_tip_y),
                (cx + wing_tip_dx, wing_tip_y + 2),
                (cx + 2, mid_wing_y),
            ])
            # 3) ENGINES at the top (back of ship, pulsing)
            eng_y = body_top_y
            eng_c = (
                int(255 * engine_pulse),
                int(180 * engine_pulse),
                int(60 * engine_pulse),
            )
            pygame.draw.rect(target, eng_c, (cx - 1, eng_y, 1, 2))
            pygame.draw.rect(target, eng_c, (cx, eng_y, 1, 2))
            # 4) MAIN BODY — angular dart with sharp nose at the BOTTOM
            pygame.draw.polygon(target, wolf_base, [
                (cx, body_bot_y),               # sharp nose DOWN
                (cx + 3, mid_wing_y + 1),
                (cx + 1, shoulder_y),
                (cx, body_top_y + 1),
                (cx - 1, shoulder_y),
                (cx - 3, mid_wing_y + 1),
            ])
            # Body panel detail (darker stripe down the center)
            pygame.draw.line(target, wolf_dark, (cx, body_top_y + 1), (cx, body_bot_y - 1), 1)
            # 5) MENACING CYAN EYE in the body center (3 layers, 3 Hz pulse)
            eye_r1 = int(4 * eye_pulse)
            eye_r2 = int(3 * eye_pulse)
            eye_r3 = int(2 * eye_pulse)
            pygame.draw.circle(target, (40, 80, 110), (cx, cy_b), eye_r1 + 1)  # dark outer
            pygame.draw.circle(target, cyan_eye, (cx, cy_b), eye_r1)  # main eye
            pygame.draw.circle(target, (200, 240, 255), (cx, cy_b), eye_r2)  # bright glow
            pygame.draw.circle(target, (255, 255, 255), (cx, cy_b), eye_r3)  # white-hot
            # 6) Wing leading-edge highlights
            wing_hi = (195, 205, 220)
            pygame.draw.line(target, wing_hi,
                             (cx - 1, shoulder_y), (cx - wing_tip_dx, wing_tip_y), 1)
            pygame.draw.line(target, wing_hi,
                             (cx + 1, shoulder_y), (cx + wing_tip_dx, wing_tip_y), 1)
            # 7) Red Star Wolf accent stripes along wing leading edges
            pygame.draw.line(target, wolf_red,
                             (cx - 2, shoulder_y + 1),
                             (cx - wing_tip_dx + 1, wing_tip_y + 1), 1)
            pygame.draw.line(target, wolf_red,
                             (cx + 2, shoulder_y + 1),
                             (cx + wing_tip_dx - 1, wing_tip_y + 1), 1)
            # 8) Wingtip running lights (red dots at the wing tips)
            pygame.draw.circle(target, (255, 80, 80),
                               (cx - wing_tip_dx, wing_tip_y), 1)
            pygame.draw.circle(target, (255, 80, 80),
                               (cx + wing_tip_dx, wing_tip_y), 1)
            # 9) Subtle outer red halo to mark it as a mini-boss (the menace aura)
            halo = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
            halo_alpha = 40 + int(20 * math.sin(self._t * 6))
            pygame.draw.ellipse(halo, (*wolf_red, halo_alpha),
                                (0, 0, w + 16, h + 16), 1)
            target.blit(halo, (cx - (w + 16) // 2, cy_b - (h + 16) // 2))
        else:
            # Default: rectangle with inner detail
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.rect(target, color, rect)
            if w >= 10 and h >= 6:
                inner = rect.inflate(-max(2, w // 3), -max(2, h // 3))
                inner_color = (max(0, color[0] - 60), max(0, color[1] - 60), max(0, color[2] - 60))
                pygame.draw.rect(target, inner_color, inner)
        # Mini drones: white inner highlight
        if cfg.is_mini:
            pygame.draw.rect(target, (180, 230, 255),
                             (cx - w // 2 + 1, cy - h // 2 + 1, w - 2, h - 2))

    def _draw_boss(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 51: dispatch to per-boss visual.
        - GOLIATH (Act 1): biblical giant warrior — armor, helmet, spear, shield.
        - HYDRA/PHANTOM/NEMESIS: simple rect (per-boss redesign deferred to future BLOQUE).
        """
        if self._boss is None:
            return
        if self._boss.id == BossId.GOLIATH:
            self._draw_goliath(target, ox, oy)
        else:
            self._draw_boss_simple(target, ox, oy)

    def _draw_boss_spear(self, target: pygame.Surface, s: "BossSpear",
                          ox: int, oy: int) -> None:
        """BLOQUE 52: render a GOLIATH spear projectile in flight.

        Main spears are big and detailed (wood shaft + iron tip + glow).
        Fragments are smaller chunks (just shaft + tip). Both orient
        along their base direction and pulse slightly. Hit flash goes
        white for 0.08s.
        """
        if s.kind == "main":
            self._draw_spear_main(target, s, ox, oy)
        else:
            self._draw_spear_fragment(target, s, ox, oy)

    def _draw_shield_laser(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 53a: render the GOLIATH charged shield laser.

        A thick vertical beam from the boss's shield position down to
        the bottom of the screen. Pulses red, with a bright white core
        and an outer red glow. Drawn after the boss so it sits on top.
        """
        if self._boss is None:
            return
        # Beam source = shield position (mirrors _handle_shield_collisions)
        beam_cx = int(self._boss.x - 30) + ox
        beam_top = int(self._boss.y + 12) + oy
        beam_w = 8
        # Pulse intensity
        pulse = 0.5 + 0.5 * math.sin(self._t * 30.0)
        beam_h = INTERNAL_H - beam_top + 4
        # Outer red glow (wide)
        glow = pygame.Surface((beam_w + 24, beam_h), pygame.SRCALPHA)
        glow_alpha = int(80 + 40 * pulse)
        pygame.draw.rect(glow, (255, 60, 40, glow_alpha),
                         (0, 0, beam_w + 24, beam_h))
        target.blit(glow, (beam_cx - (beam_w + 24) // 2, beam_top - 2))
        # Mid red beam
        mid = pygame.Surface((beam_w + 8, beam_h), pygame.SRCALPHA)
        mid_alpha = int(180 + 40 * pulse)
        pygame.draw.rect(mid, (255, 120, 60, mid_alpha),
                         (0, 0, beam_w + 8, beam_h))
        target.blit(mid, (beam_cx - (beam_w + 8) // 2, beam_top - 2))
        # White hot core
        core = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
        pygame.draw.rect(core, (255, 240, 200, 230),
                         (0, 0, beam_w, beam_h))
        target.blit(core, (beam_cx - beam_w // 2, beam_top - 2))
        # Bright top origin (the shield exploding)
        origin_size = 24
        origin = pygame.Surface((origin_size, origin_size), pygame.SRCALPHA)
        origin_alpha = int(220 + 35 * pulse)
        pygame.draw.circle(origin, (255, 220, 160, origin_alpha),
                           (origin_size // 2, origin_size // 2),
                           origin_size // 2)
        target.blit(origin, (beam_cx - origin_size // 2,
                              beam_top - origin_size // 2 + 4))

    def _draw_spear_main(self, target: pygame.Surface, s: "BossSpear",
                          ox: int, oy: int) -> None:
        """BLOQUE 52: main spear visual (long, thick, iron-tipped)."""
        cx = int(s.x) + ox
        cy = int(s.y) + oy
        # Angle of the base direction
        angle = math.atan2(s.base_vy, s.base_vx)
        # Perpendicular to the base for shaft thickness (perp already computed)
        # Length: 28 px shaft + 6 px tip
        # Compute endpoints
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # Shaft: from cx-14*cos to cx+14*cos
        shaft_back_x = cx - int(14 * cos_a)
        shaft_back_y = cy - int(14 * sin_a)
        shaft_front_x = cx + int(14 * cos_a)
        shaft_front_y = cy + int(14 * sin_a)
        # Perpendicular for thickness (2px)
        perp_x = -sin_a * 2
        perp_y = cos_a * 2
        # Iron body color (or white if flashing)
        if s.flash_t > 0.0:
            wood_color = (255, 255, 255)
            iron_color = (255, 255, 255)
            glow_color = (255, 255, 255)
        else:
            wood_color = (130, 90, 55)
            iron_color = (160, 160, 180)
            glow_color = (255, 180, 100)
        # Outer glow (aura around the spear)
        aura = pygame.Surface((40, 12), pygame.SRCALPHA)
        aura_alpha = 80 + int(40 * math.sin(s.wave_t * 6.0))
        pygame.draw.ellipse(
            aura, (*glow_color, aura_alpha),
            (0, 0, 40, 12),
        )
        # Rotate the aura around its center
        rotated_aura = pygame.transform.rotate(aura, -math.degrees(angle))
        aura_rect = rotated_aura.get_rect(center=(cx, cy))
        target.blit(rotated_aura, aura_rect.topleft)
        # Wooden shaft (thick rectangle along the base direction)
        shaft_poly = [
            (shaft_back_x + perp_x, shaft_back_y + perp_y),
            (shaft_front_x + perp_x, shaft_front_y + perp_y),
            (shaft_front_x - perp_x, shaft_front_y - perp_y),
            (shaft_back_x - perp_x, shaft_back_y - perp_y),
        ]
        pygame.draw.polygon(target, (70, 50, 30), shaft_poly)  # dark wood edge
        pygame.draw.polygon(target, wood_color, [
            (shaft_back_x + perp_x * 0.6, shaft_back_y + perp_y * 0.6),
            (shaft_front_x + perp_x * 0.6, shaft_front_y + perp_y * 0.6),
            (shaft_front_x - perp_x * 0.6, shaft_front_y - perp_y * 0.6),
            (shaft_back_x - perp_x * 0.6, shaft_back_y - perp_y * 0.6),
        ])
        # Wood grain (a darker line down the middle)
        pygame.draw.line(
            target, (90, 60, 35),
            (shaft_back_x, shaft_back_y),
            (shaft_front_x, shaft_front_y), 1,
        )
        # Iron spearhead (triangle at the front, extending past the shaft)
        tip_back_x = shaft_front_x
        tip_back_y = shaft_front_y
        tip_left_x = shaft_front_x + int(2 * cos_a) - int(perp_x * 2)
        tip_left_y = shaft_front_y + int(2 * sin_a) - int(perp_y * 2)
        tip_right_x = shaft_front_x + int(2 * cos_a) + int(perp_x * 2)
        tip_right_y = shaft_front_y + int(2 * sin_a) + int(perp_y * 2)
        tip_point_x = shaft_front_x + int(8 * cos_a)
        tip_point_y = shaft_front_y + int(8 * sin_a)
        pygame.draw.polygon(target, (40, 40, 50), [
            (tip_back_x, tip_back_y),
            (tip_left_x, tip_left_y),
            (tip_point_x, tip_point_y),
            (tip_right_x, tip_right_y),
        ])
        pygame.draw.polygon(target, iron_color, [
            (tip_back_x, tip_back_y),
            (tip_left_x, tip_left_y),
            (tip_point_x, tip_point_y),
            (tip_right_x, tip_right_y),
        ], 1)
        # Iron tip highlight
        pygame.draw.line(
            target, (220, 220, 240),
            (tip_back_x, tip_back_y),
            (tip_point_x, tip_point_y), 1,
        )
        # HP indicator (small dots on the shaft, one per HP)
        # Place at the back of the shaft
        for i in range(s.max_hp):
            dot_offset = -10 + i * 5
            dot_x = cx + int(dot_offset * cos_a)
            dot_y = cy + int(dot_offset * sin_a)
            if i < s.hp:
                dot_color = (255, 60, 60)
            else:
                dot_color = (60, 30, 30)
            pygame.draw.circle(target, dot_color, (dot_x, dot_y), 1)

    def _draw_spear_fragment(self, target: pygame.Surface, s: "BossSpear",
                              ox: int, oy: int) -> None:
        """BLOQUE 52: small spear fragment (shorter, no aura, just a chunk)."""
        cx = int(s.x) + ox
        cy = int(s.y) + oy
        angle = math.atan2(s.base_vy, s.base_vx)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # Smaller shaft: 6 long, 1 thick
        shaft_back_x = cx - int(6 * cos_a)
        shaft_back_y = cy - int(6 * sin_a)
        shaft_front_x = cx + int(6 * cos_a)
        shaft_front_y = cy + int(6 * sin_a)
        # Perpendicular
        perp_x = -sin_a
        perp_y = cos_a
        # Flash
        if s.flash_t > 0.0:
            wood_color = (255, 255, 255)
            iron_color = (255, 255, 255)
        else:
            wood_color = (140, 100, 60)
            iron_color = (180, 180, 200)
        # Shaft
        pygame.draw.line(
            target, wood_color,
            (shaft_back_x, shaft_back_y),
            (shaft_front_x, shaft_front_y), 2,
        )
        # Tiny iron tip
        tip_x = shaft_front_x + int(3 * cos_a)
        tip_y = shaft_front_y + int(3 * sin_a)
        pygame.draw.polygon(target, iron_color, [
            (shaft_front_x, shaft_front_y),
            (shaft_front_x + int(cos_a) - int(perp_x), shaft_front_y + int(sin_a) - int(perp_y)),
            (tip_x, tip_y),
            (shaft_front_x + int(cos_a) + int(perp_x), shaft_front_y + int(sin_a) + int(perp_y)),
        ])

    def _draw_boss_simple(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """Default boss visual — simple rectangle with eye. Used by HYDRA/PHANTOM/NEMESIS."""
        if self._boss is None:
            return
        cfg = BOSS_CONFIGS[self._boss.id]
        w, h = cfg.width, cfg.height
        rect = pygame.Rect(
            int(self._boss.x - w / 2 + ox),
            int(self._boss.y - h / 2 + oy),
            w, h,
        )
        # Glow under boss
        glow = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*cfg.color, 60), (0, 0, w + 16, h + 16), border_radius=4)
        target.blit(glow, (rect.x - 8, rect.y - 8))
        pygame.draw.rect(target, cfg.color, rect)
        # Boss "eye" detail
        eye_w = max(4, w // 3)
        eye_h = max(2, h // 4)
        eye_rect = pygame.Rect(
            rect.x + (w - eye_w) // 2,
            rect.y + (h - eye_h) // 2,
            eye_w, eye_h,
        )
        pygame.draw.rect(target, (255, 255, 255), eye_rect)
        # Phase border color
        border_color = (255, 220, 80) if self._boss.phase >= 2 else (180, 180, 220)
        pygame.draw.rect(target, border_color, rect, 1)
        # HP bar
        if self._boss.hp < self._boss.max_hp:
            bar_w = w + 4
            ratio = self._boss.hp / self._boss.max_hp
            pygame.draw.rect(target, (60, 60, 80), (rect.x - 2, rect.y - 6, bar_w, 3))
            pygame.draw.rect(target, (220, 80, 80), (rect.x - 1, rect.y - 5, int(bar_w * ratio), 2))

    def _draw_goliath(self, target: pygame.Surface, ox: int, oy: int) -> None:
        """BLOQUE 51: GOLIATH — biblical giant warrior visual.

        Reference: the Philistine giant from the David vs. Goliath story.
        Heavy bronze armor, helmet with visor, glowing red eyes behind the
        slit, a long spear in the right hand, and a round shield in the
        left. A subtle "breathing" bob + eye pulse + floating embers give
        it a menacing, alive feel. Phase 2 reveals cracked armor with
        inner red glow.

        The visual bounding box is ~44x44 (slightly larger than the 32x18
        hitbox). The hitbox stays 70% of cfg.width/height so the boss is
        still fair to fight — only the silhouette grows.
        """
        if self._boss is None:
            return
        cfg = BOSS_CONFIGS[self._boss.id]
        # Visual is centered on the hitbox; offset y for the "breathing" bob.
        bob = math.sin(self._t * 1.0) * 1.5
        # Hit feedback (white flash for 0.08s after a hit)
        flash_t = self._boss_flash.get(id(self._boss), 0.0)
        flashing = flash_t > 0.0
        # Center of the hitbox (anchor for the visual)
        cx = int(self._boss.x + ox)
        cy = int(self._boss.y + oy)
        # Visual offset (centered on hitbox, much larger than 32x18 hitbox
        # to feel like a GIANT — the hitbox is 70% of cfg.width/height so
        # the visual is the imposing silhouette, the hitbox is the armor core)
        vw, vh = 64, 60
        vx = cx - vw // 2
        vy = cy - vh // 2 + int(bob)
        # Color palette
        bronze_main = (180, 130, 70) if not flashing else (240, 220, 200)
        bronze_hi = (220, 170, 100)
        bronze_sh = (100, 70, 40)
        iron = (70, 70, 85)
        # Phase 2 makes the inner red glow stronger
        phase2 = self._boss.phase >= 2
        # ------------------------------------------------------------------
        # Layer 1: bronze aura / halo (pulsing)
        # ------------------------------------------------------------------
        aura_pulse = 0.5 + 0.5 * math.sin(self._t * 1.5)
        aura_size = 88
        aura = pygame.Surface((aura_size, aura_size), pygame.SRCALPHA)
        aura_alpha = int(35 + 25 * aura_pulse)
        pygame.draw.ellipse(
            aura, (180, 110, 50, aura_alpha),
            (0, 0, aura_size, aura_size), 1,
        )
        target.blit(aura, (cx - aura_size // 2, cy - aura_size // 2 + int(bob)))
        # ------------------------------------------------------------------
        # Layer 2: idle embers (floating up from the boss). Cheap, drawn
        # here rather than via ParticleEngine to keep frame budget tight.
        # ------------------------------------------------------------------
        for i in range(4):
            ember_phase = (self._t * 0.8 + i * 0.25) % 1.0
            ember_x = cx + int(math.sin(ember_phase * 6.28 + i) * 18)
            ember_y = vy + vh - int(ember_phase * 32)
            ember_size = 1 + int((1.0 - ember_phase) * 1.5)
            ember_alpha = int(200 * (1.0 - ember_phase))
            ember_color = (255, 140, 60) if phase2 else (255, 170, 80)
            ember_surf = pygame.Surface((ember_size * 2 + 2, ember_size * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                ember_surf, (*ember_color, ember_alpha),
                (ember_size + 1, ember_size + 1), ember_size,
            )
            target.blit(ember_surf, (ember_x - ember_size - 1, ember_y - ember_size - 1))
        # ------------------------------------------------------------------
        # Layer 3: stone base / plinth (the giant stands on a platform)
        # ------------------------------------------------------------------
        base_w = 56
        base_h = 5
        base_x = cx - base_w // 2
        base_y = vy + vh - 2
        pygame.draw.rect(target, (50, 45, 40), (base_x, base_y, base_w, base_h))
        pygame.draw.rect(target, (90, 80, 65), (base_x, base_y, base_w, 1))  # top edge
        # Cracks in the base
        for i, (sx, ex) in enumerate([(base_x + 8, base_x + 16), (base_x + 32, base_x + 44)]):
            pygame.draw.line(target, (30, 25, 20), (sx, base_y + 1), (ex, base_y + base_h - 1), 1)
        # ------------------------------------------------------------------
        # Layer 4: greaves (leg armor — two bronze blocks)
        # ------------------------------------------------------------------
        greave_w = 11
        greave_h = 11
        greave_y = vy + vh - 2 - greave_h
        # Left greave
        pygame.draw.rect(target, bronze_sh, (cx - 16, greave_y, greave_w, greave_h))
        pygame.draw.rect(target, bronze_main, (cx - 16, greave_y, greave_w, greave_h - 1))
        pygame.draw.rect(target, bronze_hi, (cx - 16, greave_y, greave_w, 1))  # top edge
        # Right greave
        pygame.draw.rect(target, bronze_sh, (cx + 5, greave_y, greave_w, greave_h))
        pygame.draw.rect(target, bronze_main, (cx + 5, greave_y, greave_w, greave_h - 1))
        pygame.draw.rect(target, bronze_hi, (cx + 5, greave_y, greave_w, 1))
        # Knee highlights
        pygame.draw.circle(target, bronze_hi, (cx - 11, greave_y + 3), 1)
        pygame.draw.circle(target, bronze_hi, (cx + 10, greave_y + 3), 1)
        # ------------------------------------------------------------------
        # Layer 5: torso / main body armor (segmented plates)
        # ------------------------------------------------------------------
        torso_w = 36
        torso_h = 30
        torso_x = cx - torso_w // 2
        torso_y = vy + vh - 2 - greave_h - torso_h
        # Outer body
        pygame.draw.rect(target, bronze_sh, (torso_x, torso_y, torso_w, torso_h))
        pygame.draw.rect(target, bronze_main, (torso_x, torso_y, torso_w, torso_h - 1))
        # 4 horizontal plate segments (with glowing red seams)
        plate_h = torso_h // 4
        for i in range(1, 4):
            seam_y = torso_y + i * plate_h
            # Dark seam
            pygame.draw.line(
                target, (60, 40, 20),
                (torso_x + 1, seam_y), (torso_x + torso_w - 2, seam_y), 1,
            )
            # Inner red glow (phase 2 makes this more visible)
            glow_color = (255, 80, 30) if phase2 else (180, 60, 30)
            glow_alpha = int(160 if phase2 else 80)
            seam_glow = pygame.Surface((torso_w - 4, 2), pygame.SRCALPHA)
            seam_glow.fill((*glow_color, glow_alpha))
            target.blit(seam_glow, (torso_x + 2, seam_y - 1))
        # Central bronze "spine" highlight
        pygame.draw.line(
            target, bronze_hi,
            (cx, torso_y + 2), (cx, torso_y + torso_h - 3), 1,
        )
        # Central chest emblem (small cross / star)
        emblem_y = torso_y + plate_h + 1
        pygame.draw.line(target, (255, 220, 150), (cx - 3, emblem_y), (cx + 3, emblem_y), 1)
        pygame.draw.line(target, (255, 220, 150), (cx, emblem_y - 2), (cx, emblem_y + 2), 1)
        # ------------------------------------------------------------------
        # Layer 6: pauldrons (shoulder armor — wider on each side)
        # ------------------------------------------------------------------
        pauldron_w = 12
        pauldron_h = 8
        pauldron_y = torso_y - pauldron_h + 1
        # Left pauldron
        pygame.draw.rect(
            target, bronze_main,
            (torso_x - pauldron_w + 1, pauldron_y, pauldron_w, pauldron_h),
        )
        pygame.draw.rect(target, bronze_hi, (torso_x - pauldron_w + 1, pauldron_y, pauldron_w, 1))
        # Spikes on left pauldron
        pygame.draw.polygon(target, bronze_hi, [
            (torso_x - pauldron_w + 3, pauldron_y - 1),
            (torso_x - pauldron_w + 5, pauldron_y - 1),
            (torso_x - pauldron_w + 4, pauldron_y - 4),
        ])
        # Right pauldron
        pygame.draw.rect(
            target, bronze_main,
            (torso_x + torso_w - 1, pauldron_y, pauldron_w, pauldron_h),
        )
        pygame.draw.rect(target, bronze_hi, (torso_x + torso_w - 1, pauldron_y, pauldron_w, 1))
        # Spikes on right pauldron
        pygame.draw.polygon(target, bronze_hi, [
            (torso_x + torso_w + 5, pauldron_y - 1),
            (torso_x + torso_w + 7, pauldron_y - 1),
            (torso_x + torso_w + 6, pauldron_y - 4),
        ])
        # ------------------------------------------------------------------
        # Layer 7: helmet (bronze dome with visor + crest + horns)
        # ------------------------------------------------------------------
        helmet_w = 22
        helmet_h = 14
        helmet_x = cx - helmet_w // 2
        helmet_y = pauldron_y - helmet_h + 1
        # Helmet body
        pygame.draw.rect(target, bronze_sh, (helmet_x, helmet_y, helmet_w, helmet_h))
        pygame.draw.rect(target, bronze_main, (helmet_x, helmet_y, helmet_w, helmet_h - 1))
        pygame.draw.rect(target, bronze_hi, (helmet_x, helmet_y, helmet_w, 1))
        # Side horns (left + right) — biblical giant icon
        pygame.draw.polygon(target, bronze_hi, [
            (helmet_x, helmet_y + 2),
            (helmet_x - 4, helmet_y - 1),
            (helmet_x - 2, helmet_y + 2),
        ])
        pygame.draw.polygon(target, bronze_hi, [
            (helmet_x + helmet_w, helmet_y + 2),
            (helmet_x + helmet_w + 4, helmet_y - 1),
            (helmet_x + helmet_w + 2, helmet_y + 2),
        ])
        # Visor slit (dark)
        visor_y = helmet_y + 5
        visor_h = 3
        pygame.draw.rect(
            target, (15, 10, 5),
            (helmet_x + 2, visor_y, helmet_w - 4, visor_h),
        )
        # Crest / peak on top
        pygame.draw.polygon(target, bronze_hi, [
            (cx - 2, helmet_y - 4),
            (cx + 2, helmet_y - 4),
            (cx, helmet_y - 9),
        ])
        # Crest ridge (red plume highlight)
        pygame.draw.line(target, (200, 40, 40), (cx, helmet_y - 9), (cx, helmet_y - 1), 1)
        # Helmet rivets (4 corners + center)
        for rx, ry in [(helmet_x + 1, helmet_y + 1), (helmet_x + helmet_w - 2, helmet_y + 1),
                        (helmet_x + 1, helmet_y + helmet_h - 2), (helmet_x + helmet_w - 2, helmet_y + helmet_h - 2)]:
            pygame.draw.circle(target, bronze_sh, (rx, ry), 1)
        # ------------------------------------------------------------------
        # Layer 8: glowing red eyes (inside the visor slit) — BLOQUE 51
        # signature element. Pulses, gets brighter on phase 2 / hit.
        # ------------------------------------------------------------------
        eye_pulse = 0.5 + 0.5 * math.sin(self._t * 4.0)
        if phase2:
            eye_pulse = 0.7 + 0.3 * math.sin(self._t * 6.0)  # faster, more frantic
        if flashing:
            eye_color = (255, 255, 255)  # white on hit
        else:
            eye_r = 255
            eye_g = int(40 + 50 * eye_pulse)
            eye_b = int(20 + 30 * eye_pulse)
            eye_color = (eye_r, eye_g, eye_b)
        # Eye glow halo (oval, extends slightly outside the visor)
        eye_halo = pygame.Surface((16, 8), pygame.SRCALPHA)
        eye_halo_alpha = int(70 + 70 * eye_pulse)
        pygame.draw.ellipse(
            eye_halo, (*eye_color, eye_halo_alpha),
            (0, 0, 16, 8),
        )
        target.blit(eye_halo, (cx - 8, visor_y - 2))
        # Two eye dots
        pygame.draw.circle(target, eye_color, (cx - 4, visor_y + 1), 1)
        pygame.draw.circle(target, eye_color, (cx + 4, visor_y + 1), 1)
        # Bright core
        if not flashing:
            pygame.draw.circle(target, (255, 240, 200), (cx - 4, visor_y + 1), 0)
            pygame.draw.circle(target, (255, 240, 200), (cx + 4, visor_y + 1), 0)
        # ------------------------------------------------------------------
        # Layer 9: shield (round, on the LEFT side)
        # BLOQUE 53a: as the player charges the shield (20 hits), it
        # glows brighter. At 20, the boss fires the laser instead of
        # drawing a normal shield (the laser is drawn separately).
        # ------------------------------------------------------------------
        shield_cx = cx - 30
        shield_cy = torso_y + 12
        shield_r = 13
        # Charge ratio (0..1) — only meaningful when not firing the laser
        charge_ratio = min(1.0, self._boss_shield_hits / 20.0)
        # Shield body (iron) — recolor as it charges: iron → bright blue
        if charge_ratio < 0.5:
            shield_color = iron
        elif charge_ratio < 0.85:
            # Iron → mid blue
            t = (charge_ratio - 0.5) / 0.35
            shield_color = (
                int(70 + (110 - 70) * t),
                int(70 + (170 - 70) * t),
                int(85 + (255 - 85) * t),
            )
        else:
            # Mid blue → bright cyan-white
            t = (charge_ratio - 0.85) / 0.15
            shield_color = (
                int(110 + (220 - 110) * t),
                int(170 + (240 - 170) * t),
                int(255),
            )
        pygame.draw.circle(target, shield_color, (shield_cx, shield_cy), shield_r)
        pygame.draw.circle(target, (110, 110, 125), (shield_cx, shield_cy), shield_r, 1)
        # Charging glow (intensity scales with charge)
        if charge_ratio > 0.0:
            glow_outer = pygame.Surface((shield_r * 4, shield_r * 4), pygame.SRCALPHA)
            glow_alpha = int(40 + 100 * charge_ratio)
            pulse = 0.5 + 0.5 * math.sin(self._t * 6.0)
            ga = int(glow_alpha * (0.6 + 0.4 * pulse))
            pygame.draw.circle(
                glow_outer, (160, 220, 255, ga),
                (shield_r * 2, shield_r * 2), shield_r + 4,
            )
            target.blit(glow_outer,
                        (shield_cx - shield_r * 2, shield_cy - shield_r * 2))
        # Inner bronze boss (center stud)
        pygame.draw.circle(target, bronze_main, (shield_cx, shield_cy), 4)
        pygame.draw.circle(target, bronze_hi, (shield_cx, shield_cy), 4, 1)
        # 4 rivets around the boss
        for i in range(4):
            a = i * math.pi / 2 + 0.4
            rx = shield_cx + int(math.cos(a) * 8)
            ry = shield_cy + int(math.sin(a) * 8)
            pygame.draw.circle(target, (40, 40, 50), (rx, ry), 1)
        # ------------------------------------------------------------------
        # Layer 10: spear (long, on the RIGHT side, pointing down).
        # BLOQUE 52: animation states.
        #   - "ready"   : spear fully extended at rest position (right side)
        #   - "winding" : pulled back behind the boss (charging)
        #   - "thrown"  : NOT drawn here (the spear is in flight, drawn
        #                 separately via _draw_boss_spear). Boss's hand
        #                 is empty for a beat — looks "unarmed".
        spear_phase = self._boss_spear_phase
        if spear_phase != "thrown":
            # Compute where the spear is in the boss's hand based on phase
            if spear_phase == "ready":
                # Default resting position
                spear_top_x = cx + 30
                spear_top_y = pauldron_y - 2
                spear_bot_x = spear_top_x + 5
                spear_bot_y = spear_top_y + 42
            else:
                # "winding" — pull the spear back behind the boss + tilt
                # Ease-in from 0.0 → 1.0 over 0.3s
                w_t = min(1.0, self._boss_spear_phase_t / 0.3)
                ease = 1.0 - (1.0 - w_t) ** 2  # ease-out
                # Pull back: shift the spear top to the left + up
                back_off_x = int(8 * ease)
                back_off_y = int(-4 * ease)
                # Also tilt the shaft back (negative tilt)
                tilt = -0.3 * ease  # radians
                spear_top_x = cx + 30 - back_off_x
                spear_top_y = pauldron_y - 2 - back_off_y
                spear_bot_x = spear_top_x + int(5 * math.cos(tilt))
                spear_bot_y = spear_top_y + int(42 * math.cos(tilt)) + int(5 * math.sin(tilt))
            # Wooden shaft
            pygame.draw.line(
                target, (90, 60, 35),
                (spear_top_x, spear_top_y), (spear_bot_x, spear_bot_y), 2,
            )
            # Shaft highlight
            pygame.draw.line(
                target, (130, 90, 55),
                (spear_top_x - 1, spear_top_y), (spear_bot_x - 1, spear_bot_y), 1,
            )
            # Iron spearhead (pointy triangle at the BOTTOM of the shaft)
            spear_tip_x = spear_bot_x + 1
            spear_tip_y = spear_bot_y + 8
            pygame.draw.polygon(target, iron, [
                (spear_bot_x - 3, spear_bot_y),
                (spear_bot_x + 5, spear_bot_y),
                (spear_tip_x, spear_tip_y),
            ])
            pygame.draw.polygon(target, (160, 160, 180), [
                (spear_bot_x - 3, spear_bot_y),
                (spear_bot_x + 5, spear_bot_y),
                (spear_tip_x, spear_tip_y),
            ], 1)
            # Spear tip glow (pulses — phase 2 brighter, or when winding)
            tip_glowing = phase2 or flashing or spear_phase == "winding"
            if tip_glowing:
                tip_glow = pygame.Surface((10, 10), pygame.SRCALPHA)
                if spear_phase == "winding":
                    tip_alpha = int(80 + 120 * w_t)
                else:
                    tip_alpha = int(120 + 80 * eye_pulse) if not flashing else 200
                pygame.draw.circle(
                    tip_glow, (255, 80, 40, tip_alpha), (5, 5), 4,
                )
                target.blit(tip_glow, (spear_tip_x - 5, spear_tip_y - 5))
            # Top of spear (small tassel / grip)
            pygame.draw.circle(target, (160, 30, 30), (spear_top_x, spear_top_y), 1)
        else:
            # "thrown" — boss hand is empty, show a brief motion blur at
            # the throw origin (the boss's right shoulder) to sell the
            # release.
            throw_x = cx + 30
            throw_y = pauldron_y
            # A small white "release" burst that fades quickly
            burst_t = self._boss_spear_phase_t  # 0.0 → 0.2 visible
            if burst_t < 0.2:
                burst_alpha = int(180 * (1.0 - burst_t / 0.2))
                burst = pygame.Surface((14, 14), pygame.SRCALPHA)
                pygame.draw.circle(
                    burst, (255, 200, 140, burst_alpha), (7, 7), 5,
                )
                target.blit(burst, (throw_x - 7, throw_y - 7))
        # ------------------------------------------------------------------
        # Layer 11: phase 2 cracks on the armor (glowing red lines)
        # ------------------------------------------------------------------
        if phase2 and not flashing:
            crack_color = (255, 60, 30)
            for (sx, sy, ex, ey) in [
                (torso_x + 6, torso_y + 4, torso_x + 10, torso_y + 12),
                (torso_x + torso_w - 7, torso_y + 6, torso_x + torso_w - 11, torso_y + 14),
                (helmet_x + 4, helmet_y + 2, helmet_x + 7, helmet_y + 8),
                (torso_x + 12, torso_y + plate_h * 2 - 2, torso_x + 16, torso_y + plate_h * 2 + 4),
            ]:
                pygame.draw.line(target, crack_color, (sx, sy), (ex, ey), 1)
        # ------------------------------------------------------------------
        # Layer 12: HP bar (always visible, with a bronze frame)
        # ------------------------------------------------------------------
        bar_w = vw + 4
        bar_h = 3
        bar_x = cx - bar_w // 2
        bar_y = vy - 6
        # Frame
        pygame.draw.rect(target, (40, 30, 20), (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))
        # Background
        pygame.draw.rect(target, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h))
        # HP fill
        ratio = self._boss.hp / self._boss.max_hp
        hp_color = (220, 60, 40) if ratio < 0.34 else (220, 140, 50)
        pygame.draw.rect(target, hp_color, (bar_x, bar_y, int(bar_w * ratio), bar_h))
