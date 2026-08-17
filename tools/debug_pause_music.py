"""Manually exercise the pause flow in-process to see the diagnostic log."""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Use dummy audio so we don't need real hardware
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# Clear the log so we see only this run
log_path = "logs/_audio_status.log"
try:
    os.remove(log_path)
except FileNotFoundError:
    pass

import pygame
pygame.init()
# Force mixer init with channels
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.set_num_channels(8)

from src.audio import music
from src.audio.music import GAMEPLAY_TRACK
import wave

# Check we can find the BGM
from src.audio.music import _find_track
path = _find_track(GAMEPLAY_TRACK)
print(f"BGM path: {path}")
if path is None:
    print("ERROR: BGM not found, aborting")
    sys.exit(1)

# Open it briefly to see properties
with wave.open(str(path), "rb") as wf:
    print(f"  channels: {wf.getnchannels()}, rate: {wf.getframerate()}, frames: {wf.getnframes()}")

# Step 1: Start the gameplay music
print("\n[step 1] play_gameplay_music()")
ok = music.play_gameplay_music()
print(f"  result: {ok}, track: {music.get_current_track()}")
print(f"  BGM channel: {music._bgm_channel}")
if music._bgm_channel:
    print(f"  BGM busy: {music._bgm_channel.get_busy()}")
time.sleep(1.0)
if music._bgm_channel:
    print(f"  BGM busy after 1s: {music._bgm_channel.get_busy()}")

# Step 2: Enter pause
print("\n[step 2] enter_pause_lowpass()")
ok = music.enter_pause_lowpass()
print(f"  result: {ok}, _is_paused: {music._is_paused}, track: {music.get_current_track()}")
time.sleep(2.0)

# Step 3: Exit pause
print("\n[step 3] exit_pause_lowpass()")
ok = music.exit_pause_lowpass()
print(f"  result: {ok}, _is_paused: {music._is_paused}, track: {music.get_current_track()}")
if music._bgm_channel:
    print(f"  BGM busy after exit: {music._bgm_channel.get_busy()}")
time.sleep(1.0)

print("\n--- Audio diagnostic log ---")
try:
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            print(line.rstrip())
except FileNotFoundError:
    print("(no log file)")
