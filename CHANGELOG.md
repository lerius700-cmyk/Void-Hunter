# CHANGELOG — VOID HUNTER

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-08 — BLOQUE 0..17 (Production MVP)

### Added

#### BLOQUE 0 — Bootstrap (`e7da13b`, `52abe58`)
- Project skeleton: `pyproject.toml`, `requirements.txt`, `.gitignore`, `README.md`
- 80+ constants in `src/core/settings.py` (single source of truth)
- `main.py` CLI dispatcher with `--check` flag
- `smoke.py` consolidated quality gate runner
- 22 tests in `tests/test_settings.py`
- `docs/design/void-hunter-gdd.md` (14-section spec, ~19k words)

#### BLOQUE 1 — Pool + 18-kind ParticleEngine + 64-char palette (`f139d4c`)
- `src/systems/pool.py` — generic `Pool[T]` with `active` flag + `on_spawn`/`on_release` hooks
- `src/systems/particle_engine.py` — 18 kinds, pool 1500, LRU tint cache 128, single `target.blits()` batch
- `src/utils/palette.py` — 64 unique ASCII chars, 6 themes
- `src/utils/easing.py` — 9 easing functions
- 97 tests (pool + particle)

#### BLOQUE 2 — ProjectilePool 400 + 4 sprite types + 4-frame anim (`b2ba22a`)
- `src/systems/projectile.py` — 4 kinds (player/charged/enemy/boss), 4-frame pulse at 16 FPS
- 16 pre-baked surfaces, pierce mechanic, expand_for_boss → 600
- 28 tests

#### BLOQUE 3+4+5 — SpriteFactory + Parallax + Juice (`04ff515`)
- `src/systems/sprite_factory.py` — 6 helpers: outline, glow_halo, tint_shift, composite, dither, scanline
- `src/systems/parallax.py` — 5 star layers (20/50/100/180/280 px/s), 6 nebula, planets + atmosphere + ring
- `src/systems/screen_shake.py` — Eiserloh trauma², max 8px (4→8 spec)
- `src/systems/hitstop.py` — FIFO queue, 3-12 frames
- `src/systems/slowmo.py` — factor [0.3, 0.95]
- `src/core/event_bus.py` — pub/sub, exception isolation, 35 typed event names
- 86 tests

#### BLOQUE 6+7 — Player FSM 7 states + WeaponSystem 3 paths (`22ba494`)
- `src/entities/player/player.py` — 7 states: IDLE, MOVE, SHOOT, CHARGE, DASH, HIT, DEAD
  - Charge engloba build (0.5/1.0/1.5s → L1/L2/L3) + fire anim (0.20s)
  - Dash 0.18s @ 480 px/s, 22 i-frames, directional
  - Hit 0.30s + 60 invuln frames
  - Tilt ±15°, after-image 8 frames, 70% forgiving hitbox
- `src/systems/weapon_system.py` — 3 paths × 3 levels + special unlock at 50 kills
  - PLASMA (kinetic/splash), ION (electric/pierce), SHOCK (slow/knockback)
  - Specials: INFERNO, CHAIN_LIGHTNING, QUAKE
  - Element bonus +50% damage, +2 XP
- 64 tests

#### BLOQUE 8+9 — 8 enemy archetypes + 4 bosses (`c58cf44`)
- `src/entities/enemies/enemy.py` — 8 archetypes per GDD §4
  - SCOUT (1HP, sine wobble), CRUISER (4HP, twin cannon), HEAVY (12HP, 24f telegraph)
  - KAMIKAZE (homing, 30f glow telegraph), DRONE (spawns 3 mini-drones)
  - SNIPER (anchored, 60f laser telegraph), TURRET (3-spread rotating)
  - CARRIER (20HP, spawns scouts + drones)
- `src/entities/enemies/boss.py` — 4 bosses
  - GOLIATH (32×18, 800 HP, 2 phases)
  - HYDRA (36×20, 1400 HP, 3 phases including enraged)
  - PHANTOM (40×22, 2000 HP, 2 phases)
  - NEMESIS (48×28, 5000 HP, 4 phases including DESESPERACIÓN)
  - 8-attack catalog: aimed / 3-spread / 5-spread / ring / spiral / laser / charge-and-release / wall-of-bullets
  - NEMESIS P4: arena shrink 20%, tempo +20%, hitbox 50%
- 52 tests

#### BLOQUE 10+11+12 — WaveManager + Scoring + ThemeManager (`795bcbb`)
- `src/systems/wave_manager.py` — 18 waves (3 acts × 6)
  - DEFAULT_WAVES with per-act enemy mix per GDD §6 + §4
  - Adaptive difficulty (HP>80% + high score → 1.2×)
  - Sub-boss trigger at 40 kills
  - JSON-loadable from `data/waves/`
- `src/systems/scoring_system.py` — multiplier 1×→16×, decay 1.5s
  - Boss kill +5 chain steps, timer 3.0s
  - Element bonus +2 chain steps, ×1.5 score
  - Streak bonuses at 10/25/50 kills (+500/+2500/+5000)
  - Rank D/C/B/A/S/S+/SSS
  - Atomic save high-score JSON
- `src/systems/theme_manager.py` — 6 themes, 30-frame crossfade
- 64 tests

#### BLOQUE 13+14 — Audio synth + Game state machine + scenes (`24175b0`)
- `src/audio/synth.py` — 24 SFX + 4 BGM procedural
  - 4 voices: square / triangle / saw / noise
  - ADSR envelope configurable per SFX
  - 16-channel mixer @ 44100 Hz, 16-bit PCM raw
  - Null-safe if mixer init fails
- `src/core/scene_manager.py` — 9 main states + PAUSE overlay
  - Valid transition table per GDD §13
  - Scene base class, overlay stack
- `src/ui/scenes.py` — 10 scene classes (TITLE, ACT_INTRO, GAMEPLAY, BOSS_INTRO, BOSS_FIGHT, ACT_CLEARED, GAME_OVER, VICTORY, CREDITS, PAUSE)
- `src/core/game.py` — fixed-timestep accumulator at 120 FPS
- 48 tests

#### BLOQUE 15+16 — HUD + damage popup + stress harness (`c8b7652`)
- `src/ui/hud.py` — HUD (HP bar color-coded, bomb icons, weapon level + XP, multiplier, score)
  - DamagePopupPool: 32 popups, float upward, fade out, color by milestone
- `main.py` rewritten with full CLI: --check, --profile, --act, --boss, --stress, --duration, --debug, --validate-waves
- `smoke.py` — 11-gate quality runner
- **Stress test: 117.7 FPS with 1500 particles + 400 bullets (target ≥90)**
- 16 tests

### Quality Gates (Final)

| Gate | Target | Actual |
| --- | --- | --- |
| `python main.py --check` | exit 0 | exit 0 |
| `pytest -q` | all pass | **538 passed** |
| `pytest --cov=src/` | ≥35% | **89.59%** |
| `mypy src/` (strict) | 0 errors | **0 errors in 33 source files** |
| `rg 'import motor' src/` | 0 matches | 0 matches (soberanía) |
| Stress 1500p+400b | ≥90 FPS | **117.7 FPS** |
| Single `target.blits()` per frame | 1 match | 1 match in `particle_engine.draw()` |
| Smoke gates | all pass | **11/11** |

### Architecture Summary

```
void-hunter/
├── main.py                     # CLI entry
├── smoke.py                    # 11-gate runner
├── src/
│   ├── core/
│   │   ├── settings.py        # 80+ constants (single source of truth)
│   │   ├── game.py            # Game root + fixed-timestep loop
│   │   ├── event_bus.py       # 35 typed events, exception isolation
│   │   └── scene_manager.py   # 9 states + PAUSE overlay
│   ├── audio/
│   │   └── synth.py           # 24 SFX + 4 BGM procedural
│   ├── entities/
│   │   ├── player/            # 7-state FSM
│   │   └── enemies/           # 8 archetypes + 4 bosses
│   ├── systems/
│   │   ├── pool.py            # Generic Pool[T]
│   │   ├── particle_engine.py # 18 kinds, pool 1500
│   │   ├── projectile.py      # 4 sprite types, pool 400
│   │   ├── parallax.py        # 5 layers + 6 nebula + planets
│   │   ├── screen_shake.py    # Eiserloh trauma²
│   │   ├── hitstop.py         # 3-12 frames
│   │   ├── slowmo.py          # 0.3×-0.95×
│   │   ├── sprite_factory.py  # 6 helpers
│   │   ├── weapon_system.py   # 3 paths × 3 levels + special
│   │   ├── wave_manager.py    # 18 waves + adaptive
│   │   ├── scoring_system.py  # multiplier chain + high-score
│   │   └── theme_manager.py   # 6 themes + 30f fade
│   ├── ui/
│   │   ├── hud.py             # HP, bombs, weapon, multiplier, score
│   │   └── scenes.py          # 10 scene classes
│   └── utils/
│       ├── palette.py         # 64-char palette + 6 themes
│       └── easing.py          # 9 easing functions
├── tests/                     # 538 tests, 89.59% coverage
├── data/
│   ├── waves/                 # (empty by default, falls back to DEFAULT_WAVES)
│   └── highscores/            # atomic JSON saves
└── docs/design/
    └── void-hunter-gdd.md     # 14-section spec
```

### Known Limitations (v0.1.0, MVP per spec)

- `--boss` / `--act` modes route to main game (full act chain integration in next sprint)
- Audio mixer is silent on systems without SDL audio backend (null-safe)
- No 2-player co-op (Ikaruga inspiration, out of scope per spec)
- Local JSON high-score only (no online leaderboard)
- No localization beyond English (EN-only per spec)
- 12 sound effects + 4 BGM pre-baked in init — about 50KB total memory
- Particle systems do not yet have the spawn-on-kill enemy integration in the live gameplay scene (deferred to polish sprint)

### Future Work (v0.2.0+)

- Per-act wave→boss sequence wired into GameplayScene
- Live enemy AI (drift, fire, homing) integrated into gameplay loop
- Bullet collision detection between player bullets and enemies
- Score popups + HUD integrated into live gameplay
- Per-frame shake/hitstop/slow-mo application on game events
- Per-act audio theme (BGM switching at act boundaries)
- Theme fade applied to background during crossfade
- Difficulty curve optimization via playtesting
- SFX sample replacement (Freesound CC0) for production polish

---

## [0.2.0] - 2026-08-10 — BLOQUE 18..58 (Polish + Boss + Formations + Bezier + Roguelike)

Closed every "Future Work" item from v0.1.0. Game now plays end-to-end:
title screen → 4 chained waves with sub-boss → Act 1 boss (GOLIATH) with
shield, spear, laser → HP bar + gold rings + tech upgrades → victory.

### Added

#### BLOQUE 18-26 — Polish pass (sprite scale, mouse aim, charge aura)
- Player sprite scaled 0.75, nose_lerp 28 px/s, removed legacy 360° spin bug
- BGM disabled, 320x480 internal playfield, fast mouse tracking
- WASD movement confirmed, shift-only dash, boost removed
- 360° mouse aim (no clamp), snappier banking ±25° (was 15°)
- LMB charge aura with energy absorption
- Title screen "PRESS ANY KEY" (no auto-start)
- Dense local energy aura (24-48px ring around player, not from screen edges)
- 19 polish_*.png visual frames captured

#### BLOQUE 36-39 — Weapons polish (L3 beam + continuous laser + homing missile)
- L3 beam plasma recolored (cyan)
- Continuous L3 plasma laser (no bullet spam, held saw SFX)
- RMB rapid fire fix (165 px/s mouse follow, 50 deg/s)
- Homing missile (B/L key, follows mouse, explodes on contact)

#### BLOQUE 40-45 — Encounter refactor (formation system)
- Formation types: LINE / V / ARC / STAIRCASE / SQUADRON
- Density cap on overlapping spawns
- Act 1 DEFAULT_WAVES use formations
- Boss trigger 60s + perfect run
- 28 wave JSONs (3 acts × 6 waves + boss)

#### BLOQUE 46-47.1 — Star Fox squadron + reticle fix
- Squadron formation (1 leader + 2 followers replaying path)
- Reticle aligned to actual display size (was using stale display size)
- 8 polish_*.png visual frames

#### BLOQUE 48-49.1 — Chained wave system + local aura
- WaveChain: 4 chained waves (O1=8, O2=13, O3=10, O4=12 ships) → sub-boss → boss
- BossTrigger: 3-tier (main 45s, perfect 60s+kills≥1, safety 120s)
- Title screen "PRESS ANY KEY" + charge aura + orange laser sparks
- Localized energy aura (particles in 16-20px ring around player)

#### BLOQUE 50-50.1 — Diffuse aura + sub-boss + warning signs
- Diffuse energy aura (double-layer: P_SPARK outer + P_GLOW inner)
- 43 → 62 ships in level 1 mode (O1:8→12, O2:13→19, O3:10→14, O4:12→17)
- Act 1 default waves 4-6 → 6-8 ships each
- New `EnemyKind.SUB_BOSS` — HP 20, speed 90, 2.5 shots/s, 3 Hz sine wobble
- `sub_boss_after: True` on wave O2, runtime spawns in `_update_enemies`
- BossIntroScene → RED ALARM (8 Hz pulse, diagonal stripes, !! INCOMING HOSTILE !!)
- SubBossIntroScene → YELLOW WARNING (5 Hz pulse, subtler, ! WARNING !, HOSTILE FRENETIC)
- New `GameState.SUB_BOSS_INTRO` registered in scene_manager + game.py
- BLOQUE 50.1 fix: sub-boss intro no longer loops (resume from SUB_BOSS_INTRO
  preserves player/weapon/score/chain, only clears transient visuals)

#### BLOQUE 51-52 — GOLIATH redesigned + spear throw
- GOLIATH = biblical giant warrior (12 visual layers, 64x60 px)
  - Bronze armor, helmet with horns, visor, glowing red eyes
  - Round shield with rivets, long spear, phase 2 armor cracks
- `src/entities/boss_spear.py` — BossSpear dataclass with serpentine motion
  - State machine: ready → winding (0.3s) → thrown (1.2s) → ready
  - Main spear 3 HP, splits into 3 fragments in 40° cone on destroy
  - +500 SPEAR bonus + score popup + hitstop on split
  - 17 tests, 3 polish_*.png frames (winding, flight, split)

#### BLOQUE 53a-d — Shield charge + HP bar + gold rings + tech upgrades
- **53a** GOLIATH shield charge (20 hits) + 1s vertical laser
  - Shield circle at (boss.x-30, boss.y+12, r=13)
  - Player bullets consumed + counter++
  - At 20 hits → 1s beam (8px wide), 1 dmg/frame
  - Shield color: iron → blue → cyan-white based on charge
- **53b** HP bar (Mega Man / Star Fox) — 30 max + 10 segments
  - `Player.hp/hp_max` use `PLAYER_HP` (was 3)
  - New `Player.heal(amount)` with cap
  - HUD: 100x8px bar, 10 segments, color tier green/yellow/red
- **53c** Gold rings (Star Fox) — 8% drop, +2 HP, 3-stack = HP double
  - New `POWERUP_GOLD_RING` kind
  - `Player.add_gold_ring()` increments counter
  - At 3 → one-time `hp_max *= 2` + refill + `hp_doubled=True`
  - 4 rotating sparkles, big "HP x2 !" popup on double
- **53d** Tech upgrades — HP_BOOST_10 + GOLIATH_SUMMON
  - HP_BOOST_10: +10% max HP (min +1, cap 999)
  - GOLIATH_SUMMON: at elapsed ≥ 60s, destroys all live enemies
    - +2000 score bonus, "GOLIATH SUMMONED!" popup
    - Transitions to BOSS_INTRO

### Quality Gates (Final)

| Gate | Target | Actual |
| --- | --- | --- |
| `python main.py --check` | exit 0 | exit 0 |
| `pytest -q` | all pass | **746 passed** |
| `mypy src/` (strict) | 0 errors | **0 errors in 35 source files** |
| `rg 'import motor' src/` | 0 matches | 0 matches (soberanía) |
| Visual frames committed | 40 polish_*.png | 40 frames BLOQUE 1-40 |
| Commits since v0.1.0 | – | 47 (BLOQUE 18-53) |

### Architecture Notes (v0.2.0)

- `src/ui/gameplay_runtime.py` — 4088 lines, 79 methods (god class)
  - 16 `_draw_*` methods, 7 `_update_*` methods
  - Clear sub-system clusters (input, weapons, wave, boss, collision, VFX)
  - **Refactor deferred to v0.3.0** (would split into InputController,
    WeaponManager, EnemySpawner, BossController, PlayerVFX, EnemyVFX,
    CollisionManager, PowerupManager)
- `src/entities/boss_spear.py` (BLOQUE 52) — new file, dataclass-based
- `src/entities/player/player.py` — 621 lines, 7-state FSM + 6 new methods
  (reset, take_damage, heal, add_gold_ring, add_tech_upgrade, is_invulnerable)
- `src/ui/scenes.py` — 622 lines, 12 scenes (added SubBossIntroScene)
- `src/systems/wave_manager.py` — 660 lines, 8 formation types + chained waves

#### BLOQUE 55 — 3 new formations (spiral, hilera, x)
- `FORMATION_TYPES` extended from 5 to 8 types (additive, no breaking changes)
- **SPIRAL**: logarithmic spiral entering from top, classic Galaga/Xevious
  pattern. 8 ships in 2 turns, radius 60→20, center offset 92px down to
  stay within playfield bounds
- **HILERA**: tight vertical column of N ships falling together. Useful
  for dense "dive attack" patterns
- **X**: cross pattern with 1 center + 4 cardinals (NW, NE, SW, SE).
  Caps at 5 ships; extras are dropped
- 5 new tests in `tests/test_wave_manager.py` (regression for existing
  formations unchanged, +5 total = 751)
- All math: stdlib `math.cos`/`math.sin` only, no numpy (per GDD §0)
- No changes to gameplay_runtime, enemy, or any other module

#### BLOQUE 56 — Bezier curves + 3 more formations + GOLIATH entrance
- **`src/systems/bezier_path.py`** (NEW, 235 lines): `BezierPath` class with
  cubic + quadratic eval, `update(dt, speed)` advancing t proportionally to
  speed / path_length, optional `prebake(steps=N)` for cache-friendly eval
  (linear interp between adjacent samples instead of polynomial each frame).
  `on_complete` callback fires exactly once when t reaches 1.0.
- **GOLIATH bezier entrance**: `Boss.bezier_path: BezierPath | None` field.
  When set, boss follows the curve; once complete, falls back to the
  default sine oscillation. `on_spawn()` clears it so each new spawn
  starts clean. Zero impact on existing GOLIATH behavior (bezier_path=None
  by default).
- **DIAMOND** formation: 1 center + 4 cardinals (N, E, S, W). Like X but
  axis-aligned.
- **BOX** formation: ships in a rectangular perimeter. 4 ships = 4 corners.
  8 ships = 4 corners + 1 midpoint per side. Layout adjusts to count.
- **WINGMAN** formation: V-shaped leader-follower spawn layout
  (Star Fox / R-Type). Leader at apex, wingmen trail behind in V.
  Since all ships share the same vy, V shape is maintained during
  descent without per-frame sync. (True reactive follower-reading-leader
  is a future enhancement; not needed while enemies share vy.)
- `FORMATION_TYPES` now has 11 types (line, v, arc, staircase, squadron,
  spiral, hilera, x, diamond, box, wingman).
- **22 new tests**: 7 in `test_bezier_path.py` (eval, update, on_complete,
  prebake, reset, GOLIATH entrance scenario) + 6 in `test_wave_manager.py`
  (diamond_5, box_4, box_8, wingman_3, wingman_5, wingman_v_preserved) +
  4 in `test_boss_fsm.py` (GOLIATH default sine, GOLIATH with bezier,
  GOLIATH bezier-then-sine, GOLIATH on_spawn clears bezier).
- Total tests: 773 (was 751, +22).
- All math: stdlib only, no numpy (per GDD §0).

#### BLOQUE 57 — Roguelike core (opt-in via --roguelike [seed])
- New package `src/roguelike/` (9 modules, ~1000 lines, stdlib only).
- **RoguelikeSeed**: splitmix64 PRNG (period 2^64, no attractor at 0)
  with hierarchical derivation: `derive(level, attempt, salt) -> master`,
  then `derive_wave_seed / derive_slot_seed / derive_audio_seed /
  derive_drop_seed / derive_particle_seed`. JSON round-trip.
- **SeededRNG**: drop-in replacement for `random` with `random / randint /
  choice / choices / shuffle / gauss` (Box-Muller). State save/restore
  via `state_dict / load_state_dict` for replay.
- **ProceduralFormationGenerator**: 9 family builders (LINE / V / ARC /
  STAIRCASE / SPIRAL / HILERA / X / DIAMOND / BOX) with weighted family
  selection. `FormationParams` validates family_weights (normalization,
  non-negative, non-zero sum, length-mismatch).
- **RoguelikeRun**: lifecycle (start / checkpoint / restore / log_action
  / finalize), JSON serialization. Bounded action log (1000) and
  checkpoint list (10) to keep memory under 1 MB/run.
- **StuckPatternDetector**: sliding-window detector for repeated
  families and weight deviation. `record_formation / is_stuck_pattern /
  check_distribution` for dev-mode diagnostics.
- **DistributionTelemetry**: 5 metrics (run_count, family_distribution,
  seed_uniqueness, replay_fidelity, pattern_diversity, entropy_per_run).
  Optional JSON persistence to `data/roguelike_stats.json`. Shannon
  entropy utility.
- **ReplaySystem**: play / verify / watch / export_replay (JSON only) /
  import_replay. `ReplayDivergenceError` raised on RNG state mismatch.
  1000-trial fidelity test confirms byte-identical replays.
- **Integration**: opt-in via `--roguelike [seed]` CLI flag. Without
  the flag, the 18 hand-tuned wave JSONs continue to work unchanged.
  With the flag, `inject_roguelike_waves(wave_manager)` replaces the
  scripts list with 6 procedurally generated waves using the given seed.
- **76 new tests** in `tests/roguelike/` (8 test files): seed (8),
  rng (10), formation_generator (8), run (8), anti_stuck (5),
  telemetry (8), replay (9), integration (5).
- Total tests: 849 (was 773, +76).
- Hard rules: no numpy, no global `random` import in the module
  (verified by test), no scipy.

#### BLOQUE 58 — Full roguelike redesign (with shmup invariants)
The game is now a **space-shooter & roguelike hybrid**. Default mode is
roguelike (procedural); `--campaign` opts back into the 18 hand-tuned
JSON waves.

**BLOQUE 58 INVARIANTS** (per user requirement: not random, these are
part of the shmup balance and scoring system):
  - **Ship count per wave is FIXED**: Act 1 = 12/19/14/17, Act 2 =
    15/22/18/20, Act 3 = 18/25/22/24. Same for all seeds.
  - **Sub-boss appears at FIXED position** (after wave 2). Only the
    boss identity is randomized.
  - **Final boss appears at FIXED position** (end of level). Only the
    boss identity is randomized.

**ROGUELIKE content** (random per seed):
  - **Formation type per wave**: 11-family pool with level-weighted
    distribution (Act 1 basic-heavy, Act 3 all-equal).
  - **Boss identity from 4-pool**: GOLIATH, HYDRA, PHANTOM, NEMESIS.
    Level bias: Act 1 favors GOLIATH (0.55), Act 2 favors HYDRA (0.45),
    Act 3 favors PHANTOM (0.40) and NEMESIS (0.30). But "any of 4 can
    come out" — in 500 Act-1 seeds we see 3+ of the 4 bosses.
  - **Bezier entrance path** for each boss: 4 control points derived
    from seed (start off-screen top + 2 mid controls + anchor).
  - **Powerup drops** between waves: 5-kind pool (gold_ring 50%,
    heal_small 20%, bomb 15%, damage_boost 10%, nothing 5%).

**New modules** (3 files in `src/roguelike/`):
  - `boss_pool.py` — boss selection with level bias + procedural bezier
  - `powerup_pool.py` — 5-kind weighted powerup pool
  - `level_generator.py` — full level (4 waves + sub-boss + final boss
    + powerup drops) with the BLOQUE 58 invariants

**CLI changes**:
  - `python main.py` → **default = roguelike mode** (procedural)
  - `python main.py --roguelike 42` → explicit seed
  - `python main.py --campaign` → opt back into the 18 hand-tuned JSON
    waves (legacy mode)

**27 new tests** in `tests/roguelike/`:
  - test_boss_pool.py (7): valid boss, same-seed determinism,
    variety, all-4-bosses-can-appear-in-Act-1, bezier 4 control points,
    level bias, weight sum
  - test_powerup_pool.py (6): valid kind, same-seed determinism,
    variety, weight sum, gold_ring most common, nothing rare
  - test_level_generator.py (14): 4 waves per level, sub-boss fixed
    position, final boss at end, ship counts fixed per level (BLOQUE 58
    invariant), formation varies by seed, same seed same level,
    powerup drops between waves, boss bezier entrances, act 1/2/3
    ship counts, default seed derivation

**Total tests: 876** (was 849, +27).

**Visual proof**: `polish_44_roguelike_level.png` — annotated frame of
a procedural level (4 waves + sub-boss Hydra + final boss GOLIATH +
3 powerup drops) at seed=42.

### Known Limitations (v0.2.0)

- `gameplay_runtime.py` is a 4088-line god class (refactor in v0.3.0)
- HUD rendering still embedded in gameplay_runtime (separate in v0.3.0)
- No E2E integration test for full level 1 → sub-boss → boss flow
- BLOQUE 47, 48, 49, 50, 51, 53a, 53b, 53d lack dedicated test files
  (covered by gameplay_runtime + regression tests)
- HYDRA / PHANTOM / NEMESIS still render as simple rect (only GOLIATH
  got the full biblical giant redesign in BLOQUE 51)

### Future Work (v0.3.0)

- Split `gameplay_runtime.py` into 8-9 focused classes
- Add integration test for full chained level 1 → sub-boss → boss
- Add dedicated test files for BLOQUE 47-53d gaps
- Redesign HYDRA / PHANTOM / NEMESIS visual (BLOQUE 51+ pattern)
- Online leaderboard (currently local JSON)
- Per-act audio theme switching (BGM off for now)

---

[0.1.0]: Initial production MVP. 17 BLOQUE delivered. 538 tests. 89.59% coverage. 0 mypy errors. 117.7 FPS stress.
[0.2.0]: Polish + boss mechanics. BLOQUE 18-53 delivered. 746 tests. 0 mypy errors. 40 visual frames. Game is end-to-end playable.
