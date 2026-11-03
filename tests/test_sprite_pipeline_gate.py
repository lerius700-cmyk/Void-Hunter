"""BLOQUE 75: the gate runs and passes on the shipped tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# The gate runs a whole phase's checks: a hung gate would hang the CI job
# until `timeout-minutes: 15` kills it, with no diagnostic. The gate takes
# ~10s when it is healthy, so this is a wide margin that still fits inside
# the job's budget -- and a hang is reported as a failure instead of
# vanishing.
GATE_TIMEOUT_S = 300


def test_the_gate_passes():
    cmd = [sys.executable, str(ROOT / "tools" / "sprite_pipeline" / "gate.py")]
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
    assert "PHASE 1 GATE OK" in out
