"""Tests for the Boss animation state machine (BLOQUE 60 Task 7).

Verifies the 5-state animation contract on ``src.entities.enemies.boss.Boss``:
  - ``animation_state`` defaults to ``"idle"`` on a fresh instance.
  - ``animation_path`` formats as ``"bosses/goliath/<state>/frame_NN.png"``.
  - ``update_animation(dt)`` advances the frame at 10 fps.
  - ``idle`` (and ``damage``/``phase2``) loop; ``death`` (and ``intro``)
    hold the last frame (one-shot).

BLOQUE 60 deviation: the plan's literal test code inlines
``os.environ.setdefault("SDL_VIDEODRIVER", "dummy")`` etc. at module
top, but the actual file uses the project's standard ``pygame.init() +
display.set_mode((1, 1))`` headless pattern, mirroring the rest of
``tests/``. The headless video driver is set via
``pygame_venv_dummy`` on this machine, so we only init pygame here.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Headless pygame — required because Boss uses pygame.Rect via hitbox().
# We initialize the display so image-related pygame paths work in tests.
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.entities.enemies.boss import Boss, BossId  # noqa: E402


def test_boss_starts_in_idle() -> None:
    b = Boss()
    b.active = True
    assert b.animation_state == "idle"
    assert b.animation_frame == 0
    assert b.animation_timer == 0.0


def test_boss_animation_path_format() -> None:
    b = Boss()
    b.active = True
    b.animation_state = "idle"
    b.animation_frame = 3
    assert b.animation_path == "bosses/goliath/idle/frame_03.png"


def test_boss_animation_path_phase2() -> None:
    b = Boss()
    b.active = True
    b.animation_state = "phase2"
    b.animation_frame = 7
    assert b.animation_path == "bosses/goliath/phase2/frame_07.png"


def test_boss_advance_frame_on_update() -> None:
    """Calling update_animation(0.10) advances the frame by 1."""
    b = Boss()
    b.active = True
    b.update_animation(0.10)
    assert b.animation_frame == 1
    assert b.animation_timer == 0.0


def test_boss_idle_loops() -> None:
    """idle state loops back to frame 0 after frame 9."""
    b = Boss()
    b.active = True
    b.animation_state = "idle"
    b.animation_frame = 9
    b.update_animation(0.10)
    assert b.animation_frame == 0


def test_boss_death_is_oneshot() -> None:
    """death state holds frame 9 once reached (no loop)."""
    b = Boss()
    b.active = True
    b.animation_state = "death"
    b.animation_frame = 9
    b.update_animation(0.10)
    assert b.animation_frame == 9
    b.update_animation(0.10)
    assert b.animation_frame == 9
