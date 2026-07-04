"""Build the evening concert plan and vision-paper draft documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
PDF_DIR = ROOT / "output" / "pdf" / "quartet_director"

PLAN_MD = OUTPUT_DIR / "concert_plan.md"
VISION_MD = OUTPUT_DIR / "vision_paper_draft.md"
PLAN_PDF = PDF_DIR / "gesualdo_take6_evening_concert_plan.pdf"
VISION_PDF = PDF_DIR / "gesualdo_take6_vision_paper_draft.pdf"


@dataclass(frozen=True)
class ProgramItem:
    number: int
    piece: str
    composer: str
    source: str
    duration: str
    function: str


PROGRAM: tuple[ProgramItem, ...] = (
    ProgramItem(1, "Luci serene e chiare", "Carlo Gesualdo", "5 voices", "2:59", "Opening Gesualdo example"),
    ProgramItem(2, "Dolcissima mia vita", "Carlo Gesualdo", "5 voices", "2:15", "Short lyrical madrigal"),
    ProgramItem(3, "Gia piansi nel dolore", "Carlo Gesualdo", "5 voices", "2:37", "Chromatic expression of grief"),
    ProgramItem(4, "S'io non miro non moro", "Carlo Gesualdo", "5 voices", "2:00", "Compact madrigal; Mantovani link"),
    ProgramItem(5, "Come Unto Me", "Take 6", "6 vocal parts", "2:13", "First Take 6 comparison"),
    ProgramItem(6, "Moro, lasso, al mio duolo", "Carlo Gesualdo", "5 voices", "2:58", "Central Gesualdo example"),
    ProgramItem(7, "Sparge la morte", "Carlo Gesualdo", "5 voices", "2:49", "Contrasting madrigal texture"),
    ProgramItem(8, "Belta, poi che t'assenti", "Carlo Gesualdo", "5 voices", "2:11", "Stravinsky connection"),
    ProgramItem(9, "Tristis est anima mea", "Carlo Gesualdo", "6 voices", "3:00", "Six-voice sacred work"),
    ProgramItem(10, "Hark! The Herald Angels Sing", "Take 6", "6 vocal parts", "2:32", "Bright late-program contrast"),
    ProgramItem(11, "A Quiet Place", "Take 6", "6 vocal parts", "2:46", "Final calm piece"),
)


PLAN_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Concept",
        (
            "This evening presents vocal music without voices. Gesualdo's madrigals and sacred pieces were written for five or six voices. Take 6 works in a very different idiom - gospel, jazz, pop, and studio vocal virtuosity - but it also depends on several independent voices forming one harmonic body.",
            "The string quartet cannot reproduce the words, breath, or vocal blend of the originals. It can make other things clear: counterpoint, harmonic structure, register, and the movement from one sonority to another. The practical question is simple: what can be kept when five or six vocal lines have to become four string parts?",
        ),
    ),
    (
        "Why Reduce This Music for String Quartet",
        (
            "The string quartet is not just a practical four-part ensemble. It is often treated as a quintessence of Western harmonic and contrapuntal music. In a Weberian sense, it can be heard as a highly rationalized musical medium: four independent tuned instruments, written notation, controlled voice-leading, and a long history of harmonic thought.",
            "This makes the quartet a strong test for Gesualdo and Take 6. Both repertoires were made for voices, but both depend on the relation between independent lines and harmonic result. Reducing them for quartet asks whether their essential musical events can survive in one of the most demanding instrumental formats.",
            "The project also has a practical artistic goal: to enrich the string quartet repertoire with music that normally belongs to vocal ensembles, and to make Gesualdo's repertoire better known, more playable, and more alive for contemporary listeners.",
        ),
    ),
    (
        "AI Argument",
        (
            "A central part of the project is the custom AI system developed for these reductions. The problem is not only to remove notes. The system has to choose between many competing constraints: preserving important lines, keeping characteristic dissonances and chromatic motions, respecting instrument ranges and sweet spots, avoiding unreadable notation, and producing something a quartet can actually play.",
            "This is an unusual use of AI, but one that is worthwhile: AI as complex problem solving, involving no issues about copyright or ethics. Here the goal is to transform a given piece to make it playable by a quartet. This AI makes reduction decisions explicit, tests alternatives, detects issues, and helps balance antagonistic musical constraints.",
            "The final scores are not automatic transcriptions, but the result of a guided process combining musical judgment, algorithms, notation cleanup, and listening.",
        ),
    ),
    (
        "Overall Timing",
        (
            "Nominal music duration: about 28:20. Realistic performed music duration: about 31-32 minutes. With transitions and short spoken islands: about 39-40 minutes. Total spoken introduction and discussion: about 19-21 minutes. Total event: about 58-61 minutes.",
            "The evening should feel like a concert first and a conference second: short spoken islands, then music. The explanations should sharpen listening rather than interrupt it.",
        ),
    ),
    (
        "Musical Shape",
        (
            "Part I - Gesualdo madrigal language: Luci serene e chiare; Dolcissima mia vita; Gia piansi nel dolore; S'io non miro non moro.",
            "Part II - Comparison and central examples: Come Unto Me; Moro, lasso, al mio duolo; Sparge la morte; Belta, poi che t'assenti.",
            "Part III - Six-voice and closing pieces: Tristis est anima mea; Hark! The Herald Angels Sing; A Quiet Place.",
        ),
    ),
    (
        "Spoken Islands",
        (
            "Opening, 3-4 minutes: vocal music without voices; why Gesualdo and Take 6 are in the same programme; why the string quartet is a useful medium.",
            "After piece 2 or before piece 3, 3 minutes: what a madrigal is; how words create musical decisions; why chromatic voice-leading matters more than isolated chords.",
            "Before Come Unto Me, 3 minutes: why Take 6 belongs here; six vocal parts as a modern comparison to Gesualdo's multi-voice writing.",
            "Before Moro, lasso, 4 minutes: the AI/reduction problem. Explain the competing constraints: keep essential musical events, fit four instruments, preserve readable notation, and avoid losing the character of the original.",
            "Before Tristis or Hark, 4 minutes: place the last group clearly: one six-voice Gesualdo work, then two Take 6 pieces to close the evening in a different harmonic world.",
        ),
    ),
    (
        "Closing Formulation",
        (
            "The concert does not try to make Gesualdo and Take 6 the same. It uses the quartet to compare two kinds of complex vocal harmony. Gesualdo shows how chromatic voice-leading can create extraordinary tension. Take 6 shows another use of dense harmony: clarity, blend, and consolation. The AI system is the tool that makes this comparison playable and inspectable.",
        ),
    ),
)


VISION_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Provisional Abstract",
        (
            "This project transforms vocal works by Carlo Gesualdo and Take 6 into music for string quartet. It is not simply a transcription project. It asks what remains of vocal harmony when the voices, words, and breath disappear, and what must be preserved for the music still to carry its expressive force.",
            "The central claim is that quartet reduction can become a form of analysis. Gesualdo's harmonic shocks are not autonomous chordal objects; they are produced by independent lines, semitone motions, suspensions, false relations, and local chromatic wounds. Reducing these works to four string parts forces explicit decisions about which events are essential.",
        ),
    ),
    (
        "Gesualdo's Historical Paradox",
        (
            "Gesualdo belongs to the late Renaissance and remains grounded in counterpoint, modality, and madrigalian text expression. Yet his late madrigals can sound uncannily close to later harmonic worlds. He is not Baroque in the normal sense, and not a proto-modernist in any simple causal sense. He is better understood as a late-Renaissance Mannerist whose music pushes Renaissance technique to the edge of rupture.",
            "His modernity is retrospective. Gesualdo sounds modern because he explored a path that Western music largely did not take: an extreme modal-chromatic language generated by voice-leading rather than by later tonal function. His late madrigals contain, in this sense, a future that did not happen.",
        ),
    ),
    (
        "Why the String Quartet",
        (
            "The string quartet is not just a convenient four-part ensemble. It is one of the privileged media of Western art music: four independent lines, harmonic responsibility without orchestral excess, contrapuntal clarity, and an intense balance between individual voice and collective structure.",
            "Placing Gesualdo inside this medium is historically charged. A six-voice madrigal belongs to late Renaissance vocal culture. A string quartet belongs symbolically to later instrumental modernity. The reduction stages a confrontation between Renaissance chromatic excess and a later Western ideal of disciplined four-part thought.",
        ),
    ),
    (
        "Reduction as Analysis",
        (
            "Because a quartet has only four voices, reduction requires loss. That loss is productive. Every decision asks which voice must remain, which chromatic inflection carries the expressive force, which dissonance is structurally essential, and which vertical sonority can be implied rather than literally preserved.",
            "A piano can absorb notes and turn counterpoint into chordal objects. An orchestra can hide compromises in color and mass. A quartet cannot. Its austerity makes the reduction problem audible. The quartet does not conceal the loss; it dramatizes the choice.",
        ),
    ),
    (
        "What Must Be Preserved",
        (
            "A successful reduction must preserve motions, not only notes. Gesualdo's semitone inflections, suspensions, false relations, cadential distortions, registral tensions, and abrupt color shifts are often more important than complete vertical pitch coverage.",
            "The absent text also matters. In the vocal originals, words such as death, pain, sighing, cruelty, and desire push the counterpoint out of balance. The quartet removes the words, but it should preserve the damage they inflicted on the music. In the instrumental version, the words disappear, but their chromatic scars remain.",
            "This is why a purely chordal view is insufficient. The shocking sonority may matter less than how it is approached and abandoned. Gesualdo's harmony is not a sequence of objects, but a sequence of wounds in the voice-leading.",
        ),
    ),
    (
        "Against Simplification",
        (
            "The project does not claim that Gesualdo was literally Baroque, Romantic, or modern. Nor does it depend on the biographical myth of the murderous prince, or on a simplified story of the diabolus in musica. The useful point is not sensational biography, but musical pressure: the sensation that a disciplined contrapuntal order is being bent from within.",
            "The quartet version should therefore not smooth Gesualdo into beautiful Renaissance counterpoint. It should preserve instability. It should allow the listener to hear the music as a theatre of chromatic transgression without pretending that Gesualdo simply anticipated later harmonic systems.",
        ),
    ),
    (
        "Take 6 as Modern Mirror",
        (
            "Take 6 enters the project not as a stylistic contrast only, but as a modern mirror. Their music also treats several independent voices as a single harmonic organism. The language is gospel, jazz, pop, studio precision, and close-harmony virtuosity, but the structural fascination is related: how multiple human lines create a harmonic body no single line could produce.",
            "In quartet form, Take 6 becomes another version of vocal music without voices. The difficulty is not merely density; it is preserving warmth, blend, inner motion, and harmonic brilliance when six singers become four strings.",
        ),
    ),
    (
        "Modern Reactivations",
        (
            "The project belongs to a broader history of modern Gesualdo reactivation. Stravinsky's Monumentum pro Gesualdo recomposes three Gesualdo madrigals for instruments and was premiered in Venice in 1960. His Tres sacrae cantiones completed missing parts in Gesualdo, producing, in Robert Craft's phrase quoted by Boosey, not pure Gesualdo, but a fusion of the two composers.",
            "Noel Akchote's Gesualdo: Madrigals for Five Guitars, originally released in 2014, adapts Book V madrigals for electric guitars. Bruno Mantovani's Time Stretch (on Gesualdo), 2006, expands Gesualdo into contemporary orchestral time. The present project differs by compression: it asks what survives when Gesualdo is forced into four exposed instrumental lines.",
        ),
    ),
    (
        "Weberian Tension",
        (
            "Max Weber's unfinished study of music, written around 1912-1913 and published posthumously in 1921, is useful as a conceptual background because it links Western harmonic music to instruments, tuning, notation, and rationalization. The string quartet can be heard as a later emblem of this rationalized musical world.",
            "Bringing Gesualdo into quartet therefore creates a productive tension: chromatic excess inside disciplined instrumental form, vocal wounds inside tuned strings, modal instability inside a medium associated with later harmonic thought.",
        ),
    ),
    (
        "AI and the Musical Workbench",
        (
            "The AI component should be understood as a musical workbench rather than a replacement composer. It helps inspect scores, test constraints, compare reductions, locate notational problems, and make explicit the criteria that musicians often apply intuitively.",
            "A computational reduction of six voices to four requires priorities: preserve the bass where necessary, preserve cadential motion, keep semitone inflections and false relations, retain suspensions and their resolutions, avoid unidiomatic string writing, and maintain enough independence for the four parts to feel like lines rather than a chordal summary.",
            "The difficulty is that the important events are not always obvious from pitch content alone. A note may matter because of its text, its dissonance, its register, its role in a cadence, or its participation in a contradiction across voices. The system should not merely reduce notes; it should help identify and preserve expressive events.",
        ),
    ),
    (
        "The Concert as Argument",
        (
            "The evening programme turns the argument into a listening path. It begins with five-voice Gesualdo pieces where light, sweetness, grief, and paradox are gradually destabilized. Take 6 then appears as the first modern mirror: another world of vocal harmony, compressed into strings.",
            "The center of the concert is Moro, lasso, al mio duolo, where chromatic suffering becomes almost physical. The programme then moves through death, absence, and six-voice sacred darkness before turning to Take 6 again: Hark! The Herald Angels Sing as sacred radiance, and A Quiet Place as final repose.",
            "The final point is not that Take 6 resolves Gesualdo historically. It does something gentler and more interesting: it places another model of complex vocal harmony beside Gesualdo, one in which density can become consolation.",
        ),
    ),
    (
        "Toward the Full Paper",
        (
            "The full paper can develop this argument through case studies: original vocal texture, naive reduction, and quartet reduction. It can compare what is preserved or lost in semitone motions, suspensions, false relations, cadential distortions, and registral shocks.",
            "The methodological question is also computational: can a system identify must-preserve events? Can false relations, suspensions, cadential motions, and expressive chromatic inflections be detected and weighted? The artistic question remains inseparable from the technical one: the system should not merely reduce notes; it should preserve expressive events.",
        ),
    ),
    (
        "Factual Anchors",
        (
            "Weber's music study is unfinished, written around 1912-1913 and published posthumously in 1921. Stravinsky's Monumentum pro Gesualdo is described by Boosey as three Gesualdo madrigals recomposed for instruments and was premiered in Venice in 1960.",
            "Stravinsky's Tres sacrae cantiones completed missing parts in Gesualdo; according to Robert Craft as quoted in Boosey's note, the result was not pure Gesualdo, but a fusion of the two composers. Noel Akchote's Gesualdo: Madrigals for Five Guitars was originally released in 2014 and adapts Book V madrigals for electric guitars. Bruno Mantovani's Time Stretch (on Gesualdo), 2006, is for orchestra.",
        ),
    ),
)


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, spaceAfter=8 * mm),
        "subtitle": ParagraphStyle("Subtitle", parent=sample["Normal"], fontName="Helvetica", fontSize=11.5, leading=16, textColor=colors.HexColor("#444444"), spaceAfter=8 * mm),
        "heading": ParagraphStyle("Heading", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17, spaceBefore=4 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.8, leading=14, spaceAfter=3 * mm),
        "small": ParagraphStyle("Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.5),
    }


def _program_table(styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[str | Paragraph]] = [["#", "Piece", "Source", "Time", "Function"]]
    for item in PROGRAM:
        rows.append(
            [
                str(item.number),
                Paragraph(f"{item.composer}, <i>{item.piece}</i>" if item.composer == "Carlo Gesualdo" else f"{item.composer}, <i>{item.piece}</i>", styles["small"]),
                item.source,
                item.duration,
                Paragraph(item.function, styles["small"]),
            ]
        )
    table = Table(rows, colWidths=[8 * mm, 53 * mm, 24 * mm, 15 * mm, 60 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECECEC")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.2),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (3, -1), "CENTER"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#777777")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#D0D0D0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _doc(path: Path, title: str, subtitle: str) -> SimpleDocTemplate:
    path.parent.mkdir(parents=True, exist_ok=True)
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="Francois Pachet",
    )


def _write_plan_markdown() -> None:
    lines = [
        "# Gesualdo / Take 6 - Evening Concert Plan",
        "",
    ]
    for heading, paragraphs in PLAN_SECTIONS[:2]:
        lines.extend([f"## {heading}", ""])
        for paragraph in paragraphs:
            lines.extend([paragraph, ""])
    lines.extend(["## Programme", ""])
    lines.append("| # | Piece | Original | Duration | Function |")
    lines.append("|---|---|---:|---:|---|")
    for item in PROGRAM:
        lines.append(f"| {item.number} | {item.composer}, *{item.piece}* | {item.source} | {item.duration} | {item.function} |")
    lines.append("")
    for heading, paragraphs in PLAN_SECTIONS[2:]:
        lines.extend([f"## {heading}", ""])
        for paragraph in paragraphs:
            lines.extend([paragraph, ""])
    PLAN_MD.write_text("\n".join(lines), encoding="utf-8")


def _write_vision_markdown() -> None:
    lines = ["# Vocal Harmony Without Voices", "", "## A Vision Paper Draft for the Gesualdo / Take 6 Quartet Project", ""]
    for heading, paragraphs in VISION_SECTIONS:
        lines.extend([f"## {heading}", ""])
        for paragraph in paragraphs:
            lines.extend([paragraph, ""])
    lines.extend(
        [
            "## Provisional Thesis",
            "",
            "Gesualdo's late madrigals pose a unique reduction problem because their most radical harmonies are not autonomous chordal objects but emergent products of chromatic voice-leading. Transforming five- and six-voice vocal music into string quartet therefore requires a method that preserves expressive motions, false relations, suspensions, and local harmonic shocks rather than merely maximizing vertical pitch coverage. In this sense, quartet reduction becomes a form of analysis: it reveals vocal harmony as a drama of lines under pressure.",
            "",
        ]
    )
    VISION_MD.write_text("\n".join(lines), encoding="utf-8")


def build_plan_pdf() -> Path:
    styles = _styles()
    story = [
        Paragraph("Gesualdo / Take 6", styles["title"]),
        Paragraph("Evening concert plan - vocal harmony without voices", styles["subtitle"]),
    ]
    for heading, paragraphs in PLAN_SECTIONS[:2]:
        story.append(Paragraph(heading, styles["heading"]))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["body"]))
    story.append(Paragraph("Programme", styles["heading"]))
    story.append(KeepTogether(_program_table(styles)))
    for heading, paragraphs in PLAN_SECTIONS[2:]:
        story.append(Paragraph(heading, styles["heading"]))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["body"]))
    _doc(PLAN_PDF, "Gesualdo / Take 6 Evening Concert Plan", "Vocal harmony without voices").build(story)
    return PLAN_PDF


def build_vision_pdf() -> Path:
    styles = _styles()
    story = [
        Paragraph("Vocal Harmony Without Voices", styles["title"]),
        Paragraph("A vision paper draft for the Gesualdo / Take 6 quartet project", styles["subtitle"]),
    ]
    for heading, paragraphs in VISION_SECTIONS:
        story.append(Paragraph(heading, styles["heading"]))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["body"]))
    story.append(Paragraph("Provisional Thesis", styles["heading"]))
    story.append(
        Paragraph(
            "Gesualdo's late madrigals pose a unique reduction problem because their most radical harmonies are not autonomous chordal objects but emergent products of chromatic voice-leading. Transforming five- and six-voice vocal music into string quartet therefore requires a method that preserves expressive motions, false relations, suspensions, and local harmonic shocks rather than merely maximizing vertical pitch coverage. In this sense, quartet reduction becomes a form of analysis: it reveals vocal harmony as a drama of lines under pressure.",
            styles["body"],
        )
    )
    _doc(VISION_PDF, "Vocal Harmony Without Voices", "Vision paper draft").build(story)
    return VISION_PDF


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    _write_plan_markdown()
    _write_vision_markdown()
    for path in (build_plan_pdf(), build_vision_pdf(), PLAN_MD, VISION_MD):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
