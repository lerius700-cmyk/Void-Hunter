"""Wave manager + 18 wave JSON scripts (BLOQUE 10 + BLOQUE 41 formations).

Per GDD §6: 6 waves per act × 3 acts = 18 waves. Each wave script is a
JSON file in data/waves/ with archetype counts, kill target, optional
sub-boss trigger, and special conditions. Adaptive difficulty scales
spawn rate based on player HP/score.

BLOQUE 41: formation-based spawning. Each wave can declare a `formation`
that spawns enemies in choreographed shapes (LINE, V, ARC, STAIRCASE)
instead of the legacy random `mix` dictionary. The `parse_formation`
and `spawn_formation` helpers produce a list of (x, y, vx, vy) tuples
for the formation; gameplay_runtime spawns enemies from those tuples.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from src.core.settings import (
    FORMATION_PATTERN_SPEED_MAX,
    FORMATION_PATTERN_SPEED_MIN,
    FORMATION_SPACING_MAX_PX,
    FORMATION_SPACING_MIN_PX,
    FORMATION_TELEGRAPH_FRAMES_MAX,
    FORMATION_TELEGRAPH_FRAMES_MIN,
    INTERNAL_H,
    INTERNAL_W,
    SUBBOSS_TRIGGER_KILLS,
    WAVE_KILL_TARGET,
    WAVE_TIME_LIMIT_S,
)


WAVES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "waves"


# ---------------------------------------------------------------------------
# BLOQUE 41: formation types
# ---------------------------------------------------------------------------
FORMATION_TYPES: tuple[str, ...] = ("line", "v", "arc", "staircase", "squadron", "spiral", "hilera", "x")


class Formation(NamedTuple):
    """Scripted enemy formation for a wave.

    Fields map 1:1 to the JSON spec in actX_wY.json under "formation".
    All waves are destructible (destructible=True implicitly).
    """
    formation_type: str           # one of FORMATION_TYPES
    enemy_type: str               # SCOUT|CRUISER|HEAVY|KAMIKAZE|DRONE|SNIPER|TURRET|CARRIER
    enemy_count: int              # 4..8 (named enemy_count to avoid NamedTuple's `.count` method)
    spacing_px: int               # 24..32 (line/v) or general offset
    entry_axis: str               # "top" | "side" | "bottom" (currently "top")
    pattern_speed: float          # 30..60 px/s (downward)
    telegraph_frames: int         # 24..60 (0.2-0.5s @ 120fps)


class Spawn(NamedTuple):
    """One enemy spawn from a formation. Returned by spawn_formation()."""
    x: float
    y: float
    vx: float
    vy: float
    kind: str                     # enemy type
    # BLOQUE 47: squadron support. time_offset_s is 0 for normal spawns;
    # >0 for SQUADRON followers (they trail the leader by this many seconds,
    # replaying the leader's path). Default 0 keeps backward-compat.
    time_offset_s: float = 0.0


# ---------------------------------------------------------------------------
# BLOQUE 41: formation helpers
# ---------------------------------------------------------------------------
def _clamp_formation(formation: Formation) -> Formation:
    """Sanitize a formation: clamp out-of-range values to safe defaults."""
    ftype = formation.formation_type if formation.formation_type in FORMATION_TYPES else "line"
    spacing = max(FORMATION_SPACING_MIN_PX, min(FORMATION_SPACING_MAX_PX, formation.spacing_px))
    # If count*spacing > screen width, halve the spacing so the row fits.
    max_count_width = INTERNAL_W - 16
    if formation.enemy_count > 1 and (formation.enemy_count - 1) * spacing > max_count_width:
        spacing = max(16, max_count_width // (formation.enemy_count - 1))
    speed = max(FORMATION_PATTERN_SPEED_MIN, min(FORMATION_PATTERN_SPEED_MAX, formation.pattern_speed))
    tele = max(FORMATION_TELEGRAPH_FRAMES_MIN, min(FORMATION_TELEGRAPH_FRAMES_MAX, formation.telegraph_frames))
    return Formation(
        formation_type=ftype,
        enemy_type=formation.enemy_type,
        enemy_count=max(1, formation.enemy_count),
        spacing_px=spacing,
        entry_axis=formation.entry_axis or "top",
        pattern_speed=speed,
        telegraph_frames=tele,
    )


def parse_formation(spec: dict[str, Any]) -> Formation:
    """Parse a JSON formation spec into a Formation namedtuple.

    Raises ValueError if the formation_type is unknown (no silent fallback —
    callers want to know).
    """
    ftype = spec.get("formation_type", "line")
    if ftype not in FORMATION_TYPES:
        raise ValueError(
            f"Unknown formation_type {ftype!r}; must be one of {FORMATION_TYPES}"
        )
    return _clamp_formation(Formation(
        formation_type=ftype,
        enemy_type=str(spec.get("enemy_type", "SCOUT")).upper(),
        enemy_count=int(spec.get("count", 4)),
        spacing_px=int(spec.get("spacing_px", 28)),
        entry_axis=str(spec.get("entry_axis", "top")),
        pattern_speed=float(spec.get("pattern_speed", 40.0)),
        telegraph_frames=int(spec.get("telegraph_frames", 30)),
    ))


def spawn_formation(formation: Formation) -> list[Spawn]:
    """Generate the (x, y, vx, vy) tuples for every enemy in the formation.

    Convention:
      - All formations enter from the top (y small) and move downward (vy > 0).
      - The formation is centered horizontally in INTERNAL_W.
      - spacing_px controls intra-formation offsets.
    """
    f = _clamp_formation(formation)
    cx = INTERNAL_W / 2
    spawns: list[Spawn] = []
    if f.formation_type == "line":
        # Horizontal row, evenly spaced. y = 16 (just inside top).
        if f.enemy_count == 1:
            xs = [cx]
        else:
            half = (f.enemy_count - 1) * f.spacing_px / 2
            xs = [cx - half + i * f.spacing_px for i in range(f.enemy_count)]
        y = 16.0
        vy = f.pattern_speed
        for x in xs:
            spawns.append(Spawn(x=x, y=y, vx=0.0, vy=vy, kind=f.enemy_type))
    elif f.formation_type == "v":
        # Inverted V: middle at the top, wings angled down.
        # 5 enemies: x offsets relative to center, y offsets increase by spacing_y.
        spacing_y = f.spacing_px
        if f.enemy_count == 1:
            offsets = [(0.0, 0.0)]
        else:
            mid = (f.enemy_count - 1) / 2
            offsets = [(f.spacing_px * (i - mid), spacing_y * abs(i - mid))
                       for i in range(f.enemy_count)]
        y_top = 16.0
        vy = f.pattern_speed
        for ox, oy in offsets:
            spawns.append(Spawn(x=cx + ox, y=y_top + oy, vx=0.0, vy=vy, kind=f.enemy_type))
    elif f.formation_type == "arc":
        # 30°-span concave arc centered horizontally, peaking downward.
        # For count=5: positions at -30°, -15°, 0°, +15°, +30° around center.
        radius_x = (f.enemy_count - 1) * f.spacing_px / 2
        radius_y = 24.0
        span_deg = 30.0
        if f.enemy_count == 1:
            offsets_deg = [0.0]
        else:
            step = span_deg / (f.enemy_count - 1)
            offsets_deg = [-span_deg / 2 + step * i for i in range(f.enemy_count)]
        y_top = 16.0
        vy = f.pattern_speed
        for d in offsets_deg:
            rad = math.radians(d)
            spawns.append(Spawn(
                x=cx + math.sin(rad) * radius_x,
                y=y_top + (1.0 - math.cos(rad)) * radius_y,
                vx=0.0, vy=vy, kind=f.enemy_type,
            ))
    elif f.formation_type == "staircase":
        # Diagonal: each enemy offset 30px RIGHT + 20px DOWN from the previous.
        step_x = 30.0
        step_y = 20.0
        y_top = 16.0
        vy = f.pattern_speed
        for i in range(f.enemy_count):
            spawns.append(Spawn(
                x=cx - (f.enemy_count - 1) * step_x / 2 + i * step_x,
                y=y_top + i * step_y,
                vx=0.0, vy=vy, kind=f.enemy_type,
            ))
    elif f.formation_type == "squadron":
        # BLOQUE 47: SQUADRON — Star Fox 64 style. One leader follows a
        # sine-wave path; N-1 followers replay the same path with a delay.
        # Each follower is 0.4s behind the previous (scaled by enemy_count).
        # Spawn position: all start at the same top-center point. The
        # leader's path is computed in gameplay_runtime from time + time_offset_s.
        y_top = 16.0
        vy = f.pattern_speed
        delay_per_follower = 0.4  # seconds behind the previous follower
        for i in range(f.enemy_count):
            spawns.append(Spawn(
                x=cx,
                y=y_top,
                vx=0.0,
                vy=vy,
                kind=f.enemy_type,
                time_offset_s=float(i) * delay_per_follower,
            ))
    elif f.formation_type == "spiral":
        # BLOQUE 55: SPIRAL — logarithmic spiral entering from top.
        # Ships are placed around a center point below the top edge with
        # decreasing radius and increasing angle. The center is offset
        # down by radius_start so the spiral stays within the playfield
        # (y >= 0). Classic Galaga/Xevious attack pattern. 8 ships in
        # 2 turns is the canonical config.
        vy = f.pattern_speed
        turns = 2.0
        radius_start = 60.0
        radius_end = 20.0
        cy = 32.0 + radius_start  # = 92.0; ensures y stays >= 32
        if f.enemy_count == 1:
            spawns.append(Spawn(x=cx, y=cy, vx=0.0, vy=vy, kind=f.enemy_type))
        else:
            for i in range(f.enemy_count):
                t = i / (f.enemy_count - 1)  # 0..1
                theta = t * turns * 2.0 * math.pi
                radius = radius_start + (radius_end - radius_start) * t
                spawns.append(Spawn(
                    x=cx + radius * math.cos(theta),
                    y=cy + radius * math.sin(theta),
                    vx=0.0, vy=vy, kind=f.enemy_type,
                ))
    elif f.formation_type == "hilera":
        # BLOQUE 55: HILERA — tight vertical column falling in a row.
        # All ships at the same x (centered), y stacked with spacing_px.
        # Useful for dense "dive attack" patterns where many enemies
        # enter together in a single file.
        y_top = 16.0
        vy = f.pattern_speed
        for i in range(f.enemy_count):
            spawns.append(Spawn(
                x=cx,
                y=y_top + i * f.spacing_px,
                vx=0.0, vy=vy, kind=f.enemy_type,
            ))
    elif f.formation_type == "x":
        # BLOQUE 55: X — 5 ships in a cross pattern. 1 center + 4
        # cardinals (NW, NE, SW, SE) at spacing_px offset. Centered
        # horizontally; vertical center placed below the top edge so
        # the NW/NE cardinals stay in the playfield.
        cx_y = 48.0
        vy = f.pattern_speed
        s = float(f.spacing_px)
        x_offsets: list[tuple[float, float]] = [(0.0, 0.0)]
        if f.enemy_count >= 2:
            x_offsets.append((-s, -s))  # NW
        if f.enemy_count >= 3:
            x_offsets.append((s, -s))   # NE
        if f.enemy_count >= 4:
            x_offsets.append((-s, s))   # SW
        if f.enemy_count >= 5:
            x_offsets.append((s, s))    # SE
        # Clamp to enemy_count (only first 5 ships in X shape; rest follow
        # the cardinals in clockwise order, but typical count is exactly 5).
        x_offsets = x_offsets[:f.enemy_count]
        for ox, oy in x_offsets:
            spawns.append(Spawn(
                x=cx + ox,
                y=cx_y + oy,
                vx=0.0, vy=vy, kind=f.enemy_type,
            ))
    else:  # pragma: no cover — _clamp_formation already forces "line"
        return []
    return spawns


# Default 18-wave script (per GDD §6 + §4 enemy mix table)
# BLOQUE 45: Act 1 waves now use the formation system (LINE/V/ARC/STAIRCASE)
# with explicit formation_type, count, spacing_px, pattern_speed,
# telegraph_frames. Acts 2 & 3 keep the legacy `mix` dict and fall
# back to a derived LINE formation (see `current_formation()`).
DEFAULT_WAVES: list[dict[str, Any]] = [
    # Act 1 (Blue Void) — formations
    {
        "act": 1, "wave": 1, "theme": "blue_void",
        "formation": {
            "formation_type": "line", "enemy_type": "SCOUT",
            "count": 6, "spacing_px": 30, "entry_axis": "top",
            "pattern_speed": 40, "telegraph_frames": 30,
        },
        "kill_target": 6, "time_limit_s": 25.0, "sub_boss": None,
    },
    {
        "act": 1, "wave": 2, "theme": "blue_void",
        # BLOQUE 47: SQUADRON — 7 SCOUT in a leader+followers choreography
        # (Star Fox 64 style). Leader traces a sine path; followers replay
        # the same path 0.4s/0.8s/1.2s/1.6s/2.0s/2.4s behind.
        "formation": {
            "formation_type": "squadron", "enemy_type": "SCOUT",
            "count": 7, "spacing_px": 22, "entry_axis": "top",
            "pattern_speed": 50, "telegraph_frames": 30,
        },
        "kill_target": 7, "time_limit_s": 30.0, "sub_boss": None,
    },
    {
        "act": 1, "wave": 3, "theme": "blue_void",
        "formation": {
            "formation_type": "arc", "enemy_type": "CRUISER",
            "count": 7, "spacing_px": 26, "entry_axis": "top",
            "pattern_speed": 30, "telegraph_frames": 45,
        },
        "kill_target": 7, "time_limit_s": 32.0, "sub_boss": None,
    },
    {
        "act": 1, "wave": 4, "theme": "blue_void",
        "formation": {
            "formation_type": "staircase", "enemy_type": "HEAVY",
            "count": 6, "spacing_px": 28, "entry_axis": "top",
            "pattern_speed": 30, "telegraph_frames": 60,
        },
        "kill_target": 6, "time_limit_s": 35.0, "sub_boss": None,
    },
    {
        "act": 1, "wave": 5, "theme": "blue_void",
        # BLOQUE 50: mixed formation — 8 ships (more than before) for variety.
        "formation": {
            "formation_type": "line", "enemy_type": "SNIPER",
            "count": 8, "spacing_px": 22, "entry_axis": "top",
            "pattern_speed": 35, "telegraph_frames": 40,
        },
        "kill_target": 8, "time_limit_s": 38.0, "sub_boss": None,
    },
    {
        "act": 1, "wave": 6, "theme": "blue_void",
        # V formation of mixed heavies (HEAVY-dominant so the player
        # practices against the toughest non-boss enemy).
        "formation": {
            "formation_type": "v", "enemy_type": "HEAVY",
            "count": 8, "spacing_px": 24, "entry_axis": "top",
            "pattern_speed": 32, "telegraph_frames": 50,
        },
        "kill_target": 8, "time_limit_s": 40.0, "sub_boss": "goliath",
    },
    # Act 2 (Pink Void -> Mars -> Teal) — legacy `mix`, formation derived
    {"act": 2, "wave": 1, "theme": "pink_void", "mix": {"scout": 5, "cruiser": 5, "heavy": 4, "kamikaze": 2, "drone": 2}, "kill_target": 18, "time_limit_s": 38.0, "sub_boss": None},
    {"act": 2, "wave": 2, "theme": "pink_void", "mix": {"scout": 4, "cruiser": 4, "heavy": 4, "kamikaze": 3, "drone": 3}, "kill_target": 18, "time_limit_s": 40.0, "sub_boss": None},
    {"act": 2, "wave": 3, "theme": "mars", "mix": {"scout": 3, "cruiser": 3, "heavy": 3, "kamikaze": 3, "drone": 4, "sniper": 2}, "kill_target": 18, "time_limit_s": 42.0, "sub_boss": None},
    {"act": 2, "wave": 4, "theme": "mars", "mix": {"scout": 2, "cruiser": 2, "heavy": 2, "kamikaze": 3, "drone": 3, "sniper": 2, "turret": 1}, "kill_target": 15, "time_limit_s": 45.0, "sub_boss": None},
    {"act": 2, "wave": 5, "theme": "teal", "mix": {"scout": 1, "cruiser": 1, "heavy": 2, "kamikaze": 3, "drone": 2, "sniper": 2, "turret": 1}, "kill_target": 12, "time_limit_s": 50.0, "sub_boss": None},
    {"act": 2, "wave": 6, "theme": "teal", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 2, "turret": 1}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": "hydra"},
    # Act 3 (Purple Dusk -> Gold/Amber) — legacy `mix`
    {"act": 3, "wave": 1, "theme": "purple_dusk", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 8, "time_limit_s": 50.0, "sub_boss": None},
    {"act": 3, "wave": 2, "theme": "purple_dusk", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 9, "time_limit_s": 55.0, "sub_boss": None},
    {"act": 3, "wave": 3, "theme": "gold_amber", "mix": {"scout": 1, "cruiser": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 1}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": None},
    {"act": 3, "wave": 4, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 2, "drone": 1, "sniper": 1, "turret": 1, "carrier": 2}, "kill_target": 9, "time_limit_s": 60.0, "sub_boss": None},
    {"act": 3, "wave": 5, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 2, "carrier": 2}, "kill_target": 9, "time_limit_s": 65.0, "sub_boss": None},
    {"act": 3, "wave": 6, "theme": "gold_amber", "mix": {"scout": 1, "heavy": 1, "kamikaze": 1, "drone": 1, "sniper": 1, "turret": 2, "carrier": 3}, "kill_target": 10, "time_limit_s": 90.0, "sub_boss": "phantom_then_nemesis"},
]


@dataclass
class WaveState:
    """Live state of an in-progress wave."""
    wave_index: int = 0
    kills: int = 0
    elapsed_s: float = 0.0
    cleared: bool = False
    failed: bool = False
    # Adaptive difficulty multiplier (1.0 = baseline, 1.2 = harder)
    difficulty_mult: float = 1.0


class WaveManager:
    """18-wave scriptable manager. JSON-loadable, adaptive difficulty."""

    def __init__(self, scripts: list[dict[str, Any]] | None = None) -> None:
        self.scripts: list[dict[str, Any]] = scripts or DEFAULT_WAVES
        self.current: WaveState = WaveState()
        self.on_wave_cleared: bool = False
        self.on_wave_failed: bool = False
        self.on_sub_boss_trigger: str | None = None

    @classmethod
    def from_json_dir(cls, directory: Path | None = None) -> "WaveManager":
        """Load wave scripts from data/waves/*.json. Falls back to defaults."""
        directory = directory or WAVES_DIR
        if not directory.exists():
            return cls(DEFAULT_WAVES)
        scripts: list[dict[str, Any]] = []
        for path in sorted(directory.glob("act*_wave*.json")):
            with open(path, encoding="utf-8") as f:
                scripts.append(json.load(f))
        if not scripts:
            return cls(DEFAULT_WAVES)
        return cls(scripts)

    def validate(self) -> tuple[bool, str]:
        """Sanity check: 18 waves, kill_targets positive, themes known."""
        if len(self.scripts) != 18:
            return False, f"expected 18 waves, got {len(self.scripts)}"
        for i, s in enumerate(self.scripts):
            if "kill_target" not in s or s["kill_target"] <= 0:
                return False, f"wave {i} missing kill_target"
            if "theme" not in s:
                return False, f"wave {i} missing theme"
        return True, "ok"

    def start_wave(self, index: int) -> None:
        """Begin wave[index]."""
        if not (0 <= index < len(self.scripts)):
            raise IndexError(f"wave {index} out of range")
        self.current = WaveState(wave_index=index)
        self.on_wave_cleared = False
        self.on_wave_failed = False
        self.on_sub_boss_trigger = None

    def current_wave(self) -> dict[str, Any]:
        return self.scripts[self.current.wave_index]

    def current_formation(self) -> Formation | None:
        """BLOQUE 41: return the Formation for the current wave, if any.

        Falls back to deriving a LINE formation from the legacy `mix` dict
        (uses the first enemy type and the total count) so old wave JSONs
        without a `formation` field still produce a sensible spawn.
        Returns None only if the wave has neither `formation` nor `mix`.
        """
        wave = self.current_wave()
        if "formation" in wave and isinstance(wave["formation"], dict):
            try:
                return parse_formation(wave["formation"])
            except ValueError:
                pass  # bad spec — fall through to mix-derived fallback
        mix = wave.get("mix", {})
        if not mix:
            return None
        first_kind = next(iter(mix.keys()))
        total = sum(int(v) for v in mix.values())
        # Default formation: LINE with the dominant kind and the count.
        return Formation(
            formation_type="line",
            enemy_type=str(first_kind).upper(),
            enemy_count=min(8, max(4, total)),
            spacing_px=28,
            entry_axis="top",
            pattern_speed=40.0,
            telegraph_frames=30,
        )

    def on_kill(self) -> None:
        """Called when an enemy dies. Tracks wave progress."""
        self.current.kills += 1
        if self.current.kills >= self.current_wave()["kill_target"]:
            self.current.cleared = True
            self.on_wave_cleared = True
        # Sub-boss trigger: at SUBBOSS_TRIGGER_KILLS, fire the sub_boss event
        if (self.on_sub_boss_trigger is None
                and self.current_wave().get("sub_boss")
                and self.current.kills >= SUBBOSS_TRIGGER_KILLS):
            self.on_sub_boss_trigger = self.current_wave()["sub_boss"]

    def update(self, dt: float) -> None:
        """Advance elapsed time; fail wave if time limit exceeded."""
        self.current.elapsed_s += dt
        time_limit = self.current_wave().get("time_limit_s", WAVE_TIME_LIMIT_S)
        if self.current.elapsed_s >= time_limit and not self.current.cleared:
            self.current.failed = True
            self.on_wave_failed = True

    def adapt_difficulty(self, player_hp_pct: float, score: int) -> float:
        """Adjust spawn rate based on player performance.

        HP > 80% AND high score → harder (1.2x).
        HP < 30% → easier (0.8x).
        """
        if player_hp_pct > 0.8 and score > 50000:
            self.current.difficulty_mult = 1.2
        elif player_hp_pct < 0.3:
            self.current.difficulty_mult = 0.8
        else:
            self.current.difficulty_mult = 1.0
        return self.current.difficulty_mult

    def total_kills_remaining(self) -> int:
        target: int = self.current_wave()["kill_target"]
        return max(0, target - self.current.kills)

    def reset(self) -> None:
        self.current = WaveState()
        self.on_wave_cleared = False
        self.on_wave_failed = False
        self.on_sub_boss_trigger = None


# ---------------------------------------------------------------------------
# BLOQUE 48: chained wave system for level 1 mode
# ---------------------------------------------------------------------------
LEVEL1_WAVES: list[dict[str, Any]] = [
    # O1 — intro/tutorial: 12 SCOUT diagonal, no fire (was 8)
    {
        "enemies": ["SCOUT"] * 12,
        "spawn_cadence_s": 1.0,
        "max_duration_s": 10.0,
        "formation": "diagonal",
        "fire_allowed": False,
    },
    # O2 — pattern recognition: 14 SCOUT + 5 CRUISER, V formation (was 10+3)
    # BLOQUE 50: triggers a sub-boss encounter after this wave is cleared
    {
        "enemies": ["SCOUT"] * 14 + ["CRUISER"] * 5,
        "spawn_cadence_s": 0.6,
        "max_duration_s": 16.0,
        "formation": "v",
        "fire_allowed": True,
        "sub_boss_after": True,
    },
    # O3 — mixed composition: 10 SCOUT + 4 HEAVY, line, HEAVY as anchor (was 8+2)
    {
        "enemies": ["SCOUT"] * 10 + ["HEAVY"] * 4,
        "spawn_cadence_s": 0.8,
        "max_duration_s": 19.0,
        "formation": "line",
        "fire_allowed": True,
    },
    # O4 — finale: 8 SCOUT + 6 CRUISER + 3 HEAVY, diamond (was 6+4+2)
    {
        "enemies": ["SCOUT"] * 8 + ["CRUISER"] * 6 + ["HEAVY"] * 3,
        "spawn_cadence_s": 0.9,
        "max_duration_s": 22.0,
        "formation": "diamond",
        "fire_allowed": True,
    },
]


class WaveChain:
    """BLOQUE 48: chained wave manager for level 1 mode.

    Tracks spawn schedule per wave, advances to next wave when the current
    one is fully spawned + cleared, OR when its max_duration_s is reached
    (whichever comes first). Single source of truth for kills.

    BLOQUE 50: supports an optional `sub_boss_after` flag on each wave
    spec. When that wave is cleared, the chain sets `_sub_boss_pending`
    and pauses further wave progression. The runtime is responsible for
    spawning the sub-boss, then calling `clear_sub_boss_pending()` to
    resume the chain.
    """

    def __init__(
        self,
        wave_specs: list[dict[str, Any]] | None = None,
        max_alive: int = 8,
    ) -> None:
        self.wave_specs: list[dict[str, Any]] = wave_specs or LEVEL1_WAVES
        self.max_alive: int = max_alive
        self.current_wave_idx: int = 0
        # Per-wave state
        self._spawned_per_wave: list[int] = [0] * len(self.wave_specs)
        self._alive_per_wave: list[int] = [0] * len(self.wave_specs)
        self._wave_elapsed_s: list[float] = [0.0] * len(self.wave_specs)
        self._spawn_timer: list[float] = [0.0] * len(self.wave_specs)
        # Single kill counter
        self.kills: int = 0
        # Total elapsed since chain start
        self.elapsed_s: float = 0.0
        # Perfect score (no escapes)
        self.perfect: bool = True
        # All waves complete?
        self.waves_complete: bool = False
        # Total ships in level
        self.total_ships: int = sum(len(w["enemies"]) for w in self.wave_specs)
        # BLOQUE 50: sub-boss gating
        self._sub_boss_pending: bool = False
        self._sub_boss_defeated: bool = False
        # Pre-compute which wave indices trigger a sub-boss after they clear
        self._sub_boss_after_waves: set[int] = {
            i for i, w in enumerate(self.wave_specs)
            if w.get("sub_boss_after", False)
        }

    @property
    def alive_count(self) -> int:
        return sum(self._alive_per_wave)

    @property
    def sub_boss_pending(self) -> bool:
        """True if the chain is paused and a sub-boss should be spawned."""
        return self._sub_boss_pending

    def clear_sub_boss_pending(self) -> None:
        """Called by the runtime after the sub-boss is killed. Resumes chain."""
        self._sub_boss_pending = False
        self._sub_boss_defeated = True

    def tick(self, dt: float) -> None:
        """Advance timers; advance to next wave if current is done.

        BLOQUE 50: pauses on sub_boss_pending so the chain doesn't advance
        while the runtime is fighting the sub-boss.
        """
        self.elapsed_s += dt
        if self.current_wave_idx >= len(self.wave_specs):
            self.waves_complete = True
            return
        # BLOQUE 50: don't tick waves while sub-boss is pending
        if self._sub_boss_pending:
            return
        spec = self.wave_specs[self.current_wave_idx]
        self._wave_elapsed_s[self.current_wave_idx] += dt
        self._spawn_timer[self.current_wave_idx] += dt
        # Check if current wave is done
        all_spawned = (
            self._spawned_per_wave[self.current_wave_idx]
            >= len(spec["enemies"])
        )
        all_dead = self._alive_per_wave[self.current_wave_idx] == 0
        timed_out = (
            self._wave_elapsed_s[self.current_wave_idx]
            >= spec["max_duration_s"]
        )
        # Advance if: completed (spawned + dead), OR (spawned + timed out),
        # OR timed out (escapees become rezagadas for next wave)
        if (all_spawned and all_dead) or (all_spawned and timed_out) or timed_out:
            finished_wave_idx = self.current_wave_idx
            # Advance to next wave
            self.current_wave_idx += 1
            if self.current_wave_idx >= len(self.wave_specs):
                self.waves_complete = True
                return
            # BLOQUE 50: check if the wave we just finished triggers a sub-boss
            if finished_wave_idx in self._sub_boss_after_waves:
                self._sub_boss_pending = True

    def spawn(self, wave_idx: int | None = None, x: float = 0.0, y: float = 0.0,
              kind: str = "SCOUT") -> bool:
        """Try to spawn an enemy. Returns True if spawned, False if blocked by
        density cap or wave already full.
        """
        idx = wave_idx if wave_idx is not None else self.current_wave_idx
        if idx >= len(self.wave_specs):
            return False
        spec = self.wave_specs[idx]
        # Check spawn cadence
        if self._spawn_timer[idx] < spec["spawn_cadence_s"]:
            return False
        # Check density cap
        if self.alive_count >= self.max_alive:
            return False
        # Check wave full
        if self._spawned_per_wave[idx] >= len(spec["enemies"]):
            return False
        # Spawn!
        self._spawned_per_wave[idx] += 1
        self._alive_per_wave[idx] += 1
        self._spawn_timer[idx] = 0.0
        return True

    def kill(self, wave_idx: int | None = None) -> None:
        """Mark an enemy killed. Decrements alive, increments kills."""
        idx = wave_idx if wave_idx is not None else self.current_wave_idx
        if self._alive_per_wave[idx] > 0:
            self._alive_per_wave[idx] -= 1
        self.kills += 1

    def escape(self) -> None:
        """Mark an enemy that escaped the screen (breaks perfect)."""
        self.perfect = False

    def reset(self) -> None:
        self.current_wave_idx = 0
        self._spawned_per_wave = [0] * len(self.wave_specs)
        self._alive_per_wave = [0] * len(self.wave_specs)
        self._wave_elapsed_s = [0.0] * len(self.wave_specs)
        self._spawn_timer = [0.0] * len(self.wave_specs)
        self.kills = 0
        self.elapsed_s = 0.0
        self.perfect = True
        self.waves_complete = False
        # BLOQUE 50: sub-boss reset
        self._sub_boss_pending = False
        self._sub_boss_defeated = False


class BossTrigger:
    """BLOQUE 48: 3-tier boss trigger hierarchy.

    Returns the trigger name that fired (or None if no boss yet).
    Hierarchy:
      - main: waves_complete AND elapsed >= BOSS_MIN_TRIGGER_S (45s)
      - perfect: elapsed >= BOSS_PERFECT_TRIGGER_S (60s) AND perfect AND kills >= 1
      - safety: elapsed >= BOSS_SAFETY_TRIGGER_S (120s)
    """

    def evaluate(
        self,
        elapsed_s: float,
        waves_complete: bool,
        perfect: bool,
        kills: int,
    ) -> str | None:
        from src.core.settings import (
            BOSS_MIN_TRIGGER_S,
            BOSS_PERFECT_TRIGGER_S,
            BOSS_SAFETY_TRIGGER_S,
        )
        if waves_complete and elapsed_s >= BOSS_MIN_TRIGGER_S:
            return "main"
        if (
            elapsed_s >= BOSS_PERFECT_TRIGGER_S
            and perfect
            and kills >= 1
        ):
            return "perfect"
        if elapsed_s >= BOSS_SAFETY_TRIGGER_S:
            return "safety"
        return None
