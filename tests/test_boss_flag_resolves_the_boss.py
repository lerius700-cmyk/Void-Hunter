"""BLOQUE 76: `--boss <name>` must spawn the boss it NAMES.

The flag used to be resolved by mapping the name to an ACT and letting the
runtime pick the boss from the act. Act 3's boss IS NEMESIS, so
`--boss phantom` printed "jumped to PHANTOM (act 3)" and spawned NEMESIS:
PHANTOM comes out of the roguelike pool, not out of an act. The flag LIED,
and it lied in the one place the developer looks to see what they are about
to fight.

The name is now resolved against the BossId enum and handed to the runtime
as an id. These tests hold BOTH halves of that chain:

  1. the resolution (`main._resolve_boss`), and
  2. the runtime really spawning the CHOSEN boss.

The second half is the one that matters: a resolution that is never handed
to the runtime would prove nothing. And the test that spawns PHANTOM is
paired with the test that shows act 3 ALONE still spawns NEMESIS, so the
pair fails together if the override ever stops working.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

import main  # noqa: E402
from src.core.scene_manager import GameState  # noqa: E402
from src.entities.enemies.boss import BossId  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402


@pytest.fixture(autouse=True)
def _init_pygame():
    import pygame

    pygame.init()
    yield


def _noop_transition(state: GameState) -> None:
    pass


def _boss_runtime(boss_id: BossId | None = None, act: int = 1) -> GameplayRuntime:
    rt = GameplayRuntime(
        transition_to=_noop_transition,
        is_boss=True,
        act=act,
        boss_id=boss_id,
    )
    rt.on_enter()
    return rt


# ---------------------------------------------------------------------------
# 1. The resolution: the name decides the BOSS, not the act.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("goliath", BossId.GOLIATH),
        ("hydra", BossId.HYDRA),
        ("phantom", BossId.PHANTOM),
        ("nemesis", BossId.NEMESIS),
    ],
)
def test_every_boss_name_resolves_to_its_own_id(name: str, expected: BossId) -> None:
    resolved = main._resolve_boss(name)
    assert resolved is not None, f"{name!r} did not resolve"
    boss_id, _act = resolved
    assert boss_id is expected


def test_the_name_is_case_insensitive() -> None:
    assert main._resolve_boss("GOLIATH")[0] is BossId.GOLIATH
    assert main._resolve_boss("Phantom")[0] is BossId.PHANTOM


def test_an_unknown_boss_name_is_rejected() -> None:
    assert main._resolve_boss("bogus") is None
    assert main._resolve_boss("") is None


def test_every_boss_id_is_reachable_by_name() -> None:
    """The flag's vocabulary is the enum's, not a list that can rot.

    A hand-written list of names would drift the first time a boss is
    added; the enum cannot.
    """
    for boss_id in BossId:
        assert main._resolve_boss(boss_id.value) is not None, boss_id


# ---------------------------------------------------------------------------
# 2. The runtime really spawns the CHOSEN boss.
# ---------------------------------------------------------------------------
def test_the_runtime_spawns_the_chosen_boss() -> None:
    rt = _boss_runtime(boss_id=BossId.PHANTOM, act=3)
    assert rt._boss is not None
    assert rt._boss.id is BossId.PHANTOM


def test_the_act_alone_still_picks_the_act_boss() -> None:
    """The contraposition.

    Act 3 without an override still spawns NEMESIS. If this test ever
    starts failing, the act map changed -- and the pair with it
    (`test_the_runtime_spawns_the_chosen_boss`) says whether the override
    still holds or whether the two paths became indistinguishable.
    """
    rt = _boss_runtime(act=3)
    assert rt._boss is not None
    assert rt._boss.id is BossId.NEMESIS


def test_the_chosen_boss_wins_over_the_act() -> None:
    """The override is not a coincidence of the act it borrows.

    PHANTOM borrows act 3's waves, so act 3 + PHANTOM is the only way to
    tell "the override worked" from "the act decided".
    """
    assert _boss_runtime(boss_id=BossId.PHANTOM, act=3)._boss.id is BossId.PHANTOM
    assert _boss_runtime(act=3)._boss.id is BossId.NEMESIS
    assert _boss_runtime(boss_id=BossId.GOLIATH, act=3)._boss.id is BossId.GOLIATH


# ---------------------------------------------------------------------------
# 3. The flag's own guards.
# ---------------------------------------------------------------------------
def test_act_and_boss_cannot_be_combined(capsys: pytest.CaptureFixture[str]) -> None:
    """`--act 2 --boss goliath` used to run act 1 without a word.

    The boss already picks the act; two flags that disagree must be an
    error, not a silent winner.
    """
    code = main._cmd_play(1, boss="goliath", act=2)
    assert code == 2
    assert "cannot be combined" in capsys.readouterr().err


def test_the_guard_runs_before_the_game_is_built() -> None:
    """The usage error must not boot a whole game to complain about it.

    `Game()` builds the window, the audio and the scenes. A usage error
    that has to build all of that first is a usage error that can hang on
    a machine with no audio device.
    """
    import unittest.mock as mock

    with mock.patch("src.core.game.Game") as game:
        assert main._cmd_play(1, boss="goliath", act=2) == 2
    assert not game.called, "the Game was built before the usage error was reported"
