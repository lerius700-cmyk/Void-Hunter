"""16-bit / Mega Drive-style procedural audio synth.

Pure stdlib (array, math, random, wave) per GDD §0.
Expands the 8-bit synth.py with:
  - Wavetable synthesis (sum of sines with custom partials)
  - FM-style synthesis (carrier + modulator)
  - Multi-voice layering (up to 8 voices per SFX, with detune)
  - 1-pole analog filter (lowpass, highpass, sweep)
  - Bit-crush (downsample + bit depth reduce) for "opaque" feel
  - LFO modulation (sine, amplitude)
  - Transient shaping (noise click attack)
  - ADSR per-layer + master envelope
  - WAV writer (16-bit signed PCM, mono, stdlib `wave`)

Used by the 5 new SFX (warning_miniboss, warning_boss, propulsion,
enemy_shoot, engine_hum) and to overhaul the existing 26 SFX.
"""
from __future__ import annotations

import array
import math
import random
import wave
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants & defaults
# ---------------------------------------------------------------------------
DEFAULT_SAMPLE_RATE: int = 44100
INT16_MAX: int = 32767
INT16_MIN: int = -32768
TWO_PI: float = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Core DSP primitives
# ---------------------------------------------------------------------------
def wavetable_sine_sum(
    t: float,
    fundamental: float,
    partials: List[Tuple[float, float]],
) -> float:
    """Sum of N sines at multiples of fundamental with given amplitudes.

    partials: list of (freq_multiplier, amplitude).
    E.g. [(1.0, 0.6), (2.0, 0.3), (3.0, 0.15)] ≈ sawtooth-like.
    """
    s = 0.0
    for mult, amp in partials:
        s += amp * math.sin(TWO_PI * fundamental * mult * t)
    return s


def fm_voice(
    t: float,
    carrier_freq: float,
    mod_freq: float,
    mod_index: float,
) -> float:
    """Simple FM synthesis (1 carrier, 1 modulator). mod_index → brightness."""
    modulator = mod_index * math.sin(TWO_PI * mod_freq * t)
    return math.sin(TWO_PI * carrier_freq * t + modulator)


def noise_white(rng: random.Random) -> float:
    return rng.uniform(-1.0, 1.0)


def lfo_sine(t: float, rate_hz: float, phase: float = 0.0) -> float:
    """LFO output in [-1, 1]."""
    return math.sin(TWO_PI * rate_hz * t + phase)


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------
def envelope_adsr(
    t: float,
    duration: float,
    attack: float = 0.005,
    decay: float = 0.1,
    sustain: float = 0.7,
    release: float = 0.2,
) -> float:
    """ADSR envelope. Returns multiplier in [0, 1]."""
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
# Filters (1-pole — cheap and good enough for SFX)
# ---------------------------------------------------------------------------
def lowpass_1pole(
    signal: array.array,
    cutoff_hz: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """Simple 1-pole lowpass. cutoff_hz in (0, sample_rate/2)."""
    n = len(signal)
    if n == 0 or cutoff_hz <= 0 or cutoff_hz >= sample_rate / 2:
        return array.array(signal.typecode, signal)
    rc = 1.0 / (TWO_PI * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    out = array.array(signal.typecode, [0] * n)
    prev = 0.0
    for i in range(n):
        prev = prev + alpha * (signal[i] - prev)
        out[i] = int(max(INT16_MIN, min(INT16_MAX, prev)))
    return out


def highpass_1pole(
    signal: array.array,
    cutoff_hz: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """1-pole highpass."""
    n = len(signal)
    if n == 0 or cutoff_hz <= 0 or cutoff_hz >= sample_rate / 2:
        return array.array(signal.typecode, signal)
    rc = 1.0 / (TWO_PI * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    out = array.array(signal.typecode, [0] * n)
    prev_in = 0.0
    prev_out = 0.0
    for i in range(n):
        s = signal[i]
        y = alpha * (prev_out + s - prev_in)
        prev_in = s
        prev_out = y
        out[i] = int(max(INT16_MIN, min(INT16_MAX, y)))
    return out


def lowpass_sweep(
    signal: array.array,
    cutoff_start_hz: float,
    cutoff_end_hz: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """1-pole lowpass with linear-cutoff sweep across the buffer."""
    n = len(signal)
    if n == 0:
        return array.array(signal.typecode, signal)
    out = array.array(signal.typecode, [0] * n)
    dt = 1.0 / sample_rate
    prev = 0.0
    for i in range(n):
        cutoff = cutoff_start_hz + (cutoff_end_hz - cutoff_start_hz) * (i / max(1, n - 1))
        if cutoff <= 0 or cutoff >= sample_rate / 2:
            prev = float(signal[i])
            out[i] = signal[i]
            continue
        rc = 1.0 / (TWO_PI * cutoff)
        alpha = dt / (rc + dt)
        prev = prev + alpha * (signal[i] - prev)
        out[i] = int(max(INT16_MIN, min(INT16_MAX, prev)))
    return out


# ---------------------------------------------------------------------------
# Bit-crush / lo-fi (for "opaque" feel)
# ---------------------------------------------------------------------------
def bit_crush(
    signal: array.array,
    target_bits: int = 8,
) -> array.array:
    """Reduce bit depth only — preserves duration and sample rate.

    target_bits: 1..16 (16 = passthrough). For the gritty lo-fi feel
    without changing playback duration, use this alone. For full lo-fi
    with sample rate reduction (and preserved duration via lower playback
    rate), use `downsample` + `bit_crush` + `write_wav` with the new rate.
    """
    if target_bits >= 16:
        return array.array(signal.typecode, signal)
    target_bits = max(1, min(16, target_bits))
    levels = float(1 << (target_bits - 1))
    n = len(signal)
    out = array.array(signal.typecode, [0] * n)
    for i in range(n):
        s = signal[i] / 32767.0
        quantized = round(s * levels) / levels
        out[i] = int(max(INT16_MIN, min(INT16_MAX, quantized * 32767.0)))
    return out


def downsample(
    signal: array.array,
    factor: int = 2,
) -> array.array:
    """Average groups of `factor` samples to decimate.

    Returns a shorter signal. To preserve playback duration, write
    the WAV at `original_sr // factor`.
    """
    factor = max(1, factor)
    n = len(signal)
    if factor <= 1:
        return array.array(signal.typecode, signal)
    new_n = max(1, n // factor)
    out = array.array(signal.typecode, [0] * new_n)
    for i in range(new_n):
        s = 0
        for j in range(factor):
            idx = i * factor + j
            if idx < n:
                s += signal[idx]
        out[i] = s // factor
    return out


# ---------------------------------------------------------------------------
# Reverb (Schroeder-style comb filter) + soft saturation
# ---------------------------------------------------------------------------
def comb_filter(
    signal: array.array,
    delay_s: float = 0.03,
    feedback: float = 0.4,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """Single-tap feedback comb filter — adds a delayed echo for size/space.

    delay_s: time of the echo in seconds (typical: 0.02-0.08 for tight room).
    feedback: 0.0 = dry, 0.5 = noticeable echo, 0.7+ = long ringing tail.
    """
    n = len(signal)
    if n == 0 or delay_s <= 0 or feedback <= 0:
        return array.array(signal.typecode, signal)
    delay_samples = max(1, int(delay_s * sample_rate))
    out = array.array(signal.typecode, [0] * n)
    # Initial pass — direct signal
    for i in range(n):
        out[i] = signal[i]
    # Feedback tap
    for i in range(delay_samples, n):
        # Mix in the delayed sample (attenuated)
        delayed = int(out[i - delay_samples] * feedback)
        mixed = out[i] + delayed
        out[i] = max(INT16_MIN, min(INT16_MAX, mixed))
    return out


def soft_saturate(
    signal: array.array,
    drive: float = 1.5,
) -> array.array:
    """Soft saturation (cheap tanh approximation) for warmth/harmonics.

    drive: 1.0 = passthrough, 1.5-2.0 = noticeable warmth, 3.0+ = grit.
    Adds even-order harmonics, simulates analog tape/console saturation.
    """
    n = len(signal)
    out = array.array(signal.typecode, [0] * n)
    for i, s in enumerate(signal):
        x = (s / 32767.0) * drive
        # Soft clip: y = x / (1 + |x|) — cheap, monotonic, smooth
        y = x / (1.0 + abs(x))
        out[i] = int(max(-1.0, min(1.0, y)) * 32767.0)
    return out



# ---------------------------------------------------------------------------
# Mix / amp / envelope utilities
# ---------------------------------------------------------------------------
def mix_at(signal: array.array, mix_target: array.array, amp: float) -> None:
    """In-place additive mix of `signal` * amp into `mix_target`."""
    n = min(len(signal), len(mix_target))
    for i in range(n):
        mixed = mix_target[i] + int(signal[i] * amp)
        mix_target[i] = max(INT16_MIN, min(INT16_MAX, mixed))


def apply_amp(signal: array.array, amp: float) -> array.array:
    """Scale signal amplitude (0.0 to 1.0+)."""
    out = array.array(signal.typecode, [0] * len(signal))
    for i, s in enumerate(signal):
        out[i] = int(max(INT16_MIN, min(INT16_MAX, s * amp)))
    return out


def apply_lfo_amp(
    signal: array.array,
    lfo_rate_hz: float,
    lfo_depth: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """Modulate amplitude with sine LFO. depth=0 → no mod, depth=1 → 100% depth."""
    n = len(signal)
    out = array.array(signal.typecode, [0] * n)
    for i, s in enumerate(signal):
        t = i / sample_rate
        mod = 1.0 - lfo_depth + lfo_depth * (0.5 + 0.5 * math.sin(TWO_PI * lfo_rate_hz * t))
        out[i] = int(max(INT16_MIN, min(INT16_MAX, s * mod)))
    return out


def apply_envelope(
    signal: array.array,
    duration_s: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> array.array:
    """Apply ADSR envelope to a signal."""
    n = len(signal)
    out = array.array(signal.typecode, [0] * n)
    for i, s in enumerate(signal):
        t = i / sample_rate
        env = envelope_adsr(t, duration_s, attack, decay, sustain, release)
        out[i] = int(max(INT16_MIN, min(INT16_MAX, s * env)))
    return out


# ---------------------------------------------------------------------------
# Voice renderers
# ---------------------------------------------------------------------------
def render_wavetable_voice(
    partials: List[Tuple[float, float]],
    freq_hz: float,
    duration_s: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    freq_lfo_hz: float = 0.0,
    freq_lfo_depth_hz: float = 0.0,
    amp_lfo_hz: float = 0.0,
    amp_lfo_depth: float = 0.0,
    detune_cents: float = 0.0,
    rng: Optional[random.Random] = None,
    phase_offset: float = 0.0,
) -> array.array:
    """Render a single wavetable voice.

    partials: list of (freq_mult, amp) for sine sum.
    freq_lfo_hz/depth: optional LFO on instantaneous frequency (for sirens).
    amp_lfo_hz/depth: optional amplitude LFO (for tremolo / pulse).
    detune_cents: ± cents for layering.
    """
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    if n_samples == 0:
        return out
    detune_mult = 2 ** (detune_cents / 1200.0)
    rand_phase = (rng.random() * TWO_PI) if rng else 0.0
    for i in range(n_samples):
        t = i / sample_rate
        # Frequency with LFO
        if freq_lfo_hz > 0.0 and freq_lfo_depth_hz != 0.0:
            freq = (freq_hz + freq_lfo_depth_hz * math.sin(TWO_PI * freq_lfo_hz * t)) * detune_mult
        else:
            freq = freq_hz * detune_mult
        sample = wavetable_sine_sum(t + (rand_phase + phase_offset) / TWO_PI, freq, partials)
        # Amplitude LFO
        if amp_lfo_hz > 0.0 and amp_lfo_depth > 0.0:
            sample *= 1.0 - amp_lfo_depth + amp_lfo_depth * (0.5 + 0.5 * math.sin(TWO_PI * amp_lfo_hz * t))
        out[i] = int(max(INT16_MIN, min(INT16_MAX, sample * 32767.0 * 0.7)))
    return out


def render_fm_voice(
    carrier_hz: float,
    mod_hz: float,
    mod_index: float,
    duration_s: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    mod_index_slide: float = 0.0,
) -> array.array:
    """Render a single FM voice with optional mod_index slide."""
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        idx = mod_index + mod_index_slide * t
        sample = fm_voice(t, carrier_hz, mod_hz, idx)
        out[i] = int(max(INT16_MIN, min(INT16_MAX, sample * 32767.0 * 0.7)))
    return out


def render_noise(
    duration_s: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    rng: Optional[random.Random] = None,
    color: str = "white",
) -> array.array:
    """Render noise. color: 'white', 'pink' (4-tap average), 'brown' (integrated)."""
    rng = rng or random.Random()
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    if color == "white":
        for i in range(n_samples):
            out[i] = int(noise_white(rng) * 32767 * 0.5)
    elif color == "pink":
        for i in range(n_samples):
            v = (noise_white(rng) + noise_white(rng) + noise_white(rng) + noise_white(rng)) * 0.25
            out[i] = int(v * 32767 * 0.5)
    elif color == "brown":
        v = 0.0
        for i in range(n_samples):
            v = v * 0.99 + noise_white(rng) * 0.05
            v = max(-1.0, min(1.0, v))
            out[i] = int(v * 32767 * 0.5)
    return out


def render_click(
    duration_s: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    rng: Optional[random.Random] = None,
    amp: float = 1.0,
) -> array.array:
    """Short noise burst with very fast attack + exponential decay (transient)."""
    rng = rng or random.Random()
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    for i in range(n_samples):
        t = i / sample_rate
        env = math.exp(-t * 50)  # fast decay
        out[i] = int(noise_white(rng) * env * 32767 * 0.6 * amp)
    return out


# ---------------------------------------------------------------------------
# Final utilities
# ---------------------------------------------------------------------------
def signal_peak(signal: array.array) -> float:
    return float(max(abs(s) for s in signal)) if signal else 0.0


def normalize(signal: array.array, target_peak: float = 0.85 * 32767) -> array.array:
    """Normalize to target peak (default 85% of max to avoid clipping on master mix)."""
    peak = signal_peak(signal)
    if peak <= 0:
        return signal
    factor = target_peak / peak
    return apply_amp(signal, factor)


def write_wav(
    signal: array.array,
    path: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> None:
    """Write a signed 16-bit mono WAV file (uses stdlib `wave`)."""
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(signal.tobytes())


# ---------------------------------------------------------------------------
# Convenience: padded mix for layered SFX
# ---------------------------------------------------------------------------
def empty_buffer(n_samples: int, typecode: str = "h") -> array.array:
    return array.array(typecode, [0] * n_samples)
