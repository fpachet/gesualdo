from fractions import Fraction

import pytest

pytest.importorskip("music21")

from music21 import clef, dynamics, key, meter, note, pitch, stream, tie

from gesualdo_reduction.notation_cleanup import cleanup_score
from gesualdo_reduction.octave_optimization import optimize_score_octaves
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
    build_six_voice_quartet_score,
    build_take6_quartet_score,
    choose_global_transposition,
    extract_events,
    key_signature_transposition_burden,
    normalize_short_note_rest_artifacts,
    ql_to_fraction,
    reduce_to_piano,
    reduce_to_quartet,
    reduce_take6_to_quartet,
    title_from_source_path,
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


def test_cleanup_score_hides_redundant_naturals_and_adds_final_barlines():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin I"
    measure = stream.Measure(number=1)
    measure.insert(0, key.KeySignature(0))
    first = note.Note("C4", quarterLength=1)
    first.pitch.accidental = pitch.Accidental("natural")
    second = note.Note("D4", quarterLength=3)
    measure.insert(0, first)
    measure.insert(1, second)
    part.insert(0, measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.suppressed_naturals == 1
    assert first.pitch.accidental.displayStatus is False
    assert measure.rightBarline.type == "final"


def test_cleanup_score_preserves_key_signature_natural():
    score = stream.Score()
    part = stream.Part()
    measure = stream.Measure(number=1)
    measure.insert(0, key.KeySignature(-1))
    b_natural = note.Note("B4", quarterLength=4)
    b_natural.pitch.accidental = pitch.Accidental("natural")
    measure.insert(0, b_natural)
    part.insert(0, measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.suppressed_naturals == 0
    assert b_natural.pitch.accidental.displayStatus is not False


def test_cleanup_score_clean_mode_removes_dynamics_and_hairpins():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin I"
    measure = stream.Measure(number=1)
    first = note.Note("C4", quarterLength=2)
    second = note.Note("D4", quarterLength=2)
    measure.insert(0, first)
    measure.insert(2, second)
    measure.insert(0, dynamics.Dynamic("mf"))
    part.insert(0, measure)
    score.insert(0, part)
    hairpin = dynamics.Crescendo()
    hairpin.addSpannedElements([first, second])
    score.insert(0, hairpin)

    report = cleanup_score(score, clean_dynamics=True)

    assert report.removed_dynamics == 1
    assert report.removed_hairpins == 1
    assert not list(score.recurse().getElementsByClass(dynamics.Dynamic))
    assert not list(score.recurse().getElementsByClass(dynamics.DynamicWedge))


def test_cleanup_score_hides_accidentals_on_tie_continuations():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin I"
    measure = stream.Measure(number=1)
    first = note.Note("C#4", quarterLength=2)
    first.tie = tie.Tie("start")
    second = note.Note("C#4", quarterLength=2)
    second.tie = tie.Tie("stop")
    second.pitch.accidental.displayStatus = True
    measure.insert(0, first)
    measure.insert(2, second)
    part.insert(0, measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.suppressed_tie_continuation_accidentals == 1
    assert second.pitch.accidental.displayStatus is False


def test_cleanup_score_normalizes_dangling_ties():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin II"
    measure = stream.Measure(number=1)
    dangling_start = note.Note("D4", quarterLength=2)
    dangling_start.tie = tie.Tie("start")
    tied_start = note.Note("G4", quarterLength=1)
    tied_start.tie = tie.Tie("start")
    tied_continue = note.Note("G4", quarterLength=1)
    tied_continue.tie = tie.Tie("continue")
    measure.insert(0, dangling_start)
    measure.insert(2, tied_start)
    measure.insert(3, tied_continue)
    part.insert(0, measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.normalized_dangling_ties == 2
    assert dangling_start.tie is None
    assert tied_continue.tie.type == "stop"


def test_cleanup_score_adds_cello_high_clef_without_flicker():
    score = stream.Score()
    cello = stream.Part()
    cello.partName = "Violoncello"
    first_measure = stream.Measure(number=1)
    first_measure.insert(0, clef.BassClef())
    first_measure.insert(0, note.Note("C3", quarterLength=4))
    second_measure = stream.Measure(number=2)
    second_measure.insert(0, note.Note("G4", quarterLength=4))
    third_measure = stream.Measure(number=3)
    third_measure.insert(0, note.Note("C3", quarterLength=4))
    cello.insert(0, first_measure)
    cello.insert(4, second_measure)
    cello.insert(8, third_measure)
    score.insert(0, cello)

    report = cleanup_score(score)

    assert report.cello_clef_changes_added == 2
    assert any(isinstance(item, clef.TrebleClef) for item in second_measure.getElementsByClass(clef.Clef))
    assert any(isinstance(item, clef.BassClef) for item in third_measure.getElementsByClass(clef.Clef))


def test_global_transposition_can_prefer_cleaner_key_within_guard():
    score = stream.Score()
    for _ in range(4):
        part = stream.Part()
        part.insert(0, meter.TimeSignature("4/4"))
        part.insert(0, key.KeySignature(0))
        part.insert(0, note.Note("C2", quarterLength=4))
        score.insert(0, part)

    choice = choose_global_transposition(
        score,
        profile=PIANO_REDUCTION,
        candidate_semitones=(0, 1),
        key_signature_tessitura_tolerance=999,
        key_signature_min_abs_improvement=1,
        key_signature_min_rel_improvement=0.1,
    )

    assert key_signature_transposition_burden(score, 0) == 0
    assert key_signature_transposition_burden(score, 1) == 5
    assert choice.semitones == 0


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


def test_six_voice_quartet_reduction_is_explicit_about_source_count():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("inner 1", [(0, 4, "G5")]),
            make_part("inner 2", [(0, 4, "E5")]),
            make_part("inner 3", [(0, 4, "C4")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    with pytest.raises(ValueError, match="Expected exactly 6 source parts"):
        build_six_voice_quartet_score(score, enforce_ranges=False)


def test_six_voice_quartet_reduction_preserves_outer_voices():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("inner 1", [(0, 4, "G5")]),
            make_part("inner 2", [(0, 4, "E5")]),
            make_part("inner 3", [(0, 4, "C4")]),
            make_part("inner 4", [(0, 4, "G3")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_six_voice_quartet_score(
        score,
        enforce_ranges=False,
        add_editorial_harmony=False,
        add_editorial_thirds=False,
    )

    assert_measures_are_exact(reduced, bars)
    assert len(reduced.parts) == 4

    violin_1_note = list(reduced.parts[0].getElementsByClass(stream.Measure))[0].notes[0]
    cello_note = list(reduced.parts[3].getElementsByClass(stream.Measure))[0].notes[0]
    assert violin_1_note.editorial.sourcePartIndex == 0
    assert cello_note.editorial.sourcePartIndex == 5


def test_six_voice_quartet_reduction_keeps_third_before_duplicate():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("duplicate top pc", [(0, 4, "C5")]),
            make_part("fifth", [(0, 4, "G4")]),
            make_part("third", [(0, 4, "E4")]),
            make_part("duplicate fifth", [(0, 4, "G3")]),
            make_part("bottom", [(0, 4, "C2")]),
        ]
    )

    reduced = build_six_voice_quartet_score(
        score,
        enforce_ranges=False,
        add_editorial_harmony=False,
        add_editorial_thirds=False,
    )
    notes = [
        element
        for part in reduced.parts
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]

    assert len(notes) == 4
    assert {element.pitch.pitchClass for element in notes} == {0, 4, 7}
    assert any(element.pitch.name == "E" for element in notes)


def test_take6_quartet_reduction_prefers_guide_tones_in_dense_sonority():
    score = make_score(
        [
            make_part("lead", [(0, 4, "C6")]),
            make_part("ninth", [(0, 4, "D5")]),
            make_part("seventh", [(0, 4, "B-4")]),
            make_part("third", [(0, 4, "E4")]),
            make_part("fifth", [(0, 4, "G3")]),
            make_part("bass", [(0, 4, "C2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_take6_quartet_score(score, enforce_ranges=False)

    assert_measures_are_exact(reduced, bars)
    notes = [
        element
        for part in reduced.parts
        for element in list(part.getElementsByClass(stream.Measure))[0].notes
    ]

    assert len(notes) == 4
    assert {element.pitch.pitchClass for element in notes} == {0, 4, 10}
    assert any(element.pitch.name == "E" for element in notes)
    assert any(element.pitch.name == "B-" for element in notes)
    assert not any(element.pitch.name == "G" for element in notes)


def test_take6_voice_preservation_continues_line_before_doubling_third():
    score = make_score(
        [
            make_part("lead", [(0, 2, "A4"), (2, 1, "A4"), (3, 1, "A4")]),
            make_part("duplicate third", [(0, 2, "A4"), (2, 1, "A4"), (3, 1, "A4")]),
            make_part("inner line", [(0, 2, "G4"), (2, 1, "G4"), (3, 1, "F4")]),
            make_part("fifth", [(0, 2, "C4"), (2, 1, "C4"), (3, 1, "C4")]),
            make_part("duplicate fifth", [(0, 2, "C4"), (2, 1, "C4"), (3, 1, "C4")]),
            make_part("bass", [(0, 2, "F3"), (2, 1, "F3"), (3, 1, "F3")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    violin_2_measure = list(reduced.parts[1].getElementsByClass(stream.Measure))[0]
    violin_2_notes = list(violin_2_measure.notes)

    assert [element.pitch.nameWithOctave for element in violin_2_notes] == ["G4", "G4", "F4"]


def test_take6_double_stops_are_optional_and_source_based():
    score = make_score(
        [
            make_part("lead", [(0, 4, "C6")]),
            make_part("ninth", [(0, 4, "D5")]),
            make_part("seventh", [(0, 4, "B-4")]),
            make_part("third", [(0, 4, "E4")]),
            make_part("fifth", [(0, 4, "G3")]),
            make_part("bass", [(0, 4, "C2")]),
        ]
    )

    plain = build_take6_quartet_score(score, enforce_ranges=False)
    doubled = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)

    assert not any(element.isChord for part in plain.parts for element in part.recurse().notesAndRests)
    chords = [element for part in doubled.parts for element in part.recurse().notesAndRests if element.isChord]
    assert chords

    represented_pitch_classes = set()
    for part in doubled.parts:
        measure = list(part.getElementsByClass(stream.Measure))[0]
        for element in measure.notes:
            if element.isChord:
                represented_pitch_classes.update(chord_note.pitch.pitchClass for chord_note in element.notes)
                assert hasattr(element.editorial, "sourceEventIds")
            else:
                represented_pitch_classes.add(element.pitch.pitchClass)

    assert represented_pitch_classes == {0, 2, 4, 7, 10}


def test_take6_double_stop_can_split_longer_host_event():
    score = make_score(
        [
            make_part("lead", [(0, 3, "D5")]),
            make_part("alto", [(0, 3, "A4")]),
            make_part("third", [(0, 2, "E4")]),
            make_part("root color", [(0, 3, "C4")]),
            make_part("sharp five", [(0, 2, "F#3")]),
            make_part("bass", [(0, 3, "B-2")]),
        ]
    )

    doubled = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    active_pitch_classes = set()
    for part in doubled.parts:
        measure = list(part.getElementsByClass(stream.Measure))[0]
        for element in measure.notes:
            if element.offset > 0:
                continue
            if element.isChord:
                active_pitch_classes.update(chord_note.pitch.pitchClass for chord_note in element.notes)
            else:
                active_pitch_classes.add(element.pitch.pitchClass)

    assert active_pitch_classes == {0, 2, 4, 6, 9, 10}
    cello_measure = list(doubled.parts[3].getElementsByClass(stream.Measure))[0]
    assert cello_measure.notes[0].isChord
    assert ql_to_fraction(cello_measure.notes[0].quarterLength) == Fraction(2, 1)
    assert ql_to_fraction(cello_measure.notes[1].quarterLength) == Fraction(1, 1)


def test_take6_double_stops_preserve_long_source_doublings():
    score = make_score(
        [
            make_part("lead", [(0, 4, "D5"), (4, 4, "C5")]),
            make_part("alto", [(0, 4, "A4"), (4, 4, "G4")]),
            make_part("upper duplicate", [(0, 4, "G4"), (4, 4, "E4")]),
            make_part("lower duplicate", [(0, 4, "D4"), (4, 4, "C4")]),
            make_part("baritone", [(0, 4, "B3"), (4, 4, "G3")]),
            make_part("bass", [(0, 4, "G2"), (4, 4, "C2")]),
        ]
    )

    doubled = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    output_pitches = []
    chord_count = 0
    for part in doubled.parts:
        for element in part.flatten().notes:
            start = ql_to_fraction(element.offset)
            end = start + ql_to_fraction(element.quarterLength)
            if not (start <= Fraction(0, 1) < end):
                continue
            if element.isChord:
                chord_count += 1
                output_pitches.extend(chord_note.pitch.nameWithOctave for chord_note in element.notes)
            else:
                output_pitches.append(element.pitch.nameWithOctave)

    assert chord_count == 2
    assert sorted(output_pitches) == sorted(["G2", "B3", "D4", "G4", "A4", "D5"])


def test_take6_double_stops_do_not_preserve_short_source_doublings():
    score = make_score(
        [
            make_part("lead", [(0, 1, "D5"), (1, 3, None)]),
            make_part("alto", [(0, 1, "A4"), (1, 3, None)]),
            make_part("upper duplicate", [(0, 1, "G4"), (1, 3, None)]),
            make_part("lower duplicate", [(0, 1, "D4"), (1, 3, None)]),
            make_part("baritone", [(0, 1, "B3"), (1, 3, None)]),
            make_part("bass", [(0, 1, "G2"), (1, 3, None)]),
        ]
    )

    doubled = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    output_pitches = []
    for part in doubled.parts:
        for element in part.flatten().notes:
            start = ql_to_fraction(element.offset)
            end = start + ql_to_fraction(element.quarterLength)
            if start <= Fraction(0, 1) < end:
                if element.isChord:
                    output_pitches.extend(chord_note.pitch.nameWithOctave for chord_note in element.notes)
                else:
                    output_pitches.append(element.pitch.nameWithOctave)

    assert len(output_pitches) == 4
    assert set(name[:-1] for name in output_pitches) == {"G", "B", "A", "D"}


def test_take6_double_stops_do_not_add_short_isolated_color_attacks():
    score = make_score(
        [
            make_part("lead", [(0, Fraction(1, 4), "D5"), (Fraction(1, 4), Fraction(15, 4), None)]),
            make_part("alto", [(0, Fraction(1, 4), "A4"), (Fraction(1, 4), Fraction(15, 4), None)]),
            make_part("upper color", [(0, Fraction(1, 4), "E4"), (Fraction(1, 4), Fraction(15, 4), None)]),
            make_part("lower color", [(0, Fraction(1, 4), "C4"), (Fraction(1, 4), Fraction(15, 4), None)]),
            make_part("baritone", [(0, Fraction(1, 4), "B3"), (Fraction(1, 4), Fraction(15, 4), None)]),
            make_part("bass", [(0, Fraction(1, 4), "G2"), (Fraction(1, 4), Fraction(15, 4), None)]),
        ]
    )

    doubled = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    chord_count = 0
    output_pitches = []
    for part in doubled.parts:
        for element in part.flatten().notes:
            start = ql_to_fraction(element.offset)
            end = start + ql_to_fraction(element.quarterLength)
            if start <= Fraction(0, 1) < end:
                if element.isChord:
                    chord_count += 1
                    output_pitches.extend(chord_note.pitch.nameWithOctave for chord_note in element.notes)
                else:
                    output_pitches.append(element.pitch.nameWithOctave)

    assert chord_count == 0
    assert len(output_pitches) == 4


def test_take6_preservation_avoids_tiny_trimmed_duple_triplet_splice():
    score = make_score(
        [
            make_part(
                "lead",
                [
                    (0, 2, "E5"),
                    (2, 1, None),
                    (3, Fraction(1, 2), "B-5"),
                    (Fraction(7, 2), Fraction(1, 2), "A5"),
                ],
            ),
            make_part(
                "straight inner",
                [
                    (0, 2, "E4"),
                    (2, Fraction(1, 2), "C4"),
                    (Fraction(5, 2), Fraction(1, 2), "D4"),
                    (3, Fraction(1, 2), "E-4"),
                    (Fraction(7, 2), Fraction(1, 2), "D4"),
                ],
            ),
            make_part(
                "triplet inner",
                [
                    (0, Fraction(3, 2), "F#4"),
                    (Fraction(3, 2), Fraction(1, 2), "E4"),
                    (2, Fraction(1, 3), "E4"),
                    (Fraction(7, 3), Fraction(1, 3), "D4"),
                    (Fraction(8, 3), Fraction(4, 3), "E4"),
                ],
            ),
            make_part(
                "tenor",
                [
                    (0, 2, "B3"),
                    (2, Fraction(1, 2), "G3"),
                    (Fraction(5, 2), Fraction(1, 2), "A3"),
                    (3, 1, "B-3"),
                ],
            ),
            make_part("baritone", [(0, 2, "G3"), (2, 2, "E3")]),
            make_part("bass", [(0, 2, "C#3"), (2, 2, "F#2")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    violin_2_measure = list(reduced.parts[1].getElementsByClass(stream.Measure))[0]
    second_half = [
        element
        for element in violin_2_measure.notesAndRests
        if ql_to_fraction(element.offset) >= Fraction(2, 1)
    ]

    assert [ql_to_fraction(element.quarterLength) for element in second_half] == [
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(1, 2),
    ]
    assert [element.pitch.nameWithOctave for element in second_half if isinstance(element, note.Note)] == [
        "C4",
        "D4",
        "E-4",
        "D4",
    ]


def test_take6_double_stops_preserve_omitted_inner_melodic_pickup():
    score = make_score(
        [
            make_part("lead", [(0, Fraction(3, 2), "G#4"), (Fraction(3, 2), Fraction(3, 2), "F#4"), (3, Fraction(5, 2), "A4"), (Fraction(11, 2), Fraction(1, 2), None)]),
            make_part("inner 1", [(0, Fraction(3, 2), "E4"), (Fraction(3, 2), Fraction(3, 2), "D4"), (3, Fraction(5, 2), "D4"), (Fraction(11, 2), Fraction(1, 2), None)]),
            make_part("inner 2", [(0, Fraction(3, 2), "C#4"), (Fraction(3, 2), Fraction(3, 2), "B3"), (3, Fraction(5, 2), "C#4"), (Fraction(11, 2), Fraction(1, 2), None)]),
            make_part("melody pickup", [(0, 3, "A3"), (3, 1, None), (4, Fraction(1, 2), "E4"), (Fraction(9, 2), Fraction(3, 2), "F#4")]),
            make_part("baritone", [(0, Fraction(3, 2), "F#3"), (Fraction(3, 2), Fraction(3, 4), "D3"), (Fraction(9, 4), Fraction(3, 4), "E3"), (3, Fraction(5, 2), "F#3"), (Fraction(11, 2), Fraction(1, 2), None)]),
            make_part("bass", [(0, Fraction(3, 2), "D2"), (Fraction(3, 2), Fraction(3, 2), "G2"), (3, Fraction(5, 2), "E2"), (Fraction(11, 2), Fraction(1, 2), None)]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    sounding_by_offset: dict[Fraction, list[str]] = {}
    for part in reduced.parts:
        for element in part.flatten().notes:
            start = ql_to_fraction(element.offset)
            end = start + ql_to_fraction(element.quarterLength)
            for probe in (Fraction(4, 1), Fraction(9, 2), Fraction(11, 2)):
                if start <= probe < end:
                    sounding_by_offset.setdefault(probe, [])
                    if element.isChord:
                        sounding_by_offset[probe].extend(chord_note.pitch.nameWithOctave for chord_note in element.notes)
                    else:
                        sounding_by_offset[probe].append(element.pitch.nameWithOctave)

    assert "E4" in sounding_by_offset[Fraction(4, 1)]
    assert "F#4" in sounding_by_offset[Fraction(9, 2)]
    assert "F#4" in sounding_by_offset[Fraction(11, 2)]


def test_short_note_rest_artifact_normalization_snaps_isolated_odd_pair():
    events = [
        SourceEvent("p0:e0", 0, 0, Fraction(0, 1), Fraction(5, 12), 64, False),
        SourceEvent("p0:e1", 0, 1, Fraction(5, 12), Fraction(7, 12), None, True),
        SourceEvent("p0:e2", 0, 2, Fraction(1, 1), Fraction(1, 1), 62, False),
    ]

    normalized = normalize_short_note_rest_artifacts(events)

    assert [(event.start, event.duration, event.is_rest) for event in normalized] == [
        (Fraction(0, 1), Fraction(1, 2), False),
        (Fraction(1, 2), Fraction(1, 2), True),
        (Fraction(1, 1), Fraction(1, 1), False),
    ]


def test_short_note_rest_artifact_normalization_absorbs_tiny_intra_voice_gap():
    events = [
        SourceEvent("p0:e0", 0, 0, Fraction(0, 1), Fraction(1, 3), 70, False),
        SourceEvent("p0:e1", 0, 1, Fraction(1, 3), Fraction(1, 3), 66, False),
        SourceEvent("p0:e2", 0, 2, Fraction(2, 3), Fraction(1, 12), None, True),
        SourceEvent("p0:e3", 0, 3, Fraction(3, 4), Fraction(3, 4), 68, False),
    ]

    normalized = normalize_short_note_rest_artifacts(events)

    assert [(event.start, event.duration, event.pitch_midi, event.is_rest) for event in normalized] == [
        (Fraction(0, 1), Fraction(1, 3), 70, False),
        (Fraction(1, 3), Fraction(1, 3), 66, False),
        (Fraction(2, 3), Fraction(5, 6), 68, False),
    ]


def test_short_note_rest_artifact_normalization_trims_tiny_note_overlap():
    events = [
        SourceEvent("p0:e0", 0, 0, Fraction(0, 1), Fraction(3, 4), 68, False),
        SourceEvent("p0:e1", 0, 1, Fraction(3, 4), Fraction(1, 3), 67, False),
        SourceEvent("p0:e2", 0, 2, Fraction(1, 1), Fraction(1, 4), 70, False),
        SourceEvent("p0:e3", 0, 3, Fraction(5, 4), Fraction(1, 4), None, True),
    ]

    normalized = normalize_short_note_rest_artifacts(events)

    assert [(event.start, event.duration, event.pitch_midi, event.is_rest) for event in normalized] == [
        (Fraction(0, 1), Fraction(3, 4), 68, False),
        (Fraction(3, 4), Fraction(1, 4), 67, False),
        (Fraction(1, 1), Fraction(1, 4), 70, False),
        (Fraction(5, 4), Fraction(1, 4), None, True),
    ]


def test_six_voice_quartet_reduction_trims_overlapping_outer_source_voice():
    score = make_score(
        [
            make_part("top", [(0, 4, "C6")]),
            make_part("inner 1", [(0, 4, "G5")]),
            make_part("inner 2", [(0, 4, "E5")]),
            make_part("inner 3", [(0, 4, "C4")]),
            make_part("inner 4", [(0, 4, "G3")]),
            make_part("bottom with overlap", [(0, 4, "C2"), (2, 2, "D2")]),
        ]
    )

    bars = build_bar_map(score)
    reduced = build_six_voice_quartet_score(
        score,
        enforce_ranges=False,
        add_editorial_harmony=False,
        add_editorial_thirds=False,
    )

    assert_measures_are_exact(reduced, bars)
    cello_measure = list(reduced.parts[3].getElementsByClass(stream.Measure))[0]
    cello_notes = list(cello_measure.notes)
    assert [ql_to_fraction(element.offset) for element in cello_notes] == [Fraction(0, 1), Fraction(2, 1)]
    assert [ql_to_fraction(element.quarterLength) for element in cello_notes] == [Fraction(2, 1), Fraction(2, 1)]
    assert [element.pitch.nameWithOctave for element in cello_notes] == ["C2", "D2"]


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


def test_reduction_metadata_uses_source_filename_and_default_composer(tmp_path):
    score = make_score(
        [
            make_part("top", [(0, 4, "C5")]),
            make_part("middle 1", [(0, 4, "E4")]),
            make_part("middle 2", [(0, 4, "G4")]),
            make_part("bottom", [(0, 4, "C3")]),
        ]
    )
    midi_path = tmp_path / "47 A quiet place, originalrevu.mid"
    out_path = tmp_path / "quartet.musicxml"
    score.write("midi", fp=str(midi_path))

    reduced = reduce_to_quartet(
        midi_path,
        out_path=out_path,
        enforce_ranges=False,
        candidate_semitones=(0,),
    )

    assert reduced.metadata.title == "A Quiet Place - Reduction for String Quartet"
    assert reduced.metadata.composer == "F. Pachet and AI"
    assert out_path.exists()


def test_take6_reduction_metadata_uses_take6_composer_and_clean_title(tmp_path):
    score = make_score(
        [
            make_part("lead", [(0, 4, "D5")]),
            make_part("alto", [(0, 4, "A4")]),
            make_part("inner 1", [(0, 4, "G4")]),
            make_part("inner 2", [(0, 4, "D4")]),
            make_part("baritone", [(0, 4, "B3")]),
            make_part("bass", [(0, 4, "G2")]),
        ]
    )
    midi_path = tmp_path / "47 A quiet place, originalrevu.mid"
    out_path = tmp_path / "take6.musicxml"
    score.write("midi", fp=str(midi_path))

    reduced = reduce_take6_to_quartet(
        midi_path,
        out_path=out_path,
        semitones=0,
        add_source_double_stops=True,
    )

    assert reduced.metadata.title == "A Quiet Place - Reduction for String Quartet"
    assert reduced.metadata.composer == "Take 6, arrangement F. Pachet and AI"
    assert out_path.exists()


def test_octave_optimizer_preserves_pitch_classes_while_smoothing_neighbors():
    score = make_score(
        [
            make_part("Violin II", [(0, 1, "C#5"), (1, 1, "E4"), (2, 1, "F#5"), (3, 1, "E5")]),
            make_part("Viola", [(0, 1, "B-3"), (1, 2, "E-5"), (3, 1, "F#4")]),
        ]
    )
    before_pitch_classes = [
        int(element.pitch.midi) % 12
        for part in score.parts
        for element in part.recurse().notes
        if isinstance(element, note.Note)
    ]

    changes = optimize_score_octaves(score)

    changed = {(change.part, change.old_pitches, change.new_pitches) for change in changes}
    assert ("Violin II", (64,), (76,)) in changed
    assert ("Viola", (75,), (63,)) in changed
    after_pitch_classes = [
        int(element.pitch.midi) % 12
        for part in score.parts
        for element in part.recurse().notes
        if isinstance(element, note.Note)
    ]
    assert after_pitch_classes == before_pitch_classes


def test_title_from_source_path_splits_take6_camel_case():
    assert title_from_source_path("data/take6/ComeUntoMe.mid") == "Come Unto Me"
