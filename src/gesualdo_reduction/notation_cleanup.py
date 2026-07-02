"""Shared notation cleanup helpers for review and PDF export."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from fractions import Fraction
from typing import Iterable

from music21 import bar, clef, converter, dynamics, key, note, stream, tie


@dataclass
class NotationCleanupReport:
    """Counts collected while preparing notation for review export."""

    suppressed_naturals: int = 0
    removed_dynamics: int = 0
    removed_hairpins: int = 0
    beat_readability_changes: int = 0
    final_barlines_added: int = 0
    cello_clef_changes_added: int = 0
    viola_clef_changes_added: int = 0
    suppressed_tie_continuation_accidentals: int = 0
    normalized_dangling_ties: int = 0
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


def _ql_fraction(value) -> Fraction:
    try:
        return Fraction(value).limit_denominator(4096)
    except TypeError:
        return Fraction(float(value)).limit_denominator(4096)


def _set_ql(element: note.GeneralNote, value: Fraction) -> None:
    element.quarterLength = float(value) if value.denominator not in {1, 2, 3, 4, 6, 8} else value


def _same_pitch_content(left: note.GeneralNote, right: note.GeneralNote) -> bool:
    if left.isRest and right.isRest:
        return True
    if left.isNote and right.isNote:
        return int(round(left.pitch.midi)) == int(round(right.pitch.midi))
    if left.isChord and right.isChord:
        return tuple(sorted(int(round(p.midi)) for p in left.pitches)) == tuple(
            sorted(int(round(p.midi)) for p in right.pitches)
        )
    return False


def _is_tied_pair(left: note.GeneralNote, right: note.GeneralNote) -> bool:
    left_tie = getattr(getattr(left, "tie", None), "type", None)
    right_tie = getattr(getattr(right, "tie", None), "type", None)
    if left_tie in {"start", "continue"} and right_tie in {"stop", "continue"}:
        return True
    if left.isChord and right.isChord:
        left_ties = {getattr(getattr(chord_note, "tie", None), "type", None) for chord_note in left.notes}
        right_ties = {getattr(getattr(chord_note, "tie", None), "type", None) for chord_note in right.notes}
        return bool(left_ties & {"start", "continue"}) and bool(right_ties & {"stop", "continue"})
    return False


def _clear_ties(element: note.GeneralNote) -> None:
    if element.isNote:
        element.tie = None
    elif element.isChord:
        for chord_note in element.notes:
            chord_note.tie = None


def _copy_with_duration(element: note.GeneralNote, duration: Fraction) -> note.GeneralNote:
    copied = copy.deepcopy(element)
    _set_ql(copied, duration)
    return copied


def _rewrite_measure_notes_and_rests(measure: stream.Measure, items: list[tuple[Fraction, note.GeneralNote]]) -> None:
    for element in list(measure.notesAndRests):
        _safe_remove(element)
    for offset, element in items:
        measure.insert(float(offset), element)


def _merge_tied_same_pitch_and_rests(measure: stream.Measure) -> int:
    items = sorted(
        list(measure.notesAndRests),
        key=lambda element: (_ql_fraction(element.offset), getattr(element, "sortTuple", lambda: ())()),
    )
    if len(items) < 2:
        return 0

    rewritten: list[tuple[Fraction, note.GeneralNote]] = []
    changes = 0
    for element in items:
        offset = _ql_fraction(element.offset)
        duration = _ql_fraction(element.quarterLength)
        if rewritten:
            previous_offset, previous = rewritten[-1]
            previous_end = previous_offset + _ql_fraction(previous.quarterLength)
            can_merge = (
                previous_end == offset
                and _same_pitch_content(previous, element)
                and (
                    previous.isRest
                    or element.isRest
                    or _is_tied_pair(previous, element)
                )
            )
            if can_merge:
                _set_ql(previous, _ql_fraction(previous.quarterLength) + duration)
                if not previous.isRest:
                    _clear_ties(previous)
                changes += 1
                continue
        rewritten.append((offset, _copy_with_duration(element, duration)))

    if changes:
        _rewrite_measure_notes_and_rests(measure, rewritten)
    return changes


def _measure_total(measure: stream.Measure) -> Fraction:
    duration = measure.barDuration or measure.duration
    return _ql_fraction(duration.quarterLength)


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


def _nearest_beat_boundary(value: Fraction, total: Fraction, beat: Fraction) -> Fraction:
    if beat <= 0:
        return value
    candidates = [Fraction(0, 1), total]
    count = int(total / beat) + 2
    for index in range(1, count):
        boundary = beat * index
        if Fraction(0, 1) < boundary < total:
            candidates.append(boundary)
    return min(candidates, key=lambda candidate: abs(candidate - value))


def _normalize_release_residue(measure: stream.Measure, *, tolerance: Fraction = Fraction(1, 4)) -> int:
    items = sorted(list(measure.notesAndRests), key=lambda element: _ql_fraction(element.offset))
    if len(items) < 2:
        return 0
    total = _measure_total(measure)
    beat = _beat_unit(measure)
    last = items[-1]
    previous = items[-2]
    if not last.isRest or previous.isRest:
        return 0
    last_offset = _ql_fraction(last.offset)
    last_duration = _ql_fraction(last.quarterLength)
    if last_offset + last_duration != total:
        return 0

    previous_offset = _ql_fraction(previous.offset)
    previous_duration = _ql_fraction(previous.quarterLength)
    previous_end = previous_offset + previous_duration
    if previous_end != last_offset:
        return 0

    if last_duration <= tolerance and previous_duration >= Fraction(1, 1):
        _set_ql(previous, previous_duration + last_duration)
        _safe_remove(last)
        return 1

    boundary = _nearest_beat_boundary(previous_end, total, beat)
    delta = boundary - previous_end
    if delta <= 0 or delta > tolerance or last_duration <= delta:
        return 0
    _set_ql(previous, previous_duration + delta)
    _set_ql(last, last_duration - delta)
    last.offset = float(boundary)
    return 1


def _split_rests_at_beat_boundaries(measure: stream.Measure) -> int:
    total = _measure_total(measure)
    beat = _beat_unit(measure)
    if beat <= 0:
        return 0
    changes = 0
    for element in list(measure.notesAndRests):
        if not element.isRest:
            continue
        offset = _ql_fraction(element.offset)
        duration = _ql_fraction(element.quarterLength)
        end = offset + duration
        if offset == 0 and duration == total:
            continue
        boundaries: list[Fraction] = []
        index = 1
        while beat * index < total:
            boundary = beat * index
            if offset < boundary < end:
                boundaries.append(boundary)
            index += 1
        if not boundaries:
            continue
        split_points = [offset, *boundaries, end]
        _safe_remove(element)
        for start, stop in zip(split_points, split_points[1:]):
            measure.insert(float(start), _copy_with_duration(element, stop - start))
        changes += len(split_points) - 2
    return changes


def normalize_beat_readability(score: stream.Score) -> int:
    """Clean source-derived note/rest residues that obscure the beat."""

    changes = 0
    for part in score.parts:
        for measure in part.getElementsByClass(stream.Measure):
            changes += _merge_tied_same_pitch_and_rests(measure)
            changes += _normalize_release_residue(measure)
            changes += _split_rests_at_beat_boundaries(measure)
    return changes


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


def _tied_note_items(part: stream.Part) -> list[tuple[note.Note, float, float, int]]:
    items: list[tuple[note.Note, float, float, int]] = []
    for element in part.recurse().notes:
        try:
            offset = float(element.getOffsetInHierarchy(part))
        except Exception:
            offset = float(element.offset)
        duration = float(element.quarterLength)
        if isinstance(element, note.Note):
            items.append((element, offset, offset + duration, int(round(element.pitch.midi))))
        elif element.isChord:
            for chord_note in element.notes:
                items.append((chord_note, offset, offset + duration, int(round(chord_note.pitch.midi))))
    return sorted(items, key=lambda item: (item[1], item[2], item[3]))


def suppress_tie_continuation_accidentals(score: stream.Score) -> int:
    """Hide visible accidentals on notes that continue an existing tie."""

    count = 0
    for part in score.parts:
        for tied_note, _start, _end, _midi in _tied_note_items(part):
            if getattr(getattr(tied_note, "tie", None), "type", None) not in {"stop", "continue"}:
                continue
            accidental = tied_note.pitch.accidental
            if accidental is not None and accidental.displayStatus is not False:
                accidental.displayStatus = False
                count += 1
    return count


def normalize_dangling_ties(score: stream.Score) -> int:
    """Remove or repair tie markings that do not connect to a matching pitch."""

    count = 0
    for part in score.parts:
        items = _tied_note_items(part)
        for tied_note, start, end, midi in items:
            tie_type = getattr(getattr(tied_note, "tie", None), "type", None)
            if tie_type is None:
                continue
            has_previous = any(
                previous_midi == midi
                and abs(previous_end - start) < 1e-6
                and getattr(getattr(previous_note, "tie", None), "type", None) in {"start", "continue"}
                for previous_note, _previous_start, previous_end, previous_midi in items
            )
            has_next = any(
                next_midi == midi
                and abs(next_start - end) < 1e-6
                and getattr(getattr(next_note, "tie", None), "type", None) in {"stop", "continue"}
                for next_note, next_start, _next_end, next_midi in items
            )
            new_tie_type = tie_type
            if tie_type == "start" and not has_next:
                new_tie_type = None
            elif tie_type == "continue":
                if has_previous and not has_next:
                    new_tie_type = "stop"
                elif not has_previous and has_next:
                    new_tie_type = "start"
                elif not has_previous and not has_next:
                    new_tie_type = None
            elif tie_type == "stop" and not has_previous:
                new_tie_type = None

            if new_tie_type == tie_type:
                continue
            tied_note.tie = None if new_tie_type is None else tie.Tie(new_tie_type)
            count += 1
    return count


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


def _is_viola_part(part: stream.Part) -> bool:
    name = _part_name(part)
    return "viola" in name or "vla" in name


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


def add_viola_high_clefs(
    score: stream.Score,
    *,
    treble_midi: int = 69,
    alto_return_midi: int = 65,
    min_high_duration: float = 1.0,
) -> int:
    """Insert treble clef for sustained high viola passages."""

    count = 0
    for part in score.parts:
        if not _is_viola_part(part):
            continue
        current_clef: clef.Clef = clef.AltoClef()
        for measure in part.getElementsByClass(stream.Measure):
            measure_clefs = list(measure.getElementsByClass(clef.Clef))
            if measure_clefs:
                current_clef = measure_clefs[-1]
            values = _measure_pitch_values(measure)
            if not values:
                target_clef = current_clef
            elif (
                max(midi for midi, _ in values) >= treble_midi
                and _duration_at_or_above(values, treble_midi) >= min_high_duration
            ):
                target_clef = clef.TrebleClef()
            elif max(midi for midi, _ in values) <= alto_return_midi:
                target_clef = clef.AltoClef()
            else:
                target_clef = current_clef
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
    suppress_tie_accidentals: bool = True,
    normalize_ties: bool = True,
    beat_readability: bool = True,
    final_barlines: bool = True,
    cello_clefs: bool = True,
    viola_clefs: bool = True,
) -> NotationCleanupReport:
    """Apply conservative notation cleanup for review exports."""

    report = NotationCleanupReport()
    if normalize_ties:
        report.normalized_dangling_ties = normalize_dangling_ties(score)
    if beat_readability:
        report.beat_readability_changes = normalize_beat_readability(score)
    if suppress_naturals:
        report.suppressed_naturals = suppress_unneeded_naturals(score)
    if suppress_tie_accidentals:
        report.suppressed_tie_continuation_accidentals = suppress_tie_continuation_accidentals(score)
    if clean_dynamics:
        report.removed_dynamics, report.removed_hairpins = remove_editorial_dynamics(score)
    if final_barlines:
        report.final_barlines_added = add_final_barlines(score)
    if cello_clefs:
        report.cello_clef_changes_added = add_cello_high_clefs(score)
    if viola_clefs:
        report.viola_clef_changes_added = add_viola_high_clefs(score)
    return report


def cleanup_musicxml(
    input_path: str | Path,
    output_path: str | Path,
    *,
    clean_dynamics: bool = False,
    suppress_naturals: bool = True,
    suppress_tie_accidentals: bool = True,
    normalize_ties: bool = True,
    beat_readability: bool = True,
    final_barlines: bool = True,
    cello_clefs: bool = True,
    viola_clefs: bool = True,
) -> NotationCleanupReport:
    """Read MusicXML, clean it, and write a MusicXML file."""

    score = converter.parse(input_path)
    report = cleanup_score(
        score,
        clean_dynamics=clean_dynamics,
        suppress_naturals=suppress_naturals,
        suppress_tie_accidentals=suppress_tie_accidentals,
        normalize_ties=normalize_ties,
        beat_readability=beat_readability,
        final_barlines=final_barlines,
        cello_clefs=cello_clefs,
        viola_clefs=viola_clefs,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(output_path))
    return report
