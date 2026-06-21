#!/usr/bin/env python3
"""Audit reduced quartet parts for awkward jumps, sparse fragments, and notation flags."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from music21 import chord, converter, note, spanner, stream, tie


DEFAULT_REPORTS = (
    Path("data/kdf/reductions/string_quartet_report.tsv"),
    Path("data/cpdl/5-voices/reductions/string_quartet/report.tsv"),
    Path("data/cpdl/5-voices/reductions/string_quartet_plus_viole/report.tsv"),
    Path("data/cpdl/6-voices/reductions/string_quartet/report.tsv"),
    Path("data/take6/reductions/string_quartet_double_stops/report.tsv"),
)


@dataclass(frozen=True)
class WorkRow:
    batch: str
    work_id: str
    title: str
    output_path: Path | None
    status: str
    error: str


@dataclass(frozen=True)
class PitchedEvent:
    part_index: int
    part_name: str
    measure_number: str
    offset: float
    end: float
    duration: float
    pitches: tuple[int, ...]
    tie_types: tuple[str, ...]
    accidental_count: int

    @property
    def attack_count(self) -> int:
        return 1


@dataclass(frozen=True)
class Island:
    events: tuple[PitchedEvent, ...]
    silence_before: float
    silence_after: float

    @property
    def start(self) -> float:
        return self.events[0].offset

    @property
    def end(self) -> float:
        return self.events[-1].end

    @property
    def measure_number(self) -> str:
        return self.events[0].measure_number

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def note_duration(self) -> float:
        return sum(event.duration for event in self.events)

    @property
    def attack_count(self) -> int:
        return sum(event.attack_count for event in self.events)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


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
    if "take6" in text:
        return "take6_string_quartet_double_stops"
    return report_path.parent.name


def _rows_from_report(report_path: Path) -> list[WorkRow]:
    batch = _batch_name(report_path)
    rows: list[WorkRow] = []
    for row in _read_tsv(report_path):
        if batch.startswith("kdf"):
            work_id = f"{row.get('book', '')} {row.get('title', '')}".strip()
            title = row.get("title", "")
            output_path = Path(row["output"]) if row.get("output") else None
            status = row.get("status", "")
            error = row.get("error", "")
        elif batch.startswith("take6"):
            output_path = Path(row["output_path"]) if row.get("output_path") else None
            work_id = output_path.stem if output_path is not None else row.get("source_path", "")
            title = work_id.replace("_", " ").title()
            status = row.get("status", "")
            error = row.get("error", "")
        else:
            work_id = row.get("work_index", "")
            title = row.get("work_title", "")
            output_path = Path(row["output_path"]) if row.get("output_path") else None
            status = row.get("status", "")
            error = row.get("error", "")
        rows.append(WorkRow(batch=batch, work_id=work_id, title=title, output_path=output_path, status=status, error=error))
    return rows


def _ql(value) -> float:
    try:
        return float(value)
    except TypeError:
        return float(value.quarterLength)


def _absolute_offset(element, part: stream.Part) -> float:
    try:
        return float(element.getOffsetInHierarchy(part))
    except Exception:
        return float(element.offset)


def _measure_number(element) -> str:
    measure = element.getContextByClass(stream.Measure)
    value = getattr(measure, "number", None)
    return "" if value is None else str(value)


def _part_name(part: stream.Part, index: int) -> str:
    return (part.partName or part.partAbbreviation or f"Part {index + 1}").strip()


def _event_pitches(element: note.GeneralNote) -> tuple[int, ...]:
    if isinstance(element, chord.Chord):
        return tuple(sorted(int(round(pitch.midi)) for pitch in element.pitches))
    if isinstance(element, note.Note):
        return (int(round(element.pitch.midi)),)
    return ()


def _event_ties(element: note.GeneralNote) -> tuple[str, ...]:
    if isinstance(element, chord.Chord):
        return tuple(getattr(chord_note.tie, "type", "") or "" for chord_note in element.notes)
    return (getattr(getattr(element, "tie", None), "type", "") or "",)


def _event_accidental_count(element: note.GeneralNote) -> int:
    if isinstance(element, chord.Chord):
        pitches = list(element.pitches)
    elif isinstance(element, note.Note):
        pitches = [element.pitch]
    else:
        pitches = []
    return sum(1 for pitch in pitches if pitch.accidental is not None and pitch.accidental.displayStatus is not False)


def _measure_duration(score: stream.Score) -> float:
    durations: list[float] = []
    for measure in score.recurse().getElementsByClass(stream.Measure):
        duration = measure.barDuration or measure.duration
        value = _ql(duration)
        if value > 0:
            durations.append(value)
    if not durations:
        return 4.0
    return statistics.median(durations)


def _part_events(part: stream.Part, part_index: int) -> list[PitchedEvent]:
    events: list[PitchedEvent] = []
    name = _part_name(part, part_index)
    for element in part.recurse().notes:
        pitches = _event_pitches(element)
        if not pitches:
            continue
        offset = _absolute_offset(element, part)
        duration = _ql(element.duration)
        if duration <= 0:
            continue
        events.append(
            PitchedEvent(
                part_index=part_index,
                part_name=name,
                measure_number=_measure_number(element),
                offset=offset,
                end=offset + duration,
                duration=duration,
                pitches=pitches,
                tie_types=_event_ties(element),
                accidental_count=_event_accidental_count(element),
            )
        )
    return sorted(events, key=lambda event: (event.offset, event.end, event.pitches))


def _min_pitch_distance(left: Sequence[int], right: Sequence[int]) -> int:
    return min(abs(a - b) for a in left for b in right)


def _closest_pitch_label(left: Sequence[int], right: Sequence[int]) -> tuple[int, int, int]:
    best = min((abs(a - b), a, b) for a in left for b in right)
    return best[1], best[2], best[0]


def _is_tied_continuation(event: PitchedEvent) -> bool:
    return any(tie_type in {"stop", "continue"} for tie_type in event.tie_types)


def _audit_jumps(
    work: WorkRow,
    events: Sequence[PitchedEvent],
    *,
    threshold: int,
    short_duration: float,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for previous, current in zip(events, events[1:], strict=False):
        if _is_tied_continuation(current):
            continue
        interval = _min_pitch_distance(previous.pitches, current.pitches)
        if interval < threshold:
            continue
        prev_pitch, current_pitch, interval = _closest_pitch_label(previous.pitches, current.pitches)
        short_side = previous.duration <= short_duration or current.duration <= short_duration
        severity = "high" if interval >= 19 and short_side else "medium" if interval >= 12 else "low"
        rows.append(
            {
                "kind": "register_jump",
                "severity": severity,
                "batch": work.batch,
                "work_id": work.work_id,
                "title": work.title,
                "output_path": str(work.output_path or ""),
                "part": current.part_name,
                "measure": current.measure_number,
                "offset": f"{current.offset:.6g}",
                "detail": f"{interval} semitones from MIDI {prev_pitch} to {current_pitch}",
                "context": f"prev_dur={previous.duration:.6g}; current_dur={current.duration:.6g}",
            }
        )
    return rows


def _event_islands(events: Sequence[PitchedEvent], *, max_internal_gap: float, score_end: float) -> list[Island]:
    if not events:
        return []

    islands: list[list[PitchedEvent]] = [[events[0]]]
    for event in events[1:]:
        previous = islands[-1][-1]
        if event.offset - previous.end <= max_internal_gap:
            islands[-1].append(event)
        else:
            islands.append([event])

    result: list[Island] = []
    for index, island_events in enumerate(islands):
        previous_end = 0.0 if index == 0 else islands[index - 1][-1].end
        next_start = score_end if index == len(islands) - 1 else islands[index + 1][0].offset
        result.append(
            Island(
                events=tuple(island_events),
                silence_before=max(0.0, island_events[0].offset - previous_end),
                silence_after=max(0.0, next_start - island_events[-1].end),
            )
        )
    return result


def _audit_fragments(
    work: WorkRow,
    events: Sequence[PitchedEvent],
    *,
    score_end: float,
    measure_duration: float,
    long_rest_bars: float,
    max_internal_gap: float,
    max_fragment_duration: float,
    max_fragment_attacks: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    long_rest = long_rest_bars * measure_duration
    for island in _event_islands(events, max_internal_gap=max_internal_gap, score_end=score_end):
        short_island = island.note_duration <= max_fragment_duration or island.attack_count <= max_fragment_attacks
        isolated = island.silence_before >= long_rest or island.silence_after >= long_rest
        if not short_island or not isolated:
            continue
        severe = island.silence_before >= long_rest and island.silence_after >= long_rest
        rows.append(
            {
                "kind": "sparse_fragment",
                "severity": "high" if severe else "medium",
                "batch": work.batch,
                "work_id": work.work_id,
                "title": work.title,
                "output_path": str(work.output_path or ""),
                "part": island.events[0].part_name,
                "measure": island.measure_number,
                "offset": f"{island.start:.6g}",
                "detail": f"{island.attack_count} attacks, {island.note_duration:.6g} ql after/before long silence",
                "context": f"silence_before={island.silence_before:.6g}; silence_after={island.silence_after:.6g}",
            }
        )
    return rows


def _audit_sparse_windows(
    work: WorkRow,
    events: Sequence[PitchedEvent],
    *,
    score_end: float,
    measure_duration: float,
    window_bars: float,
    max_window_duration: float,
    max_window_attacks: int,
) -> list[dict[str, str]]:
    if not events or score_end <= 0:
        return []

    rows: list[dict[str, str]] = []
    window_length = max(measure_duration, window_bars * measure_duration)
    part_start = math.floor(events[0].offset / window_length) * window_length
    part_end = math.ceil(score_end / window_length) * window_length
    start = part_start
    while start < part_end:
        end = start + window_length
        window_events = [event for event in events if event.offset < end and event.end > start]
        if window_events:
            note_duration = sum(
                max(0.0, min(event.end, end) - max(event.offset, start))
                for event in window_events
            )
            attack_count = sum(1 for event in window_events if start <= event.offset < end)
            if 0 < attack_count <= max_window_attacks and note_duration <= max_window_duration:
                severe = note_duration <= max_window_duration / 2 and attack_count <= max(1, max_window_attacks - 1)
                rows.append(
                    {
                        "kind": "sparse_window",
                        "severity": "high" if severe else "medium",
                        "batch": work.batch,
                        "work_id": work.work_id,
                        "title": work.title,
                        "output_path": str(work.output_path or ""),
                        "part": window_events[0].part_name,
                        "measure": window_events[0].measure_number,
                        "offset": f"{start:.6g}",
                        "detail": f"{attack_count} attacks, {note_duration:.6g} ql in {window_bars:g}-bar window",
                        "context": f"window_start={start:.6g}; window_end={end:.6g}",
                    }
                )
        start = end
    return rows


def _tie_pitch_keys(event: PitchedEvent) -> set[int]:
    return set(event.pitches)


def _audit_ties(work: WorkRow, events: Sequence[PitchedEvent]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, event in enumerate(events):
        if not any(tie_type in {"start", "continue"} for tie_type in event.tie_types):
            continue
        next_event = events[index + 1] if index + 1 < len(events) else None
        next_continues = (
            next_event is not None
            and abs(next_event.offset - event.end) < 1e-6
            and bool(_tie_pitch_keys(event) & _tie_pitch_keys(next_event))
            and any(tie_type in {"stop", "continue"} for tie_type in next_event.tie_types)
        )
        if next_continues:
            continue
        rows.append(
            {
                "kind": "dangling_tie",
                "severity": "medium",
                "batch": work.batch,
                "work_id": work.work_id,
                "title": work.title,
                "output_path": str(work.output_path or ""),
                "part": event.part_name,
                "measure": event.measure_number,
                "offset": f"{event.offset:.6g}",
                "detail": f"tie {','.join(t for t in event.tie_types if t)} without matching continuation",
                "context": f"pitches={','.join(str(pitch) for pitch in event.pitches)}",
            }
        )
    return rows


def _audit_accidentals_on_ties(work: WorkRow, events: Sequence[PitchedEvent]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for event in events:
        if event.accidental_count <= 0 or not _is_tied_continuation(event):
            continue
        rows.append(
            {
                "kind": "accidental_on_tie_continuation",
                "severity": "low",
                "batch": work.batch,
                "work_id": work.work_id,
                "title": work.title,
                "output_path": str(work.output_path or ""),
                "part": event.part_name,
                "measure": event.measure_number,
                "offset": f"{event.offset:.6g}",
                "detail": f"{event.accidental_count} visible accidental(s) on tied continuation",
                "context": f"pitches={','.join(str(pitch) for pitch in event.pitches)}",
            }
        )
    return rows


def _audit_slurs(work: WorkRow, score: stream.Score) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for slur in score.recurse().getElementsByClass(spanner.Slur):
        elements = list(slur.getSpannedElements())
        if len(elements) >= 2:
            continue
        part = elements[0].getContextByClass(stream.Part) if elements else None
        measure = elements[0].getContextByClass(stream.Measure) if elements else None
        part_name = _part_name(part, 0) if isinstance(part, stream.Part) else ""
        measure_number = "" if measure is None else str(getattr(measure, "number", ""))
        rows.append(
            {
                "kind": "dangling_slur",
                "severity": "low",
                "batch": work.batch,
                "work_id": work.work_id,
                "title": work.title,
                "output_path": str(work.output_path or ""),
                "part": part_name,
                "measure": measure_number,
                "offset": "",
                "detail": f"slur spans {len(elements)} element(s)",
                "context": "",
            }
        )
    return rows


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _count_by(rows: Iterable[dict[str, str]], *fields: str) -> dict[tuple[str, ...], int]:
    counts: dict[tuple[str, ...], int] = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in fields)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _float_value(row: dict[str, str], field: str) -> float:
    try:
        return float(row.get(field, "0") or 0)
    except ValueError:
        return 0.0


def _top_rows(rows: list[dict[str, str]], *, limit: int) -> list[dict[str, str]]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        rows,
        key=lambda row: (
            severity_rank.get(row.get("severity", ""), 9),
            row.get("batch", ""),
            row.get("work_id", ""),
            row.get("part", ""),
            _float_value(row, "offset"),
        ),
    )[:limit]


def _markdown_table(rows: list[dict[str, str]], fields: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for label, _field in fields) + " |",
        "| " + " | ".join("---" for _label, _field in fields) + " |",
    ]
    for row in rows:
        values = []
        for _label, field in fields:
            values.append(row.get(field, "").replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_markdown_summary(path: Path, issue_rows: list[dict[str, str]], parse_rows: list[dict[str, str]], *, top_n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_kind = _count_by(issue_rows, "kind")
    by_batch_kind = _count_by(issue_rows, "batch", "kind")
    by_part_kind = _count_by(issue_rows, "part", "kind")
    high_or_medium = [row for row in issue_rows if row.get("severity") in {"high", "medium"}]

    lines = [
        "# Quartet Part-Coherence Audit",
        "",
        "This audit flags likely awkward reading spots in generated MusicXML reductions. It is intentionally observational: it does not rewrite the music.",
        "",
        "Checks:",
        "- `register_jump`: melodic movement of at least the configured interval between successive written events in the same part.",
        "- `sparse_fragment`: a short island of notes after or before a long silence.",
        "- `sparse_window`: very low participation density over a multi-bar window.",
        "- `dangling_tie`, `dangling_slur`, `accidental_on_tie_continuation`: conservative notation-structure flags.",
        "",
        "## Issue Counts",
        "",
        "| Kind | Count |",
        "| --- | ---: |",
    ]
    for (kind,), count in sorted(by_kind.items()):
        lines.append(f"| {kind} | {count} |")

    if parse_rows:
        lines.extend(["", "## Parse Issues", "", "| Batch | Work | Title | Status | Note |", "| --- | --- | --- | --- | --- |"])
        for row in parse_rows:
            lines.append(
                f"| {row.get('batch', '')} | {row.get('work_id', '')} | {row.get('title', '')} | {row.get('status', '')} | {row.get('note', '').replace('|', '\\|')} |"
            )

    lines.extend(["", "## Counts By Batch", "", "| Batch | Kind | Count |", "| --- | --- | ---: |"])
    for (batch, kind), count in sorted(by_batch_kind.items()):
        lines.append(f"| {batch} | {kind} | {count} |")

    lines.extend(["", "## Counts By Part", "", "| Part | Kind | Count |", "| --- | --- | ---: |"])
    for (part, kind), count in sorted(by_part_kind.items()):
        lines.append(f"| {part} | {kind} | {count} |")

    lines.extend(["", f"## Highest Priority Examples (Top {min(top_n, len(high_or_medium))})", ""])
    lines.extend(
        _markdown_table(
            _top_rows(high_or_medium, limit=top_n),
            [
                ("Severity", "severity"),
                ("Kind", "kind"),
                ("Batch", "batch"),
                ("Work", "work_id"),
                ("Title", "title"),
                ("Part", "part"),
                ("Measure", "measure"),
                ("Detail", "detail"),
            ],
        )
    )
    lines.extend(["", "Full issue rows are in `part_coherence_audit.tsv`.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_audit(args: argparse.Namespace) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    issue_rows: list[dict[str, str]] = []
    parse_rows: list[dict[str, str]] = []
    works = [work for report in args.reports for work in _rows_from_report(report)]
    if args.limit:
        works = works[: args.limit]

    for index, work in enumerate(works, start=1):
        if args.verbose:
            print(f"[{index:03d}/{len(works):03d}] {work.batch}: {work.title}", flush=True)

        if work.status != "ok":
            parse_rows.append(
                {
                    "batch": work.batch,
                    "work_id": work.work_id,
                    "title": work.title,
                    "output_path": str(work.output_path or ""),
                    "status": "source_status_error",
                    "note": work.error,
                }
            )
            continue
        if work.output_path is None:
            parse_rows.append(
                {
                    "batch": work.batch,
                    "work_id": work.work_id,
                    "title": work.title,
                    "output_path": "",
                    "status": "missing_output",
                    "note": "",
                }
            )
            continue

        try:
            score = converter.parse(work.output_path)
        except Exception as exc:  # noqa: BLE001 - batch audit should report every parse miss.
            parse_rows.append(
                {
                    "batch": work.batch,
                    "work_id": work.work_id,
                    "title": work.title,
                    "output_path": str(work.output_path),
                    "status": "parse_error",
                    "note": str(exc),
                }
            )
            continue

        measure_duration = _measure_duration(score)
        score_end = float(score.highestTime or 0.0)
        issue_rows.extend(_audit_slurs(work, score))
        for part_index, part in enumerate(score.parts):
            events = _part_events(part, part_index)
            issue_rows.extend(
                _audit_jumps(
                    work,
                    events,
                    threshold=args.jump_threshold,
                    short_duration=args.short_duration,
                )
            )
            issue_rows.extend(
                _audit_fragments(
                    work,
                    events,
                    score_end=score_end,
                    measure_duration=measure_duration,
                    long_rest_bars=args.long_rest_bars,
                    max_internal_gap=args.max_internal_gap,
                    max_fragment_duration=args.max_fragment_duration,
                    max_fragment_attacks=args.max_fragment_attacks,
                )
            )
            issue_rows.extend(
                _audit_sparse_windows(
                    work,
                    events,
                    score_end=score_end,
                    measure_duration=measure_duration,
                    window_bars=args.sparse_window_bars,
                    max_window_duration=args.max_sparse_window_duration,
                    max_window_attacks=args.max_sparse_window_attacks,
                )
            )
            issue_rows.extend(_audit_ties(work, events))
            issue_rows.extend(_audit_accidentals_on_ties(work, events))

    return issue_rows, parse_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", nargs="+", type=Path, default=list(DEFAULT_REPORTS))
    parser.add_argument("--output", type=Path, default=Path("outputs/reports/part_coherence_audit.tsv"))
    parser.add_argument("--parse-output", type=Path, default=Path("outputs/reports/part_coherence_parse_issues.tsv"))
    parser.add_argument("--markdown-output", type=Path, default=Path("outputs/reports/part_coherence_audit.md"))
    parser.add_argument("--jump-threshold", type=int, default=12)
    parser.add_argument("--short-duration", type=float, default=1.0)
    parser.add_argument("--long-rest-bars", type=float, default=2.0)
    parser.add_argument("--max-internal-gap", type=float, default=1.0)
    parser.add_argument("--max-fragment-duration", type=float, default=1.5)
    parser.add_argument("--max-fragment-attacks", type=int, default=3)
    parser.add_argument("--sparse-window-bars", type=float, default=4.0)
    parser.add_argument("--max-sparse-window-duration", type=float, default=1.5)
    parser.add_argument("--max-sparse-window-attacks", type=int, default=3)
    parser.add_argument("--top-n", type=int, default=60)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    issue_rows, parse_rows = run_audit(args)
    fields = [
        "kind",
        "severity",
        "batch",
        "work_id",
        "title",
        "output_path",
        "part",
        "measure",
        "offset",
        "detail",
        "context",
    ]
    parse_fields = ["batch", "work_id", "title", "output_path", "status", "note"]
    _write_rows(args.output, fields, issue_rows)
    _write_rows(args.parse_output, parse_fields, parse_rows)
    write_markdown_summary(args.markdown_output, issue_rows, parse_rows, top_n=args.top_n)
    print(f"Wrote {len(issue_rows)} issue rows to {args.output}")
    if parse_rows:
        print(f"Wrote {len(parse_rows)} parse/status rows to {args.parse_output}")
    print(f"Wrote summary to {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
