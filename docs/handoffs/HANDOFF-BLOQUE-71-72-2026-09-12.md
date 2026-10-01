# HANDOFF — Trabajo futuro en BLOQUE 71+72 (asteroid hit + 4-weapon powerup)

> **Para el siguiente agente que trabaje en asteroid hit feedback, weapon powerup system, o BLOQUE 72 en general.**
> **Fecha:** 2026-09-12 (BLOQUE 72 Task 5 done; BLOQUE 71 ya released v1.4.0)
> **Contexto:** sesión cerrada después de BLOQUE 72 Task 5 (`8c8d82b`).

---

## TL;DR

**BLOQUE 71 está released (v1.4.0, `d70b8da`).** Asteroid hit feedback funciona end-to-end con flash shape-aware 70% opacity + SFX dispatch. **BLOQUE 72 está en curso, Task 5 done** (`8c8d82b`): `WeaponSlot` dataclass + ammo constants commiteado, 8/8 tests pass. **Pendiente T6+ en BLOQUE 72** hasta llegar al input remap RMB + wheel cycling.

Si vas a retomar BLOQUE 72, leé este documento completo. Si vas a otra cosa, sección "Other BLOQUE work" al final.

---

## 1. Estado actual del proyecto

| Item | Valor |
|---|---|
| **Path** | `F:\AI\Opencode Projects\Gaming Development\void-hunter\` |
| **Versión shipped** | v1.4.0 (commit `d70b8da` pushed) |
| **Tag** | `v1.4.0` en `origin/master` |
| **Release GitHub** | https://github.com/lerius700-cmyk/Void-Hunter/releases/tag/v1.4.0 |
| **HEAD local** | `8c8d82b feat: BLOQUE 72 Task 5 - WeaponSlot dataclass + ammo constants` |
| **Stack** | Python 3.11 + pygame 2.6, sin numpy en runtime |
| **Tests** | 2,700 pass + 23 pre-existing fail + 6 skipped (3 archivos nuevos en BLOQUE 71) |
| **LOC** | 26,760 en src/ (87 archivos Python) |
| **Display** | 240×360 escalado 2.1× a 674×1011 (internal 320×480) |

---

## 2. BLOQUE 71 — qué hace / qué NO hace

### Qué hace (verificado en gameplay + 18 tests nuevos)

- **`Asteroid.hit(damage=1)`** ahora setea `hit_timer = HIT_FLASH_DURATION_S = 0.15s` y retorna `False` (BLOQUE 64.A indestructible preservado).
- **Render shape-aware flash** (`draw_asteroid_with_hit_flash` en `src/entities/asteroid.py`): sprite original + overlay blanco al 70% opacity siguiendo el alpha mask. NO reemplaza el sprite (la forma rocosa se ve debajo). Antes del BLOQUE 71.1 era un cuadrado `BLEND_RGBA_ADD` opaco que rompía la silueta.
- **MINE-ASTEROID hit en 4 estados**: `closed/open1/open2/open3`. closed/open1/open2 son inmunes pero igual flashean; open3 toma HP-- con flash blanco (antes era rojo, BLOQUE 71.1 unifica). `Enemy.hit()` delega a `apply_damage()` para no-MINE kinds (preserva death animation pipeline).
- **`hit_timer` decrementa en TODOS los enemy kinds** (BLOQUE 71.2 fix). El bug original era que solo MINE-ASTEROID lo tickaba en `_update_mine_asteroid`.
- **SFX `asteroid_hit`** (noise burst 0.05s, vol 0.3) generado en `Assets/sounds/asteroid_hit.wav`. Dispatch en `_asteroid_bullet_collision` (`src/ui/gameplay_runtime.py:1754-1780`) vía `self._play_sfx("asteroid_hit", volume=0.3)`.

### Qué NO hace

- **NO hay daño a regular asteroids.** `Asteroid.hit()` retorna siempre False; siguen siendo indestructibles (decisión BLOQUE 64.A — feel Star Fox 64).
- **NO hay line/wire indicator visual** del `hit_timer` decay. Solo el flash blanco cubre la silueta durante 0.15s.
- **NO hay hit SFX diferenciado** para cada enemy kind (asteroid_hit se reusa para SCOUT/CRUISER/HEAVY/MINE). Si querés SFX distintos, hay que agregar specs en `src/audio/sfx.py`.

---

## 3. BLOQUE 72 — qué está hecho, qué falta

### Fase 1 (BLOQUE 71 — done, released)

T1–T4: spec, plan, dispatch refactor, e2e visual + CHANGELOG + release v1.4.0.

### Fase 2 (BLOQUE 72 — en curso)

#### Task 5 ✅ (commiteado `8c8d82b`)

- `src/entities/weapon_slot.py` (40 LOC) — `WeaponSlot` dataclass con `letter`, `weapon_id`, `ammo`, `max_ammo`. Métodos: `is_empty` property, `add_ammo(amount)` (cap en max, excess dropped), `consume(amount)` (retorna amount consumido, nunca negativo).
- `src/core/settings.py` — 5 constantes nuevas: `WEAPON_PICKUP_AMMO=30`, `MAX_AMMO_THICK=100`, `MAX_AMMO_LASER=200`, `MAX_AMMO_FLAME=50`, `MAX_AMMO_DOUBLE=150`.
- `tests/test_weapon_slot.py` (8 tests) — init empty, add_ammo stacks/caps/exact, consume clamps. **8/8 pass.**

#### Task 6 ⏳ (SIGUIENTE — listo para arrancar)

**Files:**
- Modify: `src/ui/gameplay_runtime.py` (`__init__` method, agregar state de weapon slots).
- Create: `tests/test_runtime_weapon_slots.py` (5 tests).

**Spec:**
```python
# En GameplayRuntime.__init__ (al final, antes del bloque if is_boss: si existe):
from src.entities.weapon_slot import WeaponSlot
from src.core.settings import (
    WEAPON_PICKUP_AMMO,
    MAX_AMMO_THICK, MAX_AMMO_LASER, MAX_AMMO_FLAME, MAX_AMMO_DOUBLE,
)
self._weapon_slots: list[WeaponSlot] = [
    WeaponSlot("A", "thick",  0, MAX_AMMO_THICK),
    WeaponSlot("S", "laser",  0, MAX_AMMO_LASER),
    WeaponSlot("D", "flame",  0, MAX_AMMO_FLAME),
    WeaponSlot("F", "double", 0, MAX_AMMO_DOUBLE),
]
self._weapon_active_idx: int = 0
self._weapon_pop_anim: dict[str, float] = {"A": 0.0, "S": 0.0, "D": 0.0, "F": 0.0}
```

**Tests (5):**
1. `runtime._weapon_slots` existe y tiene 4 items.
2. Todos los slots inician vacíos (ammo=0, is_empty=True).
3. Letters son ["A", "S", "D", "F"] en ese orden.
4. weapon_ids son ["thick", "laser", "flame", "double"].
5. `_weapon_active_idx == 0` inicial.

**RED test primero:**
```python
"""BLOQUE 72 T6: GameplayRuntime initializes 4 empty weapon slots."""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
pygame.init()
import pytest
from src.ui.gameplay_runtime import GameplayRuntime

@pytest.fixture
def runtime():
    return GameplayRuntime(transition_to=lambda *a, **k: None)

def test_runtime_has_4_weapon_slots(runtime):
    assert hasattr(runtime, "_weapon_slots")
    assert len(runtime._weapon_slots) == 4

def test_slots_initially_empty(runtime):
    for s in runtime._weapon_slots:
        assert s.ammo == 0
        assert s.is_empty is True

def test_slot_letters_are_asdf(runtime):
    letters = [s.letter for s in runtime._weapon_slots]
    assert letters == ["A", "S", "D", "F"]

def test_slot_weapon_ids(runtime):
    ids = [s.weapon_id for s in runtime._weapon_slots]
    assert ids == ["thick", "laser", "flame", "double"]

def test_active_idx_starts_at_zero(runtime):
    assert runtime._weapon_active_idx == 0
```

**Commit message:**
```
feat: BLOQUE 72 — 4 empty weapon slots in player state
```

#### Task 7 ⏳ (PowerupKind expansion)

- Modify `src/entities/asteroid.py` — reemplazar `PowerupKind.WEAPON` por 4 nuevos: `THICK/LASER/FLAME/DOUBLE`. Actualizar `POWERUP_WEIGHTS` (suma=100).
- Modify `src/entities/enemies/enemy.py` — `pick_mine_powerup` a 6-kind pool.
- Tests: `tests/test_powerup_4weapons.py`.

#### Task 8 ⏳ (_apply_powerup fills slots)

- Modify `src/ui/gameplay_runtime.py` — agregar `_apply_powerup_weapon()` helper + hook en `_apply_powerup` (asteroid path en línea ~1808 y enemy path en ~3604) + tick del pop anim en `update()`.
- Tests: `tests/test_apply_powerup_4weapons.py` (7 tests).

#### Task 9 ⏳ (HUD slot rendering)

- Modify `src/ui/hud.py` — `_draw_weapon_slots()` method (4 cajas 12×12 bottom-center, color por weapon, pop scale 1.0→1.4→1.0 en 0.2s, ammo count, selection pulse 0.5Hz).
- Hook en `HUD.draw()` con 3 nuevos kwargs (`weapon_slots`, `weapon_active_idx`, `weapon_pop_anim`).
- Tests: `tests/test_hud_slots.py` (4 tests).

#### Task 10 ⏳ (BLOQUE 72.A e2e + visual)

- `tools/verify_bloque_72a_e2e.py` — 60s + 4 capturas PNG (0/1/2/4 slots).
- `tools/playtest_out/bloque_72a_slots_*.png`.
- CHANGELOG entry para BLOQUE 72.A.

#### Task 11+ ⏳ (Fase 72.B — 4 weapon kinds)

- `src/entities/projectile.py` — 4 funciones de disparo (`fire_thick`, `fire_laser`, `fire_flame`, `fire_double`).
- SFX: `shoot_thick`, `laser_hum`, `flame_loop`, `shoot_double` (WAV via `tools/synth.py`).
- Sprites: `Assets/sprites/weapons/bullet_thick.png`, `laser_beam.png`, `flame_particle.png`, `double_laser.png` (16×16 procedural via `tools/weapon_assets/`).

#### Task N ⏳ (Fase 72.C — input remap)

- Modify `src/ui/gameplay_runtime.py` — RMB ahora dispara weapon activa (consume ammo del `_weapon_slots[_weapon_active_idx]`).
- Mouse wheel UP/DOWN cicla `_weapon_active_idx` (con wrap-around).
- LMB queda como primary fire (default).

---

## 4. Archivos clave para retomar BLOQUE 72

```
src/entities/weapon_slot.py              ← T5 done (dataclass + ammo logic)
src/core/settings.py                     ← T5 done (5 ammo constants)
tests/test_weapon_slot.py                ← T5 done (8 tests)

src/ui/gameplay_runtime.py               ← T6 target (__init__ + slots state)
tests/test_runtime_weapon_slots.py       ← T6 to create (5 tests)

src/entities/asteroid.py                 ← T7 target (PowerupKind.WEAPON → 4 kinds)
src/entities/enemies/enemy.py            ← T7 target (pick_mine_powerup 6-kind pool)
tests/test_powerup_4weapons.py           ← T7 to create

src/ui/hud.py                            ← T9 target (_draw_weapon_slots method)
src/audio/sfx.py                         ← T11 target (4 weapon SFX)
src/entities/projectile.py               ← T11 target (4 firing functions)
Assets/sprites/weapons/                  ← T11 target (procedural bullets)
Assets/sounds/                           ← T11 target (procedural SFX)

docs/superpowers/specs/2026-09-09-asteroid-hit-and-powerup-system-design.md
docs/superpowers/plans/2026-09-09-asteroid-hit-and-powerup-system.md
```

**Spec:** `docs/superpowers/specs/2026-09-09-asteroid-hit-and-powerup-system-design.md`
**Plan:** `docs/superpowers/plans/2026-09-09-asteroid-hit-and-powerup-system.md` (Tasks 1-10 detallados con código)

---

## 5. ANTI-PATRONES aprendidos (lee si vas a tocar código)

### 5.1 El bug `hit_timer` solo en MINE (BLOQUE 71.2)

El dispatch original seteaba `hit_timer` solo para MINE-ASTEROID (en `_update_mine_asteroid`). El resto de enemies (SCOUT/CRUISER/HEAVY) flasheaban con la lógica vieja (square `BLEND_RGBA_ADD` opaco). BLOQUE 71.2 fix: el decrement tiene que estar en el path genérico (`Enemy.update` o equivalente), no en cada kind-specific updater.

**Regla:** cuando agregás un counter a una jerarquía (Enemy base + MINE subclass), el tick del counter va en la base, no en el subclass.

### 5.2 El refactor a `Enemy.hit()` centralizado (BLOQUE 71)

Antes de BLOQUE 71, la lógica de hit estaba dispersa entre `_asteroid_bullet_collision` (gameplay_runtime.py), `_update_mine_asteroid` (enemy.py), y posiblemente otros sitios. BLOQUE 71 centralizó en `Enemy.hit(damage)` que delega a `apply_damage()` para no-MINE kinds.

**Regla:** cuando una acción lógica está duplicada en 3+ sitios, refactor a un método en la jerarquía. **PERO** primero escribí el test que verifica el comportamiento actual end-to-end (60s e2e), así sabés que el refactor no rompe nada.

### 5.3 Shape-aware flash vs square flash (BLOQUE 71.1)

La implementación original era `pygame.Surface.fill((255,255,255)) + BLEND_RGBA_ADD(200/255)`. Eso producía un cuadrado opaco en el bounding box del sprite — rompía la silueta del asteroid y se veía como un bloque blanco, no como "el asteroid está flasheando".

La implementación nueva itera pixel-by-pixel sobre el sprite original y reemplaza solo los colores no-rocosos con blanco, manteniendo la silueta exacta.

**Regla:** si vas a hacer un "flash" visual, asegurate que la silueta del sprite se preserve. Un flash que cambia la forma NO es un flash, es un reemplazo.

### 5.4 NO digas "listo" sin e2e + visual

BLOQUE 71 released con `tools/verify_bloque_71_e2e.py` que corre 60s + captura PNG. La captura está en `tools/playtest_out/bloque_71_asteroid_flash_01.png` y muestra al menos un asteroid en estado mid-flash (blanco con silueta rocosa visible).

**Regla:** cada BLOQUE debe cerrar con un script `tools/verify_bloque_NN_e2e.py` que corre 60s sin crash + 1+ captura PNG. Si no podés correr el e2e headless (display requerido), NO digas "listo".

---

## 6. Acceptance criteria para "done" en BLOQUE 72

El siguiente agente debe verificar TODOS estos antes de decir "listo" en cualquier Task de BLOQUE 72:

1. ✅ `pytest tests/test_<task>.py -v` pasa con N tests.
2. ✅ `pytest tests/ --tb=no -q` sin regresiones nuevas (2,700 + 23 pre-existing failures).
3. ✅ **GameplayRuntime.update() corre 60s sin crash en `logs/crash.log`** (usar el patrón de `tools/verify_bloque_71_e2e.py`).
4. ✅ **Captura PNG del estado real** en `tools/playtest_out/`, con label que muestre el estado del feature.
5. ✅ **Comportamiento visible verificado**: el user confirma en gameplay que ve lo que debería ver (Lerius repite quejas hasta ver evidencia visual).
6. ✅ Commit con prefijo `feat: BLOQUE 72 — <descripción>`.
7. ✅ CHANGELOG entry en `docs/changelog/CHANGELOG_v1.x.md`.

Si falta cualquiera de estos 7, NO es "listo".

---

## 7. Comandos útiles

```powershell
# Activar venv
& "F:\AI\Opencode Projects\Gaming Development\void-hunter\.venv\Scripts\python.exe" ...

# Correr tests específicos
.\.venv\Scripts\python.exe -m pytest tests/test_weapon_slot.py -v
.\.venv\Scripts\python.exe -m pytest tests/ --tb=no -q

# Verificar e2e BLOQUE 71 (funciona, ya usado)
.\.venv\Scripts\python.exe tools/verify_bloque_71_e2e.py

# Verificar sf-sm compliance (script no disponible, manual via SKILL.md)
# Ver .synapse:short_term_memory.synaptic_shortcuts.auditar_sf_sm

# T6 verify
.\.venv\Scripts\python.exe -m pytest tests/test_runtime_weapon_slots.py -v

# Commit per BLOQUE rule
git add <files>
git commit -m "feat: BLOQUE 72 — 4 empty weapon slots in player state"

# NO push sin pedir (BLOQUE 58.14 rule). Push solo para releases.
```

---

## 8. Resumen ejecutivo (para el siguiente agente en 30 segundos)

- **Proyecto:** shmup vertical 8-bit pixelart en pygame, v1.4.0 en GitHub. 2,700 tests pass, 26,760 LOC.
- **BLOQUE 71 (DONE, released v1.4.0):** asteroid hit feedback con flash shape-aware + SFX dispatch.
- **BLOQUE 72 (EN CURSO, T1-T5 done):** 4-Weapon Powerup System. T5 WeaponSlot dataclass + ammo constants done. **T6 SIGUIENTE:** slots en GameplayRuntime.
- **Plan completo:** `docs/superpowers/plans/2026-09-09-asteroid-hit-and-powerup-system.md` (Tasks 1-10+ con código).
- **Pendiente T6:** agregar `_weapon_slots` (4 items), `_weapon_active_idx`, `_weapon_pop_anim` en `GameplayRuntime.__init__`. 5 tests en `tests/test_runtime_weapon_slots.py`.
- **Después de T6:** T7 (PowerupKind expand a 4 weapons), T8 (`_apply_powerup_weapon`), T9 (HUD slot render), T10 (e2e + visual BLOQUE 72.A), T11+ (Fase B y C — armas + input).
- **Anti-patrón crítico:** NO decir "listo" sin e2e 60s + captura PNG visible al user.
- **Lenguaje del user:** español, vos. Respeto por su paciencia. Él prefiere "listo" cuando TODO está verificado, no antes.
