"""Easing functions for camera, transitions, UI animations.

Standard t∈[0,1] → eased value ∈[0,1]. All return 0 at t=0 and 1 at t=1
(continuity at endpoints) except `linear` which is the identity.

Source: standard reference implementations, also used in Vlambeer GDC talks
and many shmup postmortems.
"""
from __future__ import annotations

import math


def linear(t: float) -> float:
    return t


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t: float) -> float:
    return t ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t ** 3
    p = 2.0 * t - 2.0
    return 0.5 * p ** 3 + 1.0


def ease_out_quad(t: float) -> float:
    return 1.0 - (1.0 - t) ** 2


def ease_out_bounce(t: float) -> float:
    """Bouncy ease-out for hit feedback / score popups."""
    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """GLSL-style smoothstep. Returns 0 below edge0, 1 above edge1, smooth in between."""
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
