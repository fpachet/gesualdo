"""Render CPDL reduction MusicXML files to MP3 with MuseScore 4."""

from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
from pathlib import Path

from music21 import converter


DEFAULT_MUSESCORE = Path("/Applications/MuseScore 4 2.app/Contents/MacOS/mscore")
MUSESCORE_CANDIDATES = (
    DEFAULT_MUSESCORE,
    Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore"),
)


def default_musescore_path() -> Path:
    for candidate in MUSESCORE_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_MUSESCORE
DEFAULT_JOBS = (
    ("5-voices", "string_quartet"),
    ("5-voices", "string_quartet_plus_viole"),
    ("6-voices", "string_quartet"),
)


def report_rows(report_path: Path) -> list[dict[str, str]]:
    with report_path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle, delimiter="\t") if row.get("status") == "ok"]


def run_musescore(musescore: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(musescore), "-o", str(output_path), str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def render_musicxml(musescore: Path, input_path: Path, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    direct_result = run_musescore(musescore, input_path, output_path)
    if direct_result.returncode == 0:
        return "musicxml"

    if output_path.exists():
        output_path.unlink()

    with tempfile.TemporaryDirectory(prefix="cpdl_render_") as tmpdir:
        midi_path = Path(tmpdir) / f"{input_path.stem}.mid"
        converter.parse(input_path).write("midi", fp=str(midi_path))
        midi_result = run_musescore(musescore, midi_path, output_path)
        if midi_result.returncode == 0:
            return "midi_fallback"

    raise RuntimeError(
        f"MuseScore failed for {input_path} with return code {direct_result.returncode}."
    )


def render_job(root: Path, musescore: Path, voice_dir: str, target: str, force: bool) -> dict[str, int]:
    if voice_dir == "take6":
        report_path = root / "data" / "take6" / "reductions" / target / "report.tsv"
        output_dir = root / "data" / "take6" / "renders" / f"{target}_mp3"
    else:
        report_path = root / "data" / "cpdl" / voice_dir / "reductions" / target / "report.tsv"
        output_dir = root / "data" / "cpdl" / voice_dir / "renders" / f"{target}_mp3"
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    counts = {"musicxml": 0, "midi_fallback": 0, "failed": 0, "skipped": 0}
    for row in report_rows(report_path):
        input_path = root / row["output_path"]
        output_path = output_dir / f"{input_path.stem}.mp3"
        if output_path.exists() and not force:
            counts["skipped"] += 1
            continue
        print(f"{input_path} -> {output_path}", flush=True)
        try:
            mode = render_musicxml(musescore, input_path, output_path)
        except Exception as error:  # noqa: BLE001 - batch rendering should finish and report every miss.
            counts["failed"] += 1
            print(f"FAILED {input_path}: {error}", flush=True)
            continue
        counts[mode] += 1
    return counts


def parse_job(value: str) -> tuple[str, str]:
    try:
        voice_dir, target = value.split(":", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("jobs must be formatted as VOICE_DIR:TARGET") from error
    return voice_dir, target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--musescore", type=Path, default=default_musescore_path())
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--job",
        action="append",
        type=parse_job,
        help="Render one CPDL reduction set, for example 6-voices:string_quartet.",
    )
    args = parser.parse_args()

    if not args.musescore.exists():
        raise FileNotFoundError(args.musescore)

    jobs = args.job or DEFAULT_JOBS
    totals = {"musicxml": 0, "midi_fallback": 0, "failed": 0, "skipped": 0}
    for voice_dir, target in jobs:
        counts = render_job(args.root, args.musescore, voice_dir, target, args.force)
        for key, value in counts.items():
            totals[key] += value
        print(f"{voice_dir}/{target}: {counts}", flush=True)

    print(f"done: {totals}", flush=True)
    if totals["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
