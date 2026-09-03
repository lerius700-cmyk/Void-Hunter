"""FlightFormation \u2014 preset slot shapes for enemy groups (BLOQUE 58.6x).

A FlightFormation is a set of (dx, dy) offsets from the path's center
position. When the path's center is at (cx, cy) at time t, each ship in
the formation sits at (cx + dx, cy + dy) where (dx, dy) is its slot
offset.

Presets (BLOQUE 58.6x, requested by user):
  - V          : chevron, point forward
  - LINE       : straight horizontal/vertical row
  - DIAMOND    : 5-slot diamond
  - SQUARE     : 4 corners + center
  - WEDGE      : right-pointing > (mirrored V)
  - CIRCLE     : N slots evenly around a circle
  - TRIANGLE   : 3-slot (or N-slot) triangle pointing forward
  - HALF_V     : half-chevron, like > or <
  - CUSTOM     : user-defined offsets (from JSON or inline list)

Slot count is the number of ships in the formation. For shapes that
have a fixed geometry (V, DIAMOND, SQUARE, TRIANGLE), the requested
count may be truncated or expanded.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Sequence


class FormationKind(str, Enum):
    V = "v"
    LINE = "line"
    DIAMOND = "diamond"
    SQUARE = "square"
    WEDGE = "wedge"
    CIRCLE = "circle"
    TRIANGLE = "triangle"
    HALF_V = "half_v"
    CUSTOM = "custom"
    FLOWER_OF_LIFE = "flower_of_life"
    VESICA_PISCIS = "vesica_piscis"
    FIBONACFI_SPIRAL = "fibonacfi_spiral"  # sic (intentional typo per user)
    TREE_OF_LIFE = "tree_of_life"
    SIERPINSKI_TRIANGLE = "sierpinski_triangle"
    HEX_CLOSE_PACK = "hex_close_pack"
    MANDALA_RINGS = "mandala_rings"
    GOLDEN_RATIO_ROW = "golden_ratio_row"
    KOCH_3FOLD = "koch_3fold"
    DRAGON_CURVE = "dragon_curve"


class FlightFormation:
    """A set of slot offsets that the formation uses to position ships.

    All offsets are in the path's local frame: +x is right, +y is down
    (screen coordinates). The formation "center" sits at (0, 0); slot
    offsets place ships around it.
    """

    __slots__ = ("kind", "count", "offsets")

    def __init__(self, kind: FormationKind, offsets: Sequence[tuple[float, float]]) -> None:
        self.kind = kind
        self.offsets: list[tuple[float, float]] = [tuple(o) for o in offsets]
        self.count = len(self.offsets)

    # ------------------------------------------------------------------
    # Preset builders
    # ------------------------------------------------------------------
    @staticmethod
    def v(count: int = 5, spacing: float = 18.0) -> "FlightFormation":
        """Chevron / V shape pointing down (+y). Leader at (0, 0).

        count=3 -> 3 slots: (0, 0), (-s, s), (s, s)
        count=5 -> 5 slots: (0, 0), (-s, s), (s, s), (-2s, 2s), (2s, 2s)
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.V, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(1, (count + 1) // 2 + 1):
            offsets.append((-spacing * i, spacing * i))
            offsets.append((spacing * i, spacing * i))
        offsets.sort(key=lambda p: (p[1], p[0]))  # by depth, then x
        return FlightFormation(FormationKind.V, offsets[:count])

    @staticmethod
    def line(count: int = 5, spacing: float = 22.0) -> "FlightFormation":
        """Horizontal line of N slots centered on (0, 0)."""
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.LINE, [(0.0, 0.0)])
        half = (count - 1) * spacing / 2.0
        offsets = [(-half + i * spacing, 0.0) for i in range(count)]
        return FlightFormation(FormationKind.LINE, offsets)

    @staticmethod
    def diamond(count: int = 5, spacing: float = 20.0) -> "FlightFormation":
        """Diamond shape. count must be 1, 5, 9, 13 (1 + 4*k layers)."""
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.DIAMOND, [(0.0, 0.0)])
        # Build concentric layers
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        layer = 1
        while len(offsets) < count:
            # Top, right, bottom, left
            offsets.append((0.0, -spacing * layer))
            if len(offsets) >= count:
                break
            offsets.append((spacing * layer, 0.0))
            if len(offsets) >= count:
                break
            offsets.append((0.0, spacing * layer))
            if len(offsets) >= count:
                break
            offsets.append((-spacing * layer, 0.0))
            layer += 1
        return FlightFormation(FormationKind.DIAMOND, offsets[:count])

    @staticmethod
    def square(count: int = 5, spacing: float = 22.0) -> "FlightFormation":
        """Square corners + center. count <= 5: just corners + center.
        For more, fill edges between corners.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.SQUARE, [(0.0, 0.0)])
        corners = [
            (-spacing, -spacing),
            (spacing, -spacing),
            (spacing, spacing),
            (-spacing, spacing),
        ]
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for c in corners:
            if len(offsets) >= count:
                break
            offsets.append(c)
        # Edge fillers for count > 5
        edge_idx = 1
        while len(offsets) < count:
            a = corners[(edge_idx - 1) % 4]
            b = corners[edge_idx % 4]
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            offsets.append(mid)
            edge_idx += 1
        return FlightFormation(FormationKind.SQUARE, offsets[:count])

    @staticmethod
    def wedge(count: int = 5, spacing: float = 18.0) -> "FlightFormation":
        """Wedge (right-pointing >, or DUCK shape). Like V but mirrored.

        Leader is at the tip (left side), wings flare to the right.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.WEDGE, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(1, (count + 1) // 2 + 1):
            offsets.append((spacing * i, -spacing * i))
            offsets.append((spacing * i, spacing * i))
        offsets.sort(key=lambda p: (p[0], p[1]))  # by x, then y
        return FlightFormation(FormationKind.WEDGE, offsets[:count])

    @staticmethod
    def circle(count: int = 6, radius: float = 24.0) -> "FlightFormation":
        """N slots evenly around a circle of given radius."""
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.CIRCLE, [(0.0, 0.0)])
        offsets = [
            (
                math.cos(2.0 * math.pi * i / count) * radius,
                math.sin(2.0 * math.pi * i / count) * radius,
            )
            for i in range(count)
        ]
        return FlightFormation(FormationKind.CIRCLE, offsets)

    @staticmethod
    def triangle(count: int = 6, spacing: float = 18.0) -> "FlightFormation":
        """Triangle pointing down (+y). count=3 -> 3 slots (1+2),
        count=6 -> 6 slots (1+2+3), count=10 -> 10 slots (1+2+3+4).
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.TRIANGLE, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = []
        placed = 0
        row = 0
        while placed < count:
            row_size = row + 1
            start_x = -(row * spacing) / 2.0
            for k in range(row_size):
                if placed >= count:
                    break
                offsets.append((start_x + k * spacing, row * spacing))
                placed += 1
            row += 1
        return FlightFormation(FormationKind.TRIANGLE, offsets)

    @staticmethod
    def half_v(count: int = 5, spacing: float = 18.0) -> "FlightFormation":
        """Half-chevron: leader + only the RIGHT wing (or LEFT if mirrored).

        Mirrored V \u2014 all slots on the same side.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.HALF_V, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(1, count):
            offsets.append((spacing * i, spacing * i))
        return FlightFormation(FormationKind.HALF_V, offsets)

    @staticmethod
    def flower_of_life(count: int = 7, radius: float = 18.0) -> "FlightFormation":
        """Sacred geometry: center + 6 hex points (Flower of Life pattern).

        count=7 -> center (0, 0) + 6 hex at radius 18, angles 0/60/120/180/240/300.
        count=1 -> only the center.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.FLOWER_OF_LIFE, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(6):
            angle = math.radians(i * 60)
            offsets.append((math.cos(angle) * radius, math.sin(angle) * radius))
        return FlightFormation(FormationKind.FLOWER_OF_LIFE, offsets[:count])

    @staticmethod
    def vesica_piscis(count: int = 2, spacing: float = 18.0) -> "FlightFormation":
        """Two ships facing each other across the center (vesica piscis shape).

        count=2 -> ships at (-spacing/2, 0) and (+spacing/2, 0).
        count=1 -> center only. For count>2, additional pairs alternate
        sides at increasing |x| = half * (1 + 2*k).
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.VESICA_PISCIS, [(0.0, 0.0)])
        half = spacing / 2.0
        offsets: list[tuple[float, float]] = [(-half, 0.0), (half, 0.0)]
        while len(offsets) < count:
            x = half * (1 + 2 * (len(offsets) // 2))
            offsets.append((-x, 0.0))
            if len(offsets) >= count:
                break
            offsets.append((x, 0.0))
        return FlightFormation(FormationKind.VESICA_PISCIS, offsets[:count])

    @staticmethod
    def fibonacfi_spiral(count: int = 8, r0: float = 8.0) -> "FlightFormation":
        """Logarithmic spiral r = r0 * phi^(i/2), theta = i * 60 deg.

        The spiral starts at the center and grows outward with the golden
        ratio (phi = (1+sqrt(5))/2) as the scale factor per half-revolution.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.FIBONACFI_SPIRAL, [(0.0, 0.0)])
        phi = (1 + math.sqrt(5)) / 2
        offsets: list[tuple[float, float]] = []
        for i in range(count):
            r = r0 * (phi ** (i / 2))
            theta = math.radians(i * 60)
            offsets.append((r * math.cos(theta), r * math.sin(theta)))
        return FlightFormation(FormationKind.FIBONACFI_SPIRAL, offsets)

    @staticmethod
    def tree_of_life(count: int = 10, spacing: float = 22.0) -> "FlightFormation":
        """Kabbalah Tree of Life: 3 cols x 3 rows + 1 kingdom = 10 sephirot.

        Top three rows (crown, wisdom/understanding, beauty/severity/mercy):
        each row has 3 ships at x = -spacing, 0, +spacing. Bottom row:
        one ship at (0, +2*spacing) (the kingdom, Malkuth).
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.TREE_OF_LIFE, [(0.0, 0.0)])
        y_values = [-spacing, 0.0, spacing, 2 * spacing]
        x_values = [-spacing, 0.0, spacing]
        positions: list[tuple[float, float]] = []
        for y in y_values[:3]:  # first 3 rows: 3 ships each
            for x in x_values:
                positions.append((x, y))
        positions.append((0.0, 2 * spacing))  # kingdom (Malkuth)
        return FlightFormation(FormationKind.TREE_OF_LIFE, positions[:count])

    @staticmethod
    def sierpinski_triangle(count: int = 7, radius: float = 24.0) -> "FlightFormation":
        """Sierpinski triangle depth 2: 3 vertices + 3 midpoints + 1 centroid.

        Equilateral triangle inscribed in a circle of `radius`. The three
        outer midpoints sit halfway between each pair of vertices, and the
        centroid (0, 0) anchors the sub-triangle pattern.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.SIERPINSKI_TRIANGLE, [(0.0, 0.0)])
        h = radius * math.sin(math.radians(60))  # = radius * sqrt(3)/2
        top = (0.0, -radius)
        bl = (-h, radius / 2)
        br = (h, radius / 2)
        midpoints = [
            ((top[0] + bl[0]) / 2, (top[1] + bl[1]) / 2),
            ((top[0] + br[0]) / 2, (top[1] + br[1]) / 2),
            ((bl[0] + br[0]) / 2, (bl[1] + br[1]) / 2),
        ]
        centroid = (0.0, 0.0)
        positions = [top, midpoints[0], midpoints[1], centroid, midpoints[2], bl, br]
        return FlightFormation(FormationKind.SIERPINSKI_TRIANGLE, positions[:count])

    @staticmethod
    def hex_close_pack(count: int = 7, radius: float = 14.0) -> "FlightFormation":
        """Same as flower_of_life but radius=14 (honeycomb spacing).

        count=7 -> center + 6 hex at radius 14.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.HEX_CLOSE_PACK, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(6):
            angle = math.radians(i * 60)
            offsets.append((math.cos(angle) * radius, math.sin(angle) * radius))
        return FlightFormation(FormationKind.HEX_CLOSE_PACK, offsets[:count])

    @staticmethod
    def mandala_rings(count: int = 12, inner_r: float = 12.0,
                      outer_r: float = 24.0) -> "FlightFormation":
        """6 inner hex + 6 outer hex offset by 30 deg (12 total by default).

        For count=6, only the inner ring. For count>12, the inner+outer
        build exhausts the default 12; additional counts beyond 12 are not
        added by this minimal implementation (caller may request a 3rd
        ring via custom if needed).
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.MANDALA_RINGS, [(0.0, 0.0)])
        offsets: list[tuple[float, float]] = []
        n_inner = min(6, count)
        for i in range(n_inner):
            a = math.radians(i * 60)
            offsets.append((inner_r * math.cos(a), inner_r * math.sin(a)))
        n_outer = min(6, count - n_inner)
        for i in range(n_outer):
            a = math.radians(30 + i * 60)
            offsets.append((outer_r * math.cos(a), outer_r * math.sin(a)))
        return FlightFormation(FormationKind.MANDALA_RINGS, offsets)

    @staticmethod
    def golden_ratio_row(count: int = 5, spacing: float = 10.0) -> "FlightFormation":
        """Horizontal row at offsets 0, phi, 2*phi, 3*phi, 4*phi * spacing.

        Each successive ship is `phi * spacing` further right, producing
        a progressively-widening row that follows the golden ratio.
        """
        count = max(1, count)
        if count == 1:
            return FlightFormation(FormationKind.GOLDEN_RATIO_ROW, [(0.0, 0.0)])
        phi = (1 + math.sqrt(5)) / 2
        offsets = [(i * phi * spacing, 0.0) for i in range(count)]
        return FlightFormation(FormationKind.GOLDEN_RATIO_ROW, offsets)

    @staticmethod
    def koch_3fold(count: int = 7, scale: float = 24.0) -> "FlightFormation":
        """7 pre-computed anchor points on a 3-fold Koch zigzag (no central peak).

        Per spec §3.9, the 7 anchors are pre-computed (not generated by
        recursion). The base layout is scaled by `scale / 24.0` so callers
        can size the formation. Crucially, there is NO (0, 0) point — this
        is a zigzag, not a star.
        """
        s = scale / 24.0
        base = [
            (-24, -14), (-12, -24), (0, -14),
            (12, -24), (24, -14), (-24, 14), (24, 14),
        ]
        offsets = [(x * s, y * s) for x, y in base]
        return FlightFormation(FormationKind.KOCH_3FOLD, offsets[:count])

    @staticmethod
    def dragon_curve(count: int = 8, scale: float = 16.0) -> "FlightFormation":
        """8 pre-computed anchors of the Heighway dragon curve (scaled).

        The base layout is scaled by `scale / 16.0` so callers can size
        the formation. Starts at origin (0, 0) and zigzags up-right.
        """
        s = scale / 16.0
        base = [
            (0, 0), (0, -16), (16, -16), (16, 0),
            (32, 0), (32, 16), (16, 16), (16, 32),
        ]
        offsets = [(x * s, y * s) for x, y in base]
        return FlightFormation(FormationKind.DRAGON_CURVE, offsets[:count])

    @staticmethod
    def custom(offsets: Sequence[tuple[float, float]]) -> "FlightFormation":
        """User-defined slot offsets (e.g. from JSON or inline)."""
        if not offsets:
            raise ValueError("custom formation requires at least 1 offset")
        return FlightFormation(FormationKind.CUSTOM, offsets)

    @staticmethod
    def make(kind: FormationKind, count: int = 5, spacing: float = 18.0,
             radius: float = 24.0) -> "FlightFormation":
        """Dispatch to the right preset builder based on `kind`."""
        if kind == FormationKind.V:
            return FlightFormation.v(count, spacing)
        if kind == FormationKind.LINE:
            return FlightFormation.line(count, spacing)
        if kind == FormationKind.DIAMOND:
            return FlightFormation.diamond(count, spacing)
        if kind == FormationKind.SQUARE:
            return FlightFormation.square(count, spacing)
        if kind == FormationKind.WEDGE:
            return FlightFormation.wedge(count, spacing)
        if kind == FormationKind.CIRCLE:
            return FlightFormation.circle(count, radius)
        if kind == FormationKind.TRIANGLE:
            return FlightFormation.triangle(count, spacing)
        if kind == FormationKind.HALF_V:
            return FlightFormation.half_v(count, spacing)
        if kind == FormationKind.FLOWER_OF_LIFE:
            return FlightFormation.flower_of_life(count, radius)
        if kind == FormationKind.VESICA_PISCIS:
            return FlightFormation.vesica_piscis(count, spacing)
        if kind == FormationKind.FIBONACFI_SPIRAL:
            return FlightFormation.fibonacfi_spiral(count, spacing)
        if kind == FormationKind.TREE_OF_LIFE:
            return FlightFormation.tree_of_life(count, spacing)
        if kind == FormationKind.SIERPINSKI_TRIANGLE:
            return FlightFormation.sierpinski_triangle(count, spacing)
        if kind == FormationKind.HEX_CLOSE_PACK:
            return FlightFormation.hex_close_pack(count, spacing)
        if kind == FormationKind.MANDALA_RINGS:
            return FlightFormation.mandala_rings(count, radius=radius)
        if kind == FormationKind.GOLDEN_RATIO_ROW:
            return FlightFormation.golden_ratio_row(count, spacing)
        if kind == FormationKind.KOCH_3FOLD:
            return FlightFormation.koch_3fold(count, spacing)
        if kind == FormationKind.DRAGON_CURVE:
            return FlightFormation.dragon_curve(count, spacing)
        if kind == FormationKind.CUSTOM:
            raise ValueError("custom formations require explicit offsets")
        raise ValueError(f"unknown formation kind: {kind}")
