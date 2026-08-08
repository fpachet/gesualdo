# YAML Reduction Rule Summary

Generated from structured files in `rules/`.

## Rule Counts

| File | Rule count |
| --- | ---: |
| `rules/gesualdo.yaml` | 14 |
| `rules/shared_quartet.yaml` | 15 |
| `rules/take6.yaml` | 17 |

## Rules By Scope

- `borrowing`: 2
  - `allow_idle_outer_borrowing_for_coverage`: Allow idle outer parts to borrow inner material
  - `avoid_high_borrowed_bottom_register`: Avoid high borrowed bottom register
- `chromatic_motion`: 1
  - `preserve_characteristic_chromatic_events`: Preserve chromatic and dissonant events
- `continuity_repair`: 2
  - `continue_source_lines_before_redundant_doubling`: Continue source lines before redundant doubling
  - `smooth_isolated_handoffs`: Smooth isolated handoffs into active lines
- `dissonance_preservation`: 1
  - `avoid_smoothing_dissonance`: Avoid smoothing dissonances
- `double_stops`: 2
  - `allow_source_based_double_stops`: Allow source-based double-stops
  - `preserve_long_source_doublings_with_double_stops`: Preserve long source doublings with double-stops
- `editorial_generation`: 5
  - `allow_editorial_missing_third_completion`: Allow editorial missing-third completion
  - `allow_editorial_support_harmony`: Allow editorial support harmony
  - `disable_editorial_dynamics_for_take6`: Disable editorial dynamics for Take 6
  - `emit_editorial_dynamics_when_enabled`: Emit editorial dynamics only when enabled
  - `prohibit_default_generated_jazz_reharmonization`: Prohibit default generated jazz reharmonization
- `evaluation`: 3
  - `apply_reviewed_take6_tempo_overrides`: Apply reviewed Take 6 tempo overrides
  - `use_director_review_as_constraint_discovery`: Use director review as constraint discovery
  - `use_take6_review_cases_as_regression_corpus`: Use Take 6 review cases as regression corpus
- `fragment_pruning`: 2
  - `penalize_isolated_fragments`: Penalize isolated fragments
  - `trim_tiny_preservation_fragments`: Trim tiny preservation fragments
- `global_transposition`: 3
  - `apply_reviewed_take6_transposition_overrides`: Apply reviewed Take 6 transposition overrides
  - `choose_two_stage_global_transposition`: Choose two-stage global transposition
  - `prefer_simple_key_signature_when_tessitura_tied`: Apply stage-two cleaner-key guardrail
- `harmonic_role_priority`: 2
  - `penalize_redundant_roots_and_fifths`: Penalize redundant roots and fifths
  - `prefer_close_harmony_color_tones`: Prefer close-harmony color tones
- `inner_voice_compression`: 2
  - `compress_five_voice_inner_material`: Compress five-voice inner material
  - `compress_six_voice_inner_material`: Compress six-voice inner material
- `instrument_range`: 1
  - `define_instrument_ranges`: Define instrument ranges
- `instrument_sweet_spot`: 1
  - `define_preferred_registers`: Define preferred registers
- `musescore_compatibility`: 2
  - `normalize_musescore_time_modification_import`: Normalize MuseScore time-modification import
  - `normalize_piece_level_musescore_grid_rhythm`: Normalize piece-level MuseScore grid rhythm
- `notation_cleanup`: 3
  - `apply_reviewed_take6_local_corrections`: Apply reviewed Take 6 local corrections
  - `cleanup_review_notation`: Clean notation for review
  - `normalize_short_note_rest_artifacts`: Normalize short note/rest MIDI artifacts
- `outer_voice_assignment`: 2
  - `preserve_outer_source_voices`: Preserve outer source voices
  - `preserve_soprano_bass_frame`: Preserve soprano and bass frame
- `pitch_class_coverage`: 1
  - `increase_weight_for_uncovered_pitch_classes`: Preserve active pitch classes
- `provenance`: 1
  - `require_source_event_or_editorial_tag`: Preserve source provenance
- `register_placement`: 2
  - `lower_high_cello_register`: Lower high cello register when playable
  - `prefer_pitch_class_preserving_octaves`: Prefer pitch-class-preserving octave movement
- `source_event_model`: 2
  - `preserve_source_rhythm_and_pitch_class`: Preserve source rhythm and pitch class
  - `preserve_source_timing_identity`: Preserve source timing identity
- `source_parsing`: 2
  - `require_exactly_six_take6_source_parts`: Require exactly six Take 6 source parts
  - `require_expected_gesualdo_source_voice_count`: Require expected Gesualdo source voice count
- `source_voice_restoration`: 1
  - `allow_source_voice_restoration`: Allow source-voice restoration
- `validation`: 3
  - `complete_measures_with_rests`: Complete measures with rests
  - `require_four_quartet_parts`: Require four quartet parts
  - `validate_no_overlaps_or_overfull_measures`: Reject overlaps and overfull measures

## Hard Constraints

- `complete_measures_with_rests`: Complete measures with rests
- `define_instrument_ranges`: Define instrument ranges
- `preserve_source_rhythm_and_pitch_class`: Preserve source rhythm and pitch class
- `preserve_source_timing_identity`: Preserve source timing identity
- `prohibit_default_generated_jazz_reharmonization`: Prohibit default generated jazz reharmonization
- `require_exactly_six_take6_source_parts`: Require exactly six Take 6 source parts
- `require_expected_gesualdo_source_voice_count`: Require expected Gesualdo source voice count
- `require_four_quartet_parts`: Require four quartet parts
- `require_source_event_or_editorial_tag`: Preserve source provenance
- `validate_no_overlaps_or_overfull_measures`: Reject overlaps and overfull measures

## Optional Enrichments

- `allow_editorial_missing_third_completion`: Allow editorial missing-third completion
- `allow_editorial_support_harmony`: Allow editorial support harmony
- `allow_source_based_double_stops`: Allow source-based double-stops
- `allow_source_voice_restoration`: Allow source-voice restoration
- `emit_editorial_dynamics_when_enabled`: Emit editorial dynamics only when enabled

## Gesualdo-Specific Rules

- `allow_editorial_missing_third_completion`
- `allow_editorial_support_harmony`
- `allow_idle_outer_borrowing_for_coverage`
- `allow_source_voice_restoration`
- `avoid_smoothing_dissonance`
- `compress_five_voice_inner_material`
- `compress_six_voice_inner_material`
- `increase_weight_for_uncovered_pitch_classes`
- `penalize_isolated_fragments`
- `preserve_characteristic_chromatic_events`
- `preserve_outer_source_voices`
- `preserve_source_rhythm_and_pitch_class`
- `require_expected_gesualdo_source_voice_count`
- `use_director_review_as_constraint_discovery`

## Take 6-Specific Rules

- `allow_source_based_double_stops`
- `apply_reviewed_take6_local_corrections`
- `apply_reviewed_take6_tempo_overrides`
- `apply_reviewed_take6_transposition_overrides`
- `continue_source_lines_before_redundant_doubling`
- `disable_editorial_dynamics_for_take6`
- `lower_high_cello_register`
- `normalize_piece_level_musescore_grid_rhythm`
- `normalize_short_note_rest_artifacts`
- `penalize_redundant_roots_and_fifths`
- `prefer_close_harmony_color_tones`
- `preserve_long_source_doublings_with_double_stops`
- `preserve_soprano_bass_frame`
- `prohibit_default_generated_jazz_reharmonization`
- `require_exactly_six_take6_source_parts`
- `trim_tiny_preservation_fragments`
- `use_take6_review_cases_as_regression_corpus`

## Rules With Missing Evidence

- None detected.

## Likely Underspecified Parameters

- None detected.
