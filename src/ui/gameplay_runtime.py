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

from src.core.settings import INTERNAL_H, INTERNAL_W, FIXED_DT
from src.entities.enemies import EnemyKind, EnemyPool, Enemy
from src.entities.enemies.boss import Boss, BossId, BossPool, BOSS_CONFIGS
from src.entities.player import Player, PlayerState
from src.systems.hitstop import Hitstop
from src.systems.parallax import ParallaxBackground
from src.systems.particle_engine import (
    P_DEBRIS, P_DUST, P_FIRE, P_FLASH, P_GLOW, P_ION, P_MUZZLE, P_SHRAPNEL,
    P_SMOKE, P_SPARK, ParticleEngine,
)
from src.systems.projectile import (
    BULLET_BOSS, BULLET_ENEMY, BULLET_PLAYER, BULLET_PLAYER_CHARGED,
    OWNER_BOSS, OWNER_ENEMY, OWNER_PLAYER, ProjectilePool,
)
from src.systems.scoring_system import ScoringSystem
from src.systems.screen_shake import ScreenShake
from src.systems.slowmo import SlowMo
from src.systems.weapon_system import WeaponLevel, WeaponPath, WeaponSystem
from src.ui.hud import HUD

if TYPE_CHECKING:
    from src.audio.synth import AudioEngine
    from src.systems.wave_manager import WaveManager
    from src.ui.scenes import TransitionFn


# Wave spawn intervals (seconds) — how often to drop a new enemy during a wave
WAVE_SPAWN_INTERVAL_S = 0.9
# Max enemies alive at once during regular waves
WAVE_MAX_LIVE = 8
# Score awarded per enemy archetype (mirrors ENEMY_CONFIGS)
_ENEMY_SCORE = {
    EnemyKind.SCOUT: 50, EnemyKind.CRUISER: 150, EnemyKind.HEAVY: 400,
    EnemyKind.KAMIKAZE: 200, EnemyKind.DRONE: 80, EnemyKind.SNIPER: 300,
    EnemyKind.TURRET: 250, EnemyKind.CARRIER: 800,
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
        self._pending_wave_spawns: list[tuple[float, EnemyKind, float, float]] = []
        self._is_wave_active: bool = True
        self._transition_pending: Optional[str] = None  # "boss_intro" or "act_cleared"

        # Polish state
        self._score_popups: list[ScorePopup] = []
        self._powerups: list[PowerUp] = []
        self._enemy_flash: dict[int, float] = {}  # id(e) -> flash_timer
        self._shockwaves: list[Shockwave] = []  # expanding ring effects
        self._screen_flash: float = 0.0  # 0..1 alpha of white overlay (bomb)
        self._boss_entry_t: float = 0.0  # boss slides in on first 1.5s of fight
        self._dash_consumed: bool = False  # SFX dedup
        self._last_charge_level: int = 0
        self._death_exploded: bool = False
        # BGM state
        self._bgm_started: bool = False
        # Player-state snapshot for transition SFX
        self._prev_player_state: PlayerState = PlayerState.IDLE
        # BLOQUE 22: extra polish
        self._muzzle_flash: float = 0.0  # 0..1 alpha of muzzle flash overlay
        self._charge_release_flash: float = 0.0  # 0..1 full-screen flash on charge fire
        self._boss_death_stage: int = 0  # 0 = alive, 1..3 = multi-stage explosion frames
        self._boss_death_timer: float = 0.0  # time since death for staging
        self._charge_release_shock: bool = False  # spawn expanding ring on charge release
        self._boss_death_pos: tuple[float, float] = (0.0, 0.0)  # cached pos for staged burst
        # BLOQUE 24: more polish
        self._pickup_flash: float = 0.0  # 0..1 alpha of green pickup flash overlay
        self._speed_line_t: float = 0.0  # accumulator for speed line drift
        self._level_up_flash: float = 0.0  # brief flash when weapon levels up

    def _play_sfx(self, name: str, volume: float = 1.0) -> None:
        if self._audio is not None:
            self._audio.play_sfx(name, volume)

    def _start_bgm(self, name: str) -> None:
        if self._audio is not None and not self._bgm_started:
            self._audio.play_bgm(name)
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

    def _emit_burst(self, x: float, y: float, count: int, kind: str = "spark") -> None:
        """Spawn a radial burst of particles at (x, y)."""
        kind_id = _BURST_KIND.get(kind, P_SPARK)
        for _ in range(count):
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(40.0, 120.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self._particles.emit(kind_id, x, y, vx, vy)

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
        self._player.reset()
        self._weapon.reset()
        self._scoring.reset()
        self._bullets.release_all()
        self._enemies.release_all()
        self._particles.release_all()
        self._score_popups.clear()
        self._powerups.clear()
        self._enemy_flash.clear()
        self._shockwaves.clear()
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
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_j:
                self._player.input_fire = True
            elif event.key == pygame.K_k:
                self._player.input_dash = True
            elif event.key == pygame.K_l:
                self._player.input_bomb = True
            elif event.key == pygame.K_ESCAPE:
                from src.core.scene_manager import GameState
                self._transition_to(GameState.PAUSE)

    # ------------------------------------------------------------------
    # Firing
    # ------------------------------------------------------------------
    def _handle_firing(self, dt: float) -> None:
        # Charge release (player.wants_to_charge_release)
        if self._player.wants_to_charge_release:
            charge_level = self._player.get_charge_level()
            if charge_level == 0:
                charge_level = 1
            self._weapon.request_fire(charge_level=charge_level)
        # Normal fire
        elif self._player.wants_to_shoot:
            self._weapon.request_fire(charge_level=0)
        # Bomb
        if self._player.wants_to_bomb and self._player.bombs > 0:
            self._player._consume_bomb()
            self._scoring.on_bomb()
            self._screen_clear_damage()
            self._slowmo.trigger(0.50, 8)
            self._shake.add_trauma(0.4)
            self._emit_burst(self._player.x, self._player.y, count=24, kind="spark")
            self._play_sfx("bomb", volume=0.9)
        # Charge SFX: rising pitch as charge level increases
        current_charge = self._player.get_charge_level()
        if current_charge > self._last_charge_level:
            self._play_sfx("charge_loop", volume=0.5)
        self._last_charge_level = current_charge
        fire_now, special_now, charge_level = self._weapon.consume_pending()
        if fire_now or special_now:
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

    def _spawn_player_bullet(self, charge_level: int = 0) -> None:
        spec = self._weapon.get_spec()
        # Base bullet position (at player nose)
        bx = self._player.x
        by = self._player.y - 8
        # Muzzle flash particles at the player nose
        self._emit_burst(bx, by - 2, count=3, kind="muzzle")
        # Single bullet or fan
        if spec.count == 1:
            kind = BULLET_PLAYER_CHARGED if charge_level > 0 else BULLET_PLAYER
            self._bullets.spawn(
                kind, bx, by, 0.0, -spec.speed_mult * 480.0,
                damage=spec.damage, owner=OWNER_PLAYER,
                pierce=spec.pierce, has_trail=spec.trail,
                trail_color=spec.color,
            )
        else:
            spread = math.radians(spec.spread_deg)
            for i in range(spec.count):
                # Symmetric spread around 0 (forward = -y)
                if spec.count == 1:
                    angle = 0.0
                else:
                    angle = -spread / 2 + (spread * i / (spec.count - 1))
                vx = math.sin(angle) * 480.0 * spec.speed_mult
                vy = -math.cos(angle) * 480.0 * spec.speed_mult
                kind = BULLET_PLAYER_CHARGED if charge_level > 0 else BULLET_PLAYER
                self._bullets.spawn(
                    kind, bx, by, vx, vy,
                    damage=spec.damage, owner=OWNER_PLAYER,
                    pierce=spec.pierce, has_trail=spec.trail,
                    trail_color=spec.color,
                )

    def _screen_clear_damage(self) -> None:
        """Bomb: kill all enemy bullets and damage visible enemies."""
        # Full-screen white flash (decreases over time)
        self._screen_flash = 1.0
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
        mix: dict[str, int] = script.get("mix", {})
        # Convert string keys to EnemyKind
        for kind_str, count in mix.items():
            try:
                kind = EnemyKind(kind_str)
            except ValueError:
                continue
            for _ in range(count):
                # Stagger spawns over WAVE_SPAWN_INTERVAL_S
                x = random.uniform(20, INTERNAL_W - 20)
                y = -10.0 - random.uniform(0, 60)
                self._pending_wave_spawns.append((0.0, kind, x, y))
        random.shuffle(self._pending_wave_spawns)
        # Stagger
        for i, item in enumerate(self._pending_wave_spawns):
            t = i * WAVE_SPAWN_INTERVAL_S
            self._pending_wave_spawns[i] = (t,) + item[1:]

    def _spawn_pending(self, dt: float) -> None:
        if self._is_boss:
            return
        self._wave_spawn_timer += dt
        remaining: list[tuple[float, EnemyKind, float, float]] = []
        for when, kind, x, y in self._pending_wave_spawns:
            if self._wave_spawn_timer >= when and self._enemies.active_count < WAVE_MAX_LIVE:
                e = self._enemies.spawn(kind, x, y)
                if e is not None:
                    self._wave_spawn_timer = 0.0  # reset for next spawn slot
            else:
                remaining.append((when, kind, x, y))
        self._pending_wave_spawns = remaining

    def _update_enemies(self, dt: float) -> None:
        for e in self._enemies.pool:
            if not e.active:
                continue
            e.update(dt, self._player.x, self._player.y)
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
                    # Check phase change
                    cfg = BOSS_CONFIGS[self._boss.id]
                    new_phase = 1
                    for i, threshold in enumerate(cfg.phase_thresholds):
                        if self._boss.hp / self._boss.max_hp <= threshold:
                            new_phase = i + 2
                    if new_phase != self._boss.phase:
                        self._boss.phase = new_phase
                        self._hitstop.trigger(6)
                        self._shake.add_trauma(0.5)
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

    # ------------------------------------------------------------------
    # Kill handlers
    # ------------------------------------------------------------------
    def _on_enemy_killed(self, e: Enemy) -> None:
        score = _ENEMY_SCORE.get(e.kind, 50)
        # Element bonus: plasma bonus vs heavy/cruiser/turret/carrier
        element_bonus = e.kind.value in ("heavy", "cruiser", "turret", "carrier")
        awarded = self._scoring.on_kill(score, is_boss=False, is_element_bonus=element_bonus)
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
            self._wave_mgr.on_wave_cleared = self._check_wave_cleared()
        # Free
        self._enemies.release(e)

    def _on_boss_killed(self) -> None:
        if self._boss is None:
            return
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

    def _update_wave_state(self, dt: float) -> None:
        if self._is_boss:
            return
        self._wave_mgr.current.elapsed_s += dt
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

    # ------------------------------------------------------------------
    # Player death
    # ------------------------------------------------------------------
    def _check_player_death(self) -> None:
        if self._player.is_dead:
            self._scoring.on_death()
            from src.core.scene_manager import GameState
            self._transition_to(GameState.GAME_OVER)

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return
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
        self._player.update(effective_dt)
        # Dash SFX: detect DASH entry
        if prev_player_state != PlayerState.DASH and self._player.state == PlayerState.DASH:
            self._play_sfx("dash", volume=0.5)
            self._emit_burst(self._player.x, self._player.y, count=6, kind="smoke")
        self._handle_firing(effective_dt)
        self._bullets.update(effective_dt)
        self._update_enemies(effective_dt)
        self._handle_collisions()
        self._spawn_pending(effective_dt)
        self._update_wave_state(effective_dt)
        self._update_score_popups(effective_dt)
        self._update_powerups(effective_dt)
        self._update_enemy_flash(effective_dt)
        self._update_shockwaves(effective_dt)
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
        # BLOQUE 24: speed line drift accumulator
        self._speed_line_t += effective_dt
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
        """Power-ups drift down slowly; player touches to collect."""
        alive: list[PowerUp] = []
        phb = self._player.hitbox
        for p in self._powerups:
            p.y += p.vy * dt
            p.life -= dt
            if p.life <= 0.0 or p.y > INTERNAL_H + 10:
                continue
            # Player pickup
            if not self._player.is_dead:
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
            return
        decayed: dict[int, float] = {}
        for eid, t in self._enemy_flash.items():
            t -= dt
            if t > 0.0:
                decayed[eid] = t
        self._enemy_flash = decayed

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
        """Roll for a power-up drop on enemy kill (per ENEMY_CONFIGS)."""
        from src.entities.enemies.enemy import ENEMY_CONFIGS
        cfg = ENEMY_CONFIGS.get(e.kind)
        if cfg is None:
            return
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
        for p in self._powerups:
            alpha = max(0, min(255, int(255 * (p.life / 2.0))))
            cx, cy = int(p.x) + shx, int(p.y) + shy
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
        # Player (only if not in DEAD state and not i-frames invisible)
        if not self._player.is_dead:
            self._draw_player(target, shx, shy)
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
            BULLET_BOSS, BULLET_ENEMY, BULLET_PLAYER, BULLET_PLAYER_CHARGED,
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
        surf = pygame.Surface((24, 18), pygame.SRCALPHA)
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
        # Main body (triangle pointing up)
        pygame.draw.polygon(surf, body_color, [(12, 0), (6, 12), (18, 12)])
        # Wings (two small triangles on the sides)
        pygame.draw.polygon(surf, wing_color, [(6, 8), (0, 14), (6, 14)])
        pygame.draw.polygon(surf, wing_color, [(18, 8), (24, 14), (18, 14)])
        # Cockpit (smaller triangle in center)
        cockpit_color = (255, 100, 100)
        if self._player.state == PlayerState.CHARGE:
            level = self._player.get_charge_level()
            if level >= 3:
                cockpit_color = (255, 200, 255)
            elif level >= 2:
                cockpit_color = (255, 150, 200)
            elif level >= 1:
                cockpit_color = (255, 120, 150)
        pygame.draw.polygon(surf, cockpit_color, [(12, 4), (9, 12), (15, 12)])
        # Cockpit highlight (1px white)
        pygame.draw.circle(surf, (255, 255, 255), (12, 6), 1)
        # BLOQUE 25: Wing tip lights — pulsing (red port, green starboard)
        # Pulse with different phase so they appear to "alternate"
        red_pulse = 0.5 + 0.5 * math.sin(self._t * 6.0)
        green_pulse = 0.5 + 0.5 * math.sin(self._t * 6.0 + math.pi)
        # Red port (left, x=2)
        red_color = (int(255 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)),
                     int(60 * (0.4 + 0.6 * red_pulse)))
        green_color = (int(60 * (0.4 + 0.6 * green_pulse)),
                       int(255 * (0.4 + 0.6 * green_pulse)),
                       int(100 * (0.4 + 0.6 * green_pulse)))
        pygame.draw.circle(surf, red_color, (2, 13), 1)
        pygame.draw.circle(surf, green_color, (22, 13), 1)
        # Engine intake (small dark notch at the back)
        pygame.draw.rect(surf, (40, 50, 70), (10, 12, 4, 2))
        rotated = pygame.transform.rotate(surf, -self._player.current_tilt)
        rect = rotated.get_rect(center=(int(self._player.x + ox), int(self._player.y + oy)))
        target.blit(rotated, rect)
        # BLOQUE 25: Shield effect during respawn invulnerability
        if self._player.respawn_invuln > 0.0:
            self._draw_shield(target, ox, oy)
        # BLOQUE 22: muzzle flash overlay — bright oval at the player nose
        if self._muzzle_flash > 0.0:
            self._draw_muzzle_flash(target, ox, oy)
        # Afterimage trail
        for tx, ty, age in self._player.afterimage:
            alpha = max(0, int(255 * (1 - age / self._player.AFTERIMAGE_LIFE)))
            ghost = pygame.Surface((24, 18), pygame.SRCALPHA)
            pygame.draw.polygon(ghost, (220, 240, 255, alpha), [(12, 0), (6, 12), (18, 12)])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [(6, 8), (0, 14), (6, 14)])
            pygame.draw.polygon(ghost, (180, 200, 230, alpha), [(18, 8), (24, 14), (18, 14)])
            target.blit(ghost, (int(tx - 12 + ox), int(ty - 9 + oy)))
        # Charge indicator: a ring around the player that fills as charge builds
        charge_level = self._player.get_charge_level()
        if self._player.state == PlayerState.CHARGE and charge_level > 0:
            self._draw_charge_indicator(target, charge_level, ox, oy)
        elif self._player.input_fire and self._player.charge_time > 0.1:
            # Building up — show dim ring
            progress = min(1.0, self._player.charge_time / 0.5)
            self._draw_charge_ring(target, progress, (180, 180, 200), ox, oy)

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
        """
        # Position: nose of the ship (12, 0) in the 24x18 surface
        # We draw in screen space so we can use bigger radii
        flash = self._muzzle_flash
        # Ship nose is at (player.x, player.y - 8) before tilt, near top of ship
        cx = int(self._player.x + ox)
        cy = int(self._player.y - 8 + oy)
        # Outer warm halo (yellow)
        surf = pygame.Surface((24, 24), pygame.SRCALPHA)
        outer_alpha = int(min(255, 200 * flash))
        pygame.draw.circle(surf, (255, 220, 100, outer_alpha), (12, 12), 11)
        # Middle white core
        mid_alpha = int(min(255, 230 * flash))
        pygame.draw.circle(surf, (255, 240, 200, mid_alpha), (12, 12), 6)
        # Bright center
        inner_alpha = int(min(255, 255 * flash))
        pygame.draw.circle(surf, (255, 255, 255, inner_alpha), (12, 12), 3)
        # 4 directional rays
        for ang in (0, 90, 180, 270):
            r = math.radians(ang)
            rx1 = 12 + int(math.cos(r) * 6)
            ry1 = 12 + int(math.sin(r) * 6)
            rx2 = 12 + int(math.cos(r) * 12)
            ry2 = 12 + int(math.sin(r) * 12)
            pygame.draw.line(surf, (255, 255, 200, outer_alpha), (rx1, ry1), (rx2, ry2), 2)
        target.blit(surf, (cx - 12, cy - 12))

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
        # Different shapes per kind (so the eye can distinguish)
        if e.kind == EnemyKind.SCOUT:
            # Triangle (diamond pointing down — "incoming" feel)
            points = [(cx, cy - h // 2), (cx + w // 2, cy + h // 2), (cx - w // 2, cy + h // 2)]
            pygame.draw.polygon(target, color, points)
            # Inner darker triangle for detail
            inner_color = (max(0, color[0] - 50), max(0, color[1] - 50), max(0, color[2] - 50))
            points2 = [(cx, cy - h // 4), (cx + w // 4, cy + h // 4), (cx - w // 4, cy + h // 4)]
            pygame.draw.polygon(target, inner_color, points2)
            # Eye/cockpit dot
            pygame.draw.circle(target, (255, 255, 255), (cx, cy), 1)
        elif e.kind == EnemyKind.CRUISER:
            # Hexagon (wider, more "tank" feel)
            import math as _m
            points = []
            for i in range(6):
                a = i * _m.pi / 3 + _m.pi / 6
                points.append((cx + int(_m.cos(a) * w / 2), cy + int(_m.sin(a) * h / 2)))
            pygame.draw.polygon(target, color, points)
            # Inner detail: a smaller hex rotated
            inner_color = (max(0, color[0] - 60), max(0, color[1] - 60), max(0, color[2] - 60))
            points2 = []
            for i in range(6):
                a = i * _m.pi / 3
                points2.append((cx + int(_m.cos(a) * w / 4), cy + int(_m.sin(a) * h / 4)))
            pygame.draw.polygon(target, inner_color, points2)
        elif e.kind == EnemyKind.HEAVY:
            # Square (chunky, armored)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.rect(target, color, rect)
            # Corner reinforcement (darker triangles in each corner)
            inner_color = (max(0, color[0] - 70), max(0, color[1] - 70), max(0, color[2] - 70))
            corner_size = max(2, w // 4)
            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                cx_c = cx + dx * (w // 2 - corner_size // 2)
                cy_c = cy + dy * (h // 2 - corner_size // 2)
                pygame.draw.rect(target, inner_color,
                                 (cx_c - corner_size // 2, cy_c - corner_size // 2,
                                  corner_size, corner_size))
            # Central cannon (small red circle)
            pygame.draw.circle(target, (255, 80, 80), (cx, cy + h // 4), 1)
        elif e.kind == EnemyKind.KAMIKAZE:
            # Inverted triangle (aggressive, pointed down)
            points = [(cx - w // 2, cy - h // 2), (cx + w // 2, cy - h // 2), (cx, cy + h // 2)]
            pygame.draw.polygon(target, color, points)
            # Pulsing red eye
            pulse = 200 + int(55 * math.sin(self._t * 8))
            pygame.draw.circle(target, (pulse, 50, 50), (cx, cy - 1), 2)
        elif e.kind == EnemyKind.SNIPER:
            # Long horizontal rectangle (sniper shape)
            rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
            pygame.draw.rect(target, color, rect)
            # Red laser aim line (vertical)
            pygame.draw.line(target, (255, 60, 60), (cx, cy + h // 2), (cx, cy + h // 2 + 6), 1)
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
