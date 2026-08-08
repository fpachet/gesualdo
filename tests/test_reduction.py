from fractions import Fraction
from xml.etree import ElementTree as ET

import pytest

pytest.importorskip("music21")

from music21 import chord, clef, dynamics, instrument, key, meter, note, pitch, stream, tie

import gesualdo_reduction.reduction as reduction_module
from gesualdo_reduction.musicxml_compat import cleanup_musicxml_engraving, strip_time_modifications
from gesualdo_reduction.notation_cleanup import cleanup_score
from gesualdo_reduction.octave_optimization import optimize_score_octaves
from gesualdo_reduction.reduction import (
    Bar,
    PIANO_REDUCTION,
    ReductionConfig,
    SourceEvent,
    STRING_QUARTET,
    _editorial_dynamic_points,
    _lower_high_cello_register,
    _merge_adjacent_generated_harmony_events,
    _smooth_isolated_handoffs,
    build_ensemble_score,
    build_bar_map,
    build_measured_part,
    build_piano_score,
    build_quartet_plus_viole_sweetspot_score,
    build_quartet_plus_viole_score,
    build_quartet_score,
    build_six_voice_quartet_score,
    build_take6_quartet_score,
    choose_global_transposition,
    extract_events,
    key_signature_transposition_burden,
    normalize_musescore_grid_rhythm,
    normalize_musescore_rhythm_artifacts,
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


def test_musicxml_engraving_cleanup_respells_without_dropping_wedges(tmp_path):
    xml_path = tmp_path / "flat_key.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-3</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>C</sign><line>4</line></clef>
      </attributes>
      <direction><direction-type><wedge type="crescendo"/></direction-type></direction>
      <note>
        <pitch><step>G</step><alter>1</alter><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>sharp</accidental>
      </note>
      <direction><direction-type><wedge type="stop"/></direction-type></direction>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.respelled_key_signature_accidentals == 1
    assert report.suppressed_redundant_accidentals == 1
    assert text.count("<wedge") == 2
    assert "<step>A</step>" in text
    assert "<alter>-1</alter>" in text
    assert "<accidental>" not in text
    assert "<sign>F</sign>" in text


def test_musicxml_engraving_cleanup_removes_text_annotations_but_keeps_tempo_and_dynamics(tmp_path):
    xml_path = tmp_path / "annotations.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <credit><credit-words>This edition?</credit-words></credit>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction><direction-type><words>Imported vocal text</words></direction-type></direction>
      <direction>
        <direction-type>
          <metronome><beat-unit>quarter</beat-unit><per-minute>58</per-minute></metronome>
        </direction-type>
        <sound tempo="58" />
      </direction>
      <direction><direction-type><dynamics><mf /></dynamics></direction-type></direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <lyric><text>la</text></lyric>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.removed_text_annotations == 4
    assert "This edition?" not in text
    assert "Imported vocal text" not in text
    assert "<lyric>" not in text
    assert "<metronome>" in text
    assert 'tempo="58"' in text
    assert "<mf" in text


def test_musicxml_engraving_cleanup_removes_dangling_ties(tmp_path):
    xml_path = tmp_path / "dangling_ties.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-1</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>C</sign><line>3</line></clef>
      </attributes>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
        <tie type="start" />
        <type>quarter</type>
        <notations><tied type="start" /></notations>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>1</duration>
        <tie type="start" />
        <type>quarter</type>
        <notations><tied type="start" /></notations>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>1</duration>
        <tie type="stop" />
        <type>quarter</type>
        <notations><tied type="stop" /></notations>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_dangling_ties == 1
    assert text.count('<tie type="start" />') == 1
    assert text.count('<tied type="start" />') == 1
    assert '<tie type="stop" />' in text
    assert '<tied type="stop" />' in text


def test_musicxml_engraving_cleanup_normalizes_tied_enharmonics(tmp_path):
    xml_path = tmp_path / "tied_enharmonics.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><alter>1</alter><octave>4</octave></pitch>
        <duration>2</duration>
        <tie type="start" />
        <type>half</type>
        <accidental>sharp</accidental>
        <notations><tied type="start" /></notations>
      </note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>D</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>2</duration>
        <tie type="stop" />
        <type>half</type>
        <accidental>flat</accidental>
        <notations><tied type="stop" /></notations>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_tied_enharmonics == 1
    assert "<step>D</step>" not in text
    assert text.count("<step>C</step>") == 2
    assert text.count("<alter>1</alter>") == 2
    assert "<accidental>flat</accidental>" not in text


def test_musicxml_engraving_cleanup_normalizes_adjacent_enharmonics(tmp_path):
    xml_path = tmp_path / "adjacent_enharmonics.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>C</sign><line>3</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><alter>1</alter><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>D</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>flat</accidental>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_adjacent_enharmonics == 1
    assert "<step>D</step>" not in text
    assert text.count("<step>C</step>") == 2
    assert text.count("<alter>1</alter>") == 2
    assert "<accidental>flat</accidental>" not in text


def test_musicxml_engraving_cleanup_leaves_adjacent_natural_enharmonics(tmp_path):
    xml_path = tmp_path / "adjacent_natural_enharmonics.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>E</step><alter>1</alter><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_adjacent_enharmonics == 0
    assert "<step>E</step>" in text
    assert "<alter>1</alter>" in text
    assert "<step>F</step>" in text


def test_musicxml_engraving_cleanup_removes_isolated_redundant_short_note(tmp_path):
    xml_path = tmp_path / "isolated_redundant_short_note.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>3</duration><type>eighth</type><dot /></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>7</duration><type>quarter</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.removed_isolated_redundant_notes == 1
    assert report.normalized_fragmented_rests == 1
    assert text.count("<rest />") == 3
    assert text.count("<step>C</step>") == 1
    assert "<duration>12</duration>\n        <type>half</type>\n        <dot />" in text


def test_musicxml_engraving_cleanup_merges_deleted_note_rest_fragment(tmp_path):
    xml_path = tmp_path / "fragmented_rests.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="31">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><alter>1</alter><octave>5</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>3</duration><type>eighth</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_fragmented_rests == 1
    assert text.count("<rest />") == 1
    assert "<duration>12</duration>\n        <type>half</type>\n        <dot />" in text


def test_musicxml_engraving_cleanup_simplifies_long_fragmented_rest_run(tmp_path):
    xml_path = tmp_path / "dolcissima_cello_bar_13_rests.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Dolcissima mia vita</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="13">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>2</beat-type></time></attributes>
      <note><pitch><step>E</step><alter>-1</alter><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>2</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>F</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_fragmented_rests == 1
    assert text.count("<rest />") == 2
    assert "<duration>16</duration>\n        <type>whole</type>" in text
    assert "<duration>4</duration>\n        <type>quarter</type>" in text


def test_musicxml_engraving_cleanup_applies_dolcissima_bar_14_and_e_flats(tmp_path):
    xml_path = tmp_path / "dolcissima_bar_14.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Dolcissima mia vita</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="14">
      <attributes><divisions>4</divisions><time><beats>8</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>24</duration><type>whole</type></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>7</duration><type>quarter</type><dot /></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="14">
      <attributes><divisions>4</divisions><time><beats>8</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>24</duration><type>whole</type></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>3</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>3</duration><type>eighth</type><dot /></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
    <measure number="16">
      <note>
        <pitch><step>D</step><alter>1</alter><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>D</step><alter>1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_dolcissima_line_cleanups == 3
    assert text.count("<step>B</step>") == 1
    assert text.count("<step>E</step>") == 2
    assert text.count("<alter>-1</alter>") == 3
    assert "<accidental>flat</accidental>" in text
    assert "<accidental>sharp</accidental>" not in text
    assert "<duration>4</duration>\n        <type>quarter</type>" in text


def test_musicxml_engraving_cleanup_adds_final_barlines(tmp_path):
    xml_path = tmp_path / "missing_final_barlines.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>4</duration><type>whole</type></note>
      <barline location="right"><bar-style>regular</bar-style></barline>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()
    styles = [
        part.findall("measure")[-1].findtext("barline[@location='right']/bar-style")
        for part in root.findall("part")
    ]

    assert report.final_barlines_added == 4
    assert styles == ["light-heavy", "light-heavy"]


def test_musicxml_engraving_cleanup_keeps_nonstandard_trailing_rest_fragment(tmp_path):
    xml_path = tmp_path / "trailing_rest_fragment.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>5</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>15</duration><type>half</type><dot /></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.normalized_fragmented_rests == 0
    assert text.count("<rest />") == 2


def test_musicxml_engraving_cleanup_extends_terminal_sixteenth_into_rest(tmp_path):
    xml_path = tmp_path / "terminal_sixteenth.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>15</duration><type>half</type><dot /></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>10</duration><type>half</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.extended_terminal_short_notes == 1
    assert text.count("<rest />") == 1
    assert "<duration>2</duration>\n        <type>eighth</type>" in text


def test_musicxml_engraving_cleanup_keeps_other_voice_terminal_rest(tmp_path):
    xml_path = tmp_path / "other_voice_terminal_rest.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>14</duration><type>half</type><dot /></note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>16th</type>
      </note>
      <note><rest /><duration>1</duration><voice>2</voice><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.extended_terminal_short_notes == 0
    assert text.count("<rest />") == 1


def test_musicxml_engraving_cleanup_keeps_dissonant_terminal_sixteenth_rest(tmp_path):
    xml_path = tmp_path / "dissonant_terminal_sixteenth.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>15</duration><type>half</type><dot /></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>14</duration><type>half</type><dot /></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.extended_terminal_short_notes == 0
    assert text.count("<rest />") == 2


def test_musicxml_engraving_cleanup_allows_gia_piansi_bar_46_editorial_exception(tmp_path):
    xml_path = tmp_path / "gia_piansi_bar_46_exception.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>15</duration><type>half</type><dot /></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="46">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>14</duration><type>half</type><dot /></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.extended_terminal_short_notes == 1
    assert text.count("<rest />") == 1


def test_musicxml_engraving_cleanup_applies_gia_piansi_line_cleanups(tmp_path):
    xml_path = tmp_path / "gia_piansi_line_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Viola</part-name></score-part>
    <score-part id="P2"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="51">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>14</duration><type>half</type><dot /></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
    <measure number="52">
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="53">
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>6</duration><type>quarter</type><dot /></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="51">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="53">
      <note><rest /><duration>14</duration><type>half</type><dot /></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_gia_piansi_line_cleanups == 5
    assert text.count("<rest measure=\"yes\" />") == 1
    assert text.count("<step>B</step>") == 1
    assert text.count("<step>D</step>") == 1
    assert text.count("<step>G</step>") == 1
    assert text.count("<step>C</step>") == 1


def test_musicxml_engraving_cleanup_applies_gia_piansi_bar_8_handoff(tmp_path):
    xml_path = tmp_path / "gia_piansi_bar_8_handoff.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
    <score-part id="P3"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="8">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>8</duration><type>half</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="8">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>3</duration><type>eighth</type><dot /></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="8">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>3</duration><type>eighth</type><dot /></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()
    parts = {part.get("id"): part for part in root.findall("part")}
    violin_ii_notes = parts["P1"].findall("./measure[@number='8']/note")
    viola_notes = parts["P2"].findall("./measure[@number='8']/note")
    cello_notes = parts["P3"].findall("./measure[@number='8']/note")
    viola_pitches = [
        (
            note.findtext("pitch/step"),
            note.findtext("pitch/octave"),
            note.findtext("duration"),
        )
        for note in viola_notes
        if note.find("pitch") is not None
    ]

    assert report.applied_gia_piansi_line_cleanups == 3
    assert len(violin_ii_notes) == 1
    assert violin_ii_notes[0].find("rest").get("measure") == "yes"  # type: ignore[union-attr]
    assert violin_ii_notes[0].findtext("duration") == "16"
    assert viola_pitches[-3:] == [("A", "4", "1"), ("B", "4", "1"), ("C", "5", "8")]
    assert not any(
        note.findtext("pitch/step") == "C"
        and note.findtext("pitch/octave") == "4"
        for note in viola_notes
    )
    assert [(note.find("rest") is not None, note.findtext("duration"), note.findtext("type")) for note in cello_notes] == [
        (True, "8", "half"),
        (False, "4", "quarter"),
        (True, "4", "quarter"),
    ]


def test_musicxml_engraving_cleanup_applies_gia_piansi_bar_27_violin_ii(tmp_path):
    xml_path = tmp_path / "gia_piansi_bar_27_violin_ii.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="27">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note>
        <pitch><step>G</step><octave>3</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
        <stem>up</stem>
        <beam number="1">begin</beam>
        <beam number="2">begin</beam>
      </note>
      <note>
        <chord />
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>7</duration><type>quarter</type><dot /><dot /></note>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()
    notes = root.findall("./part/measure[@number='27']/note")
    pitches = [
        (note.findtext("pitch/step"), note.findtext("pitch/octave"), note.findtext("duration"), note.findtext("type"))
        for note in notes
        if note.find("pitch") is not None
    ]

    assert report.applied_gia_piansi_line_cleanups == 2
    assert len(notes) == 7
    assert notes[0].find("chord") is None
    assert notes[0].find("beam[@number='1']").text == "begin"  # type: ignore[union-attr]
    assert pitches[:5] == [
        ("B", "4", "1", "16th"),
        ("A", "4", "1", "16th"),
        ("G", "4", "1", "16th"),
        ("F", "4", "1", "16th"),
        ("E", "4", "2", "eighth"),
    ]
    assert notes[5].find("rest") is not None
    assert notes[5].findtext("duration") == "6"
    assert notes[5].findtext("type") == "quarter"
    assert len(notes[5].findall("dot")) == 1


def test_musicxml_engraving_cleanup_applies_gia_piansi_bar_45_rest_merge(tmp_path):
    xml_path = tmp_path / "gia_piansi_bar_45_rests.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Viola</part-name></score-part>
    <score-part id="P2"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="45">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <direction placement="below"><direction-type><dynamics><mf /></dynamics></direction-type></direction>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <direction placement="below"><direction-type><wedge number="2" spread="0" type="crescendo" /></direction-type></direction>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <direction placement="below"><direction-type><wedge number="1" spread="15" type="stop" /></direction-type></direction>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="48">
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="50">
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="45">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <direction placement="below"><direction-type><dynamics><mf /></dynamics></direction-type></direction>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <direction placement="below"><direction-type><wedge number="2" spread="0" type="crescendo" /></direction-type></direction>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <direction placement="below"><direction-type><wedge number="1" spread="15" type="stop" /></direction-type></direction>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>2</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="50">
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()

    assert report.applied_gia_piansi_line_cleanups == 5
    for part in root.findall("part"):
        notes = part.findall("./measure[@number='45']/note")
        rests = [note for note in notes if note.find("rest") is not None]
        assert [(rest.findtext("duration"), rest.findtext("type")) for rest in rests] == [
            ("4", "quarter"),
            ("4", "quarter"),
        ]
        assert len(part.findall("./measure[@number='45']/direction")) == 3
    viola_bar_48_rests = [
        note
        for note in root.findall("./part[@id='P1']/measure[@number='48']/note")
        if note.find("rest") is not None
    ]
    assert [(rest.findtext("duration"), rest.findtext("type")) for rest in viola_bar_48_rests] == [
        ("4", "quarter"),
    ]
    for part in root.findall("part"):
        notes = part.findall("./measure[@number='50']/note")
        assert len(notes) == 1
        assert notes[0].find("rest").get("measure") == "yes"  # type: ignore[union-attr]
        assert notes[0].findtext("duration") == "16"
        assert notes[0].find("type") is None


def test_musicxml_engraving_cleanup_applies_gia_piansi_bars_51_and_57_handoffs(tmp_path):
    xml_path = tmp_path / "gia_piansi_bars_51_57_handoffs.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Già piansi nel dolore</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="51">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
    </measure>
    <measure number="57">
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="51">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration><type>16th</type>
        <stem>up</stem><beam number="1">begin</beam><beam number="2">begin</beam>
      </note>
      <note><chord /><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="57">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration><type>16th</type>
        <stem>up</stem><beam number="1">begin</beam><beam number="2">begin</beam>
      </note>
      <note><chord /><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>16th</type></note>
      <note>
        <pitch><step>G</step><octave>3</octave></pitch>
        <duration>1</duration><type>16th</type>
        <stem>up</stem><beam number="1">begin</beam><beam number="2">begin</beam>
      </note>
      <note><chord /><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()
    parts = {part.get("id"): part for part in root.findall("part")}

    violin_ii_51 = parts["P1"].findall("./measure[@number='51']/note")
    violin_ii_57 = parts["P1"].findall("./measure[@number='57']/note")
    viola_51 = parts["P2"].findall("./measure[@number='51']/note")
    viola_57 = parts["P2"].findall("./measure[@number='57']/note")

    assert report.applied_gia_piansi_line_cleanups == 5
    assert violin_ii_51[1].findtext("pitch/step") == "E"
    assert violin_ii_51[1].findtext("pitch/octave") == "4"
    assert violin_ii_51[1].findtext("duration") == "4"
    assert violin_ii_51[1].findtext("type") == "quarter"
    assert not any(note.findtext("pitch/step") == "E" and note.findtext("pitch/octave") == "4" for note in viola_51)
    assert not any(note.find("chord") is not None for note in viola_51)

    assert [(violin_ii_57[index].findtext("pitch/step"), violin_ii_57[index].findtext("pitch/octave"), violin_ii_57[index].findtext("duration")) for index in (4, 5)] == [
        ("D", "4", "2"),
        ("G", "3", "2"),
    ]
    assert not any(
        note.findtext("pitch/step") in {"D", "G"}
        and note.findtext("pitch/octave") in {"4", "3"}
        and note.find("chord") is None
        for note in viola_57[1:5]
    )
    assert not any(note.find("chord") is not None for note in viola_57)


def test_musicxml_engraving_cleanup_applies_luci_serene_cello_cleanup(tmp_path):
    xml_path = tmp_path / "luci_serene_cello_bar_7.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Luci serene e chiare</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="7">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note>
        <pitch><step>B</step><alter>-1</alter><octave>3</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
        <beam number="1">begin</beam>
        <beam number="2">forward hook</beam>
      </note>
      <note>
        <pitch><step>E</step><alter>-1</alter><octave>3</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
        <beam number="1">end</beam>
      </note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>F</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_luci_serene_line_cleanups == 1
    assert "<step>B</step>" not in text
    assert text.count("<rest />") == 2
    assert "<duration>1</duration>" not in text
    assert "<pitch>\n          <step>E</step>\n          <alter>-1</alter>\n          <octave>3</octave>\n        </pitch>\n        <duration>4</duration>\n        <type>quarter</type>" in text


def test_musicxml_engraving_cleanup_applies_luci_serene_bar_9_delayed_16ths(tmp_path):
    xml_path = tmp_path / "luci_serene_bar_9_delayed_16ths.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Luci serene e chiare</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
    <score-part id="P3"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="9">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>14</duration><type>half</type><dot /></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="9">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>12</duration><type>half</type><dot /></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="9">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <note><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>12</duration><type>half</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_luci_serene_line_cleanups == 3
    assert "<type>16th</type>" not in text
    assert text.count("<type>eighth</type>") == 5
    assert text.count("<rest />") == 0


def test_musicxml_engraving_cleanup_applies_luci_serene_d_flat_spellings(tmp_path):
    xml_path = tmp_path / "luci_serene_d_flat_spellings.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Luci serene e chiare</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="41">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>-3</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note>
        <pitch><step>C</step><alter>1</alter><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>D</step><octave>5</octave></pitch>
        <duration>14</duration>
        <type>half</type>
        <dot />
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_luci_serene_line_cleanups == 1
    assert "<step>C</step>" not in text
    assert "<step>D</step>" in text
    assert "<alter>-1</alter>" in text
    assert "<accidental>flat</accidental>" in text
    assert "<accidental>sharp</accidental>" not in text


def test_musicxml_engraving_cleanup_applies_sio_non_miro_local_cleanups(tmp_path):
    xml_path = tmp_path / "sio_non_miro_local_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>S'io non miro non moro</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
    <score-part id="P3"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="20">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key></attributes>
      <note>
        <pitch><step>E</step><alter>-1</alter><octave>6</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <accidental>flat</accidental>
      </note>
    </measure>
  </part>
  <part id="P2">
    <measure number="18">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>3</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="6">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key></attributes>
      <note><pitch><step>E</step><alter>-1</alter><octave>3</octave></pitch><duration>8</duration><type>half</type><accidental>flat</accidental></note>
    </measure>
    <measure number="11">
      <note><pitch><step>E</step><alter>-1</alter><octave>3</octave></pitch><duration>8</duration><type>half</type><accidental>flat</accidental></note>
    </measure>
    <measure number="27">
      <note><pitch><step>A</step><alter>-1</alter><octave>3</octave></pitch><duration>8</duration><type>half</type><accidental>flat</accidental></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_sio_non_miro_line_cleanups == 5
    assert text.count("<step>D</step>") == 2
    assert text.count("<step>G</step>") == 1
    assert text.count("<alter>1</alter>") == 3
    assert "<octave>6</octave>" not in text
    assert "<octave>5</octave>" in text
    assert "<duration>2</duration>\n        <type>eighth</type>" in text
    assert text.count("<rest />") == 0


def test_musicxml_engraving_cleanup_applies_come_unto_me_local_cleanups(tmp_path):
    xml_path = tmp_path / "come_unto_me_local_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Come Unto Me</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
    <score-part id="P3"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="23">
      <attributes><divisions>4</divisions><key><fifths>-2</fifths></key></attributes>
      <note><rest /><duration>10</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="49">
      <note><rest /><duration>13</duration><type>half</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><type>16th</type><accidental>natural</accidental></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="15">
      <attributes><divisions>4</divisions><key><fifths>-2</fifths></key></attributes>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type><tie type="start" /><notations><tied type="start" /></notations></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type><tie type="stop" /><notations><tied type="stop" /></notations></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="23">
      <attributes><divisions>4</divisions><key><fifths>-2</fifths></key></attributes>
      <note><rest /><duration>10</duration><type>half</type></note>
      <note><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><type>eighth</type><accidental>flat</accidental></note>
      <note><chord /><pitch><step>A</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><type>eighth</type><accidental>flat</accidental></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.applied_come_unto_me_line_cleanups == 3
    assert text.count("<chord />") == 1
    assert "<step>A</step>\n          <alter>-1</alter>\n          <octave>4</octave>" in text
    assert text.count("<step>A</step>") == 1
    assert text.count("<step>C</step>") == 3
    assert "<tie" not in text
    assert "<tied" not in text
    assert "<step>E</step>\n          <alter>-1</alter>\n          <octave>5</octave>" in text
    assert "<accidental>natural</accidental>" not in text


def test_musicxml_engraving_cleanup_applies_moro_lasso_local_cleanups(tmp_path):
    xml_path = tmp_path / "moro_lasso_local_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Moro, lasso, al mio duolo</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
    <score-part id="P3"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="7">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>3</duration><type>eighth</type><dot /></note>
    </measure>
    <measure number="33">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>8</duration><type>half</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="7">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
    </measure>
    <measure number="33">
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><chord /><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="7">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>6</duration><type>quarter</type><dot /></note>
    </measure>
    <measure number="9">
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>F</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    second_report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()

    assert report.applied_moro_lasso_line_cleanups == 7
    assert second_report.normalized_dangling_ties == 0
    violin_ii_measures = root.find("part[@id='P1']")
    viola_measures = root.find("part[@id='P2']")
    assert violin_ii_measures is not None
    assert viola_measures is not None

    violin_ii_bar_33 = violin_ii_measures.find("measure[@number='33']")
    viola_bar_33 = viola_measures.find("measure[@number='33']")
    assert violin_ii_bar_33 is not None
    assert viola_bar_33 is not None
    assert "<step>E</step>" in ET.tostring(violin_ii_bar_33, encoding="unicode")
    assert "<chord" not in ET.tostring(viola_bar_33, encoding="unicode")
    assert ET.tostring(viola_bar_33, encoding="unicode").count("<step>E</step>") == 1
    assert ET.tostring(viola_bar_33, encoding="unicode").count("<step>A</step>") == 3
    assert ET.tostring(viola_bar_33, encoding="unicode").count('type="start"') == 4
    assert ET.tostring(viola_bar_33, encoding="unicode").count('type="stop"') == 4
    offsets: list[tuple[Fraction, Fraction, str, str | None, set[str], list[tuple[str, str]]]] = []
    offset = Fraction(0, 1)
    for note_element in viola_bar_33.findall("note"):
        if note_element.find("chord") is not None:
            continue
        duration = Fraction(int(note_element.findtext("duration") or "0"), 4)
        pitch_element = note_element.find("pitch")
        note_name = "rest" if pitch_element is None else f"{pitch_element.findtext('step')}{pitch_element.findtext('octave')}"
        tie_types = {tie_element.get("type") or "" for tie_element in note_element.findall("tie")}
        beams = [(beam.get("number") or "", beam.text or "") for beam in note_element.findall("beam")]
        offsets.append((offset, offset + duration, note_name, note_element.findtext("type"), tie_types, beams))
        offset += duration
    assert offsets[2:] == [
        (Fraction(1, 1), Fraction(5, 4), "G4", "16th", set(), [("1", "begin"), ("2", "begin")]),
        (Fraction(5, 4), Fraction(3, 2), "A4", "16th", {"start"}, [("1", "continue"), ("2", "end")]),
        (Fraction(3, 2), Fraction(2, 1), "A4", "eighth", {"stop", "start"}, [("1", "end")]),
        (Fraction(2, 1), Fraction(4, 1), "A4", "half", {"stop"}, []),
    ]

    text = xml_path.read_text(encoding="utf-8")
    assert text.count("<duration>4</duration>\n        <type>quarter</type>") >= 4


def test_musicxml_engraving_cleanup_applies_sparge_la_morte_local_cleanups(tmp_path):
    xml_path = tmp_path / "sparge_la_morte_local_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Sparge la morte</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
    <score-part id="P3"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="49">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><pitch><step>E</step><alter>-1</alter><octave>5</octave></pitch><duration>16</duration><type>whole</type><accidental>flat</accidental></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="40">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><pitch><step>C</step><alter>1</alter><octave>4</octave></pitch><duration>4</duration><type>quarter</type><accidental>sharp</accidental></note>
      <note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>4</duration><type>quarter</type><accidental>sharp</accidental></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="19">
      <attributes><divisions>4</divisions><key><fifths>0</fifths></key></attributes>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>3</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()

    assert report.applied_sparge_la_morte_line_cleanups == 4
    text = xml_path.read_text(encoding="utf-8")
    assert "<step>C</step>\n          <alter>1</alter>" not in text
    assert "<step>F</step>\n          <alter>1</alter>" not in text
    assert "<step>E</step>\n          <alter>-1</alter>" not in text
    assert "<step>D</step>\n          <alter>-1</alter>" in text
    assert "<step>G</step>\n          <alter>-1</alter>" in text
    assert "<step>D</step>\n          <alter>1</alter>" in text

    cello_bar_19 = root.find("part[@id='P3']/measure[@number='19']")
    assert cello_bar_19 is not None
    d_notes = [
        note_element
        for note_element in cello_bar_19.findall("note")
        if note_element.findtext("pitch/step") == "D" and note_element.findtext("pitch/octave") == "3"
    ]
    assert [note_element.findtext("type") for note_element in d_notes] == ["quarter", "quarter"]
    assert ["start"] == [tie_element.get("type") for tie_element in d_notes[0].findall("tie")]
    assert ["stop"] == [tie_element.get("type") for tie_element in d_notes[1].findall("tie")]


def test_musicxml_engraving_cleanup_extends_hark_cello_bar_six_c(tmp_path):
    xml_path = tmp_path / "hark_cello_sustain.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Hark! The Herald Angels Sing</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin II</part-name></score-part>
    <score-part id="P2"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="5">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>16</duration><type>whole</type></note>
    </measure>
    <measure number="6">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>10</duration><type>half</type><dot /></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="5">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>F</sign><line>4</line></clef>
      </attributes>
      <note><pitch><step>D</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
    </measure>
    <measure number="6">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>F</sign><line>4</line></clef>
      </attributes>
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><pitch><step>F</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.removed_isolated_redundant_notes == 0
    assert report.extended_isolated_redundant_notes == 1
    assert text.count("<step>C</step>") == 2
    assert "<duration>4</duration>\n        <type>quarter</type>" in text


def test_musicxml_engraving_cleanup_applies_hark_herald_local_cleanups(tmp_path):
    xml_path = tmp_path / "hark_herald_local_cleanups.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Hark! The Herald Angels Sing</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
    <score-part id="P3"><part-name>Viola</part-name></score-part>
    <score-part id="P4"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="10">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><rest /><duration>16</duration><type>whole</type></note>
    </measure>
    <measure number="12"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="34">
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>15</duration><type>whole</type></note>
      <note><rest /><duration>1</duration><type>16th</type></note>
    </measure>
    <measure number="44">
      <note><pitch><step>G</step><alter>1</alter><octave>4</octave></pitch><duration>16</duration><accidental>sharp</accidental><type>whole</type></note>
    </measure>
    <measure number="65">
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><chord /><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
    </measure>
    <measure number="67"><note><rest /><duration>16</duration><type>whole</type></note></measure>
  </part>
  <part id="P2">
    <measure number="10">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><rest /><duration>16</duration><type>whole</type></note>
    </measure>
    <measure number="12">
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>2</duration><type>eighth</type></note>
      <note><rest /><duration>8</duration><type>half</type></note>
    </measure>
    <measure number="34"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="44"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="65"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="67"><note><rest /><duration>16</duration><type>whole</type></note></measure>
  </part>
  <part id="P3">
    <measure number="10">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>C</sign><line>3</line></clef></attributes>
      <note><rest /><duration>16</duration><type>whole</type></note>
    </measure>
    <measure number="12"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="34">
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><pitch><step>D</step><alter>1</alter><octave>4</octave></pitch><duration>8</duration><accidental>sharp</accidental><type>half</type></note>
      <note><chord /><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>8</duration><accidental>flat</accidental><type>half</type></note>
    </measure>
    <measure number="44"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="65">
      <note><rest /><duration>14</duration><type>half</type><dot /></note>
      <note><pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch><duration>2</duration><accidental>flat</accidental><type>eighth</type></note>
      <note><chord /><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>2</duration><accidental>sharp</accidental><type>eighth</type></note>
    </measure>
    <measure number="67">
      <note><rest /><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>G</step><alter>1</alter><octave>3</octave></pitch><duration>12</duration><accidental>sharp</accidental><type>half</type><dot /></note>
      <note><chord /><pitch><step>B</step><alter>1</alter><octave>3</octave></pitch><duration>12</duration><accidental>sharp</accidental><type>half</type><dot /></note>
    </measure>
  </part>
  <part id="P4">
    <measure number="10">
      <attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>F</sign><line>4</line></clef></attributes>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>D</step><alter>-1</alter><octave>3</octave></pitch><duration>4</duration><accidental>flat</accidental><type>quarter</type></note>
    </measure>
    <measure number="12"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="34"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="44"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="65"><note><rest /><duration>16</duration><type>whole</type></note></measure>
    <measure number="67"><note><rest /><duration>16</duration><type>whole</type></note></measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()

    assert report.applied_hark_herald_line_cleanups >= 12

    parts = root.findall("part")
    violin_i_bar_34 = parts[0].find("measure[@number='34']")
    assert violin_i_bar_34 is not None
    assert violin_i_bar_34.findtext("note/duration") == "16"
    assert len(violin_i_bar_34.findall("note")) == 1

    violin_ii_bar_12 = parts[1].find("measure[@number='12']")
    assert violin_ii_bar_12 is not None
    g_notes = [
        note_element
        for note_element in violin_ii_bar_12.findall("note")
        if note_element.findtext("pitch/step") == "G"
    ]
    assert g_notes[0].findtext("duration") == "4"
    assert g_notes[0].findtext("type") == "quarter"

    viola_bar_34 = parts[2].find("measure[@number='34']")
    assert viola_bar_34 is not None
    assert any(
        note_element.findtext("pitch/step") == "A"
        and note_element.findtext("pitch/alter") == "1"
        and note_element.findtext("pitch/octave") == "4"
        for note_element in viola_bar_34.findall("note")
    )

    for part in parts:
        bar_44 = part.find("measure[@number='44']")
        assert bar_44 is not None
        assert bar_44.findtext("attributes/key/fifths") == "-4"

    viola_bar_65 = parts[2].find("measure[@number='65']")
    assert viola_bar_65 is not None
    assert all(note_element.find("chord") is None for note_element in viola_bar_65.findall("note"))

    viola_bar_67 = parts[2].find("measure[@number='67']")
    assert viola_bar_67 is not None
    spellings = [
        (note_element.findtext("pitch/step"), note_element.findtext("pitch/alter"))
        for note_element in viola_bar_67.findall("note")
        if note_element.find("pitch") is not None
    ]
    assert ("A", "-1") in spellings
    assert ("C", None) in spellings
    assert all(note_element.find("accidental") is None for note_element in viola_bar_67.findall("note"))

    cello_bar_10 = parts[3].find("measure[@number='10']")
    assert cello_bar_10 is not None
    assert any(
        note_element.findtext("pitch/step") == "C" and note_element.findtext("pitch/alter") == "1"
        for note_element in cello_bar_10.findall("note")
    )


def test_musicxml_engraving_cleanup_applies_a_quiet_place_bar_5_override(tmp_path):
    xml_path = tmp_path / "a_quiet_place_bar_5.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>A Quiet Place</movement-title>
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
    <score-part id="P3"><part-name>Viola</part-name></score-part>
    <score-part id="P4"><part-name>Violoncello</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="5">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>8</duration><accidental>sharp</accidental><type>half</type></note>
      <note><chord /><pitch><step>D</step><octave>5</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>4</duration><accidental>natural</accidental><type>quarter</type></note>
      <note><chord /><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="5">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>12</duration><type>half</type><dot /></note>
      <note><chord /><pitch><step>A</step><octave>4</octave></pitch><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P3">
    <measure number="5">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>C</sign><line>3</line></clef></attributes>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>8</duration><type>half</type></note>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><chord /><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P4">
    <measure number="5">
      <attributes><divisions>4</divisions><key><fifths>-1</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>F</sign><line>4</line></clef></attributes>
      <note><pitch><step>B</step><alter>-1</alter><octave>2</octave></pitch><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>B</step><alter>-1</alter><octave>2</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><chord /><pitch><step>G</step><octave>2</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    root = ET.parse(xml_path).getroot()
    parts = root.findall("part")

    assert report.applied_a_quiet_place_line_cleanups >= 10

    violin_i_notes = parts[0].findall("measure[@number='5']/note")
    assert violin_i_notes[0].findtext("pitch/step") == "E"
    assert violin_i_notes[0].findtext("pitch/alter") is None
    assert any(
        note_element.find("chord") is not None
        and note_element.findtext("pitch/step") == "E"
        and note_element.findtext("pitch/octave") == "4"
        for note_element in violin_i_notes
    )

    violin_ii_notes = parts[1].findall("measure[@number='5']/note")
    assert len(violin_ii_notes) == 2
    assert [note_element.findtext("duration") for note_element in violin_ii_notes] == ["16", "16"]
    assert [note_element.findtext("type") for note_element in violin_ii_notes] == ["whole", "whole"]

    viola_pitches = [
        (note_element.findtext("pitch/step"), note_element.findtext("pitch/alter"), note_element.findtext("pitch/octave"))
        for note_element in parts[2].findall("measure[@number='5']/note")
        if note_element.find("pitch") is not None
    ]
    assert viola_pitches == [("F", "1", "4"), ("F", None, "4"), ("E", None, "4")]

    cello_notes = parts[3].findall("measure[@number='5']/note")
    assert len(cello_notes) == 2
    assert all(note_element.find("chord") is None for note_element in cello_notes)


def test_musicxml_engraving_cleanup_keeps_isolated_uncovered_short_note(tmp_path):
    xml_path = tmp_path / "isolated_uncovered_short_note.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Violin II</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><rest /><duration>8</duration><type>half</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>3</duration><type>eighth</type><dot /></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><rest /><duration>12</duration><type>half</type><dot /></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><rest /><duration>7</duration><type>quarter</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.removed_isolated_redundant_notes == 0
    assert text.count("<step>C</step>") == 1


def test_musicxml_engraving_cleanup_respells_flat_side_chromatic_neighbor(tmp_path):
    xml_path = tmp_path / "chromatic_neighbor.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-3</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><alter>1</alter><octave>5</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>natural</accidental>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.respelled_chromatic_context_accidentals == 1
    assert "<step>D</step>" in text
    assert "<alter>-1</alter>" in text
    assert "<accidental>flat</accidental>" in text
    assert "<accidental>natural</accidental>" not in text


def test_musicxml_engraving_cleanup_uses_score_key_for_parts_without_key(tmp_path):
    xml_path = tmp_path / "shared_key_signature.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
    <score-part id="P2"><part-name>Viola</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-3</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
  <part id="P2">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>C</sign><line>3</line></clef>
      </attributes>
      <note><pitch><step>A</step><alter>1</alter><octave>3</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>B</step><octave>3</octave></pitch><duration>3</duration><type>half</type><dot /></note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.respelled_key_signature_accidentals == 1
    assert "<step>A</step>" not in text
    assert text.count("<step>B</step>") == 3
    assert text.count("<alter>-1</alter>") == 2
    assert "<alter>1</alter>" not in text


def test_musicxml_engraving_cleanup_preserves_upward_leading_tone(tmp_path):
    xml_path = tmp_path / "leading_tone.musicxml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Violin I</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>-3</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>F</step><alter>1</alter><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    report = cleanup_musicxml_engraving(xml_path, xml_path)
    text = xml_path.read_text(encoding="utf-8")

    assert report.respelled_chromatic_context_accidentals == 0
    assert "<step>F</step>" in text
    assert "<alter>1</alter>" in text
    assert "<accidental>sharp</accidental>" in text


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


def test_build_bar_map_prefers_part_with_real_time_signature_changes():
    score = stream.Score()
    authoritative = stream.Part()
    authoritative.insert(0, meter.TimeSignature("4/4"))
    authoritative.insert(4, meter.TimeSignature("2/4"))
    authoritative.insert(6, meter.TimeSignature("4/4"))
    authoritative.insert(0, note.Note("C4", quarterLength=10))
    naive = stream.Part()
    naive.insert(0, meter.TimeSignature("4/4"))
    naive.insert(0, note.Note("E3", quarterLength=10))
    score.insert(0, authoritative)
    score.insert(0, naive)

    bars = build_bar_map(score)

    assert [(bar.start, bar.duration, bar.time_signature.ratioString if bar.time_signature else None) for bar in bars[:3]] == [
        (Fraction(0, 1), Fraction(4, 1), "4/4"),
        (Fraction(4, 1), Fraction(2, 1), "2/4"),
        (Fraction(6, 1), Fraction(4, 1), "4/4"),
    ]
    assert Fraction(8, 1) not in {bar.start for bar in bars}


def test_editorial_dynamic_points_avoid_final_diminuendo():
    points = _editorial_dynamic_points([0.2, 0.9, 0.4, 0.1], phrase_bars=2)

    assert points[-1].bar_index == 3
    assert points[-1].level > points[-2].level


def test_strip_time_modifications_preserves_tuplet_notations(tmp_path):
    path = tmp_path / "tuplets.musicxml"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part id="P1">
    <measure number="1">
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="start"/></notations>
      </note>
    </measure>
  </part>
</score-partwise>
""",
        encoding="utf-8",
    )

    assert strip_time_modifications(path) == 1
    musicxml = path.read_text(encoding="utf-8")
    assert "<time-modification>" not in musicxml
    assert "<duration>1</duration>" in musicxml
    assert '<tuplet type="start"/>' in musicxml


def test_reduce_take6_to_quartet_preserves_triplet_time_modifications(monkeypatch, tmp_path):
    score = stream.Score()
    violin = stream.Part()
    violin.partName = "Violin I"
    measure = stream.Measure(number=1)
    measure.append(meter.TimeSignature("4/4"))
    for pitch_name in ("C4", "D4", "E4"):
        measure.append(note.Note(pitch_name, quarterLength=Fraction(1, 3)))
    measure.append(note.Rest(quarterLength=3))
    violin.append(measure)
    score.append(violin)

    for part_name in ("Violin II", "Viola", "Violoncello"):
        part = stream.Part()
        part.partName = part_name
        part_measure = stream.Measure(number=1)
        part_measure.append(meter.TimeSignature("4/4"))
        part_measure.append(note.Rest(quarterLength=4))
        part.append(part_measure)
        score.append(part)

    def fake_reduce_to_ensemble(*args, **kwargs):
        return score

    monkeypatch.setattr(reduction_module, "reduce_to_ensemble", fake_reduce_to_ensemble)
    output_path = tmp_path / "take6_triplet.musicxml"

    reduce_take6_to_quartet(tmp_path / "source.mid", out_path=output_path)

    musicxml = output_path.read_text(encoding="utf-8")
    assert musicxml.count("<time-modification>") == 3
    assert musicxml.count("<actual-notes>3</actual-notes>") == 3
    assert musicxml.count("<normal-notes>2</normal-notes>") == 3
    assert '<tuplet bracket="yes"' in musicxml


def test_normalize_musescore_rhythm_artifacts_rewrites_tiny_residues():
    score = stream.Score()
    part = stream.Part()
    measure = stream.Measure(number=1)
    measure.insert(0, meter.TimeSignature("4/4"))
    for offset, ql, pitch_name in [
        (0, 1, "C5"),
        (1, Fraction(1, 4), "C5"),
        (Fraction(5, 4), Fraction(5, 12), "A4"),
        (Fraction(5, 3), Fraction(1, 3), "G4"),
        (2, 1, "G4"),
        (3, 1, "A4"),
    ]:
        measure.insert(offset, note.Note(pitch_name, quarterLength=ql))
    part.insert(0, measure)
    score.insert(0, part)

    changes = normalize_musescore_rhythm_artifacts(score)
    measure = list(score.parts[0].getElementsByClass(stream.Measure))[0]

    assert changes == 1
    assert [(ql_to_fraction(el.offset), ql_to_fraction(el.quarterLength)) for el in measure.notesAndRests] == [
        (Fraction(0, 1), Fraction(1, 1)),
        (Fraction(1, 1), Fraction(1, 4)),
        (Fraction(5, 4), Fraction(1, 2)),
        (Fraction(7, 4), Fraction(1, 4)),
        (Fraction(2, 1), Fraction(1, 1)),
        (Fraction(3, 1), Fraction(1, 1)),
    ]
    assert sum((ql_to_fraction(el.quarterLength) for el in measure.notesAndRests), Fraction(0, 1)) == 4


def test_normalize_musescore_grid_rhythm_preserves_measure_total():
    score = stream.Score()
    part = stream.Part()
    measure = stream.Measure(number=1)
    measure.insert(0, meter.TimeSignature("4/4"))
    for offset, ql, pitch_name in [
        (0, Fraction(1, 3), "G5"),
        (Fraction(1, 3), Fraction(1, 3), "A5"),
        (Fraction(2, 3), Fraction(1, 3), "G5"),
        (1, Fraction(1, 2), "F5"),
        (Fraction(3, 2), Fraction(7, 6), "E5"),
        (Fraction(8, 3), Fraction(2, 3), "D5"),
        (Fraction(10, 3), Fraction(1, 3), "C5"),
        (Fraction(11, 3), Fraction(1, 3), "D5"),
    ]:
        measure.insert(offset, note.Note(pitch_name, quarterLength=ql))
    part.insert(0, measure)
    score.insert(0, part)

    changes = normalize_musescore_grid_rhythm(score)

    assert changes == 1
    durations = [ql_to_fraction(el.quarterLength) for el in measure.notesAndRests]
    assert sum(durations, Fraction(0, 1)) == 4
    assert all(duration.denominator in {1, 2, 4} for duration in durations)


def test_build_measured_part_simplifies_tiny_output_rhythm_scar():
    events = [
        SourceEvent("d:first", 1, 0, Fraction(0, 1), Fraction(2, 3), 74, False),
        SourceEvent("d:second", 1, 1, Fraction(2, 3), Fraction(1, 4), 74, False),
        SourceEvent("b", 4, 2, Fraction(1, 1), Fraction(1, 1), 59, False),
    ]
    bars = [Bar(0, 1, Fraction(0, 1), Fraction(2, 1), meter.TimeSignature("2/4"))]

    part = build_measured_part(
        events,
        bars,
        part_name="Violin II",
        instrument_obj=instrument.Violin(),
        clef_obj=clef.TrebleClef(),
    )
    measure = list(part.getElementsByClass(stream.Measure))[0]

    assert [
        (ql_to_fraction(element.offset), element.pitch.nameWithOctave, ql_to_fraction(element.quarterLength))
        for element in measure.notes
    ] == [
        (Fraction(0, 1), "D5", Fraction(1, 1)),
        (Fraction(1, 1), "B3", Fraction(1, 1)),
    ]


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

    report = cleanup_score(score, beat_readability=False)

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


def test_cleanup_score_keeps_cello_bass_clef_for_isolated_high_measure():
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

    assert report.cello_clef_changes_added == 0
    assert not list(second_measure.getElementsByClass(clef.Clef))
    assert not list(third_measure.getElementsByClass(clef.Clef))


def test_cleanup_score_adds_cello_tenor_clef_for_sustained_high_run():
    score = stream.Score()
    cello = stream.Part()
    cello.partName = "Violoncello"
    first_measure = stream.Measure(number=1)
    first_measure.insert(0, clef.BassClef())
    first_measure.insert(0, note.Note("C3", quarterLength=4))
    second_measure = stream.Measure(number=2)
    second_measure.insert(0, note.Note("G4", quarterLength=4))
    third_measure = stream.Measure(number=3)
    third_measure.insert(0, note.Note("G4", quarterLength=4))
    fourth_measure = stream.Measure(number=4)
    fourth_measure.insert(0, note.Note("C3", quarterLength=4))
    cello.insert(0, first_measure)
    cello.insert(4, second_measure)
    cello.insert(8, third_measure)
    cello.insert(12, fourth_measure)
    score.insert(0, cello)

    report = cleanup_score(score)

    assert report.cello_clef_changes_added == 2
    assert any(isinstance(item, clef.TenorClef) for item in second_measure.getElementsByClass(clef.Clef))
    assert not list(third_measure.getElementsByClass(clef.Clef))
    assert any(isinstance(item, clef.BassClef) for item in fourth_measure.getElementsByClass(clef.Clef))


def test_cleanup_score_normalizes_tied_release_residue_to_beat():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin I"
    part.insert(0, meter.TimeSignature("4/4"))
    measure = stream.Measure(number=1)
    first = note.Note("G4", quarterLength=2)
    first.tie = tie.Tie("start")
    second = note.Note("G4", quarterLength=0.75)
    second.tie = tie.Tie("stop")
    measure.insert(0, first)
    measure.insert(2, second)
    measure.insert(2.75, note.Rest(quarterLength=1))
    measure.insert(3.75, note.Rest(quarterLength=0.25))
    part.append(measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.beat_readability_changes == 3
    items = list(measure.notesAndRests)
    assert [(ql_to_fraction(item.offset), ql_to_fraction(item.quarterLength)) for item in items] == [
        (Fraction(0, 1), Fraction(3, 1)),
        (Fraction(3, 1), Fraction(1, 1)),
    ]
    assert items[0].tie is None


def test_cleanup_score_does_not_split_rests_that_cross_beat_boundaries():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Cello"
    part.insert(0, meter.TimeSignature("4/4"))
    measure = stream.Measure(number=1)
    measure.insert(0, note.Rest(quarterLength=1))
    measure.insert(1, note.Note("C3", quarterLength=0.5))
    measure.insert(1.5, note.Rest(quarterLength=1))
    measure.insert(2.5, note.Note("D3", quarterLength=1.5))
    part.append(measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.beat_readability_changes == 0
    items = [(ql_to_fraction(item.offset), ql_to_fraction(item.quarterLength), item.isRest) for item in measure.notesAndRests]
    assert items == [
        (Fraction(0, 1), Fraction(1, 1), True),
        (Fraction(1, 1), Fraction(1, 2), False),
        (Fraction(3, 2), Fraction(1, 1), True),
        (Fraction(5, 2), Fraction(3, 2), False),
    ]


def test_cleanup_score_keeps_viola_alto_clef_for_ordinary_high_passage():
    score = stream.Score()
    viola = stream.Part()
    viola.partName = "Viola"
    viola.insert(0, clef.AltoClef())
    first_measure = stream.Measure(number=1)
    first_measure.insert(0, clef.AltoClef())
    first_measure.insert(0, note.Note("C4", quarterLength=4))
    second_measure = stream.Measure(number=2)
    second_measure.insert(0, note.Note("A4", quarterLength=4))
    third_measure = stream.Measure(number=3)
    third_measure.insert(0, note.Note("C4", quarterLength=4))
    viola.append(first_measure)
    viola.append(second_measure)
    viola.append(third_measure)
    score.insert(0, viola)

    report = cleanup_score(score)

    assert report.viola_clef_changes_added == 0
    assert not list(second_measure.getElementsByClass(clef.Clef))
    assert not list(third_measure.getElementsByClass(clef.Clef))


def test_cleanup_score_adds_viola_treble_clef_only_for_sustained_very_high_run():
    score = stream.Score()
    viola = stream.Part()
    viola.partName = "Viola"
    viola.insert(0, clef.AltoClef())
    first_measure = stream.Measure(number=1)
    first_measure.insert(0, clef.AltoClef())
    first_measure.insert(0, note.Note("C4", quarterLength=4))
    second_measure = stream.Measure(number=2)
    second_measure.insert(0, note.Note("E5", quarterLength=4))
    third_measure = stream.Measure(number=3)
    third_measure.insert(0, note.Note("E5", quarterLength=4))
    fourth_measure = stream.Measure(number=4)
    fourth_measure.insert(0, note.Note("C4", quarterLength=4))
    viola.append(first_measure)
    viola.append(second_measure)
    viola.append(third_measure)
    viola.append(fourth_measure)
    score.insert(0, viola)

    report = cleanup_score(score)

    assert report.viola_clef_changes_added == 2
    assert any(isinstance(item, clef.TrebleClef) for item in second_measure.getElementsByClass(clef.Clef))
    assert not list(third_measure.getElementsByClass(clef.Clef))
    assert any(isinstance(item, clef.AltoClef) for item in fourth_measure.getElementsByClass(clef.Clef))


def test_cleanup_score_respells_key_signature_enharmonics():
    score = stream.Score()
    part = stream.Part()
    part.partName = "Violin I"
    measure = stream.Measure(number=1)
    measure.insert(0, key.KeySignature(-3))
    g_sharp = note.Note("G#4", quarterLength=1)
    g_sharp.pitch.accidental.displayStatus = True
    measure.insert(0, g_sharp)
    part.append(measure)
    score.insert(0, part)

    report = cleanup_score(score)

    assert report.respelled_key_signature_accidentals == 1
    assert g_sharp.pitch.nameWithOctave == "A-4"
    assert g_sharp.pitch.accidental.displayStatus is False


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


def test_take6_voice_preservation_keeps_continuing_octave_duplicate_line():
    score = make_score(
        [
            make_part("lead", [(0, 1, "G5"), (1, 1, "A5"), (4, 1, "G5")]),
            make_part("high inner", [(4, 1, "E5")]),
            make_part("inner 1", [(4, 1, "D4")]),
            make_part("inner 2", [(4, 1, "B3")]),
            make_part("borrowed lower line", [(0, 1, "E3"), (1, 1, "A3"), (4, 1, "C3")]),
            make_part("bass", [(4, 1, "C2")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    carrying_parts = []
    for part_index, part in enumerate(reduced.parts):
        early_notes = [
            element
            for element in part.flatten().notes
            if ql_to_fraction(element.offset) in {Fraction(0, 1), Fraction(1, 1)}
            and getattr(element.editorial, "sourcePartIndex", None) == 4
        ]
        if early_notes:
            carrying_parts.append((part_index, [element.pitch.nameWithOctave for element in early_notes]))

    assert carrying_parts == [(2, ["E3", "A3"])]


def test_take6_does_not_put_high_borrowed_duplicate_in_cello():
    score = make_score(
        [
            make_part("lead", [(0, 1, "C6"), (1, 1, None)]),
            make_part("duplicate upper glue", [(0, 1, "C5"), (1, 1, "D5")]),
            make_part("inner color", [(0, 1, "E4"), (1, 1, "E4")]),
            make_part("inner 2", [(0, 1, None), (1, 1, "A4")]),
            make_part("lower inner", [(0, 1, None), (1, 1, "G3")]),
            make_part("bass", [(0, 1, None), (1, 1, "C2")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    cello_notes = list(reduced.parts[3].flatten().notes)

    assert not any(
        element.pitch.nameWithOctave == "C5"
        and ql_to_fraction(element.offset) == Fraction(0, 1)
        for element in cello_notes
    )


def test_gesualdo_voice_preservation_avoids_high_borrowed_cello():
    score = make_score(
        [
            make_part("soprano", [(0, 1, "C6"), (1, 1, None)]),
            make_part("alto", [(0, 1, "C5"), (1, 1, None)]),
            make_part("tenor", [(0, 1, "E4"), (1, 1, None)]),
            make_part("baritone", [(0, 1, "C4"), (1, 1, None)]),
            make_part("bass", [(0, 1, None), (1, 1, "C2")]),
        ]
    )

    reduced = build_quartet_score(score, enforce_ranges=False, preserve_active_voice_count=True)
    cello_notes = list(reduced.parts[3].flatten().notes)

    assert all(
        element.pitch.midi <= STRING_QUARTET.bottom_part.preferred_register[1]
        or getattr(element.editorial, "sourcePartIndex", None) == 4
        for element in cello_notes
    )
    assert not any(
        element.pitch.nameWithOctave == "C5"
        and getattr(element.editorial, "sourcePartIndex", None) == 1
        for element in cello_notes
    )


def test_gesualdo_primary_selection_avoids_high_borrowed_cello():
    score = make_score(
        [
            make_part("soprano I", [(0, 4, "F5")]),
            make_part("soprano II", [(0, 1, "D5"), (1, 1, "C5"), (2, 2, "B-4")]),
            make_part("alto", [(0, 4, "F4")]),
            make_part("tenor", [(0, 4, "A4")]),
            make_part("bass", [(0, 2, None), (2, 2, "B-3")]),
        ]
    )

    reduced = build_quartet_score(
        score,
        enforce_ranges=False,
        preserve_active_voice_count=True,
        add_editorial_harmony=True,
        add_editorial_thirds=True,
    )
    cello_notes = list(reduced.parts[3].flatten().notes)

    assert not any(
        element.pitch.nameWithOctave == "C5"
        and getattr(element.editorial, "sourcePartIndex", None) == 1
        for element in cello_notes
    )
    assert any(
        element.pitch.nameWithOctave == "B-3"
        and getattr(element.editorial, "sourcePartIndex", None) == 4
        for element in cello_notes
    )


def test_take6_lowers_high_cello_line_into_sweet_spot():
    score = make_score(
        [
            make_part("lead", [(0, 2, "C6"), (2, 2, "D6")]),
            make_part("alto", [(0, 4, "B-4")]),
            make_part("tenor", [(0, 4, "G4")]),
            make_part("inner", [(0, 4, "E4")]),
            make_part("baritone", [(0, 4, "C4")]),
            make_part("bass", [(0, 2, "G3"), (2, 2, "F3")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    cello_notes = list(reduced.parts[3].flatten().notes)

    assert [element.pitch.nameWithOctave for element in cello_notes] == ["G2", "F3"]


def test_take6_lowers_only_playable_high_cello_double_stops():
    score = make_score(
        [
            make_part("lead", [(0, 4, "C6")]),
            make_part("alto", [(0, 4, "A4")]),
            make_part("tenor", [(0, 4, "F4")]),
            make_part("inner", [(0, 4, "E4")]),
            make_part("baritone", [(0, 4, "C4")]),
            make_part("bass", [(0, 4, "C4")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False, add_source_double_stops=True)
    cello_notes = list(reduced.parts[3].flatten().notes)
    cello_pitches = [
        pitch.nameWithOctave
        for element in cello_notes
        for pitch in (element.pitches if element.isChord else [element.pitch])
    ]

    assert "C3" in cello_pitches
    assert "C4" not in cello_pitches


def test_high_cello_register_pass_can_lower_only_upper_chord_pitch():
    score = stream.Score()
    cello_part = stream.Part()
    cello_part.partName = "Violoncello"
    cello_part.insert(0, meter.TimeSignature("4/4"))
    measure = stream.Measure(number=1)
    measure.append(chord.Chord(["D3", "F4"], quarterLength=4))
    cello_part.append(measure)
    score.insert(0, cello_part)

    changed = _lower_high_cello_register(score, STRING_QUARTET.bottom_part, 55)
    lowered = list(score.parts[0].recurse().notes)[0]

    assert changed == 1
    assert [pitch.nameWithOctave for pitch in lowered.pitches] == ["D3", "F3"]


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


def test_take6_reduction_disables_editorial_dynamics(tmp_path):
    score = make_score(
        [
            make_part("lead", [(0, 8, "C6"), (8, 4, "D6")]),
            make_part("alto", [(0, 8, "A4"), (8, 4, "B4")]),
            make_part("tenor", [(0, 8, "F4"), (8, 4, "G4")]),
            make_part("inner", [(0, 8, "E4"), (8, 4, "F4")]),
            make_part("baritone", [(0, 8, "C4"), (8, 4, "D4")]),
            make_part("bass", [(0, 8, "C3"), (8, 4, "D3")]),
        ]
    )

    reduced = build_take6_quartet_score(score, enforce_ranges=False)
    out_path = tmp_path / "take6_without_dynamics.musicxml"
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


def test_smooth_isolated_handoff_fills_neighbor_line_gap():
    assignments = {
        "vln1": [],
        "vln2": [
            SourceEvent("src:vln2:d", 1, 0, Fraction(1, 1), Fraction(1, 4), 62, False),
            SourceEvent("src:vln2:bb", 1, 1, Fraction(3, 2), Fraction(1, 4), 58, False),
            SourceEvent("src:vln2:a", 1, 2, Fraction(7, 4), Fraction(1, 4), 57, False),
        ],
        "vla": [
            SourceEvent("src:vla:eb", 2, 0, Fraction(0, 1), Fraction(2, 1), 63, False),
        ],
        "vc": [
            SourceEvent("src:vc:low", 3, 0, Fraction(0, 1), Fraction(1, 1), 51, False),
            SourceEvent("src:vc:c", 3, 1, Fraction(5, 4), Fraction(1, 4), 60, False),
            SourceEvent("src:vc:d", 3, 2, Fraction(2, 1), Fraction(1, 1), 50, False),
        ],
    }

    smoothed = _smooth_isolated_handoffs(assignments, STRING_QUARTET, ReductionConfig())

    vln2_pitches = [
        event.pitch_midi
        for event in smoothed["vln2"]
        if Fraction(1, 1) <= event.start < Fraction(2, 1)
    ]
    cello_offsets = {event.start for event in smoothed["vc"]}
    assert vln2_pitches == [62, 60, 58, 57]
    assert Fraction(5, 4) not in cello_offsets


def test_smooth_isolated_handoff_trims_receiver_note_before_insert():
    assignments = {
        "vln1": [],
        "vln2": [],
        "vla": [
            SourceEvent("src:vla:a", 2, 0, Fraction(2, 1), Fraction(1, 2), 69, False),
            SourceEvent("src:vla:g", 2, 1, Fraction(5, 2), Fraction(1, 2), 67, False),
        ],
        "vc": [
            SourceEvent("src:vc:c", 3, 0, Fraction(9, 4), Fraction(1, 4), 60, False),
            SourceEvent("src:vc:b", 3, 1, Fraction(3, 1), Fraction(1, 4), 59, False),
        ],
    }

    smoothed = _smooth_isolated_handoffs(assignments, STRING_QUARTET, ReductionConfig())

    viola_events = [
        (event.start, event.duration, event.pitch_midi)
        for event in smoothed["vla"]
        if Fraction(2, 1) <= event.start < Fraction(3, 1)
    ]
    cello_offsets = {event.start for event in smoothed["vc"]}
    assert viola_events == [
        (Fraction(2, 1), Fraction(1, 4), 69),
        (Fraction(9, 4), Fraction(1, 4), 60),
        (Fraction(5, 2), Fraction(1, 2), 67),
    ]
    assert Fraction(9, 4) not in cello_offsets


def test_smooth_isolated_handoff_absorbs_playable_adjacent_double_stop_when_trim_is_not_clear():
    assignments = {
        "vln1": [],
        "vln2": [],
        "vla": [
            SourceEvent("src:vla:a", 2, 0, Fraction(2, 1), Fraction(1, 1), 69, False),
            SourceEvent("src:vla:g", 2, 1, Fraction(3, 1), Fraction(1, 2), 67, False),
        ],
        "vc": [
            SourceEvent("src:vc:c", 3, 0, Fraction(9, 4), Fraction(1, 4), 60, False),
            SourceEvent("src:vc:b", 3, 1, Fraction(7, 2), Fraction(1, 4), 59, False),
        ],
    }

    smoothed = _smooth_isolated_handoffs(assignments, STRING_QUARTET, ReductionConfig())

    viola_events = [
        (event.start, event.duration, event.pitch_midi)
        for event in smoothed["vla"]
        if Fraction(2, 1) <= event.start < Fraction(3, 1)
    ]
    cello_offsets = {event.start for event in smoothed["vc"]}
    assert viola_events == [
        (Fraction(2, 1), Fraction(1, 4), 69),
        (Fraction(9, 4), Fraction(1, 4), 60),
        (Fraction(9, 4), Fraction(1, 4), 69),
        (Fraction(5, 2), Fraction(1, 2), 69),
    ]
    assert Fraction(9, 4) not in cello_offsets


def test_smooth_isolated_handoff_extends_receiver_tail_line():
    assignments = {
        "vln1": [
            SourceEvent("src:vln1:a", 0, 0, Fraction(3, 1), Fraction(1, 2), 57, False),
            SourceEvent("src:vln1:f", 0, 1, Fraction(7, 2), Fraction(1, 4), 65, False),
        ],
        "vln2": [
            SourceEvent("src:vln2:a", 1, 0, Fraction(3, 1), Fraction(1, 1), 69, False),
        ],
        "vla": [
            SourceEvent("src:vla:d", 2, 0, Fraction(3, 1), Fraction(1, 2), 62, False),
            SourceEvent("src:vla:g", 2, 1, Fraction(15, 4), Fraction(1, 4), 67, False),
            SourceEvent("src:vla:next_d", 2, 2, Fraction(4, 1), Fraction(1, 2), 62, False),
        ],
        "vc": [],
    }

    smoothed = _smooth_isolated_handoffs(assignments, STRING_QUARTET, ReductionConfig())

    vln1_tail = [
        (event.start, event.duration, event.pitch_midi)
        for event in smoothed["vln1"]
        if Fraction(3, 1) <= event.start < Fraction(4, 1)
    ]
    viola_offsets = {event.start for event in smoothed["vla"] if event.source_id != "src:vla:next_d"}
    assert vln1_tail == [
        (Fraction(3, 1), Fraction(1, 2), 57),
        (Fraction(7, 2), Fraction(1, 4), 65),
        (Fraction(15, 4), Fraction(1, 4), 67),
    ]
    assert Fraction(15, 4) not in viola_offsets


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


def test_title_from_source_path_ignores_cpdl_download_suffix():
    assert (
        title_from_source_path("data/cpdl/5-voices/sources/092_dolcissima_mia_vita__02_dolcissima_mia_vita_gesualdo.mxl")
        == "Dolcissima Mia Vita"
    )
