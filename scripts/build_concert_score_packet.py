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
        "Luci serene e chiare",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/109_luci_serene_e_chiare.pdf",
    ),
    ProgramScore(
        2,
        "Dolcissima mia vita",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/092_dolcissima_mia_vita.pdf",
    ),
    ProgramScore(
        3,
        "Gia piansi nel dolore",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/100_gi_piansi_nel_dolore.pdf",
    ),
    ProgramScore(
        4,
        "S'io non miro non moro",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/147_s_io_non_miro_non_moro.pdf",
    ),
    ProgramScore(
        5,
        "Come Unto Me",
        "Take 6",
        "6 vocal parts",
        ROOT / "data/take6/renders/string_quartet_double_stops_pdf/come_unto_me.pdf",
    ),
    ProgramScore(
        6,
        "Moro, lasso, al mio duolo",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/121_moro_lasso_al_mio_duolo.pdf",
    ),
    ProgramScore(
        7,
        "Sparge la morte",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/161_sparge_la_morte.pdf",
    ),
    ProgramScore(
        8,
        "Belta, poi che t'assenti",
        "Carlo Gesualdo",
        "5 voices",
        ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf/074_belt_poi_che_t_assenti.pdf",
    ),
    ProgramScore(
        9,
        "Tristis est anima mea",
        "Carlo Gesualdo",
        "6 voices",
        ROOT / "data/cpdl/6-voices/renders/string_quartet_pdf/051_tristis_est_anima_mea.pdf",
    ),
    ProgramScore(
        10,
        "Hark! The Herald Angels Sing",
        "Take 6",
        "6 vocal parts",
        ROOT / "data/take6/renders/string_quartet_double_stops_pdf/hark_herald.pdf",
    ),
    ProgramScore(
        11,
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


def _front_matter_pdf(program: tuple[ProgramScore, ...]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ConcertTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#202020"),
    )
    subtitle_style = ParagraphStyle(
        "ConcertSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#444444"),
    )
    small_style = ParagraphStyle(
        "ConcertSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
    )
    toc_style = ParagraphStyle(
        "ConcertToc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#202020"),
    )

    margin = 22 * mm
    y = height - 42 * mm
    y = _draw_paragraph(c, "Gesualdo / Take 6", title_style, margin, y, width - 2 * margin)
    y -= 5 * mm
    y = _draw_paragraph(c, "Concert score packet for string quartet", subtitle_style, margin, y, width - 2 * margin)
    y -= 10 * mm
    _draw_paragraph(
        c,
        f"{len(program)} scores in concert order. Generated from the clean review PDFs.",
        small_style,
        margin,
        y,
        width - 2 * margin,
    )
    c.setStrokeColor(colors.HexColor("#777777"))
    c.line(margin, 35 * mm, width - margin, 35 * mm)
    _draw_paragraph(
        c,
        "Gesualdo reductions and Take 6 double-stop reductions for quartet director review.",
        small_style,
        margin,
        30 * mm,
        width - 2 * margin,
    )
    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - 24 * mm, "Contents")
    y = height - 38 * mm
    for score in program:
        line = f"{score.number}. {score.title} - {score.composer} ({score.original_voices})"
        y = _draw_paragraph(c, line, toc_style, margin, y, width - 2 * margin)
        y -= 3 * mm
    c.save()
    return buffer.getvalue()


def build_packet(output_path: Path = OUTPUT_PATH) -> Path:
    missing = [score.pdf_path for score in PROGRAM if not score.pdf_path.exists()]
    if missing:
        missing_list = "\n".join(str(path.relative_to(ROOT)) for path in missing)
        raise FileNotFoundError(f"Missing source PDFs:\n{missing_list}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    front_reader = PdfReader(io.BytesIO(_front_matter_pdf(PROGRAM)))
    for page in front_reader.pages:
        writer.add_page(page)
    writer.add_outline_item("Contents", 1)

    for score in PROGRAM:
        reader = PdfReader(str(score.pdf_path))
        start_page = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)
        writer.add_outline_item(f"{score.number}. {score.title}", start_page)

    with output_path.open("wb") as fh:
        writer.write(fh)
    return output_path


def main() -> None:
    output_path = build_packet()
    print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
