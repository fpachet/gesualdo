# Take 6 Quartet Reduction Rules

This document describes the rules currently used for Take 6-style six-voice
close-harmony sources reduced to string quartet. It is an editorial guide, not
an implementation manual: the goal is to make the musical decisions inspectable
when reviewing the generated score.

For a presentation-level narrative of the complete reduction process and the
director-feedback loop, see
[`reduction_process_overview.md`](reduction_process_overview.md).

The Take 6 reducer is deterministic. It does not learn from examples and it
does not invent jazz harmony by default. Its main difference from the Gesualdo
quartet reducer is that dense vertical color is treated as primary material:
thirds, sevenths, altered tones, and added tones are often more important than
roots and fifths.

## Presentation Summary

The Take 6 problem is not simply "six voices into four instruments." It is a
choice about which musical information survives when close-harmony source
textures contain more notes than the quartet can play literally.

The current answer is:

1. Keep the soprano and bass frame stable.
2. Preserve missing pitch classes before adding duplicates.
3. Prefer guide tones and color tones in dense sonorities.
4. Use source-based double-stops only when they are playable and musically
   useful.
5. Avoid unreadable notation fragments, short isolated double-stops, and
   interrupted borrowed lines.
6. Validate the result as both music and MusicXML/MuseScore material.

The rules below record the successive refinements that came from score
inspection and quartet-director feedback.

## Entry Points

The Take 6 variant is enabled through a separate API:

```python
build_take6_quartet_score(score)
reduce_take6_to_quartet("source.mid", out_path="take6_quartet.musicxml")
```

The batch script exposes the same behavior:

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
  --output-dir data/take6/reductions/string_quartet_double_stops \
  --double-stops \
  --force
```

The output target remains Violin I, Violin II, Viola, and Cello. The reducer is
therefore allowed to compress six source voices, but every copied note remains
traceable to a real source event.

The generated MusicXML title is derived from the source filename when reducing
from a file path. For example, `47 A quiet place, originalrevu.mid` becomes
`A Quiet Place - Reduction for String Quartet`, and `ComeUntoMe.mid` becomes
`Come Unto Me - Reduction for String Quartet`. Leading track numbers and the
`originalrevu` suffix are removed for the generated score titles and output
filenames. Take 6 reductions write the score composer as
`Take 6, arrangement F. Pachet and AI` so exported PDFs and audio renders no
longer inherit the generic Music21 metadata.

## Source Preparation

1. Parse all six source parts.

   Take 6 reductions expect exactly six source parts. The specialized policy
   is intentionally explicit, so a four- or five-part source is not silently
   treated as Take 6 close harmony.

2. Choose a global transposition unless the caller forces one.

   The same transposition machinery as the general reducer is used. Candidate
   transpositions are scored for string range, preferred register, source
   displacement, and key-signature simplicity.

3. Apply reviewed song tempos when known.

   Take 6 tempo overrides live in the independent metadata file
   `data/take6/tempo_overrides.json`. The reducer uses these values after
   generating each score, replacing imported/default MIDI tempos while leaving
   unknown songs untouched until reviewed tempos are available.

4. Normalize isolated MIDI duration artifacts.

   `normalize_short_note_rest_artifacts=True` is the default for Take 6. It
   fixes isolated suspicious note+rest pairs such as `5/12 + 7/12` when their
   total is one quarter note and the note can be snapped to a simple duration
   such as `1/2`. This is deliberately narrow: it cleans MIDI import noise
   without quantizing the whole source.

   It also absorbs tiny intra-voice gaps of at most `1/12` quarter note when
   they occur directly between two notes in the same source line. The following
   note is started at the tiny-rest offset and lengthened to keep the same end
   point. This was added for `He Never Sleeps`, measure 22, where the top source
   voice contained `1/3 + 1/3 + 1/12 rest + 3/4`; the reduction now prints the
   opening as continuous source notes instead of exposing the micro-rest.

   The same normalizer trims tiny note-to-note overlaps of at most `1/12`
   quarter note inside one source voice. This was added for `He Never Sleeps`,
   measure 27, where a `1/3` source note overlapped the following chord by
   `1/12`, causing the quartet to print a strange `1/3` note followed by a
   `5/12` rest. The earlier note is now shortened to the following onset, so
   the following source attack can be represented normally.

5. Strip MuseScore-problematic explicit time-modification tags.

   The generated MusicXML keeps its exact `<duration>` values and tuplet
   notation brackets, but the Take 6 pipeline removes music21-written
   `<time-modification>` tags before saving final MusicXML files. MuseScore
   Studio can otherwise over-count certain mixed tuplets and report corrupted
   measures, as in `Come Unto Me`, measures 26 and 32, staff 2. This is an
   import-compatibility pass rather than a rhythmic quantization pass.

6. Use a piece-specific MuseScore grid fallback only where needed.

   `If We Ever` still triggered raw MuseScore "incomplete measure" warnings
   after the tag-level compatibility pass, notably in measures 9, 25, 35, 55,
   57, 82, 91, 107, and 117. For that song only, the batch Take 6 generator
   now runs a dynamic-programming measure optimizer that keeps each affected
   measure total unchanged while replacing non-dyadic MIDI residues with nearby
   quarter-grid durations. This is deliberately not applied corpus-wide because
   it is more rhythmically invasive than the normal tiny-artifact cleanup.

7. Prefer the MIDI part that carries real time signatures.

   Some corrected Take 6 MIDI files carry time-signature changes only in the
   first source part, while the remaining parts parse as uninterrupted 4/4
   measures. The bar-map builder now treats the part with non-initial
   time-signature events as authoritative. This fixed `Hark Herald`, where a
   real 2/4 bar at measure 22 was previously merged with naive 4/4 measures
   from the other parts, causing a stutter/repeated phrase at measures 22-23.

8. Preserve exact offsets and durations after cleanup.

   The reducer does not rebuild the piece on a new rhythmic grid. It copies
   source offsets and durations, splitting only where notation or double-stop
   construction requires it.

9. Smooth tiny output-only rhythm scars.

   After source selection, a string part may still contain tiny notation scars
   created by switching between source voices: adjacent same-pitch slivers, or
   a `1/12` generated rest that prevents a near-quarter note from printing as a
   simple quarter. The measured-part writer now merges adjacent same-pitch
   fragments and absorbs a tiny generated rest when doing so turns an awkward
   duration into a simple one. This is not a global quantizer; it is a final
   monophonic readability pass.

   This was added for `Come Unto Me`, measure 32. Violin II previously printed
   a `2/3 + 1/4 + 1/12 rest` scar before the next attack. The current reduction
   prints the passage as ordinary `D5` quarter, repeated `B3` quarter/eighth,
   and `D5` eighth material.

## Structural Voice Mapping

1. Preserve outer source voices as anchors.

   The highest source voice by median pitch is assigned to Violin I. The lowest
   source voice by median pitch is assigned to Cello. These outer voices define
   the melodic top and bass frame.

2. Compress the four middle voices into available quartet capacity.

   The four internal source voices are selected into Violin II, Viola, and any
   idle outer capacity that can be borrowed safely.

3. Keep source identity in the selected notes.

   Output notes carry source-event provenance. This matters because the Take 6
   reducer often chooses among several enharmonically or registrally close
   alternatives; the score should remain auditable.

## Dense Chord Priority

1. Prefer missing pitch classes before duplicate pitch classes.

   At each source onset, the first priority is to cover pitch classes that are
   not already sounding in the reduction.

2. Rank dense sonorities by color above the bass.

   When the active source sonority contains more than four pitch classes,
   candidates are scored by their interval above the bass. The current priority
   favors:

   - thirds;
   - sevenths;
   - tritones and altered tones;
   - ninths and thirteenths;
   - then roots and fifths.

3. Penalize redundant roots and fifths in dense chords.

   In a six-voice close-harmony chord, keeping another root or fifth is often
   less valuable than keeping a third, seventh, sharp five, flat five, ninth, or
   thirteenth. The rule is not a chord-label parser; it is a local interval
   heuristic relative to the active bass.

4. Favor dissonant color that clarifies the sonority.

   Candidate tones get a small reward when they make semitone or tritone
   relationships with already covered pitch classes. This helps preserve the
   bite of altered Take 6 voicings.

## Voice Continuity

1. Continue an existing source line when possible.

   If a candidate can continue the same source part on the same target string,
   that continuity can outrank a purely vertical choice.

2. Avoid doubling guide tones without need.

   Duplicating thirds or sevenths is penalized more heavily than duplicating a
   root or fifth when the duplicate does not preserve an important line.

3. Prefer new attacks over tied continuations.

   A newly articulated source note is generally more audible as contrapuntal
   information than a held continuation, all else equal.

4. Preserve source voice count up to quartet capacity.

   `preserve_active_voice_count=True` is the Take 6 default. It tries to keep
   active source voices represented, capped by the available four quartet
   parts before optional double-stops are considered.

5. Avoid tiny trimmed preservation fragments.

   Preserving active source voices must not create unreadable splice rhythms.
   When a duplicate-pitch preservation candidate would be trimmed to less than
   a triplet eighth (`1/3` quarter note), the Take 6 reducer keeps the full
   source event instead of creating the tiny clipped fragment. This favors a
   stable readable line over a momentary voice-count repair.

   This rule was introduced for `A Quiet Place`, measure 18. The earlier
   reduction spliced a straight eighth-note inner voice into a triplet-tied
   line, creating a `1/6`-quarter Violin II fragment. The current reduction
   keeps the straight eighth-note source line through the second half of the
   measure, removing the visual rhythmic scar while still using real source
   notes.

6. Keep borrowed source lines continuous through duplicate pitch classes.

   A duplicate pitch class is normally lower priority than missing harmonic
   material, but it can still be the right choice when it continues the same
   source part on the same quartet instrument. In that case the reducer
   reserves the continuing target before matching other preservation
   candidates. This was added for `Hark Herald`, measures 2-3, where the cello
   had already borrowed a lower source line at the end of measure 2; the next
   two lower notes duplicate upper pitch classes, but keeping them avoids an
   awkward stop-and-reenter cello gesture.

7. Keep the cello out of high borrowed duplicate material.

   The cello may still carry the true lowest source voice, and it may still
   borrow material when this is needed for missing harmonic coverage. But in
   Take 6 reductions it should not act as spare high-register capacity for a
   duplicate pitch class already covered above. Borrowed cello duplicates above
   C4 are therefore rejected. This was added for `Come Unto Me`, measure 7,
   where the cello had copied Violin I's high C5 line after the real lower
   voices rested. The current reduction leaves the cello resting there instead
   of pushing it far outside its normal color.

## Optional Source Double-Stops

This layer is enabled with `add_source_double_stops=True` or the CLI
`--double-stops` flag.

1. Added double-stop notes must come from real source events.

   This layer does not invent notes. It only restores notes that were present
   in the source and omitted by the four-part compression.

2. Recover missing pitch classes first.

   If the active source sonority has more pitch classes than the quartet
   currently covers, double-stops try to add the best missing colors.

3. Preserve long homorhythmic doublings when useful.

   When a source attack is homorhythmic, has more source notes than quartet
   instruments, and lasts at least two quarter notes, the reducer may also add
   playable duplicate pitch classes. This keeps sustained six-voice sonorities
   from collapsing into a thin four-note texture when the extra source notes
   are octave or register doublings.

4. Do not add very short isolated double-stops.

   Optional source double-stops must overlap their host note for at least a
   half quarter note. Shorter source attacks stay monophonic in the quartet
   line. This was added after `He Never Sleeps`, measure 27, where a quarter-note
   source chord produced an awkward one-off Violin I double-stop.

5. Do not densify short passing attacks with duplicate pitch classes.

   Duplicate-pitch-class double-stops are not added for short attacks. The goal
   is to preserve sustained sonority, not to make every transient verticality
   heavier.

6. Preserve exposed omitted melodic pickups.

   There is one narrow exception to the previous rule. If a source voice is not
   otherwise represented, enters with real melodic motion, and can be attached
   as a playable double-stop, the reducer may preserve it even when its pitch
   class is already present elsewhere. This protects short audible pickups from
   disappearing merely because another voice covers the same pitch class in a
   less melodic register.

   This rule was introduced for `He Never Sleeps`, measure 9. The fourth source
   voice has an `E` to tied `F-sharp` pickup, transposed in the quartet output
   to `F` to `G`. Earlier reductions omitted this line because those pitch
   classes were already covered by lower voices. The current reduction keeps it
   as a playable double-stop and lets the `G` continue alone when the host note
   releases.

7. Keep at most two simultaneous notes on one string part.

   The MusicXML writer accepts only real double-stops here, not triple-stops or
   independent polyphonic voices inside one string part.

8. Require conservative playability.

   A double-stop candidate must fit the target instrument range and pass a
   simple adjacent-string check. The current accepted intervals are:

   ```text
   3, 4, 5, 6, 7, 8, 9, 12, 15, 16 semitones
   ```

   The check also uses approximate string positions and rejects stretches that
   are too wide for this conservative model.

9. Split host notes only when notation remains simple.

   A longer already-selected note may be split so a shorter source note can be
   attached as a double-stop. This can happen at the host onset or inside an
   already-sounding host note. If the source note continues after the host
   releases, the overlapping portion is written as a double-stop and the tail
   continues as a single note. The split is allowed only when all resulting
   durations have simple denominators:

   ```text
   1, 2, 3, 4, 6, 8
   ```

   This avoids MusicXML fragments such as `5/12` that MuseScore may flag as
   corrupt or awkward.

## Editorial Harmony

1. Missing-third completion is disabled by default.

   `add_editorial_thirds=False` for Take 6 because close-harmony, altered,
   suspended, or rootless sonorities should not be completed with a Renaissance
   triadic rule.

2. Generated harmony is not part of the default Take 6 behavior.

   `add_editorial_harmony=False` by default. The preferred Take 6 strategy is
   to preserve source color, not to generate substitute harmony.

3. If editorial harmony is enabled, it remains marked.

   Generated notes are still tagged internally as generated events, separate
   from copied source notes.

## Current Generated Set

The current Take 6 web/review set contains 10 double-stop quartet reductions:
`Spread Love`, `Gold Mine`, `A Quiet Place`, `He Never Sleeps`,
`David et Goliath`, `Get Away Jordan`, `If We Ever`, `Hark Herald`,
`I'm On My Way`, and `Come Unto Me`. `A_quiet_place_joined.mid` is treated as
an intermediate/alternate source and is not included in the active report.

The current Take 6 double-stop reduction of `A Quiet Place` uses global
transposition `+3`.

With `--double-stops`, the long-homorhythmic doubling rule currently affects
these onsets:

| Measure | Result |
| --- | --- |
| 1 | Six source notes retained over four pitch classes |
| 6 | Six source notes retained over four pitch classes |
| 18 | Five source notes retained over four pitch classes |
| 40 | Five source notes retained over four pitch classes |
| 47 | Final six-note sonority retained over four pitch classes |

The final chord after transposition is:

```text
G2, B3, D4, G4, A4, D5
```

It contains six source notes but four pitch classes. The double-stop layer keeps
the extra `D` and `G` doublings because the chord is long, homorhythmic,
source-based, and playable under the current conservative model.

## Validation

1. Measures must remain complete.

   Generated rests fill gaps, and every measured part is validated after
   construction.

2. No overlapping incompatible fragments are allowed.

   A part may contain one note or one two-note chord at a given offset. Partial
   overlaps that would require independent voices inside a string part are
   rejected.

3. Every note must have provenance.

   Source notes carry source-event IDs. Double-stop chords carry the source
   IDs of both source events. Generated editorial notes, if enabled, are marked
   separately.

4. MuseScore export is part of practical validation.

   The Take 6 generated MusicXML is checked by exporting with MuseScore when
   practical, because notation-valid MusicXML can still expose reader-specific
   duration or chord issues.

5. Rule changes should have regression tests.

   Repeated musical problems are converted into small tests when possible:
   missing melodic pickups, tiny preservation fragments, micro-rest cleanup,
   overlap cleanup, short double-stop rejection, mixed time-signature mapping,
   and borrowed-line continuity all have focused checks or export validation.

6. Presentation traceability is part of the artifact.

   Improvements are recorded in `docs/development_log.md`; the higher-level
   story is summarized in `docs/reduction_process_overview.md`; exported PDF
   cleanup counts are recorded in
   `data/take6/renders/string_quartet_double_stops_pdf/review_pdf_report.tsv`.

## Known Limits

1. The dense-chord rule is local.

   It does not solve a global harmonic analysis. A local bass-relative color
   heuristic can still choose a tone that is defensible locally but not ideal
   for a larger phrase.

2. Double-stop playability is conservative and approximate.

   The model checks adjacent strings, interval class, range, and rough finger
   distance. It does not know all idiomatic exceptions a string player might
   accept.

3. Long homorhythmic doubling uses a fixed duration threshold.

   The current threshold is two quarter notes. This works well for sustained
   Take 6 sonorities, but it may need tuning for faster pieces or different
   meters.

4. Enharmonic spelling comes from the notation pipeline.

   The reducer reasons mostly in MIDI pitch and pitch class. Some enharmonic
   spelling choices may still need review in MuseScore.
