# Silo: arch (Architecture)

**Propósito:** Documentación arquitectónica y roadmap del producto VOID HUNTER. Single source of truth para decisiones de diseño de alto nivel.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `ARCHITECTURE.md` | Mapa | Los 13 sistemas del juego con LOC por módulo y diagrama de dependencias |
| `ROADMAP.md` | Plan | Roadmap del producto (features en curso, próximas, futuras) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `ARCHITECTURE.md` | L (LOAD) | Mapa de sistemas — entry point técnico |
| `ROADMAP.md` | R (REFERENCE) | Plan de features — consultar al estimar scope |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| `ARCHITECTURE.md` ↔ `src/` | Mapeo archivo → sistema | `grep -c 'class\|^def ' src/ui/gameplay_runtime.py` (debe matchear LOC declarado) |

> Cada bridge necesita un Truth Anchor verificable: comando shell real, no la frase suelta.

---

## Cuándo entrar a este silo

- Decisiones de arquitectura (nuevo sistema, refactor mayor, cambio de stack).
- Onboarding de un agente nuevo que necesita entender el sistema.
- Estimación de scope ("¿cuánto cuesta agregar X?").
- Documentar un BLOQUE nuevo en el mapa.

## Cuándo NO entrar

- Implementar código de un sistema existente → ir a `src/<sistema>/`.
- Cambios visuales → ir a `tools/` (capture scripts) + revisar `Assets/`.
- Tests → ir a `tests/`.

---

## Lock Status

**Estado:** Sin lock
