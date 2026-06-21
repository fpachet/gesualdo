# Reduction Process Overview

This document is the presentation-level description of the project: how the
reduction pipeline evolved, what musical rules it now applies, and how each
improvement is traced and validated. The detailed rule references remain in
`docs/reduction_rules.md` for Gesualdo-style polyphony and
`docs/take6_reduction_rules.md` for Take 6 six-voice close harmony.

## Core Idea

The system turns multi-voice vocal or vocal-style sources into playable string
quartet scores. It is deterministic and rule-based: it does not improvise new
music by default. Most written notes are copied from real source events, then
placed into Violin I, Violin II, Viola, and Cello with range, register,
continuity, harmonic coverage, and readability constraints.

The work has two complementary goals:

1. Preserve the source: rhythm, attacks, durations, pitch classes, voice
   identity, and characteristic harmony should remain auditable.
2. Produce a usable quartet score: the output must be readable, idiomatic
   enough for string players, importable in MuseScore, and suitable for
   conductor/director review.

## Development Timeline

1. Baseline reduction rules.

   The first stage encoded general quartet-reduction principles: preserve
   outer voices, compress middle voices, fit instrumental ranges, choose a
   global transposition, and mark generated editorial material separately from
   copied source material.

2. Cleaner key signatures and corpus review.

   The transposition selector was improved so near-equivalent range/register
   choices prefer simpler printed key signatures. This reduced unnecessary
   sharps/flats across the review corpus while keeping tessitura within a
   conservative tolerance.

3. Review infrastructure.

   The project added batch MusicXML, MP3, and PDF rendering, a local review
   interface, compiled director books, and TSV reports recording export and
   notation-cleanup statistics.

4. Clean engraving mode.

   Because generated dynamics and hairpins were visually confusing in early
   reviews, clean review PDFs suppress generated expressive markings. The same
   export pass removes redundant naturals, fixes dangling ties, suppresses
   accidentals on tied continuations, adds final barlines, and inserts cello
   clef changes where useful.

5. Director-feedback audit loop.

   Quartet-director comments were converted into repeatable checks:
   register-jump flags, sparse-fragment flags, sparse-window flags,
   dangling-tie/slur flags, and tied-continuation accidental flags. The audit
   is intentionally broader than one instrument because the director noted that
   cello jumps, sparse violin/viola writing, and visual artifacts were repeated
   problems.

6. Pitch-class-preserving octave optimization.

   `A Quiet Place` was used as the first prototype for fixing awkward register
   jumps without changing harmonic content. The optimizer uses dynamic
   programming over candidate octave placements, preserves pitch classes and
   measure rhythm, and writes a report of every octave move.

7. Take 6 close-harmony refinement.

   Take 6 reductions required a different musical priority from Gesualdo:
   dense chord color matters. The reducer now favors guide tones, altered
   tones, ninths, thirteenths, and source-based double-stops where playable.
   Later director and score-inspection passes added protections against tiny
   splices, missing exposed pickups, short isolated double-stops, source
   micro-rests, one-note overlaps, MusicXML tuplet import warnings, piece-level
   rhythm residues, mixed time-signature bar-map errors, and interrupted
   borrowed source lines.

## Musical Rule Families

1. Source preservation.

   The reducer keeps source events whenever possible. Written notes carry
   provenance so a generated score can be checked against the original source.
   Editorial/generated notes are a separate optional layer.

2. Instrumental assignment.

   Violin I and Cello anchor the outer source voices. Inner voices are selected
   for Violin II and Viola, with idle outer strings allowed to borrow inner
   material when this preserves a real line.

3. Harmonic coverage.

   For Gesualdo-style polyphony, the reducer prioritizes contrapuntal source
   preservation and can optionally fill missing thirds or support tones. For
   Take 6, the priority changes: dense sonorities favor missing pitch classes,
   guide tones, color tones, altered tones, and sustained source doublings
   rather than generic triadic completion.

4. Voice continuity.

   The algorithm penalizes isolated fragments and rewards continuation of the
   same source part on the same quartet instrument. Recent Take 6 work extends
   this to borrowed lower lines: a duplicate pitch class may be retained if it
   continues a source line that has already entered, as in `Hark Herald`
   measures 2-3.

5. Rhythmic readability.

   The system preserves source rhythm, but it also cleans narrow MIDI import
   artifacts that produce unreadable fragments: tiny note/rest gaps, tiny
   same-voice overlaps, and clipped preservation fragments shorter than a
   triplet eighth.

6. String playability.

   Optional Take 6 double-stops are source-based and conservative. They must
   fit range, interval, approximate adjacent-string position, and a minimum
   overlap duration. Very short isolated double-stops are rejected even if the
   interval is theoretically playable.

7. Notation and import compatibility.

   MusicXML validity is not enough: MuseScore import/export is part of the
   validation loop. The pipeline strips problematic explicit
   `<time-modification>` tags where MuseScore over-counts tuplets and applies
   scoped quarter-grid fallbacks only for pieces that need them: `If We Ever`
   for raw MuseScore import warnings and `Come Unto Me` for string-readability
   cleanup of visible tuplets/sixths.

## Director-Driven Improvements

The director's comments are preserved as part of the development trace. The
main implemented responses are:

- Clean review PDFs without confusing generated dynamics/hairpins.
- Redundant accidental cleanup, including tied-continuation accidentals.
- Dangling tie/slur cleanup.
- Cello clef changes for high passages.
- All-part part-coherence audit, not only cello.
- Octave optimization that preserves pitch classes and harmonic coverage.
- Avoidance of tiny clipped Take 6 fragments.
- Protection of exposed omitted melodic pickups.
- Cleanup of `He Never Sleeps` rhythm artifacts in measures 22 and 27.
- Rejection of very short isolated double-stops.
- Independent tempo metadata for reviewed Take 6 songs.
- MuseScore import fixes for `Come Unto Me` and `If We Ever`.
- Correct mixed-meter bar mapping for `Hark Herald`.
- Continuous borrowed cello line in `Hark Herald` measures 2-3.
- Cello sweet-spot protection in `Come Unto Me`, where high borrowed duplicate
  C5 material was removed from the cello without changing the global
  transposition.
- Final output rhythm-scar cleanup in `Come Unto Me`, where bar 32 was reduced
  from tiny slivers and a micro-rest to ordinary string-readable durations.
- Piece-specific quarter/eighth-grid cleanup in `Come Unto Me`, where bar 26
  no longer shows triplet/sixth-note residue in the string parts.

## Validation And Audit Trail

Each change is expected to leave evidence:

- Unit tests for rule-level behavior.
- MusicXML measure-completeness checks.
- Provenance on copied source notes.
- Before/after part-coherence audit reports for octave optimization.
- TSV reports for PDF cleanup and rendering.
- MuseScore raw import/export checks for files that exposed corruption
  warnings.
- Development notes in `docs/development_log.md`.
- Rule descriptions in `docs/reduction_rules.md` and
  `docs/take6_reduction_rules.md`.

This makes the process explainable in a presentation: each director comment can
be shown as a musical observation, then as a rule or audit, then as a tested
implementation, then as regenerated review material.

## Suggested Presentation Structure

1. Problem statement.

   Show the core challenge: reducing dense vocal or vocal-style polyphony to a
   string quartet without losing source identity, harmonic color, or
   playability.

2. Baseline rule system.

   Explain that the reducer is deterministic and source-traceable. The main
   baseline decisions are global transposition, outer-voice anchoring, middle
   voice compression, range fitting, and optional editorial layers.

3. Take 6 special case.

   Present Take 6 as a harder close-harmony case: six active voices often
   contain more color than four monophonic string parts can carry. The key
   design choice is to preserve guide tones, altered tones, source doublings,
   and selected playable double-stops instead of applying generic triadic
   completion.

4. Professional feedback loop.

   Show how quartet-director comments became engineering requirements:
   awkward jumps became part-coherence audits, confusing hairpins became clean
   review PDFs, accidentals on tied notes became notation cleanup, and
   interrupted fragments became continuity rules.

5. Iterative improvements.

   Use concrete examples: `A Quiet Place` for octave optimization,
   `He Never Sleeps` for missing pickup and rhythm-artifact cleanup,
   `Come Unto Me` and `If We Ever` for MuseScore import compatibility, and
   `Hark Herald` for mixed meter and cello-line continuity.

6. Validation.

   Close the technical story with tests, MusicXML measure completeness,
   MuseScore raw import/export checks, cleanup TSV reports, and before/after
   audit comparisons.

7. Musical status and next work.

   End with the active review set, remaining enharmonic-spelling work, the
   question of applying octave optimization corpus-wide, and the possible later
   creation of an expressive edition after clean review materials are stable.

## Presentation Artifacts To Show

- A source excerpt and its generated quartet reduction.
- One clean PDF before/after example where generated dynamics were removed.
- The `A Quiet Place` before/after octave-optimization comparison.
- The `He Never Sleeps` examples for restored pickup, cleaned micro-rest, and
  short double-stop rejection.
- The `Hark Herald` mixed-meter correction at measures 22-23.
- The `Hark Herald` cello-continuity correction at measures 2-3.
- The `Come Unto Me` cello tessitura correction in measure 7.
- The `Come Unto Me` grid-rhythm simplification in measure 26.
- The `Come Unto Me` rhythm simplification in measure 32.
- A TSV or Markdown audit excerpt showing how improvements are counted.
- The current Take 6 review set and known tempo metadata.

## Current Outputs

The active Take 6 review set contains ten preferred double-stop quartet
reductions:

- `Spread Love`
- `Gold Mine`
- `A Quiet Place`
- `He Never Sleeps`
- `David et Goliath`
- `Get Away Jordan`
- `If We Ever`
- `Hark Herald`
- `I'm On My Way`
- `Come Unto Me`

Known reviewed tempos are stored in `data/take6/tempo_overrides.json` rather
than in code. At the time of this note: `He Never Sleeps` is 75,
`A Quiet Place` is 68, `Hark Herald` is 108, and `If We Ever` is 117.

## Remaining Work

The main open presentation points are:

- Review whether the clean optimized octave candidates should replace the
  active corpus.
- Add a deeper enharmonic-spelling audit and preserve source spelling when
  available.
- Decide whether a later expressive edition should reintroduce curated
  dynamics after the clean review stage.
- Continue turning repeated director annotations into explicit rules, tests,
  and audit checks.
