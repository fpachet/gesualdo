# Gesualdo Quartet Reduction Rules

This document describes the musical rules currently encoded in the quartet
reduction algorithm. It is written as an editorial guide rather than as code
documentation, so that the output can be reviewed musically.

The reducer is deterministic. It does not learn from examples, and it does not
improvise freely. Most notes in the quartet are copied from real source notes
in the madrigal. A smaller optional layer may add explicitly marked editorial
harmony.

## General Principles

1. Preserve the madrigal before improving the quartet texture.

   The first obligation is to keep the source rhythm, attacks, durations, pitch
   classes, and voice identity as much as possible. Notes copied from the
   madrigal carry source-event provenance.

2. Prefer four idiomatic string parts over a literal vocal transcription.

   The quartet should be playable by Violin I, Violin II, Viola, and Cello.
   Notes may be moved by octave to fit range and register, but their pitch
   class and duration are preserved unless a separately enabled editorial
   option says otherwise.

3. Keep editorial material distinguishable from source material.

   Source-preservation enrichment copies real madrigal notes. Editorial harmony
   and editorial thirds create generated notes and mark them internally as
   generated events.

4. Avoid adding notes merely to make the page look full.

   Empty strings are acceptable when the source texture is sparse or when
   filling them would create weak doublings, isolated fragments, or misleading
   harmony.

## Global Transposition

1. Choose a global transposition automatically unless the caller forces one.

   The reducer tests candidate transpositions and scores them against the
   target ensemble.  The default search covers `-18` to `+6` semitones.

2. Favor playable ranges and preferred registers.

   Long notes matter more than short notes in the transposition score, because
   sustained structural tones expose range problems more strongly than passing
   tones.

3. Prefer simpler printed key signatures among near-equivalent choices.

   Once the best range/register candidate is known, another candidate can
   replace it only when the tessitura score remains essentially tied and the
   printed key signature becomes substantially lighter.  The current rule uses
   duration-weighted average `abs(sharps)` as the key burden, so a move from six
   sharps/flats to one matters much more than a cosmetic one-step change.

   The production guardrail is deliberately conservative: the cleaner-key
   candidate must be within `0.02` of the best range/register score, must reduce
   the weighted key-signature burden by at least `2.0`, and must improve it by
   at least `40%`.  Ties are broken toward the lower key burden, then the better
   tessitura score, then the smaller move away from the range/register winner.

4. Minimize unnecessary displacement from the source.

   A transposition that keeps the music close to the original pitch level is
   preferred when it remains playable.

## Basic Quartet Assignment

1. Preserve the outer voices first.

   The highest source voice by median pitch is assigned to Violin I. The lowest
   source voice by median pitch is assigned to Cello.

2. Reduce the remaining source voices into Violin II and Viola.

   The middle reduction is selective: it chooses source events that improve
   harmonic coverage and voice continuity.

3. Prefer new pitch classes over doubled pitch classes.

   At each source onset, the algorithm first looks for notes whose pitch class
   is not already sounding in the assigned outer voices or earlier selected
   inner notes.

4. Prefer fresh attacks over tied continuations.

   A new attack is more useful than a held note when both are otherwise good
   candidates, because it preserves audible contrapuntal activity.

5. Prefer notes that widen or clarify the sonority.

   Among uncovered candidates, notes that create a better spread around the
   outer anchors are preferred.

6. Assign selected notes to instruments by musical cost.

   The assignment balances register fit, melodic continuity from the previous
   note in the target part, octave displacement, and voice-order stability.

## Borrowing Idle Outer Parts

1. Idle outer strings may borrow inner source material.

   If Violin I or Cello is resting, the reducer may temporarily use that string
   for an uncovered source line.

2. Borrowed notes must behave like a line, not a stray chord filler.

   The reducer prunes isolated borrowed events unless they have nearby
   borrowed neighbors in the same source voice.

3. Borrowed outer targets are secondary capacity.

   Violin II and Viola are used first for normal inner coverage. Idle outer
   strings are used when the regular inner capacity is exhausted or when they
   help sustain a continuous gesture.

## Source-Voice Enrichment

This optional layer is enabled with `preserve_active_voice_count=True`.

1. Try to preserve the number of active source voices.

   If the madrigal has more active source voices than the plain quartet
   reduction currently represents, the reducer tries to add source notes until
   the quartet has a comparable number of active strings, capped at four.

2. Added notes must come from real source events.

   This mode does not invent harmony. It only restores source material that the
   plain reduction omitted.

3. Prefer unrepresented source voices.

   When choosing which source notes to restore, the reducer gives priority to
   source parts that are not already represented at that moment.

4. Permit duplicate pitch classes only when there is enough context.

   Duplicate pitch classes can be preserved when they are part of a richer
   sonority or an independent source line. But if the active source sonority
   contains only one pitch class, the reducer does not add another octave or
   unison duplicate merely to increase the active string count.

5. Trim duplicate-pitch restorations at the next real source change.

   If a restored note duplicates a pitch class already sounding, it is shortened
   to the next source change when needed, so it does not cover or suppress a
   later chromatic source event.

## Editorial Harmony Filling

This optional layer is enabled with `add_editorial_harmony=True`.

1. Fill only when there is a real idle target string.

   The algorithm checks that a string is free for the whole proposed support
   interval before adding a generated note.

2. Require a minimum duration.

   Very short gaps are ignored. Generated support must last at least half a
   quarter note.

3. Require at least two active source pitch classes.

   The harmony filler does not act on a bare unison or octave sonority.

4. Prefer active source tones.

   The basic harmony filler chooses from pitch classes already active in the
   source, fitted into the target instrument's range and register.

5. Penalize exact note duplication.

   Repeating the exact same MIDI pitch as an already sounding quartet note is
   allowed only when it wins against register and continuity costs.

6. Merge repeated generated support notes.

   Adjacent generated notes of the same pitch on the same target are merged, so
   the score does not show artificial repeated notes caused by internal
   segmentation.

## Editorial Missing Thirds

This narrower optional layer is enabled with `add_editorial_thirds=True`, and
is used together with `add_editorial_harmony=True`.

1. Detect bare fifth shells.

   If the sounding material contains a possible root and fifth but lacks both
   minor and major third, the chord is considered a candidate for an editorial
   third.

2. Do not add a third when one is already present.

   If either the minor third or major third above the implied root is already
   sounding, the rule does nothing.

3. Prefer the third that appears later in the source.

   The algorithm looks ahead for the nearest source note that would supply the
   missing minor or major third. If one appears, that pitch class is preferred.

4. Default to a major third when the source gives no immediate clue.

   This is a pragmatic default rather than a claim about Gesualdo's harmony.
   It can be revised if listening exposes systematic errors.

5. Fit the invented third to the target string.

   The chosen third is placed in an octave that fits the free instrument's range
   and preferred register, with a small preference for melodic continuity from
   the previous note in that part.

## Rhythm, Durations, and Ties

1. Preserve source offsets and durations whenever possible.

   The reducer works with exact rational quarter-lengths and splits notes only
   when measure boundaries require it.

2. Maintain ties across barlines.

   If a source note crosses a barline, the output note is split and tied.

3. Ignore repeated same-pitch source articulations as harmonic changes for
   editorial support duration.

   If a source voice repeats the same pitch class, generated support can
   continue through that articulation instead of blinking off and on.

## Rests and Validation

1. Measures must be complete.

   Rests are inserted to fill gaps so every part has complete bars.

2. No overlaps or overfull measures are allowed.

   The score is validated after construction.

3. Every note must be traceable or explicitly generated.

   Source notes carry source-event IDs. Editorial notes are marked as generated
   harmony events. Notes without either provenance are rejected by validation.

## Editorial Dynamics

1. Dynamics are an optional notation layer.

   They do not alter source rhythm or note choice.

2. Dynamics follow a coarse energy estimate.

   The algorithm estimates bar-level energy from active part count, attack
   density, average register, and registral span.

3. Hairpins are short and local.

   Crescendo and diminuendo wedges are capped to short spans so the notation
   stays readable.

## Known Limits

1. The rules are local, not a global optimization over the whole piece.

   The reducer makes good local decisions at source onsets, but it does not yet
   solve one global contrapuntal or harmonic plan.

2. The implied-root logic is simple.

   Editorial thirds are based on root-fifth shell detection and source
   lookahead. Ambiguous Renaissance sonorities may still need manual review.

3. Register choices are cost-based, not instrumentally expressive.

   The algorithm prefers playable and stable placements, but it does not yet
   understand bowing, string choice, timbre, or phrase-level instrumental
   rhetoric.

4. The best rule is still listening.

   The comparison renders are part of the method: suspicious bars should be
   inspected in both notation and audio, then turned into explicit rules only
   when the musical reason is clear.
