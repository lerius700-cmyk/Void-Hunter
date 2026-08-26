"""Ship overlay — blit ship_01 (the Arwing) onto a frame at a given position and scale.

The ship is loaded from the actual game sprites (Assets/sprites/player_ships/ship_01/).
This guarantees the in-game video shows the same ship the player will pilot.

The 64×64 frames have a dark-gray checker background (NOT alpha-transparent) baked
in by the sprite generator. We key it out by making any dark-gray pixel (R==G==B
and value < 80) transparent before compositing.

Animation alternates between idle and propulsion frames based on t (time).
"""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
from PIL import Image
from . import palette


_SHIP_01_DIR: Path = Path(__file__).resolve().parents[3] / "Assets" / "sprites" / "player_ships" / "ship_01"
_SPRITES_TOP_DIR: Path = Path(__file__).resolve().parents[3] / "Assets" / "sprites"

_idle_frames: list[Image.Image] | None = None
_propulsion_frames: list[Image.Image] | None = None
_loaded = False


def _chroma_key(img: Image.Image, max_gray: int = 150) -> Image.Image:
    """Make dark-gray pixels transparent. Keeps chromatic pixels (ship) opaque.

    A pixel is "background" if it's grayscale (R == G == B) AND its value is
    below max_gray. The ship uses saturated colors (cyan, red, yellow) which
    are NOT grayscale, so the chroma key only affects the dark background.

    Higher max_gray = more aggressive (catches more edge anti-aliasing) but may
    also clip dark outlines on the ship itself.
    """
    arr = np.array(img, dtype=np.uint8)
    if arr.shape[-1] == 4:
        r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    else:
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        a = np.full_like(r, 255)
    # Background = grayscale AND dark
    is_gray = (r == g) & (g == b)
    is_dark = r < max_gray
    is_bg = is_gray & is_dark
    # Set bg pixels to fully transparent
    new_a = np.where(is_bg, 0, a)
    # Also slightly fade partial-alpha bg pixels (the "fog" from anti-aliased edges)
    # For pixels that are NOT bg but also not strongly chromatic, reduce alpha
    chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    # Low chroma = likely background edge. Fade them.
    fade = (chroma < 30) & (new_a > 0)
    new_a = np.where(fade, (new_a * chroma // 60).astype(np.uint8), new_a)
    out = np.stack([r, g, b, new_a], axis=-1)
    return Image.fromarray(out, mode="RGBA")


def _load_ship_frames() -> None:
    """Load the 8 idle + 8 propulsion frames for ship_01. Cached on first call."""
    global _idle_frames, _propulsion_frames, _loaded
    if _loaded:
        return
    _idle_frames = []
    for i in range(8):
        path = _SHIP_01_DIR / "idle" / f"frame_{i:02d}.png"
        if path.exists():
            _idle_frames.append(_chroma_key(Image.open(path).convert("RGBA")))
        else:
            _idle_frames.append(Image.new("RGBA", (32, 32), (0, 0, 0, 0)))
    _propulsion_frames = []
    for i in range(8):
        path = _SHIP_01_DIR / "propulsion" / f"frame_{i:02d}.png"
        if path.exists():
            _propulsion_frames.append(_chroma_key(Image.open(path).convert("RGBA")))
        else:
            _propulsion_frames.append(Image.new("RGBA", (32, 32), (0, 0, 0, 0)))
    _loaded = True


def get_ship_size() -> tuple[int, int]:
    """Return (width, height) of a single ship frame in source pixels."""
    _load_ship_frames()
    if _idle_frames and _idle_frames[0].width > 0:
        return (_idle_frames[0].width, _idle_frames[0].height)
    return (32, 32)


def blit_ship_01(
    target: Image.Image,
    cx: float,
    cy: float,
    scale: float = 1.0,
    anim_phase: float = 0.0,
    use_propulsion: bool = False,
    rotation_deg: float = 0.0,
    bob_amplitude: float = 0.0,
    bob_phase: float = 0.0,
) -> None:
    """Blit ship_01 onto target, centered at (cx, cy), at given scale.

    Args:
        target: RGBA image to draw onto
        cx, cy: center position in target coordinates
        scale: 1.0 = native size, 2.0 = 2x larger, etc.
        anim_phase: 0..1, which sub-frame of the 8-frame rotation
        use_propulsion: if True, use propulsion sprites (flame); else idle
        rotation_deg: rotate the ship (in degrees, CCW positive)
        bob_amplitude: how much to bob vertically (in pixels)
        bob_phase: 0..1 phase of the bob cycle
    """
    _load_ship_frames()
    frames = _propulsion_frames if use_propulsion else _idle_frames
    if not frames:
        return
    idx = int(anim_phase * 8) % 8
    sprite = frames[idx]
    if bob_amplitude > 0:
        cy = cy + math.sin(bob_phase * math.tau) * bob_amplitude
    # Scale
    if scale != 1.0:
        new_w = max(1, int(sprite.width * scale))
        new_h = max(1, int(sprite.height * scale))
        sprite = sprite.resize((new_w, new_h), Image.Resampling.NEAREST)
    if rotation_deg != 0.0:
        sprite = sprite.rotate(rotation_deg, resample=Image.Resampling.NEAREST, expand=True)
    # Blit centered
    px = int(cx - sprite.width / 2)
    py = int(cy - sprite.height / 2)
    target.alpha_composite(sprite, (px, py))


def draw_ship_engine_glow(
    target: Image.Image,
    cx: float,
    cy: float,
    scale: float = 1.0,
    phase: float = 0.0,
) -> None:
    """Draw a soft cyan/yellow engine glow under the ship's engines.
    Called in addition to blit_ship_01 for that 'real engine' feel.
    """
    from PIL import ImageDraw
    if target.mode != "RGBA":
        return
    draw = ImageDraw.Draw(target)
    # The ship_01_base has two engines spaced ~30% of the body width apart
    # In the small idle/propulsion frames (~28-30px wide), engines are at ~x-5 and ~x+5
    # Adjust by scale
    eng_x_offset = int(6 * scale)
    eng_y = int(cy + 4 * scale)
    eng_radius = max(2, int(3 * scale + 2 * abs(math.sin(phase * math.tau))))
    # Two glows: warm yellow inside, fading to orange
    for ox in (-eng_x_offset, eng_x_offset):
        x = int(cx) + ox
        # Outer orange
        draw.ellipse(
            [x - eng_radius * 2, eng_y - eng_radius * 2,
             x + eng_radius * 2, eng_y + eng_radius * 2],
            fill=palette.FLAME_ORANGE,
        )
        # Inner yellow
        draw.ellipse(
            [x - eng_radius, eng_y - eng_radius,
             x + eng_radius, eng_y + eng_radius],
            fill=palette.FLAME_YELLOW,
        )


# Stand-in procedural Arwing when sprite assets are unavailable.
def draw_arwing_fallback(
    target: Image.Image,
    cx: float,
    cy: float,
    scale: float = 4.0,
) -> None:
    """Draw a simple procedural Arwing delta wing if the sprite assets are missing."""
    from PIL import ImageDraw
    if target.mode != "RGBA":
        return
    draw = ImageDraw.Draw(target)
    s = scale
    body_main = palette.NEON_CYAN
    body_dark = palette.NEON_CYAN_DARK
    canopy = palette.NEON_CYAN_BRIGHT
    engine_y = palette.FLAME_YELLOW
    # Wings delta silhouette (centered on cx, cy)
    body_y_top = int(cy - 6 * s)
    body_y_bot = int(cy + 6 * s)
    wing_tip_x = int(cx + 16 * s)
    wing_root_x = int(cx + 4 * s)
    # Polygon: nose (cx, body_y_top) → right wing tip (wing_tip_x, cy) → tail (cx, body_y_bot) → left wing tip
    polygon = [
        (cx, body_y_top),
        (wing_tip_x, cy - 2 * s),
        (wing_root_x, cy),
        (wing_tip_x, cy + 2 * s),
        (cx, body_y_bot),
        (wing_root_x - 2 * wing_root_x + cx, cy + 2 * s),
        (2 * cx - wing_tip_x, cy + 2 * s),
        (2 * cx - wing_root_x, cy),
        (2 * cx - wing_tip_x, cy - 2 * s),
    ]
    draw.polygon(polygon, fill=body_dark)
    # Canopy
    draw.rectangle(
        [int(cx - 2 * s), int(cy - 3 * s), int(cx + 2 * s), int(cy)],
        fill=canopy,
    )
    # Engine flames
    for ox in (-int(5 * s), int(5 * s)):
        draw.rectangle(
            [int(cx + ox - s), int(cy + 4 * s), int(cx + ox + s), int(cy + 7 * s)],
            fill=engine_y,
        )
