"""
Feedback Collector — post-delivery lessons to knowledge base evolution.

Parses git log for recent bug fixes, hotfixes, and rollbacks, maps them
to knowledge domains, and generates candidate knowledge entries for review.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.feedback_collector")

# Map commit message keywords to knowledge domains
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "security": [
        "security",
        "vulnerability",
        "xss",
        "csrf",
        "injection",
        "auth",
        "token",
        "sanitize",
        "escape",
        "csp",
    ],
    "frontend": [
        "ui",
        "css",
        "layout",
        "render",
        "component",
        "style",
        "responsive",
        "animation",
        "icon",
    ],
    "backend": [
        "api",
        "route",
        "endpoint",
        "controller",
        "service",
        "database",
        "query",
        "migration",
    ],
    "performance": [
        "performance",
        "slow",
        "optimize",
        "memory",
        "cache",
        "lazy",
        "bundle",
        "chunk",
    ],
    "testing": [
        "test",
        "coverage",
        "spec",
        "assertion",
        "mock",
        "fixture",
        "e2e",
        "integration",
    ],
    "architecture": [
        "refactor",
        "architect",
        "module",
        "dependency",
        "coupling",
        "interface",
        "abstraction",
    ],
}


@dataclass
class FeedbackEntry:
    """A single feedback entry from post-delivery analysis."""

    commit_hash: str = ""
    commit_message: str = ""
    commit_type: str = ""  # fix | refactor | feat | revert
    domain: str = ""
    lesson: str = ""
    suggested_knowledge_file: str = ""
    confidence: float = 0.0
    timestamp: str = ""


@dataclass
class FeedbackReport:
    """Full feedback collection report."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_commits_analyzed: int = 0
    feedback_entries: int = 0
    entries: list[FeedbackEntry] = field(default_factory=list)
    domain_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "total_commits_analyzed": self.total_commits_analyzed,
            "feedback_entries": self.feedback_entries,
            "entries": [asdict(e) for e in self.entries],
            "domain_distribution": self.domain_distribution,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Feedback Collection Report",
            "",
            f"**Project**: {self.project_name}",
            f"**Generated**: {self.generated_at}",
            f"**Commits Analyzed**: {self.total_commits_analyzed}",
            f"**Feedback Entries**: {self.feedback_entries}",
            "",
            "---",
            "",
        ]

        if self.domain_distribution:
            lines.extend(["## Domain Distribution", ""])
            for domain, count in sorted(
                self.domain_distribution.items(), key=lambda x: -x[1]
            ):
                lines.append(f"- **{domain}**: {count} entries")
            lines.append("")

        if self.entries:
            lines.extend(
                [
                    "## Feedback Entries",
                    "",
                    "| Commit | Type | Domain | Lesson |",
                    "|:---|:---:|:---|:---|",
                ]
            )
            for e in self.entries:
                lines.append(
                    f"| {e.commit_hash[:7]} | {e.commit_type} | {e.domain} | {e.lesson[:80]} |"
                )
            lines.append("")

        return "\n".join(lines)


def _classify_commit(message: str) -> str:
    """Classify commit type from message."""
    msg_lower = message.lower()
    if msg_lower.startswith("fix") or "bug" in msg_lower or "hotfix" in msg_lower:
        return "fix"
    if msg_lower.startswith("revert") or "rollback" in msg_lower:
        return "revert"
    if msg_lower.startswith("refactor"):
        return "refactor"
    if msg_lower.startswith("feat") or "add" in msg_lower:
        return "feat"
    return "other"


def _classify_domain(message: str) -> str:
    """Map commit message to knowledge domain."""
    msg_lower = message.lower()
    domain_scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            domain_scores[domain] = score

    if not domain_scores:
        return "general"

    return max(domain_scores, key=lambda d: domain_scores[d])


def _suggest_knowledge_file(domain: str) -> str:
    """Suggest a knowledge file path for the domain."""
    domain_to_path: dict[str, str] = {
        "security": "knowledge/security/",
        "frontend": "knowledge/frontend/",
        "backend": "knowledge/backend/",
        "performance": "knowledge/development/",
        "testing": "knowledge/testing/",
        "architecture": "knowledge/architecture/",
        "general": "knowledge/development/",
    }
    return domain_to_path.get(domain, "knowledge/")


def _extract_lesson(commit_type: str, message: str) -> str:
    """Extract a lesson from the commit."""
    # Remove conventional commit prefix
    cleaned = re.sub(r"^(fix|feat|refactor|revert|chore|docs|ci)\([^)]*\):\s*", "", message)
    cleaned = cleaned.strip()

    if commit_type == "fix":
        return f"Bug fixed: {cleaned}"
    if commit_type == "revert":
        return f"Rollback needed: {cleaned}"
    if commit_type == "refactor":
        return f"Refactored: {cleaned}"
    return cleaned


def run_feedback_collection(
    project_dir: Path,
    max_commits: int = 100,
) -> FeedbackReport:
    """Run post-delivery feedback collection from git history.

    Args:
        project_dir: Root of the project.
        max_commits: Maximum number of commits to analyze.

    Returns:
        FeedbackReport with collected feedback entries.
    """
    report = FeedbackReport(project_name=project_dir.name)

    try:
        import subprocess

        result = subprocess.run(
            [
                "git",
                "log",
                f"-{max_commits}",
                '--format=%H|%s|%aI',
            ],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return report

        commits = []
        for line in result.stdout.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) >= 3:
                commits.append(
                    {
                        "hash": parts[0],
                        "message": parts[1],
                        "timestamp": parts[2],
                    }
                )

        report.total_commits_analyzed = len(commits)

        for commit in commits:
            msg = commit["message"]
            commit_type = _classify_commit(msg)

            # Only collect lessons from fixes, reverts, and significant refactors
            if commit_type not in ("fix", "revert", "refactor"):
                continue

            domain = _classify_domain(msg)
            lesson = _extract_lesson(commit_type, msg)

            entry = FeedbackEntry(
                commit_hash=commit["hash"],
                commit_message=msg,
                commit_type=commit_type,
                domain=domain,
                lesson=lesson,
                suggested_knowledge_file=_suggest_knowledge_file(domain),
                confidence=0.8 if commit_type == "fix" else 0.6,
                timestamp=commit["timestamp"],
            )
            report.entries.append(entry)

            # Track domain distribution
            if domain not in report.domain_distribution:
                report.domain_distribution[domain] = 0
            report.domain_distribution[domain] += 1

    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    report.feedback_entries = len(report.entries)

    # Persist
    super_dev_dir = project_dir / ".super-dev"
    super_dev_dir.mkdir(parents=True, exist_ok=True)

    (super_dev_dir / "feedback-candidates.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (super_dev_dir / "feedback-candidates.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )

    return report
