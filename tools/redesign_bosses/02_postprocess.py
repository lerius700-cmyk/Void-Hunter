"""Stage 2: Post-process AI bases for GOLIATH (BLOQUE 60).

For each state:
  1. Load the 1024x1024 base PNG.
  2. Crop bottom 15% (removes the AI watermark).
  3. Rotate 90 CCW (face down in the playfield).
  4. Center-crop to square.
  5. Resize to 96x80 with LANCZOS.
  6. Map pixels to the 64-color palette.
  7. Run the shared damero-cleaner with distance_threshold=90.
  8. Threshold alpha to binary.
  9. Save to Assets/sprites/redesign/goliath/<state>/_source.png.

Usage:
    python tools/redesign_bosses/02_postprocess.py
    python tools/redesign_bosses/02_postprocess.py --state idle
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from tools.redesign_bosses._specs import GOLIATH_SPEC
from tools.redesign_ships._palette_map import map_image_to_palette

# The ships pipeline file is named ``02_postprocess.py`` — its leading
# digit is not a valid Python identifier, so a normal ``import
# tools.redesign_ships._02_postprocess`` raises ``ModuleNotFoundError``.
# Load it by file path with importlib instead. This is the same pattern
# the test suite uses (see tests/test_postprocess_shared.py).
_SHIP_POSTPROCESS_PATH = (
    PROJECT_ROOT / "tools" / "redesign_ships" / "02_postprocess.py"
)
_ship_pp_spec = importlib.util.spec_from_file_location(
    "_redesign_ships_postprocess", _SHIP_POSTPROCESS_PATH
)
assert _ship_pp_spec is not None and _ship_pp_spec.loader is not None, (
    f"could not load spec for {_SHIP_POSTPROCESS_PATH}"
)
_ship_pp = importlib.util.module_from_spec(_ship_pp_spec)
sys.modules["_redesign_ships_postprocess"] = _ship_pp
_ship_pp_spec.loader.exec_module(_ship_pp)
_transparentize_damero_after_resize = _ship_pp._transparentize_damero_after_resize

BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "bosses" / "goliath" / "_base"
REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "goliath"
SOURCE_SIZE = 96
SOURCE_HEIGHT = 80
WATERMARK_CROP_BOTTOM_PCT = 0.15
TRANSPARENTIZE_DISTANCE_THRESHOLD = 90.0  # BLOQUE 60: boss needs wider threshold


def load_base(state_key: str) -> Image.Image:
    base_path = BASE_DIR / f"goliath_{state_key}_base.png"
    if not base_path.exists():
        raise FileNotFoundError(f"missing base: {base_path} (run stage 1 first)")
    return Image.open(base_path).convert("RGBA")


def preprocess_base(base: Image.Image) -> Image.Image:
    """Crop + rotate + center-crop square."""
    w, h = base.size
    crop_h = int(h * (1 - WATERMARK_CROP_BOTTOM_PCT))
    cropped = base.crop((0, 0, w, crop_h))
    rotated = cropped.rotate(90, expand=True)
    rw, rh = rotated.size
    side = min(rw, rh)
    left = (rw - side) // 2
    top = (rh - side) // 2
    return rotated.crop((left, top, left + side, top + side))


def make_source_png(base: Image.Image, out_path: Path) -> None:
    """Full pipeline: square -> resize 96x80 -> palette -> transparentize -> save."""
    square = preprocess_base(base)
    small = square.resize((SOURCE_SIZE, SOURCE_HEIGHT), Image.LANCZOS)
    small = _transparentize_damero_after_resize(
        small, distance_threshold=TRANSPARENTIZE_DISTANCE_THRESHOLD,
    )
    r, g, b, a = small.split()
    a = a.point(lambda v: 255 if v >= 128 else 0)
    rgb = map_image_to_palette(Image.merge("RGB", (r, g, b)))
    r2, g2, b2 = rgb.split()
    out = Image.merge("RGBA", (r2, g2, b2, a))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)


def postprocess_one(state_key: str) -> None:
    out = REDESIGN_DIR / state_key / "_source.png"
    if out.exists():
        print(f"[skip] {state_key}")
        return
    base = load_base(state_key)
    make_source_png(base, out)
    print(f"[src ] {state_key} -> {out}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", help="Post-process only this state key")
    args = parser.parse_args()
    targets = GOLIATH_SPEC.states
    if args.state:
        targets = [s for s in targets if s.key == args.state]
        if not targets:
            print(f"unknown state: {args.state}")
            return 1
    for spec in targets:
        postprocess_one(spec.key)
    print(f"\nDone. {len(targets)} state(s) post-processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
