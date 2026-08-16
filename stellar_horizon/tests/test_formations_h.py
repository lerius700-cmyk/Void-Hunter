# stellar_horizon/tests/test_formations_h.py
import pytest

from stellar_horizon.waves.formations_h import (
    v_pointing_left, line_horizontal, diamond_pointing_left, wedge_pointing_left,
)


def test_v_pointing_left_default_count():
    offsets = v_pointing_left()
    assert len(offsets) == 5


def test_v_pointing_left_count_3():
    offsets = v_pointing_left(count=3)
    assert len(offsets) == 3


def test_v_pointing_left_wings_behind_leader():
    """For enemies moving -X, wings must be at +X (behind the leader)."""
    offsets = v_pointing_left(count=5, spacing=18.0)
    leader = offsets[0]
    assert leader == (0.0, 0.0)
    for dx, dy in offsets[1:]:
        assert dx > 0


def test_v_pointing_left_wings_symmetric_y():
    offsets = v_pointing_left(count=5, spacing=18.0)
    ys = sorted([abs(dy) for _, dy in offsets[1:]])
    assert ys[0] == ys[-1] or len(set(ys)) <= 2


def test_line_horizontal_default_count():
    offsets = line_horizontal()
    assert len(offsets) == 5
    for _, dy in offsets:
        assert dy == 0.0


def test_line_horizontal_spans_correctly():
    offsets = line_horizontal(count=5, spacing=22.0)
    xs = sorted([dx for dx, _ in offsets])
    # half = (5-1) * 22 / 2 = 44; range is -44 to +44
    assert xs[0] == -44.0
    assert xs[-1] == 44.0


def test_diamond_pointing_left_default_count():
    offsets = diamond_pointing_left()
    assert len(offsets) == 5


def test_diamond_pointing_left_vertex_at_origin():
    offsets = diamond_pointing_left(count=5, spacing=20.0)
    assert offsets[0] == (0.0, 0.0)


def test_wedge_pointing_left_count_3():
    offsets = wedge_pointing_left(count=3)
    assert len(offsets) == 3


def test_wedge_pointing_left_tip_at_origin():
    offsets = wedge_pointing_left(count=5)
    assert offsets[0] == (0.0, 0.0)


def test_formations_with_count_1():
    """count=1 formations should return a single (0, 0) slot."""
    for fn in (v_pointing_left, line_horizontal, diamond_pointing_left, wedge_pointing_left):
        offsets = fn(count=1)
        assert len(offsets) == 1
        assert offsets[0] == (0.0, 0.0)
