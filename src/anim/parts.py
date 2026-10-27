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

# A frame that is missing from the anchor table still has a body: only its
# REGISTRATION CORRECTION is unknown, so it degrades to a plain centred
# blit instead of making the character disappear. The oval stays absent --
# without a measurement there is no credible position for it.
NO_OFFSET = FrameAnchor(
    body_dx=0,
    body_dy=0,
    eye=None,
    eye_source="missing",
    shield=None,
    shield_source="missing",
)


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

    None when the frame carries no anchor, or when the plate is UNRESOLVED:
    an unresolved feature has no credible position, and guessing one would
    put the oval in the corner of the screen.
    """
    if anchor is None or anchor.shield is None:
        return None
    base_x, base_y = _base(anchor, origin, canvas)
    cx, cy, rx, ry = anchor.shield
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
    (without the registration correction); everything that needs a
    measurement -- the oval, the eye -- stays undrawn.
    """
    if anchor is None:
        if part.draw != "frames" or surf is None:
            return
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
            # Unresolved plate: there is no credible position to draw it
            # at, and the canvas origin is not one of them.
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
