#!/usr/bin/env python3
"""Batch octave optimization for reviewable clean candidate reductions."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from gesualdo_reduction.notation_cleanup import cleanup_musicxml
from gesualdo_reduction.octave_optimization import OctaveOptimizationConfig, optimize_musicxml_octaves

import audit_part_coherence
from optimize_octaves import _audit_file, verify_pitch_class_invariants, write_comparison
from render_review_pdfs import default_musescore_path, run_musescore_pdf


DEFAULT_REPORTS = audit_part_coherence.DEFAULT_REPORTS
FIXABLE_KINDS = ("register_jump", "dangling_tie", "accidental_on_tie_continuation")
SUMMARY_FIELDS = [
    "batch",
    "work_id",
    "title",
    "input_path",
    "output_path",
    "pdf_path",
    "status",
    "error",
    "changes",
    "before_total",
    "after_total",
    "before_register_jump",
    "after_register_jump",
    "before_dangling_tie",
    "after_dangling_tie",
    "before_accidental_on_tie_continuation",
    "after_accidental_on_tie_continuation",
    "before_sparse_fragment",
    "after_sparse_fragment",
    "before_sparse_window",
    "after_sparse_window",
    "removed_dynamics",
    "removed_hairpins",
    "normalized_dangling_ties",
    "suppressed_tie_continuation_accidentals",
]


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _slug(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "work"


def _safe_work_slug(work: audit_part_coherence.WorkRow) -> str:
    if work.output_path is not None:
        return _slug(work.output_path.stem)
    return _slug(work.work_id or work.title)


def _issue_paths(issue_report: Path, kinds: set[str]) -> set[str]:
    return {
        row["output_path"]
        for row in _read_tsv(issue_report)
        if row.get("kind") in kinds and row.get("output_path")
    }


def _counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        kind = row.get("kind", "")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


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
    _write_tsv(report_path, list(rows[0]), rows)


def _write_changes(path: Path, changes) -> None:
    _write_tsv(
        path,
        ["part", "measure", "offset", "old_pitches", "new_pitches", "duration", "reason"],
        [change.as_row() for change in changes],
    )


def _write_cleanup_report(path: Path, cleanup_report) -> None:
    _write_tsv(path, list(cleanup_report.as_row()), [cleanup_report.as_row()])


def _candidate_rows(args: argparse.Namespace) -> list[audit_part_coherence.WorkRow]:
    fixable_paths = _issue_paths(args.issue_report, set(args.issue_kind)) if args.changed_only else set()
    rows: list[audit_part_coherence.WorkRow] = []
    include_batches = set(args.include_batch or [])
    for report in args.reports:
        for work in audit_part_coherence._rows_from_report(report):
            if work.status != "ok" or work.output_path is None:
                continue
            if include_batches and work.batch not in include_batches:
                continue
            if args.changed_only and str(work.output_path) not in fixable_paths:
                continue
            rows.append(work)
    return rows


def _summary_row(
    work: audit_part_coherence.WorkRow,
    input_path: Path,
    output_path: Path,
    pdf_path: Path | None,
    status: str,
    error: str,
    changes: int,
    before_rows: list[dict[str, str]],
    after_rows: list[dict[str, str]],
    cleanup_report,
) -> dict[str, str]:
    before_counts = _counts(before_rows)
    after_counts = _counts(after_rows)
    row = {
        "batch": work.batch,
        "work_id": work.work_id,
        "title": work.title,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "pdf_path": "" if pdf_path is None else str(pdf_path),
        "status": status,
        "error": error,
        "changes": str(changes),
        "before_total": str(len(before_rows)),
        "after_total": str(len(after_rows)),
    }
    for kind in (
        "register_jump",
        "dangling_tie",
        "accidental_on_tie_continuation",
        "sparse_fragment",
        "sparse_window",
    ):
        row[f"before_{kind}"] = str(before_counts.get(kind, 0))
        row[f"after_{kind}"] = str(after_counts.get(kind, 0))
    report_row = cleanup_report.as_row() if cleanup_report is not None else {}
    for field in (
        "removed_dynamics",
        "removed_hairpins",
        "normalized_dangling_ties",
        "suppressed_tie_continuation_accidentals",
    ):
        row[field] = report_row.get(field, "0")
    return row


def process_work(
    root: Path,
    output_root: Path,
    work: audit_part_coherence.WorkRow,
    config: OctaveOptimizationConfig,
    args: argparse.Namespace,
) -> dict[str, str]:
    assert work.output_path is not None
    input_path = root / work.output_path
    work_slug = _safe_work_slug(work)
    work_root = output_root / work.batch / work_slug
    output_path = work_root / f"{work_slug}_optimized.musicxml"
    pdf_path = work_root / f"{work_slug}_optimized.pdf" if args.render_pdfs else None
    changes_path = work_root / f"{work_slug}_octave_changes.tsv"
    before_audit_path = work_root / f"{work_slug}_before_audit.tsv"
    after_audit_path = work_root / f"{work_slug}_after_audit.tsv"
    comparison_path = work_root / f"{work_slug}_audit_comparison.tsv"
    cleanup_path = work_root / f"{work_slug}_cleanup_report.tsv"

    before_rows: list[dict[str, str]] = []
    after_rows: list[dict[str, str]] = []
    cleanup_report = None
    changes = []
    status = "ok"
    error = ""
    try:
        changes = optimize_musicxml_octaves(input_path, output_path, config=config)
        cleanup_report = cleanup_musicxml(output_path, output_path, clean_dynamics=True)
        verify_pitch_class_invariants(input_path, output_path)
        _write_changes(changes_path, changes)
        _write_cleanup_report(cleanup_path, cleanup_report)
        before_rows = _audit_file(input_path, "before", work_root)
        after_rows = _audit_file(output_path, "after", work_root)
        write_comparison(comparison_path, before_rows, after_rows)
        _write_tsv(before_audit_path, list(before_rows[0]) if before_rows else [], before_rows)
        _write_tsv(after_audit_path, list(after_rows[0]) if after_rows else [], after_rows)
        if args.render_pdfs and pdf_path is not None:
            result = run_musescore_pdf(args.musescore, output_path, pdf_path)
            if result.returncode != 0:
                status = "pdf_failed"
                error = result.stderr.strip() or f"MuseScore failed with return code {result.returncode}"
    except Exception as exc:  # noqa: BLE001 - batch mode should record each failure.
        status = "failed"
        error = str(exc)
    return _summary_row(
        work,
        input_path,
        output_path,
        pdf_path,
        status,
        error,
        len(changes),
        before_rows,
        after_rows,
        cleanup_report,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path("outputs/batch_octave_optimization"))
    parser.add_argument("--reports", type=Path, nargs="+", default=list(DEFAULT_REPORTS))
    parser.add_argument("--issue-report", type=Path, default=Path("outputs/reports/part_coherence_audit.tsv"))
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--include-batch", action="append")
    parser.add_argument("--issue-kind", action="append", default=list(FIXABLE_KINDS))
    parser.add_argument("--all", dest="changed_only", action="store_false", help="Process every ok row in the selected reports.")
    parser.set_defaults(changed_only=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-octave-shift", type=int, default=1)
    parser.add_argument("--max-changes", type=int, default=20)
    parser.add_argument("--displacement-weight", type=float, default=12.0)
    parser.add_argument("--transition-weight", type=float, default=1.0)
    parser.add_argument("--register-weight", type=float, default=1.0)
    parser.add_argument("--render-pdfs", action="store_true")
    parser.add_argument("--musescore", type=Path, default=default_musescore_path())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root
    output_root = root / args.output_root
    summary_path = root / (args.summary or args.output_root / "summary.tsv")
    rows = _candidate_rows(args)
    if args.limit:
        rows = rows[: args.limit]

    config = OctaveOptimizationConfig(
        max_octave_shift=args.max_octave_shift,
        max_changes=args.max_changes,
        displacement_weight=args.displacement_weight,
        transition_weight=args.transition_weight,
        register_weight=args.register_weight,
    )

    summary_rows: list[dict[str, str]] = []
    total = len(rows)
    for index, work in enumerate(rows, start=1):
        print(f"[{index:03d}/{total:03d}] {work.batch} {work.output_path}", flush=True)
        summary_rows.append(process_work(root, output_root, work, config, args))
        _write_tsv(summary_path, SUMMARY_FIELDS, summary_rows)

    failed = sum(1 for row in summary_rows if row["status"] == "failed")
    pdf_failed = sum(1 for row in summary_rows if row["status"] == "pdf_failed")
    print(f"Wrote {len(summary_rows)} rows to {summary_path}", flush=True)
    print(f"Failed: {failed}", flush=True)
    print(f"PDF failed: {pdf_failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
