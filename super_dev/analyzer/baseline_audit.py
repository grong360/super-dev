from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..artifact_utils import resolve_project_artifact_prefix
from ..review_state import load_workflow_state
from ..work_mode import detect_work_mode, work_mode_label
from .detectors import detect_project_type, detect_tech_stack

_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".next",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _top_level_directories(project_dir: Path, *, limit: int = 12) -> list[str]:
    values: list[str] = []
    for path in sorted(project_dir.iterdir(), key=lambda item: item.name):
        if not path.is_dir():
            continue
        if path.name in _IGNORED_DIRS:
            continue
        values.append(path.name)
        if len(values) >= limit:
            break
    return values


def _top_level_files(project_dir: Path, *, limit: int = 12) -> list[str]:
    values: list[str] = []
    for path in sorted(project_dir.iterdir(), key=lambda item: item.name):
        if not path.is_file():
            continue
        values.append(path.name)
        if len(values) >= limit:
            break
    return values


def _existing_paths(project_dir: Path, candidates: list[str]) -> list[str]:
    return [candidate for candidate in candidates if (project_dir / candidate).exists()]


def _infer_frontend_surfaces(project_dir: Path) -> list[str]:
    candidates = [
        "app",
        "pages",
        "src",
        "components",
        "frontend",
        "super-dev-website",
        "super_dev/web/frontend",
    ]
    return _existing_paths(project_dir, candidates)


def _infer_backend_surfaces(project_dir: Path) -> list[str]:
    candidates = [
        "backend",
        "api",
        "server",
        "super_dev/web",
        "routes",
        "supabase",
        "functions",
    ]
    return _existing_paths(project_dir, candidates)


def _infer_data_surfaces(project_dir: Path) -> list[str]:
    candidates = ["db", "database", "migrations", "prisma", "schema", "models"]
    return _existing_paths(project_dir, candidates)


def _infer_ui_surfaces(project_dir: Path) -> dict[str, Any]:
    return {
        "component_directories": _existing_paths(
            project_dir,
            ["components", "src/components", "app/components", "super_dev/web/frontend"],
        ),
        "route_surfaces": _existing_paths(
            project_dir,
            ["app", "pages", "src/app", "src/pages", "pages.json"],
        ),
        "token_surfaces": _existing_paths(
            project_dir,
            [
                "tokens",
                "design",
                "styles",
                "tailwind.config.js",
                "tailwind.config.ts",
                "theme.json",
            ],
        ),
    }


def _collect_constraints(project_dir: Path, workflow_payload: dict[str, Any]) -> list[str]:
    constraints: list[str] = []
    if (project_dir / ".super-dev" / "SESSION_BRIEF.md").exists():
        constraints.append("仓库存在活动 Super Dev workflow，上下文需要继续而不是重新开题。")
    workflow_status = str(workflow_payload.get("status", "")).strip()
    if workflow_status:
        constraints.append(f"当前 workflow status={workflow_status}，差量方案必须与现有流程状态保持一致。")
    if (project_dir / "package.json").exists():
        constraints.append("前端/Node 侧依赖与脚本必须兼容现有 package.json。")
    if (project_dir / "pyproject.toml").exists():
        constraints.append("Python 侧实现必须兼容现有 pyproject.toml 与现有 CLI/包结构。")
    if (project_dir / "output").exists():
        constraints.append("已有 output 工件属于当前项目真源，差量文档和实现不能脱离现有产物。")
    return constraints[:8]


def _infer_delta_scope(project_dir: Path) -> dict[str, list[str]]:
    affected = []
    frontend_surfaces = _infer_frontend_surfaces(project_dir)
    backend_surfaces = _infer_backend_surfaces(project_dir)
    data_surfaces = _infer_data_surfaces(project_dir)
    for item in (
        frontend_surfaces
        + backend_surfaces
        + data_surfaces
    ):
        if item not in affected:
            affected.append(item)
    reuse_surfaces = []
    for item in frontend_surfaces[:3] + backend_surfaces[:3]:
        if item not in reuse_surfaces:
            reuse_surfaces.append(item)
    risks = [
        "差量需求如果不先锁定现有边界，容易破坏已有路由、组件契约或数据结构。",
        "已有项目模式必须先确认复用面和禁止改动面，再进入 docs/spec/implementation。",
    ]
    return {
        "goals": [],
        "affected_modules": affected[:12],
        "reuse_surfaces": reuse_surfaces[:8],
        "out_of_scope": ["暂不重写整个现有项目，仅围绕本次差量范围推进。"],
        "risks": risks,
    }


@dataclass
class BaselineAuditReport:
    project_name: str
    work_mode: str
    work_mode_label: str
    generated_at: str = field(default_factory=_utc_now)
    current_state: dict[str, Any] = field(default_factory=dict)
    architecture_summary: dict[str, Any] = field(default_factory=dict)
    ui_summary: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    delta_scope: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        current_summary = str(self.current_state.get("summary", "")).strip()
        modules = self.delta_scope.get("affected_modules", [])
        return (
            f"当前项目 baseline 已建立：mode={self.work_mode}，"
            f"{current_summary or '已完成现状扫描'}，建议优先关注 {', '.join(modules[:4]) or '现有模块边界'}。"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "work_mode": self.work_mode,
            "work_mode_label": self.work_mode_label,
            "current_state": self.current_state,
            "architecture_summary": self.architecture_summary,
            "ui_summary": self.ui_summary,
            "constraints": list(self.constraints),
            "delta_scope": self.delta_scope,
            "summary": self.summary,
        }

    def to_markdown(self) -> str:
        current = self.current_state
        architecture = self.architecture_summary
        ui = self.ui_summary
        delta = self.delta_scope
        lines = [
            "# Baseline Audit",
            "",
            f"- Project: `{self.project_name}`",
            f"- Work Mode: `{self.work_mode}` ({self.work_mode_label})",
            f"- Generated at (UTC): {self.generated_at}",
            "",
            "## Summary",
            "",
            f"- {self.summary}",
            "",
            "## Current State",
            "",
            f"- Project Category: {current.get('project_category', '-')}",
            f"- Summary: {current.get('summary', '-')}",
            f"- Top-Level Directories: {', '.join(current.get('top_level_directories', [])) or '-'}",
            f"- Top-Level Files: {', '.join(current.get('top_level_files', [])) or '-'}",
            f"- Business Capabilities: {', '.join(current.get('business_capabilities', [])) or '-'}",
            f"- Entry Points: {', '.join(current.get('entry_points', [])) or '-'}",
            f"- Key Modules: {', '.join(current.get('key_modules', [])) or '-'}",
            f"- Data Surfaces: {', '.join(current.get('data_surfaces', [])) or '-'}",
            f"- Workflow Status: {current.get('workflow_status', '-')}",
            "",
            "## Architecture Summary",
            "",
            f"- Style: {architecture.get('style', '-')}",
            f"- Language: {architecture.get('language', '-')}",
            f"- Framework: {architecture.get('framework', '-')}",
            f"- Frontend Surfaces: {', '.join(architecture.get('frontend_surfaces', [])) or '-'}",
            f"- Backend Surfaces: {', '.join(architecture.get('backend_surfaces', [])) or '-'}",
            f"- Data Surfaces: {', '.join(architecture.get('data_surfaces', [])) or '-'}",
            f"- Affected Modules: {', '.join(architecture.get('affected_modules', [])) or '-'}",
            f"- Integration Points: {', '.join(architecture.get('integration_points', [])) or '-'}",
            "",
            "## UI Summary",
            "",
            f"- Surface Type: {ui.get('surface_type', '-')}",
            f"- Design System: {ui.get('design_system', '-')}",
            f"- Component Surfaces: {', '.join(ui.get('component_directories', [])) or '-'}",
            f"- Route Surfaces: {', '.join(ui.get('route_surfaces', [])) or '-'}",
            f"- Token Surfaces: {', '.join(ui.get('token_surfaces', [])) or '-'}",
            f"- Key Surfaces: {', '.join(ui.get('key_surfaces', [])) or '-'}",
            "",
            "## Constraints",
            "",
        ]
        if self.constraints:
            for item in self.constraints:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前未提取到额外硬约束。")
        lines.extend(
            [
                "",
                "## Delta Scope Draft",
                "",
                f"- Goals: {', '.join(delta.get('goals', [])) or '-'}",
                f"- Affected Modules: {', '.join(delta.get('affected_modules', [])) or '-'}",
                f"- Reuse Surfaces: {', '.join(delta.get('reuse_surfaces', [])) or '-'}",
                f"- Out of Scope: {', '.join(delta.get('out_of_scope', [])) or '-'}",
                "",
                "### Risks",
                "",
            ]
        )
        risks = delta.get("risks", [])
        if isinstance(risks, list) and risks:
            for item in risks:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前未记录风险。")
        return "\n".join(lines) + "\n"


class BaselineAuditBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = resolve_project_artifact_prefix(
            self.project_dir,
            fallback_name=self.project_dir.name,
        )

    def build(self, *, work_mode_override: str | None = None) -> BaselineAuditReport:
        workflow_payload = load_workflow_state(self.project_dir) or {}
        work_mode = work_mode_override or detect_work_mode(self.project_dir, workflow_payload)
        tech_stack = detect_tech_stack(self.project_dir).to_dict()
        frontend_surfaces = _infer_frontend_surfaces(self.project_dir)
        backend_surfaces = _infer_backend_surfaces(self.project_dir)
        data_surfaces = _infer_data_surfaces(self.project_dir)
        ui_surfaces = _infer_ui_surfaces(self.project_dir)
        business_capabilities = []
        for item in frontend_surfaces[:2] + backend_surfaces[:2]:
            if item not in business_capabilities:
                business_capabilities.append(item)
        entry_points = []
        for item in ui_surfaces.get("route_surfaces", [])[:3] + backend_surfaces[:2]:
            if item not in entry_points:
                entry_points.append(item)
        key_modules = []
        for item in frontend_surfaces[:3] + backend_surfaces[:3]:
            if item not in key_modules:
                key_modules.append(item)
        current_summary = (
            f"当前仓库以 {tech_stack.get('framework', '-') or tech_stack.get('category', 'project')} 为主，"
            f"已存在 {', '.join(key_modules[:4]) or '关键模块'} 等核心实现面。"
        )
        current_state = {
            "project_category": detect_project_type(self.project_dir).value,
            "summary": current_summary,
            "top_level_directories": _top_level_directories(self.project_dir),
            "top_level_files": _top_level_files(self.project_dir),
            "business_capabilities": business_capabilities,
            "entry_points": entry_points,
            "key_modules": key_modules,
            "data_surfaces": data_surfaces,
            "workflow_status": str(workflow_payload.get("status", "")).strip() or "unknown",
            "workflow_mode": str(workflow_payload.get("workflow_mode", "")).strip() or "start",
        }
        architecture_summary = {
            "style": tech_stack.get("category", ""),
            "language": tech_stack.get("language", ""),
            "framework": tech_stack.get("framework", ""),
            "ui_library": tech_stack.get("ui_library", ""),
            "frontend_surfaces": frontend_surfaces,
            "backend_surfaces": backend_surfaces,
            "data_surfaces": data_surfaces,
            "affected_modules": key_modules,
            "integration_points": entry_points,
        }
        ui_surfaces["surface_type"] = tech_stack.get("category", "")
        ui_surfaces["design_system"] = (
            tech_stack.get("ui_library", "")
            or ", ".join(ui_surfaces.get("token_surfaces", [])[:2])
            or "unknown"
        )
        ui_surfaces["key_surfaces"] = ui_surfaces.get("route_surfaces", [])[:4]
        return BaselineAuditReport(
            project_name=self.project_name,
            work_mode=work_mode,
            work_mode_label=work_mode_label(work_mode),
            current_state=current_state,
            architecture_summary=architecture_summary,
            ui_summary=ui_surfaces,
            constraints=_collect_constraints(self.project_dir, workflow_payload),
            delta_scope=_infer_delta_scope(self.project_dir),
        )

    def write(self, report: BaselineAuditReport) -> dict[str, Path]:
        markdown_path = self.output_dir / f"{self.project_name}-baseline-audit.md"
        json_path = self.output_dir / f"{self.project_name}-baseline-audit.json"
        markdown_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"markdown": markdown_path, "json": json_path}
