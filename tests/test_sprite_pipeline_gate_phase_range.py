"""BLOQUE 77: la promesa de una fase es sobre el TRABAJO de la fase.

El range de la Fase 1 (G5 y G11) es `base..HEAD`. Mientras la fase estaba
EN CURSO, HEAD era la punta de la fase, asi que el range ERA la fase. Pero
el range crece con cada commit que aterriza en la rama DESPUES de la fase, y
la PROMESA no: la Fase 1 prometio que el pipeline de enemigos no tocaba a
GOLIATH, y esa promesa es sobre el trabajo de la Fase 1 -- que termino donde
empezo la Fase 2 (e619527 es el HEAD de la linea de release cuando la Fase 2
arranco).

BLOQUE 77 cambio el manifiesto de GOLIATH A PROPOSITO: la regla de deteccion
rechazaba la placa de canto, y la elipse tenia que MEDIRSE en vez de inventarse.
Medido sobre `base..HEAD`, el gate de la Fase 1 lo trato como una violacion de
una promesa que hacia una fase cerrada hace tiempo.

ASI QUE EL RANGE DE UNA FASE TERMINA DONDE EMPIEZA LA SIGUIENTE. Y lo que no
se pierde esta escrito en el modulo: el ARTE lo sigue guardando el P2-G5 de
la Fase 2 (diffea todos los PNG del arbol sobre e619527..HEAD), la ESPECIE la
sigue guardando el CONTRATO (las comprobaciones tienen que coincidir
EXACTAMENTE) y la MEDICION la guarda la FRESCURA.

Estos tests usan el arnes del gate sobre un repositorio temporal: nada se
escribe en el repositorio (L7).
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from sprite_pipeline import gate  # noqa: E402

MANIFEST = "Assets/sprites/bosses/goliath/manifest.toml"
FRAME = "Assets/sprites/bosses/goliath/death/frame_00.png"

AUTHOR = ("-c", "user.email=gate@test", "-c", "user.name=gate")


def _git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    """A temporary git repository with one SPEC and one PNG."""
    repo = tmp_path / "repo"
    for rel in (MANIFEST, FRAME):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"base\n")
    _git(repo, ["init", "-q", "-b", "main"])
    _git(repo, ["add", "-A"])
    _git(repo, [*AUTHOR, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "base"])
    return repo


def _commit_change(repo: Path, rel: str, payload: bytes) -> str:
    """Change one file, commit it, and return the new commit."""
    (repo / rel).write_bytes(payload)
    _git(repo, ["add", "-A"])
    _git(
        repo,
        [*AUTHOR, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "change"],
    )
    return _git(repo, ["rev-parse", "HEAD"])


def test_the_phase_range_ends_where_the_next_phase_started(tmp_path, monkeypatch):
    """Con la fase siguiente ya en la historia, el range termina en su base."""
    repo = _repo(tmp_path)
    phase_end = _commit_change(repo, MANIFEST, b"changed\n")
    monkeypatch.setattr(gate, "PHASE_2_BASE", phase_end)

    assert gate.phase_range_end(1, repo=repo) == phase_end, (
        "the Phase 1 range must end where Phase 2 started: the promise is "
        "about the phase's work, not about every commit that came after it"
    )


def test_a_phase_in_progress_still_measures_up_to_head(tmp_path, monkeypatch):
    """Una fase EN CURSO mide hasta HEAD, que es su punta."""
    repo = _repo(tmp_path)
    _commit_change(repo, MANIFEST, b"changed\n")
    # The next phase has not started yet: its base is not in this history.
    monkeypatch.setattr(gate, "PHASE_2_BASE", "not-a-commit-in-this-repo")

    assert gate.phase_range_end(1, repo=repo) == "HEAD"


def test_a_change_inside_the_phase_is_still_reported(tmp_path, monkeypatch):
    """LA PROMESA SIGUE VIVA: un cambio DENTRO de la fase se reporta."""
    repo = _repo(tmp_path)
    base = _git(repo, ["rev-parse", "HEAD"])
    phase_end = _commit_change(repo, MANIFEST, b"changed inside the phase\n")
    monkeypatch.setattr(gate, "PHASE_2_BASE", phase_end)

    proc = gate._goliath_assets_diff(base, phase_end, repo=repo)
    assert proc.returncode == 0, proc.stderr
    assert "goliath/manifest.toml" in proc.stdout, proc.stdout


def test_a_change_after_the_phase_is_not_reported_by_that_phase(tmp_path, monkeypatch):
    """Un cambio DESPUES de la fase es de la fase siguiente, no de esta."""
    repo = _repo(tmp_path)
    base = _git(repo, ["rev-parse", "HEAD"])
    phase_end = _commit_change(repo, MANIFEST, b"changed inside the phase\n")
    # The ART moves AFTER the phase: the PNG is the thing G5's range guards.
    _commit_change(repo, FRAME, b"\x89PNG\r\n\x1a\nchanged after the phase")
    monkeypatch.setattr(gate, "PHASE_2_BASE", phase_end)

    # The phase's own range does not see it: the change is not the phase's.
    inside = gate._goliath_assets_diff(base, phase_end, repo=repo)
    assert "frame_00.png" not in inside.stdout, (
        "the phase's range must stop at the end of the phase:\n" + inside.stdout
    )

    # And the range that DOES cover it reports it.
    after = gate._goliath_assets_diff(phase_end, "HEAD", repo=repo)
    assert "frame_00.png" in after.stdout, after.stdout
