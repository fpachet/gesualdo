#!/usr/bin/env python3
"""Apply obvious key-signature transposition improvements in place."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from gesualdo_reduction import reduce_to_quartet, reduce_to_quartet_plus_viole
from gesualdo_reduction.reduction import reduce_six_to_quartet


DEFAULT_AUDIT = Path("outputs/reports/transposition_key_signature_audit.tsv")
DEFAULT_OUTPUT_ROOT = Path("outputs/transposition_comparison/obvious_key_signature")

REPORTS_BY_BATCH = {
    "kdf_string_quartet": Path("data/kdf/reductions/string_quartet_report.tsv"),
    "cpdl_5_voice_string_quartet": Path("data/cpdl/5-voices/reductions/string_quartet/report.tsv"),
    "cpdl_5_voice_quartet_plus_viole": Path("data/cpdl/5-voices/reductions/string_quartet_plus_viole/report.tsv"),
    "cpdl_6_voice_string_quartet": Path("data/cpdl/6-voices/reductions/string_quartet/report.tsv"),
}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _selected_rows(path: Path, max_tessitura_delta: float) -> list[dict[str, str]]:
    rows = _read_tsv(path)
    return sorted(
        [
            row
            for row in rows
            if row.get("status") == "attention"
            and row.get("best_semitones")
            and row.get("source_path")
            and row.get("output_path")
            and float(row.get("tessitura_delta") or 0.0) <= max_tessitura_delta
        ],
        key=lambda row: (row["batch"], row["work_id"], row["title"]),
    )


def _comparison_stem(row: dict[str, str]) -> str:
    old = int(row["current_semitones"])
    new = int(row["best_semitones"])
    return f"{Path(row['output_path']).stem}__t{old:+d}_to_{new:+d}"


def _snapshot_path(row: dict[str, str], output_root: Path, kind: str) -> Path:
    path = output_root / row["batch"] / kind / f"{_comparison_stem(row)}.musicxml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _reduce(row: dict[str, str]) -> None:
    source_path = Path(row["source_path"])
    output_path = Path(row["output_path"])
    semitones = int(row["best_semitones"])
    batch = row["batch"]

    if batch in {"kdf_string_quartet", "cpdl_5_voice_string_quartet"}:
        reduce_to_quartet(
            source_path,
            semitones=semitones,
            out_path=output_path,
            preserve_active_voice_count=True,
            add_editorial_harmony=True,
            add_editorial_thirds=True,
        )
        return

    if batch == "cpdl_5_voice_quartet_plus_viole":
        reduce_to_quartet_plus_viole(source_path, semitones=semitones, out_path=output_path)
        return

    if batch == "cpdl_6_voice_string_quartet":
        reduce_six_to_quartet(source_path, semitones=semitones, out_path=output_path)
        return

    raise ValueError(f"Unsupported batch: {batch}")


def _report_key(row: dict[str, str]) -> tuple[str, str]:
    if row["batch"] == "kdf_string_quartet":
        return ("output", row["output_path"])
    return ("output_path", row["output_path"])


def update_reports(applied_rows: list[dict[str, str]]) -> None:
    by_batch: dict[str, dict[str, dict[str, str]]] = {}
    for row in applied_rows:
        key_name, key_value = _report_key(row)
        by_batch.setdefault(row["batch"], {})[key_value] = row | {"_key_name": key_name}

    for batch, updates in by_batch.items():
        report_path = REPORTS_BY_BATCH[batch]
        rows = _read_tsv(report_path)
        fieldnames = list(rows[0].keys()) if rows else []
        for report_row in rows:
            key_name = "output" if batch == "kdf_string_quartet" else "output_path"
            update = updates.get(report_row.get(key_name, ""))
            if update is None:
                continue
            if batch == "kdf_string_quartet":
                report_row["chosen_semitones"] = update["best_semitones"]
                report_row["transposition_score"] = update["best_tessitura_score"]
            else:
                report_row["global_transposition"] = update["best_semitones"]
        _write_tsv(report_path, rows, fieldnames)


def _mp3_path_for_output(output_path: Path) -> Path:
    parts = output_path.parts
    if "cpdl" in parts:
        voice_dir = parts[parts.index("cpdl") + 1]
        target = parts[parts.index("reductions") + 1]
        return Path("data") / "cpdl" / voice_dir / "renders" / f"{target}_mp3" / f"{output_path.stem}.mp3"
    if "kdf" in parts:
        book = parts[parts.index("kdf") + 1]
        return Path("data") / "kdf" / book / "renders" / "string_quartet_mp3" / f"{output_path.stem}.mp3"
    raise ValueError(f"Cannot derive MP3 path for {output_path}")


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "batch",
        "work_id",
        "title",
        "source_path",
        "output_path",
        "mp3_path",
        "original_snapshot_path",
        "updated_snapshot_path",
        "current_semitones",
        "updated_semitones",
        "current_key_burden",
        "updated_key_burden",
        "key_burden_delta",
        "current_tessitura_score",
        "updated_tessitura_score",
        "tessitura_delta",
        "status",
        "error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> list[dict[str, str]]:
    selected = _selected_rows(args.audit, args.max_tessitura_delta)
    manifest_rows: list[dict[str, str]] = []
    applied_rows: list[dict[str, str]] = []

    for index, row in enumerate(selected, start=1):
        print(f"[{index:03d}/{len(selected):03d}] {row['batch']}: {row['title']} {row['current_semitones']} -> {row['best_semitones']}", flush=True)
        output_path = Path(row["output_path"])
        original_snapshot = _snapshot_path(row, args.output_root, "original")
        updated_snapshot = _snapshot_path(row, args.output_root, "updated")
        base = {
            "batch": row["batch"],
            "work_id": row["work_id"],
            "title": row["title"],
            "source_path": row["source_path"],
            "output_path": row["output_path"],
            "mp3_path": str(_mp3_path_for_output(output_path)),
            "original_snapshot_path": str(original_snapshot),
            "updated_snapshot_path": str(updated_snapshot),
            "current_semitones": row["current_semitones"],
            "updated_semitones": row["best_semitones"],
            "current_key_burden": row["current_key_burden"],
            "updated_key_burden": row["best_key_burden"],
            "key_burden_delta": row["key_burden_delta"],
            "current_tessitura_score": row["current_tessitura_score"],
            "updated_tessitura_score": row["best_tessitura_score"],
            "tessitura_delta": row["tessitura_delta"],
        }
        try:
            if not args.dry_run:
                _copy_file(output_path, original_snapshot)
                _reduce(row)
                _copy_file(output_path, updated_snapshot)
                applied_rows.append(row)
            manifest_rows.append({**base, "status": "ok", "error": ""})
        except Exception as exc:
            manifest_rows.append({**base, "status": "error", "error": str(exc)})

    if not args.dry_run:
        update_reports(applied_rows)
    _write_manifest(args.manifest, manifest_rows)
    return manifest_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_OUTPUT_ROOT / "manifest.tsv")
    parser.add_argument("--max-tessitura-delta", type=float, default=0.02)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = run(args)
    ok = sum(row["status"] == "ok" for row in rows)
    errors = len(rows) - ok
    print(f"Wrote {args.manifest} ({ok} ok, {errors} errors).")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
