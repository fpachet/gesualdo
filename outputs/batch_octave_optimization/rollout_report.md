# Batch Octave Optimization Rollout

This report summarizes the first broader application of the `A Quiet Place`
octave-optimization and clean-notation workflow.

The pass is intentionally reviewable. It writes optimized candidates under
`outputs/batch_octave_optimization/` and does not replace the active corpus
files under `data/`.

## Method

- Select works with fixable part-coherence audit issues:
  `register_jump`, `dangling_tie`, or `accidental_on_tie_continuation`.
- Optimize octave placement per part while preserving sounding pitch classes.
- Cap changes at 20 per piece for this first broader rollout.
- Run clean-review notation cleanup after optimization.
- Verify sounding pitch-class coverage over time before accepting a candidate.
- Write per-piece change reports and before/after audit comparisons.

## Summary

| Corpus | Rows | Safe Candidates | True Failures | PDF Failures | Octave Changes | Issues Before | Issues After |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Take 6 double-stop quartet | 10 | 8 | 2 | 4 | 175 | 460 | 147 |
| KDF Gesualdo quartet | 37 | 37 | 0 | 0 | 1307 | 2038 | 129 |
| CPDL Gesualdo quartet | 278 | 276 | 2 | 0 | 6293 | 9564 | 844 |

`Safe Candidates` includes MusicXML candidates that passed the coverage
invariant. `PDF Failures` means the MusicXML candidate passed but MuseScore did
not render a PDF in this run.

## Issue Counts

### Take 6 Double-Stop Quartet

| Issue | Before | After |
| --- | ---: | ---: |
| `register_jump` | 269 | 118 |
| `dangling_tie` | 79 | 0 |
| `accidental_on_tie_continuation` | 110 | 27 |
| `sparse_fragment` | 2 | 2 |
| `sparse_window` | 0 | 0 |

Safe candidates: 8 of 10.

True failures:

- `david_et_goliath`: pitch-class coverage invariant mismatch.
- `get_away_jordan`: pitch-class coverage invariant mismatch.

MusicXML-safe candidates with PDF render failure:

- `spread_love`
- `gold_mine`
- `if_we_ever`
- `come_unto_me`

### KDF Gesualdo Quartet

| Issue | Before | After |
| --- | ---: | ---: |
| `register_jump` | 1339 | 129 |
| `dangling_tie` | 402 | 0 |
| `accidental_on_tie_continuation` | 297 | 0 |
| `sparse_fragment` | 0 | 0 |
| `sparse_window` | 0 | 0 |

Safe candidates: 37 of 37.

### CPDL Gesualdo Quartet

| Issue | Before | After |
| --- | ---: | ---: |
| `register_jump` | 6553 | 708 |
| `dangling_tie` | 1673 | 0 |
| `accidental_on_tie_continuation` | 1202 | 0 |
| `sparse_fragment` | 88 | 88 |
| `sparse_window` | 48 | 48 |

Safe candidates: 276 of 278.

True failures:

- Two CPDL rows with `work_id=72`, both failed the pitch-class coverage
  invariant after MusicXML rewriting.

## Interpretation

The cleanup side of the workflow generalized very well: dangling ties and
accidental-on-tie-continuation artifacts were eliminated for all safe Gesualdo
candidates and most safe Take 6 candidates.

The Take 6 baseline now includes the short-trim guard from commit `4534994`
(`Avoid tiny Take 6 rhythm splices`). This rule prevents duplicate-pitch
preservation from clipping a source event into an unreadably short fragment
when the trimmed duration would be less than a triplet eighth.

The octave optimizer strongly reduced register-jump warnings, but it did not
eliminate all of them. This is expected for a conservative first rollout with a
20-change cap per piece and range/register guardrails.

Sparse fragments and sparse windows are unchanged because they require a
different musical repair strategy. They are participation/texture problems, not
octave-placement problems.

## Next Review Step

Before replacing active corpus files, review a shortlist:

- all Take 6 safe candidates, especially those without rendered PDFs;
- several KDF Gesualdo candidates with the largest register-jump reduction;
- representative CPDL five- and six-voice candidates;
- the four true failures, to decide whether the issue is MusicXML serialization
  complexity or an optimizer bug.
