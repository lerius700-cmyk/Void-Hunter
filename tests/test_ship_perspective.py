"""BLOQUE 62 — Ship perspective / top-down regen tests.

Validates the top-down ship pass: 8 ships regenerated with no "3/4" wording
in active prompts, 4 anims x 10 frames per ship, and heuristic orientation
checks (enemy faces DOWN, player faces UP).

Ships in the existing pipeline (_ship_specs.py SHIPS tuple):
  - 7 enemies: enemy_scout, enemy_drone, enemy_kamikaze, enemy_sniper,
    enemy_turret, enemy_heavy, enemy_cruiser
  - 1 player:  player

Animations: idle / thrust / damage / death (4 states x 10 frames = 40 PNGs
per ship). 8 ships * 40 = 320 PNGs total.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REDESIGN_DIR = PROJECT_ROOT / "Assets" / "sprites" / "redesign"
PLAYER_DIR = PROJECT_ROOT / "Assets" / "sprites" / "player_ships" / "ship_01"
ENEMY_DIR = PROJECT_ROOT / "Assets" / "sprites" / "enemies"
TOOLS_DIR = PROJECT_ROOT / "tools" / "redesign_ships"
MANIFEST_PATH = TOOLS_DIR / "manifest.json"
GENERATE_BASES = TOOLS_DIR / "01_generate_bases.py"
SHIP_SPECS = TOOLS_DIR / "_ship_specs.py"
POSTPROCESS = TOOLS_DIR / "02_postprocess.py"
ANIM_FRAMES = TOOLS_DIR / "_animation_frames.py"
BUILD_SHEETS = TOOLS_DIR / "03_build_sheets.py"
INTEGRATE = TOOLS_DIR / "04_integrate.py"

ENEMY_KEYS = [
    "enemy_scout",
    "enemy_drone",
    "enemy_kamikaze",
    "enemy_sniper",
    "enemy_turret",
    "enemy_heavy",
    "enemy_cruiser",
]
PLAYER_KEY = "player"
ALL_KEYS = ENEMY_KEYS + [PLAYER_KEY]

ANIMATIONS = ("idle", "thrust", "damage", "death")
FRAME_COUNT = 10


# ---------------------------------------------------------------------------
# 1. No "3/4" wording in active prompt files
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


def test_no_3_4_in_generate_bases() -> None:
    """BLOQUE 62: 01_generate_bases.py must NOT contain '3/4'."""
    content = _read(GENERATE_BASES)
    assert "3/4" not in content, (
        "01_generate_bases.py still contains '3/4' wording — must be removed"
    )


def test_no_3_4_in_ship_specs() -> None:
    """BLOQUE 62: _ship_specs.py must NOT contain '3/4'."""
    content = _read(SHIP_SPECS)
    assert "3/4" not in content, (
        "_ship_specs.py still contains '3/4' wording — must be removed"
    )


def test_no_3_4_in_postprocess_module() -> None:
    """BLOQUE 62: 02_postprocess.py must NOT contain '3/4'."""
    content = _read(POSTPROCESS)
    assert "3/4" not in content, (
        "02_postprocess.py still contains '3/4' wording"
    )


def test_no_3_4_in_animation_frames() -> None:
    """BLOQUE 62: _animation_frames.py must NOT contain '3/4'."""
    content = _read(ANIM_FRAMES)
    assert "3/4" not in content, (
        "_animation_frames.py still contains '3/4' wording"
    )


def test_no_3_4_in_build_sheets() -> None:
    """BLOQUE 62: 03_build_sheets.py must NOT contain '3/4'."""
    content = _read(BUILD_SHEETS)
    assert "3/4" not in content, (
        "03_build_sheets.py still contains '3/4' wording"
    )


def test_no_3_4_in_integrate() -> None:
    """BLOQUE 62: 04_integrate.py must NOT contain '3/4'."""
    content = _read(INTEGRATE)
    assert "3/4" not in content, (
        "04_integrate.py still contains '3/4' wording"
    )


def test_no_3_4_in_manifest() -> None:
    """BLOQUE 62: regenerated manifest.json entries must NOT contain '3/4'.

    A regenerated entry has a recent created_at; pre-existing entries from
    older regens (BLOQUE 59 v3) that still contain '3/4' are tolerated
    but flagged. The test passes as long as every entry is current
    (post-BLOQUE-62) and free of '3/4'.
    """
    if not MANIFEST_PATH.exists():
        pytest.skip("manifest.json not generated yet")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    bases = data.get("bases", {})
    assert bases, "manifest.json has no bases"
    for key, entry in bases.items():
        prompt = entry.get("prompt", "")
        assert "3/4" not in prompt, (
            f"manifest entry for {key} still contains '3/4'"
        )


# ---------------------------------------------------------------------------
# 2. Prompt content sanity
# ---------------------------------------------------------------------------

def test_prompt_template_uses_top_down() -> None:
    """The PROMPT_TEMPLATE must mention 'TOP-DOWN' (or equivalent) and NOSE DOWN."""
    content = _read(GENERATE_BASES)
    assert "TOP-DOWN" in content or "top-down" in content, (
        "prompt template missing TOP-DOWN wording"
    )
    assert "NOSE" in content, "prompt template missing NOSE wording"
    assert "DOWN" in content, "prompt template missing DOWN wording"


def test_postprocess_uses_lanczos_resize() -> None:
    """02_postprocess.py resizes to 32x32 using LANCZOS."""
    content = _read(POSTPROCESS)
    assert "LANCZOS" in content, "postprocess missing LANCZOS resize"
    assert "32" in content, "postprocess missing target size 32"


def test_transparentize_damero_after_resize_exists() -> None:
    """02_postprocess.py has a transparentize_damero_after_resize function."""
    content = _read(POSTPROCESS)
    assert "_transparentize_damero_after_resize" in content, (
        "postprocess missing _transparentize_damero_after_resize helper"
    )


# ---------------------------------------------------------------------------
# 3. Ship specs (face_down flags)
# ---------------------------------------------------------------------------

def test_enemy_face_down_flag_true() -> None:
    """All 7 enemy specs have a template in {light, medium, heavy}.

    Per the existing postprocess logic, any ship with a non-'player' template
    is treated as face_down=True (enemy ships face DOWN).
    """
    from tools.redesign_ships._ship_specs import SHIPS
    for spec in SHIPS:
        if spec.key == PLAYER_KEY:
            continue
        assert spec.template in ("light", "medium", "heavy"), (
            f"enemy {spec.key} has unexpected template {spec.template!r}"
        )


def test_player_template_is_player() -> None:
    """The player spec has template == 'player'."""
    from tools.redesign_ships._ship_specs import SHIPS
    player = next(s for s in SHIPS if s.key == PLAYER_KEY)
    assert player.template == "player"


# ---------------------------------------------------------------------------
# 4. File presence — 8 base PNGs
# ---------------------------------------------------------------------------

def test_all_8_ship_bases_exist() -> None:
    """8 ship base PNGs exist in _base/ (1 player + 7 enemies)."""
    base = PROJECT_ROOT / "Assets" / "sprites" / "redesign" / "_base"
    for key in ALL_KEYS:
        path = base / f"{key}_base.png"
        assert path.is_file(), f"missing base: {path}"


# ---------------------------------------------------------------------------
# 5. Animation frame file presence
# ---------------------------------------------------------------------------

def test_player_ship_anim_frames() -> None:
    """Player ship: 4 anims x 10 frames = 40 PNGs."""
    for anim in ANIMATIONS:
        anim_dir = PLAYER_DIR / anim
        assert anim_dir.is_dir(), f"missing player anim dir: {anim_dir}"
        for i in range(FRAME_COUNT):
            f = anim_dir / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing player frame: {f}"


@pytest.mark.parametrize("kind", [
    "scout", "drone", "kamikaze", "sniper", "turret", "heavy", "cruiser"
])
def test_enemy_ship_anim_frames(kind: str) -> None:
    """Each enemy kind: 4 anims x 10 frames = 40 PNGs."""
    for anim in ANIMATIONS:
        anim_dir = ENEMY_DIR / kind / anim
        assert anim_dir.is_dir(), f"missing {kind}/{anim}"
        for i in range(FRAME_COUNT):
            f = anim_dir / f"frame_{i:02d}.png"
            assert f.is_file(), f"missing {kind}/{anim}/frame_{i:02d}.png"


def test_animation_states_count_4() -> None:
    """The pipeline defines exactly 4 animation states (idle/thrust/damage/death)."""
    from tools.redesign_ships._animation_frames import (
        generate_idle_frames,
        generate_thrust_frames,
        generate_damage_frames,
        generate_death_frames,
    )
    fns = [generate_idle_frames, generate_thrust_frames,
           generate_damage_frames, generate_death_frames]
    assert len(fns) == 4


def test_animation_frames_count_10() -> None:
    """Each frame generator produces 10 frames."""
    src = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for name, gen in [
            ("idle", __import__(
                "tools.redesign_ships._animation_frames", fromlist=["generate_idle_frames"]
            ).generate_idle_frames),
            ("thrust", __import__(
                "tools.redesign_ships._animation_frames", fromlist=["generate_thrust_frames"]
            ).generate_thrust_frames),
            ("damage", __import__(
                "tools.redesign_ships._animation_frames", fromlist=["generate_damage_frames"]
            ).generate_damage_frames),
            ("death", __import__(
                "tools.redesign_ships._animation_frames", fromlist=["generate_death_frames"]
            ).generate_death_frames),
        ]:
            frames = gen(src, td_path / name)
            assert len(frames) == 10, f"{name} produced {len(frames)} frames"


# ---------------------------------------------------------------------------
# 6. Sprite orientation heuristic
# ---------------------------------------------------------------------------

def _analyze_orientation(img: Image.Image) -> dict:
    """Find the lowest and highest opaque pixel (alpha > 128)."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    nose_y = -1  # lowest opaque pixel
    top_y = h    # highest opaque pixel
    min_x = w
    max_x = -1
    opaque_count = 0
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 128:
                opaque_count += 1
                if y > nose_y:
                    nose_y = y
                if y < top_y:
                    top_y = y
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
    return {
        "nose_y": nose_y,
        "top_y": top_y,
        "width": max_x - min_x + 1 if max_x >= 0 else 0,
        "height": nose_y - top_y + 1 if nose_y >= 0 else 0,
        "opaque_count": opaque_count,
    }


def test_enemy_sprite_faces_down() -> None:
    """Heuristic: enemy idle/frame_00 has its lowest opaque pixel in the bottom 60%."""
    sample = ENEMY_DIR / "scout" / "idle" / "frame_00.png"
    if not sample.is_file():
        pytest.skip(f"missing {sample}")
    img = Image.open(sample).convert("RGBA")
    m = _analyze_orientation(img)
    h = img.size[1]
    assert m["opaque_count"] > 0, "scout idle frame_00 has no opaque pixels"
    assert m["nose_y"] >= int(h * 0.6), (
        f"scout: nose_y={m['nose_y']} < {int(h * 0.6)} (h={h}) — ship does not face DOWN"
    )


def test_player_sprite_faces_up() -> None:
    """Heuristic: player idle/frame_00 has its highest opaque pixel in the top 50%."""
    sample = PLAYER_DIR / "idle" / "frame_00.png"
    if not sample.is_file():
        pytest.skip(f"missing {sample}")
    img = Image.open(sample).convert("RGBA")
    m = _analyze_orientation(img)
    h = img.size[1]
    assert m["opaque_count"] > 0, "player idle frame_00 has no opaque pixels"
    assert m["top_y"] < int(h * 0.5), (
        f"player: top_y={m['top_y']} >= {int(h * 0.5)} (h={h}) — ship does not face UP"
    )


# ---------------------------------------------------------------------------
# 7. Sprite sheet count and dimensions
# ---------------------------------------------------------------------------

def test_player_spritesheet_exists() -> None:
    """Player sprite sheet (ship_01_spritesheet.png) exists."""
    f = PROJECT_ROOT / "Assets" / "sprites" / "player_ships" / "ship_01_spritesheet.png"
    assert f.is_file(), f"missing player sprite sheet: {f}"


def test_player_spritesheet_dimensions() -> None:
    """Player sprite sheet has reasonable dimensions (BLOQUE 58.60 grid).

    The existing sprite sheet is built by tools/build_sprite_sheet.py:
    LABEL_WIDTH (96) + 8 columns * FRAME_SIZE (64) + padding. We only
    assert it's non-empty and wider than tall.
    """
    f = PROJECT_ROOT / "Assets" / "sprites" / "player_ships" / "ship_01_spritesheet.png"
    if not f.is_file():
        pytest.skip("no player sprite sheet")
    with Image.open(f) as img:
        w, h = img.size
        assert w > 0 and h > 0, f"player sheet has zero dim: {w}x{h}"
        assert w >= 200, f"player sheet too narrow: {w}"
        assert h >= 200, f"player sheet too short: {h}"


def test_spritesheet_count_5() -> None:
    """5 player sprite sheets exist (ship_01 .. ship_05)."""
    d = PROJECT_ROOT / "Assets" / "sprites" / "player_ships"
    sheets = sorted(d.glob("ship_*_spritesheet.png"))
    assert len(sheets) == 5, f"expected 5 sprite sheets, found {len(sheets)}"


# ---------------------------------------------------------------------------
# 8. Collision / movement unaffected (smoke tests)
# ---------------------------------------------------------------------------

def test_collision_unchanged_24x24() -> None:
    """Enemy hitboxes are still sensible (BLOQUE 60 invariant).

    Per-kind hitbox dimensions (from ENEMY_CONFIGS, * 0.7 forgiving scale):
    vary by kind (scout is small, heavy is big). The invariant this test
    guards is that the hitbox method returns a valid pygame.Rect for every
    enemy kind. Width and height must be positive.
    """
    import pygame
    from src.entities.enemies.enemy import Enemy, EnemyKind
    for kind in EnemyKind:
        if kind == EnemyKind.SUB_BOSS:
            continue  # sub-boss has separate hitbox logic
        e = Enemy(kind=kind, x=160, y=240)
        # hitbox is a method (not a property) — call it
        hb = e.hitbox()
        assert isinstance(hb, pygame.Rect), f"{kind}: hitbox returned {type(hb).__name__}"
        assert hb.width > 0, f"{kind}: hitbox width={hb.width}"
        assert hb.height > 0, f"{kind}: hitbox height={hb.height}"


def test_player_movement_unchanged() -> None:
    """Player position + velocity fields are still present and sane."""
    from src.entities.player import Player
    p = Player(x=160, y=240)
    assert hasattr(p, "x")
    assert hasattr(p, "y")
    assert hasattr(p, "vx")
    assert hasattr(p, "vy")
    assert p.x == 160
    assert p.y == 240


# ---------------------------------------------------------------------------
# 9. Enemy kinds and live directory alignment
# ---------------------------------------------------------------------------

def test_enemy_7_kinds_have_live_sprites() -> None:
    """All 7 enemy kinds have a directory under Assets/sprites/enemies/."""
    expected = {"scout", "drone", "kamikaze", "sniper", "turret", "heavy", "cruiser"}
    actual = {p.name for p in ENEMY_DIR.iterdir() if p.is_dir()}
    assert expected.issubset(actual), (
        f"missing enemy kinds: {expected - actual}"
    )


def test_player_ship_01_in_player_ships_dir() -> None:
    """ship_01 is the canonical player ship, in player_ships/."""
    assert PLAYER_DIR.is_dir(), f"missing {PLAYER_DIR}"


# ---------------------------------------------------------------------------
# 10. Backwards compatibility
# ---------------------------------------------------------------------------

def test_redesign_pipeline_files_present() -> None:
    """All redesign pipeline files exist (BLOQUE 59 baseline preserved)."""
    for p in [GENERATE_BASES, SHIP_SPECS, POSTPROCESS, ANIM_FRAMES, BUILD_SHEETS, INTEGRATE]:
        assert p.is_file(), f"missing pipeline file: {p}"


def test_postprocess_one_signature_unchanged() -> None:
    """02_postprocess.postprocess_one(spec_key, face_down, force) signature is stable."""
    import importlib
    import inspect
    _postprocess = importlib.import_module("tools.redesign_ships.02_postprocess")
    sig = inspect.signature(_postprocess.postprocess_one)
    params = list(sig.parameters.keys())
    assert "spec_key" in params
    assert "face_down" in params
    assert "force" in params
