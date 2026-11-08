# HANDOFF — BLOQUE 75: gstack-review de la línea de release (2026-11-07)

**Rama:** `bloquec-67-goliath-port` · **Base de la review:** `d70b8da` (v1.4.0) · **Diff revisado:** `d70b8da..61c08d9` (333 archivos, +44.381 líneas) · **Perfil:** Lite · **Schema:** `.synapse` 2.2.0

Este handoff es el canal: lo que el próximo agente (y el otro agente sobre este
repo) necesita saber de la ola de revisión que siguió a la release v1.9.0.

---

## 1. Qué se revisó

`gstack-review` sobre el rango completo de la línea de release (no un PR):
**Pass 1 (CRITICAL)** + **Pass 2 (informational)** + **6 especialistas en
paralelo** (testing, security, maintainability, performance, simplification,
state-machines).

**Gate Integrity medido:** `listed=98 eligible=52 inspected=25 unread=27`,
`tagged={RH-13:26, RH-15:1, RH-15?:1, RH-16:4}`, `unmatched=101`.

- Los **26 RH-13** (suppression pragmas) son `# noqa: E402`, `# type: ignore`
  y `# noqa: PLC0415`: no silencian ninguna aserción. Ninguno es hallazgo.
- Los **4 RH-16** (excepción tragada) son estrechos y justificados
  (`except OSError:` alrededor de un log, `except pygame.error:` del
  fallback headless, `except Exception:` que devuelve `False` y **loguea**).
  Ninguno es hallazgo.
- El **RH-15** (timeout del CI 15 → 25 min) está justificado en el propio
  diff por una medición (136,83 s medidos en el run 42148928648).

---

## 2. Los 3 CRITICAL (corregidos en esta ola)

### 2.1 El gate pasaba en verde con un rango VACÍO

`tools/sprite_pipeline/gate.py` mide la promesa de la fase sobre el rango
`base..HEAD`. Con `--base HEAD` el rango tiene **0 commits**: todos los
checks de rango miden NADA, no encuentran nada que-MGIR y el gate imprimía
`PHASE 1 GATE OK` / `PHASE 2 GATE OK` (exit 0). Las constantes
`PHASE_1_BASE` / `PHASE_2_BASE` no estaban fijadas por ningún test.

**Contraposición ejecutada:** `gate.py --phase 1 --base HEAD` → `PHASE 1 GATE OK`,
exit 0. Los rangos reales son 110 y 57 commits.

**Corregido:** `_range_commit_count()` + guarda en `main()` **antes de cualquier
otro check** (un gate que tiene que correr todo para admitir que no vio nada
gasta el presupuesto del CI para aprender que está ciego). Un rango vacío es
un FAILURE, no un SKIP.

**Test:** `tests/test_gate_range_must_not_be_empty.py` (7 casos).

### 2.2 `--boss phantom` anunciaba PHANTOM y spawneaba NEMESIS

`main.py` mapeaba el nombre del boss a un **acto**, y el runtime elegía el
boss por el acto. El acto 3 es NEMESIS; PHANTOM sale del pool roguelike
(`src/roguelike/boss_pool.py`), no de un acto. El flag mentía.

**Corregido:** el boss se resuelve por **nombre** contra el enum `BossId`
(`main._resolve_boss`) y se entrega al runtime como id
(`GameplayRuntime(boss_id=...)`, `BossFightScene(boss_id=...)`). PHANTOM pide
prestado el acto 3 (el acto decide qué olas corren antes del combate).

**Test:** `tests/test_boss_flag_resolves_the_boss.py` (12 casos). La
contraposición está probada: con el override desactivado, 2 tests se ponen
rojos.

### 2.3 `--act N` se perdía en silencio

El branch `elif act is not None:` sólo hacía `transition_to(ACT_INTRO)` y
**nunca re-registraba las escenas** con el acto pedido: `Game.__init__`
las registraba con `act=1`. `--act 2` imprimía "jumped to act 2" y jugaba
**ACT 1**. Como `gameplay_runtime` exige `_act >= 3` para VICTORY, `--act 3`
tampoco llegaba a VICTORY.

**Corregido:** el acto es del **`Game`** (`Game(act=...)`), no del `main.py`:
las escenas se registran ahí, y el runtime calcula su índice de olas en el
constructor (parchear el acto después dejaría las olas del acto anterior).
`--patterns` sigue funcionando porque no se re-registra nada.

**Verificado:** `Game(act=2)` → `ACT_INTRO._act = 2`, `GAMEPLAY._rt._act = 2`,
`_wave_idx = 6` (antes 0).

---

## 3. Los fixes mecánicos (todos con contraposición o test)

| # | Archivo | Qué cambió |
|---|---------|-----------|
| 1 | `tools/sprite_pipeline/gate.py` | G13 lee el **junit XML** (exige 84 casos, 0 fallos, 0 errores, **0 skips**) en vez del exit code. `pytest` sale 0 si todo se skipea: un guard que deja de correr dejaba el gate verde. |
| 2 | `tools/sprite_pipeline/gate.py` | Comentario del presupuesto corregido (decía `timeout-minutes: 15`). La aritmética real: 840 + 1380 + 120 = **2340 s**. |
| 3 | `.github/workflows/test.yml` | `permissions: contents: read` + `persist-credentials: false` en los dos checkouts: el job corre código de la rama y el token no queda en `.git/config`. |
| 4 | `.github/workflows/test.yml` | Borrado el paso **"Install uv"** (no lo usaba nadie) y el comentario `.build-venv` que mentía sobre él. |
| 5 | `.github/workflows/test.yml` | El reloj del job `gates` pasa de 25 a **45 min**: 2340 s < 2700 s, así que el diagnóstico del gate SIEMPRE llega antes que el muro del job. |
| 6 | `src/anim/manifest.py` | `clip.dir` se valida: tiene que ser **un nombre** dentro del set. Se concatenaba a la ruta para LEER los frames y para ESCRIBIR los reparados: un `dir = "../../.."` salía del set. |
| 7 | `src/anim/clip.py` | La cache de superficies se indexa por `(clip_id, frame)` y no por `Path`: construir un `pathlib.Path` cuesta 4,25 µs (70× el lookup) y corría **por enemigo por frame** (12 ms/s de CPU al tope del juego). |
| 8 | `tools/regen_status.py` | `BINARY_REL` se **deriva** de `VERSION` (una sola fuente). Antes estaban escritos dos veces y el comentario decía que había una. |
| 9 | `tools/regen_status.py` | El parser de pytest cuenta los **errores** como fallos y nombra los tests que ERROREARON. "2 passed, 1 error" se leía como "2 pass, 0 fail" y el bloque afirmaba que la suite estaba verde. |
| 10 | `tools/regen_status.py` | `loc()` y `pyfiles()` pasan el folder como **argumento**, no interpolado en el código ni en un `-Command` de PowerShell. |
| 11 | `tests/test_redesign_sprites.py` | La sonda que decide el `skipif` captura **sólo `FileNotFoundError`**. Con `except Exception`, un wrapper ROTO hacía que los tests que existen para cazar un wrapper roto se saltaran en silencio. |
| 12 | `src/ui/scenes.py` | `BossFightScene` inyecta el `_game` en su **runtime** (la misma trampa que BLOQUE 73.6 corrigió en el camino de gameplay, todavía abierta en el del boss). |
| 13 | `src/ui/scenes.py` | `TitleScene` lee su `_game` con guarda, como todas las demás escenas. Sin back-ref, las teclas de fondo no hacían nada (o reventaban con AttributeError). |
| 14 | `src/core/scene_manager.py` | La pausa anuncia "C: CREDITS" y la escena **pide** CREDITS, pero la tabla no lo permitía: el `StateError` se tragaba y la tecla no hacía nada. |
| 15 | `src/entities/enemies/boss.py` + `src/core/game.py` | `boss_for_act()` es la fuente única del acto→boss. La intro del boss ahora nombra al boss (decía el literal "BOSS"). |
| 16 | `docs/changelog/CHANGELOG_v1.x.md` | El header duplicaba métricas del bloque STATUS ("1,103 passing", la ruta `D:\AI\void-hunter`). Ahora apunta al bloque generado. |
| 17 | `tools/tiles/ai_gen/_batch_args.json` + `.gitignore` | Las URLs prefirmadas (con el **AccessKey ID** de Aliyun) salieron del archivo commiteado; la URL de una corrida nueva va en `_batch_args.local.json`, ignorado. |
| 18 | `docs/changelog/release-notes-v1.9.0.md` | Las release notes salieron de la raíz (el último huérfano de Tree Integrity) al silo `changelog`. |

---

## 4. Verificación (en este árbol, working tree sin commitear)

| Check | Resultado |
|-------|-----------|
| `pytest tests/ --tb=short` | **3162 tests, 0 fallos, 0 errores, 7 skipped** (6 skipped + 1 xfailed) |
| `tools/sprite_pipeline/gate.py --phase 1` | `PHASE 1 GATE OK` (exit 0) |
| `tools/sprite_pipeline/gate.py --phase 2` | `PHASE 2 GATE OK` (exit 0) |
| `gate.py --phase 1 --base HEAD` | `PHASE 1 GATE FAILED` (exit 1) — la contraposición del 2.1 |
| `main.py --check` | 15 scenes, 18 waves, 4 bosses |
| `main.py --check-pipeline` | 8 sets en `pivot=fixed scale=(1.05,1.05)`, `layers: 30`, exit 0 |
| `main.py --boss phantom` | `jumped to PHANTOM (act 3)` |
| `audit_sf_sm.py --perfil=lite` | **SF COMPLIANCE 7/7**, 0 findings |
| R1 (arte) | 0 PNGs modificados |

---

## 5. Decisiones que le pertenecen al usuario (NO se tomaron)

### 5.1 El gate del CI no bloquea merges
No hay branch protection en `bloquec-67-goliath-port` ni en `master`
(HTTP 404 en la API). El gate corre y falla el job, pero un merge puede
pasar sin él. Es el P1 abierto desde la revisión anterior.

### 5.2 El lowpass: 6,1 s de CPU bloqueante al entrar en GAMEPLAY
El diff **sacó del bundle** el WAV filtrado (`_lp600.wav`, 63,9 MB) y lo
pasa a calcular en runtime: `apply_lowpass_to_wav` es un bucle IIR por
muestra en Python puro sobre un WAV de 91,4 MB → **6,18 s medidos**, y
escribe 63,9 MB. El camino frío completo: 6,13 s + 63,9 MB.
La 2ª corrida es instantánea (0,0003 s) porque hay cache, **pero si la
carpeta del `.exe` no es escribible** (Program Files) el fallback escribe
en `_MEIPASS`, que se borra al salir → **6,1 s + 63,9 MB en CADA sesión**.
Opciones: (a) recalcular y publicar el WAV en el build (+63,9 MB de
descarga, el estado anterior); (b) generarlo en un hilo al arrancar y
bloquear la MÚSICA, no el frame; (c) dejarlo como está.

### 5.3 La AccessKey de Aliyun
El AccessKey **ID** `LTAI5t9dXq2sLrMZ8f1XfiFZ` quedó publicado en el
historial de git (commit `7d315aa`) de un repo **público**. El *secret* no
está en el repo y las URLs prefirmadas vencieron (403 verificado), así que
no es explotable hoy — pero si esa clave sigue viva, hay que **rotarla**.
Sacar la URL del árbol no la saca del historial.

---

## 6. Follow-ups que quedaron (además de los 13 del handoff de release)

1. La lista de los 8 sets de enemigos está literal en **14 archivos**; sólo
   3 copias están ancladas al disco por una aserción de igualdad. Un set nuevo
   queda fuera de 8 guardas y del `--check-pipeline`. El arreglo mínimo
   (un helper `discover_enemy_sets()` cacheado en `src/anim/clip.py` + una
   sola expectativa) toca 10-12 archivos: **vale la pena, no vale bloquear
   la release**.
2. `DrawContext` expone 4 campos (`origin`, `scale`, `time`, `size`) y 2
   métodos (`with_origin`, `at`) que **ningún consumidor de producción lee**.
   Borrarlos es un diff chico, pero `src/render/` se aprobó como motor
   genérico: borrarlos es una decisión de arquitectura.
3. `Part.on_missing` y `AnimSet.sided` no los lee nadie. `meta.sided` es un
   **duplicado** de `detect.side` (el mismo hecho declarado dos veces, capaz
   de contradecirse). O se los borra, o se los vuelve load-bearing.
4. 25 líneas duplicadas byte a byte dentro de `gate.py` (G11 vs P2-G5).
   Extraer un helper: −35 líneas netas.
5. `tools/sprite_pipeline/gate.py` tiene la lista de sets hardcodeada
   **mientras importa `discover_sets`**.
6. El bundle lleva `spritesheet_goliath_64b.png` (81 KB) y
   `_backup_pre_bloque_65/` (11 KB) que ningún código de runtime lee.
7. `src/anim/clip.py`: la cache del lowpass no incluye la identidad del
   track original, así que una actualización del juego en la misma carpeta
   reutiliza un WAV filtrado obsoleto.
8. Las actions del CI no están pineadas por SHA y las deps no están
   pineadas (`pillow>=10.0` es la nueva).

---

## 7. Cómo retomar

El árbol está **sin commitear** en
`F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port`. La ola completa
son 18 archivos modificados + 2 nuevos. **No se commiteó** porque la regla
del proyecto pide preguntar antes.

Para verificar la ola desde cero:

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=short -q
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
$env:PYTHONUTF8='1'
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py . --perfil=lite
```
