"""
开发：Excellent（11964948@qq.com）
功能：统一构建 workflow / framework / hook harness payload
作用：为 CLI、Web API、proof-pack 等提供共享的 harness 聚合真源
创建时间：2026-04-06
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .framework_harness import FrameworkHarnessBuilder
from .hook_harness import HookHarnessBuilder
from .workflow_harness import WorkflowHarnessBuilder


class _HarnessBuilder(Protocol):
    def build(self, *args: Any, **kwargs: Any) -> Any: ...

    def write(self, report: Any) -> dict[str, Path]: ...


HARNESS_LABELS: dict[str, str] = {
    "workflow": "Workflow Continuity",
    "framework": "Framework Harness",
    "hooks": "Hook Audit Trail",
}


def build_operational_harness_payload(
    project_dir: Path,
    *,
    hook_limit: int = 20,
    write_reports: bool = True,
) -> dict[str, Any]:
    project_path = Path(project_dir).resolve()
    builders: dict[str, _HarnessBuilder] = {
        "workflow": WorkflowHarnessBuilder(project_path),
        "framework": FrameworkHarnessBuilder(project_path),
        "hooks": HookHarnessBuilder(project_path),
    }
    payload: dict[str, Any] = {
        "project_dir": str(project_path),
        "all_passed": True,
        "harnesses": {},
    }

    for key, builder in builders.items():
        if key == "hooks":
            report = builder.build(limit=max(hook_limit, 1))
        else:
            report = builder.build()
        item = report.to_dict()
        item["kind"] = key
        item["label"] = HARNESS_LABELS.get(key, key)
        if write_reports:
            files = builder.write(report)
            item["report_file"] = str(files["markdown"])
            item["json_file"] = str(files["json"])
        else:
            item["report_file"] = ""
            item["json_file"] = ""
        payload["harnesses"][key] = item
        if item.get("enabled") and not item.get("passed"):
            payload["all_passed"] = False
    return payload


def summarize_operational_harnesses(
    project_dir: Path,
    *,
    hook_limit: int = 20,
    write_reports: bool = False,
) -> list[dict[str, Any]]:
    payload = build_operational_harness_payload(
        project_dir=project_dir,
        hook_limit=hook_limit,
        write_reports=write_reports,
    )
    summaries: list[dict[str, Any]] = []
    harnesses = payload.get("harnesses", {})
    if not isinstance(harnesses, dict):
        return summaries
    for key, item in harnesses.items():
        if not isinstance(item, dict):
            continue
        blockers = item.get("blockers")
        summaries.append(
            {
                "kind": str(item.get("kind", key)),
                "label": str(item.get("label", key)),
                "enabled": bool(item.get("enabled", False)),
                "passed": bool(item.get("passed", False)),
                "blocker_count": len(blockers) if isinstance(blockers, list) else 0,
                "first_blocker": (
                    str(blockers[0]).strip()
                    if isinstance(blockers, list) and blockers and str(blockers[0]).strip()
                    else ""
                ),
                "json_file": str(item.get("json_file", "")).strip(),
                "report_file": str(item.get("report_file", "")).strip(),
            }
        )
    return summaries


def derive_operational_focus(
    project_dir: Path,
    *,
    hook_limit: int = 20,
) -> dict[str, Any]:
    payload = build_operational_harness_payload(
        project_dir=project_dir,
        hook_limit=hook_limit,
        write_reports=False,
    )
    harnesses = payload.get("harnesses", {})
    if not isinstance(harnesses, dict):
        return {
            "status": "idle",
            "kind": "",
            "label": "",
            "reason": "",
            "recommended_action": "",
            "summary": "当前没有运行时 harness 数据。",
        }

    for key in ("workflow", "framework", "hooks"):
        item = harnesses.get(key, {})
        if not isinstance(item, dict) or not item.get("enabled"):
            continue
        if item.get("passed"):
            continue
        blockers = item.get("blockers")
        next_actions = item.get("next_actions")
        blocker = (
            str(blockers[0]).strip()
            if isinstance(blockers, list) and blockers and str(blockers[0]).strip()
            else ""
        )
        next_action = (
            str(next_actions[0]).strip()
            if isinstance(next_actions, list) and next_actions and str(next_actions[0]).strip()
            else ""
        )
        label = str(item.get("label", HARNESS_LABELS.get(key, key))).strip()
        return {
            "status": "needs_attention",
            "kind": key,
            "label": label,
            "reason": blocker,
            "recommended_action": next_action,
            "summary": f"{label} 需要先处理" + (f"：{blocker}" if blocker else "。"),
        }

    enabled_items = [
        item for item in harnesses.values() if isinstance(item, dict) and item.get("enabled")
    ]
    if enabled_items:
        return {
            "status": "passed",
            "kind": "",
            "label": "Operational Harness",
            "reason": "",
            "recommended_action": "当前 workflow / framework / hooks harness 已形成统一运行时证据。",
            "summary": "当前 workflow / framework / hooks harness 已全部通过。",
        }

    return {
        "status": "idle",
        "kind": "",
        "label": "",
        "reason": "",
        "recommended_action": "",
        "summary": "当前没有启用的运行时 harness。",
    }
