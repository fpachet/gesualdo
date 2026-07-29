# YAML Rule Format

The files in `rules/` are structured rule specifications for the Gesualdo
reduction project. They are intended to be readable by humans and strict enough
for a future clean-room reducer to parse without importing the current Python
implementation.

## Top-Level Structure

Reduction rule files use this shape:

```yaml
version: 1
name: gesualdo
description: >
  Human-readable summary of the rule file.
target_ensemble: string_quartet
source_idiom: gesualdo_madrigal
imports:
  - shared_quartet.yaml
metadata:
  generated_from_project: gesualdo
  generated_date: "2026-07-04"
  extraction_status: draft
  source_files_inspected: []
passes: []
priorities:
  hard_constraints: []
  optimization_pressures: []
  optional_enrichments: []
rules: []
validation:
  required_checks: []
  expected_metrics: []
```

`rules/evaluation_corpus.yaml` has a related but corpus-oriented format. It
lists corpora, baseline reports, review artifacts, audit reports, and pilot
subsets.

## Rule Fields

Every rule has these required fields:

- `id`: stable snake_case identifier.
- `title`: short human-readable title.
- `scope`: one value from the approved scope vocabulary.
- `priority`: one value from the approved priority vocabulary.
- `action`: snake_case action name that a future reducer could implement.
- `parameters`: object containing thresholds, flags, modes, and rule data.
- `rationale`: short explanation of why the rule exists.
- `evidence`: object with `docs`, `code`, `reports`, and `examples` lists.
- `exceptions`: list of named exceptions, empty when none are known.

Optional fields include `applies_to`, `pass`, and `metrics`.

## Scope Vocabulary

Allowed scopes are:

- `source_parsing`
- `source_event_model`
- `global_transposition`
- `voice_mapping`
- `outer_voice_assignment`
- `inner_voice_compression`
- `event_selection`
- `pitch_class_coverage`
- `chromatic_motion`
- `dissonance_preservation`
- `harmonic_role_priority`
- `register_placement`
- `instrument_range`
- `instrument_sweet_spot`
- `texture_density`
- `source_voice_restoration`
- `borrowing`
- `double_stops`
- `editorial_generation`
- `fragment_pruning`
- `continuity_repair`
- `notation_cleanup`
- `musescore_compatibility`
- `provenance`
- `validation`
- `evaluation`

Add a new scope only when the existing vocabulary cannot name the behavior, then
update `schemas/reduction_rules.schema.json` and
`scripts/validate_reduction_rules.py`.

## Priority Semantics

- `hard`: must not be violated unless the score is rejected.
- `very_high`: violated only under severe conflict.
- `high`: strong default preference.
- `medium`: ordinary cost or weight pressure.
- `low`: tie-breaker or weak preference.
- `optional`: enabled only by a named mode or parameter.

A future interpreter should treat `hard` rules as validation gates. Other
priorities are optimization pressures unless the action name explicitly says
otherwise.

## Action Names

Actions are named operations, not executable code. Use snake_case names such as:

- `require_target_parts`
- `score_global_transposition_candidates`
- `increase_weight_for_uncovered_pitch_classes`
- `allow_source_based_double_stops`
- `normalize_musescore_rhythm_artifacts`

Do not put Python expressions or lambdas in YAML. Put implementation details in
the future interpreter, and keep the YAML declarative.

## Parameters

Parameters should expose concrete values when the current project has them:

```yaml
parameters:
  tessitura_tolerance: 0.05
  minimum_absolute_key_burden_improvement: 2.0
```

When the current reducer uses procedural scoring without a single exposed
number, mark it honestly:

```yaml
parameters:
  semitone_motion_bonus:
    value: null
    status: underspecified
    note: "Current implementation does not expose one scalar bonus."
```

This is intentional. The YAML is a bridge to a clean-room reducer, not a claim
that all tacit procedural judgment is already solved.

## Evidence Format

Evidence is grouped by kind:

```yaml
evidence:
  docs:
    - path: docs/reduction_rules.md
      note: "Human-facing description."
  code: []
  reports:
    - path: outputs/reports/part_coherence_audit.tsv
      note: "Corpus audit data."
  examples:
    - piece_id: hark_herald
      note: "Borrowed-line continuity case."
```

The `code` evidence list is kept for schema compatibility but should stay empty
in clean-room-facing rule files. Evidence paths are checked by
`scripts/validate_reduction_rules.py`. Missing paths are warnings by default,
because some review artifacts may be generated outside a lightweight checkout.

## Exceptions

Exceptions are named and explained:

```yaml
exceptions:
  - id: range_conflict
    description: "Preserve pitch class by octave displacement."
```

Exceptions should not silently cancel a hard rule. If an exception changes a
validation outcome, make that behavior explicit in the action or parameters.

## Validation

Run:

```bash
python scripts/validate_reduction_rules.py
```

or:

```bash
uv run python scripts/validate_reduction_rules.py
```

The validator loads all YAML files in `rules/`, checks schema-critical fields,
checks imports, rejects duplicate rule IDs within a file, and warns about
missing evidence paths.

## Adding Rules

1. Choose the most specific existing rule file.
2. Add a stable snake_case `id`.
3. Use an existing scope when possible.
4. Use a named declarative action.
5. Put thresholds and flags in `parameters`.
6. Cite at least one doc, code, report, or example when possible.
7. Mark procedural or uncertain knowledge as underspecified.
8. Run validation and regenerate the summary:

```bash
python scripts/summarize_reduction_rules.py --output docs/yaml_rule_summary.md
```
