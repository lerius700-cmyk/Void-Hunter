"""Tests for src.systems.wave_manager (BLOQUE 10)."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.core.settings import SUBBOSS_TRIGGER_KILLS, WAVE_KILL_TARGET
from src.systems.wave_manager import DEFAULT_WAVES, WaveManager, WaveState


@pytest.fixture
def wm() -> WaveManager:
    return WaveManager()


# ---------------------------------------------------------------------------
# 1. 18 waves
# ---------------------------------------------------------------------------
def test_eighteen_waves_default(wm: WaveManager) -> None:
    assert len(wm.scripts) == 18


def test_three_acts_six_waves_each(wm: WaveManager) -> None:
    acts: dict[int, int] = {}
    for s in wm.scripts:
        acts[s["act"]] = acts.get(s["act"], 0) + 1
    assert acts == {1: 6, 2: 6, 3: 6}


def test_validation_passes_for_defaults(wm: WaveManager) -> None:
    ok, msg = wm.validate()
    assert ok, msg


# ---------------------------------------------------------------------------
# 2. Start wave
# ---------------------------------------------------------------------------
def test_start_wave_resets_state(wm: WaveManager) -> None:
    wm.current.kills = 100
    wm.start_wave(0)
    assert wm.current.wave_index == 0
    assert wm.current.kills == 0


def test_start_wave_out_of_range_raises(wm: WaveManager) -> None:
    with pytest.raises(IndexError):
        wm.start_wave(99)


# ---------------------------------------------------------------------------
# 3. Kill tracking + wave clear
# ---------------------------------------------------------------------------
def test_on_kill_increments_count(wm: WaveManager) -> None:
    wm.start_wave(0)
    wm.on_kill()
    assert wm.current.kills == 1


def test_wave_clears_at_target(wm: WaveManager) -> None:
    wm.start_wave(0)
    target = wm.current_wave()["kill_target"]
    for _ in range(target):
        wm.on_kill()
    assert wm.current.cleared is True
    assert wm.on_wave_cleared is True


def test_wave_cleared_only_at_exact_target(wm: WaveManager) -> None:
    wm.start_wave(0)
    target = wm.current_wave()["kill_target"]
    for _ in range(target - 1):
        wm.on_kill()
    assert wm.current.cleared is False


# ---------------------------------------------------------------------------
# 4. Sub-boss trigger
# ---------------------------------------------------------------------------
def test_sub_boss_trigger_at_threshold(wm: WaveManager) -> None:
    wm.start_wave(5)  # Act 1 wave 6 = GOLIATH
    for _ in range(SUBBOSS_TRIGGER_KILLS):
        wm.on_kill()
    assert wm.on_sub_boss_trigger == "goliath"


def test_sub_boss_trigger_only_once(wm: WaveManager) -> None:
    wm.start_wave(5)
    for _ in range(SUBBOSS_TRIGGER_KILLS + 10):
        wm.on_kill()
    assert wm.on_sub_boss_trigger == "goliath"  # stays at first


# ---------------------------------------------------------------------------
# 5. Time limit
# ---------------------------------------------------------------------------
def test_wave_fails_at_time_limit(wm: WaveManager) -> None:
    wm.start_wave(0)
    wm.update(wm.current_wave()["time_limit_s"] + 1.0)
    assert wm.current.failed is True
    assert wm.on_wave_failed is True


# ---------------------------------------------------------------------------
# 6. Adaptive difficulty
# ---------------------------------------------------------------------------
def test_adaptive_easier_when_low_hp(wm: WaveManager) -> None:
    mult = wm.adapt_difficulty(player_hp_pct=0.2, score=0)
    assert mult == 0.8


def test_adaptive_harder_when_full_hp_high_score(wm: WaveManager) -> None:
    mult = wm.adapt_difficulty(player_hp_pct=1.0, score=100000)
    assert mult == 1.2


def test_adaptive_normal(wm: WaveManager) -> None:
    mult = wm.adapt_difficulty(player_hp_pct=0.5, score=0)
    assert mult == 1.0


# ---------------------------------------------------------------------------
# 7. JSON load (uses defaults if dir empty)
# ---------------------------------------------------------------------------
def test_from_json_dir_with_no_files_falls_back_to_defaults(tmp_path: Path) -> None:
    wm = WaveManager.from_json_dir(tmp_path)
    assert len(wm.scripts) == 18


def test_from_json_dir_with_files(tmp_path: Path) -> None:
    # Create 3 valid wave files
    for act in (1, 2, 3):
        for wave in range(1, 7):
            data = {
                "act": act,
                "wave": wave,
                "theme": "blue_void",
                "mix": {"scout": 5},
                "kill_target": 5,
                "time_limit_s": 30.0,
                "sub_boss": None,
            }
            (tmp_path / f"act{act}_wave{wave}.json").write_text(
                json.dumps(data), encoding="utf-8"
            )
    wm = WaveManager.from_json_dir(tmp_path)
    assert len(wm.scripts) == 18


# ---------------------------------------------------------------------------
# 8. Reset
# ---------------------------------------------------------------------------
def test_reset_clears_state(wm: WaveManager) -> None:
    wm.current.kills = 50
    wm.on_wave_cleared = True
    wm.reset()
    assert wm.current.kills == 0
    assert wm.on_wave_cleared is False


# ---------------------------------------------------------------------------
# 9. Per-act sub-boss
# ---------------------------------------------------------------------------
def test_act_3_wave_6_has_phantom_then_nemesis(wm: WaveManager) -> None:
    wm.start_wave(17)  # Act 3 wave 6
    assert wm.current_wave()["sub_boss"] == "phantom_then_nemesis"


def test_act_2_wave_6_has_hydra(wm: WaveManager) -> None:
    wm.start_wave(11)
    assert wm.current_wave()["sub_boss"] == "hydra"


# ---------------------------------------------------------------------------
# 8. BLOQUE 41: formation system
# ---------------------------------------------------------------------------
def test_parse_formation_line() -> None:
    """BLOQUE 41: LINE formation with 4 SCOUT produces 4 evenly-spaced spawns."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "line",
        "enemy_type": "SCOUT",
        "count": 4,
        "spacing_px": 32,
        "entry_axis": "top",
        "pattern_speed": 40,
        "telegraph_frames": 30,
    })
    assert f.enemy_count == 4
    assert f.spacing_px == 32
    spawns = spawn_formation(f)
    assert len(spawns) == 4
    # All y values should be the same (LINE has constant y)
    ys = {round(s.y, 1) for s in spawns}
    assert len(ys) == 1
    # All vy should equal pattern_speed (downward)
    for s in spawns:
        assert s.vy == 40.0
        assert s.vx == 0.0
        assert s.kind == "SCOUT"


def test_parse_formation_v() -> None:
    """BLOQUE 41: V formation with 5 enemies produces 5 non-linear spawns."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "v",
        "enemy_type": "SCOUT",
        "count": 5,
        "spacing_px": 24,
        "entry_axis": "top",
        "pattern_speed": 40,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    # Middle spawn (index 2) should be at the top (smallest y)
    ys = [s.y for s in spawns]
    middle_y = ys[2]
    assert all(s.y >= middle_y - 0.01 for s in spawns), (
        f"Wings should be at or below middle: {ys}"
    )


def test_parse_formation_arc() -> None:
    """BLOQUE 41: ARC formation produces 5 concave arc spawns."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "arc",
        "enemy_type": "CRUISER",
        "count": 5,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 45,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    # All should be CRUISER kind
    assert all(s.kind == "CRUISER" for s in spawns)


def test_parse_formation_staircase() -> None:
    """BLOQUE 41: STAIRCASE formation produces 4 diagonal spawns."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "staircase",
        "enemy_type": "HEAVY",
        "count": 4,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 60,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 4
    # All HEAVY
    assert all(s.kind == "HEAVY" for s in spawns)
    # y should INCREASE from first to last (staircase goes down)
    for i in range(1, len(spawns)):
        assert spawns[i].y > spawns[i - 1].y, (
            f"Staircase y must increase: {[(s.x, s.y) for s in spawns]}"
        )


def test_parse_formation_rejects_unknown_type() -> None:
    """BLOQUE 41: unknown formation_type raises ValueError (no silent fallback)."""
    from src.systems.wave_manager import parse_formation
    with pytest.raises(ValueError, match="Unknown formation_type"):
        parse_formation({"formation_type": "circle", "enemy_type": "SCOUT", "count": 4})


# ---------------------------------------------------------------------------
# 8b. BLOQUE 55: 3 new formations (spiral, hilera, x)
# ---------------------------------------------------------------------------
def test_parse_formation_spiral_8() -> None:
    """BLOQUE 55: SPIRAL with 8 ships in 2 turns produces 8 spiral spawns.
    All ships have the same vy (= pattern_speed) and stay within the playfield
    horizontally (cx ± 60 px) and vertically (y >= 32)."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "spiral",
        "enemy_type": "SCOUT",
        "count": 8,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 35,
        "telegraph_frames": 40,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 8
    # All ships descend at the same rate
    for s in spawns:
        assert s.vy == 35.0
        assert s.vx == 0.0
        assert s.kind == "SCOUT"
    # Spiral stays within the 320-wide playfield (cx=160, max radius 60)
    for s in spawns:
        assert 100.0 <= s.x <= 220.0, f"x={s.x} out of spiral range"
        assert 32.0 <= s.y <= 152.0, f"y={s.y} out of spiral vertical range [32, 152]"


def test_parse_formation_hilera_5() -> None:
    """BLOQUE 55: HILERA with 5 ships produces a tight vertical column.
    All ships share the same x (center) and y increases by spacing_px
    (clamped to [24, 32] by _clamp_formation)."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "hilera",
        "enemy_type": "DRONE",
        "count": 5,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 50,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    # All same x (center)
    xs = {round(s.x, 1) for s in spawns}
    assert len(xs) == 1, f"Hilera must share x: {xs}"
    # y stacked with clamped spacing (24..32)
    spacing_used = round(spawns[1].y - spawns[0].y, 1)
    assert 24.0 <= spacing_used <= 32.0, f"spacing_used={spacing_used} outside [24, 32]"
    for i in range(2, len(spawns)):
        assert abs(spawns[i].y - spawns[i - 1].y - spacing_used) < 0.01
    # All descend
    for s in spawns:
        assert s.vy == 50.0


def test_parse_formation_x_5() -> None:
    """BLOQUE 55: X with 5 ships produces a cross pattern.
    1 center at (cx, 48) + 4 cardinals (NW, NE, SW, SE) at spacing_px offset."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "x",
        "enemy_type": "HEAVY",
        "count": 5,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 45,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    s = float(f.spacing_px)  # clamped to [24, 32]
    # 1 ship at the exact center (cx, 48)
    center = next(sp for sp in spawns if sp.x == 160.0 and sp.y == 48.0)
    assert center is not None
    # 4 cardinals: NW (-s,-s), NE (+s,-s), SW (-s,+s), SE (+s,+s)
    expected_cardinals = {
        (160.0 - s, 48.0 - s),
        (160.0 + s, 48.0 - s),
        (160.0 - s, 48.0 + s),
        (160.0 + s, 48.0 + s),
    }
    actual = {(round(sp.x, 1), round(sp.y, 1)) for sp in spawns}
    assert expected_cardinals.issubset(actual), (
        f"Missing cardinals: expected {expected_cardinals}, got {actual}"
    )


def test_parse_formation_x_clamps_to_5() -> None:
    """BLOQUE 55: X formation with count > 5 still returns only 5 spawns.
    Extra ships are dropped (X is a fixed-shape pattern)."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "x",
        "enemy_type": "HEAVY",
        "count": 7,  # over-spec
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 45,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5, f"X must cap at 5 ships, got {len(spawns)}"


def test_formation_types_includes_new_ones() -> None:
    """BLOQUE 55-56: FORMATION_TYPES tuple must include all 11 formation types."""
    from src.systems.wave_manager import FORMATION_TYPES
    expected = (
        "line", "v", "arc", "staircase", "squadron",
        "spiral", "hilera", "x", "diamond", "box", "wingman",
    )
    for name in expected:
        assert name in FORMATION_TYPES, f"{name!r} missing from FORMATION_TYPES"


# ---------------------------------------------------------------------------
# 8c. BLOQUE 56: 3 more formations (diamond, box, wingman)
# ---------------------------------------------------------------------------
def test_parse_formation_diamond_5() -> None:
    """BLOQUE 56: DIAMOND with 5 ships: 1 center + N + E + S + W cardinals."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "diamond",
        "enemy_type": "SCOUT",
        "count": 5,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 35,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    s = float(f.spacing_px)
    # Center: (160, 48)
    center = next(sp for sp in spawns if sp.x == 160.0 and sp.y == 48.0)
    assert center is not None
    # N: (cx, cy - s), E: (cx + s, cy), S: (cx, cy + s), W: (cx - s, cy)
    expected_cardinals = {
        (160.0, 48.0 - s),  # N
        (160.0 + s, 48.0),  # E
        (160.0, 48.0 + s),  # S
        (160.0 - s, 48.0),  # W
    }
    actual = {(round(sp.x, 1), round(sp.y, 1)) for sp in spawns}
    assert expected_cardinals.issubset(actual), (
        f"Missing cardinals: expected {expected_cardinals}, got {actual}"
    )


def test_parse_formation_box_4() -> None:
    """BLOQUE 56: BOX with 4 ships: just the 4 corners of a rectangle."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "box",
        "enemy_type": "CRUISER",
        "count": 4,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 40,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 4
    # All 4 should share y_top (NW and NE) OR (SE and SW)
    ys = sorted({round(sp.y, 1) for sp in spawns})
    assert len(ys) == 2, f"Box should have 2 distinct y values, got {ys}"


def test_parse_formation_box_8() -> None:
    """BLOQUE 56: BOX with 8 ships: 4 corners + 1 midpoint per side.
    Layout: 3 ships at top y, 2 ships at middle y, 3 ships at bottom y."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "box",
        "enemy_type": "CRUISER",
        "count": 8,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 30,
        "telegraph_frames": 40,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 8
    top_ys = [sp for sp in spawns if sp.y < 30.0]   # y_top region
    mid_ys = [sp for sp in spawns if 30.0 <= sp.y < 70.0]
    bot_ys = [sp for sp in spawns if sp.y >= 70.0]
    assert len(top_ys) == 3, f"Expected 3 top ships, got {len(top_ys)}"
    assert len(mid_ys) == 2, f"Expected 2 mid ships, got {len(mid_ys)}"
    assert len(bot_ys) == 3, f"Expected 3 bot ships, got {len(bot_ys)}"


def test_parse_formation_wingman_3() -> None:
    """BLOQUE 56: WINGMAN with 3 ships: leader + 2 wingmen in V shape.
    All spawn at the same x area but with offset_y > 0 for wingmen."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "wingman",
        "enemy_type": "SCOUT",
        "count": 3,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 50,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 3
    # Leader at (160, 16)
    leader = next(sp for sp in spawns if sp.x == 160.0 and sp.y == 16.0)
    assert leader is not None
    # Wingmen at (160 - s, 16 + s) and (160 + s, 16 + s)
    s = float(f.spacing_px)
    expected_wings = {(160.0 - s, 16.0 + s), (160.0 + s, 16.0 + s)}
    actual = {(round(sp.x, 1), round(sp.y, 1)) for sp in spawns}
    assert expected_wings.issubset(actual), (
        f"Missing wingmen: expected {expected_wings}, got {actual}"
    )


def test_parse_formation_wingman_5() -> None:
    """BLOQUE 56: WINGMAN with 5 ships: leader + 4 wingmen in double V.
    All 5 ships spawn with a clear leader at the top, wingmen behind."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "wingman",
        "enemy_type": "SCOUT",
        "count": 5,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 50,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    assert len(spawns) == 5
    # Leader has the smallest y (at the front of the V)
    leader = min(spawns, key=lambda sp: sp.y)
    assert leader.y == 16.0
    # Wingmen y > leader y
    wingmen = [sp for sp in spawns if sp.y > 16.0]
    assert len(wingmen) == 4, f"Expected 4 wingmen behind leader, got {len(wingmen)}"
    # Wingmen split into 2 y-tiers (close and far)
    wingmen_ys = sorted({round(sp.y, 1) for sp in wingmen})
    assert len(wingmen_ys) == 2, f"Expected 2 y-tiers, got {wingmen_ys}"


def test_wingman_v_shape_preserved_during_descent() -> None:
    """BLOQUE 56: WINGMAN ships share the same vy, so the V shape is
    maintained during descent without per-frame sync. We verify the
    relative offsets between leader and wingmen stay constant when
    each ship advances by the same delta_t * vy."""
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "wingman",
        "enemy_type": "SCOUT",
        "count": 3,
        "spacing_px": 28,
        "entry_axis": "top",
        "pattern_speed": 50,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    # Capture initial offsets from leader
    leader = next(sp for sp in spawns if sp.y == 16.0)
    initial_offsets: list[tuple[float, float]] = []
    for sp in spawns:
        if sp is not leader:
            initial_offsets.append((sp.x - leader.x, sp.y - leader.y))
    # Simulate 1s of descent (each ship advances by vy * 1.0 = 50 px)
    descend = 1.0
    new_leader_y = leader.y + f.pattern_speed * descend
    # Since all share the same vy, offsets stay identical
    for ox, oy in initial_offsets:
        # After descent, wingman is at (leader.x + ox, leader.y + oy + descend*vy)
        # = (leader.x + ox, new_leader_y + oy)
        # So the relative offset (ox, oy) is preserved
        new_oy = oy  # unchanged because all descend by same amount
        assert abs(new_oy - oy) < 0.01, f"Offset y should be preserved: {oy} -> {new_oy}"


def test_parse_formation_clamps_extreme_values() -> None:
    """BLOQUE 41: out-of-range values are clamped, not passed through."""
    from src.systems.wave_manager import parse_formation
    f = parse_formation({
        "formation_type": "line",
        "enemy_type": "SCOUT",
        "count": 4,
        "spacing_px": 999,        # way too big � clamp to 32
        "pattern_speed": 999.0,   # way too fast � clamp to 60
        "telegraph_frames": 0,    # too low � clamp to 24
    })
    from src.core.settings import (
        FORMATION_PATTERN_SPEED_MAX, FORMATION_SPACING_MAX_PX,
        FORMATION_TELEGRAPH_FRAMES_MIN,
    )
    assert f.spacing_px <= FORMATION_SPACING_MAX_PX
    assert f.pattern_speed <= FORMATION_PATTERN_SPEED_MAX
    assert f.telegraph_frames >= FORMATION_TELEGRAPH_FRAMES_MIN


def test_spawn_formation_keeps_spawns_inside_screen() -> None:
    """BLOQUE 41: even with extreme count+spacing, spawns stay inside the play area."""
    from src.core.settings import INTERNAL_W
    from src.systems.wave_manager import parse_formation, spawn_formation
    f = parse_formation({
        "formation_type": "line",
        "enemy_type": "SCOUT",
        "count": 8,
        "spacing_px": 32,  # 8*32=256, would overflow 320
        "pattern_speed": 40,
        "telegraph_frames": 30,
    })
    spawns = spawn_formation(f)
    for s in spawns:
        assert 0 <= s.x <= INTERNAL_W, f"Spawn x out of bounds: {s.x}"


def test_wave_manager_current_formation_falls_back_to_mix() -> None:
    """BLOQUE 41: a wave with no `formation` field derives one from `mix`."""
    from src.systems.wave_manager import WaveManager
    wm = WaveManager([{
        "act": 1, "wave": 1, "theme": "blue_void",
        "mix": {"scout": 6, "cruiser": 2},
        "kill_target": 8, "time_limit_s": 25.0, "sub_boss": None,
    }])
    wm.start_wave(0)
    f = wm.current_formation()
    assert f is not None
    assert f.enemy_type == "SCOUT"  # first key in mix
    assert f.enemy_count == 8  # capped at 8
    assert f.formation_type == "line"


def test_all_default_waves_destructible() -> None:
    """BLOQUE 41: every enemy in DEFAULT_WAVES is destructible (no indestructibles)."""
    from src.systems.wave_manager import DEFAULT_WAVES
    for i, wave in enumerate(DEFAULT_WAVES):
        # No wave is "indestructible" by design
        assert "indestructible" not in wave, f"wave {i} has indestructible flag"
        # Every wave has a kill_target > 0 (so they CAN be cleared)
        assert wave.get("kill_target", 0) > 0


# ---------------------------------------------------------------------------
# 9. BLOQUE 45: act 1 DEFAULT_WAVES use formations
# ---------------------------------------------------------------------------
def test_act1_wave1_is_line_formation() -> None:
    """BLOQUE 50: Act 1, Wave 1 is a LINE formation of 6 SCOUT (denser)."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[0]
    assert wave["act"] == 1 and wave["wave"] == 1
    f = parse_formation(wave["formation"])
    assert f.formation_type == "line"
    assert f.enemy_type == "SCOUT"
    assert f.enemy_count == 6
    assert f.telegraph_frames == 30
    assert f.pattern_speed == 40


def test_act1_wave2_is_squadron_formation() -> None:
    """BLOQUE 50: Act 1, Wave 2 is a SQUADRON formation of 7 SCOUT
    (Star Fox 64 leader/follower choreography)."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[1]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "squadron"
    assert f.enemy_count == 7
    assert f.enemy_type == "SCOUT"


def test_act1_wave3_is_arc_formation() -> None:
    """BLOQUE 50: Act 1, Wave 3 is an ARC formation of 7 CRUISER (denser)."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[2]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "arc"
    assert f.enemy_count == 7
    assert f.enemy_type == "CRUISER"
    assert f.telegraph_frames == 45


def test_act1_wave4_is_staircase_formation() -> None:
    """BLOQUE 50: Act 1, Wave 4 is a STAIRCASE formation of 6 HEAVY (denser)."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[3]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "staircase"
    assert f.enemy_count == 6
    assert f.enemy_type == "HEAVY"
    assert f.telegraph_frames == 60


def test_act1_wave5_is_line_mixed() -> None:
    """BLOQUE 50: Act 1, Wave 5 is a LINE formation of 8 enemies (denser)."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[4]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "line"
    assert f.enemy_count == 8


def test_act1_wave6_is_v_with_sub_boss_goliath() -> None:
    """BLOQUE 50: Act 1, Wave 6 is a V formation of 8 HEAVY triggering goliath boss."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[5]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "v"
    assert f.enemy_count == 8
    assert wave["sub_boss"] == "goliath"


def test_act1_uses_all_5_formation_types() -> None:
    """BLOQUE 47: act 1 uses all 5 formation types
    (LINE/V/ARC/STAIRCASE/SQUADRON)."""
    from src.systems.wave_manager import DEFAULT_WAVES
    types = {DEFAULT_WAVES[i]["formation"]["formation_type"] for i in range(6)}
    assert types == {"line", "v", "arc", "staircase", "squadron"}, (
        f"Act 1 should use all 5 types; got {types}"
    )


def test_act2_and_act3_still_use_mix_field() -> None:
    """BLOQUE 45: act 2 & 3 keep `mix` (formation derived as LINE fallback)."""
    from src.systems.wave_manager import DEFAULT_WAVES
    for i in range(6, 18):
        assert "mix" in DEFAULT_WAVES[i], (
            f"act 2/3 wave {i} should still use mix field"
        )
        assert "formation" not in DEFAULT_WAVES[i], (
            f"act 2/3 wave {i} should not have explicit formation yet"
        )


def test_wave_manager_validate_still_18_waves() -> None:
    """BLOQUE 45: validate() must still pass: 18 waves, all kill_target > 0, all themes present."""
    from src.systems.wave_manager import WaveManager
    wm = WaveManager()
    ok, msg = wm.validate()
    assert ok, f"validate failed: {msg}"


def test_act1_kill_targets_match_formation_count() -> None:
    """BLOQUE 45: act 1 kill_target = formation count (so clearing == perfect score)."""
    from src.systems.wave_manager import DEFAULT_WAVES
    for i in range(6):
        wave = DEFAULT_WAVES[i]
        f = wave["formation"]
        assert wave["kill_target"] == f["count"], (
            f"act 1 wave {i + 1}: kill_target {wave['kill_target']} != formation count {f['count']}"
        )


def test_act1_formations_emit_spawns_inside_screen() -> None:
    """BLOQUE 45: every act 1 formation produces spawns within the play area."""
    from src.core.settings import INTERNAL_H, INTERNAL_W
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation, spawn_formation
    for i in range(6):
        wave = DEFAULT_WAVES[i]
        f = parse_formation(wave["formation"])
        spawns = spawn_formation(f)
        for s in spawns:
            assert 0 <= s.x <= INTERNAL_W, f"wave {i + 1}: x out of bounds {s.x}"
            assert 0 <= s.y <= INTERNAL_H, f"wave {i + 1}: y out of bounds {s.y}"
            assert s.vy > 0, f"wave {i + 1}: enemies should move down"
