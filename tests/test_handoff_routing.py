"""BLOQUE 75: the context handoff has to stay REACHABLE.

The whole point of this branch is that the second agent can start cold and
find what it needs by reading the repository. That property is made of
routes -- a path in `CONTEXT.md`, a row in the silo's context, a pointer in
`.synapse`, the prompt's own reading order -- and a route is the easiest
thing in the world to break by renaming a file.

So the routes are asserted here. Renaming the prompt, moving the silo or
editing the pointer out of `.synapse` turns this module red instead of
leaving a second agent to guess where the context went.

The `.synapse` carries ROUTES, not claims: a pointer that does not exist is
an error the reader can see. That is the rule this module enforces.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROMPT_REL = "docs/superpowers/prompts/2026-10-29-bloque-75-migration-spec-prompt.md"
DESIGN_REL = "docs/superpowers/specs/2026-10-29-agent-context-handoff-design.md"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_the_prompt_is_where_the_synapse_points_at():
    """The prompt exists at the path the pointer names."""
    assert (ROOT / PROMPT_REL).is_file(), (
        f"the prompt is gone from {PROMPT_REL}: the second agent would have "
        "nothing to paste"
    )


def test_every_synapse_pointer_resolves():
    """Every route in the `.synapse` exists on disk.

    The `.synapse` is the pointer of last resort: it carries paths, not
    claims, precisely so that a stale route is VISIBLE. A pointer that
    does not resolve is a broken handoff.
    """
    data = json.loads(_read(".synapse"))
    pointers = data["short_term_memory"]["active_context_pointers"]
    assert pointers, "the .synapse has no active_context_pointers"
    for pointer in pointers:
        assert (ROOT / pointer).exists(), (
            f"the .synapse points at {pointer!r}, which does not exist"
        )


def test_the_prompt_is_routed_from_the_root_switch():
    """`CONTEXT.md` routes the prompts silo.

    This is the ADUANA: an agent that reads only the switch must be able
    to tell that the prompt lives in `docs/superpowers/prompts/`.
    """
    switch = _read("CONTEXT.md")
    assert "docs/superpowers/prompts/" in switch, (
        "CONTEXT.md does not route the prompts silo"
    )


def test_the_prompt_is_listed_in_its_silo():
    """The silo's own context table lists the prompt by name.

    The table is relative to the silo (``prompts/...``), the way its
    ``plans/`` and ``specs/`` rows are.
    """
    silo = _read("docs/superpowers/CONTEXT.md")
    silo_rel = PROMPT_REL.removeprefix("docs/superpowers/")
    assert silo_rel in silo, (
        f"the superpowers silo does not list {silo_rel!r}"
    )


def test_the_project_identity_points_at_the_prompt():
    """`CLAUDE.md` names the prompt: the file every agent opens first."""
    identity = _read("CLAUDE.md")
    assert PROMPT_REL in identity, (
        "CLAUDE.md does not mention the BLOQUE 75 prompt"
    )


def test_the_prompt_carries_its_own_reading_order():
    """The prompt says where to work and what to read before starting.

    A prompt pasted on its own is the seed, not the map. If the prompt
    stops naming the branch and the reading order, the handoff depends on
    someone remembering to explain it -- which is the failure this whole
    branch exists to remove.
    """
    prompt = _read(PROMPT_REL)
    for needed in ("CLAUDE.md", "CONTEXT.md", ".synapse", "bloquec-67-goliath-port"):
        assert needed in prompt, (
            f"the prompt does not mention {needed!r}: an agent that only "
            "receives the prompt would have no way to find the context"
        )
    assert "verify_contract.py" in prompt, (
        "the prompt does not tell the agent how to verify the pipeline"
    )


def test_the_design_doc_stays_next_to_the_prompt():
    """The design doc (why the repo is the channel) is one route away."""
    assert (ROOT / DESIGN_REL).is_file()
