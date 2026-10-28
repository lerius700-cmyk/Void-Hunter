"""BLOQUE 74: anchors.toml must match the assets it describes.

The anchors are the measurement of every frame. If the art changes and the
anchors do not, the runtime draws the shield ellipse where the plate used
to be. This test regenerates the anchors and fails on any diff.
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
sys.path.insert(0, str(ROOT / "tools"))

from src.anim.manifest import load_set


@pytest.fixture(scope="module")
def display():
    """pygame needs a video mode before convert_alpha() works."""
    import pygame

    pygame.init()
    pygame.display.set_mode((320, 480))
    yield


def test_anchors_toml_is_up_to_date(display):
    from sprite_pipeline.audit import audit_set, render_anchors_toml

    anim_set = load_set("goliath")
    _, measurements = audit_set(anim_set)
    rendered = render_anchors_toml(anim_set, measurements)

    anchors_path = anim_set.path / "anchors.toml"
    assert anchors_path.is_file(), "anchors.toml does not exist yet"
    current = anchors_path.read_text(encoding="utf-8")
    assert current == rendered, (
        "anchors.toml is stale -- regenerate it with "
        "`python tools/sprite_pipeline/audit.py goliath --write-anchors` "
        "(BLOQUE 74 Task 6 adds `python tools/sprite_pipeline/run.py "
        "goliath --fix` as the one-step fix)"
    )


def test_the_manifest_hash_survives_a_crlf_checkout(tmp_path, display):
    """The freshness check must not depend on the checkout's line endings.

    With core.autocrlf=true and no .gitattributes, the same manifest blob
    materialises as LF on one machine and CRLF on another. A hash over the
    RAW BYTES made the anchors look stale on half the checkouts, which is
    how this was found: merging the branch into another worktree turned
    the freshness test red with no change to the art.
    """
    import shutil

    from sprite_pipeline.audit import audit_set, render_anchors_toml

    source = load_set("goliath")
    copy_dir = tmp_path / "goliath"
    shutil.copytree(source.path, copy_dir)

    manifest = copy_dir / "manifest.toml"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_bytes(original.replace("\n", "\r\n").encode("utf-8"))
    assert b"\r\n" in manifest.read_bytes(), "the CRLF rewrite did not apply"

    crlf_set = load_set("goliath", root=copy_dir.parent)
    _, crlf_measurements = audit_set(crlf_set)
    crlf_rendered = render_anchors_toml(crlf_set, crlf_measurements)

    _, lf_measurements = audit_set(source)
    lf_rendered = render_anchors_toml(source, lf_measurements)

    assert crlf_rendered == lf_rendered, (
        "the manifest hash changed with the line endings -- the anchors "
        "would look stale on a CRLF checkout"
    )
