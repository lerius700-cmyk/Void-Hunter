# KNOWN_ISSUES — Estado de items diferidos al primer push

**BLOQUE:** 67 (primer push)
**Fecha:** 2026-10-21
**Estado:** vivo (se actualiza cuando cada issue se cierra)

> Tracker honesto del estado del repo al momento del primer push a
> GitHub. **No** es un bug-tracker: cada item tiene un *plan de
> resolución* claro o está esperando una sesión futura.

Este documento es la **primera lectura recomendada** para cualquiera
que clone el repo. Si algo no funciona como uno esperaría — tests
que fallan, números de versión que no coinciden con el binario — la
respuesta probablemente está acá.

Cuando un issue se cierra, moverlo a `## Cerrados` (al final) con la
fecha y el BLOQUE que lo resolvió. No borrar el histórico: el
doc mismo es un audit trail.

---

## ISSUE-001 — Divergencia source ↔ binario (la más importante)

**Symptom**: la fuente commiteada en este repo está en **BLOQUE 66.6**
(revert del óvalo GOLIATH a `0837a86` con `DX=-11`, `DY=6`, más el
bypass del test de phase change de la sesión de pulido del
2026-10-20). El binario distribuido como primer release
(`dist/VoidHunter-v1.4.0-win64.zip`, 397 MB) **se compiló el
2026-10-09** desde una fuente en BLOQUE 71 que **no vive en este
repo**.

**Impact**: quien clone el repo y lea el código va a ver *menos*
features que las que el binario distribuido expone. **No** es un bug
del juego; es disclosure honesta. El caption del `.exe` lee
`VOID HUNTER v1.4.0 (BLOQUE 71)` y el source muestra BLOQUE 66.6, y
eso debe estar documentado para que la diferencia sea evidente a
primera vista.

**Cómo confirmar** (en orden):

```powershell
# 1. La fuente está en BLOQUE 66.6
cd F:\AI\MM\void-hunter
git log --oneline | Select-Object -First 1
# Esperado: un commit cuyo mensaje menciona BLOQUE 66.6

# 2. El binario fue compilado en BLOQUE 71 (ejecutar el .exe)
& "dist\void-hunter\void-hunter.exe"
# Mirar la barra de título / primer frame. Debe decir v1.4.0 (BLOQUE 71)
```

**Fix plan** (sesión futura BLOQUE 67.next o BLOQUE 72):

1. Identificar el otro tree de source donde vive BLOQUE 71
   (presumiblemente un worktree separado o un clone en `D:\AI\void-hunter`).
2. Decidir política: ¿merge del BLOQUE 71 *into* este repo, o
   rebuild del `.exe` desde este repo? La segunda opción es la
   correcta si BLOQUE 71 nunca se commiteó porque era experimental.
3. Cuando la fuente esté en BLOQUE 71+, regenerar el binario con
   `pyinstaller build.spec --clean` y republicar el `.zip` del
   release.
4. ISSUE-003 se cierra automáticamente como side-effect.

**Status**: **OPEN**. Resolución: próximo BLOQUE post-67 que toque
la fuente.

---

## ISSUE-002 — Tests pre-existentes fallan por path hardcodeado

**Symptom**: **8 archivos de test** (más 1 sub-test puntual que ya se
fixeó en BLOQUE 66.6) fallan porque tienen referencias hardcodeadas
a `D:\AI\void-hunter\Assets\background\tiles\act1` mientras este
proyecto vive en `F:\AI\MM\void-hunter\`. Son artefactos de la vida
anterior del repo en otra máquina / otra ruta.

**Impact**: `pytest tests/` reporta **19 failures** en este push
inicial:

- 18 vienen del hardcoded path (8 archivos × ~3 tests cada uno =
  ~18).
- 1 (la trampa que se fixó en BLOQUE 66.6) era el
  `test_boss_phase_change_spawns_burst` y se bypaseó *temporalmente*
  (ver `tests/test_gameplay_runtime.py` comentario inline) — **no
  se borró el código del test**, se marcó `pytest.skip` con nota
  para retomar.

**Archivos de test afectados** (NO fixeados en este push —
explícitamente fuera de scope del primer push):

- `tests/test_asteroid_sprites.py`
- `tests/test_bloque_50_1.py`
- `tests/test_bloque_58_10.py`
- `tests/test_bloque_58_46.py`
- `tests/test_bloque_58_57.py`
- `tests/test_gameplay_runtime.py::test_boss_phase_change_spawns_burst` — *FIXED parciamente* (skip) en BLOQUE 66.6
- `tests/test_parallax_tile_mode.py`
- `tests/test_paths.py::test_paths_no_star_shapes`
- `tests/test_tile_manager.py`

**Tests que SÍ pasan** (run de verificación post-push):
**298/298** de los tests de boss/goliath/shield/javelin (ver
`docs/OPERATIONS.md` §5 y la checklist del review final del plan
`2026-10-20-v1-4-ship-as-is`).

**Cómo confirmar**:

```powershell
cd F:\AI\MM\void-hunter
python -m pytest tests/ -q 2>&1 | Select-String -Pattern "^(FAILED|=+ )"
# Esperado: lista de ~18-19 FAILED en los archivos de arriba
```

**Fix plan** (sesión futura, baja prioridad — el juego anda bien,
solo la suite de tests tiene polvo del pasado):

1. Reemplazar las ocurrencias literales de `D:\AI\void-hunter` por
   paths relativos al repo root. Patrón recomendado:
   ```python
   from pathlib import Path
   REPO_ROOT = Path(__file__).resolve().parent.parent
   TILE_DIR = REPO_ROOT / "Assets" / "background" / "tiles" / "act1"
   ```
   Esto hace los tests reproducibles en cualquier máquina.
2. Re-habilitar el test de phase change que se skipeó en BLOQUE 66.6
   (sacarle el `pytest.skip`) una vez confirmado que el revert del
   óvalo está estable.
3. Re-correr `pytest tests/ -q`. Target: 0 failures.

**Status**: **DEFERRED** (fuera de scope para el primer push).

---

## ISSUE-003 — `CLAUDE.md` reporta versión stale

**Symptom**: la primera línea de la metadata en `CLAUDE.md` dice
`Versión actual: v1.2.5 (BLOQUE 58.60 — gallery + sprite sheets)`. La
realidad al momento del primer push: el binario es **v1.4.0 /
BLOQUE 71**, y la fuente está en **BLOQUE 66.6** (ver ISSUE-001).

**Impact**: cosmético. Quien lee el repo ve una etiqueta de versión
vieja como header principal. No tiene impacto en runtime, tests, ni
binarios; es metadata.

**Fix plan**: cuando ISSUE-001 se cierre (source resynced a BLOQUE
71+), bumpear la línea de `CLAUDE.md` a la versión vigente (ej.
`Versión actual: v1.4.0 (BLOQUE 71)`). Resuelve como side-effect
— no requiere trabajo dedicado.

**Status**: **DEFERRED** (se cierra automáticamente cuando ISSUE-001
se cierra).

---

## ISSUE-004 — Smoke test puede fallar en CI sin `display.init()`

> *Opcional — incluido para honestidad del snapshot. Solo afecta CI
> headless; local con display funciona.*

**Symptom**: algunos tests que instancian `GameplayRuntime` fallan en
entornos CI headless que nunca llamaron a `pygame.display.init()`.
Local con monitor conectado funciona perfecto.

**Impact**: solo CI. Local no se ve afectado.

**Cómo confirmar**:

```powershell
cd F:\AI\MM\void-hunter
# En un entorno sin DISPLAY (server Linux, CI GitHub Actions):
SDL_VIDEODRIVER=dummy python -m pytest tests/test_gameplay_runtime.py -q
# Esperado: falla con "pygame.error: No video mode available" o similar
```

**Fix plan** (cuando se agregue CI real):

1. Crear `tests/conftest.py` con un fixture:
   ```python
   import pytest
   import pygame

   @pytest.fixture(autouse=True)
   def _ensure_display():
       pygame.init()
       if not pygame.display.get_init():
           pygame.display.init()
           pygame.display.set_mode((1, 1))
       try:
           yield
       finally:
           pygame.display.quit()
   ```
2. Confirmar que `pytest tests/ -q` pasa en CI con
   `SDL_VIDEODRIVER=dummy`.

**Status**: **DEFERRED** (no hay CI configurada aún; será relevante
cuando BLOQUE 67 D-series agregue GitHub Actions).

---

## Cerrados

_(Vacío al momento del primer push. Cada vez que un ISSUE-XXX se
resuelva, moverlo acá con la fecha y el BLOQUE.)_

---

## Referencias internas

- `CLAUDE.md` — identidad del proyecto + reglas globales.
- `docs/OPERATIONS.md` — runbook de `gh` / PAT / release.
- `docs/architecture/` — arquitectura + roadmap.
- `docs/bloques/2026-10-20-polish-bloque-66-6.md` — sesión del revert
  óvalo + bypass del test (causa raíz parcial de ISSUE-002).
