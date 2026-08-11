"""5 SFX recipes — Star Fox-inspired cinematic SFX (Iter 2).

Per user feedback on iter 1 (16-bit Mega Drive was "horrible"), this
revision re-orients to the Star Fox DNA: sub-bass weight, punchy
transients, reverb for size, soft saturation for warmth, multiple
layers for density. Not retro 16-bit — modern cinematic rail-shooter.

All recipes pure procedural + stdlib, per GDD §0.

SFX:
  - warning_miniboss: 2.5s YELLOW klaxon (SubBossIntroScene)
  - warning_boss:     4.5s RED siren (BossIntroScene)
  - propulsion:       ~2s engine thrust (PROPULSION player state, loop)
  - enemy_shoot:      0.3s opaque shot (every enemy attack pattern)
  - engine_hum:       ~2s idle engine hum (MOVE/IDLE, loop)
"""
from __future__ import annotations

import array
import math
import random
from typing import List, Tuple

from src.audio.synth_16bit import (
    DEFAULT_SAMPLE_RATE,
    INT16_MAX,
    INT16_MIN,
    TWO_PI,
    apply_amp,
    apply_envelope,
    apply_lfo_amp,
    bit_crush,
    comb_filter,
    downsample,
    empty_buffer,
    highpass_1pole,
    lowpass_1pole,
    lowpass_sweep,
    mix_at,
    normalize,
    render_click,
    render_fm_voice,
    render_noise,
    render_wavetable_voice,
    signal_peak,
    soft_saturate,
)


# Wavetable partials (still used for some layer shapes)
SAW_PARTIALS: List[Tuple[float, float]] = [
    (1.0, 0.55), (2.0, 0.28), (3.0, 0.18), (4.0, 0.12), (5.0, 0.08), (6.0, 0.05),
]
SQUARE_PARTIALS: List[Tuple[float, float]] = [
    (1.0, 0.55), (3.0, 0.18), (5.0, 0.10), (7.0, 0.06), (9.0, 0.04),
]
TRIANGLE_PARTIALS: List[Tuple[float, float]] = [
    (1.0, 0.6), (3.0, 0.07), (5.0, 0.03), (7.0, 0.015),
]


def _sine_voice(
    freq_hz: float,
    duration_s: float,
    sample_rate: int,
    freq_lfo_hz: float = 0.0,
    freq_lfo_depth_hz: float = 0.0,
    amp: float = 0.5,
    detune_cents: float = 0.0,
) -> array.array:
    """Clean sine voice with optional frequency LFO. For sub-bass / fundamentals."""
    n_samples = int(duration_s * sample_rate)
    out = array.array("h", [0] * n_samples)
    if n_samples == 0:
        return out
    detune_mult = 2 ** (detune_cents / 1200.0)
    for i in range(n_samples):
        t = i / sample_rate
        if freq_lfo_hz > 0 and freq_lfo_depth_hz > 0:
            freq = (freq_hz + freq_lfo_depth_hz * math.sin(TWO_PI * freq_lfo_hz * t)) * detune_mult
        else:
            freq = freq_hz * detune_mult
        sample = math.sin(TWO_PI * freq * t) * amp
        out[i] = int(max(INT16_MIN, min(INT16_MAX, sample * 32767.0 * 0.85)))
    return out


# ---------------------------------------------------------------------------
# 1. warning_miniboss — YELLOW MILITARY THREAT DETECTION, 2.5s
#    Star Fox 64 boost DNA: sweep ascendente con energía tipo "boost"
#    + peso militar (sub-bass + transient punch), NO ring de teléfono.
# ---------------------------------------------------------------------------
def render_warning_miniboss(
    duration_s: float = 2.5,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 2,
) -> array.array:
    """YELLOW WARNING — military threat detection (Star Fox boost DNA).

    Concept: a military spaceship detected a threat. Inspired by the
    Star Fox 64 Arwing boost sound (rising pitch sweep + whoosh + body)
    but with MILITARY weight (sub-bass 55 Hz, transient punch) and
    REPEATED in short pulses to feel like a "detection alarm" not a
    phone ring.

    Structure (6 pulses/s = matches 6 Hz visual pulse of SubBossIntro):
      Each pulse is ~0.17s long and shaped like a mini Arwing boost:
        - 0.00-0.02s: hard transient (noise click + body thump)
        - 0.02-0.10s: rising pitch sweep 450 -> 1600 Hz (the "boost")
        - 0.10-0.17s: fast exponential decay
      The whole thing has:
        - Sub-bass 55 Hz sine constant (military weight)
        - Saw 100 Hz constant (presence body)
        - Reverb comb 0.04s (space/sci-fi)
        - Soft saturation drive 1.3 (analog warmth)
    """
    rng = random.Random(seed)
    n = int(duration_s * sample_rate)
    out = empty_buffer(n)

    # ============================================================
    # Layer 1: Sub-bass 55 Hz sine CONSTANTE — peso militar
    # ============================================================
    sub_bass = _sine_voice(55.0, duration_s, sample_rate, amp=0.5)
    mix_at(sub_bass, out, 1.0)

    # ============================================================
    # Layer 2: Saw 100 Hz CONSTANTE — cuerpo
    # ============================================================
    body_voice = render_wavetable_voice(
        SAW_PARTIALS, freq_hz=100.0, duration_s=duration_s,
        sample_rate=sample_rate, rng=rng,
    )
    mix_at(apply_amp(body_voice, 0.35), out, 1.0)

    # ============================================================
    # Layer 3: PULSOS tipo "boost" (sweep ascendente + transient)
    # 6 pulsos/segundo = cada 0.167s
    # ============================================================
    pulse_rate_hz = 6.0
    pulse_period = 1.0 / pulse_rate_hz  # 0.167s
    sweep_start_hz = 450.0
    sweep_end_hz = 1600.0
    pulse_dur = 0.13  # duración activa de cada pulso

    for i in range(n):
        t = i / sample_rate
        # Posición dentro del ciclo de pulso
        local_t = (t % pulse_period)

        if local_t < pulse_dur:
            # Fase 1: transient (0-0.02s) — click + body thump
            if local_t < 0.02:
                trans_env = math.exp(-local_t * 80)
                # Noise + sub-thump en el transient
                noise = rng.uniform(-1, 1) * trans_env * 0.6
                thump_freq = 80.0 - 30.0 * local_t / 0.02
                thump = math.sin(TWO_PI * thump_freq * t) * trans_env * 0.5
                v = (noise + thump) * 0.5
            else:
                # Fase 2: rising sweep 450 -> 1600 Hz (el "boost" feel)
                sweep_t = (local_t - 0.02) / (pulse_dur - 0.02)
                # Curva exponencial para que el sweep se sienta rápido
                freq = sweep_start_hz * (sweep_end_hz / sweep_start_hz) ** sweep_t
                # Triangle con armónicos
                fundamental = math.sin(TWO_PI * freq * t)
                # Sumamos un par de armónicos para "voz"
                harm2 = 0.3 * math.sin(TWO_PI * freq * 2 * t)
                harm3 = 0.15 * math.sin(TWO_PI * freq * 3 * t)
                # Envolvente attack rápido, decay exponencial
                env = math.exp(-(local_t - 0.02) * 15)
                v = (fundamental + harm2 + harm3) * env * 0.7
            out[i] = max(INT16_MIN, min(INT16_MAX, out[i] + int(v * 32767.0)))

    # ============================================================
    # Layer 4: Reverb comb 0.04s, 0.35 feedback — space/sci-fi
    # ============================================================
    out = comb_filter(out, delay_s=0.04, feedback=0.35, sample_rate=sample_rate)

    # ============================================================
    # Layer 5: Soft saturation (analog warmth)
    # ============================================================
    out = soft_saturate(out, drive=1.3)

    # ============================================================
    # Lowpass doma los brillos
    # ============================================================
    out = lowpass_1pole(out, 4000.0, sample_rate)

    # ============================================================
    # ADSR overall
    # ============================================================
    out = apply_envelope(out, duration_s, 0.005, 0.05, 0.9, 0.1, sample_rate)

    return normalize(out)


# ---------------------------------------------------------------------------
# 2. warning_boss — RED siren, 4.5s, dramática (Star Fox-style)
# ---------------------------------------------------------------------------
def render_warning_boss(
    duration_s: float = 4.5,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 3,
) -> array.array:
    """RED ALARM — boss final warning (Star Fox DNA: dramatic, weighty).

    Sound: 3 dramatic rising-tone sweeps (1.5s each, 1.5 Hz) layered
    over a deep 40 Hz sub-bass rumble with breathing LFO. Bandpass
    noise (1-3 kHz) for the "air raid" texture. Each sweep has a
    transient click at its peak. Reverb tail for cinematic size.
    Soft saturation gives analog warmth. The result is cinematic,
    not a 16-bit beep — feels like a real "INCOMING HOSTILE" klaxon.
    """
    rng = random.Random(seed)
    n = int(duration_s * sample_rate)
    out = empty_buffer(n)

    # Layer 1: SIREN — 3 sweeps rising 80→220 Hz en 1.5s
    # Usa 2 sawtooths desentonados (chorus) + frequency LFO
    siren1 = render_wavetable_voice(
        SAW_PARTIALS,
        freq_hz=150.0,
        duration_s=duration_s,
        sample_rate=sample_rate,
        freq_lfo_hz=0.67,  # 0.67 Hz = 3 sweeps en 4.5s
        freq_lfo_depth_hz=70.0,  # 80→220 Hz
        rng=rng,
    )
    mix_at(apply_amp(siren1, 0.55), out, 1.0)

    siren2 = render_wavetable_voice(
        SAW_PARTIALS,
        freq_hz=150.0,
        duration_s=duration_s,
        sample_rate=sample_rate,
        freq_lfo_hz=0.67,
        freq_lfo_depth_hz=70.0,
        rng=rng,
        detune_cents=+12.0,
    )
    mix_at(apply_amp(siren2, 0.45), out, 1.0)

    # Layer 2: Sub-bass rumble 40 Hz con LFO 0.67 Hz en amplitud
    sub = _sine_voice(40.0, duration_s, sample_rate, amp=0.6)
    sub = apply_lfo_amp(sub, 0.67, 0.4, sample_rate)
    mix_at(sub, out, 1.0)

    # Layer 3: Sub-bass 80 Hz (fifth) para "presencia grave"
    sub2 = _sine_voice(80.0, duration_s, sample_rate, amp=0.35)
    sub2 = apply_lfo_amp(sub2, 0.67, 0.3, sample_rate)
    mix_at(sub2, out, 1.0)

    # Layer 4: Air-raid noise (bandpass white noise alrededor 2 kHz)
    noise = render_noise(duration_s, sample_rate, rng, color="white")
    noise = highpass_1pole(noise, 1500.0, sample_rate)
    noise = lowpass_1pole(noise, 4000.0, sample_rate)
    mix_at(apply_amp(noise, 0.18), out, 1.0)

    # Layer 5: Click transient al pico de cada sweep (cada 1.5s)
    for cycle in range(3):
        click_time = cycle * 1.5 + 0.75  # mid-sweep
        click_start = int(click_time * sample_rate)
        click_samples = int(0.04 * sample_rate)
        for j in range(click_samples):
            idx = click_start + j
            if 0 <= idx < n:
                env = math.exp(-(j / sample_rate) * 80)
                click_val = (rng.uniform(-1, 1)) * env * 0.5
                out[idx] = max(INT16_MIN, min(INT16_MAX, out[idx] + int(click_val * 32767)))

    # 8 Hz amplitude pulse (visual sync)
    out = apply_lfo_amp(out, 8.0, 0.25, sample_rate)

    # Soft saturation for analog warmth
    out = soft_saturate(out, drive=1.6)

    # Reverb (cinematic size) — 0.06s delay, 0.45 feedback
    out = comb_filter(out, delay_s=0.06, feedback=0.45, sample_rate=sample_rate)

    # Lowpass doma los agudos
    out = lowpass_1pole(out, 4000.0, sample_rate)

    # ADSR overall — attack rápido, decay medio, sustain alto, release generoso
    out = apply_envelope(out, duration_s, 0.02, 0.3, 0.9, 0.6, sample_rate)

    return normalize(out)


# ---------------------------------------------------------------------------
# 3. propulsion — Thruster / engine thrust (PROPULSION state, loop-friendly)
# ---------------------------------------------------------------------------
def render_propulsion(
    duration_s: float = 2.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 4,
) -> array.array:
    """Rocket thruster / engine thrust (Star Fox-style Arwing boost).

    Sound: Filtered noise sweep (the "air rushing" of a real jet) +
    deep 50 Hz sub-bass for weight + 200 Hz sawtooth for mid presence.
    A 4 Hz LFO modulates the bandpass center frequency, so the filter
    "breathes" like a real engine. Reverb adds space. The result is
    a powerful continuous thrust, not a 16-bit saw drone.
    """
    rng = random.Random(seed)
    n = int(duration_s * sample_rate)
    out = empty_buffer(n)

    # Layer 1: Air-rushing noise (white noise filtrado a bandpass)
    noise = render_noise(duration_s, sample_rate, rng, color="white")
    noise = highpass_1pole(noise, 200.0, sample_rate)
    noise = lowpass_1pole(noise, 1200.0, sample_rate)
    mix_at(apply_amp(noise, 0.55), out, 1.0)

    # Layer 2: Sub-bass 50 Hz sine (peso del motor)
    sub = _sine_voice(50.0, duration_s, sample_rate, amp=0.5)
    sub = apply_lfo_amp(sub, 4.0, 0.15, sample_rate)
    mix_at(sub, out, 1.0)

    # Layer 3: Mid saw 200 Hz (presencia)
    saw_mid = render_wavetable_voice(
        SAW_PARTIALS, freq_hz=200.0, duration_s=duration_s,
        sample_rate=sample_rate, rng=rng, detune_cents=-7.0,
    )
    mix_at(apply_amp(saw_mid, 0.25), out, 1.0)

    # Layer 4: Sub-octave saw 100 Hz (cuerpo)
    saw_low = render_wavetable_voice(
        SAW_PARTIALS, freq_hz=100.0, duration_s=duration_s,
        sample_rate=sample_rate, rng=rng,
    )
    mix_at(apply_amp(saw_low, 0.3), out, 1.0)

    # 4 Hz amplitude LFO (engine throb)
    out = apply_lfo_amp(out, 4.0, 0.15, sample_rate)

    # Soft saturation
    out = soft_saturate(out, drive=1.5)

    # Reverb (size)
    out = comb_filter(out, delay_s=0.04, feedback=0.3, sample_rate=sample_rate)

    # Final lowpass (doma los chirridos)
    out = lowpass_1pole(out, 1500.0, sample_rate)

    # ADSR loop-friendly (attack/release muy cortos → seamless loop)
    out = apply_envelope(out, duration_s, 0.02, 0.1, 0.9, 0.02, sample_rate)

    return normalize(out)


# ---------------------------------------------------------------------------
# 4. enemy_shoot — Disparo naves enemigas, "más opaco", 0.3s
# ---------------------------------------------------------------------------
def render_enemy_shoot(
    duration_s: float = 0.3,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 5,
) -> Tuple[array.array, int]:
    """Enemy ship shot — opaque / lo-fi (intentionally bitcrushed).

    Sound: Square wave with downward pitch slide (240 → 130 Hz) +
    sub-sine 80 Hz for body + transient click. Bit-crushed to 6-bit
    at quarter sample rate. Less crisp than your ship's shots — the
    enemy uses older, cheaper weapons.

    Returns:
        (signal_array, 11025) — write WAV at 11025 Hz to preserve
        the original 0.3s duration.
    """
    rng = random.Random(seed)
    n = int(duration_s * sample_rate)
    out = empty_buffer(n)

    # Voice 1: square con slide descendente 240 → 130 Hz
    for i in range(n):
        t = i / sample_rate
        freq = 240.0 - 380.0 * t  # 240 → ~130 en 0.3s
        v = 0.0
        for mult, amp in SQUARE_PARTIALS:
            v += amp * math.sin(TWO_PI * freq * mult * t)
        out[i] = int(max(INT16_MIN, min(INT16_MAX, v * 32767.0 * 0.55)))

    # Sub-sine 80 Hz (body, slide down)
    sub = _sine_voice(80.0, duration_s, sample_rate, amp=0.4)
    # Slide del sub también
    for i in range(n):
        t = i / sample_rate
        sub[i] = int(sub[i] * (1.0 - 0.4 * t))
    mix_at(sub, out, 1.0)

    # Click inicial
    click = render_click(0.01, sample_rate, rng, amp=1.2)
    mix_at(click, out, 1.0)

    # ADSR — attack rápido, decay rápido
    out = apply_envelope(out, duration_s, 0.002, 0.06, 0.0, 0.15, sample_rate)

    # Soft saturation (warmth + grit)
    out = soft_saturate(out, drive=2.0)

    # Lowpass 800 Hz (corta agudos)
    out = lowpass_1pole(out, 800.0, sample_rate)

    # LO-FI: downsample a 1/4 + 6-bit crush
    out = downsample(out, factor=4)
    out = bit_crush(out, target_bits=6)
    out = normalize(out)

    return out, sample_rate // 4


# ---------------------------------------------------------------------------
# 5. engine_hum — Idle engine hum (MOVE/IDLE state, loop-friendly)
# ---------------------------------------------------------------------------
def render_engine_hum(
    duration_s: float = 2.0,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int = 6,
) -> array.array:
    """High-tech idle engine hum (Star Fox Arwing at cruise).

    Sound: A chord of sine waves (50/100/150/200/300 Hz) gives a
    clean, electronic "powered on" feel. A subtle filtered pink
    noise (high-passed) adds electrical texture. A 0.5 Hz LFO
    gently modulates amplitude. Reverb comb-filter adds size.
    The volume scales with |vx|/130 per GDD §9 — this preview
    is at baseline. The result is a calm, high-tech drone —
    not a 16-bit saw stack.
    """
    rng = random.Random(seed)
    n = int(duration_s * sample_rate)
    out = empty_buffer(n)

    # Chord of sines (clean fundamentals, no harmonics = high-tech feel)
    freqs_amps = [
        (50.0, 0.35),   # sub
        (100.0, 0.45),  # fundamental
        (150.0, 0.25),  # fifth
        (200.0, 0.20),  # octave
        (300.0, 0.12),  # fifth up (aire)
    ]
    for freq, amp in freqs_amps:
        v = _sine_voice(freq, duration_s, sample_rate, amp=amp)
        mix_at(v, out, 1.0)

    # Subtle high-passed pink noise (electrical texture)
    noise = render_noise(duration_s, sample_rate, rng, color="pink")
    noise = highpass_1pole(noise, 2000.0, sample_rate)
    mix_at(apply_amp(noise, 0.06), out, 1.0)

    # 0.5 Hz gentle amplitude LFO
    out = apply_lfo_amp(out, 0.5, 0.10, sample_rate)

    # Soft saturation (warmth)
    out = soft_saturate(out, drive=1.2)

    # Reverb comb (size, very subtle)
    out = comb_filter(out, delay_s=0.05, feedback=0.25, sample_rate=sample_rate)

    # Lowpass doma el high-passed noise
    out = lowpass_1pole(out, 5000.0, sample_rate)

    # ADSR loop-friendly (seamless)
    out = apply_envelope(out, duration_s, 0.02, 0.08, 0.9, 0.02, sample_rate)

    return normalize(out)


# ---------------------------------------------------------------------------
# Catalog (5 new SFX, keyed by name)
# ---------------------------------------------------------------------------
NEW_SFX_RECIPES = {
    "warning_miniboss": render_warning_miniboss,
    "warning_boss": render_warning_boss,
    "propulsion": render_propulsion,
    "enemy_shoot": render_enemy_shoot,
    "engine_hum": render_engine_hum,
}
