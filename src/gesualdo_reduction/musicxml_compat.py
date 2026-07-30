"""Small MusicXML compatibility post-processors."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
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


def _pitch_element_midi(pitch: ET.Element) -> int | None:
    step = pitch.findtext("step")
    octave = pitch.findtext("octave")
    if step not in _STEP_TO_SEMITONE or octave is None:
        return None
    alter = int(float(pitch.findtext("alter") or "0"))
    return (int(octave) + 1) * 12 + _STEP_TO_SEMITONE[step] + alter


def _pitch_element_alter(pitch: ET.Element) -> int:
    return int(float(pitch.findtext("alter") or "0"))


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
        boundary_target = _boundary_resolution_spelling(
            group_midi,
            note_infos[group_start - 1] if group_start > 0 else None,
            note_infos[index] if index < len(note_infos) else None,
        )
        if boundary_target is not None:
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
    names = _part_names(root)
    for part in root.findall("part"):
        fifths: int | None = None
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

    ET.indent(root, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return report
