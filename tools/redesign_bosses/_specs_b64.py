"""Boss spec for GOLIATH redesign (BLOQUE 64.B).

Six animation states, ten frames per state = 60 frame PNGs total.
BLOQUE 64.B replaces the 5-state BLOQUE 60 spec with 6 new states:
  - phase1_idle   (replaces "idle")
  - phase2_idle   (replaces "phase2")
  - javelin       (replaces "damage" for the javelin throw attack)
  - laser         (new — Phase 2 eye laser)
  - purple_bullet (new — Phase 2 purple burst)
  - death         (replaces "death" from BLOQUE 60)

All prompts are BORDERLESS with a TRANSPARENT BACKGROUND so the postprocess
can produce a clean 96x80 sprite with no dark frame around the silhouette.
The runtime reads from `Assets/sprites/bosses/goliath/<state>/frame_NN.png`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateSpec:
    """One animation state of a boss."""
    key: str            # "phase1_idle" | "phase2_idle" | "javelin" | "laser" | "purple_bullet" | "death"
    base_filename: str  # e.g. "goliath_phase1_idle_base.png"
    prompt_fill: str    # appended to the standard prompt template
    frame_count: int    # always 10 for BLOQUE 64.B


@dataclass(frozen=True)
class BossSpec:
    """One boss to redesign."""
    key: str                # "goliath"
    source_size: int        # 96
    states: tuple[StateSpec, ...]


# ---------------------------------------------------------------------------
# 6 new states
# ---------------------------------------------------------------------------

GOLIATH_PHASE1_IDLE = StateSpec(
    key="phase1_idle",
    base_filename="goliath_phase1_idle_base.png",
    prompt_fill=(
        "Phase 1 idle stance, weight on right leg, weapon at rest, eye "
        "glowing softly, no attack motion"
    ),
    frame_count=10,
)

GOLIATH_PHASE2_IDLE = StateSpec(
    key="phase2_idle",
    base_filename="goliath_phase2_idle_base.png",
    prompt_fill=(
        "Phase 2 idle stance, more aggressive posture, red eye glowing "
        "brighter, body slightly hunched forward"
    ),
    frame_count=10,
)

GOLIATH_JAVELIN = StateSpec(
    key="javelin",
    base_filename="goliath_javelin_base.png",
    prompt_fill=(
        "Throwing a javelin forward — arm extended, body leaning into the "
        "throw, motion blur on the javelin, frames 0-3 wind-up, 4-6 "
        "release, 7-9 follow-through"
    ),
    frame_count=10,
)

GOLIATH_LASER = StateSpec(
    key="laser",
    base_filename="goliath_laser_base.png",
    prompt_fill=(
        "Firing eye laser — eye fully lit red, body planted, beam "
        "emanating from eye forward, frames 0-3 charge, 4-7 fire, 8-9 "
        "cool-down"
    ),
    frame_count=10,
)

GOLIATH_PURPLE_BULLET = StateSpec(
    key="purple_bullet",
    base_filename="goliath_purple_bullet_base.png",
    prompt_fill=(
        "Firing purple projectiles — arm raised pointing forward, purple "
        "muzzle glow, frames 0-4 charge, 5-7 fire, 8-9 recoil"
    ),
    frame_count=10,
)

GOLIATH_DEATH = StateSpec(
    key="death",
    base_filename="goliath_death_base.png",
    prompt_fill=(
        "Death sequence — body collapsing, armor falling apart, frames "
        "0-3 stagger, 4-6 fall, 7-9 collapse with explosion particles"
    ),
    frame_count=10,
)

GOLIATH_SPEC_64B = BossSpec(
    key="goliath",
    source_size=96,
    states=(
        GOLIATH_PHASE1_IDLE,
        GOLIATH_PHASE2_IDLE,
        GOLIATH_JAVELIN,
        GOLIATH_LASER,
        GOLIATH_PURPLE_BULLET,
        GOLIATH_DEATH,
    ),
)

# Animations that loop (frame index resets to 0 after frame 9).
LOOPING_ANIMS = frozenset({
    "phase1_idle",
    "phase2_idle",
    "javelin",
    "laser",
    "purple_bullet",
})

# Animations that play once and hold the last frame.
ONE_SHOT_ANIMS = frozenset({
    "death",
})

# All valid GOLIATH animation states for BLOQUE 64.B.
ALL_STATES = frozenset({
    "phase1_idle",
    "phase2_idle",
    "javelin",
    "laser",
    "purple_bullet",
    "death",
})
