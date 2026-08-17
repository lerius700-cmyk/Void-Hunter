"""Diagnose: does Channel.unpause() actually preserve position for a Sound?

This is the core mechanic BLOQUE 58.14 v1.2 depends on. If this fails,
no amount of code-level fix will help — we need a different approach.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

import pygame
import array


def make_test_wav(path: str, duration_s: float = 2.0) -> None:
    """Generate a 2s tone so we can hear/see distinct positions."""
    sr = 44100
    n = int(sr * duration_s)
    samples = array.array("h")
    for i in range(n):
        # 440 Hz tone with envelope
        t = i / sr
        env = math.sin(2 * math.pi * t / duration_s)  # fade in/out
        v = int(20000 * env * math.sin(2 * math.pi * 440 * t))
        samples.append(v)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())


def main() -> int:
    print("SDL_AUDIODRIVER =", os.environ.get("SDL_AUDIODRIVER", "default"))
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(8)

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "tone.wav")
        make_test_wav(wav_path, duration_s=2.0)
        sound = pygame.mixer.Sound(wav_path)
        channel = pygame.mixer.Channel(2)
        print(f"Sound length: {sound.get_length():.3f}s")

        # Play
        channel.play(sound, loops=-1)
        print("Playing...")
        time.sleep(0.8)  # let it play for 0.8s

        # Pause
        channel.pause()
        print(f"After pause: get_busy()={channel.get_busy()}")
        # Wait a bit
        time.sleep(0.3)

        # Unpause and check if the position is roughly where it was
        # (we slept 0.3s while paused, so the position should NOT have advanced)
        channel.unpause()
        print(f"After unpause: get_busy()={channel.get_busy()}")
        # We can't easily get the playback position from a Sound on a
        # Channel, but we can verify by re-pausing and unpausing
        time.sleep(0.5)
        channel.pause()
        time.sleep(0.2)
        # Position should still be around 0.8s + 0.5s = 1.3s into the loop,
        # not 0.8 + 0.5 + 0.2 = 1.5s (which would happen if pause leaked)
        channel.unpause()
        time.sleep(0.5)
        channel.stop()
        print("Done. If you heard the tone resume from where it stopped")
        print("(not restart from 0 each time), then the unpause() works.")
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
