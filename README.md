# Gesualdo Reduction

Experimental work on reducing six-voice madrigals into string-quartet material.

This is a standalone Python project for reducing Gesualdo madrigal MIDI into
string-quartet MusicXML. It includes a local `data/gesualdo/` folder so the
default examples do not depend on a sibling MusES checkout for score data.

## Install

From this directory:

```bash
uv sync --extra notation
uv run pytest -q
```

The `pyproject.toml` still uses the parent checkout of MusES as an editable
local dependency for the analysis helpers via `tool.uv.sources`.

For non-uv workflows, install MusES first from the repository root, then install
this project:

```bash
python -m pip install -e ../..
python -m pip install -e .
```

## Run

Analyze a madrigal MIDI file:

```bash
uv run gesualdo-analyze data/gesualdo/gesualdo_vi_libro_madrigali_22.mid
```

The current analysis reports voice ranges, a rough global transposition plan,
and dense sonorities found through MusES chordification.

Generate the current rhythm-first quartet reduction:

```bash
uv run python experiments/reduction.py
```

This writes:

```text
data/gesualdo/gesualdo_quartet_rhythm_first.musicxml
```

## Layout

- `src/gesualdo_reduction/analysis.py`: MusES-based analysis helpers and CLI.
- `src/gesualdo_reduction/reduction.py`: rhythm-first MusicXML reduction.
- `data/gesualdo/`: local Gesualdo MIDI/reference data.
- `tests/`: project-level tests.
- `experiments/`: preserved exploratory scripts.

## Optional Notation Experiments

Some preserved experiments still import `music21` for score parsing, notation
streams, and attempted MusicXML output. Install them only when needed:

```bash
uv sync --extra notation
```

MusicXML writing through `music21` has not been reliable enough to treat as a
MusES feature. Future work should separate the reduction model from notation
export and use MusES for the MIDI/object layer where possible.
