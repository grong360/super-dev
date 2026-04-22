from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FILES = [
    "knowledge/development/08-catalog/catalog.yaml",
    "knowledge/development/11-ui-excellence/ui-aesthetic-system.md",
    "knowledge/development/11-ui-excellence/ui-component-excellence-standard.md",
    "knowledge/development/11-ui-excellence/ui-accessibility-wcag-playbook.md",
    "knowledge/development/12-scenarios/ai-application-scenario-pack.md",
    "knowledge/development/12-scenarios/multitenant-saas-scenario-pack.md",
    "knowledge/development/13-implementation-assets/ui-kpi-and-quality-gates.yaml",
    "knowledge/development/13-implementation-assets/scenario-coverage-matrix.yaml",
    "knowledge/development/14-full-lifecycle/lifecycle-end-to-end-map.md",
    "knowledge/development/14-full-lifecycle/requirement-discovery-playbook.md",
    "knowledge/development/14-full-lifecycle/architecture-decision-gate.md",
    "knowledge/development/14-full-lifecycle/testing-verification-gate.md",
    "knowledge/development/14-full-lifecycle/security-compliance-gate.md",
    "knowledge/development/14-full-lifecycle/release-change-management-playbook.md",
    "knowledge/development/14-full-lifecycle/operations-observability-runbook.md",
    "knowledge/development/14-full-lifecycle/stage-exit-criteria.yaml",
]

REQUIRED_FILE_ALTERNATES = {
    "knowledge/development/11-ui-excellence/ui-component-excellence-standard.md": [
        (
            "knowledge/development/11-ui-excellence/ui-engineering-excellence.md",
            ["## 3. Component Excellence Standard"],
        )
    ],
    "knowledge/development/11-ui-excellence/ui-accessibility-wcag-playbook.md": [
        (
            "knowledge/development/11-ui-excellence/ui-engineering-excellence.md",
            ["## 6. Accessibility (WCAG Compliance)", "WCAG 2.2"],
        )
    ],
    "knowledge/development/12-scenarios/ai-application-scenario-pack.md": [
        (
            "knowledge/development/12-scenarios/development-scenarios-guide.md",
            ["## 7. AI Application Scenario Pack"],
        )
    ],
    "knowledge/development/12-scenarios/multitenant-saas-scenario-pack.md": [
        (
            "knowledge/development/12-scenarios/development-scenarios-guide.md",
            ["## 4. Multi-Tenant SaaS Scenario Pack"],
        )
    ],
    "knowledge/development/13-implementation-assets/ui-kpi-and-quality-gates.yaml": [
        (
            "knowledge/development/13-implementation-assets/implementation-toolkit.md",
            ["## 4. UI KPIs & Quality Gates", "token_coverage", "blocking_bugs"],
        )
    ],
    "knowledge/development/13-implementation-assets/scenario-coverage-matrix.yaml": [
        (
            "knowledge/development/13-implementation-assets/implementation-toolkit.md",
            ["## 2. Scenario Coverage Matrix", "  b2b:", "  ecommerce_peak:"],
        )
    ],
    "knowledge/development/14-full-lifecycle/lifecycle-end-to-end-map.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 1. Lifecycle End-to-End Map"],
        )
    ],
    "knowledge/development/14-full-lifecycle/requirement-discovery-playbook.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 2. Stage 1: Requirement Discovery"],
        )
    ],
    "knowledge/development/14-full-lifecycle/architecture-decision-gate.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 4. Stage 3: Architecture Decision Gate"],
        )
    ],
    "knowledge/development/14-full-lifecycle/testing-verification-gate.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 6. Stage 5: Testing & Verification Gate"],
        )
    ],
    "knowledge/development/14-full-lifecycle/security-compliance-gate.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 7. Stage 6: Security & Compliance Gate"],
        )
    ],
    "knowledge/development/14-full-lifecycle/release-change-management-playbook.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 8. Stage 7: Release & Change Management"],
        )
    ],
    "knowledge/development/14-full-lifecycle/operations-observability-runbook.md": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 9. Stage 8: Operations & Observability"],
        )
    ],
    "knowledge/development/14-full-lifecycle/stage-exit-criteria.yaml": [
        (
            "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md",
            ["## 11. Stage Exit Criteria Summary (YAML Reference)", "stage_exit_criteria:"],
        )
    ],
}

REQUIRED_SCENARIOS = [
    "b2b",
    "b2c",
    "multitenant_saas",
    "internationalization",
    "mobile",
    "ai_application",
    "fintech",
    "ecommerce_peak",
]

REQUIRED_UI_GATES = [
    "token_coverage",
    "component_state_coverage",
    "accessibility_wcag",
    "lighthouse_accessibility",
    "lighthouse_performance",
    "visual_regression_threshold",
    "critical_flow_pass_rate",
    "blocking_bugs",
]

REQUIRED_LIFECYCLE_STAGES = [
    "requirement",
    "design",
    "architecture",
    "implementation",
    "testing",
    "security",
    "release",
    "operations",
    "incident_learning",
]

REQUIRED_TEMPLATE_FILES = [
    "knowledge/development/15-lifecycle-templates/template-catalog.yaml",
    "knowledge/development/15-lifecycle-templates/requirement-template.md",
    "knowledge/development/15-lifecycle-templates/design-handoff-template.md",
    "knowledge/development/15-lifecycle-templates/architecture-adr-template.md",
    "knowledge/development/15-lifecycle-templates/implementation-pr-template.md",
    "knowledge/development/15-lifecycle-templates/testing-report-template.md",
    "knowledge/development/15-lifecycle-templates/security-compliance-template.md",
    "knowledge/development/15-lifecycle-templates/release-change-template.md",
    "knowledge/development/15-lifecycle-templates/operations-runbook-template.md",
    "knowledge/development/15-lifecycle-templates/postmortem-template.md",
    "knowledge/development/15-lifecycle-templates/lifecycle-review-board-template.md",
]

TEMPLATE_FILE_ALTERNATES = {
    "knowledge/development/15-lifecycle-templates/template-catalog.yaml": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## Template Catalog", "| T-01 | Requirement Template |", "| T-10 | Lifecycle Review Board Template |"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/requirement-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-01: Requirement Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/design-handoff-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-02: Design Handoff Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/architecture-adr-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-03: Architecture ADR Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/implementation-pr-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-04: Implementation PR Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/testing-report-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-05: Testing Report Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/security-compliance-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-06: Security & Compliance Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/release-change-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-07: Release Change Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/operations-runbook-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-08: Operations Runbook Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/postmortem-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-09: Postmortem Template"],
        )
    ],
    "knowledge/development/15-lifecycle-templates/lifecycle-review-board-template.md": [
        (
            "knowledge/development/15-lifecycle-templates/project-templates-collection.md",
            ["## T-10: Lifecycle Review Board Template"],
        )
    ],
}

TEMPLATE_STAGE_ALTERNATES = {
    "requirement": ["Requirement Discovery"],
    "design": ["Product & Design"],
    "architecture": ["Architecture Decision"],
    "implementation": ["Implementation Execution"],
    "testing": ["Testing & Verification"],
    "security": ["Security & Compliance"],
    "release": ["Release & Change Management"],
    "operations": ["Operations & Observability"],
    "incident_learning": ["Incident Learning"],
}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _matches_alternate(project_dir: Path, alternates: list[tuple[str, list[str]]]) -> bool:
    for rel, markers in alternates:
        text = _load_text(project_dir / rel)
        if text and all(marker in text for marker in markers):
            return True
    return False


def _find_missing_files(project_dir: Path) -> list[str]:
    missing = []
    for rel in REQUIRED_FILES:
        if (project_dir / rel).exists():
            continue
        if _matches_alternate(project_dir, REQUIRED_FILE_ALTERNATES.get(rel, [])):
            continue
        missing.append(rel)
    return missing


def _find_missing_template_files(project_dir: Path) -> list[str]:
    missing = []
    for rel in REQUIRED_TEMPLATE_FILES:
        if (project_dir / rel).exists():
            continue
        if _matches_alternate(project_dir, TEMPLATE_FILE_ALTERNATES.get(rel, [])):
            continue
            missing.append(rel)
    return missing


def _check_scenario_matrix(project_dir: Path) -> list[str]:
    matrix_path = project_dir / "knowledge/development/13-implementation-assets/scenario-coverage-matrix.yaml"
    text = _load_text(matrix_path)
    if not text:
        text = _load_text(project_dir / "knowledge/development/13-implementation-assets/implementation-toolkit.md")
    missing = []
    for key in REQUIRED_SCENARIOS:
        if f"  {key}:" not in text:
            missing.append(key)
    return missing


def _check_ui_gates(project_dir: Path) -> list[str]:
    gates_path = project_dir / "knowledge/development/13-implementation-assets/ui-kpi-and-quality-gates.yaml"
    text = _load_text(gates_path)
    if not text:
        text = _load_text(project_dir / "knowledge/development/13-implementation-assets/implementation-toolkit.md")
    missing = []
    for key in REQUIRED_UI_GATES:
        if f"  {key}:" not in text:
            missing.append(key)
    return missing


def _check_md_header(project_dir: Path) -> list[str]:
    root = project_dir / "knowledge/development"
    missing = []
    for md in root.rglob("*.md"):
        text = _load_text(md).lstrip("\ufeff")
        if text.startswith("---\n"):
            parts = text.split("\n---", 1)
            if len(parts) == 2:
                text = parts[1].lstrip()
        first_non_empty = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                first_non_empty = stripped
                break
        if not re.match(r"^#\s+\S", first_non_empty):
            missing.append(str(md.relative_to(project_dir)))
    return missing


def _check_lifecycle_stages(project_dir: Path) -> list[str]:
    path = project_dir / "knowledge/development/14-full-lifecycle/stage-exit-criteria.yaml"
    text = _load_text(path)
    if not text:
        text = _load_text(project_dir / "knowledge/development/14-full-lifecycle/software-lifecycle-gates.md")
    missing = []
    for stage in REQUIRED_LIFECYCLE_STAGES:
        if f"  {stage}:" not in text:
            missing.append(stage)
    return missing


def _check_template_catalog_stages(project_dir: Path) -> list[str]:
    path = project_dir / "knowledge/development/15-lifecycle-templates/template-catalog.yaml"
    text = _load_text(path)
    using_consolidated = False
    if not text:
        text = _load_text(project_dir / "knowledge/development/15-lifecycle-templates/project-templates-collection.md")
        using_consolidated = True
    missing = []
    for stage in REQUIRED_LIFECYCLE_STAGES:
        if using_consolidated:
            markers = TEMPLATE_STAGE_ALTERNATES.get(stage, [])
            if not all(marker in text for marker in markers):
                missing.append(stage)
            continue
        if f"  {stage}:" not in text:
            missing.append(stage)
    return missing


def _normalize_title(text: str) -> str:
    normalized = re.sub(r"[\s\-_]+", "", text.lower())
    return normalized


def _collect_duplicate_titles(project_dir: Path) -> list[dict]:
    root = project_dir / "knowledge/development"
    buckets: dict[str, list[str]] = {}
    for md in root.rglob("*.md"):
        key = _normalize_title(md.stem)
        buckets.setdefault(key, []).append(str(md.relative_to(project_dir)))
    duplicates: list[dict] = []
    for key, files in buckets.items():
        if len(files) > 1:
            duplicates.append({"key": key, "files": sorted(files)})
    duplicates.sort(key=lambda item: len(item["files"]), reverse=True)
    return duplicates


def _collect_stale_files(project_dir: Path, stale_days: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    stale: list[dict] = []
    root = project_dir / "knowledge/development"
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_days = int((now - mtime).total_seconds() // 86400)
        if age_days > stale_days:
            stale.append(
                {
                    "path": str(path.relative_to(project_dir)),
                    "age_days": age_days,
                }
            )
    stale.sort(key=lambda item: item["age_days"], reverse=True)
    return stale


def _collect_catalog_indexed_files(project_dir: Path) -> set[str]:
    catalog_path = project_dir / "knowledge/development/08-catalog/catalog.yaml"
    text = _load_text(catalog_path)
    indexed: set[str] = {"knowledge/development/08-catalog/catalog.yaml"}
    current_section_path = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("- path: "):
            current_section_path = line.replace("- path: ", "", 1).strip()
            continue
        if line.startswith("path: "):
            current_section_path = line.replace("path: ", "", 1).strip()
            continue
        if line.startswith("- "):
            item = line.replace("- ", "", 1).strip()
            if current_section_path and item:
                indexed.add(f"knowledge/{current_section_path}/{item}")
    return indexed


def _collect_unindexed_files(project_dir: Path) -> list[str]:
    indexed = _collect_catalog_indexed_files(project_dir)
    allowed_extra = {
        "knowledge/development/DEVELOPMENT_KB_MASTER_INDEX.md",
        "knowledge/development/api-governance-complete.md",
        "knowledge/development/backend-engineering-complete.md",
        "knowledge/development/frontend-engineering-complete.md",
    }
    unindexed: list[str] = []
    root = project_dir / "knowledge/development"
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(project_dir))
        if rel in indexed or rel in allowed_extra:
            continue
        unindexed.append(rel)
    return sorted(unindexed)


def _build_advice(report: dict) -> list[str]:
    advice: list[str] = []
    if report["missing_files"]:
        advice.append("补齐缺失关键文件并更新catalog索引。")
    if report["missing_scenarios"]:
        advice.append("在scenario-coverage-matrix.yaml补齐缺失场景键。")
    if report["missing_ui_gates"]:
        advice.append("在ui-kpi-and-quality-gates.yaml补齐缺失UI门禁项。")
    if report["missing_headers_total"] > 0:
        advice.append("为缺失头信息的文档补齐“# 开发：”首行规范。")
    if report["missing_lifecycle_stages"]:
        advice.append("在stage-exit-criteria.yaml补齐缺失流程阶段定义。")
    if report["missing_template_files"] or report["missing_template_stages"]:
        advice.append("补齐15-lifecycle-templates模板资产与模板目录阶段定义。")
    if report["stale_files_total"] > 0:
        advice.append("优先刷新最老文档并建立季度复审节奏。")
    if report["duplicate_title_groups_total"] > 0:
        advice.append("清理重复主题文档，合并后保留单一事实源。")
    if report["unindexed_files_total"] > 0:
        advice.append("将未入catalog文件纳入目录或归档清理。")
    if not advice:
        advice.append("当前知识门禁通过，继续保持季度治理。")
    return advice


def _build_score(report: dict) -> int:
    score = 100
    score -= len(report["missing_files"]) * 15
    score -= len(report["missing_scenarios"]) * 10
    score -= len(report["missing_ui_gates"]) * 10
    score -= len(report["missing_lifecycle_stages"]) * 10
    score -= len(report["missing_template_files"]) * 8
    score -= len(report["missing_template_stages"]) * 8
    score -= min(20, report["missing_headers_total"] * 2)
    score -= min(10, report["duplicate_title_groups_total"] * 3)
    score -= min(10, report["stale_files_total"])
    score -= min(10, report["unindexed_files_total"] // 3)
    return max(0, score)


def run(project_dir: Path, stale_days: int = 180) -> tuple[bool, dict]:
    missing_files = _find_missing_files(project_dir)
    missing_template_files = _find_missing_template_files(project_dir)
    missing_scenarios = _check_scenario_matrix(project_dir)
    missing_ui_gates = _check_ui_gates(project_dir)
    missing_lifecycle_stages = _check_lifecycle_stages(project_dir)
    missing_template_stages = _check_template_catalog_stages(project_dir)
    missing_headers = _check_md_header(project_dir)
    duplicate_title_groups = _collect_duplicate_titles(project_dir)
    stale_files = _collect_stale_files(project_dir, stale_days=stale_days)
    unindexed_files = _collect_unindexed_files(project_dir)

    report = {
        "project_dir": str(project_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "missing_files": missing_files,
        "missing_scenarios": missing_scenarios,
        "missing_ui_gates": missing_ui_gates,
        "missing_lifecycle_stages": missing_lifecycle_stages,
        "missing_template_files": missing_template_files,
        "missing_template_stages": missing_template_stages,
        "missing_headers": missing_headers[:20],
        "missing_headers_total": len(missing_headers),
        "duplicate_title_groups": duplicate_title_groups[:20],
        "duplicate_title_groups_total": len(duplicate_title_groups),
        "stale_days_threshold": stale_days,
        "stale_files": stale_files[:20],
        "stale_files_total": len(stale_files),
        "unindexed_files": unindexed_files[:20],
        "unindexed_files_total": len(unindexed_files),
    }
    report["score"] = _build_score(report)
    report["advice"] = _build_advice(report)
    critical_failed = bool(
        missing_files
        or missing_template_files
        or missing_scenarios
        or missing_ui_gates
        or missing_lifecycle_stages
        or missing_template_stages
        or missing_headers
    )
    ok = not critical_failed and report["score"] >= 85
    report["status"] = "pass" if ok else "fail"
    return ok, report


def _render_markdown(report: dict) -> str:
    lines = [
        "# Knowledge Gate Report",
        "",
        f"- Status: {report['status']}",
        f"- Score: {report['score']}",
        f"- Generated At: {report['generated_at']}",
        f"- Stale Threshold Days: {report['stale_days_threshold']}",
        "",
        "## Critical Checks",
        "",
        f"- missing_files: {len(report['missing_files'])}",
        f"- missing_template_files: {len(report['missing_template_files'])}",
        f"- missing_scenarios: {len(report['missing_scenarios'])}",
        f"- missing_ui_gates: {len(report['missing_ui_gates'])}",
        f"- missing_lifecycle_stages: {len(report['missing_lifecycle_stages'])}",
        f"- missing_template_stages: {len(report['missing_template_stages'])}",
        f"- missing_headers_total: {report['missing_headers_total']}",
        "",
        "## Warning Checks",
        "",
        f"- duplicate_title_groups_total: {report['duplicate_title_groups_total']}",
        f"- stale_files_total: {report['stale_files_total']}",
        f"- unindexed_files_total: {report['unindexed_files_total']}",
        "",
        "## Advice",
        "",
    ]
    for item in report["advice"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _render_html(report: dict) -> str:
    advice_html = "".join(f"<li>{html.escape(item)}</li>" for item in report["advice"])
    return (
        "<html><head><meta charset='utf-8'><title>Knowledge Gate Report</title></head><body>"
        f"<h1>Knowledge Gate Report</h1><p>Status: <b>{html.escape(report['status'])}</b></p>"
        f"<p>Score: <b>{report['score']}</b></p>"
        f"<p>Generated At: {html.escape(report['generated_at'])}</p>"
        "<h2>Critical Checks</h2><ul>"
        f"<li>missing_files: {len(report['missing_files'])}</li>"
        f"<li>missing_template_files: {len(report['missing_template_files'])}</li>"
        f"<li>missing_scenarios: {len(report['missing_scenarios'])}</li>"
        f"<li>missing_ui_gates: {len(report['missing_ui_gates'])}</li>"
        f"<li>missing_lifecycle_stages: {len(report['missing_lifecycle_stages'])}</li>"
        f"<li>missing_template_stages: {len(report['missing_template_stages'])}</li>"
        f"<li>missing_headers_total: {report['missing_headers_total']}</li>"
        "</ul><h2>Warning Checks</h2><ul>"
        f"<li>duplicate_title_groups_total: {report['duplicate_title_groups_total']}</li>"
        f"<li>stale_files_total: {report['stale_files_total']}</li>"
        f"<li>unindexed_files_total: {report['unindexed_files_total']}</li>"
        f"</ul><h2>Advice</h2><ul>{advice_html}</ul></body></html>"
    )


def _render_junit(report: dict) -> str:
    checks = [
        ("missing_files", len(report["missing_files"]) == 0, json.dumps(report["missing_files"], ensure_ascii=False)),
        (
            "missing_template_files",
            len(report["missing_template_files"]) == 0,
            json.dumps(report["missing_template_files"], ensure_ascii=False),
        ),
        (
            "missing_scenarios",
            len(report["missing_scenarios"]) == 0,
            json.dumps(report["missing_scenarios"], ensure_ascii=False),
        ),
        (
            "missing_ui_gates",
            len(report["missing_ui_gates"]) == 0,
            json.dumps(report["missing_ui_gates"], ensure_ascii=False),
        ),
        (
            "missing_lifecycle_stages",
            len(report["missing_lifecycle_stages"]) == 0,
            json.dumps(report["missing_lifecycle_stages"], ensure_ascii=False),
        ),
        (
            "missing_template_stages",
            len(report["missing_template_stages"]) == 0,
            json.dumps(report["missing_template_stages"], ensure_ascii=False),
        ),
        (
            "missing_headers",
            report["missing_headers_total"] == 0,
            json.dumps(report["missing_headers"][:5], ensure_ascii=False),
        ),
    ]
    failures = sum(1 for _, passed, _ in checks if not passed)
    lines = [f"<testsuite name='knowledge-gates' tests='{len(checks)}' failures='{failures}'>"]
    for name, passed, details in checks:
        lines.append(f"  <testcase classname='knowledge.gates' name='{name}'>")
        if not passed:
            lines.append(f"    <failure message='{name} failed'>{html.escape(details)}</failure>")
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"


def _render_report(report: dict, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output_format == "md":
        return _render_markdown(report)
    if output_format == "html":
        return _render_html(report)
    if output_format == "junit":
        return _render_junit(report)
    raise ValueError(f"Unsupported format: {output_format}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check development knowledge gates.")
    parser.add_argument("--project-dir", default=".", help="Project root directory")
    parser.add_argument("--stale-days", type=int, default=180, help="Stale file threshold in days")
    parser.add_argument("--format", choices=["json", "md", "html", "junit"], default="json")
    parser.add_argument("--out", default="", help="Output file path")
    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()
    ok, report = run(project_dir, stale_days=args.stale_days)
    rendered = _render_report(report, args.format)
    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered.rstrip())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
