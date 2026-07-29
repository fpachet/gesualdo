"""Build a short audience-facing concert document for the Gesualdo / Take 6 program."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "quartet_director"
OUTPUT_PATH = OUTPUT_DIR / "gesualdo_take6_concert_program.pdf"


@dataclass(frozen=True)
class ProgramItem:
    number: int
    title: str
    composer: str
    original_voices: str
    duration: str


PROGRAM: tuple[ProgramItem, ...] = (
    ProgramItem(1, "Anonymous opening chorale", "revealed later", "4 voices", "c. 1:10"),
    ProgramItem(2, "Luci serene e chiare", "Carlo Gesualdo", "5 voices", "c. 3:00"),
    ProgramItem(3, "Dolcissima mia vita", "Carlo Gesualdo", "5 voices", "c. 2:15"),
    ProgramItem(4, "Gia piansi nel dolore", "Carlo Gesualdo", "5 voices", "c. 2:40"),
    ProgramItem(5, "S'io non miro non moro", "Carlo Gesualdo", "5 voices", "c. 2:00"),
    ProgramItem(6, "Come Unto Me", "Take 6", "6 vocal parts", "c. 2:15"),
    ProgramItem(7, "Moro, lasso, al mio duolo", "Carlo Gesualdo", "5 voices", "c. 3:00"),
    ProgramItem(8, "Sparge la morte", "Carlo Gesualdo", "5 voices", "c. 2:50"),
    ProgramItem(9, "Belta, poi che t'assenti", "Carlo Gesualdo", "5 voices", "c. 2:15"),
    ProgramItem(10, "Tristis est anima mea", "Carlo Gesualdo", "6 voices", "c. 3:00"),
    ProgramItem(11, "Hark! The Herald Angels Sing", "Take 6", "6 vocal parts", "c. 2:30"),
    ProgramItem(12, "A Quiet Place", "Take 6", "6 vocal parts", "c. 2:45"),
)


INTRO_PARAGRAPHS = (
    "This concert-conference begins with a short four-voice piece played without "
    "a label. The audience is invited to hear it first as a question: Renaissance, "
    "Baroque, sacred, modern? The reveal is part of the argument: the piece is "
    "the Beach Boys' Our Prayer, and it already shows vocal harmony becoming "
    "quartet harmony.",
    "The programme then places two distant vocal worlds beside one another: Carlo "
    "Gesualdo's late Renaissance madrigals and sacred music, and the dense, "
    "radiant close harmony of Take 6. Both repertoires are built from voices that "
    "move with extraordinary independence, but both also create moments where harmony "
    "seems to stop time: suspensions, chromatic shocks, luminous clusters, and "
    "unexpected resolutions.",
    "The string quartet hears these works from inside. Instead of treating the quartet "
    "as a simple transcription machine, the project asks how five or six vocal lines "
    "can be reduced, redistributed, and made playable by four instruments while keeping "
    "as much of the original contrapuntal pressure as possible. This is also where AI "
    "enters the evening: as a tool for listening, searching, recombining, testing, and "
    "auditing musical decisions.",
    "The programme moves from the four-voice opening into Gesualdo's five-voice madrigal world, then toward "
    "more extreme chromatic writing, then opens a modern mirror through Take 6. The "
    "six-voice Gesualdo near the end acts as a historical summit, and the final Take 6 "
    "piece, A Quiet Place, gives the evening a calm landing after the harmonic vertigo.",
)


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#202020"),
            spaceAfter=7 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#444444"),
            spaceAfter=9 * mm,
        ),
        "heading": ParagraphStyle(
            "Heading",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#202020"),
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=10.2,
            leading=15,
            textColor=colors.HexColor("#202020"),
            spaceAfter=4 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=12,
            textColor=colors.HexColor("#555555"),
        ),
    }


def _playlist_table(styles: dict[str, ParagraphStyle]) -> Table:
    header = ["#", "Piece", "Composer", "Original", "Approx."]
    rows: list[list[str | Paragraph]] = [header]
    for item in PROGRAM:
        rows.append(
            [
                str(item.number),
                Paragraph(item.title, styles["small"]),
                item.composer,
                item.original_voices,
                item.duration,
            ]
        )

    table = Table(rows, colWidths=[9 * mm, 64 * mm, 35 * mm, 28 * mm, 22 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECECEC")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#202020")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.4),
                ("LEADING", (0, 1), (-1, -1), 10.5),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#707070")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#D0D0D0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_document(output_path: Path = OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=24 * mm,
        bottomMargin=22 * mm,
        title="Gesualdo / Take 6 Concert Program",
        author="Francois Pachet",
    )

    story = [
        Paragraph("Gesualdo / Take 6", styles["title"]),
        Paragraph("Concert-conference for string quartet, AI, and impossible harmonies", styles["subtitle"]),
        Paragraph("Introduction", styles["heading"]),
    ]
    for paragraph in INTRO_PARAGRAPHS:
        story.append(Paragraph(paragraph, styles["body"]))

    story.extend(
        [
            Spacer(1, 3 * mm),
            Paragraph("Programme", styles["heading"]),
            KeepTogether(_playlist_table(styles)),
            Spacer(1, 5 * mm),
            Paragraph(
                "Total music: approximately 29:30 strict timing, or about 32-33 minutes with "
                "stage pacing and transitions. The complete event can comfortably fit into a one-hour "
                "concert-conference with short spoken introductions between musical groups.",
                styles["small"],
            ),
            PageBreak(),
            Paragraph("Suggested Spoken Arc", styles["heading"]),
            Paragraph(
                "<b>1. Opening question.</b> Begin with the anonymous four-voice piece, then reveal "
                "the Beach Boys and use that surprise to introduce vocal harmony without voices.",
                styles["body"],
            ),
            Paragraph(
                "<b>2. Reduction as listening.</b> How the quartet version compresses five or six "
                "voices into four instruments, and what has to be preserved: line, tension, register, "
                "and harmonic identity.",
                styles["body"],
            ),
            Paragraph(
                "<b>3. AI as a musical workbench.</b> The system is not presented as a replacement "
                "composer, but as a way to inspect style, test constraints, locate problems, and generate "
                "musical alternatives.",
                styles["body"],
            ),
            Paragraph(
                "<b>4. The final turn.</b> After Gesualdo's 6-voice sacred depth, Hark brings radiance "
                "and A Quiet Place closes the evening not with a demonstration, but with a destination.",
                styles["body"],
            ),
        ]
    )

    doc.build(story)
    return output_path


def main() -> None:
    output_path = build_document()
    print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
