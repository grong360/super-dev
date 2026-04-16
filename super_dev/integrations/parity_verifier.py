"""
Multi-Host Parity Verifier — cross-host commands/skills consistency checker.

Scans all host directories and compares command/skill files for content
consistency, ensuring all 18+ hosts have equivalent governance coverage.
"""

from __future__ import annotations

import difflib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.parity_verifier")

# Known host directories and their content types
_HOST_REGISTRY: dict[str, dict[str, str]] = {
    "claude-code": {
        "dir": ".claude",
        "commands_dir": "commands",
        "skills_dir": "skills",
        "workflows_dir": "workflows",
    },
    "cursor": {
        "dir": ".cursor",
        "commands_dir": "commands",
    },
    "codebuddy": {
        "dir": ".codebuddy",
        "commands_dir": "commands",
        "agents_dir": "agents",
        "skills_dir": "skills",
    },
    "codex": {
        "dir": ".codex",
        "skills_dir": "skills",
    },
    "openclaw": {
        "dir": ".openclaw",
        "commands_dir": "commands",
    },
    "opencode": {
        "dir": ".opencode",
        "commands_dir": "commands",
        "skills_dir": "skills",
    },
    "qoder": {
        "dir": ".qoder",
        "commands_dir": "commands",
        "skills_dir": "skills",
    },
    "kilocode": {
        "dir": ".kilocode",
        "commands_dir": "commands",
        "skills_dir": "skills",
    },
    "windsurf": {
        "dir": ".windsurf",
        "skills_dir": "skills",
    },
    "kiro": {
        "dir": ".kiro",
        "skills_dir": "skills",
    },
    "roo": {
        "dir": ".roo",
        "skills_dir": "skills",
    },
    "trae": {
        "dir": ".trae",
        "commands_dir": "commands",
    },
    "cline": {
        "dir": ".cline",
        "rules_dir": "rules",
    },
    "clinerules": {
        "dir": ".clinerules",
    },
    "junie": {
        "dir": ".junie",
        "workflows_dir": "workflows",
    },
}


@dataclass
class ParityDiff:
    """A single parity difference between hosts."""

    item_name: str
    item_type: str  # command | skill | agent | workflow | rule
    reference_host: str
    reference_content_hash: str = ""
    hosts_with_it: list[str] = field(default_factory=list)
    hosts_missing_it: list[str] = field(default_factory=list)
    content_diffs: dict[str, int] = field(default_factory=dict)  # host -> line diff count

    @property
    def is_parity_issue(self) -> bool:
        return len(self.hosts_missing_it) > 0 or any(v > 5 for v in self.content_diffs.values())


@dataclass
class ParityReport:
    """Full parity verification report."""

    project_name: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hosts_scanned: int = 0
    total_items: int = 0
    parity_issues: int = 0
    diffs: list[ParityDiff] = field(default_factory=list)
    score: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "hosts_scanned": self.hosts_scanned,
            "total_items": self.total_items,
            "parity_issues": self.parity_issues,
            "diffs": [
                {
                    "item_name": d.item_name,
                    "item_type": d.item_type,
                    "reference_host": d.reference_host,
                    "hosts_with_it": d.hosts_with_it,
                    "hosts_missing_it": d.hosts_missing_it,
                    "content_diffs": d.content_diffs,
                    "is_parity_issue": d.is_parity_issue,
                }
                for d in self.diffs
            ],
            "score": self.score,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Multi-Host Parity Report",
            "",
            f"**Project**: {self.project_name}",
            f"**Generated**: {self.generated_at}",
            f"**Hosts Scanned**: {self.hosts_scanned}",
            f"**Total Items**: {self.total_items}",
            f"**Parity Issues**: {self.parity_issues}",
            f"**Score**: {self.score}/100",
            "",
            "---",
            "",
        ]

        issues = [d for d in self.diffs if d.is_parity_issue]
        if issues:
            lines.extend(
                [
                    "## Parity Issues",
                    "",
                    "| Item | Type | Reference | Missing In | Diff Hosts |",
                    "|:---|:---|:---|:---|:---|",
                ]
            )
            for d in issues:
                missing = ", ".join(d.hosts_missing_it) or "(none)"
                diff_hosts = ", ".join(
                    f"{h} ({v} lines)" for h, v in d.content_diffs.items() if v > 5
                ) or "(none)"
                lines.append(
                    f"| {d.item_name} | {d.item_type} | {d.reference_host} | {missing} | {diff_hosts} |"
                )
            lines.append("")
        else:
            lines.append("All hosts have parity. No issues found.")

        return "\n".join(lines)


def _content_hash(content: str) -> str:
    """Simple content hash for comparison."""
    import hashlib

    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


def _content_line_diff(ref: str, other: str) -> int:
    """Count lines that differ between two files."""
    ref_lines = ref.splitlines()
    other_lines = other.splitlines()
    matcher = difflib.SequenceMatcher(None, ref_lines, other_lines)
    diff_lines = sum(
        tag in ("replace", "delete", "insert")
        for tag, _i1, _i2, _j1, _j2 in matcher.get_opcodes()
    )
    return diff_lines


def _collect_items(
    project_dir: Path, host_id: str, host_config: dict[str, str]
) -> dict[str, dict[str, str]]:
    """Collect all items (commands, skills, etc.) for a host.

    Returns {item_name: {path: str, content: str, type: str}}.
    """
    host_dir = project_dir / host_config["dir"]
    items: dict[str, dict[str, str]] = {}

    if not host_dir.exists():
        return items

    # Commands
    cmd_dir_key = "commands_dir"
    if cmd_dir_key in host_config:
        cmd_dir = host_dir / host_config[cmd_dir_key]
        if cmd_dir.exists():
            for f in cmd_dir.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    items[f.stem] = {
                        "path": str(f),
                        "content": content,
                        "type": "command",
                    }
                except OSError:
                    pass

    # Skills (SKILL.md files)
    skills_key = "skills_dir"
    if skills_key in host_config:
        skills_dir = host_dir / host_config[skills_key]
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        try:
                            content = skill_md.read_text(encoding="utf-8", errors="ignore")
                            items[f"skill:{skill_dir.name}"] = {
                                "path": str(skill_md),
                                "content": content,
                                "type": "skill",
                            }
                        except OSError:
                            pass

    # Agents
    agents_key = "agents_dir"
    if agents_key in host_config:
        agents_dir = host_dir / host_config[agents_key]
        if agents_dir.exists():
            for f in agents_dir.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    items[f"agent:{f.stem}"] = {
                        "path": str(f),
                        "content": content,
                        "type": "agent",
                    }
                except OSError:
                    pass

    # Workflows
    wf_key = "workflows_dir"
    if wf_key in host_config:
        wf_dir = host_dir / host_config[wf_key]
        if wf_dir.exists():
            for f in wf_dir.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    items[f"workflow:{f.stem}"] = {
                        "path": str(f),
                        "content": content,
                        "type": "workflow",
                    }
                except OSError:
                    pass

    # Rules (clinerules)
    rules_key = "rules_dir"
    if rules_key in host_config:
        rules_dir = host_dir / host_config[rules_key]
        if rules_dir.exists():
            for f in rules_dir.glob("*.md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    items[f"rule:{f.stem}"] = {
                        "path": str(f),
                        "content": content,
                        "type": "rule",
                    }
                except OSError:
                    pass

    return items


def run_parity_check(
    project_dir: Path,
    reference_host: str = "claude-code",
    output_dir: Path | None = None,
) -> ParityReport:
    """Run multi-host parity verification.

    Args:
        project_dir: Root of the project.
        reference_host: Host ID to use as reference (default: claude-code).
        output_dir: Directory to write reports.

    Returns:
        ParityReport with consistency findings.
    """
    if output_dir is None:
        output_dir = project_dir / "output"

    report = ParityReport(project_name=project_dir.name)

    # Collect all items from all hosts
    host_items: dict[str, dict[str, dict[str, str]]] = {}
    for host_id, host_config in _HOST_REGISTRY.items():
        host_dir = project_dir / host_config["dir"]
        if host_dir.exists():
            items = _collect_items(project_dir, host_id, host_config)
            if items:
                host_items[host_id] = items

    report.hosts_scanned = len(host_items)

    if reference_host not in host_items:
        report.score = 0
        return report

    # Build unified item set from reference host
    ref_items = host_items[reference_host]
    all_item_names: set[str] = set(ref_items.keys())

    # Also collect items from other hosts that reference doesn't have
    for host_id, items in host_items.items():
        if host_id == reference_host:
            continue
        all_item_names.update(items.keys())

    report.total_items = len(all_item_names)

    # Compare each item across hosts
    for item_name in sorted(all_item_names):
        ref_data = ref_items.get(item_name)
        if ref_data is None:
            continue

        diff = ParityDiff(
            item_name=item_name,
            item_type=ref_data["type"],
            reference_host=reference_host,
            reference_content_hash=_content_hash(ref_data["content"]),
        )

        ref_content = ref_data["content"]

        for host_id, items in host_items.items():
            if host_id == reference_host:
                diff.hosts_with_it.append(host_id)
                continue

            host_data = items.get(item_name)
            if host_data is None:
                diff.hosts_missing_it.append(host_id)
                continue

            diff.hosts_with_it.append(host_id)
            line_diff = _content_line_diff(ref_content, host_data["content"])
            if line_diff > 0:
                diff.content_diffs[host_id] = line_diff

        report.diffs.append(diff)

    # Calculate score and issues
    report.parity_issues = sum(1 for d in report.diffs if d.is_parity_issue)
    if report.total_items > 0:
        report.score = int(
            (1 - report.parity_issues / report.total_items) * 100
        )
    else:
        report.score = 100

    # Persist
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "host-parity.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "host-parity.md").write_text(
        report.to_markdown(), encoding="utf-8"
    )

    return report
