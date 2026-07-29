"""Build the evening concert score packet for the Gesualdo / Take 6 quartet program."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "quartet_director"
OUTPUT_PATH = OUTPUT_DIR / "gesualdo_take6_evening_score_packet.pdf"


@dataclass(frozen=True)
class ProgramScore:
    number: int
    title: str
    composer: str
    original_voices: str
    pdf_path: Path


PROGRAM: tuple[ProgramScore, ...] = (
    ProgramScore(
        1,
        "Our Prayer",
        "The Beach Boys",
        "4 voices",
        ROOT / "data/beach boys/renders/string_quartet_pdf/our_prayer_low_cello.pdf",
    ),
    ProgramScore(
        2,
        "Luci serene e chiare",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/109_luci_serene_e_chiare.pdf",
    ),
    ProgramScore(
        3,
        "Dolcissima mia vita",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/092_dolcissima_mia_vita.pdf",
    ),
    ProgramScore(
        4,
        "Già piansi nel dolore",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/100_gi_piansi_nel_dolore.pdf",
    ),
    ProgramScore(
        5,
        "S'io non miro non moro",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/147_s_io_non_miro_non_moro.pdf",
    ),
    ProgramScore(
        6,
        "Come Unto Me",
        "Take 6",
        "6 vocal parts",
        ROOT / "data/take6/renders/string_quartet_double_stops_pdf/come_unto_me.pdf",
    ),
    ProgramScore(
        7,
        "Moro, lasso, al mio duolo",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/121_moro_lasso_al_mio_duolo.pdf",
    ),
    ProgramScore(
        8,
        "Sparge la morte",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/161_sparge_la_morte.pdf",
    ),
    ProgramScore(
        9,
        "Beltà, poi che t'assenti",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/074_belt_poi_che_t_assenti.pdf",
    ),
    ProgramScore(
        10,
        "Tristis est anima mea",
        "Carlo Gesualdo",
        "6 voices",
        ROOT / "data/cpdl/6-voices/renders/string_quartet_pdf/051_tristis_est_anima_mea.pdf",
    ),
    ProgramScore(
        11,
        "Hark! The Herald Angels Sing",
        "Take 6",
        "6 vocal parts",
        ROOT / "data/take6/renders/string_quartet_double_stops_pdf/hark_herald.pdf",
    ),
    ProgramScore(
        12,
        "A Quiet Place",
        "Take 6",
        "6 vocal parts",
        ROOT / "data/take6/renders/string_quartet_double_stops_pdf/a_quiet_place.pdf",
    ),
)


def _draw_paragraph(c: canvas.Canvas, text: str, style: ParagraphStyle, x: float, y: float, width: float) -> float:
    paragraph = Paragraph(text, style)
    _wrapped_width, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(c, x, y - height)
    return y - height


def _source_page_counts(program: tuple[ProgramScore, ...]) -> dict[int, int]:
    return {score.number: len(PdfReader(str(score.pdf_path)).pages) for score in program}


def _score_start_pages(program: tuple[ProgramScore, ...], page_counts: dict[int, int]) -> dict[int, int]:
    start_pages: dict[int, int] = {}
    next_page = 3
    for score in program:
        start_pages[score.number] = next_page
        next_page += page_counts[score.number]
    return start_pages


def _front_matter_pdf(program: tuple[ProgramScore, ...], start_pages: dict[int, int]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ConcertTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=27,
        leading=33,
        textColor=colors.HexColor("#202020"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "ConcertSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=19,
        textColor=colors.HexColor("#444444"),
        alignment=1,
    )
    small_style = ParagraphStyle(
        "ConcertSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#555555"),
        alignment=1,
    )
    margin = 22 * mm
    y = height - 52 * mm
    y = _draw_paragraph(c, "Vocal Harmony Without Voices", title_style, margin, y, width - 2 * margin)
    y -= 6 * mm
    y = _draw_paragraph(c, "Beach Boys / Gesualdo / Take 6", subtitle_style, margin, y, width - 2 * margin)
    y -= 12 * mm
    _draw_paragraph(
        c,
        "Concert score packet for string quartet",
        small_style,
        margin,
        y,
        width - 2 * margin,
    )
    c.setStrokeColor(colors.HexColor("#909090"))
    c.line(width / 2 - 38 * mm, y - 13 * mm, width / 2 + 38 * mm, y - 13 * mm)
    _draw_paragraph(
        c,
        f"{len(program)} scores in concert order",
        small_style,
        margin,
        y - 24 * mm,
        width - 2 * margin,
    )
    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - 24 * mm, "Contents")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - margin, height - 24 * mm, "Page")
    y = height - 38 * mm
    for score in program:
        line = f"{score.number}. {score.title} - {score.composer} ({score.original_voices})"
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, line)
        c.drawRightString(width - margin, y, str(start_pages[score.number]))
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


def build_packet(output_path: Path = OUTPUT_PATH) -> Path:
    missing = [score.pdf_path for score in PROGRAM if not score.pdf_path.exists()]
    if missing:
        missing_list = "\n".join(str(path.relative_to(ROOT)) for path in missing)
        raise FileNotFoundError(f"Missing source PDFs:\n{missing_list}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_counts = _source_page_counts(PROGRAM)
    start_pages = _score_start_pages(PROGRAM, page_counts)

    writer = PdfWriter()
    front_reader = PdfReader(io.BytesIO(_front_matter_pdf(PROGRAM, start_pages)))
    for page in front_reader.pages:
        writer.add_page(page)
    writer.add_outline_item("Contents", 1)

    for score in PROGRAM:
        reader = PdfReader(str(score.pdf_path))
        start_page = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        writer.add_outline_item(f"{score.number}. {score.title}", start_page)

    for index, page in enumerate(writer.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_reader = _page_number_overlay(index, width, height)
        page.merge_page(overlay_reader.pages[0])

    with output_path.open("wb") as fh:
        writer.write(fh)
    return output_path


def main() -> None:
    output_path = build_packet()
    print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
