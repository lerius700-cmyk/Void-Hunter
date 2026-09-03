# Silo: movement (Ship Choreography — FROZEN subsystem)

**Propósito:** Documentar el sistema de coreografía de naves enemigas. **FROZEN subsystem** — la implementación en `src/movement/` y `src/systems/wave_patterns/` no se debe modificar sin re-leer este silo completo. Cambios al contrato rompen silenciosamente los 56 wave patterns (6 base) + 4,275 COMPOSED cross-product patterns.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `README.md` | Índice | "The soul of the game" + source code map + contract table |
| `01_movement_primitives.md` | Spec | `BezierPath`, `WaypointPath`, `HybridPath` (los 3 building blocks) |
| `02_formations.md` | Spec | `FlightFormation` + 9 shapes (V, LINE, DIAMOND, SQUARE, WEDGE, CIRCLE, TRIANGLE, HALF_V, CUSTOM) |
| `03_path_follower.md` | Spec | `PathFollower`, `FormationPathSpec` (cómo navegan las naves) |
| `04_wave_patterns.md` | Spec | 6 base + 50 COMPOSED patterns + `ProceduralWaveManager` |
| `05_advanced_paths.md` | Spec | `ParallelPathPair` (SF64 pair dance) + `OrbitalPath` (butterfly orbit) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo + FROZEN status |
| `README.md` | L (LOAD) | Índice + contract table (no romper sin leer) |
| `01_movement_primitives.md` | L (LOAD) | BezierPath / WaypointPath / HybridPath |
| `02_formations.md` | L (LOAD) | 9 formation shapes |
| `03_path_follower.md` | L (LOAD) | PathFollower + spec |
| `04_wave_patterns.md` | L (LOAD) | 56 patterns + manager |
| `05_advanced_paths.md` | L (LOAD) | ParallelPathPair + OrbitalPath |
| `src/movement/*.py` | R (REFERENCE) | Implementación — FROZEN, no tocar |
| `src/systems/wave_patterns/*.py` | R (REFERENCE) | Implementación — FROZEN, no tocar |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|---------------|
| `README.md` ↔ `src/movement/` | 8 archivos documentados ↔ 8 archivos reales | `Get-ChildItem src/movement -Filter *.py \| Measure-Object \| Select-Object -ExpandProperty Count` (debe ser 8) |
| `README.md` ↔ `src/systems/wave_patterns/` | 10 archivos documentados ↔ 10 archivos reales | `Get-ChildItem src/systems/wave_patterns -Filter *.py \| Measure-Object \| Select-Object -ExpandProperty Count` (debe ser 10) |
| Contract table ↔ source | `BezierPath.position_at`, `PathFollower.update`, `FlightFormation.offsets`, `HybridPath.position_at` | `pytest tests/test_movement.py tests/test_wave_patterns.py -q` (debe pasar todos) |

> Cada bridge necesita un Truth Anchor verificable: comando shell real (PowerShell-compatible), no la frase suelta.

---

## Cuándo entrar a este silo

- **ANTES** de modificar cualquier archivo en `src/movement/` o `src/systems/wave_patterns/`.
- Cuando se reporta un bug visual de movimiento de naves (path incorrecto, formation rota, ship no se mueve).
- Cuando se diseña un nuevo wave pattern o formation shape.
- Cuando se refactoriza la math del bezier / waypoint / hybrid.
- En el SF-SM audit (cualquier persona/agente que entre al proyecto).

## Cuándo NO entrar

- Cambios de gameplay que NO son movement → ir a `src/ui/` o `src/entities/`.
- Cambios visuales de UI / HUD → ir a `src/ui/`.
- Cambios de audio → ir a `src/audio/`.
- Cambios de wave data (qué oleada aparece en cada act) → ir a `Assets/` (JSON waves).

---

## Lock Status

**Estado: FROZEN** (intencional)

**Razón:** este silo documenta la "alma" del juego (Star Fox 64-style choreography + sacred geometry & fractal patterns). Cambios al contrato sin re-leer las 7 secciones + `06_paths.md` rompen silenciosamente los 56 wave patterns + 4,275 COMPOSED. La próxima vez que se desbloquee, **re-leer completo y agregar test de regresión** por cada cambio de signature.

**Historial de un-FREEZE:**
- 2026-09-02: BLOQUE 58.next (Movement Expansion: Sacred Geometry & Fractal Symbolism) — 10 formations + 7 paths + 4,275 COMPOSED patterns agregados. Re-FROZEN después de merge.

**Si necesitás cambiar algo aquí:** abrir un BLOQUE nuevo con spec en `docs/superpowers/specs/`, plan en `docs/superpowers/plans/`, y PR description que cite qué métodos del contract cambian.
