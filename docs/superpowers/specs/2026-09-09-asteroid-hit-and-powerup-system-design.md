# BLOQUE 71 + 72 — Asteroid Hit Feedback & 4-Weapon Powerup System

**Author:** Mavis (brainstorming session 2026-09-09)
**Status:** DRAFT (awaiting user review)
**Scope:** `src/entities/asteroid.py`, `src/entities/enemies/enemy.py`, `src/ui/hud.py`, `src/ui/gameplay_runtime.py`, `src/audio/sfx.py`, HUD slot system, input remap (RMB = powerup fire, wheel = slot cycle).

---

## 1. Problem

Two related gaps in the current game:

**1a. Asteroids (regular + MINE) have no visible hit feedback.** `_asteroid_bullet_collision` (`src/ui/gameplay_runtime.py:1754-1780`) calls `ast.hit()` which is a no-op returning False. The bullet dies but the player gets no signal that they hit a gameplay-layer asteroid. Background-tile asteroids visually overlap gameplay asteroids, so the player cannot tell what is interactive.

**1b. The existing `PowerupKind.WEAPON` pickup does nothing useful.** `_apply_powerup` (`src/ui/gameplay_runtime.py:1808-1828`) bumps `self._weapon.level` capped at 2 — no visual change, no feel change. The user picks up "W" letters and nothing happens. Meanwhile, the RMB input (`gameplay_runtime.py:712-715`) fires a continuous L1 rapid fire that overlaps conceptually with what a "laser powerup" should be.

## 2. Goals

### BLOQUE 71 (small)
- All asteroid hits trigger a brief **white flash** (0.15s) like ships do on hit.
- Visual signal: tells the player "you hit a gameplay-layer asteroid, not background tile".
- MINE-ASTEROID (all 4 states: closed/open1/open2/open3) flash the same way; only `open3` decrements HP and is destructible.
- Regular asteroids remain indestructible (BLOQUE 64.A) but get the flash feedback.
- New SFX: `asteroid_hit.wav` (short click, ~0.05s) added to `src/audio/sfx.py`.

### BLOQUE 72 (large)
- Replace the broken `PowerupKind.WEAPON` with **4 distinct weapon powerups**: thick shot (A), laser (S), flamethrower (D), double blue laser (F).
- Each weapon has its own bullet sprite, damage, range, fire mode, ammo cost, and SFX.
- Player inventory: 4 fixed HUD slots. Initial state = all empty. Pickups fill/stack into the corresponding slot.
- **Input remap:** LMB = main fire (unchanged). **RMB = fire selected powerup weapon** (replaces current rapid fire). **Mouse wheel = cycle through filled slots only**.
- RMB on empty active slot: **auto-cycle to next filled slot** (zero dead input).
- Mouse wheel scope: **only slots with ammo** (skip empty).

## 3. Non-Goals

- HYDRA / PHANTOM / NEMESIS redesign.
- LMB charge-up laser (`src/ui/gameplay_runtime.py:760+`) — kept as is, not a powerup.
- BOMB/HP drops from other enemies (existing system, untouched).
- AI-generation of new weapon sprites — using procedural 8-bit pixelart via PIL (consistent with existing `tools/redesign_ships/` pipeline pattern but simpler, single-frame sprites).
- Boss-tied weapon drops (e.g., GOLIATH drops only laser) — random equal weight from 6-kind pool.
- Mouse wheel to switch ships or other state — wheel is weapon-slot-only.
- Stack beyond max_ammo — pickup that would overflow is silently dropped (no excess storage).

## 4. Architecture

### 4.1 BLOQUE 71 — Asteroid hit feedback

**Data changes (`src/entities/asteroid.py`):**
- `Asteroid` dataclass: add `hit_timer: float = 0.0`.
- `Asteroid.update(dt)`: decrement `hit_timer` by `dt`.
- `Asteroid.hit(damage)`: set `self.hit_timer = 0.15`, return False (indestructible). The `damage` arg is kept for API compat.
- New helper `draw_asteroid_with_hit_flash(target, ast)`: if `hit_timer > 0`, render the sprite with a palette-swap that replaces non-transparent non-black colors with white. Uses pre-computed LUT for speed.

**Data changes (`src/entities/enemies/enemy.py`):**
- MINE-ASTEROID `hit()` in closed/open1/open2 states: set `e.hit_timer = 0.15`, return False.
- MINE-ASTEROID `hit()` in open3 state: set `e.hit_timer = 0.15`, decrement HP, return True if HP<=0 (was red flash 0.2s — REPLACED with white flash for consistency).
- MINE-ASTEROID `update(dt)`: decrement `hit_timer`.
- Mine rendering: same palette-swap as regular asteroid.

**Collision update (`src/ui/gameplay_runtime.py:1754-1780`):**
- The existing collision loop already calls `ast.hit()` and releases the bullet. The `hit()` change makes the new flash behavior automatic. No new code at the collision site itself.

**SFX (`src/audio/sfx.py`):**
- Add `asteroid_hit` event to the SFX pool. Synth via `tools/synth.py` (or similar): short noise burst ~0.05s, vol 0.3.
- Dispatch from `_asteroid_bullet_collision` only when `hit_timer` was actually set (i.e., the asteroid is alive and the hit registered).

**Visual approach:** palette swap, not alpha overlay. Reason: consistent with the 8-bit pixelart aesthetic; no transparency glitches on varied backgrounds; cheap (one LUT, one recolor pass per draw).

### 4.2 BLOQUE 72 — 4-weapon powerup system

**Data model:**

```python
# src/entities/weapon_slot.py (NEW)
@dataclass
class WeaponSlot:
    letter: str            # "A" | "S" | "D" | "F"
    weapon_id: str         # "thick" | "laser" | "flame" | "double"
    ammo: int              # 0 = empty
    max_ammo: int          # cap for visual
```

**Player state (in `GameplayRuntime`):**
```python
self._weapon_slots: list[WeaponSlot] = [
    WeaponSlot("A", "thick",  0, 100),
    WeaponSlot("S", "laser",  0, 200),
    WeaponSlot("D", "flame",  0,  50),
    WeaponSlot("F", "double", 0, 150),
]
self._weapon_active_idx: int = 0  # index into _weapon_slots
```

**The 4 weapons:**

| Slot | Weapon | Damage | Range | Fire mode | Visual | Ammo/s | Initial pickup | Cap |
|---|---|---|---|---|---|---|---|---|
| A | Thick shot | 2x | 300 px | L1, 6/s | Orange bullet, 3× size | 6 | 30 | 100 |
| S | Laser | 1/tick | 600 px | Hold RMB | Green beam, 4 px wide | 5 | 30 | 200 |
| D | Flamethrower | 1/tick | 80 px (cone 30°) | Hold RMB | 5 orange bullets/s in spread | 8 | 30 | 50 |
| F | Double blue laser | 0.5/tick ×2 | 500 px | Hold RMB | 2 cyan beams 8 px apart | 6 | 30 | 150 |

**`PowerupKind` change (`src/entities/asteroid.py`):**
- Remove `PowerupKind.WEAPON`.
- Add 4 new: `THICK = "thick"`, `LASER = "laser"`, `FLAME = "flame"`, `DOUBLE = "double"`.
- Keep `BOMB`, `HP`, `SCORE` (BOMB/HP from MINE drops, SCORE from other enemies).
- Update `POWERUP_WEIGHTS` (used by `pick_random_powerup` for asteroid-side drops): split WEAPON weight into 4 equal parts.

**MINE-ASTEROID drop pool (`src/entities/enemies/enemy.py`):**
- `pick_mine_powerup(rng)`: now picks from `[BOMB, HP, THICK, LASER, FLAME, DOUBLE]` with equal probability (1/6 each). Removed WEAPON.

**Pickup application (`src/ui/gameplay_runtime.py:_apply_powerup`):**
- For weapon kinds: `target_slot = weapon_index[kind]`. If `slot.ammo == 0`, set `ammo = pickup_amount`. Else, `ammo = min(slot.ammo + pickup_amount, slot.max_ammo)`. Snap animation handled in HUD.
- BOMB/HP: existing logic.

**Input remap (`src/ui/gameplay_runtime.py`):**
- LMB: unchanged (main fire, charge shot).
- RMB: replace rapid-fire dispatch with `self._fire_weapon_slot()`.
  - If active slot has ammo > 0: fire that weapon, consume ammo per the weapon's rate.
  - If active slot is empty: cycle to next filled slot (next index with ammo > 0, wrap-around). If none filled, do nothing.
- Mouse wheel: `event.y` positive = cycle down, negative = cycle up. Skip empty slots.
- B / L keys: unchanged (bomb).

**HUD slots (new, in `src/ui/hud.py`):**
- New method `_draw_weapon_slots(target, t)`.
- Position: bottom-center, 4 boxes 12×12 px, 4 px spacing, total width 60 px, centered on `INTERNAL_W/2`.
- Empty slot: dark gray outline (60, 60, 70), black fill, no letter.
- Filled slot: weapon-color background, white letter centered (pygame.font, size 9), ammo count below the slot in pixel-font size 5.
- Selected slot: white border 1 px + scale 1.0→1.05 pulse at 0.5 Hz.
- Pickup pop animation: scale 1.0 → 1.4 → 1.0 over 0.2s on the affected slot.

**MINE-ASTEROID drop visuals (in `src/entities/asteroid.py:Powerup.draw`):**
- Letter and color now reflect the kind: B (red BOMB), + (green HP), A (orange THICK), S (green LASER), D (red-orange FLAME), F (cyan DOUBLE). SCORE is yellow S (unchanged).
- Snap animation on pickup: powerup flies from world pos to the corresponding HUD slot over 0.3s, then despawns.

**New bullet kinds / firing (in `src/entities/projectile.py` or wherever bullets live):**
- `BULLET_THICK`: bigger sprite, 2x damage, same speed.
- `LASER_BEAM`: continuous, no individual entity; rendered as a quad each tick while RMB held. Damage per tick.
- `BULLET_FLAME`: small fast bullet, 5/s in a 30° spread.
- `BULLET_DOUBLE_LASER`: two parallel beams (or two stacked bullets in a 1-frame loop), 8 px apart.

**SFX additions (`src/audio/sfx.py`):**
- `shoot_thick`: short, punchy 0.08s square wave, low freq, vol 0.5.
- `laser_hum`: continuous 0.5s triangle 200→800 Hz, loops while RMB held, vol 0.3.
- `flame_loop`: continuous noise burst loop, 0.1s, vol 0.4.
- `shoot_double`: dual short clicks 0.04s, slight detune, vol 0.4.

**Asset generation (`tools/weapon_assets/`):**
- 4 bullet PNGs (16×16 each) — procedural 8-bit pixelart via PIL (no AI gen for these).
- 4 floating powerup PNGs (8×8) — reuses existing pattern with new letters and colors.
- 4 HUD slot PNGs (12×12) — outlined empty + filled colored.
- 4 SFX WAVs — generated via `tools/synth.py` extending the existing synth.

### 4.3 Code change list

| File | Change |
|---|---|
| `src/entities/asteroid.py` | `Asteroid.hit_timer` + flash render. `PowerupKind`: remove WEAPON, add 4 new. `Powerup` dataclass: extended letter/color map. |
| `src/entities/enemies/enemy.py` | MINE-ASTEROID: `hit_timer` + flash in all 4 states. `pick_mine_powerup`: 6-kind pool. |
| `src/entities/weapon_slot.py` | NEW: `WeaponSlot` dataclass. |
| `src/entities/projectile.py` | 4 new bullet kinds / firing functions. |
| `src/ui/hud.py` | `_draw_weapon_slots()`. Hook in `draw()`. |
| `src/ui/gameplay_runtime.py` | `_weapon_slots` state. `_apply_powerup` for 4 weapon kinds. RMB handler replaced. Mouse wheel handler added. |
| `src/audio/sfx.py` | 4 new SFX events. |
| `src/core/settings.py` | Constants: `MAX_AMMO_THICK/LASER/FLAME/DOUBLE`, `WEAPON_PICKUP_AMMO`. |
| `Assets/sprites/weapons/*.png` | 4 new weapon sprites (16×16). |
| `Assets/sprites/powerups/*.png` | 4 new powerup floating icons (8×8). |
| `Assets/sounds/asteroid_hit.wav` | NEW. |
| `Assets/sounds/shoot_thick.wav`, `laser_hum.wav`, `flame_loop.wav`, `shoot_double.wav` | NEW. |
| `tools/weapon_assets/generate_bullets.py` | NEW: procedural PIL generation. |
| `tools/weapon_assets/generate_powerups.py` | NEW: 8×8 icons. |
| `tools/weapon_assets/generate_hud_slots.py` | NEW: 12×12 outlined + filled. |
| `tools/synth/generate_weapon_sfx.py` | NEW: 4 weapon SFX WAVs. |
| `tests/test_asteroid.py` | +3 tests (hit_timer set/decrement, flash render, no-destroy). |
| `tests/test_mine_asteroid.py` | +3 tests (closed/open1/open2 flash without damage, open3 flash + HP). |
| `tests/test_weapon_slot.py` | NEW: ~8 tests. |
| `tests/test_powerup_4weapons.py` | NEW: ~6 tests. |
| `tests/test_hud_slots.py` | NEW: ~4 tests. |
| `tests/test_weapon_fire.py` | NEW: ~5 tests (RMB dispatch, ammo consume, no fire if empty, wheel cycling). |
| `tests/test_audio_weapons.py` | NEW: ~3 tests (SFX catalog presence + spec accuracy). |
| `docs/changelog/CHANGELOG_v1.x.md` | +2 entries (BLOQUE 71, BLOQUE 72). |

### 4.4 Implementation order

1. **BLOQUE 71** (1-2 sessions): tests → code → SFX → e2e 60s → visual capture → commit.
2. **BLOQUE 72.A** (1-2 sessions): `WeaponSlot` dataclass + player state + HUD slots (no weapons yet). Tests + visual capture (HUD with all 4 slots in different states).
3. **BLOQUE 72.B** (2-3 sessions): 4 weapons one by one. Each weapon: bullet sprite → firing function → SFX → tests → visual. Cumulative test.
4. **BLOQUE 72.C** (1 session): input remap (RMB + wheel). Drop pool rebalance. End-to-end test (60s, all 4 weapons fired at least once).
5. **Release** (1 session): .exe rebuild + zip + GitHub release.

## 5. Decisions log (resolved with user 2026-09-09)

| Q | Decision |
|---|---|
| MINE open3 hit feedback | Option A: white flash all states, no progress indicator (replaces current red). |
| Flash duration | 0.15s (same as ships). |
| Asteroid hit SFX | YES, `asteroid_hit.wav` added in this BLOQUE. |
| Regular asteroid destructibility | UNCHANGED. Indestructible, no powerup drop. |
| Weapon letter mapping | A / S / D / F (WASD mirror). |
| Initial ammo per pickup | Medium (30 per pickup, tunable in `settings.py`). |
| Mouse wheel scope | Only slots with ammo (skip empty). |
| RMB on empty active slot | Auto-cycle to next filled slot. |
| Stack behavior | Cap at max_ammo, excess silently dropped. |
| HUD slot position | Bottom-center, between HP and score. |
| LMB charge-up laser | UNCHANGED, not a powerup. |
| Rapid-fire RMB | REMOVED, replaced by powerup fire. |
| Boss-tied weapon drops | NO, random equal-weight from 6-kind pool. |
| New sprite generation | Procedural 8-bit PIL, no AI gen. |

## 6. Acceptance criteria (8-point from handoff)

For **BLOQUE 71:**
1. ✅ `pytest tests/test_asteroid.py tests/test_mine_asteroid.py` passes.
2. ✅ `pytest tests/` no new regressions (1,639 + 6 pre-existing failures maintained).
3. ✅ `GameplayRuntime.update()` runs 60s without `NameError` in `logs/crash.log` (BLOQUE 70 pattern).
4. ✅ PNG capture in `tools/playtest_out/` showing regular asteroid mid-flash AND MINE-ASTEROID mid-flash.
5. ✅ User confirms visual: white flash is visible and brief.
6. ✅ .exe rebuild.
7. ✅ Commit + push to `master`.
8. ✅ CHANGELOG entry.

For **BLOQUE 72** (same 8 + extras):
1-8 above, PLUS:
9. ✅ All 4 weapons fire from RMB correctly.
10. ✅ Mouse wheel cycles only filled slots.
11. ✅ RMB on empty slot auto-cycles to next filled.
12. ✅ Each weapon has a unique SFX that plays on fire.
13. ✅ HUD shows 4 slots, current state matches inventory.
14. ✅ Capture: HUD with 0/1/2/3/4 slots, each weapon mid-fire, mouse wheel mid-cycle.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Continuous laser (S) + flamethrower (D) + double laser (F) all "hold RMB" can cause perf issues (many bullets/tick) | Cap bullet count per weapon. Laser = single beam (not many particles). Flamethrower = max 5 active. Already-tested ProjectilePool capacity (400) absorbs this. |
| BOMB/HP drops conflict with new weapon drops in MINE pool | Old pool was 3 kinds, new is 6. Weights normalized to 1/6 each. BOMB/HP still drop, just less frequently (50% × 1/6 = ~8% each). |
| Mouse wheel can desync active slot index if multiple events fire in one frame | Wheel events are processed in event loop before update; index is single source of truth. |
| HUD slots cover existing HUD elements (HP, score) | Bottom-center is empty in current HUD (HP left, score right). No conflict. |
| Powerup snap animation (0.3s) delays ammo apply | Apply ammo immediately on collision (not on animation end). Animation is visual only. |

## 8. Out of scope (deferred)

- Mouse aiming reticle change.
- Custom crosshair per weapon.
- Weapon-specific reload times (all weapons are ammo-based, no reload).
- Weapon upgrades (e.g., laser level 2 = wider beam) — pure quantity, no tiers.
- Tradeoff with non-weapon powerups in HUD (BOMB/HP aren't in the slot system).
- Save/load weapon state across runs.
