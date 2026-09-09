"""Stage 2: Postprocess MINE-ASTEROID bases + copy closed state (BLOQUE 63 + 65).

Takes the AI-generated 1024x1024 bases in
``Assets/sprites/redesign/_base/mine_asteroid_<state>_base.png``
and produces the final game-ready sprite sheets in
``Assets/sprites/enemies/mine_asteroid/<state>/frame_NN.png``.

BLOQUE 65: 4-state cycle (closed/open1/open2/open3). The legacy
5-state cycle (closed/opening/open/closing) is replaced. The
`open/` directory now contains the new ship reference (BLOQUE 65
swap). Each state has 1 frame (the per-state animation is the
4-frame cycle itself, not multi-frame within a single state).

Reuses the existing pipeline from
``tools/redesign_ships/02_postprocess.py`` (LANCZOS resize to 64x64
+ damero transparentize pass).

Then, copy ``Assets/sprites/asteroids/round.png`` byte-for-byte to
``Assets/sprites/enemies/mine_asteroid/closed/frame_00.png`` so the
closed state is visually IDENTICAL to a regular asteroid (perfect
camo requires byte-equal pixels).

Frame counts per state (from spec):
  - closed: 1 frame (00) — copied from round.png
  - open1: 1 frame (00) — 25% open (BLOQUE 65)
  - open2: 1 frame (00) — 75% open (BLOQUE 65)
  - open: 1 frame (00) — 100% open / open3 (new ship reference, BLOQUE 65)
  - death: 10 frames (00..09)

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


# BLOQUE 65: 64x64 sprites (was 32x32 in BLOQUE 63) to match the
# asteroid size (which was bumped to 64x64 in BLOQUE 64.A).
SOURCE_SIZE = 64

# Frame counts per state. BLOQUE 65: each non-death state is a
# single static frame; the 4-frame cycle plays the opening sequence
# over 0.6s (open1=0.2s + open2=0.2s + open3=indefinite).
FRAME_COUNTS = {
    "closed": 1,
    "open1": 1,
    "open2": 1,
    "open": 1,    # BLOQUE 65: this is the open3 / terminal vulnerable state
    "death": 10,
}


BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
OUT_DIR = PROJECT_ROOT / "Assets" / "sprites" / "enemies" / "mine_asteroid"
ASTER_ROUND = PROJECT_ROOT / "Assets" / "sprites" / "asteroids" / "round.png"


def postprocess_one(state: str, frame_count: int) -> None:
    """For a given state, take the AI base, LANCZOS-resize to 64x64,
    apply the damero transparentize pass, and save ``frame_count``
    copies to the output directory.

    BLOQUE 65: 'open' is special-cased — the canonical `open/frame_00.png`
    is the user's new ship reference (processed from _new_reference_open.png
    by the BLOQUE 65 integration step), NOT an AI-generated base. We
    skip postprocess for 'open' here.
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
    if state == "open":
        # BLOQUE 65: 'open' is the user's new ship reference, not an
        # AI base. The reference is processed separately (see the
        # BLOQUE 65 reference processing step in the integration
        # commit). Skip here.
        out_dir = OUT_DIR / "open"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "frame_00.png"
        if out_path.exists():
            print(f"[skip] {out_path} (BLOQUE 65 user reference)")
        else:
            print(f"[ERR ] {out_path} missing — run the BLOQUE 65 reference processing step")
        return
    base_path = BASE_DIR / f"mine_asteroid_{state}_base.png"
    if not base_path.exists():
        print(f"[ERR ] missing base: {base_path}")
        return
    out_dir = OUT_DIR / state
    out_dir.mkdir(parents=True, exist_ok=True)
    # Load + LANCZOS resize to 64x64. Convert to RGBA first so the
    # damero pass has an alpha channel to work on.
    img = Image.open(base_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img64 = img.resize((SOURCE_SIZE, SOURCE_SIZE), Image.LANCZOS)
    img64 = _damero(img64)
    for i in range(frame_count):
        out_path = out_dir / f"frame_{i:02d}.png"
        if not out_path.exists():
            img64.save(out_path)
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
