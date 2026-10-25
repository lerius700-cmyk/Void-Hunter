"""BLOQUE 67: el build.spec tiene que cubrir TODOS los assets de runtime.

Este guard existe por un bug real: `Assets/imagen fondo del juego.jpg` (el
fondo pintado del boss fight) vivia en la RAIZ de Assets/ y el spec solo
bundleaba WAVs sueltos de ahi, asi que el JPG nunca entro al .exe. En el
.juego compilado el boss fight caia al fallback del parallax (negro con
estrellas) en vez del fondo con la nebulosa y los asteroides. Como el
fallback no rompe nada, `--check` pasaba y el bug llego a una release
publicada.

Estos tests leen el build.spec y comprueban la cobertura, sin necesidad de
compilar.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "Assets"
SPEC = ROOT / "build.spec"


def _spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_spec_exists() -> None:
    assert SPEC.is_file(), "no encuentro build.spec"


def test_boss_fight_background_is_bundled() -> None:
    """El fondo pintado del boss fight tiene que estar en el .exe.

    `TilingImage` lo busca como `<_MEIPASS>/Assets/imagen fondo del
    juego.jpg` — en la RAIZ de Assets/. Si el spec no lo bundlea, el
    boss fight cae al parallax y se ve negro con estrellas.
    """
    assert (ASSETS / "imagen fondo del juego.jpg").is_file(), (
        "el asset del fondo del boss fight no existe en el repo"
    )
    spec = _spec_text()
    assert "imagen fondo del juego.jpg" in spec, (
        "build.spec no bundlea 'imagen fondo del juego.jpg': el boss "
        "fight se va a ver negro con estrellas en el .exe"
    )


def test_every_root_asset_is_covered_by_a_glob() -> None:
    """La raiz de Assets/ se bundlea con un glob, no con una lista a mano.

    Una lista a mano es como se colaron los omissions: alguien agrego un
    WAV y olvido el JPG. Con el glob, todo archivo nuevo de la raiz entra
    solo.
    """
    spec = _spec_text()
    assert '(PROJECT_ROOT / "Assets").glob("*")' in spec, (
        "build.spec deberia bundlear la raiz de Assets/ con un glob para "
        "que ningun asset nuevo se quede afuera"
    )


def test_lowpass_cache_is_excluded_except_the_prebaked_one() -> None:
    """El cache *_lp*.wav se regenera solo; solo se bundlea el lp600.

    El cache son 61 MB por cutoff. El unico que va al .exe es el lp600
    pre-generado (BLOQUE 58.14), que existe para no pagar los 8 s de
    regeneracion en la primera pausa.
    """
    spec = _spec_text()
    assert '"_lp" not in p.name' in spec, (
        "el glob de la raiz de Assets/ deberia excluir el cache *_lp*.wav"
    )
    assert "gameplay_lp600.wav" in spec, "el lp600 pre-generado si va al .exe"


def test_runtime_directories_are_bundled() -> None:
    """Las carpetas que el juego necesita en runtime, una por una."""
    spec = _spec_text()
    for folder in ("background", "sprites", "video"):
        assert f'"Assets" / "{folder}"' in spec, (
            f"build.spec no bundlea Assets/{folder}/"
        )


def test_tiles_are_bundled() -> None:
    """Los tiles del Asteroid Approach (el fondo morado de v1.4.0).

    Viven en Assets/background/tiles/act1/, asi que el glob de
    Assets/background los cubre. Este test es la garantia de que no
    desaparecen del .exe (que fue justamente lo que paso con v1.4.0).
    """
    tiles = ASSETS / "background" / "tiles" / "act1"
    assert tiles.is_dir(), "no existe Assets/background/tiles/act1/"
    pngs = sorted(tiles.glob("tile_*.png"))
    assert len(pngs) == 6, f"deberian ser 6 tiles, hay {len(pngs)}"
    assert '"Assets" / "background"' in _spec_text(), (
        "build.spec no bundlea Assets/background/, asi que los tiles no "
        "entran al .exe"
    )


def test_goliath_frames_are_bundled() -> None:
    """Los 60 frames de GOLIATH van dentro de Assets/sprites/."""
    goliath = ASSETS / "sprites" / "bosses" / "goliath"
    assert goliath.is_dir()
    anims = ("phase1_idle", "phase2_idle", "javelin", "laser",
             "purple_bullet", "death")
    for anim in anims:
        frames = sorted((goliath / anim).glob("frame_*.png"))
        assert len(frames) == 10, f"{anim}: {len(frames)} frames en vez de 10"
    assert '"Assets" / "sprites"' in _spec_text()
