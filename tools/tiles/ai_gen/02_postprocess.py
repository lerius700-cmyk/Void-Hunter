"""Post-process the 6 raw AI generations into final 320x480 16-color tiles.

Pipeline per tile:
1. Load raw from tools/tiles/ai_gen/_raw/<name>.png (downloads first if needed)
2. Crop center 320 wide (X = (W-320)/2 to (W+320)/2)
3. Resize to 320x480 with LANCZOS then NEAREST (preserves pixel art)
4. Quantize to 16 colors with MEDIANCUT
5. Save to Assets/background/tiles/act1/<name>.png

Also produces:
- _contact_sheet.png  (1920x480, 6 tiles horizontal)
- _stacked_preview.png (320x2880, 6 tiles vertical)

Usage:
    python tools/tiles/ai_gen/02_postprocess.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

# Paths
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[2]
RAW_DIR = THIS_DIR / "_raw"
OUT_DIR = REPO_ROOT / "Assets" / "background" / "tiles" / "act1"
RESPONSE_JSON = THIS_DIR / "_batch_response.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Tile definitions (must match the order in _batch_args.json)
TILES = [
    "tile_01_atmosphere_exit",
    "tile_02_enter_belt",
    "tile_03_mid_belt",
    "tile_04_peak_belt",
    "tile_05_exit_belt",
    "tile_06_open_stars",
]

TILE_W = 320
TILE_H = 480
PALETTE_MAX = 16


MCODE_TOOLS = r"C:\Users\Lerius\.minimax\bin\mcode-tools.cmd"


def get_asset_url(node_id: str) -> str:
    """Call mcode-tools get_asset_url to fetch a short-lived URL for a node."""
    result = subprocess.run(
        [MCODE_TOOLS, "get-asset-url", node_id],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data["download_url"]


def download_node(node_id: str, dest: Path) -> None:
    """Download a node to dest via a short-lived URL."""
    import urllib.request

    url = get_asset_url(node_id)
    print(f"  Downloading {node_id[:16]}... from short-lived URL")
    urllib.request.urlretrieve(url, dest)
    print(f"  Saved: {dest.name} ({dest.stat().st_size} bytes)")


def crop_center_strip(img: Image.Image, target_w: int) -> Image.Image:
    """Crop center target_w wide strip from img."""
    w, _ = img.size
    if w == target_w:
        return img
    x0 = (w - target_w) // 2
    x1 = x0 + target_w
    return img.crop((x0, 0, x1, img.size[1]))


def resize_to_target(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize preserving pixel art feel: LANCZOS smooth first, then NEAREST."""
    w, h = img.size
    if w == target_w and h == target_h:
        return img
    # LANCZOS to smooth compression artifacts
    if h != target_h:
        scale = target_h / h
        new_w = max(1, int(round(w * scale)))
        img = img.resize((new_w, target_h), Image.LANCZOS)
    # Final NEAREST resize to target_w
    if img.size[0] != target_w:
        img = img.resize((target_w, target_h), Image.NEAREST)
    return img


def quantize_16(img: Image.Image) -> Image.Image:
    """Quantize to 16 colors using MEDIANCUT."""
    return img.convert("RGB").quantize(colors=PALETTE_MAX, method=Image.Quantize.MEDIANCUT).convert("RGB")


def postprocess_one(tile_name: str, raw_path: Path) -> Path:
    """Process one tile: load raw, crop, resize, quantize, save final."""
    out_path = OUT_DIR / f"{tile_name}.png"
    print(f"\n[tile] {tile_name}")
    print(f"  Loading raw: {raw_path.name}")
    raw = Image.open(raw_path)
    print(f"  Raw size: {raw.size}, mode: {raw.mode}")
    cropped = crop_center_strip(raw, TILE_W)
    print(f"  After crop: {cropped.size}")
    resized = resize_to_target(cropped, TILE_W, TILE_H)
    print(f"  After resize: {resized.size}")
    quantized = quantize_16(resized)
    unique_colors = len(quantized.getcolors(maxcolors=256) or [])
    print(f"  After quantize: {quantized.size}, unique colors: {unique_colors}")
    quantized.save(out_path, optimize=True)
    print(f"  Saved: {out_path}")
    return out_path


def build_contact_sheet(tile_paths: list[Path]) -> Path:
    """Build 1920x480 contact sheet of 6 tiles side by side."""
    sheet = Image.new("RGB", (TILE_W * 6, TILE_H), (4, 8, 20))
    for i, p in enumerate(tile_paths):
        tile = Image.open(p).convert("RGB")
        sheet.paste(tile, (i * TILE_W, 0))
    out = OUT_DIR / "_contact_sheet.png"
    sheet.save(out, optimize=True)
    print(f"\nContact sheet: {out}")
    return out


def build_stacked_preview(tile_paths: list[Path]) -> Path:
    """Build 320x2880 stacked preview of 6 tiles vertically."""
    stacked = Image.new("RGB", (TILE_W, TILE_H * 6), (4, 8, 20))
    for i, p in enumerate(tile_paths):
        tile = Image.open(p).convert("RGB")
        stacked.paste(tile, (0, i * TILE_H))
    out = OUT_DIR / "_stacked_preview.png"
    stacked.save(out, optimize=True)
    print(f"Stacked preview: {out}")
    return out


def main() -> int:
    if not RESPONSE_JSON.exists():
        print(f"ERROR: {RESPONSE_JSON} not found. Run 01_generate_tiles.py first.")
        return 1

    print("=" * 60)
    print("Post-process 6 AI tiles")
    print("=" * 60)

    with open(RESPONSE_JSON, encoding="utf-8-sig") as f:
        response = json.load(f)

    # The response may be a list of result items (per item in the batch).
    # Each item has node_id and file_name on success.
    success_items = response.get("success_items") or response.get("data", {}).get("success_items") or []
    if not success_items:
        # Try alternative: response is a list directly
        if isinstance(response, list):
            success_items = response
        else:
            print(f"ERROR: Could not find success_items in response.")
            print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else type(response)}")
            return 1

    print(f"Success items: {len(success_items)}")

    final_paths: list[Path] = []
    for i, item in enumerate(success_items[:6]):
        if i >= len(TILES):
            break
        node_id = item.get("node_id")
        file_name = item.get("file_name", f"{TILES[i]}.png")
        if not node_id:
            print(f"WARN: item {i} has no node_id, skipping")
            continue
        # Download raw to _raw/
        raw_path = RAW_DIR / file_name
        if not raw_path.exists():
            try:
                download_node(node_id, raw_path)
            except Exception as e:
                print(f"ERROR downloading {node_id}: {e}")
                continue
        else:
            print(f"  Reusing cached raw: {raw_path.name}")
        # Post-process
        try:
            final = postprocess_one(TILES[i], raw_path)
            final_paths.append(final)
        except Exception as e:
            print(f"ERROR post-processing {TILES[i]}: {e}")
            continue

    if not final_paths:
        print("\nERROR: no tiles post-processed successfully.")
        return 1

    print("\n" + "=" * 60)
    print(f"Post-processed {len(final_paths)}/6 tiles")
    print("=" * 60)
    build_contact_sheet(final_paths)
    build_stacked_preview(final_paths)
    print(f"\nWrap time: {6 * TILE_H / 12:.0f} s = {6 * TILE_H / 12 / 60:.1f} min @ 12 px/s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
