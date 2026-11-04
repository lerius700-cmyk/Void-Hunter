"""BLOQUE 75: the Phase 2 gate runs and passes on the shipped tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

GATE_TIMEOUT_S = 600


def test_the_phase_2_gate_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "sprite_pipeline" / "gate.py"), "--phase", "2"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            cwd=str(ROOT),
            timeout=GATE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"the gate did not finish in {GATE_TIMEOUT_S}s")
    out = proc.stdout.decode("utf-8")
    assert proc.returncode == 0, out + proc.stderr.decode("utf-8")
    assert "PHASE 2 GATE OK" in out
