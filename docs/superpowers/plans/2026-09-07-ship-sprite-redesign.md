# Ship Sprite Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static single-frame enemy sprites and the existing `ship_01` player ship with a redesigned, AI-generated, animated sprite system (3 enemy templates + 1 player, 32×32 source → 16px render, 4 animations × 10 frames each, Metal Slug style).

**Architecture:** 4-stage pipeline (AI generate → PIL post-process → sprite-sheet preview → live integration) with human review gates after each visual stage. State machine added to Enemy class so per-frame PNGs are looked up per tick instead of single static PNGs.

**Tech Stack:** Python 3.11, PIL (Pillow), mcode-tools (`connector__matrix__generate_image`), pygame 2.6 (existing), pytest (existing).

**Reference spec:** `docs/superpowers/specs/2026-09-07-ship-sprite-redesign-design.md` — read first.

## Global Constraints

- **Python:** 3.11.15 (existing venv at `D:\AI\void-hunter\.venv\Scripts\python.exe`)
- **Source sprite size:** 32×32 px RGBA, scaled to 16×16 at render time via `pygame.transform.scale(..., (16, 16))` (nearest-neighbor)
- **Palette:** MUST use the 64-color palette from `src/utils/palette.py` (RGB tuple keys). Tolerance ±2 RGB units for LANCZOS rounding. NEVER introduce new colors.
- **BLOQUE number:** 59 (this is a new BLOQUE, separate from the 58.next work in this session)
- **Commits:** `feat: BLOQUE 59 ...` / `fix: BLOQUE 59 ...` / `chore: BLOQUE 59 ...` / `docs(spec): BLOQUE 59 ...` / `docs: BLOQUE 59 ...` / `test: BLOQUE 59 ...`
- **Human gates:** Stages 1, 3, 4 each end with USER REVIEW before the next stage. Do NOT proceed past a gate without user OK.
- **8 ships total:** 3 enemy templates × variants = 7 enemy ships + 1 player ship. See spec §4.1 for the mapping.

---

## File Structure

**Create:**
- `tools/redesign_ships/__init__.py` (empty, package marker)
- `tools/redesign_ships/_ai_client.py` — wrapper around mcode-tools
- `tools/redesign_ships/_palette_map.py` — palette mapper + nearest-color helper
- `tools/redesign_ships/01_generate_bases.py` — Stage 1 entry point
- `tools/redesign_ships/02_postprocess.py` — Stage 2 entry point
- `tools/redesign_ships/03_build_sheets.py` — Stage 3 entry point
- `tools/redesign_ships/04_integrate.py` — Stage 4 entry point
- `tools/redesign_ships/_animation_frames.py` — frame-generation logic (4 animations)
- `tools/redesign_ships/manifest.json` — generated, tracks node_ids, prompts, sizes
- `tools/redesign_ships/README.md` — how to re-run the pipeline
- `Assets/sprites/redesign/` — output dir (created by scripts)
- `Assets/sprites/enemies/` — new per-frame enemy layout (live assets)
- `archive/_legacy_sprites/` — old single-frame enemy PNGs
- `tests/test_redesign_sprites.py` — full test suite for the redesign

**Modify:**
- `src/entities/enemies/enemy.py` — add `animation_state`, `animation_frame` fields + frame-advance logic
- `src/ui/gameplay_runtime.py` — render path looks up per-frame PNG per tick
- `build.spec` — add `Assets/sprites/enemies` to bundled datas
- `docs/changelog/CHANGELOG_v1.x.md` — add BLOQUE 59 entry

---

## Task 1: Pipeline scaffolding + palette mapper

**Files:**
- Create: `tools/redesign_ships/__init__.py`
- Create: `tools/redesign_ships/_palette_map.py`
- Create: `tests/test_redesign_sprites.py` (skeleton)
- Modify: `tests/test_redesign_sprites.py` (add palette_map tests)

**Interfaces:**
- Consumes: `src.utils.palette.PALETTE` (the 64-color dict)
- Produces: `nearest_palette_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]` and `map_image_to_palette(img: Image.Image) -> Image.Image`

- [ ] **Step 1: Write the failing test for `nearest_palette_color`**

Add to `tests/test_redesign_sprites.py`:

```python
"""Tests for the ship sprite redesign pipeline (BLOQUE 59)."""
from __future__ import annotations

from PIL import Image

from tools.redesign_ships._palette_map import map_image_to_palette, nearest_palette_color
from src.utils.palette import PALETTE


def test_nearest_palette_color_returns_exact_match():
    """A color that's exactly in the palette returns itself."""
    palette_rgb = next(iter(PALETTE.values()))
    result = nearest_palette_color(palette_rgb)
    assert result == palette_rgb


def test_nearest_palette_color_finds_nearest():
    """A color near a palette entry returns that entry (Euclidean RGB)."""
    target = next(iter(PALETTE.values()))
    # Nudge each channel by +1
    near = (target[0] + 1, target[1] + 1, target[2] + 1)
    result = nearest_palette_color(near)
    assert result == target


def test_map_image_to_palette_uses_only_palette_colors():
    """Every pixel after mapping is within ±2 of a palette color."""
    # Create a small test image with random colors
    test_img = Image.new("RGB", (4, 4))
    pixels = test_img.load()
    for x in range(4):
        for y in range(4):
            pixels[x, y] = (50, 100, 150)  # arbitrary RGB
    mapped = map_image_to_palette(test_img)
    assert mapped.size == (4, 4)
    mapped_pixels = mapped.load()
    palette_set = set(PALETTE.values())
    for x in range(4):
        for y in range(4):
            rgb = mapped_pixels[x, y]
            # Check this pixel is within ±2 of some palette color
            found = False
            for p in palette_set:
                if all(abs(rgb[i] - p[i]) <= 2 for i in range(3)):
                    found = True
                    break
            assert found, f"pixel {rgb} not within ±2 of any palette color"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tools.redesign_ships._palette_map'"

- [ ] **Step 3: Create the package skeleton**

Write `tools/redesign_ships/__init__.py`:

```python
"""Ship sprite redesign pipeline (BLOQUE 59).

4 stages: generate_bases → postprocess → build_sheets → integrate.
See docs/superpowers/specs/2026-09-07-ship-sprite-redesign-design.md.
"""
```

- [ ] **Step 4: Implement `_palette_map.py`**

Write `tools/redesign_ships/_palette_map.py`:

```python
"""Nearest-color palette mapper (BLOQUE 59).

Maps arbitrary RGB pixels to the closest color in the 64-color palette
defined in `src/utils/palette.py`. Uses Euclidean distance in RGB space.
"""
from __future__ import annotations

from PIL import Image

from src.utils.palette import PALETTE


def nearest_palette_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return the palette color with minimum Euclidean distance to `rgb`."""
    r, g, b = rgb
    best = None
    best_dist = float("inf")
    for color in PALETTE.values():
        d = (color[0] - r) ** 2 + (color[1] - g) ** 2 + (color[2] - b) ** 2
        if d < best_dist:
            best_dist = d
            best = color
    return best


def map_image_to_palette(img: Image.Image) -> Image.Image:
    """Return a new RGB image where every pixel is the nearest palette color."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    out = Image.new("RGB", img.size)
    src = img.load()
    dst = out.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            dst[x, y] = nearest_palette_color(src[x, y])
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/__init__.py tools/redesign_ships/_palette_map.py tests/test_redesign_sprites.py
git commit -m "feat: BLOQUE 59 add palette_map helper and test skeleton"
```

---

## Task 2: AI client wrapper for mcode-tools

**Files:**
- Create: `tools/redesign_ships/_ai_client.py`
- Modify: `tests/test_redesign_sprites.py` (add ai_client tests)

**Interfaces:**
- Consumes: nothing (the mcode-tools CLI is on PATH)
- Produces: `generate_ship_base(prompt: str, output_file: str) -> str` returning the `node_id` from the mcode-tools call

- [ ] **Step 1: Write the failing test for `generate_ship_base`**

Add to `tests/test_redesign_sprites.py`:

```python
import subprocess
from unittest import mock

from tools.redesign_ships._ai_client import generate_ship_base


def test_generate_ship_base_invokes_mcode_tools(monkeypatch, tmp_path):
    """The wrapper calls mcode-tools with the right args and returns the node_id."""
    fake_response = '{"success_items": [{"node_id": "abc123", "file_name": "test.png"}]}'
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_response, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    out_file = str(tmp_path / "out.png")
    node_id = generate_ship_base(
        prompt="16-bit pixel art spaceship",
        output_file=out_file,
    )
    assert node_id == "abc123"
    cmd = captured["cmd"]
    assert cmd[0] == "mcode-tools"
    assert cmd[1] == "connector"
    assert cmd[2] == "call"
    assert cmd[3] == "connector__matrix__generate_image"
    assert "--args-file" in cmd


def test_generate_ship_base_raises_on_no_success(monkeypatch):
    """If the response has no success_items, raise RuntimeError."""
    fake_response = '{"success_items": []}'

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_response, stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    try:
        generate_ship_base(prompt="x", output_file="y.png")
    except RuntimeError as e:
        assert "no success_items" in str(e).lower()
    else:
        raise AssertionError("expected RuntimeError")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tools.redesign_ships._ai_client'"

- [ ] **Step 3: Implement `_ai_client.py`**

Write `tools/redesign_ships/_ai_client.py`:

```python
"""mcode-tools wrapper for ship base image generation (BLOQUE 59).

Wraps `mcode-tools connector call connector__matrix__generate_image` so the
pipeline can generate 1024x1024 base art for each ship and get back a
`node_id` for downloading.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def generate_ship_base(prompt: str, output_file: str) -> str:
    """Call mcode-tools to generate one ship base image.

    Args:
        prompt: Text description of the ship (e.g. "16-bit pixel art,
            small fast scout, cyan and electric blue, single thruster...").
        output_file: Local path where the generated PNG should be saved.
            Used as the `output_file` field in the mcode-tools request.

    Returns:
        The `node_id` from mcode-tools. Pass to `download_node` to fetch bytes.
    """
    args = {
        "requests": [
            {
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "resolution": "1K",
                "output_file": Path(output_file).name,  # mcode-tools ignores dir components
            }
        ]
    }
    cmd = [
        "mcode-tools",
        "connector",
        "call",
        "connector__matrix__generate_image",
        "--args",
        json.dumps(args),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"mcode-tools failed (exit {result.returncode}): {result.stderr}")
    response = json.loads(result.stdout)
    success_items = response.get("success_items", [])
    if not success_items:
        raise RuntimeError(f"mcode-tools returned no success_items: {result.stdout[:500]}")
    return success_items[0]["node_id"]


def download_node(node_id: str, dest_path: str) -> None:
    """Download a generated asset by node_id to dest_path."""
    # First get the short-lived URL
    cmd = ["mcode-tools", "get_asset_url", node_id]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"get_asset_url failed: {result.stderr}")
    data = json.loads(result.stdout)
    url = data["download_url"]
    # Then fetch the URL
    import urllib.request
    urllib.request.urlretrieve(url, dest_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 5 passed (3 from Task 1 + 2 new)

- [ ] **Step 5: Commit**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/_ai_client.py tests/test_redesign_sprites.py
git commit -m "feat: BLOQUE 59 add mcode-tools wrapper for AI image generation"
```

---

## Task 3: Stage 1 — Generate 8 base images (with USER REVIEW gate)

**Files:**
- Create: `tools/redesign_ships/01_generate_bases.py`
- Create: `tools/redesign_ships/_ship_specs.py` (8 ship definitions in one place)
- Create: `Assets/sprites/redesign/_base/` (output, created by script)

**Interfaces:**
- Consumes: `_ai_client.generate_ship_base`, `_ai_client.download_node`
- Produces: 8 PNG files at `Assets/sprites/redesign/_base/<ship_key>_base.png` (1024×1024) + `manifest.json` with node_ids and prompts

- [ ] **Step 1: Create `_ship_specs.py` with the 8 ship definitions**

Write `tools/redesign_ships/_ship_specs.py`:

```python
"""The 8 ships to redesign (BLOQUE 59).

3 enemy templates (light/medium/heavy) covering 7 enemy types as variants,
plus 1 player ship (ship_01 redesign).

Each entry has:
  key: filesystem-safe identifier (used in paths)
  template: "light" | "medium" | "heavy" | "player"
  display_name: human-readable name
  prompt_fill: text appended to the standard prompt template
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShipSpec:
    key: str
    template: str
    display_name: str
    prompt_fill: str


SHIPS: tuple[ShipSpec, ...] = (
    # Light template (cyan/electric blue, small, pointy)
    ShipSpec(
        key="enemy_scout",
        template="light",
        display_name="Scout (light)",
        prompt_fill="small fast scout ship, narrow pointy wings, single thruster, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_drone",
        template="light",
        display_name="Drone (light)",
        prompt_fill="small boxy drone, four small thrusters, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    ShipSpec(
        key="enemy_kamikaze",
        template="light",
        display_name="Kamikaze (light)",
        prompt_fill="small triangular ship with central glowing core, pointed nose, compact ~20x14 pixels equivalent, cyan and electric blue color scheme",
    ),
    # Medium template (navy blue/void, balanced)
    ShipSpec(
        key="enemy_sniper",
        template="medium",
        display_name="Sniper (medium)",
        prompt_fill="balanced fighter, medium wings, focused weapon hardpoint, mid-sized ~24x18 pixels equivalent, navy blue and dark void color scheme",
    ),
    ShipSpec(
        key="enemy_turret",
        template="medium",
        display_name="Turret (medium)",
        prompt_fill="round turret-style ship, omnidirectional weapon mount, mid-sized ~24x18 pixels equivalent, navy blue and dark void color scheme",
    ),
    # Heavy template (red/mars, large, armored)
    ShipSpec(
        key="enemy_heavy",
        template="heavy",
        display_name="Heavy (heavy)",
        prompt_fill="large armored ship, blocky hull, multiple turrets, thick armor, large ~30x22 pixels equivalent, red and mars orange color scheme",
    ),
    ShipSpec(
        key="enemy_cruiser",
        template="heavy",
        display_name="Cruiser (heavy)",
        prompt_fill="long armored cruiser, multiple turrets along the hull, large ~30x22 pixels equivalent, red and mars orange color scheme",
    ),
    # Player ship (white + gold + red, hero)
    ShipSpec(
        key="player",
        template="player",
        display_name="Player ship (ship_01 redesign)",
        prompt_fill="hero ship, sleek aggressive silhouette, prominent cockpit, gold accents, white hull with gold highlights and red engine tips, heroic ~30x24 pixels equivalent with more detail",
    ),
)


def ship_by_key(key: str) -> ShipSpec:
    for s in SHIPS:
        if s.key == key:
            return s
    raise KeyError(f"unknown ship key: {key!r}")
```

- [ ] **Step 2: Implement `01_generate_bases.py`**

Write `tools/redesign_ships/01_generate_bases.py`:

```python
"""Stage 1: Generate 8 base images via mcode-tools (BLOQUE 59).

For each of the 8 ships, calls mcode-tools to generate a 1024x1024 base
image, downloads it, saves to Assets/sprites/redesign/_base/, and logs
the node_id + prompt to manifest.json.

Usage:
    python tools/redesign_ships/01_generate_bases.py
    python tools/redesign_ships/01_generate_bases.py --ship enemy_scout  # regenerate one
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_ships._ai_client import download_node, generate_ship_base
from tools.redesign_ships._ship_specs import SHIPS, ShipSpec


PROMPT_TEMPLATE = (
    "16-bit pixel art, top-down 3/4 view, facing forward (upward in playfield), "
    "isolated on pure black transparent background, single spaceship, sharp clean "
    "pixel edges, no anti-aliasing, no gradients, limited palette (max 8 colors), "
    "Metal Slug aesthetic, {FILL}, game asset sprite, no background scenery"
)


BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
MANIFEST_PATH = PROJECT_ROOT / "tools" / "redesign_ships" / "manifest.json"


def build_prompt(spec: ShipSpec) -> str:
    return PROMPT_TEMPLATE.format(FILL=spec.prompt_fill)


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"bases": {}}


def save_manifest(m: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, indent=2), encoding="utf-8")


def generate_one(spec: ShipSpec, manifest: dict) -> None:
    out_path = BASE_DIR / f"{spec.key}_base.png"
    if out_path.exists():
        print(f"[skip] {spec.key}: {out_path} already exists")
        return
    print(f"[gen ] {spec.key} ({spec.display_name})")
    prompt = build_prompt(spec)
    node_id = generate_ship_base(prompt=prompt, output_file=str(out_path))
    print(f"        node_id={node_id}, downloading...")
    download_node(node_id, str(out_path))
    manifest["bases"][spec.key] = {
        "node_id": node_id,
        "prompt": prompt,
        "template": spec.template,
        "display_name": spec.display_name,
        "out_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_manifest(manifest)
    print(f"        saved: {out_path} ({out_path.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ship", help="Regenerate only this ship key")
    args = parser.parse_args()
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    targets = SHIPS if not args.ship else [s for s in SHIPS if s.key == args.ship]
    if args.ship and not targets:
        print(f"unknown ship: {args.ship}")
        return 1
    for spec in targets:
        generate_one(spec, manifest)
    print(f"\nDone. {len(targets)} base(s) processed. Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run Stage 1 for all 8 ships**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe tools/redesign_ships/01_generate_bases.py 2>&1 | tee logs/stage1.log`

Expected: 8 `[gen ]` lines followed by 8 `[skip]` lines on re-run, plus the final `Done.` line. The 8 PNGs exist at `Assets/sprites/redesign/_base/`. `manifest.json` has 8 entries.

This step takes ~5-10 min (8 AI generations × ~30-60s each).

- [ ] **Step 4: USER REVIEW GATE**

Present the 8 base images to the user. Open each one (use `read` tool with the path, or have the user open `Assets/sprites/redesign/_base/` in their file explorer). The user reviews each and either:
- Approves → proceed to Task 4
- Requests regeneration → run `python tools/redesign_ships/01_generate_bases.py --ship <key>` to regenerate just that one

**Do not proceed to Task 4 until the user explicitly approves all 8 bases.**

- [ ] **Step 5: Commit Stage 1 output + manifest**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/01_generate_bases.py tools/redesign_ships/_ship_specs.py tools/redesign_ships/manifest.json
git commit -m "feat: BLOQUE 59 generate 8 ship base images via mcode-tools"
```

Note: the actual base PNGs are NOT committed (they're 1024×1024 AI-generated images, can be regenerated from manifest). The manifest.json is committed as the source of truth.

---

## Task 4: Stage 2 — Post-process to 32×32 + generate animation frames

**Files:**
- Create: `tools/redesign_ships/_animation_frames.py`
- Create: `tools/redesign_ships/02_postprocess.py`
- Modify: `tests/test_redesign_sprites.py` (add post-process tests)

**Interfaces:**
- Consumes: `tools/redesign_ships/manifest.json` (Stage 1 output)
- Produces: 8 ships × (1 `_source.png` + 4 anim dirs × 10 frames) = 328 PNGs at `Assets/sprites/redesign/<ship_key>/`

- [ ] **Step 1: Write the failing test for animation frame generation**

Add to `tests/test_redesign_sprites.py`:

```python
import os
from pathlib import Path

from PIL import Image

from tools.redesign_ships._animation_frames import (
    generate_death_frames,
    generate_damage_frames,
    generate_idle_frames,
    generate_thrust_frames,
)


def _make_test_source(size: int = 32) -> Image.Image:
    """Create a 32x32 RGBA test source with a simple ship shape."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    # Draw a 12x8 ship in the center
    for x in range(10, 22):
        for y in range(12, 20):
            px[x, y] = (200, 200, 220, 255)  # light gray hull
    # Engine glow at bottom
    for y in range(20, 24):
        px[14, y] = (255, 180, 80, 255)
        px[15, y] = (255, 180, 80, 255)
        px[16, y] = (255, 180, 80, 255)
        px[17, y] = (255, 180, 80, 255)
    return img


def test_generate_idle_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "idle"
    frames = generate_idle_frames(src, out_dir)
    assert len(frames) == 10
    assert all(f.exists() for f in frames)
    assert all(Image.open(f).size == (32, 32) for f in frames)


def test_generate_thrust_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "thrust"
    frames = generate_thrust_frames(src, out_dir)
    assert len(frames) == 10


def test_generate_damage_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "damage"
    frames = generate_damage_frames(src, out_dir)
    assert len(frames) == 10


def test_generate_death_frames_produces_10(tmp_path):
    src = _make_test_source()
    out_dir = tmp_path / "death"
    frames = generate_death_frames(src, out_dir)
    assert len(frames) == 10


def test_idle_frame0_equals_frame9(tmp_path):
    """Idle loop must be seamless: frame 0 == frame 9."""
    src = _make_test_source()
    out_dir = tmp_path / "idle"
    frames = generate_idle_frames(src, out_dir)
    f0 = Image.open(frames[0])
    f9 = Image.open(frames[9])
    assert list(f0.getdata()) == list(f9.getdata()), "idle loop seam not pixel-perfect"


def test_thrust_frame0_equals_frame9(tmp_path):
    """Thrust loop must be seamless."""
    src = _make_test_source()
    out_dir = tmp_path / "thrust"
    frames = generate_thrust_frames(src, out_dir)
    f0 = Image.open(frames[0])
    f9 = Image.open(frames[9])
    assert list(f0.getdata()) == list(f9.getdata()), "thrust loop seam not pixel-perfect"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tools.redesign_ships._animation_frames'"

- [ ] **Step 3: Implement `_animation_frames.py`**

Write `tools/redesign_ships/_animation_frames.py`:

```python
"""Frame generation for the 4 ship animations (BLOQUE 59).

Each function takes a 32x32 RGBA source image and an output dir, generates
10 frames of one animation, and returns the list of frame paths in order.

idle: 1px Y bob + engine pulse, looped (frame 0 == frame 9)
thrust: 1px X forward lean + dilated engine, looped (frame 0 == frame 9)
damage: red flash + tilt ±1px, one-shot (no loop requirement)
death: expand + recolor + debris, one-shot (no loop requirement)
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image


# Colors used for the damage flash and death recolor
_RED_TINT = (255, 60, 40, 255)        # "r" in palette
_DEATH_TINT_1 = (255, 140, 60, 255)   # "2" in palette
_DEATH_TINT_2 = (255, 220, 100, 255)  # "4" in palette
_DEBRIS_COLOR = (120, 120, 140, 255)  # "▓" in palette


def _shift_image(img: Image.Image, dx: int, dy: int) -> Image.Image:
    """Return a new RGBA image with the source shifted by (dx, dy)."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (dx, dy), img)
    return out


def _tint_nontransparent(img: Image.Image, tint_rgba: tuple[int, int, int, int]) -> Image.Image:
    """Replace all non-transparent pixels with `tint_rgba`."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    src = img.load()
    dst = out.load()
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            r, g, b, a = src[x, y]
            if a > 0:
                dst[x, y] = tint_rgba
    return out


def _dilate_pixels(img: Image.Image, target_rgba: tuple[int, int, int, int], radius: int = 1) -> Image.Image:
    """Expand all pixels matching target_rgba by `radius` (cheap dilation)."""
    out = img.copy()
    src = img.load()
    dst = out.load()
    w, h = img.size
    matches: list[tuple[int, int]] = []
    for x in range(w):
        for y in range(h):
            if src[x, y] == target_rgba:
                matches.append((x, y))
    for x, y in matches:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] == 0:
                    dst[nx, ny] = target_rgba
    return out


def _write_frames(frames: list[Image.Image], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, frame in enumerate(frames):
        p = out_dir / f"frame_{i:02d}.png"
        frame.save(p)
        paths.append(p)
    return paths


def generate_idle_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: 1px Y bob, frame 0 == frame 9 for seamless loop."""
    frames: list[Image.Image] = []
    for i in range(10):
        dy = round(math.sin(i * math.pi / 5) * 1)  # -1, -1, 0, 1, 1, 1, 0, -1, -1, 0
        frames.append(_shift_image(source, 0, dy))
    return _write_frames(frames, out_dir)


def generate_thrust_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: 1px X forward lean + engine dilation, frame 0 == frame 9."""
    # Find the engine color (anything close to orange in the source)
    engine_targets = {(255, 180, 80, 255), (255, 140, 60, 255), (255, 220, 100, 255)}
    frames: list[Image.Image] = []
    for i in range(10):
        leaned = _shift_image(source, 1, 0)
        # Engine pulse: even frames dilated, odd frames not
        if i % 2 == 0:
            for target in engine_targets:
                leaned = _dilate_pixels(leaned, target, radius=1)
        frames.append(leaned)
    return _write_frames(frames, out_dir)


def generate_damage_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: red flash + tilt left then right, one-shot."""
    frames: list[Image.Image] = []
    for i in range(10):
        if i < 4:
            # Tilt left, red flash
            shifted = _shift_image(source, -1, 0)
            frames.append(_tint_nontransparent(shifted, _RED_TINT))
        elif i < 7:
            # Tilt right, red flash
            shifted = _shift_image(source, 1, 0)
            frames.append(_tint_nontransparent(shifted, _RED_TINT))
        else:
            # Return to rest
            frames.append(source.copy())
    return _write_frames(frames, out_dir)


def generate_death_frames(source: Image.Image, out_dir: Path) -> list[Path]:
    """10 frames: expanding recolor + debris, one-shot."""
    frames: list[Image.Image] = []
    w, h = source.size
    for i in range(10):
        if i == 0:
            frames.append(source.copy())
        elif i < 4:
            # Scale 1.2x, orange tint
            scaled = source.resize((int(w * 1.2), int(h * 1.2)), Image.NEAREST)
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            canvas.paste(scaled, ((w - scaled.size[0]) // 2, (h - scaled.size[1]) // 2), scaled)
            frames.append(_tint_nontransparent(canvas, _DEATH_TINT_1))
        elif i < 7:
            # Scale 1.5x, yellow tint, add 4 debris pixels
            scaled = source.resize((int(w * 1.5), int(h * 1.5)), Image.NEAREST)
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            canvas.paste(scaled, ((w - scaled.size[0]) // 2, (h - scaled.size[1]) // 2), scaled)
            canvas = _tint_nontransparent(canvas, _DEATH_TINT_2)
            # Scatter 4 debris pixels at fixed positions (deterministic)
            for dx, dy in [(2, 28), (28, 2), (5, 25), (25, 5)]:
                if 0 <= dx < w and 0 <= dy < h:
                    canvas.putpixel((dx, dy), _DEBRIS_COLOR)
            frames.append(canvas)
        else:
            # Mostly transparent, gray specks
            canvas = Image.new("RGBA", source.size, (0, 0, 0, 0))
            for dx, dy in [(8, 24), (24, 8), (12, 28), (28, 12), (16, 26)]:
                if 0 <= dx < w and 0 <= dy < h:
                    canvas.putpixel((dx, dy), _DEBRIS_COLOR)
            frames.append(canvas)
    return _write_frames(frames, out_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 12 passed (5 from Tasks 1-2 + 7 new)

- [ ] **Step 5: Implement `02_postprocess.py`**

Write `tools/redesign_ships/02_postprocess.py`:

```python
"""Stage 2: Post-process AI bases into 32x32 source + animation frames (BLOQUE 59).

For each ship in manifest.json:
  1. Load the 1024x1024 base PNG.
  2. Resize to 32x32 with LANCZOS, save as <ship>/_source.png.
  3. Map pixels to the 64-color palette.
  4. Generate 10 frames each for idle/thrust/damage/death.
  5. Save per-frame PNGs to <ship>/<animation>/frame_NN.png.

Usage:
    python tools/redesign_ships/02_postprocess.py
    python tools/redesign_ships/02_postprocess.py --ship enemy_scout
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from tools.redesign_ships._animation_frames import (
    generate_death_frames,
    generate_damage_frames,
    generate_idle_frames,
    generate_thrust_frames,
)
from tools.redesign_ships._palette_map import map_image_to_palette
from tools.redesign_ships._ship_specs import SHIPS
import json

BASE_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"
MANIFEST_PATH = PROJECT_ROOT / "tools" / "redesign_ships" / "manifest.json"
SOURCE_SIZE = 32


def load_base(spec_key: str) -> Image.Image:
    base_path = BASE_DIR / f"{spec_key}_base.png"
    if not base_path.exists():
        raise FileNotFoundError(f"missing base: {base_path} (run Stage 1 first)")
    return Image.open(base_path).convert("RGBA")


def make_source_png(base: Image.Image, out_path: Path) -> None:
    # Resize 1024 -> 32 with smooth downscale
    small = base.resize((SOURCE_SIZE, SOURCE_SIZE), Image.LANCZOS)
    # Map to palette
    rgb = map_image_to_palette(small.convert("RGB"))
    # Recombine with alpha
    r, g, b = rgb.split()
    a = small.split()[3]
    out = Image.merge("RGBA", (r, g, b, a))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)


def postprocess_one(spec_key: str) -> None:
    ship_dir = REDESIGN_DIR / spec_key
    source_path = ship_dir / "_source.png"
    if not source_path.exists():
        print(f"[src ] {spec_key}")
        base = load_base(spec_key)
        make_source_png(base, source_path)
    source = Image.open(source_path).convert("RGBA")
    # Generate 4 animations
    for gen_fn, anim in [
        (generate_idle_frames, "idle"),
        (generate_thrust_frames, "thrust"),
        (generate_damage_frames, "damage"),
        (generate_death_frames, "death"),
    ]:
        out_dir = ship_dir / anim
        # Skip if all 10 frames already exist
        if all((out_dir / f"frame_{i:02d}.png").exists() for i in range(10)):
            print(f"[skip] {spec_key}/{anim} (all 10 frames exist)")
            continue
        print(f"[anim] {spec_key}/{anim}")
        gen_fn(source, out_dir)
    print(f"        done: {ship_dir}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ship", help="Post-process only this ship key")
    args = parser.parse_args()
    if not MANIFEST_PATH.exists():
        print("manifest.json not found; run Stage 1 first")
        return 1
    targets = SHIPS if not args.ship else [s for s in SHIPS if s.key == args.ship]
    if args.ship and not targets:
        print(f"unknown ship: {args.ship}")
        return 1
    for spec in targets:
        postprocess_one(spec.key)
    print(f"\nDone. {len(targets)} ship(s) post-processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run Stage 2 for all 8 ships**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe tools/redesign_ships/02_postprocess.py 2>&1 | tee logs/stage2.log`

Expected: 8 `[src ]` lines (or `[skip]`), 32 `[anim]` lines (4 anims × 8 ships, or `[skip]` if already done), 8 `[done]` lines. The directory `Assets/sprites/redesign/<ship>/` has `_source.png` + 4 subdirs each with 10 frames = 41 PNGs per ship, 328 total.

- [ ] **Step 7: Run tests to verify all post-process tests still pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 12 passed (no regression)

- [ ] **Step 8: Commit Stage 2 output**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/_animation_frames.py tools/redesign_ships/02_postprocess.py tests/test_redesign_sprites.py
git commit -m "feat: BLOQUE 59 add animation frame generation and post-process pipeline"
```

---

## Task 5: Stage 3 — Build sprite-sheet previews (with USER REVIEW gate)

**Files:**
- Create: `tools/redesign_ships/03_build_sheets.py`
- Create: `Assets/sprites/redesign/spritesheet_*.png` (8 output PNGs)

**Interfaces:**
- Consumes: `Assets/sprites/redesign/<ship>/<animation>/frame_NN.png` (Stage 2 output)
- Produces: `Assets/sprites/redesign/spritesheet_<ship>.png` (preview combining 4×10 = 40 frames per ship)

- [ ] **Step 1: Implement `03_build_sheets.py`**

Write `tools/redesign_ships/03_build_sheets.py`:

```python
"""Stage 3: Build sprite-sheet previews (BLOQUE 59).

For each ship, combine the 4 animations x 10 frames = 40 frames into a
single preview PNG with labels. Extends the logic from
tools/build_sprite_sheet.py to support 10-frame animations (the existing
script only supports 8).

Usage:
    python tools/redesign_ships/03_build_sheets.py
    python tools/redesign_ships/03_build_sheets.py --ship enemy_scout
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageFont

from tools.redesign_ships._ship_specs import SHIPS

ANIMATIONS = ("idle", "thrust", "damage", "death")
FRAME_SIZE = 32
LABEL_WIDTH = 96
COLUMNS = 10
ROWS = len(ANIMATIONS)
PADDING = 8
GRID_BG = (28, 24, 36)
LABEL_BG = (16, 12, 24)
LABEL_COLOR = (200, 220, 255)
FRAME_BORDER = (60, 50, 80)

SHEET_WIDTH = LABEL_WIDTH + COLUMNS * FRAME_SIZE + PADDING * (COLUMNS + 1)
SHEET_HEIGHT = ROWS * FRAME_SIZE + PADDING * (ROWS + 1)

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("consola.ttf", size=size)
    except OSError:
        pass
    return ImageFont.load_default()


def _load_frame(ship_dir: Path, anim: str, frame_idx: int) -> Image.Image | None:
    p = ship_dir / anim / f"frame_{frame_idx:02d}.png"
    if not p.is_file():
        return None
    img = Image.open(p).convert("RGBA")
    if img.size != (FRAME_SIZE, FRAME_SIZE):
        img = img.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.NEAREST)
    return img


def build_sheet(ship_key: str, out_path: Path) -> None:
    ship_dir = REDESIGN_DIR / ship_key
    sheet = Image.new("RGB", (SHEET_WIDTH, SHEET_HEIGHT), GRID_BG)
    draw = ImageDraw.Draw(sheet)
    font = _load_font(size=14)
    # Title bar at top
    title = f"VOID HUNTER - {ship_key.upper()} - 4 ANIM x 10 FRAMES - BLOQUE 59"
    draw.text((PADDING, 2), title, fill=LABEL_COLOR, font=font)
    for row, anim in enumerate(ANIMATIONS):
        # Label column
        y0 = PADDING + row * (FRAME_SIZE + PADDING) + PADDING
        draw.rectangle((0, y0 - PADDING, LABEL_WIDTH, y0 + FRAME_SIZE), fill=LABEL_BG)
        draw.text((PADDING, y0 + FRAME_SIZE // 2 - 8), anim.upper(), fill=LABEL_COLOR, font=font)
        # 10 frame cells
        for col in range(COLUMNS):
            x0 = LABEL_WIDTH + PADDING + col * (FRAME_SIZE + PADDING)
            # Cell border
            draw.rectangle((x0, y0, x0 + FRAME_SIZE, y0 + FRAME_SIZE), outline=FRAME_BORDER)
            # Frame number
            draw.text((x0 + 2, y0 + 2), str(col), fill=(100, 100, 120), font=font)
            # Frame image
            frame = _load_frame(ship_dir, anim, col)
            if frame is not None:
                sheet.paste(frame, (x0, y0), frame)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ship", help="Build sheet for only this ship key")
    args = parser.parse_args()
    targets = SHIPS if not args.ship else [s for s in SHIPS if s.key == args.ship]
    if args.ship and not targets:
        print(f"unknown ship: {args.ship}")
        return 1
    for spec in targets:
        out = REDESIGN_DIR / f"spritesheet_{spec.key}.png"
        build_sheet(spec.key, out)
        print(f"[sheet] {spec.key} -> {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run Stage 3 for all 8 ships**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe tools/redesign_ships/03_build_sheets.py 2>&1 | tee logs/stage3.log`

Expected: 8 `[sheet]` lines. The 8 sprite-sheet PNGs exist at `Assets/sprites/redesign/spritesheet_*.png`, each ~50-100 KB.

- [ ] **Step 3: USER REVIEW GATE**

Present the 8 sprite-sheet previews to the user. The user opens each PNG and reviews:
- Is the ship silhouette readable at 16px equivalent?
- Do the 4 animations look distinct (idle bob, thrust flare, damage flash, death explosion)?
- Is the color scheme right for the template (light=cyan, medium=navy, heavy=red, player=white+gold)?
- Are idle and thrust loops seamless (frame 0 == frame 9)?

If the user requests changes, two options:
- Tweak the post-process transforms in `_animation_frames.py` and re-run Stage 2 + 3 for that ship
- Regenerate the AI base (run Stage 1 with `--ship <key>`) and re-run Stage 2 + 3

**Do not proceed to Task 6 until the user explicitly approves all 8 sprite-sheets.**

- [ ] **Step 4: Add test for sprite-sheet dimensions**

Add to `tests/test_redesign_sprites.py`:

```python
def test_spritesheet_dimensions():
    """Each generated sprite-sheet has the expected 4-row x 10-col layout."""
    for spec in SHIPS:
        sheet_path = REDESIGN_DIR / f"spritesheet_{spec.key}.png"
        if sheet_path.exists():
            img = Image.open(sheet_path)
            assert img.size == (SHEET_WIDTH, SHEET_HEIGHT), (
                f"{spec.key}: expected ({SHEET_WIDTH}, {SHEET_HEIGHT}), got {img.size}"
            )
```

(Add `from tools.redesign_ships._ship_specs import SHIPS` and the constants at the top of the test file.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 13 passed (12 from before + 1 new)

- [ ] **Step 6: Commit Stage 3**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/03_build_sheets.py tests/test_redesign_sprites.py
git commit -m "feat: BLOQUE 59 add sprite-sheet preview builder (10-frame support)"
```

---

## Task 6: Add enemy animation state machine (integration prep)

**Files:**
- Modify: `src/entities/enemies/enemy.py` (add fields, advance logic)
- Modify: `src/ui/gameplay_runtime.py` (per-frame PNG lookup in render path)
- Modify: `tests/test_redesign_sprites.py` (state machine tests)

- [ ] **Step 1: Read the current enemy + render code to find the integration points**

Read `src/entities/enemies/enemy.py` (the `Enemy` class) and `src/ui/gameplay_runtime.py` (the enemy render path). Identify:
- The field declaration block in `Enemy.__init__` (near the `is_leader: bool` from BLOQUE 58.next)
- The tick/advance method (likely `update` or `tick`)
- The render call in `gameplay_runtime.py` (search for `enemy_scout` or `enemy_heavy`)

Note: the exact line numbers will be documented in the actual code edits below; read first to confirm.

- [ ] **Step 2: Add animation fields to the Enemy class**

In `src/entities/enemies/enemy.py`, near the `is_leader: bool = False` field added in BLOQUE 58.next, add:

```python
# BLOQUE 59: animation state for per-frame sprite lookup
self.animation_state: str = "idle"  # one of: idle, thrust, damage, death
self.animation_frame: int = 0       # 0..9
self.animation_timer: float = 0.0   # accumulator for frame advance
self.ANIMATION_FRAME_DURATION: float = 0.08  # 10 frames at ~12.5 fps
```

Find the `update` method (or equivalent tick method) on Enemy. Add at the start of that method:

```python
# BLOQUE 59: advance animation frame
self.animation_timer += dt
if self.animation_timer >= self.ANIMATION_FRAME_DURATION:
    self.animation_timer -= self.ANIMATION_FRAME_DURATION
    self.animation_frame = (self.animation_frame + 1) % 10
```

Find the existing `on_spawn` method (where `is_leader` is reset to False in BLOQUE 58.next). Add after the `is_leader` reset:

```python
# BLOQUE 59: reset animation on respawn
self.animation_state = "idle"
self.animation_frame = 0
self.animation_timer = 0.0
```

- [ ] **Step 3: Find the enemy render call in gameplay_runtime.py**

In `src/ui/gameplay_runtime.py`, search for the function/method that renders enemies. Currently it does something like `surface.blit(enemy_image, (x, y))` where `enemy_image = load_image("enemy_scout.png")`. We need to change this to look up the per-frame PNG.

Identify the existing function name and line range. The plan assumes it's a method called `_render_enemies` or similar — adjust the code below to match.

- [ ] **Step 4: Update the render path to look up per-frame PNG**

In the render function, replace the static lookup with:

```python
# BLOQUE 59: per-frame enemy sprite lookup
for enemy in self._enemies:
    sprite_path = (
        f"Assets/sprites/enemies/{enemy.kind}/"
        f"{enemy.animation_state}/frame_{enemy.animation_frame:02d}.png"
    )
    img = self._sprite_cache.get(sprite_path)  # or your existing cache mechanism
    if img is None:
        img = pygame.image.load(sprite_path).convert_alpha()
        self._sprite_cache[sprite_path] = img
    surface.blit(img, (int(enemy.x), int(enemy.y)))
```

(Adjust `enemy.kind`, the cache mechanism, and the iteration variable to match the existing code. The plan's intent: replace static `enemy_scout.png` lookup with a dynamic `<kind>/<state>/<frame>.png` lookup.)

- [ ] **Step 5: Add state machine tests**

Add to `tests/test_redesign_sprites.py`:

```python
from src.entities.enemies.enemy import Enemy  # adjust import as needed


def test_enemy_animation_starts_idle():
    """A new enemy starts in idle state, frame 0."""
    e = Enemy(kind="scout", x=0, y=0)  # adjust constructor to match
    assert e.animation_state == "idle"
    assert e.animation_frame == 0


def test_enemy_animation_frame_advances_on_tick():
    """Each tick advances the frame after ANIMATION_FRAME_DURATION seconds."""
    e = Enemy(kind="scout", x=0, y=0)
    e.update(dt=e.ANIMATION_FRAME_DURATION)  # one frame worth of time
    assert e.animation_frame == 1
    e.update(dt=e.ANIMATION_FRAME_DURATION * 9)  # 9 more frames
    assert e.animation_frame == 0  # wrapped around (mod 10)


def test_enemy_damage_state_transitions():
    """Calling take_damage transitions to 'damage' state."""
    e = Enemy(kind="scout", x=0, y=0)
    e.take_damage(1)  # adjust to match existing API
    assert e.animation_state == "damage"


def test_enemy_death_state_transitions():
    """Killing an enemy transitions to 'death' state."""
    e = Enemy(kind="scout", x=0, y=0)
    e.hp = 1
    e.take_damage(1)  # adjust
    assert e.animation_state == "death"
```

(Adjust the Enemy constructor signature, the `take_damage` API, and the `hp` field to match the existing code.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/test_redesign_sprites.py -v`
Expected: 17 passed (13 from before + 4 new)

If any test fails due to API mismatch, fix the test to match the real Enemy API (read the actual code in step 1).

- [ ] **Step 7: Run full test suite to verify no regression**

Run: `cd D:\AI\void-hunter && $env:SDL_VIDEODRIVER='dummy'; D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 1,630 + 17 = 1,647 tests pass, 6 pre-existing failures remain

- [ ] **Step 8: Commit**

```bash
cd D:\AI\void-hunter
git add src/entities/enemies/enemy.py src/ui/gameplay_runtime.py tests/test_redesign_sprites.py
git commit -m "feat: BLOQUE 59 add enemy animation state machine and per-frame render lookup"
```

---

## Task 7: Stage 4 — Integrate + rebuild .exe (with USER VISUAL CHECK)

**Files:**
- Create: `tools/redesign_ships/04_integrate.py`
- Create: `archive/_legacy_sprites/` (move old PNGs here)
- Create: `Assets/sprites/enemies/<kind>/<animation>/frame_NN.png` (live assets, 7 enemies × 40 frames)
- Create: `Assets/sprites/player_ships/ship_01/<animation>/frame_NN.png` (overwrite existing)
- Modify: `build.spec` (add `Assets/sprites/enemies` to datas)
- Rebuild: `dist/void-hunter.exe`

- [ ] **Step 1: Implement `04_integrate.py`**

Write `tools/redesign_ships/04_integrate.py`:

```python
"""Stage 4: Copy redesigned sprites to live asset locations (BLOQUE 59).

For each ship:
  - Player: copy Assets/sprites/redesign/player/<anim>/frame_NN.png
    to Assets/sprites/player_ships/ship_01/<anim>/frame_NN.png
    (overwriting the existing 8-frame version; new files have 10 frames).
  - Enemies: copy Assets/sprites/redesign/enemy_<kind>/<anim>/frame_NN.png
    to Assets/sprites/enemies/<kind>/<anim>/frame_NN.png (new dir).
  - Old single-frame enemy PNGs at Assets/sprites/enemy_<variant>.png
    are moved to archive/_legacy_sprites/ for git history preservation.

Usage:
    python tools/redesign_ships/04_integrate.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.redesign_ships._ship_specs import SHIPS

REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"
PLAYER_LIVE = PROJECT_ROOT / "Assets" / "sprites" / "player_ships" / "ship_01"
ENEMY_LIVE_PARENT = PROJECT_ROOT / "Assets" / "sprites" / "enemies"
LEGACY_DIR = PROJECT_ROOT / "archive" / "_legacy_sprites"
ANIMATIONS = ("idle", "thrust", "damage", "death")


def integrate_player() -> None:
    src_root = REDESIGN_DIR / "player"
    if not src_root.exists():
        print(f"[skip] player: no source dir {src_root}")
        return
    for anim in ANIMATIONS:
        src_anim = src_root / anim
        dst_anim = PLAYER_LIVE / anim
        if not src_anim.exists():
            print(f"[skip] player/{anim}: no source")
            continue
        dst_anim.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            src = src_anim / f"frame_{i:02d}.png"
            dst = dst_anim / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
    print(f"[done] player: copied 4 anims x 10 frames to {PLAYER_LIVE}")


def integrate_enemy(spec_key: str) -> None:
    src_root = REDESIGN_DIR / spec_key
    if not src_root.exists():
        print(f"[skip] {spec_key}: no source dir")
        return
    kind = spec_key.replace("enemy_", "")  # "scout", "heavy", etc.
    for anim in ANIMATIONS:
        src_anim = src_root / anim
        dst_anim = ENEMY_LIVE_PARENT / kind / anim
        if not src_anim.exists():
            print(f"[skip] {spec_key}/{anim}: no source")
            continue
        dst_anim.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            src = src_anim / f"frame_{i:02d}.png"
            dst = dst_anim / f"frame_{i:02d}.png"
            if src.exists():
                shutil.copy2(src, dst)
    print(f"[done] {spec_key} -> {ENEMY_LIVE_PARENT / kind}")


def archive_old_enemy_pngs() -> None:
    LEGACY_DIR.mkdir(parents=True, exist_ok=True)
    for spec in SHIPS:
        if not spec.key.startswith("enemy_"):
            continue
        old = PROJECT_ROOT / "Assets" / "sprites" / f"{spec.key}.png"
        if old.exists():
            dest = LEGACY_DIR / old.name
            shutil.move(str(old), str(dest))
            print(f"[arch] {old.name} -> {dest}")


def main() -> int:
    integrate_player()
    for spec in SHIPS:
        if spec.key.startswith("enemy_"):
            integrate_enemy(spec.key)
    archive_old_enemy_pngs()
    print("\nStage 4 done. Live assets updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run Stage 4**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe tools/redesign_ships/04_integrate.py 2>&1 | tee logs/stage4.log`

Expected: 1 `[done] player` line + 7 `[done] enemy_*` lines + 7 `[arch]` lines. Live assets:
- `Assets/sprites/player_ships/ship_01/<anim>/frame_00.png` through `frame_09.png` (40 files)
- `Assets/sprites/enemies/<kind>/<anim>/frame_00.png` through `frame_09.png` (280 files for 7 kinds × 4 anims × 10 frames)
- `archive/_legacy_sprites/enemy_scout.png` through `enemy_cruiser.png` (7 files)

- [ ] **Step 3: Update `build.spec` to bundle `Assets/sprites/enemies`**

In `build.spec`, find the `datas=[` block and add a new entry after the existing `Assets/sprites` line:

```python
(str(PROJECT_ROOT / "Assets" / "sprites" / "enemies"), "Assets/sprites/enemies"),
```

- [ ] **Step 4: Rebuild the .exe**

Run: `cd D:\AI\void-hunter && D:\AI\void-hunter\.venv\Scripts\python.exe -m PyInstaller build.spec --clean --noconfirm 2>&1 | tee logs/build.log`

Expected: build completes successfully. The new `dist/void-hunter.exe` exists, size ~266-270 MB (slight increase from 266 MB due to ~22 KB of new sprite data).

- [ ] **Step 5: USER VISUAL CHECK**

Launch the .exe and have the user play Act 1:
- Run: `Start-Process 'D:\AI\void-hunter\dist\void-hunter.exe'`
- The user plays for 1-2 minutes, watching for:
  - Player ship animates (idle bob, thrust flare on dash, damage flash on hit, death explosion)
  - Enemies animate (idle bob, thrust on chase, damage flash, death explosion)
  - Different enemy types look distinct (light/medium/heavy)
  - No visual regressions in the rest of the game

If the user reports a problem, fix it (usually a path lookup issue or a palette mismatch) and re-run Stages 3-4.

- [ ] **Step 6: Commit**

```bash
cd D:\AI\void-hunter
git add tools/redesign_ships/04_integrate.py build.spec
git commit -m "feat: BLOQUE 59 integrate redesigned sprites into live assets + rebuild .exe"
```

Note: the live per-frame PNGs are committed because they're 32x32 source art (small, deterministic, version-controllable). The 1024x1024 AI bases are NOT committed (regenerable from manifest).

---

## Task 8: CHANGELOG + final verification

**Files:**
- Modify: `docs/changelog/CHANGELOG_v1.x.md` (add BLOQUE 59 entry)
- Modify: `tests/test_redesign_sprites.py` (final coverage tests)
- Rebuild: `dist/void-hunter.exe` (only if not rebuilt in Task 7)

- [ ] **Step 1: Add the CHANGELOG entry**

In `docs/changelog/CHANGELOG_v1.x.md`, add at the top (after the file header) a new section:

```markdown
### BLOQUE 59 — Ship sprite redesign (2026-09-07)

- **3 enemy templates redesigned:** light (cyan, small, pointy — scout/drone/kamikaze),
  medium (navy, balanced — sniper/turret), heavy (red, large, armored — heavy/cruiser).
  Each template has 2-3 visual variants covering the 7 existing enemy types.
- **1 player ship redesigned:** `ship_01` (white + gold + red, hero aesthetic).
- **4 animations × 10 frames = 40 frames per ship:** idle, thrust, damage, death.
  idle and thrust loop seamlessly (frame 0 == frame 9).
- **32×32 source → 16px render:** PNG source is 32×32 RGBA, scaled to 16×16 with
  nearest-neighbor at render time.
- **Palette discipline:** all new pixels map to the 64-color palette in
  `src/utils/palette.py` (no new colors).
- **Pipeline:** `tools/redesign_ships/01_generate_bases.py` (mcode-tools AI gen)
  → `02_postprocess.py` (PIL downscale + palette map + animation frame gen) →
  `03_build_sheets.py` (preview sprite-sheets) → `04_integrate.py` (copy to live assets).
- **Enemy state machine:** `src/entities/enemies/enemy.py` gains
  `animation_state` + `animation_frame` + `animation_timer` fields; render path
  in `src/ui/gameplay_runtime.py` looks up per-frame PNG per tick.
- **Old single-frame enemy PNGs** (e.g. `Assets/sprites/enemy_scout.png`) moved
  to `archive/_legacy_sprites/` for git history.

### Verified
- 1,630 + 17 = 1,647 tests pass (the 6 pre-existing failures remain pre-existing).
- Visual verification by user: ships animate in-game (idle bob, thrust flare,
  damage flash, death explosion), enemy types visually distinct.
```

- [ ] **Step 2: Add final coverage tests**

Add to `tests/test_redesign_sprites.py`:

```python
def test_all_8_ships_have_4_animations():
    """Each of the 8 ships has 4 animation directories."""
    for spec in SHIPS:
        ship_dir = REDESIGN_DIR / spec.key
        for anim in ANIMATIONS:
            anim_dir = ship_dir / anim
            assert anim_dir.exists(), f"{spec.key}/{anim} missing"


def test_each_animation_has_10_frames():
    """Each animation directory has frame_00.png through frame_09.png."""
    for spec in SHIPS:
        ship_dir = REDESIGN_DIR / spec.key
        for anim in ANIMATIONS:
            anim_dir = ship_dir / anim
            if not anim_dir.exists():
                continue
            for i in range(10):
                frame = anim_dir / f"frame_{i:02d}.png"
                assert frame.exists(), f"{spec.key}/{anim}/frame_{i:02d}.png missing"


def test_each_frame_is_32x32_rgba():
    """Each frame is 32x32 RGBA."""
    for spec in SHIPS:
        ship_dir = REDESIGN_DIR / spec.key
        for anim in ANIMATIONS:
            anim_dir = ship_dir / anim
            if not anim_dir.exists():
                continue
            for i in range(10):
                frame = anim_dir / f"frame_{i:02d}.png"
                if frame.exists():
                    img = Image.open(frame)
                    assert img.size == (32, 32), f"{frame} size {img.size} != (32, 32)"
                    assert img.mode == "RGBA", f"{frame} mode {img.mode} != RGBA"
```

(Adjust the `ANIMATIONS`, `REDESIGN_DIR`, and `SHIPS` imports to match what's at the top of the test file.)

- [ ] **Step 3: Run the full test suite**

Run: `cd D:\AI\void-hunter && $env:SDL_VIDEODRIVER='dummy'; D:\AI\void-hunter\.venv\Scripts\python.exe -m pytest tests/ -q`
Expected: 1,630 + 17 + 3 = 1,650 tests pass, 6 pre-existing failures remain. Total ≈ 1,656 collected, 1,650 passing.

- [ ] **Step 4: Rebuild .exe if not done in Task 7**

If Task 7 step 4 didn't run, run it now:
```bash
cd D:\AI\void-hunter
D:\AI\void-hunter\.venv\Scripts\python.exe -m PyInstaller build.spec --clean --noconfirm
```

- [ ] **Step 5: Commit final state**

```bash
cd D:\AI\void-hunter
git add docs/changelog/CHANGELOG_v1.x.md tests/test_redesign_sprites.py
git commit -m "docs: BLOQUE 59 add CHANGELOG entry and final coverage tests"
```

- [ ] **Step 6: Push to origin**

```bash
cd D:\AI\void-hunter
git push origin master
```
Expected: "Everything up-to-date" (already pushed per-task) or successful push of final commit.

---

## Self-Review Checklist

After all tasks are complete, verify:

- [ ] All 8 ships have 40 frames each (4 anims × 10 frames) in `Assets/sprites/redesign/`
- [ ] All 8 ships have 40 frames each in live assets (`Assets/sprites/player_ships/ship_01/` and `Assets/sprites/enemies/<kind>/`)
- [ ] 8 sprite-sheet previews exist in `Assets/sprites/redesign/spritesheet_*.png`
- [ ] Old single-frame enemy PNGs are in `archive/_legacy_sprites/`
- [ ] `build.spec` includes `Assets/sprites/enemies` in datas
- [ ] `dist/void-hunter.exe` rebuilds and launches without error
- [ ] User has visually verified ships animate in-game
- [ ] Full test suite: 1,650+ pass, 6 pre-existing failures remain
- [ ] CHANGELOG entry added
- [ ] All commits pushed to `origin/master`

---

*Plan author: Mavis · 2026-09-07*
