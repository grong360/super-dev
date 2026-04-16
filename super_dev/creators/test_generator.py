"""
Test Generator — generate acceptance tests and API contract tests from specs.

Parses PRD requirements into Gherkin feature files for BDD acceptance tests,
and generates API contract test scaffolding from architecture docs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.test_generator")


@dataclass
class GeneratedTest:
    """A single generated test file."""

    name: str
    test_type: str  # acceptance | contract | unit_scaffold
    path: str
    content: str
    requirement_ids: list[str] = field(default_factory=list)


@dataclass
class TestGenerationReport:
    """Report from test generation."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acceptance_tests: int = 0
    contract_tests: int = 0
    total_generated: int = 0
    tests: list[GeneratedTest] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "acceptance_tests": self.acceptance_tests,
            "contract_tests": self.contract_tests,
            "total_generated": self.total_generated,
            "tests": [
                {
                    "name": t.name,
                    "test_type": t.test_type,
                    "path": t.path,
                    "requirement_ids": t.requirement_ids,
                }
                for t in self.tests
            ],
        }


def _parse_prd_scenarios(prd_path: Path) -> list[dict[str, str]]:
    """Extract testable scenarios from PRD.

    Looks for requirement patterns that can be converted to Given-When-Then.
    """
    content = prd_path.read_text(encoding="utf-8", errors="ignore")
    scenarios: list[dict[str, str]] = []

    lines = content.split("\n")
    current_section = ""
    req_counter = 0

    for line in lines:
        heading_match = re.match(r"^#{1,4}\s+(.+)", line)
        if heading_match:
            current_section = heading_match.group(1).strip()
            continue

        req_match = re.match(r"^(?:\d+\.\s+|[-*]\s+)(.+)", line)
        if req_match and len(req_match.group(1).strip()) > 10:
            req_counter += 1
            text = req_match.group(1).strip()
            section_prefix = re.sub(r"[^a-zA-Z0-9]", "", current_section[:20]) if current_section else "REQ"

            # Try to decompose into Given-When-Then
            scenario = _decompose_to_gherkin(text, section_prefix, req_counter)
            scenarios.append(scenario)

    return scenarios


def _decompose_to_gherkin(text: str, section: str, counter: int) -> dict[str, str]:
    """Decompose a requirement into Gherkin Given-When-Then structure."""
    req_id = f"{section}-{counter:03d}"

    # Detect action keywords
    action_patterns = [
        (r"should\s+(?:be able to\s+)?(.+)", r"action"),
        (r"must\s+(?:be able to\s+)?(.+)", r"action"),
        (r"can\s+(.+)", r"action"),
        (r"user\s+(?:should\s+)?(?:can\s+)?(.+)", r"action"),
        (r"(?:display|show|render|navigate|redirect)\s+(.+)", r"action"),
    ]

    action = text
    for pat, _label in action_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            action = m.group(1).strip()
            break

    # Detect precondition keywords
    given = "the user is on the application"
    pre_patterns = [
        r"when\s+(?:the\s+)?(.+?)(?:\s+is|\s+are|\s+has)",
        r"if\s+(.+?)(?:\s+is|\s+are|\s+has)",
        r"given\s+(.+)",
    ]
    for pat in pre_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            given = m.group(1).strip()
            break

    # Detect expected result
    then = f"the expected outcome of '{action[:50]}' is achieved"
    result_patterns = [
        r"then\s+(.+)",
        r"(?:should|must)\s+(?:see|display|show|receive|get|return)\s+(.+)",
        r"result(?:s)?\s*(?:should|must)\s+be\s+(.+)",
    ]
    for pat in result_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            then = m.group(1).strip()
            break

    return {
        "id": req_id,
        "feature": section or "Core",
        "given": given,
        "when": action,
        "then": then,
        "original_text": text,
    }


def _render_gherkin_feature(
    feature_name: str, scenarios: list[dict[str, str]]
) -> str:
    """Render Gherkin feature file content."""
    lines = [
        f"Feature: {feature_name}",
        "",
        f"  {'# ' + scenarios[0]['original_text'][:80] if scenarios else ''}",
        "",
    ]

    for scenario in scenarios:
        lines.extend(
            [
                f"  Scenario: {scenario['id']} - {scenario['when'][:50]}",
                f"    Given {scenario['given']}",
                f"    When {scenario['when']}",
                f"    Then {scenario['then']}",
                "",
            ]
        )

    return "\n".join(lines)


def _parse_api_routes(arch_path: Path) -> list[dict[str, str]]:
    """Extract API route definitions from architecture doc."""
    content = arch_path.read_text(encoding="utf-8", errors="ignore")
    routes: list[dict[str, str]] = []

    # Match REST API definitions
    route_patterns = re.findall(
        r"(GET|POST|PUT|DELETE|PATCH)\s+`?(/[a-zA-Z0-9/{}_.-]+)`?",
        content,
        re.IGNORECASE,
    )
    for method, path in route_patterns:
        routes.append({"method": method.upper(), "path": path})

    return routes


def _render_contract_test(
    routes: list[dict[str, str]], base_url: str = "http://localhost:8000"
) -> str:
    """Render API contract test file content."""
    lines = [
        '"""',
        "Auto-generated API Contract Tests by Super Dev.",
        "Verify that API endpoints exist and return expected status codes.",
        '"""',
        "",
        "import pytest",
        "import requests",
        "",
        "",
        f"BASE_URL = {repr(base_url)}",
        "",
        "",
    ]

    for i, route in enumerate(routes):
        method = route["method"]
        path = route["path"]
        # Clean path params for test name
        test_name = re.sub(r"[{}:/]", "_", path).strip("_")
        test_name = f"test_{method.lower()}_{test_name}"

        lines.extend(
            [
                f"def {test_name}():",
                f'    """Contract test: {method} {path}"""',
                f'    response = requests.{method.lower()}(f"{{BASE_URL}}{path}")',
                "    assert response.status_code in (200, 201, 204, 401, 403),",
                f'        f"Expected valid status for {method} {path}, got {{response.status_code}}"',
                "",
                "",
            ]
        )

    return "\n".join(lines)


def run_test_generation(
    project_dir: Path,
    output_dir: Path | None = None,
    tests_dir: Path | None = None,
) -> TestGenerationReport:
    """Generate acceptance and contract tests from spec artifacts.

    Args:
        project_dir: Root of the project.
        output_dir: Directory containing spec artifacts.
        tests_dir: Directory to write generated tests.

    Returns:
        TestGenerationReport with generated test metadata.
    """
    if output_dir is None:
        output_dir = project_dir / "output"
    if tests_dir is None:
        tests_dir = project_dir / "tests" / "generated"

    report = TestGenerationReport(project_name=project_dir.name)

    # --- Acceptance tests from PRD ---
    prd_files = list(output_dir.glob("*-prd.md")) + list(output_dir.glob("*prd*.md"))
    for prd_path in prd_files:
        scenarios = _parse_prd_scenarios(prd_path)
        if not scenarios:
            continue

        # Group by feature
        features: dict[str, list[dict[str, str]]] = {}
        for s in scenarios:
            feat = s["feature"]
            if feat not in features:
                features[feat] = []
            features[feat].append(s)

        for feature_name, feat_scenarios in features.items():
            feature_filename = re.sub(r"[^a-zA-Z0-9]", "_", feature_name.lower())
            feature_filename = f"{feature_filename}.feature"

            content = _render_gherkin_feature(feature_name, feat_scenarios)

            acceptance_dir = tests_dir / "acceptance"
            acceptance_dir.mkdir(parents=True, exist_ok=True)
            file_path = acceptance_dir / feature_filename
            file_path.write_text(content, encoding="utf-8")

            test = GeneratedTest(
                name=feature_filename,
                test_type="acceptance",
                path=str(file_path),
                content=content,
                requirement_ids=[s["id"] for s in feat_scenarios],
            )
            report.tests.append(test)
            report.acceptance_tests += 1

    # --- Contract tests from architecture doc ---
    arch_files = list(output_dir.glob("*-architecture.md")) + list(
        output_dir.glob("*architecture*.md")
    )
    for arch_path in arch_files:
        routes = _parse_api_routes(arch_path)
        if not routes:
            continue

        content = _render_contract_test(routes)

        contract_dir = tests_dir / "contract"
        contract_dir.mkdir(parents=True, exist_ok=True)
        file_path = contract_dir / "test_api_contract.py"
        file_path.write_text(content, encoding="utf-8")

        test = GeneratedTest(
            name="test_api_contract.py",
            test_type="contract",
            path=str(file_path),
            content=content,
            requirement_ids=[f"{r['method']} {r['path']}" for r in routes],
        )
        report.tests.append(test)
        report.contract_tests += 1

    report.total_generated = len(report.tests)

    # Write report
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test-generation-report.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report
