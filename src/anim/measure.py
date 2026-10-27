"""BLOQUE 74: pixel-level measurement primitives.

Pure functions over a pygame Surface. No manifest, no filesystem, no
caching. Used by the auditor (offline) and by the tests.

Everything works on the ALPHA channel unless the rule says otherwise, so a
transparent canvas never contributes to a measurement.

ONE EXCEPTION to the module-wide alpha cut (ALPHA_MIN = 32): `alpha_centroid`
counts every pixel with alpha != 0, for parity with the shipped runtime's
registration offset. See that function's docstring for why.

Performance: one full-frame pass with get_at over all 60 GOLIATH frames
costs 0.09 s, which is fine for an offline tool. numpy is NOT used --
BLOQUE 58.14 allows it for the pause-screen lowpass only.
"""
from __future__ import annotations

import pygame

from src.anim.manifest import DetectRule, WarmRule

ALPHA_MIN = 32


def alpha_centroid(surf: pygame.Surface) -> tuple[float, float] | None:
    """Alpha-weighted centroid of the silhouette.

    None when the sprite is fully transparent. This is the correction that
    cancels the per-frame registration error: the AI generator drew the
    character at a different offset inside the canvas in every frame, and
    the offset needed to put its visual centre of mass back on the anchor
    spans -16..+20 px across the 60 GOLIATH frames.

    ALPHA CUT: this function counts every pixel with alpha != 0, NOT the
    alpha > ALPHA_MIN (32) cut the rest of this module uses. That is
    deliberate parity with the shipped runtime's
    `get_sprite_centroid_offset` (src/ui/scenes.py), which tests `a == 0`
    too: the centroid has to agree with the runtime's registration offset
    to the pixel, so it may not use a stricter cut than the runtime does.
    """
    w, h = surf.get_size()
    sum_a = sum_x = sum_y = 0
    for y in range(h):
        for x in range(w):
            alpha = surf.get_at((x, y))[3]
            if alpha == 0:
                continue
            sum_a += alpha
            sum_x += x * alpha
            sum_y += y * alpha
    if sum_a == 0:
        return None
    return (sum_x / sum_a, sum_y / sum_a)


def silhouette_bbox(
    surf: pygame.Surface, threshold: int = ALPHA_MIN
) -> tuple[int, int, int, int] | None:
    """(left, top, right, bottom) of the silhouette, exclusive on the right.

    None when the sprite is fully transparent.
    """
    w, h = surf.get_size()
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if surf.get_at((x, y))[3] > threshold:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y
    if right < 0:
        return None
    return (left, top, right + 1, bottom + 1)


def silhouette_height(
    surf: pygame.Surface,
    rule: DetectRule | None = None,
    drop_warm: bool = False,
    threshold: int = ALPHA_MIN,
) -> int | None:
    """Height of the silhouette, optionally dropping the warm pixels.

    Height is a LINEAR dimension and is far less pose-sensitive than area:
    area is dominated by the pose (a frame with an outstretched arm has
    many more opaque pixels at the same body size), which is why the
    pipeline measures height and not area.
    """
    w, h = surf.get_size()
    warm = rule.warm_fallback if (rule is not None and drop_warm) else None
    top, bottom = h, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if a <= threshold:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            if y < top:
                top = y
            if y > bottom:
                bottom = y
    if bottom < 0:
        return None
    return bottom + 1 - top


def color_centroid(
    surf: pygame.Surface,
    rule: DetectRule,
    band: tuple[int, int] | None = None,
    col_range: tuple[int, int] | None = None,
    warm: WarmRule | None = None,
) -> tuple[float, float] | None:
    """Centroid of the pixels that satisfy a colour rule.

    `band` is (top, bottom) in rows; `col_range` is (first, last) in
    columns. When either is None it falls back to the window the RULE
    declares (`head_band` and `col_range` respectively), and to the whole
    surface only when the rule declares no window at all. None when
    nothing matches.

    `warm` is an optional WarmRule: when given, the pixels it matches are
    dropped before the signature is applied. The PROBE needs this -- the
    brass signature also matches two of the beam's colours, so without the
    warm filter the probe latches onto the beam.
    """
    w, h = surf.get_size()
    # A rule that declares no window scans the WHOLE surface. The windows
    # are optional on purpose: a default of (0, 0) would be truthy and
    # would silently produce an empty scan window.
    if band is None:
        band = rule.head_band if rule.head_band is not None else (0, h)
    if col_range is None:
        col_range = rule.col_range if rule.col_range is not None else (0, w)
    top, bottom = band
    first, last = col_range

    hits: list[tuple[int, int]] = []
    for y in range(max(0, top), min(h, bottom)):
        for x in range(max(0, first), min(w, last)):
            r, g, b, a = surf.get_at((x, y))
            if a <= ALPHA_MIN:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            if r < rule.r_min:
                continue
            if rule.g_min and g < rule.g_min:
                continue
            if rule.b_max < 255 and b > rule.b_max:
                continue
            if rule.rg_min and (r - g) < rule.rg_min:
                continue
            if rule.r_minus_b_min and (r - b) < rule.r_minus_b_min:
                continue
            hits.append((x, y))
    if not hits:
        return None
    return (
        sum(p[0] for p in hits) / len(hits),
        sum(p[1] for p in hits) / len(hits),
    )


def plate_ellipse(
    surf: pygame.Surface, rule: DetectRule, drop_warm: bool = False
) -> tuple[float, float, float, float] | None:
    """Ellipse of the last solid run of each row inside the band.

    This is the SHAPE measurement. The plate shares its palette with the
    body (160,110,50), so colour cannot identify it; the only usable
    signature is the outline. The rule walks the band, takes the last
    contiguous run of opaque pixels in each row, and keeps the runs that
    reach at least `min_col`.

    With `drop_warm` the warm pixels (the baked eye beam) are treated as
    background, exactly like the shipped runtime does.

    Returns (cx, cy, rx, ry) or None when no run qualifies.
    """
    w, h = surf.get_size()
    if rule.band is None:
        return None
    band_top, band_bottom = rule.band
    if band_bottom <= band_top:
        return None
    warm = rule.warm_fallback if drop_warm else None

    points: list[tuple[int, int]] = []
    for y in range(max(0, band_top), min(h, band_bottom)):
        end = -1
        for x in range(w - 1, -1, -1):
            r, g, b, a = surf.get_at((x, y))
            if a <= ALPHA_MIN:
                continue
            if warm is not None and warm.matches(r, g, b):
                continue
            end = x
            break
        if end < rule.min_col:
            continue
        start = end
        while start - 1 >= 0:
            r, g, b, a = surf.get_at((start - 1, y))
            if a <= ALPHA_MIN:
                break
            if warm is not None and warm.matches(r, g, b):
                break
            start -= 1
        first = max(start, rule.min_col)
        points.extend((x, y) for x in range(first, end + 1))

    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (x1 - x0) / 2.0, (y1 - y0) / 2.0)


def credible_ellipse(
    surf: pygame.Surface, rule: DetectRule
) -> tuple[float, float, float, float] | None:
    """The two-pass measurement, exactly like the shipped runtime.

    The plain silhouette is measured first. Only when that result is not
    credible -- because the baked beam extended the contour -- is the
    measurement retried with the warm pixels dropped.

    Returns the credible ellipse, or None when neither pass gives one.
    """
    plain = plate_ellipse(surf, rule, drop_warm=False)
    if _credible(plain, rule):
        return plain
    if rule.warm_fallback is None:
        return None
    warm = plate_ellipse(surf, rule, drop_warm=True)
    if _credible(warm, rule):
        return warm
    return None


def _credible(
    ellipse: tuple[float, float, float, float] | None, rule: DetectRule
) -> bool:
    """True when the ellipse is inside the rule's believable range."""
    if ellipse is None:
        return False
    rx, ry = ellipse[2], ellipse[3]
    return (
        rule.rx_range[0] <= rx <= rule.rx_range[1]
        and rule.ry_range[0] <= ry <= rule.ry_range[1]
    )


def interpolate(values: list[float | None], index: int) -> float | None:
    """Fill a missing measurement from its neighbours.

    Catmull-Rom through the nearest measured values on each side. When only
    one measured neighbour exists on a side, that side's tangent collapses
    and the curve becomes a smooth one that still passes through both
    measured endpoints (it is NOT a straight line: at the midpoint of a gap
    it returns the midpoint, but between the endpoints it bows slightly).
    Returns None when there is nothing to interpolate from.

    This is inbetweening: the shield plate moves smoothly with the arm, so
    the frames where the art forgot it can be reconstructed from the ones
    where it is there.
    """
    if index < 0 or index >= len(values):
        return None
    current = values[index]
    if current is not None:
        return float(current)

    left = index - 1
    while left >= 0 and values[left] is None:
        left -= 1
    right = index + 1
    while right < len(values) and values[right] is None:
        right += 1

    left_value = values[left] if left >= 0 else None
    right_value = values[right] if right < len(values) else None

    # The two guards are nested rather than chained so that the type of
    # each neighbour is known on its own branch.
    if left_value is None:
        if right_value is None:
            return None
        return float(right_value)
    if right_value is None:
        return float(left_value)

    # Catmull-Rom needs two points on each side.
    left2 = left - 1
    while left2 >= 0 and values[left2] is None:
        left2 -= 1
    right2 = right + 1
    while right2 < len(values) and values[right2] is None:
        right2 += 1
    # The scans above stop on a measured value, so left2 / right2 hold one
    # whenever the index is in range. The None checks below are the
    # type-safe spelling of that invariant for mypy; they are NOT a
    # separate fallback path and cannot be reached in practice.
    p0 = values[left2] if left2 >= 0 else None
    p3 = values[right2] if right2 < len(values) else None
    if p0 is None:
        p0 = left_value
    if p3 is None:
        p3 = right_value

    span = right - left
    t = (index - left) / span
    t2 = t * t
    t3 = t2 * t
    return float(
        0.5
        * (
            (2 * left_value)
            + (-p0 + right_value) * t
            + (2 * p0 - 5 * left_value + 4 * right_value - p3) * t2
            + (-p0 + 3 * left_value - 3 * right_value + p3) * t3
        )
    )
