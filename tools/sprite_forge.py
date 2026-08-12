"""Sprite Forge — unified procedural sprite generator for VOID HUNTER.

BLOQUE 58.33: Replaces the 40+ ad-hoc capture_* scripts in tools/.
Renders EVERY procedural sprite the game uses to PNG files, in
two layouts:

  1. Per-sprite PNGs       :  tools/playtest_out/forge/<category>/<sprite>.png
  2. Per-category atlas    :  tools/playtest_out/forge/atlas_<category>.png
  3. Combined atlas        :  tools/playtest_out/forge/atlas_all.png

The atlas is a labeled contact sheet: each cell has the sprite and
its name underneath, so you can diff visuals side-by-side after
tweaking the game code.

USAGE
-----
    python tools/sprite_forge.py                # render everything
    python tools/sprite_forge.py --list         # show categories
    python tools/sprite_forge.py player         # one category
    python tools/sprite_forge.py --atlas-only   # only the atlases

CATEGORIES
----------
    player       : 4 ship states (idle, charge-1/2/3, propulsion)
    enemies      : 8 enemy kinds + sub-boss 4 cardinal angles = 11
    boss         : 4 boss visuals (goliath p1/p2, simple, hp)
    projectiles  : 7 projectile visuals
    effects      : 8 effect visuals (flame, muzzle, shield, ...)
    particles    : 19 particle kinds
    tron_trail   : 3 trail samples
    hud          : 11 HUD element variants

DESIGN
------
We re-use the game's actual drawing functions wherever possible by
instantiating the runtime with ``__new__`` and pointing the methods
at a fresh transparent surface. This guarantees the captured sprite
is byte-identical to what the player sees in-game — no risk of the
forge drifting from the real visuals.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Headless pygame setup MUST happen before importing game modules.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("VOID_HUNTER_INVULN", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from src.entities.boss_spear import BossSpear  # noqa: E402
from src.entities.enemies.enemy import Enemy, EnemyKind, ENEMY_CONFIGS  # noqa: E402
from src.entities.player.player import (  # noqa: E402
    CHARGE_L1_S, CHARGE_L2_S, CHARGE_L3_S, Player, PlayerState,
)
from src.systems.particle_engine import (  # noqa: E402
    KIND_CONFIG, P_KIND_COUNT, ParticleEngine,
)
from src.systems.tron_trail import TronTrail, TronSegment  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime, HomingMissile  # noqa: E402
from src.ui.hud import HUD  # noqa: E402

OUT_DIR = ROOT / "tools" / "playtest_out" / "forge"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _save_png(surface: pygame.Surface, path: Path) -> None:
    """Save a surface to a PNG, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(path))


def _crop_bounds(surface: pygame.Surface, pad: int = 2) -> pygame.Surface:
    """Return a cropped copy of ``surface`` around its non-transparent bbox.

    Adds ``pad`` pixels of padding on each side so the sprite doesn't
    sit flush against the cell edge in the atlas.
    """
    if surface.get_width() < 1 or surface.get_height() < 1:
        return surface.copy()
    bbox = surface.get_bounding_rect()
    if bbox.width < 1 or bbox.height < 1:
        return surface.copy()
    # Clamp pad to keep the crop inside the surface.
    x = max(0, bbox.x - pad)
    y = max(0, bbox.y - pad)
    w = min(surface.get_width() - x, bbox.width + pad * 2)
    h = min(surface.get_height() - y, bbox.height + pad * 2)
    return surface.subsurface((x, y, w, h)).copy()


def _text(surface: pygame.Surface, text: str, color: tuple[int, int, int],
          size: int = 10, bold: bool = False) -> pygame.Surface:
    """Render a small label using the system console font.

    Falls back to the default font if consolas isn't available
    (e.g. on minimal Linux).
    """
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        font = pygame.font.SysFont("consolas", size, bold=bold)
    except Exception:
        font = pygame.font.Font(None, size)
    return font.render(text, True, color)


# ---------------------------------------------------------------------------
# Runtime harness — instantiate gameplay_runtime without running __init__
# ---------------------------------------------------------------------------
def _new_runtime() -> GameplayRuntime:
    """Create a GameplayRuntime with ``__new__`` (skip __init__).

    We populate only the fields the drawing methods actually touch.
    Adding more is cheap; missing one will surface as an AttributeError
    the moment a drawing method reads it.
    """
    rt = GameplayRuntime.__new__(GameplayRuntime)
    # Time / mouse
    rt._t = 0.0
    rt._mouse_x = 160
    rt._mouse_y = 240
    rt._mouse_r_held = False
    # Player
    rt._player = Player()
    rt._player.x = 0
    rt._player.y = 0
    rt._player.vx = 0.0
    rt._player.tilt = 0.0
    rt._player.current_tilt = 0.0
    rt._player.nose_angle = 0.0
    rt._player.current_nose_angle = 0.0
    rt._player.dash_iframes_left = 0
    rt._player.respawn_invuln = 0.0
    rt._player.dash_heat = 0.0
    rt._player.state = PlayerState.IDLE
    # Muzzle / charge feedback
    rt._muzzle_flash = 0.0
    rt._muzzle_flash_source = "lmb"
    rt._charge_release_flash = 0.0
    rt._charge_release_shock = False
    # Laser (continuous beam)
    rt._laser_active = False
    rt._laser_end_x = 0.0
    rt._laser_end_y = 0.0
    rt._laser_damage_timer = 0.0
    rt._laser_pulse_t = 0.0
    # Dicts (hit-flash bookkeeping)
    rt._enemy_flash = {}
    rt._boss_flash = {}
    # Subsystems that the drawing methods call into. Cheap to construct;
    # each is a self-contained object with no game-state dependencies.
    from src.systems.particle_engine import ParticleEngine as _PE
    from src.systems.projectile import ProjectilePool
    from src.systems.weapon_system import WeaponSystem
    rt._particles = _PE(pool_size=64)
    rt._bullets = ProjectilePool(capacity=64)
    rt._weapon = WeaponSystem()
    rt._missiles = []
    rt._boss_spears = []
    rt._boss = None
    # Boss-related state (so the boss drawing methods don't crash on
    # attributes that only exist during a live boss fight).
    rt._bosses = type("BossPool", (), {"spawn": staticmethod(lambda *_: None)})()
    rt._boss_spear_phase = "ready"
    rt._boss_spear_phase_t = 0.0
    rt._boss_shield_hits = 0
    rt._boss_shield_laser_t = 0.0
    rt._boss_shield_laser_duration = 1.0
    rt._boss_shield_laser_damage_cooldown = {}
    rt._boss_entry_t = 0.0
    rt._boss_death_stage = 0
    rt._boss_death_timer = 0.0
    rt._boss_death_pos = (0.0, 0.0)
    # Scratch surface for the sub-boss rotation. Allocated on demand.
    rt._sub_boss_scratch = pygame.Surface((96, 96), pygame.SRCALPHA)
    return rt


def _draw_into_bbox(
    draw_fn: Callable[[pygame.Surface, int, int], None],
    size: tuple[int, int] = (128, 128),
) -> pygame.Surface:
    """Run ``draw_fn`` into a fresh transparent surface and crop to bbox.

    ``draw_fn`` receives ``(target, ox, oy)``. We pass ox=oy=0 and let
    the function draw at the world origin; we then crop to the visible
    bbox and return it. Use ``size`` to set the scratch surface size.
    """
    target = pygame.Surface(size, pygame.SRCALPHA)
    target.fill((0, 0, 0, 0))
    # Place the entity at the surface center.
    cx, cy = size[0] // 2, size[1] // 2
    # Translate the world origin to (cx, cy) by passing ox=cx, oy=cy.
    draw_fn(target, cx, cy)
    return _crop_bounds(target, pad=2)


# ---------------------------------------------------------------------------
# CATEGORY: player
# ---------------------------------------------------------------------------
def render_player(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    """Render the 4 player ship states."""
    rt = _new_runtime()
    out: list[tuple[str, pygame.Surface]] = []

    # IDLE
    rt._player.state = PlayerState.IDLE
    out.append(("player_idle", _draw_into_bbox(rt._draw_player)))

    # CHARGE levels 1, 2, 3
    for level, threshold in [(1, CHARGE_L1_S), (2, CHARGE_L2_S), (3, CHARGE_L3_S)]:
        rt._player.state = PlayerState.CHARGE
        # Force the charge level by setting charge_time just past the threshold.
        rt._player.charge_time = threshold + 0.01
        out.append((f"player_charge_{level}", _draw_into_bbox(rt._draw_player)))

    # PROPULSION
    rt._player.state = PlayerState.PROPULSION
    out.append(("player_propulsion", _draw_into_bbox(rt._draw_player)))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: enemies (8 types + sub-boss 4 angles)
# ---------------------------------------------------------------------------
def _make_enemy(kind: EnemyKind, x: float = 0, y: float = 0) -> Enemy:
    e = Enemy.__new__(Enemy)
    e.kind = kind
    e.x = x
    e.y = y
    e.vx = 0.0
    e.vy = 0.0
    e.telegraph_timer = 0
    e.hp = float(ENEMY_CONFIGS[kind].hp)  # type: ignore[assignment]
    e.max_hp = float(ENEMY_CONFIGS[kind].hp)  # type: ignore[assignment]
    return e


def render_enemies(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    rt = _new_runtime()
    out: list[tuple[str, pygame.Surface]] = []

    kinds = [
        (EnemyKind.SCOUT, "scout"),
        (EnemyKind.CRUISER, "cruiser"),
        (EnemyKind.HEAVY, "heavy"),
        (EnemyKind.KAMIKAZE, "kamikaze"),
        (EnemyKind.SNIPER, "sniper"),
        (EnemyKind.DRONE, "drone"),
        (EnemyKind.TURRET, "turret"),
    ]
    def _draw_enemy_for(e: Enemy) -> Callable[[pygame.Surface, int, int], None]:
        def _fn(t: pygame.Surface, ox: int, oy: int) -> None:
            rt._draw_enemy(t, e, ox, oy)
        return _fn

    for kind, label in kinds:
        rt._enemy_flash = {}
        e = _make_enemy(kind)
        cfg = ENEMY_CONFIGS[kind]
        size = (cfg.width * 4 + 16, cfg.height * 4 + 16)
        out.append((f"enemy_{label}", _draw_into_bbox(
            _draw_enemy_for(e), size=size,
        )))

    # Sub-boss at 4 cardinal angles
    for angle, label in [(0, "down"), (90, "right"), (180, "up"), (270, "left")]:
        e = _make_enemy(EnemyKind.SUB_BOSS)
        # sub_boss_facing_angle: DOWN=0, RIGHT=+90, UP=180, LEFT=270
        if angle == 0:
            e.vx, e.vy = 0.0, 50.0
        elif angle == 90:
            e.vx, e.vy = 50.0, 0.0
        elif angle == 180:
            e.vx, e.vy = 0.0, -50.0
        else:
            e.vx, e.vy = -50.0, 0.0
        rt._enemy_flash = {}
        size = (ENEMY_CONFIGS[EnemyKind.SUB_BOSS].width * 6 + 16,
                ENEMY_CONFIGS[EnemyKind.SUB_BOSS].height * 6 + 16)
        out.append((f"sub_boss_{label}", _draw_into_bbox(
            _draw_enemy_for(e), size=size,
        )))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: boss (goliath p1/p2, simple, hp-bar)
# ---------------------------------------------------------------------------
def render_boss(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    from src.entities.enemies.boss import BOSS_CONFIGS, Boss, BossId

    rt = _new_runtime()
    out: list[tuple[str, pygame.Surface]] = []

    # GOLIATH phase 1
    b = Boss.__new__(Boss)
    b.id = BossId.GOLIATH
    b.x = 0.0
    b.y = 0.0
    b.phase = 1
    cfg = BOSS_CONFIGS[b.id]
    b.hp = float(cfg.max_hp)  # type: ignore[assignment]
    b.max_hp = float(cfg.max_hp)  # type: ignore[assignment]
    rt._boss = b
    rt._boss_flash = {}
    out.append(("boss_goliath_phase1", _draw_into_bbox(
        rt._draw_goliath, size=(80, 80),
    )))

    # GOLIATH phase 2 (cracks glowing red)
    b.phase = 2
    b.hp = float(int(cfg.max_hp * 0.4))  # type: ignore[assignment]
    out.append(("boss_goliath_phase2", _draw_into_bbox(
        rt._draw_goliath, size=(80, 80),
    )))

    # BLOQUE 58.37: simple bosses redesigned as Star Fox 64 ships.
    # Render all 3 (HYDRA / PHANTOM / NEMESIS) so atlas_boss.png shows them.
    for boss_id, label in [
        (BossId.HYDRA, "boss_hydra"),
        (BossId.PHANTOM, "boss_phantom"),
        (BossId.NEMESIS, "boss_nemesis"),
    ]:
        b2 = Boss.__new__(Boss)
        b2.id = boss_id
        b2.x = 0.0
        b2.y = 0.0
        b2.phase = 1
        cfg2 = BOSS_CONFIGS[b2.id]
        b2.hp = float(cfg2.max_hp)  # type: ignore[assignment]
        b2.max_hp = float(cfg2.max_hp)  # type: ignore[assignment]
        rt._boss = b2
        rt._boss_flash = {}
        out.append((f"{label}_phase1", _draw_into_bbox(
            rt._draw_boss_simple, size=(96, 96),
        )))
        # Phase 2 variant (more weapons, cracks glow, etc.)
        b2.phase = 2
        b2.hp = float(int(cfg2.max_hp * 0.5))  # type: ignore[assignment]
        out.append((f"{label}_phase2", _draw_into_bbox(
            rt._draw_boss_simple, size=(96, 96),
        )))
        # Phase 3/4 variant (only NEMESIS has 4 phases; others fall back to 2)
        b2.phase = min(4, len(cfg2.phase_thresholds) + 1)
        b2.hp = float(int(cfg2.max_hp * 0.25))  # type: ignore[assignment]
        out.append((f"{label}_phase_max", _draw_into_bbox(
            rt._draw_boss_simple, size=(96, 96),
        )))

    # HP bar variant (goliath damaged)
    b.phase = 2
    b.hp = float(int(cfg.max_hp * 0.2))  # type: ignore[assignment]
    out.append(("boss_goliath_low_hp", _draw_into_bbox(
        rt._draw_goliath, size=(80, 80),
    )))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: projectiles
# ---------------------------------------------------------------------------
def render_projectiles(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    """Render projectile visuals using the actual ProjectilePool + drawing fns."""
    from src.systems.projectile import (
        BULLET_BOSS, BULLET_ENEMY, BULLET_PLAYER, BULLET_PLAYER_BEAM,
        BULLET_PLAYER_CHARGED, ProjectilePool,
    )
    rt = _new_runtime()
    rt._bullets = ProjectilePool(capacity=64)
    out: list[tuple[str, pygame.Surface]] = []

    def _draw_bullets_with_kind(t: pygame.Surface, kind: int, ox: int, oy: int,
                                 vx: float = 0.0, vy: float = -300.0) -> None:
        # Place bullet at (ox, oy), then run the runtime's bullet draw.
        rt._bullets.spawn(kind, float(ox), float(oy), vx, vy)
        rt._draw_bullets_with_glow(t, 0, 0)

    # Player L0 (small) + L1 (charged) bullets
    def player_lasers(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._bullets.spawn(BULLET_PLAYER, float(ox), float(oy), 0.0, -300.0)
        rt._bullets.spawn(BULLET_PLAYER_CHARGED, float(ox) - 8, float(oy), 0.0, -300.0)
        rt._bullets.spawn(BULLET_PLAYER_CHARGED, float(ox) + 8, float(oy), 0.0, -300.0)
        rt._draw_bullets_with_glow(t, 0, 0)

    out.append(("projectile_player_lasers", _draw_into_bbox(
        player_lasers, size=(40, 40),
    )))

    # Player L3 beam
    def player_beam(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._bullets.spawn(BULLET_PLAYER_BEAM, float(ox), float(oy), 0.0, -300.0)
        rt._draw_bullets_with_glow(t, 0, 0)

    out.append(("projectile_player_beam", _draw_into_bbox(
        player_beam, size=(40, 40),
    )))

    # Enemy bullet
    def enemy_bullet(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._bullets.spawn(BULLET_ENEMY, float(ox), float(oy), 0.0, 100.0)
        rt._draw_bullets_with_glow(t, 0, 0)

    out.append(("projectile_enemy_bullet", _draw_into_bbox(
        enemy_bullet, size=(40, 40),
    )))

    # Boss bullet
    def boss_bullet(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._bullets.spawn(BULLET_BOSS, float(ox), float(oy), 0.0, 80.0)
        rt._draw_bullets_with_glow(t, 0, 0)

    out.append(("projectile_boss_bullet", _draw_into_bbox(
        boss_bullet, size=(40, 40),
    )))

    # Homing missile
    def missile(t: pygame.Surface, ox: int, oy: int) -> None:
        m = HomingMissile(x=float(ox), y=float(oy), vx=0.0, vy=-200.0,
                          angle=-90.0, speed=200.0, life=1.0)
        rt._missiles = [m]
        rt._draw_missiles(t, 0, 0)

    out.append(("projectile_missile", _draw_into_bbox(
        missile, size=(40, 40),
    )))

    # Continuous laser (a long vertical beam)
    def laser(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._player.x = float(ox)
        rt._player.y = float(oy + 60)
        rt._player.state = PlayerState.CHARGE
        rt._player.charge_time = CHARGE_L3_S + 1.0
        rt._laser_active = True
        rt._laser_end_x = float(ox)
        rt._laser_end_y = float(oy - 80)
        rt._laser_damage_timer = 0.0
        rt._draw_continuous_laser(t, 0, 0)

    out.append(("projectile_continuous_laser", _draw_into_bbox(
        laser, size=(40, 100),
    )))

    # Boss spear (main)
    def spear(t: pygame.Surface, ox: int, oy: int) -> None:
        s = BossSpear(x=float(ox), y=float(oy),
                      base_vx=0.0, base_vy=-1.0, kind="main",
                      hp=3, max_hp=3, speed=180.0)
        rt._boss_spears = [s]
        rt._draw_boss_spear(t, s, 0, 0)

    out.append(("projectile_boss_spear", _draw_into_bbox(
        spear, size=(60, 60),
    )))

    # Boss spear (fragment)
    def frag(t: pygame.Surface, ox: int, oy: int) -> None:
        s = BossSpear(x=float(ox), y=float(oy),
                      base_vx=0.6, base_vy=-0.8, kind="fragment",
                      hp=1, max_hp=1, speed=220.0)
        rt._boss_spears = [s]
        rt._draw_boss_spear(t, s, 0, 0)

    out.append(("projectile_spear_fragment", _draw_into_bbox(
        frag, size=(40, 40),
    )))

    # Shield laser (vertical beam) — needs a boss
    from src.entities.enemies.boss import Boss, BossId
    b = Boss(active=True, id=BossId.GOLIATH, x=0.0, y=0.0,
             vx=0.0, vy=0.0, hp=400, max_hp=400, phase=2)
    rt._boss = b
    out.append(("projectile_shield_laser", _draw_into_bbox(
        rt._draw_shield_laser, size=(60, 200),
    )))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: effects
# ---------------------------------------------------------------------------
def render_effects(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    rt = _new_runtime()
    out: list[tuple[str, pygame.Surface]] = []

    # Engine flame at 3 speeds
    for speed, label in [(0, "idle"), (80, "cruise"), (160, "boost")]:
        rt._player.x = 0
        rt._player.y = 0
        rt._player.vx = float(speed)
        rt._player.state = PlayerState.PROPULSION if speed > 0 else PlayerState.IDLE
        out.append((f"effect_engine_flame_{label}", _draw_into_bbox(
            rt._draw_engine_flame, size=(40, 40),
        )))

    # Muzzle flash (LMB = yellow, RMB = orange)
    for source, label in [("lmb", "lmb"), ("rmb", "rmb")]:
        rt._muzzle_flash = 1.0
        rt._muzzle_flash_source = source
        out.append((f"effect_muzzle_flash_{label}", _draw_into_bbox(
            rt._draw_muzzle_flash, size=(40, 40),
        )))

    # Shield (respawn invuln)
    rt._player.respawn_invuln = 1.0
    out.append(("effect_shield", _draw_into_bbox(
        rt._draw_shield, size=(40, 40),
    )))

    # Charge aura (L3)
    rt._player.state = PlayerState.CHARGE
    rt._player.charge_time = CHARGE_L3_S + 1.0
    out.append(("effect_charge_aura_l3", _draw_into_bbox(
        rt._draw_charge_aura, size=(40, 40),
    )))

    # Charge ring (charging)
    def _charge_ring(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._draw_charge_ring(t, 0.7, (255, 220, 100), ox, oy)

    out.append(("effect_charge_ring", _draw_into_bbox(
        _charge_ring, size=(40, 40),
    )))

    # Reticle
    rt._mouse_x = 0
    rt._mouse_y = 0
    out.append(("effect_reticle", _draw_into_bbox(
        rt._draw_reticle, size=(40, 40),
    )))

    # Speed lines
    rt._speed_line_t = 0.0

    def _speed_lines(t: pygame.Surface, ox: int, oy: int) -> None:
        rt._draw_speed_lines(t)

    out.append(("effect_speed_lines", _draw_into_bbox(
        _speed_lines, size=(120, 80),
    )))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: particles (19 kinds)
# ---------------------------------------------------------------------------
def render_particles(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    """Render one example of each of the 19 particle kinds.

    We instantiate a ParticleEngine just enough to call
    ``_init_base_surfaces`` so we get the same per-kind base sprites
    the game uses, then tint each one with the kind's base color.
    """
    pe = ParticleEngine.__new__(ParticleEngine)
    pe._base_surfs = {}  # normally set in __init__
    pe._init_base_surfaces()
    base_surfs = pe._base_surfs  # set by _init_base_surfaces

    out: list[tuple[str, pygame.Surface]] = []
    for kind in range(P_KIND_COUNT):
        cfg = KIND_CONFIG[kind]
        r, g, b = cfg.base_color
        base = base_surfs.get(kind)
        if base is None:
            # Fallback: a tiny colored square
            base = pygame.Surface((cfg.base_size, cfg.base_size), pygame.SRCALPHA)
            base.fill((*cfg.base_color, 255))
        # Tint via BLEND_RGBA_MULT against a flat color surface
        # (mirrors what the engine's tint cache does).
        tinted = base.copy()
        scratch = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        scratch.fill((r, g, b, 255))
        tinted.blit(scratch, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # For ring-style kinds, scale up to a more visible size.
        from src.systems.particle_engine import (
            P_RING_FILL, P_RING_THICK, P_SHOCKWAVE,
        )
        if kind in (P_SHOCKWAVE, P_RING_FILL, P_RING_THICK):
            scaled_size = max(48, cfg.base_size * 4)
            tinted = pygame.transform.scale(tinted, (scaled_size, scaled_size))
        # Pad for atlas visibility (some are 1x1)
        if tinted.get_width() < 16 or tinted.get_height() < 16:
            padded = pygame.Surface((max(16, tinted.get_width()),
                                     max(16, tinted.get_height())), pygame.SRCALPHA)
            padded.blit(tinted, ((padded.get_width() - tinted.get_width()) // 2,
                                 (padded.get_height() - tinted.get_height()) // 2))
            tinted = padded
        label = _label_for_particle_kind(kind)
        out.append((f"particle_{label}", tinted))

    return out


def _label_for_particle_kind(kind: int) -> str:
    from src.systems.particle_engine import (
        P_DEBRIS, P_DUST, P_ELECTRIC, P_ELECTRIC_ARC, P_FIRE, P_FLASH,
        P_GLOW, P_ION, P_LIGHT_FLASH, P_LINE, P_MUZZLE, P_RING_FILL,
        P_RING_THICK, P_SHOCKWAVE, P_SHRAPNEL, P_SMOKE, P_SPARK,
        P_SQUARE, P_WAKE,
    )
    return {
        P_SPARK: "spark",
        P_SMOKE: "smoke",
        P_SHRAPNEL: "shrapnel",
        P_DEBRIS: "debris",
        P_SHOCKWAVE: "shockwave",
        P_FIRE: "fire",
        P_ELECTRIC: "electric",
        P_DUST: "dust",
        P_MUZZLE: "muzzle",
        P_GLOW: "glow",
        P_ION: "ion",
        P_FLASH: "flash",
        P_RING_FILL: "ring_fill",
        P_RING_THICK: "ring_thick",
        P_ELECTRIC_ARC: "electric_arc",
        P_SQUARE: "square",
        P_LINE: "line",
        P_LIGHT_FLASH: "light_flash",
        P_WAKE: "wake",
    }[kind]


# ---------------------------------------------------------------------------
# CATEGORY: tron_trail
# ---------------------------------------------------------------------------
def render_tron_trail(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    """Render 3 samples of the Tron trail: head, middle, fading end."""
    from src.core.settings import (
        TRON_TRAIL_MAX_AGE_S, TRON_TRAIL_MAX_SEGMENTS, TRON_TRAIL_SEGMENT_LENGTH,
    )

    out: list[tuple[str, pygame.Surface]] = []
    rt = _new_runtime()
    rt._player.x = 0
    rt._player.y = 0

    # Use the real TronTrail constructor so all the color attrs and
    # other state are properly initialized, then pre-populate segments.
    trail = TronTrail(
        max_segments=TRON_TRAIL_MAX_SEGMENTS,
        segment_length=TRON_TRAIL_SEGMENT_LENGTH,
        segment_thickness=4.0,
        max_age=TRON_TRAIL_MAX_AGE_S,
    )

    # Synthesize a curved trail with segments at varying ages. We
    # build a gentle S-curve that fits in 320x320 (world coords).
    cx, cy = 20, 20
    for i in range(80):
        age = i * 0.04
        ang = -math.pi / 2 + 0.02 * (i - 40)  # gentle S-curve
        # The trail moves downward with a slight horizontal sway, all
        # contained within the 0..320 x 0..320 world area.
        x = 160 + math.sin(ang + 1.0) * (i * 1.5)
        y = 20 + i * 3.0
        # TronSegment: (cx, cy, angle, length, thickness, age, max_age)
        seg = TronSegment(cx=x, cy=y, angle=ang, length=6.0, thickness=4.0,
                          age=age, max_age=2.5)
        trail.segments.append(seg)

    rt._tron_trail = trail
    rt._player.state = PlayerState.PROPULSION

    # Full trail — position segments at known world coords, then offset
    # the drawing so the trail lands in the middle of a 320x320 image.
    # Trail spans world x = 20..300, y = 20..300; we offset by (0, 0)
    # and the surface is 320x320, so the trail fills the canvas.
    target = pygame.Surface((320, 320), pygame.SRCALPHA)
    target.fill((0, 0, 0, 0))
    trail.draw(target, (0, 0))
    out.append(("tron_trail_full", _crop_bounds(target, pad=4)))

    # Head: a fresh, short, straight trail — densely bright at the tip.
    trail_short = TronTrail(
        max_segments=TRON_TRAIL_MAX_SEGMENTS,
        segment_length=TRON_TRAIL_SEGMENT_LENGTH,
        max_age=TRON_TRAIL_MAX_AGE_S,
    )
    for i in range(40):
        x = 20 + i * 6
        y = 60
        trail_short.segments.append(TronSegment(
            cx=x, cy=y, angle=0.0, length=6.0, thickness=4.0,
            age=i * 0.02, max_age=2.5,
        ))
    head = pygame.Surface((320, 80), pygame.SRCALPHA)
    head.fill((0, 0, 0, 0))
    trail_short.draw(head, (0, 0))
    out.append(("tron_trail_head", _crop_bounds(head, pad=2)))

    # Fading: an OLD trail — most segments already past their max_age.
    trail_old = TronTrail(
        max_segments=TRON_TRAIL_MAX_SEGMENTS,
        segment_length=TRON_TRAIL_SEGMENT_LENGTH,
        max_age=TRON_TRAIL_MAX_AGE_S,
    )
    for i in range(40):
        x = 20 + i * 6
        y = 60
        # 3.0s / 2.5s max_age → life factor = 0 (invisible) for all but
        # the very newest segment. Use a milder "almost gone" age
        # (2.0s) so the fade is still visible.
        age = 0.5 + i * 0.04
        trail_old.segments.append(TronSegment(
            cx=x, cy=y, angle=0.0, length=6.0, thickness=4.0,
            age=age, max_age=2.5,
        ))
    end = pygame.Surface((320, 80), pygame.SRCALPHA)
    end.fill((0, 0, 0, 0))
    trail_old.draw(end, (0, 0))
    out.append(("tron_trail_fading", _crop_bounds(end, pad=2)))

    return out


# ---------------------------------------------------------------------------
# CATEGORY: hud
# ---------------------------------------------------------------------------
def render_hud(category_dir: Path) -> list[tuple[str, pygame.Surface]]:
    """Render HUD elements at different states."""
    from src.core.settings import (
        PLAYER_DASH_HEAT_MAX, PLAYER_HP_MAX,
    )
    from src.systems.scoring_system import ScoringSystem

    hud = HUD()
    rt = _new_runtime()
    rt._player.x = 60
    rt._player.y = 30

    out: list[tuple[str, pygame.Surface]] = []

    # HP bar at 3 levels
    for hp_pct, label in [(1.0, "full"), (0.6, "60pct"), (0.2, "low")]:
        rt._player.hp = int(PLAYER_HP_MAX * hp_pct)
        rt._player.hp_max = PLAYER_HP_MAX
        size = (130, 14)
        target = pygame.Surface(size, pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        hud._draw_hp_bar(target, rt._player, 0, 0.0)
        out.append((f"hud_hp_{label}", _crop_bounds(target, pad=2)))

    # Heat bar at 3 levels
    for heat_pct, label in [(0.0, "cool"), (0.5, "warm"), (1.0, "hot")]:
        rt._player.dash_heat = PLAYER_DASH_HEAT_MAX * heat_pct
        size = (130, 14)
        target = pygame.Surface(size, pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        hud._draw_overheat_bar(target, rt._player, 0, 0.0)
        out.append((f"hud_heat_{label}", _crop_bounds(target, pad=2)))

    # Rings at 3 levels
    for rings, label in [(0, "0"), (2, "2"), (3, "3")]:
        rt._player.gold_rings = rings
        size = (130, 14)
        target = pygame.Surface(size, pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        hud._draw_gold_rings(target, rt._player, 0, 0.0)
        out.append((f"hud_rings_{label}", _crop_bounds(target, pad=2)))

    # Bombs at 3 levels
    for bombs, label in [(3, "3"), (2, "2"), (0, "0")]:
        rt._player.bombs = bombs
        size = (130, 14)
        target = pygame.Surface(size, pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        hud._draw_bombs(target, rt._player, 0, 0.0)
        out.append((f"hud_bombs_{label}", _crop_bounds(target, pad=2)))

    # Score panel (rendered at right margin, so use the full width)
    sc = ScoringSystem()
    sc.score = 123456
    from src.core.settings import INTERNAL_W
    size = (INTERNAL_W, 24)
    target = pygame.Surface(size, pygame.SRCALPHA)
    target.fill((0, 0, 0, 0))
    hud._draw_score(target, sc)
    out.append(("hud_score", _crop_bounds(target, pad=2)))

    return out


# ---------------------------------------------------------------------------
# Atlas builder
# ---------------------------------------------------------------------------
@dataclass
class Cell:
    name: str
    surface: pygame.Surface


def _build_atlas(cells: list[Cell], out_path: Path,
                 cell_w: int = 96, cell_h: int = 96,
                 label_h: int = 14, pad: int = 6,
                 bg: tuple[int, int, int] = (20, 20, 28),
                 cols: int = 6) -> None:
    """Pack cells into a grid and save the resulting atlas PNG.

    Each cell shows the sprite scaled to fit ``(cell_w, cell_h - label_h)``
    (preserving aspect ratio) plus a text label underneath.
    """
    if not cells:
        return
    n = len(cells)
    rows = (n + cols - 1) // cols
    W = pad + cols * (cell_w + pad)
    H = pad + rows * (cell_h + pad)
    atlas = pygame.Surface((W, H), pygame.SRCALPHA)
    atlas.fill((*bg, 255))

    for i, cell in enumerate(cells):
        r, c = divmod(i, cols)
        cx = pad + c * (cell_w + pad)
        cy = pad + r * (cell_h + pad)
        # Cell background
        cell_bg = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
        cell_bg.fill((40, 40, 52, 255))
        # Inner area (for the sprite)
        inner = cell_bg.subsurface((2, 2, cell_w - 4, cell_h - 4 - label_h))
        # Fit sprite into inner area (preserving aspect)
        sw, sh = cell.surface.get_size()
        avail_w, avail_h = inner.get_size()
        scale = min(avail_w / max(1, sw), avail_h / max(1, sh), 4.0)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        scaled = pygame.transform.scale(cell.surface, (new_w, new_h))
        ix = 2 + (avail_w - new_w) // 2
        iy = 2 + (avail_h - new_h) // 2
        cell_bg.blit(scaled, (ix, iy))
        # Label
        label_surf = _text(cell_bg, cell.name, (220, 220, 230), size=10)
        cell_bg.blit(label_surf, (4, cell_h - label_h + 1))
        atlas.blit(cell_bg, (cx, cy))

    _save_png(atlas, out_path)


# ---------------------------------------------------------------------------
# Category registry
# ---------------------------------------------------------------------------
CATEGORIES: dict[str, Callable[[Path], list[tuple[str, pygame.Surface]]]] = {
    "player": render_player,
    "enemies": render_enemies,
    "boss": render_boss,
    "projectiles": render_projectiles,
    "effects": render_effects,
    "particles": render_particles,
    "tron_trail": render_tron_trail,
    "hud": render_hud,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VOID HUNTER sprite forge — render every procedural sprite.",
    )
    parser.add_argument(
        "category", nargs="?",
        help="category to render (default: all). Use --list to see options.",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="print available categories and exit.",
    )
    parser.add_argument(
        "--atlas-only", action="store_true",
        help="skip individual PNGs, only render the per-category atlases.",
    )
    parser.add_argument(
        "--no-all-atlas", action="store_true",
        help="skip the combined atlas_all.png (smaller output).",
    )
    args = parser.parse_args(argv)

    if args.list:
        print("sprite_forge categories:")
        for name, fn in CATEGORIES.items():
            print(f"  {name:<12} ({fn.__name__})")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    targets: list[str]
    if args.category:
        if args.category not in CATEGORIES:
            print(f"Unknown category: {args.category!r}")
            print(f"Available: {', '.join(CATEGORIES)}")
            return 2
        targets = [args.category]
    else:
        targets = list(CATEGORIES.keys())

    all_cells: list[Cell] = []

    for cat in targets:
        print(f"[forge] {cat} ...", flush=True)
        cat_dir = OUT_DIR / cat
        sprites = CATEGORIES[cat](cat_dir)
        if not args.atlas_only:
            for name, surf in sprites:
                _save_png(surf, cat_dir / f"{name}.png")
        # Atlas for this category
        cells = [Cell(name=name, surface=surf) for name, surf in sprites]
        _build_atlas(cells, OUT_DIR / f"atlas_{cat}.png")
        all_cells.extend(cells)
        print(f"  -> {len(sprites)} sprites + atlas_{cat}.png", flush=True)

    if not args.no_all_atlas and not args.category:
        _build_atlas(all_cells, OUT_DIR / "atlas_all.png", cols=8)
        print(f"[forge] combined atlas: atlas_all.png "
              f"({len(all_cells)} sprites)", flush=True)

    # README
    readme = OUT_DIR / "_README.md"
    readme.write_text(
        "# sprite_forge output\n\n"
        "Generated by `python tools/sprite_forge.py`.\n\n"
        "## Layout\n"
        "- `<category>/<sprite>.png` — individual sprite PNGs\n"
        "- `atlas_<category>.png` — labeled contact sheet for one category\n"
        "- `atlas_all.png` — combined contact sheet (all categories)\n\n"
        f"## Categories ({len(CATEGORIES)})\n"
        + "".join(f"- `{n}`\n" for n in CATEGORIES)
        + "\nRe-run the tool any time you tweak the game's drawing code.\n",
        encoding="utf-8",
    )
    print(f"[forge] done. output: {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
