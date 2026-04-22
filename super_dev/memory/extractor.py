"""
自动记忆提取器 — 从 pipeline 执行结果中提取 4 种记忆

每个 pipeline 阶段结束时调用 extract_from_phase()，
根据阶段类型自动提取 project / reference / feedback / user 记忆。
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .store import MemoryEntry, MemoryStore

_logger = logging.getLogger("super_dev.memory.extractor")


def _slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower().strip())
    slug = re.sub(r"[\s_]+", "_", slug)
    return slug[:max_len].rstrip("_")


def _make_filename(phase: str, label: str, ext: str = ".md") -> str:
    """Generate a deterministic filename for a memory entry."""
    slug = _slugify(label)
    short_hash = hashlib.sha256(f"{phase}:{label}".encode()).hexdigest()[:6]
    return f"{phase}_{slug}_{short_hash}{ext}"


def _safe_str(value: Any, max_len: int = 1000) -> str:
    text = str(value) if value else ""
    return text[:max_len] if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Phase-specific extraction rules
# ---------------------------------------------------------------------------


def _extract_discovery_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """discovery 阶段: 提取项目级记忆（技术栈、需求摘要）"""
    entries: list[MemoryEntry] = []
    user_input = context.get("user_input", {})
    metadata = context.get("metadata", {})

    # Tech stack
    tech_stack = metadata.get("tech_stack") or user_input.get("tech_stack")
    if tech_stack:
        content = (
            _safe_str(tech_stack)
            if isinstance(tech_stack, str)
            else (
                "\n".join(f"- {k}: {v}" for k, v in tech_stack.items())
                if isinstance(tech_stack, dict)
                else "\n".join(f"- {_safe_str(item)}" for item in tech_stack)
            )
        )
        entries.append(
            MemoryEntry(
                name="Project Tech Stack",
                description="Technology stack identified during discovery",
                type="project",
                filename=_make_filename(phase, "tech_stack"),
                content=content,
            )
        )

    # Requirements summary
    description = user_input.get("description", "")
    requirements = user_input.get("requirements", "")
    if description or requirements:
        content_parts = []
        if description:
            content_parts.append(f"## Description\n\n{_safe_str(description, 2000)}")
        if requirements:
            req_text = (
                _safe_str(requirements, 2000)
                if isinstance(requirements, str)
                else "\n".join(f"- {_safe_str(r)}" for r in requirements)
            )
            content_parts.append(f"## Requirements\n\n{req_text}")
        entries.append(
            MemoryEntry(
                name="Requirements Summary",
                description="Project requirements captured during discovery",
                type="project",
                filename=_make_filename(phase, "requirements_summary"),
                content="\n\n".join(content_parts),
            )
        )

    return entries


def _extract_intelligence_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """intelligence 阶段: 提取参考记忆（竞品 URL、工具发现）"""
    entries: list[MemoryEntry] = []
    research_data = context.get("research_data", {})

    # Competitors
    competitors = research_data.get("competitors", [])
    if competitors:
        if isinstance(competitors, list):
            lines = []
            for comp in competitors[:20]:
                if isinstance(comp, dict):
                    name = comp.get("name", "Unknown")
                    url = comp.get("url", "")
                    desc = comp.get("description", "")
                    line = f"- **{name}**"
                    if url:
                        line += f": {url}"
                    if desc:
                        line += f" — {desc}"
                    lines.append(line)
                else:
                    lines.append(f"- {_safe_str(comp, 300)}")
            content = "\n".join(lines)
        else:
            content = _safe_str(competitors, 2000)
        entries.append(
            MemoryEntry(
                name="Competitive Research",
                description="Competitor products and URLs from intelligence phase",
                type="reference",
                filename=_make_filename(phase, "competitive_research"),
                content=content,
            )
        )

    # Tools / insights
    tools = research_data.get("tools", research_data.get("insights", []))
    if tools:
        if isinstance(tools, list):
            content = "\n".join(f"- {_safe_str(t, 300)}" for t in tools[:20])
        else:
            content = _safe_str(tools, 2000)
        entries.append(
            MemoryEntry(
                name="Research Insights",
                description="Tools and insights discovered during intelligence phase",
                type="reference",
                filename=_make_filename(phase, "research_insights"),
                content=content,
            )
        )

    return entries


def _extract_drafting_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """drafting 阶段: 提取项目记忆（架构决策、关键约束）"""
    entries: list[MemoryEntry] = []
    documents = context.get("documents", {})
    metadata = context.get("metadata", {})

    # Architecture decisions
    decisions = (
        documents.get("architecture_decisions")
        or metadata.get("decisions")
        or documents.get("decisions")
    )
    if decisions:
        if isinstance(decisions, list):
            content = "\n".join(f"- {_safe_str(d, 500)}" for d in decisions[:20])
        elif isinstance(decisions, dict):
            content = "\n".join(f"- **{k}**: {_safe_str(v, 400)}" for k, v in decisions.items())
        else:
            content = _safe_str(decisions, 3000)
        entries.append(
            MemoryEntry(
                name="Architecture Decisions",
                description="Key architecture decisions from drafting phase",
                type="project",
                filename=_make_filename(phase, "architecture_decisions"),
                content=content,
            )
        )

    # Key constraints
    constraints = metadata.get("constraints") or documents.get("constraints")
    if constraints:
        if isinstance(constraints, list):
            content = "\n".join(f"- {_safe_str(c, 300)}" for c in constraints[:20])
        else:
            content = _safe_str(constraints, 2000)
        entries.append(
            MemoryEntry(
                name="Key Constraints",
                description="Project constraints identified during drafting",
                type="project",
                filename=_make_filename(phase, "key_constraints"),
                content=content,
            )
        )

    return entries


def _extract_redteam_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """redteam 阶段: 提取项目记忆（安全发现、性能关注点）"""
    entries: list[MemoryEntry] = []
    quality_reports = context.get("quality_reports", {})
    results = context.get("results", {})

    findings: list[str] = []
    for _name, report in quality_reports.items():
        if isinstance(report, dict):
            for issue in report.get("issues", report.get("findings", [])):
                if isinstance(issue, dict):
                    severity = issue.get("severity", "")
                    msg = issue.get("message", issue.get("finding", ""))
                    prefix = f"[{severity}] " if severity else ""
                    findings.append(f"- {prefix}{_safe_str(msg, 400)}")
                elif isinstance(issue, str):
                    findings.append(f"- {issue[:400]}")
        elif isinstance(report, list):
            for item in report:
                findings.append(f"- {_safe_str(item, 400)}")

    # Also pull from results
    for key in ("security_findings", "performance_concerns", "vulnerabilities"):
        items = results.get(key, [])
        if isinstance(items, list):
            for item in items:
                findings.append(f"- [{key}] {_safe_str(item, 400)}")

    if findings:
        entries.append(
            MemoryEntry(
                name="Security & Performance Findings",
                description="Red-team findings on security and performance",
                type="project",
                filename=_make_filename(phase, "redteam_findings"),
                content="\n".join(findings[:30]),
            )
        )

    return entries


def _extract_qa_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """qa 阶段: 提取反馈记忆（质量问题、常见模式）"""
    entries: list[MemoryEntry] = []
    quality_reports = context.get("quality_reports", {})
    results = context.get("results", {})

    # Quality score and issues
    score = results.get("quality_score", results.get("score"))
    issues: list[str] = []
    for _name, report in quality_reports.items():
        if isinstance(report, dict):
            for issue in report.get("issues", []):
                if isinstance(issue, dict):
                    issues.append(_safe_str(issue.get("message", str(issue)), 400))
                elif isinstance(issue, str):
                    issues.append(issue[:400])

    if score is not None or issues:
        content_parts = []
        if score is not None:
            content_parts.append(f"**Quality Score:** {score}")
        if issues:
            content_parts.append("**Issues:**")
            content_parts.extend(f"- {i}" for i in issues[:20])
        entries.append(
            MemoryEntry(
                name="QA Quality Report",
                description="Quality gate results and issues from QA phase",
                type="feedback",
                filename=_make_filename(phase, "quality_report"),
                content="\n".join(content_parts),
            )
        )

    # Common patterns
    patterns = results.get("patterns", results.get("common_patterns"))
    if patterns:
        if isinstance(patterns, list):
            content = "\n".join(f"- {_safe_str(p, 300)}" for p in patterns[:15])
        else:
            content = _safe_str(patterns, 2000)
        entries.append(
            MemoryEntry(
                name="Common Quality Patterns",
                description="Recurring patterns identified during QA",
                type="feedback",
                filename=_make_filename(phase, "quality_patterns"),
                content=content,
            )
        )

    return entries


def _extract_delivery_memories(phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
    """delivery 阶段: 提取项目记忆（部署配置、发布状态）"""
    entries: list[MemoryEntry] = []
    metadata = context.get("metadata", {})
    results = context.get("results", {})

    # Deployment config
    deploy_config = metadata.get("deployment") or results.get("deployment_config")
    if deploy_config:
        if isinstance(deploy_config, dict):
            content = "\n".join(f"- **{k}**: {_safe_str(v, 300)}" for k, v in deploy_config.items())
        else:
            content = _safe_str(deploy_config, 2000)
        entries.append(
            MemoryEntry(
                name="Deployment Configuration",
                description="Deployment settings from delivery phase",
                type="project",
                filename=_make_filename(phase, "deployment_config"),
                content=content,
            )
        )

    # Release state
    release = results.get("release") or results.get("release_state")
    if release:
        if isinstance(release, dict):
            content = "\n".join(f"- **{k}**: {_safe_str(v, 300)}" for k, v in release.items())
        else:
            content = _safe_str(release, 2000)
        entries.append(
            MemoryEntry(
                name="Release State",
                description="Release status captured at delivery",
                type="project",
                filename=_make_filename(phase, "release_state"),
                content=content,
            )
        )

    return entries


# ---------------------------------------------------------------------------
# Phase → extractor mapping
# ---------------------------------------------------------------------------

_PHASE_EXTRACTORS: dict[
    str,
    list[tuple[str, str, ExtractorFn]],
] = {
    "discovery": [("project", "project", _extract_discovery_memories)],
    "intelligence": [("reference", "reference", _extract_intelligence_memories)],
    "drafting": [("project", "project", _extract_drafting_memories)],
    "redteam": [("project", "project", _extract_redteam_memories)],
    "qa": [("feedback", "feedback", _extract_qa_memories)],
    "delivery": [("project", "project", _extract_delivery_memories)],
}


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------


class MemoryExtractor:
    """自动记忆提取器 — 从 pipeline 阶段执行结果中提取 4 种记忆。"""

    def __init__(self, store: MemoryStore):
        self.store = store

    def should_extract(self, phase: str, context: dict[str, Any]) -> bool:
        """判断是否应该从该阶段提取记忆。

        只有当阶段有对应提取器且上下文非空时才提取。
        """
        if phase not in _PHASE_EXTRACTORS:
            return False
        # At least one meaningful context field should be non-empty
        for key in (
            "user_input",
            "research_data",
            "documents",
            "quality_reports",
            "results",
            "metadata",
        ):
            value = context.get(key)
            if value and isinstance(value, dict) and len(value) > 0:
                return True
        return False

    def extract_from_phase(self, phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
        """从阶段执行上下文中提取记忆并保存。

        Returns the list of extracted entries (already persisted).
        """
        if not self.should_extract(phase, context):
            return []

        all_entries: list[MemoryEntry] = []
        extractors = _PHASE_EXTRACTORS.get(phase, [])

        for label, _mtype, extractor_fn in extractors:
            try:
                entries = extractor_fn(phase, context)
            except Exception as exc:
                _logger.warning(
                    "Memory extraction failed for phase '%s' (%s): %s",
                    phase,
                    label,
                    exc,
                )
                continue

            for entry in entries:
                # Check for duplicate — update if exists
                existing = self.store.find_duplicate(entry.name, entry.type)
                if existing:
                    entry.filename = existing.filename
                    entry.created_at = existing.created_at
                    entry.updated_at = datetime.now(timezone.utc).isoformat()
                    _logger.debug("Updating existing memory '%s' (%s)", entry.name, entry.type)

                self.store.save(entry)
                all_entries.append(entry)

        _logger.info("Extracted %d memories from phase '%s'", len(all_entries), phase)
        return all_entries

    def _extract_project_memories(self, phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
        """Convenience wrapper — delegates to phase-specific extractors."""
        entries: list[MemoryEntry] = []
        for label, _mtype, fn in _PHASE_EXTRACTORS.get(phase, []):
            if label == "project":
                entries.extend(fn(phase, context))
        return entries

    def _extract_reference_memories(self, phase: str, context: dict[str, Any]) -> list[MemoryEntry]:
        """Convenience wrapper — delegates to phase-specific extractors."""
        entries: list[MemoryEntry] = []
        for label, _mtype, fn in _PHASE_EXTRACTORS.get(phase, []):
            if label == "reference":
                entries.extend(fn(phase, context))
        return entries
ExtractorFn = Callable[[str, dict[str, Any]], list[MemoryEntry]]
