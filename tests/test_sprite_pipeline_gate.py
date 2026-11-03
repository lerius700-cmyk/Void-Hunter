"""BLOQUE 75: the gate runs and passes on the shipped tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_the_gate_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sprite_pipeline" / "gate.py")],
        capture_output=True,
        cwd=str(ROOT),
    )
    out = proc.stdout.decode("utf-8")
    assert proc.returncode == 0, out + proc.stderr.decode("utf-8")
    assert "PHASE 1 GATE OK" in out
