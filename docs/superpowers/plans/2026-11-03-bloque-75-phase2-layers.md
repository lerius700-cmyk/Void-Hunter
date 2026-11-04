# BLOQUE 75 Phase 2 — The layered frame engine: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The gameplay frame is composed by a declarative `LayerStack` (30 ordered layers driven by a `DrawContext`), and the enemy sets are drawn through the sprite pipeline — with **0 differing pixels** against golden frames captured from today's runtime.

**Architecture:** Two checkpoints. **2A** replaces the runtime's ~200-line draw sequence with 30 ordered layers whose bodies are *the drawing code that exists today*, driven by a `DrawContext` that carries the origin, the scale, the clock and the shake. **2B** draws the enemy bodies through the `ClipPlayer` (the pipeline), with the `fixed` pivot and the clip's own scale. The proof in both checkpoints is the same: the golden frames captured by Task 1 must not change by a single pixel.

**Tech Stack:** Python 3.11+, pygame 2.6, `tomllib` (stdlib), pytest. Stdlib + pygame only — no numpy, no new dependency.

**Design:** `docs/superpowers/specs/2026-11-03-bloque-75-phase2-layers-design.md`
**Spec (constraints):** `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md`

---

## Global Constraints

These apply to **every** task. Copy them verbatim into any dispatch brief.

| # | Constraint | Value |
|---|---|---|
| R1 | **Not one PNG byte may change.** The enemy art and GOLIATH's art are user-approved. | `git diff --stat <base>..HEAD -- '*.png'` must be empty, except the ONE line of GOLIATH's `anchors.toml` header in Task 7. |
| R2 | GOLIATH stays the control group | its `manifest.toml` must not change; its `anchors.toml` may change in **exactly one line** (the generated header, Task 7); `verify_contract.py goliath` must still print `CONTRACT OK` and exit 0 |
| R4 | `src/` is stdlib + pygame only | no numpy, no new third-party import |
| R7 | Headless and deterministic | no wall clock, no network, no AI in `src/` or in the harness |
| L1 | No multi-line inline table in any TOML | every inline table stays on ONE line |
| L5 | Narrow `except` | never a bare `except:`; catch `(OSError, ValueError)` |
| L7 | The tests never write into the repository | anything that runs the pipeline does it on a `tmp_path` copy |
| — | **The internal resolution stays 320×480** | `src/core/settings.py::INTERNAL_W/INTERNAL_H`; the window scaling stays in `Game._present()` |
| — | **The baseline** | `python -m pytest tests\ --tb=no` → **0 failed**. On this branch the suite collects **3 038** tests (3 031 passed + 6 skipped + 1 xfailed). **Treat the count as a DELTA, not an absolute number:** each task adds its own tests, and an absolute count breaks the moment another agent adds one. (The Phase 1 plan shipped with "3 036 passed" — that number was the suite's TOTAL, not its passed count; the implementer of Task 2 caught it.) |
| — | pytest output | pytest 9.1.1 omits the final counts line on a full-suite run: use `--junitxml=<path in %TEMP%>` and read the totals from the XML, or run with `-v`. Report real numbers. |
| — | mypy | **The SYSTEM python has no mypy — but the PROJECT's venv does: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe` ships mypy 2.4.0.** That is the interpreter the repo's own gate uses (`docs/handoffs/HANDOFF-BLOQUE-75-2026-11-02.md:87`). Run the gate with it: `& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\render\` (and `… -m mypy src\anim\` — the documented gate, currently green). **Install nothing.** Measured at `39f5113`: `mypy src/anim/` → 0 errors in 6 files; `mypy src/render/` → 0 errors in 2 files. (Note: `mypy src/` is NOT clean — 182 pre-existing errors, all in `src/ui/` and `src/core/`, identical before and after this phase.) |
| — | Windows / PowerShell 5.1 | no `&&`, no `ls -la`, no `head`/`tail`/`grep`. **There is NO Git Bash** (the `bash.exe` on PATH is the WSL launcher). |
| — | Line endings | the repo's `.py` files are CRLF, no BOM. The generated `.toml` files are LF (`.gitattributes`: `*.toml text eol=lf`). |
| — | Commits | one per task, message given in the task, explicit paths only (`git add <paths>`, never `-A`) |
| — | Branch | `bloquec-75-phase2-layers`, based on `bloquec-67-goliath-port` @ `e619527`. Never `master`. |

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `tools/capture/layerstack_frames.py` | create | the deterministic golden-frame harness: builds the scene, ticks it with a fixed `dt`, scripted input, writes the internal 320×480 frame |
| `tools/golden/layerstack/*.png` | create, committed | the reference frames — the proof itself. Five frames. |
| `src/render/__init__.py` | create | the package |
| `src/render/layer.py` | create | `DrawContext`, `Layer`, `LayerStack` — generic, stdlib + pygame, **no imports from `src/ui/` or `src/entities/`** |
| `src/ui/gameplay_layers.py` | create | `build_layers(rt) -> LayerStack` — the 30 layers in the measured order |
| `src/ui/gameplay_runtime.py` | modify | `draw()` builds the context and calls the stack; the inline draw blocks become `_draw_*` methods |
| `src/anim/parts.py` | modify | `_base()` honours `pivot == "fixed"` |
| `src/anim/clip.py` | modify | the frames part is scaled by `Part.scale` and cached scaled; the CLIP's canvas reaches `draw_part` |
| `src/anim/manifest.py` | modify | `mode`/`on_end` are enforced; the sets root knows `enemies` |
| `Assets/sprites/enemies/*/manifest.toml` | modify | the body part declares `scale = [1.05, 1.05]` |
| `Assets/sprites/enemies/*/anchors.toml` | regenerate | the manifest hash changes; the generated header names the gate |
| `Assets/sprites/bosses/goliath/anchors.toml` | regenerate | **one line**: the generated header |
| `tools/sprite_pipeline/audit.py` | modify | the generated header names the gate, not a test file |
| `tools/sprite_pipeline/run.py`, `audit.py` | modify | the CLIs resolve a set through `sprite_pipeline.sets` |
| `tools/sprite_pipeline/gate.py` | modify | the Phase 2 gate checks |
| `tests/test_layer_stack_order.py` | create | the layer ids and their `z` |
| `tests/test_layer_stack_renders_identical_frames.py` | create | the pixel comparison |
| `tests/test_layer_stack_context.py` | create | the context |
| `tests/test_fixed_pivot.py` | create | the pivot |
| `tests/test_enemy_scale_matches_runtime.py` | create | the enemy scale |

---

### Task 1: The deterministic golden-frame harness

The golden frames are the whole proof. They are only worth something if the
capture is **reproducible**: the runtime uses the GLOBAL `random` module in 31
screen-affecting places and seeds only `_asteroid_rng`, so a naive capture
drifts and a golden frame that moves looks like a regression — or hides one.

**Files:**
- Create: `tools/capture/layerstack_frames.py`
- Create: `tools/golden/layerstack/*.png` (5 files, generated)
- Create: `tests/test_golden_frames_are_deterministic.py`

**Interfaces:**
- Consumes: `GameplayRuntime(transition_to, is_boss=False, act=1, audio=None)`
  (`src/ui/gameplay_runtime.py:3222`), `GameplayRuntime.update(dt)`,
  `GameplayRuntime.draw(target)`, `src.core.settings.INTERNAL_W/INTERNAL_H`
- Produces: `python tools\capture\layerstack_frames.py --out <dir>` writes the
  five frames; `python tools\capture\layerstack_frames.py --check` verifies that
  two captures of the same frame are byte-identical and exits 1 if they are not

- [ ] **Step 1: Write the failing test**

Create `tests/test_golden_frames_are_deterministic.py`:

```python
"""BLOQUE 75 Fase 2: the golden frames must be reproducible.

The runtime uses the GLOBAL `random` module in 31 screen-affecting places and
seeds only `_asteroid_rng`. A capture that is not reproducible makes the
pixel comparison meaningless: a golden frame that drifts looks like a
regression, and a real regression can hide behind the drift.

This test captures the SAME frame twice and requires the two PNGs to be
byte-identical.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HARNESS), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )


def test_the_harness_exists():
    assert HARNESS.is_file(), HARNESS


def test_two_captures_of_the_same_frame_are_byte_identical(tmp_path):
    """The determinism self-check: capture twice, compare the bytes."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    for target in (first, second):
        proc = _run("--out", str(target), "--only", "enemies")
        assert proc.returncode == 0, proc.stdout + proc.stderr
    digests = {}
    for target in (first, second):
        for png in sorted(target.glob("*.png")):
            digests.setdefault(png.name, []).append(
                hashlib.md5(png.read_bytes()).hexdigest()
            )
    assert digests, "the harness wrote no frames"
    for name, hashes in digests.items():
        assert hashes[0] == hashes[1], (
            f"{name} is not reproducible: {hashes[0]} != {hashes[1]}"
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_golden_frames_are_deterministic.py -v`

Expected: **FAIL** — `AssertionError` on `HARNESS.is_file()` (the harness does not exist yet).

- [ ] **Step 3: Write the harness**

Create `tools/capture/layerstack_frames.py`:

```python
"""BLOQUE 75 Fase 2: the deterministic golden-frame harness.

The golden frames are the proof that the LayerStack changed NOTHING. That
proof is only worth something if the capture is reproducible, so this
harness is built to be reproducible by construction:

  * the GLOBAL `random` module is seeded before the scene is built -- the
    runtime uses it in 31 screen-affecting places and seeds only
    `_asteroid_rng`;
  * the scene is REBUILT for every capture (a reused scene keeps its RNG
    state and its entity positions);
  * time advances by a FIXED dt, never by the wall clock;
  * the input is scripted through `pygame.key.set_pressed` /
    `pygame.mouse.set_pressed`, the same channels the runtime reads
    (`GameplayRuntime._read_input`, gameplay_runtime.py:765-785).

Usage:
    python tools/capture/layerstack_frames.py --out tools/golden/layerstack
    python tools/capture/layerstack_frames.py --check
"""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import hashlib
import random
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.settings import INTERNAL_H, INTERNAL_W  # noqa: E402
from src.ui.gameplay_runtime import GameplayRuntime  # noqa: E402

SEED = 20261103
DT = 1.0 / 60.0

# The five frames the proof needs: enemies on screen, the boss, the mine in
# its open3 state, the player firing, and the HUD populated.
FRAMES: tuple[tuple[str, int, tuple[int, ...]], ...] = (
    ("enemies", 180, (pygame.K_LEFT, pygame.K_a)),
    ("boss", 240, (pygame.K_RIGHT,)),
    ("mine_open", 300, (pygame.K_UP, pygame.K_a)),
    ("firing", 360, (pygame.K_a,)),
    ("hud", 420, (pygame.K_d,)),
)


def _build_scene() -> GameplayRuntime:
    """A fresh gameplay runtime, with the global RNG seeded.

    `transition_to` is a no-op: the harness never leaves the scene.
    `audio=None` keeps the runtime muted, so no sound device is needed.
    """
    random.seed(SEED)
    pygame.event.clear()
    return GameplayRuntime(lambda *args, **kwargs: None, is_boss=False, act=1, audio=None)


def _press(keys: tuple[int, ...]) -> None:
    pygame.key.set_pressed(list(keys))


def _release() -> None:
    pygame.key.set_pressed([])


def capture(out_dir: Path, only: str | None = None) -> dict[str, str]:
    """Capture the frames and return {name: md5}."""
    pygame.init()
    pygame.display.set_mode((INTERNAL_W, INTERNAL_H))
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    for name, ticks, keys in FRAMES:
        if only is not None and only != name:
            continue
        scene = _build_scene()
        target = pygame.Surface((INTERNAL_W, INTERNAL_H))
        for tick in range(ticks):
            _press(keys)
            scene.update(DT)
            _release()
            if tick == ticks - 1:
                scene.draw(target)
        path = out_dir / f"{name}.png"
        pygame.image.save(target, str(path))
        digests[name] = hashlib.md5(path.read_bytes()).hexdigest()
    return digests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "tools" / "golden" / "layerstack")
    parser.add_argument("--only", default=None, help="capture a single frame by name")
    parser.add_argument(
        "--check",
        action="store_true",
        help="capture twice and fail if the bytes differ",
    )
    args = parser.parse_args()

    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            first = capture(Path(tmp) / "first", args.only)
            second = capture(Path(tmp) / "second", args.only)
        drifted = {k: (first[k], second[k]) for k in first if first[k] != second[k]}
        if drifted:
            print("NOT REPRODUCIBLE:")
            for name, (a, b) in drifted.items():
                print(f"  {name}: {a} != {b}")
            return 1
        print("REPRODUCIBLE:", ", ".join(sorted(first)))
        return 0

    digests = capture(args.out, args.only)
    for name, digest in sorted(digests.items()):
        print(f"{name}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the harness to see whether it is reproducible**

Run: `python tools\capture\layerstack_frames.py --check`

Expected: **`REPRODUCIBLE: boss, enemies, firing, hud, mine_open`**, exit 0.

**If it prints `NOT REPRODUCIBLE`:** something is still reading the wall clock
or an unseeded source of randomness. Find it, seed it or make it a fixed
value, and re-run. **Do not proceed until the harness is reproducible** — a
golden frame that drifts makes every later check meaningless.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_golden_frames_are_deterministic.py -v`

Expected: **2 passed**

- [ ] **Step 6: Capture and commit the golden frames**

```powershell
python tools\capture\layerstack_frames.py --out tools\golden\layerstack
```

Expected: five md5 digests printed, and five PNGs in `tools/golden/layerstack/`.

Then commit the harness, the frames and the test:

```powershell
git add tools/capture/layerstack_frames.py tools/golden/layerstack tests/test_golden_frames_are_deterministic.py
git commit -m "test: BLOQUE 75 - el arnes de golden frames es reproducible: el frame de hoy, capturado"
```

- [ ] **Step 7: Prove the frames are not empty**

Run: `python -c "import pygame;from pathlib import Path;ps=sorted(Path('tools/golden/layerstack').glob('*.png'));[print(p.name, pygame.image.load(str(p)).get_size(), pygame.image.load(str(p)).get_at((10,10))) for p in ps]"`

Expected: every frame is `(320, 480)` and the pixels are not all transparent
(a fully blank frame would make the whole proof vacuous). If a frame is blank,
change that frame's tick count or its scripted keys so the scene has something
in it, then re-capture and re-commit.

---

### Task 2: The engine — `src/render/layer.py`

**Files:**
- Create: `src/render/__init__.py`
- Create: `src/render/layer.py`
- Test: `tests/test_layer_stack_context.py`

**Interfaces:**
- Produces:
  - `class DrawContext` (frozen dataclass) with fields `target: pygame.Surface`,
    `origin: tuple[float, float]`, `scale: float`, `time: float`,
    `shake: tuple[int, int]`, `size: tuple[int, int]`, the method
    `with_origin(x: float, y: float) -> DrawContext` and the method
    `at(x: float, y: float) -> tuple[int, int]`
  - `class Layer` (frozen dataclass) with fields `id: str`, `z: int`,
    `draw: Callable[[pygame.Surface, DrawContext], None]`
  - `class LayerStack` with `__init__(layers: Sequence[Layer])`,
    the property `layers -> tuple[Layer, ...]` and
    `render(ctx: DrawContext) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_layer_stack_context.py`:

```python
"""BLOQUE 75 Fase 2: the frame engine.

The engine is generic: it knows about layers, an order and a context, and
NOTHING about the game. That boundary is what keeps the mypy gate clean
(L6): `src/render/` must not import `src/ui/` or `src/entities/`.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.render.layer import DrawContext, Layer, LayerStack


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _ctx(**kwargs) -> DrawContext:
    base = {
        "target": pygame.Surface((320, 480)),
        "origin": (160.0, 240.0),
        "scale": 1.0,
        "time": 0.0,
        "shake": (0, 0),
        "size": (320, 480),
    }
    base.update(kwargs)
    return DrawContext(**base)


def test_the_stack_renders_in_z_order(display):
    calls: list[str] = []
    stack = LayerStack(
        [
            Layer(id="second", z=5, draw=lambda t, c: calls.append("second")),
            Layer(id="first", z=1, draw=lambda t, c: calls.append("first")),
        ]
    )
    stack.render(_ctx())
    assert calls == ["first", "second"]


def test_the_stack_is_stable_for_equal_z(display):
    calls: list[str] = []
    stack = LayerStack(
        [
            Layer(id="a", z=1, draw=lambda t, c: calls.append("a")),
            Layer(id="b", z=1, draw=lambda t, c: calls.append("b")),
        ]
    )
    stack.render(_ctx())
    assert calls == ["a", "b"]


def test_the_context_keeps_the_internal_resolution(display):
    ctx = _ctx()
    assert ctx.size == (320, 480)
    assert ctx.scale == 1.0


def test_with_origin_moves_the_origin_without_mutating_the_original(display):
    ctx = _ctx()
    moved = ctx.with_origin(10.0, 20.0)
    assert moved.origin == (10.0, 20.0)
    assert ctx.origin == (160.0, 240.0)
    assert moved.shake == ctx.shake
    assert moved.target is ctx.target


def test_at_adds_the_shake_once(display):
    ctx = _ctx(shake=(3, -4))
    assert ctx.at(10.0, 20.0) == (13, 16)


def test_the_render_package_does_not_import_the_game(display):
    """L6: `src/render/` must not depend on `src/ui/` or `src/entities/`."""
    source = (ROOT / "src" / "render" / "layer.py").read_text(encoding="utf-8")
    for forbidden in ("src.ui", "src.entities", "src.anim"):
        assert forbidden not in source, f"{forbidden} must not be imported by src/render/"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_layer_stack_context.py -v`

Expected: **FAIL** — `ModuleNotFoundError: No module named 'src.render'`

- [ ] **Step 3: Write the engine**

Create `src/render/__init__.py`:

```python
"""BLOQUE 75: the layered frame engine.

Generic: it knows about layers, an order and a context -- and nothing about
the game. The game-specific layers live in `src/ui/gameplay_layers.py`.
"""
```

Create `src/render/layer.py`:

```python
"""BLOQUE 75: the layered frame engine.

Three objects:

  * `DrawContext` -- WHERE and WHEN a layer draws: the target surface, the
    world point at the target's centre, the uniform scale, the scene clock,
    the screen shake and the target size. The internal resolution is fixed
    at 320x480; the window scaling happens in `Game._present()`, never
    here.
  * `Layer` -- ONE draw operation: an id, a `z` (the global order) and the
    draw body. The body is the drawing code that already exists.
  * `LayerStack` -- the ordered set of layers that compose one frame.

This module is generic on purpose: it imports stdlib and pygame and
NOTHING from the game. That keeps the mypy gate over `src/anim/` clean
(L6) and makes the engine reusable by another scene later.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Sequence

import pygame


@dataclass(frozen=True)
class DrawContext:
    """Everything a layer needs to know about WHERE and WHEN it draws."""

    target: pygame.Surface
    origin: tuple[float, float]
    scale: float
    time: float
    shake: tuple[int, int]
    size: tuple[int, int]

    def with_origin(self, x: float, y: float) -> "DrawContext":
        """A copy whose origin is another world point.

        The procedural fallback draws into a scratch surface centred on the
        entity: the scratch is 64x64 (player), 48x48 (enemy) or 64x64
        (sub-boss), and the current code computes
        `offset = scratch_size // 2 - entity_pos` per entity
        (gameplay_runtime.py:5351-5353). `with_origin` replaces that
        arithmetic: the layer asks for a context centred on the entity and
        the scratch draw becomes ordinary code.
        """
        return replace(self, origin=(x, y))

    def at(self, x: float, y: float) -> tuple[int, int]:
        """A world position mapped to screen pixels, shake included.

        The shake is added HERE and nowhere else: the old code passed
        `(target, shx, shy)` to every draw call.
        """
        return (int(x) + self.shake[0], int(y) + self.shake[1])


@dataclass(frozen=True)
class Layer:
    """One draw operation of the frame."""

    id: str
    z: int
    draw: Callable[[pygame.Surface, DrawContext], None]


class LayerStack:
    """The ordered set of layers that compose one frame.

    The stack owns the ORDER and nothing else: it never draws a layer
    itself, never mutates a layer and never reorders at runtime. The order
    is fixed at build time and asserted by `tests/test_layer_stack_order.py`.
    """

    def __init__(self, layers: Sequence[Layer]) -> None:
        self._layers = tuple(sorted(layers, key=lambda layer: layer.z))

    @property
    def layers(self) -> tuple[Layer, ...]:
        return self._layers

    def render(self, ctx: DrawContext) -> None:
        for layer in self._layers:
            layer.draw(ctx.target, ctx)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_layer_stack_context.py -v`

Expected: **6 passed**

- [ ] **Step 5: Commit**

```powershell
git add src/render/__init__.py src/render/layer.py tests/test_layer_stack_context.py
git commit -m "feat: BLOQUE 75 - el motor de capas: Layer, LayerStack y DrawContext"
```

---

### Task 3: The 30 layers, and the runtime's inline blocks become methods

**Files:**
- Create: `src/ui/gameplay_layers.py`
- Modify: `src/ui/gameplay_runtime.py` (the inline draw blocks become `_draw_*` methods)
- Test: `tests/test_layer_stack_order.py`

**Interfaces:**
- Consumes: `src.render.layer.Layer`, `LayerStack`, `DrawContext` (Task 2)
- Produces: `build_layers(rt: GameplayRuntime) -> LayerStack` in
  `src/ui/gameplay_layers.py`, with the 30 layers in the table below

**The bridge, stated once.** The layer bodies call the runtime's draw
helpers. Some of them are `_`-prefixed today (`rt._draw_ambient_dust`) and some
are INLINE blocks inside `GameplayRuntime.draw()` right now — those become
`_draw_*` methods on the runtime in this task. `gameplay_layers.py` reaches
into the runtime's private draw helpers **on purpose**: the alternative (30
public wrappers) is bloat, and moving the bodies out of the runtime breaks
encapsulation the other way. Splitting the 6 750-line runtime is another
BLOQUE.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layer_stack_order.py`:

```python
"""BLOQUE 75 Fase 2: the layer order is DATA, not code.

The order the frame used to be drawn in is now a list of layers with a
`z`. This test pins it: a layer moved by accident changes the frame, and
the golden frames would catch the pixels -- but only if the ids and their
order are pinned here too.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPECTED = (
    "ambient_dust",
    "player_damage_flash",
    "powerups",
    "enemies",
    "asteroids_and_powerups",
    "leader_glows",
    "boss",
    "boss_spears",
    "shield_laser",
    "shockwaves",
    "bomb_bursts",
    "bullets",
    "missiles",
    "tron_trail",
    "player_afterimage",
    "player",
    "continuous_laser",
    "reticle",
    "bomb_flash",
    "particles",
    "score_popups",
    "wave_indicator",
    "play_area_frame",
    "hud",
    "pattern_banner",
    "screen_flash",
    "charge_release_flash",
    "pickup_flash",
    "level_up_flash",
    "speed_lines",
)


@pytest.fixture(scope="module")
def display():
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_the_layer_order_is_pinned(display):
    from src.ui.gameplay_layers import build_layers
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    stack = build_layers(runtime)
    assert tuple(layer.id for layer in stack.layers) == EXPECTED
    assert tuple(layer.z for layer in stack.layers) == tuple(range(len(EXPECTED)))


def test_every_layer_calls_a_method_that_exists(display):
    """A renamed runtime method must break here, not silently."""
    from src.ui.gameplay_layers import LAYER_BODIES
    from src.ui.gameplay_runtime import GameplayRuntime

    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    for method_name in LAYER_BODIES:
        assert hasattr(runtime, method_name), method_name
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_layer_stack_order.py -v`

Expected: **FAIL** — `ModuleNotFoundError: No module named 'src.ui.gameplay_layers'`

- [ ] **Step 3: Extract the runtime's inline draw blocks into methods**

In `src/ui/gameplay_runtime.py`, `GameplayRuntime.draw()` currently contains
the ~200-line draw sequence. In this task, **only** the INLINE blocks become
named methods (a pure extraction, no behaviour change):

| the inline block today | becomes |
|---|---|
| the full-screen red player-damage flash | `_draw_player_damage_flash(target)` |
| the powerups loop | `_draw_powerup_pass(target)` |
| the enemies loop | `_draw_enemy_pass(target)` |
| the boss spears loop | `_draw_boss_spear_pass(target)` |
| the shockwaves loop | `_draw_shockwave_pass(target)` |
| the bomb bursts loop | `_draw_bomb_burst_pass(target)` |
| the full-screen white bomb flash | `_draw_bomb_flash(target)` |
| the pattern banner | `_draw_pattern_banner(target)` |
| the four full-screen flashes (screen / charge release / pickup / level up) | `_draw_screen_flashes(target)` |

Every method body is the block **verbatim** — same order, same conditions,
same values. The methods take `target` only; the shake is applied inside them
exactly as it is today (this task does NOT change how the shake reaches the
draws — that is Task 4's job).

- [ ] **Step 4: Write the layer factory**

Create `src/ui/gameplay_layers.py`:

```python
"""BLOQUE 75 Fase 2: the gameplay frame as an ordered list of layers.

The order the frame used to be drawn in is now DATA: thirty layers, each
with a `z`, each calling the drawing code that already exists. Nothing is
moved OUT of the runtime -- the bodies stay there -- so this module is an
ORDER, not a rewrite.

The bridge is deliberate: the layer bodies call the runtime's draw
helpers, including the `_`-prefixed ones. Splitting the 6 750-line runtime
into focused modules is another BLOQUE; until then, the order lives here
and the bodies live there.
"""
from __future__ import annotations

from src.render.layer import DrawContext, Layer, LayerStack

# The runtime method each layer calls. Exported so the order test can
# assert that every one of them still exists.
LAYER_BODIES: tuple[str, ...] = (
    "_draw_ambient_dust",
    "_draw_player_damage_flash",
    "_draw_powerup_pass",
    "_draw_enemy_pass",
    "_draw_asteroids_and_powerups",
    "_draw_leader_glows",
    "_draw_boss",
    "_draw_boss_spear_pass",
    "_draw_shield_laser",
    "_draw_shockwave_pass",
    "_draw_bomb_burst_pass",
    "_draw_bullets_with_glow",
    "_draw_missiles",
    "_draw_tron_trail",
    "_draw_player_afterimage",
    "_draw_player_scaled",
    "_draw_continuous_laser",
    "_draw_reticle",
    "_draw_bomb_flash",
    "_draw_particles",
    "_draw_score_popups",
    "_draw_wave_indicator",
    "_draw_play_area_frame",
    "_draw_hud",
    "_draw_pattern_banner",
    "_draw_screen_flashes",
    "_draw_speed_lines",
)

# (layer id, runtime method, z)
_LAYERS: tuple[tuple[str, str, int], ...] = (
    ("ambient_dust", "_draw_ambient_dust", 0),
    ("player_damage_flash", "_draw_player_damage_flash", 1),
    ("powerups", "_draw_powerup_pass", 2),
    ("enemies", "_draw_enemy_pass", 3),
    ("asteroids_and_powerups", "_draw_asteroids_and_powerups", 4),
    ("leader_glows", "_draw_leader_glows", 5),
    ("boss", "_draw_boss", 6),
    ("boss_spears", "_draw_boss_spear_pass", 7),
    ("shield_laser", "_draw_shield_laser", 8),
    ("shockwaves", "_draw_shockwave_pass", 9),
    ("bomb_bursts", "_draw_bomb_burst_pass", 10),
    ("bullets", "_draw_bullets_with_glow", 11),
    ("missiles", "_draw_missiles", 12),
    ("tron_trail", "_draw_tron_trail", 13),
    ("player_afterimage", "_draw_player_afterimage", 14),
    ("player", "_draw_player_scaled", 15),
    ("continuous_laser", "_draw_continuous_laser", 16),
    ("reticle", "_draw_reticle", 17),
    ("bomb_flash", "_draw_bomb_flash", 18),
    ("particles", "_draw_particles", 19),
    ("score_popups", "_draw_score_popups", 20),
    ("wave_indicator", "_draw_wave_indicator", 21),
    ("play_area_frame", "_draw_play_area_frame", 22),
    ("hud", "_draw_hud", 23),
    ("pattern_banner", "_draw_pattern_banner", 24),
    ("screen_flash", "_draw_screen_flashes", 25),
    ("charge_release_flash", "_draw_screen_flashes", 26),
    ("pickup_flash", "_draw_screen_flashes", 27),
    ("level_up_flash", "_draw_screen_flashes", 28),
    ("speed_lines", "_draw_speed_lines", 29),
)


def build_layers(rt) -> LayerStack:
    """The thirty layers of the gameplay frame, in the measured order.

    `rt` is the `GameplayRuntime`. Each layer calls one of its draw
    helpers; the helpers are the code that exists today.
    """
    layers = []
    for layer_id, method_name, z in _LAYERS:
        method = getattr(rt, method_name)
        layers.append(
            Layer(
                id=layer_id,
                z=z,
                draw=lambda target, ctx, _method=method: _method(target),
            )
        )
    return LayerStack(layers)
```

**Note the four screen flashes**: they share ONE runtime method
(`_draw_screen_flashes`) but are FOUR layers, because the old code drew them
at four different points in the sequence. The runtime method must therefore
draw only the flash that belongs to the layer it serves — split it into four
methods (`_draw_screen_flash`, `_draw_charge_release_flash`,
`_draw_pickup_flash`, `_draw_level_up_flash`) so each layer draws its own.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_layer_stack_order.py -v`

Expected: **2 passed**

- [ ] **Step 6: Commit**

```powershell
git add src/ui/gameplay_layers.py src/ui/gameplay_runtime.py tests/test_layer_stack_order.py
git commit -m "refactor: BLOQUE 75 - los bloques de dibujo del runtime pasan a metodos y el orden pasa a ser una lista de capas"
```

---

### Task 4: Checkpoint 2A — the frame loop uses the stack, and not one pixel moves

**Files:**
- Modify: `src/ui/gameplay_runtime.py` (`draw()` builds the context and renders the stack)
- Test: `tests/test_layer_stack_renders_identical_frames.py`

**Interfaces:**
- Consumes: `build_layers(rt)` (Task 3), `DrawContext` (Task 2)
- Produces: `GameplayRuntime.draw(target)` renders through the stack

- [ ] **Step 1: Write the failing test**

Create `tests/test_layer_stack_renders_identical_frames.py`:

```python
"""BLOQUE 75 Fase 2: the proof. The frame must not change by a pixel.

The golden frames were captured from the runtime BEFORE the LayerStack
existed (Task 1). After the refactor, every one of them must be
PIXEL-IDENTICAL. This is the only thing that proves checkpoint 2A: the
frame loop was reorganised into layers without changing what is drawn.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tools" / "golden" / "layerstack"
HARNESS = ROOT / "tools" / "capture" / "layerstack_frames.py"


@pytest.mark.parametrize(
    "name",
    ("enemies", "boss", "mine_open", "firing", "hud"),
)
def test_the_frame_is_pixel_identical(tmp_path, name):
    if not (GOLDEN / f"{name}.png").is_file():
        pytest.skip(f"no golden frame for {name}")
    proc = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--out",
            str(tmp_path),
            "--only",
            name,
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    golden = pygame_pixels(GOLDEN / f"{name}.png")
    current = pygame_pixels(tmp_path / f"{name}.png")
    assert golden == current, (
        f"{name}: the frame changed -- "
        f"{sum(1 for a, b in zip(golden, current) if a != b)} differing pixels"
    )


def pygame_pixels(path: Path):
    """The frame's pixels as a flat tuple of RGB triples."""
    import pygame

    surf = pygame.image.load(str(path)).convert_alpha()
    return tuple(surf.get_at((x, y))[:3] for y in range(surf.get_height())
                 for x in range(surf.get_width()))
```

- [ ] **Step 2: Run the test — it must FAIL before the change**

Run: `python -m pytest tests/test_layer_stack_renders_identical_frames.py -v`

Expected: **PASS** — because the runtime has not been changed yet, the frame
is still the old one and it still matches the golden. **That is the point:**
this test is the proof, and it must be green BEFORE and AFTER. If it fails
now, the golden frames are stale: re-capture them and commit that separately
before touching the runtime.

- [ ] **Step 2b: Capture a sixth golden frame WITH a non-zero shake**

The five golden scenes all have an **integer shake of (0, 0)** — the shake
truncates to zero in every one of them — so the golden set as it stands never
exercises the layers that consume the shake. A regression in the shake
plumbing would leave all five frames identical and the phase's proof would
not notice.

The Task 1 review proved the gap and the fix: forcing the runtime's screen
trauma so the integer shake is non-zero yields **0 differing pixels** between
the inline frame and the stack path (with shake `(8, 8)`), i.e. the stack
handles the shake correctly. But that was a throwaway experiment — the
committed golden set does not cover it.

So, BEFORE touching the runtime, capture a sixth frame with the shake forced:

1. Add a `--shake` flag to `tools/capture/layerstack_frames.py` that sets the
   runtime's screen trauma so the integer shake is non-zero. Read the
   runtime's own shake code for the exact attribute names; the Task 1 review
   used `trauma = 1.0` with the noise offsets set to `1.0`, which produced
   the integer shake `(8, 8)`.
2. Add a `shake` entry to the harness's `FRAMES` table, captured at a tick
   where something is on screen (the same tick discipline as the others: the
   scene is built, ticked, and rendered exactly ONCE — a draw MUTATES the
   scene: `_draw_engine_flame` emits a spark with `random.random()` during
   the draw).
3. Capture it and commit it with the others:
   ```powershell
   python tools\capture\layerstack_frames.py --out tools\golden\layerstack
   ```
4. Add the sixth name to the parametrized list in
   `tests/test_layer_stack_renders_identical_frames.py` (Step 1 above).

- [ ] **Step 3: Make the frame loop use the stack**

In `src/ui/gameplay_runtime.py`:

1. Add to `GameplayRuntime.__init__`:
   ```python
   self._layers = build_layers(self)
   ```
   with `from src.ui.gameplay_layers import build_layers` at the top of the
   module. **Build it AFTER the constructor has created everything the layers
   touch** (the player, the entity lists) — place the assignment at the END of
   `__init__`.

2. Replace the ~200-line draw sequence in `draw()` with:
   ```python
   ctx = DrawContext(
       target=target,
       origin=(INTERNAL_W / 2, INTERNAL_H / 2),
       scale=1.0,
       time=self._t,
       shake=(shx, shy),
       size=(INTERNAL_W, INTERNAL_H),
   )
   self._layers.render(ctx)
   ```
   with `from src.render.layer import DrawContext` at the top, and
   `INTERNAL_W, INTERNAL_H` from `src.core.settings`.

3. The background (the parallax + the galaxy strip) stays OUTSIDE the stack,
   exactly where it is today — it is drawn before the stack renders. The
   design calls it "the stack's backdrop".

**The factory's type contract.** `src/ui/gameplay_layers.py:112` currently
declares `build_layers(rt: Any)`, because importing `GameplayRuntime` there
would create a cycle (the runtime imports the layers module). `Any` means the
module no longer type-checks the runtime's shape. Replace it with a
`Protocol` in `src/ui/gameplay_layers.py` — the layer factory only needs the
draw helpers, so the protocol can declare just those:

```python
class _RuntimeLike(Protocol):
    """What the layer factory needs from the runtime.

    A Protocol instead of `GameplayRuntime`: importing the runtime here
    would be a cycle (the runtime imports this module), and `Any` would
    stop type-checking the shape entirely.
    """
```

Give it the members the factory actually calls, and type
`build_layers(rt: _RuntimeLike) -> LayerStack`. The runtime satisfies the
protocol structurally — no import, no cycle, and the contract is checked.

**The shake.** The old code passed `(shx, shy)` to each draw helper. The new
code has the shake in the context. In this task the helpers keep their
current signatures (`target` only) and the runtime keeps computing `shx, shy`
the same way — the helpers that need the shake read it from the context in
Task 8's refactor, NOT here. **To keep checkpoint 2A honest, the helpers
that take `shx, shy` today keep taking them in this task**: the layer bodies
pass `ctx.shake` into them:
   ```python
   draw=lambda target, ctx, _method=method: _method(target, ctx.shake[0], ctx.shake[1])
   ```
   for the helpers whose signature is `(target, shx, shy)`, and
   ```python
   draw=lambda target, ctx, _method=method: _method(target)
   ```
   for the ones that take only `target`. **The two forms must match the
   helper's real signature** — check each one in the runtime before writing
   the lambda. This is why the layer factory needs one lambda per helper,
   not one generic one.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_layer_stack_renders_identical_frames.py -v`

Expected: **5 passed** — and if any frame differs, the message says how many
pixels moved. **Do not adjust the golden frames to make it pass**: a
difference means the refactor changed the picture, and that is a defect to
find, not to paper over.

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest tests\ --tb=no --junitxml=%TEMP%\b75_p2a.xml`

Expected: **0 failed**, 3 036 + the new tests passed, 7 skipped.

- [ ] **Step 6: Commit**

```powershell
git add src/ui/gameplay_runtime.py tests/test_layer_stack_renders_identical_frames.py
git commit -m "refactor: BLOQUE 75 - el frame se compone con el LayerStack: 30 capas, 0 pixeles movidos"
```

---

### Task 5: The `fixed` pivot

**Files:**
- Modify: `src/anim/parts.py` (`_base()`)
- Test: `tests/test_fixed_pivot.py`

**Interfaces:**
- Consumes: `Part.pivot` (already parsed: `"centroid"`, `"detect"` or `"fixed"`),
  `FrameAnchor.body_dx/body_dy`
- Produces: `parts._base(origin, canvas, anchor, part)` applies the anchor
  offset ONLY when the pivot is not `"fixed"`

- [ ] **Step 1: Write the failing test**

Create `tests/test_fixed_pivot.py`:

```python
"""BLOQUE 75 Fase 2: a `fixed` pivot means "do not apply the correction".

`pivot = "fixed"` is what the enemy sets declare: the sprite is blitted
CENTRED on the entity, exactly as the runtime does today. The measured
registration is recorded in the anchors table, but applying it would move
the ship up to 3.7 px off its hitbox -- and the golden frames would catch
it.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.anchors import FrameAnchor
from src.anim.parts import _base
from src.anim.manifest import Part


def _part(pivot: str) -> Part:
    """A `Part` with every required field filled.

    `Part` has NINE required fields and no defaults, so a short
    `Part(id=..., draw=..., pivot=..., z=0)` raises TypeError. Building it
    through a helper keeps the test readable without touching
    `src/anim/manifest.py` (which is not this task's file).
    """
    return Part(
        id="body",
        draw="frames",
        pivot=pivot,
        z=0,
        offset=(0.0, 0.0),
        scale=(1.0, 1.0),
        radii=(),
        detect=None,
        on_missing="interpolate",
    )


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def _anchor(dx: int, dy: int) -> FrameAnchor:
    return FrameAnchor(
        body_dx=dx,
        body_dy=dy,
        eye=None,
        eye_source="missing",
        shield=None,
        shield_source="missing",
    )


def test_a_centroid_pivot_applies_the_correction():
    part = _part("centroid")
    x, y = _base((100, 100), (32, 32), _anchor(3, -2), part)
    # 100 - 32//2 + 3, 100 - 32//2 - 2
    assert (x, y) == (87, 82)


def test_a_fixed_pivot_does_not_apply_the_correction():
    part = _part("fixed")
    x, y = _base((100, 100), (32, 32), _anchor(3, -2), part)
    # 100 - 32//2, 100 - 32//2 -- centred, with no correction
    assert (x, y) == (84, 84)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_fixed_pivot.py -v`

Expected: **FAIL** — the fixed pivot still applies the correction
(`assert (103, 98) == (100, 100)`).

- [ ] **Step 3: Make `_base()` honour the pivot**

In `src/anim/parts.py`, replace `_base` with:

```python
def _base(
    origin: tuple[int, int],
    canvas: tuple[int, int],
    anchor: FrameAnchor,
    part: Part,
) -> tuple[int, int]:
    """Where a part's surface is blitted.

    The anchor's `body_dx/body_dy` is the measured REGISTRATION
    correction: it moves the silhouette's centroid onto the set's anchor.
    A part with `pivot = "fixed"` does NOT apply it -- the surface is
    blitted centred, which is what the enemy sets declare (and what the
    runtime does today). `pivot = "centroid"` keeps the shipped
    behaviour, which is what GOLIATH uses.
    """
    if part.pivot == "fixed":
        return (origin[0] - canvas[0] // 2, origin[1] - canvas[1] // 2)
    return (
        origin[0] - canvas[0] // 2 + anchor.body_dx,
        origin[1] - canvas[1] // 2 + anchor.body_dy,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_fixed_pivot.py -v`

Expected: **2 passed**

- [ ] **Step 5: GOLIATH must not move**

Run: `python tools\sprite_pipeline\verify_contract.py goliath`

Expected: `CONTRACT OK`, exit 0 — GOLIATH's parts use `pivot = "centroid"`,
so the behaviour is unchanged.

- [ ] **Step 6: Commit**

```powershell
git add src/anim/parts.py tests/test_fixed_pivot.py
git commit -m "fix: BLOQUE 75 - el pivote fixed no aplica la correccion de registro"
```

---

### Task 6: The clip's own scale and canvas

**Files:**
- Modify: `src/anim/clip.py` (the frames surface is scaled and cached scaled;
  the CLIP's canvas reaches `draw_part`)
- Test: `tests/test_enemy_scale_matches_runtime.py`

**Interfaces:**
- Consumes: `Part.scale: tuple[float, float]`, `Clip.canvas: tuple[int, int] | None`
- Produces: `ClipPlayer.surface(clip_id, frame)` returns the RAW surface (as
  today); `ClipPlayer.scaled_surface(clip_id, frame, part)` returns the
  surface scaled by the part's scale

**Why this task exists.** The runtime draws the enemy at
`_ship_scale_enemy = 1.05` (`gameplay_runtime.py:408`) while the pipeline
draws the PNG raw. Without the scale, the enemy would be 32×32 instead of
33×33 — a pixel of difference on every edge, and the golden frames would
fail for a reason nobody could explain.

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy_scale_matches_runtime.py`:

```python
"""BLOQUE 75 Fase 2: the pipeline must draw the enemy at the SAME size.

The runtime scales the enemy sprite by `_ship_scale_enemy` (1.05) and
truncates: `int(32 * 1.05) == 33`. The pipeline must reproduce that
EXACTLY, or the golden frames differ by a pixel on every edge.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys
from pathlib import Path

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.entities.enemies.enemy import Enemy
from src.ui.gameplay_runtime import GameplayRuntime


@pytest.fixture(scope="module")
def display():
    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_the_runtime_scales_the_enemy_by_1_05():
    runtime = GameplayRuntime(lambda *a, **k: None, is_boss=False, act=1, audio=None)
    assert runtime._ship_scale_enemy == 1.05
    assert int(32 * runtime._ship_scale_enemy) == 33


def test_the_enemy_manifests_declare_that_scale():
    from src.anim.manifest import load_set

    enemies = ROOT / "Assets" / "sprites" / "enemies"
    for name in ("scout", "cruiser", "drone", "heavy", "kamikaze", "sniper", "turret"):
        anim_set = load_set(name, root=enemies)
        body = anim_set.part("body")
        assert body.scale == (1.05, 1.05), name
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_enemy_scale_matches_runtime.py -v`

Expected: **FAIL** — the enemy manifests do not declare `scale` yet (Task 7
adds it); the first test passes.

- [ ] **Step 3: Make the compositor scale the frames part**

In `src/anim/clip.py`:

1. Add a method next to `surface()`:
   ```python
   def scaled_surface(
       self, clip_id: str, frame: int, part: Part
   ) -> pygame.Surface | None:
       """The frame's surface, scaled by the part's scale.

       The runtime draws the enemy at `_ship_scale_enemy` (1.05) with the
       SAME truncation: `int(32 * 1.05) == 33`. Reproducing that exactly
       is what keeps the golden frames identical.
       """
       raw = self.surface(clip_id, frame)
       if raw is None:
           return None
       sx, sy = part.scale
       if sx == 1.0 and sy == 1.0:
           return raw
       width = int(raw.get_width() * sx)
       height = int(raw.get_height() * sy)
       if width <= 0 or height <= 0:
           return None
       return pygame.transform.scale(raw, (width, height))
   ```
2. Pass the part's scale and the CLIP's canvas to `draw_part`:
   - `draw_part(surface, target, part, anchor, canvas, ...)` already receives
     `canvas`; the caller in `clip.py` passes `self.set.canvas` — change it
     to the clip's effective canvas:
     ```python
     canvas = clip.canvas or self.set.canvas
     ```
   - and the `frames` branch must draw the SCALED surface:
     ```python
     scaled = self.scaled_surface(clip.id, frame, part)
     if scaled is not None:
         target.blit(scaled, base)
     ```

- [ ] **Step 4: Run the test**

Run: `python -m pytest tests/test_enemy_scale_matches_runtime.py -v`

Expected: the first test passes; the second still fails (Task 7 adds the
declaration).

- [ ] **Step 5: GOLIATH must not move**

Run: `python tools\sprite_pipeline\verify_contract.py goliath`

Expected: `CONTRACT OK`, exit 0 — GOLIATH's body part declares no scale, so
`scaled_surface` returns the raw surface and nothing changes.

- [ ] **Step 6: Commit**

```powershell
git add src/anim/clip.py tests/test_enemy_scale_matches_runtime.py
git commit -m "feat: BLOQUE 75 - el compositor escala la parte frames con la escala de la parte y el canvas del clip"
```

---

### Task 7: The enemy manifests declare the scale, and the anchors are regenerated

**Files:**
- Modify: `Assets/sprites/enemies/*/manifest.toml` (8 files: `scale = [1.05, 1.05]` on the `body` part)
- Modify: `tools/sprite_pipeline/audit.py` (the generated header names the gate)
- Regenerate: `Assets/sprites/enemies/*/anchors.toml` (8) and `Assets/sprites/bosses/goliath/anchors.toml` (one line)

**Interfaces:**
- Consumes: `Part.scale` (Task 6)
- Produces: the 8 enemy manifests with `scale = [1.05, 1.05]`; the generated
  anchors carry the new header

- [ ] **Step 1: Add the scale to the 8 enemy manifests**

In each `Assets/sprites/enemies/<kind>/manifest.toml`, the `[[parts]]` block
becomes:

```toml
[[parts]]
id    = "body"
draw  = "frames"
pivot = "fixed"
# The runtime draws the enemy at _ship_scale_enemy = 1.05, truncated:
# int(32 * 1.05) == 33. The compositor reproduces that exactly.
scale = [1.05, 1.05]
z     = 0
```

- [ ] **Step 2: Run the scale test**

Run: `python -m pytest tests/test_enemy_scale_matches_runtime.py -v`

Expected: **2 passed**

- [ ] **Step 3: Fix the generated header**

In `tools/sprite_pipeline/audit.py`, `render_anchors_toml` writes a header
naming a TEST FILE. That is wrong for the enemy sets (their guard is
`tests/test_enemy_anchors_are_fresh.py`) and it names a file that only
protects GOLIATH. Replace the header line with one that is true for EVERY
set:

```
# DO NOT HAND-EDIT: the Phase 1 gate (G2) fails if this file is stale.
```

The gate already checks every set's freshness (`gate.py`, G2) and GOLIATH's
contract includes `anchors_fresh` ✓ — so the header names a check that really
runs, for every set.

- [ ] **Step 4: Regenerate every anchors file**

```powershell
foreach ($set in @('goliath')) { python tools\sprite_pipeline\audit.py $set --root Assets\sprites\bosses --write-anchors }
foreach ($set in @('scout','cruiser','drone','heavy','kamikaze','sniper','turret','mine_asteroid')) { python tools\sprite_pipeline\audit.py $set --root Assets\sprites\enemies --write-anchors }
```

Expected: each run writes its `anchors.toml`. The FIRST run of each set exits
1 if the set has findings — the enemy sets audit clean (0 findings), so they
exit 0 ✓.

- [ ] **Step 5: Check the diffs are what you expect**

```powershell
git diff --stat -- Assets\sprites
```

Expected:
- the 8 enemy `anchors.toml`: **one line each** — the `manifest_sha256`
  (the manifest text changed) and the **header** (Task 7 step 3);
- the 8 enemy `manifest.toml`: the `scale` line;
- GOLIATH's `anchors.toml`: **one line** — the header ONLY. Its
  `manifest_sha256` must NOT change (GOLIATH's manifest did not change) ✓.

If GOLIATH's `manifest_sha256` changed, the manifest was modified by mistake
— restore it (`git checkout -- Assets\sprites\bosses\goliath\manifest.toml`)
and re-run.

- [ ] **Step 6: GOLIATH's contract and the enemy audit**

```powershell
python tools\sprite_pipeline\verify_contract.py goliath
```

Expected: `CONTRACT OK`, exit 0.

- [ ] **Step 7: Commit**

```powershell
git add Assets/sprites tools/sprite_pipeline/audit.py
git commit -m "feat: BLOQUE 75 - los enemies declaran la escala 1.05 y el header generado nombra al gate"
```

---

### Task 8: Checkpoint 2B — the enemies are drawn through the pipeline

**Files:**
- Modify: `src/ui/gameplay_runtime.py` (`_draw_enemy_pass` draws the body through the pipeline)
- Test: `tests/test_layer_stack_renders_identical_frames.py` (the same proof, now covering 2B)

**Interfaces:**
- Consumes: `ClipPlayer` (`src/anim/clip.py`), the enemy manifests, the
  anchors tables
- Produces: the enemy bodies drawn by the compositor, at the same size, at
  the same position, with the same flash

- [ ] **Step 1: Draw the enemy body through the pipeline**

In `src/ui/gameplay_runtime.py`:

1. The runtime needs a `ClipPlayer` per enemy kind. `src/ui/scenes.py` already
   builds one for GOLIATH (`get_clip_player()`); the enemies need the same
   for each kind. Add to `src/anim/clip.py` a loader that reads a set BY
   KIND from the enemies root:
   ```python
   def load_player_for_kind(kind: str, root: Path | None = None) -> ClipPlayer | None:
       """The ClipPlayer for an enemy kind, or None when it cannot load.

       The enemies live in `Assets/sprites/enemies/<kind>/`; the bosses in
       `Assets/sprites/bosses/<name>/`. This is the ONE place that knows
       both roots -- `src/anim/manifest.py::_sets_root` currently knows
       only the bosses.
       """
   ```
   and have it resolve the enemies root with the same `_MEIPASS` probe.
   **This is the "two roots coexist" item that Phase 1 deferred** — do it
   here, in one place, and let `src/anim/manifest.py::_sets_root()` keep its
   single-root behaviour for GOLIATH.

2. In `_draw_enemy_pass`, draw each enemy:
   - the CLIP id is the enemy's `animation_state` (`idle`, `thrust`,
     `damage`, `death`) — the enemy manifests declare exactly those ids ✓;
   - the frame is the enemy's own `animation_frame` — **the runtime keeps
     counting it**; the pipeline does not compute time (the design's
     decision: the layer passes the frame, the compositor never re-derives
     it);
   - the origin is the enemy's position with the shake applied;
   - the MINE is special: its `closed` clip holds five VARIANTS, so the
     frame is the mine's `mine_variant`, not a counter; and its `open3`
     state uses the `open3` clip (which points at the `open/` directory).

3. The white damage flash stays a runtime overlay (N4: overlays are not
   manifest features): it is applied to the SAME surface the compositor
   drew, so the shape-aware overlay keeps matching the sprite exactly.

- [ ] **Step 2: Run the golden frame test**

Run: `python -m pytest tests/test_layer_stack_renders_identical_frames.py -v`

Expected: **5 passed** — the frames are IDENTICAL after the enemies moved
to the pipeline.

**If a frame differs:** the difference is the bug. Check, in this order:
the scale (33 vs 32), the pivot (centred vs offset), the frame index (the
runtime's counter vs a re-derived one) and the origin (the shake). Do NOT
adjust the golden frames.

- [ ] **Step 3: Run the whole suite and the Phase 1 gate**

```powershell
python -m pytest tests\ --tb=no --junitxml=%TEMP%\b75_p2b.xml
python tools\sprite_pipeline\gate.py
```

Expected: **0 failed** and `PHASE 1 GATE OK` (exit 0) — the Phase 1 gate
still holds after the enemies moved to the pipeline.

- [ ] **Step 4: Commit**

```powershell
git add src/ui/gameplay_runtime.py src/anim/clip.py
git commit -m "feat: BLOQUE 75 - los enemigos se dibujan por el pipeline: 0 pixeles movidos"
```

---

### Task 9: The plumbing Phase 1 deferred

**Files:**
- Modify: `tools/sprite_pipeline/run.py`, `tools/sprite_pipeline/audit.py` (resolve a set through `sprite_pipeline.sets`)
- Modify: `src/anim/manifest.py` (enforce `mode`/`on_end`; the mine's contradiction)
- Test: `tests/test_manifest_mode_vocabulary.py`

**Interfaces:**
- Consumes: `sprite_pipeline.sets.resolve_set(name, root)` (Phase 1),
  `Clip.mode`, `Clip.on_end`

- [ ] **Step 1: The CLIs resolve a set through `sets.py`**

In `tools/sprite_pipeline/run.py` and `audit.py`, replace

```python
anim_set = load_set(args.set, root=Path(args.root) if args.root else None)
```

with a resolution that goes through `sprite_pipeline.sets.resolve_set` and
then `load_set` on the resolved directory:

```python
from sprite_pipeline.sets import resolve_set
...
root = Path(args.root) if args.root else None
try:
    set_dir = resolve_set(args.set, root=root)
except (OSError, ValueError) as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 2
anim_set = load_set(args.set, root=set_dir.parent)
```

(The CLI already catches `ValueError` and returns 2 — `SetNotFoundError` is a
`ValueError` ✓.)

- [ ] **Step 2: Enforce the `mode` vocabulary**

In `src/anim/manifest.py`, after the clips are parsed, validate:

```python
_VALID_MODES = ("sequence", "variants", "state", "archive")
_VALID_ON_END = ("loop", "hold", "reset")
```

- a clip with `mode == "variants"` must have `distinct == frames` (every
  variant is a different image);
- a clip with `mode == "state"` must have `frames == 1`;
- a clip with `mode == "archive"` is never played (the runtime does not
  select it) — and it must not declare an `fps`, because no fps applies to
  a clip that never advances;
- `on_end` must be one of the three values, and it must AGREE with `loop`:
  `on_end == "loop"` implies `loop is True`, and `on_end in ("hold",
  "reset")` implies `loop is False`.

Raise `ManifestError` with the offending clip id and field.

**The mine.** Its clips are static: `closed` is a variant set, `open1/open2/
open3` are single frames and `death` is an archive. Under the new rule the
mine's clips must therefore declare `loop = false` and `on_end = "hold"`,
because none of them advances. **That is the contradiction Phase 1's review
found** (`mode="variants"` with a derived `loop=True, on_end="loop"`): the
manifest now says what the runtime does.

- [ ] **Step 3: The test**

Create `tests/test_manifest_mode_vocabulary.py`:

```python
"""BLOQUE 75 Fase 2: `mode` and `on_end` have a vocabulary.

Phase 1 PARSED these fields but did not enforce them, because enforcing
them on GOLIATH's manifest would have rejected it. Phase 2 enforces them,
and the enemy manifests are corrected to match what the runtime actually
does.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anim.manifest import ManifestError, load_set


def test_goliath_still_loads():
    """GOLIATH declares neither `mode` nor `on_end`; it must keep loading."""
    anim_set = load_set("goliath")
    for clip in anim_set.clips.values():
        assert clip.mode == "sequence"
        assert clip.on_end in ("loop", "hold")


def test_the_mine_clips_are_static():
    """The mine never advances a frame: its clips are static."""
    anim_set = load_set("mine_asteroid", root=ROOT / "Assets" / "sprites" / "enemies")
    for clip in anim_set.clips.values():
        assert clip.loop is False, clip.id
        assert clip.on_end == "hold", clip.id


def test_a_variant_clip_declares_every_frame_as_distinct():
    anim_set = load_set("mine_asteroid", root=ROOT / "Assets" / "sprites" / "enemies")
    closed = anim_set.clip("closed")
    assert closed.mode == "variants"
    assert closed.distinct == closed.frames


def test_an_unknown_mode_is_rejected(tmp_path):
    set_dir = tmp_path / "probe"
    set_dir.mkdir()
    (set_dir / "manifest.toml").write_text(
        '[meta]\n'
        'name = "PROBE"\n'
        'canvas = [8, 8]\n'
        '\n'
        '[[clips]]\n'
        'id = "idle"\n'
        'frames = 2\n'
        'mode = "sequences"\n'
        '\n'
        '[[parts]]\n'
        'id = "body"\n'
        'draw = "frames"\n',
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_set("probe", root=tmp_path)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_manifest_mode_vocabulary.py -v`

Expected: **4 passed**

- [ ] **Step 5: The Phase 1 gate still holds**

Run: `python tools\sprite_pipeline\gate.py`

Expected: `PHASE 1 GATE OK`, exit 0.

- [ ] **Step 6: Commit**

```powershell
git add src/anim/manifest.py tools/sprite_pipeline/run.py tools/sprite_pipeline/audit.py tests/test_manifest_mode_vocabulary.py Assets/sprites/enemies/mine_asteroid/manifest.toml
git commit -m "feat: BLOQUE 75 - mode y on_end tienen vocabulario y los clips estaticos lo declaran"
```

---

### Task 10: The Phase 2 gate

**Files:**
- Modify: `tools/sprite_pipeline/gate.py` (the Phase 2 checks)
- Create: `tests/test_sprite_pipeline_gate_phase2.py`

**Interfaces:**
- Consumes: everything above
- Produces: `python tools\sprite_pipeline\gate.py --phase 2` → `PHASE 2 GATE OK`

- [ ] **Step 1: The Phase 2 checks**

Add to `tools/sprite_pipeline/gate.py`:

| check | what it does | passes when |
|---|---|---|
| P2-G1 | the golden frames are pixel-identical to the committed ones | `tests/test_layer_stack_renders_identical_frames.py` is green |
| P2-G2 | the harness is reproducible | `tools/capture/layerstack_frames.py --check` exits 0 |
| P2-G3 | `mypy src/render/` is clean | 0 errors, run with the PROJECT's venv interpreter: `& F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\render\` (mypy 2.4.0). Also check `… -m mypy src\anim\` (the documented gate, currently 0 errors in 6 files). |
| P2-G4 | the layer order is pinned | `tests/test_layer_stack_order.py` is green |
| P2-G5 | the enemy PNGs did not move | `git diff --stat <phase2 base>..HEAD -- '*.png' ':!tools/golden/'` is empty — **`tools/golden/` is EXCLUDED**: the golden frames are proof fixtures, not art, and Task 1 commits them (spec decision B3). The same exclusion is already in the Phase 1 gate's G11 (`tools/sprite_pipeline/gate.py`, commit `1e423da`). |
| P2-G6 | GOLIATH's contract still holds | `verify_contract.verify("goliath", None)` passes |

The phase-2 base is the commit the Phase 2 branch started from (`e619527`);
like Phase 1, it must be overridable (`--base`) and must FAIL (not skip) when
it is missing.

- [ ] **Step 2: The test**

Create `tests/test_sprite_pipeline_gate_phase2.py` — the same shape as
`tests/test_sprite_pipeline_gate.py`: run the gate with `--phase 2`, assert
`PHASE 2 GATE OK` and exit 0, with a timeout.

- [ ] **Step 3: Run the test**

Run: `python -m pytest tests/test_sprite_pipeline_gate_phase2.py -v`

Expected: **PASS**

- [ ] **Step 4: The whole suite and both gates**

```powershell
python -m pytest tests\ --tb=no --junitxml=%TEMP%\b75_p2_final.xml
python tools\sprite_pipeline\gate.py --phase 1
python tools\sprite_pipeline\gate.py --phase 2
```

Expected: **0 failed**, `PHASE 1 GATE OK`, `PHASE 2 GATE OK`.

- [ ] **Step 5: Commit**

```powershell
git add tools/sprite_pipeline/gate.py tests/test_sprite_pipeline_gate_phase2.py
git commit -m "feat: BLOQUE 75 - el gate de Fase 2: golden frames identicos, mypy limpio y el arte sin moverse"
```

---

## Self-review

**Spec coverage.** The Phase 2 design's §4.1-§4.5 → Task 2 (the engine) and
Task 3 (the 30 layers); §4.6 (checkpoint 2A) → Task 4; §4.7 (checkpoint 2B:
the scale, the pivot, the timing, the clip's canvas) → Tasks 5, 6, 7, 8;
§4.8 (the harness) → Task 1; §4.9 (errors) → the `DrawContext` contract and
the loader's `ManifestError`; §4.10 (the tests) → the six test files; the
Phase 1 deferred items → Task 9 (the CLI wiring, the root unification, the
`mode`/`on_end` vocabulary) and Task 7 (the anchors header).

**Placeholder scan.** No "TBD", no "similar to Task N", no unimplemented
steps: every task carries the code it needs. The two places where the
implementer must READ the code first are marked as such — the shake
signature of each draw helper (Task 3/4) and the four screen flashes
(Task 3) — because guessing them would produce a frame that differs by a
pixel, and the golden frames exist precisely to catch that.

**Type consistency.** `DrawContext(target, origin, scale, time, shake, size)`
is used identically in Tasks 2, 3 and 4; `Layer(id, z, draw)` likewise;
`build_layers(rt) -> LayerStack` is the single factory; `LayerStack.render(ctx)`
takes the context (not the target) everywhere; `_base(origin, canvas, anchor,
part)` keeps its signature and only its body changes.

**The one thing the plan cannot know in advance:** which draw helpers take
`(target, shx, shy)` and which take `(target)`. The implementer must check
each one in the runtime. That is stated in Task 3 and Task 4, and the golden
frames are the backstop: a wrong guess shows up as differing pixels, not as a
silent pass.

---

# Corrections log (added while the phase was executed)

This section is appended to the plan as the phase runs, so the audit trail
survives in git. **The briefs themselves live in `.superpowers/` (gitignored)
and are NOT rewritten once dispatched** — a rewritten brief cannot be audited
("deviation vs the brief" becomes invisible). Corrections go to a new,
versioned brief file and are recorded here.

Every defect listed below was found by a **reviewer** or by an
**implementer**; none was found by reading the diff.

## The briefs (controller defects)

| Brief | Defect | Severity | Who found it |
|---|---|---|---|
| Task 5 | the expected coordinates were arithmetically impossible: the base `_base` subtracts `canvas // 2`, so `centroid` is `(87, 82)` and `fixed` is `(84, 84)`, not `(103, 98)` / `(100, 100)` | Critical | implementer + reviewer |
| Task 5 | the test snippet was not executable: `Part` has NINE required fields and no defaults, so `Part(id=..., draw=..., pivot=..., z=0)` raises `TypeError` | Critical | implementer + reviewer |
| Task 5 | the helper's field values (`radii=()`, `on_missing="interpolate"`) were not the parser's real defaults (`radii=None`, `on_missing="fallback"`) | Minor | reviewer |
| Task 5 | the brief on disk was REWRITTEN IN PLACE after the implementer had committed and reported, so the deviation record was destroyed | Critical (process) | reviewer |
| Task 7 | Step 2 predicted "2 passed" for a file that holds 7 test functions | Minor | implementer |
| Task 7 | the brief did not say that the manifests are hand-edited SPECs whose prose must document every field they encode | Important | controller (preflight) |
| Task 8 | "5 passed" for a golden test that is parametrized over SIX frames | Minor | controller (preflight) |
| Task 8 | the flash path would have blitted the enemy body TWICE (the runtime's flash branch draws body+overlay, but the compositor draws the body) | Important | controller (preflight) |
| Task 8 | **the golden frames are BLIND to whether the enemies went through the pipeline** — a runtime that never calls the compositor draws the same pixels | Important | controller (preflight) |
| Task 9 | the "an archive clip must not declare an fps" rule cannot be checked on the parsed `Clip` (its `fps` default is 10, indistinguishable from a declared `fps = 10`): it needs the RAW entry | Important | controller (preflight) |
| Task 9 | editing the mine's manifest changes its `manifest_sha256`, so its `anchors.toml` goes stale and the Phase 1 gate turns RED — the brief did not say to regenerate it | Important | controller (preflight) |
| Task 10 | the gate has NO `--phase` argument: the brief assumed one existed | Important | controller (preflight) |
| Task 10 | the brief hardcoded an absolute path to the developer's venv, which does not exist in a worktree nor in CI | Important | controller (preflight) |
| Task 10 | a SKIPPED test is not a pass: the golden test SKIPS a case when its golden is missing, and `pytest -q` exits 0 when everything was skipped | Important | controller (preflight) |

## The implementation (defects the implementers caught)

| Task | Defect | Severity |
|---|---|---|
| Task 7 | the Phase 1 gate's check G5 diffs the whole `Assets/sprites/bosses/` directory over a commit range, so Phase 2's legitimate change to GOLIATH's **generated** `anchors.toml` turned the gate RED — and there is no escape (not regenerating it makes `verify_contract` report it stale) | Important |

**The principle it produced:** a GENERATED file is validated by **freshness**
("is it current?"), not by "did it change?". The freshness of GOLIATH's
anchors was already checked, by G5's second half (`verify_contract` →
`anchors_fresh`). Fix: `42d252e` narrows G5's RANGE pathspec to exclude the
generated measurement, keeping the manifest and the PNGs inside the diff.

## The reviews (defects in the committed work)

| Task | Defect | Severity |
|---|---|---|
| Task 5 | the `fixed` pivot's guarantee was **unpinned by the public path**: the two new tests called the private `_base()`, and a mutation that makes `draw_part` ignore the pivot left the **whole suite green** (3072 total / 3064 passed / 0 failures) | Important |

**The principle it produced:** a pixel-equality proof proves the PIXELS, not
the PATH. A checkpoint that says "the observable behaviour did not change"
needs TWO proofs: the equality of the result, and a test that the new code
path was actually exercised. Fix: `9d9742d` adds a test that renders a `fixed`
part through `parts.draw_part()` and asserts where the **pixels** land.

## The process rules this phase ended with

1. **A brief is written once, before dispatch, and frozen.** Corrections go to
   a new versioned file (`task-N-brief-r1.md`) and to the log above.
2. **The implementation outranks the brief.** When they disagree, the
   implementation is kept and the brief is corrected afterwards — but only if
   the implementer REPORTS the deviation instead of improvising.
3. **Every new test must be shown to be able to fail**, by mutating the code
   and pasting the red run.
4. **Never two implementers committing in the same worktree** (the git index
   race). Reviews may run in parallel; implementers may not.
