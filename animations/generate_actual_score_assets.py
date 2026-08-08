"""Generate engraved one-bar MusicXML/SVG assets for the Manim explanation.

The bar is intentionally small but fully notated: six independent source
parts, followed by three alternative string-quartet realizations.  Verovio is
used only at asset-generation time; the Manim scene consumes the checked-in
SVG files directly.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "actual_score"

SOURCE_LINES = {
    "Soprano": ["G5", "Ab5", "G5", "F#5"],
    "Alto I": ["Eb5", "F5", "E5", "Eb5"],
    "Alto II": ["C5", "Db5", "C5", "B4"],
    "Tenor I": ["G4", "Ab4", "G4", "F#4"],
    "Tenor II": ["Eb4", "F4", "E4", "Eb4"],
    "Bass": ["C3", "Bb2", "C3", "D3"],
}

SOURCE_PARTS = [
    ("Soprano", "S", "G", 2),
    ("Alto I", "A I", "G", 2),
    ("Alto II", "A II", "G", 2),
    ("Tenor I", "T I", "G", 2),
    ("Tenor II", "T II", "G", 2),
    ("Bass", "B", "F", 4),
]

QUARTET_PARTS = [
    ("Violin I", "Vln. I", "G", 2),
    ("Violin II", "Vln. II", "G", 2),
    ("Viola", "Vla.", "C", 3),
    ("Cello", "Vc.", "F", 4),
]

REDUCTIONS = {
    # The upper voices have been assigned in the wrong order.
    "crossing": ["Alto I", "Soprano", "Alto II", "Bass"],
    # The doubled tenor G is retained while the only inner C/Db/B line is lost.
    "harmonic_loss": ["Soprano", "Alto I", "Tenor I", "Bass"],
    # Outer voices are anchored and all distinct harmonic information survives.
    "accepted": ["Soprano", "Alto I", "Alto II", "Bass"],
}


def add_text(parent: ET.Element, tag: str, text: str, **attributes: str) -> ET.Element:
    node = ET.SubElement(parent, tag, attributes)
    node.text = text
    return node


def pitch_components(pitch: str) -> tuple[str, int | None, int]:
    match = re.fullmatch(r"([A-G])([b#]?)(\d)", pitch)
    if not match:
        raise ValueError(f"Unsupported pitch: {pitch}")
    step, accidental, octave = match.groups()
    alter = {"": None, "b": -1, "#": 1}[accidental]
    return step, alter, int(octave)


def build_score(
    path: Path,
    parts: list[tuple[str, str, str, int]],
    note_lines: list[list[str]],
) -> None:
    score = ET.Element("score-partwise", version="4.0")
    identification = ET.SubElement(score, "identification")
    encoding = ET.SubElement(identification, "encoding")
    add_text(encoding, "software", "Gesualdo reduction Manim asset generator")

    part_list = ET.SubElement(score, "part-list")
    group_start = ET.SubElement(part_list, "part-group", type="start", number="1")
    add_text(group_start, "group-symbol", "bracket")
    add_text(group_start, "group-barline", "yes")
    for index, (name, abbreviation, _, _) in enumerate(parts, start=1):
        score_part = ET.SubElement(part_list, "score-part", id=f"P{index}")
        add_text(score_part, "part-name", name)
        add_text(score_part, "part-abbreviation", abbreviation)
    ET.SubElement(part_list, "part-group", type="stop", number="1")

    for index, ((_, _, clef_sign, clef_line), pitches) in enumerate(
        zip(parts, note_lines), start=1
    ):
        part = ET.SubElement(score, "part", id=f"P{index}")
        measure = ET.SubElement(part, "measure", number="1")
        attributes = ET.SubElement(measure, "attributes")
        add_text(attributes, "divisions", "1")
        key = ET.SubElement(attributes, "key")
        add_text(key, "fifths", "-3")
        time = ET.SubElement(attributes, "time")
        add_text(time, "beats", "4")
        add_text(time, "beat-type", "4")
        clef = ET.SubElement(attributes, "clef")
        add_text(clef, "sign", clef_sign)
        add_text(clef, "line", str(clef_line))

        for pitch in pitches:
            step, alter, octave = pitch_components(pitch)
            note = ET.SubElement(measure, "note")
            pitch_node = ET.SubElement(note, "pitch")
            add_text(pitch_node, "step", step)
            if alter is not None:
                add_text(pitch_node, "alter", str(alter))
            add_text(pitch_node, "octave", str(octave))
            add_text(note, "duration", "1")
            add_text(note, "voice", "1")
            add_text(note, "type", "quarter")

        barline = ET.SubElement(measure, "barline", location="right")
        add_text(barline, "bar-style", "light-heavy")

    tree = ET.ElementTree(score)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def engrave(musicxml: Path, svg: Path) -> None:
    verovio = shutil.which("verovio")
    if not verovio:
        raise FileNotFoundError("verovio is required to regenerate score SVGs")
    subprocess.run(
        [
            verovio,
            "--condense",
            "none",
            "--header",
            "none",
            "--footer",
            "none",
            "--no-justification",
            "--adjust-page-height",
            "--page-width",
            "1500",
            "--page-height",
            "1800",
            "--page-margin-top",
            "25",
            "--page-margin-bottom",
            "25",
            "--page-margin-left",
            "25",
            "--page-margin-right",
            "25",
            "--scale",
            "34",
            "-o",
            str(svg),
            str(musicxml),
        ],
        check=True,
    )


def rasterize(svg: Path, png: Path) -> None:
    """Render SVG faithfully, then make dark ink light on transparency."""

    from PIL import Image, ImageChops, ImageOps

    with tempfile.TemporaryDirectory(prefix="gesualdo-score-") as temp_dir:
        temp = Path(temp_dir)
        preview = temp / f"{svg.name}.png"
        qlmanage = shutil.which("qlmanage")
        if not qlmanage:
            raise FileNotFoundError(
                "qlmanage is required for SVG rasterization on this macOS setup"
            )
        subprocess.run(
            [qlmanage, "-t", "-s", "1800", "-o", str(temp), str(svg)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        source = Image.open(preview).convert("RGBA")
        grey = ImageOps.grayscale(source)
        ink = ImageOps.invert(grey)
        ink = ImageChops.multiply(ink, source.getchannel("A"))
        bbox = ink.point(lambda value: 255 if value > 8 else 0).getbbox()
        if bbox is None:
            raise RuntimeError(f"No engraved content found in {svg}")

        rgba = Image.new("RGBA", source.size, (242, 244, 248, 0))
        rgba.putalpha(ink)
        cropped = rgba.crop(bbox)
        padded = ImageOps.expand(cropped, border=28, fill=(242, 244, 248, 0))
        padded.save(png)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    source_xml = ASSET_DIR / "source.musicxml"
    build_score(source_xml, SOURCE_PARTS, [SOURCE_LINES[name] for name, *_ in SOURCE_PARTS])
    source_svg = ASSET_DIR / "source.svg"
    engrave(source_xml, source_svg)
    rasterize(source_svg, ASSET_DIR / "source.png")

    for name, source_names in REDUCTIONS.items():
        musicxml = ASSET_DIR / f"{name}.musicxml"
        build_score(musicxml, QUARTET_PARTS, [SOURCE_LINES[item] for item in source_names])
        svg = ASSET_DIR / f"{name}.svg"
        engrave(musicxml, svg)
        rasterize(svg, ASSET_DIR / f"{name}.png")


if __name__ == "__main__":
    main()
