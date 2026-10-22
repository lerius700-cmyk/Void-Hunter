"""BLOQUE 73.5: GOLIATH must actually advance its sprite animation.

`Boss.update_animation()` was added in BLOQUE 64.B for precisely this and
had **no caller anywhere in src/** until BLOQUE 73.5. `animation_frame`
therefore stayed pinned at 0 for the entire fight: the game played one of
the 60 frames forever, which is why the boss read as a still image no
matter how correct the PNGs on disk were.

These tests tick the real runtime and assert the frame index moves. If the
call is ever dropped again, they fail immediately — the bug is invisible
in a screenshot because frame 0 is a perfectly valid-looking pose.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


@pytest.fixture(scope="module")
def goliath():
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.core.game import Game
    from src.core.scene_manager import GameState
    from src.ui.scenes import BossFightScene

    g = Game()
    g.scenes.register_scene(
        GameState.BOSS_FIGHT,
        BossFightScene(
            g.scenes.transition_to,
            act=1,
            audio=g.audio,
            get_session_score=g._get_session_score,
            set_session_score=g._set_session_score,
        ),
    )
    for st in (
        GameState.ACT_INTRO,
        GameState.GAMEPLAY,
        GameState.BOSS_INTRO,
        GameState.BOSS_FIGHT,
    ):
        g.scenes.transition_to(st)
    return g.scenes.scenes[GameState.BOSS_FIGHT]._rt


def test_boss_is_goliath(goliath) -> None:
    assert goliath._boss.id.name == "GOLIATH"


def test_idle_animation_advances(goliath) -> None:
    """phase1_idle must cycle through all 10 frames, not sit on frame 0."""
    b = goliath._boss
    b.set_animation_state("phase1_idle")
    seen = set()
    for _ in range(120 * 3):  # 3s at 120Hz; frame duration is 0.10s
        goliath.update(1.0 / 120.0)
        seen.add(b.animation_frame)
    assert len(seen) >= 8, (
        f"only {sorted(seen)} seen over 3s — the idle animation is not "
        f"advancing (update_animation is probably not being called)"
    )


def test_every_animation_state_advances(goliath) -> None:
    """All six states must advance; a stuck state means a broken timer."""
    b = goliath._boss
    for state in (
        "phase1_idle",
        "phase2_idle",
        "javelin",
        "laser",
        "purple_bullet",
        "death",
    ):
        b.set_animation_state(state)
        b.animation_frame = 0
        seen = set()
        for _ in range(120 * 3):
            goliath.update(1.0 / 120.0)
            seen.add(b.animation_frame)
        assert len(seen) >= 3, (
            f"{state}: only frames {sorted(seen)} in 3s — animation frozen"
        )


def test_death_holds_at_last_frame(goliath) -> None:
    """death is one-shot: it must stop at frame 9, not wrap to 0."""
    b = goliath._boss
    b.set_animation_state("death")
    b.animation_frame = 9
    for _ in range(120 * 2):
        goliath.update(1.0 / 120.0)
    assert b.animation_frame == 9, (
        f"death wrapped to {b.animation_frame}; it should hold at 9"
    )


def test_attack_animation_returns_to_idle(goliath) -> None:
    """An attack anim must fall back to the phase's idle when it expires."""
    b = goliath._boss
    b.phase = 1
    b.set_animation_state("javelin")
    b.attack_anim_timer = 0.05
    for _ in range(120):
        goliath.update(1.0 / 120.0)
    assert b.animation_state == "phase1_idle", (
        f"javelin never returned to idle (state={b.animation_state})"
    )


def test_boss_flag_reaches_a_real_fight() -> None:
    """`--boss golith` must land in BOSS_FIGHT, not the title screen.

    The flag used to print "full integration in next BLOQUE" and run the
    normal game, so the dev loop recommended throughout the repo silently
    did nothing.
    """
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.core.game import Game
    from src.core.scene_manager import GameState
    from src.ui.scenes import BossFightScene

    g = Game()
    g.scenes.register_scene(
        GameState.BOSS_FIGHT,
        BossFightScene(
            g.scenes.transition_to,
            act=1,
            audio=g.audio,
            get_session_score=g._get_session_score,
            set_session_score=g._set_session_score,
        ),
    )
    for st in (
        GameState.ACT_INTRO,
        GameState.GAMEPLAY,
        GameState.BOSS_INTRO,
        GameState.BOSS_FIGHT,
    ):
        g.scenes.transition_to(st)

    assert g.scenes.current_state is GameState.BOSS_FIGHT
    scene = g.scenes.scenes[GameState.BOSS_FIGHT]
    assert scene._rt._boss.id.name == "GOLIATH"