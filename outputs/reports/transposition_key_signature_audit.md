# Global Transposition Key-Signature Audit

This audit checks whether a nearby global transposition would materially reduce the printed key-signature burden while preserving the current instrumental tessitura fit.

Method:
- Candidate window: current transposition +/- 5 semitones.
- Key-signature burden: duration-weighted average of `abs(sharps)` after transposition; lower is easier.
- Tessitura guard: reuse the reducer's existing `score_global_transposition` range/register score.
- A candidate is allowed when its tessitura score is no worse than the current score by max(0.05, 0.1 relative).
- A piece is flagged when the allowed candidate improves key burden by at least 2 and 40%.

## Status Counts

| Status | Count |
| --- | --- |
| no_key_signature_data | 7 |
| ok | 309 |
| source_status_error | 15 |

## Counts By Batch

| Batch | Attention | OK | Other |
| --- | ---: | ---: | ---: |
| cpdl_5_voice_quartet_plus_viole | 0 | 122 | 8 |
| cpdl_5_voice_string_quartet | 0 | 123 | 7 |
| cpdl_6_voice_string_quartet | 0 | 27 | 7 |
| kdf_string_quartet | 0 | 37 | 0 |

## Largest Attention Cases (Top 0)

| Batch | Work | Title | Current | Current burden | Candidate | Candidate burden | Delta | Tessitura delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Full per-piece results are in `transposition_key_signature_audit.tsv`; all candidate scores are in `transposition_key_signature_candidates.tsv`.
