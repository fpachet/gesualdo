"""Small MusicXML compatibility post-processors."""

from __future__ import annotations

import re
from pathlib import Path


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
