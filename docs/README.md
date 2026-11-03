# Documentation

Welcome to the VOID HUNTER documentation.

## Quick links

| Doc | Purpose |
|---|---|
| [README.md](../README.md) | Product overview, quick start, project layout |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 13 major systems, file map, BLOQUE history |
| [ROADMAP.md](./ROADMAP.md) | What's now, next, later, backlog |
| [CHANGELOG_v1.x.md](./CHANGELOG_v1.x.md) | Full version history (v1.0 → v1.27), bug log |
| [bloques/USER_PROMPTS_CHECKLIST.md](./bloques/USER_PROMPTS_CHECKLIST.md) | Every prompt + preference tracked |

## Maintenance and handoffs

| Doc | Purpose |
|---|---|
| [arch/MAINTENANCE-CLEANUP-2026-10-30.md](./arch/MAINTENANCE-CLEANUP-2026-10-30.md) | First cleanup round: 15.70 GB → 2.35 GB, the pristine baseline and a pre-landing review |
| [arch/MAINTENANCE-CLEANUP-2026-11-02.md](./arch/MAINTENANCE-CLEANUP-2026-11-02.md) | Second round: the persistent lowpass cache, the 220 MB binary and the disk budget |
| [handoffs/HANDOFF-BLOQUE-75-2026-11-02.md](./handoffs/HANDOFF-BLOQUE-75-2026-11-02.md) | BLOQUE 75 close-out: the cache, the budget and the agent handoff |

## Design

| Doc | Purpose |
|---|---|
| [design/void-hunter-gdd.md](./design/void-hunter-gdd.md) | Game design document (GDD) — vision, mechanics, scope |

## Reference

| Doc | Purpose |
|---|---|
| [references/](./references/) | Star Fox 64 reference images used for visual design |

## Historical

| Doc | Purpose |
|---|---|
| [session-reports/SESSION_REPORT_BLOQUES_18-53.txt](./session-reports/SESSION_REPORT_BLOQUES_18-53.txt) | Work log from BLOQUE 18-53 era |
| [changelog/CHANGELOG.md](./changelog/CHANGELOG.md) | Older changelog (BLOQUE-level commits) |

---

## How to read this

**If you're new:** start with [README.md](../README.md) → [ARCHITECTURE.md](./ARCHITECTURE.md) → run `python main.py --easy`.

**If you want to contribute:** [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview, then read the relevant `src/` file.

**If you want to play:** download a release from [releases/](../releases/), run `void-hunter.exe`.

**If you want to track my work:** [USER_PROMPTS_CHECKLIST.md](./USER_PROMPTS_CHECKLIST.md).

---

*Last updated: 2026-11-03*
