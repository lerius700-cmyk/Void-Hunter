# Repo hygiene: prune 15.7 GB of dead build artifacts and cut a pristine baseline

**Date:** 2026-10-30
**Status:** APPROVED BY USER (design), pending execution
**Branch:** `bloquec-75-sprite-migration` (active work branch)
**Base:** `bloquec-67-goliath-port` (v1.8.0, the release line)
**Author:** Lerius (intent) + Mavis (draft)

---

## 1. Problem

`F:\AI\MM\void-hunter` weighs **15.70 GB**. The game inside it weighs
**46 MB**. The rest is build output from versions of the project that no
longer exist, plus one disk cache that was committed to git by mistake.

Two facts make this worth doing rather than tolerating:

1. **The repository does not know what it weighs.** There is no metric, no
   truth anchor, no test that would notice a 13 GB regression. Every build
   since v1.3.0 added ~424 MB to `dist/` and nothing ever took it out.
2. **The project needs a clean copy to implement the BLOQUE 75 migration.**
   That migration touches the sprite runtime of every enemy set. It needs
   a starting point that is provably free of unrelated files, and it needs
   a restore point that cannot itself have been damaged by the work.

The same discipline that produced the sprite pipeline (measure, don't
assume; assert, don't hope) applies here: the sizes below were measured,
not estimated, and every claim in this document is reproducible with the
command listed next to it.

---

## 2. Measurements (the truth anchors)

All measured on 2026-10-30 with
`Get-ChildItem <path> -Recurse -File -Force | Measure-Object Length -Sum`.

### 2.1 Top level of the repository root

| Entry | Size | Nature |
|---|---:|---|
| `dist/` | 8.58 GB | 25 entries: 11 `.exe`, 11 `.zip`, 1 onedir, `logs/` |
| `.worktrees/` | 3.39 GB | 3 worktrees + scratch |
| `release/` | 1.53 GB | 5 zips from the dead v1.1.x line + `videos/` |
| `.git/` | 0.50 GB | history (see 2.3) |
| `Assets/` | 0.46 GB | 327 MB tracked + 150 MB ignored intermediates |
| `build/` | 0.42 GB | PyInstaller cache, 2026-10-22 (v1.6.x era) |
| `_archive_v1.6.2/` | 0.42 GB | duplicated v1.6.2 `.exe` |
| `.venv/` | 0.29 GB | needed |
| `tools/` | 0.07 GB | `playtest_out/` is 72 MB of it |
| `logs/` | 0.04 GB | `patterns.log` alone is 40 MB |
| **Total** | **15.70 GB** | |

### 2.2 The tracked tree is small

`git ls-files` in the repository root (`master`) → **2,282 files, 331.7 MB**.
The release line is slightly smaller: `git ls-tree -r -l
bloquec-67-goliath-port` → **2,267 files, 271 MB** (master carries the four
`Assets/sounds/*.wav` of the BLOQUE 72 weapon system, which the v1.4.0
port reverted, plus one extra `_lp8000.wav`).

Broken down (measured on `master`):

| Category | Size | Files |
|---|---:|---:|
| `Assets/*.wav` | 281.27 MB | 13 |
| `Assets/` (rest) | 12.81 MB | 15 |
| `Assets/video/` (cinematic frames) | 9.82 MB | 662 |
| `Assets/sprites/` (the 16-bit game art) | 8.07 MB | 622 |
| `Assets/sprites/redesign/` (1024px AI bases) | 7.17 MB | 465 |
| `tools/` | 7.15 MB | 245 |
| `player_ships/*_base.png` (art sources) | 2.18 MB | 5 |
| `docs/` | 1.26 MB | 57 |
| `src/` | 1.14 MB | 87 |
| `tests/` | 0.83 MB | 99 |

**281 of the 331.7 MB are four WAV files.** The actual game — code, tests,
docs and every pixel of runtime art — is **~50 MB**.

Of the four WAVs, two are **generated output, not input**:
`keep kept - Lerius - soundtrack gameplay_lp600.wav` and `_lp8000.wav`
(60.94 MB each). `src/audio/music.py::_ensure_filtered_bgm()` writes them
next to the source the first time the pause lowpass runs, and reuses them
if they exist. They were committed by mistake and now ship inside every
`.exe`.

> **User decision: they stay.** The 122 MB in the repo and in every binary
> is accepted. This document therefore plans around them: the baseline
> copy is 271 MB, and the `.exe` stays at 278 MB. The option of
> untracking them was measured and explicitly declined.

### 2.3 Git history is mostly those same WAVs

`git rev-list --objects --all | git cat-file --batch-check` → **407 MB of
blobs across all branches, of which 282.21 MB are `.wav`**.

The history is NOT rewritten. Rewriting it would change every commit hash
and orphan the published tags `v1.7.0`, `v1.7.2` and `v1.8.0`, which
have GitHub releases attached to them. The `.git` directory stays as it is.

### 2.4 The release worktree carries its own build output

`F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port` weighs 2.57 GB:
`dist/` 1.93 GB, `build/` 286 MB, `Assets/` 321 MB (a full git checkout).

### 2.5 Two identical binaries

`dist/void-hunter-v1.8.0.exe` (repo root) and
`.worktrees/bloquec-67-goliath-port/dist/void-hunter.exe` are
**byte-identical**:

```
SHA256 = DF97122791327485799186EDCC66DB050F0AA2CB9EE3B99CF2FB4E6222F081BB
```

### 2.6 The other agent is already working

`.worktrees/bloquec-75-migration-spec` exists (337 MB). It is the second
agent's worktree. **It is not touched by this plan.** Neither is
`.worktrees/bloquec-75-sprite-migration` (this branch's worktree) beyond
the scratch folder described in 4.2.

---

## 3. Decisions (taken by the user, 2026-10-30)

| # | Decision | Answer |
|---|---|---|
| D1 | The two generated `_lp*.wav` (122 MB) | **Keep them tracked.** Status quo accepted. |
| D2 | `dist/` contents | **Keep only `void-hunter-v1.8.0.exe`**; archive the other 24 entries. |
| D3 | The clean copy for the migration | **`git archive` of the release line**: tracked files only, no `.git`, no history. |
| D4 | Where the unused stuff goes | **Outside the repository**: `F:\AI\MM\_vh_archive_2026-10-30\`. |

Plus the design approval: consolidate the duplicate binary, and document
the whole thing in the repo.

---

## 4. The design

### 4.1 Principle: nothing is deleted, and the backup comes first

Two invariants drive every step:

- **Nothing is deleted.** Everything removed from the working tree is
  *moved* to the archive folder. The harness blocks `Remove-Item
  -Recurse -Force` anyway, and moving is the safer operation: a wrong
  move is undone by moving it back.
- **The baseline is cut BEFORE anything is touched.** A restore point
  created after the cleanup cannot prove that the cleanup did not damage
  what it was supposed to preserve.

Every move is within the `F:` volume, so each one is a rename: **instant,
no copy, no 13 GB of I/O**.

### 4.2 Phase 1 — The pristine baseline

```
F:\AI\MM\void-hunter-baseline-v1.8.0\
```

Produced by `git archive bloquec-67-goliath-port`, extracted so the result
is a plain directory tree:

- 2,267 files (the release line's tree, to be verified against
  `git ls-tree -r`)
- 271 MB
- **No `.git`. No history. No ignored file. No file that is not in the
  release tree.**

This directory is both the migration's starting point and the restore
point. If BLOQUE 75 damages the runtime, the tree comes back from here.

**Verification (all four must pass):**

1. **Completeness** — the file count matches `git ls-tree -r --name-only
   bloquec-67-goliath-port`, and no path outside it appears.
2. **Integrity** — the SHA256 of every extracted file equals the SHA256
   of the corresponding git blob.
3. **It boots** — `python main.py --check` from the baseline prints
   `15 scenes, 18 waves, 4 bosses`.
4. **It tests** — `python -m pytest tests/ --tb=no` from the baseline
   gives 2,886 pass + 1 pre-existing fail + 6 skipped.

Checks 3 and 4 run with the repository's own venv
(`F:\AI\MM\void-hunter\.venv\Scripts\python.exe`); the baseline has no
venv of its own, because a venv is not part of the source.

### 4.3 Phase 2 — The archive

```
F:\AI\MM\_vh_archive_2026-10-30\
├── MANIFEST.md                  ← what each block is, why, how to restore
├── dist_old_builds/             ← 24 entries, v1.3.0→v1.7.2          8.30 GB
├── release_v1.1.x_zips/         ← 5 zips, dead line                 1.53 GB
├── dist_release_wt/             ← the release worktree's dist/       1.93 GB
├── build_cache/                 ← build/ at root and in the wt       0.72 GB
├── archive_v1.6.2/              ← duplicated v1.6.2 exe              0.42 GB
├── srcrefs_scratch/             ← this session's archived scratch    0.21 GB
├── assets_intermediates/        ← _strips/, _base/, _seed/, _test/   0.15 GB
└── playtest_out_logs/           ← verification captures + logs       0.11 GB
```

`MANIFEST.md` records, per block: the original path, the size, the date
and the reason. Restoring is one `Move-Item` back.

### 4.4 Phase 3 — One canonical binary

`dist/void-hunter-v1.8.0.exe` (repo root) is kept. The byte-identical
copy in the release worktree is archived with the rest of that worktree's
`dist/`.

The `STATUS:GENERATED` row for the build points at
`../bloquec-67-goliath-port/dist/void-hunter.exe`. Two things follow, and
the second one is easy to miss:

1. The row is updated to point at the surviving copy
   (`dist/void-hunter-v1.8.0.exe`) and to carry the SHA256, so the truth
   anchor of the block still resolves and now identifies exactly one
   binary.
2. **`tools/regen_status.py` must be updated in the same change.** It
   writes that row from `RELEASE_WT / "dist" / "void-hunter.exe"`, so
   regenerating the block with the tool as-is would reintroduce the
   broken path. The generator and the block move together, or the block
   lies again the next time anyone regenerates it.

### 4.5 Phase 4 — The repository still works

The cleanup touches only ignored files, so git is unaffected by
construction. That claim is not trusted, it is checked: suite, mypy, the
sprite contract guard, `main.py --check`, and `sf-sm-doctor` all run
afterwards.

### 4.6 Phase 5 — Documentation

- `docs/arch/MAINTENANCE-CLEANUP-2026-10-30.md` in the repository: what
  was archived, why, the hashes, and the one-command restore procedure.
- A copy of the same manifest inside the archive folder, so the record
  survives even if the repository does.
- `.synapse` updated (objective + last successful action + verification
  timestamp) and the `STATUS:GENERATED` block regenerated with
  `tools/regen_status.py`.

### 4.7 Phase 6 — Gates

| Gate | Tool | When | Pass condition |
|---|---|---|---|
| Structural integrity | `sf-sm-doctor --perfil=lite` | before and after | 7/7, exit 0, 0 findings |
| Root-cause debugging | `systematic-debugging` | if anything breaks | cause identified before any fix; no patch without a stated cause |
| Diff review | `gstack-review` | before landing the doc commit | no blocking finding |
| Completion proof | `verification-before-completion` | last step | the final table, every row with its command |

---

## 5. What is explicitly NOT touched

| Thing | Why |
|---|---|
| `.worktrees/bloquec-75-migration-spec/` | the other agent's worktree |
| `.venv/` | needed to run anything |
| `.git/` | rewriting history would orphan the published tags |
| `release/videos/` | 4 mp4, the standalone cinematics — user-facing |
| `dist/void-hunter-v1.8.0.exe` | the release binary |
| the 4 `.wav` files | decision D1 |
| `Assets/` tracked content | it is the game |
| `master` and `bloquec-67-goliath-port` | no commit, no merge without the user asking |

---

## 6. Expected outcome

| Metric | Before | After |
|---|---:|---:|
| Repository root on disk | 15.70 GB | **~2.3 GB** |
| Archived and recoverable | 0 | **~13.4 GB** |
| Baseline copy (outside the repo) | 0 | 271 MB, 2,267 files |
| Tracked tree (`master`) | 331.7 MB | 331.7 MB (unchanged) |
| Binary copies of v1.8.0 | 2 | 1 |

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| A move lands in the wrong place | every move is verified: source gone, destination present, byte count equal |
| The baseline is subtly broken | four independent checks (4.2), run BEFORE the cleanup |
| The cleanup breaks the runtime | the suite and the contract guard run after; nothing is deleted, only moved |
| The other agent is mid-work | its worktree is not touched; the archive moves only ignored files of the root and of the release worktree |
| A future build re-creates the bloat | the archive's manifest + the repo doc state what was removed and why; `sf-sm-doctor` keeps the structural invariants |

---

## 8. Rollback

Every step is reversible without git:

```powershell
# restore one block
Move-Item F:\AI\MM\_vh_archive_2026-10-30\dist_old_builds F:\AI\MM\void-hunter\dist -Force

# restore the repository wholesale
Move-Item F:\AI\MM\_vh_archive_2026-10-30\build_cache F:\AI\MM\void-hunter\build -Force
```

And the full source state, independent of the archive:

```powershell
git -C F:\AI\MM\void-hunter worktree add F:\AI\MM\void-hunter-baseline-v1.8.0 bloquec-67-goliath-port
```
