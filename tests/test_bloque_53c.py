"""BLOQUE 53c: tests for gold ring (Star Fox) mechanic.

Covers:
  - Player.heal adds HP up to max
  - Player.add_gold_ring heals + stacks rings
  - 3 rings → one-time HP double (hp_doubled flag set)
  - After double, rings are no-op
  - HP boost from tech upgrade (BLOQUE 53d basic test)
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
pygame.init()


def _make_player():
    from src.entities.player.player import Player
    p = Player()
    p.reset()
    return p


# ---------------------------------------------------------------------------
# 1. heal
# ---------------------------------------------------------------------------
def test_heal_adds_hp() -> None:
    p = _make_player()
    p.hp = 10
    healed = p.heal(5)
    assert healed == 5
    assert p.hp == 15


def test_heal_caps_at_max() -> None:
    p = _make_player()
    p.hp = 25
    healed = p.heal(100)  # would overflow
    # Cap at hp_max
    assert p.hp == p.hp_max
    assert healed == p.hp_max - 25


def test_heal_returns_actual_healed() -> None:
    p = _make_player()
    p.hp = p.hp_max
    assert p.heal(5) == 0
    p.hp = p.hp_max - 2
    assert p.heal(5) == 2  # only 2 actually healed


# ---------------------------------------------------------------------------
# 2. add_gold_ring
# ---------------------------------------------------------------------------
def test_gold_ring_heals() -> None:
    p = _make_player()
    p.hp = 10
    doubled = p.add_gold_ring()
    # Default heal is 2 (GOLD_RING_HEAL)
    assert p.hp == 12
    assert doubled == 0
    assert p.gold_rings == 1


def test_three_rings_doubles_max_hp() -> None:
    p = _make_player()
    initial_max = p.hp_max
    p.add_gold_ring()  # 1
    p.add_gold_ring()  # 2
    assert p.hp_doubled is False
    p.add_gold_ring()  # 3 — triggers double
    assert p.hp_doubled is True
    assert p.hp_max == initial_max * 2
    # HP is fully refilled on the double
    assert p.hp == p.hp_max
    # Counter resets
    assert p.gold_rings == 0


def test_doubled_rings_are_noop() -> None:
    p = _make_player()
    for _ in range(3):
        p.add_gold_ring()
    assert p.hp_doubled is True
    # Add 3 more rings — should be no-op
    for _ in range(3):
        result = p.add_gold_ring()
        assert result == 0
    # HP max should stay doubled (not x4)
    assert p.hp_max == 60  # 30 * 2


def test_gold_ring_heal_caps_at_new_max_after_double() -> None:
    """When the double fires, HP is fully refilled. Future heals
    cap at the new (doubled) max."""
    p = _make_player()
    p.hp = 5
    for _ in range(3):
        p.add_gold_ring()
    # After double, HP should be hp_max
    assert p.hp == p.hp_max
    # Heal more — caps at new max
    healed = p.heal(100)
    assert healed == 0  # already at max
    assert p.hp == p.hp_max


# ---------------------------------------------------------------------------
# 3. add_tech_upgrade (BLOQUE 53d stub)
# ---------------------------------------------------------------------------
def test_hp_boost_10_increases_max_hp() -> None:
    p = _make_player()
    initial_max = p.hp_max
    p.add_tech_upgrade("HP_BOOST_10")
    # +10% of current max (rounded up, min +1)
    expected_boost = max(1, int(initial_max * 0.10))
    assert p.hp_max == initial_max + expected_boost
    # HP refilled on upgrade
    assert p.hp == p.hp_max
    # Upgrade recorded
    assert "HP_BOOST_10" in p.tech_upgrades


def test_duplicate_tech_upgrade_is_noop() -> None:
    p = _make_player()
    p.add_tech_upgrade("HP_BOOST_10")
    initial_max = p.hp_max
    p.add_tech_upgrade("HP_BOOST_10")
    assert p.hp_max == initial_max
    assert p.tech_upgrades.count("HP_BOOST_10") == 1
