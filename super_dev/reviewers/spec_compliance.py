"""
Spec Compliance Checker — requirement-to-code traceability matrix.

Parses PRD requirements from output/*-prd.md, scans implementation files,
and generates a traceability matrix showing which requirements map to which
code files, with confidence scoring.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..artifact_utils import resolve_project_artifact_prefix
from ..evidence_identity import (
    build_evidence_identity,
    evidence_identity_matches,
    load_json_payload,
)

_LANGUAGE_MAP: dict[str, tuple[str, ...]] = {
    "python": (".py",),
    "javascript": (".js", ".jsx"),
    "typescript": (".ts", ".tsx"),
    "vue": (".vue",),
    "svelte": (".svelte",),
    "css": (".css", ".scss", ".less"),
    "html": (".html", ".htm"),
}

_ALL_CODE_EXTENSIONS: set[str] = set()
for _exts in _LANGUAGE_MAP.values():
    _ALL_CODE_EXTENSIONS.update(_exts)

_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "coverage",
        ".super-dev",
        "output",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "venv",
        "env",
        ".venv",
    }
)


@dataclass
class RequirementMatch:
    """Traceability link between a requirement and code."""

    requirement_id: str
    requirement_text: str
    status: str  # found | partial | missing
    files: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """Full spec compliance report."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_requirements: int = 0
    found: int = 0
    partial: int = 0
    missing: int = 0
    score: int = 0
    matches: list[RequirementMatch] = field(default_factory=list)
    evidence_identity: dict[str, Any] = field(default_factory=dict)

    @property
    def coverage_percent(self) -> float:
        if self.total_requirements == 0:
            return 100.0
        return round((self.found + 0.5 * self.partial) / self.total_requirements * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "total_requirements": self.total_requirements,
            "found": self.found,
            "partial": self.partial,
            "missing": self.missing,
            "score": self.score,
            "coverage_percent": self.coverage_percent,
            "matches": [asdict(m) for m in self.matches],
            "evidence_identity": dict(self.evidence_identity),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Spec Compliance Report",
            "",
            f"**Project**: {self.project_name}",
            f"**Generated**: {self.generated_at}",
            f"**Requirements**: {self.total_requirements}",
            f"**Found**: {self.found} | **Partial**: {self.partial} | **Missing**: {self.missing}",
            f"**Coverage**: {self.coverage_percent}%",
            f"**Score**: {self.score}/100",
            "",
            "---",
            "",
            "| ID | Requirement | Status | Confidence | Files |",
            "|:---|:---|:---:|:---:|:---|",
        ]
        for m in self.matches:
            status_label = {"found": "PASS", "partial": "PARTIAL", "missing": "MISS"}[
                m.status
            ]
            files_str = ", ".join(m.files[:3])
            if len(m.files) > 3:
                files_str += f" +{len(m.files) - 3} more"
            req_text = m.requirement_text[:60] + "..." if len(m.requirement_text) > 60 else m.requirement_text
            lines.append(
                f"| {m.requirement_id} | {req_text} | {status_label} | {m.confidence:.0%} | {files_str} |"
            )
        lines.append("")
        return "\n".join(lines)


def _parse_prd_requirements(prd_path: Path) -> list[tuple[str, str]]:
    """Extract requirements from PRD markdown.

    Looks for numbered items and heading-structured sections.
    Returns list of (requirement_id, requirement_text).
    """
    requirements: list[tuple[str, str]] = []
    content = prd_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")

    current_section = ""
    req_counter = 0
    for line in lines:
        heading_match = re.match(r"^#{1,4}\s+(.+)", line)
        if heading_match:
            current_section = heading_match.group(1).strip()
            continue

        # Match numbered requirements: "1. xxx" or "- xxx" or "* xxx"
        req_match = re.match(r"^(?:\d+\.\s+|[-*]\s+)(.+)", line)
        if req_match and len(req_match.group(1).strip()) > 10:
            req_counter += 1
            section_prefix = re.sub(r"[^a-zA-Z0-9]", "", current_section[:20]) if current_section else "REQ"
            req_id = f"{section_prefix}-{req_counter:03d}"
            requirements.append((req_id, req_match.group(1).strip()))

    return requirements


def _extract_keywords(text: str) -> list[str]:
    """Extract searchable keywords from requirement text."""
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "and", "or", "but", "not", "no", "nor", "so", "yet", "both",
        "either", "neither", "each", "every", "all", "any", "few", "more",
        "most", "other", "some", "such", "than", "too", "very",
        "user", "system", "page", "feature", "function", "data",
    }
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_-]{2,}", text.lower())
    return [w for w in words if w not in stop_words]


def _scan_code_files(project_dir: Path) -> dict[str, str]:
    """Scan project for code files, return {relative_path: content}."""
    files: dict[str, str] = {}
    for path in project_dir.rglob("*"):
        if path.is_file() and path.suffix in _ALL_CODE_EXTENSIONS:
            # Skip ignored directories
            parts = path.relative_to(project_dir).parts
            if any(p in _IGNORE_DIRS for p in parts):
                continue
            try:
                rel = str(path.relative_to(project_dir))
                files[rel] = path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, ValueError):
                continue
    return files


def _scan_code_file_paths(project_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in project_dir.rglob("*"):
        if not path.is_file() or path.suffix not in _ALL_CODE_EXTENSIONS:
            continue
        parts = path.relative_to(project_dir).parts
        if any(p in _IGNORE_DIRS for p in parts):
            continue
        paths.append(path.resolve())
    return sorted(paths)


def _report_paths(project_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    project_name = resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)
    return (
        output_dir / f"{project_name}-spec-compliance.json",
        output_dir / "spec-compliance.json",
    )


def _report_dependencies(project_dir: Path, output_dir: Path) -> list[Path]:
    prd_files = sorted(list(output_dir.glob("*-prd.md")) + list(output_dir.glob("*prd*.md")))
    return [*prd_files, *_scan_code_file_paths(project_dir)]


def _load_existing_report(
    project_dir: Path,
    output_dir: Path,
    *,
    expected_identity: dict[str, Any],
) -> ComplianceReport | None:
    prefixed_json, fallback_json = _report_paths(project_dir, output_dir)
    for path in (prefixed_json, fallback_json):
        payload = load_json_payload(path)
        if not payload:
            continue
        identity_ok, _ = evidence_identity_matches(payload, expected=expected_identity)
        if not identity_ok:
            continue
        matches_payload = payload.get("matches", [])
        matches = [
            RequirementMatch(**item)
            for item in matches_payload
            if isinstance(item, dict)
        ]
        return ComplianceReport(
            project_name=str(payload.get("project_name", "")).strip(),
            generated_at=str(payload.get("generated_at", "")).strip()
            or datetime.now(timezone.utc).isoformat(),
            total_requirements=int(payload.get("total_requirements", 0) or 0),
            found=int(payload.get("found", 0) or 0),
            partial=int(payload.get("partial", 0) or 0),
            missing=int(payload.get("missing", 0) or 0),
            score=int(payload.get("score", 0) or 0),
            matches=matches,
            evidence_identity=dict(payload.get("evidence_identity", {}))
            if isinstance(payload.get("evidence_identity", {}), dict)
            else {},
        )
    return None


def inspect_spec_compliance_artifact(
    project_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if output_dir is None:
        output_dir = project_dir / "output"
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()
    expected_identity = build_evidence_identity(
        project_dir,
        artifact_name="spec-compliance",
        dependencies=_report_dependencies(project_dir, output_dir),
    )
    prefixed_json, fallback_json = _report_paths(project_dir, output_dir)
    for path in (prefixed_json, fallback_json):
        if not path.exists():
            continue
        payload = load_json_payload(path)
        if not payload:
            return {
                "status": "unreadable",
                "path": str(path),
                "expected_identity": expected_identity,
            }
        identity = payload.get("evidence_identity", {})
        if not isinstance(identity, dict) or not str(identity.get("inputs_digest", "")).strip():
            return {
                "status": "identity_missing",
                "path": str(path),
                "expected_identity": expected_identity,
            }
        identity_ok, _ = evidence_identity_matches(payload, expected=expected_identity)
        if not identity_ok:
            return {
                "status": "identity_mismatch",
                "path": str(path),
                "expected_identity": expected_identity,
            }
        return {
            "status": "ready",
            "path": str(path),
            "expected_identity": expected_identity,
        }
    return {
        "status": "missing",
        "path": str(prefixed_json),
        "expected_identity": expected_identity,
    }


def _match_requirement(
    req_id: str,
    req_text: str,
    code_files: dict[str, str],
) -> RequirementMatch:
    """Match a single requirement against code files."""
    keywords = _extract_keywords(req_text)
    if not keywords:
        return RequirementMatch(
            requirement_id=req_id,
            requirement_text=req_text,
            status="missing",
        )

    matches: list[tuple[str, float, list[str]]] = []
    for file_path, content in code_files.items():
        evidence: list[str] = []
        hit_count = 0
        content_lower = content.lower()
        for kw in keywords:
            if kw.lower() in content_lower:
                hit_count += 1
                # Find the line with the keyword
                for line_idx, line in enumerate(content.split("\n")):
                    if kw.lower() in line.lower() and len(evidence) < 2:
                        evidence.append(f"{file_path}:{line_idx + 1}: {line.strip()[:80]}")

        if hit_count > 0:
            confidence = min(hit_count / len(keywords), 1.0)
            matches.append((file_path, confidence, evidence))

    if not matches:
        return RequirementMatch(
            requirement_id=req_id,
            requirement_text=req_text,
            status="missing",
        )

    # Sort by confidence
    matches.sort(key=lambda x: x[1], reverse=True)
    top_files = [m[0] for m in matches[:5]]
    top_evidence = []
    for m in matches[:3]:
        top_evidence.extend(m[2])

    best_confidence = matches[0][1]
    if best_confidence >= 0.5:
        status = "found"
    elif best_confidence >= 0.2:
        status = "partial"
    else:
        status = "missing"

    return RequirementMatch(
        requirement_id=req_id,
        requirement_text=req_text,
        status=status,
        files=top_files,
        confidence=round(best_confidence, 3),
        evidence=top_evidence,
    )


def run_spec_compliance(
    project_dir: Path,
    output_dir: Path | None = None,
) -> ComplianceReport:
    """Run spec compliance check: PRD requirements vs. implementation code.

    Args:
        project_dir: Root of the project to scan.
        output_dir: Directory to write reports. Defaults to project_dir/output/.

    Returns:
        ComplianceReport with traceability matrix.
    """
    if output_dir is None:
        output_dir = project_dir / "output"
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()

    dependencies = _report_dependencies(project_dir, output_dir)
    expected_identity = build_evidence_identity(
        project_dir,
        artifact_name="spec-compliance",
        dependencies=dependencies,
    )
    cached = _load_existing_report(
        project_dir,
        output_dir,
        expected_identity=expected_identity,
    )
    if cached is not None:
        return cached

    report = ComplianceReport(
        project_name=resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)
    )
    report.evidence_identity = expected_identity

    # Find PRD files
    prd_files = list(output_dir.glob("*-prd.md")) + list(output_dir.glob("*prd*.md"))
    if not prd_files:
        report.score = 0
        return report

    # Collect all requirements
    all_requirements: list[tuple[str, str]] = []
    for prd_path in prd_files:
        all_requirements.extend(_parse_prd_requirements(prd_path))

    if not all_requirements:
        report.score = 100
        report.total_requirements = 0
        return report

    report.total_requirements = len(all_requirements)

    # Scan code
    code_files = _scan_code_files(project_dir)
    if not code_files:
        for req_id, req_text in all_requirements:
            report.matches.append(
                RequirementMatch(
                    requirement_id=req_id,
                    requirement_text=req_text,
                    status="missing",
                )
            )
        report.missing = report.total_requirements
        report.score = 0
        return report

    # Match each requirement
    for req_id, req_text in all_requirements:
        match = _match_requirement(req_id, req_text, code_files)
        report.matches.append(match)
        if match.status == "found":
            report.found += 1
        elif match.status == "partial":
            report.partial += 1
        else:
            report.missing += 1

    # Calculate score
    report.score = int(report.coverage_percent)

    # Persist reports
    output_dir.mkdir(parents=True, exist_ok=True)
    prefixed_json = output_dir / f"{report.project_name}-spec-compliance.json"
    prefixed_md = output_dir / f"{report.project_name}-spec-compliance.md"
    payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    (output_dir / "spec-compliance.json").write_text(
        payload,
        encoding="utf-8",
    )
    (output_dir / "spec-compliance.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )
    prefixed_json.write_text(payload, encoding="utf-8")
    prefixed_md.write_text(report.to_markdown(), encoding="utf-8")

    return report
