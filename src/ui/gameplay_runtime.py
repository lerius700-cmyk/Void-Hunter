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
from typing import TYPE_CHECKING, Optional

import pygame

from src.core.settings import INTERNAL_H, INTERNAL_W, FIXED_DT
from src.entities.enemies import EnemyKind, EnemyPool, Enemy
from src.entities.enemies.boss import Boss, BossId, BossPool, BOSS_CONFIGS
from src.entities.player import Player
from src.systems.hitstop import Hitstop
from src.systems.parallax import ParallaxBackground
from src.systems.particle_engine import (
    P_DEBRIS, P_DUST, P_FIRE, P_FLASH, P_SHRAPNEL, P_SMOKE, P_SPARK, ParticleEngine,
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
}


class GameplayRuntime:
    """Owns the live action loop. One per GAMEPLAY or BOSS_FIGHT scene.

    Public API:
      __init__(transition_to, is_boss=False, act=1)
      on_enter() / on_exit()
      update(dt)  — call from scene.update
      draw(target) — call from scene.draw
    """

    def __init__(self, transition_to: "TransitionFn", is_boss: bool = False, act: int = 1) -> None:
        self._transition_to = transition_to
        self._is_boss = is_boss
        self._act = act

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
        self._t = 0.0
        self._wave_spawn_timer = 0.0
        self._is_wave_active = not self._is_boss
        self._transition_pending = None
        if not self._is_boss:
            self._wave_mgr.start_wave(self._wave_idx)
            self._populate_spawn_queue()
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

    def on_exit(self) -> None:
        self._bullets.release_all()
        self._enemies.release_all()
        self._particles.release_all()
        self._bosses.release_all()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def _read_input(self) -> None:
        keys = pygame.key.get_pressed()
        self._player.input_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self._player.input_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
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
        fire_now, special_now, charge_level = self._weapon.consume_pending()
        if fire_now or special_now:
            self._spawn_player_bullet(charge_level=charge_level)
        # Reset bomb output flag
        self._player.wants_to_bomb = False

    def _spawn_player_bullet(self, charge_level: int = 0) -> None:
        spec = self._weapon.get_spec()
        # Base bullet position (at player nose)
        bx = self._player.x
        by = self._player.y - 8
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
            self._boss.update(dt)
            # Boss attack selection
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
                    self._emit_burst(p.x, p.y, count=3, kind="spark")
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
                self._player.take_damage(p.damage)
                self._emit_burst(p.x, p.y, count=4, kind="spark")
                self._shake.add_trauma(0.15)
        # Enemies ↔ player (Kamikaze / contact)
        for e in self._enemies.pool:
            if not e.active or e.state.name == "DEAD":
                continue
            if e.hitbox().colliderect(phb):
                self._player.take_damage(1)
                # Kamikaze dies on contact
                if e.kind == EnemyKind.KAMIKAZE:
                    e.apply_damage(99)
                    self._on_enemy_killed(e)
                self._emit_burst(e.x, e.y, count=6, kind="spark")
                self._shake.add_trauma(0.2)

    # ------------------------------------------------------------------
    # Kill handlers
    # ------------------------------------------------------------------
    def _on_enemy_killed(self, e: Enemy) -> None:
        score = _ENEMY_SCORE.get(e.kind, 50)
        # Element bonus: plasma bonus vs heavy/cruiser/turret/carrier
        element_bonus = e.kind.value in ("heavy", "cruiser", "turret", "carrier")
        awarded = self._scoring.on_kill(score, is_boss=False, is_element_bonus=element_bonus)
        # Weapon XP
        self._weapon.on_kill(e.kind.value)
        # Particles
        self._emit_burst(e.x, e.y, count=14, kind="explosion")
        # Hitstop on tougher kills
        if e.kind in (EnemyKind.HEAVY, EnemyKind.CARRIER, EnemyKind.SNIPER):
            self._hitstop.trigger(3)
            self._shake.add_trauma(0.2)
        # Wave progress
        if not self._is_boss:
            self._wave_mgr.current.kills += 1
            self._wave_mgr.on_wave_cleared = self._check_wave_cleared()
        # Free
        self._enemies.release(e)

    def _on_boss_killed(self) -> None:
        if self._boss is None:
            return
        score = BOSS_CONFIGS[self._boss.id].score
        self._scoring.on_kill(score, is_boss=True)
        self._scoring.on_boss_defeated(BOSS_CONFIGS[self._boss.id].name)
        self._emit_burst(self._boss.x, self._boss.y, count=64, kind="explosion")
        self._hitstop.trigger(20)
        self._shake.add_trauma(0.8)
        self._slowmo.trigger(0.30, 30)
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
        # Hitstop pauses game logic
        if self._hitstop.is_active:
            self._hitstop.update()
            return
        slowmo_factor = self._slowmo.get_factor()
        effective_dt = dt * slowmo_factor
        self._t += effective_dt
        self._read_input()
        self._player.update(effective_dt)
        self._handle_firing(effective_dt)
        self._bullets.update(effective_dt)
        self._update_enemies(effective_dt)
        self._handle_collisions()
        self._spawn_pending(effective_dt)
        self._update_wave_state(effective_dt)
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
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, target: pygame.Surface) -> None:
        # Background
        self._bg.draw(target)
        # Shake offset
        shx_f, shy_f = self._shake.get_offset()
        shx, shy = int(shx_f), int(shy_f)
        # Enemies
        for e in self._enemies.pool:
            if e.active:
                self._draw_enemy(target, e, shx, shy)
        # Boss
        if self._is_boss and self._boss is not None and self._boss.active:
            self._draw_boss(target, shx, shy)
        # Bullets
        self._bullets.draw(target)
        # Player (only if not in DEAD state and not i-frames invisible)
        if not self._player.is_dead:
            self._draw_player(target, shx, shy)
        # Particles
        self._particles.draw(target, (shx, shy))
        # HUD
        self._hud.draw(target, self._player, self._weapon, self._scoring)

    def _draw_player(self, target: pygame.Surface, ox: int, oy: int) -> None:
        surf = pygame.Surface((18, 16), pygame.SRCALPHA)
        # Flicker iframes
        if self._player.dash_iframes_left > 0 and (self._t * 30) % 2 < 1:
            return
        pygame.draw.polygon(surf, (220, 240, 255), [(9, 0), (0, 16), (18, 16)])
        pygame.draw.polygon(surf, (255, 100, 100), [(9, 4), (4, 14), (14, 14)])
        rotated = pygame.transform.rotate(surf, -self._player.current_tilt)
        rect = rotated.get_rect(center=(int(self._player.x + ox), int(self._player.y + oy)))
        target.blit(rotated, rect)
        # Afterimage trail
        for tx, ty, age in self._player.afterimage:
            alpha = max(0, int(255 * (1 - age / self._player.AFTERIMAGE_LIFE)))
            ghost = pygame.Surface((18, 16), pygame.SRCALPHA)
            pygame.draw.polygon(ghost, (220, 240, 255, alpha), [(9, 0), (0, 16), (18, 16)])
            target.blit(ghost, (int(tx - 9 + ox), int(ty - 8 + oy)))

    def _draw_enemy(self, target: pygame.Surface, e: Enemy, ox: int, oy: int) -> None:
        from src.entities.enemies.enemy import ENEMY_CONFIGS
        cfg = ENEMY_CONFIGS[e.kind]
        w, h = cfg.width, cfg.height
        rect = pygame.Rect(
            int(e.x - w / 2 + ox),
            int(e.y - h / 2 + oy),
            w, h,
        )
        # Telegraph (red flash) — skip for archetypes w/o telegraph
        if e.telegraph_timer > 0:
            color = (255, 100, 100)
        else:
            color = cfg.color
        pygame.draw.rect(target, color, rect)
        # Mini drones
        if cfg.is_mini:
            pygame.draw.rect(target, (180, 230, 255), rect.inflate(-2, -2))

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
        pygame.draw.rect(target, cfg.color, rect)
        # Phase border color
        border_color = (255, 220, 80) if self._boss.phase >= 2 else (180, 180, 220)
        pygame.draw.rect(target, border_color, rect, 1)
        # HP bar
        if self._boss.hp < self._boss.max_hp:
            bar_w = w + 4
            ratio = self._boss.hp / self._boss.max_hp
            pygame.draw.rect(target, (60, 60, 80), (rect.x - 2, rect.y - 6, bar_w, 3))
            pygame.draw.rect(target, (220, 80, 80), (rect.x - 1, rect.y - 5, int(bar_w * ratio), 2))
