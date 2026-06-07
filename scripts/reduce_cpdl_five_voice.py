#!/usr/bin/env python3
"""Generate enriched string-quartet reductions from five-voice CPDL sources."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from music21 import converter

from gesualdo_reduction.reduction import reduce_to_quartet


FIVE_VOICE_SECTIONS = {
    "Sacred works for five voices",
    "Secular works for five voices",
}
PREFERRED_FORMAT_ORDER = {"mxl": 0, "musicxml": 1, "xml": 2, "mid": 3, "midi": 4}


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return slug or "untitled"


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_report(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "work_index",
        "section",
        "work_title",
        "source_path",
        "source_format",
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


def five_voice_work_groups(rows: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["section"] in FIVE_VOICE_SECTIONS:
            groups[row["work_index"]].append(row)
    return sorted(groups.items(), key=lambda item: int(item[0]))


def sorted_candidates(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            PREFERRED_FORMAT_ORDER.get(row["format"].lower(), 99),
            int(row["download_index"]),
            row["local_path"],
        ),
    )


def parseable_five_part_sources(rows: list[dict[str, str]]) -> tuple[list[tuple[dict[str, str], int]], list[str]]:
    sources: list[tuple[dict[str, str], int]] = []
    errors: list[str] = []
    for row in sorted_candidates(rows):
        source_path = Path(row["local_path"])
        try:
            score = converter.parse(source_path)
            part_count = len(score.parts)
        except Exception as exc:  # pragma: no cover - exercised by corpus script
            errors.append(f"{source_path}: parse failed: {exc}")
            continue
        if part_count == 5:
            sources.append((row, part_count))
        else:
            errors.append(f"{source_path}: expected 5 parts, found {part_count}")
    return sources, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/cpdl/manifest.tsv"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/cpdl_reductions/five_voice_string_quartet"),
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit works for quick test runs.")
    parser.add_argument("--force", action="store_true", help="Regenerate existing reductions.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_rows: list[dict[str, str]] = []
    work_groups = five_voice_work_groups(read_manifest(args.manifest))
    if args.limit:
        work_groups = work_groups[: args.limit]

    print(f"Found {len(work_groups)} CPDL five-voice work pages.")
    for ordinal, (work_index, rows) in enumerate(work_groups, start=1):
        first = rows[0]
        work_title = first["work_title"]
        output_path = args.output_dir / f"{int(work_index):03d}_{slugify(work_title)}__quartet_rhythm_first.musicxml"
        print(f"[{ordinal:03d}/{len(work_groups):03d}] {work_title}", flush=True)

        try:
            sources, source_errors = parseable_five_part_sources(rows)
            if not sources:
                raise ValueError("; ".join(source_errors) if source_errors else "no candidate source files")
            reduction_errors = []
            source_row: dict[str, str] | None = None
            source_parts = 0
            global_transposition = ""
            for candidate_row, candidate_parts in sources:
                try:
                    if output_path.exists() and not args.force:
                        reduced = converter.parse(output_path)
                        global_transposition = getattr(reduced.editorial, "globalTransposition", "")
                    else:
                        reduced = reduce_to_quartet(
                            candidate_row["local_path"],
                            out_path=output_path,
                            preserve_active_voice_count=True,
                            add_editorial_harmony=True,
                            add_editorial_thirds=True,
                        )
                        global_transposition = getattr(reduced.editorial, "globalTransposition", "")
                    source_row = candidate_row
                    source_parts = candidate_parts
                    break
                except Exception as exc:
                    reduction_errors.append(f"{candidate_row['local_path']}: reduction failed: {exc}")
            if source_row is None:
                all_errors = [*source_errors, *reduction_errors]
                raise ValueError("; ".join(all_errors) if all_errors else "no usable candidate source files")
            report_rows.append(
                {
                    "work_index": work_index,
                    "section": first["section"],
                    "work_title": work_title,
                    "source_path": source_row["local_path"],
                    "source_format": source_row["format"],
                    "source_parts": str(source_parts),
                    "output_path": str(output_path),
                    "global_transposition": str(global_transposition),
                    "status": "ok",
                    "error": "",
                }
            )
        except Exception as exc:
            report_rows.append(
                {
                    "work_index": work_index,
                    "section": first["section"],
                    "work_title": work_title,
                    "source_path": "",
                    "source_format": "",
                    "source_parts": "",
                    "output_path": str(output_path),
                    "global_transposition": "",
                    "status": "error",
                    "error": str(exc),
                }
            )

    write_report(args.output_dir / "report.tsv", report_rows)
    ok_count = sum(row["status"] == "ok" for row in report_rows)
    error_count = len(report_rows) - ok_count
    print(f"Generated {ok_count} reductions. Logged {error_count} errors.")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
