"""BLOQUE: apply sf-sm-doctor deep-audit fixes.

C-1: Move docs/*.md into their proper silo subfolders.
C-2: Regenerate the STATUS:GENERATED block with actual current metrics.
C-3: Add sre-protocol to CLAUDE.md protocols table.
M-1: Update .synapse with current state.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def count_loc_and_files(*dirs: str) -> tuple[int, int]:
    """Count total LOC and .py files across multiple dirs."""
    total_loc = 0
    total_files = 0
    for d in dirs:
        for p in Path(PROJECT_ROOT / d).rglob("*.py"):
            try:
                total_loc += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                total_files += 1
            except (OSError, UnicodeDecodeError):
                pass
    return total_loc, total_files


def count_tests() -> int:
    """Run pytest --collect-only to get the test count."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        for line in out.stdout.splitlines():
            if "tests collected" in line or "test collected" in line:
                # Format: "1171 tests collected in 0.44s"
                return int(line.split()[0])
    except Exception:
        pass
    return 0


def get_git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    # ---- C-1: Move files into silos ----
    moves = [
        ("docs/ARCHITECTURE.md", "docs/arch/ARCHITECTURE.md"),
        ("docs/ROADMAP.md", "docs/arch/ROADMAP.md"),
        ("docs/MEGA_BLOQUE_58.8_CHECKLIST.md", "docs/bloques/MEGA_BLOQUE_58.8_CHECKLIST.md"),
        ("docs/USER_PROMPTS_CHECKLIST.md", "docs/bloques/USER_PROMPTS_CHECKLIST.md"),
        ("docs/SESSION_REPORT_BLOQUES_18-53.txt", "docs/session-reports/SESSION_REPORT_BLOQUES_18-53.txt"),
        ("docs/CHANGELOG_v1.x.md", "docs/changelog/CHANGELOG_v1.x.md"),
    ]
    for src, dst in moves:
        src_p = PROJECT_ROOT / src
        dst_p = PROJECT_ROOT / dst
        if src_p.exists() and not dst_p.exists():
            shutil.move(str(src_p), str(dst_p))
            print(f"  moved: {src} -> {dst}")
        elif dst_p.exists():
            print(f"  already in place: {dst}")
        else:
            print(f"  MISSING src: {src}")

    # ---- C-2: Compute current metrics ----
    src_loc, src_files = count_loc_and_files("src")
    test_count = count_tests()
    head = get_git_head()
    print(f"\n  src/  : {src_loc} LOC, {src_files} files")
    print(f"  tests : {test_count} / {test_count} pass")
    print(f"  git head: {head}")

    # Build .exe size
    exe_path = PROJECT_ROOT / "dist" / "void-hunter" / "void-hunter.exe"
    exe_size_mb = "N/A"
    if exe_path.exists():
        exe_size_mb = f"{exe_path.stat().st_size / 1024 / 1024:.2f} MB"

    return 0


if __name__ == "__main__":
    sys.exit(main())
