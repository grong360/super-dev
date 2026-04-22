"""
开发：Excellent（11964948@qq.com）
功能：工作流恢复链专项验证与交付证据
作用：汇总 workflow state、history snapshots 与 event log，生成独立 continuity harness 报告
创建时间：2026-04-05
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review_state import (
    describe_workflow_event,
    latest_workflow_snapshot_file,
    load_recent_operational_timeline,
    load_recent_workflow_events,
    load_recent_workflow_snapshots,
    load_workflow_state,
    workflow_event_log_file,
    workflow_state_file,
)


@dataclass
class WorkflowHarnessReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = False
    workflow_status: str = ""
    workflow_mode: str = ""
    current_step_label: str = ""
    updated_at: str = ""
    checks: dict[str, bool] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    recent_snapshots: list[dict[str, Any]] = field(default_factory=list)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    recent_timeline: list[dict[str, Any]] = field(default_factory=list)
    source_files: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return (
            self.enabled and not self.blockers and all(self.checks.values())
            if self.checks
            else self.enabled and not self.blockers
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "enabled": self.enabled,
            "passed": self.passed,
            "workflow_status": self.workflow_status,
            "workflow_mode": self.workflow_mode,
            "current_step_label": self.current_step_label,
            "updated_at": self.updated_at,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
            "recent_snapshots": list(self.recent_snapshots),
            "recent_events": list(self.recent_events),
            "recent_timeline": list(self.recent_timeline),
            "source_files": dict(self.source_files),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Workflow Harness",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Enabled: {'yes' if self.enabled else 'no'}",
            f"- Passed: {'yes' if self.passed else 'no'}",
        ]
        if not self.enabled:
            lines.extend(["", "当前项目未检测到活动 workflow continuity trail。", ""])
            return "\n".join(lines)

        lines.extend(
            [
                f"- Status: `{self.workflow_status or '-'}`",
                f"- Mode: `{self.workflow_mode or '-'}`",
                f"- Current Step: `{self.current_step_label or '-'}`",
                f"- Updated at: {self.updated_at or '-'}",
                "",
                "## Checks",
                "",
            ]
        )
        for name, passed in self.checks.items():
            lines.append(f"- {name}: {'pass' if passed else 'fail'}")
        lines.extend(["", "## Recent Snapshots", ""])
        if self.recent_snapshots:
            for item in self.recent_snapshots[:3]:
                lines.append(
                    f"- {item.get('updated_at') or '-'} · {item.get('current_step_label') or item.get('status') or '-'}"
                )
        else:
            lines.append("- 当前没有 workflow snapshots。")
        lines.extend(["", "## Recent Events", ""])
        if self.recent_events:
            for item in self.recent_events[:5]:
                lines.append(f"- {item.get('timestamp') or '-'} · {describe_workflow_event(item)}")
        else:
            lines.append("- 当前没有 workflow events。")
        lines.extend(["", "## Recent Timeline", ""])
        if self.recent_timeline:
            for item in self.recent_timeline[:8]:
                title = str(item.get("title", "")).strip() or str(item.get("kind", "")).strip()
                message = str(item.get("message", "")).strip() or "-"
                lines.append(f"- {item.get('timestamp') or '-'} · {title} · {message}")
        else:
            lines.append("- 当前没有统一运行时时间线。")
        lines.extend(["", "## Blockers", ""])
        if self.blockers:
            for blocker in self.blockers:
                lines.append(f"- {blocker}")
        else:
            lines.append("- 当前没有 workflow continuity 阻塞项。")
        lines.extend(["", "## Next Actions", ""])
        if self.next_actions:
            for action in self.next_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- 当前 workflow continuity 证据已经齐全。")
        return "\n".join(lines).rstrip() + "\n"


class WorkflowHarnessBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.project_name = self.project_dir.name

    def build(self) -> WorkflowHarnessReport:
        report = WorkflowHarnessReport(project_name=self.project_name)
        state_payload = load_workflow_state(self.project_dir)
        recent_snapshots = load_recent_workflow_snapshots(self.project_dir, limit=3)
        recent_events = load_recent_workflow_events(self.project_dir, limit=5)
        recent_timeline = load_recent_operational_timeline(self.project_dir, limit=8)

        if state_payload is None and not recent_snapshots:
            return report

        report.enabled = True
        report.workflow_status = str(
            (state_payload or {}).get("status", "")
            or (state_payload or {}).get("workflow_status", "")
        ).strip()
        report.workflow_mode = str((state_payload or {}).get("workflow_mode", "")).strip()
        report.current_step_label = str((state_payload or {}).get("current_step_label", "")).strip()
        report.updated_at = str((state_payload or {}).get("updated_at", "")).strip()
        report.recent_snapshots = recent_snapshots
        report.recent_events = recent_events
        report.recent_timeline = recent_timeline
        state_path = workflow_state_file(self.project_dir)
        latest_snapshot = latest_workflow_snapshot_file(self.project_dir)
        event_log = workflow_event_log_file(self.project_dir)
        report.source_files = {
            "workflow_state": str(state_path),
            "latest_snapshot": str(latest_snapshot),
            "workflow_event_log": str(event_log),
        }

        report.checks["workflow_state_present"] = state_payload is not None
        report.checks["workflow_snapshots_present"] = bool(recent_snapshots)
        report.checks["workflow_events_present"] = bool(recent_events)
        report.checks["operational_timeline_present"] = bool(recent_timeline)

        if not report.checks["workflow_state_present"]:
            report.blockers.append("workflow-state.json 缺失或无法读取")
        if not report.checks["workflow_snapshots_present"]:
            report.blockers.append("workflow-history 快照缺失")
        if not report.checks["workflow_events_present"]:
            report.blockers.append("workflow-events.jsonl 缺失或没有事件")
        if not report.checks["operational_timeline_present"]:
            report.blockers.append("统一运行时时间线缺失")

        if not report.checks["workflow_state_present"]:
            report.next_actions.append(
                "重新写入 .super-dev/workflow-state.json，确保当前 workflow status、mode、step 已正式落盘。"
            )
        if not report.checks["workflow_snapshots_present"]:
            report.next_actions.append(
                "补齐 .super-dev/workflow-history 快照，确保恢复链能回退到最近有效状态。"
            )
        if not report.checks["workflow_events_present"]:
            report.next_actions.append(
                "补齐 .super-dev/workflow-events.jsonl，确保恢复、返工和次日继续有正式事件轨迹。"
            )
        if not report.checks["operational_timeline_present"]:
            report.next_actions.append(
                "补齐统一运行时时间线，确保流程快照、语义事件和 Hook 事件可被恢复链与发布摘要直接消费。"
            )
        if not report.next_actions:
            report.next_actions.append(
                "当前 workflow continuity harness 已满足恢复与发布前证据要求。"
            )
        return report

    def write(self, report: WorkflowHarnessReport) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = self.output_dir / f"{self.project_name}-workflow-harness"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}
