#!/usr/bin/env python3
"""Render reduction MusicXML files to conductor-review PDFs."""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from music21 import converter

from gesualdo_reduction.musicxml_compat import cleanup_musicxml_engraving
from gesualdo_reduction.notation_cleanup import NotationCleanupReport, cleanup_musicxml

from render_cpdl_mp3 import DEFAULT_MUSESCORE


MUSESCORE_CANDIDATES = (
    DEFAULT_MUSESCORE,
    Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore"),
)


def default_musescore_path() -> Path:
    for candidate in MUSESCORE_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_MUSESCORE


@dataclass(frozen=True)
class RenderJob:
    name: str
    report_path: Path
    output_field: str


DEFAULT_JOBS = {
    "kdf": RenderJob("kdf", Path("data/kdf/reductions/string_quartet_report.tsv"), "output"),
    "cpdl5:string_quartet": RenderJob(
        "cpdl5:string_quartet",
        Path("data/cpdl/5-voices/reductions/string_quartet/report.tsv"),
        "output_path",
    ),
    "cpdl5:string_quartet_plus_viole": RenderJob(
        "cpdl5:string_quartet_plus_viole",
        Path("data/cpdl/5-voices/reductions/string_quartet_plus_viole/report.tsv"),
        "output_path",
    ),
    "cpdl6:string_quartet": RenderJob(
        "cpdl6:string_quartet",
        Path("data/cpdl/6-voices/reductions/string_quartet/report.tsv"),
        "output_path",
    ),
    "take6:string_quartet_double_stops": RenderJob(
        "take6:string_quartet_double_stops",
        Path("data/take6/reductions/string_quartet_double_stops/report.tsv"),
        "output_path",
    ),
}
DEFAULT_JOB_NAMES = (
    "kdf",
    "cpdl5:string_quartet",
    "cpdl5:string_quartet_plus_viole",
    "cpdl6:string_quartet",
    "take6:string_quartet_double_stops",
)


def read_report(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle, delimiter="\t") if row.get("status") == "ok"]


def pdf_path_for_musicxml(musicxml_path: Path) -> Path:
    parts = list(musicxml_path.parts)
    if "reductions" in parts:
        index = parts.index("reductions")
        if index + 1 < len(parts):
            target = parts[index + 1]
            parts[index] = "renders"
            parts[index + 1] = f"{target}_pdf"
            return Path(*parts).with_suffix(".pdf")
    return musicxml_path.with_suffix(".pdf")


def run_musescore_pdf(musescore: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [str(musescore), "-o", str(output_path), str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def render_pdf(
    musescore: Path,
    input_path: Path,
    output_path: Path,
    *,
    clean_dynamics: bool,
    cleanup: bool,
) -> NotationCleanupReport:
    render_input = input_path
    report = NotationCleanupReport()
    if not cleanup:
        result = run_musescore_pdf(musescore, input_path, output_path)
        if result.returncode != 0:
            _render_pdf_from_midi_fallback(musescore, render_input, output_path)
            report.pdf_midi_fallbacks = 1
        return report

    with tempfile.TemporaryDirectory(prefix="review_pdf_") as tmpdir:
        clean_path = Path(tmpdir) / input_path.name
        if clean_dynamics:
            report = cleanup_musicxml(input_path, clean_path, clean_dynamics=clean_dynamics)
        else:
            shutil.copyfile(input_path, clean_path)
            xml_report = cleanup_musicxml_engraving(clean_path, clean_path)
            report.respelled_key_signature_accidentals = xml_report.respelled_key_signature_accidentals
            report.respelled_chromatic_context_accidentals = xml_report.respelled_chromatic_context_accidentals
            report.suppressed_naturals = xml_report.suppressed_redundant_accidentals
            report.cello_clef_changes_added = xml_report.cello_clef_changes
            report.viola_clef_changes_added = xml_report.viola_clef_changes
            report.final_barlines_added = xml_report.final_barlines_added
            report.normalized_dangling_ties = xml_report.normalized_dangling_ties
            report.normalized_tied_enharmonics = xml_report.normalized_tied_enharmonics
            report.normalized_adjacent_enharmonics = xml_report.normalized_adjacent_enharmonics
            report.removed_isolated_redundant_notes = xml_report.removed_isolated_redundant_notes
            report.extended_isolated_redundant_notes = xml_report.extended_isolated_redundant_notes
            report.normalized_fragmented_rests = xml_report.normalized_fragmented_rests
            report.extended_terminal_short_notes = xml_report.extended_terminal_short_notes
            report.applied_gia_piansi_line_cleanups = xml_report.applied_gia_piansi_line_cleanups
            report.applied_luci_serene_line_cleanups = xml_report.applied_luci_serene_line_cleanups
            report.applied_dolcissima_line_cleanups = xml_report.applied_dolcissima_line_cleanups
            report.applied_sio_non_miro_line_cleanups = xml_report.applied_sio_non_miro_line_cleanups
            report.applied_come_unto_me_line_cleanups = xml_report.applied_come_unto_me_line_cleanups
            report.applied_a_quiet_place_line_cleanups = xml_report.applied_a_quiet_place_line_cleanups
            report.applied_moro_lasso_line_cleanups = xml_report.applied_moro_lasso_line_cleanups
            report.applied_sparge_la_morte_line_cleanups = xml_report.applied_sparge_la_morte_line_cleanups
            report.applied_hark_herald_line_cleanups = xml_report.applied_hark_herald_line_cleanups
        result = run_musescore_pdf(musescore, clean_path, output_path)
        if result.returncode != 0:
            _render_pdf_from_midi_fallback(musescore, input_path, output_path)
            report.pdf_midi_fallbacks = 1
        return report


def _render_pdf_from_midi_fallback(musescore: Path, input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="review_pdf_midi_") as tmpdir:
        midi_path = Path(tmpdir) / f"{input_path.stem}.mid"
        converter.parse(input_path).write("midi", fp=str(midi_path))
        result = run_musescore_pdf(musescore, midi_path, output_path)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"MuseScore failed with return code {result.returncode}")


def render_job(root: Path, job: RenderJob, args: argparse.Namespace) -> dict[str, int]:
    report_path = root / job.report_path
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    rows = read_report(report_path)
    if args.limit:
        rows = rows[: args.limit]

    counts = {"rendered": 0, "skipped": 0, "failed": 0}
    audit_rows: list[dict[str, str]] = []
    clean_dynamics = args.mode == "clean"
    for index, row in enumerate(rows, start=1):
        input_path = root / row[job.output_field]
        output_path = root / pdf_path_for_musicxml(Path(row[job.output_field]))
        print(f"[{job.name} {index:03d}/{len(rows):03d}] {input_path} -> {output_path}", flush=True)

        audit = {
            "job": job.name,
            "input_path": str(input_path.relative_to(root)),
            "pdf_path": str(output_path.relative_to(root)),
            "mode": args.mode,
            "status": "",
            "error": "",
        }
        if output_path.exists() and not args.force:
            counts["skipped"] += 1
            audit["status"] = "skipped"
            audit.update(NotationCleanupReport().as_row())
            audit_rows.append(audit)
            continue

        try:
            cleanup_report = render_pdf(
                args.musescore,
                input_path,
                output_path,
                clean_dynamics=clean_dynamics,
                cleanup=not args.no_cleanup,
            )
            counts["rendered"] += 1
            audit["status"] = "rendered"
            audit.update(cleanup_report.as_row())
        except Exception as exc:  # noqa: BLE001 - batch export should report every miss.
            counts["failed"] += 1
            audit["status"] = "failed"
            audit["error"] = str(exc)
            audit.update(NotationCleanupReport().as_row())
            print(f"FAILED {input_path}: {exc}", flush=True)
        audit_rows.append(audit)

    write_audit(root, job, audit_rows)
    return counts


def write_audit(root: Path, job: RenderJob, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    first_pdf = Path(rows[0]["pdf_path"])
    audit_path = root / first_pdf.parent / "review_pdf_report.tsv"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "job",
        "input_path",
        "pdf_path",
        "mode",
        "status",
        "suppressed_naturals",
        "removed_dynamics",
        "removed_hairpins",
        "beat_readability_changes",
        "final_barlines_added",
        "cello_clef_changes_added",
        "viola_clef_changes_added",
        "respelled_key_signature_accidentals",
        "respelled_chromatic_context_accidentals",
        "suppressed_tie_continuation_accidentals",
        "normalized_dangling_ties",
        "normalized_tied_enharmonics",
        "normalized_adjacent_enharmonics",
        "removed_isolated_redundant_notes",
        "extended_isolated_redundant_notes",
        "normalized_fragmented_rests",
        "extended_terminal_short_notes",
        "applied_gia_piansi_line_cleanups",
        "applied_luci_serene_line_cleanups",
        "applied_dolcissima_line_cleanups",
        "applied_sio_non_miro_line_cleanups",
        "applied_come_unto_me_line_cleanups",
        "applied_a_quiet_place_line_cleanups",
        "applied_moro_lasso_line_cleanups",
        "applied_sparge_la_morte_line_cleanups",
        "applied_hark_herald_line_cleanups",
        "pdf_midi_fallbacks",
        "error",
    ]
    with audit_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            normalized["error"] = normalized.get("error") or "-"
            writer.writerow(normalized)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--musescore", type=Path, default=default_musescore_path())
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-cleanup", action="store_true", help="Render source MusicXML directly.")
    parser.add_argument("--mode", choices=("clean", "expressive"), default="clean")
    parser.add_argument(
        "--job",
        action="append",
        choices=tuple(DEFAULT_JOBS),
        help="Render one job. Defaults to all current review jobs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.musescore.exists():
        raise FileNotFoundError(args.musescore)

    job_names = args.job or list(DEFAULT_JOB_NAMES)
    totals = {"rendered": 0, "skipped": 0, "failed": 0}
    for job_name in job_names:
        counts = render_job(args.root, DEFAULT_JOBS[job_name], args)
        for key, value in counts.items():
            totals[key] += value
        print(f"{job_name}: {counts}", flush=True)

    print(f"done: {totals}", flush=True)
    return 0 if totals["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
