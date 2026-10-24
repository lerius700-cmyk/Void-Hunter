"""BLOQUE 67: el fondo ASTEROID NEBULA es el real de v1.4.0.

Los 6 tiles del "Asteroid Approach" (Assets/background/tiles/act1/) NUNCA
se commitearon. Por eso:

  - v1.4.0 crasheaba al arrancar (TileManager pedia los tiles),
  - y el gameplay no tenia el fondo morado que el usuario recuerda.

Los tiles se recuperaron de dos copias locales del repo (verificadas con
MD5 identico) y ahora estan commiteados (78 KB). Estos tests fijan:

  1. que los 6 tiles existen y cargan,
  2. que ASTEROID NEBULA dibuja ESOS tiles (no la galaxia de v1.6),
  3. que SPACE VOID no los dibuja,
  4. que sin los tiles el parallax cae al strip procedural (degrada, no
     se rompe).
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

TILES_DIR = ROOT / "Assets" / "background" / "tiles" / "act1"
EXPECTED_TILES = (
    "tile_01_atmosphere_exit.png",
    "tile_02_enter_belt.png",
    "tile_03_mid_belt.png",
    "tile_04_peak_belt.png",
    "tile_05_exit_belt.png",
    "tile_06_open_stars.png",
)


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


class _Game:
    bg_mode = 1
    bg_variant_idx = 3


def _make_runtime(bg_mode: int):
    from src.ui.gameplay_runtime import GameplayRuntime

    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.on_enter()
    rt._game = _Game()
    rt._game.bg_mode = bg_mode
    return rt


def _render(rt):
    import pygame

    surf = pygame.Surface((320, 480))
    surf.fill((0, 0, 0))
    rt.draw(surf)
    return surf


# --------------------------------------------------------------------------
# 1. Los tiles existen
# --------------------------------------------------------------------------
def test_the_six_tiles_are_committed(display) -> None:
    """Los 6 tiles del Asteroid Approach tienen que estar en el repo."""
    for name in EXPECTED_TILES:
        p = TILES_DIR / name
        assert p.is_file(), f"falta el tile {name} en {TILES_DIR}"
        assert p.stat().st_size > 1000, f"{name} parece truncado"


def test_tile_manager_loads_all_six(display) -> None:
    """El TileManager tiene que cargar los 6 y quedar disponible."""
    from src.systems.tile_manager import TileManager

    tm = TileManager(TILES_DIR)
    assert tm.available, "el TileManager no cargo los tiles"
    assert len(tm._tile_surfaces) == 6


# --------------------------------------------------------------------------
# 2. ASTEROID NEBULA dibuja los tiles
# --------------------------------------------------------------------------
def test_asteroid_nebula_draws_the_tiles(display) -> None:
    """El fondo del gameplay tiene que ser el de los tiles, no la galaxia.

    Se comparan dos frames del MISMO instante: uno con el fondo de fondo
    normal (bg_mode 1) y uno con el tile manager apagado. Si difieren
    mucho, es que los tiles se estan dibujando.
    """
    import numpy as np

    rt = _make_runtime(bg_mode=1)
    for _ in range(30):
        rt.update(1.0 / 60.0)
    with_tiles = _render(rt)

    rt2 = _make_runtime(bg_mode=1)
    for _ in range(30):
        rt2.update(1.0 / 60.0)
    _render(rt2)          # el primer draw aplica el modo de fondo
    tm = rt2._parallax_bg._tile_manager
    assert tm is not None and tm.available, "el runtime no tiene tiles cargados"
    tm.set_enabled(False)  # ahora si: el modo ya quedo aplicado
    without_tiles = _render(rt2)

    a = pygame.surfarray.array3d(with_tiles).astype(np.int16)
    b = pygame.surfarray.array3d(without_tiles).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).mean() * 100.0
    assert diff > 30.0, (
        f"los tiles no se estan dibujando (solo {diff:.1f}% de diferencia)"
    )


def test_space_void_does_not_draw_the_tiles(display) -> None:
    """SPACE VOID = solo estrellas. Sin tiles, sin galaxia."""
    import numpy as np

    rt_void = _make_runtime(bg_mode=0)
    for _ in range(30):
        rt_void.update(1.0 / 60.0)
    void = _render(rt_void)

    rt_neb = _make_runtime(bg_mode=1)
    for _ in range(30):
        rt_neb.update(1.0 / 60.0)
    nebula = _render(rt_neb)

    a = pygame.surfarray.array3d(void).astype(np.int16)
    b = pygame.surfarray.array3d(nebula).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).mean() * 100.0
    assert diff > 50.0, (
        f"los dos modos de fondo se ven iguales ({diff:.1f}% de diferencia)"
    )


def test_space_void_disables_the_tile_manager(display) -> None:
    rt = _make_runtime(bg_mode=0)
    rt.update(1.0 / 60.0)
    _render(rt)          # el modo se aplica en el draw
    tm = rt._parallax_bg._tile_manager
    assert tm is not None
    assert not tm.available, "SPACE VOID deberia apagar los tiles"


def test_asteroid_nebula_enables_the_tile_manager(display) -> None:
    rt = _make_runtime(bg_mode=1)
    rt.update(1.0 / 60.0)
    _render(rt)          # el modo se aplica en el draw
    tm = rt._parallax_bg._tile_manager
    assert tm is not None
    assert tm.available, "ASTEROID NEBULA deberia prender los tiles"


# --------------------------------------------------------------------------
# 3. Degradacion: sin tiles cae al strip procedural
# --------------------------------------------------------------------------
def test_parallax_falls_back_to_the_strip_without_tiles(display, tmp_path) -> None:
    """Si los tiles no estan, el parallax dibuja la galaxia, no negro.

    Se compara el mismo parallax con el strip prendido y apagado: si
    difieren, el strip se esta dibujando (el fallback funciona).
    """
    import numpy as np

    from src.systems.parallax import ParallaxBackground

    empty = tmp_path / "tiles_missing"
    empty.mkdir()
    bg = ParallaxBackground(width=320, height=480, stars_per_layer=8,
                            spawn_planets=False, use_tile_sequence=True,
                            tiles_dir=empty)
    assert bg._tile_manager is not None
    assert not bg._tile_manager.available, "no deberia haber tiles"

    # Con strip
    bg.set_strip_enabled(True)
    with_strip = pygame.Surface((320, 480))
    with_strip.fill((0, 0, 0))
    bg.draw(with_strip)

    # Sin strip: solo las estrellas
    bg.set_strip_enabled(False)
    without_strip = pygame.Surface((320, 480))
    without_strip.fill((0, 0, 0))
    bg.draw(without_strip)

    a = pygame.surfarray.array3d(with_strip).astype(np.int16)
    b = pygame.surfarray.array3d(without_strip).astype(np.int16)
    diff = (np.abs(a - b).sum(axis=2) > 0).mean() * 100.0
    assert diff > 1.0, (
        f"sin tiles el fondo no cae al strip ({diff:.2f}% de diferencia)"
    )
