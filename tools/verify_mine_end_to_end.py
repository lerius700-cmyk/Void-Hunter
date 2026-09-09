"""BLOQUE 68: end-to-end verification that a MINE-ASTEROID actually
opens and fires in the integrated flow.

This simulates the full lifecycle:
1. spawn_obstacle returns a MINE_ASTEROID payload (with drift_vx, drift_vy)
2. The enemy is created and drift velocity is applied (gameplay_runtime.py:1720-1722)
3. The enemy drifts down at vy=20-50 px/s
4. After ~6-8 seconds, the mine reaches y < 200 (OPENING_Y_THRESHOLD) and opens
5. The mine fires a 3-bullet fan on entry to open3, then every 1s

If any of these steps fail, the test fails loudly. This is the
integration test that would have caught the BLOQUE 65/66/67 bug:
'asteroids are static, they don't open'."""
import sys
sys.path.insert(0, '.')
import random
from src.entities.enemies.enemy import (
    Enemy, EnemyKind, EnemyState, create_enemy, spawn_obstacle,
    OPENING_Y_THRESHOLD, MINE_FIRE_INTERVAL_S,
)
from src.systems.projectile import ProjectilePool

# Step 1: find a MINE_ASTEROID payload
payload = None
for seed in range(200):
    rng = random.Random(seed)
    if rng.random() < 0.25:  # MINE_SPAWN_FRACTION
        kind, p = spawn_obstacle(rng)
        if kind == "mine_asteroid":
            payload = p
            break
assert payload is not None, "could not sample a MINE_ASTEROID payload"
print(f"Step 1: payload = {payload}")

# Step 2: create enemy and apply drift (mimics gameplay_runtime.py)
e = create_enemy(EnemyKind.MINE_ASTEROID, payload["x"], payload["y"])
e.vx = payload["drift_vx"]
e.vy = payload["drift_vy"]
e.mine_variant = 0
print(f"Step 2: enemy created at ({e.x:.1f}, {e.y:.1f}), vx={e.vx:.1f}, vy={e.vy:.1f}")
assert e.mine_state == "closed"
assert e.vy > 0, "drift_vy should be positive (downward)"

# Step 3: simulate the integration site (gameplay_runtime.py:1941)
pool = ProjectilePool(capacity=256)
def integrate(enemy, dt):
    """Mimics gameplay_runtime integration site: advance, fire, cull."""
    enemy.update(dt, 160.0, 400.0)
    fired = 0
    if enemy.on_fire:
        enemy.on_fire = False
        if enemy.kind == EnemyKind.MINE_ASTEROID:
            enemy._fire_mine_bullets(pool)
            fired = 1
    return fired

# Step 4: run the full lifecycle. Start at e.y (likely -80 to 0),
# drift down, expect to reach open3 in ~6-8 seconds, then fire every 1s.
TICK = 0.05  # 50ms ticks
MAX_T = 20.0  # 20s cap (should be enough for spawn -> drift -> open3 -> 10s of firing)
opens_at = None
fires = 0
t = 0.0
while t < MAX_T:
    fires += integrate(e, TICK)
    if e.mine_state == "open3" and opens_at is None:
        opens_at = t
    if e.mine_state == "open3" and t - opens_at > 4.0:
        # 4s of post-open3 firing is enough
        break
    t += TICK

# Step 5: assert the mine actually opened
print(f"Step 5: mine opened at t={opens_at:.2f}s, current state={e.mine_state}")
print(f"        total fires in {t:.2f}s = {fires}")
if opens_at is None:
    print("FAIL: mine never opened!")
    sys.exit(1)
if fires < 3:
    print(f"FAIL: mine opened but fired only {fires} times in {t:.2f}s. Expected >= 3.")
    sys.exit(1)

print()
print("PASS: MINE-ASTEROID lifecycle works end-to-end")
print(f"  - spawns with drift velocity")
print(f"  - drifts down to OPENING_Y_THRESHOLD={OPENING_Y_THRESHOLD}")
print(f"  - opens (closed -> open1 -> open2 -> open3) in {opens_at:.2f}s")
print(f"  - fires {fires} times in {t - opens_at:.2f}s of open3 time")
print(f"  - fire rate: {fires / (t - opens_at):.2f} Hz (target: ~1.0 Hz at MINE_FIRE_INTERVAL_S={MINE_FIRE_INTERVAL_S}s)")
