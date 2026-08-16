"""Main gameplay scene: player, waves, boss, HUD, FX, audio."""
from __future__ import annotations

from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.entities.boss import Boss
from stellar_horizon.entities.bullet import EnemyBullet, PlayerBullet
from stellar_horizon.entities.enemy import Enemy
from stellar_horizon.entities.player import Player
from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.screen_shake import ScreenShake
from stellar_horizon.settings import (
    ENEMY_BULLET_POOL, INTERNAL_W, INTERNAL_H, PLAYER_BULLET_POOL,
)
from stellar_horizon.ui.backgrounds import Background
from stellar_horizon.ui.hud import Hud
from stellar_horizon.waves.wave_manager import WaveManager


class GameplayScene(Scene):
    name = SceneName.GAMEPLAY

    def __init__(self, midi_player: MidiPlayer, wave_json: Path,
                 assets_dir: Path) -> None:
        self.midi_player = midi_player
        self.wave_json = wave_json
        self.assets_dir = assets_dir
        self.player: Player | None = None
        self.wave_manager: WaveManager | None = None
        self.boss: Boss | None = None
        self.boss_active: bool = False
        self.background: Background | None = None
        self.hud = Hud()
        self.fx = FxLayer()
        self.shake = ScreenShake()
        self.player_bullets: list[PlayerBullet] = [PlayerBullet() for _ in range(PLAYER_BULLET_POOL)]
        self.enemy_bullets: list[EnemyBullet] = [EnemyBullet() for _ in range(ENEMY_BULLET_POOL)]
        self.score: int = 0
        self._next: Scene | None = None
        self._keys = None

    def on_enter(self) -> None:
        screen_rect = pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)
        self.player = Player(screen_rect)
        self.wave_manager = WaveManager(self.wave_json)
        self.wave_manager.begin()
        self.background = Background(self.assets_dir / "backgrounds" / f"{self.wave_manager.background}.png")
        self.midi_player.play(str(self.assets_dir / "midi" / self.wave_manager.midi_track), loop=True)
        self.hud.set_player(self.player)
        self.hud.set_wave(1, len(self.wave_manager.waves))
        self.hud.set_enemies_remaining(0, 0)

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt: float, events: list) -> None:
        self._keys = pygame.key.get_pressed()
        self.player.firing = self._keys[pygame.K_SPACE]
        # Player
        new_player_bullets = []
        self.player.update(dt, self._keys, self.player_bullets)
        for b in self.player_bullets:
            b.update(dt)
            if b.alive:
                new_player_bullets.append(b)
        self.player_bullets = new_player_bullets
        # Wave manager + enemies
        if self.wave_manager and not self.boss_active:
            self.wave_manager.update(dt)
            for e in self.wave_manager.spawned_enemies:
                new_bullets = e.update(dt, self.player)
                for nb in new_bullets:
                    for slot in self.enemy_bullets:
                        if not slot.alive:
                            slot.x, slot.y, slot.vx, slot.vy, slot.alive = (
                                nb.x, nb.y, nb.vx, nb.vy, True
                            )
                            break
            # Bullet-vs-enemy collision
            for b in self.player_bullets:
                if not b.alive:
                    continue
                for e in self.wave_manager.spawned_enemies:
                    if e.alive and b.hitbox().colliderect(e.hitbox()):
                        e.take_damage(1)
                        b.alive = False
                        if not e.alive:
                            self.score += e.score_value()
                            self.fx.emit_explosion(e.x, e.y, scale=1.0)
                            self.shake.add_trauma(0.10)
                        break
            # Enemy-vs-player collision
            for e in self.wave_manager.spawned_enemies:
                if e.alive and e.hitbox().colliderect(self.player.hitbox()):
                    self.player.take_hit()
                    self.shake.add_trauma(0.20)
                    self.fx.emit_explosion(e.x, e.y, scale=0.6)
                    e.alive = False
            if self.wave_manager.wave_complete:
                if not self.wave_manager.next_wave():
                    self._spawn_boss()
        # Boss
        if self.boss_active and self.boss is not None:
            new_bullets = self.boss.update(dt, self.player)
            for nb in new_bullets:
                for slot in self.enemy_bullets:
                    if not slot.alive:
                        slot.x, slot.y, slot.vx, slot.vy, slot.alive = (
                            nb.x, nb.y, nb.vx, nb.vy, True
                        )
                        break
            for b in self.player_bullets:
                if not b.alive:
                    continue
                if self.boss.alive and b.hitbox().colliderect(self.boss.hitbox()):
                    self.boss.take_damage(1)
                    b.alive = False
                    if not self.boss.alive:
                        self.score += self.boss.score_value()
                        self.fx.emit_explosion(self.boss.x, self.boss.y, scale=3.0)
                        self.shake.add_trauma(0.50)
            if self.boss.alive and self.boss.hitbox().colliderect(self.player.hitbox()):
                self.player.take_hit()
                self.shake.add_trauma(0.30)
        # Enemy bullets vs player
        new_enemy_bullets = []
        for b in self.enemy_bullets:
            b.update(dt)
            if b.alive:
                if b.hitbox().colliderect(self.player.hitbox()):
                    self.player.take_hit()
                    b.alive = False
                    self.shake.add_trauma(0.15)
                else:
                    new_enemy_bullets.append(b)
        self.enemy_bullets = new_enemy_bullets
        self.fx.update(dt)
        self.shake.update(dt)
        self.background.update(dt, scroll_speed=0.0)
        # HUD
        self.hud.set_score(self.score)
        if self.boss_active and self.boss is not None:
            self.hud.set_boss(self.boss)
            self.hud.set_enemies_remaining(1 if self.boss.alive else 0, 1)
        else:
            self.hud.set_boss(None)
            alive = sum(1 for e in self.wave_manager.spawned_enemies if e.alive) if self.wave_manager else 0
            self.hud.set_enemies_remaining(alive, max(alive, 10))
            self.hud.set_wave(
                (self.wave_manager.current_wave_index + 1) if self.wave_manager else 0,
                len(self.wave_manager.waves) if self.wave_manager else 0,
            )
        # State transitions
        if not self.player.alive:
            from stellar_horizon.scenes.game_over import GameOverScene
            self._next = GameOverScene(self.midi_player, score=self.score)
        elif self.boss_active and self.boss and self.boss.phase == "dead":
            from stellar_horizon.scenes.game_over import GameOverScene
            self._next = GameOverScene(self.midi_player, score=self.score, victory=True)

    def draw(self, surface: pygame.Surface) -> None:
        ox, oy = self.shake.offset()
        bg_surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.background.draw(bg_surface)
        surface.blit(bg_surface, (int(ox), int(oy)))
        if self.wave_manager:
            for e in self.wave_manager.spawned_enemies:
                if e.alive:
                    self._draw_placeholder_enemy(surface, e, ox, oy)
        if self.boss_active and self.boss and self.boss.alive:
            self._draw_placeholder_boss(surface, self.boss, ox, oy)
        if self.player.alive:
            self._draw_placeholder_player(surface, self.player, ox, oy)
        for b in self.player_bullets:
            if b.alive:
                pygame.draw.rect(surface, (255, 240, 100),
                                 (int(b.x - 6 + ox), int(b.y - 2 + oy), 12, 4))
        for b in self.enemy_bullets:
            if b.alive:
                pygame.draw.circle(surface, (240, 80, 100),
                                   (int(b.x + ox), int(b.y + oy)), 4)
        self.fx.draw(surface)
        self.hud.draw(surface)

    def next_scene(self):
        return self._next

    def _spawn_boss(self) -> None:
        self.boss = Boss()
        self.boss_active = True
        self.hud.set_boss(self.boss)

    def _draw_placeholder_player(self, surface, p, ox, oy) -> None:
        cx, cy = int(p.x + ox), int(p.y + oy)
        pygame.draw.polygon(surface, (90, 220, 120),
                            [(cx - 6, cy - 5), (cx - 6, cy + 5), (cx + 6, cy)])

    def _draw_placeholder_enemy(self, surface, e, ox, oy) -> None:
        cx, cy = int(e.x + ox), int(e.y + oy)
        if e.kind == "scout":
            color = (220, 60, 60)
        elif e.kind == "cruiser":
            color = (240, 130, 40)
        else:
            color = (180, 180, 200)
        if e.telegraphing:
            color = (255, 240, 100)
        size = 10 if e.kind != "heavy" else 14
        pygame.draw.rect(surface, color, (cx - size // 2, cy - size // 2, size, size))

    def _draw_placeholder_boss(self, surface, b, ox, oy) -> None:
        cx, cy = int(b.x + ox), int(b.y + oy)
        size = 48
        pts = []
        import math
        for i in range(6):
            a = 2 * math.pi * i / 6
            pts.append((cx + int(math.cos(a) * size / 2), cy + int(math.sin(a) * size / 2)))
        pygame.draw.polygon(surface, (160, 140, 110), pts)
        pygame.draw.polygon(surface, (220, 100, 60), pts, 2)
