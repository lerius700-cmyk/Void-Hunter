# REPORT — SFX Render Iter 3 (warning_miniboss rebuilt with Star Fox 64 boost DNA)

> **Iter 3 — warning_miniboss rebuilt:** user said iter 2 sounded like
> "a phone ringing". Replaced the alternating tone klaxon with a
> **military threat detection alarm** inspired by the Star Fox 64
> Arwing boost sound (rising pitch sweep + whoosh + transient + body).
> See warning_miniboss section below.
>
> The other 4 SFX (warning_boss, propulsion, enemy_shoot, engine_hum)
> are unchanged from iter 2 — user did not flag them.

## Lo que cambió vs iter 1

| Aspecto | Iter 1 (16-bit MD) | Iter 2 (Star Fox) |
| --- | --- | --- |
| Fundamental base | Saw/triangle 880-1175 Hz klaxon | Triangle + sub-octave + 100 Hz sub-bass sine |
| Reverb | (ninguno) | Comb filter 0.045-0.06s con 0.25-0.45 feedback |
| Saturación | (ninguna) | Soft saturation drive 1.2-2.0 |
| Transients | Solo click inicial | Click + sweep gates en cada cambio de tono |
| Boss warning | 1.5 Hz LFO sweep simple | 3 sweeps dramáticos con transient click al peak + air-raid noise 1.5-4 kHz + 40 Hz sub rumble |
| Engine hum | Square + triangle 8-bit style | Sine chord (50/100/150/200/300 Hz) + high-passed noise — high-tech feel |
| Propulsion | 3 detuned saws + sub + tri | Bandpass noise sweep + 50 Hz sub + 200 Hz saw, con LFO 4 Hz en amplitud |

## Spectral analysis (DFT, sin numpy)

| SFX | Centroid | Loudness RMS | Top freqs (Hz) | Notable |
| --- | --- | --- | --- | --- |
| `warning_boss`     | **161 Hz** | -10.6 dBFS | 40, 80, 200, 160 | sub-bass rumble domina — cinematic |
| `warning_miniboss` | **215 Hz** *(iter 3)* | -8.1 dBFS  | 55, 100, 200, 300, 400 | **sub-bass 55 Hz DOMINA** (mag 7586) — militar, no ring |
| `propulsion`       | **252 Hz** | -6.3 dBFS  | 100, 200, 300, 400, 500 | air + harmonics del filter sweep |
| `enemy_shoot`      | **220 Hz** | -15.4 dBFS | 80, 220, 65, 55 | sub-sine body + lo-fi square |
| `engine_hum`       | **207 Hz** | -7.1 dBFS  | 100, 200, 300, 250, 500 | chord of sines — high-tech |

### Iter 2 vs Iter 3 — warning_miniboss comparison

| | Iter 2 (phone ring) | Iter 3 (boost detection) |
| --- | --- | --- |
| Centroid | 642 Hz (high, bright) | 215 Hz (low, weighty) |
| Sub-bass 55 Hz magnitude | 3051 | **7586** (dominant) |
| D6 (1175 Hz) magnitude | 2740 | very low (sweep averages it) |
| Crest factor | 7.9 dB | 6.7 dB |
| Character | alternating pure tones (ring) | rising sweep + transient + sub (boost) |

### Loop seamlessness (propulsion, engine_hum)

Loop ratio = (first 100 samples RMS) / (last 100 samples RMS). 1.0 = perfecto.
- `propulsion`: 1.20x (bueno, imperceptible click)
- `engine_hum`:  1.01x (casi perfecto, seamless)

## What to listen for

### 1. `warning_miniboss.wav` (SubBossIntroScene — 2.5s yellow klaxon) — **ITER 3 REBUILT**

Concept: **military spaceship threat detection** (Star Fox 64 boost DNA).

NOT a phone ring (the user explicitly flagged iter 2 as "phone ring").
Each pulse is a mini Arwing boost: rising pitch sweep + transient thump
+ sub-bass weight.

Pulse structure (6 pulses/second = 6 Hz, matches the 6 Hz visual pulse
of SubBossIntro):
- **0.00-0.02s of each pulse:** hard transient — noise click + body thump
  sweeping 80→50 Hz (the "detection hit" feel)
- **0.02-0.13s of each pulse:** rising pitch sweep 450→1600 Hz
  (exponential curve, the iconic Star Fox 64 boost character)
- **0.13-0.167s of each pulse:** silence (gap between pulses)

Layers:
- **Sub-bass 55 Hz sine CONSTANT** (military weight — dominant in mix)
- **Saw 100 Hz CONSTANT** (body / presence)
- **6 pulses/s** of transient + rising sweep (the "detection alarm")
- **Reverb comb 0.04s, 0.35 feedback** (sci-fi space)
- **Soft saturation drive 1.3** (analog warmth)
- **Lowpass 4000 Hz** (tame brightness)
- **ADSR**: A 0.005, D 0.05, S 0.9, R 0.1

Why it sounds different from iter 2 (phone ring):
- Iter 2: alternating pure tones (A5 / D6) — that's a phone ring pattern
- Iter 3: rising sweep with body thumps + dominant sub-bass — that's a
  boost / detection alarm pattern

### 2. `warning_boss.wav` (BossIntroScene — 4.5s red siren)
- **3 sweeps dramáticos** rising 80→220 Hz en 1.5s cada uno (no beep continuo)
- 2 saws desentonados (chorus) para cuerpo
- **Sub-bass 40 Hz sine con LFO 0.67 Hz en amplitud** (el "respirar" Star Fox)
- Sub-bass 80 Hz (fifth, presencia grave)
- Bandpass noise 1500-4000 Hz (air-raid texture)
- **Click transient en cada peak de sweep** (3 clicks, uno por sweep)
- 8 Hz amp LFO (visual pulse)
- Reverb comb 0.06s, 0.45 feedback (cinematic size)
- Soft saturation drive 1.6 (analog warmth)
- ADSR: attack 0.02, decay 0.3, sustain 0.9, release 0.6 (largo, dramático)

### 3. `propulsion.wav` (Player PROPULSION state — shift held)
- **Bandpass white noise 200-1200 Hz** (el "air rushing" de un jet real)
- Sub-bass 50 Hz sine con LFO 4 Hz
- Mid saw 200 Hz (presencia)
- Sub-octave saw 100 Hz (cuerpo)
- 4 Hz amp LFO (throb del motor)
- Soft saturation drive 1.5
- Reverb comb 0.04s, 0.3 feedback
- Lowpass 1500 Hz
- Loops seamlessly (1.20x ratio)

### 4. `enemy_shoot.wav` (every enemy attack pattern)
- Square wave 240→130 Hz slide
- **Sub-sine 80 Hz con slide también** (más cuerpo que iter 1)
- Click inicial fuerte
- Soft saturation drive 2.0 (grit)
- 6-bit + quarter sample rate (11025 Hz)
- Total: 0.3s grungy shot, suena como arma más barata/antigua que la del player

### 5. `engine_hum.wav` (Player MOVE/IDLE state)
- **Chord de sines**: 50/100/150/200/300 Hz (no saw — más "high-tech")
- High-passed pink noise 2 kHz+ (textura eléctrica sutil)
- 0.5 Hz amp LFO (gentle throb)
- Soft saturation drive 1.2
- Reverb comb 0.05s, 0.25 feedback
- Loops seamlessly (1.01x ratio — casi perfecto)
- Volumen escala con |vx|/130 per GDD §9 (en el gameplay code)

## Cómo están construidos (técnica)

Motor: `src/audio/synth_16bit.py` (expanded en iter 2 con `comb_filter` y `soft_saturate`).
Recetas: `src/audio/sfx_16bit_recipes.py` (re-escritas en iter 2).

Técnicas en uso:
- **Wavetable synthesis** (suma de senos con parciales) para saw/triangle
- **Sine voices limpias** para sub-bass y high-tech hum
- **Multi-voice layering** con detune para chorus
- **1-pole analog filters** (lowpass, highpass, sweep)
- **Comb filter reverb** (Schroeder) para "size" — `delay=0.04-0.06s, feedback=0.25-0.45`
- **Soft saturation** (tanh approx) para warmth/analog feel — `drive=1.2-2.0`
- **LFO modulation** en amplitud y frecuencia (sirens, throbs)
- **Bit-crush + downsample** para lo-fi del enemy shoot
- **Transient noise clicks** gateados a eventos
- **ADSR per-SFX**, extra-corto attack/release para loops seamless

Todo pure stdlib (`array.array`, `math`, `random`, `wave`). GDD §0 preserved.

## Iterate

Si todavía no da en el blanco, decime:
- **"[name] más [dirección]"** (ej: "warning_boss más intenso", "propulsion más jet", "engine_hum más sci-fi")
- **Referencia específica** (ej: "quiero que el propulsion suene como [video/game/audio]")

Si me pedís un approach completamente distinto (samples externos, IA, etc.), también decímelo.
