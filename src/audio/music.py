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
_music_volume: float = 0.7  # 0..1, headroom for SFX


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
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        return True
    except pygame.error:
        return False


def _diag_log(msg: str) -> None:
    """Diagnostic helper (no-op in production; left in for debugging)."""
    pass


def play_title_music(loops: int = -1) -> bool:
    """Play the title-screen track on loop. Returns True on success."""
    global _current_track
    if not _ensure_mixer():
        return False
    path = _find_track(TITLE_TRACK)
    if path is None:
        print(f"[music] WARN: '{TITLE_TRACK}' not found in Assets/")
        return False
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(_music_volume)
        pygame.mixer.music.play(loops=loops)
        _current_track = "title"
        return True
    except pygame.error as exc:
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
        print(f"[music] WARN: failed to load '{GAMEPLAY_TRACK}': {exc}")
        return False


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
