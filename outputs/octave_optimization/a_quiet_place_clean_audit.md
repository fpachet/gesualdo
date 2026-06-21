# Quartet Part-Coherence Audit

This audit flags likely awkward reading spots in generated MusicXML reductions. It is intentionally observational: it does not rewrite the music.

Checks:
- `register_jump`: melodic movement of at least the configured interval between successive written events in the same part.
- `sparse_fragment`: a short island of notes after or before a long silence.
- `sparse_window`: very low participation density over a multi-bar window.
- `dangling_tie`, `dangling_slur`, `accidental_on_tie_continuation`: conservative notation-structure flags.

## Issue Counts

| Kind | Count |
| --- | ---: |

## Counts By Batch

| Batch | Kind | Count |
| --- | --- | ---: |

## Counts By Part

| Part | Kind | Count |
| --- | --- | ---: |

## Highest Priority Examples (Top 0)

| Severity | Kind | Batch | Work | Title | Part | Measure | Detail |
| --- | --- | --- | --- | --- | --- | --- | --- |

Full issue rows are in `part_coherence_audit.tsv`.
