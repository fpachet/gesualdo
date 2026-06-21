#!/usr/bin/env python3
"""Optimize octave placement in a reduced MusicXML score and compare audits."""

from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path

from music21 import chord, converter, note, stream

from gesualdo_reduction.octave_optimization import OctaveOptimizationConfig, optimize_musicxml_octaves

import audit_part_coherence


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _event_signature(score: stream.Score) -> list[tuple[int, str, float, float, tuple[int, ...]]]:
    signature = []
    for part_index, part in enumerate(score.parts):
        for element in part.recurse().notesAndRests:
            measure = element.getContextByClass(stream.Measure)
            measure_number = "" if measure is None else str(getattr(measure, "number", ""))
            try:
                offset = float(element.getOffsetInHierarchy(part))
            except Exception:
                offset = float(element.offset)
            duration = float(element.quarterLength)
            if isinstance(element, note.Rest):
                pitch_classes: tuple[int, ...] = ()
            elif isinstance(element, note.Note):
                pitch_classes = (int(element.pitch.midi) % 12,)
            elif isinstance(element, chord.Chord):
                pitch_classes = tuple(sorted(int(pitch.midi) % 12 for pitch in element.pitches))
            else:
                continue
            signature.append((part_index, measure_number, offset, duration, pitch_classes))
    return signature


def verify_pitch_class_invariants(before_path: Path, after_path: Path) -> None:
    before = converter.parse(before_path)
    after = converter.parse(after_path)
    before_sig = _event_signature(before)
    after_sig = _event_signature(after)
    if before_sig != after_sig:
        for index, (left, right) in enumerate(zip(before_sig, after_sig, strict=False)):
            if left != right:
                raise AssertionError(f"Invariant mismatch at event {index}: {left} != {right}")
        raise AssertionError(f"Invariant length mismatch: {len(before_sig)} != {len(after_sig)}")


def _single_file_report(path: Path, report_path: Path) -> None:
    rows = [
        {
            "source_path": "",
            "source_parts": "",
            "output_path": str(path),
            "global_transposition": "",
            "status": "ok",
            "error": "",
        }
    ]
    _write_rows(report_path, list(rows[0]), rows)


def _audit_file(path: Path, label: str, tmpdir: Path) -> list[dict[str, str]]:
    report_path = tmpdir / f"{label}.tsv"
    _single_file_report(path, report_path)
    args = audit_part_coherence.build_parser().parse_args(
        [
            "--reports",
            str(report_path),
            "--output",
            str(tmpdir / f"{label}_issues.tsv"),
            "--parse-output",
            str(tmpdir / f"{label}_parse.tsv"),
            "--markdown-output",
            str(tmpdir / f"{label}.md"),
        ]
    )
    issue_rows, parse_rows = audit_part_coherence.run_audit(args)
    if parse_rows:
        raise RuntimeError(f"Audit parse issues for {path}: {parse_rows}")
    return issue_rows


def _count_by(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(field, "")
        counts[value] = counts.get(value, 0) + 1
    return counts


def write_comparison(path: Path, before_rows: list[dict[str, str]], after_rows: list[dict[str, str]]) -> None:
    before_counts = _count_by(before_rows, "kind")
    after_counts = _count_by(after_rows, "kind")
    kinds = sorted(set(before_counts) | set(after_counts))
    rows = [
        {
            "kind": kind,
            "before": str(before_counts.get(kind, 0)),
            "after": str(after_counts.get(kind, 0)),
            "delta": str(after_counts.get(kind, 0) - before_counts.get(kind, 0)),
        }
        for kind in kinds
    ]
    _write_rows(path, ["kind", "before", "after", "delta"], rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--change-report", type=Path, required=True)
    parser.add_argument("--comparison-report", type=Path, required=True)
    parser.add_argument("--before-audit", type=Path)
    parser.add_argument("--after-audit", type=Path)
    parser.add_argument("--max-octave-shift", type=int, default=1)
    parser.add_argument("--max-changes", type=int)
    parser.add_argument("--displacement-weight", type=float, default=12.0)
    parser.add_argument("--transition-weight", type=float, default=1.0)
    parser.add_argument("--register-weight", type=float, default=1.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = OctaveOptimizationConfig(
        max_octave_shift=args.max_octave_shift,
        max_changes=args.max_changes,
        displacement_weight=args.displacement_weight,
        transition_weight=args.transition_weight,
        register_weight=args.register_weight,
    )
    changes = optimize_musicxml_octaves(args.input, args.output, config=config)
    _write_rows(
        args.change_report,
        ["part", "measure", "offset", "old_pitches", "new_pitches", "duration", "reason"],
        [change.as_row() for change in changes],
    )
    verify_pitch_class_invariants(args.input, args.output)

    with tempfile.TemporaryDirectory(prefix="octave_audit_") as tmp:
        tmpdir = Path(tmp)
        before_rows = _audit_file(args.input, "before", tmpdir)
        after_rows = _audit_file(args.output, "after", tmpdir)
    write_comparison(args.comparison_report, before_rows, after_rows)
    if args.before_audit:
        _write_rows(args.before_audit, list(before_rows[0]) if before_rows else [], before_rows)
    if args.after_audit:
        _write_rows(args.after_audit, list(after_rows[0]) if after_rows else [], after_rows)

    print(f"Wrote optimized score: {args.output}")
    print(f"Wrote {len(changes)} octave changes: {args.change_report}")
    print(f"Wrote audit comparison: {args.comparison_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
