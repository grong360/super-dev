"""
Session Auto-Brief — automatic SESSION_BRIEF.md generation after each phase.

Generates/updates the session brief with: completed phases, current phase,
next step, discovered risks, and pending decisions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("super_dev.session_auto_brief")

_PHASE_LABELS: dict[str, str] = {
    "research": "Research complete",
    "core_docs": "Core documents generated",
    "confirmation_gate": "Waiting for docs confirmation",
    "spec": "Spec and tasks created",
    "frontend": "Frontend implementation",
    "preview_gate": "Waiting for preview confirmation",
    "backend": "Backend implementation",
    "quality": "Quality gate check",
    "delivery": "Delivery and release",
}


@dataclass
class PhaseStatus:
    """Status of a single phase."""

    phase: str
    label: str
    completed: bool = False
    timestamp: str = ""


@dataclass
class AutoBriefResult:
    """Result of auto-brief generation."""

    brief_path: str = ""
    phases_total: int = 0
    phases_completed: int = 0
    current_phase: str = ""
    next_step: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _detect_current_phase(super_dev_dir: Path) -> str:
    """Detect current phase from workflow state."""
    state_path = super_dev_dir / "workflow-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            return str(state.get("status", state.get("current_step_label", "")))
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def _detect_completed_phases(super_dev_dir: Path) -> list[PhaseStatus]:
    """Detect completed phases from artifacts and events."""
    phases: list[PhaseStatus] = []

    for phase_key, phase_label in _PHASE_LABELS.items():
        ps = PhaseStatus(phase=phase_key, label=phase_label)
        phases.append(ps)

    # Check artifacts to determine completed phases
    # This is a heuristic based on output file existence
    output_dir = super_dev_dir.parent / "output"
    if output_dir.exists():
        if list(output_dir.glob("*-research.md")):
            _mark_completed(phases, "research")
        if list(output_dir.glob("*-prd.md")) and list(output_dir.glob("*-architecture.md")):
            _mark_completed(phases, "core_docs")
        if (super_dev_dir / "changes").exists():
            changes = list((super_dev_dir / "changes").iterdir())
            if any(c.is_dir() and not c.name.startswith(".") for c in changes):
                _mark_completed(phases, "spec")

    # Check workflow events for phase completions
    events_path = super_dev_dir / "workflow-events.jsonl"
    if events_path.exists():
        try:
            for line in events_path.read_text(encoding="utf-8").split("\n"):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    detail = event.get("detail", event.get("message", ""))
                    if "phase" in event_type.lower() and "complete" in str(detail).lower():
                        # Try to match phase name
                        for phase_key in _PHASE_LABELS:
                            if phase_key in str(detail).lower():
                                _mark_completed(phases, phase_key)
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    return phases


def _mark_completed(phases: list[PhaseStatus], phase_key: str) -> None:
    """Mark a phase as completed."""
    for ps in phases:
        if ps.phase == phase_key:
            ps.completed = True
            ps.timestamp = datetime.now(timezone.utc).isoformat()


def _detect_risks(super_dev_dir: Path) -> list[str]:
    """Detect risks from workflow events and review state."""
    risks: list[str] = []

    # Check for quality gate failures
    events_path = super_dev_dir / "workflow-events.jsonl"
    if events_path.exists():
        try:
            lines = events_path.read_text(encoding="utf-8").split("\n")
            for line in lines[-50:]:  # Last 50 events
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    detail = str(event.get("detail", event.get("message", "")))
                    if any(kw in detail.lower() for kw in ["fail", "error", "reject", "block"]):
                        risks.append(detail[:200])
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    return risks[-5:]  # Cap at 5 risks


def generate_auto_brief(project_dir: Path) -> AutoBriefResult:
    """Generate/update automatic session brief.

    Args:
        project_dir: Root of the project.

    Returns:
        AutoBriefResult with brief metadata.
    """
    super_dev_dir = project_dir / ".super-dev"
    result = AutoBriefResult()

    # Detect state
    current_phase = _detect_current_phase(super_dev_dir)
    phases = _detect_completed_phases(super_dev_dir)
    risks = _detect_risks(super_dev_dir)

    completed_count = sum(1 for p in phases if p.completed)
    result.phases_total = len(phases)
    result.phases_completed = completed_count
    result.current_phase = current_phase

    # Find next step
    next_phase = ""
    for p in phases:
        if not p.completed:
            next_phase = p.phase
            break
    result.next_step = next_phase or "All phases completed"

    # Find next phase label
    next_label = _PHASE_LABELS.get(next_phase, "Unknown")

    # Build brief content
    brief_lines = [
        "# Super Dev Session Brief (Auto-Generated)",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Current Phase**: {current_phase or '(not started)'}",
        f"- **Progress**: {completed_count}/{len(phases)} phases completed",
        f"- **Next Step**: {next_label}",
        "",
        "## Phase Progress",
        "",
        "| Phase | Status |",
        "|:---|:---:|",
    ]
    for p in phases:
        status = "DONE" if p.completed else ("CURRENT" if p.phase == next_phase else "PENDING")
        brief_lines.append(f"| {p.label} | {status} |")

    if risks:
        brief_lines.extend(["", "## Active Risks", ""])
        for risk in risks:
            brief_lines.append(f"- {risk}")

    brief_lines.extend(["", "---", "", "<!-- This brief is auto-generated by Super Dev -->"])

    brief_content = "\n".join(brief_lines)

    # Write brief
    brief_path = super_dev_dir / "SESSION_BRIEF.md"
    super_dev_dir.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_content, encoding="utf-8")

    result.brief_path = str(brief_path)
    return result
