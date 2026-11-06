# HANDOFF — BLOQUE 75: la release v1.9.0

**Date:** 2026-11-04
**Branch:** `bloquec-67-goliath-port` (la línea de release; `master` no se toca)
**Status:** **publicado**. El tag `v1.9.0` y el release de GitHub existen:
`published_at` 2026-11-06T03:17:08Z, `draft: false`, asset
`VoidHunter-v1.9.0-win64.zip`, y `releases/latest` → `v1.9.0`.

---

## 1. Qué se publica

| | |
|---|---|
| Versión | **v1.9.0** |
| Binario | `F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe` |
| Tamaño | 230.900.897 bytes (220,2 MB) |
| SHA256 | `D8EDB1FD4EA332E8AB183165DECD3025AB209CD691B93AEA1C41BFBB49E9AE36` |
| Tag | `v1.9.0` — publicado, apunta al commit de la release `157af82` |
| Asset del release | `VoidHunter-v1.9.0-win64.zip` — publicado |

La release cierra tres cosas:

**La Fase 1 — los enemigos son datos.** Los ocho sets de enemigos pasaron al
mismo pipeline de manifests que GOLIATH: un `manifest.toml` por set (la spec,
editada a mano) y un `anchors.toml` (la medición, horneada). Nueve manifests
y nueve tablas de anclas en total.

**La Fase 2 — el frame es un stack de capas.** El motor vive en `src/render/`
(`Layer`, `LayerStack`, `DrawContext`) y es genérico: **cero imports del
juego**. El orden de dibujo del frame pasó de código a datos: 30 capas
nombradas, cada una con su `z` explícito (0..29), cada una llamando al código
que ya existía. Los cuerpos de los enemigos los dibuja el compositor del
pipeline, y el pivote `fixed` y la escala `(1.05, 1.05)` los **declara** el
manifesto, no el runtime.

**El cierre — la puerta corre sola.** `tools/sprite_pipeline/gate_ci.py`
decide qué gates aplican a la rama y los corre. El CI de la línea de release
tiene un job `gates` nuevo en `windows-latest` con 25 minutos de presupuesto:
los dos gates (Fase 1 `G1..G13` y Fase 2 `P2-G1..G6`) se verifican solos en
cada push. El bundle congelado se verifica contra los **nueve** sets, y el
juego puede reportar si su propio pipeline de enemigos está disponible
(`main.py --check-pipeline`, que corre igual en el source y en el `.exe`).

**Para quien juega, nada cambia.** Cero píxeles movidos, verificado con seis
frames de referencia (*goldens*) comparados byte a byte en dos checkpoints
(2A y 2B). El `.exe` pesa 220,2 MB (35 KB más que el de la v1.8.1: son los
nueve manifests que ahora viajan dentro) y el self-test sigue reportando
15 escenas, 18 olas y 4 bosses.

**Para quien desarrolla, el frame es un stack y los enemigos son datos.** Y el
bundle dejó de ser una caja negra: el `.exe` de la v1.8.1 llevaba **1 de 9**
manifests (el del boss); el de la v1.9.0 lleva los **9**. Desde la Fase 2 los
manifests de enemigos son *load-bearing*: sin ellos el build congelado cae al
camino viejo **sin ningún error** — el juego corre, los enemigos se ven, y
nada lo reporta. Eso ya no puede pasar en silencio.

---

## 2. Cómo se verifica

Desde el worktree de la línea de release:

```powershell
Set-Location F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port

# 1. La suite
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=no
#    esperado: 3123 passed, 6 skipped, 1 xfailed (3130 total, 0 fallos)

# 2. Los dos gates (los mismos que corre el CI)
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
#    esperado: "PHASE 1 GATE OK" y "PHASE 2 GATE OK", exit 0

# 3. El pipeline, en el source
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check-pipeline
#    esperado: los 8 sets con pivot=fixed scale=(1.05, 1.05),
#               "layers: 30  missing methods: none", "pipeline check OK"

# 4. El pipeline, en el BINARIO que se descarga
& F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe --check-pipeline
#    esperado: lo mismo, exit 0

# 5. El binario contra la suite
& F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe --check
#    esperado: "15 scenes, 18 waves, 4 bosses", exit 0
```

**El bundle lleva los nueve sets:**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port\tools'); from pathlib import Path; from regen_status import _bundle_entries, frozen_assets_verified; print(frozen_assets_verified(_bundle_entries(Path(r'F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe'))))"
#    esperado: True   (el mismo comando sobre void-hunter-v1.8.1.exe: False)
```

**El arte no se movió:**

```powershell
git diff --name-status 773cf08..HEAD -- '*.png'
#    esperado: seis filas "A", todas bajo tools/golden/layerstack/,
#              y NINGUNA fila M ni D. Los 1768 PNGs de Assets/ tienen el
#              mismo digest de árbol.
```

**El CI de la línea de release está verde.** Los dos runs que **cubren la
release** son:

| run | head SHA | qué cubre |
|---|---|---|
| `42155472049` | `157af82` | el commit de la release (`157af82` = el tag `v1.9.0`) |
| `42156102393` | `fd314d4` | la punta de la rama (`fd314d4`) |

Ambos `completed/success`, con los jobs `pytest` y `gates` en verde.

> Ojo con el run que este documento citaba antes: `42148928648` es verde,
> pero su `headSha` es `9565139`, **cuatro commits antes** del commit de la
> release. Servía para probar que el job `gates` funciona; no prueba esta
> release.

```powershell
gh run view 42155472049 --json status,conclusion,headSha
gh run view 42156102393 --json status,conclusion,headSha
gh run list --workflow test.yml --branch bloquec-67-goliath-port
```

---

## 3. Lo que NO se hizo

Esta parte no es opcional: es lo que evita que la próxima sesión repita el
trabajo o prometa lo que no está.

- **El motor de capas cubre una escena de quince.** Sólo `GameplayRuntime`
  usa el `LayerStack`; las otras catorce escenas siguen dibujando como
  siempre. El engine es genérico y reutilizable, pero **todavía no se
  reutilizó**.
- **El clip `death` de la mina nunca se reproduce.** El manifiesto de la mina
  declara cinco clips (`closed`, `open1`, `open2`, `open3`, `death`), pero el
  runtime elige el clip por `mine_state`, y `death` no está en esa lista. El
  pipeline reproduce el runtime con fidelidad; el arte sigue sin usarse. Quiere
  una decisión de diseño, no un fix.
- **`CARRIER` no tiene set.** No existe `Assets/sprites/enemies/carrier/`: ese
  enemigo sigue por el camino procedural, como antes. La llamada
  `load_player_for_kind("carrier")` por frame **no es un defecto de
  rendimiento**: `src/anim/manifest.py` cachea el fallo (`_LOADED_FAILED`), así
  que después del primer frame es una consulta a un `set`, no un re-parseo
  del manifiesto.
- **La rama legacy de `_get_enemy_sprite` —la del PNG de un frame— es código
  muerto.** Los `Assets/sprites/enemy_<kind>.png` ya no existen (0 archivos),
  así que esa rama nunca se toma.
  **Pero `_get_enemy_sprite` NO se puede borrar:** su *primera* rama —la que
  resuelve `e.animation_path` y dibuja el frame por frame del pipeline— está
  viva, y es **la red de seguridad que mantiene los píxeles idénticos cuando
  el pipeline falla**. La revisión final lo comprobó por mutación: con el
  pipeline devolviendo `None`, los seis goldens siguen en verde. Borrar esa
  rama rompería la paridad de píxeles en silencio.
- **La salida de build se mide, no se recuerda.** El techo es 1200 MB y la
  cifra vive en la fila `Salida de build (dist/)` del bloque
  `STATUS:GENERATED` de `CLAUDE.md`, que la produce
  `python tools/repo_budget.py`. Aquí no hay número escrito a mano porque
  cambiaría con cada build: un número fijo en un documento es un número que
  miente en la regeneración siguiente.
- **El `.exe` no se reconstruye por fase:** se reconstruye una vez, al cierre.
  Por eso el `dist/` acumula binarios viejos (v1.8.1 y v1.9.0 conviven).
- **La Fase 3 no arrancó.** No hay spec, ni plan, ni worktree para ella.
- **El `timeout-minutes` del job `gates` es 25, no 15.** El peor caso del
  gate de Fase 2 es 1380 s; con 15 minutos el job moría sin diagnóstico.

---

## 4. Las cinco garantías, y la mutación que las mata

Cada garantía de la Fase 2 se comprobó **volviéndola roja a propósito**. La
prueba de que un check funciona no es que pase: es que **se puede romper**.

| garantía | la mutación que la mata |
|---|---|
| los seis goldens son píxel-exactos | mover el origen del enemigo 1 px → **5 de 6** se ponen rojos |
| los enemigos pasan por el compositor | hacer que el draw del pipeline devuelva `None` → los **3 spies** se ponen rojos **mientras los 6 goldens siguen pasando** (son ciegos al camino) |
| el pivote `fixed` se respeta en el camino público | hacer que `draw_part` use la aritmética previa a la Task 5 → **sólo** el test del camino público se pone rojo |
| el flash dibuja el cuerpo cuando el pipeline no pudo | hacer inalcanzable el blit del cuerpo de fallback → **2** se ponen rojos |
| el camino caliente no hace trabajo de sistema de archivos por frame | reparsear el manifest por enemigo y por frame → **el guard** se pone rojo |

El detalle de cada una está en
`docs/handoffs/HANDOFF-BLOQUE-75-PHASE2-2026-11-04.md` §2.

---

## 5. Las reglas de proceso que produjo la fase

1. **Un brief se escribe una vez, antes del despacho, y se congela.** Las
   correcciones van a un archivo nuevo versionado (`task-N-brief-r1.md`) y al
   log de correcciones del plan. Reescribir un brief ya despachado falsifica
   el registro: un revisor que audite "desviación vs brief" desde los archivos
   en disco ya no puede verla.
2. **La implementación le gana al brief**, pero quien implementa **reporta** la
   desviación en vez de improvisar. Seis implementadores lo hicieron, y cada
   uno encontró un defecto real.
3. **Todo check nuevo tiene que poder fallar**, mutando el código y pegando
   la corrida en rojo. Una garantía que el check no puede ver es una hipótesis.
4. **Nunca dos implementadores commiteando en el mismo worktree** (la carrera
   del índice de git). Los reviews pueden ir en paralelo; los implementadores
   no.
5. **Un archivo generado se valida por frescura, no por "¿cambió?"**. El gate
   de la Fase 1 tuvo que dejar de diffear las anclas *generadas* de GOLIATH
   para poder probar que el arte no se tocó.
6. **Una prueba de igualdad de píxeles prueba los píxeles, no el camino.** Un
   runtime que nunca llama al compositor dibuja los mismos píxeles: por eso
   el checkpoint 2B necesitó una segunda prueba (un spy que cuenta las
   llamadas).
7. **Un truth anchor que no mide es una mentira.** La fila `Versión` del
   bloque `STATUS:GENERATED` apuntaba a `git log --oneline -1`, que no mide
   la versión; ahora apunta a la constante que la sostiene.

El log con cada defecto encontrado está en
`docs/superpowers/plans/2026-11-03-bloque-75-phase2-layers.md`, sección
"# Corrections log".

---

## 6. Dónde sigue el próximo agente

| | |
|---|---|
| El plan de esta ola | `docs/superpowers/plans/2026-11-04-bloque-75-cierre-de-entrega.md` |
| El spec de esta ola | `docs/superpowers/specs/2026-11-04-bloque-75-cierre-de-entrega-design.md` |
| El plan de la Fase 2 | `docs/superpowers/plans/2026-11-03-bloque-75-phase2-layers.md` |
| El handoff de la Fase 2 | `docs/handoffs/HANDOFF-BLOQUE-75-PHASE2-2026-11-04.md` |
| El log de correcciones | `docs/superpowers/plans/2026-11-03-bloque-75-phase2-layers.md` → "# Corrections log" |
| Este handoff | `docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` |

**Lo que se hizo (ya no está pendiente):**

1. **El zip** — `F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip`
   (229.436.399 bytes).
2. **El tag anotado `v1.9.0`** — sobre `157af82`, el commit de la release
   (`git rev-list -n 1 v1.9.0` → `157af82370a94c2b0a74ec8d82d194a871aafb01`).
3. **`gh release create v1.9.0 … --latest`** — publicado el
   2026-11-06T03:17:08Z, `draft: false`, `prerelease: false`, asset
   `VoidHunter-v1.9.0-win64.zip`. `releases/latest` → `v1.9.0`.
4. **`git push origin bloquec-67-goliath-port`** — el CI corrió sobre el
   commit de la release (`157af82`) y sobre la punta (`fd314d4`), los dos en
   verde.

**La limpieza — lo que realmente queda (el paso 5 decía dos cosas que ya no
existen):**

- El worktree de la Fase 2 **ya está desregistrado**: `git worktree list`
  muestra sólo la raíz y `bloquec-67-goliath-port`. No hay nada que quitar
  con `git worktree remove`, y la rama `bloquec-75-phase2-layers` **ya no
  existe** — `git branch -d bloquec-75-phase2-layers` fallaría.
- Lo que queda es un directorio **sin build output**:
  `F:\AI\MM\void-hunter\.worktrees\bloquec-67-phase2-layers` (0 MB de
  `dist/`; sólo conserva
  `.superpowers/sdd/2026-11-04-bloque-75-cierre-de-entrega/ledger-addendum.md`,
  2.384 bytes). Se puede borrar con `rm -r` cuando nadie más lo use.
- La rama local que **sí** queda es `bloquec-75-sprite-migration`, más las
  remotas `origin/bloquec-75-ci-gates`, `origin/bloquec-75-migration-spec` y
  `origin/bloquec-75-sprite-migration`: son ramas viejas, ya mergeadas, y se
  pueden borrar con `git branch -d` / `git push origin --delete`.
- Los dos `.exe` duplicados del `dist/` **de este worktree**
  (`void-hunter.exe`, byte a byte igual al `void-hunter-v1.9.0.exe` de la
  raíz, y `void-hunter-v1.8.1.exe`, igual al de la raíz) **ya se borraron**:
  la salida de build bajó de 1160,5 MB a 720,1 MB. **En la raíz no se tocó
  nada**: conserva `void-hunter-v1.8.1.exe`, `void-hunter-v1.9.0.exe` y
  `VoidHunter-v1.9.0-win64.zip`.

**Lo que sigue de verdad:**

1. **La Fase 3**, que no arrancó: sin spec, sin plan, sin worktree.
2. **Los trece follow-ups** de la revisión final — están en la sección 7 de
   este handoff, para que la próxima sesión los herede en vez de
   redescubrirlos.

Las notas del release ya están escritas y commiteadas:
`release-notes-v1.9.0.md` (en la raíz del repo).

---

## 7. Los trece follow-ups de la revisión final

La revisión final del rango `e619527..fd314d4` devolvió **MERGE WITH FIXES**:
el código que se publicó es sólido, y lo que pedía eran la verdad de los
documentos, aire en el disco y tres correcciones de una línea — todo eso ya
está hecho. Pero dejó **trece hallazgos diferidos como tareas de seguimiento**,
no como bloqueantes. Están acá para que la próxima sesión los herede en vez de
redescubrirlos:

1. **`gate_ci.main` — la función que el CI realmente llama — no tiene test**, y
   `main(argv)` ignora su argumento. El `applicable()` sí está cubierto.
2. **La regla de destino de `datas` del test de contrato del build-spec** es
   más estricta de lo necesario: rechazaría una entrada legítima
   `("Assets", "Assets")`.
3. **Los tres tests de mutación de ese archivo** asertan sobre el predicado
   compartido en vez de invocar la función de test principal.
4. **`_ensure_frame_display()` no tiene guarda de excepción**: un fallo ahí
   produce un traceback en vez de un FAIL limpio.
5. **Los ocho tipos de enemigo están hardcodeados en cinco lugares** y
   derivan de `EnemyKind` (10 miembros). Se quiere una lista canónica.
6. **La fila `Tests` del STATUS depende de la máquina**: sus 6 skips son
   `release/videos/ not found`, que sólo existen si el zip está descomprimido.
7. **El ancla de la fila `Build .exe` no es ejecutable desde el árbol que
   lleva el bloque**: resuelve sólo en la raíz del repo
   (`dist/void-hunter-v1.9.0.exe`).
8. **Los fixtures golden se pueden regenerar en silencio**: el harness avisa
   pero lo permite, y el gate seguiría en verde contra una prueba nueva.
   Fijar el SHA256 de los seis goldens convertiría una regeneración en un
   diff visible y deliberado.
9. **En `master` el job `gates` es un no-op verde** (ninguna de las dos bases
   es ancestro de `master`, así que ambas fases hacen SKIP con exit 0). Un
   flag `--require-applies` en el paso de la rama de release lo endurecería
   contra un squash o un rebase.
10. **Ramas remotas viejas**: `origin/bloquec-75-ci-gates`,
    `origin/bloquec-75-migration-spec`, `origin/bloquec-75-sprite-migration`, y
    la local `bloquec-75-sprite-migration`.
11. **`gh` registró `target_commitish: "master"`** en el release, aunque el tag
    apunta al commit de la release (`157af82`).
12. **El prefijo de commit `ci:` está fuera de la lista global del plan**
    (`feat:/fix:/docs:/test:/build:`); el plan sanciona `merge:`, que es lo que
    usan los dos commits de merge.
13. **`src/ui/gameplay_runtime.py:1698` conserva una ruta de fallback
    hardcodeada** `D:/AI/void-hunter/logs/_sub_boss.log`, de la era v1.4.0.
    Es preexistente, pero va a morder al primer agente que corra el juego
    desde otra unidad.
