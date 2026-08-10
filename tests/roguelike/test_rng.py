"""Tests for src.roguelike.rng (BLOQUE 57)."""
from __future__ import annotations

import pytest

from src.roguelike.rng import SeededRNG


# ---------------------------------------------------------------------------
# 1. Basic API
# ---------------------------------------------------------------------------
def test_random_in_range() -> None:
    rng = SeededRNG(seed=42)
    for _ in range(1000):
        v = rng.random()
        assert 0.0 <= v < 1.0


def test_randint_inclusive() -> None:
    rng = SeededRNG(seed=42)
    for _ in range(1000):
        v = rng.randint(1, 6)
        assert 1 <= v <= 6


def test_randint_single_value() -> None:
    rng = SeededRNG(seed=42)
    for _ in range(100):
        assert rng.randint(5, 5) == 5


def test_randint_invalid_range_raises() -> None:
    rng = SeededRNG(seed=42)
    with pytest.raises(ValueError, match="a .* must be <= b"):
        rng.randint(10, 1)


# ---------------------------------------------------------------------------
# 2. choice / choices
# ---------------------------------------------------------------------------
def test_choice_uniform() -> None:
    rng = SeededRNG(seed=42)
    options = ["a", "b", "c"]
    for _ in range(1000):
        assert rng.choice(options) in options


def test_choices_with_weights() -> None:
    rng = SeededRNG(seed=42)
    # Strong weight on "a" -> mostly "a"
    counts = {"a": 0, "b": 0}
    for _ in range(1000):
        v = rng.choices(["a", "b"], [0.99, 0.01])
        counts[v] += 1
    assert counts["a"] > 900
    assert counts["b"] < 100


def test_choices_zero_weight_excluded() -> None:
    rng = SeededRNG(seed=42)
    for _ in range(100):
        v = rng.choices(["a", "b"], [1.0, 0.0])
        assert v == "a"


def test_choices_invalid_weights_raise() -> None:
    rng = SeededRNG(seed=42)
    with pytest.raises(ValueError, match="negative"):
        rng.choices(["a", "b"], [1.0, -0.5])
    with pytest.raises(ValueError, match="sum to zero"):
        rng.choices(["a", "b"], [0.0, 0.0])
    with pytest.raises(ValueError, match="length"):
        rng.choices(["a", "b"], [1.0])


# ---------------------------------------------------------------------------
# 3. State save / restore
# ---------------------------------------------------------------------------
def test_state_save_restore() -> None:
    rng1 = SeededRNG(seed=42)
    rng1.random()
    rng1.random()
    state = rng1.state_dict()
    rng2 = SeededRNG(seed=99)  # different seed
    rng2.load_state_dict(state)
    # Now they should produce identical sequences
    for _ in range(100):
        assert rng1.random() == rng2.random()


def test_state_save_after_many_calls() -> None:
    rng1 = SeededRNG(seed=42)
    for _ in range(500):
        rng1.random()
    state = rng1.state_dict()
    rng2 = SeededRNG(seed=0)
    rng2.load_state_dict(state)
    assert rng1.random() == rng2.random()


# ---------------------------------------------------------------------------
# 4. Shuffle
# ---------------------------------------------------------------------------
def test_shuffle_deterministic() -> None:
    rng1 = SeededRNG(seed=42)
    rng2 = SeededRNG(seed=42)
    a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    b = list(a)
    rng1.shuffle(a)
    rng2.shuffle(b)
    assert a == b
    # And the shuffle actually permuted (not identity)
    assert a != list(range(1, 11))


def test_shuffle_changes_order() -> None:
    rng = SeededRNG(seed=42)
    original = list(range(20))
    a = list(original)
    rng.shuffle(a)
    assert a != original
    assert sorted(a) == original  # all elements preserved


# ---------------------------------------------------------------------------
# 5. gauss
# ---------------------------------------------------------------------------
def test_gauss_distribution() -> None:
    """1000 samples from N(0, 1) should have mean ~0 and stddev ~1."""
    rng = SeededRNG(seed=42)
    samples = [rng.gauss(0.0, 1.0) for _ in range(2000)]
    mean = sum(samples) / len(samples)
    var = sum((s - mean) ** 2 for s in samples) / len(samples)
    stddev = var ** 0.5
    assert abs(mean) < 0.1, f"mean={mean} too far from 0"
    assert 0.9 < stddev < 1.1, f"stddev={stddev} too far from 1"


# ---------------------------------------------------------------------------
# 6. No global random import
# ---------------------------------------------------------------------------
def test_no_global_random_in_module() -> None:
    """BLOQUE 57: SeededRNG must not use the global `random` module.
    Check actual import lines, not arbitrary text matches."""
    import re
    with open("src/roguelike/rng.py", encoding="utf-8") as f:
        content = f.read()
    # Strip docstrings (triple-quoted strings) before scanning
    content_no_docs = re.sub(r'"""[\s\S]*?"""', "", content)
    content_no_docs = re.sub(r"'''[\s\S]*?'''", "", content_no_docs)
    # Now check for actual import statements
    assert not re.search(r"^\s*import\s+random\b", content_no_docs, re.MULTILINE)
    assert not re.search(r"^\s*from\s+random\b", content_no_docs, re.MULTILINE)
