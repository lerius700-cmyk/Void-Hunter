"""BLOQUE 74: the HUD font cache must survive a pygame.quit().

``HUD._ensure_fonts()`` builds three ``pygame.font.Font`` objects, caches
them and never looks at them again. ``pygame.quit()`` tears the font
subsystem down and invalidates those objects *natively*: rendering one
afterwards is an access violation (0xC0000005), not a Python exception.
So the guard in ``HUD._ensure_fonts`` has to check that the font subsystem
is still up -- not only that the HUD already built its fonts.

The crash-prone sequence cannot run inside the pytest process: a native
access violation kills the interpreter, taking the whole test run with it.
The sequence therefore runs in a subprocess and the test asserts on its
exit code (0 = the fonts were rebuilt and the frame rendered; anything
else = the stale font was used).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The script is written to a temp file at test time and run in its own
# interpreter. __VH_ROOT__ is replaced by the repo root so the subprocess
# imports the same `src/` the test suite does.
_SCRIPT = '''\
"""Reproduce the stale-HUD-font crash after pygame.quit()."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, __VH_ROOT__)

import pygame

from src.entities.player import Player
from src.systems.scoring_system import ScoringSystem
from src.systems.weapon_system import WeaponSystem
from src.ui.hud import HUD


def main() -> int:
    pygame.init()
    pygame.display.set_mode((320, 480))

    hud = HUD()
    surface = pygame.Surface((320, 480), pygame.SRCALPHA)
    player = Player()
    weapon = WeaponSystem()
    scoring = ScoringSystem()

    # First frame: the HUD builds and caches its fonts.
    hud.draw(surface, player, weapon, scoring)
    stale_font = hud.font_score
    if stale_font is None:
        print("FONT_BUILT=0")
        return 2
    print("FONT_BUILT=1")

    # Tear pygame down: the cached Font objects are dangling from now on.
    pygame.quit()
    print("FONT_DOWN=%d" % (0 if pygame.font.get_init() else 1))

    # The guard must notice that the font subsystem is down and rebuild.
    hud._ensure_fonts()
    print("FONT_INIT=%d" % (1 if pygame.font.get_init() else 0))
    print("FONT_OK=%d" % (1 if hud.font_score is not None else 0))
    print("FONT_REBUILT=%d" % (1 if hud.font_score is not stale_font else 0))

    # Render a real frame with the rebuilt fonts.
    hud.draw(surface, player, weapon, scoring)
    print("DRAW_OK=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def _run_repro(tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the crash-prone sequence in its own interpreter."""
    script = tmp_path / "hud_font_cache_repro.py"
    script.write_text(
        _SCRIPT.replace("__VH_ROOT__", repr(str(ROOT))), encoding="utf-8"
    )
    env = dict(os.environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(ROOT),
    )


def test_hud_rebuilds_its_fonts_after_pygame_quit(tmp_path: Path) -> None:
    """The HUD must not render with a font that outlived pygame.quit().

    Without the `pygame.font.get_init()` guard the subprocess dies with
    "Library not initialized" (or a native access violation) and exits
    non-zero; with the guard it exits 0.
    """
    proc = _run_repro(tmp_path)

    assert proc.returncode == 0, (
        "the HUD font cache did not survive pygame.quit()\n"
        f"returncode={proc.returncode}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )
    out = proc.stdout
    assert "FONT_BUILT=1" in out, out
    # The scenario was real: the font subsystem was down after the quit.
    assert "FONT_DOWN=1" in out, out
    # The guard brought the subsystem back up ...
    assert "FONT_INIT=1" in out, out
    # ... and replaced the stale Font objects with fresh ones.
    assert "FONT_OK=1" in out, out
    assert "FONT_REBUILT=1" in out, out
    # The real draw path rendered a frame with the rebuilt fonts.
    assert "DRAW_OK=1" in out, out


def test_ensure_fonts_guards_on_the_font_subsystem() -> None:
    """The guard must be in the source, not just in the runtime behaviour.

    Cheap guard against someone deleting the one-line check: the
    subprocess test above proves the behaviour, this one proves the
    check is still there.
    """
    import inspect

    from src.ui.hud import HUD

    src = inspect.getsource(HUD._ensure_fonts)
    assert "self.initialized and pygame.font.get_init()" in src, (
        "HUD._ensure_fonts() must gate the fast path on "
        "pygame.font.get_init(): a Font object that outlived "
        "pygame.quit() is dead and rendering it is a native access "
        "violation."
    )
