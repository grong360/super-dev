"""
Architecture Drift Detector — compare architecture spec vs. actual implementation.

Parses output/*-architecture.md for declared modules, dependencies, and tech
stack, then builds an actual import graph from the codebase and reports drifts.
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

_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".next",
        ".super-dev",
        "output",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "venv",
        "env",
        ".venv",
        "super_dev.egg-info",
    }
)


@dataclass
class DriftItem:
    """A single architecture drift finding."""

    drift_type: str  # missing_module | extra_module | missing_dependency | extra_dependency | tech_mismatch
    declared: str = ""
    actual: str = ""
    severity: str = "medium"  # critical | high | medium | low
    description: str = ""
    file: str = ""


@dataclass
class DriftReport:
    """Full architecture drift report."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    declared_modules: list[str] = field(default_factory=list)
    actual_modules: list[str] = field(default_factory=list)
    declared_tech_stack: list[str] = field(default_factory=list)
    actual_tech_stack: list[str] = field(default_factory=list)
    drifts: list[DriftItem] = field(default_factory=list)
    score: int = 0
    evidence_identity: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for d in self.drifts if d.severity == "critical")

    @property
    def total_drifts(self) -> int:
        return len(self.drifts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "declared_modules": self.declared_modules,
            "actual_modules": self.actual_modules,
            "declared_tech_stack": self.declared_tech_stack,
            "actual_tech_stack": self.actual_tech_stack,
            "drifts": [asdict(d) for d in self.drifts],
            "score": self.score,
            "evidence_identity": dict(self.evidence_identity),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Architecture Drift Report",
            "",
            f"**Project**: {self.project_name}",
            f"**Generated**: {self.generated_at}",
            f"**Score**: {self.score}/100",
            f"**Total Drifts**: {self.total_drifts} (Critical: {self.critical_count})",
            "",
            "---",
            "",
        ]

        if self.drifts:
            lines.extend(
                [
                    "| Type | Declared | Actual | Severity | Description |",
                    "|:---|:---|:---|:---:|:---|",
                ]
            )
            for d in self.drifts:
                lines.append(
                    f"| {d.drift_type} | {d.declared} | {d.actual} | {d.severity} | {d.description} |"
                )
            lines.append("")

        if self.declared_tech_stack:
            lines.extend(["## Declared Tech Stack", ""])
            for t in self.declared_tech_stack:
                marker = ""
                if t.lower() not in " ".join(self.actual_tech_stack).lower():
                    marker = " **[NOT FOUND]**"
                lines.append(f"- {t}{marker}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Architecture doc parser
# ---------------------------------------------------------------------------


def _parse_architecture_doc(arch_path: Path) -> dict[str, Any]:
    """Extract declared modules, dependencies, tech stack from architecture doc."""
    content = arch_path.read_text(encoding="utf-8", errors="ignore")
    result: dict[str, Any] = {
        "modules": [],
        "dependencies": [],
        "tech_stack": [],
    }

    # Extract tech stack mentions
    tech_patterns = [
        r"(?:React|Next\.js|Vue|Angular|Svelte|Nuxt)\s*[\d.]*",
        r"(?:FastAPI|Flask|Django|Express|NestJS|Spring)\s*[\d.]*",
        r"(?:PostgreSQL|MySQL|MongoDB|Redis|SQLite|Prisma)\s*[\d.]*",
        r"(?:TypeScript|Python|Go|Rust|Java)\s*[\d.]*",
        r"(?:Tailwind|Bootstrap|Material|Ant Design|Chakra)\s*[\d.]*",
        r"(?:Docker|Kubernetes|Terraform|Ansible)\s*[\d.]*",
        r"(?:Redis|RabbitMQ|Kafka|Celery)\s*[\d.]*",
    ]
    for pat in tech_patterns:
        found = re.findall(pat, content, re.IGNORECASE)
        for f in found:
            cleaned = f.strip()
            if cleaned and cleaned.lower() not in [t.lower() for t in result["tech_stack"]]:
                result["tech_stack"].append(cleaned)

    # Extract module/section names from headings
    heading_pattern = re.compile(r"^#{1,4}\s+(?:Module|模块|Component|组件|Service|服务|Layer|层)\s*[:\-]?\s*(.+)", re.MULTILINE | re.IGNORECASE)
    for m in heading_pattern.finditer(content):
        mod_name = m.group(1).strip()
        if mod_name and len(mod_name) < 50:
            result["modules"].append(mod_name)

    # Extract directory structure from code blocks
    code_block_pattern = re.compile(r"```\n(.*?)```", re.DOTALL)
    for block_match in code_block_pattern.finditer(content):
        block = block_match.group(1)
        for line in block.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "/" in line:
                parts = line.split("/")
                if parts:
                    result["dependencies"].append(parts[0].strip())

    return result


# ---------------------------------------------------------------------------
# Code scanner
# ---------------------------------------------------------------------------


def _scan_imports(project_dir: Path) -> dict[str, list[str]]:
    """Build import graph from codebase. Returns {file: [imported_modules]}."""
    imports: dict[str, list[str]] = {}

    for path in project_dir.rglob("*"):
        if path.is_file():
            rel = ""
            try:
                rel = str(path.relative_to(project_dir))
            except ValueError:
                continue

            parts = path.relative_to(project_dir).parts
            if any(p in _IGNORE_DIRS for p in parts):
                continue

            if path.suffix == ".py":
                imports[rel] = _extract_python_imports(path)
            elif path.suffix in (".ts", ".tsx", ".js", ".jsx"):
                imports[rel] = _extract_js_imports(path)

    return imports


def _extract_python_imports(path: Path) -> list[str]:
    """Extract imported module names from a Python file."""
    modules: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return modules

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("import "):
            mod = line.replace("import ", "").split(",")[0].split(" as ")[0].strip()
            if mod:
                modules.append(mod)
        elif line.startswith("from "):
            match = re.match(r"from\s+([\w.]+)", line)
            if match:
                modules.append(match.group(1))

    return modules


def _extract_js_imports(path: Path) -> list[str]:
    """Extract imported module names from a JS/TS file."""
    modules: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return modules

    # ES module imports and require()
    for match in re.finditer(
        r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))",
        content,
    ):
        mod = match.group(1) or match.group(2) or ""
        if mod and not mod.startswith("."):
            modules.append(mod)

    return modules


def _scan_tech_stack(project_dir: Path) -> list[str]:
    """Detect actual tech stack from config files."""
    tech: list[str] = []

    # package.json
    pkg_path = project_dir / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            known_frameworks = {
                "react": "React",
                "next": "Next.js",
                "vue": "Vue",
                "nuxt": "Nuxt",
                "angular": "Angular",
                "svelte": "Svelte",
                "tailwindcss": "Tailwind CSS",
                "typescript": "TypeScript",
                "express": "Express",
                "fastify": "Fastify",
                "prisma": "Prisma",
            }
            for dep, label in known_frameworks.items():
                if dep in deps:
                    tech.append(f"{label} {deps[dep].lstrip('^~>=<')}")
        except (json.JSONDecodeError, OSError):
            pass

    # pyproject.toml / requirements
    for req_file in ("requirements.txt", "requirements.lock"):
        req_path = project_dir / req_file
        if req_path.exists():
            try:
                for line in req_path.read_text(encoding="utf-8").split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pkg_name = re.split(r"[><=!]", line)[0].strip()
                        if pkg_name:
                            tech.append(pkg_name)
            except OSError:
                pass

    # pyproject.toml dependencies
    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            dep_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if dep_match:
                for dep_line in dep_match.group(1).split("\n"):
                    dep_clean = dep_line.strip().strip('",')
                    if dep_clean:
                        tech.append(dep_clean)
        except OSError:
            pass

    return tech


def _scan_source_file_paths(project_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(project_dir).parts
        if any(p in _IGNORE_DIRS for p in parts):
            continue
        if path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            paths.append(path.resolve())
    return sorted(paths)


def _report_paths(project_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    project_name = resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)
    return (
        output_dir / f"{project_name}-architecture-drift.json",
        output_dir / "architecture-drift.json",
    )


def _report_dependencies(project_dir: Path, output_dir: Path) -> list[Path]:
    arch_files = sorted(list(output_dir.glob("*-architecture.md")) + list(output_dir.glob("*architecture*.md")))
    dependency_files = [
        project_dir / "package.json",
        project_dir / "pyproject.toml",
        project_dir / "requirements.txt",
        project_dir / "requirements.lock",
    ]
    return [
        *arch_files,
        *[path.resolve() for path in dependency_files if path.exists()],
        *_scan_source_file_paths(project_dir),
    ]


def _load_existing_report(
    project_dir: Path,
    output_dir: Path,
    *,
    expected_identity: dict[str, Any],
) -> DriftReport | None:
    prefixed_json, fallback_json = _report_paths(project_dir, output_dir)
    for path in (prefixed_json, fallback_json):
        payload = load_json_payload(path)
        if not payload:
            continue
        identity_ok, _ = evidence_identity_matches(payload, expected=expected_identity)
        if not identity_ok:
            continue
        drifts_payload = payload.get("drifts", [])
        drifts = [DriftItem(**item) for item in drifts_payload if isinstance(item, dict)]
        return DriftReport(
            project_name=str(payload.get("project_name", "")).strip(),
            generated_at=str(payload.get("generated_at", "")).strip()
            or datetime.now(timezone.utc).isoformat(),
            declared_modules=list(payload.get("declared_modules", []) or []),
            actual_modules=list(payload.get("actual_modules", []) or []),
            declared_tech_stack=list(payload.get("declared_tech_stack", []) or []),
            actual_tech_stack=list(payload.get("actual_tech_stack", []) or []),
            drifts=drifts,
            score=int(payload.get("score", 0) or 0),
            evidence_identity=dict(payload.get("evidence_identity", {}))
            if isinstance(payload.get("evidence_identity", {}), dict)
            else {},
        )
    return None


def inspect_architecture_drift_artifact(
    project_dir: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if output_dir is None:
        output_dir = project_dir / "output"
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()
    expected_identity = build_evidence_identity(
        project_dir,
        artifact_name="architecture-drift",
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


def run_architecture_drift(
    project_dir: Path,
    output_dir: Path | None = None,
) -> DriftReport:
    """Run architecture drift detection: spec vs. implementation.

    Args:
        project_dir: Root of the project to scan.
        output_dir: Directory to write reports. Defaults to project_dir/output/.

    Returns:
        DriftReport with drift findings.
    """
    if output_dir is None:
        output_dir = project_dir / "output"
    project_dir = project_dir.resolve()
    output_dir = output_dir.resolve()

    dependencies = _report_dependencies(project_dir, output_dir)
    expected_identity = build_evidence_identity(
        project_dir,
        artifact_name="architecture-drift",
        dependencies=dependencies,
    )
    cached = _load_existing_report(
        project_dir,
        output_dir,
        expected_identity=expected_identity,
    )
    if cached is not None:
        return cached

    report = DriftReport(
        project_name=resolve_project_artifact_prefix(project_dir, fallback_name=project_dir.name)
    )
    report.evidence_identity = expected_identity

    # Find architecture doc
    arch_files = list(output_dir.glob("*-architecture.md")) + list(
        output_dir.glob("*architecture*.md")
    )
    if not arch_files:
        report.score = 100
        return report

    # Parse declared architecture
    declared = _parse_architecture_doc(arch_files[0])
    report.declared_modules = declared["modules"]
    report.declared_tech_stack = declared["tech_stack"]

    # Scan actual
    _scan_imports(project_dir)
    actual_tech = _scan_tech_stack(project_dir)
    report.actual_tech_stack = actual_tech

    # Detect tech stack drifts
    for dt in declared_tech_stack_lower_unique(declared["tech_stack"]):
        found = any(dt in at.lower() for at in actual_tech)
        if not found:
            report.drifts.append(
                DriftItem(
                    drift_type="tech_mismatch",
                    declared=dt,
                    actual="(not detected)",
                    severity="high",
                    description=f"Declared tech {dt} not found in actual dependencies",
                )
            )

    # Build actual module list from directory structure
    actual_dirs: set[str] = set()
    for path in project_dir.iterdir():
        if path.is_dir() and path.name not in _IGNORE_DIRS and not path.name.startswith("."):
            actual_dirs.add(path.name)
    report.actual_modules = sorted(actual_dirs)

    # Score: start at 100, subtract for each drift
    penalty = 0
    for d in report.drifts:
        if d.severity == "critical":
            penalty += 15
        elif d.severity == "high":
            penalty += 10
        elif d.severity == "medium":
            penalty += 5
        else:
            penalty += 2
    report.score = max(0, 100 - penalty)

    # Persist reports
    output_dir.mkdir(parents=True, exist_ok=True)
    prefixed_json = output_dir / f"{report.project_name}-architecture-drift.json"
    prefixed_md = output_dir / f"{report.project_name}-architecture-drift.md"
    payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    (output_dir / "architecture-drift.json").write_text(
        payload,
        encoding="utf-8",
    )
    (output_dir / "architecture-drift.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )
    prefixed_json.write_text(payload, encoding="utf-8")
    prefixed_md.write_text(report.to_markdown(), encoding="utf-8")

    return report


def declared_tech_stack_lower_unique(tech_stack: list[str]) -> list[str]:
    """Extract unique lowercase tech names from declared stack."""
    result: list[str] = []
    seen: set[str] = set()
    for t in tech_stack:
        name = t.lower().split()[0]
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result
