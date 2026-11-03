"""BLOQUE 75: the canvas is not the hitbox.

The hitbox lives in ENEMY_CONFIGS (the collision box); the canvas is the
sprite's surface. They are different numbers and the manifest must carry
only the second one. The guard: the hitbox fits inside the canvas, always.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import load_set
from src.entities.enemies.enemy import ENEMY_CONFIGS, EnemyKind

ENEMY_SETS = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


@pytest.fixture(scope="module")
def enemies_root() -> Path:
    return ROOT / "Assets" / "sprites" / "enemies"


@pytest.mark.parametrize("name", ENEMY_SETS)
def test_the_hitbox_fits_inside_the_canvas(enemies_root: Path, name: str) -> None:
    anim_set = load_set(name, root=enemies_root)
    # ENEMY_CONFIGS is keyed by the EnemyKind enum, not by the bare string.
    config = ENEMY_CONFIGS[EnemyKind(name)]
    assert config.width <= anim_set.canvas[0], name
    assert config.height <= anim_set.canvas[1], name


def test_the_hitbox_is_not_the_canvas() -> None:
    """A guard against the two being conflated: they are not equal."""
    enemies_root = ROOT / "Assets" / "sprites" / "enemies"
    anim_set = load_set("scout", root=enemies_root)
    config = ENEMY_CONFIGS[EnemyKind("scout")]
    assert (config.width, config.height) != anim_set.canvas
