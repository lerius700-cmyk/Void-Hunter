# MANIFEST — explicit mapping for the next agent

This is the source of truth for the other agent to do the integration.
If anything in the codebase has changed since this file was written,
treat the codebase as authoritative and update this manifest.

## 1. WAV → SFX catalog slot

Every file in this folder is named after the SFX catalog key it should
take (or augment) in `src/audio/synth.py::SFX_CATALOG`.

| File | SFX key | Status | Duration | SR | Loops? | Recipe in |
| --- | --- | --- | --- | --- | --- | --- |
| `warning_boss.wav`     | `warning_boss`     | NEW   | 4.50 s | 44100 Hz | no  | `sfx_16bit_recipes.py::render_warning_boss` |
| `warning_miniboss.wav` | `warning_miniboss` | NEW   | 2.50 s | 44100 Hz | no  | `sfx_16bit_recipes.py::render_warning_miniboss` |
| `propulsion.wav`       | `propulsion`       | NEW   | 2.00 s | 44100 Hz | yes (1.17x) | `sfx_16bit_recipes.py::render_propulsion` |
| `enemy_shoot.wav`      | `enemy_shoot`      | NEW   | 0.30 s | **11025 Hz** (lo-fi) | no | `sfx_16bit_recipes.py::render_enemy_shoot` |
| `engine_hum.wav`       | `engine_hum`       | NEW   | 2.00 s | 44100 Hz | yes (1.30x) | `sfx_16bit_recipes.py::render_engine_hum` |

> **Note on `enemy_shoot.wav`:** the WAV is written at 11025 Hz instead
> of 44100 Hz. This is **intentional** — it preserves the 0.3s duration
> while giving the lo-fi "opaque shot" feel via quarter-rate + 6-bit
> quantization. The AudioEngine must load this file with its native
> sample rate (11025 Hz), not resample to 44100.

## 2. SFX call sites in gameplay code

The current 8-bit code calls these SFX in the following places.
**Update them** to use the new names where indicated.

| Current call | File:Line | What to change |
| --- | --- | --- |
| `audio.play_sfx("boss_warning", volume=0.9)` | `src/ui/scenes.py:206` (BossIntroScene.on_enter) | Change to `audio.play_sfx("warning_boss", volume=0.9)` |
| `audio.play_sfx("boss_warning", volume=0.7)` | `src/ui/scenes.py:352` (SubBossIntroScene.on_enter) | Change to `audio.play_sfx("warning_miniboss", volume=0.7)` |
| (no current call — needs to be added) | n/a | Add `audio.play_sfx("propulsion", volume=0.6)` loop when player enters `PlayerState.PROPULSION` (currently in `src/ui/gameplay_runtime.py` ~ line 2315: `if self._player.state == PlayerState.PROPULSION:`). Loop with `pygame.mixer.Sound(loops=-1)` and stop on PROPULSION exit. |
| (no current call — needs to be added) | n/a | Add `audio.play_sfx("enemy_shoot", volume=0.5)` in `src/entities/enemies/enemy.py` `Enemy.attack()` for every attack pattern (8 patterns). |
| (no current call — needs to be added) | n/a | Add `audio.play_sfx("engine_hum", volume=0.3 + 0.4*|vx|/130, loops=-1)` per GDD §9. Currently the engine hum described in the GDD does not exist. Wire it to the player's `MOVE` state in `src/ui/gameplay_runtime.py`. Volume scales with horizontal velocity. |

## 3. What stays the same

These 26 existing 8-bit SFX names are **unchanged** by this delivery.
They will be overhauled in **Entrega 2** (next iteration, after this
preview is approved):

```
shoot, shoot_charged, hit, explode_small, explode_medium, explode_boss,
bomb, powerup, dash, multiplier_up, boss_phase_change, wave_cleared,
act_clear, game_over, victory, ui_click, ui_hover, charge_loop,
beam_charge, beam_fire, missile_lock, missile_fire, screen_shake_thump,
laser_continuous, laser_end, boss_warning  (last one deprecated after migration)
```

## 4. Files referenced from this folder

When integrating, the AudioEngine should:
1. Try to load `data/sfx/<name>.wav`
2. If found → use it
3. If missing → fall back to the procedural recipe from `sfx_16bit_recipes.py` (or for the 26 old ones, from the existing `synth.py` catalog)

This way, the system degrades gracefully and the user can drop in
custom WAVs by overwriting files in this folder.

## 5. Test impact

`tests/test_audio_synth.py` has these relevant assertions that may need updates:

- `test_twenty_six_sfx_in_catalog` — currently expects `len(SFX_CATALOG) == 26`.
  After integration, catalog should have **31** (26 + 5 new).
  Update the test count and the `test_all_expected_sfx_present` set.
- The 5 new SFX don't need procedural recipes in SFX_CATALOG if the
  AudioEngine only loads them from disk. Decide based on architecture.
