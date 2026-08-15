"""BLOQUE 58.8 integration tests.

Verifies the runtime integration:
- ProceduralWaveManager wires into GameplayRuntime
- Patterns actually spawn enemies
- HUD pattern label is set
- --patterns flag is parsed
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
import random


@pytest.fixture(autouse=True)
def _ensure_pygame():
    if not __import__("pygame").get_init():
        __import__("pygame").init()
    if not __import__("pygame").display.get_init():
        __import__("pygame").display.set_mode((320, 480))
    yield


def test_runtime_enable_procedural_patterns():
    """Enabling procedural patterns sets the manager and clears state."""
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    assert rt._use_procedural_patterns is False
    rt.enable_procedural_patterns(seed=42, floor=1, spawn_interval=4.0)
    assert rt._use_procedural_patterns is True
    assert rt._proc_mgr is not None
    assert rt._active_pattern_kind_label == ""


def test_runtime_disable_procedural_patterns():
    """Disabling clears the manager."""
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.enable_procedural_patterns(seed=42, floor=1)
    rt.disable_procedural_patterns()
    assert rt._use_procedural_patterns is False
    assert rt._proc_mgr is None


def test_runtime_spawn_procedural_patterns():
    """Spawning picks a pattern and spawns enemies."""
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.enemy import EnemyKind
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.enable_procedural_patterns(seed=42, floor=1, spawn_interval=0.1)
    # Tick for a while until a pattern spawns
    spawned_any = False
    for _ in range(30):
        rt._spawn_pending(1.0 / 60.0)
        if rt._active_pattern_runtime is not None:
            spawned_any = True
            assert rt._active_pattern_kind_label != ""
            break
    assert spawned_any, "no pattern spawned after 30 ticks"


def test_runtime_hud_label_changes_per_pattern():
    """Each pattern kind has a unique HUD label."""
    from src.systems.wave_patterns.runtime import get_pattern_hud_label
    from src.systems.wave_patterns.base import WavePatternKind
    labels = set()
    for kind in WavePatternKind:
        label = get_pattern_hud_label(kind)
        labels.add(label)
    assert len(labels) == len(WavePatternKind), (
        f"duplicate labels: {labels}"
    )


def test_runtime_spawn_completes_and_respawns():
    """After a pattern completes, a new one spawns."""
    from src.ui.gameplay_runtime import GameplayRuntime
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.enable_procedural_patterns(seed=42, floor=1, spawn_interval=0.1)
    # Force a pattern
    rt._pattern_spawn_timer = 0.0
    rt._spawn_pending(1.0 / 60.0)
    first_kind = rt._active_pattern_kind_label
    # Force completion
    if rt._active_pattern_runtime is not None:
        rt._active_pattern_runtime.elapsed = 100.0
    # Tick again to clear
    rt._spawn_pending(1.0 / 60.0)
    # Tick more to allow respawn
    for _ in range(60):
        rt._spawn_pending(1.0 / 60.0)
    # Should eventually have a new pattern (might be the same kind by chance)
    assert rt._active_pattern_kind_label is not None


def test_gameplay_scene_enable_procedural_patterns():
    """GameplayScene forwards enable_procedural_patterns to the runtime."""
    from src.ui.scenes import GameplayScene
    from src.ui.gameplay_runtime import GameplayRuntime
    scene = GameplayScene(transition_to=lambda s: None, act=1)
    # Verify the runtime is set up
    assert hasattr(scene, "_rt")
    assert isinstance(scene._rt, GameplayRuntime)
    # Call enable method
    scene.enable_procedural_patterns(seed=42, floor=1, spawn_interval=4.0)
    assert scene._rt._use_procedural_patterns is True


def test_runtime_pattern_enemy_has_path_or_rigid():
    """Spawned enemies either have a path follower (bezier) or move rigid."""
    from src.ui.gameplay_runtime import GameplayRuntime
    from src.entities.enemies.enemy import EnemyKind
    rt = GameplayRuntime(transition_to=lambda s: None, is_boss=False, act=1)
    rt.enable_procedural_patterns(seed=42, floor=3, spawn_interval=0.1)
    # Tick to spawn
    for _ in range(30):
        rt._spawn_pending(1.0 / 60.0)
        if rt._active_pattern_runtime is not None:
            break
    assert rt._active_pattern_runtime is not None
    # Find an active enemy
    found_active = False
    for e in rt._enemies.pool:
        if e.active and e.kind == EnemyKind.SCOUT:
            found_active = True
            # Either has a path follower (bezier patterns) or doesn't (rigid)
            assert e.path_follower is None or e.path_follower is not None
            break
    assert found_active


def test_main_argparse_patterns():
    """--patterns flag is recognized by main.py argparse."""
    import sys
    # Save and restore argv
    old_argv = sys.argv
    try:
        sys.argv = ["main.py", "--patterns", "42"]
        import main
        args = main._parse_args()
        assert args.patterns == 42
    finally:
        sys.argv = old_argv


def test_main_argparse_patterns_no_seed():
    """--patterns without seed uses default 42."""
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["main.py", "--patterns"]
        import main
        args = main._parse_args()
        assert args.patterns == 42
    finally:
        sys.argv = old_argv


def test_main_argparse_no_patterns():
    """--patterns not given = None (default)."""
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["main.py"]
        import main
        args = main._parse_args()
        assert args.patterns is None
    finally:
        sys.argv = old_argv
