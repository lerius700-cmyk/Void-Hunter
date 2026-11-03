"""The pause lowpass must keep its filtered track BETWEEN runs.

The filtered track used to be written next to its source, which in the
onefile build is `_MEIPASS` -- a temporary directory wiped when the
process exits. The 8-second computation was therefore paid on the first
pause of EVERY session, which is why a 61 MB copy of the result was
bundled into the binary instead.

Two things have to hold:

* the cache lives next to the EXECUTABLE, so it survives the process;
* it does NOT live in a directory called `Assets`, because
  `_find_assets_dir()` probes `<exe_dir>/Assets` FIRST and a cache there
  would shadow the bundle's own assets and break the original music.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.audio import lowpass_cache  # noqa: E402


@pytest.fixture
def fake_exe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Pretend to be a frozen onefile executable in a temporary folder."""
    exe = tmp_path / "void-hunter.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    return tmp_path


def test_the_cache_lives_next_to_the_executable(fake_exe: Path):
    """The cache directory is a sibling of the executable."""
    directory = lowpass_cache.ensure_cache_dir()
    assert directory is not None
    assert directory.parent == fake_exe
    assert directory.name == lowpass_cache.CACHE_DIR_NAME


def test_asking_for_the_cache_does_not_create_it(fake_exe: Path):
    """A query does not litter the folder next to the executable.

    `cache_dir()` answers "is there a cache directory, and can I write
    to it". `ensure_cache_dir()` is the one that creates it, and it is
    called only when a track is about to be written.
    """
    assert lowpass_cache.cache_dir() is None, (
        "the cache directory already existed"
    )
    assert not (fake_exe / lowpass_cache.CACHE_DIR_NAME).exists(), (
        "asking for the cache created the directory: a query must not "
        "leave a folder next to the executable"
    )


def test_the_cache_is_not_called_assets(fake_exe: Path):
    """The cache must not be able to shadow the assets directory."""
    directory = lowpass_cache.ensure_cache_dir()
    assert directory is not None
    assert directory.name.lower() != "assets"


def test_the_cache_does_not_shadow_the_bundle_assets(fake_exe: Path):
    """With both present, the assets directory is still the bundle's.

    `_find_assets_dir()` returns the FIRST candidate that exists, and
    `<exe_dir>/Assets` comes before the cache. A cache placed inside a
    directory called `Assets` would become the assets directory, and the
    original gameplay track would vanish.
    """
    bundle_assets = fake_exe / "Assets"
    bundle_assets.mkdir()
    (bundle_assets / "keep kept - Lerius - soundtrack gameplay.wav").write_bytes(
        b"RIFF"
    )
    lowpass_cache.cache_dir()  # the cache, next to the executable

    from src.audio.music import GAMEPLAY_TRACK, _find_assets_dir, _find_track

    assets = _find_assets_dir()
    assert assets is not None
    assert assets == bundle_assets
    assert _find_track(GAMEPLAY_TRACK) is not None


def test_the_cached_track_is_found_and_reused(fake_exe: Path, monkeypatch):
    """A cached file is returned as-is; nothing is regenerated."""
    calls: list[str] = []
    monkeypatch.setattr(
        lowpass_cache,
        "store_filtered",
        lambda src, dst, cutoff: calls.append(str(dst)) or True,
    )
    directory = lowpass_cache.ensure_cache_dir()
    assert directory is not None
    target = directory / lowpass_cache.filtered_name(600.0)
    target.write_bytes(b"RIFFfake")

    found = lowpass_cache.cached_filtered(600.0)
    assert found is not None
    assert found == target
    assert calls == []


def test_store_filtered_writes_atomically(fake_exe: Path, tmp_path: Path):
    """The file is generated to a temporary name and moved into place."""
    src = tmp_path / "src.wav"
    src.write_bytes(b"RIFF")
    directory = lowpass_cache.ensure_cache_dir()
    assert directory is not None
    dst = directory / "out.wav"

    def fake_filter(
        input_path: str,
        output_path: str,
        cutoff_hz: float = 600.0,
        sample_rate: int = 44100,
    ) -> bool:
        Path(output_path).write_bytes(b"RIFFgenerated")
        return True

    import src.audio.synth as synth

    original = synth.apply_lowpass_to_wav
    synth.apply_lowpass_to_wav = fake_filter  # type: ignore[assignment]
    try:
        ok = lowpass_cache.store_filtered(src, dst, 600.0)
    finally:
        synth.apply_lowpass_to_wav = original  # type: ignore[assignment]

    assert ok
    assert dst.read_bytes() == b"RIFFgenerated"
    # No temporary file is left behind.
    leftovers = [p.name for p in directory.iterdir() if p.name != "out.wav"]
    assert leftovers == []


def test_store_filtered_leaves_nothing_behind_on_failure(
    fake_exe: Path, tmp_path: Path
):
    """A failed filter does not leave a half-written file."""
    src = tmp_path / "src.wav"
    src.write_bytes(b"RIFF")
    directory = lowpass_cache.ensure_cache_dir()
    assert directory is not None
    dst = directory / "out.wav"

    def failing(
        input_path: str,
        output_path: str,
        cutoff_hz: float = 600.0,
        sample_rate: int = 44100,
    ) -> bool:
        Path(output_path).write_bytes(b"RIFFtrunc")
        return False

    import src.audio.synth as synth

    original = synth.apply_lowpass_to_wav
    synth.apply_lowpass_to_wav = failing  # type: ignore[assignment]
    try:
        ok = lowpass_cache.store_filtered(src, dst, 600.0)
    finally:
        synth.apply_lowpass_to_wav = original  # type: ignore[assignment]

    assert not ok
    assert not dst.exists()
    assert [p.name for p in directory.iterdir()] == []
