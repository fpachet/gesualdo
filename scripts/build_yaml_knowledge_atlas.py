#!/usr/bin/env python3
"""Build a presentation atlas from the YAML reduction knowledge files."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - used by minimal environments
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
DEFAULT_OUTPUT = ROOT / "docs" / "yaml_knowledge_atlas.html"

FOCUS_RULE_IDS = (
    "choose_two_stage_global_transposition",
    "avoid_high_borrowed_bottom_register",
    "allow_source_based_double_stops",
    "cleanup_review_notation",
    "preserve_characteristic_chromatic_events",
)

SCOPE_LABELS = {
    "source_parsing": "Source parsing",
    "source_event_model": "Source events",
    "global_transposition": "Transposition",
    "outer_voice_assignment": "Outer voices",
    "inner_voice_compression": "Compression",
    "pitch_class_coverage": "Pitch classes",
    "chromatic_motion": "Chromatic motion",
    "dissonance_preservation": "Dissonance",
    "harmonic_role_priority": "Harmony color",
    "register_placement": "Register",
    "instrument_range": "Ranges",
    "instrument_sweet_spot": "Sweet spots",
    "source_voice_restoration": "Restoration",
    "borrowing": "Borrowing",
    "double_stops": "Double-stops",
    "editorial_generation": "Editorial layers",
    "fragment_pruning": "Fragments",
    "continuity_repair": "Continuity",
    "notation_cleanup": "Notation cleanup",
    "musescore_compatibility": "MuseScore",
    "provenance": "Provenance",
    "validation": "Validation",
    "evaluation": "Evaluation",
}


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


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def walk_values(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        items: list[tuple[str, Any]] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            items.extend(walk_values(child, child_path))
        return items
    if isinstance(value, list):
        items = []
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            items.extend(walk_values(child, child_path))
        return items
    return [(path, value)]


def count_numeric_values(value: Any) -> int:
    count = 0
    for _path, leaf in walk_values(value):
        if isinstance(leaf, bool):
            continue
        if isinstance(leaf, (int, float)):
            count += 1
        elif isinstance(leaf, str) and re.fullmatch(r"-?\d+(\.\d+)?", leaf.strip()):
            count += 1
    return count


def count_boolean_values(value: Any) -> int:
    return sum(1 for _path, leaf in walk_values(value) if isinstance(leaf, bool))


def collect_parameter_leaves(value: Any, limit: int = 9) -> list[dict[str, str]]:
    leaves = []
    for path, leaf in walk_values(value):
        if isinstance(leaf, (dict, list)):
            continue
        if isinstance(leaf, str) and len(leaf) > 90:
            continue
        if isinstance(leaf, bool):
            rendered = "true" if leaf else "false"
        else:
            rendered = str(leaf)
        if path and rendered:
            leaves.append({"path": path, "value": rendered})
    score_order = {"midi": 0, "threshold": 0, "weight": 1, "cost": 1, "duration": 1, "tolerance": 1}
    leaves.sort(
        key=lambda item: (
            min((score_order[key] for key in score_order if key in item["path"].lower()), default=3),
            len(item["path"]),
            item["path"],
        )
    )
    return leaves[:limit]


def evidence_counts(rule: dict[str, Any]) -> dict[str, int]:
    evidence = rule.get("evidence", {})
    if not isinstance(evidence, dict):
        return {"docs": 0, "reports": 0, "examples": 0, "code": 0}
    return {
        "docs": len(evidence.get("docs", []) or []),
        "reports": len(evidence.get("reports", []) or []),
        "examples": len(evidence.get("examples", []) or []),
        "code": len(evidence.get("code", []) or []),
    }


def compact_rule(rule: dict[str, Any], file_key: str) -> dict[str, Any]:
    parameters = rule.get("parameters", {}) if isinstance(rule.get("parameters"), dict) else {}
    counts = evidence_counts(rule)
    return {
        "id": str(rule.get("id", "")),
        "title": str(rule.get("title", "")),
        "scope": str(rule.get("scope", "")),
        "scopeLabel": SCOPE_LABELS.get(str(rule.get("scope", "")), str(rule.get("scope", ""))),
        "priority": str(rule.get("priority", "")),
        "action": str(rule.get("action", "")),
        "file": f"rules/{file_key}.yaml",
        "fileKey": file_key,
        "rationale": str(rule.get("rationale", "")).strip(),
        "numericCount": count_numeric_values(parameters),
        "booleanCount": count_boolean_values(parameters),
        "parameterLeaves": collect_parameter_leaves(parameters),
        "evidence": counts,
    }


def first_existing(paths: list[Path]) -> str:
    for path in paths:
        if path.exists():
            return str(path.relative_to(ROOT))
    return str(paths[0].relative_to(ROOT))


def build_data(rules_dir: Path) -> dict[str, Any]:
    files = rule_files(rules_dir)
    rules: list[dict[str, Any]] = []
    file_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    imported_files: set[str] = set()
    source_docs: set[str] = set()

    for path in files:
        data = load_yaml(path)
        file_key = path.stem
        imported_files.update(str(item) for item in data.get("imports", []) or [])
        for inspected in data.get("metadata", {}).get("source_files_inspected", []) or []:
            source_docs.add(str(inspected))
        for rule in data.get("rules", []) or []:
            if not isinstance(rule, dict):
                continue
            item = compact_rule(rule, file_key)
            rules.append(item)
            file_counts[item["file"]] += 1
            scope_counts[item["scope"]] += 1
            priority_counts[item["priority"]] += 1

    evaluation_path = rules_dir / "evaluation_corpus.yaml"
    evaluation = load_yaml(evaluation_path) if evaluation_path.exists() else {}
    corpora = evaluation.get("corpora", []) or []
    pilots = evaluation.get("pilot_subsets", []) or []
    review_artifacts = evaluation.get("review_artifacts", []) or []
    audit_reports = evaluation.get("audit_reports", []) or []

    focus_rules = [rule for rule in rules if rule["id"] in FOCUS_RULE_IDS]
    focus_rules.sort(key=lambda rule: FOCUS_RULE_IDS.index(rule["id"]))

    total_numeric = sum(rule["numericCount"] for rule in rules)
    total_boolean = sum(rule["booleanCount"] for rule in rules)
    total_code_refs = sum(rule["evidence"]["code"] for rule in rules)
    total_examples = sum(rule["evidence"]["examples"] for rule in rules)

    return {
        "metrics": {
            "ruleCount": len(rules),
            "fileCount": len(files) + (1 if evaluation else 0),
            "scopeCount": len(scope_counts),
            "numericCount": total_numeric,
            "booleanCount": total_boolean,
            "codeRefs": total_code_refs,
            "exampleCount": total_examples,
            "corpusCount": len(corpora),
            "pilotCount": len(pilots),
            "reviewArtifactCount": len(review_artifacts),
            "auditReportCount": len(audit_reports),
        },
        "rules": rules,
        "focusRules": focus_rules,
        "fileCounts": [{"file": key, "count": value} for key, value in sorted(file_counts.items())],
        "scopeCounts": [
            {"scope": key, "label": SCOPE_LABELS.get(key, key), "count": value}
            for key, value in sorted(scope_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "priorityCounts": [{"priority": key, "count": value} for key, value in sorted(priority_counts.items())],
        "corpora": corpora,
        "pilots": pilots,
        "reviewArtifacts": review_artifacts,
        "auditReports": audit_reports,
        "sourceDocs": sorted(source_docs),
        "imports": sorted(imported_files),
        "updatedFrom": first_existing([ROOT / "docs" / "yaml_rule_summary.md", ROOT / "rules" / "shared_quartet.yaml"]),
    }


def render_html(data: dict[str, Any]) -> str:
    data_json = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YAML Reduction Knowledge Atlas</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f3ea;
      --ink: #202426;
      --muted: #69706f;
      --panel: #fffaf1;
      --line: #d6cfc0;
      --teal: #0d6f6f;
      --blue: #4d658f;
      --red: #9b3f42;
      --gold: #a87521;
      --green: #4a7650;
      --shadow: 0 18px 40px rgba(45, 38, 27, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(13, 111, 111, 0.12), transparent 34rem),
        radial-gradient(circle at 84% 14%, rgba(168, 117, 33, 0.16), transparent 28rem),
        var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    a {{ color: inherit; }}
    .page {{ max-width: 1480px; margin: 0 auto; padding: 28px; }}
    .topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .kicker {{ color: var(--teal); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; }}
    h1 {{
      margin: 4px 0 0;
      font-size: clamp(32px, 4.5vw, 72px);
      line-height: 0.98;
      letter-spacing: -0.03em;
      max-width: 980px;
    }}
    .subtitle {{ max-width: 720px; color: var(--muted); font-size: clamp(16px, 1.5vw, 20px); margin: 14px 0 0; }}
    .badge {{
      border: 1px solid var(--line);
      background: rgba(255, 250, 241, 0.72);
      border-radius: 999px;
      padding: 9px 12px;
      color: var(--muted);
      white-space: nowrap;
      font-size: 13px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 12px;
      margin: 22px 0;
    }}
    .metric {{
      min-height: 116px;
      padding: 16px;
      border: 1px solid var(--line);
      background: rgba(255, 250, 241, 0.86);
      box-shadow: var(--shadow);
    }}
    .metric strong {{ display: block; font-size: clamp(28px, 3vw, 46px); line-height: 1; margin-bottom: 8px; }}
    .metric span {{ color: var(--muted); font-size: 13px; display: block; }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(720px, 1.45fr) minmax(300px, .55fr);
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      border: 1px solid var(--line);
      background: rgba(255, 250, 241, 0.86);
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .atlas-map {{
      position: relative;
      min-height: 760px;
      display: block;
      overflow: hidden;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(13,111,111,.08), rgba(168,117,33,.08));
    }}
    .atlas-map svg {{ display: block; width: 100%; height: auto; }}
    .atlas-ring {{ fill: none; stroke: rgba(32,36,38,.16); stroke-width: 1.2; }}
    .atlas-spoke {{ stroke: rgba(32,36,38,.18); stroke-width: 1; }}
    .atlas-link {{ stroke: rgba(13,111,111,.45); stroke-width: 1.15; fill: none; }}
    .atlas-link.alt {{ stroke: rgba(168,117,33,.45); }}
    .atlas-node {{ fill: var(--panel); stroke: var(--teal); stroke-width: 1.6; }}
    .atlas-node.major {{ fill: var(--teal); }}
    .atlas-node-count {{ font-size: 12px; font-weight: 700; text-anchor: middle; dominant-baseline: central; fill: var(--ink); }}
    .atlas-node-count.major {{ fill: var(--panel); }}
    .atlas-core {{ fill: var(--ink); filter: drop-shadow(0 18px 22px rgba(32,36,38,.26)); }}
    .atlas-core-count {{ fill: var(--panel); font-size: 56px; font-weight: 700; text-anchor: middle; dominant-baseline: central; }}
    .atlas-core-label {{ fill: var(--panel); opacity: .86; font-size: 13px; text-anchor: middle; }}
    .atlas-label-card {{ fill: rgba(255,250,241,.96); stroke: rgba(32,36,38,.22); stroke-width: 1; }}
    .atlas-label-card.major {{ stroke: var(--teal); stroke-width: 1.4; }}
    .atlas-label-text {{ fill: var(--ink); font-size: 13px; font-weight: 650; dominant-baseline: central; }}
    .atlas-label-count {{ fill: var(--teal); font-size: 15px; font-weight: 750; text-anchor: middle; dominant-baseline: central; }}
    .atlas-label-count.major {{ fill: var(--panel); }}
    .atlas-label-count-bg {{ fill: rgba(13,111,111,.12); }}
    .atlas-label-count-bg.major {{ fill: var(--teal); }}
    .file-bars {{ display: grid; gap: 10px; margin-top: 12px; }}
    .bar-row {{ display: grid; grid-template-columns: 150px 1fr 34px; gap: 10px; align-items: center; font-size: 13px; }}
    .bar-track {{ height: 12px; border: 1px solid var(--line); background: rgba(32,36,38,.05); }}
    .bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--teal), var(--gold)); }}
    .controls {{
      display: grid;
      grid-template-columns: 1fr 180px 160px;
      gap: 10px;
      margin: 18px 0 12px;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 11px 12px;
      font: inherit;
      border-radius: 0;
    }}
    .rule-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .rule-card {{
      border: 1px solid var(--line);
      background: rgba(255, 250, 241, 0.88);
      padding: 12px;
      min-height: 148px;
      display: flex;
      flex-direction: column;
      gap: 9px;
    }}
    .rule-card h3 {{ margin: 0; font-size: 15px; line-height: 1.2; }}
    .rule-meta {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .pill {{ display: inline-flex; border: 1px solid var(--line); padding: 3px 6px; font-size: 11px; color: var(--muted); }}
    .pill.priority-hard, .pill.priority-very_high {{ color: var(--red); border-color: rgba(155,63,66,.45); }}
    .pill.priority-high {{ color: var(--teal); border-color: rgba(13,111,111,.45); }}
    .rule-card p {{ margin: 0; color: var(--muted); font-size: 12px; }}
    .precision {{ margin-top: auto; display: flex; gap: 8px; color: var(--muted); font-size: 12px; }}
    .deep-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .deep-card {{
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 14px;
      min-height: 310px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .deep-card h3 {{ margin: 0; font-size: 17px; }}
    .deep-card .action {{ color: var(--teal); font-size: 12px; font-weight: 700; word-break: break-word; }}
    .leaf-list {{ display: grid; gap: 6px; margin-top: auto; }}
    .leaf {{ display: grid; gap: 2px; padding-top: 6px; border-top: 1px solid var(--line); }}
    .leaf code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; color: var(--blue); word-break: break-word; }}
    .leaf b {{ font-size: 12px; }}
    .corpus-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .corpus {{
      border-left: 4px solid var(--teal);
      background: rgba(255,250,241,.88);
      padding: 12px;
      border-top: 1px solid var(--line);
      border-right: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      min-height: 120px;
    }}
    .corpus b {{ display: block; margin-bottom: 6px; }}
    .corpus span {{ display: block; color: var(--muted); font-size: 12px; }}
    .footer-note {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
    @media (max-width: 1180px) {{
      .metrics {{ grid-template-columns: repeat(3, 1fr); }}
      .layout {{ grid-template-columns: 1fr; }}
      .rule-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .deep-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .corpus-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      .page {{ padding: 16px; }}
      .topbar {{ align-items: flex-start; flex-direction: column; }}
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
      .controls {{ grid-template-columns: 1fr; }}
      .rule-grid, .deep-grid, .corpus-strip {{ grid-template-columns: 1fr; }}
      .atlas-map {{ min-height: 0; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      .controls {{ display: none; }}
      .page {{ max-width: none; padding: 12mm; }}
      .panel, .metric, .rule-card, .deep-card, .corpus {{ box-shadow: none; break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="topbar">
      <div>
        <div class="kicker">Reduction knowledge atlas</div>
        <h1>{data["metrics"]["ruleCount"]} explicit rules for turning voices into quartet notation.</h1>
        <p class="subtitle">A presentation view of the YAML knowledge base: what it knows, how precise it is, and where the clean-room reducer can test itself.</p>
      </div>
      <div class="badge" id="sourceBadge"></div>
    </section>

    <section class="metrics" id="metrics"></section>

    <section class="layout">
      <div class="panel">
        <h2>Rule Family Map</h2>
        <div class="atlas-map" id="atlasMap" aria-label="Rule scopes arranged around the reduction knowledge core">
        </div>
      </div>
      <div class="panel">
        <h2>Knowledge Distribution</h2>
        <div class="file-bars" id="fileBars"></div>
        <div class="footer-note">Shared quartet knowledge provides the substrate; Gesualdo and Take 6 add idiom-specific policies; evaluation metadata defines the reconstruction targets.</div>
      </div>
    </section>

    <section class="panel" style="margin-top:18px;">
      <h2>Five Rules Worth Showing On Slides</h2>
      <div class="deep-grid" id="deepGrid"></div>
    </section>

    <section class="panel" style="margin-top:18px;">
      <h2>Rule Cards</h2>
      <div class="controls">
        <input id="searchBox" type="search" placeholder="Search rules, scopes, actions">
        <select id="scopeFilter" aria-label="Filter by scope"><option value="">All scopes</option></select>
        <select id="fileFilter" aria-label="Filter by file"><option value="">All files</option></select>
      </div>
      <div class="rule-grid" id="ruleGrid"></div>
    </section>

    <section class="panel" style="margin-top:18px;">
      <h2>Evaluation Ground</h2>
      <div class="corpus-strip" id="corpora"></div>
    </section>
  </main>

  <script>
    const DATA = {data_json};

    const byId = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

    function renderMetrics() {{
      const metrics = [
        [DATA.metrics.ruleCount, "explicit reduction rules"],
        [DATA.metrics.scopeCount, "musical and technical scopes"],
        [DATA.metrics.numericCount, "numeric thresholds and weights"],
        [DATA.metrics.booleanCount, "symbolic yes/no predicates"],
        [DATA.metrics.corpusCount, "evaluation corpora"],
        [DATA.metrics.codeRefs, "code citations in rule evidence"]
      ];
      byId("metrics").innerHTML = metrics.map(([value, label]) => `
        <article class="metric"><strong>${{escapeHtml(value)}}</strong><span>${{escapeHtml(label)}}</span></article>
      `).join("");
      byId("sourceBadge").textContent = `${{DATA.metrics.fileCount}} YAML files - ${{DATA.metrics.reviewArtifactCount}} review artifacts - ${{DATA.metrics.auditReportCount}} audit reports`;
    }}

    function renderMap() {{
      const map = byId("atlasMap");
      const scopes = DATA.scopeCounts;
      const width = 980;
      const height = 760;
      const cx = width / 2;
      const cy = height / 2 + 4;
      const orbit = 184;
      const left = scopes.filter((_, index) => index % 2 === 0);
      const right = scopes.filter((_, index) => index % 2 === 1);
      const maxSide = Math.max(left.length, right.length);
      const top = 64;
      const spacing = (height - top * 2) / Math.max(maxSide - 1, 1);
      const cardW = 226;
      const cardH = 38;
      const leftX = 34;
      const rightX = width - cardW - 34;

      const labelPos = new Map();
      left.forEach((scope, i) => labelPos.set(scope.scope, {{ x: leftX, y: top + i * spacing, side: "left" }}));
      right.forEach((scope, i) => labelPos.set(scope.scope, {{ x: rightX, y: top + i * spacing, side: "right" }}));

      function polar(index, total) {{
        const angle = -Math.PI / 2 + (index / total) * Math.PI * 2;
        return {{ x: cx + Math.cos(angle) * orbit, y: cy + Math.sin(angle) * orbit, angle }};
      }}

      const defs = `
        <defs>
          <radialGradient id="atlasCoreGradient" cx="50%" cy="38%" r="65%">
            <stop offset="0%" stop-color="rgba(255,250,241,.18)" />
            <stop offset="100%" stop-color="rgba(32,36,38,1)" />
          </radialGradient>
        </defs>`;
      const rings = [112, 184, 258].map(r => `<circle class="atlas-ring" cx="${{cx}}" cy="${{cy}}" r="${{r}}"/>`).join("");
      const spokes = scopes.map((scope, index) => {{
        const p = polar(index, scopes.length);
        return `<line class="atlas-spoke" x1="${{cx}}" y1="${{cy}}" x2="${{p.x.toFixed(1)}}" y2="${{p.y.toFixed(1)}}"/>`;
      }}).join("");
      const links = scopes.map((scope, index) => {{
        const p = polar(index, scopes.length);
        const pos = labelPos.get(scope.scope);
        const targetX = pos.side === "left" ? pos.x + cardW : pos.x;
        const targetY = pos.y + cardH / 2;
        const midX = pos.side === "left" ? p.x - 54 : p.x + 54;
        return `<path class="atlas-link${{index % 2 ? " alt" : ""}}" d="M ${{p.x.toFixed(1)}} ${{p.y.toFixed(1)}} C ${{midX.toFixed(1)}} ${{p.y.toFixed(1)}}, ${{midX.toFixed(1)}} ${{targetY.toFixed(1)}}, ${{targetX.toFixed(1)}} ${{targetY.toFixed(1)}}"/>`;
      }}).join("");
      const nodes = scopes.map((scope, index) => {{
        const p = polar(index, scopes.length);
        const major = scope.count >= 3 ? " major" : "";
        const radius = 15 + Math.min(scope.count, 5) * 2;
        return `<g>
          <circle class="atlas-node${{major}}" cx="${{p.x.toFixed(1)}}" cy="${{p.y.toFixed(1)}}" r="${{radius}}"/>
          <text class="atlas-node-count${{major}}" x="${{p.x.toFixed(1)}}" y="${{p.y.toFixed(1)}}">${{scope.count}}</text>
        </g>`;
      }}).join("");
      const labels = scopes.map((scope) => {{
        const pos = labelPos.get(scope.scope);
        const major = scope.count >= 3 ? " major" : "";
        const countX = pos.side === "left" ? pos.x + cardW - 21 : pos.x + 21;
        const labelX = pos.side === "left" ? pos.x + 13 : pos.x + 48;
        const anchor = pos.side === "left" ? "start" : "start";
        return `<g>
          <rect class="atlas-label-card${{major}}" x="${{pos.x}}" y="${{pos.y}}" width="${{cardW}}" height="${{cardH}}" rx="0"/>
          <circle class="atlas-label-count-bg${{major}}" cx="${{countX}}" cy="${{pos.y + cardH / 2}}" r="14"/>
          <text class="atlas-label-count${{major}}" x="${{countX}}" y="${{pos.y + cardH / 2}}">${{scope.count}}</text>
          <text class="atlas-label-text" x="${{labelX}}" y="${{pos.y + cardH / 2}}" text-anchor="${{anchor}}">${{escapeHtml(scope.label)}}</text>
        </g>`;
      }}).join("");
      const core = `<g>
        <circle class="atlas-core" cx="${{cx}}" cy="${{cy}}" r="92" fill="url(#atlasCoreGradient)"/>
        <text class="atlas-core-count" x="${{cx}}" y="${{cy - 12}}">${{DATA.metrics.ruleCount}}</text>
        <text class="atlas-core-label" x="${{cx}}" y="${{cy + 34}}">encoded rules</text>
      </g>`;
      map.innerHTML = `<svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="Circular map of ${{DATA.metrics.ruleCount}} reduction rules grouped into ${{DATA.metrics.scopeCount}} families">${{defs}}${{rings}}${{spokes}}${{links}}${{labels}}${{nodes}}${{core}}</svg>`;
    }}

    function renderBars() {{
      const max = Math.max(...DATA.fileCounts.map(item => item.count));
      byId("fileBars").innerHTML = DATA.fileCounts.map(item => `
        <div class="bar-row">
          <span>${{escapeHtml(item.file.replace("rules/", ""))}}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${{Math.round(item.count / max * 100)}}%"></div></div>
          <b>${{item.count}}</b>
        </div>
      `).join("");
    }}

    function renderDeepDives() {{
      byId("deepGrid").innerHTML = DATA.focusRules.map(rule => {{
        const leaves = rule.parameterLeaves.slice(0, 6).map(leaf => `
          <div class="leaf"><code>${{escapeHtml(leaf.path)}}</code><b>${{escapeHtml(leaf.value)}}</b></div>
        `).join("");
        return `
          <article class="deep-card">
            <div class="rule-meta">
              <span class="pill">${{escapeHtml(rule.file.replace("rules/", ""))}}</span>
              <span class="pill priority-${{escapeHtml(rule.priority)}}">${{escapeHtml(rule.priority)}}</span>
            </div>
            <h3>${{escapeHtml(rule.title)}}</h3>
            <div class="action">${{escapeHtml(rule.action)}}</div>
            <p>${{escapeHtml(rule.rationale).slice(0, 250)}}${{rule.rationale.length > 250 ? "..." : ""}}</p>
            <div class="leaf-list">${{leaves}}</div>
          </article>
        `;
      }}).join("");
    }}

    function populateFilters() {{
      const scopeFilter = byId("scopeFilter");
      DATA.scopeCounts
        .slice()
        .sort((left, right) => left.label.localeCompare(right.label))
        .forEach(scope => {{
          const option = document.createElement("option");
          option.value = scope.scope;
          option.textContent = scope.label;
          scopeFilter.appendChild(option);
        }});
      const fileFilter = byId("fileFilter");
      DATA.fileCounts.forEach(file => {{
        const option = document.createElement("option");
        option.value = file.file;
        option.textContent = file.file.replace("rules/", "");
        fileFilter.appendChild(option);
      }});
    }}

    function ruleMatches(rule) {{
      const query = byId("searchBox").value.trim().toLowerCase();
      const scope = byId("scopeFilter").value;
      const file = byId("fileFilter").value;
      const haystack = [rule.id, rule.title, rule.scopeLabel, rule.action, rule.rationale].join(" ").toLowerCase();
      return (!query || haystack.includes(query)) && (!scope || rule.scope === scope) && (!file || rule.file === file);
    }}

    function renderRules() {{
      const visible = DATA.rules.filter(ruleMatches);
      byId("ruleGrid").innerHTML = visible.map(rule => `
        <article class="rule-card">
          <div class="rule-meta">
            <span class="pill">${{escapeHtml(rule.scopeLabel)}}</span>
            <span class="pill priority-${{escapeHtml(rule.priority)}}">${{escapeHtml(rule.priority)}}</span>
          </div>
          <h3>${{escapeHtml(rule.title)}}</h3>
          <p>${{escapeHtml(rule.action)}}</p>
          <div class="precision">
            <span>${{rule.numericCount}} numbers</span>
            <span>${{rule.booleanCount}} predicates</span>
            <span>${{rule.evidence.examples}} examples</span>
          </div>
        </article>
      `).join("");
    }}

    function renderCorpora() {{
      byId("corpora").innerHTML = DATA.corpora.map(corpus => `
        <article class="corpus">
          <b>${{escapeHtml(corpus.id)}}</b>
          <span>${{escapeHtml(corpus.source_voice_count)}} source voices - ${{escapeHtml(corpus.target)}}</span>
          <span>${{escapeHtml(corpus.baseline_output_dir)}}</span>
          <span>${{escapeHtml(corpus.notes || "")}}</span>
        </article>
      `).join("");
    }}

    function init() {{
      renderMetrics();
      renderMap();
      renderBars();
      renderDeepDives();
      populateFilters();
      renderRules();
      renderCorpora();
      ["searchBox", "scopeFilter", "fileFilter"].forEach(id => byId(id).addEventListener("input", renderRules));
    }}

    init();
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, default=RULES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rules_dir = args.rules_dir if args.rules_dir.is_absolute() else ROOT / args.rules_dir
    output = args.output if args.output.is_absolute() else ROOT / args.output
    data = build_data(rules_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(data), encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
