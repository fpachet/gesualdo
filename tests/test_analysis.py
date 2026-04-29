from gesualdo_reduction.analysis import dense_chords, transposition_plan
from muses.base.temporals import Piece, TemporalCollection


def test_transposition_plan_maps_lowest_voice_to_desired_low():
    low = TemporalCollection(name="low")
    low.insert_note(43, 0.0, 1.0)
    high = TemporalCollection(name="high")
    high.insert_note(67, 0.0, 1.0)
    piece = Piece(melodies=[low, high])

    plan = transposition_plan(piece, desired_low=36)

    assert plan["voice_ranges"] == [(43, 43), (67, 67)]
    assert plan["transposition_interval"] == -7
    assert plan["transposed_voice_ranges"] == [(36, 36), (60, 60)]


def test_dense_chords_finds_sonorities_with_many_pitch_classes():
    texture = TemporalCollection()
    for pitch in [60, 64, 67, 70, 73]:
        texture.insert_note(pitch, 0.0, 1.0)
    piece = Piece(melodies=[texture])

    chords = dense_chords(piece, max_pitch_classes=4)

    assert len(chords) == 1
    assert chords[0].get_pitches() == [60, 64, 67, 70, 73]
