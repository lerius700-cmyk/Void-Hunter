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
