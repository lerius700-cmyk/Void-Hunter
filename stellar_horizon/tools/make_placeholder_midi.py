"""Generate simple placeholder MIDI files (4 of them)."""
from __future__ import annotations

from pathlib import Path


def make_placeholder_midi(out_path: Path, seconds: int = 30) -> None:
    """Write a minimal single-track MIDI file to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import mido
        mid = mido.MidiFile(type=0)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        notes = [60, 64, 67, 72]
        for tick in range(seconds):
            note = notes[tick % 4]
            track.append(mido.Message("note_on", note=note, velocity=80, time=480))
            track.append(mido.Message("note_off", note=note, velocity=80, time=0))
        track.append(mido.MetaMessage("end_of_track", time=0))
        mid.save(str(out_path))
        return
    except ImportError:
        pass
    raise RuntimeError(
        "mido is required to generate placeholder MIDI. Install with: pip install mido"
    )


def make_all_placeholder_midis(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, secs in (("title", 60), ("act1", 180), ("boss", 60), ("game_over", 30)):
        make_placeholder_midi(out_dir / f"{name}.mid", seconds=secs)


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/midi")
    make_all_placeholder_midis(target)
    print(f"Wrote placeholder MIDIs to {target}")
