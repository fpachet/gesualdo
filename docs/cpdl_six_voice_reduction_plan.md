# CPDL Six-Voice Reduction Plan

The new CPDL corpus contains 34 six-voice work pages with downloaded files:
32 sacred works and 2 secular works. It also contains one sacred seven-voice
page. The five-voice batch now uses the current enriched string-quartet reducer:
source-voice enrichment, editorial harmony, and editorial missing thirds. Six
voices need a separate quartet-compression engine because the reducer must make
an explicit, traceable decision about which inner strands to preserve, merge,
or omit.

## Goal

Add a dedicated CPDL six-voice-to-string-quartet reduction path without
weakening the current four- and five-voice quartet reducers.

The extension should support two analysis views:

1. Six-to-four production mode: reduce six source voices into the existing
   enriched `STRING_QUARTET` profile.
2. Optional six-to-six diagnostic mode: preserve all source voices in a neutral
   instrumental score only for comparison and coverage auditing.

## Recommended Engine Shape

Add a new public entry point beside the current five-part helpers:

```python
reduce_six_to_quartet(...)
```

Internally, keep the same architecture already used by
`reduce_to_quartet`:

- `EnsembleProfile` defines the target instruments and register preferences.
- `AssignmentPolicy` chooses which source events are emitted by each target.
- `ReductionConfig` keeps validation, range enforcement, and transposition
  behavior shared with the existing reducer.

## Ensemble Profile

Reuse the existing `STRING_QUARTET` profile:

- Violin I
- Violin II
- Viola
- Violoncello

The outer voices remain top violin and cello when possible. The middle four
source voices are compressed into Violin II and Viola, with controlled borrowing
into idle outer strings when the current quartet enrichment rules permit it.

## Assignment Policy

Create `SixVoiceQuartetCompressionPolicy`.

- rank source voices by median sounding pitch;
- pin the highest source voice to Violin I and the lowest to Violoncello when
  the outer voices are active;
- evaluate the four middle source voices against Violin II, Viola, and any
  safely borrowable idle outer target;
- allow middle source voices to be temporarily omitted or merged per local
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

When the six-voice translator exists, add `scripts/reduce_cpdl_six_voice.py`
with the same operational shape as the five-voice script:

```bash
uv run --extra notation python scripts/reduce_cpdl_six_voice.py \
  --output-dir data/cpdl/6-voices/reductions/string_quartet
```

The report should include work index, section, title, selected source path,
source format, source part count, output path, global transposition, mode,
status, and error.

## Tests

Add focused tests before running the full CPDL batch:

- six-to-four mode preserves active outer voices where possible;
- six-to-four mode chooses the duplicated or least salient middle voice for
  omission;
- six-to-four mode does not omit the only active third of a sonority when a
  duplicate fifth or octave is available instead;
- all generated scores pass the existing exact-measure, no-gap, no-overlap,
  and source-provenance validators.

## Milestones

1. Add CPDL six-voice source diagnostics and report counts.
2. Add six-to-four compression policy tests.
3. Implement and batch-run six-to-four reductions.
4. Compare coverage metrics with the five-voice quartet batch.
5. Add optional six-to-six diagnostic output only if coverage auditing needs a
   full-preservation reference.
6. Decide whether the single seven-voice sacred work should use a later
   seven-to-four extension or stay out of scope for this pass.
