"""Debug: why does apply_lowpass_to_wav return False for the real BGM?"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import wave
import numpy as np
from src.audio.music import _find_track, GAMEPLAY_TRACK

path = _find_track(GAMEPLAY_TRACK)
print(f"Path: {path}")

# Open and inspect
with wave.open(str(path), "rb") as wf:
    n_channels = wf.getnchannels()
    sample_width = wf.getsampwidth()
    n_frames = wf.getnframes()
    src_rate = wf.getframerate()
    print(f"channels={n_channels}, sample_width={sample_width}, frames={n_frames}, rate={src_rate}")
    print(f"size on disk: {path.stat().st_size}")
    print(f"raw size: {n_frames * sample_width * n_channels} bytes")
    if sample_width != 2:
        print("SAMPLE WIDTH != 2 - this is why it returns False!")

# Try the actual function with timing
from src.audio.synth import apply_lowpass_to_wav
out_path = str(path) + "_lp600_test.wav"
if os.path.exists(out_path):
    os.remove(out_path)
t0 = time.time()
ok = apply_lowpass_to_wav(str(path), out_path, cutoff_hz=600.0)
dt = time.time() - t0
print(f"\napply_lowpass_to_wav: ok={ok}, time={dt:.1f}s")
print(f"output file exists: {os.path.exists(out_path)}")
if os.path.exists(out_path):
    print(f"output size: {os.path.getsize(out_path)}")
