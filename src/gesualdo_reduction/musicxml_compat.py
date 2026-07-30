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


def _cleanup_measure_accidentals(measure: ET.Element, fifths: int | None) -> tuple[int, int]:
    respelled = 0
    suppressed = 0
    key_state = _key_alterations(fifths)
    measure_state = dict(key_state)
    preferred = _preferred_spellings(fifths)
    for note in measure.findall("note"):
        pitch = note.find("pitch")
        if pitch is None:
            continue
        midi = _pitch_element_midi(pitch)
        if midi is None:
            continue
        target = preferred.get(midi % 12)
        if target is not None:
            target_step, target_alter = target
            current_step = pitch.findtext("step")
            current_alter = _pitch_element_alter(pitch)
            if (current_step, current_alter) != (target_step, target_alter):
                if _set_pitch_element_spelling(pitch, target_step, target_alter):
                    respelled += 1

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
    return respelled, suppressed


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
            respelled, suppressed = _cleanup_measure_accidentals(measure, fifths)
            report.respelled_key_signature_accidentals += respelled
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
