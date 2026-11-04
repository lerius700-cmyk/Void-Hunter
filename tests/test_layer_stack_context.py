"""BLOQUE 75 Fase 2: the frame engine.

The engine is generic: it knows about layers, an order and a context, and
NOTHING about the game. That boundary is what keeps the mypy gate clean
(L6): `src/render/` must not import `src/ui/`, `src/entities/` or
`src/anim/`.

The boundary is guarded by RESOLVING the imports of every module of
`src/render/` (see `_forbidden_imports`), not by grepping the source text:
`src/` is a package and `src/ui/` is a NAMESPACE package, so a relative
import such as `from ..ui import scenes` WORKS at runtime and would sail
through a text scan.
"""
from __future__ import annotations

import ast
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

# The packages `src/render/` must never reach into.
FORBIDDEN_ROOTS: tuple[tuple[str, ...], ...] = (
    ("src", "ui"),
    ("src", "entities"),
    ("src", "anim"),
)


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


def _dotted(name: str) -> tuple[str, ...]:
    """`"src.ui.scenes"` -> `("src", "ui", "scenes")`."""
    return tuple(part for part in name.split(".") if part)


def _package_parts(path: Path, root: Path) -> tuple[str, ...]:
    """The dotted package that CONTAINS `path`.

    A module and its package's `__init__` share the package:
    `src/render/layer.py` and `src/render/__init__.py` are both inside
    `src.render`.
    """
    return tuple(path.relative_to(root).parts[:-1])


def _reaches_forbidden(dotted: tuple[str, ...]) -> bool:
    """Is `dotted` one of the forbidden packages, or something inside one?"""
    return any(dotted[: len(root)] == root for root in FORBIDDEN_ROOTS)


def _resolved_imports(path: Path, root: Path) -> list[tuple[str, ...]]:
    """Every module path the imports of `path` reach.

    Absolute and relative imports are both resolved to a dotted path, so
    `from ..ui import scenes` (relative, level 2) and
    `from src.ui import scenes` (absolute) land on the same `src.ui`.
    """
    package = _package_parts(path, root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    reached: list[tuple[str, ...]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                reached.append(_dotted(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # A relative import: level 1 is the containing package,
                # level 2 is its parent, and so on.
                keep = len(package) - (node.level - 1)
                anchor = package[:keep] if keep >= 0 else ()
            else:
                anchor = ()
            base = anchor + _dotted(node.module or "")
            reached.append(base)
            for alias in node.names:
                reached.append(base + (alias.name,))
    return reached


def _forbidden_imports(render_dir: Path, root: Path) -> list[str]:
    """The imports under `render_dir` that reach into the game.

    EVERY `.py` under the package is scanned -- not one file -- so a module
    added later cannot slip past the boundary.
    """
    offences: list[str] = []
    for path in sorted(render_dir.rglob("*.py")):
        for reached in _resolved_imports(path, root):
            if _reaches_forbidden(reached):
                offences.append(f"{path.relative_to(root)}: {'.'.join(reached)}")
    return offences


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


def test_the_layer_draws_onto_the_context_target(display):
    """The stack must hand the layer the CONTEXT's target -- by identity.

    `LayerStack.render` calls `layer.draw(ctx.target, ctx)`: the surface is
    the one the context carries and the context is the very same object.
    A regression that passed another surface would still be called once
    per layer, so nothing else in this file would notice.
    """
    seen: list[tuple[pygame.Surface, DrawContext]] = []
    ctx = _ctx()
    stack = LayerStack([Layer(id="probe", z=0, draw=lambda t, c: seen.append((t, c)))])
    stack.render(ctx)
    assert len(seen) == 1
    surface, passed_ctx = seen[0]
    assert surface is ctx.target
    assert passed_ctx is ctx


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
    """L6: `src/render/` must not depend on `src/ui/`, `src/entities/` or `src/anim/`.

    The imports are RESOLVED, not grepped: `from ..ui import scenes` and
    `from src import ui` both reach `src/ui/` and both work at runtime
    (`src/` is a package and `src/ui/` is a namespace package), so both
    must fail here.
    """
    offences = _forbidden_imports(ROOT / "src" / "render", ROOT)
    assert offences == [], f"src/render/ must not import the game: {offences}"


# Every form that reaches the game, in every spelling. The guard must
# report each one of them.
EVADING_IMPORTS = (
    "from ..ui import scenes",
    "from ..entities import player",
    "from ..anim import clip",
    "from .. import ui",
    "from src import ui",
    "from src.ui import scenes",
    "import src.ui.scenes",
)


@pytest.mark.parametrize("breach", EVADING_IMPORTS)
def test_the_boundary_guard_catches_every_evading_form(tmp_path, breach):
    """The guard must FAIL on each form that reaches the game at runtime."""
    pkg = tmp_path / "src" / "render"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "layer.py").write_text(f"{breach}\n", encoding="utf-8")
    offences = _forbidden_imports(pkg, tmp_path)
    assert offences, f"the guard missed {breach!r}"


def test_the_boundary_guard_allows_the_benign_imports(tmp_path):
    """The guard must not cry wolf: stdlib, pygame and the package itself."""
    pkg = tmp_path / "src" / "render"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "layer.py").write_text(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from typing import Callable\n"
        "import pygame\n",
        encoding="utf-8",
    )
    (pkg / "helper.py").write_text("from .layer import Layer\n", encoding="utf-8")
    assert _forbidden_imports(pkg, tmp_path) == []
