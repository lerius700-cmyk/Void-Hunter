# Agent Context Handoff — making the repo the only channel between two agents

**Date:** 2026-10-29
**Status:** READY FOR EXECUTION
**Author:** Lerius (idea) + Mavis (draft)
**Branch:** `bloquec-75-sprite-migration`
**Base:** `bloquec-67-goliath-port` (v1.8.0, tag `v1.8.0`)

---

## Overview

A second agent is about to work on this repository, on this machine. The
repository currently answers "what is the state of the project?" with two
different, contradictory answers depending on which directory you open, and
the artefacts that agent needs to continue BLOQUE 74's work live outside the
repository, in a scratch folder, where they are invisible to git and one
agent's deletion is the other agent's loss.

This spec makes the **repository the only channel**. Every artefact the
second agent needs is versioned inside it and reachable through the project's
existing ADUANA protocol. The scratch folder stops being a shared dumping
ground and becomes what it should be: per-agent, disposable, outside the repo.

**One sentence:** the second agent must be able to start cold, read three
files, and know everything — which branch is the release line, what BLOQUE 74
delivered, where the BLOQUE 75 prompt is, and how to verify that the pipeline
still behaves.

---

## The problem, measured

### Two directories, two different projects

| | `F:\AI\MM\void-hunter` (master) | `.worktrees/bloquec-67-goliath-port` |
|---|---|---|
| Version in `CLAUDE.md` | v1.6.3 | **v1.8.0** |
| Test count | 2,791 pass + **8** fail | **2,886 pass + 1** fail |
| `.synapse` last verified | 2026-10-23 | 2026-10-28 |
| What `.synapse` says to do next | *"push de master (1 commit local) y release v1.6.4"* | the real state of BLOQUE 74 |
| Has `src/anim/` (the pipeline) | **no** | yes |
| Has `Assets/sprites/bosses/goliath/manifest.toml` | no | yes |
| Unpushed commits | 8 | 0 |

Opening the main directory tells an agent that eight tests are red, that
`master` has one unpushed commit, and that the next task is a v1.6.4
release. All three are false. It also hides the entire sprite pipeline: an
agent grepping for `src/anim/` or `manifest.toml` finds nothing and concludes
BLOQUE 74 never happened.

The divergence is not a mistake — `master` is a **different line** (v1.6.3)
that must not receive merges (R3 of the BLOQUE 74 spec). But nothing in the
repository says so, and the `.synapse` of `master` actively misdirects.

### The artefacts the second agent needs are outside the repo

BLOQUE 74 produced three things that must survive into BLOQUE 75:

| Artefact | Where it is now | Visible to the other agent? |
|---|---|---|
| The BLOQUE 75 spec prompt (27.7 KB) | `.worktrees/_srcrefs/` | **no** — not in git, no index, no routing |
| The contract harness | `.worktrees/_srcrefs/verify_shipped_contract.py` | **no** |
| The SDD ledger (the 8-task recovery map) | `.worktrees/_srcrefs/progress_bloque74.md` | **no** |

They are in a folder with 233 files accumulated across several sessions,
including files named `main_master.py`, `grt_master.py` and `suite_b67.txt`
from August. A second agent opening that folder cannot tell which of the 233
are current. And because the folder is shared between two agents on one
machine, one agent's cleanup is the other's loss of context.

---

## The contract between the two agents

### Rule 1 — one worktree, one branch, per agent

Every agent works in its **own worktree** on its **own branch**, created from
the release line:

```
F:\AI\MM\void-hunter\                                  → master            (v1.6.3, NOT the release line)
F:\AI\MM\void-hunter\.worktrees\bloquec-67-goliath-port → bloquec-67-…     (the release line, v1.8.0)
F:\AI\MM\void-hunter\.worktrees\bloquec-75-sprite-migration → bloquec-75-… (BLOQUE 75, created for the second agent)
```

Two agents in one directory collide on the index, on `HEAD` and on the files.
Two agents in two worktrees on two branches do not.

**The base branch for any new work is `bloquec-67-goliath-port`.** Never
`master`. This is already rule R3 of the BLOQUE 74 spec; what is new is that
it is stated in `CLAUDE.md` (L1) where every agent reads it first, and in
the `.synapse` of the release line.

### Rule 2 — the repository is the channel

Anything the next agent must know is **committed**, and reachable through the
ADUANA protocol that already exists:

```
CLAUDE.md  →  CONTEXT.md  →  docs/<silo>/CONTEXT.md  →  the file
```

If it is not in the repository, the next agent does not have it. The
`_srcrefs/` scratch folder is explicitly **not** a channel: it is per-agent
disposable workspace.

### Rule 3 — the state lives in three places, in this order of authority

1. **The commits** — the source of truth. `git log` never lies.
2. **The handoff** — `docs/handoffs/HANDOFF-<BLOQUE>-<date>.md`: the legible
   summary of what a BLOQUE did and what is left.
3. **The `.synapse`** — the pointer. It says *where* the truth is and what the
   next step is, in a dozen lines.

The `.synapse` is the only one of the three that goes stale silently, which
is why it must carry **paths**, not claims: "the handoff is at
`docs/handoffs/…`", not "we fixed the thing". A stale pointer is visible
because the path is missing.

### Rule 4 — what leaves a worktree goes through the repository

The second agent starts cold. It must be able to reach everything with three
reads: `CLAUDE.md`, `CONTEXT.md`, and the `.synapse`. From there, the ADUANA
routes it to the silo, and the silo's content table names the files.

---

## What gets anchored, and where

| Artefact | Destination | Why there |
|---|---|---|
| The BLOQUE 75 spec prompt | `docs/superpowers/prompts/2026-10-29-bloque-75-migration-spec-prompt.md` | A new `prompts/` under the `superpowers` silo, with the silo's date convention. It is the **input to a spec**, not a spec — putting it in `specs/` would make two different things share a name. |
| The contract harness | `tools/sprite_pipeline/verify_contract.py` | It is project verification code, next to the auditor it checks. The other agent and CI both run it. |
| The SDD ledger | **stays out of the repository** | It is the private state of one controller session, not project knowledge. The handoff already carries what matters. |
| The multi-agent rule | `CLAUDE.md` (L1) | It is a global rule, and L1 is what every agent reads first. |
| The routing row for the prompt | `CONTEXT.md` | The switch is what sends an agent to a file. |
| The content-table row | `docs/superpowers/CONTEXT.md` | The silo table is the index of that silo. |

### The prompt is routed, not just stored

A file that is versioned but not routed is a file nobody finds. Three edits
make it discoverable:

1. `CONTEXT.md` gains a routing row: `docs/superpowers/prompts/…` →
   *"Prompt del spec de BLOQUE 75 (migración del pipeline) → escribir el spec"*.
2. `docs/superpowers/CONTEXT.md` gains a content-table row and a token-budget
   row.
3. `.synapse`'s `active_context_pointers` names the prompt, so an agent that
   reads only the `.synapse` still lands on it.

### The harness becomes a guard, not a script

`verify_contract.py` asserts five things about a shipped set:

1. every frame of every clip resolves (no missing ellipse, no missing eye);
2. no FAIL state survives;
3. rendering the anchors twice is byte-identical (determinism);
4. the committed `anchors.toml` equals the freshly rendered one (freshness);
5. for a set with a known contract, the findings match it exactly.

Check 5 is what makes it a contract and not a smoke test. GOLIATH's expected
findings are pinned: **10 frames with a finding, 0 FAIL, 10 WARN** — seven
frames whose plate is not credible in the art (so their ellipse is
reconstructed by interpolation) and three whose brass probe and shape
measurement disagree because the boss is crouching or collapsing.

The guard was proven in both directions: it exits 0 on the shipped tree and
exits 1 with a legible message on a copy whose `anchors.toml` was corrupted.

---

## The minor items, resolved here

### D — the negative cache

`src/anim/manifest.py` caches a successful load but **not a failed one**. A
malformed manifest is therefore re-parsed on every call: 91.8 µs, three to
four calls per frame, ≈ 0.3 ms per frame in a build whose manifest is
broken. The sibling loader `src/ui/scenes.py:176-181` already latches the
failure (`_manifest_failed`). The fix copies that pattern.

### E — `.gitattributes`

The repository has no `.gitattributes`, and `core.autocrlf=true` means the
same `manifest.toml` checks out as LF on one machine and CRLF on another.
BLOQUE 74 already hardened the **hash** (computed over normalised text, so
the freshness check survives either), but the checkout itself is still
machine-dependent.

`.gitattributes` with a single line — `*.toml text eol=lf` — makes the
pipeline's data files deterministic everywhere. It is scoped to TOML on
purpose: a broad `* text=auto` would renormalise the whole repository, which
is not a change this BLOQUE should make.

### F — the stale review spritesheet

`Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png` is the **output**
of `tools/redesign_bosses/_03b_build_sheets_64b.py` and still holds the
pre-mirror frames. Nothing in `src/` reads it; only the generator scripts do.
It is regenerated rather than deleted, so the generator's output stays
consistent with the art it came from.

### G — the scratch folder

`_srcrefs/` holds 233 files from several sessions, in a shared location, on a
machine with two agents. The resolution is **movement, not deletion** (the
project rule): everything that is not currently in use moves to
`_srcrefs/_archive_2026-10-29/`, and only the live scripts stay at the root.
The archive is dated so a future agent can tell instantly that nothing there
is current.

---

## What stays deferred, and why

| # | Item | Why it is not here |
|---|---|---|
| I | HYDRA / PHANTOM / NEMESIS have no sprites | They are Phase 1 and Phase 2 of the BLOQUE 75 spec, not of this one |
| J | `test_paths_no_star_shapes` | A genuine LissajousPath geometry assertion, pre-existing; the pipeline does not cause it |
| K | The native crash at `hud.py:342` | Unreachable in the game: all four `pygame.quit()` calls are terminal. No safe probe exists in pygame 2.6 |
| L | ruff | The project declares no `[tool.ruff]`; the real gates are mypy and pytest, both green |
| M | The stale `.synapse` on `master` | `master` is a different line and must not receive merges. Syncing it would mix the lines; the divergence is documented in the release line's `.synapse` instead |

---

## Verification

1. `python -m pytest tests/ --tb=no` → 2,886 pass + 1 pre-existing fail + 6 skipped
2. `python -m mypy src/anim/` → 0 errors
3. `python tools/sprite_pipeline/verify_contract.py goliath` → `CONTRACT OK`, exit 0
4. `python tools/sprite_pipeline/verify_contract.py goliath --root <copy with a corrupted anchors.toml>` → exit 1
5. `Select-String -Path CONTEXT.md -Pattern 'bloque-75'` → the routing row exists
6. `Select-String -Path docs/superpowers/CONTEXT.md -Pattern 'bloque-75'` → the content-table row exists
7. `Select-String -Path CLAUDE.md -Pattern 'worktree'` → the multi-agent rule exists
8. `git status --short` → clean
9. `master` still at `a40fdaf`, clean, 8 unpushed commits — untouched

---

## File map

| File | Action | Why |
|---|---|---|
| `docs/superpowers/specs/2026-10-29-agent-context-handoff-design.md` | Create | This document |
| `docs/superpowers/prompts/2026-10-29-bloque-75-migration-spec-prompt.md` | Create | The prompt the second agent uses to write the BLOQUE 75 spec |
| `docs/superpowers/CONTEXT.md` | Modify | Content table + token budget row for the new prompt |
| `CONTEXT.md` | Modify | Routing row for the prompt; the branch rule |
| `CLAUDE.md` | Modify | The multi-agent worktree rule; the prompt pointer; the STATUS row |
| `.synapse` | Modify | The release line's pointer to the prompt and the handoff |
| `tools/sprite_pipeline/verify_contract.py` | Create | The contract guard |
| `src/anim/manifest.py` | Modify | The negative cache (D) |
| `.gitattributes` | Create | `*.toml text eol=lf` (E) |
| `Assets/sprites/bosses/goliath/spritesheet_goliath_64b.png` | Regenerate | The stale review sheet (F) |
| `.worktrees/_srcrefs/` | Move | The scratch cleanup (G) — outside the repository, not a commit |

**Out of scope:** the BLOQUE 75 migration itself. This spec only sets up the
context for it.
