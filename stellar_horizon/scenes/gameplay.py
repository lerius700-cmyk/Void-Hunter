"""Main gameplay scene: player, waves, boss, HUD, FX, audio."""
from __future__ import annotations

from pathlib import Path

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.audio import sfx
from stellar_horizon.audio.thrusters import ThrusterManager
from stellar_horizon.core.scene_manager import Scene, SceneName
from stellar_horizon.entities.boss import Boss, BossPhase
from stellar_horizon.entities.bullet import EnemyBullet, PlayerBullet
from stellar_horizon.entities.enemy import Enemy
from stellar_horizon.entities.player import Player
from stellar_horizon.entities.powerup import PowerUp, PowerUpKind, roll_enemy_drop
from stellar_horizon.fx.bullet_vfx import compute as compute_bullet_vfx
from stellar_horizon.fx.dust import DustStream
from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.screen_shake import ScreenShake
from stellar_horizon.settings import (
    ENEMY_BULLET_POOL, INTERNAL_W, INTERNAL_H, PLAYER_BULLET_POOL,
)
from stellar_horizon.ui.animated_sprite import AnimatedSprite
from stellar_horizon.ui.backgrounds import Background
from stellar_horizon.ui.hud import Hud
from stellar_horizon.ui.mountains import MountainLayer
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
        # Procedural mountain layers — drawn back to front to fake
        # depth. Each layer scrolls at its own speed (faster = closer).
        # Horizons sit around y=180-210 of the 270-tall playfield so
        # the bottom 60-90 px read as "planet surface below the ship".
        self._mountains: list[MountainLayer] = [
            # Background: low silhouette, slowest scroll, lightest color.
            MountainLayer(horizon_y=200, max_height=32, color=(110, 78, 70),
                          scroll_speed=22.0, seed=11),
            # Midground: medium silhouette + speed.
            MountainLayer(horizon_y=215, max_height=44, color=(78, 50, 50),
                          scroll_speed=40.0, seed=37),
            # Foreground: tallest, fastest, darkest (sits at the bottom).
            MountainLayer(horizon_y=235, max_height=60, color=(45, 28, 35),
                          scroll_speed=62.0, seed=73),
        ]
        # Endless right-to-left dust stream — sells the forward motion.
        self._dust = DustStream(screen_w=INTERNAL_W, screen_h=INTERNAL_H,
                                pool_size=80, spawn_rate=30.0,
                                min_speed=70.0, max_speed=200.0)
        # Per-ship thruster loops (player + 6 enemy kinds) with
        # dynamic compression. The audio engine is lazy-initialized
        # by sfx.engine() so headless tests can run without pygame.mixer.
        self.audio = sfx.engine()
        self.thrusters = ThrusterManager(self.audio)
        # Throttle for the player thruster particle emit.
        self._thrust_timer: float = 0.0
        self.player_bullets: list[PlayerBullet] = [PlayerBullet() for _ in range(PLAYER_BULLET_POOL)]
        self.enemy_bullets: list[EnemyBullet] = [EnemyBullet() for _ in range(ENEMY_BULLET_POOL)]
        # Power-up rings spawned by enemy kills and (rarely) by the
        # boss. Updated + drawn alongside the other entities.
        self.powerups: list[PowerUp] = []
        self.score: int = 0
        self._next: Scene | None = None
        self._keys = None
        # Animated sprite cache — one AnimatedSprite per logical name.
        # Each one loads a horizontal frame strip and cycles through it
        # at ~12 fps. Loaded in on_enter() so headless tests can
        # construct the scene without a display.
        # Lasers are NOT here — they're loaded as single-frame static
        # sprites in self._laser_sprites and animated via code in
        # fx/bullet_vfx.py. See the comment in _load_sprites.
        self._animated: dict = {}
        # Single-frame laser sprites keyed by laser_NN. The draw
        # code (and the HUD selector strip) blits these directly
        # and applies a per-weapon VFX on top (alpha pulse, scale
        # pulse, soft halo).
        self._laser_sprites: dict = {}
        # Per-kind counter used to cycle through enemy sprite variants
        # so consecutive spawns of the same kind look different.
        self._enemy_sprite_idx: dict = {}
        # Set of id(enemy) for enemies whose thruster is currently
        # active. Used by _sync_thrusters() to add/remove thrusters
        # as enemies spawn and die.
        self._managed_enemies: set[int] = set()
        # Boss animation states. Loaded in _load_sprites() — one
        # AnimatedSprite per state (IDLE, TELEGRAPH, CHARGE, DYING),
        # each cycling at 8 fps with 6 frames. _draw_boss_sprite()
        # picks the right one based on boss.phase + boss.action.
        self._boss_anims: dict = {}
        # Scene-time accumulator (seconds since on_enter). Used to
        # drive code-driven VFX (bullet pulses, halo phase) so they
        # stay in sync with the rest of the scene.
        self._elapsed: float = 0.0

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
        # Give the HUD access to the single-frame laser sprites so it
        # can render the weapon selector strip + current-weapon icon.
        # The bullets and the HUD both pull from this same dict.
        self.hud.set_weapon_catalog(self._laser_sprites,
                                    self._WEAPON_NAMES,
                                    self.player.weapon)
        # Reset the scene clock so VFX phases start fresh.
        self._elapsed = 0.0
        # Start the player thruster loop on channel 0. The
        # ThrusterManager handles per-enemy loops in update().
        self.thrusters.set_player("player")

    def _load_sprites(self) -> None:
        """Load animated sprite sheets from assets/sprites/*_sheet.png
        AND single-frame laser sprites from assets/sprites/laser_NN.png.

        Animated sheets (player, enemies, boss, bullets) hold 6 frames
        and cycle at 12 fps for the standard 16-bit look. Lasers are
        loaded as single-frame static sprites because:
        - 6-frame strips for round/heart shapes were inconsistent (the
          model shifted them between frames).
        - The per-weapon VFX (alpha pulse, scale pulse, halo) is more
          controllable in code than baked into frames.
        The result: 32 animated sprites (7 active + 20 enemy + 5
        player) + 10 single-frame laser sprites = 42 total.
        """
        sprite_dir = self.assets_dir / "sprites"
        # All names to load as animated sheets (no laser_NN here).
        animated_names = {
            # Active game assets.
            "player", "scout", "cruiser", "heavy", "boss",
            "player_bullet", "enemy_bullet",
            # 20 enemy variants.
            *[f"enemy_{i:02d}" for i in range(1, 21)],
            # 5 player variants.
            *[f"player_{i:02d}" for i in range(1, 6)],
        }
        # Per-name dimensions for animated sheets.
        anim_dims = {
            "player": (16, 16), "scout": (16, 16), "cruiser": (16, 16),
            "heavy": (16, 16), "boss": (48, 48),
            "player_bullet": (8, 8), "enemy_bullet": (8, 8),
        }
        for n in (f"player_{i:02d}" for i in range(1, 6)):
            anim_dims[n] = (16, 16)
        for n in (f"enemy_{i:02d}" for i in range(1, 21)):
            anim_dims[n] = (16, 16)

        self._animated.clear()
        for name in animated_names:
            w, h = anim_dims.get(name, (16, 16))
            # Skip the legacy "boss" name — replaced by the 4-state
            # boss animation set below.
            if name == "boss":
                continue
            path = sprite_dir / f"{name}_sheet.png"
            self._animated[name] = AnimatedSprite(str(path), w, h, 6,
                                                  fps=12.0)
        # Boss has 4 animations (IDLE, TELEGRAPH, CHARGE, DYING) at
        # 8 fps with 6 frames each. They replace the old single
        # "boss" sheet so the boss now visibly changes pose across
        # its state machine cycle.
        self._boss_anims.clear()
        for state in ("idle", "telegraph", "charge", "dying"):
            path = sprite_dir / f"boss_{state}_sheet.png"
            self._boss_anims[state] = AnimatedSprite(
                str(path), 48, 48, 6, fps=8.0,
            )
        # Single-frame laser sprites — loaded as plain pygame.Surface
        # (no animation). Animation comes from fx/bullet_vfx.compute()
        # at draw time.
        self._laser_sprites.clear()
        for i in range(1, 11):
            name = f"laser_{i:02d}"
            path = sprite_dir / f"{name}.png"
            try:
                # NOTE: convert_alpha() needs a display mode, which
                # isn't set during some headless tests. We try it
                # first (fast, native alpha) and fall back to the
                # raw loaded surface (still has alpha from the PNG
                # but in source format) if no display is up.
                raw = pygame.image.load(str(path))
                try:
                    surf = raw.convert_alpha()
                except pygame.error:
                    surf = raw
            except (pygame.error, FileNotFoundError):
                # Fall back to a 1x1 magenta surface so the bug is
                # visible at a glance.
                surf = pygame.Surface((1, 1), pygame.SRCALPHA)
                surf.fill((255, 0, 255, 255))
            self._laser_sprites[name] = surf

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
        return sprites[idx]

    def _sync_thrusters(self) -> None:
        """Add thrusters for newly-spawned enemies, remove for dead
        ones, and apply the dynamic compressor to the active set.

        Called once per frame from update(). Cheap: O(N enemies) with
        no pygame.mixer calls per enemy (the compressor only touches
        the channel whose volume actually changed).
        """
        if self.wave_manager is None:
            return
        spawned = self.wave_manager.spawned_enemies
        # 1. Add thrusters for NEW enemies (alive=True, not managed).
        for e in spawned:
            if e.alive and id(e) not in self._managed_enemies:
                if self.thrusters.add_enemy(e):
                    self._managed_enemies.add(id(e))
        # 2. Remove thrusters for DEAD/MISSING enemies.
        live_ids = {id(e) for e in spawned if e.alive}
        dead = self._managed_enemies - live_ids
        for eid in dead:
            # Find the enemy object (still in spawned_enemies even
            # if not alive, but maybe already removed by wave_manager).
            target = next((e for e in spawned if id(e) == eid), None)
            if target is not None:
                self.thrusters.remove_enemy(target)
            self._managed_enemies.discard(eid)
        # 3. Apply the dynamic compressor (1/sqrt(N) per active).
        self.thrusters.update()

    def on_exit(self) -> None:
        self.midi_player.fadeout(400)
        # Stop the player thruster + any enemy thrusters. Without
        # this, channels stay reserved and the next scene's mixer
        # usage is wrong.
        self.thrusters.clear_player()

    # Number keys 1-9 and 0 in that order map to weapon indices 0..9
    # so the player can cycle through all 10 laser variants without
    # leaving the home row. The order matches the WEAPON_COOLDOWN_S
    # table in the Player class (1 = yellow plasma, 0 = rainbow).
    _WEAPON_KEYS = (
        pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
        pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9, pygame.K_0,
    )
    _WEAPON_NAMES = (
        "YELLOW PLASMA",
        "RED PULSE",
        "BLUE ION",
        "GREEN ACID",
        "PURPLE VOID",
        "ORANGE FIRE",
        "WHITE PIERCE",
        "PINK HEART",
        "CYAN ICE",
        "RAINBOW",
    )

    def update(self, dt: float, events: list) -> None:
        self._keys = pygame.key.get_pressed()
        self.player.firing = self._keys[pygame.K_SPACE]
        # Advance the scene clock FIRST so any bullets spawned this
        # frame get a spawn_time that's already past `self._elapsed`
        # at the moment they're drawn.
        self._elapsed += dt

        # Number-key weapon switch. KEYDOWN events come from the
        # scene_manager; we walk the events once and pick the LAST
        # matching key (so if the user holds two, the latest wins).
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in self._WEAPON_KEYS:
                new_weapon = self._WEAPON_KEYS.index(ev.key)
                if new_weapon != self.player.weapon:
                    self.player.set_weapon(new_weapon)
                    # Tell the HUD the current weapon changed so the
                    # selector strip re-highlights.
                    self.hud.set_current_weapon(new_weapon)
                    # Small FX: sparks at the player's nose so the
                    # switch has some visible punch.
                    self.fx.emit_impact(self.player.x + 4,
                                        self.player.y, count=6,
                                        color=(255, 220, 100))
        # Player — pool is fixed-size; do NOT filter it (player.update
        # spawns by finding a dead slot, and filtering would shrink
        # the pool until no dead slot exists, blocking new shots).
        self.player.update(dt, self._keys, self.player_bullets,
                           now=self._elapsed)
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
            # Bullet-vs-enemy collision. Each hit emits a punchy spark
            # burst (12 sparks + shrapnel + flash) so the impact reads
            # even on a busy frame. Kills add a bigger explosion.
            for b in self.player_bullets:
                if not b.alive:
                    continue
                for e in self.wave_manager.spawned_enemies:
                    if e.alive and b.hitbox().colliderect(e.hitbox()):
                        # Hit point = midpoint of the two hitboxes.
                        hx = (b.x + e.x) * 0.5
                        hy = (b.y + e.y) * 0.5
                        self.fx.emit_impact(hx, hy, count=12,
                                            color=(255, 240, 100))
                        e.take_damage(1)
                        b.alive = False
                        sfx.play_event("hit")
                        if not e.alive:
                            self.score += e.score_value()
                            scale = 1.0
                            trauma = 0.10
                            kill_sfx = "explode_small"
                            if e.kind in ("heavy", "bomber"):
                                scale = 1.6
                                trauma = 0.22
                                kill_sfx = "explode_medium"
                            if e.kind == "kamikaze":
                                scale = 2.0
                                trauma = 0.30
                                kill_sfx = "explode_medium"
                            self.fx.emit_explosion(e.x, e.y, scale=scale)
                            self.fx.emit_impact(e.x, e.y, count=14,
                                                color=(255, 200, 80))
                            self.shake.add_trauma(trauma)
                            sfx.play_event(kill_sfx)
                            # Power-up drop roll (silver 10%, gold 5%).
                            drop_kind = roll_enemy_drop()
                            if drop_kind is not None:
                                self._spawn_powerup(e.x, e.y, drop_kind)
                        break
            # Enemy-vs-player collision. Kamikaze deals 2 damage (its
            # contact_damage); everything else deals 1. Every contact
            # also gets a spark burst.
            for e in self.wave_manager.spawned_enemies:
                if e.alive and e.hitbox().colliderect(self.player.hitbox()):
                    for _ in range(e.contact_damage):
                        self.player.take_hit()
                    self.shake.add_trauma(0.30 if e.kind == "kamikaze" else 0.20)
                    self.fx.emit_explosion(e.x, e.y, scale=1.4 if e.kind == "kamikaze" else 0.6)
                    self.fx.emit_impact(self.player.x, self.player.y,
                                        count=14,
                                        color=(255, 100, 100))
                    sfx.play_event("explode_small" if e.kind != "kamikaze"
                                   else "explode_medium")
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
                    sfx.play_event("hit")
                    if not self.boss.alive:
                        self.score += self.boss.score_value()
                        self.fx.emit_explosion(self.boss.x, self.boss.y, scale=3.0)
                        self.shake.add_trauma(0.50)
                        sfx.play_event("explode_boss")
            if self.boss.alive and self.boss.hitbox().colliderect(self.player.hitbox()):
                # Boss contact damage = 2 (all boss damage is 2).
                self.player.take_hit(amount=self.boss.DAMAGE_TO_PLAYER)
                self.shake.add_trauma(0.30)
                sfx.play_event("hit")
                # Reset the boss hit-streak — player took damage from
                # the boss, so the 20-in-7 ring drop window is over.
                self.boss.on_player_damaged()
        # Enemy bullets vs player — pool is fixed-size; do NOT filter.
        # Bombs (gravity projectiles) detonate with a bigger impact
        # burst on contact; regular aimed bullets get the standard
        # 10-spark hit feedback.
        for b in self.enemy_bullets:
            if b.alive:
                b.update(dt)
                if b.alive and b.hitbox().colliderect(self.player.hitbox()):
                    # Use the bullet's damage value (boss bullets = 2,
                    # regular enemy bullets = 1).
                    self.player.take_hit(amount=b.damage)
                    b.alive = False
                    self.shake.add_trauma(0.15)
                    if b._bomb:
                        self.fx.emit_impact(self.player.x, self.player.y,
                                            count=16, color=(255, 140, 40))
                        sfx.play_event("bomb")
                    else:
                        self.fx.emit_impact(self.player.x, self.player.y,
                                            count=10, color=(255, 80, 100))
                        sfx.play_event("hit")
                    # If the bullet came from the boss, also tell the
                    # boss the streak is over.
                    if self.boss_active and self.boss is not None \
                            and b.damage >= 2 and not b._bomb:
                        self.boss.on_player_damaged()
        # Power-up rings: update, apply pickup, prune dead.
        for p in self.powerups:
            if p.update(dt, self.player, self._elapsed):
                self._on_powerup_pickup(p)
        self.powerups = [p for p in self.powerups if p.alive]
        # Boss ring drop check (silver, 50% on 20 hits in 7s). Only
        # triggers while the boss is alive in PHASE_1/PHASE_2.
        if (self.boss_active and self.boss is not None
                and self.boss.alive
                and self.boss.phase in (BossPhase.PHASE_1, BossPhase.PHASE_2)):
            if self.boss.consume_ring_drop():
                self._spawn_powerup(self.boss.x, self.boss.y,
                                    PowerUpKind.SILVER)
                self.fx.emit_impact(self.boss.x, self.boss.y,
                                    count=20, color=(220, 230, 255))
                sfx.play_event("explode_small")
        self.fx.update(dt)
        self.shake.update(dt)
        self.background.update(dt, scroll_speed=0.0)
        # Add/remove per-ship thruster loops and apply the dynamic
        # compressor. Must run AFTER enemy spawns/deaths so the
        # managed set is in sync with the live set.
        self._sync_thrusters()
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

        # Scenery tick: mountains scroll + dust drifts + thruster
        # exhaust. Done AFTER game logic so the offsets reflect the
        # physics state of this frame.
        for m in self._mountains:
            m.update(dt)
        self._dust.update(dt)
        # Animation tick: every animated sprite advances one frame.
        # The thruster is now baked into the player sprite sheet, so
        # the old P_FIRE/P_WAKE particle emit is gone — animation
        # alone sells the thrust.
        for sprite in self._animated.values():
            sprite.update(dt)
        # Boss animations tick at 8 fps (independent of the 12 fps
        # the other entities use).
        for boss_anim in self._boss_anims.values():
            boss_anim.update(dt)

    def _emit_thruster(self, dt: float) -> None:
        """No-op kept for backward compatibility.

        The thruster is now baked into the player sprite sheet (one
        of the 6 frames per animation cycle is a bigger flame), so
        no per-frame particle emit is needed. The sheet cycles on
        its own regardless of whether the player is thrusting — the
        flame just looks a bit different in each frame, which is the
        standard 16-bit shmup look.
        """
        return

    def draw(self, surface: pygame.Surface) -> None:
        ox, oy = self.shake.offset()
        bg_surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        self.background.draw(bg_surface)
        surface.blit(bg_surface, (int(ox), int(oy)))
        # Mountain layers (background -> foreground), drawn BEFORE
        # entities so ships and enemies sit IN FRONT of the planet
        # surface.
        for m in self._mountains:
            m.draw(surface, INTERNAL_W)
        # Dust drifts in front of the mountains but behind the ships,
        # so the player reads as the closest object on screen.
        self._dust.draw(surface)
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
        # Power-up rings — drawn after bullets so the magneto pickup
        # effect (sparkle) reads on top of any nearby bullet.
        for p in self.powerups:
            p.draw(surface, self._elapsed)
        self.fx.draw(surface)
        self.hud.draw(surface)

    def next_scene(self):
        return self._next

    def _spawn_boss(self) -> None:
        self.boss = Boss()
        self.boss_active = True
        self.hud.set_boss(self.boss)
        # Boss intro stinger so the player knows the boss is here.
        sfx.play_event("boss_warning")

    def _spawn_powerup(self, x: float, y: float, kind: str) -> None:
        """Add a new power-up ring to the live list."""
        p = PowerUp()
        p.spawn(x, y, kind, self._elapsed)
        self.powerups.append(p)

    def _on_powerup_pickup(self, p: PowerUp) -> None:
        """Apply the picked-up ring's effect to the player and emit
        the appropriate sparkle / SFX.
        """
        if p.kind == PowerUpKind.GOLD:
            stacked = self.player.collect_gold_ring()
            # Heal +2 (or +1 if already at max lives on the current
            # cap; the heal() method caps at max_lives).
            self.player.heal(2)
            # Sparkle: gold burst.
            self.fx.emit_impact(p.x, p.y, count=18, color=(255, 220, 110))
            self.shake.add_trauma(0.08)
            sfx.play_event("hit")  # fallback if no "ring" SFX exists
            if stacked:
                # Extra punch when the cap just grew.
                self.fx.emit_impact(self.player.x, self.player.y,
                                    count=24, color=(255, 240, 180))
                self.shake.add_trauma(0.20)
        else:
            self.player.collect_silver_ring()
            self.fx.emit_impact(p.x, p.y, count=12, color=(220, 230, 255))
            sfx.play_event("hit")

    # ------------------------------------------------------------------
    # Sprite blit helpers — each picks the right animated sprite from
    # self._animated and blits the current frame centered on the
    # entity's position. AnimatedSprite.get_current_surface() returns
    # the frame for the current animation tick. If a sheet failed to
    # load, the helper falls back to a flat color shape so the game
    # still runs.
    # ------------------------------------------------------------------

    def _blit_centered(self, surface, sprite, cx: float, cy: float) -> None:
        if sprite is None:
            return
        rect = sprite.get_rect(center=(int(cx), int(cy)))
        surface.blit(sprite, rect)

    def _draw_player_sprite(self, surface, p, ox, oy) -> None:
        sprite = self._animated.get("player")
        if sprite is None or not sprite.loaded:
            cx, cy = int(p.x + ox), int(p.y + oy)
            pygame.draw.polygon(surface, (90, 220, 120),
                                [(cx - 6, cy - 5), (cx - 6, cy + 5), (cx + 6, cy)])
            return
        self._blit_centered(surface, sprite.get_current_surface(),
                            p.x + ox, p.y + oy)

    def _draw_enemy_sprite(self, surface, e, ox, oy) -> None:
        # Prefer the per-spawn sprite variant (assigned by the wave
        # manager), fall back to the kind's default animated sprite.
        anim = None
        if e.sprite_name:
            anim = self._animated.get(e.sprite_name)
        if anim is None:
            anim = self._animated.get(e.kind)
        sprite = anim.get_current_surface() if anim is not None else None
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
        # Draw the telegraph line BEHIND the boss so the boss sprite
        # sits on top of it (it must read as a warning, not a hitbox).
        if b.action == "telegraph":
            self._draw_boss_telegraph(surface, b, ox, oy)
        # Thruster particles during CHARGE — drawn first so they sit
        # behind the boss sprite, suggesting the boss is moving
        # forward and leaving the trail behind.
        if b.action == "charge":
            self._draw_boss_thruster(surface, b, ox, oy)
        # Pick the right boss animation: 4 states mapped to
        # BossPhase + BossAction.
        state = self._pick_boss_animation(b)
        anim = self._boss_anims.get(state)
        sprite = anim.get_current_surface() if anim is not None else None
        if sprite is None:
            # Fallback to the legacy 6-frame sprite (kept around in
            # self._animated for backward compatibility).
            anim = self._animated.get("boss")
            sprite = anim.get_current_surface() if anim is not None else None
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

    def _pick_boss_animation(self, b) -> str:
        """Map the boss's current state to one of the 4 animations.

        IDLE/RETREAT/COOLDOWN share the idle sheet so the boss
        doesn't need a unique sheet for every sub-state. CHARGE and
        TELEGRAPH get their own. DYING (the boss's death phase)
        overrides everything.
        """
        if b.phase == "dying":
            return "dying"
        if b.action == "charge":
            return "charge"
        if b.action == "telegraph":
            return "telegraph"
        return "idle"

    def _draw_boss_telegraph(self, surface, b, ox, oy) -> None:
        """Bright pulsing horizontal line from boss center to the
        player's current position. Pulses with a 0.6s period.
        """
        import math
        cx1, cy1 = int(b.x + ox), int(b.y + oy)
        cx2, cy2 = int(self.player.x + ox), int(self.player.y + oy)
        # Pulse: 0.3 -> 0.9 alpha over 0.6s. Use scene elapsed time.
        phase = (self._elapsed * 1.6) % 1.0
        alpha = int(76 + 178 * abs(math.sin(phase * math.pi)))
        # Three nested lines for a glow effect.
        for thickness, dim in ((5, 0.35), (3, 0.6), (1, 1.0)):
            line = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            r, g, bl = (255, 90, 60)
            a = int(alpha * dim)
            pygame.draw.line(line, (r, g, bl, a), (cx1, cy1), (cx2, cy2), thickness)
            surface.blit(line, (0, 0))

    def _draw_boss_thruster(self, surface, b, ox, oy) -> None:
        """Trail of bright particles behind the boss during CHARGE.

        The trail is a few ellipses on a per-pixel alpha surface so
        they blend with whatever is behind (mountains, dust, bg).
        Offsets start BEYOND the boss's edge (24 px half-width) so
        the trail is visible past the boss sprite.
        """
        import math
        # Direction: from boss TOWARD the player (charge direction).
        # Trail particles fly in the OPPOSITE direction so the boss
        # appears to be pushing them backward.
        dx = self.player.x - b.x
        dy = self.player.y - b.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        # Offsets start past the boss's 24px half-width (so the trail
        # is clearly outside the sprite) and extend further out.
        for i, offset in enumerate((28, 36, 44, 54, 66)):
            px = b.x - ux * offset + ox
            py = b.y - uy * offset + oy
            # Radius shrinks with distance. Alpha also fades.
            radius = int(7 - i)
            alpha = int(240 - i * 42)
            if radius < 2 or alpha < 20:
                continue
            halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # Bright yellow core.
            pygame.draw.circle(halo, (255, 220, 130, alpha),
                               (radius, radius), radius)
            # Orange rim.
            pygame.draw.circle(halo, (255, 100, 40, min(255, alpha + 20)),
                               (radius, radius), radius, 1)
            surface.blit(halo, (int(px - radius), int(py - radius)))

    def _draw_player_bullet_sprite(self, surface, b, ox, oy) -> None:
        # Use the weapon that fired this bullet (so mid-flight
        # weapon switches don't repaint already-spawned bullets) —
        # fall back to the player's current weapon for legacy bullets.
        weapon_idx = getattr(b, "weapon", self.player.weapon)
        weapon_name = f"laser_{weapon_idx + 1:02d}"
        sprite = self._laser_sprites.get(weapon_name)
        if sprite is None:
            sprite = self._laser_sprites.get("laser_01")
        if sprite is None:
            pygame.draw.rect(surface, (255, 240, 100),
                             (int(b.x - 6 + ox), int(b.y - 2 + oy), 12, 4))
            return
        # Code-driven VFX: alpha pulse, scale pulse, soft halo.
        vfx = compute_bullet_vfx(b, self._elapsed)
        cx, cy = int(b.x + ox), int(b.y + oy)
        # Halo first (behind the sprite). Drawn as a soft circle on a
        # per-pixel alpha surface so it blends with the background.
        if vfx.halo_color is not None and vfx.halo_size > 0 \
                and vfx.halo_alpha > 0:
            rad = vfx.halo_size
            halo = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*vfx.halo_color, vfx.halo_alpha),
                               (rad, rad), rad)
            surface.blit(halo, (cx - rad, cy - rad))
        # Sprite with alpha (and optional scale).
        if vfx.scale != 1.0:
            sw, sh = sprite.get_width(), sprite.get_height()
            nw, nh = max(1, int(round(sw * vfx.scale))), \
                     max(1, int(round(sh * vfx.scale)))
            scaled = pygame.transform.scale(sprite, (nw, nh))
            rect = scaled.get_rect(center=(cx, cy))
            if vfx.alpha < 255:
                scaled.set_alpha(vfx.alpha)
            surface.blit(scaled, rect)
        else:
            rect = sprite.get_rect(center=(cx, cy))
            if vfx.alpha < 255:
                sprite.set_alpha(vfx.alpha)
            surface.blit(sprite, rect)

    def _draw_enemy_bullet_sprite(self, surface, b, ox, oy) -> None:
        # Bomber gravity bombs get a distinct look: a dark red filled
        # circle with a bright orange rim so they read as "heavy ammo".
        if b._bomb:
            cx, cy = int(b.x + ox), int(b.y + oy)
            pygame.draw.circle(surface, (60, 20, 20), (cx, cy), 5)
            pygame.draw.circle(surface, (255, 140, 40), (cx, cy), 5, 1)
            spark_y = cy - 5
            pygame.draw.line(surface, (255, 200, 80), (cx, cy - 3),
                             (cx + ((-1) ** (cy // 4)), spark_y), 1)
            return
        anim = self._animated.get("enemy_bullet")
        sprite = anim.get_current_surface() if anim is not None else None
        if sprite is None:
            pygame.draw.circle(surface, (240, 80, 100),
                               (int(b.x + ox), int(b.y + oy)), 4)
            return
        rect = sprite.get_rect(center=(int(b.x + ox), int(b.y + oy)))
        surface.blit(sprite, rect)
