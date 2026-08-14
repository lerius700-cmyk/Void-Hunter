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
        if kind == FormationKind.CUSTOM:
            raise ValueError("custom formations require explicit offsets")
        raise ValueError(f"unknown formation kind: {kind}")
