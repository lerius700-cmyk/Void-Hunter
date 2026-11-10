# HANDOFF — BLOQUE 76: contenido de primera clase (2026-11-10)

**Rama:** `bloquec-76-contenido` (worktree `.worktrees/bloquec-76-contenido`) · **Base:** `origin/bloquec-67-goliath-port` @ `a0c6f6f` (v1.9.0) · **Spec:** `docs/superpowers/specs/2026-11-10-bloque-76-contenido-de-primera-clase-design.md` · **Perfil:** Lite · **Schema:** `.synapse` 2.2.0

> **Nada commiteado todavía.** La rama existe y el trabajo está en el worktree.
> El commit lo pide el usuario (regla del proyecto, BLOQUE 58.14).

Este handoff es el canal. El otro agente sobre este repo lo necesita commiteado
y ruteado; hasta que el usuario autorice el commit, esta rama es el único
lugares donde vive el trabajo.

---

## 1. Qué hace este BLOQUE, en dos frases

1. **La lista de los 8 sets de enemigos deja de estar escrita en 14 archivos**
   y pasa a estar escrita en **UNO**: `src/anim/sets.py`. Y el gate pone una
   **puerta** entre lo que el repo **debe** tener y lo que **hay** en disco.
2. **Las 6 fotos de referencia del frame llevan huella**: un archivo
   versionado (`tools/golden/layerstack/SHA256SUMS`) con el SHA256 de cada
   foto, así que un cambio deliberado del arte y uno accidental **se ven
   distinto**.

El objetivo de las dos cosas es el mismo: **que iterar contenido sea barato
y verificable.**

---

## 2. El vocabulario (dos palabras, no más)

| Palabra | Qué es | Dónde vive |
|---|---|---|
| **la EXPECTATIVA** | Los sets que el repo **debe** tener. Dato del proyecto, escrito a mano, **una sola vez**. | `src/anim/sets.py::ENEMY_SETS` |
| **el DESCUBRIMIENTO** | Los sets que **hay** en disco, leídos del directorio y memoizados. | `src/anim/sets.py::discover_enemy_sets()` |

Cada consumidor usa la que corresponde a su pregunta:

| Consumidor | Qué usa | Por qué |
|---|---|---|
| `tools/sprite_pipeline/gate.py` | **las dos** | Audita lo que hay y exige que lo que hay sea lo que debe haber (puerta G0). |
| `main.py::_pipeline_report` (`--check-pipeline`) | **la expectativa** | Es un check: verifica que el bundle traiga lo que debe traer. |
| `tools/regen_status.py::BUNDLED_SETS` | **la expectativa** (+ GOLIATH) | Es un check del bundle. |
| `src/ui/gameplay_runtime.py` | **el descubrimiento** | El runtime dibuja lo que hay; si un set falta en el bundle, ese enemigo cae al procedural (degradación correcta). |
| Los tests que parametrizan sobre los sets | **las dos**, según lo que prueben | Un test que recorre el disco cubre un set nuevo sin editarlo. |
| `src/entities/enemies/enemy.py` (`EnemyKind`) | **no se toca** | Es otra verdad: la lista de **tipos** (10), no de sets (8). |

**La puerta:** `src/anim/sets.py::enemy_sets_mismatch()` → `{faltan_en_disco,
sobran_en_disco}`. El gate la imprime y falla con eso.

---

## 3. El módulo nuevo: `src/anim/sets.py`

Vive en `src/` y **no** en `tools/` por una razón dura: el build congelado no
empaqueta `tools/`, y `main.py --check-pipeline` tiene que correr **dentro**
del `.exe`.

```python
ENEMY_SETS: tuple[str, ...] = (...)          # la EXPECTATIVA, 8 nombres
def _is_set(path) -> bool                     # UNA definición de "es un set"
@functools.lru_cache(maxsize=1)
def enemies_root() -> Path                    # la sonda de la raíz
@functools.lru_cache(maxsize=1)
def discover_enemy_sets() -> tuple[str, ...]  # el DESCUBRIMIENTO
@functools.lru_cache(maxsize=1)
def enemy_set_lookup() -> frozenset[str]      # el descubrimiento, O(1) para el hot path
def clear_enemy_sets_cache() -> None          # la puerta de la caché
def enemy_sets_mismatch() -> dict[str, list[str]]  # la puerta de la lista
```

**Por qué la lista es hardcodeada y no derivada del disco (decisión D2 del
spec):** si fuera derivada, el gate compararía el disco contra sí mismo y
siempre estaría verde. La puerta sólo es una puerta si los dos lados pueden
discrepar.

**Por qué el descubrimiento está cacheado (D3):** el runtime lo consulta en
el hot path (una vez por enemigo, por frame). La sonda de raíz ya estaba
memoizada desde el BLOQUE 75 (costaba 72-90 µs por enemigo y frame); el
descubrimiento se memoiza igual. `clear_enemy_sets_cache()` existe porque
una caché que no se puede tirar es una mentira: un set nuevo en disco tiene
que ser visible a la pregunta siguiente.

---

## 4. Quién usa qué (los 8 + las 2 derivas de la sonda)

| Archivo | Qué cambió |
|---|---|
| `src/anim/sets.py` | **NUEVO.** La expectativa + el descubrimiento + la puerta. |
| `src/anim/clip.py` | `_enemies_root()` **sale**: pasa a ser un alias de `sets.enemies_root()`. El alias conserva `cache_clear`/`cache_info`, así que `tests/test_enemies_root_is_resolved_once.py` sigue funcionando sin cambios. |
| `src/ui/gameplay_runtime.py` | El allowlist de la línea ~5312 pasa a derivarse del descubrimiento. **El mapa legacy de los PNG de un solo frame NO se toca** (codifica otro hecho), con un comentario que lo dice. |
| `main.py` | `_pipeline_report` usa la expectativa. |
| `tools/sprite_pipeline/gate.py` | La lista local **sale**; se importa la canónica. **Se agrega la puerta G0.** G6 pasó a comparar el descubrimiento del pipeline contra el canónico. |
| `tools/sprite_pipeline/sets.py` | Re-exporta `_is_set` desde `src.anim.sets` (la **misma función**, no una copia: `sprite_pipeline.sets._is_set is src.anim.sets._is_set` → `True`). `sets_roots()` usa la raíz canónica de enemigos. |
| `tools/regen_status.py` | `BUNDLED_SETS` se deriva de la expectativa + GOLIATH. |
| `tools/capture/layerstack_frames.py` | Escribe el `SHA256SUMS` junto a las fotos. |
| `.gitattributes` | Una regla estrecha para el `SHA256SUMS` (ver §6). |

**Los 9 (o 10) archivos de test que hardcodeaban la lista** ahora la importan:
`test_enemy_art_is_untouched.py` · `test_enemy_anchors_are_fresh.py` ·
`test_enemy_hitbox_is_not_the_canvas.py` · `test_enemy_manifest_matches_assets.py` ·
`test_enemy_scale_matches_runtime.py` · `test_enemy_sets_audit_clean.py` ·
`test_enemy_set_discovery.py` · `test_check_pipeline_command.py` ·
`test_regen_status_bundle.py` · **`test_enemy_clip_semantics.py`** (el décimo:
el spec se olvidó de él, y lo detectó el test nuevo).

---

## 5. Las dos contraposiciones (ejecutadas a mano, con la salida real)

> La regla de la fase: *una garantía que el check no puede ver no es una
> garantía, es una hipótesis.* Las dos se probaron de verdad.

### 5.1 Un set en disco sin declarar → el gate se pone ROJO y lo nombra

```
Assets/sprites/enemies/zz_test_set/manifest.toml   (copia del de scout)
& $py tools/sprite_pipeline/gate_ci.py
```

**Salida real:**

```
PHASE 1 GATE FAILED:
  - G0: hay sets en disco que no estan declarados en ENEMY_SETS (src/anim/sets.py): zz_test_set
```

Exit 1. Al borrar la carpeta: `PHASE 1 GATE OK` / `PHASE 2 GATE OK`, exit 0.

**Defecto que encontró esta contraposición (y que se corrigió):** la primera
vez el gate **crasheó** con un `FileNotFoundError` del auditor (el set de
prueba no tiene arte) en vez de reportar G0. Un gate que crashea en vez de
dictaminar se lleva el diagnóstico. Ahora `G1` y `G2` atrapan
`(OSError, ValueError)` y lo reportan como fallo. **Esto no estaba en el
spec** — salió de la contraposición, que es exactamente para lo que existe.

### 5.2 Una foto cambiada sin actualizar el `SHA256SUMS` → el gate se pone ROJO

El cambio fue **un byte al final del PNG**: los píxeles son **idénticos** (el
comparador de píxeles sigue en verde) y el hash cambia. Es el caso que el
comparador de píxeles **no puede ver** y que la huella sí.

```
committed hash : 8a2de232490dc85ccd4e7cb8fdaf254997f9e0f4ecfde9591085addfee550d1c
changed   hash : 6d9a6531cd3642d2cb8a4e91ddfea190e17eb3dfd4f6e172a71d333d0b230aba
```

**Salida real del gate:**

```
--- PHASE 2 GATE (base e619527) ---
PHASE 2 GATE FAILED:
  - P2-G1: pytest exited 1:
E   AssertionError: hud: the fingerprint does not match the committed photo
(8a2de232490dc85ccd4e7cb8fdaf254997f9e0f4ecfde9591085addfee550d1c !=
6d9a6531cd3642d2cb8a4e91ddfea190e17eb3dfd4f6e172a71d333d0b230aba). Either the photo was edited or
re-generated without updating the SHA256SUMS: regenerate it and commit SHA256SUMS together with the photo
```

Exit 1.

**La segunda mitad:** al actualizar el `SHA256SUMS`, el check de huella
(`P2-G1`) vuelve a **verde** (6 passed) y el diff del archivo muestra **el
hash viejo y el nuevo** lado a lado:

```diff
+6d9a6531cd3642d2cb8a4e91ddfea190e17eb3dfd4f6e172a71d333d0b230aba  hud.png
```

(Quedó rojo `P2-G5`, que es **otra** puerta: la foto modificada sin commitear.
Esa puerta es correcta y es preexistente.)

**Restaurado:** la foto volvió a su hash original
(`8a2de232…`) y `git status` sobre `tools/golden` y `Assets` quedó limpio.

---

## 6. El `SHA256SUMS` y por qué hizo falta una regla en `.gitattributes`

`core.autocrlf=true` en esta máquina: sin una regla, el archivo se checkouteaba
con **CRLF** en Windows y con **LF** en otros lados — y un registro
commiteado cuyos bytes dependen de la máquina no es un registro. La regla es
**estrecha** a propósito (una `* text=auto` renormalizaría todo el árbol y
tocaría los worktrees de los agentes en paralelo):

```
tools/golden/layerstack/SHA256SUMS text eol=lf
```

`git check-attr` → `text: set`, `eol: lf`, y el working copy queda `w/lf`.

El harness escribe el archivo **junto a las fotos que acaba de escribir**, y
describe **todas** las fotos del directorio (no sólo las capturadas): una
captura parcial (`--only hud`) produce una huella completa y no puede dejar
caer a las otras cinco en silencio.

---

## 7. El test nuevo: `tests/test_enemy_sets_are_canonical.py`

9 tests. Los que importan:

- **`test_the_list_is_declared_in_one_place_only`** — recorre `src/`, `tools/`,
  `tests/` y `main.py` con el **AST** y busca literales que declaren la lista
  completa. Sólo puede declararla `src/anim/sets.py`. (Umbral: un literal con
  **los ocho** nombres. Un literal con **siete** no es una declaración de la
  lista: es un subconjunto con un motivo — la mina no es una nave estándar.)
- **`test_every_set_is_an_enemy_kind`** y
  **`test_the_kinds_without_a_set_are_declared`** — la relación con
  `EnemyKind` (10 tipos, 8 sets). `CARRIER` y `SUB_BOSS` no tienen set **por
  diseño**, y ahora eso es un test y no una convención oral: agregar un
  `EnemyKind` nuevo falla acá hasta que se decida si tiene set.
- **La puerta, probada en aislamiento** (`test_the_door_names_a_set_that_is_on_disk_and_not_declared`,
  `..._and_not_on_disk`, `test_the_cache_can_be_dropped`): monkeypatchean
  `enemies_root` a un `tmp_path` y **no escriben nunca en el repo** (L7).

**El caso que el spec no tenía:** `test_the_list_is_declared_in_one_place_only`
encontró **tres** copias más que el spec no listaba:
`tests/test_enemy_clip_semantics.py` (las 7 sin la mina — **corregida**: ahora
se deriva de la lista canónica), `tests/test_ship_perspective.py` y
`tools/capture/capture_bloque_62_ships.py` (los dos con las 7 de la familia
"nave estándar"; **no se tocaron**, ver §9).

---

## 8. Los números (verificados, no declarados)

| Métrica | Antes (a0c6f6f) | Ahora |
|---|---|---|
| Tests | 3.172 (3.165 pass + 1 xfail + 6 skip) | **3.186** (3.179 pass + 1 xfail + 6 skip) |
| Fallos | 0 | **0** |
| Gate | `PHASE 1/2 GATE OK` | **idem** |
| `--check-pipeline` | 8 sets, `layers: 30`, exit 0 | **idem** |
| `audit_sf_sm.py --perfil=lite` | 7/7 | **7/7** |
| PNGs modificados | — | **0** (`git diff --stat a0c6f6f -- '*.png'` vacío) |
| Guard tests (G13) | 84 casos | **84 casos** (sin cambio: el gate exige el número exacto) |

Los **+14** tests: 9 del archivo nuevo de la lista canónica, 4 de la huella de
las fotos y 1 de la cobertura del bundle.

---

## 9. Lo que este BLOQUE NO hace (y sigue pendiente)

- **NO commitea.** La rama `bloquec-76-contenido` está en el worktree
  `.worktrees/bloquec-76-contenido`. El commit lo pide el usuario.
- **NO reconstruye el `.exe`.** El cambio es de código y de tools; el bundle
  no cambia de contenido (los sets son los mismos 8). Si se reconstruye, el
  SHA256 del `.exe` cambia y hay que regenerar el STATUS.
- **NO toca el motor por capas** (`src/render/`), ni `gameplay_runtime.py` más
  allá del allowlist, ni `EnemyKind`, ni un PNG de `Assets/` (R1).
- **NO parte `gameplay_runtime.py`** (6.700 líneas): es el BLOQUE siguiente y
  depende de la decisión de alcance del owner.
- **NO toca las 3 copias parciales** que quedan: `tests/test_ship_perspective.py`
  y `tools/capture/capture_bloque_62_ships.py` declaran las **7** naves
  estándar (con prefijo `enemy_` en el primero), y `src/ui/gameplay_runtime.py`
  tiene el **mapa legacy** de los PNG de un solo frame. Los tres son
  subconjuntos con un motivo, no la lista. Se dejan con un comentario que lo
  dice, para que nadie intente fusionarlos con la lista canónica.
- **NO responde las 3 preguntas de alcance de la Fase 3**
  (`docs/bloques/BLOQUE_75_CHECKLIST.md` §P4): el motor por capas, el clip
  `death` de la mina, y si el `.exe` se reconstruye en cada fase.
- **NO commitea los 22 follow-ups** del plan de las 7 tandas (este spec cubre
  las tandas 2 parcial y 5).
- **NO rota la AccessKey de Aliyun** (runbook en
  `docs/handoffs/HANDOFF-SECURITY-2026-11-08.md` §4 — es de la consola del
  usuario).

---

## 10. Cómo verificar (los comandos, con lo esperado)

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-76-contenido
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'

& $py -m pytest tests\ --tb=no            # 0 fallos
& $py tools\sprite_pipeline\gate_ci.py    # PHASE 1 GATE OK / PHASE 2 GATE OK
& $py main.py --check-pipeline            # 8 sets + layers: 30, exit 0
$env:PYTHONUTF8='1'
& $py C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py . --perfil=lite   # 7/7
git diff --stat a0c6f6f -- '*.png'        # vacío (R1)
```

**La lista en un solo lugar:**

```powershell
& $py -m pytest tests/test_enemy_sets_are_canonical.py::test_the_list_is_declared_in_one_place_only
```

**Las contraposiciones** están en §5, con la salida real.

---

## 11. La regla que este BLOQUE produce (para el próximo)

> *Una garantía que el check no puede ver no es una garantía, es una
> hipótesis.*

Aplicada al contenido: **un set nuevo tiene que ser BARATO de agregar y
VERIFICABLE de agregar.** Hoy son 4 cosas (arte + manifest + anchors + una
línea en `ENEMY_SETS`) y las 4 quedan cubiertas: el gate lo audita, el runtime
lo dibuja, `--check-pipeline` lo reporta y el bundle lo exige. Antes eran 4
cosas y ninguna de las 4 lo cubría: el set era un pasajero.

Y lo mismo para el arte: **un cambio deliberado y uno accidental tienen que
verse distinto.** Hoy se ven igual; con el `SHA256SUMS`, el deliberado
muestra el hash viejo y el nuevo, y el accidental deja la foto sin su hash.
