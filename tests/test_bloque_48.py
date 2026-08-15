"""BLOQUE 48: chained wave system for level 1 mode.

The new design replaces the absolute-timestamp spawning with chained
spawning: the next wave starts when the previous one completes OR
after a max-duration window (8s default). Each wave has a spawn
cadence and a max active count (density cap 8).

Boss triggers:
  - main: all 4 waves completed AND elapsed >= 45s
  - perfect: elapsed >= 60s AND no escapes
  - safety: elapsed >= 120s (no score required)

Score: 35 flat (21*1 + 4*2 + 2*3) + 12 perfect-run bonus = 47pt.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# 1. Settings — new constants exist
# ---------------------------------------------------------------------------
def test_settings_wave_max_duration_s_exists() -> None:
    from src.core import settings
    assert hasattr(settings, "WAVE_MAX_DURATION_S")
    assert settings.WAVE_MAX_DURATION_S == 8.0


def test_settings_boss_trigger_constants_exist() -> None:
    from src.core import settings
    assert settings.BOSS_MIN_TRIGGER_S == 45.0
    assert settings.BOSS_PERFECT_TRIGGER_S == 60.0
    assert settings.BOSS_SAFETY_TRIGGER_S == 120.0


def test_settings_level1_ship_counts_match() -> None:
    """BLOQUE 58.6z: 165 ships total = 100 SCOUT + 41 CRUISER + 24 HEAVY.
    Tuned so even a perfect player takes 3:30 to reach GOLIATH (so
    the gameplay song gets a proper listen before the boss fight)."""
    from src.core import settings
    assert settings.LEVEL1_TOTAL_SHIPS == 165
    assert settings.LEVEL1_FLAT_SCORE == 254
    assert settings.PERFECT_RUN_BONUS == 15


# ---------------------------------------------------------------------------
# 2. Level 1 wave structure (4 waves chained)
# ---------------------------------------------------------------------------
def test_level1_waves_has_exactly_4_waves() -> None:
    """BLOQUE 48: 4 waves in level 1 mode (intro, pattern, mixed, finale)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    assert len(LEVEL1_WAVES) == 4


def test_level1_wave_1_is_30_scout_diagonal() -> None:
    """BLOQUE 58.6z: O1: 30 SCOUT in diagonal column, no fire (tutorial).
    Spawn cadence 1.1s = 33s minimum spawn time, contributes to 3:30
    total minimum clear time."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[0]
    assert w["enemies"] == ["SCOUT"] * 30
    assert w["max_duration_s"] == 40.0
    assert w["fire_allowed"] is False


def test_level1_wave_2_is_25_scout_15_cruiser_v() -> None:
    """BLOQUE 58.6z: O2: 25 SCOUT + 15 CRUISER in V formation, fire enabled,
    triggers sub-boss after this wave is cleared. 40 ships * 1.1s = 44s
    minimum spawn time."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[1]
    assert w["enemies"] == ["SCOUT"] * 25 + ["CRUISER"] * 15
    assert w["fire_allowed"] is True
    assert w["formation"] == "v"
    assert w.get("sub_boss_after") is True


def test_level1_wave_3_is_25_scout_12_heavy_8_cruiser_line() -> None:
    """BLOQUE 58.6z: O3: 25 SCOUT + 12 HEAVY + 8 CRUISER in line, 45 ships
    total. 45 * 1.1s = 49.5s minimum spawn time."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[2]
    assert w["enemies"] == ["SCOUT"] * 25 + ["HEAVY"] * 12 + ["CRUISER"] * 8
    assert w["formation"] == "line"


def test_level1_wave_4_is_20_scout_18_cruiser_12_heavy_diamond() -> None:
    """BLOQUE 58.6z: O4: 20 SCOUT + 18 CRUISER + 12 HEAVY in diamond, the
    finale. 50 ships * 1.2s = 60s minimum spawn time. Together with
    O1/O2/O3/sub-boss/transitions/boss-intro the total minimum clear
    is 3:31 — matches the gameplay song length to give the player
    time to listen before GOLIATH appears."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[3]
    assert w["enemies"] == ["SCOUT"] * 20 + ["CRUISER"] * 18 + ["HEAVY"] * 12
    assert w["formation"] == "diamond"


def test_level1_total_ships_equals_165() -> None:
    """BLOQUE 58.6z: 30 + 40 + 45 + 50 = 165 ships. Tuned so the minimum
    clear time is 3:30 even for a perfect-speed player (so the gameplay
    song gets a proper listen before GOLIATH)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    total = sum(len(w["enemies"]) for w in LEVEL1_WAVES)
    assert total == 165


# ---------------------------------------------------------------------------
# 3. Chaining: next wave starts when previous is complete
# ---------------------------------------------------------------------------
def test_wave_chaining_next_starts_on_completion() -> None:
    """When all enemies of wave N are spawned and dead, wave N+1 starts."""
    from src.systems.wave_manager import WaveChain
    chain = WaveChain(wave_specs=[
        {"enemies": ["SCOUT"] * 2, "spawn_cadence_s": 0.1, "max_duration_s": 5.0},
        {"enemies": ["SCOUT"] * 2, "spawn_cadence_s": 0.1, "max_duration_s": 5.0},
    ])
    # Tick + spawn + tick + spawn (respect cadence)
    chain.tick(0.1)
    chain.spawn(0, 0.0, 0.0, "SCOUT")
    chain.tick(0.2)
    chain.spawn(0, 0.0, 0.0, "SCOUT")
    # Kill both
    chain.kill(0)
    chain.kill(0)
    # Next tick should advance to wave 1
    chain.tick(0.1)
    assert chain.current_wave_idx == 1


def test_wave_chaining_next_starts_after_max_duration() -> None:
    """If wave is not complete, next wave starts after max_duration_s."""
    from src.systems.wave_manager import WaveChain
    chain = WaveChain(wave_specs=[
        {"enemies": ["SCOUT"] * 2, "spawn_cadence_s": 1.0, "max_duration_s": 2.0},
        {"enemies": ["SCOUT"] * 1, "spawn_cadence_s": 1.0, "max_duration_s": 2.0},
    ])
    # Spawn 1 enemy, then advance time past max_duration
    chain.tick(1.0)
    chain.spawn(0, 0.0, 0.0, "SCOUT")
    # Don't kill it; just advance time past max_duration + all_spawned
    chain.tick(2.5)  # spawn 2nd enemy, then time hits max_duration
    # The chain should still advance to next wave after max duration
    # even if not all enemies are dead
    assert chain.current_wave_idx == 1


# ---------------------------------------------------------------------------
# 4. Density cap (max 8 simultaneous)
# ---------------------------------------------------------------------------
def test_density_cap_8_enforced() -> None:
    """BLOQUE 48: max 8 enemies alive on screen at once."""
    from src.systems.wave_manager import WaveChain
    chain = WaveChain(
        wave_specs=[
            {"enemies": ["SCOUT"] * 10, "spawn_cadence_s": 0.1, "max_duration_s": 5.0},
        ],
        max_alive=8,
    )
    # Spawn 12 enemies, but only 8 should be active
    for i in range(12):
        chain.tick(0.2)  # 0.2s elapsed each
        chain.spawn(0, 0.0, 0.0, "SCOUT")
    assert chain.alive_count <= 8


# ---------------------------------------------------------------------------
# 5. Single source of truth for kills
# ---------------------------------------------------------------------------
def test_wave_chain_has_single_kill_counter() -> None:
    """BLOQUE 48: only one kills counter (no _level1_kills duplicate)."""
    from src.systems.wave_manager import WaveChain
    chain = WaveChain(wave_specs=[
        {"enemies": ["SCOUT"] * 2, "spawn_cadence_s": 0.1, "max_duration_s": 5.0},
    ])
    assert hasattr(chain, "kills")
    # No _level1_kills attribute
    assert not hasattr(chain, "_level1_kills")
    # kill increments the single counter
    chain.spawn(0, 0.0, 0.0, "SCOUT")
    chain.kill(0)
    assert chain.kills == 1


# ---------------------------------------------------------------------------
# 6. Scoring: 35 flat + 12 perfect = 47
# ---------------------------------------------------------------------------
def test_level1_flat_score_is_254() -> None:
    """BLOQUE 58.6z: 100 SCOUT (1pt) + 41 CRUISER (2pt) + 24 HEAVY (3pt) = 254pt.

    Tuned alongside the new ship counts so the minimum clear time is
    3:30 (so the gameplay song gets a proper listen before GOLIATH).
    """
    from src.systems.wave_manager import LEVEL1_WAVES
    from src.core.settings import SCOUT_FLAT_SCORE, CRUISER_FLAT_SCORE, HEAVY_FLAT_SCORE
    total = 0
    for w in LEVEL1_WAVES:
        for kind in w["enemies"]:
            if kind == "SCOUT":
                total += SCOUT_FLAT_SCORE
            elif kind == "CRUISER":
                total += CRUISER_FLAT_SCORE
            elif kind == "HEAVY":
                total += HEAVY_FLAT_SCORE
    # 100 SCOUT * 1 + 41 CRUISER * 2 + 24 HEAVY * 3 = 100 + 82 + 72 = 254
    assert total == 254


def test_perfect_run_bonus_score_is_269_total() -> None:
    """BLOQUE 58.6z: 254 flat + 15 perfect = 269pt (achievable).
    Plus sub-boss bonus brings the practical max higher.
    """
    from src.core.settings import LEVEL1_FLAT_SCORE, PERFECT_RUN_BONUS
    assert LEVEL1_FLAT_SCORE + PERFECT_RUN_BONUS == 269


# ---------------------------------------------------------------------------
# 7. Boss triggers
# ---------------------------------------------------------------------------
def test_boss_main_trigger_requires_completion_and_45s() -> None:
    """All waves done AND elapsed >= 45s → boss."""
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    assert bt.evaluate(elapsed_s=30.0, waves_complete=True, perfect=False, kills=27) is None
    assert bt.evaluate(elapsed_s=44.0, waves_complete=True, perfect=False, kills=27) is None
    assert bt.evaluate(elapsed_s=45.0, waves_complete=True, perfect=False, kills=27) == "main"
    assert bt.evaluate(elapsed_s=50.0, waves_complete=True, perfect=False, kills=27) == "main"


def test_boss_perfect_trigger_at_60s() -> None:
    """elapsed >= 60s AND perfect AND kills >= 1 → boss."""
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    assert bt.evaluate(elapsed_s=59.0, waves_complete=False, perfect=True, kills=10) is None
    assert bt.evaluate(elapsed_s=60.0, waves_complete=False, perfect=True, kills=10) == "perfect"
    assert bt.evaluate(elapsed_s=60.0, waves_complete=False, perfect=True, kills=0) is None


def test_boss_safety_trigger_at_120s() -> None:
    """elapsed >= 120s → boss regardless of kills."""
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    assert bt.evaluate(elapsed_s=119.0, waves_complete=False, perfect=False, kills=0) is None
    assert bt.evaluate(elapsed_s=120.0, waves_complete=False, perfect=False, kills=0) == "safety"
