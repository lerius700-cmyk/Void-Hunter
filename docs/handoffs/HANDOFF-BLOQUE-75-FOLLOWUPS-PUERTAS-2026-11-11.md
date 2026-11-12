# HANDOFF — BLOQUE 75 (follow-ups): las puertas que no medían (2026-11-11)

**Rama:** `bloquec-76-contenido` (worktree `.worktrees/bloquec-76-contenido`) · **Base:** `origin/bloquec-67-goliath-port` @ `a0c6f6f` (v1.9.0) · **Plan:** `docs/superpowers/plans/2026-11-08-bloque-75-followups.md` (las 22, en 7 tandas) · **Perfil:** Lite · **Schema:** `.synapse` 2.2.0

> **Commiteado, local.** El BLOQUE 76 está en `e295b8c` y esta tanda en el commit
> que la acompaña. **Nada está pusheado**: la rama `bloquec-76-contenido` es local,
> así que el otro agente del repo todavía no ve este trabajo. El push/merge lo
> autoriza el usuario.

Este handoff cubre la tanda de follow-ups del BLOQUE 75: **las puertas que no
medían**. Son 9 ítems de las 3 tandas mecánicas (2, 3 y 7) más dos extras de la
tanda 1 y 4. Todos tienen contraposición ejecutada.

---

## 1. Lo que se cerr�� (9 ítems)

| # | Ítem | Qué cambió | Contraposición |
|---|---|---|---|
| **2.1** | `gate_ci.main(argv)` ignoraba `argv` | `main` ahora **usa** sus argumentos (`--phase`, `--base`) y tiene seam (`repo`, `runner`) | La mutación "vuelve a ignorar `argv`" → **3 tests en rojo** |
| **2.4** | `_ensure_frame_display()` sin guarda | Devuelve el **motivo** del fallo en vez de morir con un traceback; `_pipeline_report` lo convierte en exit 1 con mensaje | Sin la guarda → `pygame.error: no video mode available` (el traceback exacto) |
| **3.2** | La regla de `datas` era más estricta de lo necesario | `("Assets", "Assets")` es una entrada **legítima**: la regla ahora es "el set tiene que LANDAR donde el runtime lo lee" | La regla estricta → el test simétrico en rojo |
| **3.3** | Los 3 tests de mutación asertaban sobre el predicado compartido | Ahora **invocan la función principal** (`_assert_the_bundle_carries_every_set`) | El check principal roto → los 3 en rojo ("DID NOT RAISE") |
| **3.6** | El bundle llevaba archivos que nadie lee | El árbol de sprites se toma **por subárbol**, y el **staging area** (`redesign/`, 465 archivos, **7,3 MB**) no viaja | El staging de vuelta en el spec → rojo; un subárbol sin declarar → rojo |
| **7.a** | La frescura del bloque STATUS no tenía check | `rows_for(root)` **puro** + `tests/test_status_block_is_fresh.py` (4 tests) | El bloque viejo → el test lo dice con el número |
| **7.6** | La fila `Tests` dependía de la máquina | Los skips se **nombran** ("6 skipped (release/videos/ not found)") | — |
| **7.7** | El anchor de `Build .exe` no corría desde el worktree | El anchor **pregunta al generador** dónde está el binario (como la fila `Versión`) | — |
| **1.13** | Ruta absoluta `D:/AI/void-hunter/logs/...` en el runtime | Se resuelve desde `Path(__file__)`; **el runtime no tiene ninguna ruta absoluta** | La ruta de vuelta → 2 tests en rojo |
| **4.6** | `VH_WT` podía hacer escribir en un árbol ajeno | El generador **se niega** si el destino no es un árbol de este repo | — |

---

## 2. Lo más importante: 3.6 encontró algo 80 veces más grande

El plan pedía excluir **90 KB**: una hoja de contactos de GOLIATH y un backup del
arte viejo de la mina. Al medir el árbol de sprites, lo que salió fue esto:

```
redesign          465 archivos   7.339,1 KB   <- STAGING: salidas de AI, sólo tools/
player_rotation     8 archivos   4.849,9 KB   <- SÍ se usa en runtime (scenes.py)
bosses             63 archivos     939,4 KB
enemies           322 archivos     383,6 KB
player_ships      234 archivos   4.390,5 KB
```

`Assets/sprites/redesign/` es el **staging area** del pipeline de sprites: las
salidas de AI que `tools/redesign_*/` post-procesan en el arte vivo. **Nada en
`src/` lo abre** — el juego lee los frames YA post-procesados. Eran **7,3 MB en
cada descarga del `.exe`: el 3,3%**.

Eso se excluyó (por subárbol, con la exclusión DECLARADA). Los 90 KB del plan
**no** se excluyeron, y el motivo está escrito:

- Excluirlos exige partir `bosses/goliath/` y `enemies/mine_asteroid/` en sus
  hijos, lo que abre un agujero real: **un clip nuevo del jefe no viajaría** y
  nada lo detectaría (la puerta sólo mira manifests y anchors).
- 90 KB es el **0,04%** de una descarga de 220 MB. Un agujero en el bundle del
  jefe a cambio de eso no es un trato.
- La primera opción del plan ("moverlos a una carpeta dev-only") **toca el árbol
  del arte** y la puerta del propio proyecto lo dice: el gate de Fase 1 y el de
  Fase 2 se pusieron **rojos** con `G11`/`P2-G5` (7 PNGs movidos). R1 manda.

> **Lo que queda abierto de 3.6:** los 90 KB, con el motivo escrito arriba. Lo
> que se ganó: **7,4 MB** (3,4% de la descarga).

### El agujero que abre "tomar el árbol por subárbol", y cómo se cierra

Tomar el árbol por subárbol es lo que hace posible excluir el staging — y abre
un agujero: un subárbol que alguien agregue y olvide no viajaría, y el `.exe`
perdería arte **en silencio**.

Se cierra con `test_every_sprite_file_is_carried_by_some_entry`: **cada archivo**
del árbol de sprites tiene que estar cubierto por alguna entrada, exactamente
donde está. Un subárbol nuevo sin declarar → **rojo**.

Y `test_the_staging_area_is_not_carried` + `test_the_spec_really_takes_the_sprites_tree_by_subtree`
impiden que la exclusión se deshaga sola.

---

## 3. Las contraposiciones (ejecutadas, con la salida real)

**2.1** — `main` vuelve a ignorar `argv`:
```
FAILED test_main_uses_its_arguments
FAILED test_main_propagates_the_failure_of_a_gate_that_fails
FAILED test_main_runs_every_phase_when_none_is_named
3 failed, 8 passed
```

**2.4** — se saca la guarda de `pygame.error`:
```
E   pygame.error: no video mode available
FAILED test_the_command_fails_cleanly_when_the_display_cannot_be_created
```

**3.2 + 3.3** — la regla estricta de `datas` y el check principal roto:
```
FAILED test_a_symmetric_datas_entry_carries_the_sets
FAILED test_the_check_notices_a_spec_that_drops_the_enemies_tree
FAILED test_the_check_notices_a_spec_that_drops_every_set
FAILED test_the_check_notices_a_spec_that_drops_the_boss
4 failed, 5 passed
```

**3.6** — el staging vuelve al bundle, y un subárbol sin declarar:
```
E   AssertionError: the spec carries the staging area again: Assets/sprites/redesign
E   AssertionError: these files of the sprites tree do not travel inside the .exe:
    ['Assets/sprites/zz_probe/notes.txt'] -- the .exe would lose that art in silence
2 failed, 10 passed
```

**1.13** — la ruta absoluta vuelve al runtime:
```
E   AssertionError: the runtime names absolute paths of another machine:
    [('src/ui/gameplay_runtime.py', 'D:/AI/void-hunter/logs/_sub_boss.log')]
2 failed
```

---

## 4. 7.a, 7.6 y 7.7 — el bloque STATUS

**7.a.** `regen_status.main()` computaba las filas Y escribía el bloque: no había
forma de preguntar *"¿qué diría el generador hoy?"* sin escribir en el repo, y
L7 prohíbe que un test escriba ahí. Ahora las filas se calculan en
`rows_for(root)`, que es **puro** (lee y calcula; nunca escribe), y
`tests/test_status_block_is_fresh.py` compara el bloque commiteado contra eso.

**Qué NO se compara, y por qué** (es parte del check, no una acá):

| Fila | Por qué no |
|---|---|
| los 3 PESOS (árbol, build, historia) | miden el repo, y **el commit que lleva el bloque los cambia**: un bloque regenerado antes del commit está viejo por definición |
| `Tests (tests/)` | necesita la SUITE, y un test que corre la suite corre la suite dentro de la suite → se compara contra el **conteo por COLECCIÓN**, que es rápido y no ejecuta nada |
| `Build .exe` | necesita el ARTEFACTO (es un output de build, gitignored) → se compara cuando esta máquina lo tiene |

Lo que sí se compara: los LOC, el conteo de archivos, los silos, la versión y la
rama — que es donde un bloque viejo se ve: alguien agrega código y nadie
regenera.

**7.6.** Los 6 skips de la suite son los tests de export de video, que se saltean
cuando `release/videos/` no está descomprimido. El número **era el número de la
máquina** y el lector no podía distinguir un test salteado a propósito de uno que
dejó de correr. Ahora la fila los **nombra**: `+ 6 skipped (release/videos/ not found)`.

**7.7.** El anchor decía `Get-Item dist/void-hunter-v1.9.0.exe` (raiz del repo) —
pero el bloque vive en un **worktree**, donde ese `dist/` no existe. El
paréntesis decía WHICH raíz, pero el comando **no corría**. Ahora el anchor
pregunta al generador dónde está el binario (como hace la fila `Versión`), y
resuelve desde donde esté el bloque. Un test lo **ejecuta** desde el árbol del
bloque y comprueba que imprime el binario canónico.

---

## 5. Lo que NO se hizo (y por qué)

- **2.9** (el job `gates` es un no-op verde en `master`) y **1.10** (borrar las
  ramas viejas) y **1.11** (`target_commitish` del release) son cambios **a
  nivel de repo**: tocan la protección de ramas y las ramas remotas, en un repo
  compartido con otro agente. **Piden tu OK.**
- **1.12** (el prefijo `ci:`) es una decisión tuya, sin impacto funcional.
- **4.2** (pinear las actions por SHA) y **4.3** (fijar las deps) son de una
  línea cada uno, pero 4.3 cambia lo que instala el CI: eso es una decisión.
- **4.8** (la cache del lowpass confía en el nombre) es el ítem con más trabajo
  de los que quedan: hay que versionar la clave con el hash del track y
  validar el WAV cacheado.
- **3.6**: los 90 KB del plan (ver §2).
- **Tanda 6** (código muerto: `DrawContext`, `Part.on_missing`, `AnimSet.sided`)
  necesita tu decisión antes de arrancar, como siempre.

### Un hallazgo extra, fuera de los 22

`tools/` tiene **25 scripts** con rutas absolutas de `D:\AI\void-hunter\` — la
máquina de otro BLOQUE. En esta máquina (`F:\AI\MM\void-hunter`) **no funcionan**.
No son del runtime (no viajan en el `.exe`) y son scripts de BLOQUEs viejos, así
que el test nuevo (`test_runtime_has_no_absolute_paths.py`) los excluye a
propósito: un check que nombra 25 archivos que nadie va a arreglar no es un
check. **Queda anotado para cuando quieras barrerlos.**

---

## 6. Los números (verificados, no declarados)

| Métrica | Antes | Ahora |
|---|---|---|
| Tests | 3.186 | **3.205** (19 nuevos) |
| Fallos | 0 | **0** |
| Gate | `PHASE 1/2 GATE OK` | **idem** |
| `--check-pipeline` | 8 sets, `layers: 30`, exit 0 | **idem** |
| `audit_sf_sm --perfil=lite` | 7/7 | **7/7** |
| PNGs modificados | 0 | **0** (R1 intacto: el árbol del arte no se tocó) |
| El `.exe` | 220,2 MB | **220,2 MB todavía**: no se reconstruyó (§P4 q3). El **próximo** build no llevará los 7,3 MB del staging area → ~212,9 MB (a confirmar cuando se reconstruya) |

---

## 7. Cómo verificar

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-76-contenido
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'

& $py -m pytest tests\ --tb=no                      # 0 fallos
& $py tools\sprite_pipeline\gate_ci.py              # PHASE 1 GATE OK / PHASE 2 GATE OK
& $py main.py --check-pipeline                      # 8 sets + layers: 30, exit 0
$env:PYTHONUTF8='1'
& $py C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py . --perfil=lite   # 7/7
git diff --stat a0c6f6f -- '*.png'                  # vacío (R1)
```

Los archivos nuevos de esta tanda:
`tests/test_status_block_is_fresh.py` ·
`tests/test_runtime_has_no_absolute_paths.py` ·
`tests/test_regen_status_target_is_validated.py`.
