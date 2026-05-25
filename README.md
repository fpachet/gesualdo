# Gesualdo Reduction

Experimental work on reducing Gesualdo madrigals into string-ensemble material.

This is a standalone Python project for reducing Gesualdo madrigal MIDI into
MusicXML for configurable string ensembles. It includes a local `data/gesualdo/`
folder so the
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
uv run gesualdo-analyze data/gesualdo/kdf_madrigals/gesualdo_vi_libro_madrigali_22_\(c\)icking-archive.mid
```

The current analysis reports voice ranges, a rough global transposition plan,
and dense sonorities found through MusES chordification.
Reduction entry points choose a target-aware global transposition by default;
pass an explicit `semitones` value to force a fixed transposition such as the
older hand-tuned `-9`.

Generate the current rhythm-first quartet reduction:

```bash
uv run python experiments/reduction.py
```

This writes:

```text
data/gesualdo/kdf_reductions/gesualdo_vi_libro_madrigali_22_(c)icking-archive_quartet_rhythm_first.musicxml
```

Older fixed-transposition single-piece `Gia piansi` renders are kept under
`data/gesualdo/archive/legacy_gia_pensi_fixed_transposition/`.

The reduction core is profile-based. The default preset is `STRING_QUARTET`;
`QUARTET_PLUS_VIOLE` adds a fifth `Viole d'amour` part and can either map five
source voices one-to-one by register or reduce six voices into the three inner
instrumental parts.
`SweetSpotAssignmentPolicy` keeps the outer voices fixed, can remap equal-count
inner voices when another assignment better fits the target instruments, and
can place notes by octave in each instrument's preferred register.
`build_piano_score`/`reduce_to_piano` create a two-staff piano reduction: upper
voices are kept as independent right-hand notation voices and lower voices as
independent left-hand notation voices.

## Layout

- `src/gesualdo_reduction/analysis.py`: MusES-based analysis helpers and CLI.
- `src/gesualdo_reduction/reduction.py`: rhythm-first MusicXML reduction,
  ensemble profiles, and assignment policies.
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
