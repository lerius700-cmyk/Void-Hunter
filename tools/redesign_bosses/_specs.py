"""Boss spec for GOLIATH redesign (BLOQUE 60).

One boss, 5 states, 10 frames per state = 50 frame PNGs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateSpec:
    """One animation state of a boss."""
    key: str            # "idle" | "damage" | "phase2" | "death" | "intro"
    base_filename: str  # e.g. "goliath_idle_base.png"
    prompt_fill: str    # appended to the standard prompt template
    frame_count: int    # always 10 for BLOQUE 60


@dataclass(frozen=True)
class BossSpec:
    """One boss to redesign."""
    key: str                # "goliath"
    source_size: int        # 96
    states: tuple[StateSpec, ...]


GOLIATH_IDLE = StateSpec(
    key="idle",
    base_filename="goliath_idle_base.png",
    prompt_fill=(
        "standing still, breathing (slight vertical bob), calm menacing pose, "
        "spear planted on the ground, shield raised slightly"
    ),
    frame_count=10,
)

GOLIATH_DAMAGE = StateSpec(
    key="damage",
    base_filename="goliath_damage_base.png",
    prompt_fill=(
        "recoiling from a hit, body tilted back 5-10 degrees, eyes flaring red, "
        "spear knocked sideways, slight motion blur, dust kicking up at feet"
    ),
    frame_count=10,
)

GOLIATH_PHASE2 = StateSpec(
    key="phase2",
    base_filename="goliath_phase2_base.png",
    prompt_fill=(
        "armor cracked with glowing red energy leaking from seams, eyes blazing "
        "red, more aggressive crouched stance, lower body coiled for spring, "
        "spear raised overhead ready to throw, shield discarded on the ground"
    ),
    frame_count=10,
)

GOLIATH_DEATH = StateSpec(
    key="death",
    base_filename="goliath_death_base.png",
    prompt_fill=(
        "falling backwards, armor shattering into red energy fragments, "
        "helmet flying off, red energy dissipating upward, dramatic "
        "explosion silhouette"
    ),
    frame_count=10,
)

GOLIATH_INTRO = StateSpec(
    key="intro",
    base_filename="goliath_intro_base.png",
    prompt_fill=(
        "mid-stride descending from above, spear raised overhead, red eyes "
        "first to appear, dramatic entrance, bronze armor catching light, "
        "landing pose about to plant feet"
    ),
    frame_count=10,
)

GOLIATH_SPEC = BossSpec(
    key="goliath",
    source_size=96,
    states=(
        GOLIATH_IDLE,
        GOLIATH_DAMAGE,
        GOLIATH_PHASE2,
        GOLIATH_DEATH,
        GOLIATH_INTRO,
    ),
)
