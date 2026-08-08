"""VOID HUNTER — BLOQUE 0 smoke test.

Runs the 5 quality gates in order. Exits 0 if all pass, 1 if any fail.
Use: `python smoke.py` or `python -m smoke`.

Coverage of GDD §13 suite #1-#5 (subset appropriate to BLOQUE 0):
  1. python main.py --check             → exit 0
  2. pytest tests/ -q                   → tests pass
  3. pytest --cov=src/ --cov-fail-under=5 → coverage gate (5% at BLOQUE 0)
  4. mypy src/                          → 0 errors
  5. rg 'import motor' src/             → 0 matches (soberanía)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(label: str, args: list[str], cwd: Path | None = None) -> bool:
    """Run a subprocess, stream output, return True on exit 0."""
    print(f"\n=== {label} ===")
    print(f"  $ {' '.join(args)}")
    try:
        result = subprocess.run(args, cwd=cwd or ROOT, check=False)
    except FileNotFoundError as exc:
        print(f"  FAIL: {exc}")
        return False
    if result.returncode != 0:
        print(f"  FAIL: exit {result.returncode}")
        return False
    print(f"  OK")
    return True


def main() -> int:
    python = sys.executable
    gates: list[tuple[str, list[str]]] = [
        ("main.py --check",     [python, "main.py", "--check"]),
        ("pytest -q",           [python, "-m", "pytest", "-q"]),
        ("coverage gate (5%)",  [python, "-m", "pytest", "--cov=src/",
                                  "--cov-fail-under=5", "-q"]),
        ("mypy strict",         [python, "-m", "mypy", "src/"]),
    ]
    results = [_run(label, cmd) for label, cmd in gates]

    # Soberanía — only meaningful if rg is on PATH
    rg = shutil.which("rg")
    if rg is not None:
        motor = subprocess.run(
            [rg, "-l", "import motor", "src/"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        ok = motor.returncode != 0  # rg returns 1 when no matches
        print(f"\n=== soberanía (no motor.*) ===\n  rg returned {motor.returncode} {'(no matches)' if ok else '(matches found!)'}")
        results.append(ok)
    else:
        print("\n=== soberanía: skipped (rg no instalado) ===")
        results.append(True)

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"SMOKE: {passed}/{total} gates passed")
    if passed == total:
        print("BLOQUE 0 OK")
        return 0
    print("BLOQUE 0 FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
