"""The binary must not carry a GENERATED file.

`keep kept - Lerius - soundtrack gameplay_lp600.wav` is not an asset: it
is the gameplay track with a 600 Hz lowpass applied, and the game
rebuilds it in a few seconds and caches it next to the executable
(`src/audio/lowpass_cache.py`). Shipping a copy of it inside the
binary cost 61 MB in every download, for a file the game can make on
its own.

There are TWO ways a generated WAV could get into the bundle, and both
have to stay closed:

* a literal entry in `datas` (the one BLOQUE 58.14 added);
* the glob over the Assets root, which pulls in every loose file there
  -- that one has to keep excluding `*_lp*`.

The ORIGINAL tracks are assets and they stay.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build.spec"


def _spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_no_generated_wav_is_bundled_as_a_literal_entry():
    """No `datas` entry names a `*_lp*.wav`."""
    text = _spec_text()
    offenders = [
        name
        for name in re.findall(r'"([^"]+\.wav)"', text)
        if "_lp" in name.lower()
    ]
    assert not offenders, (
        f"the spec still bundles generated tracks: {offenders}. The game "
        "rebuilds and caches them next to the executable."
    )


def test_the_glob_over_the_assets_root_keeps_excluding_them():
    """The glob must not pull a generated WAV back in."""
    text = _spec_text()
    assert 'glob("*")' in text, (
        "the glob over the Assets root is gone: the loose runtime assets "
        "(the music, the painted background) would leave the binary"
    )
    assert '"_lp" not in p.name' in text, (
        "the glob over Assets/* would pull a generated WAV back into the "
        "bundle"
    )


def test_the_original_tracks_are_still_bundled():
    """The real music still goes in through the glob."""
    text = _spec_text()
    assert 'glob("*")' in text
    assets_root = ROOT / "Assets"
    for name in (
        "keep kept - Lerius - soundtrack gameplay.wav",
        "pantalla principal.wav",
    ):
        assert (assets_root / name).is_file(), (
            f"{name} is missing from the Assets root, so it cannot be bundled"
        )
        assert "_lp" not in name


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
