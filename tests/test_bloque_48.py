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
    """BLOQUE 50: 62 ships total = 44 SCOUT + 11 CRUISER + 7 HEAVY (denser)."""
    from src.core import settings
    assert settings.LEVEL1_TOTAL_SHIPS == 62
    assert settings.LEVEL1_FLAT_SCORE == 87
    assert settings.PERFECT_RUN_BONUS == 15


# ---------------------------------------------------------------------------
# 2. Level 1 wave structure (4 waves chained)
# ---------------------------------------------------------------------------
def test_level1_waves_has_exactly_4_waves() -> None:
    """BLOQUE 48: 4 waves in level 1 mode (intro, pattern, mixed, finale)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    assert len(LEVEL1_WAVES) == 4


def test_level1_wave_1_is_6_scout_diagonal() -> None:
    """BLOQUE 50: O1: 12 SCOUT in diagonal column, no fire (tutorial)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[0]
    assert w["enemies"] == ["SCOUT"] * 12
    assert w["max_duration_s"] == 10.0
    assert w["fire_allowed"] is False


def test_level1_wave_2_is_6_scout_2_cruiser_v() -> None:
    """BLOQUE 50: O2: 14 SCOUT + 5 CRUISER in V formation, fire enabled,
    triggers sub-boss after this wave is cleared."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[1]
    assert w["enemies"] == ["SCOUT"] * 14 + ["CRUISER"] * 5
    assert w["fire_allowed"] is True
    assert w["formation"] == "v"
    assert w.get("sub_boss_after") is True


def test_level1_wave_3_is_6_scout_1_heavy_line() -> None:
    """BLOQUE 50: O3: 10 SCOUT + 4 HEAVY in horizontal line, HEAVY as anchor."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[2]
    assert w["enemies"] == ["SCOUT"] * 10 + ["HEAVY"] * 4
    assert w["formation"] == "line"


def test_level1_wave_4_is_diamond_3_scout_2_cruiser_1_heavy() -> None:
    """BLOQUE 50: O4: 8 SCOUT + 6 CRUISER + 3 HEAVY in diamond, hardest wave."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[3]
    assert w["enemies"] == ["SCOUT"] * 8 + ["CRUISER"] * 6 + ["HEAVY"] * 3
    assert w["formation"] == "diamond"


def test_level1_total_ships_equals_62() -> None:
    """BLOQUE 50: 12 + 19 + 14 + 17 = 62 ships (denser than BLOQUE 49's 43)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    total = sum(len(w["enemies"]) for w in LEVEL1_WAVES)
    assert total == 62


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
def test_level1_flat_score_is_57() -> None:
    """BLOQUE 50: 44 SCOUT (1pt) + 11 CRUISER (2pt) + 7 HEAVY (3pt) = 87pt.

    The setting constant LEVEL1_FLAT_SCORE matches the actual sum.
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
    # 44 SCOUT * 1 + 11 CRUISER * 2 + 7 HEAVY * 3 = 44 + 22 + 21 = 87
    assert total == 87


def test_perfect_run_bonus_score_is_102_total() -> None:
    """BLOQUE 50: 87 flat + 15 perfect = 102pt (achievable).
    Plus sub-boss bonus (+5pt) brings the practical max to 107pt.
    """
    from src.core.settings import LEVEL1_FLAT_SCORE, PERFECT_RUN_BONUS
    assert LEVEL1_FLAT_SCORE + PERFECT_RUN_BONUS == 102


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
