#!/usr/bin/env python3
"""Regenerate cleaner-key transposition candidates into a comparison folder."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from gesualdo_reduction import reduce_to_quartet, reduce_to_quartet_plus_viole
from gesualdo_reduction.reduction import reduce_six_to_quartet


DEFAULT_AUDIT = Path("outputs/reports/transposition_key_signature_audit.tsv")
DEFAULT_OUTPUT_ROOT = Path("outputs/transposition_comparison/tier1_key_signature")


def _read_audit(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _selected_rows(path: Path, max_tessitura_delta: float) -> list[dict[str, str]]:
    rows = _read_audit(path)
    selected = [
        row
        for row in rows
        if row.get("status") == "attention"
        and row.get("best_semitones")
        and row.get("source_path")
        and row.get("output_path")
        and float(row.get("tessitura_delta") or 0.0) <= max_tessitura_delta
    ]
    return sorted(selected, key=lambda row: (row["batch"], row["work_id"], row["title"]))


def _comparison_stem(row: dict[str, str]) -> str:
    old = int(row["current_semitones"])
    new = int(row["best_semitones"])
    return f"{Path(row['output_path']).stem}__t{old:+d}_to_{new:+d}"


def _copy_original(row: dict[str, str], output_root: Path, *, force: bool) -> Path:
    source = Path(row["output_path"])
    destination = output_root / row["batch"] / "original" / f"{_comparison_stem(row)}.musicxml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return destination
    shutil.copy2(source, destination)
    return destination


def _alternative_path(row: dict[str, str], output_root: Path) -> Path:
    path = output_root / row["batch"] / "alternative" / f"{_comparison_stem(row)}.musicxml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _reduce_alternative(row: dict[str, str], out_path: Path, *, force: bool) -> None:
    if out_path.exists() and not force:
        return
    source_path = Path(row["source_path"])
    semitones = int(row["best_semitones"])
    batch = row["batch"]

    if batch in {"kdf_string_quartet", "cpdl_5_voice_string_quartet"}:
        reduce_to_quartet(
            source_path,
            semitones=semitones,
            out_path=out_path,
            preserve_active_voice_count=True,
            add_editorial_harmony=True,
            add_editorial_thirds=True,
        )
        return

    if batch == "cpdl_5_voice_quartet_plus_viole":
        reduce_to_quartet_plus_viole(source_path, semitones=semitones, out_path=out_path)
        return

    if batch == "cpdl_6_voice_string_quartet":
        reduce_six_to_quartet(source_path, semitones=semitones, out_path=out_path)
        return

    raise ValueError(f"Unsupported batch: {batch}")


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "batch",
        "work_id",
        "title",
        "source_path",
        "current_output_path",
        "original_snapshot_path",
        "alternative_output_path",
        "current_semitones",
        "alternative_semitones",
        "current_key_burden",
        "alternative_key_burden",
        "key_burden_delta",
        "current_tessitura_score",
        "alternative_tessitura_score",
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

    for index, row in enumerate(selected, start=1):
        print(f"[{index:03d}/{len(selected):03d}] {row['batch']}: {row['title']} {row['current_semitones']} -> {row['best_semitones']}", flush=True)
        base = {
            "batch": row["batch"],
            "work_id": row["work_id"],
            "title": row["title"],
            "source_path": row["source_path"],
            "current_output_path": row["output_path"],
            "current_semitones": row["current_semitones"],
            "alternative_semitones": row["best_semitones"],
            "current_key_burden": row["current_key_burden"],
            "alternative_key_burden": row["best_key_burden"],
            "key_burden_delta": row["key_burden_delta"],
            "current_tessitura_score": row["current_tessitura_score"],
            "alternative_tessitura_score": row["best_tessitura_score"],
            "tessitura_delta": row["tessitura_delta"],
        }
        try:
            original_snapshot = _copy_original(row, args.output_root, force=args.force)
            alternative = _alternative_path(row, args.output_root)
            _reduce_alternative(row, alternative, force=args.force)
            manifest_rows.append(
                {
                    **base,
                    "original_snapshot_path": str(original_snapshot),
                    "alternative_output_path": str(alternative),
                    "status": "ok",
                    "error": "",
                }
            )
        except Exception as exc:
            manifest_rows.append(
                {
                    **base,
                    "original_snapshot_path": "",
                    "alternative_output_path": "",
                    "status": "error",
                    "error": str(exc),
                }
            )

    _write_manifest(args.manifest, manifest_rows)
    return manifest_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_OUTPUT_ROOT / "manifest.tsv")
    parser.add_argument(
        "--max-tessitura-delta",
        type=float,
        default=0.01,
        help="First-tier cutoff from the audit.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing comparison files.")
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
