# stellar_horizon/tests/test_backgrounds.py
from pathlib import Path
import pytest
import pygame

from stellar_horizon.ui.backgrounds import Background, make_placeholder_backgrounds


def test_make_placeholder_backgrounds_creates_3(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    assert (tmp_path / "act1_asteroid_belt.png").exists()
    assert (tmp_path / "act2_nebula.png").exists()
    assert (tmp_path / "act3_sun_close.png").exists()


def test_background_loads_image(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    assert bg.image.get_size() == (480, 270)


def test_background_draw_doesnt_crash(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    surf = pygame.Surface((480, 270))
    bg.update(0.1)
    bg.draw(surf)


def test_background_parallax_x_advances(tmp_path):
    make_placeholder_backgrounds(tmp_path)
    bg = Background(tmp_path / "act1_asteroid_belt.png")
    bg.update(0.1, scroll_speed=30.0)
    assert bg.parallax_x != 0.0
