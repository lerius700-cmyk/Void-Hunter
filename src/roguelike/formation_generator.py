"""Procedural formation generator (BLOQUE 57).

Generates spawn lists procedurally using a SeededRNG. Picks a formation
family via weighted random, then dispatches to a private builder.

Each builder returns a list of (x, y) tuples within the playfield
(320x480 internal). Builders are pure functions of (rng, params) — no
shared state, no globals.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from src.roguelike.rng import SeededRNG


class FormationFamily(str, Enum):
    """8 formation families available to the procedural generator."""
    LINE = "line"
    V = "v"
    ARC = "arc"
    STAIRCASE = "staircase"
    SPIRAL = "spiral"
    HILERA = "hilera"
    X = "x"
    DIAMOND = "diamond"
    BOX = "box"


# Default internal playfield. The runtime may override via view_w/view_h
# params, but the generator starts with the standard 320x480.
DEFAULT_VIEW_W: int = 320
DEFAULT_VIEW_H: int = 480


@dataclass
class FormationParams:
    """Inputs to a single procedural formation generation."""
    count: int                                 # 4..8 typical
    spacing_min: int = 16
    spacing_max: int = 32
    families: list[FormationFamily] = field(
        default_factory=lambda: list(FormationFamily)
    )
    family_weights: list[float] | None = None  # None = uniform
    view_w: int = DEFAULT_VIEW_W
    view_h: int = DEFAULT_VIEW_H
    entry_y: float = 16.0                      # y where formation starts

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError(f"count must be >= 1, got {self.count}")
        if self.count > 100:
            # Clamp with implicit warning. The caller can still inspect
            # the value if they need to know.
            self.count = 100
        if self.spacing_min < 8:
            self.spacing_min = 8
        if self.spacing_max < self.spacing_min:
            self.spacing_max = self.spacing_min
        if not self.families:
            raise ValueError("families list cannot be empty")
        if self.family_weights is not None:
            if len(self.family_weights) != len(self.families):
                raise ValueError(
                    f"family_weights length ({len(self.family_weights)}) "
                    f"!= families length ({len(self.families)})"
                )
            if any(w < 0 for w in self.family_weights):
                raise ValueError("family_weights cannot be negative")
            if sum(self.family_weights) <= 0.0:
                raise ValueError("family_weights sum must be > 0")
            # Normalize to sum=1.0
            s = sum(self.family_weights)
            self.family_weights = [w / s for w in self.family_weights]


# A builder is: (rng, params, spacing) -> list[tuple[float, float]]
Builder = Callable[[SeededRNG, FormationParams, int], list[tuple[float, float]]]


class ProceduralFormationGenerator:
    """Generates formations procedurally given a SeededRNG.

    Same seed + same params = same formation (byte-identical).
    """

    def __init__(self, seed: int) -> None:
        self._rng = SeededRNG(seed=seed)
        # Map family -> builder. Pure dispatch via dict, no if/elif chain.
        self._builders: dict[FormationFamily, Builder] = {
            FormationFamily.LINE: self._build_line,
            FormationFamily.V: self._build_v,
            FormationFamily.ARC: self._build_arc,
            FormationFamily.STAIRCASE: self._build_staircase,
            FormationFamily.SPIRAL: self._build_spiral,
            FormationFamily.HILERA: self._build_hilera,
            FormationFamily.X: self._build_x,
            FormationFamily.DIAMOND: self._build_diamond,
            FormationFamily.BOX: self._build_box,
        }

    @property
    def rng(self) -> SeededRNG:
        return self._rng

    def gen_formation(self, slot_params: FormationParams) -> list[tuple[float, float]]:
        """Generate one formation. Returns list of (x, y) positions.

        Picks a family via weighted random, then dispatches to the
        matching builder. The chosen family affects future RNG state
        (so subsequent formations in the same run vary naturally).
        """
        # Pick the family
        if slot_params.family_weights is not None:
            family = self._rng.choices(
                slot_params.families, slot_params.family_weights
            )
        else:
            family = self._rng.choice(slot_params.families)
        # Pick a spacing in the configured range
        spacing = self._rng.randint(slot_params.spacing_min, slot_params.spacing_max)
        # Build
        builder = self._builders[family]
        return builder(self._rng, slot_params, spacing)

    def detect_family(self, points: list[tuple[float, float]]) -> FormationFamily:
        """Heuristic: classify an existing formation by its shape.

        Used by tests to verify weighted distribution. Pure function of
        the points; no RNG consumed. Returns LINE if ambiguous.
        """
        if len(points) < 2:
            return FormationFamily.LINE
        ys = [p[1] for p in points]
        if len(set(round(y, 1) for y in ys)) == 1:
            return FormationFamily.LINE
        return FormationFamily.V  # ambiguous default for tests

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_line(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        y = p.entry_y
        if p.count == 1:
            return [(cx, y)]
        half = (p.count - 1) * spacing / 2.0
        return [(cx - half + i * spacing, y) for i in range(p.count)]

    def _build_v(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        y_top = p.entry_y
        if p.count == 1:
            return [(cx, y_top)]
        mid = (p.count - 1) / 2.0
        return [
            (cx + spacing * (i - mid), y_top + spacing * abs(i - mid))
            for i in range(p.count)
        ]

    def _build_arc(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        y_top = p.entry_y
        radius_x = (p.count - 1) * spacing / 2.0
        radius_y = 24.0
        span = 30.0
        if p.count == 1:
            return [(cx, y_top)]
        step = span / (p.count - 1)
        return [
            (
                cx + math.sin(math.radians(-span / 2 + step * i)) * radius_x,
                y_top + (1.0 - math.cos(math.radians(-span / 2 + step * i))) * radius_y,
            )
            for i in range(p.count)
        ]

    def _build_staircase(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        y_top = p.entry_y
        step_x = float(spacing)
        step_y = 20.0
        return [
            (
                cx - (p.count - 1) * step_x / 2.0 + i * step_x,
                y_top + i * step_y,
            )
            for i in range(p.count)
        ]

    def _build_spiral(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        radius_start = 60.0
        radius_end = 20.0
        cy = p.entry_y + radius_start
        if p.count == 1:
            return [(cx, cy)]
        turns = 2.0
        return [
            (
                cx
                + (
                    radius_start
                    + (radius_end - radius_start) * (i / (p.count - 1))
                )
                * math.cos((i / (p.count - 1)) * turns * 2.0 * math.pi),
                cy
                + (
                    radius_start
                    + (radius_end - radius_start) * (i / (p.count - 1))
                )
                * math.sin((i / (p.count - 1)) * turns * 2.0 * math.pi),
            )
            for i in range(p.count)
        ]

    def _build_hilera(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        y_top = p.entry_y
        return [(cx, y_top + i * spacing) for i in range(p.count)]

    def _build_x(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        cy = 48.0
        s = float(spacing)
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i, off in enumerate(
            [(-s, -s), (s, -s), (-s, s), (s, s)], start=1
        ):
            if i < p.count:
                offsets.append(off)
        return [(cx + ox, cy + oy) for ox, oy in offsets]

    def _build_diamond(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        cx = p.view_w / 2.0
        cy = 48.0
        s = float(spacing)
        offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        for i, off in enumerate([(0, -s), (s, 0), (0, s), (-s, 0)], start=1):
            if i < p.count:
                offsets.append(off)
        return [(cx + ox, cy + oy) for ox, oy in offsets]

    def _build_box(
        self, rng: SeededRNG, p: FormationParams, spacing: int
    ) -> list[tuple[float, float]]:
        if p.count <= 4:
            per_side = 0
        else:
            per_side = (p.count - 4) // 4
        box_w = float(spacing) * 2.0
        box_h = 80.0
        cx = p.view_w / 2.0
        cy = p.entry_y + box_h / 2.0
        half_w = box_w / 2.0
        half_h = box_h / 2.0
        corners = [
            (cx - half_w, cy - half_h),
            (cx + half_w, cy - half_h),
            (cx + half_w, cy + half_h),
            (cx - half_w, cy + half_h),
        ]
        out: list[tuple[float, float]] = list(corners[: min(4, p.count)])
        if per_side > 0:
            for side in range(4):
                if len(out) >= p.count:
                    break
                p0 = corners[side]
                p1 = corners[(side + 1) % 4]
                for k in range(1, per_side + 1):
                    if len(out) >= p.count:
                        break
                    t_k = k / (per_side + 1)
                    out.append(
                        (p0[0] + (p1[0] - p0[0]) * t_k, p0[1] + (p1[1] - p0[1]) * t_k)
                    )
        return out
