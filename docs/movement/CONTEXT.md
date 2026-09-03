# Silo: movement (Ship Choreography — FROZEN subsystem)

**Propósito:** Documentar el sistema de coreografía de naves enemigas. **FROZEN subsystem** — la implementación en `src/movement/` y `src/systems/wave_patterns/` no se debe modificar sin re-leer este silo completo. Cambios al contrato rompen silenciosamente los 56 wave patterns (6 base + 50 COMPOSED).

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

**Estado: TEMPORALMENTE UN-FROZEN** para BLOQUE 58.next (Movement Expansion: Sacred Geometry & Fractal Symbolism). Re-FROZEN after the spec + plan + implementation + tests are merged.

**Cambios durante este BLOQUE:**
- 10 nuevas formations agregadas (Flower of Life, Vesica Piscis, Fibonacci Spiral, Tree of Life, Sierpinski Triangle, Hex Close-Pack, Mandala Rings, Golden Ratio Row, Koch 3-fold, Dragon Curve)
- 7 nuevos paths agregados (Lemniscate, Cardioid, Lissajous, Rose k2/k3, Hypocycloid, Epicycloid)
- 4,275 nuevos COMPOSED patterns (full cross product 19 forms × 15 paths × 3 follows × 5 counts; cap raised from 50 a 4,275)
- "2D explicit" notation fix en `01_movement_primitives.md`

**Regla para próximos cambios:** reabrir el FROZEN es BLOQUE-worthy. Spec + plan + tests + visual proof antes de tocar el código.
