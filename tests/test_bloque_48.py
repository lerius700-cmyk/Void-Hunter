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
    # BLOQUE 58.7ac: PERFECT raised to 100s so sub-boss (~95s) gets a turn.
    # SAFETY raised to 140s so it fires after the sub-boss, not at the same time.
    assert settings.BOSS_PERFECT_TRIGGER_S == 100.0
    assert settings.BOSS_SAFETY_TRIGGER_S == 140.0


def test_settings_level1_ship_counts_match() -> None:
    """BLOQUE 58.11: 380 ships total = 250 SCOUT + 82 CRUISER + 48 HEAVY.
    Doubled from BLOQUE 58.6z (165 ships). New clear target ~4:00 (was 3:30).
    User wanted "mas naves, mas frenetico, pero un poco mas de tiempo total"."""
    from src.core import settings
    assert settings.LEVEL1_TOTAL_SHIPS == 380
    assert settings.LEVEL1_FLAT_SCORE == 558
    assert settings.PERFECT_RUN_BONUS == 15


# ---------------------------------------------------------------------------
# 2. Level 1 wave structure (5 waves chained, BLOQUE 58.11)
# ---------------------------------------------------------------------------
def test_level1_waves_has_exactly_5_waves() -> None:
    """BLOQUE 58.11: 5 waves in level 1 mode (intro, pattern, mixed, finale, bridge)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    assert len(LEVEL1_WAVES) == 5


def test_level1_wave_1_is_60_scout_diagonal() -> None:
    """BLOQUE 58.11: O1: 60 SCOUT in diagonal column, no fire (tutorial).
    2x of BLOQUE 58.6z. Spawn cadence 0.6s = 36s minimum spawn time."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[0]
    assert w["enemies"] == ["SCOUT"] * 60
    assert w["max_duration_s"] == 50.0
    assert w["fire_allowed"] is False


def test_level1_wave_2_is_50_scout_30_cruiser_v() -> None:
    """BLOQUE 58.11: O2: 50 SCOUT + 30 CRUISER in V formation, fire enabled,
    triggers sub-boss after this wave is cleared. 80 ships * 0.6s = 48s
    minimum spawn time. 2x of BLOQUE 58.6z (25+15=40)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[1]
    assert w["enemies"] == ["SCOUT"] * 50 + ["CRUISER"] * 30
    assert w["fire_allowed"] is True
    assert w["formation"] == "v"
    assert w.get("sub_boss_after") is True


def test_level1_wave_3_is_50_scout_24_heavy_16_cruiser_line() -> None:
    """BLOQUE 58.11: O3: 50 SCOUT + 24 HEAVY + 16 CRUISER in line, 90 ships
    total. 90 * 0.6s = 54s minimum spawn time. 2x of BLOQUE 58.6z (25+12+8=45)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[2]
    assert w["enemies"] == ["SCOUT"] * 50 + ["HEAVY"] * 24 + ["CRUISER"] * 16
    assert w["formation"] == "line"


def test_level1_wave_4_is_40_scout_36_cruiser_24_heavy_diamond() -> None:
    """BLOQUE 58.11: O4: 40 SCOUT + 36 CRUISER + 24 HEAVY in diamond.
    100 ships * 0.6s = 60s minimum spawn time. 2x of BLOQUE 58.6z (20+18+12=50)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[3]
    assert w["enemies"] == ["SCOUT"] * 40 + ["CRUISER"] * 36 + ["HEAVY"] * 24
    assert w["formation"] == "diamond"


def test_level1_wave_5_is_50_scout_bridge() -> None:
    """BLOQUE 58.11: O5: NEW bridge wave. 50 SCOUT diagonal, no fire.
    Fills the gap between Wolfen (after O2) and GOLIATH (after O5)."""
    from src.systems.wave_manager import LEVEL1_WAVES
    w = LEVEL1_WAVES[4]
    assert w["enemies"] == ["SCOUT"] * 50
    assert w["fire_allowed"] is False


def test_level1_total_ships_equals_380() -> None:
    """BLOQUE 58.11: 60+80+90+100+50 = 380 ships. Doubled from 165.
    New clear target ~4:00 (was 3:30). User wanted "mas naves, mas
    frenetico, pero un poco mas de tiempo total"."""
    from src.systems.wave_manager import LEVEL1_WAVES
    total = sum(len(w["enemies"]) for w in LEVEL1_WAVES)
    assert total == 380


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
    # BLOQUE 58.11: 250 SCOUT + 82 CRUISER + 48 HEAVY
    # = 250*1 + 82*2 + 48*3 = 250 + 164 + 144 = 558
    assert total == 558


def test_perfect_run_bonus_score_is_573_total() -> None:
    """BLOQUE 58.11: 558 flat + 15 perfect = 573pt (achievable).
    Plus sub-boss bonus brings the practical max higher.
    """
    from src.core.settings import LEVEL1_FLAT_SCORE, PERFECT_RUN_BONUS
    assert LEVEL1_FLAT_SCORE + PERFECT_RUN_BONUS == 573


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
    """BLOQUE 58.7ac: perfect trigger now at 100s (after sub-boss ~95s)."""
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    # Before 100s: no trigger even with perfect + kills
    assert bt.evaluate(elapsed_s=99.0, waves_complete=False, perfect=True, kills=10) is None
    # At 100s: perfect trigger fires
    assert bt.evaluate(elapsed_s=100.0, waves_complete=False, perfect=True, kills=10) == "perfect"
    # At 100s with no kills: no trigger (still requires kills >= 1)
    assert bt.evaluate(elapsed_s=100.0, waves_complete=False, perfect=True, kills=0) is None


def test_boss_safety_trigger_at_120s() -> None:
    """BLOQUE 58.7ac: safety trigger now at 140s (after sub-boss + perfect)."""
    from src.systems.wave_manager import BossTrigger
    bt = BossTrigger()
    # Before 140s: no trigger without perfect + kills
    assert bt.evaluate(elapsed_s=139.0, waves_complete=False, perfect=False, kills=0) is None
    # At 140s: safety trigger fires
    assert bt.evaluate(elapsed_s=140.0, waves_complete=False, perfect=False, kills=0) == "safety"
