"""BLOQUE 75 (follow-up 1.13): the runtime has no path of another machine.

The runtime used to fall back to `D:/AI/void-hunter/logs/_sub_boss.log`
when it could not write the log where it was launched from. That path
names a drive that does not exist on most machines -- and on the machine
where it DOES exist, it points at a DIFFERENT project: the log of a
sub-boss spawn landed in somebody else's tree.

The rule this file enforces is narrow on purpose: it is about the
RUNTIME (`src/`), the code that has to run on the machine of whoever
downloads the .exe. The dev scripts under `tools/` have their own
absolute paths (25 of them, all of the same machine); they are scripts
of one-off BLOQUEs, they are not shipped, and they are NOT this check's
business. Listing them here would make a check that cannot be acted on.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# An absolute Windows path inside a string literal: a drive, a colon and
# a separator.
ABSOLUTE_WINDOWS_PATH = re.compile(r"""["']([A-Za-z]:[/\\][^"']*)["']""")


def _runtime_files() -> list[Path]:
    return sorted((ROOT / "src").rglob("*.py"))


def test_the_runtime_has_no_absolute_path_of_another_machine() -> None:
    """Not one string in `src/` names an absolute path.

    The runtime travels inside the .exe and runs on the machine of
    whoever downloads it. A path that names a drive of the machine where
    it was written is a path that cannot work anywhere else.
    """
    offenders: list[tuple[str, str]] = []
    for path in _runtime_files():
        text = path.read_text(encoding="utf-8")
        for match in ABSOLUTE_WINDOWS_PATH.finditer(text):
            offenders.append((path.relative_to(ROOT).as_posix(), match.group(1)))
    assert not offenders, (
        "the runtime names absolute paths of another machine: "
        f"{offenders} -- they cannot resolve on any other tree"
    )


def test_the_sub_boss_log_resolves_under_this_tree() -> None:
    """The sub-boss log lands in THIS tree, or nowhere.

    The check is on the SOURCE: the path has to be built from the
    module's own location. A path that is resolved from the CWD moves
    with the shell that launched the game; a path that is absolute names
    a machine.
    """
    source = (ROOT / "src" / "ui" / "gameplay_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "_sub_boss.log" in source
    assert "Path(__file__).resolve().parent.parent.parent" in source, (
        "the sub-boss log is not resolved from the module's own location"
    )
    for match in ABSOLUTE_WINDOWS_PATH.finditer(source):
        raise AssertionError(
            f"the runtime still names an absolute path: {match.group(1)!r}"
        )
