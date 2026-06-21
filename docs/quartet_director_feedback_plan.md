# Quartet Director Feedback Plan

This document turns the first professional string-quartet feedback into a
practical cleanup and review plan for the Gesualdo reductions.

For a chronological, presentation-friendly summary of the broader development
work, see `docs/development_log.md`.

## Implemented Status

The GitHub review app in `docs/index.html` now exposes pre-exported PDF links
beside MusicXML, MP3, and source links. The browser preview still uses Verovio
SVG rendering in `docs/app.js`, but conductor review can use static PDFs.

Current generated review outputs:

- 326 active review PDFs across KDF, CPDL five-voice, CPDL six-voice, and Take 6.
- Three compiled director books under `output/pdf/quartet_director/`: Gesualdo
  five-voice reductions, Gesualdo six-voice reductions, and Take 6 double-stop
  reductions.
- A draft response email at `docs/quartet_director_email.md`.
- Take 6 now exposes 10 preferred `string_quartet_double_stops` active outputs.
- The previous generated corpus was archived at
  `data/archive/key_signature_optimization_pre_2026-06-21/`.
- Eight CPDL five-voice PDFs are marked with `pdf_midi_fallbacks=1` because
  MuseScore failed direct MusicXML-to-PDF export for those files but succeeded
  through the temporary MIDI fallback.

The key-signature optimization has also been recomputed. The production
tolerance is now `0.05`; 78 cleaner-key updates were applied, and the fresh
audit reports `0 attention` rows. For example, KDF `Luci serena e chiare` now
uses semitones `0` and a one-flat key signature instead of the earlier four
sharps seen in review.

## Goals

1. Make score review faster for the quartet director.
2. Improve notation readability for unfretted string players.
3. Separate musical-generation issues from pure engraving/export issues.
4. Keep every cleanup step reproducible and auditable.

## Phase 1: PDF Review Export

Add a MuseScore-based PDF renderer alongside the existing MP3 renderer.
The first implementation lives in `scripts/render_review_pdfs.py` and covers
the current Gesualdo reports plus the Take 6 quartet report. For Take 6, the
current target is `take6:string_quartet_double_stops`.

Implemented outputs:

- full score PDFs for each reviewed MusicXML reduction;
- an export report listing rendered, skipped, failed, and MIDI-fallback files.

Individual part PDFs remain a later engraving task if the quartet wants
standalone part books.

Candidate output layout:

```text
data/kdf/book*/renders/string_quartet_pdf/
data/cpdl/5-voices/renders/string_quartet_pdf/
data/cpdl/6-voices/renders/string_quartet_pdf/
```

Then update the review app asset links to show:

- MusicXML
- PDF
- MP3
- Source

This is the highest-priority step because it lets the director annotate and
review pieces outside the web app.

## Phase 2: Clean Review Mode

Add an export/cleanup mode for conductor review PDFs.
The initial implementation uses `--mode clean` in `scripts/render_review_pdfs.py`.

Suggested modes:

- `clean`: no generated dynamics or hairpins, readable notation first;
- `expressive`: keep editorial dynamics/hairpins for later musical review.

For the first quartet pass, use `clean` by default. The current editorial
dynamics can look like long slurs or visual clutter, and the original sources
do not contain reliable dynamics.

## Phase 3: Engraving Cleanup Pass

Create a MusicXML post-processing pass that runs before PDF export. It should
be conservative, deterministic, and testable.
The shared cleanup code lives in `src/gesualdo_reduction/notation_cleanup.py`,
so the same rules apply to Gesualdo and the preferred Take 6 double-stop
exports.

Initial responsibilities:

- remove unnecessary explicit naturals;
- add final double barlines;
- add cello clef changes for sustained high passages;
- optionally suppress generated dynamics/hairpins in clean mode;
- produce an audit TSV with counts and warnings.

The audit report should include before/after counts for accidentals, dynamics,
hairpins, clef changes, missing final barlines, and dangling ties.

## Phase 4: Enharmonic Spelling

The reducer currently works mostly at MIDI-pitch level, so enharmonic spelling
is not always meaningful for string players.

Preferred strategy:

1. Preserve source spelling when reducing from source MusicXML/MXL.
2. If source spelling is unavailable, infer spelling from key signature and
   local harmonic context.
3. Use a key-aware fallback map for common cases, for example preferring `D#`
   over `Eb` in E major.

This should be implemented after the first PDF export path, because the
quartet director can then validate spelling issues directly on PDFs.

## Phase 5: Cello Clef Policy

Keep cello in bass clef by default, but switch to tenor or treble clef for
legibility in high sustained passages.

Avoid one-note clef flicker. A clef change should require a small run of high
material, for example several consecutive notes or at least two beats above a
threshold.

Suggested first rule:

- bass clef by default;
- tenor clef for sustained material above roughly G3/A3;
- treble clef only for clearly high passages;
- return to bass clef only after sustained lower material.

Exact thresholds should be tuned after looking at exported PDFs.

## Phase 6: Octave-Jump Audit

Some octave jumps may be genuine consequences of reduction, but others may be
assignment artifacts.

Add an automatic report that flags, by part and measure:

- melodic leaps of an octave or larger;
- isolated high or low notes far outside surrounding register;
- leaps introduced by octave fitting;
- discontinuities caused by reassignment between source voices.

This report should not automatically rewrite music at first. It should help
identify the most important examples to inspect with the director.

## Phase 6B: Part-Coherence Feedback And Octave Optimization

The second quartet-director pass identified three related problems:

- awkward cello register jumps in some five- and six-voice reductions;
- fragmentary writing in other parts too, especially Take 6 Violin I and Viola
  passages where a player rests for several bars and then plays a small scrap;
- residual visual artifacts such as dangling slurs/ties or accidentals on
  continuations.

The follow-up audit in `scripts/audit_part_coherence.py` broadens Phase 6 from
cello-only jumps to all-part coherence. It flags register jumps, sparse note
islands, low-density windows, dangling ties/slurs, and visible accidentals on
tied continuations.

For register jumps, the preferred first repair is not deletion. The reducer
should preserve pitch classes and harmonic coverage, then choose better octave
placements for each written part. A local example is Take 6 `A Quiet Place`,
bars 33-42:

- Violin II bar 37 should be improved by raising the previous E in bar 36 from
  E4 to E5, rather than lowering the F-sharp in bar 37.
- Viola bar 37 should move the first E-flat from E-flat5 to E-flat4.
- Violin I bar 39 is flagged, but should remain unchanged unless visual review
  confirms that it is musically awkward.

The first `A Quiet Place` prototype made four octave changes: the two expected
bar 36-37 fixes, the earlier cello bar 15 jump, and Violin I bar 39 E4 to E5.
The part-coherence audit comparison removed all four register-jump warnings
for this piece without increasing sparse-fragment or notation-artifact counts.

The implementation should be auditable:

- preserve rhythm, pitch classes, note counts, and measure completeness;
- keep notes in instrumental range and keep double-stops conservative;
- compare before/after issue counts with the part-coherence audit;
- write a changed-note report explaining every octave move.
- run the same clean-review notation cleanup after octave optimization, so
  generated dynamics and hairpins do not reappear in the review PDFs.

## Phase 7: Endings And Completeness

Ensure every exported score has a musically clear ending.

Checks:

- all parts have the same final measure;
- final measure is complete;
- no dangling ties continue past the end;
- final double barline is present.

If a source genuinely appears incomplete, the export report should flag it
rather than silently masking the problem.

## Suggested Implementation Order

1. Done: add PDF batch export for the current review catalog.
2. Done: add PDF links to the web review app.
3. Done: add clean review mode and disable editorial dynamics/hairpins in that mode.
4. Done: add final barlines and basic ending validation.
5. Done: add cello clef changes for high passages.
6. Done: add redundant-natural cleanup.
7. Done: recompute cleaner-key transpositions with the `0.05` tolerance.
8. Done: add all-part part-coherence audit for jumps, sparse fragments, and
   notation artifacts.
9. Done: prototype pitch-class-preserving octave optimization on Take 6
   `A Quiet Place`.
10. Next: review the clean `A Quiet Place` optimized PDF musically before
   applying octave optimization corpus-wide.
11. Next: add enharmonic spelling audit and source-spelling preservation.
12. Next: iterate on spelling, clefs, and suspicious jumps using director annotations.

## Open Questions

- Should the first PDF batch include only shortlisted concert candidates, or
  the full current catalog?
- Does the quartet prefer full score only, or full score plus individual parts?
- Should clean review PDFs remove all editorial dynamics, or keep simple
  dynamic marks while suppressing hairpins?
- Which engraving backend should be canonical for final PDFs: MuseScore 4,
  Verovio-generated print output, or LilyPond later?
