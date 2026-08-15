"""Concrete scenes for the 9 game states (BLOQUE 14).

All fonts are sized for the 240x360 internal surface (the screen is
scaled 4x to 960x1440 by Game._present). 240px width is the hard cap.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional
import math
import random
import sys
from pathlib import Path

import pygame

from src.core.scene_manager import GameState, Scene
from src.core.settings import INTERNAL_H, INTERNAL_W
from src.utils.palette import PALETTE


# Type alias for scene constructor
TransitionFn = Callable[[GameState], None]

if TYPE_CHECKING:
    from src.audio.synth import AudioEngine
    from src.systems.parallax import ParallaxBackground


# BLOQUE 58.45: title-screen enemy sprite dispatcher.
# Maps each EnemyKind value to the title scene's procedural ship
# drawing function. Used by TitleScene._draw_demo_ships when atlas
# sprites aren't bundled (i.e. when running from the .exe).
_ENEMY_DRAWERS: dict[str, Any] = {}  # populated below once the
# TitleScene class is defined; the values are bound methods.

# BLOQUE 58.47: path resolver for the pre-rendered ship sprite PNGs.
# Same logic as src.audio.music._find_assets_dir — probes
# <_MEIPASS>/Assets/sprites/, <exe_dir>/Assets/sprites/, etc.
_sprite_cache: dict[str, pygame.Surface] = {}


def _find_sprites_dir() -> Optional[Path]:
    """Locate the Assets/sprites/ directory containing ship PNGs."""
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_p = Path(meipass)
        candidates.append(meipass_p / "Assets" / "sprites")
        candidates.append(meipass_p / "_internal" / "Assets" / "sprites")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent.parent
    candidates.append(exe_dir / "Assets" / "sprites")
    candidates.append(exe_dir / "_internal" / "Assets" / "sprites")
    candidates.append(exe_dir.parent / "Assets" / "sprites")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _load_sprite(name: str) -> Optional[pygame.Surface]:
    """Load a pre-rendered ship sprite from Assets/sprites/.

    Returns the Surface (with alpha preserved) or None if not found.
    Results are cached in `_sprite_cache` so we only load each file once.
    """
    if name in _sprite_cache:
        return _sprite_cache[name]
    sprites_dir = _find_sprites_dir()
    if sprites_dir is None:
        return None
    path = sprites_dir / name
    if not path.is_file():
        return None
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None
    _sprite_cache[name] = surf
    return surf


# Map enemy kind value → sprite PNG filename (BLOQUE 58.47)
_ENEMY_SPRITE_FILES: dict[str, str] = {
    "scout":    "enemy_scout.png",
    "cruiser":  "enemy_cruiser.png",
    "heavy":    "enemy_heavy.png",
    "kamikaze": "enemy_kamikaze.png",
    "drone":    "enemy_drone.png",
    "sniper":   "enemy_sniper.png",
    "turret":   "enemy_turret.png",
}


def _center_blit(
    target: pygame.Surface,
    text_surface: pygame.Surface,
    y: int,
) -> None:
    """Blit a surface centered horizontally at the given y on target."""
    x = target.get_width() // 2 - text_surface.get_width() // 2
    target.blit(text_surface, (x, y))


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap text to fit max_width, breaking on spaces or at hard char limits."""
    if font.size(text)[0] <= max_width:
        return [text]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Hard-break words longer than max_width
            while font.size(word)[0] > max_width and len(word) > 1:
                # Binary search largest prefix that fits
                lo, hi = 1, len(word)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if font.size(word[:mid])[0] <= max_width:
                        lo = mid
                    else:
                        hi = mid - 1
                lines.append(word[:lo])
                word = word[lo:]
            current = word
    if current:
        lines.append(current)
    return lines


class TitleScene(Scene):
    """BLOQUE 58.41: TITLE — animated background with ships fighting,
    just the logo + 'PRESS ANY KEY' overlay. Controls are gone (moved
    to the Pause scene for an interactive reference).

    Background runs a small demo loop:
      - ParallaxBackground starfield
      - 2 enemy ships + 1 player ship flying across the screen
      - Projectiles between them
      - Occasional explosions (death)
    """

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        # Background demo
        self._bg: Optional[ParallaxBackground] = None
        self._demo_ships: list[_TitleDemoShip] = []
        self._demo_bullets: list[_TitleDemoBullet] = []
        self._demo_explosions: list[_TitleDemoExplosion] = []
        self._demo_rng: random.Random = random.Random(0xCAFE2026)
        self._next_shoot: float = 0.0
        self._next_explode: float = 1.5

    def on_enter(self) -> None:
        self._t = 0.0
        # Init background + demo entities
        from src.systems.parallax import ParallaxBackground
        self._bg = ParallaxBackground(rng_seed=0xCAFE2026)
        self._demo_ships.clear()
        self._demo_bullets.clear()
        self._demo_explosions.clear()
        # Spawn initial ships
        for _ in range(3):
            self._spawn_demo_ship()
        # BLOQUE 58.45: play the title-screen track on loop.
        from src.audio import music
        # BLOQUE 58.57: diagnostic to confirm on_enter is reached
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write("TitleScene.on_enter() reached\n")
                _f.write(f"  calling music.play_title_music()\n")
        except Exception:
            pass
        ok = music.play_title_music()
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write(f"  play_title_music() returned: {ok}\n")
        except Exception:
            pass
        # BLOQUE 58.58: title-screen voice clip removed per user request
        # (was: "Pantalla principal" SAPI announcement). The other voice
        # clips (gameplay / jefe / act_cleared) stay — they fire mid-game
        # and help the player know which phase is starting. Title screen
        # already has its own BGM; the redundant announcement was noise.

    def _spawn_demo_ship(self) -> None:
        """Spawn an enemy or player demo ship on the left or right side."""
        from src.entities.enemies.enemy import EnemyKind
        # Player ship (small) flying up-right or down-left
        is_player = (len(self._demo_ships) % 3 == 0)
        if is_player:
            from_left = self._demo_rng.random() < 0.5
            x = -16.0 if from_left else INTERNAL_W + 16.0
            y = self._demo_rng.uniform(40, INTERNAL_H - 40)
            vx = 60.0 if from_left else -60.0
            vy = (self._demo_rng.random() - 0.5) * 30.0
            self._demo_ships.append(_TitleDemoShip(
                x=x, y=y, vx=vx, vy=vy,
                kind="player", angle_deg=0.0,
                health=1, fire_cd=self._demo_rng.uniform(0.5, 2.0),
            ))
        else:
            enemy_kinds = [
                (EnemyKind.SCOUT, (12, 8)),
                (EnemyKind.CRUISER, (14, 10)),
                (EnemyKind.DRONE, (8, 8)),
                (EnemyKind.KAMIKAZE, (10, 10)),
            ]
            kind, size = self._demo_rng.choice(enemy_kinds)
            x = self._demo_rng.uniform(20, INTERNAL_W - 20)
            y = -16.0
            vx = (self._demo_rng.random() - 0.5) * 20.0
            vy = self._demo_rng.uniform(40, 70)
            self._demo_ships.append(_TitleDemoShip(
                x=x, y=y, vx=vx, vy=vy,
                kind="enemy", enemy_kind=kind, size=size,
                health=1, fire_cd=self._demo_rng.uniform(1.0, 3.0),
            ))

    def _spawn_demo_bullet(self, x: float, y: float, vx: float, vy: float,
                            color: tuple[int, int, int]) -> None:
        self._demo_bullets.append(_TitleDemoBullet(
            x=x, y=y, vx=vx, vy=vy, color=color, life=2.0,
        ))

    def _spawn_demo_explosion(self, x: float, y: float) -> None:
        # 8-12 particles
        for _ in range(self._demo_rng.randint(8, 12)):
            a = self._demo_rng.uniform(0, 6.28)
            speed = self._demo_rng.uniform(40, 100)
            self._demo_explosions.append(_TitleDemoExplosion(
                x=x, y=y,
                vx=math.cos(a) * speed,
                vy=math.sin(a) * speed,
                life=self._demo_rng.uniform(0.4, 0.8),
                color=(255, 200, 100) if self._demo_rng.random() < 0.5 else (255, 100, 80),
            ))

    def update(self, dt: float) -> None:
        self._t += dt
        # Background
        if self._bg is not None:
            self._bg.update(dt)
        # Update ships
        for ship in self._demo_ships:
            ship.x += ship.vx * dt
            ship.y += ship.vy * dt
            ship.fire_cd -= dt
        # Remove off-screen ships + maybe respawn
        kept = []
        for ship in self._demo_ships:
            if -20 <= ship.x <= INTERNAL_W + 20 and -20 <= ship.y <= INTERNAL_H + 20:
                kept.append(ship)
            else:
                # Spawn an explosion + a new ship elsewhere
                self._spawn_demo_explosion(ship.x, ship.y)
        self._demo_ships = kept
        while len(self._demo_ships) < 3:
            self._spawn_demo_ship()
        # Ships shoot
        for ship in self._demo_ships:
            if ship.fire_cd <= 0.0:
                ship.fire_cd = self._demo_rng.uniform(0.8, 2.5)
                if ship.kind == "player":
                    # Player shoots UP (toward enemies)
                    self._spawn_demo_bullet(ship.x, ship.y - 6, 0, -200, (255, 220, 100))
                else:
                    # Enemy shoots DOWN
                    self._spawn_demo_bullet(ship.x, ship.y + 4,
                                              (self._demo_rng.random() - 0.5) * 40,
                                              150, (255, 100, 100))
        # Update bullets
        for b in self._demo_bullets:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt
        self._demo_bullets = [b for b in self._demo_bullets if b.life > 0 and
                              -10 <= b.x <= INTERNAL_W + 10 and
                              -10 <= b.y <= INTERNAL_H + 10]
        # Update explosions
        for e in self._demo_explosions:
            e.x += e.vx * dt
            e.y += e.vy * dt
            e.life -= dt
        self._demo_explosions = [e for e in self._demo_explosions if e.life > 0]
        # Random ambient explosion every few seconds (for visual interest)
        if self._t > self._next_explode:
            self._next_explode = self._t + self._demo_rng.uniform(2.5, 5.0)
            x = self._demo_rng.uniform(40, INTERNAL_W - 40)
            y = self._demo_rng.uniform(40, INTERNAL_H - 40)
            self._spawn_demo_explosion(x, y)
        # Any key / click → start
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (
                pygame.K_LSHIFT, pygame.K_RSHIFT,
                pygame.K_LCTRL, pygame.K_RCTRL,
                pygame.K_LALT, pygame.K_RALT,
            ):
                continue
            self._transition_to(GameState.ACT_INTRO)
            return
        for event in pygame.event.get(pygame.MOUSEBUTTONDOWN):
            self._transition_to(GameState.ACT_INTRO)
            return

    def draw(self, target: pygame.Surface) -> None:
        # Background (parallax starfield)
        if self._bg is not None:
            self._bg.draw(target)
        else:
            target.fill((0, 0, 0))
        # Explosions (behind ships)
        self._draw_demo_explosions(target)
        # Ships
        self._draw_demo_ships(target)
        # Bullets (on top of ships)
        self._draw_demo_bullets(target)
        # Title — big + bold
        font = pygame.font.Font(None, 32)
        title = font.render("VOID HUNTER", True, (220, 220, 255))
        _center_blit(target, title, 100)
        # Subtle subtitle (just the prompt, blinks)
        font2 = pygame.font.Font(None, 14)
        sub = font2.render("PRESS ANY KEY TO START", True, (255, 240, 140))
        if int(self._t * 2) % 2 == 0:
            _center_blit(target, sub, 200)
        # Tiny credits hint (corner, not center)
        credits = font2.render("C: CREDITS", True, (80, 80, 100))
        target.blit(credits, (INTERNAL_W - credits.get_width() - 4,
                              INTERNAL_H - credits.get_height() - 2))

    def _draw_demo_ships(self, target: pygame.Surface) -> None:
        """BLOQUE 58.47: draw demo ships using the REAL ship sprites
        from `Assets/sprites/` (the same PNGs that the gameplay forge
        generates for the player + enemy ships).

        Previously this drew simplified procedural versions (~14x8 px)
        and scaled them 2.5x, which still looked like little colored
        dots. Now we load the pre-rendered PNGs (28x26 player, 13-24
        for enemies) and scale them by TITLE_SHIP_SCALE so the title
        screen shows the same recognizable Arwing-style spaceships the
        player sees in gameplay.

        BLOQUE 58.52: rotate each ship to match its velocity direction
        so the nose/tip points WHERE the ship is moving. Previously the
        player ship moved horizontally (vx=±60) but its sprite pointed
        UP, making it look like it was flying sideways. Now we compute
        the angle from the velocity vector and apply pygame.transform.
        rotate to align the nose with motion.

        Falls back to the procedural drawers if the sprite PNGs are
        missing (e.g. running from source without the bundle).
        """
        # BLOQUE 58.47: scale factor for title screen ships. The base
        # sprites are 13-28 px; SCALE=3.0 makes them ~40-85 px, big
        # enough to be clearly recognizable spaceships.
        scale = getattr(self, "_title_ship_scale", 3.0)
        for ship in self._demo_ships:
            cx, cy = int(ship.x), int(ship.y)
            # Pick the right sprite PNG
            if ship.kind == "player":
                # Alternate between IDLE and PROPULSION based on velocity
                # for visual variety (fast ship = propulsion sprite).
                if abs(ship.vx) + abs(ship.vy) > 60.0:
                    sprite_name = "player_propulsion.png"
                else:
                    sprite_name = "player_idle.png"
            else:
                kind = ship.enemy_kind
                key = kind.value if hasattr(kind, "value") else str(kind)
                sprite_name = _ENEMY_SPRITE_FILES.get(key, "")
            sprite = _load_sprite(sprite_name) if sprite_name else None
            # BLOQUE 58.52: compute rotation from velocity so the ship's
            # TIP/NOSE points in the direction it's moving. Convention
            # (matches gameplay): 0°=up, 90°=right, 180°=down, 270°=left.
            # pygame.transform.rotate is CCW, so we negate the angle.
            import math
            nose_angle_deg = math.degrees(math.atan2(ship.vx, -ship.vy)) % 360.0
            rot_deg = -nose_angle_deg
            if sprite is not None:
                # Rotate first, then scale (so the resulting image is
                # cleaner than scaling-then-rotating).
                if abs(rot_deg) > 0.5:
                    sprite = pygame.transform.rotate(sprite, rot_deg)
                w, h = sprite.get_size()
                scaled = pygame.transform.scale(
                    sprite, (int(w * scale), int(h * scale)),
                )
                blit_x = int(cx - scaled.get_width() / 2)
                blit_y = int(cy - scaled.get_height() / 2)
                target.blit(scaled, (blit_x, blit_y))
            else:
                # Fallback: scratch + procedural (in case PNGs missing)
                scratch_size = 64
                scratch = pygame.Surface((scratch_size, scratch_size), pygame.SRCALPHA)
                mid = scratch_size // 2
                if ship.kind == "player":
                    self._draw_player_ship(scratch, mid, mid, ship)
                else:
                    kind = ship.enemy_kind
                    key = kind.value if hasattr(kind, "value") else str(kind)
                    drawer = _ENEMY_DRAWERS.get(key)
                    if drawer is not None:
                        drawer(self, scratch, mid, mid, ship)
                    else:
                        self._draw_enemy_fallback(scratch, mid, mid, ship)
                if abs(rot_deg) > 0.5:
                    scratch = pygame.transform.rotate(scratch, rot_deg)
                scaled = pygame.transform.scale(
                    scratch, (int(scratch_size * scale), int(scratch_size * scale)),
                )
                blit_x = int(cx - (scratch_size * scale) / 2)
                blit_y = int(cy - (scratch_size * scale) / 2)
                target.blit(scaled, (blit_x, blit_y))

    # ----- BLOQUE 58.45: procedural ship sprites for the title demo -----
    def _draw_player_ship(self, target: pygame.Surface,
                           cx: int, cy: int, ship: "_TitleDemoShip") -> None:
        """Player Arwing sprite: cyan/white delta wing with 2 engines.
        Oriented by the ship's horizontal velocity direction (left/right).
        """
        facing_right = ship.vx >= 0
        # Body color
        body_main = (210, 230, 250)
        body_dark = (60, 80, 110)
        canopy = (140, 200, 255)
        engine = (255, 220, 140)
        # Body
        pygame.draw.polygon(target, body_dark, [
            (cx, cy - 4),                       # nose
            (cx + (5 if facing_right else -5), cy - 1),  # shoulder
            (cx + (5 if facing_right else -5), cy + 1),
            (cx, cy + 4),                       # tail
            (cx + (-5 if facing_right else 5), cy + 1),
            (cx + (-5 if facing_right else 5), cy - 1),
        ])
        # Wings (delta silhouette)
        wing_y_top = cy - 2
        wing_y_bot = cy + 2
        wing_x_out = 7 if facing_right else -7
        pygame.draw.polygon(target, body_main, [
            (cx, wing_y_top),
            (cx + wing_x_out, wing_y_top + 1),
            (cx + wing_x_out, wing_y_bot - 1),
            (cx, wing_y_bot),
        ])
        # Canopy
        pygame.draw.circle(target, canopy, (cx, cy - 1), 1)
        # Engines
        eng_x_back = -3 if facing_right else 3
        pygame.draw.circle(target, engine, (cx + eng_x_back, cy + 3), 1)
        pygame.draw.circle(target, (255, 100, 50), (cx + eng_x_back, cy + 3), 0)

    def _draw_enemy_fallback(self, target: pygame.Surface,
                              cx: int, cy: int, ship: "_TitleDemoShip") -> None:
        """Used when an enemy kind has no specific drawer."""
        pygame.draw.polygon(target, (200, 100, 100), [
            (cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy),
        ])

    def _draw_enemy_scout(self, target: pygame.Surface, cx: int, cy: int,
                          ship: "_TitleDemoShip") -> None:
        """SCOUT: small cyan dart, pointed nose."""
        facing_right = ship.vx >= 0
        col = (80, 220, 240)
        dark = (30, 90, 110)
        # Dart body
        pygame.draw.polygon(target, dark, [
            (cx, cy - 4),
            (cx + (4 if facing_right else -4), cy),
            (cx, cy + 4),
            (cx + (-2 if facing_right else 2), cy),
        ])
        pygame.draw.polygon(target, col, [
            (cx, cy - 3),
            (cx + (3 if facing_right else -3), cy),
            (cx, cy + 3),
            (cx + (-1 if facing_right else 1), cy),
        ])
        # Eye
        pygame.draw.circle(target, (255, 255, 200), (cx, cy), 0)

    def _draw_enemy_cruiser(self, target: pygame.Surface, cx: int, cy: int,
                            ship: "_TitleDemoShip") -> None:
        """CRUISER: green delta wing with side guns."""
        facing_right = ship.vx >= 0
        col = (100, 220, 100)
        dark = (40, 90, 40)
        # Body
        pygame.draw.polygon(target, dark, [
            (cx, cy - 5),
            (cx + (5 if facing_right else -5), cy - 2),
            (cx + (5 if facing_right else -5), cy + 2),
            (cx, cy + 5),
            (cx + (-5 if facing_right else 5), cy + 2),
            (cx + (-5 if facing_right else 5), cy - 2),
        ])
        # Wings
        pygame.draw.polygon(target, col, [
            (cx, cy - 3),
            (cx + (6 if facing_right else -6), cy - 1),
            (cx + (6 if facing_right else -6), cy + 1),
            (cx, cy + 3),
        ])
        # Side guns
        for side in (-1, 1):
            gx = cx + (6 if facing_right else -6)
            pygame.draw.rect(target, (60, 60, 70),
                              (gx, cy - 2, 3 if facing_right else -3, 4))
        # Eye
        pygame.draw.circle(target, (255, 240, 100), (cx, cy), 1)

    def _draw_enemy_heavy(self, target: pygame.Surface, cx: int, cy: int,
                          ship: "_TitleDemoShip") -> None:
        """HEAVY: red armored delta wing."""
        facing_right = ship.vx >= 0
        col = (220, 60, 70)
        dark = (120, 20, 30)
        # Body
        pygame.draw.polygon(target, dark, [
            (cx, cy - 5),
            (cx + (4 if facing_right else -4), cy - 3),
            (cx + (4 if facing_right else -4), cy + 3),
            (cx, cy + 5),
            (cx + (-4 if facing_right else 4), cy + 3),
            (cx + (-4 if facing_right else 4), cy - 3),
        ])
        # Wings (wider, armored)
        pygame.draw.polygon(target, col, [
            (cx, cy - 4),
            (cx + (7 if facing_right else -7), cy - 2),
            (cx + (7 if facing_right else -7), cy + 2),
            (cx, cy + 4),
        ])
        # Heavy outline
        pygame.draw.rect(target, (80, 10, 10), (cx - 1, cy - 1, 2, 2))
        # Eye
        pygame.draw.circle(target, (255, 200, 80), (cx, cy), 1)

    def _draw_enemy_kamikaze(self, target: pygame.Surface, cx: int, cy: int,
                             ship: "_TitleDemoShip") -> None:
        """KAMIKAZE: orange delta with bright flame trail."""
        facing_right = ship.vx >= 0
        col = (255, 140, 50)
        dark = (160, 70, 20)
        # Body
        pygame.draw.polygon(target, dark, [
            (cx, cy - 4),
            (cx + (5 if facing_right else -5), cy - 2),
            (cx + (5 if facing_right else -5), cy + 2),
            (cx, cy + 4),
        ])
        # Bright orange
        pygame.draw.polygon(target, col, [
            (cx, cy - 3),
            (cx + (4 if facing_right else -4), cy - 1),
            (cx + (4 if facing_right else -4), cy + 1),
            (cx, cy + 3),
        ])
        # Flame trail behind
        flame_x = -4 if facing_right else 4
        for i in range(3):
            pygame.draw.circle(target, (255, 200, 50),
                              (cx + flame_x - (flame_x // 2) * i, cy), 2 - i)

    def _draw_enemy_drone(self, target: pygame.Surface, cx: int, cy: int,
                          ship: "_TitleDemoShip") -> None:
        """DRONE: small cyan round."""
        # Body
        pygame.draw.circle(target, (30, 60, 90), (cx, cy), 4)
        pygame.draw.circle(target, (80, 200, 255), (cx, cy), 3)
        # Eye
        pygame.draw.circle(target, (255, 255, 200), (cx, cy), 1)
        # Ring outline
        pygame.draw.circle(target, (140, 230, 255), (cx, cy), 4, 1)

    def _draw_enemy_sniper(self, target: pygame.Surface, cx: int, cy: int,
                           ship: "_TitleDemoShip") -> None:
        """SNIPER: blue elongated with long cannon."""
        facing_right = ship.vx >= 0
        col = (100, 160, 255)
        dark = (30, 60, 130)
        # Elongated body
        pygame.draw.polygon(target, dark, [
            (cx, cy - 2),
            (cx + (6 if facing_right else -6), cy - 1),
            (cx + (6 if facing_right else -6), cy + 1),
            (cx, cy + 2),
            (cx + (-4 if facing_right else 4), cy + 1),
            (cx + (-4 if facing_right else 4), cy - 1),
        ])
        # Body
        pygame.draw.polygon(target, col, [
            (cx, cy - 1),
            (cx + (5 if facing_right else -5), cy),
            (cx + (-3 if facing_right else 3), cy),
        ])
        # Long cannon (extends from nose)
        cnx = cx + (7 if facing_right else -7)
        pygame.draw.line(target, (60, 60, 80),
                          (cnx, cy), (cx + (12 if facing_right else -12), cy), 1)
        # Eye
        pygame.draw.circle(target, (255, 100, 100), (cx, cy), 1)

    def _draw_enemy_turret(self, target: pygame.Surface, cx: int, cy: int,
                           ship: "_TitleDemoShip") -> None:
        """TURRET: pink round with rotating guns."""
        # Round body
        pygame.draw.circle(target, (80, 30, 70), (cx, cy), 4)
        pygame.draw.circle(target, (255, 100, 180), (cx, cy), 3)
        # Eye
        pygame.draw.circle(target, (255, 255, 200), (cx, cy), 1)
        # 4 small gun barrels around
        import math
        for i in range(4):
            ang = i * (math.pi / 2) + (ship.x * 0.1)  # slow rotation
            gx = cx + int(math.cos(ang) * 5)
            gy = cy + int(math.sin(ang) * 5)
            pygame.draw.circle(target, (40, 40, 50), (gx, gy), 1)

    def _draw_demo_bullets(self, target: pygame.Surface) -> None:
        for b in self._demo_bullets:
            alpha = int(255 * min(1.0, b.life))
            # Simple glow + core
            halo = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*b.color, alpha // 2), (4, 4), 3)
            target.blit(halo, (int(b.x) - 4, int(b.y) - 4))
            pygame.draw.circle(target, b.color, (int(b.x), int(b.y)), 1)
            # Bright center
            pygame.draw.circle(target, (255, 255, 255), (int(b.x), int(b.y)), 0)

    def _draw_demo_explosions(self, target: pygame.Surface) -> None:
        for e in self._demo_explosions:
            t = max(0.0, e.life / 0.8)
            r = max(1, int(3 * (1.0 - t) + 1))
            alpha = int(220 * t)
            halo = pygame.Surface((r * 4 + 4, r * 4 + 4), pygame.SRCALPHA)
            pygame.draw.circle(halo, (*e.color, alpha), (r * 2 + 2, r * 2 + 2), r * 2)
            target.blit(halo, (int(e.x) - r * 2 - 2, int(e.y) - r * 2 - 2))
            # Bright core
            pygame.draw.circle(target, (255, 240, 200),
                              (int(e.x), int(e.y)), max(0, r - 1))


@dataclass
class _TitleDemoShip:
    """A demo ship flying across the title screen."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    kind: str = "enemy"  # "player" or "enemy"
    enemy_kind: Any = None
    size: tuple[int, int] = (12, 8)
    health: int = 1
    fire_cd: float = 1.0
    angle_deg: float = 0.0


@dataclass
class _TitleDemoBullet:
    """A demo bullet flying across the title screen."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    color: tuple[int, int, int] = (255, 255, 255)
    life: float = 2.0


@dataclass
class _TitleDemoExplosion:
    """A demo explosion particle."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.8
    color: tuple[int, int, int] = (255, 200, 100)


# BLOQUE 58.45: bind the procedural enemy drawers after the class is
# defined. The map is used by TitleScene._draw_demo_ships to dispatch
# to the right per-enemy-kind drawing function.
_ENEMY_DRAWERS.update({
    "scout":    TitleScene._draw_enemy_scout,
    "cruiser":  TitleScene._draw_enemy_cruiser,
    "heavy":    TitleScene._draw_enemy_heavy,
    "kamikaze": TitleScene._draw_enemy_kamikaze,
    "drone":    TitleScene._draw_enemy_drone,
    "sniper":   TitleScene._draw_enemy_sniper,
    "turret":   TitleScene._draw_enemy_turret,
})


class ActIntroScene(Scene):
    """ACT_INTRO — 'ACT N' title + boss portrait placeholder."""

    def __init__(self, transition_to: TransitionFn, act: int = 1) -> None:
        self._transition_to = transition_to
        self._act = act
        self._t: float = 0.0
        self._duration: float = 4.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.GAMEPLAY)
        if self._t >= self._duration:
            self._transition_to(GameState.GAMEPLAY)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        font = pygame.font.Font(None, 40)
        text = font.render(f"ACT {self._act}", True, (255, 220, 100))
        _center_blit(target, text, 120)
        # Boss name — 18px fits "GOLIATH AWAITS" comfortably
        font2 = pygame.font.Font(None, 18)
        boss_names = {1: "GOLIATH AWAITS", 2: "HYDRA EMERGES", 3: "PHANTOM & NEMESIS"}
        sub = font2.render(boss_names.get(self._act, ""), True, (220, 80, 80))
        _center_blit(target, sub, 200)


class GameplayScene(Scene):
    """GAMEPLAY — main action scene. Delegates to GameplayRuntime.

    Runtime handles: bullets, enemies, waves, score, particles, HUD,
    boss transitions, collisions, hitstop, shake, slowmo.
    """

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None,
                 set_session_score: "Optional[Callable[[int], None]]" = None) -> None:
        self._transition_to = transition_to
        self._act = act
        self._set_session_score = set_session_score  # BLOQUE 58.46: score carry-over
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=False, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()
        # BLOQUE 58.45: switch to the gameplay soundtrack (loop).
        # BLOQUE 58.6x: don't restart if already playing. on_enter fires
        # every time we return to gameplay (after sub-boss kill, after
        # boss death before act_cleared, etc.). Restarting the BGM every
        # time was audible to the user. With force=False the music
        # continues seamlessly through transitions.
        from src.audio import music
        if music.get_current_track() != "gameplay":
            music.play_gameplay_music(force=True)
        # BLOQUE 58.59: voice clip removed per user request (was "Gameplay")

    def on_exit(self) -> None:
        # BLOQUE 58.46: push the player's accumulated score to the game
        # session so the boss / act_cleared scene can keep it.
        if self._set_session_score is not None:
            self._set_session_score(self._rt._scoring.score)
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class BossIntroScene(Scene):
    """BOSS_INTRO — RED ALARM warning, 4-6s animated intro (BLOQUE 50).

    The whole scene pulses bright red like a fire alarm. The "WARNING"
    text is rendered in big red letters, flashes at alarm frequency, and
    a scanline / diagonal-stripe pattern overlays the screen to make it
    feel like an emergency klaxon.

    Phases (4.5s total):
      0.0 - 0.3s : White flash burst, then red flash
      0.3 - 1.5s : "!! WARNING !!" text grows + flashes red
      1.5 - 3.5s : Boss portrait slides down from top with red glow
      3.5 - 4.5s : Pulsing red, boss locked in
    """

    def __init__(self, transition_to: TransitionFn, boss_name: str = "BOSS",
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._boss_name = boss_name
        self._audio = audio
        self._t: float = 0.0
        self._duration: float = 4.5

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.23: reuse the game's existing audio engine.
        # The previous code did `AudioEngine()` here, which calls
        # `_prebake_all()` and re-renders EVERY SFX + BGM from scratch.
        # That took ~1.2s, blocking the game loop right at the
        # moment the wave cleared and the boss intro was supposed
        # to start. Using the shared engine is O(1) instead.
        audio = self._audio
        if audio is None:
            # Fallback: construct one if no shared engine was passed
            # (keeps backward-compat for any callers that don't pass audio).
            try:
                from src.audio.synth import AudioEngine
                audio = AudioEngine()
            except Exception:
                return
        try:
            audio.play_sfx("boss_warning", volume=0.9)
        except Exception:
            pass

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.BOSS_FIGHT)
        if self._t >= self._duration:
            self._transition_to(GameState.BOSS_FIGHT)

    def draw(self, target: pygame.Surface) -> None:
        w, h = target.get_size()
        # Phase 1: white flash burst (first 0.2s)
        if self._t < 0.2:
            target.fill((255, 255, 255))
            return
        # BLOQUE 50: fast alarm pulse (8 Hz — twice the old 6 Hz feel)
        pulse = 0.5 + 0.5 * math.sin(self._t * 8.0)
        # BLOQUE 50: deep red background that intensifies with the pulse
        bg_r = int(60 + pulse * 80)   # 60-140 (was 40-70)
        bg_g = int(0)
        bg_b = int(0)
        target.fill((bg_r, bg_g, bg_b))
        # BLOQUE 50: alarm diagonal stripes overlay (subtle, alarm-style)
        stripe_alpha = int(30 + pulse * 30)
        stripe = pygame.Surface((w, h), pygame.SRCALPHA)
        stripe_spacing = 12
        for y in range(-h, h * 2, stripe_spacing * 2):
            pygame.draw.line(stripe, (255, 60, 60, stripe_alpha),
                             (0, y), (w, y + 40), 2)
        target.blit(stripe, (0, 0))
        # Phase 2: BIG RED WARNING text (slides + flashes)
        font = pygame.font.Font(None, 32)
        # Slide: text appears 0.2-1.0s
        text_alpha = min(1.0, max(0.0, (self._t - 0.2) / 0.4))
        # BLOQUE 50: red WARNING with boss name on second line
        warning_text = "!! WARNING !!"
        # BLOQUE 50: alarm flash — text toggles between bright red and dim red
        if int(self._t * 6) % 2 == 0:
            text_color = (255, 60, 60)
            glow_color = (200, 30, 30)
        else:
            text_color = (200, 30, 30)
            glow_color = (120, 20, 20)
        warn_surf = font.render(warning_text, True, text_color)
        warn_surf.set_alpha(int(255 * text_alpha))
        # Outer red glow (multi-layer)
        for i, alpha_mul in enumerate([0.7, 0.4, 0.2]):
            glow_surf = font.render(warning_text, True, glow_color)
            glow_surf.set_alpha(int(120 * alpha_mul * text_alpha))
            off = i + 1
            for ox, oy in [(-off, 0), (off, 0), (0, -off), (0, off)]:
                target.blit(glow_surf,
                            (w // 2 - warn_surf.get_width() // 2 + ox,
                             60 - warn_surf.get_height() // 2 + oy))
        target.blit(warn_surf,
                    (w // 2 - warn_surf.get_width() // 2,
                     60 - warn_surf.get_height() // 2))
        # Boss name (under the WARNING, in white with red glow)
        font_name = pygame.font.Font(None, 16)
        name_surf = font_name.render(self._boss_name, True, (255, 240, 220))
        name_surf.set_alpha(int(255 * text_alpha))
        # Red name glow
        for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            g = font_name.render(self._boss_name, True, (255, 60, 60))
            g.set_alpha(int(100 * text_alpha))
            target.blit(g, (w // 2 - name_surf.get_width() // 2 + ox,
                            90 + oy))
        target.blit(name_surf, (w // 2 - name_surf.get_width() // 2, 90))
        # Phase 3: Boss portrait slides down from top (1.0s+)
        if self._t > 0.8:
            # Boss rectangle (dark red, with eye detail)
            boss_size = 36
            # Slide in: y starts at -boss_size, settles at 180
            target_y = 180
            start_y = -boss_size
            t_slide = min(1.0, (self._t - 0.8) / 0.8)
            t_eased = 1.0 - (1.0 - t_slide) ** 3  # ease-out
            boss_y = int(start_y + (target_y - start_y) * t_eased)
            boss_x = w // 2
            # BLOQUE 50: bigger red glow under boss (pulsing)
            glow_size = boss_size + 20
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 40, 40, 80 + int(60 * pulse)),
                             (0, 0, glow_size, glow_size), border_radius=4)
            target.blit(glow, (boss_x - glow_size // 2, boss_y - glow_size // 2))
            # Boss body (darker red — almost black-red)
            boss_rect = pygame.Rect(boss_x - boss_size // 2, boss_y - boss_size // 4,
                                    boss_size, boss_size // 2)
            pygame.draw.rect(target, (140, 30, 30), boss_rect)
            # Inner darker rectangle
            inner = boss_rect.inflate(-max(2, boss_size // 3), -max(1, boss_size // 6))
            pygame.draw.rect(target, (80, 20, 20), inner)
            # Boss eye (white, glowing red border)
            eye_w = 14
            eye_h = 3
            pygame.draw.rect(target, (255, 80, 80),
                             (boss_x - eye_w // 2 - 1, boss_y - eye_h // 2 - 1,
                              eye_w + 2, eye_h + 2))
            pygame.draw.rect(target, (255, 255, 255),
                             (boss_x - eye_w // 2, boss_y - eye_h // 2, eye_w, eye_h))
            # Phase border (bright red, flashing)
            border_color = (255, 40, 40) if pulse > 0.5 else (180, 20, 20)
            pygame.draw.rect(target, border_color, boss_rect, 1)
        # Bottom: "INCOMING HOSTILE" subtitle (red, blinking)
        font2 = pygame.font.Font(None, 12)
        sub = font2.render("!! INCOMING HOSTILE !!", True, (255, 80, 80))
        if int(self._t * 4) % 2 == 0 and self._t > 0.5:
            _center_blit(target, sub, 250)
        # Progress bar (fills over duration, red)
        bar_w = 200
        bar_h = 4
        bar_x = (w - bar_w) // 2
        bar_y = 320
        pygame.draw.rect(target, (80, 20, 20), (bar_x, bar_y, bar_w, bar_h), 1)
        progress = min(1.0, self._t / self._duration)
        pygame.draw.rect(target, (255, 60, 60),
                         (bar_x + 1, bar_y + 1, int(bar_w * progress) - 2, bar_h - 2))
        # "PRESS ENTER TO SKIP" hint
        if self._t > 1.0:
            font3 = pygame.font.Font(None, 10)
            hint = font3.render("PRESS ENTER TO SKIP", True, (200, 160, 160))
            _center_blit(target, hint, 340)
            _center_blit(target, sub, 200)


class SubBossIntroScene(Scene):
    """SUB_BOSS_INTRO — BLOQUE 50: YELLOW WARNING intro for the mid-wave
    sub-boss. Same structure as BossIntroScene but with a yellow/amber
    palette and shorter duration (2.5s). The sub-boss is fast, hard to
    hit, and shoots a lot — the warning tells the player "incoming
    threat, but not as bad as a real boss".
    """

    def __init__(self, transition_to: TransitionFn,
                 audio: Optional["AudioEngine"] = None) -> None:
        self._transition_to = transition_to
        self._audio = audio
        self._t: float = 0.0
        self._duration: float = 5.0  # BLOQUE 58.7x: even longer so the
                                       # player has time to react + position
                                       # themselves before the dart spawns.

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.23: reuse the shared audio engine (see BossIntroScene).
        # Creating a new AudioEngine() here would re-bake all SFX + BGM
        # (~1.2s freeze) right when the sub-boss warning is supposed
        # to start playing.
        audio = self._audio
        if audio is None:
            try:
                from src.audio.synth import AudioEngine
                audio = AudioEngine()
            except Exception:
                return
        try:
            audio.play_sfx("boss_warning", volume=0.9)  # BLOQUE 58.6y: louder so the warning is obvious
        except Exception:
            pass

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.GAMEPLAY)
        if self._t >= self._duration:
            self._transition_to(GameState.GAMEPLAY)

    def draw(self, target: pygame.Surface) -> None:
        w, h = target.get_size()
        # White flash for the first 0.15s
        if self._t < 0.15:
            target.fill((255, 255, 255))
            return
        # Yellow background, gentler pulse than boss (5 Hz)
        pulse = 0.5 + 0.5 * math.sin(self._t * 5.0)
        bg_r = int(60 + pulse * 50)
        bg_g = int(50 + pulse * 30)
        bg_b = int(0)
        target.fill((bg_r, bg_g, bg_b))
        # Yellow diagonal stripes (subtler than boss red)
        stripe_alpha = int(20 + pulse * 20)
        stripe = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(-h, h * 2, 14):
            pygame.draw.line(stripe, (255, 200, 60, stripe_alpha),
                             (0, y), (w, y + 40), 2)
        target.blit(stripe, (0, 0))
        # WARNING text — yellow, flashing
        font = pygame.font.Font(None, 28)
        text_alpha = min(1.0, max(0.0, (self._t - 0.15) / 0.4))
        if int(self._t * 5) % 2 == 0:
            text_color = (255, 220, 80)
            glow_color = (200, 160, 40)
        else:
            text_color = (200, 160, 40)
            glow_color = (140, 110, 20)
        warn_surf = font.render("! WARNING !", True, text_color)
        warn_surf.set_alpha(int(255 * text_alpha))
        # Yellow glow
        for off in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            g = font.render("! WARNING !", True, glow_color)
            g.set_alpha(int(120 * text_alpha))
            target.blit(g, (w // 2 - warn_surf.get_width() // 2 + off[0],
                            80 - warn_surf.get_height() // 2 + off[1]))
        target.blit(warn_surf,
                    (w // 2 - warn_surf.get_width() // 2,
                     80 - warn_surf.get_height() // 2))
        # Sub-boss label below WARNING
        font_sub = pygame.font.Font(None, 14)
        sub = font_sub.render("HOSTILE FRENETIC", True, (255, 230, 140))
        sub.set_alpha(int(255 * text_alpha))
        _center_blit(target, sub, 110)
        # Mini ship preview (yellow dart, slides down from top)
        if self._t > 0.4:
            ship_y_target = 200
            t_slide = min(1.0, (self._t - 0.4) / 0.5)
            t_eased = 1.0 - (1.0 - t_slide) ** 3
            ship_y = int(-30 + (ship_y_target - -30) * t_eased)
            ship_x = w // 2
            # Yellow halo
            halo = pygame.Surface((50, 50), pygame.SRCALPHA)
            halo_alpha = 60 + int(40 * pulse)
            pygame.draw.ellipse(halo, (255, 200, 80, halo_alpha),
                                (0, 0, 50, 50), 1)
            target.blit(halo, (ship_x - 25, ship_y - 25))
            # Dart body (yellow)
            pygame.draw.polygon(target, (255, 200, 80), [
                (ship_x, ship_y - 12),
                (ship_x + 10, ship_y + 2),
                (ship_x + 4, ship_y + 8),
                (ship_x, ship_y + 4),
                (ship_x - 4, ship_y + 8),
                (ship_x - 10, ship_y + 2),
            ])
            # Red core (glowing)
            pygame.draw.circle(target, (255, 80, 80), (ship_x, ship_y), 2)
        # Progress bar (yellow, fills faster)
        bar_w = 200
        bar_h = 3
        bar_x = (w - bar_w) // 2
        bar_y = 320
        pygame.draw.rect(target, (100, 80, 30), (bar_x, bar_y, bar_w, bar_h), 1)
        progress = min(1.0, self._t / self._duration)
        pygame.draw.rect(target, (255, 220, 80),
                         (bar_x + 1, bar_y + 1, int(bar_w * progress) - 2, bar_h - 2))
        # "PRESS ENTER TO SKIP" hint
        if self._t > 0.5:
            font3 = pygame.font.Font(None, 10)
            hint = font3.render("PRESS ENTER TO SKIP", True, (220, 200, 140))
            _center_blit(target, hint, 340)


class BossFightScene(Scene):
    """BOSS_FIGHT — boss arena. Delegates to GameplayRuntime in boss mode."""

    def __init__(self, transition_to: "TransitionFn", act: int = 1,
                 audio: Optional["AudioEngine"] = None,
                 get_session_score: "Optional[Callable[[], int]]" = None,
                 set_session_score: "Optional[Callable[[int], None]]" = None) -> None:
        self._transition_to = transition_to
        self._act = act
        # BLOQUE 58.46: callbacks for the cross-scene session score.
        self._get_session_score = get_session_score
        self._set_session_score = set_session_score
        from src.ui.gameplay_runtime import GameplayRuntime
        self._rt = GameplayRuntime(transition_to, is_boss=True, act=act, audio=audio)

    def on_enter(self) -> None:
        self._rt.on_enter()
        # BLOQUE 58.46: override the fresh scoring system with the player's
        # accumulated score from gameplay so the HUD doesn't reset to 0.
        if self._get_session_score is not None:
            self._rt._scoring.score = self._get_session_score()
        # BLOQUE 58.45/53: gameplay music keeps playing through boss fights.
        # Now `play_gameplay_music` is idempotent — it won't restart the
        # track if it's already the current track.
        from src.audio import music
        if music.get_current_track() != "gameplay":
            music.play_gameplay_music(force=True)
        # BLOQUE 58.59: voice clip removed per user request (was "Jefe")

    def on_exit(self) -> None:
        # BLOQUE 58.46: push the boss score back to the session so the
        # GAME_OVER / ACT_CLEARED scenes can read the right number.
        if self._set_session_score is not None:
            self._set_session_score(self._rt._scoring.score)
        self._rt.on_exit()

    def update(self, dt: float) -> None:
        # BLOQUE 58.47: do NOT drain events here. The runtime handles ESC
        # and ALL other inputs (LSHIFT, B, etc.) via its own event loop.
        # Previously this scene called `pygame.event.get(KEYDOWN)` to handle
        # ESC, which CONSUMED the entire event queue before the runtime saw
        # it — so B (missile) and LSHIFT (propulsion) silently failed in
        # the boss. Symptom: "solo dash funciona, ni misiles ni propulsor".
        self._rt.update(dt)

    def draw(self, target: pygame.Surface) -> None:
        self._rt.draw(target)


class ActClearedScene(Scene):
    """ACT_CLEARED — act boss defeated, +25000 pts, act transition."""

    # BLOQUE 58.46: bonus added to the session score when an act is cleared.
    ACT_CLEAR_BONUS: int = 25000

    def __init__(self, transition_to: TransitionFn,
                 get_session_score: "Optional[Callable[[], int]]" = None,
                 set_session_score: "Optional[Callable[[int], None]]" = None) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 4.0
        # BLOQUE 58.46: when this scene starts, add the clear bonus to the
        # session score so it carries over to the next act.
        self._get_session_score = get_session_score
        self._set_session_score = set_session_score

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.46: commit the act-clear bonus to the session score.
        if (self._get_session_score is not None
                and self._set_session_score is not None):
            self._set_session_score(
                self._get_session_score() + self.ACT_CLEAR_BONUS,
            )
        # BLOQUE 58.59: voice clip removed per user request (was "Acto completado")
        from src.audio import music
        # (no voice call; gameplay music keeps playing through the cleared screen)

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.ACT_INTRO)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.ACT_INTRO)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # 28px fits "ACT CLEARED!" (12 chars) in 240px
        font = pygame.font.Font(None, 28)
        text = font.render("ACT CLEARED!", True, (255, 220, 100))
        _center_blit(target, text, 100)
        font2 = pygame.font.Font(None, 18)
        sub = font2.render("+25000 PTS", True, (255, 180, 40))
        _center_blit(target, sub, 200)


class GameOverScene(Scene):
    """GAME_OVER — 0 lives, end of run."""

    def __init__(self, transition_to: TransitionFn,
                 get_session_score: "Optional[Callable[[], int]]" = None,
                 set_session_score: "Optional[Callable[[int], None]]" = None) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 5.0
        # BLOQUE 58.46: keep a snapshot of the final score for the display
        # and reset the session score so the next run starts at 0.
        self._get_session_score = get_session_score
        self._set_session_score = set_session_score
        self._final_score: int = 0

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.46: snapshot the final score for display, then reset
        # the session so the next run starts fresh.
        if self._get_session_score is not None:
            self._final_score = self._get_session_score()
        if self._set_session_score is not None:
            self._set_session_score(0)

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.TITLE)
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 0, 0))
        # 32px fits "GAME OVER" (9 chars) in 240px
        font = pygame.font.Font(None, 32)
        text = font.render("GAME OVER", True, (255, 60, 40))
        _center_blit(target, text, 140)
        # BLOQUE 58.46: show the player's final score so they know what
        # they scored before dying.
        font2 = pygame.font.Font(None, 18)
        score_text = font2.render(
            f"FINAL SCORE: {self._final_score:06d}", True, (255, 200, 80),
        )
        _center_blit(target, score_text, 200)


class VictoryScene(Scene):
    """VICTORY — final boss defeated, runs after NEMESIS dies."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._duration: float = 6.0

    def on_enter(self) -> None:
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        if self._t >= self._duration:
            self._transition_to(GameState.CREDITS)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((40, 30, 0))
        # 40px fits "VICTORY!" (8 chars) in 240px
        font = pygame.font.Font(None, 40)
        text = font.render("VICTORY!", True, (255, 220, 100))
        _center_blit(target, text, 140)


class CreditsScene(Scene):
    """CREDITS — final roll, "PRESS ENTER FOR TITLE"."""

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._transition_to(GameState.TITLE)

    def draw(self, target: pygame.Surface) -> None:
        target.fill((0, 0, 0))
        # Title (small)
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("VOID HUNTER", True, (255, 220, 100))
        _center_blit(target, title, 30)
        # Body — wrap to fit 240px
        body_font = pygame.font.Font(None, 12)
        body_lines = [
            "A shmup by Lerius",
            "",
            "Built on Pygame 2.6 + Python 3.11",
            "120 FPS lock",
            "Zero external deps",
            "(numpy/scipy prohibited)",
            "",
            "Thanks to: Cave, Touhou, Ikaruga,",
            "DoDonPachi, Gradius, R-Type,",
            "Metal Slug, Devil May Cry",
            "",
            f"Run time: {int(self._t)}s",
            "",
            "PRESS ENTER FOR TITLE",
        ]
        y = 70
        for line in body_lines:
            text = body_font.render(line, True, (200, 200, 220))
            _center_blit(target, text, y)
            y += 16


class PauseScene(Scene):
    """BLOQUE 58.41: PAUSE overlay with interactive control reference.

    Layout (centered on screen):
      - "PAUSED" header at top
      - Control reference panel below (categorized):
        * MOVEMENT   WASD / arrows
        * AIM        mouse
        * SHOOTING   LMB charge, RMB rapid, B missile
        * MOVEMENT2  SHIFT dash/propulsion, ESC pause
      - "ESC to resume" footer
    """

    def __init__(self, transition_to: TransitionFn) -> None:
        self._transition_to = transition_to
        self._t: float = 0.0
        self._selected: int = 0  # for future interactive nav (BLOQUE 58.42)

    def on_enter(self) -> None:
        self._t = 0.0
        # BLOQUE 58.45: pause = switch back to the title-screen track
        # (so the gameplay music isn't playing while the player is paused).
        from src.audio import music
        music.play_title_music()

    def on_exit(self) -> None:
        # BLOQUE 58.45: leaving pause = switch back to the gameplay track.
        from src.audio import music
        music.play_gameplay_music()

    def update(self, dt: float) -> None:
        self._t += dt
        for event in pygame.event.get(pygame.KEYDOWN):
            if event.key == pygame.K_ESCAPE:
                self._transition_to(GameState.GAMEPLAY)  # will pop overlay
                return
            # C: CREDITS from pause (was on title)
            if event.key == pygame.K_c:
                self._transition_to(GameState.CREDITS)
                return

    def draw(self, target: pygame.Surface) -> None:
        # Dim overlay (slightly darker than before for contrast)
        dim = pygame.Surface(target.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        target.blit(dim, (0, 0))
        # PAUSED header
        font = pygame.font.Font(None, 36)
        text = font.render("PAUSED", True, (255, 240, 100))
        _center_blit(target, text, 16)
        # Control reference panel
        self._draw_controls_panel(target)
        # Footer
        font2 = pygame.font.Font(None, 12)
        footer = font2.render("ESC: resume  |  C: credits", True, (160, 160, 180))
        _center_blit(target, footer, INTERNAL_H - 16)

    def _draw_controls_panel(self, target: pygame.Surface) -> None:
        """Draw the categorized control reference panel."""
        # 4 categories, each with its own row
        categories = [
            ("MOVEMENT", [
                ("WASD / Arrows", "move"),
            ]),
            ("AIM", [
                ("Mouse", "aim"),
            ]),
            ("SHOOTING", [
                ("LMB (hold)", "charge shot"),
                ("RMB (hold)", "rapid fire"),
                ("B", "homing missile"),
            ]),
            ("TACTICAL", [
                ("Shift", "dash / propulsion"),
                ("ESC", "pause"),
            ]),
        ]
        # Panel area: starts at y=70, each category is ~20 px tall
        panel_x = 12
        panel_y = 70
        panel_w = INTERNAL_W - 24
        # Panel background (subtle)
        panel = pygame.Surface((panel_w, 130), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 15, 30, 180),
                          (0, 0, panel_w, 130), border_radius=4)
        pygame.draw.rect(panel, (60, 60, 100, 200),
                          (0, 0, panel_w, 130), 1, border_radius=4)
        target.blit(panel, (panel_x, panel_y))
        # Column headers
        font_header = pygame.font.Font(None, 12)
        font_key = pygame.font.Font(None, 12)
        font_desc = pygame.font.Font(None, 12)
        # Layout: 2 columns
        col_w = panel_w // 2
        for col_idx, (cat_name, items) in enumerate(categories):
            col_x = panel_x + 4 + col_idx * col_w
            # Category header
            header_surf = font_header.render(cat_name, True, (180, 200, 240))
            target.blit(header_surf, (col_x, panel_y + 6))
            # Underline
            pygame.draw.line(target, (100, 130, 180),
                              (col_x, panel_y + 6 + header_surf.get_height() + 1),
                              (col_x + header_surf.get_width(),
                               panel_y + 6 + header_surf.get_height() + 1), 1)
            # Items
            for i, (key, desc) in enumerate(items):
                item_y = panel_y + 24 + i * 24
                # Key (highlighted, bold-looking)
                key_surf = font_key.render(key, True, (255, 220, 100))
                target.blit(key_surf, (col_x, item_y))
                # Description (dimmer)
                desc_surf = font_desc.render(desc, True, (200, 200, 220))
                target.blit(desc_surf,
                            (col_x + key_surf.get_width() + 6, item_y + 1))
