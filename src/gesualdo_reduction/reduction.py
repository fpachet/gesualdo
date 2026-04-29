"""Rhythm-first madrigal-to-string-quartet reduction helpers.

The reducer in this module is deliberately conservative: selected output notes
are copied from real source note events, then split only where source barlines
require it.  It does not build rhythms from a global onset/offset grid.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import groupby
from pathlib import Path
from typing import Iterable, Sequence

from music21 import (
    base,
    chord,
    clef,
    common,
    converter,
    expressions,
    instrument,
    key,
    metadata,
    meter,
    note,
    stream,
    tempo,
    tie,
)


SEMITONES = -9
OUT_PATH = "gesualdo_quartet_V2.musicxml"
ENFORCE_RANGES = True
REGISTER_SPLIT = 60
MAX_DENOMINATOR = 4096

RANGES = {
    "vln1": (55, 100),  # G3..E7
    "vln2": (55, 88),  # G3..E6
    "vla": (48, 88),  # C3..E6
    "vc": (36, 72),  # C2..C5
}


class MeasureValidationError(ValueError):
    """Raised when a constructed part is not exactly measured."""


@dataclass(frozen=True)
class Bar:
    """A source-derived measure boundary."""

    index: int
    number: int
    start: Fraction
    duration: Fraction
    time_signature: meter.TimeSignature | None = None

    @property
    def end(self) -> Fraction:
        return self.start + self.duration


@dataclass(frozen=True)
class SourceEvent:
    """A note/rest event copied from one source part."""

    source_id: str
    part_index: int
    event_index: int
    start: Fraction
    duration: Fraction
    pitch_midi: int | None
    is_rest: bool
    source_element: base.Music21Object | None = None
    source_tie_type: str | None = None

    @property
    def end(self) -> Fraction:
        return self.start + self.duration

    @property
    def pitch_class(self) -> int | None:
        return None if self.pitch_midi is None else self.pitch_midi % 12


@dataclass(frozen=True)
class Fragment:
    """A measure-local fragment of a source event."""

    event: SourceEvent | None
    offset: Fraction
    duration: Fraction
    is_generated_rest: bool = False

    @property
    def end(self) -> Fraction:
        return self.offset + self.duration


def ql_to_fraction(value) -> Fraction:
    """Convert a music21 quarterLength/offset into a stable rational value."""

    normalized = common.opFrac(value)
    if isinstance(normalized, Fraction):
        return normalized
    if isinstance(normalized, int):
        return Fraction(normalized, 1)
    return Fraction(normalized).limit_denominator(MAX_DENOMINATOR)


def fraction_to_ql(value: Fraction):
    """Return a music21-friendly quarterLength."""

    return int(value) if value.denominator == 1 else value


def pitch_class(midi_pitch: int | None) -> int | None:
    return None if midi_pitch is None else int(midi_pitch) % 12


def octave_fit(midi_pitch: int | None, low: int, high: int) -> int | None:
    if midi_pitch is None:
        return None
    fitted = int(midi_pitch)
    while fitted < low:
        fitted += 12
    while fitted > high:
        fitted -= 12
    return fitted


def part_median_pitch(part: stream.Part) -> float:
    values: list[int] = []
    for el in part.flatten().notes:
        if isinstance(el, chord.Chord):
            values.extend(p.midi for p in el.pitches)
        elif isinstance(el, note.Note):
            values.append(el.pitch.midi)
    if not values:
        return float("nan")
    values.sort()
    mid = len(values) // 2
    if len(values) % 2:
        return float(values[mid])
    return 0.5 * (values[mid - 1] + values[mid])


def identify_outer_parts(parts: Sequence[stream.Part]) -> tuple[int, int]:
    medians = []
    for index, part in enumerate(parts):
        median = part_median_pitch(part)
        if median == median:
            medians.append((index, median))
    if not medians:
        raise ValueError("Could not identify outer voices; no pitched material found.")
    return max(medians, key=lambda item: item[1])[0], min(medians, key=lambda item: item[1])[0]


def build_bar_map(src_score: stream.Score) -> list[Bar]:
    """Build authoritative bar boundaries from the source measure structure."""

    measured = src_score.makeMeasures(inPlace=False)
    measured_parts = list(measured.parts) if measured.parts else [measured]
    bars_by_start: dict[Fraction, dict[str, object]] = {}

    for part in measured_parts:
        for measure in part.getElementsByClass(stream.Measure):
            start = ql_to_fraction(measure.offset)
            duration_source = measure.barDuration or measure.duration
            duration = ql_to_fraction(duration_source.quarterLength)
            if duration <= 0:
                continue
            existing = bars_by_start.setdefault(
                start,
                {
                    "duration": duration,
                    "time_signature": measure.timeSignature,
                    "number": measure.number,
                },
            )
            existing["duration"] = max(existing["duration"], duration)
            if existing["time_signature"] is None and measure.timeSignature is not None:
                existing["time_signature"] = measure.timeSignature

    if not bars_by_start:
        ts = meter.TimeSignature("4/4")
        highest = max(ql_to_fraction(src_score.highestTime), Fraction(4, 1))
        bars_by_start[Fraction(0, 1)] = {
            "duration": ql_to_fraction(ts.barDuration.quarterLength),
            "time_signature": ts,
            "number": 1,
        }
        while max(start + data["duration"] for start, data in bars_by_start.items()) < highest:
            start = max(start + data["duration"] for start, data in bars_by_start.items())
            bars_by_start[start] = {
                "duration": ql_to_fraction(ts.barDuration.quarterLength),
                "time_signature": None,
                "number": len(bars_by_start) + 1,
            }

    starts = sorted(bars_by_start)
    bars: list[Bar] = []
    for index, start in enumerate(starts):
        data = bars_by_start[start]
        bars.append(
            Bar(
                index=index,
                number=int(data["number"] or index + 1),
                start=start,
                duration=data["duration"],
                time_signature=copy.deepcopy(data["time_signature"]),
            )
        )

    highest_time = ql_to_fraction(src_score.highestTime)
    if bars and highest_time > bars[-1].end:
        last_duration = bars[-1].duration
        start = bars[-1].end
        while start < highest_time:
            bars.append(
                Bar(
                    index=len(bars),
                    number=bars[-1].number + 1,
                    start=start,
                    duration=last_duration,
                    time_signature=None,
                )
            )
            start = bars[-1].end

    return bars


def final_bar_end(bars: Sequence[Bar]) -> Fraction:
    return bars[-1].end if bars else Fraction(0, 1)


def extract_events(
    part: stream.Part,
    part_index: int,
    *,
    include_rests: bool,
    chord_policy: str = "top",
) -> list[SourceEvent]:
    """Extract source events without changing offsets or durations."""

    events: list[SourceEvent] = []
    event_index = 0
    for element in part.flatten().notesAndRests:
        start = ql_to_fraction(element.offset)
        duration = ql_to_fraction(element.quarterLength)
        if duration <= 0:
            continue

        tie_type = getattr(getattr(element, "tie", None), "type", None)
        if isinstance(element, note.Rest):
            if not include_rests:
                continue
            events.append(
                SourceEvent(
                    source_id=f"p{part_index}:e{event_index}",
                    part_index=part_index,
                    event_index=event_index,
                    start=start,
                    duration=duration,
                    pitch_midi=None,
                    is_rest=True,
                    source_element=element,
                    source_tie_type=None,
                )
            )
            event_index += 1
            continue

        pitches: list[int]
        if isinstance(element, chord.Chord):
            chord_pitches = [int(p.midi) for p in element.pitches]
            if chord_policy == "all":
                pitches = sorted(chord_pitches)
            elif chord_policy == "bottom":
                pitches = [min(chord_pitches)]
            else:
                pitches = [max(chord_pitches)]
        elif isinstance(element, note.Note):
            pitches = [int(element.pitch.midi)]
        else:
            continue

        for pitch_index, midi_pitch in enumerate(pitches):
            suffix = "" if len(pitches) == 1 else f":p{pitch_index}"
            events.append(
                SourceEvent(
                    source_id=f"p{part_index}:e{event_index}{suffix}",
                    part_index=part_index,
                    event_index=event_index,
                    start=start,
                    duration=duration,
                    pitch_midi=midi_pitch,
                    is_rest=False,
                    source_element=element,
                    source_tie_type=tie_type,
                )
            )
        event_index += 1

    return sorted(events, key=lambda ev: (ev.start, ev.end, ev.source_id))


def fit_event_to_range(event: SourceEvent, low: int, high: int) -> SourceEvent:
    if event.is_rest:
        return event
    return replace(event, pitch_midi=octave_fit(event.pitch_midi, low, high))


def collect_key_signatures(src_score: stream.Score, bars: Sequence[Bar]) -> dict[Fraction, list[key.KeySignature]]:
    starts = [bar.start for bar in bars]
    result: dict[Fraction, list[key.KeySignature]] = {}
    seen: set[tuple[Fraction, int | None]] = set()

    def snap_to_bar(offset: Fraction) -> Fraction:
        snapped = starts[0] if starts else Fraction(0, 1)
        for start in starts:
            if start <= offset:
                snapped = start
            else:
                break
        return snapped

    for key_sig in src_score.recurse().getElementsByClass(key.KeySignature):
        offset = snap_to_bar(absolute_offset(key_sig, src_score))
        marker = (offset, key_sig.sharps)
        if marker in seen:
            continue
        seen.add(marker)
        result.setdefault(offset, []).append(key.KeySignature(key_sig.sharps))
    return result


def absolute_offset(element: base.Music21Object, root: stream.Stream) -> Fraction:
    try:
        return ql_to_fraction(element.getOffsetInHierarchy(root))
    except Exception:
        return ql_to_fraction(element.offset)


def _bar_for_offset(offset: Fraction, bars: Sequence[Bar]) -> Bar | None:
    for bar in bars:
        if bar.start <= offset < bar.end:
            return bar
    if bars and offset == bars[-1].end:
        return bars[-1]
    return None


def _event_fragments_for_bar(event: SourceEvent, bar: Bar) -> Fragment | None:
    start = max(event.start, bar.start)
    end = min(event.end, bar.end)
    if start >= end:
        return None
    return Fragment(event=event, offset=start - bar.start, duration=end - start)


def _make_note_fragment_element(event: SourceEvent, offset: Fraction, duration: Fraction, bar: Bar) -> note.Note:
    if event.pitch_midi is None:
        raise ValueError(f"Note event without pitch: {event.source_id}")

    out_note = note.Note(int(event.pitch_midi), quarterLength=fraction_to_ql(duration))
    out_note.editorial.sourceEventId = event.source_id
    out_note.editorial.sourcePartIndex = event.part_index

    abs_start = bar.start + offset
    abs_end = abs_start + duration
    continues_from_before = abs_start > event.start
    continues_after = abs_end < event.end
    if continues_from_before and continues_after:
        out_note.tie = tie.Tie("continue")
    elif continues_from_before:
        out_note.tie = tie.Tie("stop")
    elif continues_after:
        out_note.tie = tie.Tie("start")
    elif event.source_tie_type is not None:
        out_note.tie = tie.Tie(event.source_tie_type)
    return out_note


def _make_rest_fragment_element(event: SourceEvent | None, duration: Fraction) -> note.Rest:
    rest = note.Rest(quarterLength=fraction_to_ql(duration))
    if event is not None:
        rest.editorial.sourceEventId = event.source_id
    return rest


def _insert_fragment(measure: stream.Measure, fragment: Fragment, bar: Bar) -> None:
    if fragment.is_generated_rest or fragment.event is None:
        element = _make_rest_fragment_element(None, fragment.duration)
    elif fragment.event.is_rest:
        element = _make_rest_fragment_element(fragment.event, fragment.duration)
    else:
        element = _make_note_fragment_element(fragment.event, fragment.offset, fragment.duration, bar)
    measure.insert(fraction_to_ql(fragment.offset), element)


def build_measured_part(
    events: Sequence[SourceEvent],
    bars: Sequence[Bar],
    *,
    part_name: str,
    instrument_obj: instrument.Instrument,
    clef_obj: clef.Clef,
    key_signatures: dict[Fraction, list[key.KeySignature]] | None = None,
) -> stream.Part:
    """Build a measured monophonic part from source events."""

    part = stream.Part()
    part.partName = part_name
    part.insert(0, copy.deepcopy(instrument_obj))
    part.insert(0, copy.deepcopy(clef_obj))
    sorted_events = sorted(events, key=lambda ev: (ev.start, ev.end, ev.source_id))
    key_signatures = key_signatures or {}

    for bar in bars:
        measure = stream.Measure(number=bar.number)
        if bar.time_signature is not None:
            measure.insert(0, meter.TimeSignature(bar.time_signature.ratioString))
        for key_sig in key_signatures.get(bar.start, []):
            measure.insert(0, copy.deepcopy(key_sig))

        fragments = [
            fragment
            for event in sorted_events
            if (fragment := _event_fragments_for_bar(event, bar)) is not None
        ]
        fragments.sort(key=lambda frag: (frag.offset, frag.end, frag.event.source_id if frag.event else ""))

        cursor = Fraction(0, 1)
        for fragment in fragments:
            if fragment.offset < cursor:
                source_id = fragment.event.source_id if fragment.event else "<generated>"
                raise MeasureValidationError(
                    f"{part_name} has overlapping source events near measure {bar.number}: {source_id}"
                )
            if fragment.offset > cursor:
                _insert_fragment(
                    measure,
                    Fragment(event=None, offset=cursor, duration=fragment.offset - cursor, is_generated_rest=True),
                    bar,
                )
            _insert_fragment(measure, fragment, bar)
            cursor = fragment.end

        if cursor < bar.duration:
            _insert_fragment(
                measure,
                Fragment(event=None, offset=cursor, duration=bar.duration - cursor, is_generated_rest=True),
                bar,
            )

        part.insert(fraction_to_ql(bar.start), measure)

    validate_measured_part(part, bars)
    return part


def validate_measured_part(part: stream.Part, bars: Sequence[Bar]) -> None:
    measures = list(part.getElementsByClass(stream.Measure))
    if len(measures) != len(bars):
        raise MeasureValidationError(
            f"{part.partName or '<part>'} has {len(measures)} measures; expected {len(bars)}."
        )

    for measure, bar in zip(measures, bars, strict=True):
        items = sorted(measure.notesAndRests, key=lambda el: ql_to_fraction(el.offset))
        cursor = Fraction(0, 1)
        for element in items:
            offset = ql_to_fraction(element.offset)
            duration = ql_to_fraction(element.quarterLength)
            if duration <= 0:
                raise MeasureValidationError(f"{part.partName} measure {bar.number} has zero-length element.")
            if offset != cursor:
                relation = "overlap" if offset < cursor else "gap"
                raise MeasureValidationError(
                    f"{part.partName} measure {bar.number} has a {relation} at {cursor}."
                )
            cursor = offset + duration
            if cursor > bar.duration:
                raise MeasureValidationError(f"{part.partName} measure {bar.number} is overfull.")
            if element.isNote and not hasattr(element.editorial, "sourceEventId"):
                raise MeasureValidationError(
                    f"{part.partName} measure {bar.number} contains an untraced output note."
                )
        if cursor != bar.duration:
            raise MeasureValidationError(
                f"{part.partName} measure {bar.number} duration {cursor} != expected {bar.duration}."
            )


def validate_score_measures(score: stream.Score, bars: Sequence[Bar]) -> None:
    for part in score.parts:
        validate_measured_part(part, bars)


def active_pitch_at(events: Sequence[SourceEvent], offset: Fraction) -> int | None:
    for event in events:
        if not event.is_rest and event.start <= offset < event.end:
            return event.pitch_midi
    return None


def spread_score(midi_pitch: int, anchors: Iterable[int | None]) -> int:
    real_anchors = [anchor for anchor in anchors if anchor is not None]
    if not real_anchors:
        return 0
    return min(abs(midi_pitch - anchor) for anchor in real_anchors)


def _is_new_onset(event: SourceEvent) -> bool:
    return event.source_tie_type not in {"stop", "continue"}


def _dedupe_candidates(candidates: Sequence[SourceEvent]) -> list[SourceEvent]:
    best_by_pitch: dict[int, SourceEvent] = {}
    for candidate in candidates:
        if candidate.pitch_midi is None:
            continue
        current = best_by_pitch.get(candidate.pitch_midi)
        if current is None:
            best_by_pitch[candidate.pitch_midi] = candidate
            continue
        if (_is_new_onset(candidate), candidate.duration) > (_is_new_onset(current), current.duration):
            best_by_pitch[candidate.pitch_midi] = candidate
    return list(best_by_pitch.values())


def select_middle_events(
    middle_events: Sequence[SourceEvent],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
) -> tuple[list[SourceEvent], list[SourceEvent]]:
    """Select real middle-note events for Violin II and Viola."""

    v2_events: list[SourceEvent] = []
    vla_events: list[SourceEvent] = []
    busy_until = {"v2": Fraction(0, 1), "vla": Fraction(0, 1)}
    last_pitch: dict[str, int | None] = {"v2": None, "vla": None}

    note_events = sorted(
        [event for event in middle_events if not event.is_rest and event.pitch_midi is not None],
        key=lambda ev: (ev.start, ev.end, ev.source_id),
    )

    for start, group_iter in groupby(note_events, key=lambda ev: ev.start):
        group = list(group_iter)
        available = [name for name in ("v2", "vla") if busy_until[name] <= start]
        if not available:
            continue

        outer_pitches = [active_pitch_at(top_events, start), active_pitch_at(bottom_events, start)]
        covered = {pitch % 12 for pitch in outer_pitches if pitch is not None}
        candidates = [
            event
            for event in _dedupe_candidates(group)
            if event.pitch_midi is not None and event.pitch_midi % 12 not in covered
        ]
        anchors = [pitch for pitch in outer_pitches if pitch is not None]
        candidates.sort(
            key=lambda ev: (
                not _is_new_onset(ev),
                -spread_score(int(ev.pitch_midi), anchors),
                -ev.duration,
                ev.source_id,
            )
        )

        chosen: list[SourceEvent] = []
        seen_pitch_classes = set(covered)
        for candidate in candidates:
            if len(chosen) >= len(available):
                break
            pc = candidate.pitch_midi % 12
            if pc in seen_pitch_classes:
                continue
            chosen.append(candidate)
            seen_pitch_classes.add(pc)

        if not chosen:
            continue

        assignments: list[tuple[str, SourceEvent]] = []
        if len(chosen) >= 2 and "v2" in available and "vla" in available:
            hi, lo = sorted(chosen[:2], key=lambda ev: int(ev.pitch_midi), reverse=True)
            if last_pitch["v2"] is not None and last_pitch["vla"] is not None:
                normal = abs(int(hi.pitch_midi) - last_pitch["v2"]) + abs(int(lo.pitch_midi) - last_pitch["vla"])
                swapped = abs(int(lo.pitch_midi) - last_pitch["v2"]) + abs(int(hi.pitch_midi) - last_pitch["vla"])
                if swapped < normal:
                    hi, lo = lo, hi
            assignments = [("v2", hi), ("vla", lo)]
        else:
            event = chosen[0]
            if len(available) == 1:
                target = available[0]
            elif last_pitch["v2"] is None and last_pitch["vla"] is None:
                target = "v2" if int(event.pitch_midi) >= register_split else "vla"
            elif last_pitch["v2"] is None:
                target = "v2"
            elif last_pitch["vla"] is None:
                target = "vla"
            else:
                target = (
                    "v2"
                    if abs(int(event.pitch_midi) - last_pitch["v2"])
                    <= abs(int(event.pitch_midi) - last_pitch["vla"])
                    else "vla"
                )
            assignments = [(target, event)]

        for target, event in assignments:
            if event.start < busy_until[target]:
                continue
            if enforce_ranges:
                low, high = RANGES["vln2"] if target == "v2" else RANGES["vla"]
                event = fit_event_to_range(event, low, high)
            if target == "v2":
                v2_events.append(event)
            else:
                vla_events.append(event)
            busy_until[target] = event.end
            last_pitch[target] = event.pitch_midi

    return v2_events, vla_events


def copy_top_staff_markings(src_score: stream.Score, out_score: stream.Score, bars: Sequence[Bar]) -> None:
    if not out_score.parts:
        return
    top_part = out_score.parts[0]
    measures = list(top_part.getElementsByClass(stream.Measure))
    seen_tempos: set[tuple[Fraction, int | None, str | None]] = set()
    seen_text: set[tuple[Fraction, str]] = set()

    def insert_at_source_offset(offset: Fraction, element: base.Music21Object) -> None:
        bar = _bar_for_offset(offset, bars)
        if bar is None:
            return
        measures[bar.index].insert(fraction_to_ql(offset - bar.start), element)

    for mark in src_score.recurse().getElementsByClass(tempo.MetronomeMark):
        offset = absolute_offset(mark, src_score)
        marker = (offset, mark.number, mark.text)
        if marker in seen_tempos:
            continue
        seen_tempos.add(marker)
        insert_at_source_offset(offset, copy.deepcopy(mark))

    for text_expression in src_score.recurse().getElementsByClass(expressions.TextExpression):
        offset = absolute_offset(text_expression, src_score)
        marker = (offset, text_expression.content)
        if marker in seen_text:
            continue
        seen_text.add(marker)
        insert_at_source_offset(offset, expressions.TextExpression(text_expression.content))


def build_quartet_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
) -> stream.Score:
    bars = build_bar_map(src_score)
    if not bars:
        raise ValueError("Could not derive any source bars.")

    parts = list(src_score.parts) if src_score.parts else [src_score]
    if len(parts) < 4:
        raise ValueError(f"Expected at least 4 parts; found {len(parts)}.")

    top_index, bottom_index = identify_outer_parts(parts)
    middle_indices = [index for index in range(len(parts)) if index not in (top_index, bottom_index)]
    key_signatures = collect_key_signatures(src_score, bars)

    top_events = extract_events(parts[top_index], top_index, include_rests=True, chord_policy="top")
    bottom_events = extract_events(parts[bottom_index], bottom_index, include_rests=True, chord_policy="bottom")
    middle_events = [
        event
        for index in middle_indices
        for event in extract_events(parts[index], index, include_rests=False, chord_policy="all")
    ]

    if enforce_ranges:
        top_events = [fit_event_to_range(event, *RANGES["vln1"]) for event in top_events]
        bottom_events = [fit_event_to_range(event, *RANGES["vc"]) for event in bottom_events]

    top_note_events = [event for event in top_events if not event.is_rest]
    bottom_note_events = [event for event in bottom_events if not event.is_rest]
    v2_events, vla_events = select_middle_events(
        middle_events,
        top_note_events,
        bottom_note_events,
        enforce_ranges=enforce_ranges,
        register_split=register_split,
    )

    quartet_parts = [
        build_measured_part(
            top_events,
            bars,
            part_name="Violin I",
            instrument_obj=instrument.Violin(),
            clef_obj=clef.TrebleClef(),
            key_signatures=key_signatures,
        ),
        build_measured_part(
            v2_events,
            bars,
            part_name="Violin II",
            instrument_obj=instrument.Violin(),
            clef_obj=clef.TrebleClef(),
            key_signatures=key_signatures,
        ),
        build_measured_part(
            vla_events,
            bars,
            part_name="Viola",
            instrument_obj=instrument.Viola(),
            clef_obj=clef.AltoClef(),
            key_signatures=key_signatures,
        ),
        build_measured_part(
            bottom_events,
            bars,
            part_name="Violoncello",
            instrument_obj=instrument.Violoncello(),
            clef_obj=clef.BassClef(),
            key_signatures=key_signatures,
        ),
    ]

    out = stream.Score()
    out.insert(0, metadata.Metadata())
    if src_score.metadata:
        out.metadata.title = ((src_score.metadata.title or "") + " - String Quartet Reduction").strip(" -")
        out.metadata.composer = src_score.metadata.composer

    for quartet_part in quartet_parts:
        out.insert(0, quartet_part)

    copy_top_staff_markings(src_score, out, bars)
    validate_score_measures(out, bars)
    return out


def reduce_to_quartet(
    midi_path: str | Path,
    semitones: int = SEMITONES,
    out_path: str | Path = OUT_PATH,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
) -> stream.Score:
    src_score = converter.parse(midi_path)
    if semitones:
        src_score = src_score.transpose(semitones)
    out_score = build_quartet_score(
        src_score,
        enforce_ranges=enforce_ranges,
        register_split=register_split,
    )
    out_score.write("musicxml", fp=str(out_path))
    print(f"Written: {out_path}")
    return out_score
