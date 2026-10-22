"""Tests for src.systems.tile_manager.TileManager.

BLOQUE 73.1 rewrite. The previous version of this file hardcoded
``D:\\AI\\void-hunter\\Assets\\background\\tiles\\act1`` and asserted that
all 6 AI-generated tile PNGs load. Those PNGs were produced by
``tools/tiles/ai_gen/`` and were NEVER committed to the repo, so every
test in this file failed on any machine (including the one that
generated them). The same missing-asset assumption crashed the shipped
v1.4.0 .exe at startup, because TileManager raised FileNotFoundError
from its constructor.

TileManager now treats a missing/partial tile directory as a supported
state (``available=False``) and draws nothing, so the procedural galaxy
strip is the visible backdrop. These tests cover THAT behaviour, plus
the geometry helpers that do not depend on the assets existing.

If the tiles are ever regenerated and committed, the ``skipif``
guards below re-enable the asset-dependent assertions automatically.
"""
from pathlib import Path

import pytest

from src.systems.tile_manager import TileManager

REPO_ROOT = Path(__file__).resolve().parent.parent
TILES_DIR = REPO_ROOT / "Assets" / "background" / "tiles" / "act1"

# True only when the 6 AI-generated tile PNGs are actually present.
HAS_TILES = TILES_DIR.is_dir() and len(
    sorted(TILES_DIR.glob("tile_0[1-6]_*.png"))
) == 6

needs_tiles = pytest.mark.skipif(
    not HAS_TILES,
    reason=(
        "Assets/background/tiles/act1/ is not in the repo (AI-generated, "
        "never committed). TileManager correctly degrades to the galaxy "
        "strip. Re-enables when tools/tiles/ai_gen/ output is committed."
    ),
)


# ---------------------------------------------------------------------------
# Graceful degradation (BLOQUE 73.1) — the regression that shipped broken
# ---------------------------------------------------------------------------


def test_missing_dir_does_not_raise() -> None:
    """BLOQUE 73.1: a missing tiles dir must NOT raise.

    This is the exact regression that made v1.4.0 crash on launch:
    ParallaxBackground constructs TileManager eagerly at scene setup.
    """
    tm = TileManager(Path(r"Z:\definitely\not\a\real\path"))
    assert tm.available is False


def test_missing_dir_has_no_surfaces() -> None:
    tm = TileManager(REPO_ROOT / "Assets" / "does_not_exist")
    assert tm._tile_surfaces == []


def test_partial_tile_set_degrades_gracefully(tmp_path: Path) -> None:
    """Only 2 of 6 tiles present -> unavailable, not an exception."""
    import pygame

    pygame.init()
    stub = pygame.Surface((320, 480))
    for i in (1, 2):
        pygame.image.save(stub, str(tmp_path / f"tile_{i:02d}_stub.png"))
    tm = TileManager(tmp_path)
    assert tm.available is False
    assert tm._tile_surfaces == []


def test_unreadable_tile_file_degrades_gracefully(tmp_path: Path) -> None:
    """A 0-byte 'tile' must not raise pygame.error at construction time."""
    import pygame

    pygame.init()
    for i in range(1, 7):
        (tmp_path / f"tile_{i:02d}_stub.png").write_bytes(b"")
    tm = TileManager(tmp_path)
    assert tm.available is False
    assert tm._tile_surfaces == []


def test_draw_is_noop_when_unavailable() -> None:
    """draw() must be callable and must not raise when tiles are absent."""
    import pygame

    pygame.init()
    target = pygame.Surface((320, 480))
    tm = TileManager(REPO_ROOT / "Assets" / "nope")
    # Every scroll_y boundary must be safe.
    for sy in (0.0, 479.0, 480.0, 481.0, 1440.0, 2879.0, 2880.0, 5760.0, -1.0):
        tm.draw(target, scroll_y=sy)  # must not raise


def test_draw_noop_leaves_target_untouched() -> None:
    import pygame

    pygame.init()
    target = pygame.Surface((320, 480))
    target.fill((7, 7, 7))
    before = pygame.surfarray.array3d(target).copy()
    tm = TileManager(REPO_ROOT / "Assets" / "nope")
    tm.draw(target, scroll_y=100.0)
    assert (pygame.surfarray.array3d(target) == before).all()


# ---------------------------------------------------------------------------
# Asset-independent geometry — always runs
# ---------------------------------------------------------------------------


def test_get_height_returns_2880_even_when_unavailable() -> None:
    """get_height() reports the strip geometry regardless of availability."""
    tm = TileManager(REPO_ROOT / "Assets" / "nope")
    assert tm.get_height() == 6 * 480 == 2880


def test_tile_dimensions_are_320x480() -> None:
    assert TileManager.TILE_W == 320
    assert TileManager.TILE_H == 480
    assert TileManager.NUM_TILES == 6


def test_real_asset_dir_is_consistent_with_available_flag() -> None:
    """Whichever way the assets go, the flag must describe the truth."""
    tm = TileManager(TILES_DIR)
    assert tm.available is HAS_TILES
    if HAS_TILES:
        assert len(tm._tile_surfaces) == 6


# ---------------------------------------------------------------------------
# Asset-dependent behaviour — runs only when the tiles are actually committed
# ---------------------------------------------------------------------------


@needs_tiles
def test_all_six_tiles_loaded() -> None:
    tm = TileManager(TILES_DIR)
    assert len(tm._tile_surfaces) == 6


@needs_tiles
def test_each_tile_is_320x480() -> None:
    tm = TileManager(TILES_DIR)
    for i, surf in enumerate(tm._tile_surfaces):
        assert surf.get_size() == (320, 480), f"Tile {i + 1} is {surf.get_size()}"


@needs_tiles
def test_tiles_horizontally_for_wide_target() -> None:
    import pygame

    pygame.init()
    tm = TileManager(TILES_DIR)
    target = pygame.Surface((960, 480))
    tm.draw(target, scroll_y=0.0)
    assert target.get_at((0, 100))[0:3] == target.get_at((320, 100))[0:3]
    assert target.get_at((320, 100))[0:3] == target.get_at((640, 100))[0:3]


@needs_tiles
def test_tiles_not_rotated() -> None:
    from PIL import Image

    tm = TileManager(TILES_DIR)
    raw = Image.open(TILES_DIR / "tile_01_atmosphere_exit.png")
    assert raw.getpixel((0, 0)) == tm._tile_surfaces[0].get_at((0, 0))[:3]


@needs_tiles
def test_scroll_y_wraps_modulo_2880() -> None:
    import pygame

    pygame.init()
    tm = TileManager(TILES_DIR)
    target = pygame.Surface((320, 480))
    for sy in (0.0, 479.0, 480.0, 481.0, 1440.0, 2879.0, 2880.0, 5760.0, -1.0):
        tm.draw(target, scroll_y=sy)  # must not raise