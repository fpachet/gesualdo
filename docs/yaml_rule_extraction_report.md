# YAML Rule Extraction Report

Generated on 2026-07-04 for the existing `gesualdo` project.

## Extraction Boundary

The current implementation, reduction scripts, tests, documentation, generated
reports, and review artifacts were inspected during extraction. The emitted rule
YAML files intentionally do not cite implementation source files, reducer
scripts, or tests. Their evidence sections cite human-readable docs and
data/report artifacts only.

This boundary is deliberate:

- numeric weights and thresholds extracted from implementation behavior are part
  of the specification;
- source-code paths and test paths are not part of the clean-room-facing rule
  specification;
- data manifests, reduction reports, render reports, and review PDFs remain
  valid as evaluation inputs and baseline comparison material.

The generated octave optimization directory contains 2,580 per-piece files in
this checkout. The YAML cites summary and representative report paths rather
than every generated artifact.

## Generated Files

Rule and corpus files:

- `rules/shared_quartet.yaml`
- `rules/gesualdo.yaml`
- `rules/take6.yaml`
- `rules/evaluation_corpus.yaml`

Schemas:

- `schemas/reduction_rules.schema.json`
- `schemas/evaluation_corpus.schema.json`

Tools:

- `scripts/validate_reduction_rules.py`
- `scripts/summarize_reduction_rules.py`

Documentation:

- `docs/yaml_rule_format.md`
- `docs/yaml_rule_extraction_report.md`
- `docs/yaml_rule_summary.md`

## Rule Counts

- `rules/shared_quartet.yaml`: 14 rules
- `rules/gesualdo.yaml`: 14 rules
- `rules/take6.yaml`: 16 rules
- `rules/evaluation_corpus.yaml`: corpus metadata, no reduction rules

Total reduction rules: 44.

## Extracted As Explicit Parameters

The second extraction pass promoted additional concrete parameters into YAML,
including:

- local assignment weights: voice continuity `10.0`, initial order `3.0`, range
  displacement `1.0`, register fit `0.1`;
- register and sweet-spot formulas, including preferred-register and octave
  displacement costs;
- global transposition two-stage scoring: bounded first-stage range/register
  cost, key-signature exclusion from stage 1, octave-folding displacement,
  source-displacement regularizer `0.12`, high-positive color penalty above
  `+3`, instrument register weights, and cleaner-key stage-two tolerance
  `0.35`;
- bottom-target borrowing guard: reject borrowed non-anchor cello candidates
  above MIDI `60` while allowing true bottom-anchor material after octave
  fitting;
- Take 6 interval-above-bass weights for roots, fifths, thirds, sevenths,
  altered tones, ninths, and thirteenths;
- Take 6 dense-sonority root/fifth penalty `-4.0`, dense-sonority bonus `1.0`,
  and chromatic/tritone adjacency bonus `0.75`;
- conservative double-stop intervals, string tunings, minimum overlap duration
  `0.5`, and long-held source-doubling threshold `2.0`;
- short note/rest artifact total duration `1.0`, snap durations, simple
  denominators, and maximum snap delta `1/12`;
- MuseScore grid cleanup duration `1/4`, maximum delta `1/3`, and safe
  denominators;
- review notation cleanup predicates for same-pitch tied merges, consecutive
  rest merges, tiny release-residue absorption or beat-boundary shifting, rest
  splitting at beat boundaries, dangling-tie repair, tied-continuation
  accidental suppression, and high cello/viola clef thresholds;
- editorial dynamic energy weights: active parts `0.35`, attack density `0.30`,
  register `0.20`, and span `0.15`.

## Grounded Mainly In Docs Or Review Experience

Some musical priorities are explicit in project docs and review history but
remain only partly formalized:

- Gesualdo chromatic motion, false relations, cross-relations, and
  suspension-like events as structural material.
- Avoiding the smoothing of dissonance.
- The director-review process as a way to promote repeated observations into
  repeatable checks.
- Take 6 quartet color as a reason for reviewed transposition overrides.
- The musical distinction between close-harmony color tones and redundant
  roots/fifths.

These rules are represented declaratively. The generated YAML summary currently
reports no parameters marked `underspecified` or `partially_procedural`, but
the items above remain musical abstractions rather than exact source-code
translations.

## Inferred From Outputs And Reports

The evaluation corpus file and several validation rules cite generated reports:

- CPDL five-voice and six-voice reduction reports.
- Take 6 double-stop reduction report.
- Beach Boys four-voice comparison report for the concert prologue baseline.
- PDF review reports.
- Part-coherence, beat-readability, transposition/key-signature, and octave
  optimization audit outputs.

These reports ground which corpora and baseline outputs a clean-room experiment
should use, but they do not by themselves define all of the decision logic.

## Hard To Express Declaratively

The most difficult behaviors still not fully expressed in YAML are:

- The exact tradeoff between continuity, fresh attacks, harmonic coverage,
  duplicate pitch-class suppression, and target register.
- Detecting Gesualdo false relations or suspension-like events as explicit
  symbolic categories.
- Borderline Take 6 harmonic-role classification when interval labels do not
  capture the perceived function of a color tone.
- Deciding when a double-stop is musically useful rather than merely possible.
- The relationship between octave placement, quartet color, and perceived
  idiomatic string writing.
- Review-driven judgments that become rules only after enough corpus evidence
  accumulates.

The YAML now states these as explicit rules or remaining review judgments
rather than hiding them as source-code references.

## Remaining Tacit Procedural Knowledge

The current reducer still contains tacit procedural knowledge, especially:

- Candidate generation and scoring inside source-event assignment.
- How competing constraints are combined into one local decision.
- How event windows are chosen and clipped.
- How source borrowing interacts with part identity over longer spans beyond
  the explicit borrowed-neighbor and bottom-register guards.
- Future MuseScore/import edge cases that are not covered by the currently
  listed cleanup predicates.

A clean-room project can use the YAML as an implementation target, but it should
expect to reconstruct remaining scoring details experimentally from the
evaluation corpus and baseline outputs.

## Validation And Summary

Validated successfully with:

```bash
uv run python scripts/validate_reduction_rules.py
```

Result:

```text
Validated 4 YAML files in /Users/francoispachet/IdeaProjects/gesualdo/rules
Evidence warnings: 0
```

Summary generated successfully with:

```bash
uv run python scripts/summarize_reduction_rules.py --output docs/yaml_rule_summary.md
```

Result:

```text
Wrote docs/yaml_rule_summary.md
```

The validator uses `jsonschema` when installed and otherwise applies equivalent
project-specific checks directly. The scripts use Python YAML support when
available and fall back to the local Ruby YAML parser in minimal `uv run`
environments.

## Guidance For The Clean-Room Project

Use the YAML as a specification boundary, not as a drop-in replacement for the
current reducer. Start with the hard constraints:

- parse only expected source voice counts;
- emit exactly four quartet parts;
- preserve source timing, pitch class, and provenance;
- keep ranges valid;
- reject overlaps and overfull measures;
- keep Take 6 source-derived by default.

Then implement weighted preferences in small, testable layers:

- global transposition;
- outer voice anchoring;
- inner voice compression;
- coverage and continuity scoring;
- optional enrichment;
- Take 6 color-tone priority;
- notation cleanup and MuseScore compatibility.

The first clean-room milestone should be a pilot subset, not the whole corpus:
`pilot_gesualdo_5_voice`, `pilot_gesualdo_6_voice`, and `pilot_take6` from
`rules/evaluation_corpus.yaml`.

## Readiness

The YAML is ready as a cleaner second-pass draft specification for the sibling
clean-room reducer experiment. It no longer cites implementation source files,
reducer scripts, or tests in the rule files. It is still not a complete
mathematical formalization of every procedural scoring decision.
