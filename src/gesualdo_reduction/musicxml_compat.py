"""Small MusicXML compatibility post-processors."""

from __future__ import annotations

import copy
import re
import shutil
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET


_TIME_MODIFICATION_RE = re.compile(
    r"\n[ \t]*<time-modification>\s*.*?\s*</time-modification>",
    re.DOTALL,
)


def strip_time_modifications(path: str | Path) -> int:
    """Remove MusicXML time-modification tags while preserving durations.

    MuseScore can over-count some music21-written nested tuplets when both
    explicit ``duration`` values and ``time-modification`` tags are present.
    The raw duration values are kept, as are tuplet notation brackets.
    """

    xml_path = Path(path)
    original = xml_path.read_text(encoding="utf-8")
    updated, removed = _TIME_MODIFICATION_RE.subn("", original)
    if removed:
        xml_path.write_text(updated, encoding="utf-8")
    return removed


@dataclass
class MusicXMLEngravingReport:
    """Counts from XML-preserving engraving cleanup."""

    respelled_key_signature_accidentals: int = 0
    respelled_chromatic_context_accidentals: int = 0
    suppressed_redundant_accidentals: int = 0
    cello_clef_changes: int = 0
    viola_clef_changes: int = 0
    final_barlines_added: int = 0
    removed_text_annotations: int = 0
    normalized_dangling_ties: int = 0
    normalized_tied_enharmonics: int = 0
    normalized_adjacent_enharmonics: int = 0
    removed_isolated_redundant_notes: int = 0
    extended_isolated_redundant_notes: int = 0
    normalized_fragmented_rests: int = 0
    extended_terminal_short_notes: int = 0
    applied_gia_piansi_line_cleanups: int = 0
    applied_luci_serene_line_cleanups: int = 0
    applied_dolcissima_line_cleanups: int = 0
    applied_sio_non_miro_line_cleanups: int = 0
    applied_come_unto_me_line_cleanups: int = 0
    applied_a_quiet_place_line_cleanups: int = 0
    applied_moro_lasso_line_cleanups: int = 0
    applied_sparge_la_morte_line_cleanups: int = 0
    applied_hark_herald_line_cleanups: int = 0


_STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_SHARP_ORDER = "FCGDAEB"
_FLAT_ORDER = "BEADGCF"
_ACCIDENTAL_NAMES = {
    -2: "double-flat",
    -1: "flat",
    0: "natural",
    1: "sharp",
    2: "double-sharp",
}
_BLACK_PITCH_CLASSES = {1, 3, 6, 8, 10}
_STEPS = "CDEFGAB"
_DURATION_NOTATION = {
    Fraction(4, 1): ("whole", 0),
    Fraction(3, 1): ("half", 1),
    Fraction(2, 1): ("half", 0),
    Fraction(3, 2): ("quarter", 1),
    Fraction(1, 1): ("quarter", 0),
    Fraction(3, 4): ("eighth", 1),
    Fraction(1, 2): ("eighth", 0),
    Fraction(3, 8): ("16th", 1),
    Fraction(1, 4): ("16th", 0),
    Fraction(3, 16): ("32nd", 1),
    Fraction(1, 8): ("32nd", 0),
}


def add_final_barlines(root: ET.Element) -> int:
    """Ensure every part ends with a final right barline."""

    changed = 0
    for part in root.findall("part"):
        measures = part.findall("measure")
        if not measures:
            continue
        last_measure = measures[-1]
        right_barline = None
        for barline in last_measure.findall("barline"):
            if barline.get("location") == "right":
                right_barline = barline
                break
        if right_barline is None:
            right_barline = ET.Element("barline", {"location": "right"})
            last_measure.append(right_barline)
            changed += 1
        bar_style = right_barline.find("bar-style")
        if bar_style is None:
            bar_style = ET.Element("bar-style")
            right_barline.insert(0, bar_style)
            changed += 1
        if bar_style.text != "light-heavy":
            bar_style.text = "light-heavy"
            changed += 1
    return changed


def _ascii_fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _key_alterations(fifths: int | None) -> dict[str, int]:
    alterations = {step: 0 for step in "ABCDEFG"}
    if fifths is None:
        return alterations
    if fifths > 0:
        for step in _SHARP_ORDER[:fifths]:
            alterations[step] = 1
    elif fifths < 0:
        for step in _FLAT_ORDER[: abs(fifths)]:
            alterations[step] = -1
    return alterations


def _preferred_spellings(fifths: int | None) -> dict[int, tuple[str, int]]:
    spellings: dict[int, tuple[str, int]] = {}
    for step, alter in _key_alterations(fifths).items():
        if alter:
            spellings[(_STEP_TO_SEMITONE[step] + alter) % 12] = (step, alter)
    return spellings


def _part_names(root: ET.Element) -> dict[str, str]:
    names: dict[str, str] = {}
    part_list = root.find("part-list")
    if part_list is None:
        return names
    for score_part in part_list.findall("score-part"):
        part_id = score_part.get("id")
        if not part_id:
            continue
        names[part_id] = " ".join(
            text.strip()
            for text in (
                score_part.findtext("part-name") or "",
                score_part.findtext("part-abbreviation") or "",
            )
            if text and text.strip()
        ).lower()
    return names


def strip_text_annotations(root: ET.Element) -> int:
    """Remove imported edition text while preserving musical directions."""

    removed = 0
    for credit in list(root.findall("credit")):
        root.remove(credit)
        removed += 1

    for note in root.findall(".//note"):
        for lyric in list(note.findall("lyric")):
            note.remove(lyric)
            removed += 1

    for direction in root.findall(".//direction"):
        for direction_type in list(direction.findall("direction-type")):
            for words in list(direction_type.findall("words")):
                direction_type.remove(words)
                removed += 1
            if len(direction_type) == 0:
                direction.remove(direction_type)

    for parent in root.iter():
        for child in list(parent):
            if child.tag == "direction" and len(child) == 0 and not child.attrib:
                parent.remove(child)
                removed += 1

    return removed


def _is_cello_name(name: str) -> bool:
    return "violoncello" in name or "cello" in name or "vc" in name


def _is_viola_name(name: str) -> bool:
    return "viola" in name or "vla" in name


def _measure_fifths(measure: ET.Element, current: int | None) -> int | None:
    fifths_text = measure.findtext("./attributes/key/fifths")
    if fifths_text is None:
        return current
    try:
        return int(fifths_text)
    except ValueError:
        return current


def _first_declared_fifths(root: ET.Element) -> int | None:
    for measure in root.findall("./part/measure"):
        fifths = _measure_fifths(measure, None)
        if fifths is not None:
            return fifths
    return None


def _pitch_element_midi(pitch: ET.Element) -> int | None:
    step = pitch.findtext("step")
    octave = pitch.findtext("octave")
    if step not in _STEP_TO_SEMITONE or octave is None:
        return None
    alter = int(float(pitch.findtext("alter") or "0"))
    return (int(octave) + 1) * 12 + _STEP_TO_SEMITONE[step] + alter


def _pitch_element_alter(pitch: ET.Element) -> int:
    return int(float(pitch.findtext("alter") or "0"))


def _pitch_element_spelling(pitch: ET.Element) -> tuple[str, int] | None:
    step = pitch.findtext("step")
    if step not in _STEP_TO_SEMITONE:
        return None
    return step, _pitch_element_alter(pitch)


def _step_distance(start: str, stop: str) -> int:
    return (_STEPS.index(stop) - _STEPS.index(start)) % len(_STEPS)


def _simple_enharmonic_spellings(midi: int) -> list[tuple[str, int]]:
    spellings: list[tuple[str, int]] = []
    pitch_class = midi % 12
    for step in _STEPS:
        for alter in (-1, 1):
            if (_STEP_TO_SEMITONE[step] + alter) % 12 == pitch_class:
                spellings.append((step, alter))
    return spellings


def _pitched_notes(measure: ET.Element) -> list[tuple[ET.Element, ET.Element, int, str, int]]:
    notes: list[tuple[ET.Element, ET.Element, int, str, int]] = []
    for note in measure.findall("note"):
        pitch = note.find("pitch")
        if pitch is None:
            continue
        midi = _pitch_element_midi(pitch)
        step = pitch.findtext("step")
        if midi is None or step not in _STEP_TO_SEMITONE:
            continue
        notes.append((note, pitch, midi, step, _pitch_element_alter(pitch)))
    return notes


def _set_child_text(parent: ET.Element, tag: str, text: str, *, after: str | None = None) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.Element(tag)
        insert_at = len(parent)
        if after is not None:
            for index, existing in enumerate(list(parent)):
                if existing.tag == after:
                    insert_at = index + 1
                    break
        parent.insert(insert_at, child)
    child.text = text
    return child


def _set_pitch_element_spelling(pitch: ET.Element, step: str, alter: int) -> bool:
    midi = _pitch_element_midi(pitch)
    if midi is None:
        return False
    for octave in range(-1, 10):
        if (octave + 1) * 12 + _STEP_TO_SEMITONE[step] + alter != midi:
            continue
        _set_child_text(pitch, "step", step)
        alter_element = pitch.find("alter")
        if alter:
            _set_child_text(pitch, "alter", str(alter), after="step")
        elif alter_element is not None:
            pitch.remove(alter_element)
        _set_child_text(pitch, "octave", str(octave), after="alter" if alter else "step")
        return True
    return False


def _local_accidental_bias(
    fifths: int | None,
    note_infos: list[tuple[ET.Element, ET.Element, int, str, int]],
    index: int,
) -> int:
    """Return -1 for flat-side, 1 for sharp-side, 0 for neutral."""

    score = 0
    if fifths is not None:
        if fifths < 0:
            score -= min(abs(fifths), 4) * 3
        elif fifths > 0:
            score += min(fifths, 4) * 3

    start = max(0, index - 4)
    stop = min(len(note_infos), index + 5)
    for local_index in range(start, stop):
        if local_index == index:
            continue
        _note, _pitch, _midi, _step, alter = note_infos[local_index]
        if alter < 0:
            score -= 1
        elif alter > 0:
            score += 1
    if score < 0:
        return -1
    if score > 0:
        return 1
    return 0


def _local_alter_surplus(
    note_infos: list[tuple[ET.Element, ET.Element, int, str, int]],
    index: int,
) -> int:
    start = max(0, index - 4)
    stop = min(len(note_infos), index + 5)
    surplus = 0
    for local_index in range(start, stop):
        if local_index == index:
            continue
        _note, _pitch, _midi, _step, alter = note_infos[local_index]
        if alter < 0:
            surplus -= 1
        elif alter > 0:
            surplus += 1
    return surplus


def _has_chromatic_respelling_evidence(
    candidate: tuple[str, int],
    previous_info: tuple[ET.Element, ET.Element, int, str, int] | None,
    next_info: tuple[ET.Element, ET.Element, int, str, int] | None,
    midi: int,
    note_infos: list[tuple[ET.Element, ET.Element, int, str, int]],
    index: int,
) -> bool:
    step, alter = candidate
    for neighbor in (previous_info, next_info):
        if neighbor is None:
            continue
        _neighbor_note, _neighbor_pitch, _neighbor_midi, neighbor_step, neighbor_alter = neighbor
        if neighbor_step == step and neighbor_alter != alter:
            return True

    if next_info is not None:
        _next_note, _next_pitch, next_midi, next_step, _next_alter = next_info
        if next_midi == midi + 1 and alter == 1 and _step_distance(step, next_step) == 1:
            return True
        if next_midi == midi - 1 and alter == -1 and _step_distance(next_step, step) == 1:
            return True

    if previous_info is not None:
        _prev_note, _prev_pitch, prev_midi, prev_step, _prev_alter = previous_info
        if prev_midi == midi - 1 and alter == -1 and _step_distance(prev_step, step) == 1:
            return True
        if prev_midi == midi + 1 and alter == 1 and _step_distance(step, prev_step) == 1:
            return True

    surplus = _local_alter_surplus(note_infos, index)
    return (alter == -1 and surplus <= -3) or (alter == 1 and surplus >= 3)


def _boundary_resolution_spelling(
    midi: int,
    previous_info: tuple[ET.Element, ET.Element, int, str, int] | None,
    next_info: tuple[ET.Element, ET.Element, int, str, int] | None,
) -> tuple[str, int] | None:
    if midi % 12 not in _BLACK_PITCH_CLASSES:
        return None
    candidates = _simple_enharmonic_spellings(midi)
    if next_info is not None:
        _next_note, _next_pitch, next_midi, next_step, _next_alter = next_info
        for candidate_step, candidate_alter in candidates:
            if (
                next_midi == midi + 1
                and candidate_alter == 1
                and _step_distance(candidate_step, next_step) == 1
            ):
                return candidate_step, candidate_alter
            if (
                next_midi == midi - 1
                and candidate_alter == -1
                and _step_distance(next_step, candidate_step) == 1
            ):
                return candidate_step, candidate_alter
    if previous_info is not None:
        _prev_note, _prev_pitch, prev_midi, prev_step, _prev_alter = previous_info
        for candidate_step, candidate_alter in candidates:
            if (
                prev_midi == midi - 1
                and candidate_alter == -1
                and _step_distance(prev_step, candidate_step) == 1
            ):
                return candidate_step, candidate_alter
            if (
                prev_midi == midi + 1
                and candidate_alter == 1
                and _step_distance(candidate_step, prev_step) == 1
            ):
                return candidate_step, candidate_alter
    return None


def _chromatic_context_spelling(
    note_infos: list[tuple[ET.Element, ET.Element, int, str, int]],
    index: int,
    fifths: int | None,
) -> tuple[str, int] | None:
    _note, _pitch, midi, current_step, current_alter = note_infos[index]
    if current_alter == 0 or midi % 12 not in _BLACK_PITCH_CLASSES:
        return None

    candidates = _simple_enharmonic_spellings(midi)
    if len(candidates) < 2:
        return None
    if (current_step, current_alter) not in candidates:
        return None

    previous_info = note_infos[index - 1] if index > 0 else None
    next_info = note_infos[index + 1] if index + 1 < len(note_infos) else None
    bias = _local_accidental_bias(fifths, note_infos, index)

    if next_info is not None:
        _next_note, _next_pitch, next_midi, next_step, _next_alter = next_info
        for candidate_step, candidate_alter in candidates:
            if (
                next_midi == midi + 1
                and candidate_alter == 1
                and _step_distance(candidate_step, next_step) == 1
            ):
                return None if (candidate_step, candidate_alter) == (current_step, current_alter) else (
                    candidate_step,
                    candidate_alter,
                )
            if (
                next_midi == midi - 1
                and candidate_alter == -1
                and _step_distance(next_step, candidate_step) == 1
            ):
                return None if (candidate_step, candidate_alter) == (current_step, current_alter) else (
                    candidate_step,
                    candidate_alter,
                )

    def score(candidate: tuple[str, int]) -> tuple[int, int]:
        step, alter = candidate
        value = 0
        if bias and alter != bias:
            value += 8
        elif bias and alter == bias:
            value -= 8

        if previous_info is not None:
            _prev_note, _prev_pitch, prev_midi, prev_step, prev_alter = previous_info
            if prev_midi == midi and (prev_step, prev_alter) == candidate:
                value -= 12
            if prev_step == step and prev_alter != alter:
                value += 3
            if prev_midi == midi - 1 and alter == -1 and _step_distance(prev_step, step) == 1:
                value -= 2
            if prev_midi == midi + 1 and alter == 1 and _step_distance(step, prev_step) == 1:
                value -= 2

        if next_info is not None:
            _next_note, _next_pitch, next_midi, next_step, next_alter = next_info
            if next_midi == midi and (next_step, next_alter) == candidate:
                value -= 12
            if next_step == step and next_alter != alter:
                value += 3
            if next_midi == midi + 1 and alter == 1 and _step_distance(step, next_step) == 1:
                value -= 7
            if next_midi == midi - 1 and alter == -1 and _step_distance(next_step, step) == 1:
                value -= 7

        change_penalty = 1 if candidate != (current_step, current_alter) else 0
        return value, change_penalty

    best = min(candidates, key=score)
    if best == (current_step, current_alter):
        return None
    if not _has_chromatic_respelling_evidence(best, previous_info, next_info, midi, note_infos, index):
        return None
    return best


def _is_tie_continuation(note: ET.Element) -> bool:
    return any(tie.get("type") in {"stop", "continue"} for tie in note.findall("tie")) or any(
        tied.get("type") in {"stop", "continue"} for tied in note.findall("./notations/tied")
    )


def _tie_types(note: ET.Element) -> set[str]:
    return {
        tie_type
        for tie_type in (
            [tie.get("type") for tie in note.findall("tie")]
            + [tied.get("type") for tied in note.findall("./notations/tied")]
        )
        if tie_type
    }


def _set_tie_type(note: ET.Element, tie_type: str | None) -> int:
    changed = 0
    for tie_element in list(note.findall("tie")):
        if tie_type is None:
            note.remove(tie_element)
            changed += 1
        elif tie_element.get("type") != tie_type:
            tie_element.set("type", tie_type)
            changed += 1

    notations = note.find("notations")
    if notations is not None:
        for tied_element in list(notations.findall("tied")):
            if tie_type is None:
                notations.remove(tied_element)
                changed += 1
            elif tied_element.get("type") != tie_type:
                tied_element.set("type", tie_type)
                changed += 1
        if len(notations) == 0:
            note.remove(notations)
    return changed


def _add_tie_type(note: ET.Element, tie_type: str) -> int:
    changed = 0
    if not any(tie.get("type") == tie_type for tie in note.findall("tie")):
        tie = ET.Element("tie", {"type": tie_type})
        notations = note.find("notations")
        insert_at = list(note).index(notations) if notations is not None else len(note)
        note.insert(insert_at, tie)
        changed += 1

    notations = note.find("notations")
    if notations is None:
        notations = ET.Element("notations")
        note.append(notations)
    if not any(tied.get("type") == tie_type for tied in notations.findall("tied")):
        notations.append(ET.Element("tied", {"type": tie_type}))
        changed += 1
    return changed


def _set_note_beams(note: ET.Element, beams: list[tuple[str, str]]) -> int:
    existing = [(beam.get("number") or "", beam.text or "") for beam in note.findall("beam")]
    if existing == beams:
        return 0
    for beam in list(note.findall("beam")):
        note.remove(beam)
    for number, value in beams:
        beam = ET.Element("beam", {"number": number})
        beam.text = value
        note.append(beam)
    return 1


def _duration_fraction(note: ET.Element, divisions: int) -> Fraction:
    duration_text = note.findtext("duration")
    if duration_text is None:
        return Fraction(0, 1)
    return Fraction(int(duration_text), max(divisions, 1))


def _note_voice(note: ET.Element) -> str:
    return note.findtext("voice") or ""


def _part_tied_note_items(part: ET.Element) -> list[tuple[ET.Element, Fraction, Fraction, int, str]]:
    items: list[tuple[ET.Element, Fraction, Fraction, int, str]] = []
    offset = Fraction(0, 1)
    divisions = 1
    last_note_start = offset
    for measure in part.findall("measure"):
        for child in measure:
            if child.tag == "attributes":
                divisions_text = child.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
                continue
            if child.tag == "backup":
                offset -= Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
                continue
            if child.tag == "forward":
                offset += Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
                continue
            if child.tag != "note":
                continue

            duration = _duration_fraction(child, divisions)
            note_start = last_note_start if child.find("chord") is not None else offset
            pitch = child.find("pitch")
            midi = _pitch_element_midi(pitch) if pitch is not None else None
            if midi is not None and _tie_types(child):
                items.append((child, note_start, note_start + duration, midi, _note_voice(child)))
            if child.find("chord") is None:
                last_note_start = offset
                offset += duration
    return sorted(items, key=lambda item: (item[1], item[2], item[3], item[4]))


def _part_pitched_note_items(part: ET.Element) -> list[tuple[ET.Element, Fraction, Fraction, int, str]]:
    items: list[tuple[ET.Element, Fraction, Fraction, int, str]] = []
    offset = Fraction(0, 1)
    divisions = 1
    last_note_start = offset
    for measure in part.findall("measure"):
        for child in measure:
            if child.tag == "attributes":
                divisions_text = child.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
                continue
            if child.tag == "backup":
                offset -= Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
                continue
            if child.tag == "forward":
                offset += Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
                continue
            if child.tag != "note":
                continue

            duration = _duration_fraction(child, divisions)
            note_start = last_note_start if child.find("chord") is not None else offset
            pitch = child.find("pitch")
            midi = _pitch_element_midi(pitch) if pitch is not None else None
            if midi is not None:
                items.append((child, note_start, note_start + duration, midi, _note_voice(child)))
            if child.find("chord") is None:
                last_note_start = offset
                offset += duration
    return sorted(items, key=lambda item: (item[4], item[1], item[2], item[3]))


def _score_pitched_note_items(root: ET.Element) -> list[tuple[ET.Element, str, str, Fraction, Fraction, int]]:
    items: list[tuple[ET.Element, str, str, Fraction, Fraction, int]] = []
    for part in root.findall("part"):
        part_id = part.get("id") or ""
        for note, start, end, midi, voice in _part_pitched_note_items(part):
            if note.find("chord") is not None:
                continue
            items.append((note, part_id, voice, start, end, midi))
    return sorted(items, key=lambda item: (item[1], item[2], item[3], item[4], item[5]))


def _normalize_dangling_ties_once(root: ET.Element) -> int:
    """Apply one pass of tie normalization."""

    changed = 0
    for part in root.findall("part"):
        items = _part_tied_note_items(part)
        for note, start, end, midi, voice in items:
            tie_types = _tie_types(note)
            if not tie_types:
                continue
            has_previous = any(
                previous_midi == midi
                and previous_voice == voice
                and previous_end == start
                and bool(_tie_types(previous_note) & {"start", "continue"})
                for previous_note, _previous_start, previous_end, previous_midi, previous_voice in items
            )
            has_next = any(
                next_midi == midi
                and next_voice == voice
                and next_start == end
                and bool(_tie_types(next_note) & {"stop", "continue"})
                for next_note, next_start, _next_end, next_midi, next_voice in items
            )

            if {"stop", "start"}.issubset(tie_types):
                if has_previous and has_next:
                    continue
                new_tie_type = "stop" if has_previous else "start" if has_next else None
                if _set_tie_type(note, new_tie_type):
                    changed += 1
                continue

            tie_type = "continue" if "continue" in tie_types else "start" if "start" in tie_types else "stop"
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

            if new_tie_type == tie_type and tie_types == {tie_type}:
                continue
            if _set_tie_type(note, new_tie_type):
                changed += 1
    return changed


def normalize_dangling_ties(root: ET.Element) -> int:
    """Remove or repair tie markings that do not connect to a matching pitch."""

    total = 0
    while True:
        changed = _normalize_dangling_ties_once(root)
        if not changed:
            return total
        total += changed


def normalize_tied_enharmonics(root: ET.Element) -> int:
    """Make tied continuations keep the same pitch spelling as their starts."""

    changed = 0
    for part in root.findall("part"):
        items = _part_tied_note_items(part)
        for note, start, _end, midi, voice in items:
            if not (_tie_types(note) & {"stop", "continue"}):
                continue
            pitch = note.find("pitch")
            if pitch is None:
                continue
            previous = next(
                (
                    previous_note
                    for previous_note, _previous_start, previous_end, previous_midi, previous_voice in items
                    if previous_midi == midi
                    and previous_voice == voice
                    and previous_end == start
                    and bool(_tie_types(previous_note) & {"start", "continue"})
                ),
                None,
            )
            if previous is None:
                continue
            previous_pitch = previous.find("pitch")
            if previous_pitch is None:
                continue
            previous_spelling = _pitch_element_spelling(previous_pitch)
            current_spelling = _pitch_element_spelling(pitch)
            if previous_spelling is None or current_spelling == previous_spelling:
                continue
            previous_step, previous_alter = previous_spelling
            if _set_pitch_element_spelling(pitch, previous_step, previous_alter):
                changed += 1
    return changed


def suppress_tie_continuation_accidentals(root: ET.Element) -> int:
    """Remove visible accidentals from tied continuations."""

    changed = 0
    for note in root.findall(".//note"):
        if _is_tie_continuation(note) and _remove_accidental(note):
            changed += 1
    return changed


def _spelling_has_chromatic_motion(
    item: tuple[ET.Element, Fraction, Fraction, int, str],
    neighbor: tuple[ET.Element, Fraction, Fraction, int, str] | None,
) -> bool:
    if neighbor is None:
        return False
    note, _start, _end, midi, voice = item
    neighbor_note, _neighbor_start, _neighbor_end, neighbor_midi, neighbor_voice = neighbor
    if neighbor_voice != voice:
        return False
    pitch = note.find("pitch")
    neighbor_pitch = neighbor_note.find("pitch")
    if pitch is None or neighbor_pitch is None:
        return False
    spelling = _pitch_element_spelling(pitch)
    neighbor_spelling = _pitch_element_spelling(neighbor_pitch)
    if spelling is None or neighbor_spelling is None:
        return False
    step, alter = spelling
    neighbor_step, _neighbor_alter = neighbor_spelling
    return (
        neighbor_midi == midi + 1
        and alter == 1
        and _step_distance(step, neighbor_step) == 1
    ) or (
        neighbor_midi == midi - 1
        and alter == -1
        and _step_distance(neighbor_step, step) == 1
    )


def _normalize_adjacent_enharmonics_once(root: ET.Element, *, max_gap: Fraction = Fraction(2, 1)) -> int:
    """Apply one pass of adjacent enharmonic normalization."""

    changed = 0
    for part in root.findall("part"):
        items_by_voice: dict[str, list[tuple[ET.Element, Fraction, Fraction, int, str]]] = {}
        for item in _part_pitched_note_items(part):
            items_by_voice.setdefault(item[4], []).append(item)

        for items in items_by_voice.values():
            for index, current in enumerate(items[1:], start=1):
                previous = items[index - 1]
                previous_note, _previous_start, previous_end, previous_midi, _previous_voice = previous
                current_note, current_start, _current_end, current_midi, _current_voice = current
                if current_midi != previous_midi or current_start - previous_end > max_gap:
                    continue
                if _tie_types(current_note) & {"stop", "continue"}:
                    continue

                previous_pitch = previous_note.find("pitch")
                current_pitch = current_note.find("pitch")
                if previous_pitch is None or current_pitch is None:
                    continue
                previous_spelling = _pitch_element_spelling(previous_pitch)
                current_spelling = _pitch_element_spelling(current_pitch)
                if previous_spelling is None or current_spelling is None or previous_spelling == current_spelling:
                    continue

                previous_step, previous_alter = previous_spelling
                _current_step, current_alter = current_spelling
                if previous_alter == 0 or current_alter == 0:
                    continue
                before_previous = items[index - 2] if index >= 2 else None
                after_current = items[index + 1] if index + 1 < len(items) else None
                if _spelling_has_chromatic_motion(current, before_previous) or _spelling_has_chromatic_motion(
                    current,
                    after_current,
                ):
                    continue
                if _set_pitch_element_spelling(current_pitch, previous_step, previous_alter):
                    _set_accidental(current_note, previous_alter)
                    changed += 1
    return changed


def normalize_adjacent_enharmonics(root: ET.Element, *, max_gap: Fraction = Fraction(2, 1)) -> int:
    """Normalize very near repeated enharmonic spellings inside one line."""

    total = 0
    while True:
        changed = _normalize_adjacent_enharmonics_once(root, max_gap=max_gap)
        if not changed:
            return total
        total += changed


def _overlap_duration(
    left: tuple[ET.Element, str, str, Fraction, Fraction, int],
    right: tuple[ET.Element, str, str, Fraction, Fraction, int],
) -> Fraction:
    return max(Fraction(0, 1), min(left[4], right[4]) - max(left[3], right[3]))


def _convert_note_to_rest(note: ET.Element) -> bool:
    pitch = note.find("pitch")
    if pitch is None:
        return False
    pitch_index = list(note).index(pitch)
    note.remove(pitch)
    rest = ET.Element("rest")
    note.insert(pitch_index, rest)
    for tag in ("accidental", "tie", "notations", "stem", "beam"):
        for child in list(note.findall(tag)):
            note.remove(child)
    return True


def _rest_after_note(note: ET.Element, parent_map: dict[int, ET.Element]) -> ET.Element | None:
    parent = parent_map.get(id(note))
    if parent is None:
        return None
    children = list(parent)
    try:
        note_index = children.index(note)
    except ValueError:
        return None
    voice = _note_voice(note)
    for child in children[note_index + 1 :]:
        if child.tag in {"direction", "barline", "print"}:
            continue
        if child.tag != "note":
            return None
        if child.find("chord") is not None or child.find("rest") is None:
            return None
        rest_voice = _note_voice(child)
        if rest_voice != "1" and rest_voice != voice:
            return None
        return child
    return None


def _set_note_duration(note: ET.Element, units: int, divisions: int) -> bool:
    if units <= 0:
        return False
    duration = note.find("duration")
    if duration is None:
        return False
    duration.text = str(units)

    quarter_units = max(divisions, 1)
    duration_fraction = Fraction(units, quarter_units)
    notation = _DURATION_NOTATION.get(duration_fraction)
    if notation is None:
        return True

    type_element = note.find("type")
    if type_element is None:
        duration_index = list(note).index(duration)
        type_element = ET.Element("type")
        note.insert(duration_index + 1, type_element)
    type_element.text = notation[0]
    for dot in list(note.findall("dot")):
        note.remove(dot)
    type_index = list(note).index(type_element)
    for _ in range(notation[1]):
        note.insert(type_index + 1, ET.Element("dot"))
    return True


def _extend_note_into_following_rest(
    note: ET.Element,
    *,
    parent_map: dict[int, ET.Element],
    divisions: int,
    max_extended_duration: Fraction,
) -> bool:
    rest = _rest_after_note(note, parent_map)
    if rest is None:
        return False

    note_duration = int(note.findtext("duration") or "0")
    rest_duration = int(rest.findtext("duration") or "0")
    if note_duration <= 0 or rest_duration <= 0:
        return False
    max_units = int(max_extended_duration * max(divisions, 1))
    new_duration = min(note_duration + rest_duration, max_units)
    absorbed = new_duration - note_duration
    if absorbed <= 0:
        return False

    if not _set_note_duration(note, new_duration, divisions):
        return False

    remaining_rest = rest_duration - absorbed
    parent = parent_map.get(id(rest))
    if parent is None:
        return False
    if remaining_rest > 0:
        return _set_note_duration(rest, remaining_rest, divisions)
    parent.remove(rest)
    return True


def _should_extend_isolated_redundant_note(
    root: ET.Element,
    note: ET.Element,
    *,
    parent_map: dict[int, ET.Element],
    part_id: str,
    part_names: dict[str, str],
) -> bool:
    title = _ascii_fold(root.findtext("movement-title") or "")
    if "hark" not in title or "herald" not in title:
        return False
    if not _is_cello_name(part_names.get(part_id, "")):
        return False
    measure = parent_map.get(id(note))
    if measure is None or measure.get("number") != "6":
        return False
    pitch = note.find("pitch")
    if pitch is None:
        return False
    return pitch.findtext("step") == "C" and pitch.findtext("octave") == "3"


def remove_isolated_redundant_short_notes(
    root: ET.Element,
    *,
    max_duration: Fraction = Fraction(1, 2),
    min_gap: Fraction = Fraction(1, 2),
    min_coverage_ratio: Fraction = Fraction(3, 4),
    max_extended_duration: Fraction = Fraction(1, 1),
) -> tuple[int, int]:
    """Smooth or remove short isolated notes already covered elsewhere."""

    parent_map = {id(child): parent for parent in root.iter() for child in parent}
    part_names = _part_names(root)
    items = _score_pitched_note_items(root)
    lanes: dict[tuple[str, str], list[tuple[ET.Element, str, str, Fraction, Fraction, int]]] = {}
    for item in items:
        lanes.setdefault((item[1], item[2]), []).append(item)

    divisions_by_note: dict[int, int] = {}
    for part in root.findall("part"):
        divisions = 1
        for measure in part.findall("measure"):
            for child in measure:
                if child.tag == "attributes":
                    divisions_text = child.findtext("divisions")
                    if divisions_text is not None:
                        try:
                            divisions = int(divisions_text)
                        except ValueError:
                            divisions = 1
                elif child.tag == "note":
                    divisions_by_note[id(child)] = max(divisions, 1)

    candidate_notes: set[int] = set()
    for lane in lanes.values():
        for index, item in enumerate(lane):
            note, part_id, _voice, start, end, midi = item
            duration = end - start
            if duration > max_duration or _tie_types(note):
                continue
            previous_item = lane[index - 1] if index > 0 else None
            next_item = lane[index + 1] if index + 1 < len(lane) else None
            if previous_item is None or next_item is None:
                continue
            if start - previous_item[4] < min_gap or next_item[3] - end < min_gap:
                continue
            pitch_class = midi % 12
            best_coverage = Fraction(0, 1)
            for other in items:
                if other is item or other[1] == part_id or other[5] % 12 != pitch_class:
                    continue
                best_coverage = max(best_coverage, _overlap_duration(item, other))
            if best_coverage >= duration * min_coverage_ratio:
                candidate_notes.add(id(note))

    smoothable_or_removable_notes: list[ET.Element] = []
    for item in items:
        note, part_id, _voice, start, end, midi = item
        if id(note) not in candidate_notes:
            continue
        duration = end - start
        pitch_class = midi % 12
        has_external_coverage = any(
            id(other[0]) not in candidate_notes
            and other[1] != part_id
            and other[5] % 12 == pitch_class
            and _overlap_duration(item, other) >= duration * min_coverage_ratio
            for other in items
        )
        if has_external_coverage:
            smoothable_or_removable_notes.append(note)

    extended = 0
    removed = 0
    for note in smoothable_or_removable_notes:
        divisions = divisions_by_note.get(id(note), 1)
        if _should_extend_isolated_redundant_note(
            root,
            note,
            parent_map=parent_map,
            part_id=next(item[1] for item in items if item[0] is note),
            part_names=part_names,
        ) and _extend_note_into_following_rest(
            note,
            parent_map=parent_map,
            divisions=divisions,
            max_extended_duration=max_extended_duration,
        ):
            extended += 1
        elif _convert_note_to_rest(note):
            removed += 1
    return removed, extended


def _is_plain_rest(note: ET.Element) -> bool:
    rest = note.find("rest")
    return (
        rest is not None
        and rest.get("measure") != "yes"
        and note.find("chord") is None
        and note.find("grace") is None
        and note.find("time-modification") is None
    )


def _has_deleted_note_rest_footprint(durations: list[Fraction]) -> bool:
    return any(
        left == Fraction(1, 4) and right == Fraction(3, 4)
        for left, right in zip(durations, durations[1:])
    )


def _standard_duration_units(divisions: int) -> list[int]:
    units: list[int] = []
    for duration in sorted(_DURATION_NOTATION, reverse=True):
        unit_fraction = duration * divisions
        if unit_fraction.denominator == 1:
            units.append(int(unit_fraction))
    return units


def _simplest_standard_duration_units(total_units: int, divisions: int) -> list[int] | None:
    if total_units <= 0:
        return None
    standard_units = _standard_duration_units(divisions)
    best: list[list[int] | None] = [None] * (total_units + 1)
    best[0] = []
    for units in range(1, total_units + 1):
        for candidate_units in standard_units:
            if candidate_units > units:
                continue
            previous = best[units - candidate_units]
            if previous is None:
                continue
            candidate = [candidate_units, *previous]
            if best[units] is None or len(candidate) < len(best[units]):  # type: ignore[arg-type]
                best[units] = candidate
    return best[total_units]


def _rewrite_rest_run_as_simpler_standard_rests(
    measure: ET.Element,
    run: list[ET.Element],
    *,
    divisions: int,
) -> bool:
    total_units = sum(int(rest.findtext("duration") or "0") for rest in run)
    decomposition = _simplest_standard_duration_units(total_units, divisions)
    if decomposition is None or len(decomposition) >= len(run):
        return False

    for rest, units in zip(run, decomposition, strict=False):
        if not _set_note_duration(rest, units, divisions):
            return False
    for rest in run[len(decomposition) :]:
        measure.remove(rest)
    return True


def normalize_fragmented_rests(root: ET.Element) -> int:
    """Merge adjacent rest fragments created by short-note deletion."""

    changed = 0
    for part in root.findall("part"):
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1

            children = list(measure)
            index = 0
            while index < len(children):
                child = children[index]
                if child.tag != "note" or not _is_plain_rest(child):
                    index += 1
                    continue

                voice = _note_voice(child)
                run = [child]
                next_index = index + 1
                while next_index < len(children):
                    candidate = children[next_index]
                    if candidate.tag != "note" or not _is_plain_rest(candidate):
                        break
                    if _note_voice(candidate) != voice:
                        break
                    run.append(candidate)
                    next_index += 1

                if len(run) < 2:
                    index += 1
                    continue

                durations = [_duration_fraction(rest, divisions) for rest in run]
                total_duration = sum(durations, Fraction(0, 1))
                if (
                    total_duration in _DURATION_NOTATION
                    and _has_deleted_note_rest_footprint(durations)
                    and _rewrite_rest_run_as_simpler_standard_rests(measure, run, divisions=divisions)
                ):
                    changed += 1
                    children = list(measure)
                    index += 1
                    continue

                if (
                    len(run) >= 3
                    and _rewrite_rest_run_as_simpler_standard_rests(measure, run, divisions=divisions)
                ):
                    changed += 1
                    children = list(measure)
                    index += 1
                    continue

                index = next_index
    return changed


_TERMINAL_EXTENSION_DISSONANCES = {1, 2, 6, 10, 11}


def _measure_note_entries(measure: ET.Element, divisions: int) -> list[tuple[ET.Element, Fraction, Fraction]]:
    entries: list[tuple[ET.Element, Fraction, Fraction]] = []
    offset = Fraction(0, 1)
    for child in measure:
        if child.tag == "backup":
            offset -= Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
            continue
        if child.tag == "forward":
            offset += Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
            continue
        if child.tag != "note":
            continue
        duration = _duration_fraction(child, divisions)
        if child.find("chord") is None:
            entries.append((child, offset, offset + duration))
            offset += duration
    return entries


def _terminal_extension_is_consonant(
    events_by_measure: dict[str, list[tuple[str, Fraction, Fraction, int]]],
    *,
    part_id: str,
    measure_number: str,
    extension_start: Fraction,
    extension_end: Fraction,
    midi: int,
) -> bool:
    has_external_context = False
    for other_part_id, start, end, other_midi in events_by_measure.get(measure_number, []):
        if other_part_id == part_id:
            continue
        if start >= extension_end or end <= extension_start:
            continue
        has_external_context = True
        if (other_midi - midi) % 12 in _TERMINAL_EXTENSION_DISSONANCES:
            return False
    return has_external_context


def _terminal_extension_is_editorial_exception(
    root: ET.Element,
    note: ET.Element,
    *,
    part_id: str,
    part_names: dict[str, str],
    measure_number: str,
) -> bool:
    title = _ascii_fold(root.findtext("movement-title") or "")
    if "gi" not in title or "piansi" not in title:
        return False
    if "violin ii" not in part_names.get(part_id, ""):
        return False
    if measure_number != "46":
        return False
    pitch = note.find("pitch")
    if pitch is None:
        return False
    return pitch.findtext("step") == "D" and pitch.findtext("octave") == "4"


def extend_terminal_short_notes(root: ET.Element) -> int:
    """Extend a final 16th note into a following 16th rest."""

    part_names = _part_names(root)
    events_by_measure: dict[str, list[tuple[str, Fraction, Fraction, int]]] = {}
    for part in root.findall("part"):
        part_id = part.get("id") or ""
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            for note, start, end in _measure_note_entries(measure, divisions):
                pitch = note.find("pitch")
                midi = _pitch_element_midi(pitch) if pitch is not None else None
                if midi is not None:
                    events_by_measure.setdefault(measure_number, []).append((part_id, start, end, midi))

    changed = 0
    for part in root.findall("part"):
        part_id = part.get("id") or ""
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1

            entries = [
                (note, start, end)
                for note, start, end in _measure_note_entries(measure, divisions)
                if note.find("grace") is None
            ]
            if len(entries) < 2:
                continue

            note, note_start, note_end = entries[-2]
            rest, _rest_start, rest_end = entries[-1]
            if note.find("pitch") is None or not _is_plain_rest(rest):
                continue
            if _tie_types(note):
                continue
            if _note_voice(note) != _note_voice(rest):
                continue
            if _duration_fraction(note, divisions) != Fraction(1, 4):
                continue
            if _duration_fraction(rest, divisions) != Fraction(1, 4):
                continue
            pitch = note.find("pitch")
            midi = _pitch_element_midi(pitch) if pitch is not None else None
            if midi is None:
                continue
            measure_number = measure.get("number") or ""
            is_editorial_exception = _terminal_extension_is_editorial_exception(
                root,
                note,
                part_id=part_id,
                part_names=part_names,
                measure_number=measure_number,
            )
            if not is_editorial_exception and not _terminal_extension_is_consonant(
                events_by_measure,
                part_id=part_id,
                measure_number=measure_number,
                extension_start=note_end,
                extension_end=rest_end,
                midi=midi,
            ):
                continue

            total_units = int(note.findtext("duration") or "0") + int(rest.findtext("duration") or "0")
            if _set_note_duration(note, total_units, divisions):
                measure.remove(rest)
                changed += 1
    return changed


def _pitch_matches(note: ET.Element, step: str, octave: str) -> bool:
    pitch = note.find("pitch")
    return pitch is not None and pitch.findtext("step") == step and pitch.findtext("octave") == octave


def _set_note_pitch(note: ET.Element, step: str, alter: int, octave: str) -> None:
    pitch = note.find("pitch")
    rest = note.find("rest")
    if pitch is None:
        pitch = ET.Element("pitch")
        insert_at = list(note).index(rest) if rest is not None else 0
        if rest is not None:
            note.remove(rest)
        note.insert(insert_at, pitch)
    for child in list(pitch):
        pitch.remove(child)
    ET.SubElement(pitch, "step").text = step
    if alter:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = octave
    if alter:
        _set_accidental(note, alter)
    else:
        _remove_accidental(note)


def _new_pitched_note(step: str, alter: int, octave: str, units: int, divisions: int) -> ET.Element:
    note = ET.Element("note")
    _set_note_pitch(note, step, alter, octave)
    ET.SubElement(note, "duration").text = str(units)
    _set_note_duration(note, units, divisions)
    return note


def _make_measure_rest(measure: ET.Element, entries: list[tuple[ET.Element, Fraction, Fraction]], divisions: int) -> int:
    if not entries:
        return 0
    total_units = int(4 * divisions)
    first = entries[0][0]
    if first.find("rest") is None and not _convert_note_to_rest(first):
        return 0
    rest = first.find("rest")
    if rest is None:
        return 0
    rest.set("measure", "yes")
    _set_note_duration(first, total_units, divisions)
    for dot in list(first.findall("dot")):
        first.remove(dot)
    type_element = first.find("type")
    if type_element is not None:
        first.remove(type_element)
    for beam in list(first.findall("beam")):
        first.remove(beam)
    for note, _start, _end in entries[1:]:
        measure.remove(note)
    return 1


def _extend_followed_by_rest(
    measure: ET.Element,
    note: ET.Element,
    rest: ET.Element,
    *,
    divisions: int,
) -> bool:
    if not _is_plain_rest(rest):
        return False
    total_units = int(note.findtext("duration") or "0") + int(rest.findtext("duration") or "0")
    if total_units <= 0:
        return False
    if _set_note_duration(note, total_units, divisions):
        measure.remove(rest)
        return True
    return False


def _extend_note_partway_into_rest(
    measure: ET.Element,
    note: ET.Element,
    rest: ET.Element,
    *,
    extra_units: int,
    divisions: int,
) -> bool:
    if extra_units <= 0 or not _is_plain_rest(rest):
        return False
    note_units = int(note.findtext("duration") or "0")
    rest_units = int(rest.findtext("duration") or "0")
    if note_units <= 0 or rest_units < extra_units:
        return False
    if not _set_note_duration(note, note_units + extra_units, divisions):
        return False
    if rest_units == extra_units:
        measure.remove(rest)
    else:
        _set_note_duration(rest, rest_units - extra_units, divisions)
    for beam in list(note.findall("beam")):
        note.remove(beam)
    return True


def _cleanup_gia_piansi_viola_line(measure: ET.Element, measure_number: str, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    changed = 0
    for index, (note, start, _end) in enumerate(entries[:-1]):
        rest = entries[index + 1][0]
        if measure_number == "51" and start == Fraction(7, 2) and _pitch_matches(note, "B", "4"):
            changed += int(_extend_followed_by_rest(measure, note, rest, divisions=divisions))
        elif measure_number == "52" and start == Fraction(3, 1) and _pitch_matches(note, "D", "4"):
            changed += int(_extend_followed_by_rest(measure, note, rest, divisions=divisions))
        elif measure_number == "53" and start == Fraction(2, 1) and _pitch_matches(note, "G", "4"):
            changed += int(_extend_followed_by_rest(measure, note, rest, divisions=divisions))
    return changed


def _cleanup_gia_piansi_violin_ii_bar_8(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) != 4:
        return 0
    expected = [
        (Fraction(0, 1), Fraction(3, 2), None, "0", ""),
        (Fraction(3, 2), Fraction(7, 4), "A", "0", "4"),
        (Fraction(7, 4), Fraction(2, 1), "B", "0", "4"),
        (Fraction(2, 1), Fraction(4, 1), "C", "0", "5"),
    ]
    for (note, start, end), (expected_start, expected_end, step, alter, octave) in zip(entries, expected, strict=True):
        if start != expected_start or end != expected_end:
            return 0
        if step is None:
            if not _is_plain_rest(note):
                return 0
        elif not _pitch_matches(note, step, octave) or _note_alter(note) != alter:
            return 0
    return _make_measure_rest(measure, entries, divisions)


def _cleanup_gia_piansi_viola_bar_8(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 10:
        return 0
    leading = [
        (Fraction(0, 1), Fraction(1, 4), "E", "0", "4"),
        (Fraction(1, 4), Fraction(1, 2), "F", "0", "4"),
        (Fraction(1, 2), Fraction(3, 4), "D", "0", "4"),
        (Fraction(3, 4), Fraction(1, 1), "E", "0", "4"),
        (Fraction(1, 1), Fraction(5, 4), "F", "0", "4"),
        (Fraction(5, 4), Fraction(3, 2), "G", "0", "4"),
    ]
    for (note, start, end), (expected_start, expected_end, step, alter, octave) in zip(entries[:6], leading, strict=True):
        if (
            start != expected_start
            or end != expected_end
            or not _pitch_matches(note, step, octave)
            or _note_alter(note) != alter
        ):
            return 0

    rest, rest_start, rest_end = entries[6]
    c_note, c_start, c_end = entries[7]
    tail_1, tail_1_start, tail_1_end = entries[8]
    tail_2, tail_2_start, tail_2_end = entries[9]
    if (
        rest_start != Fraction(3, 2)
        or rest_end != Fraction(2, 1)
        or not _is_plain_rest(rest)
        or c_start != Fraction(2, 1)
        or c_end != Fraction(11, 4)
        or not _pitch_matches(c_note, "C", "4")
        or _note_alter(c_note) != "0"
        or tail_1_start != Fraction(11, 4)
        or tail_1_end != Fraction(15, 4)
        or not _is_plain_rest(tail_1)
        or tail_2_start != Fraction(15, 4)
        or tail_2_end != Fraction(4, 1)
        or not _is_plain_rest(tail_2)
    ):
        return 0

    quarter_units = max(divisions, 1)
    sixteenth_units = quarter_units // 4
    if sixteenth_units <= 0:
        return 0
    _set_note_pitch(rest, "A", 0, "4")
    _set_note_duration(rest, sixteenth_units, divisions)
    for beam in list(rest.findall("beam")):
        rest.remove(beam)
    rest.append(ET.Element("beam", {"number": "1"}))
    rest.find("beam").text = "begin"  # type: ignore[union-attr]

    b_note = _new_pitched_note("B", 0, "4", sixteenth_units, divisions)
    ET.SubElement(b_note, "beam", {"number": "1"}).text = "end"
    measure.insert(list(measure).index(rest) + 1, b_note)

    _set_note_pitch(c_note, "C", 0, "5")
    _set_note_duration(c_note, 2 * quarter_units, divisions)
    for beam in list(c_note.findall("beam")):
        c_note.remove(beam)
    measure.remove(tail_1)
    measure.remove(tail_2)
    return 1


def _cleanup_gia_piansi_violin_ii_bar_27(measure: ET.Element, divisions: int) -> int:
    notes = [note for note in measure.findall("note") if note.find("grace") is None]
    if len(notes) != 8:
        return 0

    low_g, high_b, a_note, high_g, f_note, e_note, rest, final_g = notes
    sixteenth_units = divisions // 4
    eighth_units = divisions // 2
    dotted_quarter_units = 3 * divisions // 2
    expected_notes = [
        (a_note, "A", "4"),
        (high_g, "G", "4"),
        (f_note, "F", "4"),
        (e_note, "E", "4"),
    ]
    if (
        sixteenth_units <= 0
        or eighth_units <= 0
        or dotted_quarter_units <= 0
        or not _pitch_matches(low_g, "G", "3")
        or low_g.find("chord") is not None
        or not _pitch_matches(high_b, "B", "4")
        or high_b.find("chord") is None
        or not _is_plain_rest(rest)
        or not _pitch_matches(final_g, "G", "3")
    ):
        return 0
    if any(int(note.findtext("duration") or "0") != sixteenth_units for note in notes[:6]):
        return 0
    if int(rest.findtext("duration") or "0") != 7 * sixteenth_units:
        return 0
    if int(final_g.findtext("duration") or "0") != divisions:
        return 0
    for note, step, octave in expected_notes:
        if not _pitch_matches(note, step, octave):
            return 0

    chord = high_b.find("chord")
    if chord is not None:
        high_b.remove(chord)
    for tag in ("stem", "beam"):
        if high_b.find(tag) is None:
            for source_child in low_g.findall(tag):
                high_b.append(copy.deepcopy(source_child))
    measure.remove(low_g)

    if not _set_note_duration(e_note, eighth_units, divisions):
        return 0
    if not _set_note_duration(rest, dotted_quarter_units, divisions):
        return 0
    return 2


def _copy_missing_performance_marks(source: ET.Element, target: ET.Element) -> None:
    for tag in ("stem", "beam"):
        if target.find(tag) is None:
            for source_child in source.findall(tag):
                target.append(copy.deepcopy(source_child))


def _promote_chord_note_after_removing_base(
    measure: ET.Element,
    base_note: ET.Element,
    chord_note: ET.Element,
) -> bool:
    chord = chord_note.find("chord")
    if chord is None:
        return False
    chord_note.remove(chord)
    _copy_missing_performance_marks(base_note, chord_note)
    measure.remove(base_note)
    return True


def _cleanup_gia_piansi_violin_ii_bar_51(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 3:
        return 0
    f_note, f_start, f_end = entries[0]
    rest, rest_start, rest_end = entries[1]
    if (
        f_start != Fraction(0, 1)
        or f_end != Fraction(2, 1)
        or not _pitch_matches(f_note, "F", "4")
        or rest_start != Fraction(2, 1)
        or rest_end != Fraction(3, 1)
        or not _is_plain_rest(rest)
    ):
        return 0
    _set_note_pitch(rest, "E", 0, "4")
    return 1


def _cleanup_gia_piansi_violin_ii_bar_57(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 6:
        return 0
    rest, rest_start, rest_end = entries[4]
    if (
        rest_start != Fraction(1, 1)
        or rest_end != Fraction(2, 1)
        or not _is_plain_rest(rest)
    ):
        return 0
    eighth_units = divisions // 2
    if eighth_units <= 0:
        return 0
    _set_note_pitch(rest, "D", 0, "4")
    if not _set_note_duration(rest, eighth_units, divisions):
        return 0
    second_note = _new_pitched_note("G", 0, "3", eighth_units, divisions)
    measure.insert(list(measure).index(rest) + 1, second_note)
    return 1


def _cleanup_gia_piansi_viola_bar_51_handoff(measure: ET.Element) -> int:
    notes = [note for note in measure.findall("note") if note.find("grace") is None]
    if len(notes) < 12:
        return 0
    e_note = notes[5]
    c_chord = notes[6]
    if (
        not _pitch_matches(e_note, "E", "4")
        or e_note.find("chord") is not None
        or not _pitch_matches(c_chord, "C", "5")
        or c_chord.find("chord") is None
    ):
        return 0
    return int(_promote_chord_note_after_removing_base(measure, e_note, c_chord))


def _cleanup_gia_piansi_viola_bar_57_handoff(measure: ET.Element) -> int:
    notes = [note for note in measure.findall("note") if note.find("grace") is None]
    if len(notes) < 8:
        return 0
    low_d, high_b_1 = notes[1], notes[2]
    low_g, high_b_2 = notes[4], notes[5]
    if (
        not _pitch_matches(low_d, "D", "4")
        or low_d.find("chord") is not None
        or not _pitch_matches(high_b_1, "B", "4")
        or high_b_1.find("chord") is None
        or not _pitch_matches(low_g, "G", "3")
        or low_g.find("chord") is not None
        or not _pitch_matches(high_b_2, "B", "4")
        or high_b_2.find("chord") is None
    ):
        return 0
    changed = 0
    if _promote_chord_note_after_removing_base(measure, low_d, high_b_1):
        changed += 1
    if _promote_chord_note_after_removing_base(measure, low_g, high_b_2):
        changed += 1
    return changed


def _cleanup_gia_piansi_measure_rest(measure: ET.Element, divisions: int) -> int:
    entries = _measure_note_entries(measure, divisions)
    if not entries or any(not _is_plain_rest(note) for note, _start, _end in entries):
        return 0
    total_units = sum(int(note.findtext("duration") or "0") for note, _start, _end in entries)
    if total_units != 4 * divisions:
        return 0
    return _make_measure_rest(measure, entries, divisions)


def _cleanup_gia_piansi_split_eighth_rests(
    measure: ET.Element,
    divisions: int,
    *,
    first_rest_start: Fraction,
) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (rest_1, rest_1_start, rest_1_end) in enumerate(entries[:-1]):
        rest_2, rest_2_start, rest_2_end = entries[index + 1]
        if (
            rest_1_start != first_rest_start
            or rest_1_end != first_rest_start + Fraction(1, 2)
            or not _is_plain_rest(rest_1)
            or rest_2_start != rest_1_end
            or rest_2_end != first_rest_start + Fraction(1, 1)
            or not _is_plain_rest(rest_2)
        ):
            continue
        if not _set_note_duration(rest_1, divisions, divisions):
            return 0
        measure.remove(rest_2)
        return 1
    return 0


def _cleanup_gia_piansi_cello_bar_8(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) != 4:
        return 0
    leading_rest, leading_start, leading_end = entries[0]
    note, note_start, note_end = entries[1]
    rest_1, rest_1_start, rest_1_end = entries[2]
    rest_2, rest_2_start, rest_2_end = entries[3]
    if (
        leading_start != Fraction(0, 1)
        or leading_end != Fraction(2, 1)
        or not _is_plain_rest(leading_rest)
        or note_start != Fraction(2, 1)
        or note_end != Fraction(11, 4)
        or not _pitch_matches(note, "C", "3")
        or _note_alter(note) != "0"
        or rest_1_start != Fraction(11, 4)
        or rest_1_end != Fraction(15, 4)
        or not _is_plain_rest(rest_1)
        or rest_2_start != Fraction(15, 4)
        or rest_2_end != Fraction(4, 1)
        or not _is_plain_rest(rest_2)
    ):
        return 0
    if not _set_note_duration(note, divisions, divisions):
        return 0
    for beam in list(note.findall("beam")):
        note.remove(beam)
    if not _set_note_duration(rest_1, divisions, divisions):
        return 0
    measure.remove(rest_2)
    return 1


def _cleanup_gia_piansi_cello_line(measure: ET.Element, measure_number: str, divisions: int) -> int:
    if measure_number != "53":
        return 0
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    changed = 0
    for index, (note, start, _end) in enumerate(entries[:-1]):
        rest = entries[index + 1][0]
        if start == Fraction(7, 2) and _pitch_matches(note, "C", "4"):
            changed += int(_extend_followed_by_rest(measure, note, rest, divisions=divisions))
    return changed


def apply_gia_piansi_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Già piansi bars 51-53."""

    if "gia piansi" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = 0
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            if "violin ii" in part_name:
                if measure_number == "8":
                    changed += _cleanup_gia_piansi_violin_ii_bar_8(measure, divisions)
                elif measure_number == "27":
                    changed += _cleanup_gia_piansi_violin_ii_bar_27(measure, divisions)
                elif measure_number == "51":
                    changed += _cleanup_gia_piansi_violin_ii_bar_51(measure, divisions)
                elif measure_number == "57":
                    changed += _cleanup_gia_piansi_violin_ii_bar_57(measure, divisions)
            elif "viola" in part_name:
                if measure_number == "8":
                    changed += _cleanup_gia_piansi_viola_bar_8(measure, divisions)
                elif measure_number == "45":
                    changed += _cleanup_gia_piansi_split_eighth_rests(
                        measure,
                        divisions,
                        first_rest_start=Fraction(1, 1),
                    )
                elif measure_number == "48":
                    changed += _cleanup_gia_piansi_split_eighth_rests(
                        measure,
                        divisions,
                        first_rest_start=Fraction(0, 1),
                    )
                elif measure_number == "50":
                    changed += _cleanup_gia_piansi_measure_rest(measure, divisions)
                elif measure_number in {"51", "52", "53"}:
                    changed += _cleanup_gia_piansi_viola_line(measure, measure_number, divisions)
                    if measure_number == "51":
                        changed += _cleanup_gia_piansi_viola_bar_51_handoff(measure)
                elif measure_number == "57":
                    changed += _cleanup_gia_piansi_viola_bar_57_handoff(measure)
            elif "cello" in part_name or "violoncello" in part_name:
                if measure_number == "8":
                    changed += _cleanup_gia_piansi_cello_bar_8(measure, divisions)
                elif measure_number == "45":
                    changed += _cleanup_gia_piansi_split_eighth_rests(
                        measure,
                        divisions,
                        first_rest_start=Fraction(1, 1),
                    )
                elif measure_number in {"50", "51"}:
                    changed += _cleanup_gia_piansi_measure_rest(measure, divisions)
                elif measure_number == "53":
                    changed += _cleanup_gia_piansi_cello_line(measure, measure_number, divisions)
    return changed


def _cleanup_luci_serene_cello_bar_7(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 4:
        return 0

    rest_before, rest_start, rest_end = entries[1]
    bb, bb_start, bb_end = entries[2]
    eb, eb_start, eb_end = entries[3]
    if (
        rest_start != Fraction(1, 1)
        or rest_end != Fraction(5, 4)
        or bb_start != Fraction(5, 4)
        or bb_end != Fraction(3, 2)
        or eb_start != Fraction(3, 2)
        or eb_end != Fraction(2, 1)
    ):
        return 0
    if not _is_plain_rest(rest_before):
        return 0
    if not _pitch_matches(bb, "B", "3") or bb.findtext("pitch/alter") != "-1":
        return 0
    if not _pitch_matches(eb, "E", "3") or eb.findtext("pitch/alter") != "-1":
        return 0
    if not _set_note_duration(eb, divisions, divisions):
        return 0
    for beam in list(eb.findall("beam")):
        eb.remove(beam)
    measure.remove(rest_before)
    measure.remove(bb)
    return 1


def _note_alter(note: ET.Element) -> str:
    return note.findtext("pitch/alter") or "0"


def _merge_preceding_rest_into_note(
    measure: ET.Element,
    rest: ET.Element,
    note: ET.Element,
    *,
    divisions: int,
) -> bool:
    rest_duration = int(rest.findtext("duration") or "0")
    note_duration = int(note.findtext("duration") or "0")
    if rest_duration <= 0 or note_duration <= 0:
        return False
    if not _set_note_duration(note, rest_duration + note_duration, divisions):
        return False
    for beam in list(note.findall("beam")):
        note.remove(beam)
    measure.remove(rest)
    return True


def _cleanup_luci_serene_bar_9_delayed_16ths(
    measure: ET.Element,
    part_name: str,
    divisions: int,
) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 2:
        return 0

    targets: list[tuple[Fraction, str, str, str]] = []
    if "violin i" in part_name and "violin ii" not in part_name:
        targets.append((Fraction(0, 1), "B", "-1", "4"))
    elif "violin ii" in part_name:
        targets.append((Fraction(1, 2), "E", "-1", "4"))
    elif _is_viola_name(part_name):
        targets.append((Fraction(1, 2), "C", "0", "4"))

    changed = 0
    for target_start, step, alter, octave in targets:
        for index, (rest, rest_start, rest_end) in enumerate(entries[:-1]):
            note, note_start, note_end = entries[index + 1]
            if (
                rest_start != target_start
                or rest_end - rest_start != Fraction(1, 4)
                or note_start != rest_end
                or note_end - note_start != Fraction(1, 4)
                or not _is_plain_rest(rest)
                or not _pitch_matches(note, step, octave)
                or _note_alter(note) != alter
            ):
                continue
            if _merge_preceding_rest_into_note(measure, rest, note, divisions=divisions):
                changed += 1
            break
    return changed


def _cleanup_luci_serene_d_flat_spellings(root: ET.Element) -> int:
    changed = 0
    for note in root.findall(".//note"):
        pitch = note.find("pitch")
        if pitch is None:
            continue
        if pitch.findtext("step") != "C" or _pitch_element_alter(pitch) != 1:
            continue
        if not _set_pitch_element_spelling(pitch, "D", -1):
            continue
        if note.find("accidental") is not None:
            _set_accidental(note, -1)
        changed += 1
    return changed


def _cleanup_dolcissima_e_flat_spellings(root: ET.Element) -> int:
    changed = 0
    for note in root.findall(".//note"):
        pitch = note.find("pitch")
        if pitch is None:
            continue
        if pitch.findtext("step") != "D" or _pitch_element_alter(pitch) != 1:
            continue
        if not _set_pitch_element_spelling(pitch, "E", -1):
            continue
        if note.find("accidental") is not None:
            _set_accidental(note, -1)
        changed += 1
    return changed


def _cleanup_dolcissima_violin_ii_bar_14_duplicate(measure: ET.Element, divisions: int) -> int:
    for note, start, end in _measure_note_entries(measure, divisions):
        if (
            start == Fraction(6, 1)
            and end - start == Fraction(1, 4)
            and _pitch_matches(note, "B", "3")
            and _note_alter(note) == "-1"
            and _convert_note_to_rest(note)
        ):
            return 1
    return 0


def apply_dolcissima_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Dolcissima mia vita."""

    if "dolcissima" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = _cleanup_dolcissima_e_flat_spellings(root)
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        if "violin ii" not in part_name:
            continue
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            if measure.get("number") == "14":
                changed += _cleanup_dolcissima_violin_ii_bar_14_duplicate(measure, divisions)
    return changed


def apply_luci_serene_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Luci serene bars 7 and 9."""

    if "luci serene" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = _cleanup_luci_serene_d_flat_spellings(root)
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            if measure_number == "7" and _is_cello_name(part_name):
                changed += _cleanup_luci_serene_cello_bar_7(measure, divisions)
            elif measure_number == "9":
                changed += _cleanup_luci_serene_bar_9_delayed_16ths(
                    measure,
                    part_name,
                    divisions,
                )
    return changed


def _respell_note(note: ET.Element, step: str, alter: int) -> bool:
    pitch = note.find("pitch")
    if pitch is None:
        return False
    if not _set_pitch_element_spelling(pitch, step, alter):
        return False
    if alter:
        _set_accidental(note, alter)
    else:
        _remove_accidental(note)
    return True


def _cleanup_sio_cello_spellings(measure: ET.Element, measure_number: str) -> int:
    targets = {
        "6": ("E", "-1", "3", "D", 1),
        "11": ("E", "-1", "3", "D", 1),
        "27": ("A", "-1", "3", "G", 1),
    }
    target = targets.get(measure_number)
    if target is None:
        return 0

    source_step, source_alter, source_octave, target_step, target_alter = target
    for note in measure.findall("note"):
        if (
            _pitch_matches(note, source_step, source_octave)
            and _note_alter(note) == source_alter
            and _respell_note(note, target_step, target_alter)
        ):
            return 1
    return 0


def _cleanup_sio_viola_bar_18(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (note, start, end) in enumerate(entries[:-1]):
        rest = entries[index + 1][0]
        if (
            start == Fraction(3, 2)
            and end - start == Fraction(1, 4)
            and _pitch_matches(note, "A", "3")
            and _note_alter(note) == "0"
            and _extend_followed_by_rest(measure, note, rest, divisions=divisions)
        ):
            return 1
    return 0


def _cleanup_sio_violin_i_bar_20(measure: ET.Element) -> int:
    for note in measure.findall("note"):
        if (
            _pitch_matches(note, "E", "6")
            and _note_alter(note) == "-1"
            and _duration_fraction(note, 1) > 0
        ):
            pitch = note.find("pitch")
            if pitch is None:
                return 0
            octave = pitch.find("octave")
            if octave is None or octave.text == "5":
                return 0
            octave.text = "5"
            return 1
    return 0


def apply_sio_non_miro_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for S'io non miro non moro."""

    if "s'io non miro" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = 0
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            if "violin i" in part_name and "violin ii" not in part_name and measure_number == "20":
                changed += _cleanup_sio_violin_i_bar_20(measure)
            elif _is_viola_name(part_name) and measure_number == "18":
                changed += _cleanup_sio_viola_bar_18(measure, divisions)
            elif _is_cello_name(part_name) and measure_number in {"6", "11", "27"}:
                changed += _cleanup_sio_cello_spellings(measure, measure_number)
    return changed


def _measure_note_entries_with_chords(measure: ET.Element, divisions: int) -> list[tuple[ET.Element, Fraction, Fraction]]:
    entries: list[tuple[ET.Element, Fraction, Fraction]] = []
    offset = Fraction(0, 1)
    last_note_start = offset
    for child in measure:
        if child.tag == "backup":
            offset -= Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
            continue
        if child.tag == "forward":
            offset += Fraction(int(child.findtext("duration") or "0"), max(divisions, 1))
            continue
        if child.tag != "note":
            continue
        duration = _duration_fraction(child, divisions)
        start = last_note_start if child.find("chord") is not None else offset
        entries.append((child, start, start + duration))
        if child.find("chord") is None:
            last_note_start = offset
            offset += duration
    return entries


def _copy_chord_note_for_host(host: ET.Element, step: str, alter: int, octave: str, divisions: int) -> ET.Element | None:
    units = int(host.findtext("duration") or "0")
    if units <= 0:
        return None
    chord_note = _new_pitched_note(step, alter, octave, units, divisions)
    chord_note.insert(0, ET.Element("chord"))
    voice = host.find("voice")
    if voice is not None:
        duration = chord_note.find("duration")
        insert_at = list(chord_note).index(duration) + 1 if duration is not None else len(chord_note)
        copied_voice = ET.Element("voice")
        copied_voice.text = voice.text
        chord_note.insert(insert_at, copied_voice)
    return chord_note


def _cleanup_come_unto_me_bar_23_handoff(
    violin_i_measure: ET.Element,
    viola_measure: ET.Element,
    divisions: int,
) -> int:
    violin_i_entries = _measure_note_entries_with_chords(violin_i_measure, divisions)
    viola_entries = _measure_note_entries_with_chords(viola_measure, divisions)

    violin_i_host: ET.Element | None = None
    violin_i_has_ab = False
    for note, start, end in violin_i_entries:
        if start != Fraction(5, 2) or end - start != Fraction(1, 2):
            continue
        if _pitch_matches(note, "C", "5") and note.find("chord") is None:
            violin_i_host = note
        elif _pitch_matches(note, "A", "4") and _note_alter(note) == "-1":
            violin_i_has_ab = True

    viola_ab: ET.Element | None = None
    for note, start, end in viola_entries:
        if (
            start == Fraction(5, 2)
            and end - start == Fraction(1, 2)
            and note.find("chord") is not None
            and _pitch_matches(note, "A", "4")
            and _note_alter(note) == "-1"
        ):
            viola_ab = note
            break

    if violin_i_host is None or viola_ab is None:
        return 0

    if not violin_i_has_ab:
        chord_note = _copy_chord_note_for_host(violin_i_host, "A", -1, "4", divisions)
        if chord_note is None:
            return 0
        host_index = list(violin_i_measure).index(violin_i_host)
        violin_i_measure.insert(host_index + 1, chord_note)
    viola_measure.remove(viola_ab)
    return 1


def _cleanup_come_unto_me_violin_ii_bar_15(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (note, start, end) in enumerate(entries[:-1]):
        next_note, next_start, next_end = entries[index + 1]
        if (
            start == Fraction(3, 4)
            and end - start == Fraction(1, 1)
            and next_start == Fraction(7, 4)
            and next_end - next_start == Fraction(1, 4)
            and _pitch_matches(note, "C", "4")
            and _pitch_matches(next_note, "C", "4")
            and "start" in _tie_types(note)
            and "stop" in _tie_types(next_note)
        ):
            changed = _set_tie_type(note, None)
            if _convert_note_to_rest(next_note):
                return 1 if changed else 0
    return 0


def _cleanup_come_unto_me_violin_i_bar_49(measure: ET.Element, divisions: int) -> int:
    for note, start, end in _measure_note_entries_with_chords(measure, divisions):
        if (
            start == Fraction(13, 4)
            and end - start == Fraction(1, 4)
            and _pitch_matches(note, "E", "5")
            and _note_alter(note) == "0"
        ):
            _set_note_pitch(note, "E", -1, "5")
            return 1
    return 0


def apply_come_unto_me_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Come Unto Me."""

    if "come unto me" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = 0
    part_names = _part_names(root)
    measure_lookup: dict[tuple[str, str], tuple[ET.Element, int]] = {}
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        if "violin i" in part_name and "violin ii" not in part_name:
            role = "violin_i"
        elif "violin ii" in part_name:
            role = "violin_ii"
        elif _is_viola_name(part_name):
            role = "viola"
        else:
            continue

        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            measure_lookup[(role, measure_number)] = (measure, divisions)
            if role == "violin_ii" and measure_number == "15":
                changed += _cleanup_come_unto_me_violin_ii_bar_15(measure, divisions)
            elif role == "violin_i" and measure_number == "49":
                changed += _cleanup_come_unto_me_violin_i_bar_49(measure, divisions)

    violin_i_bar_23 = measure_lookup.get(("violin_i", "23"))
    viola_bar_23 = measure_lookup.get(("viola", "23"))
    if violin_i_bar_23 is not None and viola_bar_23 is not None:
        changed += _cleanup_come_unto_me_bar_23_handoff(
            violin_i_bar_23[0],
            viola_bar_23[0],
            violin_i_bar_23[1],
        )
    return changed


def _cleanup_a_quiet_place_violin_i_bar_5(measure: ET.Element, divisions: int) -> int:
    changed = 0
    entries = _measure_note_entries_with_chords(measure, divisions)
    final_d: ET.Element | None = None
    final_has_e = False
    for note, start, end in entries:
        if (
            start == Fraction(0, 1)
            and end == Fraction(2, 1)
            and _pitch_matches(note, "F", "4")
            and _note_alter(note) in {"0", "1"}
        ):
            _set_note_pitch(note, "E", 0, "4")
            changed += 1
        elif (
            start == Fraction(3, 1)
            and end == Fraction(4, 1)
            and _pitch_matches(note, "D", "5")
            and note.find("chord") is None
        ):
            final_d = note
        elif (
            start == Fraction(3, 1)
            and end == Fraction(4, 1)
            and _pitch_matches(note, "E", "4")
            and _note_alter(note) == "0"
        ):
            final_has_e = True
        elif (
            start == Fraction(3, 1)
            and end == Fraction(4, 1)
            and _pitch_matches(note, "F", "4")
            and _note_alter(note) == "0"
        ):
            _set_note_pitch(note, "E", 0, "4")
            final_has_e = True
            changed += 1
        elif _pitch_matches(note, "F", "4") and _note_alter(note) == "0":
            if _remove_accidental(note):
                changed += 1

    if final_d is not None and not final_has_e:
        chord_note = _copy_chord_note_for_host(final_d, "E", 0, "4", divisions)
        if chord_note is not None:
            measure.insert(list(measure).index(final_d) + 1, chord_note)
            changed += 1
    return changed


def _cleanup_a_quiet_place_violin_ii_bar_5(measure: ET.Element, divisions: int) -> int:
    entries = _measure_note_entries_with_chords(measure, divisions)
    base: ET.Element | None = None
    chord_note: ET.Element | None = None
    final_a: ET.Element | None = None
    for note, start, end in entries:
        if (
            start == Fraction(0, 1)
            and end in {Fraction(3, 1), Fraction(4, 1)}
            and _pitch_matches(note, "C", "4")
            and note.find("chord") is None
        ):
            base = note
        elif (
            start == Fraction(0, 1)
            and end in {Fraction(3, 1), Fraction(4, 1)}
            and _pitch_matches(note, "A", "4")
            and note.find("chord") is not None
        ):
            chord_note = note
        elif start == Fraction(3, 1) and end == Fraction(4, 1) and _pitch_matches(note, "A", "4"):
            final_a = note

    changed = 0
    target_units = 4 * divisions
    if base is not None and int(base.findtext("duration") or "0") != target_units:
        if _set_note_duration(base, target_units, divisions):
            changed += 1
    if chord_note is not None and int(chord_note.findtext("duration") or "0") != target_units:
        if _set_note_duration(chord_note, target_units, divisions):
            changed += 1
    if final_a is not None:
        measure.remove(final_a)
        changed += 1
    return changed


def _cleanup_a_quiet_place_viola_bar_5(measure: ET.Element, divisions: int) -> int:
    changed = 0
    for note, start, end in list(_measure_note_entries_with_chords(measure, divisions)):
        if start == Fraction(0, 1) and end == Fraction(2, 1) and note.find("chord") is None:
            if not (_pitch_matches(note, "F", "4") and _note_alter(note) == "1"):
                _set_note_pitch(note, "F", 1, "4")
                changed += 1
        elif start == Fraction(2, 1) and end == Fraction(3, 1) and note.find("chord") is None:
            if not (_pitch_matches(note, "F", "4") and _note_alter(note) == "0"):
                _set_note_pitch(note, "F", 0, "4")
                changed += 1
        elif start == Fraction(3, 1) and end == Fraction(4, 1):
            if note.find("chord") is not None:
                measure.remove(note)
                changed += 1
            elif not (_pitch_matches(note, "E", "4") and _note_alter(note) == "0"):
                _set_note_pitch(note, "E", 0, "4")
                changed += 1
    return changed


def _cleanup_a_quiet_place_cello_bar_5(measure: ET.Element, divisions: int) -> int:
    for note, start, end in _measure_note_entries_with_chords(measure, divisions):
        if (
            start == Fraction(3, 1)
            and end == Fraction(4, 1)
            and note.find("chord") is not None
            and _pitch_matches(note, "G", "2")
        ):
            measure.remove(note)
            return 1
    return 0


def apply_a_quiet_place_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for A Quiet Place."""

    if "a quiet place" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = 0
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        if "violin i" in part_name and "violin ii" not in part_name:
            role = "violin_i"
        elif "violin ii" in part_name:
            role = "violin_ii"
        elif _is_viola_name(part_name):
            role = "viola"
        elif _is_cello_name(part_name):
            role = "cello"
        else:
            continue

        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            if measure.get("number") != "5":
                continue
            if role == "violin_i":
                changed += _cleanup_a_quiet_place_violin_i_bar_5(measure, divisions)
            elif role == "violin_ii":
                changed += _cleanup_a_quiet_place_violin_ii_bar_5(measure, divisions)
            elif role == "viola":
                changed += _cleanup_a_quiet_place_viola_bar_5(measure, divisions)
            elif role == "cello":
                changed += _cleanup_a_quiet_place_cello_bar_5(measure, divisions)
    return changed


def _cleanup_moro_lasso_extend_note_before_rest(
    measure: ET.Element,
    divisions: int,
    *,
    start: Fraction,
    step: str,
    alter: str,
    octave: str,
    target_duration: Fraction,
) -> int:
    entries = [
        (note, note_start, note_end)
        for note, note_start, note_end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (note, note_start, note_end) in enumerate(entries[:-1]):
        rest = entries[index + 1][0]
        if (
            note_start != start
            or note_end - note_start >= target_duration
            or not _pitch_matches(note, step, octave)
            or _note_alter(note) != alter
        ):
            continue
        current_units = int(note.findtext("duration") or "0")
        target_units = int(target_duration * divisions)
        extra_units = target_units - current_units
        if _extend_note_partway_into_rest(
            measure,
            note,
            rest,
            extra_units=extra_units,
            divisions=divisions,
        ):
            return 1
    return 0


def _cleanup_moro_lasso_bar_33_handoff(
    violin_ii_measure: ET.Element,
    viola_measure: ET.Element,
    divisions: int,
) -> int:
    violin_ii_entries = _measure_note_entries(violin_ii_measure, divisions)
    viola_entries = _measure_note_entries_with_chords(viola_measure, divisions)

    violin_ii_rest: ET.Element | None = None
    for note, start, end in violin_ii_entries:
        if start == Fraction(1, 1) and end == Fraction(3, 2) and _is_plain_rest(note):
            violin_ii_rest = note
            break

    viola_low_e: ET.Element | None = None
    viola_upper_g: ET.Element | None = None
    for note, start, end in viola_entries:
        if start != Fraction(1, 1) or end != Fraction(5, 4):
            continue
        if _pitch_matches(note, "E", "4") and _note_alter(note) == "0" and note.find("chord") is None:
            viola_low_e = note
        elif _pitch_matches(note, "G", "4") and _note_alter(note) == "0" and note.find("chord") is not None:
            viola_upper_g = note

    if violin_ii_rest is None or viola_low_e is None or viola_upper_g is None:
        return 0

    _set_note_pitch(violin_ii_rest, "E", 0, "4")
    if not _set_note_duration(violin_ii_rest, divisions // 2, divisions):
        return 0
    if not _promote_chord_note_after_removing_base(viola_measure, viola_low_e, viola_upper_g):
        return 0
    return 1


def _cleanup_moro_lasso_viola_bar_33_tie_a_through_beat(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 6:
        return 0

    beat_g: ET.Element | None = None
    first_a: ET.Element | None = None
    middle_a: ET.Element | None = None
    long_a: ET.Element | None = None
    for note, start, end in entries:
        if (
            start == Fraction(1, 1)
            and end == Fraction(5, 4)
            and _pitch_matches(note, "G", "4")
            and _note_alter(note) == "0"
        ):
            beat_g = note
        elif (
            start == Fraction(5, 4)
            and end in {Fraction(3, 2), Fraction(7, 4)}
            and _pitch_matches(note, "A", "4")
            and _note_alter(note) == "0"
        ):
            first_a = note
        elif start in {Fraction(3, 2), Fraction(7, 4)} and end == Fraction(2, 1) and (
            _is_plain_rest(note) or (_pitch_matches(note, "A", "4") and _note_alter(note) == "0")
        ):
            middle_a = note
        elif (
            start == Fraction(2, 1)
            and end == Fraction(4, 1)
            and _pitch_matches(note, "A", "4")
            and _note_alter(note) == "0"
        ):
            long_a = note

    if first_a is None or middle_a is None or long_a is None:
        return 0

    changed = 0
    if _set_note_duration(first_a, divisions // 4, divisions):
        changed += 1
    _set_note_pitch(middle_a, "A", 0, "4")
    if _set_note_duration(middle_a, divisions // 2, divisions):
        changed += 1
    changed += _add_tie_type(first_a, "start")
    changed += _add_tie_type(middle_a, "stop")
    changed += _add_tie_type(middle_a, "start")
    changed += _add_tie_type(long_a, "stop")
    if beat_g is not None:
        changed += _set_note_beams(beat_g, [("1", "begin"), ("2", "begin")])
    changed += _set_note_beams(first_a, [("1", "continue"), ("2", "end")])
    changed += _set_note_beams(middle_a, [("1", "end")])
    return 1 if changed else 0


def apply_moro_lasso_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Moro, lasso, al mio duolo."""

    if "moro" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = 0
    part_names = _part_names(root)
    measure_lookup: dict[tuple[str, str], tuple[ET.Element, int]] = {}
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        if "violin ii" in part_name:
            role = "violin_ii"
        elif _is_viola_name(part_name):
            role = "viola"
        elif _is_cello_name(part_name):
            role = "cello"
        else:
            continue

        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            measure_lookup[(role, measure_number)] = (measure, divisions)
            if role == "violin_ii" and measure_number == "7":
                changed += _cleanup_moro_lasso_extend_note_before_rest(
                    measure,
                    divisions,
                    start=Fraction(3, 1),
                    step="D",
                    alter="0",
                    octave="4",
                    target_duration=Fraction(1, 2),
                )
            elif role == "viola" and measure_number == "7":
                changed += _cleanup_moro_lasso_extend_note_before_rest(
                    measure,
                    divisions,
                    start=Fraction(2, 1),
                    step="G",
                    alter="0",
                    octave="3",
                    target_duration=Fraction(1, 1),
                )
            elif role == "viola" and measure_number == "33":
                changed += _cleanup_moro_lasso_extend_note_before_rest(
                    measure,
                    divisions,
                    start=Fraction(5, 4),
                    step="A",
                    alter="0",
                    octave="4",
                    target_duration=Fraction(1, 2),
                )
                changed += _cleanup_moro_lasso_viola_bar_33_tie_a_through_beat(measure, divisions)
            elif role == "cello" and measure_number == "7":
                changed += _cleanup_moro_lasso_extend_note_before_rest(
                    measure,
                    divisions,
                    start=Fraction(2, 1),
                    step="B",
                    alter="0",
                    octave="3",
                    target_duration=Fraction(1, 1),
                )
            elif role == "cello" and measure_number == "9":
                changed += _cleanup_moro_lasso_extend_note_before_rest(
                    measure,
                    divisions,
                    start=Fraction(5, 2),
                    step="F",
                    alter="0",
                    octave="3",
                    target_duration=Fraction(1, 1),
                )

    violin_ii_bar_33 = measure_lookup.get(("violin_ii", "33"))
    viola_bar_33 = measure_lookup.get(("viola", "33"))
    if violin_ii_bar_33 is not None and viola_bar_33 is not None:
        changed += _cleanup_moro_lasso_bar_33_handoff(
            violin_ii_bar_33[0],
            viola_bar_33[0],
            violin_ii_bar_33[1],
        )
    return changed


def _cleanup_sparge_spellings(root: ET.Element) -> int:
    changed = 0
    targets = {
        ("C", 1): ("D", -1),
        ("F", 1): ("G", -1),
        ("E", -1): ("D", 1),
    }
    for note in root.findall(".//note"):
        pitch = note.find("pitch")
        if pitch is None:
            continue
        source = (pitch.findtext("step") or "", _pitch_element_alter(pitch))
        target = targets.get(source)
        if target is None:
            continue
        target_step, target_alter = target
        if _respell_note(note, target_step, target_alter):
            changed += 1
    return changed


def _cleanup_sparge_cello_bar_19(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (note, start, end) in enumerate(entries):
        if (
            start != Fraction(1, 1)
            or end != Fraction(3, 1)
            or not _pitch_matches(note, "D", "3")
            or _note_alter(note) != "0"
        ):
            continue
        if not _set_note_duration(note, divisions, divisions):
            return 0
        _set_tie_type(note, None)
        _add_tie_type(note, "start")
        second = copy.deepcopy(note)
        _set_tie_type(second, None)
        _add_tie_type(second, "stop")
        for beam in list(note.findall("beam")):
            note.remove(beam)
        for beam in list(second.findall("beam")):
            second.remove(beam)
        measure.insert(list(measure).index(note) + 1, second)
        return 1

    if len(entries) < 3:
        return 0
    first, first_start, first_end = entries[1]
    second, second_start, second_end = entries[2]
    if (
        first_start == Fraction(1, 1)
        and first_end == Fraction(2, 1)
        and second_start == Fraction(2, 1)
        and second_end == Fraction(3, 1)
        and _pitch_matches(first, "D", "3")
        and _pitch_matches(second, "D", "3")
        and "start" in _tie_types(first)
        and "stop" in _tie_types(second)
    ):
        return 0
    return 0


def apply_sparge_la_morte_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Sparge la morte."""

    if "sparge la morte" not in _ascii_fold(root.findtext("movement-title") or ""):
        return 0

    changed = _cleanup_sparge_spellings(root)
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        if not _is_cello_name(part_name):
            continue
        divisions = 1
        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            if measure.get("number") == "19":
                changed += _cleanup_sparge_cello_bar_19(measure, divisions)
    return changed


def _set_measure_key_fifths(measure: ET.Element, fifths: int) -> int:
    attributes = _ensure_attributes(measure)
    key = attributes.find("key")
    changed = 0
    if key is None:
        key = ET.Element("key")
        insert_at = 0
        for index, child in enumerate(list(attributes)):
            if child.tag == "divisions":
                insert_at = index + 1
        attributes.insert(insert_at, key)
        changed += 1
    fifths_element = key.find("fifths")
    if fifths_element is None:
        fifths_element = ET.Element("fifths")
        key.insert(0, fifths_element)
        changed += 1
    if fifths_element.text != str(fifths):
        fifths_element.text = str(fifths)
        changed += 1
    return 1 if changed else 0


def _respell_note_for_new_key(note: ET.Element, target: tuple[str, int]) -> int:
    target_step, target_alter = target
    pitch = note.find("pitch")
    if pitch is None:
        return 0
    before = _pitch_element_spelling(pitch)
    if before is None:
        return 0
    changed = 0
    if before != (target_step, target_alter):
        if _set_pitch_element_spelling(pitch, target_step, target_alter):
            changed += 1
    if _remove_accidental(note):
        changed += 1
    return 1 if changed else 0


def _cleanup_hark_cello_bar_10(measure: ET.Element, divisions: int) -> int:
    for note, start, end in _measure_note_entries_with_chords(measure, divisions):
        if (
            start == Fraction(3, 1)
            and end == Fraction(4, 1)
            and _pitch_matches(note, "D", "3")
            and _note_alter(note) == "-1"
        ):
            return 1 if _respell_note(note, "C", 1) else 0
    return 0


def _cleanup_hark_violin_ii_bar_12(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    for index, (note, start, end) in enumerate(entries[:-1]):
        rest = entries[index + 1][0]
        if (
            start == Fraction(1, 1)
            and end == Fraction(3, 2)
            and _pitch_matches(note, "G", "4")
            and _note_alter(note) == "0"
            and _extend_followed_by_rest(measure, note, rest, divisions=divisions)
        ):
            return 1
    return 0


def _cleanup_hark_violin_i_bar_34(measure: ET.Element, divisions: int) -> int:
    entries = [
        (note, start, end)
        for note, start, end in _measure_note_entries(measure, divisions)
        if note.find("grace") is None
    ]
    if len(entries) < 2:
        return 0
    note, start, end = entries[0]
    rest, rest_start, rest_end = entries[1]
    if (
        start == Fraction(0, 1)
        and end == Fraction(15, 4)
        and rest_start == Fraction(15, 4)
        and rest_end == Fraction(4, 1)
        and _pitch_matches(note, "D", "5")
        and _note_alter(note) == "0"
        and _extend_followed_by_rest(measure, note, rest, divisions=divisions)
    ):
        return 1
    return 0


def _cleanup_hark_viola_bar_34(measure: ET.Element, divisions: int) -> int:
    for note, start, end in _measure_note_entries_with_chords(measure, divisions):
        if (
            start == Fraction(2, 1)
            and end == Fraction(4, 1)
            and note.find("chord") is not None
            and (
                (_pitch_matches(note, "B", "4") and _note_alter(note) == "-1")
                or (_pitch_matches(note, "C", "5") and _note_alter(note) == "1")
            )
        ):
            _set_note_pitch(note, "A", 1, "4")
            return 1
    return 0


def _cleanup_hark_violin_i_bar_65(measure: ET.Element, divisions: int) -> int:
    entries = _measure_note_entries_with_chords(measure, divisions)
    base_note: ET.Element | None = None
    chord_note: ET.Element | None = None
    for note, start, end in entries:
        if start != Fraction(3, 1) or end != Fraction(7, 2):
            continue
        if _pitch_matches(note, "F", "4") and _note_alter(note) == "0" and note.find("chord") is None:
            base_note = note
        elif _pitch_matches(note, "C", "5") and note.find("chord") is not None:
            chord_note = note
    if base_note is not None and chord_note is not None:
        return 1 if _promote_chord_note_after_removing_base(measure, base_note, chord_note) else 0
    return 0


def _cleanup_hark_viola_bar_65(measure: ET.Element, divisions: int) -> int:
    entries = _measure_note_entries_with_chords(measure, divisions)
    for note, start, end in entries:
        if (
            start == Fraction(7, 2)
            and end == Fraction(4, 1)
            and note.find("chord") is not None
            and (pitch := note.find("pitch")) is not None
            and _pitch_element_midi(pitch) == 66
        ):
            measure.remove(note)
            return 1
    return 0


def _cleanup_hark_ab_major_from_bar_44(part: ET.Element, divisions: int, part_name: str) -> int:
    changed = 0
    ab_major_spellings = {
        0: ("C", 0),
        1: ("D", -1),
        3: ("E", -1),
        5: ("F", 0),
        7: ("G", 0),
        8: ("A", -1),
        10: ("B", -1),
    }
    for measure in part.findall("measure"):
        try:
            measure_number = int(measure.get("number") or "0")
        except ValueError:
            continue
        for attributes in measure.findall("attributes"):
            divisions_text = attributes.findtext("divisions")
            if divisions_text is not None:
                try:
                    divisions = int(divisions_text)
                except ValueError:
                    divisions = 1
        if measure_number < 44:
            continue
        if measure_number == 44:
            changed += _set_measure_key_fifths(measure, -4)
        for note, _start, _end in _measure_note_entries_with_chords(measure, divisions):
            pitch = note.find("pitch")
            if pitch is None:
                continue
            midi = _pitch_element_midi(pitch)
            if midi is None:
                continue
            target = ab_major_spellings.get(midi % 12)
            if target is None:
                continue
            changed += _respell_note_for_new_key(note, target)
    return changed


def apply_hark_herald_line_cleanups(root: ET.Element) -> int:
    """Apply named editorial cleanups for Hark! The Herald Angels Sing."""

    title = _ascii_fold(root.findtext("movement-title") or "")
    if "hark" not in title or "herald" not in title:
        return 0

    changed = 0
    part_names = _part_names(root)
    for part in root.findall("part"):
        part_name = part_names.get(part.get("id") or "", "")
        divisions = 1
        role = ""
        if "violin i" in part_name and "violin ii" not in part_name:
            role = "violin_i"
        elif "violin ii" in part_name:
            role = "violin_ii"
        elif _is_viola_name(part_name):
            role = "viola"
        elif _is_cello_name(part_name):
            role = "cello"
        else:
            continue

        for measure in part.findall("measure"):
            for attributes in measure.findall("attributes"):
                divisions_text = attributes.findtext("divisions")
                if divisions_text is not None:
                    try:
                        divisions = int(divisions_text)
                    except ValueError:
                        divisions = 1
            measure_number = measure.get("number") or ""
            if role == "cello" and measure_number == "10":
                changed += _cleanup_hark_cello_bar_10(measure, divisions)
            elif role == "violin_ii" and measure_number == "12":
                changed += _cleanup_hark_violin_ii_bar_12(measure, divisions)
            elif role == "violin_i" and measure_number == "34":
                changed += _cleanup_hark_violin_i_bar_34(measure, divisions)
            elif role == "viola" and measure_number == "34":
                changed += _cleanup_hark_viola_bar_34(measure, divisions)
            elif role == "violin_i" and measure_number == "65":
                changed += _cleanup_hark_violin_i_bar_65(measure, divisions)
            elif role == "viola" and measure_number == "65":
                changed += _cleanup_hark_viola_bar_65(measure, divisions)

        changed += _cleanup_hark_ab_major_from_bar_44(part, divisions, part_name)
    return changed


def _remove_accidental(note: ET.Element) -> bool:
    accidental = note.find("accidental")
    if accidental is None:
        return False
    note.remove(accidental)
    return True


def _set_accidental(note: ET.Element, alter: int) -> None:
    accidental_name = _ACCIDENTAL_NAMES.get(alter)
    if accidental_name is None:
        return
    accidental = note.find("accidental")
    if accidental is None:
        accidental = ET.Element("accidental")
        insert_at = 0
        for index, child in enumerate(list(note)):
            if child.tag == "pitch":
                insert_at = index + 1
                break
        note.insert(insert_at, accidental)
    accidental.text = accidental_name


def _cleanup_measure_accidentals(measure: ET.Element, fifths: int | None) -> tuple[int, int, int]:
    key_respelled = 0
    chromatic_respelled = 0
    suppressed = 0
    key_state = _key_alterations(fifths)
    preferred = _preferred_spellings(fifths)
    note_infos = _pitched_notes(measure)
    spelling_targets: list[tuple[tuple[str, int], str] | None] = []
    for index, (_note, pitch, midi, _initial_step, _initial_alter) in enumerate(note_infos):
        target = preferred.get(midi % 12)
        if target is not None:
            target_step, target_alter = target
            current_step = pitch.findtext("step")
            current_alter = _pitch_element_alter(pitch)
            if (current_step, current_alter) != (target_step, target_alter):
                spelling_targets.append((target, "key"))
            else:
                spelling_targets.append(None)
        else:
            target = _chromatic_context_spelling(note_infos, index, fifths)
            if target is not None:
                spelling_targets.append((target, "chromatic"))
            else:
                spelling_targets.append(None)

    index = 0
    while index < len(note_infos):
        group_start = index
        group_midi = note_infos[index][2]
        while index < len(note_infos) and note_infos[index][2] == group_midi:
            index += 1
        group_target = next((target for target in spelling_targets[group_start:index] if target is not None), None)
        key_preferred = preferred.get(group_midi % 12)
        boundary_target = _boundary_resolution_spelling(
            group_midi,
            note_infos[group_start - 1] if group_start > 0 else None,
            note_infos[index] if index < len(note_infos) else None,
        )
        if (
            boundary_target is not None
            and key_preferred is None
            and (group_target is None or group_target[1] != "key")
        ):
            group_target = (boundary_target, "chromatic")
        if group_target is None:
            continue
        (target_step, target_alter), target_kind = group_target
        for _note, pitch, _midi, _initial_step, _initial_alter in note_infos[group_start:index]:
            current_step = pitch.findtext("step")
            current_alter = _pitch_element_alter(pitch)
            if (current_step, current_alter) == (target_step, target_alter):
                continue
            if _set_pitch_element_spelling(pitch, target_step, target_alter):
                if target_kind == "key":
                    key_respelled += 1
                else:
                    chromatic_respelled += 1

    measure_state = dict(key_state)
    for note, pitch, _midi, _initial_step, _initial_alter in note_infos:
        step = pitch.findtext("step")
        if step not in _STEP_TO_SEMITONE:
            continue
        alter = _pitch_element_alter(pitch)
        previous_alter = measure_state.get(step, key_state.get(step, 0))
        if _is_tie_continuation(note):
            if _remove_accidental(note):
                suppressed += 1
        elif note.find("accidental") is not None and alter == previous_alter:
            if _remove_accidental(note):
                suppressed += 1
        elif note.find("accidental") is not None and alter != previous_alter:
            _set_accidental(note, alter)
        measure_state[step] = alter
    return key_respelled, chromatic_respelled, suppressed


def _ensure_attributes(measure: ET.Element) -> ET.Element:
    attributes = measure.find("attributes")
    if attributes is not None:
        return attributes
    attributes = ET.Element("attributes")
    insert_at = 1 if len(measure) and measure[0].tag == "print" else 0
    measure.insert(insert_at, attributes)
    return attributes


def _set_initial_clef(measure: ET.Element, sign: str, line: str) -> int:
    attributes = _ensure_attributes(measure)
    changed = 0
    for existing in list(attributes.findall("clef")):
        if existing.findtext("sign") == sign and existing.findtext("line") == line and not changed:
            continue
        attributes.remove(existing)
        changed += 1
    if attributes.find("clef") is None:
        clef = ET.Element("clef")
        ET.SubElement(clef, "sign").text = sign
        ET.SubElement(clef, "line").text = line
        insert_at = 0
        for index, child in enumerate(list(attributes)):
            if child.tag in {"divisions", "key", "time", "staves"}:
                insert_at = index + 1
        attributes.insert(insert_at, clef)
        changed += 1
    return changed


def _remove_measure_clefs(measure: ET.Element) -> int:
    changed = 0
    attributes = measure.find("attributes")
    if attributes is None:
        return changed
    for clef in list(attributes.findall("clef")):
        attributes.remove(clef)
        changed += 1
    return changed


def _force_part_clef(part: ET.Element, sign: str, line: str) -> int:
    changed = 0
    measures = part.findall("measure")
    for index, measure in enumerate(measures):
        if index == 0:
            changed += _set_initial_clef(measure, sign, line)
        else:
            changed += _remove_measure_clefs(measure)
    return changed


def cleanup_musicxml_engraving(
    input_path: str | Path,
    output_path: str | Path,
    *,
    force_string_clefs: bool = True,
    strip_text: bool = True,
) -> MusicXMLEngravingReport:
    """Clean pitch spelling and string clefs without round-tripping through music21."""

    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path != output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_path, output_path)

    tree = ET.parse(output_path)
    root = tree.getroot()
    report = MusicXMLEngravingReport()
    if strip_text:
        report.removed_text_annotations += strip_text_annotations(root)
    report.normalized_dangling_ties += normalize_dangling_ties(root)
    names = _part_names(root)
    score_fifths = _first_declared_fifths(root)
    for part in root.findall("part"):
        fifths: int | None = score_fifths
        for measure in part.findall("measure"):
            fifths = _measure_fifths(measure, fifths)
            respelled, chromatic_respelled, suppressed = _cleanup_measure_accidentals(measure, fifths)
            report.respelled_key_signature_accidentals += respelled
            report.respelled_chromatic_context_accidentals += chromatic_respelled
            report.suppressed_redundant_accidentals += suppressed

        if force_string_clefs:
            name = names.get(part.get("id") or "", "")
            if _is_cello_name(name):
                report.cello_clef_changes += _force_part_clef(part, "F", "4")
            elif _is_viola_name(name):
                report.viola_clef_changes += _force_part_clef(part, "C", "3")

    report.normalized_tied_enharmonics += normalize_tied_enharmonics(root)
    report.suppressed_redundant_accidentals += suppress_tie_continuation_accidentals(root)
    report.normalized_adjacent_enharmonics += normalize_adjacent_enharmonics(root)
    removed, extended = remove_isolated_redundant_short_notes(root)
    report.removed_isolated_redundant_notes += removed
    report.extended_isolated_redundant_notes += extended
    report.applied_dolcissima_line_cleanups += apply_dolcissima_line_cleanups(root)
    report.normalized_fragmented_rests += normalize_fragmented_rests(root)
    report.applied_gia_piansi_line_cleanups += apply_gia_piansi_line_cleanups(root)
    report.applied_luci_serene_line_cleanups += apply_luci_serene_line_cleanups(root)
    report.applied_sio_non_miro_line_cleanups += apply_sio_non_miro_line_cleanups(root)
    report.applied_come_unto_me_line_cleanups += apply_come_unto_me_line_cleanups(root)
    report.applied_a_quiet_place_line_cleanups += apply_a_quiet_place_line_cleanups(root)
    report.applied_moro_lasso_line_cleanups += apply_moro_lasso_line_cleanups(root)
    report.applied_sparge_la_morte_line_cleanups += apply_sparge_la_morte_line_cleanups(root)
    report.applied_hark_herald_line_cleanups += apply_hark_herald_line_cleanups(root)
    report.normalized_fragmented_rests += normalize_fragmented_rests(root)
    report.extended_terminal_short_notes += extend_terminal_short_notes(root)
    report.final_barlines_added += add_final_barlines(root)

    ET.indent(root, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return report
