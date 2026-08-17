"""BLOQUE 58.45: WAV music loader with streaming.

The game's soundtrack (in `Assets/`) is provided as high-quality WAV files.
We use `pygame.mixer.music` which STREAMS the file from disk via SDL_mixer,
so the 165 MB of music doesn't load into RAM (vs. `mixer.Sound` which would).

Public API:
  - `play_title_music()`  — loop the title-screen track
  - `play_gameplay_music()` — loop the gameplay soundtrack
  - `stop_music()` — stop whatever is playing (and unload)
  - `get_current_track()` — "title" | "gameplay" | None (for debugging)

Path resolution (BLOQUE 58.45):
  - Development:  `D:\AI\void-hunter\Assets\*.wav`
  - PyInstaller: `<_MEIPASS>/Assets/*.wav` (bundled as data files)
  - We probe both so the same code works for `python main.py` and the .exe.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import pygame


# Track filenames (relative to Assets/)
TITLE_TRACK = "pantalla principal.wav"
# BLOQUE 58.51: actual file is "keep kept - Lerius - soundtrack gameplay.wav"
# (with the artist prefix). The old name was wrong, which is why music
# never played in the .exe even after the path fix.
GAMEPLAY_TRACK = "keep kept - Lerius - soundtrack gameplay.wav"

# Module-level state
_current_track: Optional[str] = None
# BLOQUE 58.55: bumped to 1.0 (max). At 0.7 users were reporting
# "no audio" — the Windows volume mixer per-app slider was likely
# reducing it further, or the BGM at 70% was below the ambient noise
# floor. BGM at 100% is the standard for arcade games.
_music_volume: float = 1.0


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
    # 1/2. PyInstaller sets sys._MEIPASS for the temp/onedir dir
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_p = Path(meipass)
        candidates.append(meipass_p / "Assets")
        candidates.append(meipass_p / "_internal" / "Assets")
    # 3. The directory containing the running script / frozen exe
    if getattr(sys, "frozen", False):
        # PyInstaller: sys.executable is the .exe
        exe_dir = Path(sys.executable).parent
    else:
        # Source: main.py is in the project root
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
    """Initialize pygame.mixer if not already. Returns False on failure."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        return True
    except pygame.error:
        return False


def _diag_log(msg: str) -> None:
    """Diagnostic helper (no-op in production; left in for debugging)."""
    pass


def play_title_music(loops: int = -1) -> bool:
    """Play the title-screen track on loop. Returns True on success."""
    global _current_track
    # BLOQUE 58.57: verbose diagnostic to logs/_audio_status.log so the
    # user can see EXACTLY which audio driver pygame picked + whether
    # the mixer is producing output. This is the file the user can
    # open after running the .exe to verify audio is working.
    try:
        import os as _os
        _os.makedirs("logs", exist_ok=True)
        with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
            _f.write(
                f"play_title_music() at {os.environ.get('SDL_AUDIODRIVER', '?')}\n"
            )
            _f.write(f"  mixer init: {pygame.mixer.get_init()}\n")
            _f.write(f"  music volume setting: {_music_volume}\n")
    except Exception:
        pass
    if not _ensure_mixer():
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write("  _ensure_mixer() FAILED\n")
        except Exception:
            pass
        return False
    path = _find_track(TITLE_TRACK)
    if path is None:
        try:
            with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
                _f.write(f"  path is None: '{TITLE_TRACK}' not found\n")
        except Exception:
            pass
        print(f"[music] WARN: '{TITLE_TRACK}' not found in Assets/")
        return False
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(loops=loops)
        _current_track = "title"
        # Verify it's actually playing
        import time
        time.sleep(0.1)
        busy = pygame.mixer.music.get_busy()
        vol = pygame.mixer.music.get_volume()
        with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
            _f.write(f"  path: {path}\n")
            _f.write(f"  music.play() OK, busy={busy}, vol={vol}\n")
        return True
    except pygame.error as exc:
        with open("logs/_audio_status.log", "a", encoding="utf-8") as _f:
            _f.write(f"  pygame.error: {exc}\n")
        print(f"[music] WARN: failed to load '{TITLE_TRACK}': {exc}")
        return False


def play_gameplay_music(loops: int = -1, force: bool = False) -> bool:
    """Play the gameplay soundtrack on loop. Returns True on success.

    BLOQUE 58.53: when `force=False` (default), the music is NOT
    restarted if the gameplay track is already the current track.
    This keeps the music playing continuously through the sub-boss
    warning (SUB_BOSS_INTRO -> Gameplay) without restarting from
    the beginning. Pass `force=True` for explicit reloads (e.g.
    after game over, act transition).
    """
    global _current_track
    if not _ensure_mixer():
        return False
    if not force and _current_track == "gameplay" and pygame.mixer.music.get_busy():
        # Already playing the gameplay track — let it keep going.
        return True
    path = _find_track(GAMEPLAY_TRACK)
    if path is None:
        print(f"[music] WARN: '{GAMEPLAY_TRACK}' not found in Assets/")
        return False
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(loops=loops)
        _current_track = "gameplay"
        return True
    except pygame.error as exc:
        print(f"[music] WARN: failed to load '{GAMEPLAY_TRACK}': {exc}")
        return False


# BLOQUE 58.53: voice clip playback (SAPI-generated "pantalla principal"
# etc. announcements). Uses a separate pygame.mixer.Channel so the BGM
# on Channel 0 keeps playing. Falls back gracefully if the file is
# missing.
_voice_channel: Optional[pygame.mixer.Channel] = None


def _ensure_voice_channel() -> Optional[pygame.mixer.Channel]:
    """Get a dedicated mixer channel for voice clips (1-shot, no loop)."""
    global _voice_channel
    if not _ensure_mixer():
        return None
    if _voice_channel is None:
        pygame.mixer.set_num_channels(8)  # BGM (reserved) + 7 SFX/voice
        _voice_channel = pygame.mixer.Channel(1)
    return _voice_channel


def play_voice_clip(filename: str, volume: float = 1.0) -> bool:
    """Play a short voice announcement (e.g. "pantalla principal").

    Files live in Assets/ next to the music tracks. Returns True on
    success. The clip is one-shot; the BGM (pygame.mixer.music) keeps
    playing on its own channel.
    """
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
    """Announce the title screen ('Pantalla principal' in Spanish)."""
    return play_voice_clip("voice_pantalla_principal.wav", volume=1.0)


def play_voice_gameplay() -> bool:
    """Announce gameplay start ('Gameplay' in Spanish)."""
    return play_voice_clip("voice_gameplay.wav", volume=1.0)


def play_voice_jefe() -> bool:
    """Announce the boss ('Jefe' in Spanish)."""
    return play_voice_clip("voice_jefe.wav", volume=1.0)


def play_voice_act_cleared() -> bool:
    """Announce act completion ('Acto completado' in Spanish)."""
    return play_voice_clip("voice_act_cleared.wav", volume=1.0)


def stop_music() -> None:
    """Stop whatever is currently playing and unload the stream."""
    global _current_track
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except pygame.error:
        pass
    _current_track = None


def get_current_track() -> Optional[str]:
    """Return 'title', 'gameplay', or None."""
    return _current_track


def set_volume(volume: float) -> None:
    """Set the music volume (0..1). Live-applied if music is playing."""
    global _music_volume
    _music_volume = max(0.0, min(1.0, volume))
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(_music_volume)
    except pygame.error:
        pass


def shutdown() -> None:
    """Tear down the mixer (call on app exit)."""
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except pygame.error:
        pass


# ---------------------------------------------------------------------------
# BLOQUE 58.14: pause-screen lowpass BGM
# ---------------------------------------------------------------------------
# When the player pauses, we want the gameplay BGM to KEEP playing but
# sound "muffled" (as if heard through a wall — "music in the next room").
#
# Pygame's mixer.music (streamed) does not support runtime filter effects.
# The cleanest way to do this is:
#   1. Pre-generate a lowpass-filtered copy of the BGM (numpy IIR filter)
#   2. On pause: stop the stream, play the filtered copy
#   3. On unpause: stop the filtered, resume the original
#
# The filtered copy is generated LAZILY on the first pause. We cache the
# file path so subsequent pauses are instant. The user pays the
# computation cost once (a few seconds) and gets instant filter switching
# thereafter. The user can override the cutoff via VOID_HUNTER_LP_HZ env
# var (default 600 Hz — bass + low-mids only, "behind a wall" feel).
import tempfile
import os

_pause_filter_cache: dict[str, object] = {
    "enabled": True,
    "cutoff_hz": 600.0,
    "filtered_path": None,     # str | None
    "pause_pos_ms": 0,         # playback position at pause time
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
    # Output to a stable cache path next to the source (so it survives
    # restarts within the same install — only generated once per cutoff).
    src_dir = os.path.dirname(str(src_path))
    cutoff = get_lowpass_cutoff_hz()
    suffix = f"_lp{int(cutoff)}.wav"
    out_path = os.path.join(src_dir, "keep kept - Lerius - soundtrack gameplay" + suffix)
    # Already exists from a previous run? Use it.
    if os.path.exists(out_path):
        _pause_filter_cache["filtered_path"] = out_path
        return out_path
    # Generate. Log start/finish to logs/_audio_status.log so the user
    # sees the progress (this takes a few seconds for a 165 MB file).
    try:
        import time
        log_path = os.path.join(os.getcwd(), "logs", "_audio_status.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        t0 = time.time()
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
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(f"[lowpass] FAILED: {exc}\n")
        except Exception:
            pass
        return None
    _pause_filter_cache["filtered_path"] = out_path
    return out_path


def enter_pause_lowpass() -> bool:
    """Switch from the live BGM stream to a lowpass-filtered copy.

    Records the current playback position so exit_pause_lowpass() can
    resume from where the user paused. Returns True if the filter was
    applied (filtered BGM is now playing), False if it fell back to
    no-filter mode (e.g., numpy not available or BGM not playing).
    """
    global _current_track
    if not _ensure_mixer():
        return False
    if get_current_track() != "gameplay":
        # Not in gameplay mode (e.g., already on title) — no-op.
        return False
    if not pygame.mixer.music.get_busy():
        return False
    # Record the current playback position so we can resume later.
    try:
        pos_ms = pygame.mixer.music.get_pos()
    except pygame.error:
        pos_ms = 0
    if pos_ms < 0:
        pos_ms = 0
    _pause_filter_cache["pause_pos_ms"] = pos_ms
    # Generate (or load cached) the filtered file.
    filtered_path = _ensure_filtered_bgm()
    if filtered_path is None:
        return False
    # Swap: stop original, play filtered.
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(filtered_path)
        # Slightly quieter (room-next-door).
        pygame.mixer.music.set_volume(_music_volume * 0.85)
        pygame.mixer.music.play(loops=-1)
        # Seek to the same position the original was at. If the file
        # is already in the "filtered" state, this is a no-op.
        try:
            pygame.mixer.music.set_pos(pos_ms / 1000.0)
        except pygame.error:
            pass
    except pygame.error:
        return False
    _pause_filter_cache["paused"] = True
    _current_track = "gameplay_filtered"
    return True


def exit_pause_lowpass() -> bool:
    """Switch back from the filtered BGM to the original gameplay BGM.

    Resumes the original at the position where the user paused. Returns
    True if the swap succeeded, False otherwise.
    """
    global _current_track
    if not _ensure_mixer():
        return False
    if not _pause_filter_cache.get("paused"):
        return False
    pos_ms = _pause_filter_cache.get("pause_pos_ms", 0) or 0
    src_path = _find_track(GAMEPLAY_TRACK)
    if src_path is None:
        return False
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(src_path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(loops=-1)
        try:
            pygame.mixer.music.set_pos(pos_ms / 1000.0)
        except pygame.error:
            pass
    except pygame.error:
        return False
    _current_track = "gameplay"
    _pause_filter_cache["paused"] = False
    return True
