#!/usr/bin/env python3
"""Audit reduction MusicXML files for beat/readability notation risks."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from music21 import converter, note, stream


DEFAULT_INPUTS = (
    Path("data/take6/reductions/string_quartet_double_stops/hark_herald.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/come_unto_me.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/he_never_sleeps.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/a_quiet_place.musicxml"),
)

CONCERT_INPUTS = (
    Path("data/beach boys/reductions/string_quartet/our_prayer_low_cello.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/109_luci_serene_e_chiare.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/092_dolcissima_mia_vita.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/100_gi_piansi_nel_dolore.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/147_s_io_non_miro_non_moro.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/come_unto_me.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/121_moro_lasso_al_mio_duolo.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/161_sparge_la_morte.musicxml"),
    Path("data/cpdl/5-voices/reductions/string_quartet/074_belt_poi_che_t_assenti.musicxml"),
    Path("data/cpdl/6-voices/reductions/string_quartet/051_tristis_est_anima_mea.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/hark_herald.musicxml"),
    Path("data/take6/reductions/string_quartet_double_stops/a_quiet_place.musicxml"),
)


@dataclass(frozen=True)
class Issue:
    file: str
    part: str
    measure: str
    kind: str
    detail: str


def _ql(value) -> Fraction:
    try:
        return Fraction(value).limit_denominator(4096)
    except TypeError:
        return Fraction(float(value)).limit_denominator(4096)


def _part_name(part: stream.Part, index: int) -> str:
    return (part.partName or part.partAbbreviation or f"Part {index + 1}").strip()


def _measure_total(measure: stream.Measure) -> Fraction:
    duration = measure.barDuration or measure.duration
    return _ql(duration.quarterLength)


def _beat_unit(measure: stream.Measure) -> Fraction:
    time_sig = measure.timeSignature
    if time_sig is None:
        return Fraction(1, 1)
    denominator = int(time_sig.denominator)
    numerator = int(time_sig.numerator)
    if denominator == 2:
        return Fraction(2, 1)
    if denominator == 4 and numerator % 3 == 0 and numerator > 3:
        return Fraction(3, 2)
    return Fraction(4, denominator)


def _is_viola_part(part: stream.Part) -> bool:
    name = _part_name(part, 0).lower()
    return "viola" in name or "vla" in name


def _pitch_midis(element: note.GeneralNote) -> list[int]:
    if element.isNote:
        return [int(round(element.pitch.midi))]
    if element.isChord:
        return [int(round(pitch.midi)) for pitch in element.pitches]
    return []


def _pitch_label(element: note.GeneralNote) -> str:
    if element.isNote:
        return element.pitch.nameWithOctave
    if element.isChord:
        return ".".join(pitch.nameWithOctave for pitch in element.pitches)
    return element.classes[0]


def _tie_label(element: note.GeneralNote) -> str:
    if element.isNote:
        return getattr(getattr(element, "tie", None), "type", "") or ""
    if element.isChord:
        return ",".join(
            sorted(
                {
                    getattr(getattr(chord_note, "tie", None), "type", "") or ""
                    for chord_note in element.notes
                    if getattr(chord_note, "tie", None)
                }
            )
        )
    return ""


def _audit_measure(
    path: Path,
    part: stream.Part,
    part_index: int,
    measure: stream.Measure,
    current_clef_sign: str | None,
) -> list[Issue]:
    issues: list[Issue] = []
    part_name = _part_name(part, part_index)
    measure_number = str(measure.measureNumber)
    total = _measure_total(measure)
    beat = _beat_unit(measure)
    notes_and_rests = sorted(list(measure.notesAndRests), key=lambda element: _ql(element.offset))
    notes = [element for element in notes_and_rests if not element.isRest]

    if notes_and_rests:
        last = notes_and_rests[-1]
        if last.isRest and _ql(last.offset) + _ql(last.quarterLength) == total and _ql(last.quarterLength) <= Fraction(1, 4):
            issues.append(
                Issue(
                    str(path),
                    part_name,
                    measure_number,
                    "final_tiny_rest",
                    f"final rest duration {_ql(last.quarterLength)}",
                )
            )
    if beat > 0:
        for element in notes:
            offset = _ql(element.offset)
            duration = _ql(element.quarterLength)
            if duration <= 0 or offset % beat == 0:
                continue
            if duration >= 2 and offset.denominator == 1:
                continue
            end = offset + duration
            boundary = beat
            while boundary < total:
                if offset < boundary < end:
                    tie_text = _tie_label(element)
                    detail = f"{_pitch_label(element)} {offset}+{duration} crosses beat boundary {boundary}"
                    if tie_text:
                        detail += f"; tie={tie_text}"
                    issues.append(
                        Issue(
                            str(path),
                            part_name,
                            measure_number,
                            "note_crosses_beat",
                            detail,
                        )
                    )
                    break
                boundary += beat

    attack_count = len(notes)
    short_attacks = sum(1 for element in notes if _ql(element.quarterLength) <= Fraction(1, 4))
    if attack_count >= 10 or short_attacks >= 6:
        issues.append(
            Issue(
                str(path),
                part_name,
                measure_number,
                "dense_bar",
                f"{attack_count} attacks; {short_attacks} at sixteenth-note duration or shorter",
            )
        )

    if _is_viola_part(part):
        high_duration = Fraction(0, 1)
        for element in notes:
            if any(midi >= 69 for midi in _pitch_midis(element)):
                high_duration += _ql(element.quarterLength)
        if high_duration >= 1:
            has_treble = current_clef_sign == "G" or any(
                clef_obj.sign == "G" for clef_obj in measure.getElementsByClass("Clef")
            )
            if not has_treble:
                issues.append(
                    Issue(
                        str(path),
                        part_name,
                        measure_number,
                        "viola_treble_clef_candidate",
                        f"{high_duration} ql at A4 or above",
                    )
                )
    return issues


def audit_files(paths: list[Path]) -> list[Issue]:
    issues: list[Issue] = []
    for path in paths:
        score = converter.parse(path)
        for part_index, part in enumerate(score.parts):
            current_clef_sign: str | None = None
            for measure in part.getElementsByClass(stream.Measure):
                clefs = list(measure.getElementsByClass("Clef"))
                if clefs:
                    current_clef_sign = clefs[-1].sign
                issues.extend(_audit_measure(path, part, part_index, measure, current_clef_sign))
    return issues


def write_tsv(path: Path, issues: list[Issue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "part", "measure", "kind", "detail"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.__dict__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--concert", action="store_true", help="Audit the current concert program inputs.")
    parser.add_argument("--output", type=Path, default=Path("outputs/reports/beat_readability_audit.tsv"))
    args = parser.parse_args()

    paths = args.paths or (list(CONCERT_INPUTS) if args.concert else list(DEFAULT_INPUTS))
    issues = audit_files(paths)
    write_tsv(args.output, issues)
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1
    print(f"Audited {len(paths)} files; {len(issues)} issues.")
    for kind, count in sorted(counts.items()):
        print(f"{kind}: {count}")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
