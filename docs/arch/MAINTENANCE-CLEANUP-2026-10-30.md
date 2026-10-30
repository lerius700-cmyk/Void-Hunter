# Repository cleanup and pristine baseline — 2026-10-30

**What this document is:** the record of a repository cleanup, where the
removed material went, how to get it back, and how to prove that a copy
of the tree is uncontaminated.

**Date:** 2026-10-30
**Branch where the cleanup was executed:** `bloquec-75-sprite-migration`
**Base:** `bloquec-67-goliath-port` (v1.8.0, the release line)

---

## 1. Why

The repository weighed **15.70 GB**. The game inside it weighed about
**50 MB**. The difference was build output from versions of the project
that no longer exist, plus a disk cache that had been committed to git by
mistake.

Two things made it worth doing rather than tolerating:

1. **Nothing measured it.** There was no metric, no truth anchor and no
   test that would have noticed a 13 GB regression. Every build since
   v1.3.0 added roughly 424 MB to `dist/`, and nothing ever took it out.
2. **The project needed a clean copy** to implement the BLOQUE 75
   migration. That work touches the sprite runtime of every enemy set.
   It needs a starting point that is provably free of unrelated files,
   and a restore point that cannot itself have been damaged by the work.

## 2. The result

| | Before | After |
|---|---:|---:|
| Repository root on disk | 15.70 GB | **2.35 GB** |
| Archived and recoverable | 0 | **13.95 GB** |
| Pristine baseline (outside the repo) | 0 | 264.8 MB, 2,197 files |
| Tracked tree (`master`) | 331.7 MB | 331.7 MB (unchanged) |
| Copies of the v1.8.0 binary | 2 | 1 |

## 3. The archive

Everything that left the working tree went here. **Nothing was
deleted** — every removal is a move, and because the source and the
destination are on the same `F:` volume, every move is an instant
rename.

```
F:\AI\MM\_vh_archive_2026-10-30\
```

| Block | What it was | Size |
|---|---|---:|
| `dist_old_builds/` | 24 entries of `dist/`: 11 `.exe` and 11 `.zip` of v1.3.0 → v1.7.2, plus the onedir build and its logs | 8,503.6 MB |
| `dist_release_wt/` | the `dist/` of the release worktree | 1,932.7 MB |
| `release_v1.1.x_zips/` | 5 zips of the dead v1.1.1 → v1.1.6 line | 1,551.7 MB |
| `build_cache/` | the PyInstaller caches of the root and of the release worktree | 717.0 MB |
| `archive_v1.6.2/` | the duplicated v1.6.2 `.exe` | 424.5 MB |
| `baseline_pollution/` | the first baseline cut, dirtied by running the suite in it (kept as evidence — see §6) | 337.5 MB |
| `baseline_release_line_v1.8.0/` | the exact git tree of `bloquec-67-goliath-port` (v1.8.0) | 271.1 MB |
| `srcrefs_scratch/` | the scratch folder of the 2026-10-29 session: diagnostic builds, stray assets | 207.9 MB |
| `assets_intermediates/` | `_strips/`, `_base/`, `_seed/`, `_test/`, `_mask/`, `gifs/` — the 1024px sources the 16-bit frames are baked from | 150.6 MB |
| `playtest_out_logs/` | verification captures and `logs/` | 115.1 MB |
| `release_captures/` | 112 verification captures of the title screen and the background variants, loose in `release/` | 7.1 MB |
| `generated_lp_wavs/` | the `_lp8000.wav` the suite used to generate on every run | 60.9 MB |
| `tracked_obsolete_captures/` | the 81 captures and the log README that were still tracked in git | 7.2 MB |

**Restoring a block** is one move:

```powershell
Move-Item F:\AI\MM\_vh_archive_2026-10-30\dist_old_builds F:\AI\MM\void-hunter\dist -Force
```

## 4. The pristine baseline

```
F:\AI\MM\void-hunter-baseline\
```

Cut with `git archive` from `bloquec-75-sprite-migration`: **2,197
files, 264.8 MB, no `.git`, no history, no ignored file, and not one
file that is not in the tree.** It is both the place to implement the
migration and the restore point if the migration breaks something.

The exact v1.8.0 release tree is still reproducible at any time:

```powershell
git -C F:\AI\MM\void-hunter archive --format=tar bloquec-67-goliath-port
```

### Proving a copy is uncontaminated

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline
```

```
tree=F:\AI\MM\void-hunter-baseline ref=bloquec-75-sprite-migration checked=2197
CLEAN COPY OK
```

The tool compares the directory against the git tree: same file set,
same bytes. It separates three things:

- **missing / mismatched** — the tree declares a file and the copy does
  not have it, or has it with different bytes. Always damage.
- **extra** — a file that is not in the tree and that git does NOT
  ignore. Real contamination.
- **ignored-extra** — a file that is not in the tree but that the
  repository's `.gitignore` ignores (`__pycache__/`, `logs/`). Runtime
  litter, reported with its total size.

The line is the repository's own `.gitignore`, and it turns out to
matter: `Assets/*_lp*.wav` has been ignored by the release line since
BLOQUE 74, so the generated WAV is a byproduct, not source.

## 5. The binary

There was exactly one binary and it is named by its hash:

```
F:\AI\MM\void-hunter\dist\void-hunter-v1.8.0.exe
278.0 MB
SHA256 DF97122791327485799186EDCC66DB050F0AA2CB9EE3B99CF2FB4E6222F081BB
```

The release worktree carried a **byte-identical** copy of the same
build. It was archived with the rest of that worktree's `dist/`, and the
`STATUS:GENERATED` row — and `tools/regen_status.py`, which writes it —
now name the survivor. `tests/test_status_truth_anchors.py` asserts that
the anchor resolves and that the generator agrees with the block, so the
two cannot drift apart again.

## 6. Three things that were found and fixed on the way

**The suite wrote 61 MB into the working tree, every run.**
`tests/test_bloque_58_14.py` clamped the lowpass cutoff to 8000 Hz and
left it there — the cutoff lives in a module-level cache, so the value
escaped the test. The next test that exercised the pause filter then
wrote the filtered track **next to the source**, generating
`Assets/keep kept - Lerius - soundtrack gameplay_lp8000.wav` inside
whatever tree the suite ran in. That is how the file ended up committed
on `master` in the first place. An autouse fixture now restores the
cache, and the WAV is no longer generated.

**81 obsolete files were still tracked.** The project's `.gitignore` has
declared `tools/playtest_out/` and `logs/` out of the repository for a
long time, but the rule only applies to files that are NOT tracked, and
those 81 (80 verification captures from old BLOQUEs and one README) had
been committed before the rule existed. They were untracked with
`git rm --cached`; the content is in `tracked_obsolete_captures/`.

**The restore point has to stay out of the way.** Running anything
inside the baseline dirties it. The rule this established: the restore
point is cut clean and never run in; the sandbox is a separate worktree.

## 7. What was deliberately NOT touched

| Thing | Why |
|---|---|
| `.worktrees/bloquec-75-migration-spec/` | the second agent's worktree — it was working there throughout |
| `.venv/` | needed to run anything |
| `.git/` | rewriting history would change every commit hash and orphan the published tags `v1.7.0`, `v1.7.2` and `v1.8.0` |
| `release/videos/` | the 4 standalone cinematics — user-facing |
| `dist/void-hunter-v1.8.0.exe` | the release binary |
| the four `Assets/*.wav` | decision: 281 MB of the tracked tree stay. The release line's own `.gitignore` already treats `*_lp*.wav` as generated, but `_lp600.wav` has been tracked since before that rule, and keeping it was the explicit call |
| `master` | the old line. Its working tree was restored untouched after the moves; it still tracks 89 obsolete files of its own, and untracking them there is a separate change on a line that receives no merges |

## 8. How to check the repo is still honest

```powershell
# the suite
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests/ --tb=no

# the types
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\anim\

# the sprite contract
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\verify_contract.py goliath

# the game boots
F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check

# the structure
$env:PYTHONUTF8 = '1'
F:\AI\MM\void-hunter\.venv\Scripts\python.exe "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" --perfil=lite .

# the baseline is still uncontaminated
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline
```

`PYTHONUTF8=1` is required for the auditor: it reads the files with the
system encoding and dies on the repository's Spanish text otherwise.
