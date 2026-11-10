# BLOQUE 76 — Contenido de primera clase: la lista canónica de los sets y las fotos con huella

> **Estado:** spec para revisar y ejecutar. No hay código todavía.
> **Base:** `bloquec-67-goliath-port` (la línea de release, v1.9.0). **`master` NO es la base** (está en v1.6.3 y no recibe merges).
> **Origen:** follow-ups #5 y #1 de `docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` §7 + #1 y #8 de `docs/handoffs/HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` §6.
> **Por qué este BLOQUE:** es el que desbloquea la primera tarea del roadmap ("More enemy variety: BOMBER, MINELAYER") y hace que cambiar el arte a propósito sea un cambio **visible**.

---

## 0. Antes de empezar: qué leés primero y dónde trabajás

El contexto vive en el repo, no en este documento. En este orden:

| # | Archivo | Qué te da |
|---|---|---|
| 1 | `CLAUDE.md` | La identidad del proyecto, las reglas que no se rompen, y **"Trabajo multi-agente"** (un worktree y una rama por agente). |
| 2 | `CONTEXT.md` | El switch: qué silos existen y a cuál pertenece este trabajo (`docs/superpowers/`). |
| 3 | `docs/superpowers/CONTEXT.md` | La misión del silo y dónde viven los prompts, specs y planes. |
| 4 | `.synapse` | El puntero: `active_context_pointers` dice qué leer primero. |
| 5 | `docs/superpowers/plans/2026-11-08-bloque-75-followups.md` | **El plan de los 22 follow-ups.** Este spec es la detalle de las tandas 2 (parcial) y 5. |

**Dónde trabajás.** Creá tu propio worktree desde la línea de release:

```powershell
cd F:\AI\MM\void-hunter
git fetch origin bloquec-67-goliath-port
git worktree add .worktrees\bloquec-76-canonical-sets -b bloquec-76-canonical-sets origin/bloquec-67-goliath-port
cd .worktrees\bloquec-76-canonical-sets
```

**No trabajés sobre `master` ni sobre `bloquec-67-goliath-port` directamente, y no tocás los worktrees de los demás agentes** (hay al menos otro agente sobre este repo).

> **No comitees nada hasta que el usuario lo pida.** Es una regla explícita del proyecto (BLOQUE 58.14). Cuando pidás permiso, comiteá con prefijo `feat:`/`fix:`/`test:` y **paths explícitos** (nunca `-A`).

**Antes de tocar nada, verificá que el repo está sano** (este es el guard de contrato, y mide sobre el código real, no sobre un plan):

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=no -q
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
```

Esperado: `3172 tests / 0 fallos` y `PHASE 1 GATE OK` + `PHASE 2 GATE OK` (exit 0).

---

## 1. El problema que resuelve

### 1.1 La lista de los 8 sets de enemigos está escrita en 14 archivos

Hoy el mismo grupo de nombres —`scout`, `cruiser`, `drone`, `heavy`, `kamikaze`, `sniper`, `turret`, `mine_asteroid`— está **escrito a mano** en catorce lugares del repo. Cada consumidor lo copia:

| Consumidor | Para qué lo usa | Qué pasa con un set nuevo |
|---|---|---|
| `tools/sprite_pipeline/gate.py:62` | El gate recorre los 8 y audita cada uno | **No lo cubre**: el gate no lo ve |
| `main.py:260` | `--check-pipeline` reporta los 8 | **No lo cubre**: el binario no lo reporta |
| `src/ui/gameplay_runtime.py:5303` | Decide si a un enemigo le toca sprite | **No lo dibuja**: cae al procedural |
| `tools/regen_status.py:227` | `BUNDLED_SETS`: los 9 sets del bundle | **No lo verifica**: el bundle puede no traerlo |
| 9 archivos de test | Parametrizan sobre los 8 | **No lo cubren**: los tests no lo ven |

El resultado concreto: **agregás un enemigo nuevo (BOMBER) con su arte, su manifest y sus anchors, y todo queda verde — pero el enemigo no se dibuja, el gate no lo audita, `--check-pipeline` no lo reporta y el bundle no lo exige.** El set es un pasajero: está en disco y nadie lo mira.

Lo que hoy **sí** ata la lista al disco son sólo **3 de los 14**:
`tests/test_enemy_art_is_untouched.py:96` (`assert found == set(ENEMY_SETS)`), `tools/sprite_pipeline/gate.py:571-573` y `tests/test_enemy_set_discovery.py`. Los otros 11 pueden quedar viejos en silencio.

### 1.2 Las 6 fotos de referencia del frame se pueden regenerar en silencio

`tools/golden/layerstack/` tiene las 6 fotos que `tests/test_layer_stack_renders_identical_frames.py` compara **byte a byte** con el frame actual. Son la red que garantiza "0 píxeles movidos".

El problema: el harness (`tools/capture/layerstack_frames.py`) **avisa** al regenerarlas pero **lo permite**, y nada registra **qué** cambió. Una regeneración que cambia 300 píxeles deja el mismo diff que una que cambia 0: el resultado es indistinguible. Para **producir** (agregar una capa, cambiar un efecto) eso es un problema, porque el commit que cambia el arte a propósito y el commit que lo cambian por accidente se ven igual.

La salida de esto es una decisión de diseño: **la foto tiene que tener huella.**

---

## 2. El vocablo (dos palabras, no más)

- **La EXPECTATIVA**: la lista hardcodeada de los sets que el repo **debe** tener. Es una verdad del proyecto, escrita **una sola vez**.
- **El DESCUBRIMIENTO**: lo que **hay** en disco, leído del directorio.

Cada consumidor usa el que corresponde a su pregunta:
- "¿Qué **debe** haber?" → la **expectativa** (el gate, `--check-pipeline`, el verificador del bundle).
- "¿Qué **hay**?" → el **descubrimiento** (el runtime, que dibuja lo que existe).
- Y **la puerta que las une**: el gate exige `descubrimiento == expectativa`. Si agregás un set, el gate te pide que lo declares; si quitás uno sin querer, el gate se pone rojo.

**La regla de la casa que gobierna este BLOQUE:** *una garantía que el check no puede ver no es una garantía, es una hipótesis.* Hoy las 14 copias son hipótesis con 3 puntos de anclaje. Este BLOQUE las convierte en **una** expectativa con **una** puerta.

---

## 3. Las decisiones (ya tomadas — no las re-discutás)

| # | Decisión | Por qué |
|---|---|---|
| D1 | La lista canónica vive en **`src/anim/`**, no en `tools/` | `src/` y `main.py` **no pueden** importar `tools/`: el build congelado no empaqueta `tools/`, y `--check-pipeline` tiene que correr **dentro** del `.exe`. `src/anim/` sí está en el bundle. |
| D2 | La expectativa es **una lista hardcodeada**, no derivada | Si fuera derivada del disco, sería tautológica: el gate no tendría contra qué comparar. Derivarla es lo que hoy hace la lista "en todas partes". |
| D3 | El descubrimiento se **cachea** | El runtime lo consulta en el hot path. `_enemies_root()` ya está memoizado con `functools.lru_cache(maxsize=1)`; el descubrimiento se memoiza igual. |
| D4 | El runtime **pregunta por el descubrimiento**, el gate **pregunta por las dos** | El runtime dibuja lo que hay (degradación correcta si falta un set en el bundle); el gate exige que lo que hay sea lo que debe haber. |
| D5 | `EnemyKind` **no se toca** | `EnemyKind` (10 miembros) es la lista de **tipos de enemigo**, no de sets: `CARRIER` y `SUB_BOSS` **no tienen** set por diseño. Derivar la lista de sets de `EnemyKind` estaría mal: los tipos no son los sets. |
| D6 | La huella de las fotos va en un **archivo versionado** | Un archivo de hashes commiteado convierte "regeneré la foto" en un **diff visible y deliberado**. Un hash calculado en runtime no deja rastro. |
| D7 | Este BLOQUE **no toca** el motor por capas | El motor (`src/render/`, 67 líneas) no participa de esto. La decisión de alcance del motor (que crece vs. que se consolida) es **otra** decisión, del owner, y vive en el checklist de BLOQUE 75 §P4. |

---

## 4. El diseño

### 4.1 `src/anim/sets.py` — el módulo nuevo (≈60 líneas)

Contiene **las dos** verdades y **nada** más:

```python
"""BLOQUE 76: la lista canónica de los sets de enemigos.

DOS verdades, y que no se mezclen:

  * ENEMY_SETS -- la EXPECTATIVA: los sets que el repo DEBE tener.
    Es un dato del proyecto, escrito a mano, en UN solo lugar. No se
    deriva del disco: si se derivara, el gate no tendria contra que
    comparar y la garantia seria vacua.

  * discover_enemy_sets() -- el DESCUBRIMIENTO: los sets que HAY.
    Se lee del directorio. Es lo que el runtime consulta para decidir si
    un enemigo tiene sprite.

La puerta que las une vive en tools/sprite_pipeline/gate.py: exige que
las dos coincidan.

Este modulo vive en src/ (y no en tools/) por una razon dura: el build
congelado no empaqueta tools/, y main.py --check-pipeline tiene que
correr DENTRO del .exe.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

# La EXPECTATIVA. Los ocho sets de enemigos que el repo debe tener.
ENEMY_SETS: tuple[str, ...] = (
    "scout",
    "cruiser",
    "drone",
    "heavy",
    "kamikaze",
    "sniper",
    "turret",
    "mine_asteroid",
)


def _is_set(path: Path) -> bool:
    """UNA definicion de "es un set": nombre sin "_" y manifest.toml."""
    if path.name.startswith("_"):
        return False
    return (path / "manifest.toml").is_file()


@functools.lru_cache(maxsize=1)
def enemies_root() -> Path:
    """Donde viven los sets de enemigos.

    La MISMA sonda que usa src/anim/manifest.py::_sets_root, para el
    otro root:

        desde el codigo:  <project root>/Assets/sprites/enemies
        congelado:       <_MEIPASS>/Assets/sprites/enemies

    Se resuelve en la LLAMADA, nunca en el import: un build congelado
    nunca necesita el arbol de fuentes. Y queda memoizado: la sonda
    costs ~72-90 us en Windows y se resolvia una vez por ENEMIGO, por
    FRAME (BLOQUE 75, fix round 1).
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "Assets" / "sprites" / "enemies"
    return (
        Path(__file__).resolve().parent.parent.parent
        / "Assets" / "sprites" / "enemies"
    )


@functools.lru_cache(maxsize=1)
def discover_enemy_sets() -> tuple[str, ...]:
    """Los sets que HAY en disco, ordenados por nombre.

    El scan es de UN nivel: los hijos de la raiz. Los manifests NO se
    parsean aqui: el descubrimiento no debe lanzar ante uno roto -- el
    loader degrada a None.
    """
    root = enemies_root()
    if not root.is_dir():
        return ()
    try:
        children = sorted(root.iterdir())
    except OSError:
        return ()
    return tuple(
        child.name for child in children if child.is_dir() and _is_set(child)
    )


def enemy_sets_mismatch() -> dict[str, list[str]]:
    """{faltan_en_disco, sobran_en_disco}: donde la expectativa y el
    descubrimiento no coinciden. Vacio = todo bien.

    El gate lo imprime y falla con esto. Un set nuevo en disco sin
    declararse aparece en "sobran_en_disco"; un set declarado que no
    esta aparece en "faltan_en_disco".
    """
    on_disk = set(discover_enemy_sets())
    expected = set(ENEMY_SETS)
    return {
        "faltan_en_disco": sorted(expected - on_disk),
        "sobran_en_disco": sorted(on_disk - expected),
    }
```

**Lo que se muda desde `tools/sprite_pipeline/sets.py`:** `_is_set()` (una sola definición de "es un set") y la sonda de raíz. **`tools/sprite_pipeline/sets.py` pasa a re-exportar** `_is_set` desde `src.anim.sets` y conserva su API (`sets_roots()`, `resolve_set()`, `discover_sets(root)`) para no romper los 6 tests que la usan.

**Lo que se muda desde `src/anim/clip.py`:** `_enemies_root()` pasa a ser `src/anim/sets.py::enemies_root()`. En `clip.py` queda un alias (`_enemies_root = enemies_root`) o se actualizan los call sites — **lo que sea menos ruido**, pero **una sola** definición de la sonda.

### 4.2 Quién usa qué (la tabla que hay que respetar)

| Consumidor | Qué usa | Por qué |
|---|---|---|
| `tools/sprite_pipeline/gate.py` | **La expectativa** para auditar, **y** `enemy_sets_mismatch()` para la puerta | Auditar lo que debe haber + fallar si el disco no coincide |
| `main.py::_pipeline_report` | **La expectativa** | Es un check: verifica que el bundle traiga lo que debe traer |
| `tools/regen_status.py::BUNDLED_SETS` | **La expectativa** (+ GOLIATH) | Es un check del bundle |
| `src/ui/gameplay_runtime.py` (el allowlist de la línea 5303) | **El descubrimiento** | El runtime dibuja lo que hay; si un set falta en el bundle, ese enemigo cae al procedural (degradación correcta) |
| Los 9 archivos de test que parametrizan sobre los 8 | **El descubrimiento** (o la expectativa, según lo que estén probando) | Un test que recorre el disco cubre un set nuevo sin editarlo |
| `src/entities/enemies/enemy.py` (`EnemyKind`) | **No se toca** | Es otra verdad (D5) |

### 4.3 La puerta: `gate.py` exige que las dos coincidan

En `_run_phase_1`, **antes** de auditar:

```python
    # BLOQUE 76: la expectativa y el descubrimiento tienen que coincidir.
    # Sin esta puerta, un set nuevo puede estar en disco, no ser dibujado
    # y no ser auditado, con el gate en verde.
    mismatch = enemy_sets_mismatch()
    if mismatch["faltan_en_disco"]:
        failures.append(
            "G0: hay sets declarados que no estan en disco: "
            + ", ".join(mismatch["faltan_en_disco"])
        )
    if mismatch["sobran_en_disco"]:
        failures.append(
            "G0: hay sets en disco que no estan declarados en ENEMY_SETS "
            "(src/anim/sets.py): " + ", ".join(mismatch["sobran_en_disco"])
        )
```

Y el gate **audita el descubrimiento**, no la expectativa: si hay un set en disco, se audita (aunque no esté declarado — aunque en ese caso el gate ya falló por G0).

### 4.4 La relación con `EnemyKind` — el test que la ata

`EnemyKind` tiene 10 miembros y 8 sets. La relación ("todo set es un tipo, y todo tipo sin set es uno de los dos declarados") es un hecho que **hoy nadie verifica**, y es la clase de cosa que se rompe en silencio cuando se agrega un tipo nuevo.

**Test nuevo** (en `tests/test_enemy_set_discovery.py` o en uno nuevo):

```python
def test_every_set_is_an_enemy_kind():
    from src.entities.enemies.enemy import EnemyKind
    from src.anim.sets import ENEMY_SETS
    kinds = {k.value for k in EnemyKind}
    assert set(ENEMY_SETS) <= kinds, "un set no es un EnemyKind"


def test_the_kinds_without_a_set_are_declared():
    """CARRIER y SUB_BOSS no tienen set por diseno.

    Si se agrega un EnemyKind nuevo, este test falla hasta que se decida
    si tiene set o no: la decision explicita es el punto.
    """
    from src.entities.enemies.enemy import EnemyKind
    from src.anim.sets import ENEMY_SETS
    without_set = {k.value for k in EnemyKind} - set(ENEMY_SETS)
    assert without_set == {"carrier", "sub_boss"}, (
        f"tipos sin set inesperados: {sorted(without_set - {'carrier','sub_boss'})}"
    )
```

### 4.5 Task 2 — las fotos con huella

**Un archivo versionado** con el hash de las 6 fotos:

```
tools/golden/layerstack/SHA256SUMS
```

Formato: el formato de `sha256sum` (una línea por foto: `<hash>  <nombre>`), que `Get-FileHash` y `sha256sum` produces y que un humano puede leer.

**Quién lo escribe:**
- El harness (`tools/capture/layerstack_frames.py`) **deja de regenerar en silencio**: cuando `--out` apunta a `tools/golden/layerstack/`, escribe el `SHA256SUMS` junto con las fotos. Regenerar sin actualizar el hashes **es** un cambio deliberado: el archivo de hashes aparece en el diff.
- Cuando el harness escribe **fuera** de `tools/golden/` (el modo temporal de los tests), **no** toca el `SHA256SUMS`.

**Quién lo verifica:** el gate (o el test de los goldens) comprueba, para cada foto commiteada:
1. Que su hash **esté** en el `SHA256SUMS` → si no está, la foto no fue derivada de la fuente (FALLA).
2. Que su hash **coincida** con el del `SHA256SUMS` → si no coincide, alguien editó la foto a mano o la regeneró sin actualizar las huellas (FALLA).

**El caso que hoy no existe y esta Task crea:** regenerás una foto a propósito → el hash cambia → el `SHA256SUMS` cambia → el diff muestra **exactamente** qué foto cambió y por hash. Y un cambio accidental → el hash cambia **sin** que el `SHA256SUMS` cambie → el gate se pone rojo.

### 4.6 Los dos checkpoints (igual que en la Fase 2)

- **Checkpoint 2A — el módulo y la puerta, sin cambiar comportamiento.** Sacar la lista de 14 lugares a un solo lugar, con la puerta puesta. Los 6 goldens **no** cambian (no se toca el frame). Criterio: `pytest` verde, `gate_ci.py` verde, y **el diff del `SHA256SUMS` es vacío**.
- **Checkpoint 2B — las huellas.** El `SHA256SUMS` entra versionado y la puerta de las fotos se activa. Criterio: `pytest` verde, `gate_ci.py` verde, y **regenerar una foto a mano pone el gate en rojo**.

---

## 5. Lo que este BLOQUE NO hace

- **No toca el motor por capas** (`src/render/`), ni las 30 capas, ni el orden. La decisión de alcance del motor (que crece hacia el HUD y las otras 13 escenas, o que se consolida en el gameplay) es del **owner** y vive en `docs/bloques/BLOQUE_75_CHECKLIST.md` §P4. Este BLOQUE no la prejuzga.
- **No parte `gameplay_runtime.py`** (6.700 líneas, 57 métodos `_draw_`). Es el BLOQUE siguiente, y depende de la decisión de alcance.
- **No agrega un enemigo nuevo.** Este BLOQUE hace que agregar uno sea **barato**; el BOMBER es otro trabajo.
- **No toca `EnemyKind`** ni agrega tipos de enemigo.
- **No reescribe el historial** ni toca tags. El repo es compartido con otro agente.
- **No toca un PNG de `Assets/`** (R1).
- **No cambia el mapa de PNGs legacy** (`gameplay_runtime.py:5313`): codifica otro hecho ("qué tipos tienen PNG de un solo frame"), no "qué sets existen". Se deja como literal, con un comentario que lo diga, para que nadie intente fusionarlo con la lista canónica.

---

## 6. File map

### 6.1 Nuevos

| Archivo | Qué |
|---|---|
| `src/anim/sets.py` | La expectativa + el descubrimiento + la puerta (≈60 líneas) |
| `tools/golden/layerstack/SHA256SUMS` | La huella de las 6 fotos (6 líneas) |
| `tests/test_enemy_sets_are_canonical.py` | Los tests de la relación con `EnemyKind` + la puerta |

### 6.2 Modificados

| Archivo | Qué cambia |
|---|---|
| `src/anim/clip.py` | `_enemies_root()` sale (pasa a `sets.py`) |
| `src/ui/gameplay_runtime.py` | El allowlist de la línea ~5303 pasa a derivarse del descubrimiento. **El mapa legacy de la línea ~5313 no se toca.** |
| `main.py` | `_pipeline_report` usa la expectativa |
| `tools/sprite_pipeline/gate.py` | La lista de la línea ~62 pasa a la expectativa; **se agrega la puerta G0** |
| `tools/sprite_pipeline/sets.py` | Re-exporta `_is_set` desde `src.anim.sets` (una sola definición) |
| `tools/regen_status.py` | `BUNDLED_SETS` se deriva de la expectativa + GOLIATH |
| `tools/capture/layerstack_frames.py` | Escribe el `SHA256SUMS` cuando captura sobre `tools/golden/` |
| `tests/test_layer_stack_renders_identical_frames.py` | Verifica las huellas |
| `tests/test_enemy_art_is_untouched.py` · `test_enemy_anchors_are_fresh.py` · `test_enemy_hitbox_is_not_the_canvas.py` · `test_enemy_manifest_matches_assets.py` · `test_enemy_scale_matches_runtime.py` · `test_enemy_sets_audit_clean.py` · `test_enemy_set_discovery.py` · `test_check_pipeline_command.py` · `test_regen_status_bundle.py` | Dejan de hardcodear la lista |

### 6.3 Lo que NO se toca (y por qué)

| Archivo | Por qué |
|---|---|
| `src/entities/enemies/enemy.py` (`EnemyKind`) | Es la lista de **tipos** (10), no de sets (8). D5. |
| `src/render/layer.py` · `src/ui/gameplay_layers.py` | El motor y las 30 capas: otro BLOQUE. |
| `src/ui/gameplay_runtime.py:5313` (mapa legacy) | Codifica otro hecho. |
| `Assets/**` | R1: ni un byte del arte. |

---

## 7. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | El runtime deja de dibujar un enemigo si el bundle no trae su set | Es la **degradación que ya existe**: sin el set, el PNG tampoco está y el enemigo cae al procedural. Verificá con `--check-pipeline` sobre un bundle sin un set. |
| R2 | El descubrimiento en el hot path se nota | Va memoizado (`lru_cache`), igual que la sonda de raíz. Medí: el runtime consulta **una vez**, no por enemigo. |
| R3 | La puerta G0 hace ruido en un repo con un set a medio agregar | Es el comportamiento **deseado**: un set a medio agregar tiene que ser visible. El mensaje dice exactamente qué falta. |
| R4 | El `SHA256SUMS` se desactualiza y rompe el gate de forma confusa | El mensaje de falla debe decir **qué** foto no coincide y **cómo** se arregla ("regenerá la foto y actualizá el SHA256SUMS"). |
| R5 | Un set con nombre `_` (backup) entra al descubrimiento | `_is_set()` ya lo excluye (misma regla que hoy). No cambia. |
| R6 | El otro agente está tocando los mismos archivos | Rama y worktree propios. Los archivos que este BLOQUE toca (`src/anim/`, `main.py`, `tools/sprite_pipeline/`) son los del runtime: si el otro agente está ahí, **coordiná antes** (el repo es el único canal: commiteá y avisá por el `.synapse`). |

---

## 8. Métricas de aceptación

El BLOQUE está terminado cuando **todo** esto es cierto:

1. `pytest tests\ --tb=no` → **0 fallos**, y la suite **crece** (los tests nuevos existen y los viejos siguen).
2. `tools/sprite_pipeline/gate_ci.py` → `PHASE 1 GATE OK` y `PHASE 2 GATE OK` (exit 0).
3. `audit_sf_sm.py --perfil=lite` → **7/7**, 0 findings.
4. **La lista está en un solo lugar**: `grep -rn '"mine_asteroid"' src/ tools/ main.py tests/` devuelve **UNA** declaración de lista (la de `src/anim/sets.py`) más las **menciones legítimas** (el caso de `mine_asteroid` en `gameplay_runtime.py`, `enemy.py` y los tests que lo nombran como caso). Ningún otro archivo **declara** la lista.
5. **La contraposición de la puerta** (obligatoria): agregar un set en disco sin declararlo → **el gate se pone rojo** con un mensaje que nombra el set. Volver atrás → verde. **Esto hay que probarlo y dejarlo escrito en el commit.**
6. **La contraposición de las huellas** (obligatoria): regenerar una foto sin actualizar el `SHA256SUMS` → **el gate se pone rojo**. Actualizar el `SHA256SUMS` → verde, y el diff muestra el hash viejo y el nuevo.
7. **R1 intacto**: `git diff --stat <base>..HEAD -- '*.png'` → **0 archivos**.
8. **El frame no se movió**: el diff de `tools/golden/layerstack/*.png` está **vacío** en el checkpoint 2A.
9. **El bundle**: `void-hunter-v1.9.0.exe --check-pipeline` sigue reportando los 8 sets con `pivot=fixed scale=(1.05,1.05)` y `layers: 30` (exit 0). **No hace falta reconstruir el `.exe`** para este BLOQUE: el cambio es de código y de tools, y el bundle no cambia de contenido (los sets son los mismos 8). Si reconstruís, el SHA256 del `.exe` cambia y hay que regenerar el STATUS.

---

## 9. Cómo verificar (los comandos, con lo esperado)

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-76-canonical-sets
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'

& $py -m pytest tests\ --tb=no -q                       # 0 fallos
& $py tools\sprite_pipeline\gate_ci.py                   # PHASE 1 GATE OK / PHASE 2 GATE OK
& $py main.py --check-pipeline                          # 8 sets + layers: 30, exit 0
$env:PYTHONUTF8='1'
& $py C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py . --perfil=lite   # 7/7
```

**Las dos contraposiciones, a mano** (son el corazón del BLOQUE):

```powershell
# 1. Un set en disco sin declarar -> el gate tiene que fallar
New-Item -ItemType Directory -Force -Path 'Assets\sprites\enemies\zz_test_set' | Out-Null
Copy-Item 'Assets\sprites\enemies\scout\manifest.toml' 'Assets\sprites\enemies\zz_test_set\'
& $py tools\sprite_pipeline\gate_ci.py                   # TIENE QUE FALLAR (G0: sobra en disco)
Remove-Item -Recurse -Force 'Assets\sprites\enemies\zz_test_set'   # <- la trampa de esto: Remove-Item
# (si tu politica de borrado lo bloquea, mové la carpeta a un temp y borrala con el launcher de basura)

# 2. Regenerar una foto sin actualizar el hashes -> el gate tiene que fallar
Copy-Item 'tools\golden\layerstack\hud.png' "$env:TEMP\hud_backup.png"
& $py tools\capture\layerstack_frames.py --only hud      # regenera
& $py tools\sprite_pipeline\gate_ci.py                   # TIENE QUE FALLAR (la huella no coincide)
Copy-Item "$env:TEMP\hud_backup.png" 'tools\golden\layerstack\hud.png'   # restaurar
```

---

## 10. Lo que este BLOQUE desbloquea

Con las listas en un solo lugar y las huellas activas:

- **Agregar un enemigo nuevo** (BOMBER, MINELAYER — la primera tarea del roadmap) es: arte + manifest + anchors + **una línea** en `ENEMY_SETS`. El gate lo audita, el runtime lo dibuja, `--check-pipeline` lo reporta y el bundle lo exige. **Sin 14 ediciones.**
- **Cambiar el arte a propósito** es un diff que dice **qué** cambió y **cuánto**, no un diff invisible.
- **La lista de tipos sin set** (`CARRIER`, `SUB_BOSS`) deja de ser una convención oral y pasa a ser un test.

Y lo que sigue, para el próximo BLOQUE (no en este): **partir `gameplay_runtime.py`** con el motor por capas como vehículo, que es lo que el roadmap pide en "Next → Polish" — y que depende de la decisión de alcance que el owner tiene abierta en `docs/bloques/BLOQUE_75_CHECKLIST.md` §P4.

---

## Appendix — el registro de la revisión que lo origina

Este spec implementa dos follow-ups de dos revisiones:

- `docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md` §7 **#5** — "Los ocho tipos de enemigo están hardcodeados en cinco lugares… Se quiere una lista canónica."
- `docs/handoffs/HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` §6 **#1** — "La lista de los 8 sets de enemigos está literal en 14 archivos; sólo 3 copias están ancladas al disco por una aserción de igualdad."
- `docs/handoffs/HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` §6 **#8** — "Las actions del CI no están pineadas por SHA" *(NO es parte de este BLOQUE; está en la tanda 4 del plan).*

Y el follow-up que este BLOQUE **no** cubre, y sigue abierto: **`docs/handoffs/HANDOFF-BLOQUE-75-GSTACK-REVIEW-2026-11-07.md` §6 #2** (`DrawContext` con 4 campos y 2 métodos sin consumidor) y **#3** (`Part.on_missing` / `AnimSet.sided` sin consumidor) — que son **decisiones de arquitectura del owner**, no tareas.
