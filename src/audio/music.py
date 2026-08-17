"""BLOQUE 58.45+58.14: WAV music loader.

The game's soundtrack (in `Assets/`) is provided as high-quality WAV files.

BLOQUE 58.14 redesign: we use `pygame.mixer.Sound` + `Channel` (loaded fully
in RAM) instead of `pygame.mixer.music` (streamed) for the gameplay track.
Why: the user wants the gameplay BGM to (a) be filtered via lowpass on pause
and (b) RESUME from the exact position it was at, not restart from 0.

- `pygame.mixer.music` (streamed) does NOT support `set_pos()` for WAV files
  (only MP3/OGG). So pausing it and resuming always restarts from 0.
- `pygame.mixer.Sound` loaded fully in RAM plays via a `Channel`, and the
  Channel supports `.pause()` and `.unpause()` which PRESERVE the playback
  position. This is the only way to get true position-preserving pause/
  resume for a 165MB WAV.

Memory cost: ~165MB for the gameplay WAV. Acceptable for a PC game.

Public API:
  - `play_title_music()`  — loop the title-screen track (uses Sound too)
  - `play_gameplay_music()` — loop the gameplay soundtrack
  - `enter_pause_lowpass()` — swap to a lowpass-filtered copy on a 2nd channel
  - `exit_pause_lowpass()`  — stop the filtered, unpause the original
  - `stop_music()` — stop everything
  - `get_current_track()` — "title" | "gameplay" | "gameplay_filtered" | None

Path resolution (BLOQUE 58.45):
  - Development:  `D:\AI\void-hunter\Assets\*.wav`
  - PyInstaller: `<_MEIPASS>/Assets/*.wav` (bundled as data files)
  - We probe both so the same code works for `python main.py` and the .exe.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

import pygame


# Track filenames (relative to Assets/)
TITLE_TRACK = "pantalla principal.wav"
# BLOQUE 58.51: actual file is "keep kept - Lerius - soundtrack gameplay.wav"
GAMEPLAY_TRACK = "keep kept - Lerius - soundtrack gameplay.wav"

# Module-level state
_current_track: Optional[str] = None
_music_volume: float = 1.0

# BLOQUE 58.14: Sound + Channel state. The BGM is loaded as a Sound (in
# RAM) and played on a dedicated channel. We keep separate Sounds for the
# original and the lowpass-filtered copy, and use Channel.pause() /
# Channel.unpause() to preserve playback position across the pause.
# NOTE: pygame requires the mixer to be init'd BEFORE Sound() can be
# constructed. We lazy-init everything in `ensure_mixer()`.
_bgm_channel: Optional["pygame.mixer.Channel"] = None
_filtered_channel: Optional["pygame.mixer.Channel"] = None
_original_sound: Optional["pygame.mixer.Sound"] = None
_filtered_sound: Optional["pygame.mixer.Sound"] = None
_is_paused: bool = False


def _find_assets_dir() -> Optional[Path]:
    """Return the directory containing the .wav files, or None.

    Tries (in order):
      1. `<exe_dir>/Assets/` (user-placed copy next to .exe)
      2. `<exe_dir>/_internal/Assets/` (PyInstaller onedir bundle)
      3. `<_MEIPASS>/Assets/` (PyInstaller onefile temp dir)
      4. `<_MEIPASS>/_internal/Assets/` (PyInstaller onedir temp dir)
      5. `<project_root>/Assets/` (running from source)
    """
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_p = Path(meipass)
        candidates.append(meipass_p / "Assets")
        candidates.append(meipass_p / "_internal" / "Assets")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent.parent
    candidates.append(exe_dir / "Assets")
    candidates.append(exe_dir / "_internal" / "Assets")
    candidates.append(exe_dir.parent / "Assets")
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _find_track(filename: str) -> Optional[Path]:
    """Locate a specific track file. Returns None if Assets/ is missing."""
    assets_dir = _find_assets_dir()
    if assets_dir is None:
        return None
    path = assets_dir / filename
    return path if path.is_file() else None


def _ensure_mixer() -> bool:
    """Initialize pygame.mixer if not already. Returns False on failure.

    BLOQUE 58.14: we need at least 2 channels (BGM + filtered overlay),
    so we set_num_channels(8) for headroom (SFX/voice use the rest).
    """
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
        return True
    except pygame.error:
        return False


def _load_sound(path: Path) -> Optional["pygame.mixer.Sound"]:
    """Load a WAV into a Sound (full RAM). Returns None on failure."""
    try:
        return pygame.mixer.Sound(str(path))
    except pygame.error as exc:
        print(f"[music] WARN: failed to load Sound from '{path}': {exc}")
        return None


def _diag_log(msg: str) -> None:
    """Append a line to logs/_audio_status.log (best-effort, never raises)."""
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
            _f.write(f"{msg}\n")
    except Exception:
        pass


def _play_on_channel(sound: "pygame.mixer.Sound", channel: "pygame.mixer.Channel",
                      loops: int = -1, volume: float = 1.0) -> bool:
    """Play a Sound on a Channel, with error handling."""
    try:
        channel.set_volume(volume)
        channel.play(sound, loops=loops)
        return True
    except pygame.error as exc:
        _diag_log(f"  channel.play() failed: {exc}")
        return False


def play_title_music(loops: int = -1) -> bool:
    """Play the title-screen track on loop. Returns True on success.

    BLOQUE 58.14: uses Sound + Channel for consistency with the gameplay
    track. The title track is small (~10MB) so the RAM cost is trivial.
    """
    global _current_track, _bgm_channel
    if not _ensure_mixer():
        _diag_log("play_title_music: _ensure_mixer FAILED")
        return False
    path = _find_track(TITLE_TRACK)
    if path is None:
        print(f"[music] WARN: '{TITLE_TRACK}' not found in Assets/")
        return False
    # Stop anything currently playing on the BGM channel
    if _bgm_channel is None:
        _bgm_channel = pygame.mixer.Channel(2)  # 2 = BGM
    try:
        _bgm_channel.stop()
    except pygame.error:
        pass
    sound = _load_sound(path)
    if sound is None:
        return False
    ok = _play_on_channel(sound, _bgm_channel, loops=loops, volume=_music_volume)
    if ok:
        _current_track = "title"
        _is_paused = False
    return ok


def play_gameplay_music(loops: int = -1, force: bool = False) -> bool:
    """Play the gameplay soundtrack on loop. Returns True on success.

    BLOQUE 58.53: when `force=False` (default), the music is NOT
    restarted if the gameplay track is already the current track and
    the channel is still playing. This keeps the music playing
    continuously through scene transitions (sub-boss, boss intro) and
    through the pause overlay.

    BLOQUE 58.14: pause/resume uses Channel.pause()/unpause() to preserve
    the EXACT playback position. So the user's "music restarts on resume"
    bug is fixed at the source.
    """
    global _current_track, _bgm_channel, _original_sound
    if not _ensure_mixer():
        return False
    if not force and _current_track in ("gameplay", "gameplay_filtered"):
        if _bgm_channel is not None and not _is_paused:
            # Already playing and not paused — keep going.
            return True
    path = _find_track(GAMEPLAY_TRACK)
    if path is None:
        print(f"[music] WARN: '{GAMEPLAY_TRACK}' not found in Assets/")
        return False
    # Allocate the BGM channel
    if _bgm_channel is None:
        _bgm_channel = pygame.mixer.Channel(2)  # 2 = BGM
    try:
        _bgm_channel.stop()
    except pygame.error:
        pass
    # Cache the Sound so we don't reload the 165MB WAV on every call.
    if _original_sound is None or getattr(_original_sound, "_path", None) != str(path):
        sound = _load_sound(path)
        if sound is None:
            return False
        _original_sound = sound
        try:
            _original_sound._path = str(path)  # type: ignore[attr-defined]
        except Exception:
            pass
    ok = _play_on_channel(_original_sound, _bgm_channel, loops=loops, volume=_music_volume)
    if ok:
        _current_track = "gameplay"
        _is_paused = False
        _diag_log(f"play_gameplay_music: started (force={force})")
    return ok


# ---------------------------------------------------------------------------
# BLOQUE 58.14: pause-screen lowpass BGM
# ---------------------------------------------------------------------------
# On pause, the BGM keeps playing but the user hears a lowpass-filtered
# version (muffled, "music in the next room" feel). On resume, the
# filter stops and the original BGM unpauses from the exact saved
# position.
#
# Implementation:
#   1. We PAUSE the original BGM channel (preserves position).
#   2. We play the filtered WAV on a SEPARATE channel at low volume.
#      The filtered file is pre-generated lazily on first pause and
#      cached on disk.
#   3. On resume, we stop the filtered channel and unpause the original.
#
# Key property: the original BGM position is preserved via Channel.pause()
# which (unlike pygame.mixer.music.set_pos) works for ANY format, including
# the 165MB WAV the user has.
import tempfile

_pause_filter_cache: dict[str, object] = {
    "enabled": True,
    "cutoff_hz": 600.0,
    "filtered_path": None,     # str | None
    "paused": False,
}


def get_lowpass_cutoff_hz() -> float:
    """Return the current lowpass cutoff Hz (overridable via env var)."""
    override = os.environ.get("VOID_HUNTER_LP_HZ", "").strip()
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    return _pause_filter_cache["cutoff_hz"]  # type: ignore[return-value]


def set_lowpass_cutoff_hz(hz: float) -> None:
    """Set the lowpass cutoff Hz. Affects the NEXT pause."""
    _pause_filter_cache["cutoff_hz"] = max(80.0, min(8000.0, hz))
    # Invalidate cached file (different cutoff = different file)
    _pause_filter_cache["filtered_path"] = None
    # Also drop the cached Sound so the next pause regenerates it
    global _filtered_sound
    _filtered_sound = None


def _ensure_filtered_bgm() -> Optional[str]:
    """Generate (or load cached) lowpass-filtered version of the gameplay BGM.

    Returns the path to the filtered WAV, or None on failure.
    """
    if not _pause_filter_cache["enabled"]:
        return None
    cached = _pause_filter_cache.get("filtered_path")
    if isinstance(cached, str) and os.path.exists(cached):
        return cached
    src_path = _find_track(GAMEPLAY_TRACK)
    if src_path is None:
        return None
    # Output to a stable cache path next to the source.
    src_dir = os.path.dirname(str(src_path))
    cutoff = get_lowpass_cutoff_hz()
    suffix = f"_lp{int(cutoff)}.wav"
    out_path = os.path.join(src_dir, "keep kept - Lerius - soundtrack gameplay" + suffix)
    if os.path.exists(out_path):
        _pause_filter_cache["filtered_path"] = out_path
        return out_path
    # Generate. Log progress.
    try:
        t0 = time.time()
        log_path = os.path.join(os.getcwd(), "logs", "_audio_status.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as _f:
            _f.write(f"[lowpass] generating filtered BGM at {cutoff:.0f}Hz...\n")
        from src.audio.synth import apply_lowpass_to_wav
        ok = apply_lowpass_to_wav(str(src_path), out_path, cutoff_hz=cutoff)
        dt = time.time() - t0
        with open(log_path, "a", encoding="utf-8") as _f:
            _f.write(f"[lowpass] done ({dt:.1f}s) -> {out_path} ok={ok}\n")
        if not ok:
            return None
    except Exception as exc:
        try:
            with open(os.path.join(os.getcwd(), "logs", "_audio_status.log"),
                      "a", encoding="utf-8") as _f:
                _f.write(f"[lowpass] FAILED: {exc}\n")
        except Exception:
            pass
        return None
    _pause_filter_cache["filtered_path"] = out_path
    return out_path


def enter_pause_lowpass() -> bool:
    """Switch from the live BGM to a lowpass-filtered copy.

    Implementation:
      1. PAUSE the original BGM channel (preserves position).
      2. Play the filtered WAV on a separate channel at low volume.
    Returns True if the filter was applied, False otherwise.
    """
    global _current_track, _filtered_channel, _filtered_sound, _is_paused
    if not _ensure_mixer():
        _diag_log("enter_pause_lowpass: _ensure_mixer FAILED")
        return False
    if get_current_track() != "gameplay":
        # Not in gameplay mode (e.g., already on title) — no-op.
        _diag_log("enter_pause_lowpass: not in gameplay mode, no-op")
        return False
    if _bgm_channel is None or not _bgm_channel.get_busy():
        _diag_log("enter_pause_lowpass: BGM channel not busy, no-op")
        return False
    # Generate (or load cached) the filtered file.
    filtered_path = _ensure_filtered_bgm()
    if filtered_path is None:
        _diag_log("enter_pause_lowpass: no filtered file available, falling back")
        return False
    # Allocate the filtered channel if needed
    if _filtered_channel is None:
        _filtered_channel = pygame.mixer.Channel(3)  # 3 = filtered overlay
    # Load the filtered Sound if not already cached
    if _filtered_sound is None or getattr(_filtered_sound, "_path", None) != filtered_path:
        _filtered_sound = _load_sound(Path(filtered_path))
        if _filtered_sound is None:
            _diag_log("enter_pause_lowpass: failed to load filtered Sound")
            return False
        try:
            _filtered_sound._path = filtered_path  # type: ignore[attr-defined]
        except Exception:
            pass
    # PAUSE the original BGM (preserves position)
    try:
        _bgm_channel.pause()
    except pygame.error as exc:
        _diag_log(f"enter_pause_lowpass: pause() failed: {exc}")
        return False
    # Play the filtered version at low volume (room-next-door)
    try:
        _filtered_channel.set_volume(_music_volume * 0.85)
        _filtered_channel.play(_filtered_sound, loops=-1)
    except pygame.error as exc:
        # If filtered play failed, unpause the original so the user
        # doesn't lose audio entirely.
        try:
            _bgm_channel.unpause()
        except pygame.error:
            pass
        _diag_log(f"enter_pause_lowpass: filtered play() failed: {exc}")
        return False
    _is_paused = True
    _current_track = "gameplay_filtered"
    _pause_filter_cache["paused"] = True
    _diag_log("enter_pause_lowpass: OK (paused original, playing filtered)")
    return True


def exit_pause_lowpass() -> bool:
    """Stop the filtered overlay and unpause the original BGM (preserving position)."""
    global _current_track, _is_paused
    if not _ensure_mixer():
        return False
    if not _is_paused:
        return False
    # Stop the filtered overlay
    if _filtered_channel is not None:
        try:
            _filtered_channel.stop()
        except pygame.error:
            pass
    # Unpause the original BGM (preserves the position it was at when we paused)
    if _bgm_channel is not None:
        try:
            _bgm_channel.unpause()
        except pygame.error as exc:
            _diag_log(f"exit_pause_lowpass: unpause() failed: {exc}")
            return False
    _is_paused = False
    _current_track = "gameplay"
    _pause_filter_cache["paused"] = False
    _diag_log("exit_pause_lowpass: OK (stopped filtered, unpaused original)")
    return True


# ---------------------------------------------------------------------------
# Voice clip + other helpers (unchanged from BLOQUE 58.53)
# ---------------------------------------------------------------------------
_voice_channel: Optional[pygame.mixer.Channel] = None


def _ensure_voice_channel() -> Optional[pygame.mixer.Channel]:
    global _voice_channel
    if not _ensure_mixer():
        return None
    if _voice_channel is None:
        _voice_channel = pygame.mixer.Channel(1)
    return _voice_channel


def play_voice_clip(filename: str, volume: float = 1.0) -> bool:
    path = _find_track(filename)
    if path is None:
        return False
    try:
        sound = pygame.mixer.Sound(str(path))
        sound.set_volume(volume)
        channel = _ensure_voice_channel()
        if channel is None:
            return False
        channel.play(sound)
        return True
    except pygame.error as exc:
        print(f"[voice] WARN: failed to play '{filename}': {exc}")
        return False


def play_voice_pantalla_principal() -> bool:
    return play_voice_clip("voice_pantalla_principal.wav", volume=1.0)


def play_voice_gameplay() -> bool:
    return play_voice_clip("voice_gameplay.wav", volume=1.0)


def play_voice_jefe() -> bool:
    return play_voice_clip("voice_jefe.wav", volume=1.0)


def play_voice_act_cleared() -> bool:
    return play_voice_clip("voice_act_cleared.wav", volume=1.0)


def stop_music() -> None:
    """Stop everything (BGM + filtered overlay)."""
    global _current_track, _is_paused
    try:
        if _bgm_channel is not None:
            _bgm_channel.stop()
        if _filtered_channel is not None:
            _filtered_channel.stop()
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except pygame.error:
        pass
    _current_track = None
    _is_paused = False


def get_current_track() -> Optional[str]:
    return _current_track


def set_volume(volume: float) -> None:
    global _music_volume
    _music_volume = max(0.0, min(1.0, volume))
    # Live-apply to whichever channel is playing
    try:
        if pygame.mixer.get_init():
            if _bgm_channel is not None and _bgm_channel.get_busy() and not _is_paused:
                _bgm_channel.set_volume(_music_volume)
            if _filtered_channel is not None and _filtered_channel.get_busy():
                _filtered_channel.set_volume(_music_volume * 0.85)
            pygame.mixer.music.set_volume(_music_volume)
    except pygame.error:
        pass


def shutdown() -> None:
    try:
        if pygame.mixer.get_init():
            if _bgm_channel is not None:
                _bgm_channel.stop()
            if _filtered_channel is not None:
                _filtered_channel.stop()
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except pygame.error:
        pass
