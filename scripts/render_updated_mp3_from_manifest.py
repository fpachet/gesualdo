#!/usr/bin/env python3
"""Render MP3 files listed in an update manifest, with audio snapshots."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from render_cpdl_mp3 import DEFAULT_MUSESCORE, render_musicxml


DEFAULT_MANIFEST = Path("outputs/transposition_comparison/obvious_key_signature/manifest.tsv")


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle, delimiter="\t") if row.get("status") == "ok"]


def _snapshot_path(manifest: Path, row: dict[str, str], kind: str) -> Path:
    output_root = manifest.parent
    batch = row["batch"]
    mp3_path = Path(row["mp3_path"])
    stem = Path(row["updated_snapshot_path"]).stem
    return output_root / batch / kind / f"{stem}.mp3"


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def run(args: argparse.Namespace) -> dict[str, int]:
    rows = _read_manifest(args.manifest)
    counts = {"rendered": 0, "failed": 0, "missing_original_mp3": 0, "snapshotted_original": 0, "snapshotted_updated": 0}
    for index, row in enumerate(rows, start=1):
        input_path = Path(row["output_path"])
        mp3_path = Path(row["mp3_path"])
        original_snapshot = _snapshot_path(args.manifest, row, "original_mp3")
        updated_snapshot = _snapshot_path(args.manifest, row, "updated_mp3")
        print(f"[{index:03d}/{len(rows):03d}] {input_path} -> {mp3_path}", flush=True)

        if _copy_if_exists(mp3_path, original_snapshot):
            counts["snapshotted_original"] += 1
        else:
            counts["missing_original_mp3"] += 1

        try:
            render_musicxml(args.musescore, input_path, mp3_path)
            counts["rendered"] += 1
        except Exception as exc:  # noqa: BLE001 - keep reporting the whole batch.
            counts["failed"] += 1
            print(f"FAILED {input_path}: {exc}", flush=True)
            continue

        if _copy_if_exists(mp3_path, updated_snapshot):
            counts["snapshotted_updated"] += 1

    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--musescore", type=Path, default=DEFAULT_MUSESCORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.musescore.exists():
        raise FileNotFoundError(args.musescore)
    counts = run(args)
    print(f"done: {counts}", flush=True)
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
