# Repo Hygiene Round Two — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the pause lowpass cache persist next to the executable, take the 61 MB generated WAV out of the binary, put a ceiling on the repository's weight that a test enforces, and land everything on the release line as v1.8.1.

**Architecture:** A new `src/audio/lowpass_cache.py` owns WHERE the filtered track lives (a `_vh_cache` directory next to the executable, never `Assets`, because `_find_assets_dir()` probes `<exe_dir>/Assets` first and a cache there would shadow the bundle's own assets). `src/audio/music.py::_ensure_filtered_bgm` asks that module for the cache before it generates anything. `tools/repo_budget.py` measures three weights and `tests/test_repo_budget.py` fails when a ceiling is crossed; the numbers become rows in the STATUS block.

**Tech Stack:** Python 3.11 (`F:\AI\MM\void-hunter\.venv\Scripts\python.exe`), pygame 2.6.1, numpy 2.4.6 (audio only), PyInstaller 6.22.2, git, PowerShell 5.1.

**Spec:** `docs/superpowers/specs/2026-11-02-repo-hygiene-round-2-design.md` (commit `01fb0a7`).

## Global Constraints

These apply to EVERY task. They are not restated per task.

- **PowerShell only.** No `&&`, no `ls -la`, no `head`/`tail`/`grep`/`wc`. Use `;`, `Get-ChildItem`, `Select-Object`, `Select-String`. Start multi-statement scripts with `$ErrorActionPreference = 'Stop'`.
- **Never delete.** `Remove-Item -Recurse -Force` is blocked by the harness and forbidden by the design. Every removal is a `Move-Item` into `F:\AI\MM\_vh_archive_2026-10-30\`.
- **The git history is NOT rewritten.** The tags `v1.7.0`, `v1.7.2` and `v1.8.0` stay exactly where they are. No `git filter-repo`, no force-push of the release branch.
- **The two real WAV tracks stay** (`keep kept - Lerius - soundtrack gameplay.wav`, `pantalla principal.wav`). They are the game's music.
- **Do not touch the GOLIATH art, the shield constants or the enemy sets.** This plan is a build-and-cache change.
- **Do not touch `.worktrees/bloquec-75-migration-spec/` while the other agent may still be in it.** Read it, do not write to it, until Task 4.
- **`src/` is stdlib + pygame.** numpy stays out of `src/` except the single existing consumer in `src/audio/synth.py`.
- **Tests:** `python -m pytest tests/ --tb=no`. **Commit prefix:** `feat:` / `fix:` / `chore:` / `docs:` followed by `BLOQUE 75`.
- **Code, comments and technical docs in English.** Chat with the user in Spanish.
- **Ask before:** any push, any tag, any release, any rebuild of the `.exe` beyond the one Task 4 names.

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `src/audio/lowpass_cache.py` | **New.** Where the filtered track is cached, and how it is written. | 1 |
| `src/audio/music.py` | **Modified.** `_ensure_filtered_bgm` asks the cache first, and falls back to today's behaviour. | 1 |
| `tests/test_lowpass_cache.py` | **New.** The cache is next to the executable, never in `Assets`; it is reused, not regenerated; it is written atomically. | 1 |
| `build.spec` | **Modified.** The `_lp600.wav` data entry is gone. | 2 |
| `tests/test_build_spec_assets.py` | **New.** The spec does not bundle a generated WAV. | 2 |
| `tools/repo_budget.py` | **New.** Measures the three weights and holds the three ceilings. | 3 |
| `tests/test_repo_budget.py` | **New.** The ceilings are enforced. | 3 |
| `tools/regen_status.py` | **Modified.** Three new rows in the STATUS block. | 3 |
| `docs/arch/MAINTENANCE-CLEANUP-2026-11-02.md` | **New.** The record of round two. | 5 |
| `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md` | **Modified.** The new blocks and the new totals. | 5 |

---

### Task 1: The cache that persists

**Files:**
- Create: `src/audio/lowpass_cache.py`
- Modify: `src/audio/music.py` (`_ensure_filtered_bgm`, around line 303)
- Test: `tests/test_lowpass_cache.py`

**Interfaces:**
- Consumes: `src.audio.synth.apply_lowpass_to_wav(input_path: str, output_path: str, cutoff_hz: float = 600.0, sample_rate: int = 44100) -> bool`.
- Produces:
  - `cache_dir() -> Path | None` — the writable cache directory, or `None` when there is none.
  - `cached_filtered(cutoff_hz: float) -> Path | None` — the cached filtered track, or `None`.
  - `store_filtered(src: Path, dst: Path, cutoff_hz: float) -> bool` — filter `src` into `dst` atomically.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lowpass_cache.py`:

```python
"""The pause lowpass must keep its filtered track BETWEEN runs.

The filtered track used to be written next to its source, which in the
onefile build is `_MEIPASS` -- a temporary directory wiped when the
process exits. The 8-second computation was therefore paid on the first
pause of EVERY session, which is why a 61 MB copy was bundled into the
binary instead.

Two things have to hold:

* the cache lives next to the EXECUTABLE, so it survives the process;
* it does NOT live in a directory called `Assets`, because
  `_find_assets_dir()` probes `<exe_dir>/Assets` FIRST and a cache there
  would shadow the bundle's own assets and break the original music.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.audio import lowpass_cache  # noqa: E402


@pytest.fixture
def fake_exe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Pretend to be a frozen onefile executable in a temporary folder."""
    exe = tmp_path / "void-hunter.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    return tmp_path


def test_the_cache_lives_next_to_the_executable(fake_exe: Path):
    """The cache directory is a sibling of the executable."""
    directory = lowpass_cache.cache_dir()
    assert directory is not None
    assert directory.parent == fake_exe
    assert directory.name == lowpass_cache.CACHE_DIR_NAME


def test_the_cache_is_not_called_assets(fake_exe: Path):
    """The cache must not shadow the bundle's assets.

    `_find_assets_dir()` returns the FIRST candidate that exists, and
    `<exe_dir>/Assets` is the first one. A cache there would become the
    assets directory and the original gameplay track would vanish.
    """
    directory = lowpass_cache.cache_dir()
    assert directory is not None
    assert directory.name.lower() != "assets"


def test_the_assets_directory_is_still_found_next_to_a_cache(fake_exe: Path):
    """With a cache present, the assets directory is still the bundle's."""
    lowpass_cache.cache_dir()
    from src.audio.music import _find_assets_dir, _find_track, GAMEPLAY_TRACK

    assets = _find_assets_dir()
    assert assets is not None
    assert assets.name != lowpass_cache.CACHE_DIR_NAME
    # The real repository's track is still reachable from source.
    if _find_track(GAMEPLAY_TRACK) is None:
        pytest.skip("the gameplay track is not in this checkout")


def test_the_cached_track_is_found_and_reused(fake_exe: Path, monkeypatch):
    """A cached file is returned as-is; nothing is regenerated."""
    calls: list[str] = []
    monkeypatch.setattr(
        lowpass_cache, "store_filtered",
        lambda src, dst, cutoff: calls.append(str(dst)) or True,
    )
    directory = lowpass_cache.cache_dir()
    assert directory is not None
    target = directory / f"{lowpass_cache.TRACK_STEM}_lp600.wav"
    target.write_bytes(b"RIFFfake")

    found = lowpass_cache.cached_filtered(600.0)
    assert found is not None
    assert found == target
    assert calls == []


def test_store_filtered_writes_atomically(fake_exe: Path, tmp_path: Path):
    """The file is generated to a temporary name and moved into place."""
    src = tmp_path / "src.wav"
    src.write_bytes(b"RIFF")
    directory = lowpass_cache.cache_dir()
    assert directory is not None
    dst = directory / "out.wav"

    def fake_filter(input_path: str, output_path: str, cutoff_hz: float = 600.0,
                   sample_rate: int = 44100) -> bool:
        Path(output_path).write_bytes(b"RIFFgenerated")
        return True

    import src.audio.synth as synth

    original = synth.apply_lowpass_to_wav
    synth.apply_lowpass_to_wav = fake_filter  # type: ignore[assignment]
    try:
        ok = lowpass_cache.store_filtered(src, dst, 600.0)
    finally:
        synth.apply_lowpass_to_wav = original  # type: ignore[assignment]

    assert ok
    assert dst.read_bytes() == b"RIFFgenerated"
    # No temporary file is left behind.
    leftovers = [p.name for p in directory.iterdir() if p.name != "out.wav"]
    assert leftovers == []


def test_store_filtered_leaves_nothing_behind_on_failure(fake_exe: Path, tmp_path: Path):
    """A failed filter does not leave a half-written file."""
    src = tmp_path / "src.wav"
    src.write_bytes(b"RIFF")
    directory = lowpass_cache.cache_dir()
    assert directory is not None
    dst = directory / "out.wav"

    def failing(input_path: str, output_path: str, cutoff_hz: float = 600.0,
                sample_rate: int = 44100) -> bool:
        Path(output_path).write_bytes(b"RIFFtrunc")
        return False

    import src.audio.synth as synth

    original = synth.apply_lowpass_to_wav
    synth.apply_lowpass_to_wav = failing  # type: ignore[assignment]
    try:
        ok = lowpass_cache.store_filtered(src, dst, 600.0)
    finally:
        synth.apply_lowpass_to_wav = original  # type: ignore[assignment]

    assert not ok
    assert not dst.exists()
    assert [p.name for p in directory.iterdir()] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_lowpass_cache.py --tb=line`

Expected: FAIL with `ModuleNotFoundError: No module named 'src.audio.lowpass_cache'`.

- [ ] **Step 3: Write the implementation**

Create `src/audio/lowpass_cache.py`:

```python
"""Where the pause-screen lowpass keeps its filtered track.

The filtered track is a CACHE: the game can rebuild it from the original
in a few seconds. It used to be written next to its source, which in the
onefile build is `_MEIPASS` -- a temporary directory wiped when the
process exits. The 8-second computation was paid on the first pause of
EVERY session, and a 61 MB copy of the result was bundled into the
binary so that nobody would pay it.

Now the cache lives in a directory next to the EXECUTABLE, so it
survives the process: the filter is computed once, and every later run
finds the result.

The directory is NOT called `Assets`. `_find_assets_dir()` returns the
first candidate that exists, and `<exe_dir>/Assets` is the first one --
a cache there would shadow the bundle's own assets and the original
gameplay track would vanish.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CACHE_DIR_NAME = "_vh_cache"
TRACK_STEM = "keep kept - Lerius - soundtrack gameplay"


def _base_dir() -> Path:
    """Where the executable lives, or the project root when running from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def cache_dir() -> Path | None:
    """The writable directory the filtered track is kept in.

    `None` when there is no writable place: the executable may sit in a
    read-only directory (Program Files). The caller falls back to
    writing next to the source, which works but does not persist.
    """
    candidate = _base_dir() / CACHE_DIR_NAME
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    if not os.access(candidate, os.W_OK):
        return None
    return candidate


def filtered_name(cutoff_hz: float) -> str:
    """The file name the filtered track has for this cutoff."""
    return f"{TRACK_STEM}_lp{int(cutoff_hz)}.wav"


def cached_filtered(cutoff_hz: float) -> Path | None:
    """The cached filtered track for this cutoff, if it is already there."""
    directory = cache_dir()
    if directory is None:
        return None
    path = directory / filtered_name(cutoff_hz)
    return path if path.is_file() else None


def store_filtered(src: Path, dst: Path, cutoff_hz: float) -> bool:
    """Filter `src` into `dst`.

    The result is generated to a temporary name and moved into place, so
    an interrupted run cannot leave a truncated WAV that the next run
    would happily reuse.
    """
    from src.audio.synth import apply_lowpass_to_wav

    tmp = dst.with_name(dst.stem + ".tmp.wav")
    try:
        if not apply_lowpass_to_wav(str(src), str(tmp), cutoff_hz=cutoff_hz):
            _unlink(tmp)
            return False
        os.replace(tmp, dst)
    except Exception:
        _unlink(tmp)
        return False
    return True


def _unlink(path: Path) -> None:
    """Remove a file, ignoring the failure."""
    try:
        path.unlink()
    except OSError:
        pass
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_lowpass_cache.py --tb=line`

Expected: `7 passed`.

- [ ] **Step 5: Make `_ensure_filtered_bgm` use the cache**

In `src/audio/music.py`, replace the body of `_ensure_filtered_bgm` (the
function that starts at line 303) with:

```python
def _ensure_filtered_bgm() -> Optional[str]:
    """Generate (or load cached) lowpass-filtered version of the gameplay BGM.

    Returns the path to the filtered WAV, or None on failure.

    BLOQUE 75: the cache is looked up BEFORE anything is generated, and
    it lives next to the executable (see `src/audio/lowpass_cache.py`).
    The old behaviour -- writing next to the source -- is kept as the
    fallback for when there is no writable cache directory, so the
    filter still works in a read-only installation.
    """
    if not _pause_filter_cache["enabled"]:
        return None
    cached = _pause_filter_cache.get("filtered_path")
    if isinstance(cached, str) and os.path.exists(cached):
        return cached
    src_path = _find_track(GAMEPLAY_TRACK)
    if src_path is None:
        return None
    cutoff = get_lowpass_cutoff_hz()

    from src.audio.lowpass_cache import cache_dir, cached_filtered, filtered_name
    from src.audio.lowpass_cache import store_filtered

    # 1. the persistent cache, next to the executable
    hit = cached_filtered(cutoff)
    if hit is not None:
        _pause_filter_cache["filtered_path"] = str(hit)
        return str(hit)

    # 2. where to write it: the cache when it is writable, otherwise
    #    next to the source (today's behaviour)
    targets: list[Path] = []
    directory = cache_dir()
    if directory is not None:
        targets.append(directory / filtered_name(cutoff))
    targets.append(
        Path(os.path.dirname(str(src_path))) / filtered_name(cutoff)
    )

    for out_path in targets:
        if out_path.is_file():
            _pause_filter_cache["filtered_path"] = str(out_path)
            return str(out_path)
        try:
            t0 = time.time()
            log_path = os.path.join(os.getcwd(), "logs", "_audio_status.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(f"[lowpass] generating filtered BGM at {cutoff:.0f}Hz...\n")
            ok = store_filtered(src_path, out_path, cutoff)
            dt = time.time() - t0
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(f"[lowpass] done ({dt:.1f}s) -> {out_path} ok={ok}\n")
            if ok:
                _pause_filter_cache["filtered_path"] = str(out_path)
                return str(out_path)
        except Exception as exc:
            try:
                with open(os.path.join(os.getcwd(), "logs", "_audio_status.log"),
                          "a", encoding="utf-8") as _f:
                    _f.write(f"[lowpass] FAILED: {exc}\n")
            except Exception:
                pass
    return None
```

- [ ] **Step 6: Run the audio tests**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_bloque_58_14.py tests\test_lowpass_cache.py --tb=line`

Expected: all pass, and the pre-existing `tests/test_bloque_58_14.py` suite still does not generate a WAV next to the source.

- [ ] **Step 7: Prove the cache persists and the source is still found**

```powershell
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration'
Set-Location $wt
& $py -c "from src.audio.lowpass_cache import cache_dir, filtered_name; d=cache_dir(); print('cache dir:', d); print('nombre:', filtered_name(600.0))"
```

Expected: the cache directory is printed and its name is `_vh_cache`.

- [ ] **Step 8: Commit**

```bash
git add src/audio/lowpass_cache.py src/audio/music.py tests/test_lowpass_cache.py
git commit -m "fix: BLOQUE 75 - el cache del lowpass sobrevive a la sesion"
```

---

### Task 2: The 61 MB WAV leaves the binary

**Files:**
- Modify: `build.spec` (the `datas` list, around line 73)
- Test: `tests/test_build_spec_assets.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: a binary that does not carry a generated WAV, and a test that keeps it that way.

- [ ] **Step 1: Write the failing test**

Create `tests/test_build_spec_assets.py`:

```python
"""The binary must not carry a GENERATED file.

`keep kept - Lerius - soundtrack gameplay_lp600.wav` is not an asset: it
is the gameplay track with a 600 Hz lowpass applied, and the game
rebuilds it in a few seconds and caches it next to the executable
(`src/audio/lowpass_cache.py`). Shipping a copy of it inside the
binary cost 61 MB in every download, for a file the game can make on
its own.

The ORIGINAL tracks are assets and they stay.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build.spec"


def _bundled() -> set[str]:
    """Every file name the spec puts into the bundle."""
    text = SPEC.read_text(encoding="utf-8")
    names = set()
    for match in re.finditer(r'"([^"]+\.wav)"', text):
        names.add(match.group(1))
    for match in re.finditer(r"glob\(\"\*\"\)", text):
        names.add("*")
    return names


def test_the_spec_does_not_bundle_a_generated_wav():
    """No `_lp*.wav` is bundled."""
    offenders = [name for name in _bundled() if "_lp" in name.lower()]
    assert not offenders, (
        f"the spec still bundles generated tracks: {offenders}. The game "
        "rebuilds and caches them next to the executable."
    )


def test_the_original_tracks_are_still_bundled():
    """The real music is still in the binary."""
    names = _bundled()
    assert any("gameplay.wav" in name for name in names), (
        "the original gameplay track is no longer bundled"
    )
    assert any("pantalla principal.wav" in name for name in names), (
        "the title track is no longer bundled"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_build_spec_assets.py --tb=line`

Expected: FAIL — `the spec still bundles generated tracks: ['keep kept - Lerius - soundtrack gameplay_lp600.wav']`.

- [ ] **Step 3: Remove the entry from the spec**

In `build.spec`, delete the block that reads:

```python
        # BLOQUE 58.14: pre-generated lowpass-filtered BGM (avoid 8s
        # delay on the first pause). Generated by tools/debug_lowpass.py
        # from the original WAV at 600Hz cutoff. Safe to omit — the
        # game will regenerate on first pause if missing.
        #
        # Este es el unico *_lp*.wav que se bundlea a proposito: el resto
        # del cache lo regenera el juego solo.
        (str(PROJECT_ROOT / "Assets" / "keep kept - Lerius - soundtrack gameplay_lp600.wav"), "Assets"),
```

and leave a short note in its place:

```python
        # BLOQUE 75: the lowpass-filtered BGM is NOT bundled. It is a
        # CACHE, not an asset: the game rebuilds it in a few seconds and
        # keeps it next to the executable (src/audio/lowpass_cache.py),
        # so the cost is paid once per installation instead of 61 MB in
        # every download. numpy is already inside the bundle.
```

- [ ] **Step 4: Untrack the WAV**

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration
git rm --cached -- "Assets/keep kept - Lerius - soundtrack gameplay_lp600.wav"
```

The file stays on disk. The release line's `.gitignore` already carries
`Assets/*_lp*.wav`, so it is now untracked AND ignored.

- [ ] **Step 5: Run the test to verify it passes**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_build_spec_assets.py --tb=line`

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add build.spec tests/test_build_spec_assets.py
git commit -m "fix: BLOQUE 75 - el WAV filtrado sale del bundle y del arbol trackeado"
```

---

### Task 3: The budget that holds

**Files:**
- Create: `tools/repo_budget.py`
- Create: `tests/test_repo_budget.py`
- Modify: `tools/regen_status.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces:
  - `measure(root: Path | None = None) -> BudgetReport` with `tracked_mb`, `dist_mb`, `git_mb` and `over()`.
  - `BudgetReport.over() -> list[str]` — the ceilings that were crossed.
  - `BUDGETS: dict[str, int]` — the three ceilings, in MB.

- [ ] **Step 1: Write the failing test**

Create `tests/test_repo_budget.py`:

```python
"""The repository has a weight ceiling, and something has to enforce it.

Round one of the cleanup took the repository from 15.70 GB to 2.35 GB
and nothing noticed. Between v1.3.0 and v1.6.3, `dist/` accumulated
8.58 GB of builds that no metric ever mentioned.

The ceilings live in `tools/repo_budget.py` so that raising one is a
deliberate edit of one place -- never a quiet edit of a test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from repo_budget import BUDGETS, measure  # noqa: E402


def test_the_repository_is_inside_its_budget():
    """The repository today is under every ceiling."""
    report = measure(ROOT)
    over = report.over()
    assert not over, (
        "the repository is over its budget: "
        + "; ".join(over)
        + f" (tracked={report.tracked_mb:.1f}MB dist={report.dist_mb:.1f}MB "
        + f"git={report.git_mb:.1f}MB)"
    )


def test_every_budget_has_a_ceiling():
    """The three metrics the project watches are all bounded."""
    assert set(BUDGETS) == {"tracked", "dist", "git"}
    for name, ceiling in BUDGETS.items():
        assert ceiling > 0, f"the {name} ceiling is not a ceiling"


def test_a_crossed_ceiling_is_reported():
    """A weight over the ceiling is reported, not ignored."""
    report = measure(ROOT)
    assert report.tracked_mb > 0
    assert report.dist_mb >= 0
    assert report.git_mb > 0
    # The helper that decides whether the repository is too heavy.
    over = report.over()
    assert over == [] or all("over" in line for line in over)


def test_the_measurement_ignores_the_environment():
    """`.venv` and `.worktrees` are environment, not content.

    They are the two directories that change size for reasons that have
    nothing to do with the project, so the budget does not look at them.
    """
    from repo_budget import CONTENT_EXCLUDED

    assert ".venv" in CONTENT_EXCLUDED
    assert ".worktrees" in CONTENT_EXCLUDED
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_repo_budget.py --tb=line`

Expected: FAIL with `ModuleNotFoundError: No module named 'repo_budget'`.

- [ ] **Step 3: Write the implementation**

Create `tools/repo_budget.py`:

```python
"""Measure the weight of the repository and hold it to a budget.

Round one of the cleanup was an EVENT: the repository was measured,
pruned and archived. Nothing measured it afterwards, so 8.58 GB of
builds accumulated in `dist/` between v1.3.0 and v1.6.3 without anyone
noticing.

This is the RULE. Three weights are measured and three ceilings are
enforced by `tests/test_repo_budget.py`. The ceilings live here, so
raising one is a deliberate edit of one place.

Usage:
    python tools/repo_budget.py
    python tools/repo_budget.py --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The ceilings, in megabytes.
BUDGETS: dict[str, int] = {
    "tracked": 300,   # the tree the repository carries
    "dist": 600,      # the build output
    "git": 550,       # the history
}

# Directories that are ENVIRONMENT, not content: they change size for
# reasons that have nothing to do with the project.
CONTENT_EXCLUDED = {".venv", ".worktrees"}


@dataclass
class BudgetReport:
    """The three weights, in megabytes."""

    tracked_mb: float
    dist_mb: float
    git_mb: float

    def over(self) -> list[str]:
        """The ceilings that were crossed, as readable lines."""
        values = {
            "tracked": self.tracked_mb,
            "dist": self.dist_mb,
            "git": self.git_mb,
        }
        return [
            f"{name} is over: {value:.1f} MB > {BUDGETS[name]} MB"
            for name, value in values.items()
            if value > BUDGETS[name]
        ]

    def describe(self) -> str:
        """A readable report of the three weights."""
        lines = []
        for name, value in (
            ("tracked", self.tracked_mb),
            ("dist", self.dist_mb),
            ("git", self.git_mb),
        ):
            ceiling = BUDGETS[name]
            mark = "OVER" if value > ceiling else "ok"
            lines.append(f"{name:<8} {value:>9.1f} MB / {ceiling} MB  {mark}")
        return "\n".join(lines)


def _dir_mb(path: Path) -> float:
    """The size of a directory in megabytes."""
    if not path.is_dir():
        return 0.0
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def _tracked_mb(root: Path) -> float:
    """The size of every file the repository tracks."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
    )
    if proc.returncode != 0:
        return 0.0
    total = 0
    for chunk in proc.stdout.split(b"\0"):
        if not chunk:
            continue
        path = root / chunk.decode("utf-8", "replace")
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def measure(root: Path | None = None) -> BudgetReport:
    """Measure the three weights of the repository at `root`."""
    root = root or ROOT
    return BudgetReport(
        tracked_mb=_tracked_mb(root),
        dist_mb=_dir_mb(root / "dist"),
        git_mb=_dir_mb(root / ".git"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = measure(Path(args.root))
    if args.json:
        print(
            json.dumps(
                {
                    "tracked_mb": round(report.tracked_mb, 1),
                    "dist_mb": round(report.dist_mb, 1),
                    "git_mb": round(report.git_mb, 1),
                    "budgets": BUDGETS,
                    "over": report.over(),
                },
                indent=2,
            )
        )
    else:
        print(report.describe())
    return 1 if report.over() else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests\test_repo_budget.py --tb=line`

Expected: `4 passed`.

- [ ] **Step 5: Add the three rows to the STATUS block**

In `tools/regen_status.py`, add the import and the measurement:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_budget import measure as measure_budget
```

and inside `main()`, after `n_silos` is computed:

```python
    budget = measure_budget(ROOT)
```

and add to the `rows` dictionary:

```python
        "Peso del arbol trackeado": f"{budget.tracked_mb:.1f} MB",
        "Salida de build (dist/)": f"{budget.dist_mb:.1f} MB",
        "Historia (.git/)": f"{budget.git_mb:.1f} MB",
```

and to the `sources` dictionary:

```python
        "Peso del arbol trackeado": "`python tools/repo_budget.py`",
        "Salida de build (dist/)": "`python tools/repo_budget.py`",
        "Historia (.git/)": "`python tools/repo_budget.py`",
```

- [ ] **Step 6: Regenerate the block**

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\regen_status.py
```

Expected: `rows updated: 10` and the three new rows in the block.

- [ ] **Step 7: Commit**

```bash
git add tools/repo_budget.py tests/test_repo_budget.py tools/regen_status.py CLAUDE.md
git commit -m "feat: BLOQUE 75 - el repo tiene presupuesto de disco y un test que lo hace cumplir"
```

---

### Task 4: Merge, push and release v1.8.1

**Files:**
- Commit: `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md` (the other agent's spec, on its own branch)
- Modify: `docs/changelog/CHANGELOG_v1.x.md`, `docs/superpowers/CONTEXT.md`
- Create: `docs/handoffs/HANDOFF-BLOQUE-75-2026-11-02.md`

**Interfaces:**
- Consumes: Tasks 1-3, all merged into the release line.
- Produces: the release line at v1.8.1, the branch pushed, the tag, the release.

- [ ] **Step 1: Commit the other agent's spec on its own branch**

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-75-migration-spec'
Set-Location $wt
git add docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md docs/superpowers/CONTEXT.md
git commit -m "docs: BLOQUE 75 - spec de la migracion del pipeline de sprites (2 fases con gate)"
```

Expected: the spec is committed on `bloquec-75-migration-spec`.

- [ ] **Step 2: Merge both branches into the release line**

```powershell
$root = 'F:\AI\MM\void-hunter'
Set-Location "$root\.worktrees\bloquec-67-goliath-port"
git merge --no-ff bloquec-75-sprite-migration -m "merge: BLOQUE 75 - scaffolding de contexto multi-agente + limpieza de integridad"
git merge --no-ff bloquec-75-migration-spec -m "merge: BLOQUE 75 - spec de la migracion del pipeline de sprites"
```

Expected: both merges succeed without conflicts. If there IS a conflict in
`docs/superpowers/CONTEXT.md`, resolve it by keeping BOTH entries (the
prompt row and the spec row).

- [ ] **Step 3: Rebuild the binary from the merged release line**

```powershell
$root = 'F:\AI\MM\void-hunter'
Set-Location "$root\.worktrees\bloquec-67-goliath-port"
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
& $py -m PyInstaller --noconfirm build.spec
```

Expected: a successful build. The result is a onefile `.exe` of about
**217 MB** (it was 278 MB with the WAV inside).

- [ ] **Step 4: Verify the binary**

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
$exe = "$wt\dist\void-hunter.exe"
& $exe --check
& $exe --boss goliath --easy --duration 25
```

Expected: `--check` prints `15 scenes, 18 waves, 4 bosses` and exits 0;
the boss fight exits 0.

- [ ] **Step 5: Prove the pause filter works and caches**

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
$exe = "$wt\dist\void-hunter.exe"
$cache = "$wt\_vh_cache"
if (Test-Path $cache) { Move-Item $cache "F:\AI\MM\_vh_archive_2026-10-30\vh_cache_stale" -Force }
& $exe --boss goliath --easy --duration 25
Get-ChildItem $cache -ErrorAction SilentlyContinue | Select-Object Name, Length
```

Expected: the cache directory appears next to the executable with
`keep kept - Lerius - soundtrack gameplay_lp600.wav` inside it.

- [ ] **Step 6: Update the changelog and write the handoff**

In `docs/changelog/CHANGELOG_v1.x.md`, add a `v1.8.1` entry that
records: the pause lowpass cache that persists, the 61 MB that left the
binary, the disk budget with its ceilings, and the BLOQUE 75 handoff.

Create `docs/handoffs/HANDOFF-BLOQUE-75-2026-11-02.md` with: what the
branch did, what the two agents produced, the budget and its ceilings,
how to verify, and what comes next (the BLOQUE 75 implementation).

- [ ] **Step 7: Commit and push**

```powershell
Set-Location 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
git add -A
git commit -m "docs: BLOQUE 75 - release v1.8.1: cache persistente del lowpass, binario 217 MB y presupuesto de disco"
git push origin bloquec-67-goliath-port
git push origin bloquec-75-sprite-migration
git push origin bloquec-75-migration-spec
```

Expected: three successful pushes.

- [ ] **Step 8: Tag and publish**

```powershell
Set-Location 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
git tag -a v1.8.1 -m "BLOQUE 75: cache persistente del lowpass de pausa, el WAV generado sale del bundle (278 -> 217 MB), presupuesto de disco con test, y el handoff de contexto entre agentes."
git push origin v1.8.1
```

Then the release, following the project's flow:

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
Compress-Archive -Path "$wt\dist\void-hunter.exe" -DestinationPath "F:\AI\MM\_vh_archive_2026-10-30\VoidHunter-v1.8.1-win64.zip" -Force
gh release create v1.8.1 "F:\AI\MM\_vh_archive_2026-10-30\VoidHunter-v1.8.1-win64.zip" --title "Void Hunter v1.8.1" --notes "BLOQUE 75: cache persistente del lowpass de pausa, el WAV generado sale del bundle (278 -> 217 MB), presupuesto de disco con test que lo hace cumplir, y el handoff de contexto entre agentes." --latest
```

Expected: the release exists with the zip attached, marked as latest.

---

### Task 5: The closing pass

**Files:**
- Create: `docs/arch/MAINTENANCE-CLEANUP-2026-11-02.md`
- Modify: `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md`

**Interfaces:**
- Consumes: Task 4 (the merged release line, the pushed tag).
- Produces: a baseline that is the exact source of v1.8.1, and a repository without the two dead worktrees.

- [ ] **Step 1: Re-cut the baseline from the merged release line**

```powershell
$root = 'F:\AI\MM\void-hunter'
$base = 'F:\AI\MM\void-hunter-baseline'
Set-Location "$root\.worktrees\bloquec-67-goliath-port"
git archive --format=tar HEAD -o "$env:TEMP\vh_v181.tar"
tar -xf "$env:TEMP\vh_v181.tar" -C $base
```

Expected: the baseline now holds the v1.8.1 source, including the
`tools/repo_budget.py` tool and the cache module.

- [ ] **Step 2: Verify the baseline**

```powershell
Set-Location "$root\.worktrees\bloquec-67-goliath-port"
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline --ref HEAD
```

Expected: `CLEAN COPY OK`, exit 0.

- [ ] **Step 3: Remove the two dead worktrees**

```powershell
$root = 'F:\AI\MM\void-hunter'
git -C $root worktree remove "$root\.worktrees\bloquec-75-sprite-migration"
git -C $root worktree remove "$root\.worktrees\bloquec-75-migration-spec"
git -C $root worktree prune
```

Expected: two worktrees gone, ~620 MB reclaimed. The release worktree
stays: it is where the release line lives.

- [ ] **Step 4: Write the round-two record**

Create `docs/arch/MAINTENANCE-CLEANUP-2026-11-02.md` with the
before/after numbers of round two, the three ceilings, the cache
design, and the pointer to the round-one document.

- [ ] **Step 5: Update the archive manifest**

Add the new blocks to `F:\AI\MM\_vh_archive_2026-10-30\MANIFEST.md`:
`vh_cache_stale/` (if it exists) and the new totals.

- [ ] **Step 6: Commit**

```powershell
Set-Location "$root\.worktrees\bloquec-67-goliath-port"
git add -A
git commit -m "docs: BLOQUE 75 - segunda ronda de limpieza: cache persistente, binario de 217 MB y presupuesto de disco"
git push origin bloquec-67-goliath-port
```

- [ ] **Step 7: The final gates**

```powershell
$wt = 'F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port'
$py = 'F:\AI\MM\void-hunter\.venv\Scripts\python.exe'
Set-Location $wt
& $py -m pytest tests/ --tb=no
& $py -m mypy src\anim\
& $py tools\sprite_pipeline\verify_contract.py goliath
& $py main.py --check
& $py tools\repo_budget.py
$env:PYTHONUTF8 = '1'
& $py "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" --perfil=lite .
```

Expected: no new failures, mypy clean, `CONTRACT OK`, the game boots,
every budget line says `ok`, and `SF COMPLIANCE (lite): 7/7`.

---

## Self-Review

**1. Spec coverage.** §4.1 (the persistent cache) → Task 1. §4.2 (the
binary shrinks) → Task 2. §4.3 (the budget) → Task 3. §4.4 (merge,
push, release) → Task 4. §4.5 (the closing pass) → Task 5. §4.6 (the
gates) → Task 5 Step 7. §5 (what is not touched) → the Global
Constraints. §6 (the risks) → the tests in Tasks 1 and 2. §7 (rollback)
→ the moves in Task 5.

**2. Placeholder scan.** No `TBD`, no `TODO`, no "similar to Task N".
Every code step carries the actual code. The one judgement call is
Task 4 Step 2's conflict resolution, and it states exactly what to do.

**3. Type consistency.** `lowpass_cache.cache_dir() -> Path | None`,
`cached_filtered(cutoff_hz: float) -> Path | None`,
`store_filtered(src: Path, dst: Path, cutoff_hz: float) -> bool` are the
same signatures in the module, in `music.py` and in the test.
`repo_budget.measure(root: Path | None = None) -> BudgetReport` and
`BudgetReport.over() -> list[str]` are the same in the module and in the
test. `BUDGETS: dict[str, int]` has exactly the three keys the test
asserts: `tracked`, `dist`, `git`.

**4. The one risk this plan cannot test.** Whether the merged release
line builds and publishes cleanly is proven by running it (Task 4), not
by a test. The plan sequences it so that the merge happens BEFORE the
build, and the build before the tag, so a failure at any step leaves
the published v1.8.0 untouched.
