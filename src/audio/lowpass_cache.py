"""Where the pause-screen lowpass keeps its filtered track.

The filtered track is a CACHE: the game can rebuild it from the original
in a few seconds. It used to be written next to its source, which in the
onefile build is `_MEIPASS` -- a temporary directory wiped when the
process exits. The 8-second computation was paid on the first pause of
EVERY session, and a 61 MB copy of the result was bundled into the
binary so that nobody would pay it.

Now the cache lives in a directory next to the EXECUTABLE, so it
survives the process: the filter is computed once, and every later run
finds the result.

The directory is NOT called `Assets`. `_find_assets_dir()` returns the
first candidate that exists, and `<exe_dir>/Assets` is the first one --
a cache there would shadow the bundle's own assets and the original
gameplay track would vanish.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CACHE_DIR_NAME = "_vh_cache"
TRACK_STEM = "keep kept - Lerius - soundtrack gameplay"


def _base_dir() -> Path:
    """Where the executable lives, or the project root from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def cache_dir() -> Path | None:
    """The writable directory the filtered track is kept in.

    `None` when there is no writable place: the executable may sit in a
    read-only directory (Program Files). The caller falls back to
    writing next to the source, which works but does not persist.
    """
    candidate = _base_dir() / CACHE_DIR_NAME
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    if not os.access(candidate, os.W_OK):
        return None
    return candidate


def filtered_name(cutoff_hz: float) -> str:
    """The file name the filtered track has for this cutoff."""
    return f"{TRACK_STEM}_lp{int(cutoff_hz)}.wav"


def cached_filtered(cutoff_hz: float) -> Path | None:
    """The cached filtered track for this cutoff, if it is already there."""
    directory = cache_dir()
    if directory is None:
        return None
    path = directory / filtered_name(cutoff_hz)
    return path if path.is_file() else None


def store_filtered(src: Path, dst: Path, cutoff_hz: float) -> bool:
    """Filter `src` into `dst`.

    The result is generated to a temporary name and moved into place, so
    an interrupted run cannot leave a truncated WAV that the next run
    would happily reuse.
    """
    from src.audio.synth import apply_lowpass_to_wav

    tmp = dst.with_name(dst.stem + ".tmp.wav")
    try:
        if not apply_lowpass_to_wav(str(src), str(tmp), cutoff_hz=cutoff_hz):
            _unlink(tmp)
            return False
        os.replace(tmp, dst)
    except Exception:
        _unlink(tmp)
        return False
    return True


def _unlink(path: Path) -> None:
    """Remove a file, ignoring the failure."""
    try:
        path.unlink()
    except OSError:
        pass
