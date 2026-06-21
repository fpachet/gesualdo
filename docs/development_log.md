# Gesualdo Quartet Reduction Development Log

This document tracks the successive musical and technical improvements made to
the reduction pipeline. It is intended as a presentation-friendly companion to
the detailed rule documents.

## Rule Extraction And Baseline Reducer

- Built an explicit reduction pipeline for turning vocal polyphony into string
  quartet MusicXML.
- Documented the general reduction rules in `docs/reduction_rules.md`.
- Documented the Take 6-specific six-voice-to-quartet rules in
  `docs/take6_reduction_rules.md`.
- Added range fitting, preferred instrumental registers, assignment continuity,
  voice-order stability, and conservative source-to-instrument mapping.
- Added harmonic completion rules so the quartet texture avoids empty or weak
  sonorities when a musically plausible added note is available.
- Added conservative double-stop support for Take 6 reductions, preserving more
  six-voice harmonic information without exceeding normal quartet playability.

## Source And Corpus Handling

- Added CPDL/Kunst der Fuge ingestion and normalization for MusicXML/MIDI
  sources.
- Added Take 6 MIDI normalization, including cleanup of small import artifacts
  such as isolated note/rest duration fragments.
- Preserved exact rhythmic offsets and durations after cleanup so reductions
  remain traceable to the source.
- Added consistent displayed titles for generated Take 6 score outputs.

## Key And Transposition Readability

- Added an audit for nearby global transpositions that reduce printed
  key-signature burden while preserving tessitura.
- Applied the cleaner-key transposition pass with the `0.05` tessitura
  tolerance.
- Recorded the pre-cleaner-key corpus snapshot for comparison.
- Re-ran the transposition audit and reached `0 attention` rows at the current
  threshold.

## Review Export And Director Workflow

- Added batch PDF export for review scores.
- Added clean conductor-review mode in `scripts/render_review_pdfs.py`.
- Suppressed generated editorial dynamics and hairpins in clean mode because
  they were visually confusing and could be mistaken for slurs.
- Added PDF links to the local review interface.
- Built director review books under `output/pdf/quartet_director/` for:
  Gesualdo five-voice reductions, Gesualdo six-voice reductions, and Take 6
  double-stop reductions.
- Added per-export audit TSVs recording what cleanup was applied to each PDF.

## Engraving Cleanup

- Added a shared notation cleanup module:
  `src/gesualdo_reduction/notation_cleanup.py`.
- Added redundant-natural suppression to reduce unnecessary accidentals.
- Added final barlines to exported parts.
- Added basic ending validation concerns to the director feedback plan.
- Added cello clef changes for high passages so the cello part is easier to
  read.
- Added cleanup of dangling or malformed tie markings.
- Added suppression of visible accidentals on tied continuations.

## First Director Feedback Pass

- Recorded the first quartet-director feedback in
  `docs/quartet_director_feedback_plan.md`.
- Prioritized readable review material over expressive playback markings.
- Added `docs/quartet_director_email.md` as a draft response summarizing the
  first cleanup pass.
- Identified remaining musical/engraving work: local enharmonic spelling,
  suspicious octave jumps, and review of specific annotated examples.

## Second Director Feedback Pass

The second annotated pass raised three repeated problems:

- awkward register jumps, especially in cello but also present in other parts;
- sparse fragments in Violin I and Viola in some Take 6 reductions;
- residual visual artifacts such as slurs/ties that go nowhere and accidental
  artifacts on continuations.

In response:

- Added `scripts/audit_part_coherence.py`.
- Broadened the audit from cello-only register checks to all parts.
- Added issue categories for register jumps, sparse fragments, sparse windows,
  dangling ties/slurs, and accidentals on tied continuations.
- Generated corpus-wide reports:
  `outputs/reports/part_coherence_audit.md` and
  `outputs/reports/part_coherence_audit.tsv`.

## A Quiet Place Octave Optimization Prototype

The Take 6 reduction of `A Quiet Place` was used as the first local prototype
for director-driven octave repair.

Before octave optimization, the Take 6 reducer was improved to avoid tiny
trimmed preservation fragments. In `A Quiet Place`, measure 18, this removed a
`1/6`-quarter Violin II splice caused by clipping a straight eighth-note source
line into a triplet-tied context. The reducer now keeps the full source event
when trimming a duplicate-pitch preservation candidate would create a fragment
shorter than a triplet eighth.

The same Take 6 pass was extended after inspecting `He Never Sleeps`, measure
9. A fourth-source-voice pickup had disappeared because its pitch classes were
already covered by less melodic lower voices. The double-stop layer now allows a
narrow exception for exposed omitted melodic pickups: a duplicate pitch class
from an otherwise unrepresented moving source voice may be attached as a
playable double-stop, then continue alone if the host note releases.

`He Never Sleeps`, measure 22 exposed another MIDI-import rhythm artifact in a
fixed outer voice: `1/3 + 1/3 + 1/12 rest + 3/4`. The Take 6 short-artifact
normalizer now also applies to outer anchor voices and absorbs tiny intra-voice
gaps of at most `1/12` quarter note into the following source note. This keeps
the melodic content and endpoint intact while removing the unreadable micro-rest
from the quartet part.

The same normalizer was then extended for `He Never Sleeps`, measure 27. There,
an inner source note overlapped the following chord by `1/12` quarter note,
which blocked the following source attack and left a strange `1/3` note plus
`5/12` rest in Violin II. Tiny same-voice note overlaps are now trimmed to the
later onset before source selection, yielding ordinary readable subdivisions.

Implemented:

- Added pitch-class-preserving octave optimization in
  `src/gesualdo_reduction/octave_optimization.py`.
- Added `scripts/optimize_octaves.py` to run the optimizer and compare audits.
- Used dynamic programming over candidate octave placements for each part.
- Preserved rhythm, note count, pitch classes, and harmonic coverage.
- Wrote every octave move to
  `outputs/octave_optimization/a_quiet_place_octave_changes.tsv`.

Result for `A Quiet Place`:

- Violin II bar 36: moved the last E up an octave to avoid the bar 37 leap.
- Viola bar 37: moved the first E-flat down an octave.
- Violoncello bar 15: moved one note down an octave to remove an isolated jump.
- Violin I bar 39: moved one E up an octave according to the optimizer's local
  transition-cost criterion.

Audit result:

- `register_jump`: `4 -> 0`
- `dangling_tie`: `2 -> 0`
- `accidental_on_tie_continuation`: `3 -> 0`

The canonical optimized files are:

- `outputs/octave_optimization/a_quiet_place_optimized.musicxml`
- `outputs/octave_optimization/a_quiet_place_optimized.pdf`
- `outputs/octave_optimization/a_quiet_place_audit_comparison.tsv`

## Clean Optimized Review Output

After the octave prototype, the optimizer was corrected so optimized review
outputs also run the clean-review notation cleanup by default.

This prevents generated dynamics and hairpins from reappearing in optimized
PDFs. The old behavior is still available with `--keep-dynamics` when an
expressive/playback-oriented score is explicitly needed.

For `A Quiet Place`, the clean optimization pass removed:

- 60 dynamic markings;
- 56 hairpins;
- 5 dangling or malformed tie markings;
- visible accidental artifacts on tied continuations.

The resulting optimized MusicXML has no remaining dynamic marks, wedge hairpins,
or dynamic playback tags.

## Batch Octave Optimization Rollout

The `A Quiet Place` workflow was generalized into
`scripts/batch_optimize_octaves.py`.

The batch script:

- selects works with fixable part-coherence audit issues;
- creates optimized clean candidate MusicXML files outside the active corpus;
- caps this first rollout at 20 octave changes per piece;
- writes per-piece octave-change reports and before/after audit comparisons;
- verifies sounding pitch-class coverage before accepting each candidate.
- assumes the Take 6 no-tiny-splice preservation rule has already been applied
  when generating the active Take 6 baseline reductions.

The first broader rollout produced:

- Take 6: 8 safe candidates out of 10, with 2 true invariant failures and 5
  MusicXML-safe candidates whose candidate-PDF rendering failed.
- KDF Gesualdo: 37 safe candidates out of 37.
- CPDL Gesualdo: 276 safe candidates out of 278.

The detailed rollout summary is in
`outputs/batch_octave_optimization/rollout_report.md`.

## Current Remaining Work

- Musically review the clean optimized `A Quiet Place` PDF before applying
  octave optimization corpus-wide.
- Musically review the broader batch candidates before replacing active corpus
  files.
- Add a deeper enharmonic-spelling audit, because the current accidental cleanup
  handles visual artifacts but does not yet decide between spellings such as
  F-sharp versus G-flat in harmonic context.
- Decide whether clean review PDFs should always remove all generated dynamics,
  or whether a later expressive edition should keep a curated subset.
- Continue iterating on annotated director examples and promote repeated
  observations into explicit rules, tests, and audit checks.
