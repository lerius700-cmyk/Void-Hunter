"""Stage 2: Postprocess MINE-ASTEROID bases + copy closed state (BLOQUE 63).

Takes the 4 1024x1024 AI bases in
``Assets/sprites/redesign/_base/mine_asteroid_<state>_base.png``
and produces the final game-ready sprite sheets in
``Assets/sprites/enemies/mine_asteroid/<state>/frame_NN.png``.

Reuses the existing pipeline from
``tools/redesign_ships/02_postprocess.py`` (LANCZOS resize to 32x32 +
damero transparentize pass).

Then, copy ``Assets/sprites/asteroids/round.png`` byte-for-byte to
``Assets/sprites/enemies/mine_asteroid/closed/frame_00.png`` so the
closed state is visually IDENTICAL to a regular asteroid (perfect
camo requires byte-equal pixels).

Frame counts per state (from spec):
  - opening: 3 frames (00, 01, 02)
  - open: 1 frame (00)
  - closing: 3 frames (00, 01, 02)
  - death: 10 frames (00..09)
  - closed: 1 frame (00) — copied from round.png

Usage:
    cd D:\\AI\\void-hunter
    .venv\\Scripts\\python.exe tools/postprocess_mine_asteroid.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

# Reuse the existing pipeline: the helper lives in
# ``tools/redesign_ships/02_postprocess.py`` (a module named with a
# numeric prefix, not importable by simple dotted path). Use
# importlib to load it by file path.
import importlib.util as _importlib_util
_postprocess_path = Path(__file__).parent / "redesign_ships" / "02_postprocess.py"
_spec = _importlib_util.spec_from_file_location("redesign_postprocess", _postprocess_path)
_postprocess_mod = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_postprocess_mod)  # type: ignore
_damero = _postprocess_mod._transparentize_damero_after_resize


# Frame counts per state. The opening/closing transitions are 3 frames
# each, the open state is 1 frame, and the death sequence is 10 frames.
# These are the canonical counts the integration site (Enemy.animation_path)
# picks from via the state_timer.
FRAME_COUNTS = {
    "opening": 3,
    "open": 1,
    "closing": 3,
    "death": 10,
    "closed": 1,
}


BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
OUT_DIR = PROJECT_ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"
ASTER_ROUND = PROJECT_ROOT / "Assets" / "sprites" / "asteroids" / "round.png"


def postprocess_one(state: str, frame_count: int) -> None:
    """For a given state, take the AI base, LANCZOS-resize to 32x32,
    apply the damero transparentize pass, and save ``frame_count``
    copies to the output directory.

    We write ``frame_count`` copies because each state is a 1-frame
    cycle in BLOQUE 63 (the per-state animation comes from
    sprite-sheets / state_timer-driven frame index, not multi-frame
    rows in a single sprite). Multiple files keep the loader
    consistent with the BLOQUE 59/61/62 pattern.
    """
    if state == "closed":
        # Closed is NOT AI-generated; it's a copy of round.png.
        out_dir = OUT_DIR / "closed"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "frame_00.png"
        if not out_path.exists():
            shutil.copy2(ASTER_ROUND, out_path)
            print(f"[copy] {out_path} <- {ASTER_ROUND}")
        else:
            print(f"[skip] {out_path} already exists")
        return
    base_path = BASE_DIR / f"mine_asteroid_{state}_base.png"
    if not base_path.exists():
        print(f"[ERR ] missing base: {base_path}")
        return
    out_dir = OUT_DIR / state
    out_dir.mkdir(parents=True, exist_ok=True)
    # Load + LANCZOS resize to 32x32. Convert to RGBA first so the
    # damero pass has an alpha channel to work on.
    img = Image.open(base_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img32 = img.resize((32, 32), Image.LANCZOS)
    img32 = _damero(img32)
    for i in range(frame_count):
        out_path = out_dir / f"frame_{i:02d}.png"
        if not out_path.exists():
            img32.save(out_path)
            print(f"[save] {out_path} ({out_path.stat().st_size} bytes)")
        else:
            print(f"[skip] {out_path} already exists")


def main() -> int:
    for state, count in FRAME_COUNTS.items():
        postprocess_one(state, count)
    print("\nDone. MINE-ASTEROID sprite sheets ready in:")
    print(f"  {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
