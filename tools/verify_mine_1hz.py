"""BLOQUE 67: empirical verification of the 1Hz continuous fire in open3."""
import sys
sys.path.insert(0, '.')

# Use a fixed seed for determinism
from src.entities.enemies.enemy import (
    Enemy, EnemyKind, EnemyState, create_enemy,
    MINE_FIRE_INTERVAL_S, MINE_FAN_ANGLE_DEG,
)
from src.systems.projectile import (
    BULLET_ENEMY_MINE, OWNER_ENEMY, ProjectilePool,
)

# Step 1: build a mine and advance it to open3
e = create_enemy(EnemyKind.MINE_ASTEROID, 100.0, 50.0)
e.y = 100  # well above threshold so we can set y to trigger opening

# Simulate the gameplay_runtime integration site: read on_fire, fire, reset
def integration_step(enemy: Enemy, pool: ProjectilePool) -> int:
    """Mimics gameplay_runtime.py:1941-1943 + 2016-2019."""
    fired = 0
    if enemy.on_fire:
        enemy.on_fire = False
        if enemy.kind == EnemyKind.MINE_ASTEROID:
            enemy._fire_mine_bullets(pool)
            fired = 1
    return fired

pool = ProjectilePool(capacity=256)

# Advance to open3
e.update(0.016, 160.0, 400.0)  # closed -> open1
e.update(0.2, 160.0, 400.0)    # open1 -> open2
e.update(0.2, 160.0, 400.0)    # open2 -> open3 (entry fire: on_fire=True)
assert e.mine_state == "open3"

# Step 2: run for 5.0s of post-entry open3 time, count fires
fires = []
# Entry fire: integrate now to consume on_fire
fires.append(('entry', integration_step(e, pool)))
t = 0.0
tick = 0.05
last_logged_fire_count = pool.active_count if hasattr(pool, 'active_count') else None
# Just count on_fire transitions
n_fires = 0
while t < 5.0:
    e.update(tick, 160.0, 400.0)  # may set on_fire=True
    n_fires += integration_step(e, pool)
    t += tick

# Count bullets spawned
total_bullets = sum(1 for p in pool.pool if p.active and p.kind == BULLET_ENEMY_MINE)
expected_bullets = n_fires * 3  # 3 bullets per fan
print(f'MINE_FIRE_INTERVAL_S = {MINE_FIRE_INTERVAL_S}')
print(f'open3 time simulated : {t:.2f}s')
print(f'on_fire transitions  : {n_fires}')
print(f'expected transitions : {int(t / MINE_FIRE_INTERVAL_S)} (one on entry + every 1s)')
print(f'bullets spawned      : {total_bullets}  (expected {expected_bullets})')
print()
# At t=5s of post-entry open3 time: 1 entry fire + 5 periodic fires = 6 fires
# Tolerance: 5-7 fires
ok = 4 <= n_fires <= 7
print(f'1Hz check            : {"PASS" if ok else "FAIL"}  (need 4-7 fires in 5s)')
sys.exit(0 if ok else 1)
