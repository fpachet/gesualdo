"""Analysis helpers for madrigal-to-string-quartet reduction experiments."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from muses.base.temporals import Piece


DEFAULT_DESIRED_LOW = 36  # C2, cello's open C.


def dense_chords(piece: Piece, max_pitch_classes: int = 4):
    """Return chordified sonorities with more than ``max_pitch_classes`` classes."""

    return [
        chord for chord in piece.chordify(min_notes=max_pitch_classes + 1)
        if len({pitch % 12 for pitch in chord.pitches}) > max_pitch_classes
    ]


def voice_ranges(piece: Piece) -> list[tuple[int, int]]:
    """Return the MIDI pitch range for each melody/voice in ``piece``."""

    return [melody.get_pitch_range() for melody in piece.melodies]


def transposition_plan(piece: Piece, desired_low: int = DEFAULT_DESIRED_LOW) -> dict[str, Any]:
    """Estimate a global transposition that maps the lowest note to ``desired_low``."""

    ranges = voice_ranges(piece)
    if not ranges:
        return {
            "voice_ranges": [],
            "lowest_note": None,
            "highest_note": None,
            "transposition_interval": 0,
            "transposed_voice_ranges": [],
        }

    lowest_note = min(low for low, _ in ranges)
    highest_note = max(high for _, high in ranges)
    interval = desired_low - lowest_note
    return {
        "voice_ranges": ranges,
        "lowest_note": lowest_note,
        "highest_note": highest_note,
        "transposition_interval": interval,
        "transposed_voice_ranges": [(low + interval, high + interval) for low, high in ranges],
    }


def analyze_midi(midi_path: str | Path, desired_low: int = DEFAULT_DESIRED_LOW) -> dict[str, Any]:
    """Load a MIDI file with MusES and compute first-pass reduction diagnostics."""

    piece = Piece.load_midi(midi_path)
    chords = dense_chords(piece)
    return {
        "piece": piece,
        "dense_chords": chords,
        **transposition_plan(piece, desired_low=desired_low),
    }


def format_report(analysis: dict[str, Any]) -> str:
    """Format analysis results for the command line."""

    lines = [
        f"voices: {len(analysis['voice_ranges'])}",
        f"voice ranges: {analysis['voice_ranges']}",
        f"lowest note: {analysis['lowest_note']}",
        f"highest note: {analysis['highest_note']}",
        f"transposition interval: {analysis['transposition_interval']}",
        f"transposed ranges: {analysis['transposed_voice_ranges']}",
        f"dense sonorities: {len(analysis['dense_chords'])}",
    ]
    for chord in analysis["dense_chords"][:12]:
        lines.append(f"  {chord.start_beat:>8.3f}: {chord.get_pitches()}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("midi", type=Path, help="MIDI file to analyze.")
    parser.add_argument(
        "--desired-low",
        type=int,
        default=DEFAULT_DESIRED_LOW,
        help="Target MIDI pitch for the lowest note after global transposition.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print(format_report(analyze_midi(args.midi, desired_low=args.desired_low)))


if __name__ == "__main__":
    main()
