"""Rhythm-first madrigal-to-string-ensemble reduction helpers.

The reducer in this module is deliberately conservative: selected output notes
are copied from real source note events, then split only where source barlines
require it.  It does not build rhythms from a global onset/offset grid.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import groupby, permutations
from pathlib import Path
from typing import Callable, Iterable, Sequence

from music21 import (
    base,
    chord,
    clef,
    common,
    converter,
    expressions,
    instrument,
    key,
    layout,
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
DEFAULT_TRANSPOSITION_CANDIDATES = tuple(range(-18, 7))

RANGES = {
    "vln1": (55, 100),  # G3..E7
    "vln2": (55, 88),  # G3..E6
    "vda": (45, 88),  # A2..E6, configurable viola d'amore default
    "vla": (48, 88),  # C3..E6
    "vc": (36, 72),  # C2..C5
    "pno_rh": (48, 108),  # C3..C8
    "pno_lh": (21, 72),  # A0..C5
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


@dataclass(frozen=True)
class TargetPart:
    """One instrumental destination in a reduction profile."""

    id: str
    name: str
    midi_range: tuple[int, int]
    instrument_factory: Callable[[], instrument.Instrument]
    clef_factory: Callable[[], clef.Clef]
    role: str = "inner"
    preferred_register: tuple[int, int] | None = None

    def make_instrument(self) -> instrument.Instrument:
        return self.instrument_factory()

    def make_clef(self) -> clef.Clef:
        return self.clef_factory()


@dataclass(frozen=True)
class EnsembleProfile:
    """Instrument layout and score metadata for a reduction target."""

    name: str
    title_suffix: str
    parts: tuple[TargetPart, ...]
    minimum_source_parts: int = 2

    def target(self, target_id: str) -> TargetPart:
        for part in self.parts:
            if part.id == target_id:
                return part
        raise KeyError(f"Unknown target part: {target_id}")

    def _single_role(self, role: str) -> TargetPart:
        matches = [part for part in self.parts if part.role == role]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {role!r} part in {self.name}; found {len(matches)}.")
        return matches[0]

    @property
    def top_part(self) -> TargetPart:
        return self._single_role("top")

    @property
    def bottom_part(self) -> TargetPart:
        return self._single_role("bottom")

    @property
    def inner_parts(self) -> tuple[TargetPart, ...]:
        return tuple(part for part in self.parts if part.role == "inner")


@dataclass(frozen=True)
class ReductionConfig:
    """Runtime options shared by reduction policies."""

    enforce_ranges: bool = ENFORCE_RANGES
    register_split: int = REGISTER_SPLIT


@dataclass(frozen=True)
class ReductionContext:
    """Source-derived material needed by assignment policies."""

    source_score: stream.Score
    source_parts: tuple[stream.Stream, ...]
    bars: tuple[Bar, ...]
    top_index: int
    bottom_index: int
    middle_indices: tuple[int, ...]
    key_signatures: dict[Fraction, list[key.KeySignature]]
    top_events: tuple[SourceEvent, ...]
    bottom_events: tuple[SourceEvent, ...]
    middle_events: tuple[SourceEvent, ...]


@dataclass(frozen=True)
class TranspositionChoice:
    """A scored global transposition candidate."""

    semitones: int
    score: float
    candidate_scores: tuple[tuple[int, float], ...]


def viole_damour_instrument() -> instrument.Instrument:
    """Create a generic music21 instrument entry for viole d'amour."""

    inst = instrument.Instrument()
    inst.instrumentName = "Viole d'amour"
    inst.instrumentAbbreviation = "Vle. d'am."
    return inst


STRING_QUARTET = EnsembleProfile(
    name="string_quartet",
    title_suffix="String Quartet Reduction",
    minimum_source_parts=4,
    parts=(
        TargetPart(
            id="vln1",
            name="Violin I",
            midi_range=RANGES["vln1"],
            instrument_factory=instrument.Violin,
            clef_factory=clef.TrebleClef,
            role="top",
            preferred_register=(67, 96),
        ),
        TargetPart(
            id="vln2",
            name="Violin II",
            midi_range=RANGES["vln2"],
            instrument_factory=instrument.Violin,
            clef_factory=clef.TrebleClef,
            preferred_register=(60, 88),
        ),
        TargetPart(
            id="vla",
            name="Viola",
            midi_range=RANGES["vla"],
            instrument_factory=instrument.Viola,
            clef_factory=clef.AltoClef,
            preferred_register=(48, 72),
        ),
        TargetPart(
            id="vc",
            name="Violoncello",
            midi_range=RANGES["vc"],
            instrument_factory=instrument.Violoncello,
            clef_factory=clef.BassClef,
            role="bottom",
            preferred_register=(36, 60),
        ),
    ),
)


QUARTET_PLUS_VIOLE = EnsembleProfile(
    name="quartet_plus_viole",
    title_suffix="String Quartet + Viole d'amour Reduction",
    minimum_source_parts=5,
    parts=(
        TargetPart(
            id="vln1",
            name="Violin I",
            midi_range=RANGES["vln1"],
            instrument_factory=instrument.Violin,
            clef_factory=clef.TrebleClef,
            role="top",
            preferred_register=(67, 96),
        ),
        TargetPart(
            id="vln2",
            name="Violin II",
            midi_range=RANGES["vln2"],
            instrument_factory=instrument.Violin,
            clef_factory=clef.TrebleClef,
            preferred_register=(62, 88),
        ),
        TargetPart(
            id="vda",
            name="Viole d'amour",
            midi_range=RANGES["vda"],
            instrument_factory=viole_damour_instrument,
            clef_factory=clef.AltoClef,
            preferred_register=(55, 79),
        ),
        TargetPart(
            id="vla",
            name="Viola",
            midi_range=RANGES["vla"],
            instrument_factory=instrument.Viola,
            clef_factory=clef.AltoClef,
            preferred_register=(48, 72),
        ),
        TargetPart(
            id="vc",
            name="Violoncello",
            midi_range=RANGES["vc"],
            instrument_factory=instrument.Violoncello,
            clef_factory=clef.BassClef,
            role="bottom",
            preferred_register=(36, 60),
        ),
    ),
)


PIANO_REDUCTION = EnsembleProfile(
    name="piano",
    title_suffix="Piano Reduction",
    minimum_source_parts=2,
    parts=(
        TargetPart(
            id="pno_rh",
            name="Piano",
            midi_range=RANGES["pno_rh"],
            instrument_factory=instrument.Piano,
            clef_factory=clef.TrebleClef,
            role="top",
            preferred_register=(60, 84),
        ),
        TargetPart(
            id="pno_lh",
            name="Piano",
            midi_range=RANGES["pno_lh"],
            instrument_factory=instrument.Piano,
            clef_factory=clef.BassClef,
            role="bottom",
            preferred_register=(36, 60),
        ),
    ),
)


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


def octave_candidates(midi_pitch: int, low: int, high: int) -> list[int]:
    candidates: list[int] = []
    base_pitch = int(midi_pitch)
    for octave_shift in range(-8, 9):
        candidate = base_pitch + 12 * octave_shift
        if low <= candidate <= high:
            candidates.append(candidate)
    if candidates:
        return candidates
    fitted = octave_fit(base_pitch, low, high)
    return [] if fitted is None else [fitted]


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


def _insert_fragment(measure: stream.Stream, fragment: Fragment, bar: Bar) -> None:
    if fragment.is_generated_rest or fragment.event is None:
        element = _make_rest_fragment_element(None, fragment.duration)
    elif fragment.event.is_rest:
        element = _make_rest_fragment_element(fragment.event, fragment.duration)
    else:
        element = _make_note_fragment_element(fragment.event, fragment.offset, fragment.duration, bar)
    measure.insert(fraction_to_ql(fragment.offset), element)


def _insert_complete_fragments(
    container: stream.Stream,
    sorted_events: Sequence[SourceEvent],
    bar: Bar,
    *,
    part_name: str,
) -> None:
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
                container,
                Fragment(event=None, offset=cursor, duration=fragment.offset - cursor, is_generated_rest=True),
                bar,
            )
        _insert_fragment(container, fragment, bar)
        cursor = fragment.end

    if cursor < bar.duration:
        _insert_fragment(
            container,
            Fragment(event=None, offset=cursor, duration=bar.duration - cursor, is_generated_rest=True),
            bar,
        )


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

        _insert_complete_fragments(measure, sorted_events, bar, part_name=part_name)
        part.insert(fraction_to_ql(bar.start), measure)

    validate_measured_part(part, bars)
    return part


def build_measured_piano_staff(
    voice_event_groups: Sequence[Sequence[SourceEvent]],
    bars: Sequence[Bar],
    *,
    target: TargetPart,
    key_signatures: dict[Fraction, list[key.KeySignature]] | None = None,
) -> stream.PartStaff:
    """Build one piano staff with independent source voices as notation voices."""

    part = stream.PartStaff()
    part.partName = target.name
    part.partAbbreviation = "Pno."
    part.insert(0, copy.deepcopy(target.make_instrument()))
    part.insert(0, copy.deepcopy(target.make_clef()))
    key_signatures = key_signatures or {}
    sorted_groups = [
        sorted(events, key=lambda ev: (ev.start, ev.end, ev.source_id))
        for events in voice_event_groups
    ]
    if not sorted_groups:
        sorted_groups = [[]]

    for bar in bars:
        measure = stream.Measure(number=bar.number)
        if bar.time_signature is not None:
            measure.insert(0, meter.TimeSignature(bar.time_signature.ratioString))
        for key_sig in key_signatures.get(bar.start, []):
            measure.insert(0, copy.deepcopy(key_sig))

        for voice_index, events in enumerate(sorted_groups, start=1):
            voice = stream.Voice(id=str(voice_index))
            _insert_complete_fragments(voice, events, bar, part_name=f"{target.name} voice {voice_index}")
            measure.insert(0, voice)

        part.insert(fraction_to_ql(bar.start), measure)

    validate_measured_piano_staff(part, bars)
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


def validate_measured_voice(voice: stream.Voice, bars: Sequence[Bar], bar: Bar, part_name: str) -> None:
    items = sorted(voice.notesAndRests, key=lambda el: ql_to_fraction(el.offset))
    cursor = Fraction(0, 1)
    for element in items:
        offset = ql_to_fraction(element.offset)
        duration = ql_to_fraction(element.quarterLength)
        if duration <= 0:
            raise MeasureValidationError(f"{part_name} measure {bar.number} has zero-length element.")
        if offset != cursor:
            relation = "overlap" if offset < cursor else "gap"
            raise MeasureValidationError(
                f"{part_name} measure {bar.number} voice {voice.id} has a {relation} at {cursor}."
            )
        cursor = offset + duration
        if cursor > bar.duration:
            raise MeasureValidationError(f"{part_name} measure {bar.number} voice {voice.id} is overfull.")
        if element.isNote and not hasattr(element.editorial, "sourceEventId"):
            raise MeasureValidationError(
                f"{part_name} measure {bar.number} voice {voice.id} contains an untraced output note."
            )
    if cursor != bar.duration:
        raise MeasureValidationError(
            f"{part_name} measure {bar.number} voice {voice.id} duration {cursor} != expected {bar.duration}."
        )


def validate_measured_piano_staff(part: stream.PartStaff, bars: Sequence[Bar]) -> None:
    measures = list(part.getElementsByClass(stream.Measure))
    if len(measures) != len(bars):
        raise MeasureValidationError(
            f"{part.partName or '<part>'} has {len(measures)} measures; expected {len(bars)}."
        )

    for measure, bar in zip(measures, bars, strict=True):
        voices = list(measure.voices)
        if not voices:
            raise MeasureValidationError(f"{part.partName} measure {bar.number} has no voices.")
        for voice in voices:
            validate_measured_voice(voice, bars, bar, part.partName or "<part>")


def validate_score_measures(score: stream.Score, bars: Sequence[Bar]) -> None:
    for part in score.parts:
        validate_measured_part(part, bars)


def validate_piano_score_measures(score: stream.Score, bars: Sequence[Bar]) -> None:
    for part in score.parts:
        validate_measured_piano_staff(part, bars)


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


def _pitched_events(events: Sequence[SourceEvent]) -> list[SourceEvent]:
    return [event for event in events if not event.is_rest and event.pitch_midi is not None]


def _event_overlaps_interval(event: SourceEvent, start: Fraction, end: Fraction) -> bool:
    return not event.is_rest and event.start < end and start < event.end


def _target_is_free_for_event(
    target: TargetPart,
    event: SourceEvent,
    selected: dict[str, list[SourceEvent]],
) -> bool:
    return not any(
        _event_overlaps_interval(existing, event.start, event.end)
        for existing in selected[target.id]
    )


def _active_pitches_from_assignments(
    selected: dict[str, list[SourceEvent]],
    offset: Fraction,
) -> list[int]:
    return [
        int(event.pitch_midi)
        for events in selected.values()
        for event in events
        if event.pitch_midi is not None and event.start <= offset < event.end
    ]


def _latest_pitch_before(events: Sequence[SourceEvent], offset: Fraction) -> int | None:
    previous_events = [
        event
        for event in events
        if event.pitch_midi is not None and event.end <= offset
    ]
    if not previous_events:
        return None
    return int(max(previous_events, key=lambda event: (event.end, event.start, event.source_id)).pitch_midi)


def _has_nearby_uncovered_event(
    event: SourceEvent,
    events_by_part: dict[int, Sequence[SourceEvent]],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
    *,
    lookahead: Fraction,
) -> bool:
    if event.pitch_midi is None:
        return False
    end = event.start + lookahead
    for sibling in events_by_part.get(event.part_index, ()):
        if sibling.pitch_midi is None or sibling.start < event.start or sibling.start > end:
            continue
        outer_pitches = [active_pitch_at(top_events, sibling.start), active_pitch_at(bottom_events, sibling.start)]
        covered = {pitch % 12 for pitch in outer_pitches if pitch is not None}
        if sibling.pitch_midi % 12 not in covered:
            return True
    return False


def _has_borrowed_neighbor(
    event: SourceEvent,
    borrowed_events: Sequence[SourceEvent],
    *,
    max_gap: Fraction,
) -> bool:
    for other in borrowed_events:
        if other.source_id == event.source_id or other.part_index != event.part_index:
            continue
        gap_after = other.start - event.end
        gap_before = event.start - other.end
        if Fraction(0, 1) <= gap_after <= max_gap or Fraction(0, 1) <= gap_before <= max_gap:
            return True
    return False


def _prune_isolated_borrowed_events(
    selected: dict[str, list[SourceEvent]],
    initial_events_by_target: dict[str, Sequence[SourceEvent]],
    *,
    max_gap: Fraction = Fraction(1, 1),
) -> None:
    for target_id, initial_events in initial_events_by_target.items():
        initial_source_ids = {event.source_id for event in initial_events}
        borrowed_events = [
            event
            for event in selected[target_id]
            if event.source_id not in initial_source_ids
        ]
        if not borrowed_events:
            continue

        kept: list[SourceEvent] = []
        for event in selected[target_id]:
            if event.source_id in initial_source_ids or _has_borrowed_neighbor(event, borrowed_events, max_gap=max_gap):
                kept.append(event)
        selected[target_id] = kept


def _fit_events_to_target(
    events: Sequence[SourceEvent],
    target: TargetPart,
    config: ReductionConfig,
) -> list[SourceEvent]:
    if not config.enforce_ranges:
        return list(events)
    return [fit_event_to_range(event, *target.midi_range) for event in events]


def _extract_voice_events_for_target(
    source_part: stream.Stream,
    source_index: int,
    target: TargetPart,
) -> list[SourceEvent]:
    chord_policy = "bottom" if target.role == "bottom" else "top"
    return extract_events(source_part, source_index, include_rests=True, chord_policy=chord_policy)


def _ordered_source_indices_by_median(source_parts: Sequence[stream.Stream]) -> list[int]:
    medians = []
    for index, part in enumerate(source_parts):
        median = part_median_pitch(part)
        if median == median:
            medians.append((index, median))
    return [
        index
        for index, _median in sorted(medians, key=lambda item: item[1], reverse=True)
    ]


def _register_fit_score(target: TargetPart, midi_pitch: int, config: ReductionConfig) -> float:
    low, high = target.preferred_register or target.midi_range
    if low <= midi_pitch <= high:
        center = (low + high) / 2
        return abs(midi_pitch - center) / 100
    return min(abs(midi_pitch - low), abs(midi_pitch - high)) + 1


def _choose_single_target(
    event: SourceEvent,
    available: Sequence[TargetPart],
    last_pitch: dict[str, int | None],
    config: ReductionConfig,
) -> TargetPart:
    if event.pitch_midi is None:
        raise ValueError(f"Cannot assign unpitched event {event.source_id}.")
    if len(available) == 1:
        return available[0]

    midi_pitch = int(event.pitch_midi)
    if all(last_pitch[target.id] is None for target in available):
        if len(available) == 2:
            return available[0] if midi_pitch >= config.register_split else available[-1]
        return min(
            available,
            key=lambda target: (_register_fit_score(target, midi_pitch, config), available.index(target)),
        )

    empty_targets = [target for target in available if last_pitch[target.id] is None]
    if empty_targets:
        return min(
            empty_targets,
            key=lambda target: (_register_fit_score(target, midi_pitch, config), available.index(target)),
        )

    return min(
        available,
        key=lambda target: (abs(midi_pitch - int(last_pitch[target.id])), available.index(target)),
    )


def _assignment_cost(
    event: SourceEvent,
    target: TargetPart,
    *,
    candidate_rank: int,
    target_rank: int,
    last_pitch: dict[str, int | None],
    config: ReductionConfig,
) -> float:
    if event.pitch_midi is None:
        return float("inf")

    midi_pitch = int(event.pitch_midi)
    fitted_pitch = octave_fit(midi_pitch, *target.midi_range) if config.enforce_ranges else midi_pitch
    if fitted_pitch is None:
        return float("inf")

    previous = last_pitch[target.id]
    voice_cost = 0 if previous is None else abs(fitted_pitch - previous)
    order_cost = abs(candidate_rank - target_rank) if previous is None else 0
    range_cost = abs(fitted_pitch - midi_pitch) / 12
    register_cost = _register_fit_score(target, fitted_pitch, config)
    return voice_cost * 10 + order_cost * 3 + range_cost + register_cost / 10


def _match_events_to_targets(
    events: Sequence[SourceEvent],
    available: Sequence[TargetPart],
    last_pitch: dict[str, int | None],
    config: ReductionConfig,
    can_assign: Callable[[TargetPart, SourceEvent], bool] | None = None,
) -> list[tuple[TargetPart, SourceEvent]]:
    if not events:
        return []
    if len(events) == 1:
        assignable = [
            target
            for target in available
            if can_assign is None or can_assign(target, events[0])
        ]
        if not assignable:
            return []
        return [(_choose_single_target(events[0], assignable, last_pitch, config), events[0])]

    ranked_events = sorted(events, key=lambda ev: int(ev.pitch_midi), reverse=True)
    best_cost = float("inf")
    best_pairs: list[tuple[TargetPart, SourceEvent]] = []
    target_ranks = {target.id: index for index, target in enumerate(available)}

    for target_perm in permutations(available, len(ranked_events)):
        if can_assign is not None and any(
            not can_assign(target, event)
            for event, target in zip(ranked_events, target_perm, strict=True)
        ):
            continue
        cost = sum(
            _assignment_cost(
                event,
                target,
                candidate_rank=event_rank,
                target_rank=target_ranks[target.id],
                last_pitch=last_pitch,
                config=config,
            )
            for event_rank, (event, target) in enumerate(zip(ranked_events, target_perm, strict=True))
        )
        if cost < best_cost:
            best_cost = cost
            best_pairs = list(zip(target_perm, ranked_events, strict=True))

    return best_pairs


def _select_inner_events(
    middle_events: Sequence[SourceEvent],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
    targets: Sequence[TargetPart],
    config: ReductionConfig,
    *,
    initial_events_by_target: dict[str, Sequence[SourceEvent]] | None = None,
    allow_supporting_doublings: bool = False,
    support_lookahead: Fraction = Fraction(4, 1),
) -> dict[str, list[SourceEvent]]:
    initial_events_by_target = initial_events_by_target or {}
    selected: dict[str, list[SourceEvent]] = {
        target.id: list(initial_events_by_target.get(target.id, ()))
        for target in targets
    }
    borrowed_target_ids = set(initial_events_by_target)
    last_pitch: dict[str, int | None] = {target.id: None for target in targets}

    note_events = sorted(
        [event for event in middle_events if not event.is_rest and event.pitch_midi is not None],
        key=lambda ev: (ev.start, ev.end, ev.source_id),
    )
    events_by_part: dict[int, list[SourceEvent]] = {}
    for event in note_events:
        events_by_part.setdefault(event.part_index, []).append(event)

    for start, group_iter in groupby(note_events, key=lambda ev: ev.start):
        group = list(group_iter)
        last_pitch = {
            target.id: _latest_pitch_before(selected[target.id], start)
            for target in targets
        }

        active_output_pitches = _active_pitches_from_assignments(selected, start)
        outer_pitches = [active_pitch_at(top_events, start), active_pitch_at(bottom_events, start)]
        if not active_output_pitches:
            active_output_pitches = [pitch for pitch in outer_pitches if pitch is not None]
        covered = {pitch % 12 for pitch in active_output_pitches if pitch is not None}
        deduped = _dedupe_candidates(group)
        candidates = [
            event
            for event in deduped
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

        primary_chosen: list[SourceEvent] = []
        seen_pitch_classes = set(covered)
        chosen_source_ids: set[str] = set()
        for candidate in candidates:
            if len(primary_chosen) >= len(targets):
                break
            pc = candidate.pitch_midi % 12
            if pc in seen_pitch_classes:
                continue
            if not any(_target_is_free_for_event(target, candidate, selected) for target in targets):
                continue
            primary_chosen.append(candidate)
            chosen_source_ids.add(candidate.source_id)
            seen_pitch_classes.add(pc)

        nonborrowed_targets = [
            target
            for target in targets
            if target.id not in borrowed_target_ids
        ]
        nonborrowed_capacity = sum(
            1
            for target in nonborrowed_targets
            if any(_target_is_free_for_event(target, event, selected) for event in primary_chosen)
        )
        # Preserve newly exposed pitch classes on the regular inner targets when possible.
        # Borrowed outer targets are used only when inner capacity is genuinely exhausted.
        primary_target_pool = nonborrowed_targets if len(primary_chosen) <= nonborrowed_capacity else list(targets)

        primary_pairs: list[tuple[TargetPart, SourceEvent]] = []
        while primary_chosen:
            primary_pairs = _match_events_to_targets(
                primary_chosen,
                primary_target_pool,
                last_pitch,
                config,
                can_assign=lambda target, event: _target_is_free_for_event(target, event, selected),
            )
            if primary_pairs:
                break
            if primary_target_pool != list(targets):
                primary_target_pool = list(targets)
                continue
            primary_chosen.pop()

        for target, event in primary_pairs:
            if config.enforce_ranges:
                event = fit_event_to_range(event, *target.midi_range)
            selected[target.id].append(event)
            last_pitch[target.id] = event.pitch_midi

        if allow_supporting_doublings:
            supporting_candidates = [
                event
                for event in deduped
                if event.pitch_midi is not None
                and event.source_id not in chosen_source_ids
                and event.pitch_midi % 12 in covered
                and event.pitch_midi % 12 not in {chosen_event.pitch_midi % 12 for chosen_event in primary_chosen}
                and _has_nearby_uncovered_event(
                    event,
                    events_by_part,
                    top_events,
                    bottom_events,
                    lookahead=support_lookahead,
                )
            ]
            supporting_candidates.sort(
                key=lambda ev: (
                    not _is_new_onset(ev),
                    ev.start,
                    -ev.duration,
                    ev.source_id,
                )
            )
            # Supporting doublings are phrase glue for later coverage, so they may only
            # occupy borrowed outer targets after the primary coverage notes are placed.
            borrowed_targets = [
                target
                for target in targets
                if target.id in borrowed_target_ids
            ]
            supporting_chosen: list[SourceEvent] = []
            for candidate in supporting_candidates:
                if len(supporting_chosen) >= len(borrowed_targets):
                    break
                if not any(_target_is_free_for_event(target, candidate, selected) for target in borrowed_targets):
                    continue
                supporting_chosen.append(candidate)
                chosen_source_ids.add(candidate.source_id)

            support_pairs = _match_events_to_targets(
                supporting_chosen,
                borrowed_targets,
                last_pitch,
                config,
                can_assign=lambda target, event: _target_is_free_for_event(target, event, selected),
            )
            for target, event in support_pairs:
                if config.enforce_ranges:
                    event = fit_event_to_range(event, *target.midi_range)
                selected[target.id].append(event)
                last_pitch[target.id] = event.pitch_midi

    if initial_events_by_target:
        _prune_isolated_borrowed_events(selected, initial_events_by_target)

    return selected


class AssignmentPolicy:
    """Assign source events to target parts in an ensemble profile."""

    def assign(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
    ) -> dict[str, list[SourceEvent]]:
        raise NotImplementedError


class RegisterAssignmentPolicy(AssignmentPolicy):
    """Keep outer voices, borrowing their idle target parts for coverage passages."""

    def assign(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
    ) -> dict[str, list[SourceEvent]]:
        top_target = profile.top_part
        bottom_target = profile.bottom_part

        top_events = _fit_events_to_target(context.top_events, top_target, config)
        bottom_events = _fit_events_to_target(context.bottom_events, bottom_target, config)
        fixed_outer_events = {
            top_target.id: _pitched_events(top_events),
            bottom_target.id: _pitched_events(bottom_events),
        }

        assignments = _select_inner_events(
            context.middle_events,
            [event for event in top_events if not event.is_rest],
            [event for event in bottom_events if not event.is_rest],
            profile.parts,
            config,
            initial_events_by_target=fixed_outer_events,
            allow_supporting_doublings=True,
        )
        return assignments


class VoiceOrderAssignmentPolicy(AssignmentPolicy):
    """Map voices one-to-one by register when source and target counts match."""

    def __init__(self, fallback: AssignmentPolicy | None = None) -> None:
        self.fallback = fallback or RegisterAssignmentPolicy()

    def assign(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
    ) -> dict[str, list[SourceEvent]]:
        if len(context.source_parts) != len(profile.parts):
            return self.fallback.assign(context, profile, config)

        ordered_indices = _ordered_source_indices_by_median(context.source_parts)
        if len(ordered_indices) != len(profile.parts):
            return self.fallback.assign(context, profile, config)

        assignments: dict[str, list[SourceEvent]] = {}
        for target, source_index in zip(profile.parts, ordered_indices, strict=True):
            events = _extract_voice_events_for_target(context.source_parts[source_index], source_index, target)
            assignments[target.id] = _fit_events_to_target(events, target, config)
        return assignments


def _pitch_sweetspot_cost(target: TargetPart, midi_pitch: int) -> float:
    pref_low, pref_high = target.preferred_register or target.midi_range
    pref_center = (pref_low + pref_high) / 2
    pref_span = max(pref_high - pref_low, 1)
    center_cost = abs(midi_pitch - pref_center) / pref_span

    if midi_pitch < pref_low:
        register_cost = pref_low - midi_pitch
    elif midi_pitch > pref_high:
        register_cost = midi_pitch - pref_high
    else:
        register_cost = center_cost * 0.5

    return register_cost + center_cost


def _voice_sweetspot_cost(
    events: Sequence[SourceEvent],
    target: TargetPart,
    *,
    prefer_registers: bool = True,
) -> float:
    weighted_cost = 0.0
    total_weight = 0.0
    for event in events:
        if event.is_rest or event.pitch_midi is None:
            continue
        if prefer_registers:
            fitted_pitch = _preferred_register_fit(int(event.pitch_midi), target)
        else:
            fitted_pitch = octave_fit(int(event.pitch_midi), *target.midi_range)
        if fitted_pitch is None:
            continue
        weight = float(event.duration)
        octave_displacement_cost = abs(fitted_pitch - int(event.pitch_midi)) / 12
        weighted_cost += (_pitch_sweetspot_cost(target, fitted_pitch) + octave_displacement_cost * 3) * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return weighted_cost / total_weight


def _preferred_register_fit(
    midi_pitch: int | None,
    target: TargetPart,
    previous_pitch: int | None = None,
) -> int | None:
    if midi_pitch is None:
        return None
    candidates = octave_candidates(int(midi_pitch), *target.midi_range)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: (
            _pitch_sweetspot_cost(target, candidate)
            + abs(candidate - int(midi_pitch)) / 12 * 2
            + (0 if previous_pitch is None else abs(candidate - previous_pitch) / 12),
            abs(candidate - int(midi_pitch)),
        ),
    )


def _fit_events_to_preferred_register(
    events: Sequence[SourceEvent],
    target: TargetPart,
    config: ReductionConfig,
) -> list[SourceEvent]:
    if not config.enforce_ranges:
        return list(events)

    fitted_events: list[SourceEvent] = []
    previous_pitch: int | None = None
    for event in events:
        if event.is_rest or event.pitch_midi is None:
            fitted_events.append(event)
            continue
        fitted_pitch = _preferred_register_fit(event.pitch_midi, target, previous_pitch)
        fitted_event = replace(event, pitch_midi=fitted_pitch)
        fitted_events.append(fitted_event)
        previous_pitch = fitted_pitch
    return fitted_events


def _target_pitch_transposition_cost(target: TargetPart, transposed_pitch: int) -> float:
    fitted_pitch = _preferred_register_fit(transposed_pitch, target)
    if fitted_pitch is None:
        return 10_000.0
    octave_displacement = abs(fitted_pitch - transposed_pitch) / 12
    return _pitch_sweetspot_cost(target, fitted_pitch) + octave_displacement * 6


def _voice_transposition_cost(
    events: Sequence[SourceEvent],
    target: TargetPart,
    semitones: int,
) -> float:
    weighted_cost = 0.0
    total_weight = 0.0
    for event in events:
        if event.is_rest or event.pitch_midi is None:
            continue
        weight = float(event.duration)
        weighted_cost += _target_pitch_transposition_cost(target, int(event.pitch_midi) + semitones) * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return weighted_cost / total_weight


def _source_voice_groups_for_transposition(
    src_score: stream.Score,
    profile: EnsembleProfile,
    *,
    right_hand_voice_count: int | None = None,
) -> list[tuple[list[SourceEvent], TargetPart]]:
    parts = tuple(src_score.parts) if src_score.parts else (src_score,)
    ordered_indices = _ordered_source_indices_by_median(parts)
    if not ordered_indices:
        raise ValueError("Could not identify source voices; no pitched material found.")

    if profile is PIANO_REDUCTION or profile.name == PIANO_REDUCTION.name:
        if right_hand_voice_count is None:
            right_hand_voice_count = (len(ordered_indices) + 1) // 2
        right_hand_voice_count = max(1, min(len(ordered_indices), right_hand_voice_count))
        right_target = profile.target("pno_rh")
        left_target = profile.target("pno_lh")
        result: list[tuple[list[SourceEvent], TargetPart]] = []
        for source_index in ordered_indices[:right_hand_voice_count]:
            result.append((_extract_voice_events_for_target(parts[source_index], source_index, right_target), right_target))
        for source_index in ordered_indices[right_hand_voice_count:]:
            result.append((_extract_voice_events_for_target(parts[source_index], source_index, left_target), left_target))
        return result

    if len(ordered_indices) == len(profile.parts):
        return [
            (_extract_voice_events_for_target(parts[source_index], source_index, target), target)
            for target, source_index in zip(profile.parts, ordered_indices, strict=True)
        ]

    top_target = profile.top_part
    bottom_target = profile.bottom_part
    inner_targets = profile.inner_parts
    if not inner_targets:
        inner_targets = tuple(part for part in profile.parts if part.role not in {"top", "bottom"})
    result = [
        (_extract_voice_events_for_target(parts[ordered_indices[0]], ordered_indices[0], top_target), top_target),
    ]
    for source_index in ordered_indices[1:-1]:
        source_events = extract_events(parts[source_index], source_index, include_rests=True, chord_policy="top")
        if inner_targets:
            best_target = min(
                inner_targets,
                key=lambda target: _voice_transposition_cost(source_events, target, 0),
            )
        else:
            best_target = top_target
        result.append((source_events, best_target))
    result.append(
        (_extract_voice_events_for_target(parts[ordered_indices[-1]], ordered_indices[-1], bottom_target), bottom_target)
    )
    return result


def score_global_transposition(
    src_score: stream.Score,
    profile: EnsembleProfile,
    semitones: int,
    *,
    right_hand_voice_count: int | None = None,
) -> float:
    voice_groups = _source_voice_groups_for_transposition(
        src_score,
        profile,
        right_hand_voice_count=right_hand_voice_count,
    )
    weighted_score = 0.0
    total_weight = 0.0
    for events, target in voice_groups:
        voice_weight = sum(float(event.duration) for event in events if not event.is_rest and event.pitch_midi is not None)
        if voice_weight <= 0:
            continue
        weighted_score += _voice_transposition_cost(events, target, semitones) * voice_weight
        total_weight += voice_weight
    if total_weight == 0:
        return abs(semitones) * 0.01
    return weighted_score / total_weight + abs(semitones) * 0.01


def choose_global_transposition(
    src_score: stream.Score,
    profile: EnsembleProfile,
    *,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
    right_hand_voice_count: int | None = None,
) -> TranspositionChoice:
    if not candidate_semitones:
        raise ValueError("candidate_semitones must not be empty.")
    candidate_scores = tuple(
        (int(semitones), score_global_transposition(
            src_score,
            profile,
            int(semitones),
            right_hand_voice_count=right_hand_voice_count,
        ))
        for semitones in candidate_semitones
    )
    best_semitones, best_score = min(candidate_scores, key=lambda item: (item[1], abs(item[0]), item[0]))
    return TranspositionChoice(
        semitones=best_semitones,
        score=best_score,
        candidate_scores=candidate_scores,
    )


def _transpose_score_for_reduction(
    src_score: stream.Score,
    profile: EnsembleProfile,
    semitones: int | None,
    *,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
    right_hand_voice_count: int | None = None,
) -> tuple[stream.Score, int]:
    if semitones is None:
        semitones = choose_global_transposition(
            src_score,
            profile,
            candidate_semitones=candidate_semitones,
            right_hand_voice_count=right_hand_voice_count,
        ).semitones
    return (src_score.transpose(semitones) if semitones else src_score, int(semitones))


def _inversion_count(values: Sequence[int]) -> int:
    count = 0
    for left_index, left in enumerate(values):
        for right in values[left_index + 1:]:
            if left > right:
                count += 1
    return count


class SweetSpotAssignmentPolicy(AssignmentPolicy):
    """Map equal voice/target counts by instrumental sweet spots while preserving outer voices."""

    def __init__(
        self,
        fallback: AssignmentPolicy | None = None,
        *,
        preserve_outer_voices: bool = True,
        prefer_registers: bool = True,
        order_weight: float = 1.0,
        crossing_weight: float = 2.0,
    ) -> None:
        self.fallback = fallback or VoiceOrderAssignmentPolicy()
        self.preserve_outer_voices = preserve_outer_voices
        self.prefer_registers = prefer_registers
        self.order_weight = order_weight
        self.crossing_weight = crossing_weight

    def assign(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
    ) -> dict[str, list[SourceEvent]]:
        if len(context.source_parts) != len(profile.parts):
            return self.fallback.assign(context, profile, config)

        ordered_indices = _ordered_source_indices_by_median(context.source_parts)
        if len(ordered_indices) != len(profile.parts):
            return self.fallback.assign(context, profile, config)

        if not self.preserve_outer_voices:
            return self._assign_all_targets(context, profile, config, ordered_indices)

        top_target = profile.top_part
        bottom_target = profile.bottom_part
        middle_sources = ordered_indices[1:-1]
        middle_targets = list(profile.inner_parts)
        if len(middle_sources) != len(middle_targets):
            return self.fallback.assign(context, profile, config)

        source_events = {
            source_index: _extract_voice_events_for_target(
                context.source_parts[source_index],
                source_index,
                top_target,
            )
            for source_index in middle_sources
        }

        target_positions = {target.id: index for index, target in enumerate(middle_targets)}
        best_cost = float("inf")
        best_pairs: list[tuple[TargetPart, int]] = []
        for target_perm in permutations(middle_targets):
            target_position_sequence = [target_positions[target.id] for target in target_perm]
            cost = _inversion_count(target_position_sequence) * self.crossing_weight
            for source_rank, (source_index, target) in enumerate(zip(middle_sources, target_perm, strict=True)):
                cost += _voice_sweetspot_cost(
                    source_events[source_index],
                    target,
                    prefer_registers=self.prefer_registers,
                )
                cost += abs(source_rank - target_positions[target.id]) * self.order_weight
            if cost < best_cost:
                best_cost = cost
                best_pairs = list(zip(target_perm, middle_sources, strict=True))

        pairs = [
            (top_target, ordered_indices[0]),
            *best_pairs,
            (bottom_target, ordered_indices[-1]),
        ]
        return self._build_assignments(context, profile, config, pairs)

    def _assign_all_targets(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
        ordered_indices: Sequence[int],
    ) -> dict[str, list[SourceEvent]]:
        source_events = {
            source_index: _extract_voice_events_for_target(
                context.source_parts[source_index],
                source_index,
                profile.parts[0],
            )
            for source_index in ordered_indices
        }
        target_positions = {target.id: index for index, target in enumerate(profile.parts)}
        best_cost = float("inf")
        best_pairs: list[tuple[TargetPart, int]] = []
        for target_perm in permutations(profile.parts):
            target_position_sequence = [target_positions[target.id] for target in target_perm]
            cost = _inversion_count(target_position_sequence) * self.crossing_weight
            for source_rank, (source_index, target) in enumerate(zip(ordered_indices, target_perm, strict=True)):
                cost += _voice_sweetspot_cost(
                    source_events[source_index],
                    target,
                    prefer_registers=self.prefer_registers,
                )
                cost += abs(source_rank - target_positions[target.id]) * self.order_weight
            if cost < best_cost:
                best_cost = cost
                best_pairs = list(zip(target_perm, ordered_indices, strict=True))
        return self._build_assignments(context, profile, config, best_pairs)

    def _build_assignments(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
        target_source_pairs: Sequence[tuple[TargetPart, int]],
    ) -> dict[str, list[SourceEvent]]:
        assignments: dict[str, list[SourceEvent]] = {part.id: [] for part in profile.parts}
        for target, source_index in target_source_pairs:
            events = _extract_voice_events_for_target(context.source_parts[source_index], source_index, target)
            if self.prefer_registers:
                assignments[target.id] = _fit_events_to_preferred_register(events, target, config)
            else:
                assignments[target.id] = _fit_events_to_target(events, target, config)
        return assignments


def select_middle_events(
    middle_events: Sequence[SourceEvent],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
) -> tuple[list[SourceEvent], list[SourceEvent]]:
    """Select real middle-note events for Violin II and Viola."""
    selected = _select_inner_events(
        middle_events,
        top_events,
        bottom_events,
        STRING_QUARTET.inner_parts,
        ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
    )
    return selected["vln2"], selected["vla"]


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


class ReductionBuilder:
    """Build a measured reduction from an ensemble profile and assignment policy."""

    def __init__(
        self,
        profile: EnsembleProfile,
        *,
        config: ReductionConfig | None = None,
        policy: AssignmentPolicy | None = None,
    ) -> None:
        self.profile = profile
        self.config = config or ReductionConfig()
        self.policy = policy or RegisterAssignmentPolicy()

    def build_context(self, src_score: stream.Score) -> ReductionContext:
        bars = tuple(build_bar_map(src_score))
        if not bars:
            raise ValueError("Could not derive any source bars.")

        parts = tuple(src_score.parts) if src_score.parts else (src_score,)
        if len(parts) < self.profile.minimum_source_parts:
            raise ValueError(
                f"Expected at least {self.profile.minimum_source_parts} parts for "
                f"{self.profile.name}; found {len(parts)}."
            )

        top_index, bottom_index = identify_outer_parts(parts)
        middle_indices = tuple(index for index in range(len(parts)) if index not in (top_index, bottom_index))
        key_signatures = collect_key_signatures(src_score, bars)

        top_events = tuple(extract_events(parts[top_index], top_index, include_rests=True, chord_policy="top"))
        bottom_events = tuple(extract_events(parts[bottom_index], bottom_index, include_rests=True, chord_policy="bottom"))
        middle_events = tuple(
            event
            for index in middle_indices
            for event in extract_events(parts[index], index, include_rests=False, chord_policy="all")
        )

        return ReductionContext(
            source_score=src_score,
            source_parts=parts,
            bars=bars,
            top_index=top_index,
            bottom_index=bottom_index,
            middle_indices=middle_indices,
            key_signatures=key_signatures,
            top_events=top_events,
            bottom_events=bottom_events,
            middle_events=middle_events,
        )

    def build_score(self, src_score: stream.Score) -> stream.Score:
        context = self.build_context(src_score)
        assignments = self.policy.assign(context, self.profile, self.config)

        out = stream.Score()
        out.insert(0, metadata.Metadata())
        if src_score.metadata:
            out.metadata.title = ((src_score.metadata.title or "") + f" - {self.profile.title_suffix}").strip(" -")
            out.metadata.composer = src_score.metadata.composer

        for target in self.profile.parts:
            measured_part = build_measured_part(
                assignments.get(target.id, []),
                context.bars,
                part_name=target.name,
                instrument_obj=target.make_instrument(),
                clef_obj=target.make_clef(),
                key_signatures=context.key_signatures,
            )
            out.insert(0, measured_part)

        copy_top_staff_markings(src_score, out, context.bars)
        validate_score_measures(out, context.bars)
        return out


def build_ensemble_score(
    src_score: stream.Score,
    profile: EnsembleProfile = STRING_QUARTET,
    *,
    config: ReductionConfig | None = None,
    policy: AssignmentPolicy | None = None,
) -> stream.Score:
    return ReductionBuilder(profile, config=config, policy=policy).build_score(src_score)


def build_piano_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    right_hand_voice_count: int | None = None,
    prefer_hand_registers: bool = False,
) -> stream.Score:
    bars = build_bar_map(src_score)
    if not bars:
        raise ValueError("Could not derive any source bars.")

    parts = tuple(src_score.parts) if src_score.parts else (src_score,)
    ordered_indices = _ordered_source_indices_by_median(parts)
    if not ordered_indices:
        raise ValueError("Could not identify source voices; no pitched material found.")

    if right_hand_voice_count is None:
        right_hand_voice_count = (len(ordered_indices) + 1) // 2
    right_hand_voice_count = max(1, min(len(ordered_indices), right_hand_voice_count))

    right_target = PIANO_REDUCTION.target("pno_rh")
    left_target = PIANO_REDUCTION.target("pno_lh")
    config = ReductionConfig(enforce_ranges=enforce_ranges)
    key_signatures = collect_key_signatures(src_score, bars)

    def voice_groups(source_indices: Sequence[int], target: TargetPart) -> list[list[SourceEvent]]:
        groups: list[list[SourceEvent]] = []
        for source_index in source_indices:
            events = _extract_voice_events_for_target(parts[source_index], source_index, target)
            if prefer_hand_registers:
                events = _fit_events_to_preferred_register(events, target, config)
            else:
                events = _fit_events_to_target(events, target, config)
            groups.append(events)
        return groups

    right_indices = ordered_indices[:right_hand_voice_count]
    left_indices = ordered_indices[right_hand_voice_count:]
    right_staff = build_measured_piano_staff(
        voice_groups(right_indices, right_target),
        bars,
        target=right_target,
        key_signatures=key_signatures,
    )
    left_staff = build_measured_piano_staff(
        voice_groups(left_indices, left_target),
        bars,
        target=left_target,
        key_signatures=key_signatures,
    )

    out = stream.Score()
    out.insert(0, metadata.Metadata())
    if src_score.metadata:
        out.metadata.title = ((src_score.metadata.title or "") + f" - {PIANO_REDUCTION.title_suffix}").strip(" -")
        out.metadata.composer = src_score.metadata.composer

    out.insert(0, right_staff)
    out.insert(0, left_staff)
    out.insert(
        0,
        layout.StaffGroup(
            [right_staff, left_staff],
            name="Piano",
            abbreviation="Pno.",
            symbol="brace",
        ),
    )

    copy_top_staff_markings(src_score, out, bars)
    validate_piano_score_measures(out, bars)
    return out


def build_quartet_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
) -> stream.Score:
    return build_ensemble_score(
        src_score,
        STRING_QUARTET,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=RegisterAssignmentPolicy(),
    )


def build_quartet_plus_viole_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    one_to_one_when_possible: bool = True,
) -> stream.Score:
    policy: AssignmentPolicy
    if one_to_one_when_possible:
        policy = VoiceOrderAssignmentPolicy()
    else:
        policy = RegisterAssignmentPolicy()
    return build_ensemble_score(
        src_score,
        QUARTET_PLUS_VIOLE,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=policy,
    )


def build_quartet_plus_viole_sweetspot_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    prefer_registers: bool = True,
    order_weight: float = 1.0,
    crossing_weight: float = 2.0,
) -> stream.Score:
    return build_ensemble_score(
        src_score,
        QUARTET_PLUS_VIOLE,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=SweetSpotAssignmentPolicy(
            prefer_registers=prefer_registers,
            order_weight=order_weight,
            crossing_weight=crossing_weight,
        ),
    )


def reduce_to_ensemble(
    midi_path: str | Path,
    profile: EnsembleProfile = STRING_QUARTET,
    semitones: int | None = None,
    out_path: str | Path = OUT_PATH,
    *,
    config: ReductionConfig | None = None,
    policy: AssignmentPolicy | None = None,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    src_score = converter.parse(midi_path)
    src_score, chosen_semitones = _transpose_score_for_reduction(
        src_score,
        profile,
        semitones,
        candidate_semitones=candidate_semitones,
    )
    out_score = build_ensemble_score(src_score, profile, config=config, policy=policy)
    out_score.editorial.globalTransposition = chosen_semitones
    out_score.write("musicxml", fp=str(out_path))
    print(f"Written: {out_path} (semitones={chosen_semitones})")
    return out_score


def reduce_to_quartet(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = OUT_PATH,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    return reduce_to_ensemble(
        midi_path,
        STRING_QUARTET,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=RegisterAssignmentPolicy(),
        candidate_semitones=candidate_semitones,
    )


def reduce_to_quartet_plus_viole(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = "gesualdo_quartet_plus_viole.musicxml",
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    one_to_one_when_possible: bool = True,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    policy: AssignmentPolicy
    if one_to_one_when_possible:
        policy = VoiceOrderAssignmentPolicy()
    else:
        policy = RegisterAssignmentPolicy()
    return reduce_to_ensemble(
        midi_path,
        QUARTET_PLUS_VIOLE,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=policy,
        candidate_semitones=candidate_semitones,
    )


def reduce_to_quartet_plus_viole_sweetspot(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = "gesualdo_quartet_plus_viole_sweetspot.musicxml",
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    prefer_registers: bool = True,
    order_weight: float = 1.0,
    crossing_weight: float = 2.0,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    return reduce_to_ensemble(
        midi_path,
        QUARTET_PLUS_VIOLE,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(enforce_ranges=enforce_ranges, register_split=register_split),
        policy=SweetSpotAssignmentPolicy(
            prefer_registers=prefer_registers,
            order_weight=order_weight,
            crossing_weight=crossing_weight,
        ),
        candidate_semitones=candidate_semitones,
    )


def reduce_to_piano(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = "gesualdo_piano_reduction.musicxml",
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    right_hand_voice_count: int | None = None,
    prefer_hand_registers: bool = False,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    src_score = converter.parse(midi_path)
    src_score, chosen_semitones = _transpose_score_for_reduction(
        src_score,
        PIANO_REDUCTION,
        semitones,
        candidate_semitones=candidate_semitones,
        right_hand_voice_count=right_hand_voice_count,
    )
    out_score = build_piano_score(
        src_score,
        enforce_ranges=enforce_ranges,
        right_hand_voice_count=right_hand_voice_count,
        prefer_hand_registers=prefer_hand_registers,
    )
    out_score.editorial.globalTransposition = chosen_semitones
    out_score.write("musicxml", fp=str(out_path))
    print(f"Written: {out_path} (semitones={chosen_semitones})")
    return out_score
