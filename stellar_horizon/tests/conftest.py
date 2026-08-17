"""Shared pytest fixtures for STELLAR HORIZON."""
from __future__ import annotations

import os
import warnings

# Force SDL headless drivers BEFORE pygame is imported
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import pygame  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _suppress_pygame_renderer_warning():
    """Suppress pygame's `Warning: no fast renderer available`.

    When running under pytest's `filterwarnings = ["error"]`, this pygame
    informational warning (emitted during SCALED display init with the
    dummy video driver + software renderer) becomes a hard exception and
    breaks Game() construction. Suppress it at the test boundary.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="no fast renderer available",
            category=Warning,
        )
        yield


@pytest.fixture(autouse=True)
def _ensure_mixer_ready():
    """Re-init pygame.mixer if a previous test called mixer.quit().

    Some tests (e.g. test_midi_player, test_scenes_gameplay) tear
    down the mixer in their own teardown. Without this fixture the
    next test that constructs a MidiPlayer (which calls
    pygame.mixer.music.set_volume) crashes with "mixer not
    initialized". We just re-init at the start of every test if the
    mixer happens to be down.
    """
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except pygame.error:
            # No audio device available (e.g. CI); tests that need
            # the mixer will fail explicitly when they call into it.
            pass
    yield


if not pygame.get_init():
    pygame.init()
if not pygame.font.get_init():
    pygame.font.init()
# Note: do NOT pre-init display with a non-SCALED mode here. Tests that need a
# real display (e.g. Game) call pygame.display.set_mode() with SCALED, which
# fails if a non-SCALED mode was already created. Other tests that need a
# surface use a plain pygame.Surface().
