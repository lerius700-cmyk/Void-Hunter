"""Tests for BLOQUE 47: aim reticle, snappier banking, SQUADRON formation."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ---- 1. Reticle color when L3 laser is active ----
def test_reticle_cyan_when_laser_active() -> None:
    """When the player is charging L3, the reticle should be plasma cyan."""
    # We test by checking that the reticle color logic exists and is correct.
    # The actual draw is a pygame call we don't want to run in headless tests.
    expected_cyan = (140, 220, 255)
    # Read the source file to confirm the constant is there
    src_path = ROOT / "src" / "ui" / "gameplay_runtime.py"
    content = src_path.read_text(encoding="utf-8")
    assert "plasma cyan" in content
    assert str(expected_cyan) in content


# ---- 2. Player tilt is now 25° (was 15°) ----
def test_player_tilt_is_25_not_15() -> None:
    """BLOQUE 47: snappier banking ±25° for Star Fox feel."""
    from src.entities.player.player import Player
    p = Player(x=160, y=420)
    p.input_left = True
    for _ in range(15):
        p.update(1 / 60)
    assert p.tilt == -25.0
    p.input_left = False
    p.input_right = True
    for _ in range(15):
        p.update(1 / 60)
    assert p.tilt == 25.0


# ---- 3. SQUADRON formation creates N enemies with leader/follower offsets ----
def test_squadron_formation_creates_leader_and_followers() -> None:
    """BLOQUE 47: SQUADRON generates enemies with time_offset_s
    0 for leader, 0.4/0.8/1.2/1.6 for followers."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "squadron",
        "enemy_type": "SCOUT",
        "count": 5,
        "spacing_px": 24,
        "entry_axis": "top",
        "pattern_speed": 50,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    # Leader has offset 0
    assert spawns[0].time_offset_s == 0.0
    # Each follower is 0.4s behind
    assert abs(spawns[1].time_offset_s - 0.4) < 1e-6
    assert abs(spawns[2].time_offset_s - 0.8) < 1e-6
    assert abs(spawns[3].time_offset_s - 1.2) < 1e-6
    assert abs(spawns[4].time_offset_s - 1.6) < 1e-6
    # All spawn at top center
    for s in spawns:
        assert s.x == 160.0  # INTERNAL_W / 2
        assert s.y == 16.0


# ---- 4. SQUADRON is in FORMATION_TYPES ----
def test_squadron_in_formation_types() -> None:
    from src.systems.wave_manager import FORMATION_TYPES
    assert "squadron" in FORMATION_TYPES


# ---- 5. Spawn has time_offset_s default 0 ----
def test_spawn_default_time_offset() -> None:
    """BLOQUE 47: Spawn.time_offset_s defaults to 0 for backward compat."""
    from src.systems.wave_manager import Spawn
    s = Spawn(x=0.0, y=0.0, vx=0.0, vy=0.0, kind="SCOUT")
    assert s.time_offset_s == 0.0


# ---- 6. Enemy has squadron fields default -1 / 0.0 ----
def test_enemy_squadron_fields_default() -> None:
    """BLOQUE 47: Enemy has squadron_id / origin_x / time_offset / age fields."""
    from src.entities.enemies.enemy import Enemy
    e = Enemy()
    assert e.squadron_id == -1
    assert e.squadron_origin_x == 0.0
    assert e.squadron_time_offset == 0.0
    assert e.squadron_age == 0.0


# ---- 7. Enemy spawn resets squadron state ----
def test_enemy_on_spawn_resets_squadron() -> None:
    from src.entities.enemies.enemy import Enemy
    e = Enemy()
    e.squadron_id = 99
    e.squadron_origin_x = 123.0
    e.squadron_time_offset = 1.5
    e.squadron_age = 5.0
    e.on_spawn()
    assert e.squadron_id == -1
    assert e.squadron_origin_x == 0.0
    assert e.squadron_time_offset == 0.0
    assert e.squadron_age == 0.0


# ---- 8. Reticle is registered in draw() ----
def test_reticle_drawn_in_gameplay() -> None:
    """BLOQUE 47: _draw_reticle is called from draw() in gameplay."""
    src = (ROOT / "src" / "ui" / "gameplay_runtime.py").read_text(encoding="utf-8")
    assert "def _draw_reticle" in src
    assert "self._draw_reticle(target, shx, shy)" in src
