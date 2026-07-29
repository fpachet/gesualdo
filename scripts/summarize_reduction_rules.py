#!/usr/bin/env python3
"""Summarize structured reduction rule YAML files."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised by minimal uv envs
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"


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
        raise ValueError(f"{path}: expected mapping")
    return loaded


def rule_files(rules_dir: Path) -> list[Path]:
    return sorted(path for path in rules_dir.glob("*.yaml") if path.name != "evaluation_corpus.yaml")


def evidence_missing(rule: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    evidence = rule.get("evidence", {})
    if not isinstance(evidence, dict):
        return ["<malformed evidence>"]
    for section in ("docs", "code", "reports"):
        for entry in evidence.get(section, []) or []:
            if not isinstance(entry, dict) or not entry.get("path"):
                continue
            evidence_path = str(entry["path"])
            if "*" in evidence_path:
                if not list(ROOT.glob(evidence_path)):
                    missing.append(evidence_path)
            elif not (ROOT / evidence_path).exists():
                missing.append(evidence_path)
    return missing


def looks_underspecified(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("status") in {"underspecified", "partially_procedural", "idiom_dependent"}:
            return True
        return any(looks_underspecified(item) for item in value.values())
    if isinstance(value, list):
        return any(looks_underspecified(item) for item in value)
    return False


def render_summary(rules_dir: Path) -> str:
    files = rule_files(rules_dir)
    data_by_file = {path: load_yaml(path) for path in files}
    lines: list[str] = [
        "# YAML Reduction Rule Summary",
        "",
        "Generated from structured files in `rules/`.",
        "",
        "## Rule Counts",
        "",
        "| File | Rule count |",
        "| --- | ---: |",
    ]
    for path, data in data_by_file.items():
        lines.append(f"| `{path.relative_to(ROOT)}` | {len(data.get('rules', []) or [])} |")

    scope_counts: Counter[str] = Counter()
    rules_by_scope: dict[str, list[tuple[str, str]]] = defaultdict(list)
    hard_rules: list[tuple[str, str]] = []
    optional_rules: list[tuple[str, str]] = []
    missing_evidence: list[tuple[str, str, list[str]]] = []
    underspecified: list[tuple[str, str]] = []
    gesualdo_specific: list[str] = []
    take6_specific: list[str] = []

    for path, data in data_by_file.items():
        file_key = path.stem
        for rule in data.get("rules", []) or []:
            if not isinstance(rule, dict):
                continue
            rule_id = str(rule.get("id"))
            title = str(rule.get("title", ""))
            scope = str(rule.get("scope"))
            priority = str(rule.get("priority"))
            scope_counts[scope] += 1
            rules_by_scope[scope].append((rule_id, title))
            if priority == "hard":
                hard_rules.append((rule_id, title))
            if priority == "optional":
                optional_rules.append((rule_id, title))
            missing = evidence_missing(rule)
            if missing:
                missing_evidence.append((rule_id, title, missing))
            if looks_underspecified(rule.get("parameters", {})):
                underspecified.append((rule_id, title))
            if file_key == "gesualdo":
                gesualdo_specific.append(rule_id)
            if file_key == "take6":
                take6_specific.append(rule_id)

    lines.extend(["", "## Rules By Scope", ""])
    for scope, count in sorted(scope_counts.items()):
        lines.append(f"- `{scope}`: {count}")
        for rule_id, title in sorted(rules_by_scope[scope]):
            lines.append(f"  - `{rule_id}`: {title}")

    lines.extend(["", "## Hard Constraints", ""])
    for rule_id, title in sorted(hard_rules):
        lines.append(f"- `{rule_id}`: {title}")

    lines.extend(["", "## Optional Enrichments", ""])
    for rule_id, title in sorted(optional_rules):
        lines.append(f"- `{rule_id}`: {title}")

    lines.extend(["", "## Gesualdo-Specific Rules", ""])
    for rule_id in sorted(gesualdo_specific):
        lines.append(f"- `{rule_id}`")

    lines.extend(["", "## Take 6-Specific Rules", ""])
    for rule_id in sorted(take6_specific):
        lines.append(f"- `{rule_id}`")

    lines.extend(["", "## Rules With Missing Evidence", ""])
    if missing_evidence:
        for rule_id, title, paths in missing_evidence:
            lines.append(f"- `{rule_id}`: {title} ({', '.join(paths)})")
    else:
        lines.append("- None detected.")

    lines.extend(["", "## Likely Underspecified Parameters", ""])
    if underspecified:
        for rule_id, title in sorted(underspecified):
            lines.append(f"- `{rule_id}`: {title}")
    else:
        lines.append("- None detected.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = render_summary(args.rules_dir)
    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
        print(f"Wrote {output_path.relative_to(ROOT)}")
    else:
        print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
