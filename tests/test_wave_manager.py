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
    """BLOQUE 45: Act 1, Wave 1 is a LINE formation of 4 SCOUT."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[0]
    assert wave["act"] == 1 and wave["wave"] == 1
    f = parse_formation(wave["formation"])
    assert f.formation_type == "line"
    assert f.enemy_type == "SCOUT"
    assert f.enemy_count == 4
    assert f.telegraph_frames == 30
    assert f.pattern_speed == 40


def test_act1_wave2_is_v_formation() -> None:
    """BLOQUE 45: Act 1, Wave 2 is a V formation of 5 SCOUT."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[1]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "v"
    assert f.enemy_count == 5
    assert f.enemy_type == "SCOUT"


def test_act1_wave3_is_arc_formation() -> None:
    """BLOQUE 45: Act 1, Wave 3 is an ARC formation of 5 CRUISER."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[2]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "arc"
    assert f.enemy_count == 5
    assert f.enemy_type == "CRUISER"
    assert f.telegraph_frames == 45


def test_act1_wave4_is_staircase_formation() -> None:
    """BLOQUE 45: Act 1, Wave 4 is a STAIRCASE formation of 4 HEAVY."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[3]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "staircase"
    assert f.enemy_count == 4
    assert f.enemy_type == "HEAVY"
    assert f.telegraph_frames == 60


def test_act1_wave5_is_line_mixed() -> None:
    """BLOQUE 45: Act 1, Wave 5 is a LINE formation of 6 enemies."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[4]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "line"
    assert f.enemy_count == 6


def test_act1_wave6_is_v_with_sub_boss_goliath() -> None:
    """BLOQUE 45: Act 1, Wave 6 is a V formation triggering goliath boss."""
    from src.systems.wave_manager import DEFAULT_WAVES, parse_formation
    wave = DEFAULT_WAVES[5]
    f = parse_formation(wave["formation"])
    assert f.formation_type == "v"
    assert f.enemy_count == 6
    assert wave["sub_boss"] == "goliath"


def test_act1_uses_all_4_formation_types() -> None:
    """BLOQUE 45: act 1 uses all 4 formation types (LINE/V/ARC/STAIRCASE)."""
    from src.systems.wave_manager import DEFAULT_WAVES
    types = {DEFAULT_WAVES[i]["formation"]["formation_type"] for i in range(6)}
    assert types == {"line", "v", "arc", "staircase"}, (
        f"Act 1 should use all 4 types; got {types}"
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
