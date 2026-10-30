"""BLOQUE 74: a malformed manifest must DEGRADE, not break the game.

`manifest.toml` is HAND-EDITED (it is the set's spec), so a half-written
file is a plausible state: a missing bracket, a stray quote. `tomllib`
raises `TOMLDecodeError` for that -- and `TOMLDecodeError` is a
`ValueError`, NOT a `ManifestError`.

The game-facing loader (`src.anim.manifest.loaded_set`) must therefore
degrade to None, so `Boss.animation_path` keeps working with its own
defaults instead of raising out of the game loop. Its sibling in
`src/ui/scenes.py` already degrades that way: the two loaders must never
disagree about what "unreadable" means.

The manifest cache is a process-level cache, so it also has to be dropped
when the runtime swaps the art: `clear_anchor_cache()` is exactly that
hook, and the two caches hold the SAME file.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim import manifest  # noqa: E402

# A manifest with a SYNTAX error: the array is never closed.
BROKEN_MANIFEST = """
[meta]
name = "GOLIATH"
version = 1
canvas = [96, 80
anchor = [48, 40]
sided = "right"

[[clips]]
id = "phase1_idle"
dir = "phase1_idle"
frames = 10
fps = 10
loop = true
"""

VALID_MANIFEST = """
[meta]
name = "GOLIATH"
version = 1
canvas = [96, 80]
anchor = [48, 40]
sided = "right"

[[clips]]
id = "phase1_idle"
dir = "phase1_idle"
frames = 10
fps = 10
loop = true

[[parts]]
id = "body"
draw = "frames"
pivot = "centroid"
z = 0
"""

SWAPPED_MANIFEST = VALID_MANIFEST.replace('"phase1_idle"', '"swapped_id"')


def _clear_cache() -> None:
    """Empty the manifest cache, whatever the public hook is called."""
    clear = getattr(manifest, "clear_loaded_cache", None)
    if clear is not None:
        clear()
    else:
        manifest._LOADED.clear()


@pytest.fixture(autouse=True)
def _clean_manifest_cache():
    """The manifest cache is process-level: every test starts and ends clean."""
    _clear_cache()
    yield
    _clear_cache()


@pytest.fixture
def broken_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A set whose manifest.toml has a syntax error."""
    set_dir = tmp_path / "goliath"
    set_dir.mkdir()
    (set_dir / "manifest.toml").write_text(BROKEN_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest, "_sets_root", lambda: tmp_path)
    return set_dir


def test_a_malformed_manifest_degrades_to_none(broken_set: Path):
    """The loader returns None instead of raising.

    `tomllib.TOMLDecodeError` is a `ValueError`: the loader has to catch
    it, or a hand-edited manifest with a typo breaks the game.
    """
    assert manifest.loaded_set("goliath") is None


def test_the_boss_survives_a_malformed_manifest(broken_set: Path):
    """`Boss.animation_path` must not raise: the game loop must not break.

    With no manifest the boss falls back to its own default: the clip id
    is the directory name (which is what every shipped clip declares).
    """
    from src.entities.enemies.boss import Boss

    boss = Boss()
    boss.animation_state = "phase1_idle"
    boss.animation_frame = 0

    assert boss.animation_path == "bosses/goliath/phase1_idle/frame_00.png"


def test_a_missing_manifest_degrades_to_none(tmp_path: Path, monkeypatch):
    """The other unreadable case: there is no manifest at all."""
    monkeypatch.setattr(manifest, "_sets_root", lambda: tmp_path)
    assert manifest.loaded_set("goliath") is None


def test_a_broken_manifest_is_not_re_read_on_every_call(
    broken_set: Path, monkeypatch: pytest.MonkeyPatch
):
    """A manifest that FAILED to load must be cached as a failure too.

    `loaded_set` is on the hot path: `Boss.animation_path` calls it on
    every frame to rebuild the sprite path. It caches the SUCCESSFUL
    parses, so a manifest that degrades to None was re-read AND re-parsed
    from disk on every single frame -- the exact cost the cache exists to
    avoid, paid forever by the one state that cannot be fixed at runtime.

    The sibling loader in `src/ui/scenes.py` already caches its failure
    (`_manifest_failed`). The two loaders must behave the same way.
    """
    calls: list[str] = []
    real_load = manifest.load_set

    def counting_load(name, root=None):
        calls.append(name)
        return real_load(name, root)

    monkeypatch.setattr(manifest, "load_set", counting_load)

    assert manifest.loaded_set("goliath") is None
    assert manifest.loaded_set("goliath") is None
    assert manifest.loaded_set("goliath") is None

    assert len(calls) == 1, (
        f"the broken manifest was read {len(calls)} times: a failure must be "
        "cached too (src.anim.manifest.loaded_set)"
    )


def test_the_failure_cache_is_dropped_by_the_invalidation_hook(
    broken_set: Path, monkeypatch: pytest.MonkeyPatch
):
    """A failed manifest must be re-tried once the cache is dropped.

    Otherwise a manifest that was broken at boot -- or while the art was
    being swapped -- would stay broken for the rest of the session with no
    way to recover short of restarting the game.
    """
    assert manifest.loaded_set("goliath") is None

    # The manifest is fixed on disk (the art swap writes a valid one).
    (broken_set / "manifest.toml").write_text(VALID_MANIFEST, encoding="utf-8")
    manifest.clear_loaded_cache()

    assert manifest.loaded_set("goliath") is not None, (
        "the cached FAILURE survived the invalidation hook: a manifest that "
        "gets fixed can never be picked up again"
    )


def test_the_manifest_cache_has_a_public_invalidation_hook(tmp_path: Path):
    """The cache needs a public way to be dropped.

    It holds a parsed manifest, so a test (or a runtime swap of the art)
    must be able to force the next read to go back to the file.
    """
    clear = getattr(manifest, "clear_loaded_cache", None)
    assert clear is not None, (
        "the manifest cache needs a public invalidation hook "
        "(src.anim.manifest.clear_loaded_cache)"
    )
    clear()  # must not raise


def test_clear_anchor_cache_drops_the_manifest_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """`clear_anchor_cache()` is the hook for a runtime swap of the art.

    It must drop the manifest cache too: the two caches hold the SAME
    file, and a stale `AnimSet` would keep serving the old clips after
    the swap.
    """
    from src.ui.scenes import clear_anchor_cache

    set_dir = tmp_path / "goliath"
    set_dir.mkdir()
    manifest_path = set_dir / "manifest.toml"
    manifest_path.write_text(VALID_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest, "_sets_root", lambda: tmp_path)

    first = manifest.loaded_set("goliath")
    assert first is not None
    assert "phase1_idle" in first.clips

    # The manifest changes on disk (the runtime swap of the art).
    manifest_path.write_text(SWAPPED_MANIFEST, encoding="utf-8")
    clear_anchor_cache()

    second = manifest.loaded_set("goliath")
    assert second is not None
    assert "swapped_id" in second.clips, (
        "the manifest cache was not dropped: the swap is invisible"
    )
