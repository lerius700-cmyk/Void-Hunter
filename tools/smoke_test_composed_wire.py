"""Smoke test for the BLOQUE 58.14.7 wire: 50 composed patterns registered
with ProceduralWaveManager + SoloEnemySpawner.

Run from the project root: python tools/smoke_test_composed_wire.py
"""
import os
import sys
import random

# Make src importable when run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.systems.wave_patterns.base import WavePatternKind
from src.systems.wave_patterns.composed import (
    COMPOSED_PATTERNS, SoloEnemySpawner, register_composed_patterns,
)
from src.systems.wave_patterns.manager import ProceduralWaveManager
from src.systems.wave_patterns.runtime import spawn_solo_ship


def main():
    # Test 1: imports
    print("OK: all imports succeed")
    print(f"  WavePatternKind.COMPOSED = {WavePatternKind.COMPOSED.value!r}")
    print(f"  COMPOSED_PATTERNS has {len(COMPOSED_PATTERNS)} entries")
    assert len(COMPOSED_PATTERNS) == 50, f"expected 50, got {len(COMPOSED_PATTERNS)}"

    # Test 2: register the 50 patterns with a fresh manager
    mgr = ProceduralWaveManager(seed=42, floor=1)
    print(f"  fresh manager, composed_pool_size = {mgr.composed_pool_size()}")
    assert mgr.composed_pool_size() == 0
    n = mgr.register_composed_patterns()
    print(f"  register_composed_patterns returned {n} (expected 50)")
    assert n == 50
    assert mgr.composed_pool_size() == 50

    # Test 3: pick_pattern distribution over 500 picks
    counts = {k.value: 0 for k in WavePatternKind}
    for _ in range(500):
        result = mgr.pick_pattern(level=1, enemy_kind="SCOUT")
        counts[result.kind.value] += 1
    print("  500 picks distribution:")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {k:25s} = {v}")
    # COMPOSED should be picked a meaningful number of times
    assert counts["composed"] > 50, f"COMPOSED picked only {counts['composed']}x (expected > 50)"

    # Test 4: verify COMPOSED result has segments in extra
    composed_count = 0
    seen_patterns = set()
    for _ in range(500):
        result = mgr.pick_pattern(level=1, enemy_kind="SCOUT")
        if result.kind == WavePatternKind.COMPOSED:
            composed_count += 1
            first_ship = result.ships[0]
            assert "segments" in first_ship.extra, "no segments in extra"
            assert "segment_durations" in first_ship.extra
            assert len(first_ship.extra["segments"]) > 0
            # Track unique pattern names via formation+path+follow
            key = (first_ship.extra["formation"],
                   first_ship.extra["path"],
                   first_ship.extra["follow"])
            seen_patterns.add(key)
            if composed_count <= 3:
                print(f"  sample COMPOSED: {len(result.ships)} ships, "
                      f"{len(first_ship.extra['segments'])} segs, "
                      f"form={first_ship.extra['formation']}, "
                      f"path={first_ship.extra['path']}, "
                      f"follow={first_ship.extra['follow']}")
    print(f"  {composed_count} COMPOSED results, all have valid segments")
    print(f"  unique (formation, path, follow) combos seen: {len(seen_patterns)}")
    assert len(seen_patterns) >= 5, "expected to see at least 5 different composed patterns"

    # Test 5: SoloEnemySpawner
    solo = SoloEnemySpawner(interval_s=5.0)
    rng = random.Random(123)
    solo_ships = []
    # Simulate 12s of game time at 60fps = 720 frames
    for _ in range(720):
        ships = solo.update(0.01667, rng)
        solo_ships.extend(ships)
    print(f"  SoloEnemySpawner produced {len(solo_ships)} ships in 12s (expected ~2)")
    for s in solo_ships:
        assert "segments" in s.extra
        assert s.extra["formation"] == "solo"
        assert s.color == (255, 80, 60)
    print("  all solo ships have segments, formation=solo, red color")
    assert 1 <= len(solo_ships) <= 4, f"unexpected solo count: {len(solo_ships)}"

    # Test 6: spawn_solo_ship can be imported (smoke for runtime.py wiring)
    print(f"  spawn_solo_ship imported OK: {spawn_solo_ship.__name__}")
    print()
    print("ALL SMOKE TESTS PASS")


if __name__ == "__main__":
    main()
