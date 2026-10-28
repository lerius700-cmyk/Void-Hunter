"""BLOQUE 74: rendering one part of a clip.

A part is one of four things:

    "frames"      one PNG per frame of the current clip
    "ellipse"     a procedural primitive (the invisible shield oval)
    "point"       an anchor that draws nothing (the eye)
    "procedural"  a runtime effect; never baked into the art

Every part is positioned relative to the canvas anchor, not to the world
anchor directly: the body is blitted at (origin - canvas/2 + body_offset)
and the shield ellipse at (origin - canvas/2 + body_offset + plate + nudge).
Sharing the body offset is what keeps the oval glued to the plate.

The base is the CANVAS half-size, not the viewport half-size: the canvas
holds the character and its anchor sits at the canvas centre, so the
canvas' top-left corner lands on (origin - canvas/2 + body_offset) and the
character's visual centre of mass lands on `origin` -- which is the same
arithmetic the shipped runtime does with its 96x80 canvas.
"""
from __future__ import annotations

import pygame

from src.anim.anchors import FrameAnchor
from src.anim.manifest import Part

# The cold-steel colour of an uncharged shield: the same (96, 104, 124)
# the shipped runtime uses for `_shield_charge_color(0.0)`.
COLD_STEEL = (96, 104, 124)

# BLOQUE 67 (user request): the shield oval is INVISIBLE. The shipped
# runtime draws only the heat layer (which grows with the charge) and the
# impact flash -- the oval itself is never painted. The flag below keeps
# the drawing path available (and reviewable) without changing what the
# player sees; the GEOMETRY is what the runtime needs, and that comes from
# `shield_ellipse_rect`.
DRAW_SHIELD_OVAL = False

# BLOQUE 74: the CANONICAL plate centre and the CANONICAL radii.
#
# The centre is the median of the 60 measured plate centres (the baked
# table's cx spans 57.0..63.5 and its cy 39.5..42.5). It is where the
# plate sits on the canvas when a frame carries no measurement of its own.
CANONICAL_PLATE_CENTRE = (60.5, 40.5)

# The canonical radii (R, RX, RY), used when the manifest declares none.
# They are the BLOQUE 67 user-approved sizes, the same ones the runtime
# keeps in GOLIATH_SHIELD_R / _RX / _RY.
DEFAULT_RADII = (11.0, 11.0, 17.0)

# A frame that is missing from the anchor table still has a body: only its
# REGISTRATION CORRECTION is unknown, so it degrades to a plain centred
# blit instead of making the character disappear. The oval keeps the
# canonical geometry -- see `canonical_shield_ellipse`.
NO_OFFSET = FrameAnchor(
    body_dx=0,
    body_dy=0,
    eye=None,
    eye_source="missing",
    shield=None,
    shield_source="missing",
)


def canonical_shield_ellipse(part: Part | None) -> tuple[float, float, float, float]:
    """The canonical ellipse: the manifest's radii at the canonical centre.

    BLOQUE 74: this is the POLICY for a frame whose plate could not be
    resolved. The alternative -- no ellipse at all -- would delete the
    shield's hitbox and leave the laser with nowhere to come from, so the
    oval keeps the canonical size at the canonical place instead of
    vanishing.
    """
    radii = part.radii if part is not None else None
    if radii is None:
        radii = DEFAULT_RADII
    _r, rx, ry = radii
    return (CANONICAL_PLATE_CENTRE[0], CANONICAL_PLATE_CENTRE[1], rx, ry)


def _base(
    anchor: FrameAnchor, origin: tuple[int, int], canvas: tuple[int, int]
) -> tuple[int, int]:
    """The top-left corner of the frame's canvas in world coordinates.

    Every part of the frame shares this base: the body is the canvas
    itself, and the oval is the plate's position inside that canvas. That
    shared base is what keeps the oval glued to the plate.
    """
    ox, oy = origin
    return (
        ox - canvas[0] // 2 + anchor.body_dx,
        oy - canvas[1] // 2 + anchor.body_dy,
    )


def shield_ellipse_rect(
    part: Part,
    anchor: FrameAnchor | None,
    origin: tuple[int, int],
    canvas: tuple[int, int],
) -> pygame.Rect | None:
    """The world-space rect of the shield oval, or None when unresolved.

    The oval's centre is the plate's own position inside the canvas, moved
    by the part's `offset` (the nudge) and sized by the part's `scale` (the
    horizontal thinning). Both come from the manifest, so the manifest and
    the baked measurement can never disagree.

    BLOQUE 74: a frame whose plate could NOT be resolved gets the CANONICAL
    ellipse -- the manifest's radii at the canonical centre -- instead of no
    oval at all. The oval is invisible either way (DRAW_SHIELD_OVAL is
    False); what matters is that the geometry the hitbox and the laser
    read still exists.
    """
    if anchor is None:
        anchor = NO_OFFSET
    if anchor.shield is None:
        cx, cy, rx, ry = canonical_shield_ellipse(part)
    else:
        cx, cy, rx, ry = anchor.shield
    base_x, base_y = _base(anchor, origin, canvas)
    centre_x = int(base_x + cx + part.offset[0])
    centre_y = int(base_y + cy + part.offset[1])
    scaled_rx = max(2, int(round(rx * part.scale[0])))
    scaled_ry = max(2, int(round(ry * part.scale[1])))
    return pygame.Rect(
        centre_x - scaled_rx,
        centre_y - scaled_ry,
        scaled_rx * 2,
        scaled_ry * 2,
    )


def draw_part(
    target: pygame.Surface,
    part: Part,
    surf: pygame.Surface | None,
    anchor: FrameAnchor | None,
    origin: tuple[int, int],
    canvas: tuple[int, int],
) -> None:
    """Draw one part at a world position.

    `origin` is the world anchor (the boss's position on screen).
    `canvas` is the set's canvas size, (width, height).

    A frame that is missing from the anchor table still draws its body
    (without the registration correction); the oval falls back to the
    canonical geometry and the eye stays undrawn.
    """
    if anchor is None:
        if part.draw == "frames" and surf is None:
            return
        # A frame that is not in the table still draws: the body without
        # its registration correction, and the oval at the canonical
        # place (the oval is invisible anyway -- DRAW_SHIELD_OVAL is False).
        anchor = NO_OFFSET

    if part.draw == "frames":
        if surf is None:
            return
        base_x, base_y = _base(anchor, origin, canvas)
        target.blit(surf, (base_x, base_y))
        return

    if part.draw == "ellipse":
        rect = shield_ellipse_rect(part, anchor, origin, canvas)
        if rect is None:
            return
        if not DRAW_SHIELD_OVAL:
            # The oval is invisible by design (BLOQUE 67): the runtime
            # paints the heat layer and the impact flash instead.
            return
        pygame.draw.ellipse(target, COLD_STEEL, rect)
        return

    if part.draw == "point":
        # The eye is an ANCHOR, not a picture: the runtime reads its
        # position from the anchor table to launch the beam.
        return

    if part.draw == "procedural":
        # The eye beam is drawn by the runtime, which owns its colour ramp
        # and its charging state. Nothing to do here yet.
        return
