"""BLOQUE 58.8: capture each of the 5 wave patterns.

Renders the pattern result to a 320x480 surface and saves a PNG.
For each pattern we show 3 frames (t=0, t=mid, t=end) so the user
can see the visual difference between:
  - bezier (curved): BEZIER_SWEEP, LEADER_FOLLOWER_CHAIN, PINCER_CROSS
  - rigid (straight): V_FORMATION, DICE_FIVE_GRID
"""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
import math
import random
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()
pygame.display.set_mode((320, 480))

from src.systems.wave_patterns import (
    WavePattern, WavePatternKind, make_pattern, ProceduralWaveManager,
)
from src.core.settings import INTERNAL_W, INTERNAL_H


def render_pattern_at_t(pattern: WavePattern, t: float, level: int = 3, seed: int = 42) -> pygame.Surface:
    """Render a pattern's ship positions at parameter t in [0,1]."""
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((8, 8, 20))  # dark space background

    rng = random.Random(seed)
    result = pattern.generate(rng, level=level)

    # First, draw any bezier path lines (so ships appear on top)
    bezier_drawn = set()
    for ship in result.ships:
        if "p0" in ship.extra:
            key = (ship.extra["p0"], ship.extra["p1"], ship.extra["p2"], ship.extra["p3"])
            if key in bezier_drawn:
                continue
            bezier_drawn.add(key)
            # Draw the bezier curve
            prev_pt = None
            for tt in [i / 40.0 for i in range(41)]:
                pt = _bezier_point(tt, ship.extra["p0"], ship.extra["p1"],
                                    ship.extra["p2"], ship.extra["p3"])
                if 0 <= pt[0] < INTERNAL_W and 0 <= pt[1] < INTERNAL_H:
                    if prev_pt is not None:
                        pygame.draw.line(surf, (40, 40, 60), prev_pt, pt, 1)
                    prev_pt = pt
                else:
                    prev_pt = None

    # Now draw the ships
    for ship in result.ships:
        # For BEZIER_SWEEP / LEADER_FOLLOWER_CHAIN / PINCER_CROSS: ships
        # share the same path. Render each ship at its t_offset (so they
        # appear as a "train" along the path).
        # For V_FORMATION / DICE_FIVE_GRID: rigid, render at t directly.
        if "p0" in ship.extra and "wing_offsets" not in ship.extra:
            # Each ship at (t + ship.t_offset) along the bezier
            t_ship = (t + ship.t_offset) % 1.0
            x, y = _bezier_point(t_ship, ship.extra["p0"], ship.extra["p1"],
                                  ship.extra["p2"], ship.extra["p3"])
        else:
            x, y = compute_ship_position(ship, t)
        # Skip off-screen
        if not (0 <= x < INTERNAL_W and 0 <= y < INTERNAL_H):
            continue
        # Draw a simple diamond shape
        color = ship.color or (200, 200, 200)
        size = 6
        # Diamond
        points = [
            (int(x), int(y) - size),
            (int(x) + size, int(y)),
            (int(x), int(y) + size),
            (int(x) - size, int(y)),
        ]
        pygame.draw.polygon(surf, color, points)
        # Inner highlight
        pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), 2)

    return surf


def compute_ship_position(ship, t: float) -> tuple[float, float]:
    """Compute the ship position at parameter t in [0,1]."""
    kind = ship.extra.get("side", "default")

    # BEZIER_SWEEP / LEADER_FOLLOWER_CHAIN / PINCER_CROSS: bezier
    if "p0" in ship.extra:
        return _bezier_point(t, ship.extra["p0"], ship.extra["p1"],
                              ship.extra["p2"], ship.extra["p3"])

    # DICE_FIVE_GRID: linear with control point curve
    if "start_x" in ship.extra and "control_x" in ship.extra:
        sx, sy = ship.extra["start_x"], ship.extra["start_y"]
        ex, ey = ship.extra["end_x"], ship.extra["end_y"]
        cx, cy = ship.extra["control_x"], ship.extra["control_y"]
        # Quadratic bezier for the central point, then add dice offset
        u = 1 - t
        center_x = u*u*sx + 2*u*t*cx + t*t*ex
        center_y = u*u*sy + 2*u*t*cy + t*t*ey
        # Apply dice offset (slot determines which corner)
        if ship.extra.get("dice_offsets"):
            ox, oy = ship.extra["dice_offsets"][ship.slot]
            return (center_x + ox, center_y + oy)
        return (center_x, center_y)

    # V_FORMATION: linear with wing offsets
    if "wing_offsets" in ship.extra:
        ox, oy = ship.extra["wing_offsets"][ship.slot]
        ex, ey = ship.extra["entry_x"] + ox, ship.extra["entry_y"] + oy
        # Move in a straight line (no curve)
        end_x = ex + ship.extra["direction"] * 400
        end_y = ey + INTERNAL_H + 40
        return (ex + (end_x - ex) * t, ey + (end_y - ey) * t)

    return (ship.spawn_x, ship.spawn_y)


def _bezier_point(t, p0, p1, p2, p3):
    u = 1 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def main():
    out_dir = ROOT / "tools" / "playtest_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    patterns = [
        ("bezier_sweep", WavePatternKind.BEZIER_SWEEP, 42),
        ("v_formation", WavePatternKind.V_FORMATION, 43),
        ("leader_chain", WavePatternKind.LEADER_FOLLOWER_CHAIN, 44),
        ("dice_grid", WavePatternKind.DICE_FIVE_GRID, 45),
        ("pincer_cross", WavePatternKind.PINCER_CROSS, 46),
    ]

    # Capture each pattern at 3 time points
    # For V_FORMATION: ships go off-screen at t > 0.4, so use early t
    # For others: t = 0.5 is mid-screen
    pattern_t = {
        "bezier_sweep": [0.0, 0.5, 0.95],
        "v_formation":  [0.0, 0.2, 0.4],
        "leader_chain": [0.0, 0.5, 0.95],
        "dice_grid":     [0.0, 0.5, 0.95],
        "pincer_cross":  [0.0, 0.5, 0.95],
    }
    t_labels = ["start", "mid", "end"]

    for name, kind, seed in patterns:
        pattern = make_pattern(kind)
        for t, label in zip(pattern_t[name], t_labels):
            surf = render_pattern_at_t(pattern, t, level=5, seed=seed)
            out = out_dir / f"pattern_{name}_{label}_v1.28.png"
            pygame.image.save(surf, str(out))
            print(f"Saved {out.name}")

    # Also capture the manager's pick sequence for floor 1-5
    mgr = ProceduralWaveManager(seed=42, floor=1)
    surf = pygame.Surface((INTERNAL_W, INTERNAL_H))
    surf.fill((8, 8, 20))
    font = pygame.font.Font(None, 16)
    y_off = 10
    text = font.render("Floor 1 picks (seed=42):", True, (200, 200, 200))
    surf.blit(text, (10, y_off))
    y_off += 24
    for i in range(6):
        mgr.set_floor(1)
        r = mgr.pick_pattern(level=i + 1)
        text = font.render(f"  wave {i+1}: {r.kind.value} ({len(r.ships)} ships)",
                          True, (200, 200, 200))
        surf.blit(text, (10, y_off))
        y_off += 18
    out = out_dir / "pattern_manager_floor1_v1.28.png"
    pygame.image.save(surf, str(out))
    print(f"Saved {out.name}")

    print(f"\nAll captures in {out_dir}/")


if __name__ == "__main__":
    main()
