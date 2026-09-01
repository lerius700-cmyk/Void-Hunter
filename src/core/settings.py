"""Global settings and constants for VOID HUNTER.

Description: Vertical shmup, 240x360 base @ 4x scale, 120 FPS lock, 8-bit
             aesthetic with Metal Slug-grade juice. All numeric tunables live
             here (single source of truth — see docs/design/void-hunter-gdd.md
             Apéndice A for the full cheat-sheet).
Dependencies: none (constants only; importing this module is free).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
INTERNAL_W: int = 320        # BLOQUE 34: 1.33x wider playfield (was 240)
INTERNAL_H: int = 480        # BLOQUE 34: 1.33x taller playfield (was 360)
DEFAULT_SCALE: int = 3  # window = INTERNAL_W x INTERNAL_H at this scale
WINDOW_W: int = INTERNAL_W * DEFAULT_SCALE   # 960x1440 @ scale 3
WINDOW_H: int = INTERNAL_H * DEFAULT_SCALE
WINDOW_TITLE: str = "VOID HUNTER v1.1.6 (BLOQUE 58.62)"

# ---------------------------------------------------------------------------
# Frame timing — 120 FPS lock
# ---------------------------------------------------------------------------
FPS_TARGET: int = 120
FIXED_DT: float = 1.0 / FPS_TARGET  # 8.333ms
DT_CLAMP: float = 1.0 / 30.0         # 33.33ms — prevents death spiral on long stalls

# ---------------------------------------------------------------------------
# Pools
# ---------------------------------------------------------------------------
PROJECTILE_POOL: int = 400                # 200 in seed nebula-hunter
PROJECTILE_POOL_BOSS: int = 600           # +200 during BOSS_FIGHT state
PARTICLE_POOL: int = 1500                 # 600 in seed
DEBRIS_POOL: int = 200                    # 100 in seed
DAMAGE_POPUP_POOL: int = 32
ENEMY_POOL: int = 64
BOSS_POOL: int = 4
POWERUP_POOL: int = 16

# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
PLAYER_LIVES: int = 3
PLAYER_CONTINUES: int = 1
PLAYER_BOMBS: int = 3
PLAYER_BOMBS_MAX: int = 4                 # +1 with special unlocked
# BLOQUE 53b: HP bar (Mega Man / Star Fox style). Bigger pool so
# healing sources (gold rings, tech upgrades) feel meaningful.
PLAYER_HP: int = 30
PLAYER_HP_MAX: int = 30
PLAYER_HP_SEGMENTS: int = 10              # how many sub-divisions on the bar
# BLOQUE 53c: gold rings (Star Fox). 3 rings collected = double max HP
# (one-time per run). Rings also heal.
GOLD_RING_HEAL: int = 2                   # +HP per ring picked up
GOLD_RING_DROP_CHANCE: float = 0.08      # chance per enemy kill
GOLD_RING_DURATION_S: float = 6.0        # how long they float before despawn
GOLD_RING_DRAW_LIFE: int = 30            # ring powerup special unit (max 30 stacked)
# BLOQUE 53d: tech upgrade system. Each level drops specific pieces.
TECH_UPGRADES_PER_LEVEL: int = 2         # level 1 has 2 (sub-boss drop + perfect drop)
TECH_HP_BOOST_PCT: float = 0.10          # +10% max HP per HP_BOOST upgrade
# GOLIATH_SUMMON upgrade: triggers at second 60 of the level, skipping
# the rest of the chain and going to the boss fight with a giant
# "friendly GOLIATH sweeps the screen" visual.
GOLIATH_SUMMON_AT_S: float = 60.0
# Maximum HP cap (to prevent runaway doubling)
PLAYER_HP_ABSOLUTE_MAX: int = 999
PLAYER_SPEED: float = 165.0               # px/s — BLOQUE 38: was 130
PLAYER_FIRE_COOLDOWN_S: float = 0.10      # 12 shots/s at L1
PLAYER_DASH_SPEED: float = 480.0          # px/s (3.7x walk)
PLAYER_DASH_DURATION_S: float = 0.18
PLAYER_DASH_IFRAMES: int = 22             # at base level
# BLOQUE 58.8: dash overheat (Star Fox style). Heat builds while
# dashing, decays when not. When heat >= MAX, dash auto-cancels and
# can't be triggered again until heat drops below COOLDOWN threshold.
PLAYER_DASH_HEAT_MAX: float = 100.0
PLAYER_DASH_HEAT_PER_S: float = 280.0     # ~0.36s of continuous dashing to overheat
PLAYER_DASH_HEAT_DECAY_PER_S: float = 55.0  # ~1.8s to cool from max to 0
PLAYER_DASH_HEAT_RESUME_THRESHOLD: float = 25.0  # must drop below 25% to dash again
# BLOQUE 58.8.1: DASH and PROPULSION are now TWO SEPARATE modes that
# share the same heat bar. DASH is a quick 0.18s burst (one-shot),
# PROPULSION is a continuous thrust while shift is held.
# - DASH: consumes a flat 10 heat per use (regardless of duration)
# - PROPULSION: builds heat continuously at 30/s (overheats in ~3.3s)
PLAYER_DASH_HEAT_COST: float = 10.0
PLAYER_PROPULSION_SPEED_MULT: float = 2.0  # x2 speed during propulsion
PLAYER_PROPULSION_HEAT_PER_S: float = 30.0
# Click vs hold threshold: shift pressed for less than this = DASH
# (one-shot), shift held for >= this = PROPULSION (continuous).
# BLOQUE 58.8.2: widened from 0.15s to 0.6s — 0.15s was too tight for
# human reaction time, so a normal tap on shift was being misread as a
# hold and triggered PROPULSION instead of the one-shot DASH.
# BLOQUE 58.8.3: tightened from 0.6s to 0.28s — 0.6s introduced too much
# delay between the player committing to propulsion and the actual start.
# 0.28s is the sweet spot: still wide enough for human reaction time,
# short enough to feel responsive.
PLAYER_CLICK_VS_HOLD_THRESHOLD_S: float = 0.28
# Trail particle spawn rate during PROPULSION (one particle per N seconds)
PLAYER_PROPULSION_TRAIL_INTERVAL_S: float = 0.025  # ~40 Hz
# BLOQUE 58.8.3: delayed wake/destello spawned during PROPULSION. Each
# wake particle waits `delay_s` seconds before becoming visible, then
# fades over `life_s` seconds. Together they form a 1-second-delayed
# bright orange afterglow that "follows" the player (the wake particles
# are stationary, but new ones are continuously emitted at the player's
# CURRENT position, so the trail visually lags the ship by 1s).
PLAYER_PROPULSION_WAKE_DELAY_S: float = 1.0
PLAYER_PROPULSION_WAKE_LIFE_S: float = 0.8
PLAYER_PROPULSION_WAKE_INTERVAL_S: float = 0.04  # ~25 Hz (sparser than main trail)
# BLOQUE 58.11: Tron-style light trail. When the player PROPULSIONs, the
# ship leaves a continuous chain of cyan wall segments behind it. Each
# segment is a thick line drawn with a soft cyan gradient (Tron Legacy
# neon). Enemies that touch the trail take 3x the L1 bullet damage
# (TRON_TRAIL_DAMAGE_MULT), with a per-enemy hit cooldown to prevent
# melting in a single frame.
TRON_TRAIL_DAMAGE_MULT: float = 3.0
# BLOQUE 58.24: segment_length is now 6px (was 28). In the polyline
# renderer, this is the spacing between polyline vertices, not a
# sprite dimension. A smaller value means more vertices per curve
# segment, so the polyline follows the ship's path more smoothly.
# The previous 28px "long sprites" approach was superseded because
# rotated rectangles produced visible "rungs" along curves.
TRON_TRAIL_SEGMENT_LENGTH: float = 6.0
TRON_TRAIL_SEGMENT_THICKNESS: float = 4.0
TRON_TRAIL_MAX_AGE_S: float = 2.5
TRON_TRAIL_SPAWN_INTERVAL_S: float = 0.018  # ~55 Hz (smooth ribbon)
TRON_TRAIL_MAX_SEGMENTS: int = 240
TRON_TRAIL_HIT_COOLDOWN_S: float = 0.15   # ~7 Hz max hit rate per enemy
PLAYER_INVULN_FRAMES: int = 60            # post-hit
PLAYER_DEATH_DURATION_S: float = 1.20
PLAYER_RESPAWN_INVULN_S: float = 1.0
# BLOQUE 38: nose smoothing — snappier mouse follow (50°/s, was 28)
# BLOQUE 58.13: bumped to 180°/s. At 50°/s the visible lag when
# moving the mouse fast made the ship tip feel disconnected from
# the cursor (the bullets tracked the mouse correctly because they
# use a different code path, but the visual tip lagged). 180°/s
# is the sweet spot: the tip follows the mouse with almost no
# visible lag, but the lerp still gives the ship a sense of
# "weight" when the player makes sharp turns. Above 360°/s the
# rotation starts to feel robotic.
PLAYER_NOSE_LERP_PER_S: float = 180.0
# BLOQUE 35: sprite scale factors (visual reduction, hitbox unchanged)
PLAYER_SPRITE_SCALE: float = 0.75   # player 32x24 -> 24x18
BULLET_SPRITE_SCALE: float = 0.75   # player bullet 4x6 -> 3x5, etc.
# BLOQUE 35: RMB rapid-fire cooldown (~12 shots/s, was 0 in BLOQUE 34 freeform)
RMB_FIRE_COOLDOWN_S: float = 0.083
# BLOQUE 37: L3 continuous plasma laser
LASER_MAX_RANGE_PX: float = 560.0          # 1.17x screen height (320x480 → 560 max)
LASER_TICK_S: float = 0.05                # damage re-hit interval per enemy (20 Hz)
LASER_DAMAGE_PER_TICK: int = 4            # DPS at 20 Hz ≈ 80 dps, sustained
LASER_HIT_RADIUS_PX: int = 6              # beam thickness for hit detection
LASER_SPARK_RATE_S: float = 0.025         # ambient spark along the beam
LASER_FADE_S: float = 0.18                # release-tail visual fade after LMB up
# BLOQUE 39: homing missile bomb (B key, replaces L-key screen clear)
# BLOQUE 58.9: explosion 10x bigger (60 -> 300) per user request
MISSILE_SPEED_PX_S: float = 280.0         # top speed
MISSILE_ACCEL_PX_S2: float = 1200.0        # initial acceleration
MISSILE_TURN_RATE_DEG_S: float = 360.0    # how fast the missile can rotate
MISSILE_LIFE_S: float = 3.0               # max flight time before despawn
MISSILE_BODY_RADIUS_PX: int = 6          # hit radius for the missile itself
MISSILE_EXPLOSION_RADIUS_PX: int = 300    # BLOQUE 58.9: 5x bigger (was 60)
MISSILE_EXPLOSION_DAMAGE: int = 200        # BLOQUE 58.9: more damage for bigger radius
MISSILE_TRAIL_RATE_S: float = 0.02        # particle trail interval
MISSILE_KEY: int = ord('b')               # rebind from K_l to B

# ---------------------------------------------------------------------------
# Bullet FX
# ---------------------------------------------------------------------------
BULLET_TRAIL_PARTICLES_PER_FRAME: int = 1
ION_WAKE_RADIUS: int = 1

# ---------------------------------------------------------------------------
# Camera — Eiserloh trauma² model (DO NOT touch the formula)
# ---------------------------------------------------------------------------
TRAUMA_PER_KILL_SCOUT: float = 0.08
TRAUMA_PER_KILL_CRUISER: float = 0.10
TRAUMA_PER_KILL_HEAVY: float = 0.20
TRAUMA_PER_KILL_KAMIKAZE_AIR: float = 0.15
TRAUMA_PER_KILL_KAMIKAZE_CONTACT: float = 0.25
TRAUMA_PER_KILL_DRONE: float = 0.05
TRAUMA_PER_KILL_SNIPER: float = 0.18
TRAUMA_PER_KILL_TURRET: float = 0.15
TRAUMA_PER_KILL_CARRIER: float = 0.30
TRAUMA_PER_HIT: float = 0.35
TRAUMA_PER_BOSS_PHASE: float = 0.50
TRAUMA_PER_BOSS_DEATH: float = 0.60
TRAUMA_PER_BOMB: float = 0.20
TRAUMA_DECAY: float = 0.88
SHAKE_MAX_PX: float = 8.0                # 4.0 in seed — Eiserloh max per spec

# ---------------------------------------------------------------------------
# Hitstop
# ---------------------------------------------------------------------------
HITSTOP_FRAMES_SCOUT: int = 3
HITSTOP_FRAMES_CRUISER: int = 4
HITSTOP_FRAMES_HEAVY: int = 6
HITSTOP_FRAMES_BOSS: int = 2
HITSTOP_FRAMES_BOSS_PHASE: int = 6
HITSTOP_FRAMES_BOSS_DEATH: int = 12
HITSTOP_FRAMES_BOMB: int = 8
HITSTOP_FRAMES_PLAYER_DEATH: int = 10
HITSTOP_FRAMES_PERFECT_DASH: int = 4
HITSTOP_FRAMES_MULT_MAX: int = 3

# ---------------------------------------------------------------------------
# Slow-mo
# ---------------------------------------------------------------------------
SLOWMO_CHARGED_FACTOR: float = 0.95
SLOWMO_CHARGED_FRAMES: int = 4
SLOWMO_PERFECT_DASH_FACTOR: float = 0.30
SLOWMO_PERFECT_DASH_FRAMES: int = 30
SLOWMO_BOMB_FACTOR: float = 0.50
SLOWMO_BOMB_FRAMES: int = 8
SLOWMO_BOSS_PHASE_FACTOR: float = 0.70
SLOWMO_BOSS_PHASE_FRAMES: int = 12
SLOWMO_BOSS_DEATH_FACTOR: float = 0.40
SLOWMO_BOSS_DEATH_FRAMES: int = 24
SLOWMO_MULT_MAX_FACTOR: float = 0.85
SLOWMO_MULT_MAX_FRAMES: int = 12
SLOWMO_FINISHER_FACTOR: float = 0.50
SLOWMO_FINISHER_FRAMES: int = 12

# ---------------------------------------------------------------------------
# Wave
# ---------------------------------------------------------------------------
WAVE_KILL_TARGET: int = 20
WAVE_TIME_LIMIT_S: float = 30.0
SUBBOSS_TRIGGER_KILLS: int = 40
WAVE_GROWTH: int = 2
# BLOQUE 40: formation-based encounter pacing
MAX_ENEMIES_ON_SCREEN: int = 12           # BLOQUE 58.56: 8→12 (doubled enemies need more on-screen capacity)
SPAWN_CADENCE_S_MIN: float = 0.8         # min time between spawns
SPAWN_CADENCE_S_MAX: float = 1.5         # max time between spawns
WAVE_RESPITE_S_MIN: float = 4.0          # min breathing room between waves
WAVE_RESPITE_S_MAX: float = 6.0          # max breathing room between waves
# BLOQUE 40: boss trigger hierarchy
BOSS_FAST_TRIGGER_S: float = 60.0        # perfect-score fast path
BOSS_FALLBACK_KILLS: int = 50            # kill-count fallback
BOSS_FALLBACK_TIMEOUT_S: float = 180.0   # lenient timeout fallback
# Formation defaults
FORMATION_SPACING_MIN_PX: int = 24
FORMATION_SPACING_MAX_PX: int = 32
FORMATION_PATTERN_SPEED_MIN: float = 30.0
FORMATION_PATTERN_SPEED_MAX: float = 60.0
FORMATION_TELEGRAPH_FRAMES_MIN: int = 24
FORMATION_TELEGRAPH_FRAMES_MAX: int = 60

# ---------------------------------------------------------------------------
# BLOQUE 48: chained wave system (level 1 mode redesign)
# ---------------------------------------------------------------------------
WAVE_MAX_DURATION_S: float = 8.0         # max time a wave can take (chaining)
BOSS_MIN_TRIGGER_S: float = 45.0         # boss won't fire before this (timer hard)
# BLOQUE 58.7ac: perfect trigger raised to 100s so the sub-boss (which
# fires at ~95s) ALWAYS gets a turn. Previously 60s caused the boss to
# fire on the same frame as the sub-boss resume, killing the dart before
# the player could see it.
BOSS_PERFECT_TRIGGER_S: float = 220.0    # BLOQUE 58.13.3: was 100s, raised so
                                        # GOLIATH fires at song midpoint (3:40)
BOSS_SAFETY_TRIGGER_S: float = 220.0     # BLOQUE 58.13.3: was 140s, same
                                        # rationale — sync with perfect trigger
                                        # so the player always reaches GOLIATH
                                        # before the song ends (5:30)
# BLOQUE 58.56: doubled enemy counts and extended duration so the level
# lasts as long as the gameplay song (5.5 min ≈ 330s).
LEVEL1_TOTAL_SHIPS: int = 380            # BLOQUE 58.11: 60+80+90+100+50 = 380 ships (was 165)
                                        # Tuned so minimum clear time is 3:30 (player can
                                        # actually listen to the song before GOLIATH).
LEVEL1_FLAT_SCORE: int = 558             # BLOQUE 58.11: 250 SCOUT*1 + 82 CRUISER*2 + 48 HEAVY*3 = 250+164+144 = 558 (was 254)
PERFECT_RUN_BONUS: int = 15              # awarded on _enemies_escaped == 0 at boss
# Per-archetype flat score (used by the new level 1 chain)
SCOUT_FLAT_SCORE: int = 1
CRUISER_FLAT_SCORE: int = 2
HEAVY_FLAT_SCORE: int = 3
SUB_BOSS_FLAT_SCORE: int = 5             # BLOQUE 50: sub-boss gives 5pt flat on kill
# BLOQUE 50: sub-boss trigger point in level 1 chain — fires between O2 and O3
SUB_BOSS_TRIGGER_AFTER_WAVE: int = 1     # 0-indexed: after wave index 1 (O2)

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
SCORE_PER_SCOUT: int = 50
SCORE_PER_CRUISER: int = 150
SCORE_PER_HEAVY: int = 400
SCORE_PER_KAMIKAZE: int = 200
SCORE_PER_KAMIKAZE_AIR: int = 500        # bonus si destruido en el aire
SCORE_PER_DRONE: int = 80
SCORE_PER_MINI_DRONE: int = 50
SCORE_PER_SNIPER: int = 300
SCORE_PER_TURRET: int = 250
SCORE_PER_CARRIER: int = 800
SCORE_PER_GOLIATH: int = 5000
SCORE_PER_HYDRA: int = 8000
SCORE_PER_PHANTOM: int = 12000
SCORE_PER_NEMESIS: int = 20000
SCORE_PER_WAVE_CLEAR: int = 5000
SCORE_PER_ACT_CLEAR: int = 25000
MULTIPLIER_MAX: int = 16
MULTIPLIER_DECAY_S: float = 1.5
ELEMENT_BONUS: float = 1.5
STREAK_BONUS_CAP: float = 2.0
STREAK_BONUS_WINDOW_S: float = 3.0

# ---------------------------------------------------------------------------
# Audio — pygame.mixer config (criterio §0: 16 channels @ 44100 Hz, raw PCM)
# ---------------------------------------------------------------------------
MIXER_CHANNELS: int = 16
MIXER_SAMPLE_RATE: int = 44100
MIXER_BUFFER: int = 512
MIXER_BITS: int = 16

# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------
COVERAGE_GATE: float = 0.35               # 5% en BLOQUE 0 → 35% al release
FPS_TARGET_NORMAL: int = 120
FPS_TARGET_STRESS: int = 90
