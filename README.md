# Gesualdo Reduction

Experimental work on reducing six-voice madrigals into string-quartet material.

This is a standalone Python project that uses MusES for temporal musical
objects, MIDI IO, pitch utilities, and chordification. It lives in the MusES
repository for now, but it has its own package metadata, tests, CLI entrypoint,
and dependency boundary.

## Install

From this directory:

```bash
uv sync
uv run pytest -q
```

The `pyproject.toml` uses the parent checkout of MusES as an editable local
dependency via `tool.uv.sources`.

For non-uv workflows, install MusES first from the repository root, then install
this project:

```bash
python -m pip install -e ../..
python -m pip install -e .
```

## Run

Analyze a madrigal MIDI file:

```bash
uv run gesualdo-analyze ../muses/data/gesualdo/gesualdo_vi_libro_madrigali_22.mid
```

The current analysis reports voice ranges, a rough global transposition plan,
and dense sonorities found through MusES chordification.

## Layout

- `src/gesualdo_reduction/analysis.py`: MusES-based analysis helpers and CLI.
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
