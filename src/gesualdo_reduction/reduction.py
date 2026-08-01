"""Rhythm-first madrigal-to-string-ensemble reduction helpers.

The reducer in this module is deliberately conservative: selected output notes
are copied from real source note events, then split only where source barlines
require it.  It does not build rhythms from a global onset/offset grid.
"""

from __future__ import annotations

import copy
import re
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
    duration as m21duration,
    dynamics,
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
KEY_SIGNATURE_TESSITURA_TOLERANCE = 0.05
KEY_SIGNATURE_MIN_ABS_IMPROVEMENT = 2.0
KEY_SIGNATURE_MIN_REL_IMPROVEMENT = 0.40
DEFAULT_REDUCTION_COMPOSER = "F. Pachet and AI"
TAKE6_REDUCTION_COMPOSER = "Take 6, arrangement F. Pachet and AI"
TITLE_SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "de", "du", "et", "for", "in", "of", "on", "or", "the", "to"}

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
    preserve_active_voice_count: bool = False
    add_editorial_harmony: bool = False
    add_editorial_thirds: bool = False
    editorial_harmony_target_active_parts: int = 4
    prefer_jazz_color_tones: bool = False
    add_source_double_stops: bool = False
    normalize_short_note_rest_artifacts: bool = False
    min_preserved_trimmed_duration: Fraction | None = None
    max_borrowed_bottom_duplicate_pitch: int | None = None
    max_borrowed_bottom_pitch: int | None = None
    lower_high_cello_threshold: int | None = None
    smooth_isolated_handoffs: bool = True
    smooth_isolated_handoff_max_duration: Fraction = Fraction(1, 4)
    smooth_isolated_handoff_double_stops: bool = True
    smooth_isolated_handoff_trim_overlaps: bool = True
    add_editorial_dynamics: bool = True
    dynamic_phrase_bars: int = 4
    dynamic_hairpin_bars: int = 2


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


@dataclass(frozen=True)
class _DynamicPoint:
    """A bar-start editorial dynamic mark."""

    bar_index: int
    level: int


def viole_damour_instrument() -> instrument.Instrument:
    """Create a generic music21 instrument entry for viole d'amour."""

    inst = instrument.Instrument()
    inst.instrumentName = "Viole d'amour"
    inst.instrumentAbbreviation = "Vle. d'am."
    return inst


STRING_QUARTET = EnsembleProfile(
    name="string_quartet",
    title_suffix="Reduction for String Quartet",
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
    title_suffix="Reduction for String Quartet + Viole d'amour",
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
    title_suffix="Reduction for Piano",
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


def title_from_source_path(source_path: str | Path) -> str:
    stem = Path(source_path).stem
    if "__" in stem:
        stem = stem.split("__", 1)[0]
    title = stem.replace("_", " ").strip()
    title = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", title)
    title = re.sub(r"^\d+\s+", "", title)
    title = re.sub(r"\s*,?\s*originalrevu$", "", title, flags=re.IGNORECASE)
    title = title.strip() or Path(source_path).stem
    words = title.split()
    cased_words = [
        word.lower() if index > 0 and word.lower() in TITLE_SMALL_WORDS else word[:1].upper() + word[1:]
        for index, word in enumerate(words)
    ]
    return " ".join(cased_words)


def source_score_title(src_score: stream.Score) -> str:
    if src_score.metadata and src_score.metadata.title:
        return str(src_score.metadata.title).strip()
    return ""


def reduction_title(source_title: str, profile: EnsembleProfile) -> str:
    source_title = source_title.strip()
    return f"{source_title} - {profile.title_suffix}" if source_title else profile.title_suffix


def set_reduction_metadata(
    out_score: stream.Score,
    src_score: stream.Score,
    profile: EnsembleProfile,
    *,
    source_title: str | None = None,
    composer: str = DEFAULT_REDUCTION_COMPOSER,
) -> None:
    out_score.insert(0, metadata.Metadata())
    title = source_title or source_score_title(src_score)
    out_score.metadata.title = reduction_title(title, profile)
    out_score.metadata.composer = composer


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


def _part_measure_time_signature_count(part: stream.Part) -> int:
    return sum(
        1
        for ts_obj in part.recurse().getElementsByClass(meter.TimeSignature)
        if ql_to_fraction(ts_obj.getOffsetInHierarchy(part)) > 0
    )


def build_bar_map(src_score: stream.Score) -> list[Bar]:
    """Build authoritative bar boundaries from the source measure structure."""

    measured = src_score.makeMeasures(inPlace=False)
    measured_parts = list(measured.parts) if measured.parts else [measured]
    authoritative_part = max(
        measured_parts,
        key=lambda part: (_part_measure_time_signature_count(part), len(list(part.getElementsByClass(stream.Measure)))),
    )
    if _part_measure_time_signature_count(authoritative_part) > 0:
        measured_parts = [authoritative_part]
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


_ARTIFACT_NOTE_REST_TOTAL = Fraction(1, 1)
_ARTIFACT_ALLOWED_DENOMINATORS = {1, 2, 3, 4, 6, 8}
_ARTIFACT_SNAP_DURATIONS = (
    Fraction(1, 4),
    Fraction(1, 3),
    Fraction(1, 2),
    Fraction(2, 3),
    Fraction(3, 4),
)
_ARTIFACT_MAX_SNAP_DELTA = Fraction(1, 12)


def _nearest_artifact_snap_duration(duration: Fraction) -> Fraction | None:
    candidate = min(
        _ARTIFACT_SNAP_DURATIONS,
        key=lambda value: (abs(value - duration), value.denominator, value),
    )
    if abs(candidate - duration) > _ARTIFACT_MAX_SNAP_DELTA:
        return None
    return candidate


def normalize_short_note_rest_artifacts(events: Sequence[SourceEvent]) -> list[SourceEvent]:
    """Snap isolated MIDI-ish note+rest fragments such as 5/12+7/12 to simpler values."""

    ordered = sorted(events, key=lambda event: (event.start, event.event_index, event.source_id))
    normalized: list[SourceEvent] = []
    index = 0
    while index < len(ordered):
        event = ordered[index]
        next_event = ordered[index + 1] if index + 1 < len(ordered) else None
        following_event = ordered[index + 2] if index + 2 < len(ordered) else None
        if (
            next_event is not None
            and event.part_index == next_event.part_index
            and not event.is_rest
            and event.pitch_midi is not None
            and not next_event.is_rest
            and next_event.pitch_midi is not None
            and event.start < next_event.start < event.end
            and event.end - next_event.start <= _ARTIFACT_MAX_SNAP_DELTA
        ):
            normalized.append(replace(event, duration=next_event.start - event.start))
            index += 1
            continue
        if (
            next_event is not None
            and following_event is not None
            and event.part_index == next_event.part_index == following_event.part_index
            and not event.is_rest
            and event.pitch_midi is not None
            and next_event.is_rest
            and not following_event.is_rest
            and following_event.pitch_midi is not None
            and event.end == next_event.start
            and next_event.end == following_event.start
            and next_event.duration <= _ARTIFACT_MAX_SNAP_DELTA
        ):
            normalized.append(event)
            normalized.append(
                replace(
                    following_event,
                    start=next_event.start,
                    duration=following_event.duration + next_event.duration,
                )
            )
            index += 3
            continue
        if (
            next_event is not None
            and event.part_index == next_event.part_index
            and not event.is_rest
            and event.pitch_midi is not None
            and next_event.is_rest
            and event.end == next_event.start
            and event.duration + next_event.duration == _ARTIFACT_NOTE_REST_TOTAL
            and (
                event.duration.denominator not in _ARTIFACT_ALLOWED_DENOMINATORS
                or next_event.duration.denominator not in _ARTIFACT_ALLOWED_DENOMINATORS
            )
        ):
            snapped_duration = _nearest_artifact_snap_duration(event.duration)
            if snapped_duration is not None and Fraction(0, 1) < snapped_duration < _ARTIFACT_NOTE_REST_TOTAL:
                normalized.append(replace(event, duration=snapped_duration))
                normalized.append(
                    replace(
                        next_event,
                        start=event.start + snapped_duration,
                        duration=_ARTIFACT_NOTE_REST_TOTAL - snapped_duration,
                    )
                )
                index += 2
                continue
        normalized.append(event)
        index += 1
    return sorted(normalized, key=lambda event: (event.start, event.end, event.source_id))


def _extract_context_events(
    part: stream.Part,
    part_index: int,
    *,
    include_rests: bool,
    chord_policy: str,
    config: ReductionConfig,
) -> list[SourceEvent]:
    events = extract_events(
        part,
        part_index,
        include_rests=include_rests or config.normalize_short_note_rest_artifacts,
        chord_policy=chord_policy,
    )
    if config.normalize_short_note_rest_artifacts:
        events = normalize_short_note_rest_artifacts(events)
    if not include_rests:
        events = [event for event in events if not event.is_rest]
    return events


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


_DYNAMIC_NAMES = ("p", "mp", "mf", "f")


def _normalize_series(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high == low:
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _smoothed_profile(values: Sequence[float]) -> list[float]:
    if len(values) < 3:
        return list(values)
    smoothed: list[float] = []
    for index, value in enumerate(values):
        previous_value = values[index - 1] if index > 0 else value
        next_value = values[index + 1] if index + 1 < len(values) else value
        smoothed.append(0.25 * previous_value + 0.5 * value + 0.25 * next_value)
    return smoothed


def editorial_dynamic_energy_profile(score: stream.Score, bars: Sequence[Bar]) -> list[float]:
    """Estimate a coarse phrase-level intensity curve from the reduced score."""

    if not bars:
        return []
    parts = list(score.parts)
    if not parts:
        return []

    measures_by_part = [list(part.getElementsByClass(stream.Measure)) for part in parts]
    active_counts: list[float] = []
    attack_counts: list[float] = []
    average_pitches: list[float] = []
    spans: list[float] = []

    for bar in bars:
        pitches: list[int] = []
        attack_count = 0
        active_count = 0
        for measures in measures_by_part:
            if bar.index >= len(measures):
                continue
            notes = list(measures[bar.index].notes)
            if notes:
                active_count += 1
            for element in notes:
                if isinstance(element, chord.Chord):
                    pitches.extend(int(pitch.midi) for pitch in element.pitches)
                elif isinstance(element, note.Note):
                    pitches.append(int(element.pitch.midi))
                tie_type = getattr(getattr(element, "tie", None), "type", None)
                if tie_type not in {"stop", "continue"}:
                    attack_count += 1

        active_counts.append(active_count / max(len(parts), 1))
        attack_counts.append(float(attack_count))
        if pitches:
            average_pitches.append(sum(pitches) / len(pitches))
            spans.append(float(max(pitches) - min(pitches)))
        else:
            average_pitches.append(0.0)
            spans.append(0.0)

    normalized_attacks = _normalize_series(attack_counts)
    normalized_register = _normalize_series(average_pitches)
    normalized_spans = _normalize_series(spans)
    raw_profile = [
        (0.35 * active) + (0.30 * attacks) + (0.20 * register) + (0.15 * span)
        for active, attacks, register, span in zip(
            active_counts,
            normalized_attacks,
            normalized_register,
            normalized_spans,
            strict=True,
        )
    ]
    return _smoothed_profile(raw_profile)


def _dynamic_level_for_normalized_energy(value: float) -> int:
    if value < 0.32:
        return 0
    if value < 0.58:
        return 1
    if value < 0.83:
        return 2
    return 3


def _dynamic_levels_for_profile(profile: Sequence[float]) -> list[int]:
    normalized = _normalize_series(profile)
    return [_dynamic_level_for_normalized_energy(value) for value in normalized]


def _coalesce_dynamic_points(points: Sequence[_DynamicPoint]) -> list[_DynamicPoint]:
    by_bar: dict[int, int] = {}
    for point in points:
        by_bar[point.bar_index] = max(0, min(point.level, len(_DYNAMIC_NAMES) - 1))

    coalesced: list[_DynamicPoint] = []
    for bar_index in sorted(by_bar):
        level = by_bar[bar_index]
        if coalesced and coalesced[-1].level == level:
            continue
        coalesced.append(_DynamicPoint(bar_index, level))
    return coalesced


def _avoid_final_diminuendo(points: Sequence[_DynamicPoint]) -> list[_DynamicPoint]:
    adjusted = list(points)
    if len(adjusted) < 2:
        return adjusted
    previous = adjusted[-2]
    final = adjusted[-1]
    if final.level >= previous.level:
        return adjusted
    final_level = min(previous.level + 1, len(_DYNAMIC_NAMES) - 1)
    if final_level == previous.level:
        return adjusted[:-1]
    adjusted[-1] = _DynamicPoint(final.bar_index, final_level)
    return adjusted


def _editorial_dynamic_points(profile: Sequence[float], phrase_bars: int) -> list[_DynamicPoint]:
    if not profile:
        return []
    if len(profile) == 1:
        return [_DynamicPoint(0, 1)]

    phrase_bars = max(2, phrase_bars)
    raw_points: list[_DynamicPoint] = []
    bar_count = len(profile)
    levels = _dynamic_levels_for_profile(profile)

    for start in range(0, bar_count, phrase_bars):
        end = min(bar_count - 1, start + phrase_bars - 1)
        if start >= end:
            continue
        start_level = levels[start]
        end_level = levels[end]
        peak = max(range(start, end + 1), key=lambda index: profile[index])
        peak_level = levels[peak]

        raw_points.append(_DynamicPoint(start, start_level))
        if peak not in {start, end}:
            contrast = profile[peak] - max(profile[start], profile[end])
            if contrast >= 0.08 and peak_level <= max(start_level, end_level):
                peak_level = min(max(start_level, end_level) + 1, len(_DYNAMIC_NAMES) - 1)
            if peak_level > start_level or peak_level > end_level:
                raw_points.append(_DynamicPoint(peak, peak_level))
        raw_points.append(_DynamicPoint(end, end_level))

    if not raw_points:
        raw_points.append(_DynamicPoint(0, levels[0]))
    return _avoid_final_diminuendo(_coalesce_dynamic_points(raw_points))


def _insert_dynamic_mark(part: stream.Part, bars: Sequence[Bar], point: _DynamicPoint) -> None:
    measures = list(part.getElementsByClass(stream.Measure))
    if point.bar_index >= len(measures):
        return
    mark = dynamics.Dynamic(_DYNAMIC_NAMES[point.level])
    mark.placement = "below"
    measures[point.bar_index].insert(0, mark)


def _first_note_between(part: stream.Part, start: Fraction, end: Fraction) -> note.GeneralNote | None:
    candidates = []
    for element in part.recurse().notes:
        element_offset = absolute_offset(element, part)
        if start <= element_offset < end:
            candidates.append((element_offset, element))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def _insert_dynamic_hairpin(
    score: stream.Score,
    part: stream.Part,
    bars: Sequence[Bar],
    start: _DynamicPoint,
    end: _DynamicPoint,
    max_hairpin_bars: int,
) -> None:
    if start.level == end.level or start.bar_index >= len(bars) or end.bar_index >= len(bars):
        return
    max_hairpin_bars = max(1, max_hairpin_bars)
    hairpin_start_index = max(start.bar_index, end.bar_index - max_hairpin_bars)
    start_offset = bars[hairpin_start_index].start
    end_offset = bars[end.bar_index].start
    if end_offset <= start_offset:
        return
    end_bar = bars[end.bar_index]
    start_note = _first_note_between(part, start_offset, end_offset)
    end_note = _first_note_between(part, end_offset, end_bar.end)
    if start_note is None or end_note is None or start_note is end_note:
        return

    hairpin = dynamics.Crescendo() if end.level > start.level else dynamics.Diminuendo()
    hairpin.placement = "below"
    hairpin.addSpannedElements([start_note, end_note])
    score.insert(0, hairpin)


def add_editorial_dynamics(
    score: stream.Score,
    bars: Sequence[Bar],
    *,
    phrase_bars: int = 4,
    max_hairpin_bars: int = 2,
) -> None:
    """Add conservative visible dynamics and hairpins for MuseScore playback/export."""

    if not score.parts or not bars:
        return
    profile = editorial_dynamic_energy_profile(score, bars)
    points = _editorial_dynamic_points(profile, phrase_bars)
    if not points:
        return

    for part in score.parts:
        for point in points:
            _insert_dynamic_mark(part, bars, point)
        for start, end in zip(points, points[1:], strict=False):
            _insert_dynamic_hairpin(score, part, bars, start, end, max_hairpin_bars)


_MUSESCORE_SAFE_RHYTHM_PATTERNS: tuple[tuple[tuple[Fraction, ...], tuple[Fraction, ...]], ...] = (
    ((Fraction(5, 12), Fraction(1, 3)), (Fraction(1, 2), Fraction(1, 4))),
    ((Fraction(5, 12), Fraction(7, 12)), (Fraction(1, 2), Fraction(1, 2))),
    ((Fraction(17, 12), Fraction(13, 12)), (Fraction(3, 2), Fraction(1, 1))),
    (
        (Fraction(7, 6), Fraction(2, 3), Fraction(1, 3), Fraction(1, 3)),
        (Fraction(1, 1), Fraction(1, 2), Fraction(1, 2), Fraction(1, 2)),
    ),
)
_MUSESCORE_GRID_DURATION = Fraction(1, 4)
_MUSESCORE_GRID_MAX_DELTA = Fraction(1, 3)
_MUSESCORE_GRID_SAFE_DENOMINATORS = {1, 2, 4, 8, 16, 32, 64}


def _measure_note_groups(measure: stream.Measure) -> list[list[note.GeneralNote]]:
    by_offset: dict[Fraction, list[note.GeneralNote]] = {}
    for element in measure.notesAndRests:
        by_offset.setdefault(ql_to_fraction(element.offset), []).append(element)
    return [by_offset[offset] for offset in sorted(by_offset)]


def _group_duration(group: Sequence[note.GeneralNote]) -> Fraction | None:
    durations = {ql_to_fraction(element.quarterLength) for element in group}
    if len(durations) != 1:
        return None
    return next(iter(durations))


def _rewrite_measure_group_durations(
    measure: stream.Measure,
    groups: Sequence[Sequence[note.GeneralNote]],
    start_index: int,
    durations: Sequence[Fraction],
) -> None:
    cursor = ql_to_fraction(groups[start_index][0].offset)
    for group, new_duration in zip(groups[start_index : start_index + len(durations)], durations, strict=True):
        for element in group:
            measure.setElementOffset(element, fraction_to_ql(cursor))
            element.duration = m21duration.Duration(fraction_to_ql(new_duration))
        cursor += new_duration


def normalize_musescore_rhythm_artifacts(score: stream.Score) -> int:
    """Rewrite tiny Take 6 residues that MuseScore imports as overfull bars."""

    changes = 0
    for part in score.parts:
        for measure in part.getElementsByClass(stream.Measure):
            groups = _measure_note_groups(measure)
            index = 0
            while index < len(groups):
                matched = False
                for old_durations, new_durations in _MUSESCORE_SAFE_RHYTHM_PATTERNS:
                    span = len(old_durations)
                    if index + span > len(groups):
                        continue
                    current = tuple(_group_duration(group) for group in groups[index : index + span])
                    if current != old_durations:
                        continue
                    _rewrite_measure_group_durations(measure, groups, index, new_durations)
                    changes += 1
                    index += span
                    matched = True
                    break
                if not matched:
                    index += 1
    return changes


def _is_musescore_grid_safe_duration(duration_value: Fraction) -> bool:
    return duration_value.denominator in _MUSESCORE_GRID_SAFE_DENOMINATORS


def _musescore_grid_candidates(duration_value: Fraction, total: Fraction) -> list[Fraction]:
    candidates: set[Fraction] = set()
    if _is_musescore_grid_safe_duration(duration_value):
        candidates.add(duration_value)
    steps = int(total / _MUSESCORE_GRID_DURATION)
    for step in range(1, steps + 1):
        candidate = step * _MUSESCORE_GRID_DURATION
        if abs(candidate - duration_value) <= _MUSESCORE_GRID_MAX_DELTA:
            candidates.add(candidate)
    return sorted(candidates, key=lambda value: (abs(value - duration_value), value))


def _optimize_musescore_grid_durations(durations: Sequence[Fraction], total: Fraction) -> list[Fraction] | None:
    states: dict[Fraction, tuple[float, list[Fraction]]] = {Fraction(0, 1): (0.0, [])}
    for duration_value in durations:
        next_states: dict[Fraction, tuple[float, list[Fraction]]] = {}
        for subtotal, (cost, path) in states.items():
            for candidate in _musescore_grid_candidates(duration_value, total):
                next_subtotal = subtotal + candidate
                if next_subtotal > total:
                    continue
                delta = float(candidate - duration_value)
                candidate_cost = cost + delta * delta + (0.0 if candidate == duration_value else 0.001)
                if next_subtotal not in next_states or candidate_cost < next_states[next_subtotal][0]:
                    next_states[next_subtotal] = (candidate_cost, [*path, candidate])
        states = next_states
    result = states.get(total)
    if result is None:
        return None
    return result[1]


def normalize_musescore_grid_rhythm(score: stream.Score) -> int:
    """Quantize non-dyadic measures to a nearby quarter-grid for MuseScore import."""

    changes = 0
    for part in score.parts:
        for measure in part.getElementsByClass(stream.Measure):
            groups = _measure_note_groups(measure)
            durations = [_group_duration(group) for group in groups]
            if not durations or any(duration_value is None for duration_value in durations):
                continue
            typed_durations = [duration_value for duration_value in durations if duration_value is not None]
            if all(_is_musescore_grid_safe_duration(duration_value) for duration_value in typed_durations):
                continue
            total = sum(typed_durations, Fraction(0, 1))
            optimized = _optimize_musescore_grid_durations(typed_durations, total)
            if optimized is None or optimized == typed_durations:
                continue
            _rewrite_measure_group_durations(measure, groups, 0, optimized)
            changes += 1
    return changes


def _event_fragments_for_bar(event: SourceEvent, bar: Bar) -> Fragment | None:
    start = max(event.start, bar.start)
    end = min(event.end, bar.end)
    if start >= end:
        return None
    return Fragment(event=event, offset=start - bar.start, duration=end - start)


def _is_single_pitched_fragment(fragment: Fragment, offset_counts: dict[Fraction, int]) -> bool:
    return (
        offset_counts.get(fragment.offset, 0) == 1
        and fragment.event is not None
        and not fragment.event.is_rest
        and fragment.event.pitch_midi is not None
    )


def _is_simple_notated_duration(duration: Fraction) -> bool:
    return duration.denominator in {1, 2, 3, 4, 6, 8}


def _simplify_monophonic_fragments(
    fragments: Sequence[Fragment],
    *,
    max_gap: Fraction = Fraction(1, 12),
) -> list[Fragment]:
    if not fragments:
        return []

    offset_counts: dict[Fraction, int] = {}
    for fragment in fragments:
        offset_counts[fragment.offset] = offset_counts.get(fragment.offset, 0) + 1

    merged: list[Fragment] = []
    for fragment in fragments:
        if merged:
            previous = merged[-1]
            gap = fragment.offset - previous.end
            combined_duration = fragment.end - previous.offset
            if (
                Fraction(0, 1) <= gap <= max_gap
                and _is_single_pitched_fragment(previous, offset_counts)
                and _is_single_pitched_fragment(fragment, offset_counts)
                and previous.event is not None
                and fragment.event is not None
                and previous.event.part_index == fragment.event.part_index
                and previous.event.pitch_midi == fragment.event.pitch_midi
                and (
                    gap > 0
                    or not _is_simple_notated_duration(combined_duration)
                    or not _is_simple_notated_duration(previous.duration)
                    or not _is_simple_notated_duration(fragment.duration)
                )
            ):
                merged[-1] = replace(previous, duration=combined_duration)
                continue
        merged.append(fragment)

    offset_counts = {}
    for fragment in merged:
        offset_counts[fragment.offset] = offset_counts.get(fragment.offset, 0) + 1

    simplified: list[Fragment] = list(merged)
    for index in range(len(simplified) - 1):
        current = simplified[index]
        following = simplified[index + 1]
        gap = following.offset - current.end
        extended_duration = current.duration + gap
        if (
            Fraction(0, 1) < gap <= max_gap
            and _is_single_pitched_fragment(current, offset_counts)
            and _is_single_pitched_fragment(following, offset_counts)
            and not _is_simple_notated_duration(current.duration)
            and _is_simple_notated_duration(extended_duration)
        ):
            simplified[index] = replace(current, duration=extended_duration)

    return simplified


def _make_note_fragment_element(event: SourceEvent, offset: Fraction, duration: Fraction, bar: Bar) -> note.Note:
    if event.pitch_midi is None:
        raise ValueError(f"Note event without pitch: {event.source_id}")

    out_note = note.Note(int(event.pitch_midi), quarterLength=fraction_to_ql(duration))
    out_note.editorial.sourceEventId = event.source_id
    out_note.editorial.sourcePartIndex = event.part_index
    if event.part_index < 0 or event.source_id.startswith("generated:"):
        out_note.editorial.generatedHarmony = True

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


def _make_chord_fragment_element(fragments: Sequence[Fragment], bar: Bar) -> chord.Chord:
    fragments = sorted(
        fragments,
        key=lambda fragment: int(fragment.event.pitch_midi) if fragment.event and fragment.event.pitch_midi is not None else -1,
    )
    events = [fragment.event for fragment in fragments]
    if any(event is None or event.pitch_midi is None or event.is_rest for event in events):
        raise ValueError("Chord fragments must be pitched source events.")

    duration = fragments[0].duration
    out_chord = chord.Chord(
        [int(event.pitch_midi) for event in events if event is not None],
        quarterLength=fraction_to_ql(duration),
    )
    out_chord.editorial.sourceEventIds = tuple(event.source_id for event in events if event is not None)
    out_chord.editorial.sourcePartIndices = tuple(event.part_index for event in events if event is not None)
    if any(event.part_index < 0 or event.source_id.startswith("generated:") for event in events if event is not None):
        out_chord.editorial.generatedHarmony = True

    for chord_note, fragment in zip(out_chord.notes, fragments, strict=True):
        event = fragment.event
        if event is None:
            continue
        abs_start = bar.start + fragment.offset
        abs_end = abs_start + fragment.duration
        continues_from_before = abs_start > event.start
        continues_after = abs_end < event.end
        if continues_from_before and continues_after:
            chord_note.tie = tie.Tie("continue")
        elif continues_from_before:
            chord_note.tie = tie.Tie("stop")
        elif continues_after:
            chord_note.tie = tie.Tie("start")
        elif event.source_tie_type is not None:
            chord_note.tie = tie.Tie(event.source_tie_type)
    return out_chord


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


def _insert_chord_fragments(measure: stream.Stream, fragments: Sequence[Fragment], bar: Bar) -> None:
    element = _make_chord_fragment_element(fragments, bar)
    measure.insert(fraction_to_ql(fragments[0].offset), element)


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
    fragments = _simplify_monophonic_fragments(fragments)

    cursor = Fraction(0, 1)
    index = 0
    while index < len(fragments):
        fragment = fragments[index]
        group = [fragment]
        index += 1
        while index < len(fragments) and fragments[index].offset == fragment.offset:
            group.append(fragments[index])
            index += 1

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
        if len(group) == 1:
            _insert_fragment(container, fragment, bar)
        else:
            if len(group) > 2:
                source_ids = ", ".join(group_fragment.event.source_id for group_fragment in group if group_fragment.event)
                raise MeasureValidationError(
                    f"{part_name} has more than two simultaneous notes near measure {bar.number}: {source_ids}"
                )
            if any(group_fragment.end != fragment.end for group_fragment in group):
                source_ids = ", ".join(group_fragment.event.source_id for group_fragment in group if group_fragment.event)
                raise MeasureValidationError(
                    f"{part_name} has partially overlapping double-stop events near measure {bar.number}: {source_ids}"
                )
            if any(group_fragment.event is None or group_fragment.event.is_rest for group_fragment in group):
                source_ids = ", ".join(group_fragment.event.source_id for group_fragment in group if group_fragment.event)
                raise MeasureValidationError(
                    f"{part_name} has non-pitched double-stop fragments near measure {bar.number}: {source_ids}"
                )
            pitch_classes = {group_fragment.event.pitch_midi % 12 for group_fragment in group if group_fragment.event}
            if len(pitch_classes) != len(group):
                source_ids = ", ".join(group_fragment.event.source_id for group_fragment in group if group_fragment.event)
                raise MeasureValidationError(
                    f"{part_name} has duplicate pitch classes in a double stop near measure {bar.number}: {source_ids}"
                )
            _insert_chord_fragments(container, group, bar)
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
            if (
                (element.isNote or element.isChord)
                and not hasattr(element.editorial, "sourceEventId")
                and not hasattr(element.editorial, "sourceEventIds")
                and not getattr(element.editorial, "generatedHarmony", False)
            ):
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
        if (
            (element.isNote or element.isChord)
            and not hasattr(element.editorial, "sourceEventId")
            and not hasattr(element.editorial, "sourceEventIds")
            and not getattr(element.editorial, "generatedHarmony", False)
        ):
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


_JAZZ_INTERVAL_PRIORITY = {
    3: 9.0,   # minor third
    4: 9.0,   # major third
    10: 8.0,  # minor seventh
    11: 7.5,  # major seventh
    6: 7.0,   # tritone / sharp eleven
    1: 6.5,   # flat nine / sharp root color
    2: 6.0,   # ninth
    8: 5.5,   # sharp five / flat thirteen
    9: 5.0,   # sixth / thirteenth
    5: 4.0,   # eleventh / suspended fourth
    7: 2.0,   # fifth
    0: 1.0,   # root / octave
}


def _jazz_color_tone_score(
    pitch_class_value: int,
    *,
    bass_pitch_class: int | None,
    active_source_pitch_classes: set[int],
    covered_pitch_classes: set[int],
) -> float:
    """Rank dense close-harmony tones when only a few can fit in the quartet."""

    score = 0.0
    if bass_pitch_class is not None:
        interval = (pitch_class_value - bass_pitch_class) % 12
        score += _JAZZ_INTERVAL_PRIORITY.get(interval, 3.0)
        if len(active_source_pitch_classes) > 4 and interval in {0, 7}:
            score -= 4.0

    if len(active_source_pitch_classes) > 4:
        score += 1.0

    if any((pitch_class_value - covered) % 12 in {1, 11, 6} for covered in covered_pitch_classes):
        score += 0.75

    return score


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


def _monophonic_events_for_target(events: Sequence[SourceEvent], target: TargetPart) -> list[SourceEvent]:
    """Return non-overlapping pitched events for one target line."""

    result: list[SourceEvent] = []
    for event in sorted(_pitched_events(events), key=lambda ev: (ev.start, ev.end, ev.source_id)):
        if not result:
            result.append(event)
            continue

        previous = result[-1]
        if event.start >= previous.end:
            result.append(event)
            continue

        if event.start <= previous.start:
            if target.role == "bottom":
                keep_new = int(event.pitch_midi) < int(previous.pitch_midi)
            elif target.role == "top":
                keep_new = int(event.pitch_midi) > int(previous.pitch_midi)
            else:
                keep_new = _register_fit_score(target, int(event.pitch_midi), ReductionConfig()) < _register_fit_score(
                    target,
                    int(previous.pitch_midi),
                    ReductionConfig(),
                )
            if keep_new:
                result[-1] = event
            continue

        trimmed_duration = event.start - previous.start
        if trimmed_duration > 0:
            result[-1] = replace(previous, duration=trimmed_duration, source_tie_type=None)
            result.append(event)
        else:
            result[-1] = event
    return result


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


def _target_is_free_for_interval(
    target: TargetPart,
    start: Fraction,
    end: Fraction,
    selected: dict[str, list[SourceEvent]],
) -> bool:
    return not any(
        _event_overlaps_interval(existing, start, end)
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


def _active_events_at(events: Sequence[SourceEvent], offset: Fraction) -> list[SourceEvent]:
    return [
        event
        for event in events
        if not event.is_rest and event.pitch_midi is not None and event.start <= offset < event.end
    ]


def _active_source_part_count(
    events: Sequence[SourceEvent],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
    offset: Fraction,
) -> int:
    part_indices = {event.part_index for event in _active_events_at(events, offset)}
    part_indices.update(event.part_index for event in _active_events_at(top_events, offset))
    part_indices.update(event.part_index for event in _active_events_at(bottom_events, offset))
    return len(part_indices)


def _active_target_count(selected: dict[str, list[SourceEvent]], offset: Fraction) -> int:
    return sum(
        1
        for events in selected.values()
        if any(event.pitch_midi is not None and event.start <= offset < event.end for event in events)
    )


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
    config: ReductionConfig | None = None,
) -> list[SourceEvent]:
    chord_policy = "bottom" if target.role == "bottom" else "top"
    events = extract_events(source_part, source_index, include_rests=True, chord_policy=chord_policy)
    if config is not None and config.normalize_short_note_rest_artifacts:
        events = normalize_short_note_rest_artifacts(events)
    return events


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


def _represented_source_parts(selected: dict[str, list[SourceEvent]], offset: Fraction) -> set[int]:
    return {
        event.part_index
        for events in selected.values()
        for event in events
        if event.part_index >= 0 and event.pitch_midi is not None and event.start <= offset < event.end
    }


def _continues_target_source_part(
    event: SourceEvent,
    selected: dict[str, list[SourceEvent]],
    targets: Sequence[TargetPart],
) -> bool:
    return _target_continuing_source_part(event, selected, targets) is not None


def _target_continuing_source_part(
    event: SourceEvent,
    selected: dict[str, list[SourceEvent]],
    targets: Sequence[TargetPart],
) -> TargetPart | None:
    for target in targets:
        if not _target_is_free_for_event(target, event, selected):
            continue
        if any(
            previous.part_index == event.part_index
            and previous.pitch_midi is not None
            and previous.end == event.start
            for previous in selected[target.id]
        ):
            return target
    return None


def _target_anchor_part_indices(
    initial_events_by_target: dict[str, Sequence[SourceEvent]],
) -> dict[str, set[int]]:
    return {
        target_id: {event.part_index for event in events if event.part_index >= 0}
        for target_id, events in initial_events_by_target.items()
    }


def _is_borrowed_from_target_anchor(
    target: TargetPart,
    event: SourceEvent,
    target_anchor_parts: dict[str, set[int]],
) -> bool:
    anchor_parts = target_anchor_parts.get(target.id)
    return anchor_parts is not None and event.part_index not in anchor_parts


def _is_high_borrowed_bottom_duplicate(
    target: TargetPart,
    event: SourceEvent,
    *,
    covered_pitch_classes: set[int],
    target_anchor_parts: dict[str, set[int]],
    config: ReductionConfig,
) -> bool:
    if (
        config.max_borrowed_bottom_duplicate_pitch is None
        or target.role != "bottom"
        or event.pitch_midi is None
        or event.pitch_midi <= config.max_borrowed_bottom_duplicate_pitch
        or event.pitch_midi % 12 not in covered_pitch_classes
    ):
        return False
    return _is_borrowed_from_target_anchor(target, event, target_anchor_parts)


def _is_high_borrowed_bottom_event(
    target: TargetPart,
    event: SourceEvent,
    *,
    covered_pitch_classes: set[int],
    target_anchor_parts: dict[str, set[int]],
    config: ReductionConfig,
) -> bool:
    if (
        target.role != "bottom"
        or event.pitch_midi is None
        or not _is_borrowed_from_target_anchor(target, event, target_anchor_parts)
    ):
        return False
    if (
        config.max_borrowed_bottom_pitch is not None
        and event.pitch_midi > config.max_borrowed_bottom_pitch
    ):
        return True
    return _is_high_borrowed_bottom_duplicate(
        target,
        event,
        covered_pitch_classes=covered_pitch_classes,
        target_anchor_parts=target_anchor_parts,
        config=config,
    )


def _duplicate_color_tone_penalty(
    event: SourceEvent,
    *,
    bass_pitch_class: int | None,
    covered_pitch_classes: set[int],
) -> float:
    if event.pitch_midi is None or event.pitch_midi % 12 not in covered_pitch_classes:
        return 0.0
    if bass_pitch_class is None:
        return 1.0
    interval = (int(event.pitch_midi) - bass_pitch_class) % 12
    if interval in {3, 4, 10, 11}:
        return 3.0
    if interval in {1, 2, 6, 8, 9}:
        return 2.0
    return 0.5


_STRING_TUNINGS = {
    "vln1": (55, 62, 69, 76),
    "vln2": (55, 62, 69, 76),
    "vla": (48, 55, 62, 69),
    "vc": (36, 43, 50, 57),
}
_CONSERVATIVE_DOUBLE_STOP_INTERVALS = {3, 4, 5, 6, 7, 8, 9, 12, 15, 16}
_SIMPLE_SPLIT_DENOMINATORS = {1, 2, 3, 4, 6, 8}
_LONG_HELD_DOUBLE_STOP_MIN_DURATION = Fraction(2, 1)
_SOURCE_DOUBLE_STOP_MIN_DURATION = Fraction(1, 2)


def _pitch_string_positions(midi_pitch: int, target: TargetPart) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for string_index, open_pitch in enumerate(_STRING_TUNINGS.get(target.id, ())):
        if midi_pitch < open_pitch:
            continue
        finger_distance = midi_pitch - open_pitch
        if finger_distance <= 24:
            positions.append((string_index, finger_distance))
    return positions


def _is_playable_double_stop(target: TargetPart, first_pitch: int, second_pitch: int) -> bool:
    if first_pitch == second_pitch:
        return False
    lower, upper = sorted((int(first_pitch), int(second_pitch)))
    if upper - lower not in _CONSERVATIVE_DOUBLE_STOP_INTERVALS:
        return False

    lower_positions = _pitch_string_positions(lower, target)
    upper_positions = _pitch_string_positions(upper, target)
    for lower_string, lower_distance in lower_positions:
        for upper_string, upper_distance in upper_positions:
            if upper_string != lower_string + 1:
                continue
            if lower_distance == 0 or upper_distance == 0 or abs(upper_distance - lower_distance) <= 5:
                return True
    return False


def _lowered_cello_event_pitches(
    element: note.Note | chord.Chord,
    target: TargetPart,
    threshold: int,
) -> list[int] | None:
    pitches = [int(round(item.midi)) for item in element.pitches]
    if not pitches:
        return None

    shifted = [midi_pitch - 12 if midi_pitch >= threshold else midi_pitch for midi_pitch in pitches]
    if shifted == pitches:
        return None
    low, high = target.midi_range
    if any(midi_pitch < low or midi_pitch > high for midi_pitch in shifted):
        return None
    if len(shifted) == 1:
        return shifted
    if len(shifted) != 2:
        return None
    if not _is_playable_double_stop(target, shifted[0], shifted[1]):
        return None
    return shifted


def _lower_high_cello_register(score: stream.Score, target: TargetPart, threshold: int) -> int:
    """Move high cello-only material into the instrument's lower sweet spot."""
    changes = 0
    target_name = target.name.casefold()
    for part in score.parts:
        part_name = (part.partName or "").casefold()
        if target_name not in part_name and "cello" not in part_name and "violoncello" not in part_name:
            continue
        for element in part.recurse().notes:
            shifted = _lowered_cello_event_pitches(element, target, threshold)
            if shifted is None:
                continue
            if element.isChord:
                for chord_note, shifted_pitch in zip(element.notes, shifted, strict=True):
                    chord_note.pitch.midi = shifted_pitch
            else:
                element.pitch.midi = shifted[0]
            changes += 1
    return changes


def lower_take6_high_cello_register(score: stream.Score, threshold: int = 55) -> int:
    """Lower high Take 6 cello pitches when the result remains idiomatic."""
    return _lower_high_cello_register(score, STRING_QUARTET.bottom_part, threshold)


def _simultaneous_event_count(
    selected: dict[str, list[SourceEvent]],
    target: TargetPart,
    start: Fraction,
    end: Fraction,
) -> int:
    return sum(
        1
        for event in selected[target.id]
        if event.pitch_midi is not None and event.start == start and event.end == end
    )


def _is_simple_split_duration(duration: Fraction) -> bool:
    return (
        duration > 0
        and duration.denominator in _SIMPLE_SPLIT_DENOMINATORS
        and duration.numerator <= 4
    )


def _overlapping_target_events(
    selected: dict[str, list[SourceEvent]],
    target: TargetPart,
    start: Fraction,
    end: Fraction,
) -> list[SourceEvent]:
    return [
        event
        for event in selected[target.id]
        if event.pitch_midi is not None and _event_overlaps_interval(event, start, end)
    ]


def _split_host_for_double_stop(
    selected: dict[str, list[SourceEvent]],
    target: TargetPart,
    host: SourceEvent,
    start: Fraction,
    end: Fraction,
) -> SourceEvent:
    if host.start == start and host.end == end:
        return host
    if host.start > start or host.end < end:
        raise MeasureValidationError(f"Cannot split host event {host.source_id} for double stop.")

    split_events: list[SourceEvent] = []
    if host.start < start:
        split_events.append(
            replace(
                host,
                duration=start - host.start,
                source_tie_type=None,
            )
        )
    overlap_event = replace(host, start=start, duration=end - start, source_tie_type=None)
    split_events.append(overlap_event)
    if end < host.end:
        split_events.append(
            replace(
                host,
                start=end,
                duration=host.end - end,
                source_tie_type=None,
            )
        )

    target_events = selected[target.id]
    host_index = target_events.index(host)
    selected[target.id] = [*target_events[:host_index], *split_events, *target_events[host_index + 1:]]
    return overlap_event


def _target_attacks_at(
    selected: dict[str, list[SourceEvent]],
    target: TargetPart,
    offset: Fraction,
) -> int:
    return sum(
        1
        for event in selected[target.id]
        if event.pitch_midi is not None and event.start == offset
    )


def _double_stop_hosts(
    selected: dict[str, list[SourceEvent]],
    targets: Sequence[TargetPart],
    candidate: SourceEvent,
    config: ReductionConfig,
) -> list[tuple[TargetPart, SourceEvent, tuple[SourceEvent, ...]]]:
    if candidate.pitch_midi is None:
        return []
    result: list[tuple[TargetPart, SourceEvent, tuple[SourceEvent, ...]]] = []
    candidate_pitch = int(candidate.pitch_midi)
    for target in targets:
        overlapping_events = _overlapping_target_events(selected, target, candidate.start, candidate.end)
        if len(overlapping_events) != 1:
            continue
        event = overlapping_events[0]
        if event.start > candidate.start:
            continue
        overlap_end = min(event.end, candidate.end)
        if overlap_end <= candidate.start:
            continue
        if overlap_end - candidate.start < _SOURCE_DOUBLE_STOP_MIN_DURATION:
            continue
        split_durations = [
            candidate.start - event.start,
            overlap_end - candidate.start,
            event.end - overlap_end,
            candidate.end - overlap_end,
        ]
        if any(duration > 0 and not _is_simple_split_duration(duration) for duration in split_durations):
            continue
        if _simultaneous_event_count(selected, target, candidate.start, candidate.end) >= 2:
            continue
        host_pitch = int(event.pitch_midi)
        fitted_candidate = octave_fit(candidate_pitch, *target.midi_range) if config.enforce_ranges else candidate_pitch
        if fitted_candidate is None:
            continue
        if host_pitch % 12 == fitted_candidate % 12:
            continue
        if _is_playable_double_stop(target, host_pitch, fitted_candidate):
            prepared = [
                replace(
                    candidate,
                    pitch_midi=fitted_candidate,
                    duration=overlap_end - candidate.start,
                    source_tie_type=None,
                )
            ]
            if candidate.end > overlap_end:
                prepared.append(
                    replace(
                        candidate,
                        start=overlap_end,
                        duration=candidate.end - overlap_end,
                        pitch_midi=fitted_candidate,
                        source_tie_type=None,
                    )
                )
            result.append((target, event, tuple(prepared)))
    return result


def _has_adjacent_source_motion(
    event: SourceEvent,
    events_by_part: dict[int, Sequence[SourceEvent]],
    *,
    max_gap: Fraction = Fraction(1, 2),
) -> bool:
    if event.pitch_midi is None:
        return False
    for sibling in events_by_part.get(event.part_index, ()):
        if sibling.source_id == event.source_id or sibling.pitch_midi is None:
            continue
        if sibling.end <= event.start and event.start - sibling.end <= max_gap:
            return True
        if event.end <= sibling.start and sibling.start - event.end <= max_gap:
            return True
    return False


def _add_double_stop_candidate(
    selected: dict[str, list[SourceEvent]],
    selected_source_ids: set[str],
    covered_pitch_classes: set[int],
    targets: Sequence[TargetPart],
    candidate: SourceEvent,
    config: ReductionConfig,
) -> bool:
    hosts = _double_stop_hosts(selected, targets, candidate, config)
    if not hosts:
        return False
    target, host, prepared_events = min(
        hosts,
        key=lambda item: (
            _target_attacks_at(selected, item[0], item[2][0].end),
            item[0].role == "bottom",
            _register_fit_score(item[0], int(item[2][0].pitch_midi), config),
            item[1].end - item[2][0].end,
            abs(int(item[2][0].pitch_midi) - int(candidate.pitch_midi)) / 12,
            targets.index(item[0]),
        ),
    )
    overlap = prepared_events[0]
    _split_host_for_double_stop(selected, target, host, overlap.start, overlap.end)
    selected[target.id].extend(prepared_events)
    selected_source_ids.add(candidate.source_id)
    covered_pitch_classes.add(int(overlap.pitch_midi) % 12)
    return True


def _is_long_homorhythmic_source_attack(
    start: Fraction,
    active_source_events: Sequence[SourceEvent],
    *,
    min_source_notes: int,
    min_duration: Fraction = _LONG_HELD_DOUBLE_STOP_MIN_DURATION,
) -> bool:
    if len(active_source_events) < min_source_notes:
        return False
    if any(event.start != start for event in active_source_events):
        return False
    end_values = {event.end for event in active_source_events}
    if len(end_values) != 1:
        return False
    return next(iter(end_values)) - start >= min_duration


def _add_source_double_stops(
    selected: dict[str, list[SourceEvent]],
    source_events: Sequence[SourceEvent],
    targets: Sequence[TargetPart],
    config: ReductionConfig,
) -> None:
    selected_source_ids = _selected_source_ids(selected)
    note_events = [
        event
        for event in source_events
        if not event.is_rest and event.pitch_midi is not None
    ]
    events_by_part: dict[int, list[SourceEvent]] = {}
    for event in note_events:
        events_by_part.setdefault(event.part_index, []).append(event)
    starts = sorted({event.start for event in note_events})
    for start in starts:
        active_source_events = _active_events_at(note_events, start)
        active_source_pitch_classes = {
            int(event.pitch_midi) % 12
            for event in active_source_events
            if event.pitch_midi is not None
        }
        allow_source_doublings = _is_long_homorhythmic_source_attack(
            start,
            active_source_events,
            min_source_notes=len(targets) + 1,
        )
        if len(active_source_pitch_classes) <= len(targets) and not allow_source_doublings:
            continue
        active_output_pitches = _active_pitches_from_assignments(selected, start)
        covered_pitch_classes = {pitch % 12 for pitch in active_output_pitches}
        bass_pitch = min(active_source_events, key=lambda event: int(event.pitch_midi)).pitch_midi
        bass_pitch_class = None if bass_pitch is None else int(bass_pitch) % 12
        candidates = [
            event
            for event in active_source_events
            if event.source_id not in selected_source_ids
            and event.pitch_midi is not None
            and int(event.pitch_midi) % 12 not in covered_pitch_classes
            and event.start == start
        ]
        candidates.sort(
            key=lambda event: (
                -_jazz_color_tone_score(
                    int(event.pitch_midi) % 12,
                    bass_pitch_class=bass_pitch_class,
                    active_source_pitch_classes=active_source_pitch_classes,
                    covered_pitch_classes=covered_pitch_classes,
                ),
                not _is_new_onset(event),
                -event.duration,
                event.source_id,
            )
        )
        for candidate in candidates:
            if candidate.source_id in selected_source_ids:
                continue
            _add_double_stop_candidate(
                selected,
                selected_source_ids,
                covered_pitch_classes,
                targets,
                candidate,
                config,
            )

        if not allow_source_doublings:
            represented_parts = _represented_source_parts(selected, start)
            duplicate_candidates = [
                event
                for event in active_source_events
                if event.source_id not in selected_source_ids
                and event.pitch_midi is not None
                and event.start == start
                and int(event.pitch_midi) % 12 in covered_pitch_classes
                and event.part_index not in represented_parts
                and _is_new_onset(event)
                and event.duration >= Fraction(1, 2)
                and _has_adjacent_source_motion(event, events_by_part)
            ]
        else:
            duplicate_candidates = [
                event
                for event in active_source_events
                if event.source_id not in selected_source_ids
                and event.pitch_midi is not None
                and event.start == start
                and int(event.pitch_midi) % 12 in covered_pitch_classes
            ]

        added_duplicate_pitch_classes: set[int] = set()
        added_melodic_parts: set[int] = set()
        duplicate_candidates.sort(
            key=lambda event: (
                event.part_index in added_melodic_parts,
                -event.duration,
                -_jazz_color_tone_score(
                    int(event.pitch_midi) % 12,
                    bass_pitch_class=bass_pitch_class,
                    active_source_pitch_classes=active_source_pitch_classes,
                    covered_pitch_classes=covered_pitch_classes,
                ),
                event.source_id,
            )
        )
        for candidate in duplicate_candidates:
            if candidate.source_id in selected_source_ids:
                continue
            candidate_pitch_class = int(candidate.pitch_midi) % 12
            if allow_source_doublings and candidate_pitch_class in added_duplicate_pitch_classes:
                continue
            if not allow_source_doublings and candidate.part_index in added_melodic_parts:
                continue
            if _add_double_stop_candidate(
                selected,
                selected_source_ids,
                covered_pitch_classes,
                targets,
                candidate,
                config,
            ):
                added_duplicate_pitch_classes.add(candidate_pitch_class)
                added_melodic_parts.add(candidate.part_index)


def _selected_source_ids(selected: dict[str, list[SourceEvent]]) -> set[str]:
    return {
        event.source_id
        for events in selected.values()
        for event in events
    }


def _choose_editorial_harmony_pitch(
    source_events: Sequence[SourceEvent],
    target: TargetPart,
    last_pitch: dict[str, int | None],
    active_output_pitches: Sequence[int],
    config: ReductionConfig,
) -> SourceEvent | None:
    active_exact = set(active_output_pitches)
    best_event: SourceEvent | None = None
    best_cost = float("inf")
    previous = last_pitch[target.id]
    for source_event in source_events:
        if source_event.pitch_midi is None:
            continue
        source_pitch = int(source_event.pitch_midi)
        for candidate in octave_candidates(source_pitch, *target.midi_range):
            remaining_duration = max(source_event.end - source_event.start, Fraction(0, 1))
            register_cost = _register_fit_score(target, candidate, config)
            continuity_cost = 0 if previous is None else abs(candidate - previous) / 12
            exact_duplicate_cost = 1.5 if candidate in active_exact else 0
            displacement_cost = abs(candidate - source_pitch) / 24
            duration_reward = min(float(remaining_duration), 4.0)
            cost = register_cost + continuity_cost + exact_duplicate_cost + displacement_cost - duration_reward
            if cost < best_cost:
                best_cost = cost
                best_event = replace(source_event, pitch_midi=candidate)
    return best_event


def _third_pc_for_shell(
    active_output_pitches: Sequence[int],
    source_events: Sequence[SourceEvent],
    all_events: Sequence[SourceEvent],
    offset: Fraction,
    *,
    lookahead: Fraction = Fraction(12, 1),
) -> int | None:
    active_pcs = {pitch % 12 for pitch in active_output_pitches}
    if len(active_pcs) < 2:
        return None

    candidates: list[tuple[int, int, int]] = []
    source_pcs = {
        int(event.pitch_midi) % 12
        for event in source_events
        if event.pitch_midi is not None
    }
    for root_pc in active_pcs:
        fifth_pc = (root_pc + 7) % 12
        minor_third_pc = (root_pc + 3) % 12
        major_third_pc = (root_pc + 4) % 12
        if fifth_pc not in active_pcs:
            continue
        if minor_third_pc in active_pcs or major_third_pc in active_pcs:
            continue
        source_support = (root_pc in source_pcs) + (fifth_pc in source_pcs)
        dominant_support = 1 if (root_pc + 10) % 12 in active_pcs else 0
        candidates.append((-source_support, -dominant_support, root_pc))
    if not candidates:
        return None

    root_pc = min(candidates)[2]
    minor_third_pc = (root_pc + 3) % 12
    major_third_pc = (root_pc + 4) % 12
    search_end = offset + lookahead
    future_thirds = sorted(
        (
            (event.start, event.source_id, int(event.pitch_midi) % 12)
            for event in all_events
            if event.pitch_midi is not None
            and offset < event.start <= search_end
            and int(event.pitch_midi) % 12 in {minor_third_pc, major_third_pc}
        ),
        key=lambda item: (item[0], item[1]),
    )
    if future_thirds:
        return future_thirds[0][2]

    if (root_pc + 10) % 12 in active_pcs:
        return major_third_pc
    return major_third_pc


def _choose_editorial_third_pitch(
    active_output_pitches: Sequence[int],
    source_events: Sequence[SourceEvent],
    all_events: Sequence[SourceEvent],
    target: TargetPart,
    last_pitch: dict[str, int | None],
    start: Fraction,
    config: ReductionConfig,
) -> int | None:
    third_pc = _third_pc_for_shell(active_output_pitches, source_events, all_events, start)
    if third_pc is None:
        return None

    previous = last_pitch[target.id]
    active_pcs = {pitch % 12 for pitch in active_output_pitches}
    anchor_pitches = [
        int(event.pitch_midi)
        for event in source_events
        if event.pitch_midi is not None and int(event.pitch_midi) % 12 in active_pcs
    ]
    if not anchor_pitches:
        anchor_pitches = list(active_output_pitches)
    center = sum(anchor_pitches) / len(anchor_pitches)
    base_pitch = int(round((center - third_pc) / 12)) * 12 + third_pc
    candidates = octave_candidates(base_pitch, *target.midi_range)
    if not candidates:
        return None

    return min(
        candidates,
        key=lambda candidate: (
            _register_fit_score(target, candidate, config),
            0 if previous is None else abs(candidate - previous) / 12,
            abs(candidate - center) / 24,
        ),
    )


def _has_same_pitch_continuation(
    event: SourceEvent,
    events_by_part: dict[int, Sequence[SourceEvent]],
) -> bool:
    if event.pitch_midi is None:
        return False
    event_pc = int(event.pitch_midi) % 12
    return any(
        other.source_id != event.source_id
        and other.start == event.end
        and other.pitch_midi is not None
        and int(other.pitch_midi) % 12 == event_pc
        for other in events_by_part.get(event.part_index, ())
    )


def _has_same_pitch_previous(
    event: SourceEvent,
    events_by_part: dict[int, Sequence[SourceEvent]],
) -> bool:
    if event.pitch_midi is None:
        return False
    event_pc = int(event.pitch_midi) % 12
    return any(
        other.source_id != event.source_id
        and other.end == event.start
        and other.pitch_midi is not None
        and int(other.pitch_midi) % 12 == event_pc
        for other in events_by_part.get(event.part_index, ())
    )


def _source_change_end(
    start: Fraction,
    events: Sequence[SourceEvent],
    top_events: Sequence[SourceEvent],
    bottom_events: Sequence[SourceEvent],
) -> Fraction | None:
    pitched_events = [
        event
        for event in (*events, *top_events, *bottom_events)
        if not event.is_rest and event.pitch_midi is not None
    ]
    events_by_part: dict[int, list[SourceEvent]] = {}
    for event in pitched_events:
        events_by_part.setdefault(event.part_index, []).append(event)
    change_points = [
        event.end
        for event in pitched_events
        if event.start <= start < event.end
        and event.end > start
        and not _has_same_pitch_continuation(event, events_by_part)
    ]
    change_points.extend(
        event.start
        for event in pitched_events
        if event.start > start and not _has_same_pitch_previous(event, events_by_part)
    )
    return min(change_points) if change_points else None


def _trim_event_end(event: SourceEvent, end: Fraction) -> SourceEvent | None:
    if end <= event.start:
        return None
    if end >= event.end:
        return event
    return replace(event, duration=end - event.start)


def _prepare_preserving_candidate(
    event: SourceEvent,
    next_source_change: Fraction | None,
    covered_pitch_classes: set[int],
    config: ReductionConfig,
) -> SourceEvent | None:
    if event.pitch_midi is None:
        return event
    if event.pitch_midi % 12 not in covered_pitch_classes or next_source_change is None:
        return event

    prepared = _trim_event_end(event, next_source_change)
    if prepared is None:
        return None
    min_duration = config.min_preserved_trimmed_duration
    if prepared.duration < event.duration and min_duration is not None and prepared.duration < min_duration:
        return event
    return prepared


def _is_generated_harmony_event(event: SourceEvent) -> bool:
    return event.part_index < 0 and event.source_id.startswith(("generated:harmony:", "generated:third:"))


def _merge_adjacent_generated_harmony_events(selected: dict[str, list[SourceEvent]]) -> None:
    for target_id, events in selected.items():
        merged: list[SourceEvent] = []
        for event in sorted(events, key=lambda ev: (ev.start, ev.end, ev.source_id)):
            if (
                merged
                and _is_generated_harmony_event(merged[-1])
                and _is_generated_harmony_event(event)
                and merged[-1].pitch_midi == event.pitch_midi
                and merged[-1].end == event.start
            ):
                previous = merged[-1]
                merged[-1] = replace(previous, duration=previous.duration + event.duration)
            else:
                merged.append(event)
        selected[target_id] = merged


def _previous_pitched_event(events: Sequence[SourceEvent], event: SourceEvent) -> SourceEvent | None:
    candidates = [
        other
        for other in events
        if other.pitch_midi is not None
        and other.source_id != event.source_id
        and other.end <= event.start
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda ev: (ev.end, ev.start, ev.source_id))


def _next_pitched_event(events: Sequence[SourceEvent], event: SourceEvent) -> SourceEvent | None:
    candidates = [
        other
        for other in events
        if other.pitch_midi is not None
        and other.source_id != event.source_id
        and other.start >= event.end
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda ev: (ev.start, ev.end, ev.source_id))


def _is_short_isolated_handoff_candidate(
    events: Sequence[SourceEvent],
    event: SourceEvent,
    max_duration: Fraction,
) -> bool:
    if event.is_rest or event.pitch_midi is None or event.duration > max_duration:
        return False
    if event.part_index < 0:
        return False

    previous = _previous_pitched_event(events, event)
    next_event = _next_pitched_event(events, event)
    adjacent_before = previous is not None and previous.end == event.start
    adjacent_after = next_event is not None and next_event.start == event.end
    if adjacent_before and adjacent_after:
        return False
    if adjacent_after and not adjacent_before:
        return event.end.denominator == 1
    if adjacent_before and not adjacent_after:
        return event.start.denominator == 1

    return True


def _handoff_receiver_score(
    receiver_events: Sequence[SourceEvent],
    event: SourceEvent,
    receiver: TargetPart,
    receiver_rank: int,
    donor_rank: int,
    config: ReductionConfig,
) -> tuple[float, SourceEvent | None, SourceEvent | None] | None:
    if event.pitch_midi is None:
        return None

    midi_pitch = int(event.pitch_midi)
    if config.enforce_ranges and not (receiver.midi_range[0] <= midi_pitch <= receiver.midi_range[1]):
        return None
    if any(_event_overlaps_interval(existing, event.start, event.end) for existing in receiver_events):
        return None

    previous = _previous_pitched_event(receiver_events, event)
    next_event = _next_pitched_event(receiver_events, event)
    if previous is not None and previous.end == event.start and previous.pitch_midi is not None:
        previous_gap = abs(int(previous.pitch_midi) - midi_pitch)
        if next_event is None or next_event.start > event.end:
            if previous_gap <= 4:
                register_cost = _register_fit_score(receiver, midi_pitch, config)
                distance_cost = abs(receiver_rank - donor_rank) / 10
                score = previous_gap + register_cost + distance_cost + 1.0
                return score, previous, None

    if next_event is not None and next_event.start == event.end and next_event.pitch_midi is not None:
        next_gap = abs(midi_pitch - int(next_event.pitch_midi))
        if previous is None or previous.end < event.start:
            if next_gap <= 4:
                register_cost = _register_fit_score(receiver, midi_pitch, config)
                distance_cost = abs(receiver_rank - donor_rank) / 10
                score = next_gap + register_cost + distance_cost + 1.0
                return score, None, next_event

    if previous is None or next_event is None:
        return None
    if previous.end != event.start or next_event.start != event.end:
        return None
    if previous.pitch_midi is None or next_event.pitch_midi is None:
        return None

    previous_gap = abs(int(previous.pitch_midi) - midi_pitch)
    next_gap = abs(midi_pitch - int(next_event.pitch_midi))
    if max(previous_gap, next_gap) > 7:
        return None

    line_cost = previous_gap + next_gap
    direct_cost = abs(int(previous.pitch_midi) - int(next_event.pitch_midi))
    if line_cost > direct_cost + 4:
        return None

    register_cost = _register_fit_score(receiver, midi_pitch, config)
    distance_cost = abs(receiver_rank - donor_rank) / 10
    score = line_cost + register_cost + distance_cost
    return score, previous, next_event


def _remove_event_once(events: Sequence[SourceEvent], event: SourceEvent) -> list[SourceEvent]:
    result = list(events)
    for index, existing in enumerate(result):
        if existing == event:
            del result[index]
            return result
    return result


def _handoff_double_stop_receiver_score(
    receiver_events: Sequence[SourceEvent],
    event: SourceEvent,
    receiver: TargetPart,
    receiver_rank: int,
    donor_rank: int,
    config: ReductionConfig,
) -> tuple[float, SourceEvent] | None:
    if not config.smooth_isolated_handoff_double_stops or event.pitch_midi is None:
        return None

    midi_pitch = int(event.pitch_midi)
    if config.enforce_ranges and not (receiver.midi_range[0] <= midi_pitch <= receiver.midi_range[1]):
        return None
    if abs(receiver_rank - donor_rank) != 1:
        return None

    overlapping = [
        existing
        for existing in receiver_events
        if existing.pitch_midi is not None and _event_overlaps_interval(existing, event.start, event.end)
    ]
    if len(overlapping) != 1:
        return None

    host = overlapping[0]
    if host.start > event.start or host.end < event.end or host.pitch_midi is None:
        return None
    if host.pitch_midi % 12 == midi_pitch % 12:
        return None
    if not _is_playable_double_stop(receiver, int(host.pitch_midi), midi_pitch):
        return None

    split_durations = [
        event.start - host.start,
        event.duration,
        host.end - event.end,
    ]
    if any(duration > 0 and not _is_simple_split_duration(duration) for duration in split_durations):
        return None

    interval_cost = abs(int(host.pitch_midi) - midi_pitch) / 2
    register_cost = _register_fit_score(receiver, midi_pitch, config)
    split_cost = sum(1 for duration in split_durations if duration > 0) / 10
    distance_cost = abs(receiver_rank - donor_rank) / 10
    return interval_cost + register_cost + split_cost + distance_cost, host


def _handoff_trim_receiver_score(
    receiver_events: Sequence[SourceEvent],
    event: SourceEvent,
    receiver: TargetPart,
    receiver_rank: int,
    donor_rank: int,
    config: ReductionConfig,
) -> tuple[float, SourceEvent] | None:
    if not config.smooth_isolated_handoff_trim_overlaps or event.pitch_midi is None:
        return None

    midi_pitch = int(event.pitch_midi)
    if config.enforce_ranges and not (receiver.midi_range[0] <= midi_pitch <= receiver.midi_range[1]):
        return None
    if abs(receiver_rank - donor_rank) != 1:
        return None

    overlapping = [
        existing
        for existing in receiver_events
        if existing.pitch_midi is not None and _event_overlaps_interval(existing, event.start, event.end)
    ]
    if len(overlapping) != 1:
        return None

    host = overlapping[0]
    if host.start >= event.start or host.end != event.end:
        return None
    if host.duration > Fraction(1, 2):
        return None
    trimmed_duration = event.start - host.start
    if not _is_simple_split_duration(trimmed_duration):
        return None
    if host.pitch_midi is not None and host.pitch_midi % 12 == midi_pitch % 12:
        return None

    register_cost = _register_fit_score(receiver, midi_pitch, config)
    distance_cost = abs(receiver_rank - donor_rank) / 10
    return register_cost + distance_cost + 0.25, host


def _trim_host_for_handoff(
    selected: dict[str, list[SourceEvent]],
    target: TargetPart,
    host: SourceEvent,
    end: Fraction,
) -> None:
    if end <= host.start or end >= host.end:
        raise MeasureValidationError(f"Cannot trim host event {host.source_id} for handoff.")
    target_events = selected[target.id]
    host_index = target_events.index(host)
    selected[target.id] = [
        *target_events[:host_index],
        replace(host, duration=end - host.start, source_tie_type=None),
        *target_events[host_index + 1:],
    ]


def _smooth_isolated_handoffs(
    assignments: dict[str, list[SourceEvent]],
    profile: EnsembleProfile,
    config: ReductionConfig,
) -> dict[str, list[SourceEvent]]:
    """Move short isolated notes into an adjacent melodic gap when clearly better."""

    if not config.smooth_isolated_handoffs:
        return assignments

    smoothed = {target_id: list(events) for target_id, events in assignments.items()}
    ranks = {target.id: index for index, target in enumerate(profile.parts)}
    targets_by_id = {target.id: target for target in profile.parts}
    moved_source_ids: set[str] = set()

    changed = True
    while changed:
        changed = False
        for donor in profile.parts:
            donor_events = sorted(smoothed.get(donor.id, []), key=lambda ev: (ev.start, ev.end, ev.source_id))
            for event in donor_events:
                if event.source_id in moved_source_ids:
                    continue
                if not _is_short_isolated_handoff_candidate(
                    donor_events,
                    event,
                    config.smooth_isolated_handoff_max_duration,
                ):
                    continue

                options: list[tuple[float, str, TargetPart, SourceEvent | None]] = []
                for receiver in profile.parts:
                    if receiver.id == donor.id:
                        continue
                    gap_score = _handoff_receiver_score(
                        smoothed.get(receiver.id, []),
                        event,
                        receiver,
                        ranks[receiver.id],
                        ranks[donor.id],
                        config,
                    )
                    if gap_score is not None:
                        options.append((gap_score[0], "gap", receiver, None))

                    trim_score = _handoff_trim_receiver_score(
                        smoothed.get(receiver.id, []),
                        event,
                        receiver,
                        ranks[receiver.id],
                        ranks[donor.id],
                        config,
                    )
                    if trim_score is not None:
                        options.append((trim_score[0], "trim", receiver, trim_score[1]))

                    double_stop_score = _handoff_double_stop_receiver_score(
                        smoothed.get(receiver.id, []),
                        event,
                        receiver,
                        ranks[receiver.id],
                        ranks[donor.id],
                        config,
                    )
                    if double_stop_score is not None:
                        options.append((double_stop_score[0], "double_stop", receiver, double_stop_score[1]))

                if not options:
                    continue

                _, mode, receiver, host = min(options, key=lambda item: (item[0], ranks[item[2].id]))
                smoothed[donor.id] = _remove_event_once(smoothed.get(donor.id, []), event)
                if mode == "double_stop":
                    if host is None:
                        raise ValueError("Double-stop handoff selected without a host event.")
                    _split_host_for_double_stop(smoothed, receiver, host, event.start, event.end)
                elif mode == "trim":
                    if host is None:
                        raise ValueError("Trim handoff selected without a host event.")
                    _trim_host_for_handoff(smoothed, receiver, host, event.start)
                smoothed.setdefault(receiver.id, []).append(event)
                smoothed[receiver.id].sort(key=lambda ev: (ev.start, ev.end, ev.source_id))
                moved_source_ids.add(event.source_id)
                changed = True
                break
            if changed:
                break

    return {
        target.id: sorted(smoothed.get(target.id, []), key=lambda ev: (ev.start, ev.end, ev.source_id))
        for target in profile.parts
        if target.id in targets_by_id
    }


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
    target_anchor_parts = _target_anchor_part_indices(initial_events_by_target)
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
        if config.prefer_jazz_color_tones:
            bass_pitch = active_pitch_at(bottom_events, start)
            bass_pitch_class = None if bass_pitch is None else int(bass_pitch) % 12
            active_source_pitch_classes = {
                int(event.pitch_midi) % 12
                for event in (
                    *_active_events_at(note_events, start),
                    *_active_events_at(top_events, start),
                    *_active_events_at(bottom_events, start),
                )
                if event.pitch_midi is not None
            }
            candidates.sort(
                key=lambda ev: (
                    not _is_new_onset(ev),
                    -_jazz_color_tone_score(
                        int(ev.pitch_midi) % 12,
                        bass_pitch_class=bass_pitch_class,
                        active_source_pitch_classes=active_source_pitch_classes,
                        covered_pitch_classes=covered,
                    ),
                    -spread_score(int(ev.pitch_midi), anchors),
                    -ev.duration,
                    ev.source_id,
                )
            )
        else:
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
                can_assign=lambda target, event: _target_is_free_for_event(target, event, selected)
                and not _is_high_borrowed_bottom_event(
                    target,
                    event,
                    covered_pitch_classes=covered,
                    target_anchor_parts=target_anchor_parts,
                    config=config,
                ),
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
                can_assign=lambda target, event: _target_is_free_for_event(target, event, selected)
                and not _is_high_borrowed_bottom_event(
                    target,
                    event,
                    covered_pitch_classes=covered,
                    target_anchor_parts=target_anchor_parts,
                    config=config,
                ),
            )
            for target, event in support_pairs:
                if config.enforce_ranges:
                    event = fit_event_to_range(event, *target.midi_range)
                selected[target.id].append(event)
                last_pitch[target.id] = event.pitch_midi

        if config.preserve_active_voice_count:
            desired_active = min(
                _active_source_part_count(note_events, top_events, bottom_events, start),
                len(targets),
            )
            needed = desired_active - _active_target_count(selected, start)
            if needed > 0:
                represented_parts = _represented_source_parts(selected, start)
                existing_source_ids = _selected_source_ids(selected)
                covered_at_start = {
                    pitch % 12
                    for pitch in _active_pitches_from_assignments(selected, start)
                }
                active_source_pitch_classes = {
                    event.pitch_midi % 12
                    for event in (
                        *_active_events_at(note_events, start),
                        *_active_events_at(top_events, start),
                        *_active_events_at(bottom_events, start),
                    )
                    if event.pitch_midi is not None
                }
                next_source_change = _source_change_end(start, note_events, top_events, bottom_events)
                preserving_candidates = [
                    event
                    for event in group
                    if event.pitch_midi is not None
                    and event.source_id not in existing_source_ids
                    and (
                        len(active_source_pitch_classes) >= 2
                        or event.pitch_midi % 12 not in covered_at_start
                        or _continues_target_source_part(event, selected, targets)
                    )
                    and any(_target_is_free_for_event(target, event, selected) for target in targets)
                ]
                prepared_candidates: list[SourceEvent] = []
                for event in preserving_candidates:
                    prepared = _prepare_preserving_candidate(
                        event,
                        next_source_change,
                        covered_at_start,
                        config,
                    )
                    if prepared is not None:
                        prepared_candidates.append(prepared)
                preserving_candidates = prepared_candidates
                if config.prefer_jazz_color_tones:
                    bass_pitch = active_pitch_at(bottom_events, start)
                    bass_pitch_class = None if bass_pitch is None else int(bass_pitch) % 12
                    preserving_candidates.sort(
                        key=lambda ev: (
                            not _continues_target_source_part(ev, selected, targets),
                            _duplicate_color_tone_penalty(
                                ev,
                                bass_pitch_class=bass_pitch_class,
                                covered_pitch_classes=covered_at_start,
                            ),
                            ev.part_index in represented_parts,
                            not _is_new_onset(ev),
                            -ev.duration,
                            ev.source_id,
                        )
                    )
                else:
                    preserving_candidates.sort(
                        key=lambda ev: (
                            ev.part_index in represented_parts,
                            not _is_new_onset(ev),
                            -ev.duration,
                            ev.source_id,
                        )
                    )
                preserving_chosen = preserving_candidates[:needed]
                preserve_pairs: list[tuple[TargetPart, SourceEvent]] = []
                while preserving_chosen:
                    continuation_pairs: list[tuple[TargetPart, SourceEvent]] = []
                    reserved_target_ids: set[str] = set()
                    remaining_chosen: list[SourceEvent] = []
                    for event in preserving_chosen:
                        continuation_target = _target_continuing_source_part(event, selected, targets)
                        if continuation_target is not None and continuation_target.id not in reserved_target_ids:
                            continuation_pairs.append((continuation_target, event))
                            reserved_target_ids.add(continuation_target.id)
                        else:
                            remaining_chosen.append(event)

                    remaining_targets = [target for target in targets if target.id not in reserved_target_ids]
                    matched_pairs = _match_events_to_targets(
                        remaining_chosen,
                        remaining_targets,
                        last_pitch,
                        config,
                        can_assign=lambda target, event: _target_is_free_for_event(target, event, selected)
                        and not _is_high_borrowed_bottom_event(
                            target,
                            event,
                            covered_pitch_classes=covered_at_start,
                            target_anchor_parts=target_anchor_parts,
                            config=config,
                        ),
                    )
                    if len(matched_pairs) == len(remaining_chosen):
                        preserve_pairs = continuation_pairs + matched_pairs
                        break
                    preserving_chosen.pop()
                for target, event in preserve_pairs:
                    if config.enforce_ranges:
                        event = fit_event_to_range(event, *target.midi_range)
                    selected[target.id].append(event)
                    last_pitch[target.id] = event.pitch_midi

        if config.add_editorial_harmony:
            desired_active = min(config.editorial_harmony_target_active_parts, len(targets))
            needed = desired_active - _active_target_count(selected, start)
            support_end = _source_change_end(start, note_events, top_events, bottom_events)
            if needed > 0 and support_end is not None and support_end - start >= Fraction(1, 2):
                active_source_events = [
                    event
                    for event in (
                        *_active_events_at(note_events, start),
                        *_active_events_at(top_events, start),
                        *_active_events_at(bottom_events, start),
                    )
                    if event.pitch_midi is not None and event.end - start >= Fraction(1, 2)
                ]
                if len({event.pitch_midi % 12 for event in active_source_events if event.pitch_midi is not None}) < 2:
                    continue
                all_pitched_events = [
                    event
                    for event in (*note_events, *top_events, *bottom_events)
                    if event.pitch_midi is not None
                ]
                active_output_pitches = _active_pitches_from_assignments(selected, start)
                free_targets = [
                    target
                    for target in targets
                    if _target_is_free_for_interval(target, start, support_end, selected)
                ]
                for target in free_targets:
                    if needed <= 0:
                        break
                    generated_pitch = None
                    generated_kind = "harmony"
                    if config.add_editorial_thirds:
                        generated_pitch = _choose_editorial_third_pitch(
                            active_output_pitches,
                            active_source_events,
                            all_pitched_events,
                            target,
                            last_pitch,
                            start,
                            config,
                        )
                        if generated_pitch is not None:
                            generated_kind = "third"
                    if generated_pitch is None:
                        harmony_event = _choose_editorial_harmony_pitch(
                            active_source_events,
                            target,
                            last_pitch,
                            active_output_pitches,
                            config,
                        )
                        if harmony_event is None:
                            continue
                        generated_pitch = harmony_event.pitch_midi
                    event = SourceEvent(
                        source_id=f"generated:{generated_kind}:{target.id}:{start}",
                        part_index=-1,
                        event_index=0,
                        start=start,
                        duration=support_end - start,
                        pitch_midi=generated_pitch,
                        is_rest=False,
                        source_element=None,
                        source_tie_type=None,
                    )
                    selected[target.id].append(event)
                    last_pitch[target.id] = event.pitch_midi
                    active_output_pitches.append(int(event.pitch_midi))
                    needed -= 1

    if config.add_source_double_stops:
        _add_source_double_stops(
            selected,
            (*note_events, *top_events, *bottom_events),
            targets,
            config,
        )

    if config.add_editorial_harmony:
        _merge_adjacent_generated_harmony_events(selected)

    if initial_events_by_target and not config.preserve_active_voice_count:
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


class SixVoiceQuartetCompressionPolicy(AssignmentPolicy):
    """Compress exactly six source voices into the quartet profile.

    This keeps the current register-first quartet reducer available for four-
    and five-voice material, while making six-to-four compression an explicit
    policy choice. The highest and lowest source voices are pinned to Violin I
    and Cello; the four middle voices are selected into the two inner strings
    plus safely idle outer strings using the existing provenance-preserving
    inner-event selector.
    """

    def assign(
        self,
        context: ReductionContext,
        profile: EnsembleProfile,
        config: ReductionConfig,
    ) -> dict[str, list[SourceEvent]]:
        if profile.name != STRING_QUARTET.name:
            raise ValueError("SixVoiceQuartetCompressionPolicy only supports the string quartet profile.")
        if len(context.source_parts) != 6:
            raise ValueError(f"Expected exactly 6 source parts for six-voice quartet reduction; found {len(context.source_parts)}.")

        ordered_indices = _ordered_source_indices_by_median(context.source_parts)
        if len(ordered_indices) != 6:
            raise ValueError("Could not rank exactly 6 source voices by median pitch.")

        top_target = profile.top_part
        bottom_target = profile.bottom_part
        top_index = ordered_indices[0]
        bottom_index = ordered_indices[-1]

        top_events = _fit_events_to_target(
            _extract_voice_events_for_target(context.source_parts[top_index], top_index, top_target, config),
            top_target,
            config,
        )
        bottom_events = _fit_events_to_target(
            _extract_voice_events_for_target(context.source_parts[bottom_index], bottom_index, bottom_target, config),
            bottom_target,
            config,
        )
        middle_events = tuple(
            event
            for source_index in ordered_indices[1:-1]
            for event in _extract_context_events(
                context.source_parts[source_index],
                source_index,
                include_rests=False,
                chord_policy="all",
                config=config,
            )
        )

        fixed_outer_events = {
            top_target.id: _monophonic_events_for_target(top_events, top_target),
            bottom_target.id: _monophonic_events_for_target(bottom_events, bottom_target),
        }
        return _select_inner_events(
            middle_events,
            [event for event in top_events if not event.is_rest],
            [event for event in bottom_events if not event.is_rest],
            profile.parts,
            config,
            initial_events_by_target=fixed_outer_events,
            allow_supporting_doublings=True,
        )


class Take6QuartetCompressionPolicy(SixVoiceQuartetCompressionPolicy):
    """Six-voice close-harmony compression tuned through ``ReductionConfig``.

    The structural mapping is the same as the six-voice quartet policy: keep
    the outer source voices as melodic/bass anchors, then compress the four
    internal voices into the available quartet capacity. The Take 6 behavior is
    enabled by ``prefer_jazz_color_tones`` on the config so the same policy can
    stay transparent and testable.
    """


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
            events = _extract_voice_events_for_target(context.source_parts[source_index], source_index, target, config)
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


def _key_signature_changes(src_score: stream.Score) -> list[tuple[float, tuple[int, ...]]]:
    by_offset: dict[float, set[int]] = {}
    for key_sig in src_score.recurse().getElementsByClass(key.KeySignature):
        try:
            offset = float(key_sig.getOffsetInHierarchy(src_score))
        except Exception:
            offset = float(key_sig.offset)
        by_offset.setdefault(offset, set()).add(int(key_sig.sharps or 0))

    if not by_offset:
        return []
    if 0.0 not in by_offset:
        by_offset[0.0] = {0}
    return [(offset, tuple(sorted(sharps))) for offset, sharps in sorted(by_offset.items())]


def _transposed_key_signature_sharps(sharps: int, semitones: int) -> int:
    return int(key.KeySignature(sharps).transpose(semitones).sharps)


def key_signature_transposition_burden(src_score: stream.Score, semitones: int) -> float | None:
    """Return duration-weighted average printed key-signature complexity.

    The burden is measured as ``abs(sharps)`` after transposition.  Lower means
    fewer printed sharps/flats.  ``None`` means the source carries no key
    signature information, so this objective should not influence selection.
    """

    changes = _key_signature_changes(src_score)
    if not changes:
        return None

    highest_time = max(float(src_score.highestTime or 0.0), changes[-1][0])
    weighted = 0.0
    total = 0.0
    for index, (offset, sharps_values) in enumerate(changes):
        next_offset = changes[index + 1][0] if index + 1 < len(changes) else highest_time
        duration = max(0.0, next_offset - offset)
        if duration == 0.0 and index == len(changes) - 1:
            duration = 1.0

        transposed_abs = [
            abs(_transposed_key_signature_sharps(sharps, semitones))
            for sharps in sharps_values
        ]
        weighted += (sum(transposed_abs) / max(len(transposed_abs), 1)) * duration
        total += duration

    return weighted / total if total > 0 else 0.0


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
    key_signature_tessitura_tolerance: float = KEY_SIGNATURE_TESSITURA_TOLERANCE,
    key_signature_min_abs_improvement: float = KEY_SIGNATURE_MIN_ABS_IMPROVEMENT,
    key_signature_min_rel_improvement: float = KEY_SIGNATURE_MIN_REL_IMPROVEMENT,
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
    best_burden = key_signature_transposition_burden(src_score, best_semitones)
    if best_burden is not None:
        allowed_score = best_score + max(0.0, key_signature_tessitura_tolerance)
        key_candidates = []
        for semitones, score in candidate_scores:
            if score > allowed_score:
                continue
            burden = key_signature_transposition_burden(src_score, semitones)
            if burden is None:
                continue
            key_candidates.append((semitones, score, burden))

        if key_candidates:
            key_semitones, key_score, key_burden = min(
                key_candidates,
                key=lambda item: (item[2], item[1], abs(item[0] - best_semitones), abs(item[0]), item[0]),
            )
            improvement = best_burden - key_burden
            relative_improvement = improvement / best_burden if best_burden > 0 else 0.0
            if (
                improvement >= key_signature_min_abs_improvement
                and relative_improvement >= key_signature_min_rel_improvement
            ):
                best_semitones = key_semitones
                best_score = key_score
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
                config,
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
                config,
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
            events = _extract_voice_events_for_target(context.source_parts[source_index], source_index, target, config)
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
        source_title: str | None = None,
        reduction_composer: str = DEFAULT_REDUCTION_COMPOSER,
    ) -> None:
        self.profile = profile
        self.config = config or ReductionConfig()
        self.policy = policy or RegisterAssignmentPolicy()
        self.source_title = source_title
        self.reduction_composer = reduction_composer

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

        top_events = tuple(
            _extract_context_events(
                parts[top_index],
                top_index,
                include_rests=True,
                chord_policy="top",
                config=self.config,
            )
        )
        bottom_events = tuple(
            _extract_context_events(
                parts[bottom_index],
                bottom_index,
                include_rests=True,
                chord_policy="bottom",
                config=self.config,
            )
        )
        middle_events = tuple(
            event
            for index in middle_indices
            for event in _extract_context_events(
                parts[index],
                index,
                include_rests=False,
                chord_policy="all",
                config=self.config,
            )
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
        assignments = _smooth_isolated_handoffs(assignments, self.profile, self.config)

        out = stream.Score()
        set_reduction_metadata(
            out,
            src_score,
            self.profile,
            source_title=self.source_title,
            composer=self.reduction_composer,
        )

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
        if self.config.lower_high_cello_threshold is not None:
            _lower_high_cello_register(
                out,
                self.profile.bottom_part,
                self.config.lower_high_cello_threshold,
            )
        if self.config.add_editorial_dynamics:
            add_editorial_dynamics(
                out,
                context.bars,
                phrase_bars=self.config.dynamic_phrase_bars,
                max_hairpin_bars=self.config.dynamic_hairpin_bars,
            )
        validate_score_measures(out, context.bars)
        return out


def build_ensemble_score(
    src_score: stream.Score,
    profile: EnsembleProfile = STRING_QUARTET,
    *,
    config: ReductionConfig | None = None,
    policy: AssignmentPolicy | None = None,
    source_title: str | None = None,
    reduction_composer: str = DEFAULT_REDUCTION_COMPOSER,
) -> stream.Score:
    return ReductionBuilder(
        profile,
        config=config,
        policy=policy,
        source_title=source_title,
        reduction_composer=reduction_composer,
    ).build_score(src_score)


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
            events = _extract_voice_events_for_target(parts[source_index], source_index, target, config)
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
    set_reduction_metadata(out, src_score, PIANO_REDUCTION)

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
    preserve_active_voice_count: bool = False,
    add_editorial_harmony: bool = False,
    add_editorial_thirds: bool = False,
    editorial_harmony_target_active_parts: int = 4,
) -> stream.Score:
    return build_ensemble_score(
        src_score,
        STRING_QUARTET,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            max_borrowed_bottom_pitch=STRING_QUARTET.bottom_part.preferred_register[1],
        ),
        policy=RegisterAssignmentPolicy(),
    )


def build_six_voice_quartet_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    preserve_active_voice_count: bool = True,
    add_editorial_harmony: bool = True,
    add_editorial_thirds: bool = True,
    editorial_harmony_target_active_parts: int = 4,
) -> stream.Score:
    return build_ensemble_score(
        src_score,
        STRING_QUARTET,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            max_borrowed_bottom_pitch=STRING_QUARTET.bottom_part.preferred_register[1],
        ),
        policy=SixVoiceQuartetCompressionPolicy(),
    )


def build_take6_quartet_score(
    src_score: stream.Score,
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    preserve_active_voice_count: bool = True,
    add_source_double_stops: bool = False,
    normalize_short_note_rest_artifacts: bool = True,
    add_editorial_harmony: bool = False,
    add_editorial_thirds: bool = False,
    editorial_harmony_target_active_parts: int = 4,
) -> stream.Score:
    return build_ensemble_score(
        src_score,
        STRING_QUARTET,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            prefer_jazz_color_tones=True,
            add_source_double_stops=add_source_double_stops,
            normalize_short_note_rest_artifacts=normalize_short_note_rest_artifacts,
            min_preserved_trimmed_duration=Fraction(1, 3),
            max_borrowed_bottom_duplicate_pitch=60,
            lower_high_cello_threshold=55,
            smooth_isolated_handoff_double_stops=False,
            smooth_isolated_handoff_trim_overlaps=False,
            add_editorial_dynamics=False,
        ),
        policy=Take6QuartetCompressionPolicy(),
        reduction_composer=TAKE6_REDUCTION_COMPOSER,
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
    reduction_composer: str = DEFAULT_REDUCTION_COMPOSER,
) -> stream.Score:
    src_score = converter.parse(midi_path)
    src_score, chosen_semitones = _transpose_score_for_reduction(
        src_score,
        profile,
        semitones,
        candidate_semitones=candidate_semitones,
    )
    out_score = build_ensemble_score(
        src_score,
        profile,
        config=config,
        policy=policy,
        source_title=title_from_source_path(midi_path),
        reduction_composer=reduction_composer,
    )
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
    preserve_active_voice_count: bool = False,
    add_editorial_harmony: bool = False,
    add_editorial_thirds: bool = False,
    editorial_harmony_target_active_parts: int = 4,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    return reduce_to_ensemble(
        midi_path,
        STRING_QUARTET,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            max_borrowed_bottom_pitch=STRING_QUARTET.bottom_part.preferred_register[1],
        ),
        policy=RegisterAssignmentPolicy(),
        candidate_semitones=candidate_semitones,
    )


def reduce_six_to_quartet(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = "gesualdo_six_voice_quartet.musicxml",
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    preserve_active_voice_count: bool = True,
    add_editorial_harmony: bool = True,
    add_editorial_thirds: bool = True,
    editorial_harmony_target_active_parts: int = 4,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    return reduce_to_ensemble(
        midi_path,
        STRING_QUARTET,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            max_borrowed_bottom_pitch=STRING_QUARTET.bottom_part.preferred_register[1],
        ),
        policy=SixVoiceQuartetCompressionPolicy(),
        candidate_semitones=candidate_semitones,
    )


def reduce_take6_to_quartet(
    midi_path: str | Path,
    semitones: int | None = None,
    out_path: str | Path = "take6_quartet.musicxml",
    *,
    enforce_ranges: bool = ENFORCE_RANGES,
    register_split: int = REGISTER_SPLIT,
    preserve_active_voice_count: bool = True,
    add_source_double_stops: bool = False,
    normalize_short_note_rest_artifacts: bool = True,
    add_editorial_harmony: bool = False,
    add_editorial_thirds: bool = False,
    editorial_harmony_target_active_parts: int = 4,
    candidate_semitones: Sequence[int] = DEFAULT_TRANSPOSITION_CANDIDATES,
) -> stream.Score:
    out_score = reduce_to_ensemble(
        midi_path,
        STRING_QUARTET,
        semitones=semitones,
        out_path=out_path,
        config=ReductionConfig(
            enforce_ranges=enforce_ranges,
            register_split=register_split,
            preserve_active_voice_count=preserve_active_voice_count,
            add_editorial_harmony=add_editorial_harmony,
            add_editorial_thirds=add_editorial_thirds,
            editorial_harmony_target_active_parts=editorial_harmony_target_active_parts,
            prefer_jazz_color_tones=True,
            add_source_double_stops=add_source_double_stops,
            normalize_short_note_rest_artifacts=normalize_short_note_rest_artifacts,
            min_preserved_trimmed_duration=Fraction(1, 3),
            max_borrowed_bottom_duplicate_pitch=60,
            lower_high_cello_threshold=55,
            smooth_isolated_handoff_double_stops=False,
            smooth_isolated_handoff_trim_overlaps=False,
            add_editorial_dynamics=False,
        ),
        policy=Take6QuartetCompressionPolicy(),
        candidate_semitones=candidate_semitones,
        reduction_composer=TAKE6_REDUCTION_COMPOSER,
    )
    normalize_musescore_rhythm_artifacts(out_score)
    lower_take6_high_cello_register(out_score)
    out_score.write("musicxml", fp=str(out_path))
    return out_score


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
