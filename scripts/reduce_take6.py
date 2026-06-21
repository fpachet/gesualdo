#!/usr/bin/env python3
"""Generate Take 6-tuned six-voice string-quartet reductions."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from music21 import converter, tempo

from gesualdo_reduction.musicxml_compat import strip_time_modifications
from gesualdo_reduction.reduction import (
    normalize_musescore_grid_rhythm,
    normalize_musescore_rhythm_artifacts,
    reduce_take6_to_quartet,
    title_from_source_path,
)


SUPPORTED_SUFFIXES = {".mxl", ".musicxml", ".xml", ".mid", ".midi"}
MUSESCORE_GRID_NORMALIZATION_STEMS = {"if_we_ever", "come_unto_me"}


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return slug or "untitled"


def output_stem(source_path: Path) -> str:
    return slugify(title_from_source_path(source_path))


def discover_sources(input_dir: Path | None, explicit_sources: list[Path]) -> list[Path]:
    sources = list(explicit_sources)
    if input_dir is not None:
        sources.extend(
            path
            for path in sorted(input_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )
    unique: dict[Path, None] = {}
    for source in sources:
        unique[source] = None
    return list(unique)


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "source_path",
        "source_parts",
        "output_path",
        "global_transposition",
        "status",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def load_tempo_overrides(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return {str(key): int(value) for key, value in raw.items()}


def apply_tempo_override(score, bpm: int) -> None:
    for mark in list(score.recurse().getElementsByClass(tempo.MetronomeMark)):
        if mark.activeSite is not None:
            mark.activeSite.remove(mark)
    if not score.parts:
        return
    measures = list(score.parts[0].getElementsByClass("Measure"))
    if not measures:
        return
    measures[0].insert(0, tempo.MetronomeMark(number=bpm))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="*", type=Path)
    parser.add_argument("--input-dir", type=Path, default=Path("data/take6/sources"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/take6/reductions/string_quartet_double_stops"))
    parser.add_argument("--tempo-overrides", type=Path, default=Path("data/take6/tempo_overrides.json"))
    parser.add_argument("--semitones", type=int, default=None)
    parser.add_argument(
        "--double-stops",
        dest="double_stops",
        action="store_true",
        default=True,
        help="Add conservative source double stops when playable. Enabled by default.",
    )
    parser.add_argument(
        "--no-double-stops",
        dest="double_stops",
        action="store_false",
        help="Generate the older plain quartet comparison without double stops.",
    )
    parser.add_argument(
        "--no-normalize-artifacts",
        action="store_true",
        help="Disable conservative cleanup of isolated MIDI note+rest duration artifacts.",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate existing reductions.")
    args = parser.parse_args()

    input_dir = args.input_dir if args.input_dir.exists() else None
    sources = discover_sources(input_dir, args.sources)
    if not sources:
        print("No Take 6 source files found.", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tempo_overrides = load_tempo_overrides(args.tempo_overrides)
    report_rows: list[dict[str, str]] = []
    for ordinal, source_path in enumerate(sources, start=1):
        output_path = args.output_dir / f"{output_stem(source_path)}.musicxml"
        print(f"[{ordinal:03d}/{len(sources):03d}] {source_path}", flush=True)
        try:
            parsed = converter.parse(source_path)
            source_parts = len(parsed.parts)
            if source_parts != 6:
                raise ValueError(f"expected 6 parts, found {source_parts}")

            if output_path.exists() and not args.force:
                reduced = converter.parse(output_path)
            else:
                reduced = reduce_take6_to_quartet(
                    source_path,
                    semitones=args.semitones,
                    out_path=output_path,
                    add_source_double_stops=args.double_stops,
                    normalize_short_note_rest_artifacts=not args.no_normalize_artifacts,
                )
            stem = output_stem(source_path)
            tempo_override = tempo_overrides.get(stem)
            should_write = False
            if tempo_override is not None:
                apply_tempo_override(reduced, tempo_override)
                normalize_musescore_rhythm_artifacts(reduced)
                should_write = True
            if stem in MUSESCORE_GRID_NORMALIZATION_STEMS:
                normalize_musescore_grid_rhythm(reduced)
                should_write = True
            if should_write:
                reduced.write("musicxml", fp=str(output_path))
            strip_time_modifications(output_path)
            report_rows.append(
                {
                    "source_path": str(source_path),
                    "source_parts": str(source_parts),
                    "output_path": str(output_path),
                    "global_transposition": str(getattr(reduced.editorial, "globalTransposition", "")),
                    "status": "ok",
                    "error": "",
                }
            )
        except Exception as exc:
            report_rows.append(
                {
                    "source_path": str(source_path),
                    "source_parts": "",
                    "output_path": str(output_path),
                    "global_transposition": "",
                    "status": "error",
                    "error": str(exc),
                }
            )

    write_report(args.output_dir / "report.tsv", report_rows)
    error_count = sum(row["status"] == "error" for row in report_rows)
    print(f"Generated {len(report_rows) - error_count} reductions. Logged {error_count} errors.")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
