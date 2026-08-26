"""Composition helpers — assemble a final frame from background + ship layer + effects.

The video frames are generated in "internal" reference resolution (e.g. 270×480 for
a 1080×1920 output at 4× super-sampling) and then upscaled to the final resolution
with NEAREST to enforce the pixel grid.
"""
from __future__ import annotations
from PIL import Image
from . import effects, palette


def new_canvas(width: int, height: int) -> Image.Image:
    """Create a new RGBA canvas with the Void Hunter deep-void background."""
    return Image.new("RGBA", (width, height), palette.DEEP_VOID + (255,))


def composite(
    background: Image.Image,
    ship_layer: Image.Image | None,
    effects_layers: list[Image.Image] | None = None,
) -> Image.Image:
    """Compose a final frame from background + ship + optional effect layers.

    All inputs must be the same size. Returns a new RGBA image.
    """
    if background.mode != "RGBA":
        background = background.convert("RGBA")
    out = background.copy()
    if ship_layer is not None:
        if ship_layer.mode != "RGBA":
            ship_layer = ship_layer.convert("RGBA")
        out.alpha_composite(ship_layer)
    if effects_layers:
        for layer in effects_layers:
            if layer.mode != "RGBA":
                layer = layer.convert("RGBA")
            out.alpha_composite(layer)
    return out


def draw_nebula(
    canvas: Image.Image,
    color: tuple[int, int, int] = palette.NEON_PURPLE,
    intensity: float = 0.5,
    center: tuple[float, float] = (0.5, 0.5),
    radius: float = 0.6,
) -> None:
    """Draw a soft circular nebula glow centered on the canvas. Mutates in place."""
    from PIL import ImageDraw, ImageFilter
    w, h = canvas.size
    cx = int(w * center[0])
    cy = int(h * center[1])
    r = int(min(w, h) * radius)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Draw concentric circles with decreasing alpha
    for i in range(20, 0, -1):
        rr = int(r * (i / 20))
        a = int(255 * intensity * (1 - i / 20) * 0.3)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (a,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius=max(2, r // 15)))
    canvas.alpha_composite(layer)


def draw_distant_planet(
    canvas: Image.Image,
    cx: float,
    cy: float,
    radius: int,
    body_color: tuple[int, int, int] = palette.NEON_MAGENTA_DIM,
    glow_color: tuple[int, int, int] = palette.NEON_MAGENTA,
) -> None:
    """Draw a distant planet as a soft glowing sphere. Mutates in place."""
    from PIL import ImageDraw, ImageFilter
    # Outer glow
    glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    glow_r = int(radius * 1.5)
    for i in range(8, 0, -1):
        rr = glow_r - i * 4
        a = int(40 * (i / 8))
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=glow_color + (a,))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow_r // 6))
    canvas.alpha_composite(glow_layer)
    # Body
    draw = ImageDraw.Draw(canvas)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=body_color)
    # Highlight
    hr = max(2, radius // 3)
    draw.ellipse(
        [cx - radius // 2 - hr // 2, cy - radius // 2 - hr // 2,
         cx - radius // 2 + hr // 2, cy - radius // 2 + hr // 2],
        fill=palette.NEON_MAGENTA_BRIGHT,
    )


def draw_asteroid(
    canvas: Image.Image,
    cx: float,
    cy: float,
    radius: int,
    rotation_deg: float = 0.0,
    color_base: tuple[int, int, int] = (60, 50, 70),
    color_dark: tuple[int, int, int] = (30, 25, 40),
) -> None:
    """Draw a small pixel-art asteroid. Mutates in place."""
    from PIL import ImageDraw
    import math
    draw = ImageDraw.Draw(canvas)
    # Generate a jagged polygon outline
    n_points = 8
    points = []
    for i in range(n_points):
        a = (i / n_points) * math.tau + math.radians(rotation_deg)
        r_var = radius * (0.7 + 0.3 * ((i * 7) % 5) / 5)
        x = cx + math.cos(a) * r_var
        y = cy + math.sin(a) * r_var
        points.append((x, y))
    draw.polygon(points, fill=color_base, outline=color_dark)
    # Small craters
    for i in range(2):
        a = (i / 2) * math.tau + math.radians(rotation_deg + 30)
        cxr = cx + math.cos(a) * radius * 0.4
        cyr = cy + math.sin(a) * radius * 0.4
        cr = max(1, radius // 4)
        draw.ellipse([cxr - cr, cyr - cr, cxr + cr, cyr + cr], fill=color_dark)


def draw_pixel_text(
    canvas: Image.Image,
    text: str,
    cx: float,
    cy: float,
    color: tuple[int, int, int] = palette.STAR_WHITE,
    pixel_size: int = 1,
    font_path: str | None = None,
    glow: bool = False,
    char_spacing: int = 1,
) -> None:
    """Draw text using the project's 5x7 pixel font, scaled up with NEAREST.

    Args:
        canvas: RGBA image
        text: text to draw
        cx, cy: center position
        color: text color
        pixel_size: how big to scale (1 = 5x7 source, 2 = 10x14, etc.)
        glow: add a soft neon glow around the text
        char_spacing: source pixels between chars (default 1)
    """
    from PIL import ImageDraw
    from . import pixel_font
    bitmap = pixel_font.text_bitmap(text)
    if not bitmap:
        return
    bm_h = len(bitmap)
    bm_w = len(bitmap[0])
    # Total dimensions in source pixels
    total_w = bm_w * pixel_size
    total_h = bm_h * pixel_size
    px0 = int(cx - total_w / 2)
    py0 = int(cy - total_h / 2)
    draw = ImageDraw.Draw(canvas)
    for row in range(bm_h):
        for col in range(bm_w):
            if bitmap[row][col] == 1:
                x0 = px0 + col * pixel_size
                y0 = py0 + row * pixel_size
                draw.rectangle(
                    [x0, y0, x0 + pixel_size - 1, y0 + pixel_size - 1],
                    fill=color,
                )
    if glow:
        from .effects import add_glow_halo
        tmp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        for row in range(bm_h):
            for col in range(bm_w):
                if bitmap[row][col] == 1:
                    x0 = px0 + col * pixel_size
                    y0 = py0 + row * pixel_size
                    td.rectangle(
                        [x0, y0, x0 + pixel_size - 1, y0 + pixel_size - 1],
                        fill=color,
                    )
        glowed = add_glow_halo(tmp, color=color, intensity=0.4, blur_radius=3)
        canvas.alpha_composite(glowed)


def draw_pil_text(
    canvas: Image.Image,
    text: str,
    cx: float,
    cy: float,
    color: tuple[int, int, int] = palette.STAR_WHITE,
    size: int = 12,
    glow: bool = False,
) -> None:
    """Draw text using PIL's default font. (Legacy — prefer draw_pixel_text for in-game UI.)"""
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.load_default(size=size)
    except TypeError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(canvas)
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    px = int(cx - w / 2)
    py = int(cy - h / 2)
    draw.text((px, py), text, fill=color, font=font)
