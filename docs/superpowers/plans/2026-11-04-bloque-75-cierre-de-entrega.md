# BLOQUE 75 — Cierre de entrega Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que lo que la Fase 1 y la Fase 2 deliveraron pase a ser **publicable y verificable sin intervención humana**: la puerta de la fase corre sola en el CI, el binario descargable contiene el motor de capas, y el changelog dice qué cambió.

**Architecture:** Tres piezas nuevas y una versión. (1) `tools/sprite_pipeline/gate_ci.py` decide **qué gates aplican** a la rama y los corre — el gate sigue estricto, el que decide es el runner. (2) `tools/capture/probe_layer_stack.py` instrumenta el stack contra el **binario**, que es la única prueba de que el bundle frozen encuentra los manifests. (3) `tools/regen_status.py` verifica los 18 archivos del bundle, no 2. (4) La versión `v1.9.0`.

**Tech Stack:** Python 3.11, pygame 2.6, PyInstaller (onefile), GitHub Actions (`windows-latest`), `gh` CLI.

## Global Constraints

- **R1 — ni un byte del arte cambia.** Ni `*.png` ni los goldens (`tools/golden/layerstack/*.png`).
- **R4 — stdlib + pygame.** Cero dependencias nuevas.
- **R7 — headless y determinista.** `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy`.
- **L1 — sin tablas multilínea inline en el código.** Las tablas viven en este plan.
- **L5 — excepts estrechos.**
- **L7 — los tests nunca escriben en el repo.** El temp va a `%TEMP%`.
- **El gate NO se ablanda.** Si su base no está, falla. Lo que decide la aplicabilidad es el runner.
- **Windows:** el job de los gates corre en `windows-latest` porque el HUD usa `SysFont("consolas")` y los goldens llevan el score.
- **Shell:** PowerShell 5.1 en local (no `&&`, no `ls -la`, no `head`/`tail`/`grep`). En el CI, el shell por defecto de `windows-latest` es `pwsh`.
- **Commits:** `feat:/fix:/docs:/test:/build: BLOQUE 75 ...`, paths explícitos, nunca `-A`.
- **La línea de release es `bloquec-67-goliath-port`. `master` no se toca.**

---

### Task 1: El runner que decide qué gates aplican

**Files:**
- Modify: `tools/sprite_pipeline/gate.py` (exponer `resolve_base` público)
- Create: `tools/sprite_pipeline/gate_ci.py`
- Test: `tests/test_gate_ci.py`

**Interfaces:**
- Consumes: `gate.resolve_base(argument: str | None, phase: int) -> str` (hoy es `_resolve_base`), `gate.main(argv: list[str] | None) -> int`
- Produces: `gate_ci.applicable(base: str, repo: Path) -> tuple[bool, str]`, `gate_ci.run_gate(phase: int, repo: Path, runner: Callable[[list[str]], int] | None = None) -> int`, `gate_ci.main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Escribir el test que falla**

`tests/test_gate_ci.py`:

```python
"""BLOQUE 75: the CI runner decides WHICH gates apply.

The gate itself is strict: a base commit that is not in the repository is a
FAILURE, and that is right for the branch the phase lives on. But the CI
runs on more than one branch, and `master` has neither the Phase 1 base nor
the Phase 2 base as an ancestor. So the APPLICABILITY decision lives in the
runner, and a phase that does not apply says SKIPPED -- never OK.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate_ci


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
    return repo


def test_a_base_that_is_an_ancestor_applies(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    applies, reason = gate_ci.applicable(base, repo)
    assert applies, reason


def test_a_base_that_is_not_in_the_repository_does_not_apply(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    applies, reason = gate_ci.applicable("deadbeefdeadbeef", repo)
    assert not applies
    assert "deadbeefdeadbeef" in reason


def test_a_phase_that_does_not_apply_says_skipped_and_never_ok(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    code = gate_ci.run_gate(1, repo, runner=lambda argv: 0, base="deadbeefdeadbeef")
    out = capsys.readouterr().out
    assert code == 0
    assert "SKIPPED" in out
    assert "GATE OK" not in out


def test_a_gate_that_fails_fails_the_runner(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    code = gate_ci.run_gate(1, repo, runner=lambda argv: 3, base=base)
    capsys.readouterr()
    assert code == 3


def test_the_runner_runs_every_phase_that_applies(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    ran: list[list[str]] = []

    def runner(argv: list[str]) -> int:
        ran.append(argv)
        return 0

    code = gate_ci.run_gate(1, repo, runner=runner, base=base)
    capsys.readouterr()
    assert code == 0
    assert ran == [["--phase", "1"]]
```

- [ ] **Step 2: Correr el test y ver que falla**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_gate_ci.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'sprite_pipeline.gate_ci'`

- [ ] **Step 3: Exponer `resolve_base` en el gate**

En `tools/sprite_pipeline/gate.py`, renombrar `_resolve_base` a `resolve_base` y
actualizar su único call site. **Dejar un alias** para no romper nada:

```python
# The public name: the CI runner needs to resolve the SAME base the gate
# will measure, and it must not duplicate the constants. The underscore
# alias stays for the callers inside this module.
resolve_base = _resolve_base
```

En realidad, más limpio: renombrar la función a `resolve_base` y cambiar el call
site (`gate.py` la usa en un par de lugares). Dejar `_resolve_base = resolve_base`
como alias para los call sites internos que no se toquen.

- [ ] **Step 4: Escribir `gate_ci.py`**

```python
"""BLOQUE 75: run the gates that apply to this branch.

The gate is STRICT on purpose: a base commit that is not in the repository
is a FAILURE, because the phase's promise is about the range and a gate that
skips its own range is not a gate. That is right for the branch the phase
lives on.

But the CI runs on more than one branch, and `master` has neither the
Phase 1 base (773cf08) nor the Phase 2 base (e619527) as an ancestor -- so
on `master` both gates would fail for a reason that has nothing to do with
the code. The APPLICABILITY decision therefore lives HERE, and the gate
stays strict.

A phase that does not apply prints `PHASE <n> GATE SKIPPED: <reason>` and
NEVER prints `GATE OK`. A skipped gate is not a green gate, and the log has
to say which one it was.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate  # noqa: E402

PHASES = (1, 2)


def applicable(base: str, repo: Path) -> tuple[bool, str]:
    """Whether the phase's base commit is in this repository's history.

    Returns `(applies, reason)`. The reason is empty when it applies.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, "HEAD"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    if proc.returncode == 128:
        return False, f"the base commit {base!r} is not in this repository"
    return False, f"the base commit {base!r} is not an ancestor of HEAD"


def run_gate(
    phase: int,
    repo: Path,
    runner: Callable[[list[str]], int] | None = None,
    base: str | None = None,
) -> int:
    """Run one phase's gate, or explain why it does not apply.

    `runner` and `base` exist for the test: the test drives the decision
    without running the real gate.
    """
    resolved = base if base is not None else gate.resolve_base(None, phase)
    applies, reason = applicable(resolved, repo)
    if not applies:
        print(f"PHASE {phase} GATE SKIPPED: {reason}")
        return 0
    if runner is None:
        runner = gate.main
    print(f"--- PHASE {phase} GATE (base {resolved}) ---")
    return runner(["--phase", str(phase)])


def main(argv: Sequence[str] | None = None) -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    code = 0
    for phase in PHASES:
        result = run_gate(phase, repo)
        if result != 0:
            code = result
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Correr el test y ver que pasa**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_gate_ci.py -v
```
Expected: **5 passed**

- [ ] **Step 6: Correr el runner de verdad**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
```
Expected: los dos gates corren y salen `PHASE 1 GATE OK` y `PHASE 2 GATE OK`,
exit 0. (En esta rama las dos bases son ancestros.)

- [ ] **Step 7: Commit**

```powershell
git add tools/sprite_pipeline/gate.py tools/sprite_pipeline/gate_ci.py tests/test_gate_ci.py
git commit -m "feat: BLOQUE 75 - el runner del CI decide que gates aplican y los corre"
```

---

### Task 2: El job `gates` en el CI

**Files:**
- Modify: `.github/workflows/test.yml`

**Interfaces:**
- Consumes: `python tools/sprite_pipeline/gate_ci.py` (Task 1)
- Produces: un job `gates` con estado propio en los required checks

- [ ] **Step 1: Escribir el job**

Agregar después del job `pytest` (y NO tocar el job `pytest`):

```yaml
  gates:
    # The golden frames carry the HUD, and the HUD draws the score with
    # SysFont("consolas") -- a SYSTEM font, not a bundled one. On a Linux
    # runner that font is missing, pygame falls back to its default and the
    # score pixels change: the Phase 2 gate would be RED on every run for a
    # reason that has nothing to do with the code. So the gates run where
    # the goldens were captured.
    #
    # The timeout is 25 and not 15 because the Phase 2 gate's worst case is
    # 1380 s (3 git calls of 60 s + 4 budgets of 300 s). The pytest job kills
    # at 900 s; here the gate reports its OWN diagnosis instead of dying
    # without one. A healthy run takes ~16 s.
    runs-on: windows-latest
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
        with:
          # The FULL history: the gates measure the phase RANGE (base..HEAD).
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install the requirements
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m pip install -r requirements-dev.txt

      - name: Set SDL_VIDEODRIVER=dummy (headless)
        run: |
          echo "SDL_VIDEODRIVER=dummy" >> $GITHUB_ENV
          echo "SDL_AUDIODRIVER=dummy" >> $GITHUB_ENV

      - name: Run the gates that apply to this branch
        run: python tools/sprite_pipeline/gate_ci.py
```

- [ ] **Step 2: Validar el YAML**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -c "import yaml,pathlib; d=yaml.safe_load(pathlib.Path('.github/workflows/test.yml').read_text(encoding='utf-8')); print(sorted(d['jobs'])); print(d['jobs']['gates']['runs-on'], d['jobs']['gates']['timeout-minutes'])"
```
Expected: `['gates', 'pytest']` y `windows-latest 25`

**Si `yaml` no está en el venv**, leer el archivo y comprobarlo a mano: los dos
jobs, `runs-on: windows-latest`, `timeout-minutes: 25`.

- [ ] **Step 3: Commit**

```powershell
git add .github/workflows/test.yml
git commit -m "ci: BLOQUE 75 - el job de los gates corre en windows-latest con presupuesto de 25 minutos"
```

- [ ] **Step 4: Validarlo en el CI ANTES de la línea de release**

```powershell
git branch bloquec-75-ci-gates
git push -u origin bloquec-75-ci-gates
gh workflow run test.yml --ref bloquec-75-ci-gates
```
Esperar el job `gates`:
```powershell
gh run list --workflow test.yml --branch bloquec-75-ci-gates --limit 3
gh run watch <run-id>
```
Expected: **el job `gates` en verde** y el log diciendo `PHASE 1 GATE OK` y
`PHASE 2 GATE OK`. Si el job sale rojo, **NO** se mergea: se lee el log, se
arregla, y se repite.

- [ ] **Step 5: Mergear a la línea de release**

```powershell
git checkout bloquec-67-goliath-port
git merge --no-ff bloquec-75-ci-gates -m "merge: BLOQUE 75 - el job de los gates en el CI de la linea de release"
git push origin bloquec-67-goliath-port
```
Y confirmar que el push de la línea de release dispara el workflow con el job
`gates` en verde.

---

### Task 3: El bundle tiene que llevar los nueve sets

**Files:**
- Modify: `tools/regen_status.py` (`_frozen_assets_verified` → 18 archivos)
- Modify: `tests/test_build_spec_assets.py` (el contrato del `datas`)
- Test: `tests/test_regen_status_bundle.py`

**Interfaces:**
- Consumes: `CArchiveReader` (PyInstaller) para leer el bundle
- Produces: `regen_status.frozen_assets_verified(entries: list[str]) -> bool` (puro, testeable)

- [ ] **Step 1: Escribir el test que falla**

`tests/test_regen_status_bundle.py`:

```python
"""BLOQUE 75: the frozen bundle has to carry the manifests of ALL NINE sets.

After Phase 2 the enemy manifests are LOAD-BEARING at runtime: the
runtime reads them every frame to draw the enemies. Before Phase 2 only
GOLIATH's two files were verified, so a bundle that shipped the boss's
manifest and none of the enemies' would have passed the check -- and the
enemies would have fallen back silently, with no error anywhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from regen_status import frozen_assets_verified

SETS = (
    "Assets/sprites/bosses/goliath",
    "Assets/sprites/enemies/cruiser",
    "Assets/sprites/enemies/drone",
    "Assets/sprites/enemies/heavy",
    "Assets/sprites/enemies/kamikaze",
    "Assets/sprites/enemies/mine_asteroid",
    "Assets/sprites/enemies/scout",
    "Assets/sprites/enemies/sniper",
    "Assets/sprites/enemies/turret",
)


def _complete_entries() -> list[str]:
    entries: list[str] = []
    for set_dir in SETS:
        entries.append(f"{set_dir}/manifest.toml")
        entries.append(f"{set_dir}/anchors.toml")
    return entries


def test_a_bundle_with_every_set_is_verified() -> None:
    assert frozen_assets_verified(_complete_entries())


def test_a_bundle_without_an_enemy_manifest_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "enemies/scout/manifest.toml" not in e]
    assert not frozen_assets_verified(entries)


def test_a_bundle_with_only_the_boss_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "enemies/" not in e]
    assert not frozen_assets_verified(entries)


def test_a_bundle_without_the_anchors_is_not_verified() -> None:
    entries = [e for e in _complete_entries() if "anchors.toml" not in e]
    assert not frozen_assets_verified(entries)
```

- [ ] **Step 2: Correr el test y ver que falla**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_regen_status_bundle.py -v
```
Expected: FAIL — `ImportError: cannot import name 'frozen_assets_verified'`

- [ ] **Step 3: Implementar en `regen_status.py`**

Reemplazar `_frozen_assets_verified` por una función pura + el lector:

```python
# The sets whose manifest AND anchors the frozen bundle has to carry.
# BLOQUE 75 Phase 2: the enemy manifests are LOAD-BEARING at runtime --
# the runtime reads them every frame to draw the enemies. Before Phase 2
# only GOLIATH's two files were checked, so a bundle with the boss's
# manifest and none of the enemies' would have passed, and the enemies
# would have fallen back silently.
BUNDLED_SETS = (
    "Assets/sprites/bosses/goliath",
    "Assets/sprites/enemies/cruiser",
    "Assets/sprites/enemies/drone",
    "Assets/sprites/enemies/heavy",
    "Assets/sprites/enemies/kamikaze",
    "Assets/sprites/enemies/mine_asteroid",
    "Assets/sprites/enemies/scout",
    "Assets/sprites/enemies/sniper",
    "Assets/sprites/enemies/turret",
)


def frozen_assets_verified(entries: list[str]) -> bool:
    """Whether the bundle carries the manifest AND the anchors of every set.

    Pure on purpose: the reading of the bundle needs PyInstaller and a real
    .exe, and the DECISION does not.
    """
    normalised = {entry.replace("\\", "/") for entry in entries}
    for set_dir in BUNDLED_SETS:
        for name in ("manifest.toml", "anchors.toml"):
            wanted = f"{set_dir}/{name}"
            if not any(entry.endswith(wanted) for entry in normalised):
                return False
    return True


def _frozen_assets_verified(exe: Path) -> bool:
    """Whether the bundle really carries the nine sets."""
    return frozen_assets_verified(_bundle_entries(exe))
```

Y actualizar el texto de `_build_row` para que nombre los nueve sets en vez de
GOLIATH solo.

- [ ] **Step 4: Correr el test y ver que pasa**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_regen_status_bundle.py -v
```
Expected: **4 passed**

- [ ] **Step 5: El contrato del `datas`**

En `tests/test_build_spec_assets.py`, agregar:

```python
def test_the_bundle_carries_the_manifest_of_every_set():
    """The `datas` covers the tree where the nine manifests live.

    `build.spec` bundles `Assets/sprites` as a directory, so every
    `manifest.toml` and `anchors.toml` under it goes in. If that entry
    ever changes, the frozen build would lose the enemy manifests and
    the enemies would fall back silently -- with no error anywhere.
    """
    spec = (ROOT / "build.spec").read_text(encoding="utf-8")
    assert '"Assets" / "sprites"' in spec
    for kind in ("scout", "cruiser", "drone", "heavy", "kamikaze", "sniper", "turret", "mine_asteroid"):
        set_dir = ROOT / "Assets" / "sprites" / "enemies" / kind
        assert (set_dir / "manifest.toml").is_file(), kind
        assert (set_dir / "anchors.toml").is_file(), kind
```

Ajustar `ROOT` al que el archivo ya use (revisar las primeras líneas antes de
escribir: el archivo ya tiene una constante de raíz).

- [ ] **Step 6: Correr los dos archivos de test**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_build_spec_assets.py tests\test_regen_status_bundle.py -v
```
Expected: todos verdes

- [ ] **Step 7: Commit**

```powershell
git add tools/regen_status.py tests/test_regen_status_bundle.py tests/test_build_spec_assets.py
git commit -m "test: BLOQUE 75 - el bundle tiene que llevar los manifests de los nueve sets"
```

---

### Task 4: El juego reporta si su pipeline de enemigos está disponible

**Files:**
- Modify: `main.py` (el flag `--check-pipeline` y el comando `_cmd_check_pipeline`)
- Test: `tests/test_check_pipeline_command.py`

**Interfaces:**
- Consumes: `src.anim.clip.load_player_for_kind(kind: str, root: Path | None = None) -> ClipPlayer | None`, `src.ui.gameplay_layers.LAYER_BODIES: tuple[str, ...]`
- Produces: `main._cmd_check_pipeline() -> int` y el flag `--check-pipeline`

**Por qué un comando del juego y no un script aparte:** un script que
instrumenta `LayerStack.render` **no puede observar al `.exe`**, porque el
espía vive en el proceso padre y el binario congelado corre en otro. La
pregunta que hay que responder es *"¿este build puede dibujar los enemigos
por el compositor?"*, y la única forma de responderla **dentro** del binario
es que el binario lo reporte. Por eso el comando va en el juego.

> **Este es el hueco que la Fase 2 abrió:** después de la Fase 2 los manifests
> de enemigos son *load-bearing* en runtime. Un build congelado que no los
> lleve cae al camino viejo **sin ningún error**: el juego corre, los enemigos
> se ven, y nada lo reporta.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_check_pipeline_command.py`:

```python
"""BLOQUE 75: the game can report whether its enemy pipeline is available.

After Phase 2 the runtime reads the enemy manifests every frame to draw
the enemies. A frozen build that does not carry them falls back to the
old draw path SILENTLY -- the game still runs, the enemies still appear,
and nothing anywhere reports an error.

This command is the check that would have caught it, and it has to run
inside the frozen build too, so it lives in the game.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENEMY_KINDS = (
    "scout", "cruiser", "drone", "heavy",
    "kamikaze", "sniper", "turret", "mine_asteroid",
)


def test_the_command_reports_every_enemy_set() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "pipeline check OK" in out
    for kind in ENEMY_KINDS:
        assert kind in out, kind


def test_the_command_reports_the_pivot_and_the_scale() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "pivot=fixed" in proc.stdout
    assert "scale=(1.05, 1.05)" in proc.stdout


def test_the_command_reports_the_thirty_layers() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--check-pipeline"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "layers: 30" in proc.stdout
```

- [ ] **Step 2: Correr el test y ver que falla**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_check_pipeline_command.py -v
```
Expected: FAIL — `main.py` no reconoce `--check-pipeline` (exit 2, argparse).

- [ ] **Step 3: Escribir el comando**

En `main.py`, junto a `_cmd_check()`:

```python
def _cmd_check_pipeline() -> int:
    """BLOQUE 75: is the enemy pipeline available in THIS build?

    After Phase 2 the runtime reads the enemy manifests every frame to
    draw the enemies. A frozen build that does not carry them falls back
    to the old draw path WITHOUT AN ERROR: the game still runs, the
    enemies still appear, and nothing reports it.

    This command runs INSIDE the frozen build too, so it is the check
    that can answer the question about the .exe the user downloads.
    """
    try:
        from src.anim.clip import load_player_for_kind
        from src.ui.gameplay_layers import LAYER_BODIES
        from src.ui.gameplay_runtime import GameplayRuntime
    except ImportError as exc:
        print(f"VOID HUNTER pipeline check FAIL: {exc}", file=sys.stderr)
        return 1

    kinds = (
        "scout", "cruiser", "drone", "heavy",
        "kamikaze", "sniper", "turret", "mine_asteroid",
    )
    failures: list[str] = []
    print("VOID HUNTER pipeline check")
    for kind in kinds:
        player = load_player_for_kind(kind)
        if player is None:
            failures.append(f"{kind}: the set did not load")
            print(f"  {kind:<14} FAILED to load")
            continue
        anim_set = player.set
        body = next((p for p in anim_set.parts if p.id == "body"), None)
        if body is None:
            failures.append(f"{kind}: no 'body' part")
            print(f"  {kind:<14} FAILED: no body part")
            continue
        clips = len(anim_set.clips)
        print(
            f"  {kind:<14} {clips} clips  "
            f"pivot={body.pivot}  scale={body.scale}"
        )
        if body.pivot != "fixed" or body.scale != (1.05, 1.05):
            failures.append(f"{kind}: pivot={body.pivot} scale={body.scale}")

    missing = [m for m in LAYER_BODIES if not hasattr(GameplayRuntime, m)]
    print(f"  layers: {len(LAYER_BODIES)}  missing methods: {missing or 'none'}")
    if missing:
        failures.append(f"the layer table names methods the runtime lacks: {missing}")

    if failures:
        print("VOID HUNTER pipeline check FAIL:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("VOID HUNTER pipeline check OK")
    return 0
```

Y el flag, junto a `--check` en `_parse_args`:

```python
    parser.add_argument(
        "--check-pipeline", action="store_true",
        help=("BLOQUE 75: report whether the enemy pipeline is available in "
              "THIS build; exit 0 if all eight sets load, 1 if not."),
    )
```

Y el despacho, junto al de `--check` en `main()`:

```python
    if args.check_pipeline:
        return _cmd_check_pipeline()
```

- [ ] **Step 4: Correr el test y ver que pasa**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_check_pipeline_command.py -v
```
Expected: **3 passed**

- [ ] **Step 5: Ver el reporte a mano**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check-pipeline
```
Expected:
```
VOID HUNTER pipeline check
  scout          4 clips  pivot=fixed  scale=(1.05, 1.05)
  ...
  layers: 30  missing methods: none
VOID HUNTER pipeline check OK
```
exit 0.

**El `scale` se imprime como tupla**: `(1.05, 1.05)`. Si el parser devolviera
otra cosa, el test falla y hay que ver por qué.

- [ ] **Step 6: Commit**

```powershell
git add main.py tests/test_check_pipeline_command.py
git commit -m "feat: BLOQUE 75 - el juego reporta si su pipeline de enemigos esta disponible"
```

---

### Task 5: El bump y el build

**Files:**
- Modify: `tools/regen_status.py` (`VERSION`, `BINARY_REL`)
- (no commitea `dist/` — está gitignored)

**Interfaces:**
- Consumes: `build.spec` (PyInstaller onefile)
- Produces: `dist/void-hunter-v1.9.0.exe` en la RAÍZ del repo

- [ ] **Step 1: El bump**

En `tools/regen_status.py`:

```python
BINARY_REL = "dist/void-hunter-v1.9.0.exe"
VERSION = "v1.9.0"
```

- [ ] **Step 2: El build**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m PyInstaller build.spec --noconfirm
```
Expected: `dist/void-hunter.exe` (onefile). **Tarda**: medirlo y reportarlo.

- [ ] **Step 3: Copiar el binario a su nombre de release, en la RAÍZ**

El generador lee el `.exe` desde `REPO_ROOT/dist/`, no desde el worktree:

```powershell
Copy-Item F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port\dist\void-hunter.exe F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe -Force
Get-Item F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe
```

- [ ] **Step 4: Verificar que el bundle lleva los nueve sets**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, r'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port\tools'); from pathlib import Path; from regen_status import _bundle_entries, frozen_assets_verified; e=_bundle_entries(Path(r'F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe')); print('entradas:', len(e)); print('los 9 sets:', frozen_assets_verified(e))"
```
Expected: `los 9 sets: True`

- [ ] **Step 5: El pipeline contra el BINARIO**

```powershell
& F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe --check-pipeline
```
Expected: los ocho sets con `pivot=fixed  scale=(1.05, 1.05)`, `layers: 30`,
`VOID HUNTER pipeline check OK`, exit 0.

**Este es el paso que prueba que el binario público dibuja los enemigos por el
compositor.** Si el bundle no tuviera los manifests, el `.exe` dibujaría los
enemigos por el camino viejo y este comando reportaría el fallo — en vez de
degradar en silencio.

- [ ] **Step 6: `main.py --check` contra el source**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check
```
Expected: `VOID HUNTER check OK`, exit 0

- [ ] **Step 7: Regenerar el bloque STATUS (NO a mano)**

```powershell
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\regen_status.py
git diff -- CLAUDE.md
```
Expected: el diff toca **solo** las filas que el generador posee, con el formato
del generador (el xfail con su sufijo `(fallo conocido)`), y la fila "Build .exe"
con el nombre v1.9.0, el tamaño nuevo y el SHA256.

**Si el diff toca la fila de los tests con un formato que no es el del
generador, es señal de que algo la editó a mano: volver a correr el generador.**

- [ ] **Step 8: Commit**

```powershell
git add tools/regen_status.py CLAUDE.md
git commit -m "build: BLOQUE 75 - la version v1.9.0 y el STATUS regenerado con el binario nuevo"
```

---

### Task 6: Los documentos de la release

**Files:**
- Modify: `docs/changelog/CHANGELOG_v1.x.md`
- Create: `docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md`
- Modify: `.synapse`
- Create: `release-notes-v1.9.0.md` (en la raíz; se sube al release, no se commitea... **o sí**: decidir aquí. Si no se commitea, vive en `%TEMP%` y el release lo consume una vez.)

- [ ] **Step 1: La entrada del changelog**

Plantilla: la entrada `## BLOQUE 75 — El cache del lowpass sobrevive...` (línea
2396 del changelog). Secciones y tono iguales. Contenido:

- **Qué es**: el pipeline de sprites (Fase 1) y el motor de capas del frame (Fase 2).
- **Qué cambia para quien juega**: **nada visual** — cero píxeles movidos, verificado
  con seis goldens; el `.exe` baja/igual de tamaño; el juego arranca igual.
- **Qué cambia para quien desarrolla**: el frame es un stack de 30 capas con `z`
  explícito; los enemigos son datos (pivote y escala en los manifests); el gate de
  la Fase 2 corre en el CI.
- **Cómo se verifica**: los comandos del handoff.

- [ ] **Step 2: El handoff de la release**

`docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md`: qué se publicó, el
número de versión, el SHA256 del binario, cómo se verifica, y **qué NO se hizo**
(el motor sigue en una escena de quince; el `.exe` no se rebuildea por fase; la
Fase 3 no arrancó).

- [ ] **Step 3: El `.synapse`**

Actualizar `current_objective`, `last_successful_action`, `active_context_pointers`
(agregar el handoff de la release) y `critical_blockers` (dejar de dizer que el
gate no está en el CI).

**Cuidado con el BOM**: escribirlo sin BOM, como está el original.

- [ ] **Step 4: Las release notes**

`release-notes-v1.9.0.md`: un párrafo de qué es, uno de qué cambia para quien
juega, uno de cómo se verifica. Sin títulos de markdown (el `gh` no los renderiza).

- [ ] **Step 5: Commit**

```powershell
git add docs/changelog/CHANGELOG_v1.x.md docs/handoffs/HANDOFF-BLOQUE-75-RELEASE-2026-11-04.md .synapse release-notes-v1.9.0.md
git commit -m "docs: BLOQUE 75 - la release v1.9.0: changelog, handoff, synapse y notas"
```

---

### Task 7: El tag, el release y la limpieza

**Files:**
- (no commitea nada: publica)

- [ ] **Step 1: El zip**

```powershell
Compress-Archive -Path F:\AI\MM\void-hunter\dist\void-hunter-v1.9.0.exe -DestinationPath F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip -Force
Get-Item F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip
```
Expected: ~220 MB (el de v1.8.1 fueron 229 MB)

- [ ] **Step 2: Verificar que el árbol está limpio y verde**

```powershell
git status --porcelain
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\ --tb=no --junitxml=$env:TEMP\b75_rel.xml
& F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\gate_ci.py
```
Expected: árbol limpio, **0 fallos**, los dos gates `GATE OK`.

- [ ] **Step 3: El tag anotado**

```powershell
git tag -a v1.9.0 -m "BLOQUE 75: el pipeline de sprites y el motor de capas del frame"
git tag -l "v1.9.0" -n1
```

- [ ] **Step 4: El release**

```powershell
gh release create v1.9.0 F:\AI\MM\void-hunter\dist\VoidHunter-v1.9.0-win64.zip --latest --title "VOID HUNTER v1.9.0 (BLOQUE 75) - el pipeline de sprites y el motor de capas del frame" --notes-file release-notes-v1.9.0.md
```

- [ ] **Step 5: Verificar el release**

```powershell
gh release view v1.9.0 --json tagName,assets,isPrerelease
gh release list --limit 3
```
Expected: el tag `v1.9.0`, un asset `VoidHunter-v1.9.0-win64.zip`, y `v1.9.0`
como **Latest**.

- [ ] **Step 6: Subir la rama**

```powershell
git push origin bloquec-67-goliath-port
```

- [ ] **Step 7: La limpieza**

```powershell
git worktree remove F:\AI\MM\void-hunter\.worktrees\bloquec-75-phase2-layers
git worktree prune
git branch -d bloquec-75-phase2-layers
git worktree list
```
Expected: quedan dos worktrees (la raíz y el de la línea de release).

---

## Self-review del plan

**Cobertura del spec:** §3.1 → Tasks 1 y 2 · §3.2 → Tasks 3, 5 y 7 · §3.3 → Tasks 4,
5 y 6 · §3.4 → Task 7 · §4 (verificación) → los pasos de verificación de cada
tarea · §5 (riesgos) → los pasos "validar antes de mergear" (Task 2) y "verificar
el bundle" (Tasks 3 y 5) · §6 (lo que NO hace) → global.

**Placeholders:** ninguno. Cada paso tiene el comando o el código.

**Consistencia de tipos:** `gate.resolve_base(argument, phase) -> str` (Task 1) lo
consume `gate_ci.run_gate` (Task 1). `regen_status.frozen_assets_verified(entries)
-> bool` (Task 3) lo consume el test de Task 3. `main._cmd_check_pipeline() -> int`
(Task 4) lo consume su test y el paso 5 de Task 5.

**Un defecto encontrado y corregido en el self-review:** la primera versión de
la Task 4 era un script aparte que instrumentaba `LayerStack.render`. **Eso no
puede observar al `.exe`**: el espía vive en el proceso padre y el binario
congelado corre en otro. La pregunta que hay que responder es *"¿este build
puede dibujar los enemigos por el compositor?"*, y la única forma de
responderla **dentro** del binario es que el binario lo reporte. Por eso la
Task 4 es ahora un comando del juego (`--check-pipeline`), que corre igual en el
source y en el `.exe`.

**Consecuencia en el spec:** la sección 4 del spec (`docs/superpowers/specs/
2026-11-04-bloque-75-cierre-de-entrega-design.md`) habla del "probe"; se
actualizó para nombrar el mecanismo real.

