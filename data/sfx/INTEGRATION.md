# INTEGRATION — step-by-step for the next agent

This is the technical plan to wire the 5 new WAVs into the audio engine.
The other agent should follow these steps in order, verifying after each.

## Goal

1. The 5 new SFX load from `data/sfx/*.wav` at runtime.
2. The 5 new SFX play from the correct call sites.
3. If a WAV is missing, the engine falls back to procedural (degrade gracefully).
4. All existing tests still pass; new tests cover the 5 new SFX.

## Step 0: Verify the WAVs

```bash
ls -la data/sfx/  # should show 5 .wav + README.md + MANIFEST.md + REPORT.md + INTEGRATION.md
```

Open each WAV in any audio player (Windows Media Player, VLC, etc.)
and confirm the sounds match `REPORT.md`. If user has not said "listo",
**stop here and ask for approval**.

## Step 1: Add new SFX_CATALOG entries (catalog presence)

Even if the actual audio comes from disk, the catalog needs the names
so the rest of the code can reference them.

In `src/audio/synth.py`, **append** these entries to `SFX_CATALOG`:

```python
"warning_boss": _SfxSpec("warning_boss", Voice.SAW, 130, 0, 0.01, 0.3, 0.7, 0.5, 4.5, "Boss warning siren (16-bit)", 0.9),
"warning_miniboss": _SfxSpec("warning_miniboss", Voice.TRIANGLE, 880, 0, 0.005, 0.08, 0.7, 0.2, 2.5, "Sub-boss warning klaxon (16-bit)", 0.7),
"propulsion": _SfxSpec("propulsion", Voice.SAW, 80, 0, 0.02, 0.1, 0.9, 0.02, 2.0, "Engine thruster hum (16-bit, loop)", 0.6),
"enemy_shoot": _SfxSpec("enemy_shoot", Voice.SQUARE, 220, -280, 0.002, 0.06, 0.0, 0.15, 0.3, "Enemy shot (16-bit, lo-fi)", 0.5),
"engine_hum": _SfxSpec("engine_hum", Voice.TRIANGLE, 110, 0, 0.02, 0.08, 0.9, 0.02, 2.0, "Engine idle hum (16-bit, loop)", 0.3),
```

These are the FALLBACK recipes — they only render if the WAV is missing.
The values were chosen to mimic the 16-bit versions at a basic level.

**Why 5 entries?** `SFX_NAMES` is used in `test_all_expected_sfx_present`
and `_prebake_all` to know which sounds to prebake. Adding them keeps
the catalog consistent.

## Step 2: Wire AudioEngine to load from disk with fallback

In `src/audio/synth.py`, **modify** `AudioEngine._prebake_all`:

```python
def _prebake_all(self) -> None:
    """Render SFX (or load from data/sfx/*.wav) and wrap as pygame.mixer.Sound."""
    if not self.mixer_available:
        return
    rng = random.Random(42)
    for name in SFX_NAMES:
        wav_path = Path(__file__).resolve().parent.parent.parent / "data" / "sfx" / f"{name}.wav"
        if wav_path.exists():
            try:
                sound = pygame.mixer.Sound(str(wav_path))
                self.sfx_sounds[name] = sound
                continue
            except pygame.error:
                pass  # fall through to procedural
        # Fallback: procedural
        buf = render_sfx(name, rng)
        self.sfx_buffers[name] = buf
        try:
            sound = pygame.mixer.Sound(buffer=buf.tobytes())
            self.sfx_sounds[name] = sound
        except pygame.error:
            pass
```

For BGM, keep the existing procedural rendering (no change).

## Step 3: Update call sites

### 3a. `boss_warning` → `warning_boss` (BossIntroScene)

File: `src/ui/scenes.py`, line 206.

```python
# Before
audio.play_sfx("boss_warning", volume=0.9)
# After
audio.play_sfx("warning_boss", volume=0.9)
```

### 3b. `boss_warning` → `warning_miniboss` (SubBossIntroScene)

File: `src/ui/scenes.py`, line 352.

```python
# Before
audio.play_sfx("boss_warning", volume=0.7)
# After
audio.play_sfx("warning_miniboss", volume=0.7)
```

### 3c. Add `propulsion` loop (PROPULSION state)

File: `src/ui/gameplay_runtime.py` around line 2315.

```python
# After _start_bgm / _stop_bgm, add tracking:
self._propulsion_channel: Optional[pygame.mixer.Channel] = None

# In the player state update where PROPULSION is detected:
if self._player.state == PlayerState.PROPULSION:
    if self._propulsion_channel is None or not self._propulsion_channel.get_busy():
        sound = self._audio.sfx_sounds.get("propulsion") if self._audio else None
        if sound is not None:
            self._propulsion_channel = sound.play(loops=-1)
elif self._propulsion_channel is not None:
    self._propulsion_channel.stop()
    self._propulsion_channel = None
```

### 3d. Add `enemy_shoot` for every enemy attack

File: `src/entities/enemies/enemy.py`, `Enemy.attack()` (or wherever
the enemy actually fires a bullet). The user wants this to play for
EVERY enemy attack pattern. Find the bullet-spawn point and add:

```python
if hasattr(self, "_on_fire_sfx") and self._on_fire_sfx:
    self._on_fire_sfx()  # injected by the gameplay scene
```

Or simpler: the gameplay scene can subscribe to enemy fire events via
the event bus. Pick whichever pattern matches the existing code style.

### 3e. Add `engine_hum` loop with velocity-scaled volume

File: `src/ui/gameplay_runtime.py` (where player velocity is read each frame).

```python
# Tracking:
self._engine_hum_channel: Optional[pygame.mixer.Channel] = None

# Each frame, after player update:
vx = abs(self._player.vx)  # or however the runtime reads velocity
target_vol = 0.3 + 0.4 * (vx / 130.0)
if self._player.state in (PlayerState.MOVE, PlayerState.IDLE):
    if self._engine_hum_channel is None or not self._engine_hum_channel.get_busy():
        sound = self._audio.sfx_sounds.get("engine_hum") if self._audio else None
        if sound is not None:
            self._engine_hum_channel = sound.play(loops=-1)
    if self._engine_hum_channel is not None:
        self._engine_hum_channel.set_volume(target_vol * self._audio.master_volume)
else:
    if self._engine_hum_channel is not None:
        self._engine_hum_channel.stop()
        self._engine_hum_channel = None
```

## Step 4: Update tests

In `tests/test_audio_synth.py`:

- `test_twenty_six_sfx_in_catalog` → `test_thirty_one_sfx_in_catalog`
  (26 + 5 new)
- `test_all_expected_sfx_present` → add the 5 new names
- Add `test_audio_engine_loads_wav_from_disk` (mock `data/sfx/shoot.wav`
  existing → assert it loads; missing → assert procedural fallback).
- Add `test_warning_boss_is_different_from_boss_warning` (spectral check
  or just duration check).

## Step 5: Verify

```bash
pytest -q                                      # all tests pass
python main.py --check                         # imports + scene wiring OK
python main.py --profile                       # run game, listen to new SFX in context
```

## Step 6: Update GDD

In `docs/design/void-hunter-gdd.md` §9, update the SFX table:
- Remove `boss_warning` (deprecated)
- Add `warning_boss`, `warning_miniboss`, `propulsion`, `enemy_shoot`, `engine_hum`
- Note that they load from `data/sfx/*.wav` with procedural fallback

## Step 7: Commit

```bash
git add data/sfx/ src/audio/synth.py src/audio/sfx_16bit_recipes.py src/audio/synth_16bit.py src/ui/scenes.py src/ui/gameplay_runtime.py tests/test_audio_synth.py docs/design/void-hunter-gdd.md
git commit -m "feat(audio): 16-bit overhauls for 5 new SFX (warning_boss, warning_miniboss, propulsion, enemy_shoot, engine_hum)"
```
