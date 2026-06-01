# Gesualdo Reduction

Experimental work on reducing Gesualdo madrigals into playable instrumental
material.

This is a standalone Python project for reducing Gesualdo madrigal MIDI into
MusicXML for configurable string ensembles and piano. It includes a local
`data/gesualdo/` folder with the current source corpus, generated reductions,
and MuseScore MP3 renders, so the examples do not depend on a sibling MusES
checkout for score data.

## Current Results

The current corpus is based on the Kunst der Fuge Gesualdo madrigal MIDIs
collected in `data/gesualdo/kdf_madrigals/`.

| Output | Path | Count | Notes |
| --- | --- | ---: | --- |
| Original madrigal MIDIs | `data/gesualdo/kdf_madrigals/` | 37 | Source material from books IV and VI, indexed by `kdf_madrigals_manifest.tsv`. |
| String quartet reductions | `data/gesualdo/kdf_reductions/` | 37 | Rhythm-first MusicXML for Violin I, Violin II, Viola, and Violoncello. |
| MuseScore quartet MP3 renders | `data/gesualdo/kdf_reductions_mp3/` | 37 | MP3 audio exported from the string quartet MusicXML reductions with MuseScore 4 string sounds. |

The retained MusicXML batch completed successfully according to its report TSV:

- `data/gesualdo/kdf_reductions_report.tsv`

The MP3 batch contains one audio file per string quartet reduction. The files
are 44.1 kHz MP3s at 128 kbps; the largest file is about 5.3 MB. These files
are intended to be usable directly by a static listening page.

## Conductor Evaluation Page

A static review page for quartet conductors lives in `docs/index.html`. It
provides a searchable listening catalog, direct MP3 and MusicXML links,
piece-level ratings, shortlist marking, local notes, and CSV export for review
sessions.

The page can be hosted directly from this GitHub repository with GitHub Pages.
In the repository settings, choose Pages, deploy from the `main` branch, and set
the publishing folder to `/docs`. The root `index.html` also redirects to the
same page if Pages is configured from the repository root instead.

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

## Reduction AI

The reduction algorithm is a symbolic AI system rather than a trained neural
network. It does not learn from examples or invent new melodic material. Its
intelligence is encoded as score analysis, constraint solving, search, and
cost-based assignment over the source musical events.

The reducer first parses the madrigal into exact source events: note/rest
starts, durations, source part IDs, pitch classes, ties, bar boundaries, time
signatures, key signatures, and voice ranges. Output notes are copied from real
source note events and retain source-event metadata; generated material is
limited to rests needed to fill measures.

A global transposition is chosen automatically unless one is forced. The system
searches candidate transpositions from `-18` to `+6` semitones and scores each
candidate against the target ensemble. The score favors playable ranges,
instrumental preferred registers, small octave displacement, and shorter global
movement from the source pitch level. Note durations weight the scoring, so
long structural tones matter more than brief passing tones.

For the main string quartet reduction, the reducer identifies the highest and
lowest source voices by median pitch and preserves them as Violin I and Cello.
The middle voices are then reduced into Violin II and Viola. At each source
onset, it chooses real middle-note events that add pitch classes not already
covered by the outer voices, favors fresh attacks over tied continuations,
prefers tones that widen the sonority from the outer anchors, and avoids
duplicating pitch classes. Selected events are assigned to the available inner
instruments by minimizing a cost that combines register fit, melodic continuity,
range displacement, and voice-order stability.

For five-part outputs, `QUARTET_PLUS_VIOLE` adds a `Viole d'amour` part. When
the source and target have the same number of voices, the basic policy maps
voices one-to-one by register. `SweetSpotAssignmentPolicy` adds another symbolic
optimization layer: it can permute equal-count inner voices while preserving the
outer voices, then chooses the assignment with the best instrumental register
fit, low crossing penalty, and low order-change penalty. It can also move notes
by octave into each instrument's preferred register while preserving pitch
class.

The piano reduction uses the same source-event and transposition machinery, but
maps upper source voices to independent right-hand notation voices and lower
source voices to independent left-hand notation voices.

Every generated score is measured and validated after construction. Validation
checks that each part has the expected bar count, no gaps or overlaps, no
overfull measures, and no output note without a source trace. That makes the
system deliberately conservative: it aims for playable, inspectable reductions
whose decisions can be traced back to the original madrigal.

## Layout

- `src/gesualdo_reduction/analysis.py`: MusES-based analysis helpers and CLI.
- `src/gesualdo_reduction/reduction.py`: rhythm-first MusicXML reduction,
  ensemble profiles, and assignment policies.
- `data/gesualdo/kdf_madrigals/`: current Kunst der Fuge MIDI sources.
- `data/gesualdo/kdf_reductions/`: current string quartet MusicXML reductions.
- `data/gesualdo/kdf_reductions_mp3/`: MuseScore MP3 renders of the quartet
  reductions.
- `data/gesualdo/`: local Gesualdo MIDI, generated reductions, audio, and
  archived legacy artifacts.
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
