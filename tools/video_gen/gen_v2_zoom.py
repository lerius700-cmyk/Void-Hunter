"""V2 generator — Ship close-up dolly-back to gameplay position.

10s @ 30 FPS = 300 frames. The camera starts CLOSE to the ship_01 and dollies
back continuously, revealing nebula → asteroids → planet in successive parallax
layers. The ship reduces in apparent scale from ~3x native down to ~1x (gameplay).

Visual timeline:
  0.0-2.0s  : Ship close-up, black + stars only
  2.0-3.5s  : Nebula layer fades in (parallax back-1)
  3.5-5.0s  : Asteroids start drifting (parallax mid-1)
  5.0-6.5s  : Planet/void anomaly fades in (parallax far-1)
  6.5-8.0s  : All 3 layers visible, ship continues dolly back
  8.0-9.5s  : Ship near gameplay position
  9.5-10.0s : Final ease-out, ship lands in gameplay position
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

from common import palette, effects, ship_overlay, composition


# Default output sizes
REF_W_STANDALONE = 270
REF_H_STANDALONE = 480
REF_W_INGAME = 240
REF_H_INGAME = 360

FPS = 30
DURATION_S = 10.0
TOTAL_FRAMES = int(FPS * DURATION_S)  # 300

# Output dir
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "frames" / "v2"


def _ease_out_cubic(t: float) -> float:
    """ease-out cubic. t in [0, 1]."""
    return 1.0 - pow(1.0 - t, 3)


def _ease_in_out_cubic(t: float) -> float:
    """ease-in-out cubic. t in [0, 1]."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def _draw_distant_stars(
    canvas: Image.Image,
    rng: random.Random,
    count: int = 60,
    brightness_range: tuple[int, int] = (60, 120),
) -> None:
    """Draw a small set of dim background stars (used for the void background)."""
    draw = ImageDraw.Draw(canvas)
    for _ in range(count):
        x = rng.randint(0, canvas.width - 1)
        y = rng.randint(0, canvas.height - 1)
        b = rng.randint(*brightness_range)
        draw.point((x, y), fill=(b, b, int(b * 1.1)))


def _draw_planet_with_rings(
    canvas: Image.Image,
    cx: float,
    cy: float,
    radius: int,
    body_color: tuple[int, int, int] = palette.NEON_MAGENTA_DIM,
    glow_color: tuple[int, int, int] = palette.NEON_MAGENTA,
    ring_color: tuple[int, int, int] = palette.NEON_PURPLE,
    has_rings: bool = True,
) -> None:
    """Draw a planet with optional rings (Saturn-like)."""
    composition.draw_distant_planet(canvas, cx=cx, cy=cy, radius=radius,
                                     body_color=body_color, glow_color=glow_color)
    if has_rings and radius > 6:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(canvas)
        # Ring: horizontal ellipse, slightly tilted (use a few segments)
        for i in range(radius, int(radius * 1.8), 2):
            # Draw a thin ellipse outline
            draw.ellipse(
                [cx - i, cy - i // 4, cx + i, cy + i // 4],
                outline=ring_color, width=1,
            )


def generate_one_frame(
    frame_index: int,
    ref_w: int,
    ref_h: int,
    rng: random.Random,
) -> Image.Image:
    """Generate a single frame at the internal reference resolution."""
    t = frame_index / FPS  # 0..10 seconds
    canvas = composition.new_canvas(ref_w, ref_h)

    # ---------- SHIP SCALE (dolly back) ----------
    # Ship starts at scale 3.0 (close-up) and reduces to scale 0.7 (gameplay distance)
    # Use ease-in-out for the dolly, with a final ease-out in the last 1.5s
    if t < 8.5:
        dolly_t = t / 8.5  # 0..1 for the main dolly
        ship_scale = 3.0 - _ease_in_out_cubic(dolly_t) * (3.0 - 0.7)
    else:
        # Final ease-out: 8.5-10s
        final_t = (t - 8.5) / 1.5
        ship_scale = 0.7 - _ease_out_cubic(final_t) * 0.0  # already at 0.7, ease out

    # Ship position: stays near the bottom-center as it shrinks
    # Start at y=0.40 (closer to center for close-up), drift to y=0.65 (gameplay position)
    ship_cy_start = ref_h * 0.40
    ship_cy_end = ref_h * 0.65
    if t < 8.5:
        ship_cy = ship_cy_start + (ship_cy_end - ship_cy_start) * _ease_in_out_cubic(t / 8.5)
    else:
        final_t = (t - 8.5) / 1.5
        ship_cy = ship_cy_end + (ship_cy_end - ship_cy_start) * 0.05 * _ease_out_cubic(final_t)
    ship_cx = ref_w * 0.5

    # ---------- BACKGROUND: stars always visible ----------
    _draw_distant_stars(canvas, rng, count=80)

    # ---------- LAYER 1: NEBULA (fades in starting at 2.0s) ----------
    if t > 2.0:
        nebula_t = min(1.0, (t - 2.0) / 1.5)
        # Two nebula clouds, parallax back-1 (slow movement)
        nebula_x = ref_w * 0.3 - nebula_t * 5  # very slow drift
        nebula_y = ref_h * 0.7 - nebula_t * 2
        composition.draw_nebula(
            canvas,
            color=palette.NEON_PURPLE,
            intensity=0.6 * nebula_t,
            center=(0.35, 0.75),
            radius=0.5,
        )
        # Second nebula, magenta, top-right
        composition.draw_nebula(
            canvas,
            color=palette.NEON_MAGENTA,
            intensity=0.4 * nebula_t,
            center=(0.75, 0.25),
            radius=0.4,
        )

    # ---------- LAYER 2: ASTEROIDS (start drifting at 3.5s) ----------
    if t > 3.5:
        asteroid_t = t - 3.5
        # 3 asteroids, different sizes and speeds (parallax mid-1)
        for i, (ax0, ay0, size, speed) in enumerate([
            (ref_w * 0.15, ref_h * 0.5, 5, 18),
            (ref_w * 0.85, ref_h * 0.35, 4, 22),
            (ref_w * 0.50, ref_h * 0.85, 6, 12),
        ]):
            ax = ax0
            ay = ay0 + asteroid_t * speed
            ay = ay % (ref_h + size * 4) - size
            rotation = asteroid_t * 25 + i * 60
            composition.draw_asteroid(
                canvas, cx=ax, cy=ay, radius=size,
                rotation_deg=rotation, color_base=(80, 70, 95), color_dark=(40, 35, 55),
            )

    # ---------- LAYER 3: PLANET/VOID (fades in starting at 5.0s) ----------
    if t > 5.0:
        planet_t = min(1.0, (t - 5.0) / 1.5)
        planet_intensity = planet_t
        # Distant planet top-left, very slow parallax (far-1)
        planet_cx = ref_w * 0.20 + planet_t * 2  # very slow drift
        planet_cy = ref_h * 0.30
        planet_radius = int(20 * planet_intensity)
        if planet_radius >= 4:
            # Draw with strong glow that grows as it fades in
            from PIL import ImageDraw, ImageFilter
            glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            glow_r = int(planet_radius * 2.0)
            for i in range(8, 0, -1):
                rr = max(1, glow_r - i * 3)
                a = int(60 * (i / 8) * planet_intensity)
                gd.ellipse([planet_cx - rr, planet_cy - rr, planet_cx + rr, planet_cy + rr],
                           fill=palette.NEON_MAGENTA + (a,))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=max(1, glow_r // 4)))
            canvas.alpha_composite(glow_layer)
            # Body
            draw = ImageDraw.Draw(canvas)
            body_color = palette.blend(palette.DARK_INDIGO, palette.NEON_MAGENTA_DIM, planet_intensity)
            draw.ellipse(
                [planet_cx - planet_radius, planet_cy - planet_radius,
                 planet_cx + planet_radius, planet_cy + planet_radius],
                fill=body_color,
            )
            # Ring (Saturn-style, gives it the "void planet" feel)
            if planet_radius >= 8:
                for i in range(planet_radius + 2, int(planet_radius * 1.7), 2):
                    ring_alpha = int(120 * planet_intensity)
                    draw.ellipse(
                        [planet_cx - i, planet_cy - i // 3, planet_cx + i, planet_cy + i // 3],
                        outline=(palette.NEON_PURPLE[0], palette.NEON_PURPLE[1], palette.NEON_PURPLE[2], ring_alpha),
                        width=1,
                    )

    # ---------- SHIP OVERLAY ----------
    # Slight idle bob
    bob_phase = t * 1.5
    bob_amp = 1.5 if ship_scale < 1.5 else 0  # no bob when huge
    ship_overlay.blit_ship_01(
        canvas, cx=ship_cx, cy=ship_cy, scale=ship_scale,
        anim_phase=(t * 4) % 1.0, use_propulsion=True,
        bob_amplitude=bob_amp, bob_phase=bob_phase,
    )

    # ---------- EFFECTS ----------
    canvas = effects.add_scanlines(canvas, spacing=2, alpha=25)
    canvas = effects.add_vignette(canvas, strength=0.4)

    return canvas


def generate_all_frames(
    output_dir: Path,
    ref_w: int = REF_W_STANDALONE,
    ref_h: int = REF_H_STANDALONE,
    fps: int = FPS,
    duration_s: float = DURATION_S,
    seed: int = 0xBEEF2026,
) -> int:
    """Generate all V2 frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    total_frames = int(fps * duration_s)
    for i in range(total_frames):
        if i % 10 == 0:
            print(f"  V2 frame {i}/{total_frames}  (t={i/fps:.2f}s)")
        frame = generate_one_frame(i, ref_w, ref_h, rng)
        out_path = output_dir / f"frame_{i:04d}.png"
        frame.save(out_path)
    print(f"  V2 done: {total_frames} frames in {output_dir}")
    return total_frames


if __name__ == "__main__":
    import sys
    out = OUTPUT_DIR
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    print(f"Generating V2 frames to {out}")
    print(f"  Internal resolution: {REF_W_STANDALONE}×{REF_H_STANDALONE}")
    print(f"  Final (NEAREST upscale): 1080×1920")
    print(f"  Total frames: {TOTAL_FRAMES} @ {FPS} FPS = {DURATION_S}s")
    n = generate_all_frames(out)
    print(f"Done. {n} frames written.")
