# Gesualdo Reduction

Experimental work on reducing Gesualdo madrigals into playable instrumental
material.

This is a standalone Python project for reducing Gesualdo madrigal MIDI and
MusicXML into playable MusicXML for configurable string ensembles and piano.
The checked-in data is organized by source: Kunst der Fuge books 4 and 6 under
`data/kdf/`, and the broader CPDL vocal catalogue under `data/cpdl/`.

## Current Results

The current reduction corpus is based on the Kunst der Fuge Gesualdo madrigal
MIDIs from books 4 and 6. A broader CPDL source corpus is also kept for future
experiments over the sacred and secular vocal catalogue.

| Output | Path | Count | Notes |
| --- | --- | ---: | --- |
| KdF book 4 sources | `data/kdf/book4/sources/` | 14 | Kunst der Fuge MIDI sources, indexed by `data/kdf/manifest.tsv`. |
| KdF book 6 sources | `data/kdf/book6/sources/` | 23 | Kunst der Fuge MIDI sources, indexed by `data/kdf/manifest.tsv`. |
| KdF string quartet reductions | `data/kdf/book*/reductions/string_quartet/` | 37 | Current quartet MusicXML book, generated with source-voice enrichment, editorial harmony, and editorial missing thirds. |
| KdF quartet MP3 renders | `data/kdf/book*/renders/string_quartet_mp3/` | 37 | MP3 audio exported from the current enriched MusicXML book with MuseScore 4 string sounds. |
| CPDL source files | `data/cpdl/{4,5,6,7}-voices/sources/` | 397 | MusicXML/MIDI files linked from CPDL's Carlo Gesualdo vocal work pages, indexed by `data/cpdl/manifest.tsv`. |
| CPDL 5-voice string quartet reductions | `data/cpdl/5-voices/reductions/string_quartet/` | 123 | Supported five-voice-to-string-quartet batch, indexed by `report.tsv`. |
| CPDL 5-voice string quartet MP3 renders | `data/cpdl/5-voices/renders/string_quartet_mp3/` | 123 | MP3 audio exported from the CPDL five-voice string quartet reductions with MuseScore 4. |
| CPDL 5-voice quartet plus viole reductions | `data/cpdl/5-voices/reductions/string_quartet_plus_viole/` | 122 | Existing five-instrument reducer restored for CPDL five-voice sources, indexed by `report.tsv`. |
| CPDL 5-voice quartet plus viole MP3 renders | `data/cpdl/5-voices/renders/string_quartet_plus_viole_mp3/` | 122 | MP3 audio exported from the CPDL five-instrument reductions with MuseScore 4. |
| CPDL 6-voice string quartet reductions | `data/cpdl/6-voices/reductions/string_quartet/` | 34 | Dedicated six-voice-to-string-quartet batch using the separate six-voice compression policy, indexed by `report.tsv`. |
| CPDL 6-voice string quartet MP3 renders | `data/cpdl/6-voices/renders/string_quartet_mp3/` | 34 | MP3 audio exported from the CPDL six-voice string quartet reductions with MuseScore 4. |
| CPDL 7-voice sources | `data/cpdl/7-voices/sources/` | 2 | Sources only; seven-to-four reduction is out of scope for the current reducer. |
| Take 6 double-stop quartet reductions | `data/take6/reductions/string_quartet_double_stops/` | 10 | Preferred Take 6 six-voice-to-quartet MusicXML batch, with conservative source-derived double-stops and cleaned display titles. |
| Take 6 double-stop PDF renders | `data/take6/renders/string_quartet_double_stops_pdf/` | 10 | Clean MuseScore PDF exports generated from the Take 6 MusicXML reductions. |
| Take 6 double-stop MP3 renders | `data/take6/renders/string_quartet_double_stops_mp3/` | 10 | MuseScore MP3 exports generated from the Take 6 MusicXML reductions. |
| Editorial dynamics examples | `data/kdf/examples/dynamic/` | 3 | MusicXML and MuseScore MP3 examples with generated score dynamics and hairpins. |
| Quartet enrichment examples | `data/kdf/examples/enrichment/` | 4 variants | Side-by-side MusicXML/MP3 renders for plain, source-enriched, source-plus-harmony, and source-plus-thirds quartet reductions. |

The CPDL corpus was collected from ChoralWiki's Carlo Gesualdo composer page.
It includes `.mxl`, `.mid`, and `.midi` files, with source URLs and original
filenames recorded in `data/cpdl/manifest.tsv`. Pages with no direct
MusicXML/MIDI links at collection time are listed in `data/cpdl/errors.tsv`.
The first CPDL reduction batch covers the five-voice sacred and secular pages:
123 works reduced successfully, and 7 source-overlap failures are recorded in
`data/cpdl/5-voices/reductions/string_quartet/report.tsv`. The six-voice CPDL
batch uses a separate `six_voice_quartet` reducer mode and currently reduces
all 34 six-voice work pages successfully.

The retained MusicXML batch completed successfully according to its report TSV:

- `data/kdf/reductions/string_quartet_report.tsv`

The MP3 batches contain one audio file per supported reduction. The files are
44.1 kHz MP3s exported by MuseScore 4 and are intended to be usable directly by
a static listening page.

Global transposition is now key-signature aware. The reducer first finds the
best range/register transposition, then allows only near-equivalent candidates
to win when they substantially reduce the printed number of sharps/flats. The
current checked-in corpus includes 78 cleaner-key updates applied with the
`0.05` tessitura tolerance. A fresh audit reports `0 attention` cleaner-key
rows; comparison snapshots are generated by
`scripts/apply_key_signature_transposition_updates.py` and refreshed through
`scripts/render_updated_mp3_from_manifest.py`.

## Editorial Dynamics

The Kunst der Fuge MIDI sources do not contain printed dynamics, and their note
velocities are flat. The quartet reducer therefore adds an optional editorial
score-dynamics layer after the notes have been reduced and measured. This pass
does not alter microtiming or MIDI note velocities; it emits visible MusicXML
`<dynamics>` and hairpin `<wedge>` directions that MuseScore can interpret for
notation and playback.

The dynamics pass estimates a coarse bar-level energy contour from the reduced
score using active part count, attack density, average register, and registral
span. It maps the local contour to `p`, `mp`, `mf`, and `f`, then adds short
crescendo and diminuendo wedges around changing regions. By default, phrase
windows are four bars and hairpins are capped to two bars so the generated
marks stay locally readable rather than becoming long page-level swells.

This behavior is enabled by default for ensemble reductions and can be tuned or
disabled through `ReductionConfig`:

```python
ReductionConfig(
    add_editorial_dynamics=True,
    dynamic_phrase_bars=4,
    dynamic_hairpin_bars=2,
)
```

Three generated MusicXML/MP3 examples are kept under
`data/kdf/examples/dynamic/` for quick listening and notation review.

## Quartet Enrichment

The basic quartet reduction stays conservative: it chooses real source notes,
avoids duplicate pitch classes where possible, and emits only the material
needed for a playable four-part score. Sparse madrigal textures can therefore
produce quartet bars with only two or three active strings.

Optional enrichment modes can be enabled independently for comparison:

```python
build_quartet_score(
    score,
    preserve_active_voice_count=True,
    add_editorial_harmony=True,
    add_editorial_thirds=True,
)
```

`preserve_active_voice_count` tries to keep distinct active source voices when
the original madrigal has more voices sounding than the plain quartet reduction
selected. It remains source-traceable: added notes are copied from real source
events. To avoid thin octave/unison pickups, it does not add an extra duplicate
pitch class when the whole active source sonority contains only one pitch
class.

`add_editorial_harmony` can fill idle strings with marked editorial support
tones drawn from active source pitches. These generated events are explicitly
tagged in the internal note provenance.

`add_editorial_thirds` is a narrower editorial layer on top of harmony filling.
When a sounding sonority implies a root-fifth shell but contains no third, it
can invent the missing major or minor third, preferring the nearest third that
appears later in the source when possible. This is useful for cases where
doubling a fifth or octave makes a four-string texture sound skinny.

## Take 6 Close-Harmony Reduction

Take 6-style sources are handled by a separate six-voice quartet entry point:

```python
build_take6_quartet_score(score)
reduce_take6_to_quartet("source.mxl", out_path="take6_quartet.musicxml")
```

It still writes a four-part string quartet, so dense sonorities with five or
six pitch classes must be compressed. The Take 6 variant keeps the outer source
voices as soprano/bass anchors, then changes the inner-choice priority: when
the source sonority is dense, it favors thirds, sevenths, altered tones, and
ninth/thirteenth colors relative to the bass over redundant roots or fifths.
It does not enable editorial missing-thirds by default, because jazz and close
harmony voicings should not be completed with a Renaissance triadic rule.
With `add_source_double_stops=True`, the reducer can add conservative playable
double-stops from real source notes. It normally uses them for missing pitch
classes; on long homorhythmic attacks it may also preserve source octave
doublings so a sustained six-voice chord does not collapse unnecessarily.
File-based Take 6 reductions also clean the displayed source title and stamp
the score composer as `Take 6, arrangement F. Pachet and AI`.
The detailed editorial rules are documented in
`docs/take6_reduction_rules.md`.

Batch reduction for local source files:

```bash
uv run --extra notation python scripts/reduce_take6.py \
  "data/take6/44 Spread love.mid" \
  "data/take6/46 Gold Mine.mid" \
  "data/take6/47 A quiet place, originalrevu.mid" \
  "data/take6/47 He never sleeps.mid" \
  "data/take6/48 David et Goliath.mid" \
  "data/take6/48 Get away Jordan.mid" \
  "data/take6/50 If we ever.mid" \
  "data/take6/51 Hark herald.mid" \
  "data/take6/53 I'm on my way.mid" \
  "data/take6/ComeUntoMe.mid" \
  --input-dir data/take6/none \
  --force
```

For Take 6 material, the double-stop variant is the current output. The active
set intentionally excludes `data/take6/A_quiet_place_joined.mid`, which is an
alternate/intermediate source for `A Quiet Place`.

The Take 6 `reductions/` and `renders/` folders are intentionally separate:
`data/take6/reductions/string_quartet_double_stops/` contains the canonical
MusicXML files and `report.tsv`, while
`data/take6/renders/string_quartet_double_stops_pdf/` and
`data/take6/renders/string_quartet_double_stops_mp3/` contain derived PDF and
MP3 exports used by the web review page and compiled conductor PDF.

The comparison set for `Gia piansi nel dolore` is kept in
`data/kdf/examples/enrichment/` as MusicXML and MuseScore MP3:

- `*_quartet_plain_current.*`
- `*_quartet_source_enriched.*`
- `*_quartet_source_plus_harmony.*`
- `*_quartet_source_plus_thirds.*`

A more detailed human-readable description of the current reduction rules is
kept in `docs/reduction_rules.md`.

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
uv run gesualdo-analyze data/kdf/book6/sources/book6_22_gia_piansi_nel_dolore.mid
```

The current analysis reports voice ranges, a rough global transposition plan,
and dense sonorities found through MusES chordification.
Reduction entry points choose a target-aware global transposition by default;
among near-equivalent range/register candidates, they prefer simpler printed
key signatures.  Pass an explicit `semitones` value to force a fixed
transposition such as the older hand-tuned `-9`.

Generate the current rhythm-first quartet reduction:

```bash
uv run python experiments/reduction.py
```

This writes:

```text
data/kdf/book6/reductions/string_quartet/book6_22_gia_piansi_nel_dolore.musicxml
```

Refresh the CPDL Gesualdo source corpus:

```bash
python scripts/download_cpdl_gesualdo.py --output-dir data/cpdl --workers 2
```

The downloader uses the public CPDL mirror and falls back to MediaWiki raw
pages for work pages that do not render cleanly.

Generate supported CPDL five-voice string quartet reductions:

```bash
uv run --extra notation python scripts/reduce_cpdl_5_voice.py --target string_quartet --force
```

This selects five-part sources from the CPDL manifest, prefers MusicXML/MXL
over MIDI when several editions are available, and writes one four-part
string-quartet MusicXML reduction plus a TSV report row per work page.

Generate the restored five-voice string quartet plus viole d'amour reductions:

```bash
uv run --extra notation python scripts/reduce_cpdl_5_voice.py --target string_quartet_plus_viole --force
```

Generate supported CPDL six-voice string quartet reductions:

```bash
uv run --extra notation python scripts/reduce_cpdl_6_voice.py --force
```

This uses the dedicated six-voice compression policy rather than the five-voice
batch path. It requires exactly six source parts, pins the outer source voices
to Violin I and Cello, and compresses the four middle voices into the remaining
quartet texture with source-traceable enrichment.

Generate Take 6-tuned six-voice reductions from local sources:

```bash
uv run --extra notation python scripts/reduce_take6.py \
  "data/take6/44 Spread love.mid" \
  "data/take6/46 Gold Mine.mid" \
  "data/take6/47 A quiet place, originalrevu.mid" \
  "data/take6/47 He never sleeps.mid" \
  "data/take6/48 David et Goliath.mid" \
  "data/take6/48 Get away Jordan.mid" \
  "data/take6/50 If we ever.mid" \
  "data/take6/51 Hark herald.mid" \
  "data/take6/53 I'm on my way.mid" \
  "data/take6/ComeUntoMe.mid" \
  --input-dir data/take6/none \
  --force
```

This expects exactly six source parts. It uses the same four-part quartet target
as the CPDL six-voice reducer, but changes the dense-sonority choice rule to
prefer jazz guide tones and color tones over redundant roots/fifths.

Audit and apply cleaner-key transposition updates:

```bash
uv run --extra notation python scripts/audit_transposition_key_signatures.py
uv run --extra notation python scripts/apply_key_signature_transposition_updates.py
uv run --extra notation python scripts/render_updated_mp3_from_manifest.py
```

The apply step updates only strong cleaner-key wins by default: audit rows whose
cleaner candidate improves printed key-signature burden substantially while keeping
the tessitura-score delta at or below `0.05`. It snapshots the previous and
updated MusicXML files under `outputs/transposition_comparison/obvious_key_signature/`.
The render step refreshes only the MP3 files listed in that generated manifest
and keeps old/new MP3 snapshots beside the MusicXML comparison. Re-run the audit
after applying; the current corpus is clean at this threshold.

Render clean conductor-review PDFs for the current Gesualdo and Take 6
reduction reports:

```bash
uv run --extra notation python scripts/render_review_pdfs.py --mode clean
```

The PDF renderer uses MuseScore 4 and runs a shared notation cleanup pass before
export. Clean mode suppresses editorial dynamics/hairpins, hides redundant
naturals, adds final barlines, and inserts cello clef changes for sustained
high passages. Use `--job take6:string_quartet_double_stops` to render only
the Take 6 reductions. The active review set currently contains 326 PDFs. Eight
CPDL five-voice PDFs use the renderer's MIDI-to-PDF fallback because MuseScore
does not complete direct MusicXML PDF export for those files; the fallback rows
are marked in each `review_pdf_report.tsv`.

Build compiled conductor-review books from the generated score PDFs:

```bash
python scripts/build_director_review_books.py
```

The director pack is written under `output/pdf/quartet_director/` and currently
contains:

- `gesualdo_5_voice_string_quartet_reductions.pdf`
- `gesualdo_6_voice_string_quartet_reductions.pdf`
- `take6_string_quartet_double_stops_reductions.pdf`

This builder requires `pypdf` and `reportlab`; the Codex PDF runtime already
provides them.

Older fixed-transposition single-piece `Gia piansi` renders are kept under
`data/kdf/archive/legacy_gia_pensi_fixed_transposition/`.
The previous GitHub Pages full-book MusicXML/MP3 generation is preserved under
`data/kdf/archive/kdf_reductions_previous_web_generation_2026-06-07/`.
The default, non-enriched full-book regeneration from the same date is
preserved under
`data/kdf/archive/kdf_reductions_default_regeneration_2026-06-07/`.
The pre-cleaner-key generated corpus snapshot from 2026-06-21 is preserved under
`data/archive/key_signature_optimization_pre_2026-06-21/`.

## Reduction AI

The reduction algorithm is a symbolic AI system rather than a trained neural
network. It does not learn from examples or invent new melodic material. Its
intelligence is encoded as score analysis, constraint solving, search, and
cost-based assignment over the source musical events.

The musical problem is best understood as a constrained multi-objective
optimization problem. The target score should preserve as much of the original
madrigal as possible while also becoming idiomatic for the chosen instruments.
The objectives are sometimes aligned and sometimes in tension:

- optimize each instrument's sweet spot and playable range;
- optimize harmonic coverage, especially when a target voice is available and
  the source sonority contains an important missing pitch class;
- optimize faithfulness to the original, notably rhythmic placement, source
  attacks, durations, register contour, and traceability to real source notes;
- optimize voice continuity, avoiding isolated singleton notes that appear only
  because a voice happened to be idle for one chord;
- minimize voice crossing, abrupt octave displacement, unnecessary doubling,
  and unstable reassignment of similar source material between instruments.

The current implementation approximates this formulation with deterministic
symbolic search and local cost functions. It does not yet solve one global
integer program over the whole madrigal, but the code is organized around the
same ingredients: hard validity constraints, soft musical objectives, and
source-event provenance for every emitted note.

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
long structural tones matter more than brief passing tones.  If another
candidate is within `0.05` of the best range/register score, the reducer may
choose it instead when it substantially lowers the duration-weighted printed
key-signature burden, measured as the average absolute number of sharps/flats.

For the main string quartet reduction, the reducer identifies the highest and
lowest source voices by median pitch and preserves them as Violin I and Cello.
The middle voices are then reduced into Violin II and Viola. At each source
onset, it chooses real source-note events that add pitch classes not already
covered by the outer voices, favors fresh attacks over tied continuations,
prefers tones that widen the sonority from the outer anchors, and avoids
duplicating pitch classes. When an outer voice is temporarily idle, it may
borrow a nearby uncovered source line to improve harmonic coverage, but only
when doing so forms a musically continuous gesture rather than a stray isolated
note. Selected events are assigned to the available instruments by minimizing a
cost that combines register fit, melodic continuity, range displacement, and
voice-order stability.

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
- `docs/reduction_rules.md`: human-readable description of the current
  reduction and enrichment rules.
- `docs/development_log.md`: chronological log of the main musical and
  technical improvements, useful for presentations and progress summaries.
- `docs/quartet_director_feedback_plan.md`: action plan for addressing
  professional quartet feedback, including PDF export, spelling, clefs, and
  review workflow.
- `docs/cpdl_six_voice_reduction_plan.md`: implementation plan for a dedicated
  CPDL six-voice reduction engine.
- `scripts/download_cpdl_gesualdo.py`: CPDL Gesualdo MusicXML/MIDI collector.
- `scripts/reduce_cpdl_5_voice.py`: supported CPDL five-voice batch reduction
  script.
- `scripts/reduce_cpdl_6_voice.py`: supported CPDL six-voice batch reduction
  script using the separate six-voice quartet compression policy.
- `data/cpdl/`: downloaded CPDL source files split by voice count, plus the
  manifest, errors, and supported five- and six-voice reductions.
- `data/kdf/`: Kunst der Fuge book 4 and book 6 sources, quartet reductions,
  MP3 renders, examples, reports, and archived legacy artifacts.
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
