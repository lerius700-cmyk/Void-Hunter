# stellar_horizon/tests/test_smoke.py
from stellar_horizon import settings


def test_settings_have_expected_values():
    assert settings.INTERNAL_W == 480
    assert settings.INTERNAL_H == 270
    assert settings.WINDOW_W == 1920
    assert settings.WINDOW_H == 1080
    assert settings.FPS_TARGET == 120
    assert abs(settings.FIXED_DT - 1 / 120) < 1e-9


def test_window_title_is_set():
    assert settings.WINDOW_TITLE == "STELLAR HORIZON"


def test_pools_are_positive():
    assert settings.PLAYER_BULLET_POOL > 0
    assert settings.ENEMY_BULLET_POOL > 0
    assert settings.ENEMY_POOL > 0
    assert settings.PARTICLE_POOL > 0
