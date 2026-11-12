"""BLOQUE 75: the game can report whether its enemy pipeline is available.

After Phase 2 the runtime reads the enemy manifests every frame to draw
the enemies. A frozen build that does not carry them falls back to the
old draw path SILENTLY -- the game still runs, the enemies still appear,
and nothing anywhere reports an error.

This command is the check that would have caught it, and it has to run
inside the frozen build too, so it lives in the game.

The FAILURE path is the half that matters: a check that can only say OK
is not a check. The three tests at the bottom build the broken builds (a
root with no sets, a root whose art did not travel) OUTSIDE the
repository, under `tmp_path`, and assert that the command says so.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENEMY_SETS = ROOT / "Assets" / "sprites" / "enemies"

# The entry point is a root-level module. The other tests that need a
# root-level import put the root on sys.path the same way.
sys.path.insert(0, str(ROOT))

import main

# BLOQUE 76: the canonical list of the enemy sets (the EXPECTATION of
# `src/anim/sets.py`), imported and not written here. The command has to
# report exactly these -- a set that the command does not mention is a
# set the bundle does not have to carry.
from src.anim.sets import ENEMY_SETS as ENEMY_KINDS


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


def test_the_command_fails_when_the_sets_are_not_there(
    tmp_path: Path, capsys
) -> None:
    """The frozen build that did not carry the manifests.

    An empty root is the exact shape of that build: the loader finds
    nothing, the runtime falls back to the old draw path, and without
    this test nothing in the repository would notice if the command
    stopped failing.
    """
    code, failures = main._pipeline_report(root=tmp_path)
    assert code == 1
    joined = "\n".join(failures)
    assert "did not load" in joined
    for kind in ENEMY_KINDS:
        assert kind in joined, kind
    assert "FAILED to load" in capsys.readouterr().out


def test_the_command_fails_when_a_frame_is_missing(
    tmp_path: Path, capsys
) -> None:
    """The manifests travelled but the ART did not.

    The runtime falls back for a missing frame exactly like it does for
    a missing manifest (`player.surface()` returns None), so a bundle
    that carries only the `.toml` files has to be reported as broken --
    the manifests alone do not make the pipeline usable.
    """
    for kind in ENEMY_KINDS:
        shutil.copytree(ENEMY_SETS / kind, tmp_path / kind)
    (tmp_path / "scout" / "idle" / "frame_03.png").unlink()
    code, failures = main._pipeline_report(root=tmp_path)
    assert code == 1
    joined = "\n".join(failures)
    # ONLY the missing frame: the other seven sets are complete, and a
    # check that cried wolf would be as useless as one that stayed quiet.
    assert len(failures) == 1, failures
    assert "scout" in joined
    assert "frame_03.png" in joined
    out = capsys.readouterr().out
    assert "frames=39/40" in out


def test_the_command_fails_cleanly_when_the_display_cannot_be_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A video surface that cannot be created is a FAIL, not a traceback.

    BLOQUE 75 (follow-up 2.4): `_ensure_frame_display()` had no guard, so
    a failure there produced a traceback and the command died without an
    exit code anybody could act on. The reader of a CI log needs to know
    WHAT is wrong -- and a traceback says where the code died, not what
    the build is missing.

    The check has to be able to READ the frames: `ClipPlayer.surface()`
    converts every frame with `convert_alpha()`, pygame refuses that
    without a display, and the loader swallows the error and returns
    None. So without a surface every frame looks missing and the check
    would report a lie about a perfectly good build.
    """
    import pygame

    def boom(*args, **kwargs):
        raise pygame.error("no video mode available")

    # The surface is forced to be missing, so `set_mode` is the call that
    # fails -- whichever way the display was initialised before.
    monkeypatch.setattr(pygame.display, "get_surface", lambda: None)
    monkeypatch.setattr(pygame.display, "set_mode", boom)

    code, failures = main._pipeline_report(root=tmp_path)
    assert code == 1
    joined = "\n".join(failures)
    assert "video surface" in joined, failures
    assert "no video mode available" in joined, failures


def test_the_command_exits_with_one_when_the_pipeline_is_broken(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The exit code is what the release check reads.

    The two tests above cover the report itself; this one covers the
    contract AROUND it: a broken pipeline has to leave the command with
    a non-zero exit code and the reason on stderr. Without it, a
    regression that made the command answer 0 to a broken pipeline would
    pass every other test here.
    """
    monkeypatch.setattr(
        main,
        "_pipeline_report",
        lambda root=None: (1, ["scout: the set did not load"]),
    )
    assert main._cmd_check_pipeline() == 1
    err = capsys.readouterr().err
    assert "pipeline check FAIL" in err
    assert "scout: the set did not load" in err
