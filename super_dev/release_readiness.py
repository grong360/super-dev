"""
开发：Excellent（11964948@qq.com）
功能：发布就绪度评估器
作用：评估版本对齐、文档覆盖、宿主兼容性等发布条件
创建时间：2025-12-30
最后修改：2026-03-20
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .analyzer import FeatureChecklistBuilder
from .artifact_utils import is_artifact_stale, latest_artifact, resolve_project_artifact_prefix
from .baseline_governance import inspect_baseline_governance
from .evidence_identity import build_evidence_identity, evidence_identity_matches, load_json_payload
from .framework_harness import FrameworkHarnessBuilder
from .frameworks import framework_playbook_complete, is_cross_platform_frontend
from .harness_registry import derive_operational_focus
from .hooks.manager import HookManager
from .host_runtime_governance import collect_layered_runtime_governance_gap
from .host_workflow_context import build_host_workflow_context
from .integrations import IntegrationManager
from .operational_harness import OperationalHarnessBuilder
from .review_state import (
    load_host_runtime_validation,
    load_recent_operational_timeline,
    load_recent_workflow_events,
    load_recent_workflow_snapshots,
    load_workflow_state,
)
from .reviewers.redteam import load_redteam_evidence
from .skills import SkillManager
from .specs import SpecValidator
from .ui_contract_governance import missing_claude_design_runtime_checks
from .workflow_state import detect_pipeline_summary


@dataclass
class ReleaseReadinessCheck:
    name: str
    passed: bool
    detail: str
    severity: str = "medium"
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
            "recommendation": self.recommendation,
        }


@dataclass
class ReleaseReadinessReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    threshold: int = 85
    checks: list[ReleaseReadinessCheck] = field(default_factory=list)
    recent_timeline: list[dict[str, Any]] = field(default_factory=list)
    operational_focus: dict[str, Any] = field(default_factory=dict)
    evidence_identity: dict[str, Any] = field(default_factory=dict)
    workflow_context: dict[str, Any] = field(default_factory=dict)
    baseline_governance: dict[str, Any] = field(default_factory=dict)

    def _weight(self, severity: str) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(severity, 2)

    @property
    def score(self) -> int:
        if not self.checks:
            return 0
        total_weight = sum(self._weight(check.severity) for check in self.checks)
        passed_weight = sum(self._weight(check.severity) for check in self.checks if check.passed)
        return int((passed_weight / total_weight) * 100) if total_weight else 0

    @property
    def failed_checks(self) -> list[ReleaseReadinessCheck]:
        return [check for check in self.checks if not check.passed]

    @property
    def passed(self) -> bool:
        has_critical_failure = any(
            not check.passed and check.severity == "critical" for check in self.checks
        )
        return self.score >= self.threshold and not has_critical_failure

    @property
    def executive_summary(self) -> str:
        host_runtime_check = next(
            (check for check in self.checks if check.name == "Host Runtime Validation"),
            None,
        )
        layered_runtime_text = ""
        if host_runtime_check and not host_runtime_check.passed:
            detail = str(host_runtime_check.detail).strip()
            if "repo_probe_failed=" in detail:
                failed_segment = detail.split("repo_probe_failed=", 1)[1].split(";", 1)[0].strip()
                if failed_segment:
                    layered_runtime_text = (
                        "宿主运行时验收存在分层差异："
                        + failed_segment
                        + " 已人工通过，但仓库级 repo probe 仍未通过。"
                    )
        baseline_text = self._baseline_signal_summary()
        compliance_text = self._compliance_signal_summary()
        frontend_governance_text = self._frontend_governance_signal_summary()
        framework_text = self._framework_playbook_signal_summary()
        workflow_text = self._workflow_signal_summary()
        focus_summary = str(self.operational_focus.get("summary", "")).strip()
        focus_text = f" 当前治理焦点：{focus_summary}。" if focus_summary else ""
        if self.passed:
            return (
                f"当前仓库已达到发布阈值，score={self.score}/100。"
                " 从发布决策视角看，当前版本已经具备对外演示、验收和上线评审的基础可信度。"
                f"{workflow_text}{layered_runtime_text}{baseline_text}{compliance_text}"
                f"{frontend_governance_text}{framework_text}{focus_text}"
            )
        failed_names = "、".join(check.name for check in self.failed_checks[:3]) or "关键检查"
        return (
            f"当前仓库尚未达到发布阈值，score={self.score}/100。"
            " 从发布决策视角看，现在还不适合直接做最终客户演示、上线签字或对外交付。"
            f"优先修复：{failed_names}。{workflow_text}{layered_runtime_text}{baseline_text}"
            f"{compliance_text}{frontend_governance_text}{framework_text}{focus_text}"
        )

    def _workflow_signal_summary(self) -> str:
        context = self.workflow_context if isinstance(self.workflow_context, dict) else {}
        status = str(context.get("workflow_status", "")).strip()
        gate = str(context.get("blocking_gate", "")).strip()
        next_action = str(context.get("recommended_host_action", "")).strip()
        if not status:
            return ""
        if gate:
            action_text = f" 下一步：{next_action}。" if next_action else ""
            return (
                f" 当前流程状态为 {status}，入口 gate={gate}。"
                " 这说明当前版本还停在正式确认门之前，不能把“已经生成了一些产物”当成“已经可以发布或交付”。"
                + action_text
            )
        return f" 当前流程状态为 {status}，主入口 gate 已闭环。"

    def _baseline_signal_summary(self) -> str:
        baseline_check = next(
            (check for check in self.checks if check.name == "Baseline Confirmation"),
            None,
        )
        if baseline_check is None:
            baseline = self.baseline_governance if isinstance(self.baseline_governance, dict) else {}
            status = str(baseline.get("status", "")).strip()
            entry_gate = str(baseline.get("entry_gate", "")).strip()
            next_action = str(baseline.get("next_host_action", "")).strip()
            if status == "missing_audit":
                return " 当前是已有项目模式，但 baseline audit 还没生成。"
            if entry_gate == "waiting_baseline_confirmation":
                action_text = f" 下一步：{next_action}。" if next_action else ""
                return " 当前是已有项目模式，但 baseline 还没确认。" + action_text
            if entry_gate == "waiting_resume_gate":
                action_text = f" 下一步：{next_action}。" if next_action else ""
                return " 当前先处理 resume gate，再继续已有项目差量链路。" + action_text
            return ""
        detail = str(baseline_check.detail).strip()
        if detail == "baseline audit missing":
            return " 当前是已有项目模式，但 baseline audit 还没生成。"
        if detail == "baseline confirmation missing":
            return " 当前是已有项目模式，但 baseline confirmation 还没记录。"
        if detail.startswith("baseline confirmation "):
            return " 当前先完成 baseline confirmation，再继续差量文档、Spec 与实现。"
        return ""

    def _compliance_signal_summary(self) -> str:
        compliance_check = next(
            (check for check in self.checks if check.name == "Compliance Closure"),
            None,
        )
        if compliance_check is None:
            return ""
        detail = str(compliance_check.detail).strip()
        source_issues: list[str] = []
        for label in ("spec", "architecture", "uiux"):
            match = re.search(rf"{label}=([a-z_]+)", detail)
            state = match.group(1) if match else ""
            if state and state != "ready":
                source_issues.append(f"{label}={state}")
        if source_issues:
            return (
                " 合规链当前优先卡在证据状态："
                + "、".join(source_issues[:3])
                + "。这意味着需求、架构或 UI 约束还不能被稳定追溯到当前实现，管理侧现在还不该做最终验收签字。"
            )
        if not compliance_check.passed:
            return " 合规链证据已齐，但内容仍未达标。当前还不能证明“做出来的东西就是承诺过要交付的东西”。"
        return " 合规链证据与内容检查当前均已闭环。"

    def _frontend_governance_signal_summary(self) -> str:
        delivery_check = next(
            (check for check in self.checks if check.name == "Delivery Closure"),
            None,
        )
        if delivery_check is None:
            return ""
        detail = str(delivery_check.detail).strip()
        if "ui contract incomplete" in detail or "ui contract missing" in detail:
            return (
                " UI 阶段当前优先卡在契约冻结，Claude-Design 风格执行协议尚未完全冻结。"
                " 这会让设计、开发和验收对“什么叫完成”理解不一致。"
            )
        if "frontend runtime claude-design execution missing:" in detail:
            missing = detail.split("frontend runtime claude-design execution missing:", 1)[1].split(";", 1)[0].strip()
            return (
                " UI 阶段当前优先卡在 runtime 证明，缺少 "
                + missing
                + " 的运行证据。当前还无法向业务或管理者证明页面不只是写出来，而是真的跑起来并符合框架约束。"
            )
        if "ui review/runtime claude-design mismatch:" in detail:
            observed = detail.split("ui review/runtime claude-design mismatch:", 1)[1].split(";", 1)[0].strip()
            return (
                " UI 阶段当前存在 source/runtime 证据漂移，"
                + observed
                + "。这意味着代码、预览和审查结论还没对齐，演示时容易出现“文档说可以、现场却不稳定”。"
            )
        if "ui review source claude-design protocol missing:" in detail:
            observed = detail.split("ui review source claude-design protocol missing:", 1)[1].split(";", 1)[0].strip()
            return (
                " UI 阶段当前卡在源码/预览落地，缺少 "
                + observed
                + " 的实际执行信号。现在还不能说明页面已经按照冻结 UI 方案真实落地。"
            )
        framework_match = re.search(r"(.+?) frontend runtime framework execution missing", detail)
        if framework_match:
            framework = framework_match.group(1).strip()
            return (
                " UI 阶段当前卡在 "
                + framework
                + " 框架专项执行，implementation modules、native capabilities、validation surfaces 或 delivery evidence 仍未完全闭环。"
                " 这会直接拖慢跨端联调、演示验收和最终上线节奏。"
            )
        if "ui review screenshot visual judge failed:" in detail:
            observed = detail.split("ui review screenshot visual judge failed:", 1)[1].split(";", 1)[0].strip()
            observed_text = f" 当前观测：{observed}。" if observed else ""
            return (
                " UI 阶段当前截图级视觉验收未通过，页面仍然过平、过空或过于单一。"
                " 用户会直接感知为商业质感不足或像半成品。"
                + observed_text
            )
        return ""

    def _framework_playbook_signal_summary(self) -> str:
        framework_check = next(
            (check for check in self.checks if check.name == "Framework Harness Trail"),
            None,
        )
        if framework_check is None:
            return ""
        detail = str(framework_check.detail).strip()
        if detail == "no cross-platform framework harness required":
            return ""
        framework_match = re.match(r"(.+?) harness", detail)
        framework = framework_match.group(1).strip() if framework_match else "cross-platform"
        if framework_check.passed:
            return (
                " 跨平台框架专项当前已闭环，"
                + framework
                + " 的 playbook、runtime 执行与交付证据均已纳入发布门禁。"
                " 这意味着框架专项不再只是技术检查项，而是可被验收团队直接复核的交付打法。"
            )
        recommendation = str(framework_check.recommendation).strip()
        action_text = f" 下一步：{recommendation}" if recommendation else ""
        return (
            " 跨平台框架专项当前卡在 "
            + framework
            + " playbook/执行闭环。"
            " 这会直接影响跨端体验稳定性、专项验收效率和上线节奏。"
            + action_text
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "score": self.score,
            "passed": self.passed,
            "threshold": self.threshold,
            "summary": {"executive_summary": self.executive_summary},
            "failed_checks": [item.name for item in self.failed_checks],
            "checks": [item.to_dict() for item in self.checks],
            "recent_timeline": list(self.recent_timeline),
            "operational_focus": dict(self.operational_focus),
            "evidence_identity": dict(self.evidence_identity),
            "workflow_context": dict(self.workflow_context),
            "baseline_governance": dict(self.baseline_governance),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Release Readiness Report",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Score: {self.score}/100",
            f"- Threshold: {self.threshold}",
            f"- Passed: {'yes' if self.passed else 'no'}",
            f"- Failed checks: {len(self.failed_checks)}",
            "",
            "## Executive Summary",
            "",
            self.executive_summary,
            "",
        ]
        if self.workflow_context:
            lines.extend(
                [
                    "## Workflow Context",
                    "",
                    f"- Workflow Status: {self.workflow_context.get('workflow_status', '-')}",
                    f"- Blocking Gate: {self.workflow_context.get('blocking_gate', '') or 'clear'}",
                    f"- Recommended Host Action: {self.workflow_context.get('recommended_host_action', '-')}",
                    "",
                ]
            )
        if self.baseline_governance:
            lines.extend(
                [
                    "## Baseline Governance",
                    "",
                    f"- Status: {self.baseline_governance.get('status', '-')}",
                    f"- Entry Gate: {self.baseline_governance.get('entry_gate', '') or 'clear'}",
                    f"- Ready: {'yes' if bool(self.baseline_governance.get('ready', False)) else 'no'}",
                    f"- Next Host Action: {self.baseline_governance.get('next_host_action', '-')}",
                    "",
                ]
            )
        lines.extend(
            [
            "## Checks",
            "",
            "| Check | Result | Severity | Detail | Recommendation |",
            "|:---|:---:|:---:|:---|:---|",
            ]
        )
        for check in self.checks:
            marker = "PASS" if check.passed else "FAIL"
            lines.append(
                f"| {check.name} | {marker} | {check.severity} | {check.detail} | {check.recommendation or '-'} |"
            )
        lines.append("")

        # 治理就绪度章节
        governance_checks = [c for c in self.checks if c.name.startswith("Governance:")]
        if governance_checks:
            lines.append("## Governance Readiness")
            lines.append("")
            gov_passed = sum(1 for c in governance_checks if c.passed)
            gov_total = len(governance_checks)
            lines.append(f"- Governance checks: {gov_passed}/{gov_total} passed")
            lines.append("")
            lines.append("| Check | Result | Detail |")
            lines.append("|:---|:---:|:---|")
            for gc in governance_checks:
                marker = "PASS" if gc.passed else "FAIL"
                lines.append(f"| {gc.name} | {marker} | {gc.detail} |")
            lines.append("")

        operational_checks = [
            c
            for c in self.checks
            if c.name
            in {
                "Workflow Recovery Trail",
                "Framework Harness Trail",
                "Hook Audit Trail",
                "Operational Harness Trail",
            }
        ]
        if operational_checks:
            lines.append("## Operational Continuity")
            lines.append("")
            lines.append("| Check | Result | Detail |")
            lines.append("|:---|:---:|:---|")
            for oc in operational_checks:
                marker = "PASS" if oc.passed else "FAIL"
                lines.append(f"| {oc.name} | {marker} | {oc.detail} |")
            lines.append("")
        focus_summary = str(self.operational_focus.get("summary", "")).strip()
        focus_action = str(self.operational_focus.get("recommended_action", "")).strip()
        if focus_summary:
            lines.append("## Current Governance Focus")
            lines.append("")
            lines.append(f"- {focus_summary}")
            if focus_action:
                lines.append(f"- 建议先做: {focus_action}")
            lines.append("")
        if self.recent_timeline:
            lines.append("## Recent Operational Timeline")
            lines.append("")
            for item in self.recent_timeline:
                timestamp = str(item.get("timestamp", "")).strip() or "-"
                title = str(item.get("title", "")).strip() or str(item.get("kind", "")).strip()
                message = str(item.get("message", "")).strip() or "-"
                lines.append(f"- {timestamp} · {title} · {message}")
            lines.append("")

        return "\n".join(lines)


class ReleaseReadinessEvaluator:
    """评估当前仓库是否达到可发布状态。"""

    REQUIRED_DOCS = {
        "README.md": [
            "uv tool install",
            "/super-dev",
            "super-dev:",
            "super-dev update",
        ],
        "README_EN.md": [
            "uv tool install",
            "/super-dev",
            "super-dev:",
            "super-dev update",
        ],
        "docs/INSTALL_OPTIONS.md": ["uv tool install", "super-dev update"],
        "docs/README.md": ["用户文档", "维护者文档"],
        "docs/HOST_USAGE_GUIDE.md": ["Smoke", "/super-dev", "super-dev:"],
        "docs/HOST_CAPABILITY_AUDIT.md": ["官方依据", "integrate smoke / validate"],
        "docs/HOST_RUNTIME_VALIDATION.md": [
            "host runtime validation",
            "research",
            "super-dev review docs",
        ],
        "docs/HOST_INSTALL_SURFACES.md": ["Codex CLI", "super-dev:", "继续当前流程"],
        "docs/WORKFLOW_GUIDE.md": ["super-dev review docs", "继续当前流程"],
        "docs/WORKFLOW_GUIDE_EN.md": ["super-dev review docs", "continue current workflow"],
        "docs/PRODUCT_AUDIT.md": ["super-dev product-audit", "proof-pack", "release readiness"],
    }

    REQUIRED_RUNTIME_IGNORE_RULES = [
        "output/",
        "artifacts/",
        ".super-dev/runs/",
        ".super-dev/review-state/",
        "/.agent/",
        "/.claude/",
        "/.codebuddy/",
        "/.cursor/",
        "/.gemini/",
        "/.kiro/",
        "/.opencode/",
        "/.qoder/",
        "/.trae/",
        "/.windsurf/",
        "/GEMINI.md",
    ]

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = resolve_project_artifact_prefix(
            self.project_dir,
            fallback_name=self.project_dir.name,
        )

    def evaluate(self, verify_tests: bool = False) -> ReleaseReadinessReport:
        report = ReleaseReadinessReport(project_name=self.project_name)
        pipeline_summary = detect_pipeline_summary(self.project_dir)
        report.workflow_context = build_host_workflow_context(
            self.project_dir,
            summary=pipeline_summary,
        )
        report.baseline_governance = inspect_baseline_governance(
            self.project_dir,
            workflow_payload=pipeline_summary,
            output_dir=self.output_dir,
        )
        report.recent_timeline = load_recent_operational_timeline(self.project_dir, limit=5)
        report.operational_focus = derive_operational_focus(self.project_dir)
        report.checks.extend(
            [
                self._check_version_alignment(),
                self._check_required_docs(),
                self._check_host_matrix_integrity(),
                self._check_host_coverage_depth(),
                self._check_host_runtime_validation(),
                self._check_runtime_boundary_rules(),
                self._check_packaging_entrypoints(),
                self._check_release_spec_exists(),
                self._check_baseline_confirmation(),
                self._check_spec_quality(),
                self._check_scope_coverage(),
                self._check_compliance_closure(),
                self._check_expert_stage_governance(),
                self._check_delivery_closure(),
                self._check_workflow_recovery_trail(),
                self._check_framework_harness_trail(),
                self._check_hook_audit_trail(),
                self._check_operational_harness_trail(),
            ]
        )
        # 治理能力检查（增量添加，不影响现有逻辑）
        report.checks.extend(self._check_governance_artifacts())
        if verify_tests:
            report.checks.append(self._check_test_suite())
        return report

    def write(self, report: ReleaseReadinessReport) -> dict[str, Path]:
        base = self.output_dir / f"{self.project_name}-release-readiness"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        report.evidence_identity = self._build_report_evidence_identity()
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _build_report_evidence_identity(self) -> dict[str, Any]:
        return build_evidence_identity(
            self.project_dir,
            artifact_name="release-readiness",
            dependencies=[
                latest_artifact(
                    self.output_dir, "*-quality-gate.json", preferred_prefix=self.project_name
                )
                or latest_artifact(
                    self.output_dir, "*-quality-gate.md", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-task-execution.md", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-product-audit.json", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-ui-contract.json", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-frontend-runtime.json", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-ui-review.json", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir, "*-baseline-audit.json", preferred_prefix=self.project_name
                )
                or latest_artifact(
                    self.output_dir, "*-baseline-audit.md", preferred_prefix=self.project_name
                ),
                latest_artifact(
                    self.output_dir,
                    "*-ui-contract-alignment.json",
                    preferred_prefix=self.project_name,
                ),
                latest_artifact(self.output_dir, "*-uiux.md", preferred_prefix=self.project_name),
            ],
        )

    def _check_version_alignment(self) -> ReleaseReadinessCheck:
        pyproject = self.project_dir / "pyproject.toml"
        init_file = self.project_dir / "super_dev" / "__init__.py"
        readme = self.project_dir / "README.md"
        readme_en = self.project_dir / "README_EN.md"

        pyproject_version = self._extract_regex(pyproject, r'version\s*=\s*"([^"]+)"')
        init_version = self._extract_regex(init_file, r'__version__\s*=\s*"([^"]+)"')
        readme_version = self._extract_regex(readme, r"当前版本：`([^`]+)`")
        readme_en_version = self._extract_regex(readme_en, r"Current version: `([^`]+)`")

        versions = [
            value
            for value in [pyproject_version, init_version, readme_version, readme_en_version]
            if value
        ]
        unique_versions = sorted(set(versions))
        passed = len(unique_versions) == 1 and unique_versions[0] == __version__
        detail = f"versions={unique_versions or ['missing']}"
        return ReleaseReadinessCheck(
            name="Version Alignment",
            passed=passed,
            detail=detail,
            severity="critical" if not passed else "low",
            recommendation="同步 pyproject、super_dev/__init__.py、README 与 README_EN 中的版本号。",
        )

    def _check_required_docs(self) -> ReleaseReadinessCheck:
        missing: list[str] = []
        for relative_path, markers in self.REQUIRED_DOCS.items():
            file_path = self.project_dir / relative_path
            if not file_path.exists():
                missing.append(f"{relative_path} (missing)")
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for marker in markers:
                if marker not in text:
                    missing.append(f"{relative_path} -> {marker}")
        passed = not missing
        detail = "all required docs and markers present" if passed else "; ".join(missing[:8])
        return ReleaseReadinessCheck(
            name="Documentation Coverage",
            passed=passed,
            detail=detail,
            severity="high" if not passed else "low",
            recommendation="补齐发布、宿主使用、Smoke 验收与恢复流程文档。",
        )

    def _check_host_matrix_integrity(self) -> ReleaseReadinessCheck:
        gaps = IntegrationManager.coverage_gaps()
        skill_gaps = SkillManager.coverage_gaps()
        all_missing = sum(len(items) for items in gaps.values()) + sum(
            len(items) for items in skill_gaps.values()
        )
        passed = all_missing == 0
        detail = (
            "host targets, slash map, docs map and skill targets are aligned"
            if passed
            else f"integration_gaps={gaps}, skill_gaps={skill_gaps}"
        )
        return ReleaseReadinessCheck(
            name="Host Matrix Integrity",
            passed=passed,
            detail=detail,
            severity="critical" if not passed else "low",
            recommendation="确保宿主目录、slash/skill 覆盖、官方文档映射保持一致。",
        )

    def _check_host_coverage_depth(self) -> ReleaseReadinessCheck:
        manager = IntegrationManager(self.project_dir)
        profiles = manager.list_adapter_profiles()
        certified = [item.host for item in profiles if item.certification_level == "certified"]
        compatible = [item.host for item in profiles if item.certification_level == "compatible"]
        docs_unverified = [item.host for item in profiles if not item.docs_verified]
        official_backed = [
            item.host
            for item in profiles
            if item.host_protocol_mode
            in {
                "official-subagent",
                "official-skill",
                "official-steering",
                "official-context",
                "official-workflow",
                "official-rules",
            }
        ]

        stable_hosts = len(certified) + len(compatible)
        detail = (
            f"certified={len(certified)}, compatible={len(compatible)}, stable={stable_hosts}, "
            f"official_backed={len(official_backed)}, total={len(profiles)}"
        )
        if docs_unverified:
            detail += f", docs_unverified={docs_unverified}"
        return ReleaseReadinessCheck(
            name="Host Coverage Depth",
            passed=True,
            detail=detail,
            severity="low",
            recommendation="作为生态成熟度观察项跟踪，不阻断当前宿主里的项目交付。",
        )

    def _check_packaging_entrypoints(self) -> ReleaseReadinessCheck:
        install_script = self.project_dir / "install.sh"
        pyproject = self.project_dir / "pyproject.toml"
        readme = self.project_dir / "README.md"
        install_options = self.project_dir / "docs" / "INSTALL_OPTIONS.md"
        text = readme.read_text(encoding="utf-8", errors="ignore") if readme.exists() else ""
        install_options_text = (
            install_options.read_text(encoding="utf-8", errors="ignore")
            if install_options.exists()
            else ""
        )
        pyproject_text = (
            pyproject.read_text(encoding="utf-8", errors="ignore") if pyproject.exists() else ""
        )

        checks = [
            install_script.exists(),
            "[project.scripts]" in pyproject_text,
            "super-dev = " in pyproject_text,
            "uv tool install super-dev" in text,
            "uv tool install super-dev" in install_options_text,
            "super-dev update" in text,
        ]
        passed = all(checks)
        detail = (
            "installer, entrypoint, uv-first docs, and update docs are present"
            if passed
            else "missing installer or entrypoint/docs markers"
        )
        return ReleaseReadinessCheck(
            name="Packaging Entrypoints",
            passed=passed,
            detail=detail,
            severity="high" if not passed else "low",
            recommendation="确保 README 与 INSTALL_OPTIONS 统一为 uv-first，并且入口脚本与 update 命令文档一致。",
        )

    def _check_runtime_boundary_rules(self) -> ReleaseReadinessCheck:
        gitignore = self.project_dir / ".gitignore"
        text = gitignore.read_text(encoding="utf-8", errors="ignore") if gitignore.exists() else ""
        missing = [rule for rule in self.REQUIRED_RUNTIME_IGNORE_RULES if rule not in text]
        passed = not missing
        detail = (
            "runtime host surfaces and review-state ignore rules are present"
            if passed
            else f"missing ignore rules: {', '.join(missing[:8])}"
        )
        return ReleaseReadinessCheck(
            name="Runtime Boundary Rules",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="明确忽略宿主运行时目录、review-state 与项目级宿主接入产物，避免本机生成文件混入仓库。",
        )

    def _check_host_runtime_validation(self) -> ReleaseReadinessCheck:
        payload = load_host_runtime_validation(self.project_dir) or {}
        hosts = payload.get("hosts", {}) if isinstance(payload, dict) else {}
        if not isinstance(hosts, dict) or not hosts:
            return ReleaseReadinessCheck(
                name="Host Runtime Validation",
                passed=True,
                detail="no host runtime validation state recorded",
                severity="low",
                recommendation="如当前交付依赖宿主内继续执行或恢复，请先完成一次真人宿主验收，并把 runtime validation 状态记录到当前项目。",
            )

        pending_hosts: list[str] = []
        failed_hosts: list[str] = []
        governance_gap = collect_layered_runtime_governance_gap(self.project_dir)
        repo_probe_failed_hosts = (
            list(governance_gap.get("impacted_hosts", [])) if isinstance(governance_gap, dict) else []
        )
        for host_id, item in hosts.items():
            if not isinstance(item, dict):
                continue
            manual_status = str(item.get("status", "")).strip() or "pending"
            if manual_status == "failed":
                failed_hosts.append(str(host_id))
            elif manual_status != "passed":
                pending_hosts.append(str(host_id))

        passed = not pending_hosts and not failed_hosts and not repo_probe_failed_hosts
        if passed:
            detail = f"validated hosts ready={len(hosts)}/{len(hosts)}"
        else:
            parts: list[str] = []
            if pending_hosts:
                parts.append(f"pending={', '.join(pending_hosts[:3])}")
            if failed_hosts:
                parts.append(f"failed={', '.join(failed_hosts[:3])}")
            if repo_probe_failed_hosts:
                parts.append(f"repo_probe_failed={', '.join(repo_probe_failed_hosts[:3])}")
            detail = "host runtime validation incomplete: " + "; ".join(parts)
        return ReleaseReadinessCheck(
            name="Host Runtime Validation",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="先让目标宿主完成人工 runtime validation，再修复 repo probe 暴露的 workflow continuity / harness / frontend runtime 闭环问题。",
        )

    def _check_release_spec_exists(self) -> ReleaseReadinessCheck:
        change_dir = self.project_dir / ".super-dev" / "changes" / "release-hardening-finalization"
        required = [
            change_dir / "change.yaml",
            change_dir / "proposal.md",
            change_dir / "tasks.md",
        ]
        missing = [
            str(path.relative_to(self.project_dir)) for path in required if not path.exists()
        ]
        passed = not missing
        detail = "release change spec present" if passed else f"missing {', '.join(missing)}"
        return ReleaseReadinessCheck(
            name="Release Change Spec",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="将发布收尾任务沉淀到正式 change spec，避免口头跟踪。",
        )

    def _check_baseline_confirmation(self) -> ReleaseReadinessCheck:
        baseline = inspect_baseline_governance(self.project_dir, output_dir=self.output_dir)
        if baseline.get("status") == "not_required":
            return ReleaseReadinessCheck(
                name="Baseline Confirmation",
                passed=True,
                detail="baseline confirmation not required for current work mode",
                severity="low",
                recommendation="仅在已有项目迭代、派生或修复模式下要求 baseline confirmation。",
            )
        if baseline.get("status") == "missing_audit":
            return ReleaseReadinessCheck(
                name="Baseline Confirmation",
                passed=False,
                detail="baseline audit missing",
                severity="critical",
                recommendation="先生成 baseline audit，确认当前项目边界、现有能力和差量改动后再继续。",
            )
        if baseline.get("status") == "missing_confirmation":
            return ReleaseReadinessCheck(
                name="Baseline Confirmation",
                passed=False,
                detail="baseline confirmation missing",
                severity="critical",
                recommendation="先执行 `super-dev review baseline --status confirmed`，再进入 delta research / docs / spec / implementation。",
            )
        return ReleaseReadinessCheck(
            name="Baseline Confirmation",
            passed=bool(baseline.get("ready")),
            detail=(
                "baseline confirmed"
                if baseline.get("status") == "confirmed"
                else f"baseline confirmation {baseline.get('confirmation_status') or baseline.get('status')}"
            ),
            severity="critical" if not baseline.get("ready") else "low",
            recommendation="已有项目模式下，baseline confirmed 后才能进入后续差量文档、Spec 与实现。",
        )

    def _check_spec_quality(self) -> ReleaseReadinessCheck:
        validator = SpecValidator(self.project_dir)
        report = validator.assess_latest_change_quality(
            exclude_ids={"release-hardening-finalization"}
        )
        if report is None:
            return ReleaseReadinessCheck(
                name="Spec Quality",
                passed=True,
                detail="no active change spec under evaluation",
                severity="low",
                recommendation="如当前发布包含新需求或修复变更，先检查当前 change 的 Spec 质量报告。",
            )

        passed = report.passed
        detail = f"change={report.change_id}, score={report.score:.1f}, level={report.level}, blockers={len(report.blockers)}"
        recommendation = (
            report.action_plan[0].get("command", "")
            if report.action_plan
            else f"查看 change `{report.change_id}` 的完整 Spec 整改计划。"
        )
        return ReleaseReadinessCheck(
            name="Spec Quality",
            passed=passed,
            detail=detail,
            severity="high" if not passed else "low",
            recommendation=recommendation,
        )

    def _check_scope_coverage(self) -> ReleaseReadinessCheck:
        builder = FeatureChecklistBuilder(self.project_dir)
        report = builder.build()
        builder.write(report)

        coverage_text = (
            f"{report.coverage_rate:.1f}%" if report.coverage_rate is not None else "unknown"
        )
        detail = (
            f"status={report.status}, coverage={coverage_text}, "
            f"high_priority_gaps={report.high_priority_gap_count}, missing={report.missing_count}, unknown={report.unknown_count}"
        )

        if report.status == "unknown":
            return ReleaseReadinessCheck(
                name="Scope Coverage",
                passed=True,
                detail=detail,
                severity="low",
                recommendation="如需确认 PRD 全量覆盖率，先执行 `super-dev product-audit` 或交付审查，查看范围完成度与显式缺口。",
            )

        passed = report.high_priority_gap_count == 0 and report.missing_count == 0
        recommendation = (
            "先补齐 P0/P1 缺口或把未实现能力明确降级为后续版本，再重新执行产品审查或交付审查。"
            if not passed
            else "当前范围覆盖率未发现高优先级缺口。"
        )
        return ReleaseReadinessCheck(
            name="Scope Coverage",
            passed=passed,
            detail=detail,
            severity="high" if not passed else "low",
            recommendation=recommendation,
        )

    def _check_compliance_closure(self) -> ReleaseReadinessCheck:
        blockers: list[str] = []
        details: list[str] = []

        try:
            from .reviewers.spec_compliance import (
                inspect_spec_compliance_artifact,
                run_spec_compliance,
            )

            inspection = inspect_spec_compliance_artifact(self.project_dir, self.output_dir)
            report = run_spec_compliance(self.project_dir, self.output_dir)
            if report.total_requirements > 0:
                details.append(
                    f"spec={inspection['status']},coverage={report.coverage_percent}%/{report.total_requirements} reqs"
                )
                if inspection["status"] != "ready":
                    blockers.append(f"spec compliance artifact {inspection['status']}")
                if report.score < 80:
                    blockers.append(f"spec compliance score={report.score}")
            else:
                details.append(f"spec={inspection['status']},n/a")
        except Exception:
            blockers.append("spec compliance unreadable")

        try:
            from .reviewers.architecture_drift import (
                inspect_architecture_drift_artifact,
                run_architecture_drift,
            )

            inspection = inspect_architecture_drift_artifact(self.project_dir, self.output_dir)
            report = run_architecture_drift(self.project_dir, self.output_dir)
            if report.total_drifts > 0 or report.declared_tech_stack:
                details.append(
                    f"architecture={inspection['status']},drifts:{report.total_drifts},critical:{report.critical_count}"
                )
                if inspection["status"] != "ready":
                    blockers.append(f"architecture drift artifact {inspection['status']}")
                if report.score < 80:
                    blockers.append(
                        f"architecture drift score={report.score}, critical={report.critical_count}"
                    )
            else:
                details.append(f"architecture={inspection['status']},n/a")
        except Exception:
            blockers.append("architecture drift unreadable")

        try:
            from .reviewers.uiux_compliance import (
                inspect_uiux_compliance_artifact,
                run_uiux_compliance,
            )

            inspection = inspect_uiux_compliance_artifact(self.project_dir, self.output_dir)
            report = run_uiux_compliance(self.project_dir, self.output_dir)
            if report.files_scanned > 0:
                details.append(
                    f"uiux={inspection['status']},violations:{report.total_violations},files:{report.files_scanned}"
                )
                if inspection["status"] != "ready":
                    blockers.append(f"uiux compliance artifact {inspection['status']}")
                if report.score < 80:
                    blockers.append(f"uiux compliance score={report.score}")
            else:
                details.append(f"uiux={inspection['status']},n/a")
        except Exception:
            blockers.append("uiux compliance unreadable")

        passed = not blockers
        detail = "; ".join(details if passed else [*details, *blockers])
        recommendation = (
            "重新执行 `super-dev compliance --type all`，先修复 Requirement traceability、architecture drift 与 UIUX 违例，再生成 quality gate / proof-pack / release readiness。"
            if not passed
            else "当前 spec / architecture / UIUX 合规链已进入发布闭环。"
        )
        return ReleaseReadinessCheck(
            name="Compliance Closure",
            passed=passed,
            detail=detail or "compliance closure aligned",
            severity="critical" if not passed else "low",
            recommendation=recommendation,
        )

    def _check_expert_stage_governance(self) -> ReleaseReadinessCheck:
        summary = detect_pipeline_summary(self.project_dir)
        governance = (
            summary.get("expert_governance", {})
            if isinstance(summary.get("expert_governance", {}), dict)
            else {}
        )
        missing_stages = (
            list(governance.get("missing_stages", []))
            if isinstance(governance.get("missing_stages", []), list)
            else []
        )
        visible_stage_count = int(governance.get("visible_stage_count", 0) or 0)
        covered_count = int(governance.get("covered_count", 0) or 0)
        passed = not missing_stages
        if visible_stage_count <= 0:
            detail = "no active stage expert evidence required yet"
            passed = True
        elif passed:
            detail = (
                f"expert participation recorded for {covered_count}/{visible_stage_count} visible stages"
            )
        else:
            detail = "expert stage evidence missing: " + "、".join(missing_stages[:4])
        return ReleaseReadinessCheck(
            name="Expert Stage Governance",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="把每个已进入的主流程阶段都写成显式专家证据，避免只在提示词里说专家在线但没有落盘记录。",
        )

    def _check_test_suite(self) -> ReleaseReadinessCheck:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:
            return ReleaseReadinessCheck(
                name="Test Suite",
                passed=False,
                detail=f"pytest execution failed: {exc}",
                severity="critical",
                recommendation="修复测试环境后重新执行 `super-dev release readiness --verify-tests`。",
            )
        output = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        ).strip()
        tail = output.splitlines()[-1] if output else "no output"
        return ReleaseReadinessCheck(
            name="Test Suite",
            passed=result.returncode == 0,
            detail=tail,
            severity="critical" if result.returncode != 0 else "low",
            recommendation="确保全量 pytest 通过后再执行对外发布。",
        )

    def _check_delivery_closure(self) -> ReleaseReadinessCheck:
        redteam = load_redteam_evidence(self.project_dir, self.project_name)
        quality_gate_json = latest_artifact(
            self.output_dir, "*-quality-gate.json", preferred_prefix=self.project_name
        )
        quality_gate_file = quality_gate_json or latest_artifact(
            self.output_dir, "*-quality-gate.md", preferred_prefix=self.project_name
        )
        task_execution_file = latest_artifact(
            self.output_dir, "*-task-execution.md", preferred_prefix=self.project_name
        )
        product_audit_file = latest_artifact(
            self.output_dir, "*-product-audit.json", preferred_prefix=self.project_name
        )
        ui_contract_file = latest_artifact(
            self.output_dir, "*-ui-contract.json", preferred_prefix=self.project_name
        )
        frontend_runtime_file = latest_artifact(
            self.output_dir, "*-frontend-runtime.json", preferred_prefix=self.project_name
        )
        ui_review_file = latest_artifact(
            self.output_dir, "*-ui-review.json", preferred_prefix=self.project_name
        )
        ui_alignment_file = latest_artifact(
            self.output_dir, "*-ui-contract-alignment.json", preferred_prefix=self.project_name
        )
        uiux_file = latest_artifact(
            self.output_dir, "*-uiux.md", preferred_prefix=self.project_name
        )
        design_tokens_file = self.output_dir / "frontend" / "design-tokens.css"

        blockers: list[str] = []
        ui_contract_payload: dict[str, Any] = {}
        cross_platform_frontend = False
        framework_playbook: dict[str, Any] = {}
        frontend_value = ""

        if redteam is None:
            blockers.append("redteam missing")
        elif not redteam.passed:
            blockers.append(
                f"redteam failed ({'; '.join(redteam.blocking_reasons) or redteam.path.name})"
            )

        if quality_gate_file is None or not quality_gate_file.exists():
            blockers.append("quality gate missing")
        else:
            expected_quality_identity = build_evidence_identity(
                self.project_dir,
                artifact_name="quality-gate",
                dependencies=[ui_review_file, ui_alignment_file, uiux_file],
            )
            if quality_gate_json is not None:
                quality_gate_payload = load_json_payload(quality_gate_json)
                identity_ok, identity_reason = evidence_identity_matches(
                    quality_gate_payload,
                    expected=expected_quality_identity,
                )
                if not identity_ok:
                    blockers.append(
                        "quality gate evidence mismatch"
                        if identity_reason == "digest_mismatch"
                        else "quality gate evidence identity missing"
                    )
            if is_artifact_stale(
                quality_gate_file,
                dependencies=[ui_review_file, ui_alignment_file, uiux_file],
            ):
                blockers.append("quality gate stale")
            if quality_gate_json is not None:
                quality_gate_payload = load_json_payload(quality_gate_json)
                if quality_gate_payload:
                    if not bool(quality_gate_payload.get("passed", False)):
                        blockers.append("quality gate failed")
                else:
                    quality_text = quality_gate_file.read_text(
                        encoding="utf-8", errors="ignore"
                    ).lower()
                    if "未通过" in quality_text or "failed" in quality_text:
                        blockers.append("quality gate failed")
            else:
                quality_text = quality_gate_file.read_text(encoding="utf-8", errors="ignore").lower()
                if "未通过" in quality_text or "failed" in quality_text:
                    blockers.append("quality gate failed")

        if task_execution_file is None or not task_execution_file.exists():
            blockers.append("task execution missing")
        else:
            task_text = task_execution_file.read_text(encoding="utf-8", errors="ignore")
            if (
                "## 执行期验证摘要" not in task_text
                or "## 宿主补充自检（交付前必做）" not in task_text
            ):
                blockers.append("task execution self-review incomplete")

        if product_audit_file is None or not product_audit_file.exists():
            blockers.append("product audit missing")
        else:
            try:
                product_payload = json.loads(product_audit_file.read_text(encoding="utf-8"))
            except Exception:
                blockers.append("product audit unreadable")
            else:
                product_status = str(product_payload.get("status", "missing"))
                if product_status == "revision_required":
                    blockers.append("product audit requires revision")

        if ui_contract_file is None or not ui_contract_file.exists():
            blockers.append("ui contract missing")
        else:
            if is_artifact_stale(ui_contract_file, dependencies=[uiux_file]):
                blockers.append("ui contract stale")
            try:
                ui_contract_payload = json.loads(ui_contract_file.read_text(encoding="utf-8"))
            except Exception:
                blockers.append("ui contract unreadable")
            else:
                if not isinstance(ui_contract_payload, dict):
                    blockers.append("ui contract invalid")
                else:
                    component_stack = (
                        ui_contract_payload.get("component_stack", {})
                        if isinstance(ui_contract_payload.get("component_stack"), dict)
                        else {}
                    )
                    emoji_policy = (
                        ui_contract_payload.get("emoji_policy")
                        if isinstance(ui_contract_payload.get("emoji_policy"), dict)
                        else {}
                    )
                    analysis = (
                        ui_contract_payload.get("analysis", {})
                        if isinstance(ui_contract_payload.get("analysis"), dict)
                        else {}
                    )
                    frontend_value = str(analysis.get("frontend") or "").lower().strip()
                    cross_platform_frontend = is_cross_platform_frontend(frontend_value)
                    framework_playbook = (
                        ui_contract_payload.get("framework_playbook")
                        if isinstance(ui_contract_payload.get("framework_playbook"), dict)
                        else {}
                    )
                    icon_system = (
                        ui_contract_payload.get("icon_system")
                        or component_stack.get("icon")
                        or component_stack.get("icons")
                    )
                    required_sections = (
                        bool(ui_contract_payload.get("style_direction")),
                        (
                            (
                                isinstance(ui_contract_payload.get("typography"), dict)
                                and bool(ui_contract_payload.get("typography"))
                            )
                            or (
                                isinstance(ui_contract_payload.get("typography_preset"), dict)
                                and bool(ui_contract_payload.get("typography_preset"))
                            )
                        ),
                        bool(icon_system),
                        (
                            bool(emoji_policy)
                            and emoji_policy.get("allowed_in_ui") is False
                            and emoji_policy.get("allowed_as_icon") is False
                            and emoji_policy.get("allowed_during_development") is False
                        ),
                        isinstance(ui_contract_payload.get("ui_library_preference"), dict)
                        and bool(ui_contract_payload.get("ui_library_preference")),
                        isinstance(ui_contract_payload.get("design_tokens"), dict)
                        and bool(ui_contract_payload.get("design_tokens")),
                    )
                    if cross_platform_frontend:
                        framework_name = str(
                            framework_playbook.get("framework")
                            or frontend_value
                            or "cross-platform"
                        ).strip()
                        required_sections = (
                            *required_sections,
                            framework_playbook_complete(framework_playbook),
                        )
                    if not all(required_sections):
                        if cross_platform_frontend:
                            blockers.append(f"{framework_name} ui contract playbook incomplete")
                        else:
                            blockers.append("ui contract incomplete")

        if not design_tokens_file.exists():
            blockers.append("design tokens missing")

        if frontend_runtime_file is None or not frontend_runtime_file.exists():
            blockers.append("frontend runtime missing")
        else:
            expected_frontend_identity = build_evidence_identity(
                self.project_dir,
                artifact_name="frontend-runtime",
                dependencies=[ui_contract_file, ui_alignment_file],
            )
            if is_artifact_stale(
                frontend_runtime_file,
                dependencies=[ui_contract_file, ui_alignment_file],
            ):
                blockers.append("frontend runtime stale")
            try:
                frontend_runtime_payload = json.loads(
                    frontend_runtime_file.read_text(encoding="utf-8")
                )
            except Exception:
                blockers.append("frontend runtime unreadable")
            else:
                identity_ok, identity_reason = evidence_identity_matches(
                    frontend_runtime_payload if isinstance(frontend_runtime_payload, dict) else {},
                    expected=expected_frontend_identity,
                )
                if not identity_ok:
                    blockers.append(
                        "frontend runtime evidence mismatch"
                        if identity_reason == "digest_mismatch"
                        else "frontend runtime evidence identity missing"
                    )
                checks = (
                    frontend_runtime_payload.get("checks", {})
                    if isinstance(frontend_runtime_payload, dict)
                    else {}
                )
                key_ui_checks = (
                    "ui_contract_alignment",
                    "ui_theme_entry",
                    "ui_navigation_shell",
                    "ui_component_imports",
                    "ui_banned_patterns",
                    "ui_framework_playbook",
                    "ui_framework_execution",
                )
                missing_protocol_checks = missing_claude_design_runtime_checks(
                    checks if isinstance(checks, dict) else {},
                    ui_contract_payload if isinstance(ui_contract_payload, dict) else {},
                )
                runtime_ready = (
                    isinstance(frontend_runtime_payload, dict)
                    and bool(frontend_runtime_payload.get("passed", False))
                    and isinstance(checks, dict)
                    and bool(checks.get("ui_contract_json", False))
                    and bool(checks.get("output_frontend_design_tokens", False))
                    and all(bool(checks.get(name, True)) for name in key_ui_checks)
                    and not missing_protocol_checks
                )
                if not runtime_ready:
                    if cross_platform_frontend:
                        framework_name = str(
                            framework_playbook.get("framework")
                            or frontend_value
                            or "cross-platform"
                        ).strip()
                        blockers.append(
                            f"{framework_name} frontend runtime framework execution missing"
                        )
                    else:
                        blockers.append("frontend runtime ui contract alignment missing")
                    if missing_protocol_checks:
                        blockers.append(
                            "frontend runtime claude-design execution missing:"
                            + ",".join(missing_protocol_checks)
                        )
                ui_review_payload = {}
                if ui_review_file is not None and ui_review_file.exists():
                    try:
                        ui_review_payload = json.loads(ui_review_file.read_text(encoding="utf-8"))
                    except Exception:
                        ui_review_payload = {}
                alignment_summary = (
                    ui_review_payload.get("alignment_summary", {})
                    if isinstance(ui_review_payload, dict)
                    and isinstance(ui_review_payload.get("alignment_summary"), dict)
                    else {}
                )
                runtime_protocol_alignment = (
                    alignment_summary.get("runtime_claude_design_protocol", {})
                    if isinstance(alignment_summary.get("runtime_claude_design_protocol"), dict)
                    else {}
                )
                source_protocol_alignment = (
                    alignment_summary.get("source_claude_design_protocol", {})
                    if isinstance(alignment_summary.get("source_claude_design_protocol"), dict)
                    else {}
                )
                screenshot_visual_judge = (
                    alignment_summary.get("screenshot_visual_judge", {})
                    if isinstance(alignment_summary.get("screenshot_visual_judge"), dict)
                    else {}
                )
                premium_ui_contract_labels = {
                    "brand_signal_manifest": "品牌信号与权威感",
                    "proof_composition_rules": "证明构图规则",
                    "component_craft_requirements": "组件工艺要求",
                    "layout_tension_rules": "布局张力纪律",
                }
                if missing_claude_design_runtime_checks(
                    checks if isinstance(checks, dict) else {},
                    ui_contract_payload if isinstance(ui_contract_payload, dict) else {},
                ):
                    pass
                elif runtime_protocol_alignment and not bool(runtime_protocol_alignment.get("passed", False)):
                    blockers.append(
                        "ui review/runtime claude-design mismatch:"
                        + str(runtime_protocol_alignment.get("observed", "")).strip()
                    )
                elif source_protocol_alignment and not bool(source_protocol_alignment.get("passed", False)):
                    blockers.append(
                        "ui review source claude-design protocol missing:"
                        + str(source_protocol_alignment.get("observed", "")).strip()
                    )
                elif screenshot_visual_judge and not bool(
                    screenshot_visual_judge.get("passed", False)
                ):
                    blockers.append(
                        "ui review screenshot visual judge failed:"
                        + str(screenshot_visual_judge.get("observed", "")).strip()
                    )
                else:
                    failed_premium_contracts = [
                        label
                        for key, label in premium_ui_contract_labels.items()
                        if isinstance(alignment_summary.get(key), dict)
                        and alignment_summary[key].get("passed") is False
                    ]
                    if failed_premium_contracts:
                        blockers.append(
                            "ui review premium coaching contract missing:"
                            + ",".join(failed_premium_contracts)
                        )

        passed = not blockers
        detail = "delivery closure evidence aligned" if passed else "; ".join(blockers)
        return ReleaseReadinessCheck(
            name="Delivery Closure",
            passed=passed,
            detail=detail,
            severity="critical" if not passed else "low",
            recommendation=(
                "先补齐 redteam / quality gate / task execution / product audit / ui contract / frontend runtime 证据，并确保它们指向同一轮交付。"
            ),
        )

    def _check_workflow_recovery_trail(self) -> ReleaseReadinessCheck:
        state_payload = load_workflow_state(self.project_dir)
        recent_snapshots = load_recent_workflow_snapshots(self.project_dir, limit=3)
        recent_events = load_recent_workflow_events(self.project_dir, limit=5)

        if state_payload is None and not recent_snapshots:
            return ReleaseReadinessCheck(
                name="Workflow Recovery Trail",
                passed=True,
                detail="no active workflow recovery trail recorded",
                severity="low",
                recommendation="如当前发布来自活跃 Super Dev 流程，建议补齐 workflow-state、history snapshots 与 workflow events。",
            )

        status = str(
            (state_payload or {}).get("status", "")
            or (state_payload or {}).get("workflow_status", "")
        ).strip()
        current_step = str((state_payload or {}).get("current_step_label", "")).strip()
        baseline_pending = status == "waiting_baseline_confirmation"
        passed = (
            state_payload is not None
            and bool(recent_snapshots)
            and bool(recent_events)
            and not baseline_pending
        )
        if baseline_pending:
            detail = (
                "baseline confirmation pending: "
                f"state=yes, snapshots={len(recent_snapshots)}, events={len(recent_events)}"
            )
        else:
            detail = (
                f"status={status or 'unknown'}, step={current_step or 'unknown'}, snapshots={len(recent_snapshots)}, events={len(recent_events)}"
                if passed
                else f"workflow recovery trail incomplete: state={'yes' if state_payload is not None else 'no'}, snapshots={len(recent_snapshots)}, events={len(recent_events)}"
            )
        return ReleaseReadinessCheck(
            name="Workflow Recovery Trail",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="补齐 .super-dev/workflow-state.json、workflow-history 快照和 workflow-events.jsonl，确保关窗、断开和次日恢复有正式证据。",
        )

    def _check_hook_audit_trail(self) -> ReleaseReadinessCheck:
        history = HookManager.load_recent_history(self.project_dir, limit=20)
        if not history:
            return ReleaseReadinessCheck(
                name="Hook Audit Trail",
                passed=True,
                detail="no hook execution history recorded",
                severity="low",
                recommendation="如项目启用了 hooks，建议在关键阶段执行后保留 hook 审计历史。",
            )

        blocked = [item for item in history if item.blocked]
        failed = [item for item in history if not item.success]
        passed = not blocked and not failed
        if passed:
            detail = f"recent hook history clean across {len(history)} events"
        elif blocked:
            detail = f"recent hook history contains {len(blocked)} blocked events"
        else:
            detail = f"recent hook history contains {len(failed)} failed events"
        return ReleaseReadinessCheck(
            name="Hook Audit Trail",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation="检查 .super-dev/hook-history.jsonl 中最近的失败或阻断 hook，修复命令或放宽 blocking 策略后再重试。",
        )

    def _check_framework_harness_trail(self) -> ReleaseReadinessCheck:
        harness = FrameworkHarnessBuilder(self.project_dir).build()
        if not harness.enabled:
            return ReleaseReadinessCheck(
                name="Framework Harness Trail",
                passed=True,
                detail="no cross-platform framework harness required",
                severity="low",
                recommendation="如项目属于 uni-app / Taro / RN / Flutter / Desktop Shell，建议保留 framework harness 证据。",
            )

        passed = harness.passed
        blocker_count = len(harness.blockers)
        detail = (
            f"{harness.framework or 'framework'} harness clean"
            if passed
            else f"{harness.framework or 'framework'} harness has {blocker_count} blockers"
        )
        recommendation = (
            harness.next_actions[0]
            if harness.next_actions
            else "补齐 framework playbook、alignment 与 frontend runtime 的专项执行证据。"
        )
        return ReleaseReadinessCheck(
            name="Framework Harness Trail",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation=recommendation,
        )

    def _check_operational_harness_trail(self) -> ReleaseReadinessCheck:
        harness = OperationalHarnessBuilder(self.project_dir).build()
        focus = derive_operational_focus(self.project_dir)
        if not harness.enabled:
            return ReleaseReadinessCheck(
                name="Operational Harness Trail",
                passed=True,
                detail="no operational harness evidence required",
                severity="low",
                recommendation="如当前 run 依赖 workflow / framework / hook harness，建议保留统一 operational harness 证据。",
            )

        passed = harness.passed
        detail = (
            f"operational harness clean across {harness.passed_count}/{harness.enabled_count} enabled harnesses"
            if passed
            else str(focus.get("summary", "")).strip()
            or f"operational harness has {len(harness.blockers)} blockers across {harness.enabled_count} enabled harnesses"
        )
        recommendation = str(focus.get("recommended_action", "")).strip() or (
            harness.next_actions[0]
            if harness.next_actions
            else "补齐 workflow / framework / hook harness 后重新生成 operational harness。"
        )
        return ReleaseReadinessCheck(
            name="Operational Harness Trail",
            passed=passed,
            detail=detail,
            severity="medium" if not passed else "low",
            recommendation=recommendation,
        )

    def _check_governance_artifacts(self) -> list[ReleaseReadinessCheck]:
        """检查治理相关产物是否就绪（增量检查，不影响现有逻辑）。"""
        checks: list[ReleaseReadinessCheck] = []

        # 1. 治理报告
        governance_reports = list(self.output_dir.glob("governance-report-*.md"))
        if governance_reports:
            checks.append(
                ReleaseReadinessCheck(
                    name="Governance: Report",
                    passed=True,
                    detail=f"治理报告已生成 ({len(governance_reports)} 份)",
                    severity="medium",
                )
            )
        else:
            checks.append(
                ReleaseReadinessCheck(
                    name="Governance: Report",
                    passed=False,
                    detail="未找到治理报告 (output/governance-report-*.md)",
                    severity="low",
                    recommendation="执行治理流程生成 governance-report 后重新评估。",
                )
            )

        # 2. 知识引用报告
        knowledge_refs = list(self.output_dir.glob("*-knowledge-references*.md")) + list(
            self.output_dir.glob("*-knowledge-references*.json")
        )
        knowledge_cache = (
            list((self.output_dir / "knowledge-cache").glob("*-knowledge-bundle.json"))
            if (self.output_dir / "knowledge-cache").is_dir()
            else []
        )
        has_knowledge = bool(knowledge_refs or knowledge_cache)
        checks.append(
            ReleaseReadinessCheck(
                name="Governance: Knowledge References",
                passed=has_knowledge,
                detail=(
                    f"知识引用报告 {len(knowledge_refs)} 份, 知识缓存 {len(knowledge_cache)} 份"
                    if has_knowledge
                    else "未找到知识引用报告或知识缓存"
                ),
                severity="low",
                recommendation=(
                    "" if has_knowledge else "建议在文档阶段启用知识库引用，确保决策有据可查。"
                ),
            )
        )

        # 3. 效能度量数据
        metrics_files = (
            list(self.output_dir.glob("*-metrics*.json"))
            + list(self.output_dir.glob("*-pipeline-metrics.json"))
            + list(self.output_dir.glob("*-pipeline-metrics.md"))
            + (
                list((self.output_dir / "metrics-history").glob("*.json"))
                if (self.output_dir / "metrics-history").is_dir()
                else []
            )
            + list(self.output_dir.glob("*-performance-metrics*.md"))
        )
        has_metrics = bool(metrics_files)
        checks.append(
            ReleaseReadinessCheck(
                name="Governance: Performance Metrics",
                passed=has_metrics,
                detail=(
                    f"效能度量文件 {len(metrics_files)} 份" if has_metrics else "未找到效能度量数据"
                ),
                severity="low",
                recommendation="" if has_metrics else "建议生成效能度量报告以量化交付质量。",
            )
        )

        # 4. ADR 决策记录
        adr_dir = self.project_dir / "docs" / "adr"
        adr_files = list(adr_dir.glob("*.md")) if adr_dir.is_dir() else []
        # 也检查 output 目录中的 ADR
        adr_output = list(self.output_dir.glob("*-adr-*.md"))
        all_adrs = adr_files + adr_output
        has_adrs = bool(all_adrs)
        checks.append(
            ReleaseReadinessCheck(
                name="Governance: ADR Records",
                passed=has_adrs,
                detail=f"ADR 决策记录 {len(all_adrs)} 份" if has_adrs else "未找到 ADR 决策记录",
                severity="low",
                recommendation="" if has_adrs else "建议为重要架构决策创建 ADR 记录 (docs/adr/)。",
            )
        )

        # 5. 验证规则结果
        validation_files = list(self.output_dir.glob("*-validation-results*.json")) + list(
            self.output_dir.glob("*-validation-results*.md")
        )
        has_validation = bool(validation_files)
        checks.append(
            ReleaseReadinessCheck(
                name="Governance: Validation Results",
                passed=has_validation,
                detail=(
                    f"验证规则结果 {len(validation_files)} 份"
                    if has_validation
                    else "未找到验证规则结果"
                ),
                severity="low",
                recommendation="" if has_validation else "执行验证规则引擎生成结果后重新评估。",
            )
        )

        return checks

    def _extract_regex(self, file_path: Path, pattern: str) -> str:
        if not file_path.exists():
            return ""
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""
