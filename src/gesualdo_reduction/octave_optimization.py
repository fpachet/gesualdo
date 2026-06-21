"""Pitch-class-preserving octave optimization for reduced string parts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from music21 import chord, converter, note, stream

from gesualdo_reduction.reduction import RANGES


PREFERRED_REGISTERS = {
    "vln1": (67, 96),
    "vln2": (60, 88),
    "vla": (48, 72),
    "vda": (55, 79),
    "vc": (36, 60),
}


@dataclass(frozen=True)
class OctaveOptimizationConfig:
    """Weights and constraints for octave optimization."""

    max_octave_shift: int = 1
    leap_free_interval: int = 7
    transition_weight: float = 1.0
    displacement_weight: float = 12.0
    register_weight: float = 1.0
    long_note_change_weight: float = 2.0
    max_changes: int | None = None
    protect_bass_anchor: bool = True


@dataclass(frozen=True)
class OctaveChange:
    """One event changed by octave optimization."""

    part: str
    measure: str
    offset: float
    old_pitches: tuple[int, ...]
    new_pitches: tuple[int, ...]
    duration: float
    reason: str

    def as_row(self) -> dict[str, str]:
        return {
            "part": self.part,
            "measure": self.measure,
            "offset": f"{self.offset:.6g}",
            "old_pitches": ",".join(str(pitch) for pitch in self.old_pitches),
            "new_pitches": ",".join(str(pitch) for pitch in self.new_pitches),
            "duration": f"{self.duration:.6g}",
            "reason": self.reason,
        }


@dataclass
class _Event:
    element: note.Note | chord.Chord
    part_name: str
    target_id: str
    measure: str
    offset: float
    duration: float
    pitches: tuple[int, ...]


def _target_id_for_part(part: stream.Part, index: int) -> str | None:
    name = " ".join(
        value
        for value in (part.partName or "", part.partAbbreviation or "")
        if value
    ).lower()
    if "violoncello" in name or "cello" in name or "vc" in name:
        return "vc"
    if "viole" in name:
        return "vda"
    if "viola" in name or "vla" in name:
        return "vla"
    if "violin ii" in name or "vln ii" in name or "violin 2" in name:
        return "vln2"
    if "violin i" in name or "vln i" in name or "violin 1" in name:
        return "vln1"
    if "violin" in name:
        return "vln1" if index == 0 else "vln2"
    return None


def _part_name(part: stream.Part, index: int) -> str:
    return (part.partName or part.partAbbreviation or f"Part {index + 1}").strip()


def _measure_number(element) -> str:
    measure = element.getContextByClass(stream.Measure)
    value = getattr(measure, "number", None)
    return "" if value is None else str(value)


def _absolute_offset(element, part: stream.Part) -> float:
    try:
        return float(element.getOffsetInHierarchy(part))
    except Exception:
        return float(element.offset)


def _event_pitches(element: note.Note | chord.Chord) -> tuple[int, ...]:
    if isinstance(element, chord.Chord):
        return tuple(int(round(pitch.midi)) for pitch in element.pitches)
    return (int(round(element.pitch.midi)),)


def _part_events(part: stream.Part, index: int) -> list[_Event]:
    target_id = _target_id_for_part(part, index)
    if target_id is None:
        return []
    part_name = _part_name(part, index)
    events: list[_Event] = []
    for element in part.recurse().notes:
        if not isinstance(element, (note.Note, chord.Chord)):
            continue
        duration = float(element.quarterLength)
        if duration <= 0:
            continue
        events.append(
            _Event(
                element=element,
                part_name=part_name,
                target_id=target_id,
                measure=_measure_number(element),
                offset=_absolute_offset(element, part),
                duration=duration,
                pitches=_event_pitches(element),
            )
        )
    return sorted(events, key=lambda event: (event.offset, event.duration, event.pitches))


def _candidate_shifts(event: _Event, config: OctaveOptimizationConfig) -> list[int]:
    low, high = RANGES[event.target_id]
    candidates: list[int] = []
    for octave_shift in range(-config.max_octave_shift, config.max_octave_shift + 1):
        semitones = octave_shift * 12
        shifted = tuple(pitch + semitones for pitch in event.pitches)
        if all(low <= pitch <= high for pitch in shifted):
            candidates.append(semitones)
    return candidates or [0]


def _register_cost(event: _Event, shifted_pitches: Sequence[int]) -> float:
    low, high = PREFERRED_REGISTERS.get(event.target_id, RANGES[event.target_id])
    center = (low + high) / 2.0
    total = 0.0
    for pitch in shifted_pitches:
        if low <= pitch <= high:
            total += abs(pitch - center) / 24.0
        else:
            total += 2.0 + min(abs(pitch - low), abs(pitch - high)) / 6.0
    return total / max(len(shifted_pitches), 1)


def _min_pitch_distance(left: Sequence[int], right: Sequence[int]) -> int:
    return min(abs(a - b) for a in left for b in right)


def _transition_cost(left: Sequence[int], right: Sequence[int], config: OctaveOptimizationConfig) -> float:
    distance = _min_pitch_distance(left, right)
    excess = max(0, distance - config.leap_free_interval)
    return float(excess * excess)


def _node_cost(event: _Event, shift: int, config: OctaveOptimizationConfig) -> float:
    shifted = tuple(pitch + shift for pitch in event.pitches)
    octave_distance = abs(shift) / 12.0
    cost = config.register_weight * _register_cost(event, shifted)
    cost += config.displacement_weight * octave_distance
    if shift and event.duration >= 2.0:
        cost += config.long_note_change_weight * event.duration
    if shift and config.protect_bass_anchor and event.target_id == "vc" and min(event.pitches) <= 48:
        cost += 8.0
    return cost


def _optimize_part(events: Sequence[_Event], config: OctaveOptimizationConfig) -> list[int]:
    if not events:
        return []

    candidates = [_candidate_shifts(event, config) for event in events]
    costs: list[dict[int, float]] = []
    previous_choice: list[dict[int, int | None]] = []
    for index, event in enumerate(events):
        layer_costs: dict[int, float] = {}
        layer_previous: dict[int, int | None] = {}
        for shift in candidates[index]:
            shifted = tuple(pitch + shift for pitch in event.pitches)
            node_cost = _node_cost(event, shift, config)
            if index == 0:
                layer_costs[shift] = node_cost
                layer_previous[shift] = None
                continue
            best_prev = None
            best_cost = float("inf")
            for prev_shift, prev_cost in costs[index - 1].items():
                previous_event = events[index - 1]
                previous_shifted = tuple(pitch + prev_shift for pitch in previous_event.pitches)
                transition = config.transition_weight * _transition_cost(previous_shifted, shifted, config)
                total = prev_cost + node_cost + transition
                if total < best_cost:
                    best_cost = total
                    best_prev = prev_shift
            layer_costs[shift] = best_cost
            layer_previous[shift] = best_prev
        costs.append(layer_costs)
        previous_choice.append(layer_previous)

    final_shift = min(costs[-1], key=lambda shift: (costs[-1][shift], abs(shift)))
    result = [0] * len(events)
    current: int | None = final_shift
    for index in range(len(events) - 1, -1, -1):
        if current is None:
            current = 0
        result[index] = current
        current = previous_choice[index][current]

    if config.max_changes is not None:
        changed_indices = [index for index, shift in enumerate(result) if shift]
        if len(changed_indices) > config.max_changes:
            # Keep only the changes with the largest local transition improvement.
            scored = []
            for index in changed_indices:
                before = _local_transition_cost(events, result, index, 0, config)
                after = _local_transition_cost(events, result, index, result[index], config)
                scored.append((before - after, index))
            keep = {index for _gain, index in sorted(scored, reverse=True)[: config.max_changes]}
            result = [shift if index in keep else 0 for index, shift in enumerate(result)]
    return result


def _local_transition_cost(
    events: Sequence[_Event],
    shifts: Sequence[int],
    index: int,
    replacement_shift: int,
    config: OctaveOptimizationConfig,
) -> float:
    cost = 0.0
    current = tuple(pitch + replacement_shift for pitch in events[index].pitches)
    if index > 0:
        previous = tuple(pitch + shifts[index - 1] for pitch in events[index - 1].pitches)
        cost += _transition_cost(previous, current, config)
    if index + 1 < len(events):
        next_pitches = tuple(pitch + shifts[index + 1] for pitch in events[index + 1].pitches)
        cost += _transition_cost(current, next_pitches, config)
    return cost


def _transpose_element_by_octave(element: note.Note | chord.Chord, semitones: int) -> None:
    if semitones == 0:
        return
    if isinstance(element, chord.Chord):
        for chord_note in element.notes:
            chord_note.pitch.transpose(semitones, inPlace=True)
        return
    element.pitch.transpose(semitones, inPlace=True)


def _reason(events: Sequence[_Event], shifts: Sequence[int], index: int, config: OctaveOptimizationConfig) -> str:
    before = _local_transition_cost(events, [0 for _ in events], index, 0, config)
    after = _local_transition_cost(events, shifts, index, shifts[index], config)
    return f"local_transition_cost {before:.6g}->{after:.6g}; shift={shifts[index]}"


def optimize_score_octaves(
    score: stream.Score,
    *,
    config: OctaveOptimizationConfig | None = None,
) -> list[OctaveChange]:
    """Choose better octave placements while preserving pitch classes and rhythm."""

    config = config or OctaveOptimizationConfig()
    changes: list[OctaveChange] = []
    for part_index, part in enumerate(score.parts):
        events = _part_events(part, part_index)
        shifts = _optimize_part(events, config)
        for index, (event, shift) in enumerate(zip(events, shifts, strict=True)):
            if shift == 0:
                continue
            old_pitches = event.pitches
            new_pitches = tuple(pitch + shift for pitch in event.pitches)
            _transpose_element_by_octave(event.element, shift)
            changes.append(
                OctaveChange(
                    part=event.part_name,
                    measure=event.measure,
                    offset=event.offset,
                    old_pitches=old_pitches,
                    new_pitches=new_pitches,
                    duration=event.duration,
                    reason=_reason(events, shifts, index, config),
                )
            )
    return changes


def optimize_musicxml_octaves(
    input_path: str | Path,
    output_path: str | Path,
    *,
    config: OctaveOptimizationConfig | None = None,
) -> list[OctaveChange]:
    """Read MusicXML, optimize octaves, and write a new MusicXML file."""

    score = converter.parse(input_path)
    changes = optimize_score_octaves(score, config=config)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(output_path))
    return changes
