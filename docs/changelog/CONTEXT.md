# Silo: changelog

**Propósito:** Historia cronológica de cambios del producto VOID HUNTER. "Qué se intentó antes" para evitar repetir errores.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `CHANGELOG_v1.x.md` | Histórico | Changelog detallado de versiones v1.x (BLOQUE 1 → 58.14.4) |
| `CHANGELOG.md` | Raíz | Changelog de muy alto nivel (releases shipped) |

> **Nota:** `CHANGELOG.md` fue movido desde la raíz del repo (BLOQUE SF+SM 2026-08-17) para resolver el huérfano de Tree Integrity.

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `CHANGELOG_v1.x.md` | L (LOAD) | Historia detallada — consultar antes de cambiar algo |
| `CHANGELOG.md` | R (REFERENCE) | Releases shipped (auto-generable desde CHANGELOG_v1.x) |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| CHANGELOG ↔ git | Cada commit tiene un BLOQUE | `git log --oneline \| grep -E 'BLOQUE [0-9]+'` |
| CHANGELOG ↔ versión | Cada release tiene commit + tag | `git tag --list 'v*' \| sort -V` |

---

## Cuándo entrar a este silo

- "¿Se intentó esto antes?" antes de implementar.
- "¿Qué BLOQUE toca este cambio?" al planificar.
- "¿Cuál es la versión actual?" antes de release.
- Verificar que un bug ya no fue resuelto en un BLOQUE anterior.

## Cuándo NO entrar

- Implementar → ir a `src/`.
- Tests → ir a `tests/`.
- Decisiones arquitectónicas → ir a `docs/arch/`.

---

## Lock Status

**Estado:** Sin lock
