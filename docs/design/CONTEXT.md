# Silo: design (Game Design Document)

**Propósito:** Game Design Documents (GDDs) y decisiones de diseño de gameplay. NO arquitectura de software (eso vive en `docs/arch/`).

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `void-hunter-gdd.md` | GDD | Game Design Document principal del producto |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `*.md` | L (LOAD) | GDDs (cargar al decidir gameplay) |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| GDD ↔ código | Cada regla del GDD tiene un test o un check en runtime | `grep -r 'GDD §' src/ tests/` |
| GDD ↔ excepciones | Excepciones documentadas (ej. BLOQUE 58.14 numpy) | `grep -E 'BREAKING|EXCEPTION' docs/CHANGELOG_v1.x.md` |

> **Importante:** la regla GDD §0 dice "no numpy/scipy". El BLOQUE 58.14 ROMPE esa regla SOLO para `apply_lowpass_to_wav` (user-explicit). El GDD debe actualizarse si se decide institucionalizar la excepción.

---

## Cuándo entrar a este silo

- Decisiones de gameplay (balance, mechanics, feel).
- "¿Qué dice el GDD sobre X?" antes de cambiar comportamiento.
- Documentar un breaking change al GDD.

## Cuándo NO entrar

- Arquitectura de software → `docs/arch/`.
- Implementación → `src/`.

---

## Lock Status

**Estado:** Sin lock
