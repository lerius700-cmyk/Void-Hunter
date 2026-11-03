# HANDOFF — BLOQUE 75: contexto entre agentes, cache persistente y presupuesto de disco

**Date:** 2026-11-02
**Release:** v1.8.1 (tag `v1.8.1`, sobre `bloquec-67-goliath-port`)
**Branches merged:** `bloquec-75-sprite-migration` · `bloquec-75-migration-spec`

---

## 1. What this release is

Three things that do not belong together but crossed in the same cleanup
round, plus the handoff mechanism that made the round possible.

| | Before | v1.8.1 |
|---|---:|---:|
| `.exe` (onefile) | 278.0 MB | **220.2 MB** |
| Repository root | 15.70 GB | **2.35 GB** |
| Tracked tree | 331.7 MB | **203.9 MB** |
| Pause filter, first pause of a session | 8 s, every session | **8 s once, then cached** |

## 2. The cache that persists

`src/audio/lowpass_cache.py` (new) owns where the filtered gameplay track
lives. It is a directory next to the executable, never `Assets`:

> `_find_assets_dir()` returns the FIRST candidate that exists, and
> `<exe_dir>/Assets` is the first one. A cache there would shadow the
> bundle's own assets and the original music would vanish.

The filtered track is written to a temporary name and moved into place,
so an interrupted run cannot leave a truncated WAV that the next run
would reuse. When the executable sits in a read-only directory, the
filter falls back to writing next to the source: it still works, it just
does not persist.

Measured: 1st call 6.3 s (generates) → 2nd call 0.0 s (reuses).

## 3. The binary that shrank

`build.spec` no longer bundles `gameplay_lp600.wav`, and the file is
untracked. numpy was already inside the bundle, so the pause filter
keeps working.

`tests/test_build_spec_assets.py` keeps it that way: no literal
`*_lp*.wav` entry, and the glob over `Assets/*` keeps excluding them.

## 4. The budget that holds

`tools/repo_budget.py` measures three weights; `tests/test_repo_budget.py`
enforces three ceilings; the numbers are rows of the `STATUS:GENERATED`
block:

| Metric | Ceiling |
|---|---:|
| Tracked tree | 300 MB |
| Build output (`dist/`) | 600 MB |
| History (`.git/`) | 550 MB |

The ceilings live in the tool, not in the test.

## 5. The handoff mechanism

The repository is the ONLY channel between the agent that works and the
one that follows. Three pieces:

1. **The prompt** — `docs/superpowers/prompts/2026-10-29-bloque-75-migration-spec-prompt.md`,
   with a section 0 that says what to read, from which branch to branch,
   and where to write the result.
2. **The routing** — `CONTEXT.md`, `docs/superpowers/CONTEXT.md`,
   `CLAUDE.md` and `.synapse` all point at it. `tests/test_handoff_routing.py`
   asserts the routes still resolve.
3. **The proof** — the second agent read the prompt, created its worktree
   from the branch it names, and delivered
   `docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md`: the
   sprite-pipeline migration in two phases with a gate.

**Rule for the next agent:** one worktree and one branch per agent.
Never work in the repository root (`master` is the old line), never in
another agent's worktree. The repository is the channel; the scratch
folder `_srcrefs/` is not.

## 6. How to verify

```powershell
cd F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m pytest tests/ --tb=no
F:\AI\MM\void-hunter\.venv\Scripts\python.exe -m mypy src\anim\
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\sprite_pipeline\verify_contract.py goliath
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\repo_budget.py
F:\AI\MM\void-hunter\.venv\Scripts\python.exe main.py --check
$env:PYTHONUTF8 = '1'
F:\AI\MM\void-hunter\.venv\Scripts\python.exe "C:\Users\Lerius\.minimax\skills\sf-sm-doctor\scripts\audit_sf_sm.py" --perfil=lite .
```

The baseline at `F:\AI\MM\void-hunter-baseline\` is the restore point of
this release, verified with:

```powershell
F:\AI\MM\void-hunter\.venv\Scripts\python.exe tools\verify_clean_copy.py --tree F:\AI\MM\void-hunter-baseline --ref HEAD
```

## 6b. The line endings of the generated anchors (found on 2026-11-03)

The other agent measured the suite on a CLEAN checkout and got **2
failures where the base had 1**. The second one was
`test_the_fix_run_changes_no_file`.

The cause was a rule of ours that the generator did not honour:
`.gitattributes` declares `*.toml text eol=lf`, so a fresh checkout has
the anchors in LF — but `Path.write_text` in TEXT mode translates every
`\n` into `\r\n` on Windows. The generator wrote CRLF, so `--fix`
changed the file on every run and left the working tree dirty.

The release worktree hid it: its `anchors.toml` came from a checkout
made BEFORE the attribute existed, so it was still CRLF — which is what
the generator produced, so nothing changed and the test passed. The
defect was real and only a clean checkout could show it.

The fix is one keyword: `newline="\n"` in the write. Two tests pin it.

**The lesson worth keeping:** a test that passes on one checkout and
fails on another is not a flaky test, it is a defect that only one
environment can see. The `.gitattributes` said LF, the generator said
CRLF, and the repository believed both until somebody checked out the
tree fresh.

## 7. What comes next

The spec of BLOQUE 75 (`docs/superpowers/specs/2026-10-30-bloque-75-migration-spec.md`)
was written by the second agent, then went through an independent review
that **corrected four critical defects and reduced the scope of Phase 1**
(it is now measured against the merged tree, not against an assumption).

Beside it there is now a **Phase 1 implementation plan**:
`docs/superpowers/plans/2026-11-03-bloque-75-phase1-enemy-pipeline.md`
— 9 TDD tasks. Phase 1 brings the eight enemy sets into the pipeline;
Phase 2 turns the gameplay frame into a `LayerStack`. Both phases have a
gate.

## 8. What was deliberately not done

- **The history was not rewritten.** 122 MB of it are generated blobs that
  could be purged, but every hash would change and the published tags
  `v1.7.0`, `v1.7.2` and `v1.8.0` would be orphaned.
- The two real tracks (91 MB + 68 MB) stay: they are the music.
- `master` stays the old line (v1.6.3) and receives no merges.
- The GOLIATH art, the shield constants and the enemy sets were not
  touched: this was a build-and-cache change.
