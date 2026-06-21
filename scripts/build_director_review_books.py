"""Build merged conductor-review PDF books from generated reduction PDFs."""

from __future__ import annotations

import argparse
import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "output" / "pdf" / "quartet_director"


@dataclass(frozen=True)
class WorkPdf:
    index: str
    section: str
    title: str
    pdf_path: Path
    source_parts: str


@dataclass(frozen=True)
class BookSpec:
    title: str
    subtitle: str
    report_path: Path
    pdf_dir: Path
    output_name: str
    take6: bool = False


BOOKS = {
    "gesualdo-5": BookSpec(
        title="Gesualdo String Quartet Reductions",
        subtitle="Five-voice source works - clean review scores",
        report_path=ROOT / "data/cpdl/5-voices/reductions/string_quartet/report.tsv",
        pdf_dir=ROOT / "data/cpdl/5-voices/renders/string_quartet_pdf",
        output_name="gesualdo_5_voice_string_quartet_reductions.pdf",
    ),
    "gesualdo-6": BookSpec(
        title="Gesualdo String Quartet Reductions",
        subtitle="Six-voice source works - clean review scores",
        report_path=ROOT / "data/cpdl/6-voices/reductions/string_quartet/report.tsv",
        pdf_dir=ROOT / "data/cpdl/6-voices/renders/string_quartet_pdf",
        output_name="gesualdo_6_voice_string_quartet_reductions.pdf",
    ),
    "take6": BookSpec(
        title="Take 6 String Quartet Reductions",
        subtitle="Double-stop variant - clean review scores",
        report_path=ROOT / "data/take6/reductions/string_quartet_double_stops/report.tsv",
        pdf_dir=ROOT / "data/take6/renders/string_quartet_double_stops_pdf",
        output_name="take6_string_quartet_double_stops_reductions.pdf",
        take6=True,
    ),
}


def _read_works(spec: BookSpec) -> list[WorkPdf]:
    if spec.take6:
        return _read_take6_works(spec)
    works: list[WorkPdf] = []
    with spec.report_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("status") != "ok":
                continue
            musicxml = Path(row["output_path"])
            pdf_path = spec.pdf_dir / f"{musicxml.stem}.pdf"
            if not pdf_path.exists():
                raise FileNotFoundError(f"Missing PDF for {musicxml}: {pdf_path}")
            works.append(
                WorkPdf(
                    index=row.get("work_index", ""),
                    section=row.get("section", ""),
                    title=row.get("work_title", musicxml.stem),
                    pdf_path=pdf_path,
                    source_parts=row.get("source_parts", ""),
                )
            )
    return works


def _read_take6_works(spec: BookSpec) -> list[WorkPdf]:
    works: list[WorkPdf] = []
    with spec.report_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("status") != "ok":
                continue
            musicxml = Path(row["output_path"])
            pdf_path = spec.pdf_dir / f"{musicxml.stem}.pdf"
            if not pdf_path.exists():
                raise FileNotFoundError(f"Missing PDF for {musicxml}: {pdf_path}")
            works.append(
                WorkPdf(
                    index=str(len(works) + 1),
                    section="Take 6",
                    title=_title_from_stem(musicxml.stem),
                    pdf_path=pdf_path,
                    source_parts=row.get("source_parts", ""),
                )
            )
    return works


def _title_from_stem(stem: str) -> str:
    title = stem
    if title[:3].isdigit() and len(title) > 4:
        title = title[4:]
    return title.replace("_", " ").title()


def _draw_paragraph(c: canvas.Canvas, text: str, style: ParagraphStyle, x: float, y: float, width: float) -> float:
    paragraph = Paragraph(text, style)
    _w, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(c, x, y - height)
    return y - height


def _front_matter_pdf(spec: BookSpec, works: list[WorkPdf]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DirectorTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#202020"),
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        "DirectorSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=colors.HexColor("#444444"),
    )
    small_style = ParagraphStyle(
        "DirectorSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#555555"),
    )
    toc_style = ParagraphStyle(
        "DirectorToc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#202020"),
    )

    margin = 22 * mm
    y = height - 42 * mm
    y = _draw_paragraph(c, spec.title, title_style, margin, y, width - 2 * margin)
    y -= 5 * mm
    y = _draw_paragraph(c, spec.subtitle, subtitle_style, margin, y, width - 2 * margin)
    y -= 12 * mm
    _draw_paragraph(
        c,
        f"{len(works)} scores. Generated from the clean conductor-review PDFs.",
        small_style,
        margin,
        y,
        width - 2 * margin,
    )
    c.setStrokeColor(colors.HexColor("#777777"))
    c.line(margin, 35 * mm, width - margin, 35 * mm)
    _draw_paragraph(
        c,
        "Generated by scripts/build_director_review_books.py. Editorial dynamics and hairpins are suppressed in these clean review PDFs.",
        small_style,
        margin,
        30 * mm,
        width - 2 * margin,
    )
    c.showPage()

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, height - 24 * mm, "Contents")
    c.setFont("Helvetica", 9)
    y = height - 36 * mm
    current_section = None
    for work in works:
        if work.section and work.section != current_section:
            if y < 45 * mm:
                c.showPage()
                c.setFont("Helvetica-Bold", 16)
                c.drawString(margin, height - 24 * mm, "Contents")
                y = height - 36 * mm
            if current_section is not None:
                y -= 3 * mm
            current_section = work.section
            c.setFillColor(colors.HexColor("#303030"))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, current_section)
            y -= 8 * mm
        line = f"{work.index}. {work.title}"
        y = _draw_paragraph(c, line, toc_style, margin + 4 * mm, y, width - 2 * margin - 4 * mm)
        y -= 2.2 * mm
        if y < 32 * mm:
            c.showPage()
            c.setFont("Helvetica-Bold", 16)
            c.drawString(margin, height - 24 * mm, "Contents")
            y = height - 36 * mm
            current_section = None
    c.save()
    return buffer.getvalue()


def _append_pdf(writer: PdfWriter, pdf_path: Path) -> tuple[int, int]:
    start_page = len(writer.pages)
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)
    return start_page, len(reader.pages)


def build_book(spec: BookSpec, output_dir: Path) -> Path:
    works = _read_works(spec)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / spec.output_name

    writer = PdfWriter()
    front_reader = PdfReader(io.BytesIO(_front_matter_pdf(spec, works)))
    for page in front_reader.pages:
        writer.add_page(page)
    writer.add_outline_item("Contents", 1)

    for work in works:
        start_page, _page_count = _append_pdf(writer, work.pdf_path)
        label = f"{work.index}. {work.title}" if work.index else work.title
        writer.add_outline_item(label, start_page)

    with output_path.open("wb") as fh:
        writer.write(fh)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for merged PDF books.",
    )
    parser.add_argument(
        "--book",
        action="append",
        choices=sorted(BOOKS),
        help="Book key to build. Defaults to all books.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = args.book or sorted(BOOKS)
    for key in selected:
        output_path = build_book(BOOKS[key], args.output_dir)
        print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
