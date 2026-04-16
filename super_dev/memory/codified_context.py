"""
Codified Context Engine — auto-evolving project memory across sessions.

Parses session history, workflow events, and pipeline artifacts to extract
persistent project knowledge that survives across sessions.

Inspired by "Codified Context: Infrastructure for AI Agents in a Complex Codebase"
(arxiv 2602.20478, 2026).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.codified_context")

_TOKEN_BUDGET = 4000  # ~4K tokens ≈ 16K characters


@dataclass
class ContextEntry:
    """A single codified context entry."""

    category: str  # constraint | discovery | gotcha | pattern | api_route | lib_version
    content: str
    source: str = ""  # Where this was discovered
    confidence: float = 1.0
    phase: str = ""  # Pipeline phase when discovered
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CodifiedContextReport:
    """Report from codified context evolution."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    entries: list[ContextEntry] = field(default_factory=list)
    total_entries: int = 0
    total_chars: int = 0
    output_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "entries": [asdict(e) for e in self.entries],
            "total_entries": self.total_entries,
            "total_chars": self.total_chars,
            "output_path": self.output_path,
        }


def _estimate_chars(tokens: int) -> int:
    """Rough estimate: 1 token ≈ 4 chars."""
    return tokens * 4


def _parse_workflow_events(events_path: Path) -> list[dict[str, Any]]:
    """Parse workflow-events.jsonl for session events."""
    events: list[dict[str, Any]] = []
    if not events_path.exists():
        return events
    try:
        for line in events_path.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return events


def _parse_workflow_history(history_dir: Path) -> list[dict[str, Any]]:
    """Parse workflow history snapshots."""
    snapshots: list[dict[str, Any]] = []
    if not history_dir.exists():
        return snapshots
    for snap_path in history_dir.glob("*.json"):
        try:
            data = json.loads(snap_path.read_text(encoding="utf-8"))
            snapshots.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return snapshots


def _parse_decisions(decisions_dir: Path) -> list[dict[str, Any]]:
    """Parse ADR decisions."""
    decisions: list[dict[str, Any]] = []
    if not decisions_dir.exists():
        return decisions
    for dec_path in sorted(decisions_dir.glob("*.md"))[:50]:  # Cap at 50 most recent
        try:
            content = dec_path.read_text(encoding="utf-8", errors="ignore")
            # Extract title and status from first few lines
            title = ""
            status = ""
            for line in content.split("\n")[:10]:
                if line.startswith("# "):
                    title = line[2:].strip()
                if "Status:" in line or "状态:" in line:
                    status = line.split(":", 1)[1].strip()
            if title:
                decisions.append({
                    "title": title,
                    "status": status,
                    "file": dec_path.name,
                    "content": content[:500],
                })
        except OSError:
            continue
    return decisions


def _extract_from_output(output_dir: Path) -> list[ContextEntry]:
    """Extract context entries from pipeline output artifacts."""
    entries: list[ContextEntry] = []
    if not output_dir.exists():
        return entries

    # Extract from architecture doc
    for arch_path in output_dir.glob("*-architecture.md"):
        try:
            content = arch_path.read_text(encoding="utf-8", errors="ignore")
            # Extract tech stack declarations
            tech_matches = re.findall(
                r"(?:Framework|Language|Database|Runtime|Lib)\s*[:\-]\s*(.+)",
                content,
                re.IGNORECASE,
            )
            for tech in tech_matches:
                tech = tech.strip()
                if tech and len(tech) < 80:
                    entries.append(
                        ContextEntry(
                            category="constraint",
                            content=f"Tech stack: {tech}",
                            source=str(arch_path.name),
                            phase="docs",
                        )
                    )

            # Extract API routes
            route_matches = re.findall(
                r"(?:GET|POST|PUT|DELETE|PATCH)\s+(`?[a-zA-Z0-9/{}_-]+`?)",
                content,
            )
            for route in route_matches:
                entries.append(
                    ContextEntry(
                        category="api_route",
                        content=f"Declared API route: {route}",
                        source=str(arch_path.name),
                        phase="docs",
                    )
                )
        except OSError:
            pass

    return entries


def _extract_from_git_log(project_dir: Path) -> list[ContextEntry]:
    """Extract context from recent git history."""
    entries: list[ContextEntry] = []
    try:
        import subprocess

        result = subprocess.run(
            ["git", "log", "--oneline", "-30", "--format=%s"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Detect patterns
                if "fix" in line.lower() or "bug" in line.lower():
                    entries.append(
                        ContextEntry(
                            category="gotcha",
                            content=f"Bug fix: {line}",
                            source="git-log",
                            confidence=0.7,
                        )
                    )
                elif "feat" in line.lower() or "add" in line.lower():
                    entries.append(
                        ContextEntry(
                            category="discovery",
                            content=f"Feature added: {line}",
                            source="git-log",
                            confidence=0.6,
                        )
                    )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return entries


def _render_markdown(entries: list[ContextEntry], project_name: str) -> str:
    """Render codified context as markdown."""
    lines = [
        f"# Codified Context — {project_name}",
        "",
        "<!-- Auto-generated by Super Dev. Do not edit manually. -->",
        "<!-- This file evolves across sessions with project-specific knowledge. -->",
        "",
    ]

    # Group by category
    categories: dict[str, list[ContextEntry]] = {}
    for entry in entries:
        if entry.category not in categories:
            categories[entry.category] = []
        categories[entry.category].append(entry)

    category_labels = {
        "constraint": "Constraints (Hard Rules)",
        "discovery": "Discoveries",
        "gotcha": "Gotchas & Pitfalls",
        "pattern": "Patterns",
        "api_route": "API Routes",
        "lib_version": "Library Versions",
    }

    for cat_key, cat_label in category_labels.items():
        cat_entries = categories.get(cat_key, [])
        if not cat_entries:
            continue

        lines.extend([f"## {cat_label}", ""])
        # Deduplicate by content
        seen: set[str] = set()
        for entry in cat_entries:
            if entry.content in seen:
                continue
            seen.add(entry.content)
            source_note = f" ({entry.source})" if entry.source else ""
            lines.append(f"- {entry.content}{source_note}")
        lines.append("")

    return "\n".join(lines)


def evolve_codified_context(project_dir: Path) -> CodifiedContextReport:
    """Evolve codified context from session history and artifacts.

    Reads workflow events, decisions, output artifacts, and git history,
    extracts persistent knowledge, and writes to .super-dev/codified-context.md.

    Args:
        project_dir: Root of the project.

    Returns:
        CodifiedContextReport with extracted entries.
    """
    super_dev_dir = project_dir / ".super-dev"
    output_dir = project_dir / "output"

    report = CodifiedContextReport(project_name=project_dir.name)

    all_entries: list[ContextEntry] = []

    # 1. Extract from workflow events
    events = _parse_workflow_events(super_dev_dir / "workflow-events.jsonl")
    for event in events[-100:]:  # Last 100 events
        event_type = event.get("type", "")
        if "error" in event_type.lower() or "fail" in event_type.lower():
            msg = event.get("message", event.get("detail", ""))
            if msg and len(msg) < 200:
                all_entries.append(
                    ContextEntry(
                        category="gotcha",
                        content=f"Previous error: {msg}",
                        source="workflow-events",
                        confidence=0.8,
                    )
                )

    # 2. Extract from decisions
    decisions = _parse_decisions(super_dev_dir / "decisions")
    for dec in decisions:
        if dec.get("status", "").lower() in ("accepted", "approved"):
            all_entries.append(
                ContextEntry(
                    category="constraint",
                    content=f"ADR: {dec['title']}",
                    source=dec["file"],
                    confidence=0.9,
                )
            )

    # 3. Extract from output artifacts
    all_entries.extend(_extract_from_output(output_dir))

    # 4. Extract from git log
    all_entries.extend(_extract_from_git_log(project_dir))

    # 5. Load existing codified context and merge
    existing_path = super_dev_dir / "codified-context.md"
    if existing_path.exists():
        try:
            existing_content = existing_path.read_text(encoding="utf-8")
            # Parse existing entries (lines starting with "- ")
            for line in existing_content.split("\n"):
                line = line.strip()
                if line.startswith("- ") and len(line) > 3:
                    # Check it's not already in new entries
                    content = line[2:].strip()
                    # Remove source notes in parentheses
                    content = re.sub(r"\s*\([^)]+\)$", "", content)
                    if not any(e.content == content for e in all_entries):
                        all_entries.append(
                            ContextEntry(
                                category="constraint",
                                content=content,
                                source="existing-context",
                                confidence=0.5,
                            )
                        )
        except OSError:
            pass

    # Sort by confidence (highest first)
    all_entries.sort(key=lambda e: e.confidence, reverse=True)

    # Deduplicate
    seen_content: set[str] = set()
    unique_entries: list[ContextEntry] = []
    for entry in all_entries:
        if entry.content not in seen_content:
            seen_content.add(entry.content)
            unique_entries.append(entry)

    # Enforce token budget
    markdown = _render_markdown(unique_entries, project_dir.name)
    char_budget = _estimate_chars(_TOKEN_BUDGET)
    while len(markdown) > char_budget and len(unique_entries) > 1:
        # Remove lowest confidence entries
        unique_entries.pop()
        markdown = _render_markdown(unique_entries, project_dir.name)

    # Write
    super_dev_dir.mkdir(parents=True, exist_ok=True)
    existing_path.write_text(markdown, encoding="utf-8")

    report.entries = unique_entries
    report.total_entries = len(unique_entries)
    report.total_chars = len(markdown)
    report.output_path = str(existing_path)

    return report
