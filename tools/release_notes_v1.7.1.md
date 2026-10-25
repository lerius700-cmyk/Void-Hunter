# VOID HUNTER v1.7.1 (BLOQUE 67) — el .exe ya se ve igual que `python main.py`

> Release de corrección. La v1.7.0 tenía el juego completo pero el `.exe`
> compilado **no cargaba el fondo pintado del boss fight**. Esto lo arregla.

---

## 🐛 El bug

`Assets/imagen fondo del juego.jpg` (3.4 MB, el fondo pintado de la pelea
contra GOLIATH) vive en la **raíz** de `Assets/`. El `build.spec` bundleaba
carpetas (`Assets/background`, `Assets/sprites`, `Assets/video`) y WAVs
sueltos de la raíz, pero no ese JPG.

Consecuencia en el `.exe`:

- `TilingImage.is_ready` era `False`
- el boss fight caía al fallback del parallax
- y se veía **negro con estrellas** en vez de la nebulosa con los asteroides
  y la estructura "Keep Kept"

Era un fallo **silencioso**: `--check` pasaba, los 2825 tests pasaban, y el
juego arrancaba sin quejarse. Sólo se notaba mirando el fondo de la pelea.

También faltaba `Assets/voice_gameplay.wav` — la voz de gameplay (BLOQUE 50).

## 🔧 El fix

`build.spec` ahora bundlea la raíz de `Assets/` con un **glob** en vez de una
lista a mano:

```python
*[(str(p), "Assets")
  for p in sorted((PROJECT_ROOT / "Assets").glob("*"))
  if p.is_file() and "_lp" not in p.name]
```

Con el glob no se puede volver a colar un asset de la raíz sin bundlearlo. Se
excluyen los `*_lp*.wav` porque son el caché del lowpass (61 MB por cutoff)
que el juego regenera solo; el único que va a propósito es el `lp600`
pre-generado (BLOQUE 58.14), que sigue listado aparte.

## ✅ Guard

`tests/test_build_spec_assets.py` (7 tests) verifica la cobertura del
`build.spec` **sin necesidad de compilar**:

- el fondo del boss fight está bundleado
- la raíz de `Assets/` se bundlea con glob
- el caché del lowpass se excluye (menos el `lp600`)
- `Assets/background/`, `Assets/sprites/` y `Assets/video/` están
- los 6 tiles del Asteroid Approach y los 60 frames de GOLIATH están

Para que un bug de packaging no vuelva a llegar a una release publicada.

## 📦 Qué trae esta release

Lo mismo que la v1.7.0, con el `.exe` corregido:

- GOLIATH con el escudo invisible medido sobre la placa, capa de calor y
  parpadeo de impacto, láser naranja grueso, y el láser del ojo saliendo del
  ojo
- el fondo ASTEROID NEBULA real de v1.4.0 (los 6 tiles del Asteroid
  Approach, recuperados)
- el menú post-cinematica (NEW GAME / BOSS TIME / BACKGROUND)
- el sistema de 4 armas (BLOQUE 72 + 73 Fase A/B/C)

---

**Suite:** 8 failed / 2825 passed / 7 skipped — los 8 son fallos
pre-existentes documentados. Cero regresiones.

**Verificación visual:** comparación lado a lado del `.exe` contra
`python main.py` corriendo desde el mismo worktree — el boss fight y el
título se ven **idénticos**.

**Nota de arranque:** el `.exe` tarda ~2.3 s en abrir la ventana (extracción
onefile de 277 MB). No es un bug: es el costo del ejecutable de un solo
archivo. Corriendo `python main.py` la ventana aparece al instante.

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.7.1-win64.zip` (~276 MB).
2. Extraé en cualquier carpeta.
3. Doble-click en `void-hunter-v1.7.1.exe`.

## 💻 Requisitos

Windows 10/11 64-bit · ~290 MB disco · ~200 MB RAM
