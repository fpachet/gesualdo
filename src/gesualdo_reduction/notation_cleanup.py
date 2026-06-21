"""Shared notation cleanup helpers for review and PDF export."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from music21 import bar, clef, converter, dynamics, key, note, stream


@dataclass
class NotationCleanupReport:
    """Counts collected while preparing notation for review export."""

    suppressed_naturals: int = 0
    removed_dynamics: int = 0
    removed_hairpins: int = 0
    final_barlines_added: int = 0
    cello_clef_changes_added: int = 0
    pdf_midi_fallbacks: int = 0

    def as_row(self) -> dict[str, str]:
        return {field: str(value) for field, value in asdict(self).items()}


def _safe_remove(element) -> bool:
    site = getattr(element, "activeSite", None)
    if site is None:
        return False
    try:
        site.remove(element)
    except Exception:
        return False
    return True


def _pitch_objects(element: note.GeneralNote):
    if element.isNote:
        return [element.pitch]
    if element.isChord:
        return list(element.pitches)
    return []


def _key_alterations(key_signature: key.KeySignature | None) -> dict[str, int]:
    alterations = {step: 0 for step in "ABCDEFG"}
    if key_signature is None:
        return alterations
    for pitch in key_signature.alteredPitches:
        alterations[pitch.step] = int(pitch.accidental.alter)
    return alterations


def _measure_key_signature(measure: stream.Measure, current: key.KeySignature | None) -> key.KeySignature | None:
    signatures = list(measure.getElementsByClass(key.KeySignature))
    return signatures[-1] if signatures else current


def suppress_unneeded_naturals(score: stream.Score) -> int:
    """Hide explicit naturals that restate the key and local measure state."""

    count = 0
    for part in score.parts:
        current_key: key.KeySignature | None = None
        for measure in part.getElementsByClass(stream.Measure):
            current_key = _measure_key_signature(measure, current_key)
            key_state = _key_alterations(current_key)
            measure_state = dict(key_state)
            timed_elements = sorted(
                measure.notes,
                key=lambda element: (float(element.offset), getattr(element, "sortTuple", lambda: ())()),
            )
            for element in timed_elements:
                for pitch in _pitch_objects(element):
                    accidental = pitch.accidental
                    alter = 0 if accidental is None else int(accidental.alter)
                    previous_alter = measure_state.get(pitch.step, key_state.get(pitch.step, 0))
                    key_alter = key_state.get(pitch.step, 0)
                    if (
                        accidental is not None
                        and accidental.name == "natural"
                        and accidental.displayStatus is not False
                        and key_alter == 0
                        and previous_alter == 0
                    ):
                        accidental.displayStatus = False
                        count += 1
                    measure_state[pitch.step] = alter
    return count


def remove_editorial_dynamics(score: stream.Score) -> tuple[int, int]:
    """Remove visible dynamic marks and hairpins from a score."""

    dynamic_count = 0
    for element in list(score.recurse().getElementsByClass(dynamics.Dynamic)):
        if _safe_remove(element):
            dynamic_count += 1

    hairpin_count = 0
    for element in list(score.recurse().getElementsByClass(dynamics.DynamicWedge)):
        if _safe_remove(element):
            hairpin_count += 1
    return dynamic_count, hairpin_count


def add_final_barlines(score: stream.Score) -> int:
    """Ensure every part has a final right barline."""

    count = 0
    for part in score.parts:
        measures = list(part.getElementsByClass(stream.Measure))
        if not measures:
            continue
        last = measures[-1]
        if last.rightBarline is None or last.rightBarline.type != "final":
            last.rightBarline = bar.Barline("final")
            count += 1
    return count


def _part_name(part: stream.Part) -> str:
    return " ".join(
        value
        for value in (getattr(part, "partName", "") or "", getattr(part, "partAbbreviation", "") or "")
        if value
    ).lower()


def _is_cello_part(part: stream.Part) -> bool:
    name = _part_name(part)
    return "violoncello" in name or "cello" in name or "vc" in name


def _measure_pitch_values(measure: stream.Measure) -> list[tuple[int, float]]:
    values: list[tuple[int, float]] = []
    for element in measure.notes:
        pitches = _pitch_objects(element)
        if not pitches:
            continue
        duration = float(element.quarterLength)
        for pitch in pitches:
            values.append((int(round(pitch.midi)), duration))
    return values


def _duration_at_or_above(values: Iterable[tuple[int, float]], threshold: int) -> float:
    return sum(duration for midi, duration in values if midi >= threshold)


def _clef_id(clef_obj: clef.Clef) -> tuple[str, int | None]:
    return (clef_obj.sign, clef_obj.line)


def _target_clef_for_cello_measure(
    values: list[tuple[int, float]],
    current_clef: clef.Clef,
    *,
    tenor_midi: int,
    treble_midi: int,
    bass_return_midi: int,
    min_high_duration: float,
) -> clef.Clef:
    if not values:
        return current_clef
    max_midi = max(midi for midi, _ in values)
    if max_midi >= treble_midi and _duration_at_or_above(values, treble_midi) >= min_high_duration:
        return clef.TrebleClef()
    if max_midi >= tenor_midi and _duration_at_or_above(values, tenor_midi) >= min_high_duration:
        return clef.TenorClef()
    if max_midi <= bass_return_midi:
        return clef.BassClef()
    return current_clef


def add_cello_high_clefs(
    score: stream.Score,
    *,
    tenor_midi: int = 60,
    treble_midi: int = 67,
    bass_return_midi: int = 55,
    min_high_duration: float = 2.0,
) -> int:
    """Insert cello clef changes for sustained high passages."""

    count = 0
    for part in score.parts:
        if not _is_cello_part(part):
            continue
        current_clef: clef.Clef = clef.BassClef()
        for measure in part.getElementsByClass(stream.Measure):
            measure_clefs = list(measure.getElementsByClass(clef.Clef))
            if measure_clefs:
                current_clef = measure_clefs[-1]
            target_clef = _target_clef_for_cello_measure(
                _measure_pitch_values(measure),
                current_clef,
                tenor_midi=tenor_midi,
                treble_midi=treble_midi,
                bass_return_midi=bass_return_midi,
                min_high_duration=min_high_duration,
            )
            if _clef_id(target_clef) == _clef_id(current_clef):
                continue
            for existing in list(measure.getElementsByClass(clef.Clef)):
                if float(existing.offset) == 0:
                    _safe_remove(existing)
            measure.insert(0, target_clef)
            current_clef = target_clef
            count += 1
    return count


def cleanup_score(
    score: stream.Score,
    *,
    clean_dynamics: bool = False,
    suppress_naturals: bool = True,
    final_barlines: bool = True,
    cello_clefs: bool = True,
) -> NotationCleanupReport:
    """Apply conservative notation cleanup for review exports."""

    report = NotationCleanupReport()
    if suppress_naturals:
        report.suppressed_naturals = suppress_unneeded_naturals(score)
    if clean_dynamics:
        report.removed_dynamics, report.removed_hairpins = remove_editorial_dynamics(score)
    if final_barlines:
        report.final_barlines_added = add_final_barlines(score)
    if cello_clefs:
        report.cello_clef_changes_added = add_cello_high_clefs(score)
    return report


def cleanup_musicxml(
    input_path: str | Path,
    output_path: str | Path,
    *,
    clean_dynamics: bool = False,
    suppress_naturals: bool = True,
    final_barlines: bool = True,
    cello_clefs: bool = True,
) -> NotationCleanupReport:
    """Read MusicXML, clean it, and write a MusicXML file."""

    score = converter.parse(input_path)
    report = cleanup_score(
        score,
        clean_dynamics=clean_dynamics,
        suppress_naturals=suppress_naturals,
        final_barlines=final_barlines,
        cello_clefs=cello_clefs,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(output_path))
    return report
