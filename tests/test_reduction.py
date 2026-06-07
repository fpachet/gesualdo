from fractions import Fraction

import pytest

pytest.importorskip("music21")

from music21 import dynamics, meter, note, stream

from gesualdo_reduction.reduction import (
    PIANO_REDUCTION,
    ReductionConfig,
    SourceEvent,
    _merge_adjacent_generated_harmony_events,
    build_ensemble_score,
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


def test_source_voice_enrichment_preserves_duplicate_pitch_class_line():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("middle 1", [(0, 4, "E4")]),
            make_part("middle 2", [(0, 4, "E5")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    plain = build_quartet_score(score, enforce_ranges=False)
    enriched = build_quartet_score(score, enforce_ranges=False, preserve_active_voice_count=True)

    plain_middle_notes = [
        element
        for part in plain.parts[1:3]
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]
    enriched_middle_notes = [
        element
        for part in enriched.parts[1:3]
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]

    assert len(plain_middle_notes) == 1
    assert len(enriched_middle_notes) == 2
    assert {element.editorial.sourcePartIndex for element in enriched_middle_notes} == {1, 2}


def test_source_voice_enrichment_keeps_duplicate_pitch_class_source_line():
    score = make_score(
        [
            make_part("top", [(0, 4, None)]),
            make_part("upper", [(0, 4, "B-4")]),
            make_part("duplicate", [(0, 4, "F#4")]),
            make_part("middle", [(0, 4, "C#4")]),
            make_part("bottom", [(0, 4, "F#3")]),
        ]
    )

    plain = build_quartet_score(score, enforce_ranges=False)
    enriched = build_quartet_score(score, enforce_ranges=False, preserve_active_voice_count=True)

    plain_notes = [
        element
        for part in plain.parts
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]
    enriched_notes = [
        element
        for part in enriched.parts
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]

    assert len(plain_notes) == 3
    assert len(enriched_notes) == 4
    assert any(element.pitch.nameWithOctave == "F#4" for element in enriched_notes)


def test_source_voice_enrichment_avoids_bare_octave_duplicate_pickup():
    score = make_score(
        [
            make_part("top", [(0, 1, None), (1, 3, "E5")]),
            make_part("inner 1", [(0, 1, "C#4"), (1, 3, "E4")]),
            make_part("inner 2", [(0, 1, None), (1, 3, "A4")]),
            make_part("bottom", [(0, 4, "C#3")]),
        ]
    )

    enriched = build_quartet_score(score, enforce_ranges=False, preserve_active_voice_count=True)
    first_beat_notes = [
        element
        for part in enriched.parts
        for element in part.flatten().notes
        if ql_to_fraction(element.offset) <= Fraction(0, 1)
        < ql_to_fraction(element.offset) + ql_to_fraction(element.quarterLength)
    ]

    assert [element.pitch.name for element in first_beat_notes].count("C#") == 1


def test_editorial_harmony_can_fill_fourth_string_with_marked_chord_tone():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("middle 1", [(0, 4, "E4")]),
            make_part("middle 2", [(0, 4, None)]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    reduced = build_quartet_score(score, enforce_ranges=False, add_editorial_harmony=True)
    measure_notes = [
        element
        for part in reduced.parts
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]
    generated_notes = [
        element
        for element in measure_notes
        if element.editorial.sourceEventId.startswith("generated:harmony:")
    ]

    assert len(measure_notes) == 4
    assert len(generated_notes) == 1
    assert generated_notes[0].editorial.sourcePartIndex == -1
    assert generated_notes[0].pitch.pitchClass in {0, 4}


def test_editorial_thirds_can_complete_bare_fifth_shell():
    score = make_score(
        [
            make_part("top", [(0, 4, "G5"), (4, 4, "B5")]),
            make_part("fifth", [(0, 8, "D5")]),
            make_part("root", [(0, 8, "G4")]),
            make_part("empty", [(0, 8, None)]),
        ]
    )

    reduced = build_quartet_score(
        score,
        enforce_ranges=False,
        add_editorial_harmony=True,
        add_editorial_thirds=True,
    )
    generated_thirds = [
        element
        for part in reduced.parts
        for element in part.flatten().notes
        if element.editorial.sourceEventId.startswith("generated:third:")
    ]

    assert generated_thirds
    assert generated_thirds[0].editorial.sourcePartIndex == -1
    assert generated_thirds[0].pitch.name == "B"


def test_enrichment_does_not_hide_later_chromatic_source_note():
    score = make_score(
        [
            make_part("top", [(0, 3, None), (3, 1, "A4")]),
            make_part("chromatic", [(0, 1, None), (1, 1, "G#4"), (2, 2, "A4")]),
            make_part("long duplicate", [(0, 4, "E4")]),
            make_part("inner", [(0, 1, None), (1, 1, "B3"), (2, 2, "C4")]),
            make_part("bottom", [(0, 4, "E3")]),
        ]
    )

    reduced = build_quartet_score(
        score,
        enforce_ranges=False,
        preserve_active_voice_count=True,
        add_editorial_harmony=True,
    )
    notes_at_g_sharp = [
        element
        for part in reduced.parts
        for element in part.flatten().notes
        if ql_to_fraction(element.offset) <= Fraction(1, 1)
        < ql_to_fraction(element.offset) + ql_to_fraction(element.quarterLength)
    ]

    assert any(element.pitch.name == "G#" for element in notes_at_g_sharp)


def test_editorial_harmony_merges_adjacent_repeated_support_notes():
    selected = {
        "vln1": [
            SourceEvent("generated:harmony:vln1:1", -1, 0, Fraction(1, 1), Fraction(1, 2), 72, False),
            SourceEvent("generated:third:vln1:3/2", -1, 0, Fraction(3, 2), Fraction(1, 2), 72, False),
            SourceEvent("generated:third:vln1:2", -1, 0, Fraction(2, 1), Fraction(1, 1), 72, False),
        ]
    }

    _merge_adjacent_generated_harmony_events(selected)

    assert selected["vln1"] == [
        SourceEvent("generated:harmony:vln1:1", -1, 0, Fraction(1, 1), Fraction(2, 1), 72, False)
    ]


def test_idle_outer_part_can_borrow_continuous_line_for_coverage():
    score = make_score(
        [
            make_part("top", [(0, 8, None), (8, 4, "C6")]),
            make_part("middle 1", [(2, 2, "E4"), (4, 2, "E4"), (6, 2, "G4"), (8, 4, None)]),
            make_part("middle 2", [(2, 2, "C4"), (4, 2, "C4"), (6, 2, "D4"), (8, 4, None)]),
            make_part("middle 3", [(2, 2, "G3"), (4, 2, "G3"), (6, 2, "B-3"), (8, 4, None)]),
            make_part("bottom", [(0, 8, "C3"), (8, 4, "C3")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)

    output_at_six = []
    for part in reduced.parts:
        for element in part.flatten().notes:
            start = ql_to_fraction(element.offset)
            end = start + ql_to_fraction(element.quarterLength)
            if start <= Fraction(6, 1) < end:
                output_at_six.append(element.pitch.midi % 12)

    assert set(output_at_six) == {0, 2, 7, 10}

    borrowed_violin_1_notes = [
        element
        for element in reduced.parts[0].flatten().notes
        if ql_to_fraction(element.offset) < Fraction(8, 1)
    ]
    assert [ql_to_fraction(element.offset) for element in borrowed_violin_1_notes] == [
        Fraction(2, 1),
        Fraction(4, 1),
        Fraction(6, 1),
    ]
    assert [element.pitch.nameWithOctave for element in borrowed_violin_1_notes] == ["C4", "C4", "D4"]
    assert {element.editorial.sourcePartIndex for element in borrowed_violin_1_notes} == {2}


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


def test_quartet_reduction_exports_editorial_dynamics_and_hairpins(tmp_path):
    score = make_score(
        [
            make_part("top", [(0, 8, "C5"), (8, 1, "G5"), (9, 1, "A5"), (10, 1, "B5"), (11, 1, "C6")]),
            make_part("middle 1", [(0, 8, None), (8, 1, "E4"), (9, 1, "F4"), (10, 1, "G4"), (11, 1, "A4")]),
            make_part("middle 2", [(0, 4, None), (4, 4, "C4"), (8, 4, "E4")]),
            make_part("bottom", [(0, 12, "C3")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_quartet_score(score, enforce_ranges=False)
    assert_measures_are_exact(reduced, bars)

    out_path = tmp_path / "quartet_with_dynamics.musicxml"
    reduced.write("musicxml", fp=str(out_path))
    musicxml = out_path.read_text()
    assert "<dynamics" in musicxml
    assert "<wedge" in musicxml


def test_editorial_dynamics_can_be_disabled(tmp_path):
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("middle 1", [(0, 4, "E4")]),
            make_part("middle 2", [(0, 4, "G4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    reduced = build_ensemble_score(
        score,
        config=ReductionConfig(enforce_ranges=False, add_editorial_dynamics=False),
    )
    out_path = tmp_path / "quartet_without_dynamics.musicxml"
    reduced.write("musicxml", fp=str(out_path))
    musicxml = out_path.read_text()
    assert "<dynamics" not in musicxml
    assert "<wedge" not in musicxml


def test_editorial_hairpins_are_locally_bounded():
    score = make_score(
        [
            make_part("top", [(0, 8, "C5"), (8, 1, "G5"), (9, 1, "A5"), (10, 1, "B5"), (11, 1, "C6")]),
            make_part("middle 1", [(0, 8, None), (8, 1, "E4"), (9, 1, "F4"), (10, 1, "G4"), (11, 1, "A4")]),
            make_part("middle 2", [(0, 4, None), (4, 4, "C4"), (8, 4, "E4")]),
            make_part("bottom", [(0, 12, "C3")]),
        ]
    )
    max_bars = 2

    reduced = build_ensemble_score(
        score,
        config=ReductionConfig(
            enforce_ranges=False,
            dynamic_phrase_bars=4,
            dynamic_hairpin_bars=max_bars,
        ),
    )

    wedges = [
        spanner
        for spanner in reduced.spannerBundle
        if isinstance(spanner, dynamics.DynamicWedge)
    ]
    assert wedges
    for wedge in wedges:
        start_note, end_note = wedge.getSpannedElements()
        absolute_start = ql_to_fraction(start_note.getOffsetInHierarchy(reduced))
        absolute_end = ql_to_fraction(end_note.getOffsetInHierarchy(reduced))
        duration = absolute_end - absolute_start
        assert duration <= Fraction(max_bars * 4, 1)


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
