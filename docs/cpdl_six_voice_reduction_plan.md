# CPDL Six-Voice Reduction Plan

The new CPDL corpus contains 34 six-voice work pages with downloaded files:
32 sacred works and 2 secular works. It also contains one sacred seven-voice
page. The five-voice batch now uses the existing `QUARTET_PLUS_VIOLE` profile,
which works well when the source and target both have five parts. Six voices
need a separate engine because the musical decision is no longer just register
assignment: the reducer must either preserve all six contrapuntal strands or
make an explicit, traceable decision about which strand to merge or omit.

## Goal

Add a dedicated CPDL six-voice reduction path without weakening the current
four- and five-part reducers.

The extension should support two modes:

1. Six-to-six preservation mode: map six vocal parts to a six-instrument
   ensemble, preserving outer voices and optimizing the four inner voices.
2. Six-to-five compression mode: reduce six source voices into the existing
   `String Quartet + Viole d'amour` ensemble with an explicit omission/merge
   policy, rather than relying on the current generic voice-count fallback.

## Recommended Engine Shape

Add a new public entry point beside the current five-part helpers:

```python
reduce_to_six_voice_ensemble(...)
reduce_six_to_quartet_plus_viole(...)
```

Internally, keep the same architecture already used by
`reduce_to_quartet_plus_viole_sweetspot`:

- `EnsembleProfile` defines the target instruments and register preferences.
- `AssignmentPolicy` chooses which source events are emitted by each target.
- `ReductionConfig` keeps validation, range enforcement, and transposition
  behavior shared with the existing reducer.

## Ensemble Profiles

Start with two profiles.

`STRING_SEXTET_GESUALDO`:

- Violin I
- Violin II
- Viole d'amour
- Viola I
- Viola II
- Violoncello

This keeps the current viole d'amour color while adding a second viola for the
extra inner contrapuntal strand. The outer voices remain top violin and cello;
the four middle targets can be assigned by optimization.

`QUARTET_PLUS_VIOLE` six-to-five mode:

- reuse the existing five-part profile;
- preserve top and bottom whenever possible;
- compress only the middle four source voices into the three middle target
  instruments.

## Assignment Policy

Create `SixVoiceSweetSpotAssignmentPolicy`.

For six-to-six:

- rank source voices by median sounding pitch;
- pin the highest source voice to Violin I and the lowest to Violoncello;
- evaluate all permutations of the four inner source voices over the four
  inner targets;
- score each permutation by instrumental sweet spot, range displacement,
  crossing penalty, source-order stability, and continuity with the previous
  assignment window.

For six-to-five:

- pin outer voices first, as above;
- evaluate the four middle source voices against three middle targets;
- allow one middle source voice to be temporarily omitted or merged per local
  window;
- prefer omitting material that duplicates pitch classes already present,
  sustains through the window, has low rhythmic salience, or is registrally
  awkward for the available targets;
- penalize omissions that remove the only third/fifth of a sonority, remove a
  new attack, break a melodic line at a leap, or erase a dissonance-resolution
  pair.

The local window can start at the existing event-slice level, but the engine
should also keep a bar-level or phrase-level continuity memory so the omitted
voice does not jump unpredictably at every chord.

## Source Preflight

Before reducing the six-voice batch, add a diagnostics pass over CPDL sources:

- select sections `Sacred works for six voices` and `Secular works for six
  voices`;
- prefer `.mxl`, then `.musicxml`/`.xml`, then MIDI;
- parse every candidate and record part count;
- reject editions with piano reductions, editorial extra staves, or non-vocal
  aggregate parts unless a clean six-part candidate is also available;
- detect overlapping notes inside a single source part and report their measure
  numbers before reduction.

This preflight should write a TSV before any MusicXML generation, so bad source
editions are separated from actual reduction failures.

## Batch Script

Add `scripts/reduce_cpdl_six_voice.py` with the same operational shape as the
five-voice script:

```bash
uv run --extra notation python scripts/reduce_cpdl_six_voice.py \
  --mode six-to-six \
  --output-dir data/cpdl_reductions/six_voice_string_sextet
```

and:

```bash
uv run --extra notation python scripts/reduce_cpdl_six_voice.py \
  --mode six-to-five \
  --output-dir data/cpdl_reductions/six_voice_quartet_plus_viole
```

The report should include work index, section, title, selected source path,
source format, source part count, output path, global transposition, mode,
status, and error.

## Tests

Add focused tests before running the full CPDL batch:

- six source voices map one-to-one into the six-part profile by register;
- six-to-six sweet-spot policy can permute only inner voices while preserving
  top and bottom;
- six-to-five mode chooses the duplicated or least salient middle voice for
  omission;
- six-to-five mode does not omit the only active third of a sonority when a
  duplicate fifth or octave is available instead;
- all generated scores pass the existing exact-measure, no-gap, no-overlap,
  and source-provenance validators.

## Milestones

1. Add CPDL six-voice source diagnostics and report counts.
2. Add `STRING_SEXTET_GESUALDO` and six-to-six assignment tests.
3. Implement and batch-run six-to-six reductions.
4. Add six-to-five compression policy and tests.
5. Batch-run six-to-five reductions and compare coverage metrics with the
   six-to-six outputs.
6. Decide whether the single seven-voice sacred work should use a later
   seven-to-six/seven-to-five extension or stay out of scope for this pass.
