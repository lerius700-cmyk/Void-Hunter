"""BLOQUE 74: the contract guard must pass on the shipped set and fail on a broken one.

`tools/sprite_pipeline/verify_contract.py` is the guard that says the sprite
pipeline still behaves. A guard nobody exercises is decoration, so this
module runs it in both directions: green on the shipped tree, red on a copy
whose anchors were corrupted.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "tools" / "sprite_pipeline" / "verify_contract.py"
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_the_contract_holds_on_the_shipped_set(display):
    """GOLIATH is green: every frame resolves, no FAIL state survives, the
    anchors are deterministic and fresh, and the findings match the
    measured contract."""
    result = _run("goliath")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONTRACT OK" in result.stdout


def test_the_contract_detects_a_corrupted_anchors_file(tmp_path, display):
    """A guard that cannot fail is decoration. Corrupt a COPY of the set and
    the guard must notice."""
    source = ROOT / "Assets" / "sprites" / "bosses" / "goliath"
    copy = tmp_path / "goliath"
    shutil.copytree(source, copy)
    with (copy / "anchors.toml").open("a", encoding="utf-8") as handle:
        handle.write("\n# corrupt on purpose\n")

    result = _run("goliath", "--root", str(tmp_path))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "CONTRACT BROKEN" in result.stdout
    assert "stale" in result.stdout
