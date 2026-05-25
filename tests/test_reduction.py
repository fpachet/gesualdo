from fractions import Fraction

import pytest

pytest.importorskip("music21")

from music21 import meter, note, stream

from gesualdo_reduction.reduction import (
    PIANO_REDUCTION,
    build_bar_map,
    build_piano_score,
    build_quartet_plus_viole_sweetspot_score,
    build_quartet_plus_viole_score,
    build_quartet_score,
    choose_global_transposition,
    extract_events,
    ql_to_fraction,
    reduce_to_piano,
    validate_score_measures,
)


def make_part(name, events):
    part = stream.Part()
    part.partName = name
    part.insert(0, meter.TimeSignature("4/4"))
    for offset, duration, pitch_name in events:
        element = note.Rest(quarterLength=duration) if pitch_name is None else note.Note(pitch_name, quarterLength=duration)
        part.insert(offset, element)
    return part


def make_score(parts):
    score = stream.Score()
    for part in parts:
        score.insert(0, part)
    return score


def assert_measures_are_exact(score, bars):
    validate_score_measures(score, bars)
    for part in score.parts:
        for measure, bar in zip(part.getElementsByClass(stream.Measure), bars, strict=True):
            total = sum((ql_to_fraction(el.quarterLength) for el in measure.notesAndRests), Fraction(0, 1))
            assert total == bar.duration


def test_outer_repeated_notes_are_not_merged():
    score = make_score(
        [
            make_part("top", [(0, 1, "C6"), (1, 1, "C6"), (2, 2, None)]),
            make_part("middle 1", [(0, 1, "E4"), (1, 1, "F4"), (2, 2, None)]),
            make_part("middle 2", [(0, 2, "G4"), (2, 2, None)]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)
    violin_1_measure = list(reduced.parts[0].getElementsByClass(stream.Measure))[0]
    violin_1_notes = [el for el in violin_1_measure.notesAndRests if el.isNote]

    assert [ql_to_fraction(el.offset) for el in violin_1_notes] == [Fraction(0, 1), Fraction(1, 1)]
    assert [ql_to_fraction(el.quarterLength) for el in violin_1_notes] == [Fraction(1, 1), Fraction(1, 1)]
    assert violin_1_notes[0].editorial.sourceEventId != violin_1_notes[1].editorial.sourceEventId


def test_notes_crossing_barlines_are_split_and_tied():
    score = make_score(
        [
            make_part("top", [(0, 6, "C6")]),
            make_part("middle 1", [(0, 1, "E4")]),
            make_part("middle 2", [(0, 1, "G4")]),
            make_part("bottom", [(0, 6, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)
    violin_1_measures = list(reduced.parts[0].getElementsByClass(stream.Measure))
    first_note = violin_1_measures[0].notes[0]
    second_note = violin_1_measures[1].notes[0]

    assert ql_to_fraction(first_note.quarterLength) == Fraction(4, 1)
    assert ql_to_fraction(second_note.quarterLength) == Fraction(2, 1)
    assert first_note.tie.type == "start"
    assert second_note.tie.type == "stop"
    assert first_note.editorial.sourceEventId == second_note.editorial.sourceEventId


def test_middle_reduction_only_outputs_real_source_note_events():
    score = make_score(
        [
            make_part("top", [(0, 4, "B5")]),
            make_part("middle 1", [(0, Fraction(3, 2), "E4")]),
            make_part("middle 2", [(0, Fraction(1, 2), "G4"), (2, 1, "A4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)

    source_events = {}
    for part_index in (1, 2):
        for event in extract_events(score.parts[part_index], part_index, include_rests=False, chord_policy="all"):
            source_events[event.source_id] = event.duration

    middle_output_notes = []
    for part in reduced.parts[1:3]:
        for measure in part.getElementsByClass(stream.Measure):
            middle_output_notes.extend(measure.notes)

    assert middle_output_notes
    for output_note in middle_output_notes:
        source_id = output_note.editorial.sourceEventId
        assert source_id in source_events
        assert ql_to_fraction(output_note.quarterLength) == source_events[source_id]


def test_quartet_plus_viole_maps_five_voices_one_to_one_by_register():
    score = make_score(
        [
            make_part("tenor", [(0, 4, "E4")]),
            make_part("cantus", [(0, 4, "C6")]),
            make_part("quintus", [(0, 4, "A4")]),
            make_part("bassus", [(0, 4, "C2")]),
            make_part("altus", [(0, 4, "G5")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_plus_viole_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)
    assert [part.partName for part in reduced.parts] == [
        "Violin I",
        "Violin II",
        "Viole d'amour",
        "Viola",
        "Violoncello",
    ]

    first_source_indices = []
    for part in reduced.parts:
        measure = list(part.getElementsByClass(stream.Measure))[0]
        first_source_indices.append(measure.notes[0].editorial.sourcePartIndex)

    assert first_source_indices == [1, 4, 2, 0, 3]


def test_quartet_plus_viole_reduces_six_voices_to_five_instruments():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("inner 1", [(0, 4, "D5")]),
            make_part("inner 2", [(0, 4, "A4")]),
            make_part("inner 3", [(0, 4, "G4")]),
            make_part("inner 4", [(0, 4, "E4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_plus_viole_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)
    assert len(reduced.parts) == 5

    inner_notes = []
    for part in reduced.parts[1:4]:
        measure = list(part.getElementsByClass(stream.Measure))[0]
        inner_notes.extend(measure.notes)

    assert len(inner_notes) == 3
    assert all(hasattr(output_note.editorial, "sourceEventId") for output_note in inner_notes)


def test_quartet_plus_viole_sweetspot_can_remap_inner_voices():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("upper middle", [(0, 4, "B4")]),
            make_part("lower weighted", [(0, 3, "D3"), (3, Fraction(1, 2), "G4"), (Fraction(7, 2), Fraction(1, 2), "G4")]),
            make_part("higher weighted", [(0, 3, "C5"), (3, Fraction(1, 2), "E4"), (Fraction(7, 2), Fraction(1, 2), "E4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_plus_viole_sweetspot_score(score, enforce_ranges=False, prefer_registers=False)

    assert_measures_are_exact(reduced, bars)

    first_source_indices = []
    for part in reduced.parts:
        measure = list(part.getElementsByClass(stream.Measure))[0]
        first_source_indices.append(measure.notes[0].editorial.sourcePartIndex)

    assert first_source_indices == [0, 1, 3, 2, 4]


def test_quartet_plus_viole_sweetspot_prefers_register_octaves():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("upper middle", [(0, 4, "B3")]),
            make_part("viole candidate", [(0, 4, "A3")]),
            make_part("viola candidate", [(0, 4, "E3")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    reduced = build_quartet_plus_viole_sweetspot_score(score, enforce_ranges=True)
    violin_2_measure = list(reduced.parts[1].getElementsByClass(stream.Measure))[0]

    assert violin_2_measure.notes[0].pitch.midi == 71


def test_piano_reduction_distributes_voices_across_two_staves(tmp_path):
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("upper middle", [(0, 4, "G5")]),
            make_part("middle", [(0, 4, "A4")]),
            make_part("lower middle", [(0, 4, "E4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    reduced = build_piano_score(score, enforce_ranges=False)

    assert len(reduced.parts) == 2
    right_measure = list(reduced.parts[0].getElementsByClass(stream.Measure))[0]
    left_measure = list(reduced.parts[1].getElementsByClass(stream.Measure))[0]
    assert len(right_measure.voices) == 3
    assert len(left_measure.voices) == 2

    right_source_indices = [voice.notes[0].editorial.sourcePartIndex for voice in right_measure.voices]
    left_source_indices = [voice.notes[0].editorial.sourcePartIndex for voice in left_measure.voices]
    assert right_source_indices == [0, 1, 2]
    assert left_source_indices == [3, 4]

    out_path = tmp_path / "piano.musicxml"
    reduced.write("musicxml", fp=str(out_path))
    musicxml = out_path.read_text()
    assert "<part-name>Piano</part-name>" in musicxml
    assert "<staves>2</staves>" in musicxml


def test_global_transposition_prefers_target_registers():
    score = make_score(
        [
            make_part("top", [(0, 4, "C7")]),
            make_part("bottom", [(0, 4, "C5")]),
        ]
    )

    choice = choose_global_transposition(score, PIANO_REDUCTION, candidate_semitones=range(-12, 1))

    assert choice.semitones == -12
    assert choice.score < dict(choice.candidate_scores)[0]


def test_reduce_to_piano_uses_adaptive_transposition_by_default(tmp_path):
    score = make_score(
        [
            make_part("top", [(0, 4, "C7")]),
            make_part("bottom", [(0, 4, "C5")]),
        ]
    )
    midi_path = tmp_path / "source.mid"
    out_path = tmp_path / "piano.musicxml"
    score.write("midi", fp=str(midi_path))

    reduced = reduce_to_piano(midi_path, out_path=out_path, candidate_semitones=range(-12, 1))

    assert reduced.editorial.globalTransposition == -12
    assert out_path.exists()
