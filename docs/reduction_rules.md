# Gesualdo Quartet Reduction Rules

This document describes the musical rules currently encoded in the quartet
reduction algorithm. It is written as an editorial guide rather than as code
documentation, so that the output can be reviewed musically.

For a presentation-level narrative of the whole process, including review
workflow, director-feedback iterations, and validation strategy, see
[`reduction_process_overview.md`](reduction_process_overview.md).

The reducer is deterministic. It does not learn from examples, and it does not
improvise freely. Most notes in the quartet are copied from real source notes
in the madrigal. A smaller optional layer may add explicitly marked editorial
harmony.

The system is nevertheless an AI system in the useful sense of complex
constraint solving. It must choose among antagonistic musical requirements:
preserving important contrapuntal lines, keeping characteristic dissonances and
chromatic motions, respecting instrument ranges and sweet spots, avoiding
unreadable notation, and producing a quartet score that can actually be played.
The final scores are therefore not automatic transcriptions. They are the
result of a guided process combining musical judgment, algorithms, notation
cleanup, and listening.

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

5. Treat dissonance and chromatic motion as structural material.

   Gesualdo's identity often lives in semitone motion, false relations,
   suspensions, cross-relations, and registral collisions. The reducer should
   not smooth these away in the name of abstract completeness. When there is a
   choice, a source note that carries a characteristic chromatic or dissonant
   event can be more valuable than a note that merely fills the chord.

6. Prefer playable instrumental rhetoric over literal fullness.

   Four strings cannot reproduce five or six voices continuously. A convincing
   reduction may leave a part resting, borrow a line temporarily, or choose a
   clearer octave placement rather than forcing every source event into the
   texture.

## Constraint Model

The reducer balances several rule families at once:

1. Source fidelity: preserve attacks, durations, pitch classes, and voice
   provenance.
2. Harmonic coverage: keep the pitch classes that define the current sonority.
3. Contrapuntal continuity: avoid breaking a line into isolated fragments.
4. Instrumental fit: respect range, preferred register, and quartet balance.
5. Notation readability: avoid rhythms, ties, accidentals, or clefs that make
   the score harder to rehearse than the music requires.
6. Editorial restraint: add generated harmony only when the option is enabled
   and the musical reason is explicit.

These constraints can disagree. A note may preserve a source voice but create
an awkward leap, improve a chord but interrupt a line, or fit a range but sit
poorly on the instrument. The algorithm's job is to make such tradeoffs
explicit and repeatable so they can be reviewed musically.

## Process Summary

The production workflow is deliberately auditable:

1. Parse and normalize the source without changing musical identity.
2. Choose a global transposition that balances range, register, source
   displacement, and printed key-signature burden.
3. Assign source voices to quartet instruments with provenance.
4. Add only explicitly enabled source-preservation or editorial layers.
5. Export MusicXML, MP3, and PDF review material.
6. Run clean notation cleanup for review PDFs.
7. Run score/audit checks and record the result in TSV or Markdown reports.

Repeated director comments are promoted into this workflow only after they can
be stated as a rule, checked on the corpus, and covered by tests or export
validation.

## Global Transposition

1. Choose a global transposition automatically unless the caller forces one.

   The reducer tests candidate transpositions and scores them against the
   target ensemble.  The default search covers `-18` to `+6` semitones.

2. Favor playable ranges and preferred registers.

   Long notes matter more than short notes in the transposition score, because
   sustained structural tones expose range problems more strongly than passing
   tones.

   Preferred register is treated as a first form of instrumental sweet-spot
   modeling. A note can be technically in range and still be a poor default
   placement if it pushes the cello too high, leaves the viola in constant
   ledger lines, or makes the violins carry material in an unnecessarily harsh
   register.

3. Prefer simpler printed key signatures among near-equivalent choices.

   Once the best range/register candidate is known, another candidate can
   replace it only when the tessitura score remains essentially tied and the
   printed key signature becomes substantially lighter.  The current rule uses
   duration-weighted average `abs(sharps)` as the key burden, so a move from six
   sharps/flats to one matters much more than a cosmetic one-step change.

   The production guardrail is deliberately conservative: the cleaner-key
   candidate must be within `0.05` of the best range/register score, must reduce
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

## Instrument Ranges and Sweet Spots

1. Range is a hard constraint; sweet spot is a cost.

   Notes outside the practical instrument range are rejected. Notes inside the
   range are still evaluated for whether they sit naturally on the target
   instrument.

2. Octave movement preserves pitch class but changes instrumental meaning.

   The reducer may move source notes by octave to make them playable. This is
   not considered a harmonic change, but it is still an editorial choice
   because it changes color, spacing, and line shape.

3. The cello should not become a spare tenor instrument by default.

   Cello assignments are judged against the bass function and the instrument's
   normal color. High cello writing is allowed when it preserves the true lower
   source line or a musically exposed gesture, but not merely because the cello
   happens to be idle.

4. Viola readability is part of the reduction.

   Sustained high viola writing may require treble clef in review output. This
   is an engraving decision, but it reflects the same principle: a good
   reduction must be readable by the players for whom it is written.

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

## Take 6 Close-Harmony Variant

This optional variant is enabled by `build_take6_quartet_score(...)` or
`reduce_take6_to_quartet(...)`.

The detailed Take 6 rule set is kept separately in
[`take6_reduction_rules.md`](take6_reduction_rules.md). The summary below is
only the short version.

1. Keep the output target explicit.

   The target is still a four-part string quartet. If the source contains five
   or six simultaneous pitch classes, the reducer must choose which colors to
   keep rather than trying to represent the complete chord.

2. Preserve soprano and bass as anchors.

   The highest source voice remains Violin I and the lowest source voice
   remains Cello. The special rule is applied to the four middle voices.

3. Prefer jazz guide tones and color tones in dense sonorities.

   When the active source sonority has more than four pitch classes, candidate
   middle notes are ranked by their interval above the bass. Thirds, sevenths,
   altered tones, ninths, and thirteenths are favored over redundant roots and
   fifths.

4. Keep the decision source-traceable.

   Selected notes still come from real source events. The variant changes the
   local priority order; it does not invent replacement jazz harmony.

5. Use source double-stops conservatively when requested.

   With `add_source_double_stops=True`, added notes still have to be real source
   notes and pass the string double-stop playability check. The normal priority
   is to recover missing pitch classes. On long homorhythmic attacks, the rule
   can also keep playable source octave doublings so a sustained six-voice
   sonority retains its weight even when it contains only four pitch classes.

6. Disable Renaissance missing-third completion by default.

   `add_editorial_thirds` defaults to `False` for this entry point, because
   Take 6-style voicings can be suspended, quartal, altered, or rootless, and a
   generated triadic third would often be the wrong editorial assumption.

7. Keep the Take 6 cello in its sweet spot when possible.

   After the source-derived quartet texture is built, cello pitches at G3 or
   above are lowered by one octave when the shifted note stays inside cello
   range and any resulting double-stop remains conservatively playable. This
   keeps pitch classes and harmonic coverage while avoiding a cello part that
   lives unnecessarily in tenor register.

8. Treat beat readability as a review-stage constraint.

   Take 6 review outputs now run an additional beat-readability cleanup that
   merges tied same-pitch slivers, consecutive rests, and tiny final release
   rests when the sounding pitch content is unchanged. The same pass may switch
   sustained high viola passages to treble clef. Dense bars with many attacks
   are audited but not automatically thinned, because removing notes would be a
   musical reduction decision rather than an engraving correction.

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

## Review and Notation Cleanup

1. The clean review score is part of the method.

   MusicXML that is technically valid can still be hard to read. Review PDFs
   therefore run cleanup passes for redundant accidentals, tied-continuation
   accidentals, dangling ties or slurs, final barlines, clef changes, and
   other notation artifacts.

2. Accidentals follow the musical key context before chromatic convenience.

   Notes that belong to the active key signature should use that spelling:
   for example A-flat in E-flat major, not G-sharp. In flat-side harmonic
   contexts, local chromatic notes should also prefer flat spellings when that
   is the clearer reading. The reviewed case is `Luci serene e chiare`, where
   C-sharp spellings are forced to D-flat after the generic chromatic spelling
   pass, so the conductor score, part XMLs, and rebuilt PDFs remain consistent.
   The same principle is used in `Dolcissima mia vita`, where D-sharp spellings
   are forced to E-flat. Some reviewed cases override the general flat-side
   preference when the melodic motion reads more clearly as a leading-tone or
   chromatic ascent: in `S'io non miro non moro`, the Cello E-flats in bars 6
   and 11 are written as D-sharps, and the bar 27 Cello A-flat is written as
   G-sharp. In `Sparge la morte`, the reviewed piece-wide policy is D-flat
   instead of C-sharp, G-flat instead of F-sharp, and D-sharp instead of
   E-flat.

3. Automatic cleanup must not hide musical decisions.

   Engraving cleanup may merge tied same-pitch fragments, simplify rests, or
   improve clefs when the sounding music is unchanged. It should not remove
   attacks, thin dense bars, or invent contrapuntal material without becoming a
   named reduction rule.

4. Rests are simplified, not over-notated.

   Adjacent rest fragments may be merged, and tiny final release rests may be
   absorbed into the preceding note when the sounding pitch content remains
   acceptable. Rests are not split merely to show every beat boundary. A long
   note that starts clearly on the beat does not need to be subdivided only for
   beat readability. When a run of adjacent rests cannot be represented as a
   single standard rest, it is rewritten as the shortest standard sequence
   available; for example, the five-quarter rest span in `Dolcissima mia vita`
   bar 13 cello becomes a whole rest plus a quarter rest. In bar 14, a
   redundant isolated Violin II B-flat 16th already covered by Violin I is
   removed and the resulting rest is merged into a quarter rest. In `Già piansi
   nel dolore` bar 8, the cello's dotted-eighth C is lengthened to a quarter
   note and the trailing rest fragments are collapsed to one quarter rest. In
   bar 27, the low G is removed from the Violin II double stop and the later E
   is lengthened from a 16th to an eighth. In bars 45 and 48, successive eighth
   rests are merged into quarter rests where they only add notation clutter;
   bar 45 preserves the surrounding hairpin directions. In bar 50, Viola and
   Cello full-bar rest fragments are collapsed to measure rests. In bar 51,
   the lower Viola E is moved from a double stop to Violin II as a quarter note;
   in bar 57, the lower Viola double-stop notes D and G move to Violin II as
   eighth notes. In `S'io non miro non moro` bar 18, the Viola A 16th absorbs
   the following 16th rest and becomes an eighth note. In `Moro, lasso, al mio
   duolo`, reviewed short terminal fragments are lengthened without consuming
   the whole remaining silence: bar 7 Violin II D becomes an eighth, bar 7
   Viola G and Cello B become quarters, bar 9 Cello F becomes a quarter, and bar
   33 Viola A is notated as a 16th tied to an eighth tied into the following
   half note, with the preceding G and the two A fragments beamed as 16-16-8 so
   both the internal subdivision and beat 2 remain readable. In bar 33, the
   lower Viola E from the double stop moves to Violin II as an eighth note so
   the Violin II line continues B-E-F-G while Viola keeps the upper G. In
   `Sparge la morte`, bar 19 Cello D is split from a half note into two tied
   quarter notes so the beat boundary is visible.

5. Keep register corrections pitch-class preserving.

   Local octave repairs may move a note by octave when the notated register is
   visibly wrong or unnecessarily awkward and the pitch class remains unchanged.
   The reviewed case is `S'io non miro non moro` bar 20, where the high Violin I
   E-flat is lowered by one octave.

6. Clefs should avoid one-note flicker.

   Cello defaults to bass clef. Tenor or treble clef is reserved for sustained
   high passages, not isolated high notes in the middle of a phrase. Viola
   defaults to alto clef; treble clef is only for unusually high sustained
   writing.

7. Imported text is removed unless it is musical tempo information.

   Review and concert scores keep the title, composer, and beginning tempo
   indications, but remove imported vocal-edition page numbers, lyrics, edition
   labels, and other non-playing annotations.

7. Director comments become rules only when generalizable.

   A repeated problem should be stated as a musical rule, tested on examples or
   export validation, and recorded in the rule documentation. One isolated
   preference can remain a manual editorial note.

## Editorial Dynamics

1. Dynamics are an optional notation layer.

   They do not alter source rhythm or note choice.
   Take 6 reductions disable this layer by default because the generated marks
   proved more misleading than helpful for the close-harmony material.

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

4. The AI system explains tradeoffs; it does not eliminate judgment.

   The reducer can detect conflicts, rank alternatives, and make decisions
   repeatable. It cannot decide alone whether a particular loss of a middle
   voice is musically acceptable in performance.

5. The best rule is still listening.

   The comparison renders are part of the method: suspicious bars should be
   inspected in both notation and audio, then turned into explicit rules only
   when the musical reason is clear.
