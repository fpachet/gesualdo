"""Run the rhythm-first Gesualdo string-quartet reducer."""

from pathlib import Path

from gesualdo_reduction.reduction import (
    ENFORCE_RANGES,
    REGISTER_SPLIT,
    reduce_to_quartet,
)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    midi_path = (
        project_root
        / "data"
        / "kdf"
        / "book6"
        / "sources"
        / "book6_22_gia_piansi_nel_dolore.mid"
    )
    out_path = (
        project_root
        / "data"
        / "kdf"
        / "book6"
        / "reductions"
        / "string_quartet"
        / "book6_22_gia_piansi_nel_dolore.musicxml"
    )
    reduce_to_quartet(
        midi_path,
        out_path=out_path,
        enforce_ranges=ENFORCE_RANGES,
        register_split=REGISTER_SPLIT,
    )
