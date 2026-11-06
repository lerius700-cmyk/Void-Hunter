"""BLOQUE 75: the game can report whether its enemy pipeline is available.

After Phase 2 the runtime reads the enemy manifests every frame to draw
the enemies. A frozen build that does not carry them falls back to the
old draw path SILENTLY -- the game still runs, the enemies still appear,
and nothing anywhere reports an error.

This command is the check that would have caught it, and it has to run
inside the frozen build too, so it lives in the game.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENEMY_KINDS = (
    "scout", "cruiser", "drone", "heavy",
    "kamikaze", "sniper", "turret", "mine_asteroid",
)


def test_the_command_reports_every_enemy_set() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "pipeline check OK" in out
    for kind in ENEMY_KINDS:
        assert kind in out, kind


def test_the_command_reports_the_pivot_and_the_scale() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "pivot=fixed" in proc.stdout
    assert "scale=(1.05, 1.05)" in proc.stdout


def test_the_command_reports_the_thirty_layers() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "layers: 30" in proc.stdout
