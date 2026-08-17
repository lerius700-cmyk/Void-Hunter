"""Per-weapon bullet VFX: code-driven animation layered on top of the
single-frame laser sprite.

Why code-driven instead of 6-frame sprite sheets? The model that
generated the laser sheets produced inconsistent frames across the
strip — round shapes (acid, void, fireball, ice) shifted position
between frames, and the heart shape was unrecognizable at 8x8. Rather
than fight the model for 6 good frames per weapon, we keep ONE good
frame per weapon and animate it in code: alpha pulse, scale pulse, and
a soft halo. This is more controllable, takes zero per-weapon art time,
and reads well at 16-bit internal resolution (480x270 scaled 4x).

The VFX is per-weapon via the WEAPON_VFX_PARAMS table. Each entry is a
WeaponVFX dataclass. `compute(bullet, t)` returns the alpha (0-255),
scale factor, and halo params to apply at draw time.

The module is stdlib-only (dataclasses + math) so it can be unit
tested without pygame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class WeaponVFX:
    """Per-weapon VFX parameters. All time is in seconds.

    `alpha_pulse_amp` (0..1) + `alpha_pulse_freq` (Hz) drive a sine
    wave that modulates the sprite's per-frame alpha. 0 = no pulse
    (full alpha always).

    `scale_pulse_amp` (0..1) + `scale_pulse_freq` (Hz) drive a sine
    wave that scales the sprite between 1.0 and 1+amp. 0 = static.

    `erratic` replaces the alpha sine with a deterministic per-bullet
    pseudo-random jitter — for the green acid it gives a "bubbling"
    look.

    `halo_color` is the RGB tint of a soft glow drawn behind the
    sprite. None = no halo. `halo_size` is the radius in pixels.
    `halo_alpha` is the opacity (0-255). `halo_pulse` adds a slow sine
    modulation on top of the base alpha so the halo "breathes".
    """
    alpha_pulse_amp: float = 0.0
    alpha_pulse_freq: float = 0.0
    scale_pulse_amp: float = 0.0
    scale_pulse_freq: float = 0.0
    erratic: bool = False
    halo_color: tuple | None = None
    halo_size: int = 0
    halo_alpha: int = 0
    halo_pulse: bool = False


# Per-weapon tuning. Index = weapon id (0..9) matching Player.WEAPON_*.
#  0 yellow plasma  — classic 16-bit bolt
#  1 red pulse      — bright pulse, red glow
#  2 blue ion       — thin fast needle, cyan glow
#  3 green acid     — round orb, bubbling alpha, green glow
#  4 purple void    — dark orb, alpha pulse, purple glow
#  5 orange fireball— round orb, scale pulse, big orange glow
#  6 white piercing — fast needle, no FX (the speed is the identity)
#  7 pink heart     — heart, gentle scale + alpha, pink glow
#  8 cyan ice       — shard, alpha pulse, cyan glow
#  9 rainbow streak — long horizontal streak, alpha pulse, no halo
#                     (the rainbow gradient is the identity)
WEAPON_VFX_PARAMS: tuple[WeaponVFX, ...] = (
    # 0 yellow plasma
    WeaponVFX(alpha_pulse_amp=0.30, alpha_pulse_freq=4.0),
    # 1 red pulse
    WeaponVFX(alpha_pulse_amp=0.30, alpha_pulse_freq=6.0,
              halo_color=(255, 80, 80), halo_size=6, halo_alpha=80,
              halo_pulse=True),
    # 2 blue ion
    WeaponVFX(halo_color=(100, 200, 255), halo_size=5, halo_alpha=70),
    # 3 green acid (erratic alpha + scale pulse + green halo)
    WeaponVFX(alpha_pulse_amp=0.30, alpha_pulse_freq=7.0,
              scale_pulse_amp=0.20, scale_pulse_freq=5.0,
              erratic=True,
              halo_color=(80, 255, 120), halo_size=7, halo_alpha=100),
    # 4 purple void
    WeaponVFX(alpha_pulse_amp=0.40, alpha_pulse_freq=5.0,
              halo_color=(180, 80, 255), halo_size=6, halo_alpha=80),
    # 5 orange fireball
    WeaponVFX(alpha_pulse_amp=0.20, alpha_pulse_freq=4.0,
              scale_pulse_amp=0.30, scale_pulse_freq=3.0,
              halo_color=(255, 140, 40), halo_size=7, halo_alpha=110),
    # 6 white piercing (no FX)
    WeaponVFX(),
    # 7 pink heart
    WeaponVFX(alpha_pulse_amp=0.20, alpha_pulse_freq=2.0,
              scale_pulse_amp=0.15, scale_pulse_freq=2.0,
              halo_color=(255, 150, 200), halo_size=8, halo_alpha=90),
    # 8 cyan ice
    WeaponVFX(alpha_pulse_amp=0.30, alpha_pulse_freq=3.0,
              halo_color=(140, 220, 255), halo_size=6, halo_alpha=90),
    # 9 rainbow (alpha pulse only — the gradient is the identity)
    WeaponVFX(alpha_pulse_amp=0.40, alpha_pulse_freq=5.0),
)


@dataclass
class BulletVFX:
    """Result of computing the VFX for a single bullet at time `t`."""
    alpha: int
    scale: float
    halo_color: tuple | None
    halo_size: int
    halo_alpha: int


def _hash01(*args: int) -> float:
    """Deterministic pseudo-random in [0, 1) from a tuple of ints.

    Used to make per-bullet "erratic" alpha jitter stable across
    frames (so the bullet's alpha doesn't flicker randomly between
    consecutive renders of the same bullet).
    """
    h = 0
    for a in args:
        h = (h * 31 + a) & 0xFFFFFFFF
    # Mix to scatter bits.
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFFFF) / float(0x1000000)


def compute(bullet, t: float) -> BulletVFX:
    """Compute the VFX for `bullet` at scene time `t` (seconds).

    `bullet` needs `weapon: int` and `spawn_time: float`. Returns a
    BulletVFX with the alpha (0-255), scale factor (1.0 = no scale),
    and halo parameters. halo_color is None for weapons without a halo.
    """
    weapon = getattr(bullet, "weapon", 0)
    if not (0 <= weapon < len(WEAPON_VFX_PARAMS)):
        weapon = 0
    params = WEAPON_VFX_PARAMS[weapon]
    # Per-bullet time since spawn. Wraps to 0 if bullet has no
    # spawn_time yet (first frame after construction).
    local_t = max(0.0, t - getattr(bullet, "spawn_time", t))
    # Alpha
    if params.alpha_pulse_amp > 0.0 and params.alpha_pulse_freq > 0.0:
        if params.erratic:
            # Per-bullet hash blended with sine so consecutive bullets
            # have different "jitter" but the same bullet looks
            # consistent from frame to frame within a small window.
            base = math.sin(local_t * 2 * math.pi * params.alpha_pulse_freq)
            jitter = _hash01(weapon, int(bullet.spawn_time * 1000),
                             int(local_t * 30)) * 2 - 1
            pulse = base * 0.5 + jitter * 0.5
        else:
            pulse = math.sin(local_t * 2 * math.pi * params.alpha_pulse_freq)
        alpha_f = 1.0 - params.alpha_pulse_amp * (0.5 - 0.5 * pulse)
    else:
        alpha_f = 1.0
    alpha = max(0, min(255, int(alpha_f * 255)))
    # Scale
    if params.scale_pulse_amp > 0.0 and params.scale_pulse_freq > 0.0:
        s = math.sin(local_t * 2 * math.pi * params.scale_pulse_freq)
        scale = 1.0 + params.scale_pulse_amp * (0.5 + 0.5 * s)
    else:
        scale = 1.0
    # Halo
    halo_alpha = params.halo_alpha
    if params.halo_pulse and halo_alpha > 0:
        halo_alpha = int(halo_alpha * (0.6 + 0.4 * (
            0.5 + 0.5 * math.sin(local_t * 2 * math.pi * 2.5)
        )))
    return BulletVFX(
        alpha=alpha,
        scale=scale,
        halo_color=params.halo_color,
        halo_size=params.halo_size,
        halo_alpha=halo_alpha,
    )
