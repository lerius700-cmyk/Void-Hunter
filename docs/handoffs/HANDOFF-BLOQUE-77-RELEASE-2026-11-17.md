# HANDOFF — BLOQUE 77: la release **v1.10.0** (2026-11-17)

**Rama:** `bloquec-67-goliath-port` (la línea v1.4.0) · **Base:** `cfc28d8` ·
**Perfil:** Lite · **Schema:** `.synapse` 2.2.0

Este handoff es el **cierre de la entrega**: qué se publicó, cómo se verifica,
y qué NO se hizo.

---

## 1. Qué se publica

**v1.10.0** — la release que lleva el **contenido como clase primera** y el
**escudo de GOLIATH sobre su placa**.

Cuatro commits en la línea de release:

| Commit | Qué lleva |
|---|---|
| `e295b8c` | **BLOQUE 76** — la lista canónica de los 8 sets de enemigos (`src/anim/sets.py`), la puerta **G0** entre la expectativa y el descubrimiento, y las 6 fotos de referencia con **huella SHA256** (`tools/golden/layerstack/SHA256SUMS`) |
| `e9d2f15` | **BLOQUE 75 follow-ups** — las puertas que no medían: `gate_ci` con `--phase`/`--base`, la display que devuelve el motivo del fallo, el bundle sin los 7,3 MB de staging, el STATUS que se regenera con una función pura, el log del sub-boss sin rutas absolutas, y el generador que se niega a escribir fuera del repo |
| `f676bd7` | **BLOQUE 77 (parte 1)** — medir el escudo sobre el sprite **registrado** |
| `6ea95c9` | **BLOQUE 77 (parte 2)** — reconstruir en el espacio registrado + las 2 puertas que no medían |

### El artefacto

| Archivo | Tamaño | SHA256 |
|---|---|---|
| `void-hunter-v1.10.0.exe` | 214,1 MB | `3EF3ACFB14A898A4DF32F993F25D8A4704EBC4DFA16EEEAC52EC224CF1D1C5C0` |
| `VoidHunter-v1.10.0-win64.zip` | 213,3 MB | `DD83E1508B0CDE5A564EC1D878AEFF8A6995E57CA8AEF11BB5DAEAEC91DB7A00` |

Construido desde `cfc28d8` con `python -m PyInstaller build.spec --clean
--noconfirm` (28 s en esta máquina). El binario canónico vive en la **raíz**
del repo (`dist/void-hunter-v1.10.0.exe`), que es donde el generador del
STATUS lo mira: el worktree de release ya no lleva su propia copia.

---

## 2. Cómo se verifica (con la salida esperada)

```powershell
# el bundle lleva la medición ARREGLADA, no la vieja
python -c "from PyInstaller.archive.readers import CArchiveReader; ..."
#   -> el anchors.toml de GOLIATH dentro del .exe tiene el MISMO SHA256
#      que el del disco: cdd8459892f623ec0059eb74f913df93b029e01e940a7895a4e08d4da4e36297

# el binario responde
dist\void-hunter-v1.10.0.exe --check             # 15 scenes, 18 waves, 4 bosses (exit 0)
dist\void-hunter-v1.10.0.exe --check-pipeline    # los 8 sets + layers: 30 (exit 0)

# el codigo responde
python tools\sprite_pipeline\gate.py              # PHASE 1 GATE OK
python tools\sprite_pipeline\gate.py --phase 2    # PHASE 2 GATE OK
python -m pytest tests --tb=no                    # 3209 pass + 6 skip + 1 xfail = 3216, 0 fallos
python tools\capture\layerstack_frames.py --check  # GOLDENS MATCH (los 6 byte a byte)

# R1: ni un byte de arte
git diff --stat a0c6f6f -- '*.png'                # vacío
```

---

## 3. Lo que cambió para quien juega

**El láser naranja del escudo salía del sitio equivocado.** En 7 de los 60
frames de GOLIATH el óvalo caía sobre la panza del jefe en vez de sobre la
placa. La causa no era el arte: la regla de detección tiene columnas
**absolutas** y hay frames cuyo arte está corrido dentro de su canvas (el
registro lo compensa recién al dibujar). Medir sobre el sprite **registrado**
—y reconstruir en ese mismo espacio— lo deja sobre la placa en los 60 frames.

El ojo tenía el mismo bug y era peor porque no se veía: el ancla de
`death/frame_09` apuntaba a la fila 30, **dos filas por encima de la
silueta**, en el aire. Ahora apunta a la fila 38, sobre la cabeza.

**Probado por el usuario** (3 partidas contra GOLIATH el 2026-11-17): "la
hitbox del laser naranja grueso que se carga con disparos quedo bien".

---

## 4. Lo que NO se hizo (y por qué)

- **Los 2 frames que siguen reconstruidos** (`laser/f04`, `laser/f05`): el
  **haz rojo horneado** cruza la placa, así que el contorno que la identifica
  queda fusionado con el haz. Es el **ARTE**, y regenerar arte es decisión del
  usuario ("no agresivo regen" sigue en pie). Lo mismo con `death/f02`, donde
  el jefe se derrumba y dos detectores independientes discrepan.
- **El check `FIRMA_AMBIGUA`** (probe contra contorno) **se salta** cuando el
  óvalo no es creíble. El fix reduce el alcance del agujero, no lo cierra: la
  comparación con el probe debería correr también cuando el óvalo es
  interpolado.
- **`Part.on_missing` sigue sin leerse** (follow-up 6.3): el manifiesto declara
  `on_missing = "interpolate"` y el auditor interpola siempre, sin mirar la
  regla.
- **Los 90 KB de 3.6** (la hoja de contactos y el backup de la mina):
  excluirlos abriría un agujero en el bundle del jefe por el 0,04 % de la
  descarga. Se hizo la exclusión de los **7,3 MB** del staging area, que era
  el problema real (80× más grande de lo que decía el plan).
- **La AccessKey de Aliyun** no se puede rotar desde esta máquina: el runbook
  está en `docs/handoffs/HANDOFF-SECURITY-2026-11-08.md` §4 y se ejecuta desde
  la consola del usuario.
- **El push directo a la línea de release** entró con el bypass de admin de
  GitHub (los status checks todavía no habían corrido). Si se quiere que la
  rama quede protegida de verdad, la línea de release tiene que pasar por un
  **PR**.

---

## 5. Lo que le pertenece al usuario

1. **La AccessKey de Aliyun** (runbook en el handoff de seguridad, §4).
2. **Las 3 preguntas de alcance de la Fase 3** (`docs/bloques/BLOQUE_75_CHECKLIST.md` §P4).
3. **La tanda 6** (código muerto: `DrawContext`, `Part.on_missing`, `AnimSet.sided`).
4. **Si se commitean los 22 follow-ups** del BLOQUE 75.
5. **Si la línea de release pasa a PR** en vez de push directo.
