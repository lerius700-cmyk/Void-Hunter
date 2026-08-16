# stellar_horizon/tests/test_wave_manager.py
import json
from pathlib import Path

import pytest

from stellar_horizon.waves.wave_manager import WaveManager
from stellar_horizon.waves.wave_specs import WaveSpec


SAMPLE_JSON = """{
  "act": 1,
  "act_name": "Test Belt",
  "background": "test_bg",
  "midi_track": "test.mid",
  "boss": {
    "kind": "TEST_BOSS",
    "phases": 2,
    "hp": 60,
    "entry_path": "boss_entry"
  },
  "waves": [
    {
      "id": "w1",
      "duration_s": 5.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "v_pointing_left",
          "formation_count": 3,
          "enemy_kind": "scout",
          "path": "s_right_to_left",
          "path_y_offset": 0
        }
      ]
    },
    {
      "id": "w2",
      "duration_s": 5.0,
      "spawns": [
        {
          "delay_s": 0.0,
          "formation": "line_horizontal",
          "formation_count": 4,
          "enemy_kind": "cruiser",
          "path": "s_right_to_left",
          "path_y_offset": 60
        }
      ]
    }
  ]
}"""


@pytest.fixture
def json_path(tmp_path):
    p = tmp_path / "test_waves.json"
    p.write_text(SAMPLE_JSON, encoding="utf-8")
    return p


def test_wave_manager_loads_metadata(json_path):
    wm = WaveManager(json_path)
    assert wm.act == 1
    assert wm.background == "test_bg"
    assert wm.midi_track == "test.mid"


def test_wave_manager_loads_boss_spec(json_path):
    wm = WaveManager(json_path)
    assert wm.boss_spec is not None
    assert wm.boss_spec["kind"] == "TEST_BOSS"
    assert wm.boss_spec["hp"] == 60


def test_wave_manager_starts_at_wave_0(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    assert wm.current_wave_index == 0
    assert wm.elapsed_s == 0.0


def test_wave_manager_spawns_at_delay(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    new = wm.update(0.0)
    assert len(new) == 3
    for e in new:
        assert e.kind == "scout"


def test_wave_manager_advances_to_next_wave(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    wm.update(0.0)
    for e in wm.spawned_enemies:
        e.alive = False
    for _ in range(120):
        wm.update(1 / 60)
    assert wm.wave_complete is True
    ok = wm.next_wave()
    assert ok is True
    assert wm.current_wave_index == 1


def test_wave_manager_next_wave_returns_false_at_end(json_path):
    wm = WaveManager(json_path)
    wm.begin()
    wm.update(0.0)
    for e in wm.spawned_enemies:
        e.alive = False
    for _ in range(120):
        wm.update(1 / 60)
    wm.next_wave()
    wm.update(0.0)
    for e in wm.spawned_enemies:
        e.alive = False
    for _ in range(120):
        wm.update(1 / 60)
    ok = wm.next_wave()
    assert ok is False


def test_wave_spec_dataclass_parses():
    spec = WaveSpec(
        id="w1",
        duration_s=10.0,
        spawns=[{"delay_s": 0.5, "formation": "v_pointing_left",
                 "formation_count": 5, "enemy_kind": "scout",
                 "path": "s_right_to_left", "path_y_offset": 0}],
    )
    assert spec.id == "w1"
    assert spec.duration_s == 10.0
