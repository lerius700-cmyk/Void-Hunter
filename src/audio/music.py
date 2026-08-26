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

    BLOQUE 58.14 v2: BOTH the original and the lowpass-filtered copy
    are loaded and played in parallel on separate channels, started
    at the same time so they stay in sync. The pause effect is just
    a volume swap (original → 0, filtered → 0.85) — the BGM never
    stops or restarts. At second 50 of pause, the user is still at
    second 50 of the song.

    BLOQUE 58.53: when `force=False` (default), the music is NOT
    restarted if the gameplay track is already the current track and
    the channel is still playing.
    """
    global _current_track, _bgm_channel, _original_sound, _filtered_sound
    global _filtered_channel
    if not _ensure_mixer():
        return False
    if not force and _current_track in ("gameplay", "gameplay_filtered"):
        if _bgm_channel is not None and _bgm_channel.get_busy():
            # Already playing and not paused — keep going.
            # But ensure the filtered is also playing (for the next pause)
            if (_filtered_sound is not None
                    and _filtered_channel is not None
                    and not _filtered_channel.get_busy()):
                _filtered_channel.play(_filtered_sound, loops=-1)
            return True
    # Load BOTH sounds (original + filtered)
    if not _load_both_sounds():
        return False
    # Allocate channels
    if _bgm_channel is None:
        _bgm_channel = pygame.mixer.Channel(2)  # 2 = BGM
    if _filtered_channel is None:
        _filtered_channel = pygame.mixer.Channel(3)  # 3 = filtered
    # Start BOTH at position 0, looping forever
    # Stop whatever was on those channels first
    try:
        _bgm_channel.stop()
    except pygame.error:
        pass
    try:
        _filtered_channel.stop()
    except pygame.error:
        pass
    # Start original at full volume
    ok1 = _play_on_channel(_original_sound, _bgm_channel, loops=loops, volume=_music_volume)
    # Start filtered at 0 volume (will be unmuted on pause)
    ok2 = _play_on_channel(_filtered_sound, _filtered_channel, loops=loops, volume=0.0)
    if ok1 and ok2:
        _current_track = "gameplay"
        _is_paused = False
        _diag_log(f"play_gameplay_music: started BOTH (force={force}, "
                  f"orig_vol={_music_volume}, filt_vol=0.0)")
        return True
    _diag_log(f"play_gameplay_music: FAILED (orig={ok1}, filt={ok2})")
    return False


# ---------------------------------------------------------------------------
# BLOQUE 58.14: pause-screen lowpass BGM (v2 - continuous playback)
# ---------------------------------------------------------------------------
# BOTH the original BGM and a pre-generated lowpass-filtered copy are
# loaded into RAM as Sound objects and played on SEPARATE channels
# (BGM channel 2 + filtered channel 3), started at the same time so
# they stay in sync (they have the same length and loop together).
#
# On pause: we just SWAP the channel volumes — original → 0.0, filtered
#   → 0.85. The BGM never stops, never restarts. At second 50 of pause
#   the user is still at second 50, just hearing it through the wall.
# On resume: reverse the swap.
#
# Memory cost: original (~165 MB RAM) + filtered (~64 MB) = ~229 MB
# always loaded. Acceptable for a PC game.
#
# This is the SECOND attempt — the v1 attempt (Channel.pause/unpause)
# was technically correct but had subtle issues; the user reported the
# BGM "stopping and starting" because the filtered copy started from 0
# (out of sync with the original). The continuous approach keeps both
# sounds in sync at all times.
import tempfile

_pause_filter_cache: dict[str, object] = {
    "enabled": True,
    "cutoff_hz": 600.0,
    "filtered_path": None,     # str | None
    "is_paused": False,
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
    """Set the lowpass cutoff Hz. Affects the NEXT time we load the
    filtered sound (or generate it if the cutoff changes)."""
    _pause_filter_cache["cutoff_hz"] = max(80.0, min(8000.0, hz))
    # Invalidate cached file (different cutoff = different file)
    _pause_filter_cache["filtered_path"] = None
    # Also drop the cached Sound so the next play regenerates it
    global _filtered_sound
    _filtered_sound = None
    # If the filtered channel is currently playing, stop it (the cached
    # Sound will be regenerated the next time the user pauses).
    if _filtered_channel is not None and _filtered_channel.get_busy():
        try:
            _filtered_channel.stop()
        except pygame.error:
            pass


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


def _load_both_sounds() -> bool:
    """Load BOTH the original and the filtered BGM as Sound objects.
    Both are needed so we can play them in parallel and stay in sync.
    Returns True on success."""
    global _original_sound, _filtered_sound
    src_path = _find_track(GAMEPLAY_TRACK)
    if src_path is None:
        return False
    # Load original
    if _original_sound is None or getattr(_original_sound, "_path", None) != str(src_path):
        _original_sound = _load_sound(src_path)
        if _original_sound is None:
            return False
        try:
            _original_sound._path = str(src_path)  # type: ignore[attr-defined]
        except Exception:
            pass
    # Load filtered (generate if missing)
    filtered_path = _ensure_filtered_bgm()
    if filtered_path is None:
        return False
    if _filtered_sound is None or getattr(_filtered_sound, "_path", None) != filtered_path:
        _filtered_sound = _load_sound(Path(filtered_path))
        if _filtered_sound is None:
            return False
        try:
            _filtered_sound._path = filtered_path  # type: ignore[attr-defined]
        except Exception:
            pass
    return True


def _start_both_channels() -> bool:
    """Start BOTH the original and the filtered BGM on their channels
    at the same time, in sync. Original is audible, filtered is silent."""
    global _bgm_channel, _filtered_channel
    if _original_sound is None or _filtered_sound is None:
        return False
    # Allocate channels (2 = BGM, 3 = filtered)
    if _bgm_channel is None:
        _bgm_channel = pygame.mixer.Channel(2)
    if _filtered_channel is None:
        _filtered_channel = pygame.mixer.Channel(3)
    # Stop whatever is currently on these channels
    for ch in (_bgm_channel, _filtered_channel):
        try:
            ch.stop()
        except pygame.error:
            pass
    # Start both at position 0, looping forever
    ok1 = _play_on_channel(_original_sound, _bgm_channel, loops=-1, volume=_music_volume)
    ok2 = _play_on_channel(_filtered_sound, _filtered_channel, loops=-1, volume=0.0)
    return ok1 and ok2


def enter_pause_lowpass() -> bool:
    """BLOQUE 58.14 v2: continuous-playback lowpass.

    The BGM NEVER stops. We just swap volumes so the user hears the
    filtered version. At second 50 of pause, the BGM is still at
    second 50 of the song — just muffled.
    """
    global _current_track, _is_paused
    _diag_log(f"enter_pause_lowpass: ENTER (track={_current_track}, paused={_is_paused}, "
              f"bgm_ch_busy={_bgm_channel.get_busy() if _bgm_channel else 'None'})")
    if not _ensure_mixer():
        _diag_log("enter_pause_lowpass: _ensure_mixer FAILED")
        return False
    if get_current_track() != "gameplay":
        _diag_log("enter_pause_lowpass: not in gameplay mode, no-op")
        return False
    if _bgm_channel is None or not _bgm_channel.get_busy():
        _diag_log("enter_pause_lowpass: BGM channel not busy, no-op")
        return False
    if _filtered_channel is None:
        _diag_log("enter_pause_lowpass: filtered channel not initialized, no-op")
        return False
    # Just swap the volumes. The filtered is already playing in sync
    # (started at the same time as the original), so we just unmute it
    # and mute the original.
    try:
        _bgm_channel.set_volume(0.0)
        _filtered_channel.set_volume(_music_volume * 0.85)
    except pygame.error as exc:
        _diag_log(f"enter_pause_lowpass: set_volume failed: {exc}")
        return False
    _is_paused = True
    _current_track = "gameplay_filtered"
    _pause_filter_cache["is_paused"] = True
    _diag_log("enter_pause_lowpass: OK (swapped volumes: orig=0, filt=0.85)")
    return True


def exit_pause_lowpass() -> bool:
    """BLOQUE 58.14 v2: continuous-playback lowpass resume.

    Inverse of enter: filtered → 0, original → 1.0. BGM continues
    from the EXACT same position because both sounds were always
    playing — we never stopped or restarted anything.
    """
    global _current_track, _is_paused
    _diag_log(f"exit_pause_lowpass: ENTER (track={_current_track}, paused={_is_paused})")
    if not _ensure_mixer():
        return False
    if not _is_paused:
        _diag_log("exit_pause_lowpass: not paused, no-op")
        return False
    try:
        if _filtered_channel is not None:
            _filtered_channel.set_volume(0.0)
        if _bgm_channel is not None:
            _bgm_channel.set_volume(_music_volume)
    except pygame.error as exc:
        _diag_log(f"exit_pause_lowpass: set_volume failed: {exc}")
        return False
    _is_paused = False
    _current_track = "gameplay"
    _pause_filter_cache["is_paused"] = False
    _diag_log("exit_pause_lowpass: OK (swapped volumes: orig=1.0, filt=0)")
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


# BLOQUE 58.59: Cinematic sting (procedural SFX) for the ship zoom video.
# Uses the existing AudioEngine to render `boss_warning` (a low sawtooth
# with a long ADSR release) and plays it on the voice channel. The sting
# is intentionally short (~0.8s) so it doesn't compete with the
# gameplay BGM that fades in once the cinematic finishes.
def play_cinematic_sting() -> bool:
    """Play a procedural sting at the start of the CINEMATIC scene.

    Best-effort: if the AudioEngine can't render, fails silently. The
    cinematic visual is the main attraction; the audio is juice.
    """
    try:
        from src.audio.synth import render_sfx
        import array
        # Reuse the existing boss_warning SFX (saw, 0.8s, impactful)
        samples = render_sfx("boss_warning")
        # Mix down to mono if stereo (the SFX renderer is mono, but be safe)
        if isinstance(samples, array.array):
            # Build a temporary WAV in RAM
            import struct
            import io
            import wave
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(44100)
                wf.writeframes(samples.tobytes())
            sound = pygame.mixer.Sound(tmp_path)
            channel = _ensure_voice_channel()
            if channel is None:
                return False
            channel.play(sound)
            return True
    except Exception as exc:
        _diag_log(f"play_cinematic_sting failed: {exc}")
        return False
    return False


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
