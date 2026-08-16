"""Global settings for STELLAR HORIZON — 480x270 horizontal, 1920x1080 window."""
from __future__ import annotations

# Display
INTERNAL_W: int = 480
INTERNAL_H: int = 270
DEFAULT_SCALE: int = 4
WINDOW_W: int = INTERNAL_W * DEFAULT_SCALE   # 1920
WINDOW_H: int = INTERNAL_H * DEFAULT_SCALE   # 1080
WINDOW_TITLE: str = "STELLAR HORIZON"

# Frame timing — 120 FPS lock
FPS_TARGET: int = 120
FIXED_DT: float = 1.0 / FPS_TARGET
DT_CLAMP: float = 1.0 / 30.0

# Pools
PLAYER_BULLET_POOL: int = 32
ENEMY_BULLET_POOL: int = 64
ENEMY_POOL: int = 32
PARTICLE_POOL: int = 600
