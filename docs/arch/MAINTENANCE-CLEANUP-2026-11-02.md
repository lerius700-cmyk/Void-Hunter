# Repository hygiene, round two — 2026-11-02

**What this document is:** the record of the second cleanup round, which
followed `MAINTENANCE-CLEANUP-2026-10-30.md` (round one: 15.70 GB →
2.35 GB).

**Release:** v1.8.1, tag `v1.8.1`, on `bloquec-67-goliath-port`.

---

## 1. What round two changed

| | Before | After |
|---|---:|---:|
| `.exe` (onefile) | 278.0 MB | **220.2 MB** |
| Tracked tree | 331.7 MB | **204.0 MB** |
| Pause filter, first pause of a session | 8 s, every session | **8 s once, then cached** |
| Repository root | 15.70 GB | **2.35 GB** |

Round one was an EVENT: the repository was measured, pruned and archived.
Round two is the RULE: three weights are measured, three ceilings are
enforced by a test, and the numbers are rows of the `STATUS:GENERATED`
block, so the weight of the project is visible in the file every agent
opens.

## 2. The cache that persists

`src/audio/lowpass_cache.py` (new) owns where the filtered gameplay
track lives: a directory next to the executable, so it survives the
process. It used to be written next to its source, which in the onefile
build is `_MEIPASS` — a temporary directory wiped when the process exits.
The 8-second computation was paid on the first pause of EVERY session,
and a 61 MB copy of the result was bundled into the binary so that
nobody would pay it.

The cache directory is NOT called `Assets`. `_find_assets_dir()` returns
the first candidate that exists, and `<exe_dir>/Assets` is the first one:
a cache there would become the assets directory and the original music
would vanish. There is a test for exactly that.

Measured on the shipped binary: 1st run 6.3 s (generates and caches),
2nd run 0.0 s (reuses).

## 3. The binary that shrank

`build.spec` no longer bundles `gameplay_lp600.wav` and the file is
untracked. numpy was already inside the bundle, so the pause filter
keeps working. `tests/test_build_spec_assets.py` keeps it that way: no
literal `*_lp*.wav` entry, and the glob over `Assets/*` keeps excluding
them.

## 4. The budget that holds

| Metric | How it is measured | Ceiling | Now |
|---|---|---:|---:|
| Tracked tree | every path `git ls-files` names | 300 MB | 204.0 MB |
| Build output | `dist/` | 600 MB | 220.2 MB |
| History | `.git/` | 550 MB | 504.0 MB |

The ceilings live in `tools/repo_budget.py`, not in the test: raising one
is a deliberate edit of one place. The `dist/` ceiling is the one that
catches the failure that actually happened — 8.58 GB of accumulated builds
between v1.3.0 and v1.6.3, unnoticed for months.

## 5. The archive

Everything that left the working tree was MOVED, never deleted, to
`F:\AI\MM\_vh_archive_2026-10-30\`. The manifest there lists every
block, its original path, its size and why it went.

## 6. What was deliberately NOT done

| Thing | Why |
|---|---|
| The git history was not rewritten | 122 MB of it are generated blobs that could be purged, but every commit hash would change and the published tags `v1.7.0`, `v1.7.2` and `v1.8.0` would be orphaned |
| The two real tracks (91 MB + 68 MB) | they are the game's music |
| `master` | the old line (v1.6.3); it receives no merges |
| The GOLIATH art, the shield constants, the enemy sets | this was a build-and-cache change, not an art change |

## 7. The baseline

`F:\AI\MM\void-hunter-baseline\` is the restore point of this release:
the tree of `bloquec-67-goliath-port` at the v1.8.1 commit, 2,207 files,
204.0 MB, no `.git` and no history.

```powershell
python tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline --ref HEAD
```

The tool compares a directory against a git tree — same file set, same
content — and separates real contamination from runtime litter using the
repository's own `.gitignore`.
