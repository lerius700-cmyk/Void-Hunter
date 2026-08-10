"""Roguelike seed strategy (BLOQUE 57).

Hierarchical seed derivation: a single (level, attempt, salt) tuple
expands into many sub-seeds (game, wave, slot, audio, drop, particle).
All derivations use splitmix64, a fast 64-bit PRNG with period 2^64
and no attractor at 0 (unlike xorshift32). Reference: Steele et al. 2014.

Industry pattern: same as Slay the Spire (seed = char + ascension + floor)
and Enter the Gungeon (master_seed + offset per system).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

# splitmix64 increment (the "golden ratio constant" as 64-bit int).
# Reference: Steele, Lea & Flood, 2014.
_SPLITMIX64_INCREMENT: int = 0x9E3779B97F4A7C15
_MASK_64: int = 0xFFFFFFFFFFFFFFFF


def splitmix64(state: int) -> tuple[int, int]:
    """One step of splitmix64. Returns (new_state, output).

    Pure stdlib, no numpy. Input is treated as a 64-bit unsigned int
    (overflow handled via & _MASK_64). Period: 2^64.
    """
    state = (state + _SPLITMIX64_INCREMENT) & _MASK_64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK_64
    z = z ^ (z >> 31)
    return state, z


def splitmix64_value(seed: int) -> int:
    """One-shot splitmix64: hash a seed to a 64-bit value.

    Useful for deriving child seeds from a parent seed.
    """
    _, value = splitmix64(seed)
    return value


@dataclass(frozen=True)
class RoguelikeSeed:
    """A master game seed with derivable sub-seeds for each subsystem.

    Derive a master seed from (level_idx, attempt_number, salt), then
    expand into per-wave, per-slot, per-audio, per-drop, per-particle
    seeds. The same inputs always produce the same outputs.
    """
    master: int  # 64-bit unsigned

    @staticmethod
    def derive(level_idx: int, attempt_number: int, salt: int) -> "RoguelikeSeed":
        """Derive a master seed from a (level, attempt, salt) triple.

        Raises ValueError for out-of-range inputs.
        """
        if level_idx < 0:
            raise ValueError(f"level_idx must be >= 0, got {level_idx}")
        if attempt_number < 1:
            raise ValueError(
                f"attempt_number must be >= 1 (1 = first attempt), got {attempt_number}"
            )
        if salt < 0:
            raise ValueError(f"salt must be >= 0, got {salt}")
        # Cascade: mix all three inputs into one 64-bit seed.
        mixed = (level_idx * 7919) ^ (attempt_number * 31) ^ (salt & _MASK_64)
        master = splitmix64_value(mixed)
        return RoguelikeSeed(master=master)

    def derive_wave_seed(self, wave_idx: int) -> int:
        """Per-wave sub-seed. Different wave_idx -> different seed."""
        if wave_idx < 0:
            raise ValueError(f"wave_idx must be >= 0, got {wave_idx}")
        return splitmix64_value(self.master ^ (wave_idx * 2654435761))

    def derive_slot_seed(self, wave_idx: int, slot_idx: int) -> int:
        """Per-wave-slot sub-seed. Each spawn slot has a unique seed."""
        if slot_idx < 0:
            raise ValueError(f"slot_idx must be >= 0, got {slot_idx}")
        wave_seed = self.derive_wave_seed(wave_idx)
        return splitmix64_value(wave_seed ^ (slot_idx * 40503))

    def derive_audio_seed(self) -> int:
        """SFX randomization seed (deterministic per run)."""
        return splitmix64_value(self.master ^ 0xA5A5_A5A5_A5A5_A5A5)

    def derive_drop_seed(self) -> int:
        """Loot drop seed. Distinct from audio so drop rolls don't sync with SFX."""
        return splitmix64_value(self.master ^ 0x5A5A_5A5A_5A5A_5A5A)

    def derive_particle_seed(self) -> int:
        """Visual particle effect seed. Independent stream."""
        return splitmix64_value(self.master ^ 0x1234_5678_9ABC_DEF0)

    def to_json(self) -> str:
        """Serialize to JSON. Round-trip safe with from_json()."""
        return json.dumps(
            {"master": self.master, "_kind": "RoguelikeSeed"},
            sort_keys=True,
        )

    @staticmethod
    def from_json(data: str) -> "RoguelikeSeed":
        """Deserialize from JSON produced by to_json()."""
        obj = json.loads(data)
        if not isinstance(obj, dict) or obj.get("_kind") != "RoguelikeSeed":
            raise ValueError(f"Invalid RoguelikeSeed JSON: {data!r}")
        master = int(obj["master"])
        if not 0 <= master <= _MASK_64:
            raise ValueError(f"master out of 64-bit range: {master}")
        return RoguelikeSeed(master=master)
