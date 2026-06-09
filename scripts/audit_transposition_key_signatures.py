#!/usr/bin/env python3
"""Audit nearby transpositions for easier printed key signatures.

The reduction scorer already optimizes instrumental range/register fit.  This
audit adds a separate key-signature burden check around each current global
transposition, then flags only nearby alternatives that keep a comparable
tessitura score.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from music21 import converter, key

from gesualdo_reduction import QUARTET_PLUS_VIOLE, STRING_QUARTET, EnsembleProfile, score_global_transposition


DEFAULT_REPORTS = (
    Path("data/kdf/reductions/string_quartet_report.tsv"),
    Path("data/cpdl/5-voices/reductions/string_quartet/report.tsv"),
    Path("data/cpdl/5-voices/reductions/string_quartet_plus_viole/report.tsv"),
    Path("data/cpdl/6-voices/reductions/string_quartet/report.tsv"),
)


@dataclass(frozen=True)
class WorkRow:
    batch: str
    work_id: str
    title: str
    source_path: Path | None
    output_path: Path | None
    current_semitones: int | None
    profile: EnsembleProfile
    source_status: str
    source_error: str


@dataclass(frozen=True)
class KeyBurden:
    average_abs: float
    max_abs: int
    signature_count: int


@dataclass(frozen=True)
class Candidate:
    semitones: int
    key_burden: KeyBurden
    tessitura_score: float
    tessitura_ok: bool


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _batch_name(report_path: Path) -> str:
    text = str(report_path)
    if "data/kdf/" in text:
        return "kdf_string_quartet"
    if "5-voices" in text and "string_quartet_plus_viole" in text:
        return "cpdl_5_voice_quartet_plus_viole"
    if "5-voices" in text:
        return "cpdl_5_voice_string_quartet"
    if "6-voices" in text:
        return "cpdl_6_voice_string_quartet"
    return report_path.parent.name


def _profile_for_report(report_path: Path) -> EnsembleProfile:
    if "string_quartet_plus_viole" in str(report_path):
        return QUARTET_PLUS_VIOLE
    return STRING_QUARTET


def _rows_from_report(report_path: Path) -> list[WorkRow]:
    batch = _batch_name(report_path)
    profile = _profile_for_report(report_path)
    works: list[WorkRow] = []

    for row in _read_tsv(report_path):
        if batch.startswith("kdf"):
            work_id = f"{row.get('book', '')} {row.get('title', '')}".strip()
            title = row.get("title", "")
            source_path = Path(row["filename"]) if row.get("filename") else None
            output_path = Path(row["output"]) if row.get("output") else None
            current_semitones = _int_or_none(row.get("chosen_semitones"))
            status = row.get("status", "")
            error = row.get("error", "")
        else:
            work_id = row.get("work_index", "")
            title = row.get("work_title", "")
            source_path = Path(row["source_path"]) if row.get("source_path") else None
            output_path = Path(row["output_path"]) if row.get("output_path") else None
            current_semitones = _int_or_none(row.get("global_transposition"))
            status = row.get("status", "")
            error = row.get("error", "")

        works.append(
            WorkRow(
                batch=batch,
                work_id=work_id,
                title=title,
                source_path=source_path,
                output_path=output_path,
                current_semitones=current_semitones,
                profile=profile,
                source_status=status,
                source_error=error,
            )
        )
    return works


def _key_signature_changes(score) -> list[tuple[float, tuple[int, ...]]]:
    by_offset: dict[float, set[int]] = {}
    for key_sig in score.recurse().getElementsByClass(key.KeySignature):
        try:
            offset = float(key_sig.getOffsetInHierarchy(score))
        except Exception:
            offset = float(key_sig.offset)
        by_offset.setdefault(offset, set()).add(int(key_sig.sharps or 0))

    if not by_offset:
        # If the source carries no key signature, the printed burden is unknown.
        return []

    if 0.0 not in by_offset:
        by_offset[0.0] = {0}

    return [(offset, tuple(sorted(sharps))) for offset, sharps in sorted(by_offset.items())]


def _transpose_signature_sharps(sharps: int, semitones: int) -> int:
    return int(key.KeySignature(sharps).transpose(semitones).sharps)


def key_signature_burden(score, semitones: int) -> KeyBurden:
    changes = _key_signature_changes(score)
    if not changes:
        return KeyBurden(average_abs=math.nan, max_abs=0, signature_count=0)

    highest_time = max(float(score.highestTime or 0.0), changes[-1][0])
    weighted = 0.0
    total = 0.0
    max_abs = 0
    for index, (offset, sharps_values) in enumerate(changes):
        next_offset = changes[index + 1][0] if index + 1 < len(changes) else highest_time
        duration = max(0.0, next_offset - offset)
        if duration == 0.0 and index == len(changes) - 1:
            duration = 1.0

        transposed = [_transpose_signature_sharps(sharps, semitones) for sharps in sharps_values]
        abs_values = [abs(value) for value in transposed]
        max_abs = max(max_abs, max(abs_values, default=0))
        weighted += (sum(abs_values) / max(len(abs_values), 1)) * duration
        total += duration

    return KeyBurden(
        average_abs=weighted / total if total > 0 else 0.0,
        max_abs=max_abs,
        signature_count=sum(len(sharps_values) for _offset, sharps_values in changes),
    )


def _candidate_window(current: int, radius: int) -> list[int]:
    return list(range(current - radius, current + radius + 1))


def evaluate_candidates(
    score,
    profile: EnsembleProfile,
    current_semitones: int,
    *,
    radius: int,
    tessitura_abs_tolerance: float,
    tessitura_rel_tolerance: float,
) -> list[Candidate]:
    current_tessitura = score_global_transposition(score, profile, current_semitones)
    allowed_tessitura = current_tessitura + max(tessitura_abs_tolerance, current_tessitura * tessitura_rel_tolerance)
    candidates: list[Candidate] = []
    for semitones in _candidate_window(current_semitones, radius):
        tessitura_score = score_global_transposition(score, profile, semitones)
        candidates.append(
            Candidate(
                semitones=semitones,
                key_burden=key_signature_burden(score, semitones),
                tessitura_score=tessitura_score,
                tessitura_ok=tessitura_score <= allowed_tessitura,
            )
        )
    return candidates


def _best_cleaner_candidate(
    candidates: Iterable[Candidate],
    current: Candidate,
    *,
    min_abs_improvement: float,
    min_rel_improvement: float,
) -> Candidate | None:
    usable = [
        candidate
        for candidate in candidates
        if candidate.semitones != current.semitones
        and candidate.tessitura_ok
        and not math.isnan(candidate.key_burden.average_abs)
    ]
    if not usable or math.isnan(current.key_burden.average_abs):
        return None

    best = min(
        usable,
        key=lambda candidate: (
            candidate.key_burden.average_abs,
            candidate.tessitura_score,
            abs(candidate.semitones - current.semitones),
            abs(candidate.semitones),
        ),
    )
    improvement = current.key_burden.average_abs - best.key_burden.average_abs
    rel = improvement / current.key_burden.average_abs if current.key_burden.average_abs > 0 else 0.0
    if improvement >= min_abs_improvement and rel >= min_rel_improvement:
        return best
    return None


def _fmt(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.6g}"
    return str(value)


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _batch_status_counts(rows: list[dict[str, str]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key_value = (row.get("batch", ""), row.get("status", ""))
        counts[key_value] = counts.get(key_value, 0) + 1
    return counts


def _markdown_table(rows: list[dict[str, str]], fields: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for label, _field in fields) + " |",
        "| " + " | ".join("---" for _label, _field in fields) + " |",
    ]
    for row in rows:
        values = []
        for _label, field in fields:
            value = row.get(field, "")
            values.append(value.replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_markdown_summary(
    path: Path,
    summary_rows: list[dict[str, str]],
    *,
    radius: int,
    min_abs_improvement: float,
    min_rel_improvement: float,
    tessitura_abs_tolerance: float,
    tessitura_rel_tolerance: float,
    top_n: int = 40,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = _status_counts(summary_rows)
    batch_counts = _batch_status_counts(summary_rows)
    attention_rows = [row for row in summary_rows if row.get("status") == "attention"]
    attention_rows.sort(key=lambda row: float(row.get("key_burden_delta") or 0.0), reverse=True)

    lines = [
        "# Global Transposition Key-Signature Audit",
        "",
        "This audit checks whether a nearby global transposition would materially reduce the printed key-signature burden while preserving the current instrumental tessitura fit.",
        "",
        "Method:",
        f"- Candidate window: current transposition +/- {radius} semitones.",
        "- Key-signature burden: duration-weighted average of `abs(sharps)` after transposition; lower is easier.",
        "- Tessitura guard: reuse the reducer's existing `score_global_transposition` range/register score.",
        f"- A candidate is allowed when its tessitura score is no worse than the current score by max({tessitura_abs_tolerance:g}, {tessitura_rel_tolerance:g} relative).",
        f"- A piece is flagged when the allowed candidate improves key burden by at least {min_abs_improvement:g} and {min_rel_improvement:.0%}.",
        "",
        "## Status Counts",
        "",
        "| Status | Count |",
        "| --- | --- |",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"| {status} | {count} |")

    lines.extend(["", "## Counts By Batch", "", "| Batch | Attention | OK | Other |", "| --- | ---: | ---: | ---: |"])
    batches = sorted({row.get("batch", "") for row in summary_rows})
    for batch in batches:
        attention = batch_counts.get((batch, "attention"), 0)
        ok = batch_counts.get((batch, "ok"), 0)
        other = sum(count for (batch_name, status), count in batch_counts.items() if batch_name == batch and status not in {"attention", "ok"})
        lines.append(f"| {batch} | {attention} | {ok} | {other} |")

    lines.extend(
        [
            "",
            f"## Largest Attention Cases (Top {min(top_n, len(attention_rows))})",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            attention_rows[:top_n],
            [
                ("Batch", "batch"),
                ("Work", "work_id"),
                ("Title", "title"),
                ("Current", "current_semitones"),
                ("Current burden", "current_key_burden"),
                ("Candidate", "best_semitones"),
                ("Candidate burden", "best_key_burden"),
                ("Delta", "key_burden_delta"),
                ("Tessitura delta", "tessitura_delta"),
            ],
        )
    )
    lines.extend(
        [
            "",
            "Full per-piece results are in `transposition_key_signature_audit.tsv`; all candidate scores are in `transposition_key_signature_candidates.tsv`.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def run_audit(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    summary_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []
    works = [work for report in args.reports for work in _rows_from_report(report)]

    for index, work in enumerate(works, start=1):
        if args.verbose:
            print(f"[{index:03d}/{len(works):03d}] {work.batch}: {work.title}", flush=True)

        base_row = {
            "batch": work.batch,
            "work_id": work.work_id,
            "title": work.title,
            "source_path": str(work.source_path or ""),
            "output_path": str(work.output_path or ""),
            "current_semitones": _fmt(work.current_semitones),
        }
        if work.source_status != "ok":
            summary_rows.append({**base_row, "status": "source_status_error", "note": work.source_error})
            continue
        if work.source_path is None or work.current_semitones is None:
            summary_rows.append({**base_row, "status": "missing_source_or_transposition", "note": ""})
            continue

        try:
            score = converter.parse(work.source_path)
            candidates = evaluate_candidates(
                score,
                work.profile,
                work.current_semitones,
                radius=args.radius,
                tessitura_abs_tolerance=args.tessitura_abs_tolerance,
                tessitura_rel_tolerance=args.tessitura_rel_tolerance,
            )
        except Exception as exc:
            summary_rows.append({**base_row, "status": "parse_or_score_error", "note": str(exc)})
            continue

        current = next(candidate for candidate in candidates if candidate.semitones == work.current_semitones)
        best = _best_cleaner_candidate(
            candidates,
            current,
            min_abs_improvement=args.min_abs_improvement,
            min_rel_improvement=args.min_rel_improvement,
        )
        status = "attention" if best else "ok"
        if current.key_burden.signature_count == 0:
            status = "no_key_signature_data"

        best_key_delta = None if best is None else current.key_burden.average_abs - best.key_burden.average_abs
        best_tess_delta = None if best is None else best.tessitura_score - current.tessitura_score
        summary_rows.append(
            {
                **base_row,
                "current_key_burden": _fmt(current.key_burden.average_abs),
                "current_max_key_abs": _fmt(current.key_burden.max_abs),
                "current_tessitura_score": _fmt(current.tessitura_score),
                "best_semitones": _fmt(best.semitones if best else None),
                "best_key_burden": _fmt(best.key_burden.average_abs if best else None),
                "best_max_key_abs": _fmt(best.key_burden.max_abs if best else None),
                "best_tessitura_score": _fmt(best.tessitura_score if best else None),
                "key_burden_delta": _fmt(best_key_delta),
                "tessitura_delta": _fmt(best_tess_delta),
                "status": status,
                "note": "",
            }
        )

        for candidate in candidates:
            candidate_rows.append(
                {
                    **base_row,
                    "candidate_semitones": _fmt(candidate.semitones),
                    "candidate_key_burden": _fmt(candidate.key_burden.average_abs),
                    "candidate_max_key_abs": _fmt(candidate.key_burden.max_abs),
                    "candidate_tessitura_score": _fmt(candidate.tessitura_score),
                    "candidate_tessitura_ok": "yes" if candidate.tessitura_ok else "no",
                    "candidate_is_current": "yes" if candidate.semitones == work.current_semitones else "no",
                }
            )

    return summary_rows, candidate_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reports",
        nargs="+",
        type=Path,
        default=list(DEFAULT_REPORTS),
        help="Reduction TSV reports to audit.",
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/reports/transposition_key_signature_audit.tsv"))
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=Path("outputs/reports/transposition_key_signature_candidates.tsv"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("outputs/reports/transposition_key_signature_audit.md"),
    )
    parser.add_argument("--radius", type=int, default=5, help="Semitone radius around the current transposition.")
    parser.add_argument(
        "--min-abs-improvement",
        type=float,
        default=2.0,
        help="Minimum average key-signature burden reduction to flag.",
    )
    parser.add_argument(
        "--min-rel-improvement",
        type=float,
        default=0.40,
        help="Minimum relative key-signature burden reduction to flag.",
    )
    parser.add_argument(
        "--tessitura-abs-tolerance",
        type=float,
        default=0.05,
        help="Allowed absolute tessitura-score increase over the current transposition.",
    )
    parser.add_argument(
        "--tessitura-rel-tolerance",
        type=float,
        default=0.10,
        help="Allowed relative tessitura-score increase over the current transposition.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary_rows, candidate_rows = run_audit(args)

    summary_fields = [
        "batch",
        "work_id",
        "title",
        "source_path",
        "output_path",
        "current_semitones",
        "current_key_burden",
        "current_max_key_abs",
        "current_tessitura_score",
        "best_semitones",
        "best_key_burden",
        "best_max_key_abs",
        "best_tessitura_score",
        "key_burden_delta",
        "tessitura_delta",
        "status",
        "note",
    ]
    candidate_fields = [
        "batch",
        "work_id",
        "title",
        "source_path",
        "output_path",
        "current_semitones",
        "candidate_semitones",
        "candidate_key_burden",
        "candidate_max_key_abs",
        "candidate_tessitura_score",
        "candidate_tessitura_ok",
        "candidate_is_current",
    ]
    _write_rows(args.output, summary_fields, summary_rows)
    _write_rows(args.candidate_output, candidate_fields, candidate_rows)
    write_markdown_summary(
        args.markdown_output,
        summary_rows,
        radius=args.radius,
        min_abs_improvement=args.min_abs_improvement,
        min_rel_improvement=args.min_rel_improvement,
        tessitura_abs_tolerance=args.tessitura_abs_tolerance,
        tessitura_rel_tolerance=args.tessitura_rel_tolerance,
    )

    attention = sum(row.get("status") == "attention" for row in summary_rows)
    ok = sum(row.get("status") == "ok" for row in summary_rows)
    print(f"Wrote {args.output} ({len(summary_rows)} rows; {attention} attention, {ok} ok).")
    print(f"Wrote {args.candidate_output} ({len(candidate_rows)} rows).")
    print(f"Wrote {args.markdown_output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
