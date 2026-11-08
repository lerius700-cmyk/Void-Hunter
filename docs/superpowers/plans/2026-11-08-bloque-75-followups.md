# Plan de acción — los 22 follow-ups de BLOQUE 75

**Fecha:** 2026-11-08 · **Rama base:** `bloquec-67-goliath-port` (no `master`) · **Origen:** los 13 follow-ups de la revisión final de la release (`docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` §7) + los 9 de la revisión `gstack-review` (`docs/handoffs/HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` §6).

Este plan **no es un BLOQUE**: es una lista de trabajo ordenada para que un agente (o el owner) la ejecute sin volver a descubrir nada. Cada ítem dice **qué** hay que hacer, **cómo** se comprueba y **qué riesgo** tiene.

---

## 0. Las reglas de la casa (se aplican a TODAS las tandas)

- **R1** — ni un byte del arte cambia. Los PNG de `Assets/` son intocables.
- **R4** — runtime solo stdlib + pygame (+ numpy únicamente para el lowpass del pause).
- **R7** — headless y determinista. `SDL_VIDEODRIVER=dummy`.
- **L1** — sin tablas inline: la configuración vive en archivos.
- **L5** — excepts estrechos y justificados.
- **L7** — los tests nunca escriben en el repo (a `%TEMP%` o `tmp_path`).
- **Regla de oro de la fase** — *una garantía que el check no puede ver no es una garantía, es una hipótesis*. Todo check nuevo se prueba con **mutación + rojo pegado** antes de darse por bueno.
- **Un worktree y una rama por agente.** Nunca la raíz, nunca `master`. Nunca force-push.
- **Commits** con prefijo `feat:/fix:/docs:/test:/build:` y **paths explícitos** (nunca `-A`).
- **Antes de cada commit**: `python -m pytest tests\ --tb=no` + `python tools/sprite_pipeline/gate_ci.py` + `audit_sf_sm.py --perfil=lite`.

---

## 1. Orden de ejecución y dependencias

```
TANDA 1 (higiene)     → sin dependencias.  4 ítems, riesgo bajo.
TANDA 2 (los gates)   → T1 sólo por el orden del repo.  4 ítems, riesgo MEDIO (toca el gate).
TANDA 3 (el bundle)   → independiente.          3 ítems, riesgo bajo.
TANDA 4 (seguridad)   → independiente.          4 ítems, riesgo MEDIO.
TANDA 5 (lista canónica) → depende de T2 y T3 (toca los mismos archivos).  3 ítems, riesgo MEDIO-ALTO.
TANDA 6 (código muerto)  → DECISIÓN DEL OWNER antes de arrancar.  2 ítems, riesgo de rechazo.
TANDA 7 (truth anchors) → independiente.        3 ítems, riesgo bajo.
```

**Tanda 5 es la grande** (10-12 archivos). **Tanda 6 no arranca sin una decisión tuya**: son cosas que aprobaste como arquitectura.

---

## TANDA 1 — Higiene del repo

*Sin tocar el runtime. Todo mecánico salvo el #12.*

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 1.10 | **Ramas viejas** | Borrar las remotas `origin/bloquec-75-ci-gates`, `origin/bloquec-75-migration-spec`, `origin/bloquec-75-sprite-migration` y la local `bloquec-75-sprite-migration`. **Verificar primero** que ninguna tiene commits sin fusionar: `git log --oneline origin/<rama> --not bloquec-67-goliath-port`. | `git branch -a` no las lista | Bajo |
| 1.11 | **`target_commitish: "master"`** | El release dice `master` pero su tag vive en la línea de release. `gh release edit v1.9.0 --target bloquec-67-goliath-port`. | `gh release view v1.9.0 --json targetCommitish` | Bajo |
| 1.13 | **Ruta absoluta `D:/AI/void-hunter/logs/_sub_boss.log`** | `src/ui/gameplay_runtime.py:1707` (la línea se movió con la revisión). Dejarla de ser un path absoluto: resolverla desde `Path(__file__)`, igual que el resto del módulo. | Test que afirme que la ruta se resuelve bajo el repo, o que el log no se escribe en otra unidad | Bajo |
| 1.12 | **Prefijo `ci:`** | Hay **5 commits** con `ci:` (`aaebd25`, `ac419c8`, `cd42ced`, `65f209d`, `d38620d`), fuera de la lista global del plan. **NO se reescriben**: corregir un prefijo exige reescribir historia publicada (force-push). Lo que sí se hace: (a) registrar `ci:` como prefijo **permitido** en el plan global, o (b) dejarlo y anotarlo como deuda. **Decisión tuya, sin impacto funcional.** | El plan global lista el prefijo | Nulo |

---

## TANDA 2 — Cerrar los gates

*Lo más sensible del plan: el gate es la garantía de la fase. TDD con mutación.*

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 2.1 | **`gate_ci.main` sin test, y `main(argv)` ignora `argv`** | `main()` no usa su `argv`. Que lo use (o que el argumento se elimine y el llamador no lo pase) **y** testearlo: que devuelve el exit code correcto y que un gate que falla propaga el fallo. | Test nuevo en `tests/test_gate_ci.py`: `gate_ci.main([...])` con un gate inyectado que falla → exit != 0. **Contraposición**: que el test se ponga rojo si `main` vuelve a ignorar `argv`. | Bajo |
| 2.8 | **Los goldens se pueden regenerar en silencio** | El harness avisa pero lo permite, y el gate seguiría verde contra una prueba nueva. **Fijar el SHA256 de los 6 goldens** en un archivo (p.ej. `tools/golden/goldens.sha256`) y que el harness **falle** si un golden no está en la lista. | Regenerar un golden → el gate tiene que ponerse rojo. **Contraposición obligatoria.** | Medio |
| 2.9 | **En `master` el job `gates` es un no-op verde** | Ambas fases hacen SKIP (exit 0) porque ninguna base es ancestro de `master` → el job pasa sin medir nada. Y como la protección ahora **exige** `gates` en `master`, es una puerta que no mide. Opciones: (a) un flag `--require-applies` en el paso de la línea de release, que **falle** si ninguna fase aplicó; (b) quitar `gates` de los contexts requeridos en `master` y dejar sólo `pytest`. **(b) es lo coherente con lo que ya está instalado.** | `gh api .../branches/master/protection` → contexts sin `gates`; y un PR de prueba a `master` que no pueda pasar por un job vacío. | Bajo |
| 2.4 | **`_ensure_frame_display()` sin guarda de excepción** | Un fallo ahí produce un traceback en vez de un FAIL limpio. Envolverlo y devolver un estado de fallo explícito. | Test con `set_mode` que lanza `pygame.error` → el comando devuelve exit != 0 con un mensaje, sin traceback. | Bajo |

---

## TANDA 3 — El bundle

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 3.2 | **La regla de destino de `datas` es más estricta de lo necesario** | En el test del build-spec, rechaza una entrada legítima `("Assets", "Assets")`. Relajar la regla **sin** abrir un agujero: aceptar el par simétrico cuando el destino es el mismo directorio que el origen. | Test que hoy falla con `("Assets","Assets")` y pasa después. | Bajo |
| 3.3 | **Los 3 tests de mutación asertan sobre el predicado compartido** | En vez de invocar la función de test principal, assertan sobre el predicado. Que **invoquen la función principal**: un test que no la llama no puede detectar que la función se rompió. | Contraposición: mutar la función principal → los 3 tests se ponen rojos. | Bajo |
| 3.6 | **El bundle lleva archivos que nadie lee** | `spritesheet_goliath_64b.png` (81 KB, grew 36 KB en el diff) y `Assets/sprites/enemies/mine_asteroid/_backup_pre_bloque_65/` (11 KB) viajan dentro del `.exe` sin que ningún código de runtime los lea. Excluirlos del `datas` (o moverlos a una carpeta dev-only). | El TOC del build ya no los lista; `frozen_assets_verified` sigue dando 9/9. | Bajo |

---

## TANDA 4 — Seguridad

*Los 4 que el especialista de seguridad dejó abiertos. Ver `docs/handoffs/HANDOFF-SECURITY-2026-11-08.md` §7.*

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 4.2 | **Actions sin pinear por SHA** | `actions/checkout@v4` y `actions/setup-python@v5` son tags móviles: moverlos = código arbitrario en el runner. Pinear al SHA completo con el tag como comentario (`uses: actions/checkout@<sha> # v4.2.2`). | El workflow no tiene ningún `uses:` con tag. Actualizar los SHAs es un commit aparte, sin código. | Bajo |
| 4.3 | **Deps sin pinear** | `requirements.txt` / `requirements-dev.txt` con `>=` (incluido `pillow>=10.0`). Fijar versiones exactas (y si el proyecto lo quiere, `--require-hashes`). | `pip install` con las requirements fijas resuelve igual en el CI. | Medio |
| 4.6 | **`VH_WT` decide dónde escribe `regen_status.py`** | Un runner con esa variable reescribe el `CLAUDE.md` de **otro** árbol (el de otro agente). Hoy está documentado como override explícito; el cierre es que el destino se valide: que el `CLAUDE.md` a escribir pertenezca al árbol del repo. | Test con `VH_WT` apuntando a un árbol ajeno → el generador se niega. | Bajo |
| 4.8 | **La cache del lowpass confía en el nombre** | La clave no incluye la identidad del track original: una actualización del juego en la misma carpeta reutiliza un WAV filtrado **obsoleto**. Y el hit no valida el contenido. Fix: versionar la clave con un hash del track fuente, y validar el WAV cacheado (RIFF/tamaño). | Test: cambiar el track y comprobar que la cache no se reutiliza. | Medio |

---

## TANDA 5 — La lista canónica de los sets

*El ítem más grande del plan. Toca 10-12 archivos. Es lo que un set nuevo deja hoy fuera de 8 guardas y del `--check-pipeline`.*

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 5.5 / 5.1 / 5.5' | **La lista de los 8 sets está literal en 14 archivos**; sólo 3 copias están ancladas al disco | Una sola **expectativa** hardcodeada + todo lo demás derivado de `discover_sets()`. **El obstáculo real**: `src/` y `main.py` no pueden importar `tools/` (el build congelado no empaqueta `tools/`), y `--check-pipeline` tiene que correr **dentro** del `.exe`. Por eso el helper de discovery tiene que vivir en `src/anim/clip.py` (que ya resuelve la raíz de los sets para el bundle), con la expectativa en un archivo que `src` **y** `tools` puedan leer. | (a) un set nuevo queda cubierto por las guardas y por `--check-pipeline` sin tocar una lista; (b) el `.exe` sigue reportando los sets correctos; (c) `gate.py` deja de hardcodear la lista que importa. | Medio-alto |

**Los 14 archivos** (verificados): `main.py:261` · `tools/sprite_pipeline/gate.py:63` · `tools/regen_status.py:227` · `src/ui/gameplay_runtime.py:5316` · `src/entities/enemies/enemy.py:32` · `tests/test_enemy_art_is_untouched.py:25` · `tests/test_enemy_anchors_are_fresh.py:37` · `tests/test_enemy_hitbox_is_not_the_canvas.py:21` · `tests/test_enemy_manifest_matches_assets.py:25` · `tests/test_enemy_scale_matches_runtime.py:37` · `tests/test_enemy_set_discovery.py:40` · `tests/test_enemy_sets_audit_clean.py:33` · `tests/test_check_pipeline_command.py:35` · `tests/test_regen_status_bundle.py:26`.

**La forma mínima** (la que el especialista propuso): un helper cacheado `discover_enemy_sets()` (~12 líneas) en `src/anim/clip.py` + una sola expectativa en un archivo compartido + reemplazar los literales por la llamada. **Neto ≈ −55 líneas.** El veredicto del especialista: *"vale la pena, no vale bloquear la release"*.

---

## TANDA 6 — Código muerto (DECISIÓN TUYA antes de arrancar)

| # | Ítem | Qué hacer | Riesgo |
|---|---|---|---|
| 6.2 | **`DrawContext` expone 4 campos y 2 métodos que ningún consumidor de producción lee** (`origin`, `scale`, `time`, `size`, `with_origin()`, `at()`) | **Dos caminos, y son decisiones distintas**: (a) borrarlos (diff chico, ~20 líneas) — pero `src/render/` se aprobó como motor **genérico** y reusable, y estos campos son la superficie de esa genericidad; (b) dejarlos y documentarlos como la API del motor. **No arranca sin que decidas cuál.** | Rechazo |
| 6.3 | **`Part.on_missing` y `AnimSet.sided` no los lee nadie** — y `meta.sided` es un **duplicado** de `detect.side` (el mismo hecho declarado dos veces, capaz de contradecirse en silencio) | **Dos caminos**: (a) borrarlos (≈8 líneas + 2 claves del manifest de GOLIATH — el manifest es la *spec* del arte, así que tocarlo merece BLOQUE); (b) volverlos **load-bearing**: validar `meta.sided == detect.side` en el loader (convierte la contradicción en un error) y que el auditor **respete** `on_missing`. **La opción (b) es la que convierte una hipótesis en garantía.** | Medio |

---

## TANDA 7 — Las truth anchors del bloque STATUS

*El bloque es GENERADO: si no hay forma de comprobar que está al día, puede mentir con todo el绿色 del mundo.*

| # | Ítem | Qué hacer | Cómo se comprueba | Riesgo |
|---|---|---|---|---|
| 7.a | **La frescura del bloque STATUS no tiene check** | `regen_status.main()` no tiene un seam puro para comparar contra lo commiteado sin escribir en el repo (L7). Extraer el cálculo de filas a una función pura `rows_for(root)` y compararla en un test contra las filas commiteadas. | Agregar 10 archivos de test → el check se pone rojo. | Bajo |
| 7.6 | **La fila `Tests` depende de la máquina** | Sus 6 skips son `release/videos/ not found`, que sólo existen si el zip está descomprimido. O el conteo se normaliza (los skips se nombran), o la fila declara su condición. | La fila dice lo mismo con y sin el zip descomprimido. | Bajo |
| 7.7 | **El anchor de `Build .exe` no es ejecutable desde el árbol que lleva el bloque** | La columna "Fuente" dice `Get-Item dist/void-hunter-v1.9.0.exe` (raíz del repo), pero el bloque vive en el worktree. Que el anchor funcione desde donde vive el bloque, o que la fila diga cuál raíz usar. | El comando de la columna se ejecuta desde el árbol del bloque y resuelve. | Bajo |

---

## 2. Backlog no priorizado (encontrados, sin cerrar, sin bloqueante)

Cosas que los especialistas o la revisión dejaron anotadas y que **no** están en las 22, para que no se pierdan:

- `src/ui/gameplay_runtime.py` — el log `frame_times.csv` escribe en disco **en el hot path** (sólo cuando el frame pasó 50 ms). Preexistente; el diff sólo lo movió. Fix: buffer en memoria + vaciado por segundo.
- `src/core/scene_manager.py` — la fila `PAUSE` de `VALID_TRANSITIONS` es **inalcanzable** (PAUSE nunca es `current_state`). Hoy funciona por accidente. Dejarla como documentación o mover PAUSE al estado real.
- `main.py --boss` entra a `BOSS_FIGHT` **dos veces** (`on_enter` se llama en el walk y otra vez en `Game.run()`): reset de player/scoring y `_start_bgm` duplicados. Inocuo hoy (ocurre antes del primer tick), frágil.
- `src/anim/clip.py` — la cache del lowpass no valida el contenido del WAV cacheado (ver 4.8, es el mismo ítem).
- El job `gates` corre los gates **dos veces por CI** (una dentro del job `pytest`, otra en el job `gates`). Inocuo, pero wasteful.

---

## 3. Definición de terminado (para todo el plan)

```powershell
cd F:\AI\MM\void-hunter\.worktrees\<tu-worktree>
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=no -q
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
$env:PYTHONUTF8='1'
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py . --perfil=lite
```
Más, para cada ítem de la tanda: **su contraposición en rojo** (la mutación que lo rompe) y **R1 intacto** (0 PNGs modificados).

Y el cierre documental de cada tanda: `docs/handoffs/` (qué se hizo y qué NO), la fila del silo `CONTEXT.md`, y el `.synapse` (§2 del handoff de la revisión: el estado real, con números).

---

## 4. Lo que NO hay que hacer

- **No** force-push ni reescribir historia publicada (el tag `v1.9.0` y los 5 commits con prefijo `ci:` se quedan como están).
- **No** tocar un PNG de `Assets/` (R1).
- **No** meter el trabajo en la raíz ni en `master`: worktree propio, rama propia.
- **No** tocar el gate sin contraposición: es la única garantía de la fase.
- **No** meter una credencial en un archivo versionado, nunca (ver `docs/handoffs/HANDOFF-SECURITY-2026-11-08.md` §8).
