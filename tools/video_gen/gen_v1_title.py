"""V1 generator — Title screen video with logo reveal + ambient + demo loop.

Produces a sequence of PNG frames at `ref_w × ref_h` (internal pixel-art resolution)
that can be:
- encoded to mp4 with encode_mp4.py (standalone)
- assembled into a sprite-sheet with build_spritesheet.py (in-game)

Pipeline per frame:
  1. Background (starfield + nebula, varies with phase)
  2. Parallax asteroids (vary with phase)
  3. Ship overlay (real ship_01 sprite from Assets/sprites/...)
  4. Effects (glow, chromatic aberration on reveal, scanlines, vignette)
  5. Logo text (píxel-disolve during reveal, settled with glow otherwise)
  6. "PRESS ANY KEY" text (fades in after reveal)

Output: tools/video_gen/output/frames/v1/frame_0000.png ... frame_0359.png
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

from common import palette, effects, ship_overlay, composition, pixel_font


# Default output sizes — used as "internal" reference before NEAREST upscale.
REF_W_STANDALONE = 270  # 1080 / 4
REF_H_STANDALONE = 480  # 1920 / 4
REF_W_INGAME = 240
REF_H_INGAME = 360

FPS = 30
DURATION_S = 12.0
TOTAL_FRAMES = int(FPS * DURATION_S)  # 360

# Output dirs
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "frames" / "v1"


def _prepare_logo_reveal(text: str, n_pixels: int, start_frame: int, end_frame: int,
                          rng: random.Random) -> list[tuple[int, int, int]]:
    """Pre-compute the per-pixel reveal frame for a píxel-dissolve text effect.

    Returns a list of (px, py, reveal_frame) for each lit pixel of the text.
    reveal_frame is in absolute frame numbers.
    """
    bitmap = pixel_font.text_bitmap(text)
    h = len(bitmap)
    w = len(bitmap[0]) if h > 0 else 0
    # Assign a random reveal frame to each lit pixel
    pixels = []
    for py in range(h):
        for px in range(w):
            if bitmap[py][px] == 1:
                # Slight jitter so they don't all reveal at once
                rf = rng.randint(start_frame, end_frame)
                pixels.append((px, py, rf))
    return pixels, w, h


def _draw_logo_disolve(
    canvas: Image.Image,
    pixels: list[tuple[int, int, int]],
    bm_w: int,
    bm_h: int,
    pixel_scale: int,
    current_frame: int,
    color: tuple[int, int, int],
    cx: float,
    cy: float,
) -> None:
    """Draw the text bitmap where only pixels with reveal_frame <= current_frame are shown."""
    # Bitmap total pixel size in canvas
    total_w = bm_w * pixel_scale
    total_h = bm_h * pixel_scale
    # Center position
    px0 = int(cx - total_w / 2)
    py0 = int(cy - total_h / 2)
    draw = ImageDraw.Draw(canvas)
    for (px, py, rf) in pixels:
        if rf <= current_frame:
            x0 = px0 + px * pixel_scale
            y0 = py0 + py * pixel_scale
            draw.rectangle([x0, y0, x0 + pixel_scale - 1, y0 + pixel_scale - 1], fill=color)


def _draw_logo_glow_pulse(
    canvas: Image.Image,
    pixels: list[tuple[int, int, int]],
    bm_w: int,
    bm_h: int,
    pixel_scale: int,
    cx: float,
    cy: float,
    color: tuple[int, int, int],
    pulse_phase: float,
) -> None:
    """Draw the full logo with a soft glow halo (after reveal is complete)."""
    # Render the full logo into a temp image, then add glow
    total_w = bm_w * pixel_scale
    total_h = bm_h * pixel_scale
    tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    px0 = int(cx - total_w / 2)
    py0 = int(cy - total_h / 2)
    for (px, py, _) in pixels:
        x0 = px0 + px * pixel_scale
        y0 = py0 + py * pixel_scale
        draw.rectangle([x0, y0, x0 + pixel_scale - 1, y0 + pixel_scale - 1], fill=color)
    # Add glow halo (varies with pulse)
    intensity = 0.4 + 0.3 * (0.5 + 0.5 * math.sin(pulse_phase * math.tau))
    glowed = effects.add_glow_halo(tmp, color=color, intensity=intensity, blur_radius=4)
    canvas.alpha_composite(glowed)


def generate_one_frame(
    frame_index: int,
    ref_w: int,
    ref_h: int,
    rng: random.Random,
    logo_reveal: list[tuple[int, int, int]],
    logo_w: int,
    logo_h: int,
    pixel_scale: int,
) -> Image.Image:
    """Generate a single frame at the internal reference resolution."""
    t = frame_index / FPS  # time in seconds
    canvas = composition.new_canvas(ref_w, ref_h)

    # The full timeline:
    #   0.0s  - 4.0s  : LOGO REVEAL (plays once)
    #   4.0s  - 12.0s : LOOP (8s, ambient + demo sequential)
    #
    # In the loop, ONE 8s cycle = 3.5s ambient + 4.5s demo.
    # For the in-game video, when the video ends at frame 359, the player
    # should see the loop start over at frame 120 (start of ambient).

    LOGO_REVEAL_END = 4.0  # frame 120
    LOOP_DURATION = 8.0    # 4.0 to 12.0
    AMBIENT_DURATION = 3.5 # 0.0 to 3.5 of loop
    DEMO_DURATION = 4.5    # 3.5 to 8.0 of loop

    in_loop = t >= LOGO_REVEAL_END
    if in_loop:
        cycle_t = (t - LOGO_REVEAL_END) % LOOP_DURATION
    else:
        cycle_t = -1.0  # sentinel: not in loop

    # ----------------- BACKGROUND -----------------
    # Starfield — slight parallax, scroll slowly
    scroll = int(t * 6)  # 6 px/sec downward
    bg = effects.make_parallax_starfield(ref_w, ref_h, count=80, scroll_offset=scroll, rng=rng)
    canvas.alpha_composite(bg.convert("RGBA"))

    # Nebula fades in starting at t=0.5s
    if t > 0.5:
        nebula_intensity = min(0.5, (t - 0.5) * 0.3)
        composition.draw_nebula(
            canvas,
            color=palette.NEON_PURPLE,
            intensity=nebula_intensity,
            center=(0.5, 0.75),
            radius=0.7,
        )

    # ----------------- AMBIENT PHASE (3.5s of loop) -----------------
    # Ship does a slow arc from left to right, exits off-screen
    if 0.0 <= cycle_t < AMBIENT_DURATION:
        arc_t = cycle_t / AMBIENT_DURATION  # 0..1
        # X: from -15% to 115% of width
        sx = -ref_w * 0.15 + arc_t * ref_w * 1.3
        # Y: arcs from upper to mid to upper
        sy = ref_h * 0.30 + math.sin(arc_t * math.pi) * ref_h * 0.15
        # Use propulsion sprite, scale up for prominence
        ship_overlay.blit_ship_01(
            canvas, cx=sx, cy=sy, scale=2.5,
            anim_phase=cycle_t * 2, use_propulsion=True,
            rotation_deg=90.0,  # facing right
        )

    # ----------------- DEMO PHASE (4.5s of loop) -----------------
    if AMBIENT_DURATION <= cycle_t < LOOP_DURATION:
        demo_t = cycle_t - AMBIENT_DURATION  # 0..4.5
        # Player ship on left, slightly moving up
        psx = ref_w * 0.30
        psy = ref_h * 0.55 - demo_t * 8
        ship_overlay.blit_ship_01(
            canvas, cx=psx, cy=psy, scale=2.0,
            anim_phase=demo_t * 4, use_propulsion=True,
        )
        # Enemy ship on right, moving down
        esx = ref_w * 0.70
        esy = ref_h * 0.30 + demo_t * 8
        _draw_enemy_dart(canvas, cx=esx, cy=esy, scale=2.0)
        # Bullets
        _draw_demo_bullets(canvas, demo_t, ref_w, ref_h)
        # Explosion at t=2.4s of demo
        if 2.4 < demo_t < 3.0:
            _draw_explosion(canvas, cx=esx, cy=esy, t=(demo_t - 2.4) / 0.6, rng=rng)

    # ----------------- ASTEROIDS -----------------
    # 1-2 asteroids drifting through, visible during loop phases
    if in_loop:
        for i, (a_x0, a_y0, a_size, a_speed, a_phase) in enumerate([
            (ref_w * 0.25, ref_h * -0.05, 6, 20, 0.0),    # upper-left, slow
            (ref_w * 0.75, ref_h * -0.10, 5, 28, 0.4),    # upper-right, faster
        ]):
            a_t = cycle_t + a_phase
            ax = a_x0
            ay = a_y0 + a_t * a_speed
            ay = ay % (ref_h + a_size * 4) - a_size
            rotation = (cycle_t + a_phase) * 30 + i * 45
            composition.draw_asteroid(
                canvas, cx=ax, cy=ay, radius=a_size,
                rotation_deg=rotation, color_base=(70, 60, 85), color_dark=(35, 30, 50),
            )

    # ----------------- LOGO REVEAL -----------------
    # Phase 1 (frames 30-119): ship silhouette enters + logo dissolve
    # Phase 2 (frames 120+): logo stable with glow pulse
    if frame_index >= 30 and frame_index < 120:
        _draw_logo_disolve(
            canvas, logo_reveal, logo_w, logo_h, pixel_scale,
            frame_index, color=palette.NEON_CYAN_BRIGHT,
            cx=ref_w * 0.5, cy=ref_h * 0.30,
        )
    elif frame_index >= 120:
        pulse = (frame_index - 120) / 60.0
        _draw_logo_glow_pulse(
            canvas, logo_reveal, logo_w, logo_h, pixel_scale,
            cx=ref_w * 0.5, cy=ref_h * 0.30,
            color=palette.NEON_CYAN_BRIGHT, pulse_phase=pulse,
        )

    # Brief chromatic aberration at frame 119 (right when logo settles)
    if frame_index == 119 or frame_index == 120:
        canvas = effects.chromatic_aberration(canvas, offset=3)

    # ----------------- "PRESS ANY KEY" -----------------
    if frame_index >= 120:
        # Blinks at 2Hz
        blink = int((frame_index - 120) / 15) % 2 == 0
        if blink:
            composition.draw_pixel_text(
                canvas, "PRESS ANY KEY",
                cx=ref_w * 0.5, cy=ref_h * 0.60,
                color=palette.FLAME_YELLOW, pixel_size=2, glow=True,
            )

    # "C: CREDITS" in corner
    composition.draw_pixel_text(
        canvas, "C: CREDITS",
        cx=ref_w * 0.80, cy=ref_h * 0.95,
        color=(120, 120, 140), pixel_size=1,
    )

    # ----------------- EFFECTS -----------------
    # Scanlines (always)
    canvas = effects.add_scanlines(canvas, spacing=2, alpha=30)
    # Vignette
    canvas = effects.add_vignette(canvas, strength=0.5)

    return canvas


def _draw_enemy_dart(canvas: Image.Image, cx: float, cy: float, scale: float = 1.0) -> None:
    """Draw a small enemy ship (red dart, faces down)."""
    if canvas.mode != "RGBA":
        return
    draw = ImageDraw.Draw(canvas)
    s = scale
    # Body (red)
    body = [
        (cx, cy - 6 * s),
        (cx + 5 * s, cy),
        (cx, cy + 6 * s),
        (cx - 5 * s, cy),
    ]
    draw.polygon(body, fill=palette.NEON_HOT_PINK)
    # Outline
    draw.polygon(body, outline=palette.FLAME_RED)
    # Eye
    draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=palette.FLAME_YELLOW)


def _draw_demo_bullets(canvas: Image.Image, demo_t: float, ref_w: int, ref_h: int) -> None:
    """Draw a few bullets in the demo loop. demo_t in seconds [0, 4.5)."""
    if canvas.mode != "RGBA":
        return
    draw = ImageDraw.Draw(canvas)
    # Player bullets going up
    for i in range(3):
        b_t = demo_t - i * 0.25
        if b_t < 0 or b_t > 3.0:
            continue
        bx = ref_w * 0.30
        by = ref_h * 0.55 - b_t * 12 - 10
        draw.rectangle([bx - 1, by - 3, bx + 1, by + 3], fill=palette.FLAME_YELLOW)
    # Enemy bullets going down
    for i in range(2):
        b_t = demo_t - i * 0.5
        if b_t < 0 or b_t > 3.0:
            continue
        bx = ref_w * 0.70
        by = ref_h * 0.30 + b_t * 10 + 10
        draw.rectangle([bx - 1, by - 3, bx + 1, by + 3], fill=palette.FLAME_RED)


def _draw_explosion(canvas: Image.Image, cx: float, cy: float, t: float, rng: random.Random) -> None:
    """Draw a small explosion. t in 0..1."""
    if canvas.mode != "RGBA":
        return
    draw = ImageDraw.Draw(canvas)
    n_particles = 12
    for i in range(n_particles):
        a = (i / n_particles) * math.tau + rng.random() * 0.3
        speed = 20 + t * 30
        d = speed * t
        x = cx + math.cos(a) * d
        y = cy + math.sin(a) * d
        r = max(1, int(3 * (1 - t)))
        color = palette.FLAME_YELLOW if i % 2 == 0 else palette.FLAME_RED
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def generate_all_frames(
    output_dir: Path,
    ref_w: int = REF_W_STANDALONE,
    ref_h: int = REF_H_STANDALONE,
    fps: int = FPS,
    duration_s: float = DURATION_S,
    pixel_scale: int = 2,
    seed: int = 0xCAFE2026,
) -> int:
    """Generate all V1 frames. Returns the number of frames written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    # Pre-compute the logo dissolve
    logo_reveal, logo_w, logo_h = _prepare_logo_reveal(
        "VOID HUNTER", n_pixels=0,
        start_frame=60, end_frame=115,
        rng=rng,
    )
    total_frames = int(fps * duration_s)
    for i in range(total_frames):
        if i % 10 == 0:
            print(f"  V1 frame {i}/{total_frames}  (t={i/fps:.2f}s)")
        frame = generate_one_frame(
            i, ref_w, ref_h, rng,
            logo_reveal, logo_w, logo_h, pixel_scale,
        )
        out_path = output_dir / f"frame_{i:04d}.png"
        frame.save(out_path)
    print(f"  V1 done: {total_frames} frames in {output_dir}")
    return total_frames


if __name__ == "__main__":
    import sys
    out = OUTPUT_DIR
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    print(f"Generating V1 frames to {out}")
    print(f"  Internal resolution: {REF_W_STANDALONE}×{REF_H_STANDALONE}")
    print(f"  Final (NEAREST upscale): 1080×1920")
    print(f"  Total frames: {TOTAL_FRAMES} @ {FPS} FPS = {DURATION_S}s")
    n = generate_all_frames(out)
    print(f"Done. {n} frames written.")
