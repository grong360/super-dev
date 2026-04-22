from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .impact import ImpactAnalysisReport, ImpactAnalyzer


@dataclass
class RegressionCheck:
    title: str
    scope: str
    reason: str
    severity: str
    suggested_validation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "scope": self.scope,
            "reason": self.reason,
            "severity": self.severity,
            "suggested_validation": self.suggested_validation,
        }


@dataclass
class RegressionGuardReport:
    project_name: str
    project_path: str
    description: str
    files: list[str]
    risk_level: str
    summary: str
    high_priority_checks: list[RegressionCheck] = field(default_factory=list)
    medium_priority_checks: list[RegressionCheck] = field(default_factory=list)
    supporting_checks: list[RegressionCheck] = field(default_factory=list)
    recommended_commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "description": self.description,
            "files": list(self.files),
            "risk_level": self.risk_level,
            "summary": self.summary,
            "high_priority_checks": [item.to_dict() for item in self.high_priority_checks],
            "medium_priority_checks": [item.to_dict() for item in self.medium_priority_checks],
            "supporting_checks": [item.to_dict() for item in self.supporting_checks],
            "recommended_commands": list(self.recommended_commands),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Regression Guard",
            "",
            f"- Project: `{self.project_name}`",
            f"- Path: `{self.project_path}`",
            f"- Risk Level: `{self.risk_level}`",
        ]
        if self.description:
            lines.append(f"- Change: {self.description}")
        if self.files:
            lines.append(f"- Files: {', '.join(f'`{item}`' for item in self.files)}")
        lines.extend(["", self.summary, ""])
        self._append_checks(lines, "High Priority Checks", self.high_priority_checks)
        self._append_checks(lines, "Medium Priority Checks", self.medium_priority_checks)
        self._append_checks(lines, "Supporting Checks", self.supporting_checks)
        lines.extend(["", "## Recommended Commands", ""])
        for item in self.recommended_commands:
            lines.append(f"- `{item}`")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _append_checks(lines: list[str], title: str, items: list[RegressionCheck]) -> None:
        lines.extend(["", f"## {title}", ""])
        if not items:
            lines.append("- None")
            return
        for item in items:
            lines.append(f"- **{item.title}**")
            lines.append(f"  - Scope: {item.scope}")
            lines.append(f"  - Reason: {item.reason}")
            lines.append(f"  - Severity: `{item.severity}`")
            lines.append(f"  - Validation: {item.suggested_validation}")


class RegressionGuardBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = self.project_dir.name
        self.impact_analyzer = ImpactAnalyzer(self.project_dir)

    def build(self, description: str = "", files: list[str] | None = None) -> RegressionGuardReport:
        impact = self.impact_analyzer.build(description=description, files=files or [])
        high, medium, supporting = self._build_checks(impact)
        commands = self._recommended_commands(impact)
        summary = (
            f"Regression Guard converts the current `{impact.risk_level}`-risk change into an executable "
            f"verification checklist. Focus on the high-priority checks first, then complete the medium "
            "and supporting checks before marking the change complete."
        )
        return RegressionGuardReport(
            project_name=self.project_name,
            project_path=str(self.project_dir),
            description=description,
            files=list(files or []),
            risk_level=impact.risk_level,
            summary=summary,
            high_priority_checks=high,
            medium_priority_checks=medium,
            supporting_checks=supporting,
            recommended_commands=commands,
        )

    def write(self, report: RegressionGuardReport) -> dict[str, Path]:
        md_path = self.output_dir / f"{self.project_name}-regression-guard.md"
        json_path = self.output_dir / f"{self.project_name}-regression-guard.json"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _build_checks(
        self,
        impact: ImpactAnalysisReport,
    ) -> tuple[list[RegressionCheck], list[RegressionCheck], list[RegressionCheck]]:
        high: list[RegressionCheck] = []
        medium: list[RegressionCheck] = []
        supporting: list[RegressionCheck] = []

        for item in impact.regression_focus:
            lower = item.lower()
            if "authentication" in lower or "permission" in lower or "session" in lower:
                high.append(
                    RegressionCheck(
                        title="认证与权限主路径",
                        scope="登录、登出、权限校验、会话保持",
                        reason=item,
                        severity="high",
                        suggested_validation="覆盖成功登录、失败登录、权限拒绝、刷新后会话保持。",
                    )
                )
            elif "api contract" in lower or "route" in lower:
                high.append(
                    RegressionCheck(
                        title="接口契约与路由回归",
                        scope="状态码、字段结构、关键路由",
                        reason=item,
                        severity="high",
                        suggested_validation="核对接口字段、状态码、异常分支与关键路由是否保持兼容。",
                    )
                )
            elif "ui" in lower or "navigation" in lower or "state transition" in lower:
                medium.append(
                    RegressionCheck(
                        title="关键 UI 路径与导航",
                        scope="主页面、主按钮、状态切换、导航跳转",
                        reason=item,
                        severity="medium",
                        suggested_validation="走一遍主界面、关键 CTA 和状态切换，确认没有视觉或交互回退。",
                    )
                )
            elif "data model" in lower or "persistence" in lower or "migration" in lower:
                high.append(
                    RegressionCheck(
                        title="数据模型与持久层",
                        scope="写入、读取、迁移、兼容性",
                        reason=item,
                        severity="high",
                        suggested_validation="验证读写兼容性、历史数据兼容性以及迁移/回滚安全性。",
                    )
                )
            else:
                supporting.append(
                    RegressionCheck(
                        title="主路径烟雾验证",
                        scope="受影响模块主路径",
                        reason=item,
                        severity="supporting",
                        suggested_validation="至少走通一遍受影响主路径，确认没有新增阻塞错误。",
                    )
                )

        top_modules = [item.path for item in impact.affected_modules[:3]]
        if top_modules:
            medium.append(
                RegressionCheck(
                    title="邻近模块连带影响",
                    scope=", ".join(top_modules),
                    reason="高置信度受影响模块需要额外检查相邻调用路径。",
                    severity="medium",
                    suggested_validation="对相邻模块做最小回归检查，确认没有隐藏耦合回退。",
                )
            )
        if impact.files:
            supporting.append(
                RegressionCheck(
                    title="直接改动文件自检",
                    scope=", ".join(impact.files[:5]),
                    reason="显式改动文件必须先完成最小自检，再扩大范围。",
                    severity="supporting",
                    suggested_validation="逐个确认改动文件的输入、输出和异常分支没有被破坏。",
                )
            )

        return high[:6], medium[:6], supporting[:6]

    @staticmethod
    def _recommended_commands(impact: ImpactAnalysisReport) -> list[str]:
        commands = ["super-dev product-audit"]
        if impact.risk_level in {"medium", "high"}:
            commands.append("super-dev quality --type all")
        commands.append("查看最新 proof-pack / release readiness 报告，确认交付证据是否仍然成立")
        return commands
