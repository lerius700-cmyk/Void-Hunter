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
INTERNAL_W: int = 240
INTERNAL_H: int = 360
DEFAULT_SCALE: int = 4  # 960x1440 window
WINDOW_W: int = INTERNAL_W * DEFAULT_SCALE
WINDOW_H: int = INTERNAL_H * DEFAULT_SCALE
WINDOW_TITLE: str = "VOID HUNTER"

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
PLAYER_SPEED: float = 130.0               # px/s
PLAYER_FIRE_COOLDOWN_S: float = 0.10      # 12 shots/s at L1
PLAYER_DASH_SPEED: float = 480.0          # px/s (3.7x walk)
PLAYER_DASH_DURATION_S: float = 0.18
PLAYER_DASH_IFRAMES: int = 22             # at base level
PLAYER_INVULN_FRAMES: int = 60            # post-hit
PLAYER_DEATH_DURATION_S: float = 1.20
PLAYER_RESPAWN_INVULN_S: float = 1.0
# BLOQUE 32: boost — fast repositioning for tricky enemies
PLAYER_BOOST_MULT: float = 2.0        # 2x speed during boost
PLAYER_BOOST_DURATION_S: float = 0.4  # burst duration
PLAYER_BOOST_COOLDOWN_S: float = 1.5  # cooldown before next boost
# BLOQUE 32: nose smoothing (lerp speed for "rotate only while moving")
PLAYER_NOSE_LERP_PER_S: float = 12.0  # higher = snappier

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
