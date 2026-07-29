#!/usr/bin/env python3
"""Validate structured reduction rule YAML files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised by minimal uv envs
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
SCHEMAS_DIR = ROOT / "schemas"
RULE_SCHEMA_PATH = SCHEMAS_DIR / "reduction_rules.schema.json"
EVALUATION_SCHEMA_PATH = SCHEMAS_DIR / "evaluation_corpus.schema.json"

ALLOWED_PRIORITIES = {"hard", "very_high", "high", "medium", "low", "optional"}
ALLOWED_SCOPES = {
    "source_parsing",
    "source_event_model",
    "global_transposition",
    "voice_mapping",
    "outer_voice_assignment",
    "inner_voice_compression",
    "event_selection",
    "pitch_class_coverage",
    "chromatic_motion",
    "dissonance_preservation",
    "harmonic_role_priority",
    "register_placement",
    "instrument_range",
    "instrument_sweet_spot",
    "texture_density",
    "source_voice_restoration",
    "borrowing",
    "double_stops",
    "editorial_generation",
    "fragment_pruning",
    "continuity_repair",
    "notation_cleanup",
    "musescore_compatibility",
    "provenance",
    "validation",
    "evaluation",
}
SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is not None:
        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    else:
        command = [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "puts YAML.load_file(ARGV[0]).to_json",
            str(path),
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        loaded = json.loads(completed.stdout)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: expected mapping at top level")
    return loaded


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: expected JSON object")
    return loaded


def schema_validate_with_optional_dependency(path: Path, data: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ModuleNotFoundError:
        return []

    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{path}: schema: {location}: {error.message}")
    return errors


def require(condition: bool, errors: list[str], message: str) -> None:
    if not condition:
        errors.append(message)


def validate_metadata(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    metadata = data.get("metadata")
    require(isinstance(metadata, dict), errors, f"{path}: metadata must be an object")
    if not isinstance(metadata, dict):
        return
    for key in ("generated_from_project", "generated_date", "extraction_status", "source_files_inspected"):
        require(key in metadata, errors, f"{path}: metadata.{key} is required")
    require(metadata.get("extraction_status") in {"draft", "reviewed", "validated"}, errors, f"{path}: invalid extraction_status")
    inspected = metadata.get("source_files_inspected")
    require(isinstance(inspected, list) and bool(inspected), errors, f"{path}: source_files_inspected must be a non-empty list")


def validate_rule_file(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in (
        "version",
        "name",
        "description",
        "target_ensemble",
        "source_idiom",
        "imports",
        "metadata",
        "passes",
        "priorities",
        "rules",
        "validation",
    ):
        require(key in data, errors, f"{path}: top-level {key} is required")
    require(data.get("version") == 1, errors, f"{path}: version must be 1")
    require(isinstance(data.get("name"), str) and bool(SNAKE_RE.match(data["name"])), errors, f"{path}: name must be snake_case")
    validate_metadata(path, data, errors)

    imports = data.get("imports")
    if isinstance(imports, list):
        for imported in imports:
            imported_path = RULES_DIR / str(imported)
            require(imported_path.exists(), errors, f"{path}: import does not exist: {imported}")
    else:
        errors.append(f"{path}: imports must be a list")

    rules = data.get("rules")
    require(isinstance(rules, list) and bool(rules), errors, f"{path}: rules must be a non-empty list")
    if not isinstance(rules, list):
        return errors

    ids = [rule.get("id") for rule in rules if isinstance(rule, dict)]
    duplicates = sorted(rule_id for rule_id, count in Counter(ids).items() if rule_id and count > 1)
    for rule_id in duplicates:
        errors.append(f"{path}: duplicate rule id: {rule_id}")

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"{path}: rules[{index}] must be an object")
            continue
        rule_id = rule.get("id", f"rules[{index}]")
        for key in ("id", "title", "scope", "priority", "action", "parameters", "rationale", "evidence", "exceptions"):
            require(key in rule, errors, f"{path}: {rule_id}: missing {key}")
        require(isinstance(rule.get("id"), str) and bool(SNAKE_RE.match(str(rule.get("id")))), errors, f"{path}: {rule_id}: id must be snake_case")
        require(rule.get("scope") in ALLOWED_SCOPES, errors, f"{path}: {rule_id}: invalid scope {rule.get('scope')!r}")
        require(rule.get("priority") in ALLOWED_PRIORITIES, errors, f"{path}: {rule_id}: invalid priority {rule.get('priority')!r}")
        require(isinstance(rule.get("action"), str) and bool(SNAKE_RE.match(str(rule.get("action")))), errors, f"{path}: {rule_id}: action must be snake_case")
        require(isinstance(rule.get("parameters"), dict), errors, f"{path}: {rule_id}: parameters must be an object")
        evidence = rule.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{path}: {rule_id}: evidence must be an object")
        else:
            for key in ("docs", "code", "reports", "examples"):
                require(isinstance(evidence.get(key), list), errors, f"{path}: {rule_id}: evidence.{key} must be a list")
        exceptions = rule.get("exceptions")
        if not isinstance(exceptions, list):
            errors.append(f"{path}: {rule_id}: exceptions must be a list")
    return errors


def validate_evaluation_file(path: Path, data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("version", "name", "description", "metadata", "corpora", "pilot_subsets", "validation"):
        require(key in data, errors, f"{path}: top-level {key} is required")
    require(data.get("version") == 1, errors, f"{path}: version must be 1")
    require(data.get("name") == "evaluation_corpus", errors, f"{path}: name must be evaluation_corpus")
    validate_metadata(path, data, errors)

    corpora = data.get("corpora")
    require(isinstance(corpora, list) and bool(corpora), errors, f"{path}: corpora must be a non-empty list")
    corpus_ids: set[str] = set()
    if isinstance(corpora, list):
        for index, corpus in enumerate(corpora):
            if not isinstance(corpus, dict):
                errors.append(f"{path}: corpora[{index}] must be an object")
                continue
            corpus_id = str(corpus.get("id", f"corpora[{index}]"))
            corpus_ids.add(corpus_id)
            for key in ("id", "source_voice_count", "baseline_output_dir", "report", "target"):
                require(key in corpus, errors, f"{path}: {corpus_id}: missing {key}")
            require("source_manifest" in corpus or "source_glob" in corpus, errors, f"{path}: {corpus_id}: source_manifest or source_glob is required")

    pilots = data.get("pilot_subsets")
    require(isinstance(pilots, list) and bool(pilots), errors, f"{path}: pilot_subsets must be a non-empty list")
    if isinstance(pilots, list):
        for index, pilot in enumerate(pilots):
            if not isinstance(pilot, dict):
                errors.append(f"{path}: pilot_subsets[{index}] must be an object")
                continue
            pilot_id = pilot.get("id", f"pilot_subsets[{index}]")
            corpus = pilot.get("corpus")
            require(corpus in corpus_ids, errors, f"{path}: {pilot_id}: unknown corpus {corpus!r}")
    return errors


def iter_evidence_paths(data: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for source in data.get("metadata", {}).get("source_files_inspected", []) or []:
        paths.append(str(source))
    for rule in data.get("rules", []) or []:
        if not isinstance(rule, dict):
            continue
        evidence = rule.get("evidence", {})
        if not isinstance(evidence, dict):
            continue
        for section in ("docs", "code", "reports"):
            for entry in evidence.get(section, []) or []:
                if isinstance(entry, dict) and entry.get("path"):
                    paths.append(str(entry["path"]))
    for corpus in data.get("corpora", []) or []:
        if isinstance(corpus, dict):
            for key in ("source_manifest", "baseline_output_dir", "report", "render_report", "rule_file"):
                if corpus.get(key):
                    paths.append(str(corpus[key]))
            for extra in corpus.get("additional_baseline_output_dirs", []) or []:
                paths.append(str(extra))
    for section in ("review_artifacts", "audit_reports"):
        for entry in data.get(section, []) or []:
            if isinstance(entry, dict) and entry.get("path"):
                paths.append(str(entry["path"]))
    return paths


def evidence_warnings(path: Path, data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for evidence_path in iter_evidence_paths(data):
        if "*" in evidence_path:
            if not list(ROOT.glob(evidence_path)):
                warnings.append(f"{path}: evidence glob matched nothing: {evidence_path}")
            continue
        if not (ROOT / evidence_path).exists():
            warnings.append(f"{path}: evidence path missing: {evidence_path}")
    return warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    parser.add_argument("--strict-evidence", action="store_true", help="Treat missing evidence as fatal.")
    args = parser.parse_args(argv)

    rule_paths = sorted(args.rules_dir.glob("*.yaml")) + sorted(args.rules_dir.glob("*.yml"))
    if not rule_paths:
        print(f"No YAML rule files found in {args.rules_dir}", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    for path in rule_paths:
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(f"{path}: could not load YAML: {exc}")
            continue

        if path.name == "evaluation_corpus.yaml":
            errors.extend(schema_validate_with_optional_dependency(path, data, EVALUATION_SCHEMA_PATH))
            errors.extend(validate_evaluation_file(path, data))
        else:
            errors.extend(schema_validate_with_optional_dependency(path, data, RULE_SCHEMA_PATH))
            errors.extend(validate_rule_file(path, data))
        warnings.extend(evidence_warnings(path, data))

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.strict_evidence:
        errors.extend(warnings)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(rule_paths)} YAML files in {args.rules_dir}")
    print(f"Evidence warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
