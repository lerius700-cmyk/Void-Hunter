# Silo: references (Visual References + Asset Sources)

**Propósito:** Assets de referencia visual que el usuario proveyó como source-of-truth. NO se modifican — son la "verdad" contra la cual se compara lo generado.

---

## Contenido del silo

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `Starfox_ships_8bits.png` | Referencia | Sprite sheet de naves Star Fox 8-bit (referencia para ship selection) |

---

## Token Budget

| Archivo/Pattern | Clasificación | Razón |
|-----------------|---------------|-------|
| `CONTEXT.md` | L (LOAD) | Misión del silo |
| `*.png` / `*.jpg` / `*.jpeg` | R (REFERENCE) | Binarios de referencia (consultar al regenerar assets) |

> Las tres marcas `L (LOAD)`, `S (SKIP)`, `R (REFERENCE)` aparecen literalmente.

---

## Bridges

| Bridge | Recurso | Truth Anchor |
|--------|---------|-------------|
| `references/*.png` ↔ `Assets/sprites/player_ships/` | Las naves generadas deben parecerse a la referencia | `python tools/test_nebula_render.py` (o equivalente para ships) |
| `references/Starfox_ships_8bits.png` ↔ `docs/arch/ARCHITECTURE.md` §Ship Selection | El spec referencia esta imagen | `grep -l 'Star Fox' docs/arch/ARCHITECTURE.md` |

---

## Regla de oro: usar las referencias, no AI-generar

Cuando el usuario provee una imagen de referencia y dice "esto es lo que quiero", **usar esa imagen** (extraer, derivar, reusar). NO sustituir con generaciones AI nuevas que "deberían verse similares".

Ejemplo histórico (BLOQUE 58.14.4):
- User: "las nebulosas se ven como blob, las ultimas 4 imagenes si. basate en eso"
- Wrong: regenerar con AI nuevas descripciones de "spiral galaxy"
- Right: extraer la galaxia central de `Assets/background/galaxy_panel_0/1/2.png` con peak detection.

---

## Cuándo entrar a este silo

- Antes de regenerar un asset visual.
- Cuando el usuario provee una imagen de referencia.
- Para validar que un asset generado se parece a la referencia.

## Cuándo NO entrar

- Modificar las imágenes (son referencia, no se tocan).
- Implementación → `src/`.

---

## Lock Status

**Estado:** Sin lock
