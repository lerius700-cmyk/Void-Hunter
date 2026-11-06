# HANDOFF — BLOQUE 75: la release v1.9.0

**Date:** 2026-11-04
**Branch:** `bloquec-67-goliath-port` (la línea de release; `master` no se toca)
**Status:** el binario está construido y verificado; el tag y el release de
GitHub los publica la tarea siguiente de la ola.

---

## 1. Qué se publica

| | |
|---|---|
| Versión | **v1.9.0** |
| Binario | `F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe` |
| Tamaño | 230.900.897 bytes (220,2 MB) |
| SHA256 | `D8EDB1FD4EA332E8AB183165DECD3025AB209CD691B93AEA1C41BFBB49E9AE36` |
| Tag | `v1.9.0` — lo crea la tarea siguiente |
| Asset del release | `VoidHunter-v1.9.0-win64.zip` — lo crea la tarea siguiente |

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

**El CI de la línea de release está verde:** run `42148928648`
(`completed/success`), jobs `pytest` y `gates`.

```powershell
gh run view 42148928648 --json status,conclusion,headBranch
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
  enemigo sigue por el camino procedural, como antes, pero ahora paga una
  llamada `load_player_for_kind("carrier")` por frame que no encuentra nada.
- **La rama legacy de `_get_enemy_sprite` es código muerto.** Los
  `Assets/sprites/enemy_<kind>.png` ya no existen (0 archivos), así que la
  rama que los busca nunca se toma.
- **La salida de build está en 941,7 MB contra un techo de 1200 MB.** No es
  un problema todavía, pero el margen se come en el `dist/` de cada worktree.
  Lo que lo baja es **borrar el worktree de la Fase 2**
  (`git worktree remove .worktrees/bloquec-75-phase2-layers`), que es el paso
  de limpieza de la tarea siguiente.
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

**Lo siguiente, en orden:**

1. El zip: `Compress-Archive -Path F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe -DestinationPath F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip -Force`.
2. El tag anotado `v1.9.0` sobre el commit de la documentación.
3. `gh release create v1.9.0 F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip --latest --title "VOID HUNTER v1.9.0 (BLOQUE 75) - el pipeline de sprites y el motor de capas del frame" --notes-file release-notes-v1.9.0.md`.
4. `git push origin bloquec-67-goliath-port`.
5. La limpieza: `git worktree remove F:\AI\MM\void-hunter\.worktrees\bloquec-75-phase2-layers`, `git worktree prune`, `git branch -d bloquec-75-phase2-layers` — y con eso la salida de build baja de los 941,7 MB.

Las notas del release ya están escritas y commiteadas:
`release-notes-v1.9.0.md` (en la raíz del repo).
