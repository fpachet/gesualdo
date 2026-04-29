"""Run the rhythm-first Gesualdo string-quartet reducer."""

from pathlib import Path

from gesualdo_reduction.reduction import (
    ENFORCE_RANGES,
    REGISTER_SPLIT,
    SEMITONES,
    reduce_to_quartet,
)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    midi_path = project_root.parent / "muses" / "data" / "gesualdo" / "gesualdo_vi_libro_madrigali_22.mid"
    out_path = project_root / "gesualdo_quartet_V2.musicxml"
    reduce_to_quartet(
        midi_path,
        semitones=SEMITONES,
        out_path=out_path,
        enforce_ranges=ENFORCE_RANGES,
        register_split=REGISTER_SPLIT,
    )
