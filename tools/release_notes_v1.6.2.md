# VOID HUNTER v1.6.2 — GOLIATH se anima (de verdad esta vez)

> El bug que quedaba. Los frames existían, el escudo se veía, el juego
> arrancaba — pero el jefe **no se movía**.

---

## 🎬 La animación nunca se tickeaba

`Boss.update_animation()` existe desde **BLOQUE 64.B** — fue escrito
exactamente para esto. Un grep por todo `src/` y `main.py` encuentra la
definición y **nada más**: no lo llamaba nadie.

`Boss.update(dt)` mueve la entidad pero nunca toca `animation_frame`. Así
que `animation_frame` se quedaba clavado en `0` durante toda la pelea.

Restaurar los 60 PNGs distintos (v1.6.0) no cambió nada en pantalla: el
juego seguía mostrando el frame 0 para siempre. Los dos bugs se
combinaban — los archivos estaban bien y el código nunca los leía más
allá del primero.

Ahora sí:

| | Antes | Después |
|---|---|---|
| Poses distintas en 6 s de pelea | **2** | **15** |
| `phase1_idle` | frame 0 fijo | cicla los 10 frames |
| `javelin` | frame 0 fijo | avanza 0→4 |

---

## 🎯 `--boss` ahora sí lleva a una pelea

El flag que recommended cada nota de desarrollo del repo **no hacía nada**:

```powershell
python main.py --boss goliath --easy --duration 5
```

Imprimía `full integration in next BLOQUE; running main game` y arrancaba
el título. Encima, el flag que las notas mencionan (`--boss-test`) **nunca
existió** en master — el real es `--boss`. El dev loop documentado para
trabajar con GOLIATH era un no-op por partida doble.

Ahora `_cmd_play` recorre la cadena de escenas válida
`TITLE → ACT_INTRO → GAMEPLAY → BOSS_INTRO → BOSS_FIGHT`, mapeando el
nombre del boss a su acto primero (GOLIATH acto 1, HYDRA acto 2, PHANTOM
y NEMESIS acto 3) porque el runtime elige el boss por número de acto.

Imprime `VOID HUNTER: jumped to GOLIATH (act 1)`. Un boss desconocido
sale con código 2 y un mensaje, en vez de arrancar un juego normal en
silencio.

---

## 🧪 6 tests que faltan

`tests/test_goliath_animation_advances.py` tickea el runtime real y
verifica:

- El frame avanza en `phase1_idle` (≥8 frames distintos en 3 s)
- Las 6 animaciones avanzan
- `death` se queda en frame 9 en vez de volver a 0
- Una animación de ataque vuelve al idle de su fase
- `--boss` aterriza en `BOSS_FIGHT` con un GOLIATH dentro

Los dos primeros son guardas contra una regresión que **ya pasó dos veces**
y que es invisible en una captura: el frame 0 es una pose perfectamente
válida.

---

## ✅ Verificación

| Check | Resultado |
|-------|-----------|
| `void-hunter-v1.6.2.exe --check` | `VOID HUNTER check OK` |
| `void-hunter-v1.6.2.exe --boss goliath` | `jumped to GOLIATH (act 1)` |
| Poses distintas en 6 s | **15** (era 2) |
| Tests boss/goliath/shield/javelin | **226 passed, 1 skipped** |

---

## ⬇️ Como jugar

1. Descargá `VoidHunter-v1.6.2-win64.zip` (~423 MB)
2. Extraé en cualquier carpeta
3. Doble-click en `void-hunter-v1.6.2.exe`

Para ver a GOLIATH directo, sin jugar el acto 1:

```
void-hunter-v1.6.2.exe --boss goliath --easy --scale 2 --duration 60
```

> **Ojo**: el flag es `--boss`, no `--boss-test`. Las notas viejas en
> `docs/superpowers/` todavía dicen `--boss-test` y están equivocadas.

## 💻 Requisitos

Windows 10/11 64-bit · ~430 MB disco · ~200 MB RAM