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


# Maps each enemy kind to a list of sprite names that cycle per spawn.
# Each kind gets 2-3 visually coherent variants from the 20-sprite
# enemy library. The draw code uses the first variant as the default
# (when the cycle hasn't ticked yet) and then rotates.
_ENEMY_SPRITE_CYCLE = {
    "scout":    ("enemy_01", "enemy_07", "enemy_16"),    # red dart, pink destroyer, silver chrome
    "cruiser":  ("enemy_02", "enemy_11", "enemy_13"),    # purple wedge, magenta crystal, bronze golem
    "heavy":    ("enemy_04", "enemy_08", "enemy_14"),    # blue diamond, cyan ghost, teal aquatic
    "bomber":   ("enemy_03", "enemy_17", "enemy_19"),    # orange bomber, gold royal, crimson fanged
    "ufo":      ("enemy_06", "enemy_18"),                # yellow saucer, violet phantom
    "kamikaze": ("enemy_10", "enemy_12", "enemy_15"),    # black stealth, lime insect, coral snake
}


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
        # Sprite cache (loaded once, reused for every draw).
        # Keyed by logical name; the dict is filled in on_enter() so we
        # don't depend on a display being available at construction time
        # (tests construct the scene headless).
        self._sprites: dict = {}
        # Per-kind counter used to cycle through enemy sprite variants
        # so consecutive spawns of the same kind look different.
        self._enemy_sprite_idx: dict = {}

    def on_enter(self) -> None:
        # Load sprites FIRST so the wave manager can pick variants
        # when building each enemy.
        self._load_sprites()
        screen_rect = pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)
        self.player = Player(screen_rect)
        # Pass self._pick_enemy_sprite so each spawn entry gets one
        # sprite variant assigned to all enemies in its formation
        # (5 scouts in a V look like the same ship class).
        self.wave_manager = WaveManager(self.wave_json, sprite_picker=self._pick_enemy_sprite)
        self.wave_manager.begin()
        self.background = Background(self.assets_dir / "backgrounds" / f"{self.wave_manager.background}.png")
        self.midi_player.play(str(self.assets_dir / "midi" / self.wave_manager.midi_track), loop=True)
        self.hud.set_player(self.player)
        self.hud.set_wave(1, len(self.wave_manager.waves))
        self.hud.set_enemies_remaining(0, 0)

    def _load_sprites(self) -> None:
        """Load 16-bit pixel-art sprites from assets/sprites/.

        Loads the 7 active game assets plus the 20 enemy / 5 player /
        10 laser variants. Each enemy kind cycles through its assigned
        sprite list (see _ENEMY_SPRITE_CYCLE) so spawns look varied.
        """
        sprite_dir = self.assets_dir / "sprites"
        names = [
            # Active game assets.
            "player", "scout", "cruiser", "heavy", "boss",
            "player_bullet", "enemy_bullet",
            # 20 enemy variants (cycle per kind).
            *[f"enemy_{i:02d}" for i in range(1, 21)],
            # 5 player variants.
            *[f"player_{i:02d}" for i in range(1, 6)],
            # 10 laser variants.
            *[f"laser_{i:02d}" for i in range(1, 11)],
        ]
        self._sprites.clear()
        for name in names:
            path = sprite_dir / f"{name}.png"
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                self._sprites[name] = img
            except (pygame.error, FileNotFoundError):
                # Leave the slot missing; draw code will fall back to a
                # simple shape so the game still runs if a sprite is gone.
                self._sprites[name] = None

    def _pick_enemy_sprite(self, kind: str) -> str | None:
        """Return a sprite name for an enemy of the given kind.

        Each kind cycles through a curated list of variants so spawns
        look visually varied. A per-scene counter avoids the same
        sprite showing up twice in a row within a kind.
        """
        sprites = _ENEMY_SPRITE_CYCLE.get(kind, ())
        if not sprites:
            return None
        idx = self._enemy_sprite_idx.get(kind, 0) % len(sprites)
        self._enemy_sprite_idx[kind] = idx + 1
        name = sprites[idx]
        return name if self._sprites.get(name) else None

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)

    def update(self, dt: float, events: list) -> None:
        self._keys = pygame.key.get_pressed()
        self.player.firing = self._keys[pygame.K_SPACE]
        # Player — pool is fixed-size; do NOT filter it (player.update
        # spawns by finding a dead slot, and filtering would shrink
        # the pool until no dead slot exists, blocking new shots).
        self.player.update(dt, self._keys, self.player_bullets)
        for b in self.player_bullets:
            if b.alive:
                b.update(dt)
        # Wave manager + enemies
        if self.wave_manager and not self.boss_active:
            self.wave_manager.update(dt)
            for e in self.wave_manager.spawned_enemies:
                new_bullets = e.update(dt, self.player)
                for nb in new_bullets:
                    # Route the bullet into the enemy_bullets pool. The
                    # spawner sets nb._bomb on bomber gravity bombs; we
                    # copy that flag across so the pool entry keeps the
                    # gravity behavior in EnemyBullet.update.
                    for slot in self.enemy_bullets:
                        if not slot.alive:
                            slot.x, slot.y, slot.vx, slot.vy, slot.alive = (
                                nb.x, nb.y, nb.vx, nb.vy, True
                            )
                            slot.speed_mult = nb.speed_mult
                            slot._bomb = nb._bomb
                            slot.damage = nb.damage
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
                            # Bigger boom + shake for bigger enemies.
                            scale = 1.0
                            trauma = 0.10
                            if e.kind in ("heavy", "bomber"):
                                scale = 1.6
                                trauma = 0.22
                            if e.kind == "kamikaze":
                                scale = 2.0
                                trauma = 0.30
                            self.fx.emit_explosion(e.x, e.y, scale=scale)
                            self.shake.add_trauma(trauma)
                        break
            # Enemy-vs-player collision. Kamikaze deals 2 damage (its
            # contact_damage); everything else deals 1.
            for e in self.wave_manager.spawned_enemies:
                if e.alive and e.hitbox().colliderect(self.player.hitbox()):
                    for _ in range(e.contact_damage):
                        self.player.take_hit()
                    self.shake.add_trauma(0.30 if e.kind == "kamikaze" else 0.20)
                    self.fx.emit_explosion(e.x, e.y, scale=1.4 if e.kind == "kamikaze" else 0.6)
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
        # Enemy bullets vs player — pool is fixed-size; do NOT filter.
        for b in self.enemy_bullets:
            if b.alive:
                b.update(dt)
                if b.alive and b.hitbox().colliderect(self.player.hitbox()):
                    self.player.take_hit()
                    b.alive = False
                    self.shake.add_trauma(0.15)
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
                    self._draw_enemy_sprite(surface, e, ox, oy)
        if self.boss_active and self.boss and self.boss.alive:
            self._draw_boss_sprite(surface, self.boss, ox, oy)
        if self.player.alive:
            self._draw_player_sprite(surface, self.player, ox, oy)
        for b in self.player_bullets:
            if b.alive:
                self._draw_player_bullet_sprite(surface, b, ox, oy)
        for b in self.enemy_bullets:
            if b.alive:
                self._draw_enemy_bullet_sprite(surface, b, ox, oy)
        self.fx.draw(surface)
        self.hud.draw(surface)

    def next_scene(self):
        return self._next

    def _spawn_boss(self) -> None:
        self.boss = Boss()
        self.boss_active = True
        self.hud.set_boss(self.boss)

    # ------------------------------------------------------------------
    # Sprite blit helpers — each picks the right sprite from
    # self._sprites and centers it on the entity's position. If a
    # sprite failed to load, the helper falls back to a flat color shape
    # so the game still runs.
    # ------------------------------------------------------------------

    def _blit_centered(self, surface, sprite, cx: float, cy: float) -> None:
        if sprite is None:
            return
        rect = sprite.get_rect(center=(int(cx), int(cy)))
        surface.blit(sprite, rect)

    def _draw_player_sprite(self, surface, p, ox, oy) -> None:
        sprite = self._sprites.get("player")
        if sprite is None:
            cx, cy = int(p.x + ox), int(p.y + oy)
            pygame.draw.polygon(surface, (90, 220, 120),
                                [(cx - 6, cy - 5), (cx - 6, cy + 5), (cx + 6, cy)])
            return
        self._blit_centered(surface, sprite, p.x + ox, p.y + oy)

    def _draw_enemy_sprite(self, surface, e, ox, oy) -> None:
        # Prefer the per-spawn sprite variant (assigned by the wave
        # manager), fall back to the kind's default sprite if missing.
        sprite = None
        if e.sprite_name:
            sprite = self._sprites.get(e.sprite_name)
        if sprite is None:
            sprite = self._sprites.get(e.kind)
        if sprite is None:
            cx, cy = int(e.x + ox), int(e.y + oy)
            color = (220, 60, 60) if e.kind == "scout" else \
                    (240, 130, 40) if e.kind == "cruiser" else \
                    (180, 180, 200) if e.kind == "heavy" else \
                    (255, 180, 60) if e.kind == "bomber" else \
                    (200, 240, 100) if e.kind == "ufo" else \
                    (255, 100, 100)
            if e.telegraphing:
                color = (255, 240, 100)
            size = 14 if e.kind in ("heavy", "bomber") else 10
            pygame.draw.rect(surface, color, (cx - size // 2, cy - size // 2, size, size))
            return
        self._blit_centered(surface, sprite, e.x + ox, e.y + oy)
        # Telegraph flash: a soft yellow halo behind the sprite when
        # the enemy is about to fire. Drawn AFTER the sprite so the
        # halo frames the silhouette.
        if e.telegraphing:
            cx, cy = int(e.x + ox), int(e.y + oy)
            radius = max(8, sprite.get_width() // 2 + 3)
            halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 240, 100, 70), (radius, radius), radius)
            surface.blit(halo, (cx - radius, cy - radius))
        # Kamikaze: red warning flash while it's charging toward the
        # player (gives a moment to dodge).
        if e.kind == "kamikaze":
            cx, cy = int(e.x + ox), int(e.y + oy)
            pulse = (pygame.time.get_ticks() // 80) % 2
            if pulse:
                radius = max(8, sprite.get_width() // 2 + 4)
                halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(halo, (255, 60, 60, 90), (radius, radius), radius)
                surface.blit(halo, (cx - radius, cy - radius))

    def _draw_boss_sprite(self, surface, b, ox, oy) -> None:
        sprite = self._sprites.get("boss")
        if sprite is None:
            cx, cy = int(b.x + ox), int(b.y + oy)
            import math
            pts = []
            for i in range(6):
                a = 2 * math.pi * i / 6
                pts.append((cx + int(math.cos(a) * 24), cy + int(math.sin(a) * 24)))
            pygame.draw.polygon(surface, (160, 140, 110), pts)
            pygame.draw.polygon(surface, (220, 100, 60), pts, 2)
            return
        self._blit_centered(surface, sprite, b.x + ox, b.y + oy)

    def _draw_player_bullet_sprite(self, surface, b, ox, oy) -> None:
        sprite = self._sprites.get("player_bullet")
        if sprite is None:
            pygame.draw.rect(surface, (255, 240, 100),
                             (int(b.x - 6 + ox), int(b.y - 2 + oy), 12, 4))
            return
        rect = sprite.get_rect(center=(int(b.x + ox), int(b.y + oy)))
        surface.blit(sprite, rect)

    def _draw_enemy_bullet_sprite(self, surface, b, ox, oy) -> None:
        # Bomber gravity bombs get a distinct look: a dark red filled
        # circle with a bright orange rim so they read as "heavy ammo".
        if b._bomb:
            cx, cy = int(b.x + ox), int(b.y + oy)
            pygame.draw.circle(surface, (60, 20, 20), (cx, cy), 5)
            pygame.draw.circle(surface, (255, 140, 40), (cx, cy), 5, 1)
            # Small fuse spark above the bomb.
            spark_y = cy - 5
            pygame.draw.line(surface, (255, 200, 80), (cx, cy - 3),
                             (cx + ((-1) ** (cy // 4)), spark_y), 1)
            return
        sprite = self._sprites.get("enemy_bullet")
        if sprite is None:
            pygame.draw.circle(surface, (240, 80, 100),
                               (int(b.x + ox), int(b.y + oy)), 4)
            return
        rect = sprite.get_rect(center=(int(b.x + ox), int(b.y + oy)))
        surface.blit(sprite, rect)
