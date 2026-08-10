"""Bezier curves for path-following in 2D (BLOQUE 56).

Pure stdlib math — no numpy (per GDD section 0). Used by:
  - Boss entrance paths (GOLIATH dramatic entrance)
  - Future use: projectile arcs, sub-boss dive patterns, camera paths

Curves supported:
  - QUADRATIC: 3 control points (P0, P1, P2)
      B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
  - CUBIC: 4 control points (P0, P1, P2, P3)
      B(t) = (1-t)^3 * P0 + 3(1-t)^2 t * P1 + 3(1-t) t^2 * P2 + t^3 * P3

Pre-baking:
  For long-lived paths, call `prebake(steps=N)` to precompute the curve
  at N evenly-spaced t values. update() then does a linear interpolation
  between adjacent samples instead of recomputing the polynomial each
  frame. Tradeoff: ~2*N floats of memory for one polynomial evaluation
  per frame instead of one per frame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class ControlPoint:
    """A 2D control point with optional tangent angle (radians)."""
    x: float
    y: float
    angle: float = 0.0


# A path is either 3 points (quadratic) or 4 points (cubic). Other counts
# raise ValueError. The first point is the START, the last is the END.
MIN_CONTROL_POINTS = 3
MAX_CONTROL_POINTS = 4


class BezierPath:
    """A 2D bezier path that an object can follow over time.

    Usage:
        path = BezierPath([
            ControlPoint(0, 0),     # start (off-screen)
            ControlPoint(80, 200),  # control 1 (curve in)
            ControlPoint(240, 100), # control 2 (curve out)
            ControlPoint(160, 80),  # end (boss anchor)
        ])
        path.prebake(steps=60)
        # In game loop:
        x, y = path.update(dt=0.016, speed=80.0)
        if path.is_complete:
            # path finished, switch to fallback motion
            ...

    Speed semantics:
        `speed` is the world-space distance (in pixels per second) the
        follower should travel along the curve. Internally, t is advanced
        proportionally to dt*speed divided by the path's total length.
    """

    def __init__(
        self,
        control_points: Sequence[ControlPoint],
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        if len(control_points) not in (MIN_CONTROL_POINTS, MAX_CONTROL_POINTS):
            raise ValueError(
                f"BezierPath requires {MIN_CONTROL_POINTS} (quadratic) or "
                f"{MAX_CONTROL_POINTS} (cubic) control points; got {len(control_points)}"
            )
        self._cps: tuple[ControlPoint, ...] = tuple(control_points)
        self._t: float = 0.0
        self._is_complete: bool = False
        self._on_complete = on_complete
        # Pre-bake cache: list of (x, y) at evenly-spaced t values.
        # Populated by prebake(); consulted by update() to skip polynomial eval.
        self._cache: list[tuple[float, float]] | None = None
        self._cache_total_length: float = 0.0  # polyline length at cache resolution

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def t(self) -> float:
        """Current t along the curve. 0=start, 1=end."""
        return self._t

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def is_quadratic(self) -> bool:
        return len(self._cps) == MIN_CONTROL_POINTS

    @property
    def total_length(self) -> float:
        """Estimated total path length in pixels (polyline approximation
        across 100 samples). Used to convert speed -> t delta."""
        return self._compute_length(samples=100)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def eval(self, t: float) -> tuple[float, float]:
        """Evaluate the bezier polynomial at parameter t (0..1)."""
        t = max(0.0, min(1.0, t))
        if self.is_quadratic:
            return self._eval_quadratic(t)
        return self._eval_cubic(t)

    def _eval_quadratic(self, t: float) -> tuple[float, float]:
        p0, p1, p2 = self._cps
        u = 1.0 - t
        w0 = u * u
        w1 = 2.0 * u * t
        w2 = t * t
        return (
            w0 * p0.x + w1 * p1.x + w2 * p2.x,
            w0 * p0.y + w1 * p1.y + w2 * p2.y,
        )

    def _eval_cubic(self, t: float) -> tuple[float, float]:
        p0, p1, p2, p3 = self._cps
        u = 1.0 - t
        w0 = u * u * u
        w1 = 3.0 * u * u * t
        w2 = 3.0 * u * t * t
        w3 = t * t * t
        return (
            w0 * p0.x + w1 * p1.x + w2 * p2.x + w3 * p3.x,
            w0 * p0.y + w1 * p1.y + w2 * p2.y + w3 * p3.y,
        )

    # ------------------------------------------------------------------
    # Pre-bake (optional, for long paths or many followers)
    # ------------------------------------------------------------------
    def prebake(self, steps: int = 60) -> None:
        """Precompute the curve at `steps` evenly-spaced t values.

        Once prebaked, update() interpolates between adjacent samples
        instead of recomputing the polynomial. Useful for paths that
        are followed by many objects (e.g., 8 wingmen).
        """
        if steps < 2:
            raise ValueError(f"steps must be >= 2; got {steps}")
        samples: list[tuple[float, float]] = []
        total = 0.0
        prev = self.eval(0.0)
        for i in range(1, steps + 1):
            t = i / steps
            cur = self.eval(t)
            total += math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            samples.append(cur)
            prev = cur
        self._cache = samples
        # Total polyline length is sum of segment lengths, but we use the
        # 100-sample estimate for the speed/t conversion.
        self._cache_total_length = total

    # ------------------------------------------------------------------
    # Step the curve forward
    # ------------------------------------------------------------------
    def update(self, dt: float, speed: float) -> tuple[float, float]:
        """Advance t by `dt` at the given `speed` (px/s). Returns (x, y).

        On the first call where t reaches 1.0, the on_complete callback
        (if any) is fired and is_complete becomes True.
        """
        if self._is_complete or dt <= 0.0:
            return self.eval(self._t)
        # Approximate t delta from speed and current path length.
        length = self.total_length
        if length <= 0.0:
            return self.eval(self._t)
        t_delta = (dt * speed) / length
        self._t = min(1.0, self._t + t_delta)
        if self._cache is not None:
            pos = self._eval_from_cache(self._t)
        else:
            pos = self.eval(self._t)
        if self._t >= 1.0 and not self._is_complete:
            self._is_complete = True
            if self._on_complete is not None:
                self._on_complete()
        return pos

    def _eval_from_cache(self, t: float) -> tuple[float, float]:
        """Linearly interpolate between two adjacent prebaked samples."""
        if self._cache is None or not self._cache:
            return self.eval(t)
        n = len(self._cache)
        # Map t in [0, 1] to index in [0, n-1]
        f = t * n
        if f <= 0.0:
            return self._cache[0]
        if f >= n:
            return self._cache[-1]
        i = int(f)
        frac = f - i
        a = self._cache[i]
        b = self._cache[i + 1] if i + 1 < n else self._cache[-1]
        return (a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _compute_length(self, samples: int = 100) -> float:
        """Polyline length of the curve at the given sample resolution."""
        total = 0.0
        prev = self.eval(0.0)
        for i in range(1, samples + 1):
            t = i / samples
            cur = self.eval(t)
            total += math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            prev = cur
        return total

    def reset(self) -> None:
        """Reset t to 0 and is_complete to False. Cache is preserved."""
        self._t = 0.0
        self._is_complete = False
