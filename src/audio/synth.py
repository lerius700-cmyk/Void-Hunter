"""Procedural 8-bit audio synth — 24 SFX + 4 BGM with ADSR.

Per GDD §9:
  - 16 channels pygame.mixer @ 44100 Hz, 16-bit PCM raw via array.array
  - Null-safe: if mixer fails, all SFX/BGM are no-op
  - ADSR: A 0.005-0.05s, D 0.05-0.2s, S 0.0-0.7, R 0.1-0.6s
  - Voices: square, triangle, saw, noise
  - 4 BGM: title (idle pad), act_normal (chase), boss_fight (intense),
    credits (resolution) — A-B sections, 30-45s loops

Pure stdlib (array + math + random) per GDD §0 — no numpy/scipy.
"""
from __future__ import annotations

import array
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pygame

from src.core.settings import (
    MIXER_BUFFER,
    MIXER_CHANNELS,
    MIXER_SAMPLE_RATE,
)


# Type alias for audio buffers (16-bit signed PCM mono)
AudioBuffer = array.array


# ---------------------------------------------------------------------------
# Voice / waveform helpers
# ---------------------------------------------------------------------------
class Voice(Enum):
    SQUARE = "square"
    TRIANGLE = "triangle"
    SAW = "saw"
    NOISE = "noise"


def square_wave(t: float, freq: float) -> float:
    """Square wave in [-1, 1]."""
    phase = (t * freq) % 1.0
    return 1.0 if phase < 0.5 else -1.0


def triangle_wave(t: float, freq: float) -> float:
    """Triangle wave in [-1, 1]."""
    phase = (t * freq) % 1.0
    return 4.0 * abs(phase - 0.5) - 1.0


def saw_wave(t: float, freq: float) -> float:
    """Sawtooth wave in [-1, 1]."""
    phase = (t * freq) % 1.0
    return 2.0 * phase - 1.0


def noise_wave(t: float, freq: float, rng: random.Random) -> float:
    """Pseudo-random white noise."""
    return rng.uniform(-1.0, 1.0)


_VOICE_FUNCS = {
    Voice.SQUARE: square_wave,
    Voice.TRIANGLE: triangle_wave,
    Voice.SAW: saw_wave,
}


def adsr_envelope(
    t: float,
    duration: float,
    attack: float = 0.01,
    decay: float = 0.1,
    sustain: float = 0.5,
    release: float = 0.2,
) -> float:
    """Standard ADSR envelope. Returns amplitude multiplier in [0, 1].

    Edge cases:
      - duration <= 0: returns 0
      - t <= 0: returns 0
      - t >= duration: returns 0
    """
    if duration <= 0.0 or t <= 0.0 or t >= duration:
        return 0.0
    if t < attack:
        return t / attack
    if t < attack + decay:
        return 1.0 - (1.0 - sustain) * ((t - attack) / decay)
    release_start = duration - release
    if t < release_start:
        return sustain
    return sustain * (1.0 - (t - release_start) / release)


# ---------------------------------------------------------------------------
# SFX catalog (24 entries per GDD §9)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _SfxSpec:
    name: str
    voice: Voice
    freq_hz: float
    slide_hz_per_s: float
    attack_s: float
    decay_s: float
    sustain: float
    release_s: float
    duration_s: float
    use_case: str
    volume: float = 0.5


SFX_CATALOG: dict[str, _SfxSpec] = {
    "shoot":                  _SfxSpec("shoot", Voice.SQUARE, 880, 0,    0.005, 0.05, 0.0, 0.05, 0.10, "Bullet fired L1", 0.4),
    "shoot_charged":          _SfxSpec("shoot_charged", Voice.SQUARE, 1320, 200, 0.005, 0.10, 0.0, 0.10, 0.20, "Charged bullet fire", 0.6),
    "hit":                    _SfxSpec("hit", Voice.NOISE, 0, 0, 0.002, 0.04, 0.0, 0.04, 0.08, "Player hit", 0.7),
    "explode_small":          _SfxSpec("explode_small", Voice.NOISE, 200, -100, 0.002, 0.10, 0.1, 0.20, 0.30, "Scout/Cruiser death", 0.6),
    "explode_medium":         _SfxSpec("explode_medium", Voice.NOISE, 150, -80, 0.002, 0.15, 0.1, 0.30, 0.45, "Heavy/Drone death", 0.7),
    "explode_boss":           _SfxSpec("explode_boss", Voice.NOISE, 100, -50, 0.005, 0.30, 0.2, 0.80, 1.10, "Boss death finale", 1.0),
    "bomb":                   _SfxSpec("bomb", Voice.SAW, 80, -40, 0.002, 0.20, 0.3, 0.40, 0.60, "Bomb triggered", 0.9),
    "powerup":                _SfxSpec("powerup", Voice.TRIANGLE, 660, 440, 0.005, 0.05, 0.4, 0.20, 0.25, "Power-up collected", 0.5),
    "dash":                   _SfxSpec("dash", Voice.NOISE, 2000, -3000, 0.005, 0.05, 0.0, 0.10, 0.15, "Dash whoosh", 0.4),
    "multiplier_up":          _SfxSpec("multiplier_up", Voice.SQUARE, 880, 0, 0.005, 0.02, 0.0, 0.10, 0.13, "Multiplier increase", 0.5),
    "boss_warning":           _SfxSpec("boss_warning", Voice.SAW, 80, 0, 0.010, 0.30, 0.5, 0.50, 0.80, "Boss intro stinger", 0.9),
    "boss_phase_change":      _SfxSpec("boss_phase_change", Voice.SAW, 200, -100, 0.005, 0.20, 0.3, 0.60, 0.80, "Phase transition", 1.0),
    "wave_cleared":           _SfxSpec("wave_cleared", Voice.TRIANGLE, 1320, 0, 0.005, 0.10, 0.0, 0.30, 0.40, "Wave complete", 0.6),
    "act_clear":              _SfxSpec("act_clear", Voice.TRIANGLE, 440, 200, 0.010, 0.20, 0.5, 0.60, 0.80, "Act boss defeated", 0.8),
    "game_over":              _SfxSpec("game_over", Voice.SAW, 440, -200, 0.020, 0.40, 0.3, 1.20, 1.60, "Game over sting", 0.9),
    "victory":                _SfxSpec("victory", Voice.TRIANGLE, 440, 300, 0.020, 0.30, 0.7, 1.50, 1.80, "Victory sting", 1.0),
    "ui_click":               _SfxSpec("ui_click", Voice.SQUARE, 1200, 0, 0.002, 0.02, 0.0, 0.05, 0.07, "UI confirm", 0.3),
    "ui_hover":               _SfxSpec("ui_hover", Voice.TRIANGLE, 1500, 0, 0.002, 0.02, 0.0, 0.05, 0.07, "UI hover", 0.2),
    "charge_loop":            _SfxSpec("charge_loop", Voice.SQUARE, 220, 200, 0.050, 0.05, 0.7, 0.10, 0.20, "Charge holding L1->L3", 0.4),
    "beam_charge":            _SfxSpec("beam_charge", Voice.NOISE, 100, 700, 0.100, 0.20, 0.5, 0.10, 0.30, "Beam windup", 0.6),
    "beam_fire":              _SfxSpec("beam_fire", Voice.SAW, 800, 0, 0.005, 0.30, 0.0, 0.10, 0.40, "Beam release", 0.7),
    # BLOQUE 37: long sustained sawtooth that reads as a held laser (piiiiIIII),
    # not as discrete shots. Long sustain so the sound feels continuous while
    # the visual laser is on screen.
    "laser_continuous":       _SfxSpec("laser_continuous", Voice.SAW, 720, 60, 0.020, 0.05, 0.65, 0.30, 0.50, "L3 continuous laser", 0.55),
    "laser_end":              _SfxSpec("laser_end", Voice.SAW, 720, -400, 0.005, 0.05, 0.0, 0.10, 0.20, "L3 laser release tail", 0.35),
    "missile_lock":           _SfxSpec("missile_lock", Voice.SQUARE, 2000, 0, 0.005, 0.05, 0.0, 0.05, 0.10, "Homing lock-on", 0.4),
    "missile_fire":           _SfxSpec("missile_fire", Voice.SAW, 400, -200, 0.005, 0.10, 0.0, 0.10, 0.20, "Homing missile launch", 0.5),
    "screen_shake_thump":     _SfxSpec("screen_shake_thump", Voice.NOISE, 60, 0, 0.002, 0.08, 0.0, 0.10, 0.18, "Trauma shake thump", 0.5),
    # BLOQUE_STELLAR_HORIZON_AUDIO: per-ship thruster loops.
    # Each ship (player + 6 enemy kinds) gets a unique continuous
    # loop that loops forever while alive. The ThrusterManager applies
    # dynamic compression so N ships don't add up to Nx volume.
    # Designed for `loops=-1` playback on a dedicated mixer channel.
    # 0.55s buffer (loop seam is at zero crossings so it's inaudible).
    "thruster_player":         _SfxSpec("thruster_player", Voice.SAW, 110, 8, 0.020, 0.03, 0.78, 0.05, 0.08, "Player engine hum", 0.32),
    "thruster_scout":          _SfxSpec("thruster_scout", Voice.SQUARE, 360, -20, 0.005, 0.02, 0.82, 0.05, 0.06, "Scout dart whine", 0.30),
    "thruster_cruiser":        _SfxSpec("thruster_cruiser", Voice.SAW, 165, 5, 0.020, 0.04, 0.80, 0.05, 0.08, "Cruiser mid hum", 0.32),
    "thruster_heavy":          _SfxSpec("thruster_heavy", Voice.SQUARE, 55, 3, 0.020, 0.05, 0.85, 0.06, 0.10, "Heavy rumble", 0.40),
    "thruster_bomber":         _SfxSpec("thruster_bomber", Voice.SAW, 95, 0, 0.020, 0.04, 0.78, 0.10, 0.12, "Bomber pulse drone", 0.36),
    "thruster_ufo":            _SfxSpec("thruster_ufo", Voice.TRIANGLE, 220, 14, 0.005, 0.03, 0.80, 0.04, 0.06, "UFO warble", 0.30),
    "thruster_kamikaze":       _SfxSpec("thruster_kamikaze", Voice.SQUARE, 480, 28, 0.005, 0.02, 0.80, 0.04, 0.06, "Kamikaze rising whine", 0.32),
}

SFX_NAMES: tuple[str, ...] = tuple(SFX_CATALOG.keys())


# ---------------------------------------------------------------------------
# BGM catalog (4 entries per GDD §9)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _BgmSpec:
    name: str
    duration_s: float
    section_a_notes: tuple[tuple[float, float, Voice], ...]  # (freq_hz, duration, voice)
    section_b_notes: tuple[tuple[float, float, Voice], ...]
    tempo_bpm: float = 120.0


BGM_CATALOG: dict[str, _BgmSpec] = {
    "title": _BgmSpec(
        "title", 32.0,
        # Cm pad: C3, G3, Eb4, Bb4
        ((130.81, 4.0, Voice.TRIANGLE), (196.0, 4.0, Voice.TRIANGLE),
         (311.13, 4.0, Voice.TRIANGLE), (466.16, 4.0, Voice.TRIANGLE)),
        # arpeggio: C-E-G-C-E-G
        ((261.63, 0.5, Voice.SQUARE), (329.63, 0.5, Voice.SQUARE),
         (392.0, 0.5, Voice.SQUARE), (523.25, 0.5, Voice.SQUARE),
         (659.25, 0.5, Voice.SQUARE), (783.99, 0.5, Voice.SQUARE)),
        tempo_bpm=80.0,
    ),
    "act_normal": _BgmSpec(
        "act_normal", 40.0,
        # saw bass C2-G2 alternating
        ((65.41, 0.5, Voice.SAW), (98.0, 0.5, Voice.SAW)),
        # lead arpeggio C-E-G-Bb
        ((261.63, 0.25, Voice.SQUARE), (329.63, 0.25, Voice.SQUARE),
         (392.0, 0.25, Voice.SQUARE), (466.16, 0.25, Voice.SQUARE)),
        tempo_bpm=120.0,
    ),
    "boss_fight": _BgmSpec(
        "boss_fight", 36.0,
        # saw bass C2-C2-G2-G2
        ((65.41, 0.25, Voice.SAW), (65.41, 0.25, Voice.SAW),
         (98.0, 0.25, Voice.SAW), (98.0, 0.25, Voice.SAW)),
        # lead C5-G5-Eb6-Bb5
        ((523.25, 0.25, Voice.SQUARE), (783.99, 0.25, Voice.SQUARE),
         (622.25, 0.25, Voice.SQUARE), (466.16, 0.25, Voice.SQUARE)),
        tempo_bpm=140.0,
    ),
    "credits": _BgmSpec(
        "credits", 48.0,
        # F major pad
        ((174.61, 4.0, Voice.TRIANGLE), (220.0, 4.0, Voice.TRIANGLE),
         (261.63, 4.0, Voice.TRIANGLE), (349.23, 4.0, Voice.TRIANGLE)),
        # voice F5-A5-C6
        ((698.46, 1.0, Voice.TRIANGLE), (880.0, 1.0, Voice.TRIANGLE),
         (1046.5, 1.0, Voice.TRIANGLE)),
        tempo_bpm=70.0,
    ),
}

BGM_NAMES: tuple[str, ...] = tuple(BGM_CATALOG.keys())


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------
def _render_voice(
    voice: Voice,
    freq_hz: float,
    freq_slide: float,
    duration_s: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
    volume: float,
    rng: random.Random,
) -> array.array[int]:
    """Render a single voice into a 16-bit signed PCM array."""
    sample_rate = MIXER_SAMPLE_RATE
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    if n_samples == 0:
        return out
    if voice == Voice.NOISE:
        # Noise: random values modulated by envelope
        for i in range(n_samples):
            t = i / sample_rate
            freq = freq_hz + freq_slide * t
            # For noise, freq parameter is unused; we generate one sample per call
            sample = noise_wave(t, freq, rng)
            env = adsr_envelope(t, duration_s, attack, decay, sustain, release)
            out[i] = int(sample * env * volume * 32767)
        return out
    func = _VOICE_FUNCS.get(voice)
    if func is None:
        return out
    for i in range(n_samples):
        t = i / sample_rate
        freq = freq_hz + freq_slide * t
        sample = func(t, freq)
        env = adsr_envelope(t, duration_s, attack, decay, sustain, release)
        out[i] = int(sample * env * volume * 32767)
    return out


def render_sfx(name: str, rng: random.Random | None = None) -> array.array[int]:
    """Render a SFX to a 16-bit signed PCM array. Null-safe if name unknown."""
    if name not in SFX_CATALOG:
        return array.array("h", [0])
    spec = SFX_CATALOG[name]
    rng = rng or random.Random()
    return _render_voice(
        spec.voice, spec.freq_hz, spec.slide_hz_per_s,
        spec.duration_s, spec.attack_s, spec.decay_s,
        spec.sustain, spec.release_s, spec.volume, rng,
    )


def render_bgm(name: str, rng: random.Random | None = None) -> array.array[int]:
    """Render a BGM track (A-B sections concatenated) to 16-bit PCM."""
    if name not in BGM_CATALOG:
        return array.array("h", [0])
    spec = BGM_CATALOG[name]
    rng = rng or random.Random()
    sample_rate = MIXER_SAMPLE_RATE
    # Build a list of (freq, start, duration, voice) tuples
    events: list[tuple[float, float, float, Voice]] = []
    t = 0.0
    for freq, dur, voice in spec.section_a_notes:
        events.append((freq, t, dur, voice))
        t += dur
    for freq, dur, voice in spec.section_b_notes:
        events.append((freq, t, dur, voice))
        t += dur
    total_dur = t
    n_samples = int(total_dur * sample_rate)
    out = array.array("h", [0] * n_samples)
    for freq, start, dur, voice in events:
        voice_samples = _render_voice(
            voice, freq, 0.0, dur,
            0.005, 0.05, 0.5, 0.10,
            0.5, rng,
        )
        start_idx = int(start * sample_rate)
        for i, v in enumerate(voice_samples):
            idx = start_idx + i
            if 0 <= idx < n_samples:
                # Mix (additive, clamped)
                mixed = int(out[idx]) + int(v)
                out[idx] = max(-32767, min(32767, mixed))
    return out


# ---------------------------------------------------------------------------
# AudioEngine — wraps pygame.mixer with null-safety
# ---------------------------------------------------------------------------
@dataclass
class AudioEngine:
    """Manages 16-channel mixer with pre-baked SFX/BGM."""
    mixer_available: bool = False
    sfx_buffers: dict[str, array.array[int]] = field(default_factory=dict)
    bgm_buffers: dict[str, array.array[int]] = field(default_factory=dict)
    sfx_sounds: dict[str, pygame.mixer.Sound] = field(default_factory=dict)
    bgm_sounds: dict[str, pygame.mixer.Sound] = field(default_factory=dict)
    current_bgm: Optional[str] = None
    master_volume: float = 0.7

    def __post_init__(self) -> None:
        self.sfx_buffers = {}
        self.bgm_buffers = {}
        self.sfx_sounds = {}
        self.bgm_sounds = {}
        try:
            pygame.mixer.pre_init(
                frequency=MIXER_SAMPLE_RATE,
                size=-16,  # 16-bit signed
                channels=1,
                buffer=MIXER_BUFFER,
            )
            pygame.mixer.init()
            pygame.mixer.set_num_channels(MIXER_CHANNELS)
            self.mixer_available = True
            self._prebake_all()
        except pygame.error:
            self.mixer_available = False

    def _prebake_all(self) -> None:
        """Render all SFX + BGM and wrap as pygame.mixer.Sound."""
        if not self.mixer_available:
            return
        rng = random.Random(42)  # deterministic
        for name in SFX_NAMES:
            buf = render_sfx(name, rng)
            self.sfx_buffers[name] = buf
            try:
                sound = pygame.mixer.Sound(buffer=buf.tobytes())
                self.sfx_sounds[name] = sound
            except pygame.error:
                pass
        for name in BGM_NAMES:
            buf = render_bgm(name, rng)
            self.bgm_buffers[name] = buf
            try:
                sound = pygame.mixer.Sound(buffer=buf.tobytes())
                self.bgm_sounds[name] = sound
            except pygame.error:
                pass

    def play_sfx(self, name: str, volume: float = 1.0) -> bool:
        """Play a SFX. Returns True if dispatched, False if mixer down."""
        if not self.mixer_available or name not in self.sfx_sounds:
            return False
        sound = self.sfx_sounds[name]
        sound.set_volume(volume * self.master_volume)
        sound.play()
        return True

    def play_loop(self, name: str, channel_id: int,
                  volume: float = 1.0) -> bool:
        """Play a SFX on a specific mixer channel as a continuous loop.

        Used by ThrusterManager: each ship gets a dedicated channel
        and the loop runs forever until stop_loop() is called.
        `volume` is applied to the sound's internal volume (separate
        from `master_volume`).
        """
        if not self.mixer_available or name not in self.sfx_sounds:
            return False
        try:
            channel = pygame.mixer.Channel(channel_id)
        except (pygame.error, IndexError):
            return False
        sound = self.sfx_sounds[name]
        sound.set_volume(volume * self.master_volume)
        channel.play(sound, loops=-1)
        return True

    def stop_loop(self, channel_id: int) -> None:
        """Stop the loop on a specific mixer channel. Safe if no
        sound is playing on the channel."""
        if not self.mixer_available:
            return
        try:
            channel = pygame.mixer.Channel(channel_id)
            channel.stop()
        except (pygame.error, IndexError):
            pass

    def set_channel_volume(self, channel_id: int, volume: float) -> None:
        """Set the volume of a specific mixer channel (0.0 to 1.0).
        Used by ThrusterManager for the dynamic compressor."""
        if not self.mixer_available:
            return
        try:
            channel = pygame.mixer.Channel(channel_id)
            channel.set_volume(max(0.0, min(1.0, volume)) * self.master_volume)
        except (pygame.error, IndexError):
            pass

    def play_bgm(self, name: str, loops: int = -1) -> bool:
        """Play BGM (loops by default). Returns True if dispatched."""
        if not self.mixer_available or name not in self.bgm_sounds:
            return False
        sound = self.bgm_sounds[name]
        sound.set_volume(self.master_volume)
        sound.play(loops=loops)
        self.current_bgm = name
        return True

    def stop_bgm(self) -> None:
        if not self.mixer_available or self.current_bgm is None:
            return
        if self.current_bgm in self.bgm_sounds:
            self.bgm_sounds[self.current_bgm].stop()
        self.current_bgm = None

    def set_master_volume(self, volume: float) -> None:
        self.master_volume = max(0.0, min(1.0, volume))
        if self.mixer_available:
            pygame.mixer.music.set_volume(self.master_volume)

    def shutdown(self) -> None:
        if self.mixer_available:
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass


# ---------------------------------------------------------------------------
# BLOQUE 58.14: Lowpass filter for pause-screen "music in the next room"
# ---------------------------------------------------------------------------
# User wants the gameplay BGM to keep playing during pause but sound
# muffled (as if heard through a wall). True lowpass requires FFT or IIR
# filtering, which the GDD §0 normally forbids (no numpy/scipy). The
# user explicitly chose numpy for this feature (documented in
# requirements.txt), so we use a 1st-order IIR lowpass. It's O(n),
# simple, and produces a believable "behind a wall" effect.
#
# Filter math (1st-order RC lowpass, also called exponential moving avg):
#   y[i] = y[i-1] + alpha * (x[i] - y[i-1])
#   alpha = dt / (rc + dt) = dt * cutoff / (1 + dt * cutoff)
#   rc = 1 / (2 * pi * cutoff_hz)
#
# For 600 Hz cutoff at 44.1 kHz: alpha ≈ 0.022 → very muffled (only
# bass and low-mids pass through). That matches "next room" feel.
# ---------------------------------------------------------------------------
def apply_lowpass_to_wav(
    input_path: str,
    output_path: str,
    cutoff_hz: float = 600.0,
    sample_rate: int = 44100,
) -> bool:
    """Apply a 1st-order IIR lowpass to a 16-bit PCM WAV file.

    Reads input_path (must be 16-bit mono or stereo PCM WAV), applies
    the lowpass to each channel independently, and writes output_path.
    The output is a 16-bit PCM WAV with the same sample rate and channel
    count as the input.

    Returns True on success, False on error (missing input, bad format,
    etc.). The numpy import is local so the rest of the audio module
    stays numpy-free for tests.

    BLOQUE 58.14: this is the only numpy consumer in the audio path.
    The decision to allow numpy here is documented in requirements.txt.
    """
    try:
        import wave
        import numpy as np
    except ImportError:
        return False
    try:
        with wave.open(input_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            n_frames = wf.getnframes()
            src_rate = wf.getframerate()
            if sample_width not in (2, 3, 4):
                # 8-bit, 24-bit, 32-bit; 16-bit + 32-bit float not supported
                return False
            raw = wf.readframes(n_frames)
    except (OSError, wave.Error, EOFError):
        return False

    # Decode the sample width to a numpy int array, then convert to int16
    # (the math is identical — we just need to normalize to the [-1, 1]
    # float range for the IIR filter).
    if sample_width == 2:
        # 16-bit PCM, little-endian, signed. Direct int16 cast.
        samples = np.frombuffer(raw, dtype="<i2").astype(np.int16)
    elif sample_width == 3:
        # 24-bit PCM, little-endian, signed. Each sample is 3 bytes;
        # convert to int32 first, then downscale to int16.
        raw24 = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        as_i32 = (raw24[:, 0].astype(np.int32)
                  | (raw24[:, 1].astype(np.int32) << 8)
                  | (raw24[:, 2].astype(np.int32) << 16))
        # Sign-extend (top bit of byte 2 = bit 23 of the int)
        as_i32[as_i32 >= 0x800000] -= 0x1000000
        # Downscale 24-bit -> 16-bit (right-shift by 8)
        samples = (as_i32 >> 8).astype(np.int16)
    elif sample_width == 4:
        # 32-bit PCM, little-endian, signed. Downscale by right-shift 16.
        as_i32 = np.frombuffer(raw, dtype="<i4")
        samples = (as_i32 >> 16).astype(np.int16)
    else:
        return False

    if n_channels > 1:
        samples = samples.reshape(-1, n_channels)
    # Promote to float32 for IIR processing
    samples_f = samples.astype(np.float32)
    # 1st-order RC lowpass: y[i] = decay * y[i-1] + alpha * x[i]
    dt = 1.0 / float(sample_rate if sample_rate else src_rate)
    alpha = (dt * cutoff_hz) / (1.0 + dt * cutoff_hz)
    decay = 1.0 - alpha
    # Direct iterative IIR. The "weighted cumsum" trick has severe
    # numerical issues at large i (decay^i and decay^(-i) underflow /
    # overflow; the product stays bounded but the intermediate values
    # exceed float32 range). A simple Python loop is O(n) and numerically
    # stable; for the full 165MB BGM (~14.5M stereo samples) it takes
    # a few seconds once, and the result is cached on disk so subsequent
    # pauses are instant.
    alpha32 = np.float32(alpha)
    decay32 = np.float32(decay)
    if samples_f.ndim == 1:
        n = samples_f.shape[0]
        y = np.empty(n, dtype=np.float32)
        prev = np.float32(0.0)
        x32 = samples_f
        for i in range(n):
            cur = decay32 * prev + alpha32 * x32[i]
            y[i] = cur
            prev = cur
    else:
        # 2D: process each channel
        n = samples_f.shape[0]
        n_ch = samples_f.shape[1]
        y = np.empty_like(samples_f, dtype=np.float32)
        for ch in range(n_ch):
            prev = np.float32(0.0)
            x32 = samples_f[:, ch]
            for i in range(n):
                cur = decay32 * prev + alpha32 * x32[i]
                y[i, ch] = cur
                prev = cur
    # Back to int16 with clipping
    out = np.clip(y, -32768, 32767).astype(np.int16)
    # Write WAV
    try:
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(2)
            wf.setframerate(src_rate)
            wf.writeframes(out.tobytes())
    except (OSError, wave.Error):
        return False
    return True


