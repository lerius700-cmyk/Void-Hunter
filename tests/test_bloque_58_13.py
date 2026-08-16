"""BLOQUE 58.13: Tests for ParallelPathPair + OrbitalPath + 4 patterns."""
from __future__ import annotations

import pytest
from src.movement.parallel_path import ParallelPathPair
# OrbitalPath import added in Task 2


# ----------------------------------------------------------------------
# ParallelPathPair tests (5)
# ----------------------------------------------------------------------
def test_parallel_pair_top_bot_offset_at_midpoint():
    """top and bot paths have correct vertical offset at t=0.5 of seg 0."""
    base = [((10, 100), (50, 100), (100, 100), (200, 100))]
    ppp = ParallelPathPair(base, [2.0], gap_px=20)
    top = ppp.get_top().position_at(0.5)
    bot = ppp.get_bot().position_at(0.5)
    assert top.y == pytest.approx(100 - 10, abs=0.01)
    assert bot.y == pytest.approx(100 + 10, abs=0.01)
    assert top.x == pytest.approx(bot.x, abs=0.01)


def test_parallel_pair_same_segment_count_and_durations():
    """both paths have same segment count and durations."""
    base = [
        ((10, 100), (50, 100), (100, 100), (200, 100)),
        ((200, 100), (250, 100), (280, 150), (300, 200)),
    ]
    durations = [1.5, 2.0]
    ppp = ParallelPathPair(base, durations, gap_px=14)
    top = ppp.get_top()
    bot = ppp.get_bot()
    assert len(top.segments) == 2
    assert len(bot.segments) == 2
    assert top.segment_durations == durations
    assert bot.segment_durations == durations


def test_parallel_pair_gap_zero_equals_centerline():
    """gap_px=0 means top and bot are identical."""
    base = [((0, 50), (50, 50), (100, 50), (150, 50))]
    ppp = ParallelPathPair(base, [2.0], gap_px=0)
    top = ppp.get_top().position_at(0.3)
    bot = ppp.get_bot().position_at(0.3)
    assert top.x == pytest.approx(bot.x, abs=0.001)
    assert top.y == pytest.approx(bot.y, abs=0.001)


def test_parallel_pair_durations_match_base():
    """durations pass through unchanged for both paths."""
    durations = [1.0, 2.5, 1.5]
    base = [
        ((0, 0), (10, 0), (20, 0), (30, 0)),
        ((30, 0), (40, 0), (50, 0), (60, 0)),
        ((60, 0), (70, 0), (80, 0), (90, 0)),
    ]
    ppp = ParallelPathPair(base, durations, gap_px=10)
    assert ppp.get_top().segment_durations == durations
    assert ppp.get_bot().segment_durations == durations


def test_parallel_pair_offset_signs():
    """top is offset by -gap/2 (up), bot by +gap/2 (down)."""
    base = [((50, 100), (60, 100), (70, 100), (80, 100))]
    ppp = ParallelPathPair(base, [1.0], gap_px=14)
    top = ppp.get_top().position_at(0.5)
    bot = ppp.get_bot().position_at(0.5)
    assert top.y == pytest.approx(93.0, abs=0.01)
    assert bot.y == pytest.approx(107.0, abs=0.01)
