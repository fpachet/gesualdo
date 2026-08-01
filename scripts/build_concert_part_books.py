"""Build concert-order individual part books for the quartet programme."""

from __future__ import annotations

import copy
import importlib.util
import io
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_MUSICXML_COMPAT_SPEC = importlib.util.spec_from_file_location(
    "gesualdo_reduction_musicxml_compat",
    ROOT / "src" / "gesualdo_reduction" / "musicxml_compat.py",
)
if _MUSICXML_COMPAT_SPEC is None or _MUSICXML_COMPAT_SPEC.loader is None:
    raise ImportError("Could not load MusicXML compatibility module")
_musicxml_compat = importlib.util.module_from_spec(_MUSICXML_COMPAT_SPEC)
sys.modules[_MUSICXML_COMPAT_SPEC.name] = _musicxml_compat
_MUSICXML_COMPAT_SPEC.loader.exec_module(_musicxml_compat)
cleanup_musicxml_engraving = _musicxml_compat.cleanup_musicxml_engraving

OUTPUT_XML_DIR = ROOT / "output" / "parts" / "musicxml"
OUTPUT_PDF_DIR = ROOT / "output" / "pdf" / "quartet_director" / "parts"
PIECE_PDF_DIR = OUTPUT_PDF_DIR / "pieces"

MUSESCORE_CANDIDATES = (
    Path("/Applications/MuseScore 4.app/Contents/MacOS/mscore"),
    Path("/Applications/MuseScore 4 2.app/Contents/MacOS/mscore"),
)

INSTRUMENTS = (
    ("Violin I", "violin_i"),
    ("Violin II", "violin_ii"),
    ("Viola", "viola"),
    ("Violoncello", "cello"),
)


@dataclass(frozen=True)
class ProgramPartSource:
    number: int
    title: str
    composer: str
    musicxml_path: Path


PROGRAM: tuple[ProgramPartSource, ...] = (
    ProgramPartSource(1, "Our Prayer", "The Beach Boys", ROOT / "data/beach boys/reductions/string_quartet/our_prayer_low_cello.musicxml"),
    ProgramPartSource(2, "Luci serene e chiare", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/109_luci_serene_e_chiare.musicxml"),
    ProgramPartSource(3, "Dolcissima mia vita", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/092_dolcissima_mia_vita.musicxml"),
    ProgramPartSource(4, "Già piansi nel dolore", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/100_gi_piansi_nel_dolore.musicxml"),
    ProgramPartSource(5, "S'io non miro non moro", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/147_s_io_non_miro_non_moro.musicxml"),
    ProgramPartSource(6, "Come Unto Me", "Take 6", ROOT / "data/take6/reductions/string_quartet_double_stops/come_unto_me.musicxml"),
    ProgramPartSource(7, "Moro, lasso, al mio duolo", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/121_moro_lasso_al_mio_duolo.musicxml"),
    ProgramPartSource(8, "Sparge la morte", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/161_sparge_la_morte.musicxml"),
    ProgramPartSource(9, "Beltà, poi che t'assenti", "Carlo Gesualdo", ROOT / "data/cpdl/5-voices/reductions/string_quartet/074_belt_poi_che_t_assenti.musicxml"),
    ProgramPartSource(10, "Tristis est anima mea", "Carlo Gesualdo", ROOT / "data/cpdl/6-voices/reductions/string_quartet/051_tristis_est_anima_mea.musicxml"),
    ProgramPartSource(11, "Hark! The Herald Angels Sing", "Take 6", ROOT / "data/take6/reductions/string_quartet_double_stops/hark_herald.musicxml"),
    ProgramPartSource(12, "A Quiet Place", "Take 6", ROOT / "data/take6/reductions/string_quartet_double_stops/a_quiet_place.musicxml"),
)


def default_musescore_path() -> Path:
    for candidate in MUSESCORE_CANDIDATES:
        if candidate.exists():
            return candidate
    return MUSESCORE_CANDIDATES[0]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return slug.strip("_")


def _find_part_id(root: ET.Element, instrument_name: str) -> str:
    part_list = root.find("part-list")
    if part_list is None:
        raise ValueError("MusicXML has no part-list")
    for score_part in part_list.findall("score-part"):
        part_name = (score_part.findtext("part-name") or "").strip()
        if part_name == instrument_name:
            part_id = score_part.get("id")
            if not part_id:
                raise ValueError(f"Part {instrument_name!r} has no id")
            return part_id
    names = [(sp.findtext("part-name") or "").strip() for sp in part_list.findall("score-part")]
    raise ValueError(f"Could not find {instrument_name!r}; available parts: {names}")


def _strip_text_directions(root: ET.Element) -> None:
    for parent in root.iter():
        for note in list(parent):
            if note.tag != "note":
                continue
            for lyric in list(note.findall("lyric")):
                note.remove(lyric)

    for direction in root.findall(".//direction"):
        for direction_type in list(direction.findall("direction-type")):
            for words in list(direction_type.findall("words")):
                direction_type.remove(words)
            if len(direction_type) == 0:
                direction.remove(direction_type)

    for parent in root.iter():
        for child in list(parent):
            if child.tag == "direction" and len(child) == 0:
                parent.remove(child)


def _is_tempo_direction(direction: ET.Element) -> bool:
    if (sound := direction.find("sound")) is not None and sound.get("tempo"):
        return True
    return direction.find("./direction-type/metronome") is not None


def _tempo_key(direction: ET.Element) -> tuple[str, str, str]:
    sound_tempo = ""
    if (sound := direction.find("sound")) is not None:
        sound_tempo = sound.get("tempo") or ""
    metronome = direction.find("./direction-type/metronome")
    if metronome is None:
        return sound_tempo, "", ""
    return sound_tempo, metronome.findtext("beat-unit") or "", metronome.findtext("per-minute") or ""


def _duration_value(element: ET.Element) -> int:
    return int(element.findtext("duration") or "0")


def _collect_tempo_directions(root: ET.Element) -> dict[str, list[tuple[int, ET.Element]]]:
    tempos_by_measure: dict[str, list[tuple[int, ET.Element]]] = {}
    seen: set[tuple[str, int, tuple[str, str, str]]] = set()
    for part in root.findall("part"):
        for measure in part.findall("measure"):
            measure_number = measure.get("number") or ""
            offset = 0
            for child in measure:
                if child.tag == "direction" and _is_tempo_direction(child):
                    key = (measure_number, offset, _tempo_key(child))
                    if key in seen:
                        continue
                    seen.add(key)
                    tempos_by_measure.setdefault(measure_number, []).append((offset, copy.deepcopy(child)))
                elif child.tag == "note" and child.find("chord") is None:
                    offset += _duration_value(child)
                elif child.tag == "backup":
                    offset -= _duration_value(child)
                elif child.tag == "forward":
                    offset += _duration_value(child)
                if offset < 0:
                    offset = 0
    return tempos_by_measure


def _tempo_offsets(measure: ET.Element) -> set[tuple[int, tuple[str, str, str]]]:
    offsets: set[tuple[int, tuple[str, str, str]]] = set()
    offset = 0
    for child in measure:
        if child.tag == "direction" and _is_tempo_direction(child):
            offsets.add((offset, _tempo_key(child)))
        elif child.tag == "note" and child.find("chord") is None:
            offset += _duration_value(child)
        elif child.tag == "backup":
            offset -= _duration_value(child)
        elif child.tag == "forward":
            offset += _duration_value(child)
        if offset < 0:
            offset = 0
    return offsets


def _insert_at_offset(measure: ET.Element, offset: int, element: ET.Element) -> None:
    current = 0
    insert_at = len(measure)
    for index, child in enumerate(list(measure)):
        if child.tag in {"print", "attributes"}:
            continue
        if current >= offset:
            insert_at = index
            break
        if child.tag == "note" and child.find("chord") is None:
            current += _duration_value(child)
        elif child.tag == "backup":
            current -= _duration_value(child)
        elif child.tag == "forward":
            current += _duration_value(child)
        if current < 0:
            current = 0
    measure.insert(insert_at, element)


def _copy_tempo_directions(source_root: ET.Element, part_root: ET.Element) -> None:
    tempos_by_measure = _collect_tempo_directions(source_root)
    if not tempos_by_measure:
        return
    part = part_root.find("part")
    if part is None:
        return
    for measure in part.findall("measure"):
        measure_number = measure.get("number") or ""
        if measure_number not in tempos_by_measure:
            continue
        existing = _tempo_offsets(measure)
        for offset, direction in tempos_by_measure[measure_number]:
            key = (offset, _tempo_key(direction))
            if key in existing:
                continue
            _insert_at_offset(measure, offset, copy.deepcopy(direction))
            existing.add(key)


_STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _note_midi(note: ET.Element) -> int | None:
    pitch = note.find("pitch")
    if pitch is None:
        return None
    step = pitch.findtext("step")
    octave = pitch.findtext("octave")
    if step not in _STEP_TO_SEMITONE or octave is None:
        return None
    alter = int(float(pitch.findtext("alter") or "0"))
    return (int(octave) + 1) * 12 + _STEP_TO_SEMITONE[step] + alter


def _set_measure_clef(measure: ET.Element, sign: str, line: str) -> None:
    attributes = measure.find("attributes")
    if attributes is None:
        attributes = ET.Element("attributes")
        insert_at = 1 if len(measure) and measure[0].tag == "print" else 0
        measure.insert(insert_at, attributes)
    for clef in list(attributes.findall("clef")):
        attributes.remove(clef)
    clef = ET.SubElement(attributes, "clef")
    ET.SubElement(clef, "sign").text = sign
    ET.SubElement(clef, "line").text = line


def _optimise_cello_clefs(root: ET.Element) -> None:
    part = root.find("part")
    if part is None:
        return
    current_clef = ("F", "4")
    for measure in part.findall("measure"):
        pitches = [midi for note in measure.findall("note") if (midi := _note_midi(note)) is not None]
        if not pitches:
            continue
        low, high = min(pitches), max(pitches)
        if low >= 62 and high >= 69:
            desired_clef = ("G", "2")
        elif high >= 62:
            desired_clef = ("C", "4")
        else:
            desired_clef = ("F", "4")
        if desired_clef != current_clef:
            _set_measure_clef(measure, *desired_clef)
            current_clef = desired_clef


def _set_scaling(root: ET.Element, millimeters: str) -> None:
    defaults = root.find("defaults")
    if defaults is None:
        defaults = ET.Element("defaults")
        insert_at = 0
        for index, child in enumerate(list(root)):
            if child.tag in {"work", "movement-title", "identification"}:
                insert_at = index + 1
        root.insert(insert_at, defaults)
    scaling = defaults.find("scaling")
    if scaling is None:
        scaling = ET.SubElement(defaults, "scaling")
    _set_child_text(scaling, "millimeters", millimeters)
    _set_child_text(scaling, "tenths", "40")


def _apply_part_layout_adjustments(root: ET.Element, source: ProgramPartSource, instrument_name: str) -> None:
    if instrument_name == "Violoncello" and source.title == "Dolcissima mia vita":
        _set_scaling(root, "6.3")


def _remove_credit_elements(root: ET.Element) -> None:
    for credit in list(root.findall("credit")):
        root.remove(credit)


def _set_child_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    child.text = text
    return child


def _set_metadata(root: ET.Element, title: str, composer: str) -> None:
    work = root.find("work")
    if work is None:
        work = ET.Element("work")
        root.insert(0, work)
    _set_child_text(work, "work-title", title)
    _set_child_text(root, "movement-title", title)

    identification = root.find("identification")
    if identification is None:
        identification = ET.Element("identification")
        insert_at = 0
        for index, child in enumerate(list(root)):
            if child.tag in {"work", "movement-title"}:
                insert_at = index + 1
        root.insert(insert_at, identification)
    creators = [creator for creator in identification.findall("creator") if creator.get("type") == "composer"]
    if creators:
        creators[0].text = composer
        for extra in creators[1:]:
            identification.remove(extra)
    else:
        creator = ET.Element("creator", {"type": "composer"})
        creator.text = composer
        identification.insert(0, creator)


def extract_part_xml(source: ProgramPartSource, instrument_name: str, output_path: Path) -> Path:
    tree = ET.parse(source.musicxml_path)
    source_root = tree.getroot()
    part_id = _find_part_id(source_root, instrument_name)

    root = copy.deepcopy(source_root)
    _remove_credit_elements(root)
    _strip_text_directions(root)
    _set_metadata(root, f"{source.title} - {instrument_name}", source.composer)

    part_list = root.find("part-list")
    if part_list is None:
        raise ValueError("MusicXML has no part-list")
    for child in list(part_list):
        if child.tag != "score-part" or child.get("id") != part_id:
            part_list.remove(child)

    for part in list(root.findall("part")):
        if part.get("id") != part_id:
            root.remove(part)

    _copy_tempo_directions(source_root, root)
    _apply_part_layout_adjustments(root, source, instrument_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    cleanup_musicxml_engraving(output_path, output_path)
    return output_path


def render_pdf(musescore: Path, input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [str(musescore), "-o", str(output_path), str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"MuseScore failed with return code {result.returncode}"
        raise RuntimeError(message)


def _draw_paragraph(c: canvas.Canvas, text: str, style: ParagraphStyle, x: float, y: float, width: float) -> float:
    paragraph = Paragraph(text, style)
    _wrapped_width, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(c, x, y - height)
    return y - height


def _front_matter_pdf(instrument_name: str, start_pages: dict[int, int]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 22 * mm
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=32,
        textColor=colors.HexColor("#202020"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#444444"),
        alignment=1,
    )

    y = height - 52 * mm
    y = _draw_paragraph(c, "Vocal Harmony Without Voices", title_style, margin, y, width - 2 * margin)
    y -= 6 * mm
    y = _draw_paragraph(c, f"{instrument_name} Part Book", subtitle_style, margin, y, width - 2 * margin)
    y -= 10 * mm
    _draw_paragraph(c, "Beach Boys / Gesualdo / Take 6", subtitle_style, margin, y, width - 2 * margin)
    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - 24 * mm, "Contents")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - margin, height - 24 * mm, "Page")
    y = height - 38 * mm
    for source in PROGRAM:
        line = f"{source.number}. {source.title} - {source.composer}"
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, line)
        c.drawRightString(width - margin, y, str(start_pages[source.number]))
        y -= 7 * mm
    c.save()
    return buffer.getvalue()


def _page_number_overlay(page_number: int, page_width: float, page_height: float) -> PdfReader:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(page_width / 2, 9 * mm, str(page_number))
    c.save()
    buffer.seek(0)
    return PdfReader(buffer)


def build_part_book(instrument_name: str, instrument_slug: str, piece_pdfs: list[Path]) -> Path:
    page_counts = {
        source.number: len(PdfReader(str(pdf_path)).pages)
        for source, pdf_path in zip(PROGRAM, piece_pdfs, strict=True)
    }
    start_pages: dict[int, int] = {}
    next_page = 3
    for source in PROGRAM:
        start_pages[source.number] = next_page
        next_page += page_counts[source.number]

    writer = PdfWriter()
    front_reader = PdfReader(io.BytesIO(_front_matter_pdf(instrument_name, start_pages)))
    for page in front_reader.pages:
        writer.add_page(page)
    writer.add_outline_item("Contents", 1)

    for source, pdf_path in zip(PROGRAM, piece_pdfs, strict=True):
        reader = PdfReader(str(pdf_path))
        start_page_index = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        writer.add_outline_item(f"{source.number}. {source.title}", start_page_index)

    for index, page in enumerate(writer.pages, start=1):
        overlay = _page_number_overlay(index, float(page.mediabox.width), float(page.mediabox.height))
        page.merge_page(overlay.pages[0])

    output_path = OUTPUT_PDF_DIR / f"gesualdo_take6_evening_{instrument_slug}_part_book.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def build_all(musescore: Path | None = None) -> list[Path]:
    musescore = musescore or default_musescore_path()
    if not musescore.exists():
        raise FileNotFoundError(musescore)
    for source in PROGRAM:
        if not source.musicxml_path.exists():
            raise FileNotFoundError(source.musicxml_path)

    books: list[Path] = []
    for instrument_name, instrument_slug in INSTRUMENTS:
        piece_pdfs: list[Path] = []
        for source in PROGRAM:
            piece_slug = f"{source.number:02d}_{slugify(source.title)}"
            part_xml = OUTPUT_XML_DIR / instrument_slug / f"{piece_slug}__{instrument_slug}.musicxml"
            part_pdf = PIECE_PDF_DIR / instrument_slug / f"{piece_slug}__{instrument_slug}.pdf"
            extract_part_xml(source, instrument_name, part_xml)
            render_pdf(musescore, part_xml, part_pdf)
            piece_pdfs.append(part_pdf)
            print(part_pdf.relative_to(ROOT))
        books.append(build_part_book(instrument_name, instrument_slug, piece_pdfs))
        print(books[-1].relative_to(ROOT))
    return books


def main() -> None:
    for book in build_all():
        print(book.relative_to(ROOT))


if __name__ == "__main__":
    main()
