from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..baseline_governance import inspect_baseline_governance
from ..compliance_governance import collect_compliance_governance_signal
from ..host_runtime_governance import collect_layered_runtime_governance_gap
from ..review_state import (
    load_host_runtime_validation,
)


def _severity_weight(level: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level, 2)


@dataclass
class ProductAuditFinding:
    owner: str
    category: str
    severity: str
    title: str
    summary: str
    recommendation: str
    file_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "owner": self.owner,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "file_refs": list(self.file_refs),
        }


@dataclass
class ProductAuditReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    strengths: list[str] = field(default_factory=list)
    findings: list[ProductAuditFinding] = field(default_factory=list)

    @property
    def score(self) -> int:
        baseline = 100
        penalty = sum(_severity_weight(item.severity) * 6 for item in self.findings)
        return max(0, baseline - penalty)

    @property
    def status(self) -> str:
        if any(item.severity == "critical" for item in self.findings):
            return "revision_required"
        if self.score >= 85:
            return "ready"
        if self.score >= 70:
            return "attention"
        return "revision_required"

    @property
    def summary(self) -> str:
        if not self.findings:
            return "未发现阻断级产品或交付闭环问题。"
        critical = sum(1 for item in self.findings if item.severity == "critical")
        high = sum(1 for item in self.findings if item.severity == "high")
        return (
            f"共识别 {len(self.findings)} 项问题，其中 critical {critical} 项、high {high} 项。"
            "优先先修复会影响首次上手、审查闭环和交付可信度的问题。"
        )

    @property
    def next_actions(self) -> list[str]:
        actions: list[str] = []
        for finding in sorted(
            self.findings, key=lambda item: _severity_weight(item.severity), reverse=True
        )[:5]:
            actions.append(f"[{finding.owner}/{finding.severity}] {finding.recommendation}")
        if not actions:
            actions.append("当前产品审查通过，可继续执行质量门禁与交付流程。")
        return actions

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "status": self.status,
            "score": self.score,
            "summary": self.summary,
            "strengths": list(self.strengths),
            "next_actions": list(self.next_actions),
            "findings": [item.to_dict() for item in self.findings],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Product Audit Report",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Status: `{self.status}`",
            f"- Score: {self.score}/100",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Strengths",
            "",
        ]
        if self.strengths:
            for strength in self.strengths:
                lines.append(f"- {strength}")
        else:
            lines.append("- 暂无可归纳的明显优势。")
        lines.extend(["", "## Findings", ""])
        if self.findings:
            for idx, finding in enumerate(self.findings, start=1):
                lines.append(f"### {idx}. [{finding.severity.upper()}] {finding.title}")
                lines.append("")
                lines.append(f"- Owner: `{finding.owner}`")
                lines.append(f"- Category: `{finding.category}`")
                lines.append(f"- Summary: {finding.summary}")
                lines.append(f"- Recommendation: {finding.recommendation}")
                if finding.file_refs:
                    lines.append(f"- Files: {', '.join(finding.file_refs)}")
                lines.append("")
        else:
            lines.append("- None")
            lines.append("")
        lines.extend(["## Next Actions", ""])
        for action in self.next_actions:
            lines.append(f"- {action}")
        lines.append("")
        return "\n".join(lines)


class ProductAuditBuilder:
    DOC_MARKERS = {
        "docs/QUICKSTART.md": ["super-dev update", "/super-dev 你的需求", "继续当前流程"],
        "docs/HOST_USAGE_GUIDE.md": ["/super-dev 你的需求", "继续当前流程", "现在下一步是什么"],
        "docs/WORKFLOW_GUIDE.md": [
            "super-dev update",
            "/super-dev 做一个企业级项目管理系统",
            "evolve / variant / patch",
        ],
        "docs/PRODUCT_AUDIT.md": ["super-dev product-audit", "proof-pack", "release readiness"],
    }

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = self.project_dir.name
        self.is_super_dev_repo = (self.project_dir / "super_dev" / "cli.py").exists()

    def build(self) -> ProductAuditReport:
        report = ProductAuditReport(project_name=self.project_name)
        report.strengths.extend(self._collect_strengths())
        report.findings.extend(self._check_required_docs())
        report.findings.extend(self._check_readme_doc_links())
        report.findings.extend(self._check_closure_artifacts())
        if self.is_super_dev_repo:
            report.findings.extend(self._check_product_agent_surface())
            report.findings.extend(self._check_oversized_modules())
        return report

    def write(self, report: ProductAuditReport) -> dict[str, Path]:
        base = self.output_dir / f"{self.project_name}-product-audit"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _collect_strengths(self) -> list[str]:
        strengths: list[str] = []
        if (self.project_dir / "docs" / "QUICKSTART.md").exists():
            strengths.append("已提供 Quickstart 入口，具备最短路径引导基础。")
        if (self.project_dir / "docs" / "WORKFLOW_GUIDE.md").exists():
            strengths.append("已有显式 review/confirm/resume 机制，说明流程门禁已成形。")
        if any(self.output_dir.glob("*-proof-pack.json")):
            strengths.append("已有 proof-pack 交付证据包，说明项目具备交付审计基础。")
        if any(self.output_dir.glob("*-release-readiness.json")):
            strengths.append("已有 release readiness 报告，说明项目具备发布评分基础。")
        if any(self.output_dir.glob("*-feature-checklist.json")):
            strengths.append("已有 feature checklist，说明项目具备范围覆盖审计基础。")
        return strengths

    def _check_required_docs(self) -> list[ProductAuditFinding]:
        findings: list[ProductAuditFinding] = []
        for relative_path, markers in self.DOC_MARKERS.items():
            file_path = self.project_dir / relative_path
            if not file_path.exists():
                findings.append(
                    ProductAuditFinding(
                        owner="PRODUCT",
                        category="documentation",
                        severity="high",
                        title=f"缺少关键产品文档：{relative_path}",
                        summary="首次上手、审查闭环或产品审查缺少显式说明，会让用户只能靠猜。",
                        recommendation=f"补齐 `{relative_path}` 并明确最短路径、成功标志和失败恢复方式。",
                        file_refs=[relative_path],
                    )
                )
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            missing_markers = [marker for marker in markers if marker not in text]
            if missing_markers:
                findings.append(
                    ProductAuditFinding(
                        owner="UX",
                        category="interaction",
                        severity="medium",
                        title=f"关键文档缺少可执行标记：{relative_path}",
                        summary=f"文档存在，但缺少关键引导标记：{', '.join(missing_markers)}。",
                        recommendation="补齐最短路径命令、成功标志和失败恢复命令，减少用户摸索成本。",
                        file_refs=[relative_path],
                    )
                )
        return findings

    def _check_readme_doc_links(self) -> list[ProductAuditFinding]:
        findings: list[ProductAuditFinding] = []
        pattern = re.compile(r"\[[^\]]+\]\((docs/[^)]+)\)")
        for readme_name in ("README.md", "README_EN.md"):
            file_path = self.project_dir / readme_name
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            missing_links = []
            for target in pattern.findall(text):
                target_path = self.project_dir / target
                if not target_path.exists():
                    missing_links.append(target)
            if missing_links:
                findings.append(
                    ProductAuditFinding(
                        owner="PRODUCT",
                        category="documentation",
                        severity="high",
                        title=f"{readme_name} 存在失效文档链接",
                        summary=f"README 对外暴露了不存在的文档：{', '.join(missing_links)}。",
                        recommendation="补齐缺失文档或移除失效链接，避免用户在关键入口处遇到断链。",
                        file_refs=[readme_name, *missing_links],
                    )
                )
        return findings

    def _check_closure_artifacts(self) -> list[ProductAuditFinding]:
        findings: list[ProductAuditFinding] = []
        baseline = inspect_baseline_governance(self.project_dir, output_dir=self.output_dir)
        runtime_payload = load_host_runtime_validation(self.project_dir) or {}
        runtime_hosts = runtime_payload.get("hosts", {}) if isinstance(runtime_payload, dict) else {}
        has_runtime_state = isinstance(runtime_hosts, dict) and bool(runtime_hosts)
        expected = {
            "feature coverage": any(self.output_dir.glob("*-feature-checklist.json")),
            "quality gate": any(self.output_dir.glob("*-quality-gate.md")),
            "proof pack": any(self.output_dir.glob("*-proof-pack.json")),
            "release readiness": any(self.output_dir.glob("*-release-readiness.json")),
        }
        missing = [name for name, present in expected.items() if not present]
        if missing:
            findings.append(
                ProductAuditFinding(
                    owner="DELIVERY",
                    category="closure",
                    severity="medium",
                    title="交付闭环证据不完整",
                    summary=f"当前仓库缺少关键闭环证据：{', '.join(missing)}。",
                    recommendation="补齐范围覆盖、质量门禁、proof-pack 和发布就绪度证据，让审查结果可持续复用。",
                    file_refs=["output/"],
                )
            )
        if baseline.get("status") == "missing_audit":
            findings.append(
                ProductAuditFinding(
                    owner="PRODUCT",
                    category="baseline-governance",
                    severity="high",
                    title="已有项目模式缺少 baseline audit",
                    summary="当前仓库处于已有项目迭代/派生/修复模式，但没有看到 baseline audit，后续差量规划容易脱离现状。",
                    recommendation="先扫描当前项目的功能、架构、UI 和约束，生成 baseline audit 后再继续三文档与实现。",
                    file_refs=["output/"],
                )
            )
        elif baseline.get("required") and baseline.get("status") != "confirmed":
            findings.append(
                ProductAuditFinding(
                    owner="PRODUCT",
                    category="baseline-governance",
                    severity="high",
                    title="已有项目 baseline 尚未确认",
                    summary=(
                        "已有项目模式已经完成 baseline 扫描，但 baseline confirmation 仍未闭环："
                        + str(baseline.get("confirmation_status") or baseline.get("status"))
                        + "。"
                    ),
                    recommendation="先执行 `super-dev review baseline --status confirmed`，确认当前项目边界、复用面与差量计划后再继续后续阶段。",
                    file_refs=[
                        "output/",
                        ".super-dev/review-state/baseline-confirmation.json",
                    ],
                )
            )
        compliance_signal = collect_compliance_governance_signal(self.project_dir, output_dir=self.output_dir)
        source_issues = compliance_signal.get("source_issues", [])
        if isinstance(source_issues, list) and source_issues:
            findings.append(
                ProductAuditFinding(
                    owner="DELIVERY",
                    category="compliance-governance",
                    severity="high",
                    title="合规链证据状态未闭环",
                    summary=str(compliance_signal.get("summary", "")).strip()
                    or "合规链 artifact 仍有缺失或 identity 失配。",
                    recommendation=(
                        "先补齐或刷新 spec / architecture / uiux compliance artifacts，"
                        "确保 JSON 证据存在、可读且与当前仓库输入一致，再重新执行 product audit。"
                    ),
                    file_refs=["output/"],
                )
            )
        content_issues = compliance_signal.get("content_issues", [])
        if isinstance(content_issues, list) and content_issues:
            findings.append(
                ProductAuditFinding(
                    owner="PRODUCT",
                    category="compliance-governance",
                    severity="medium",
                    title="合规链内容仍未达标",
                    summary=str(compliance_signal.get("summary", "")).strip()
                    or "合规链证据已齐，但内容仍未达标。",
                    recommendation=(
                        "优先修复 PRD traceability、architecture drift 或 UIUX 违例，"
                        "再重新执行 quality gate / proof-pack / release readiness。"
                    ),
                    file_refs=["output/"],
                )
            )
        if not any(self.output_dir.glob("*-host-runtime-validation.json")) and not has_runtime_state:
            findings.append(
                ProductAuditFinding(
                    owner="QA",
                    category="runtime-validation",
                    severity="medium",
                    title="缺少宿主真人运行验证记录",
                    summary="当前仓库没有看到 host runtime validation 证据，说明接入效果可能只停留在静态配置层。",
                    recommendation="补充真人验收记录，确保宿主真的会先进入 research 并遵守确认门。",
                    file_refs=["output/"],
                )
            )
            return findings

        if not isinstance(runtime_hosts, dict):
            return findings

        governance_gap = collect_layered_runtime_governance_gap(self.project_dir)
        layered_gap_hosts = governance_gap.get("impacted_hosts", []) if governance_gap else []
        if layered_gap_hosts:
            findings.append(
                ProductAuditFinding(
                    owner="QA",
                    category="runtime-validation",
                    severity="high",
                    title="宿主 runtime 与交付闭环证据脱节",
                    summary=(
                        "以下宿主已人工通过 runtime validation，但仓库级 continuity / harness / runtime 证据仍未闭环："
                        + "、".join(layered_gap_hosts[:3])
                        + "。"
                    ),
                    recommendation=(
                        "优先补齐 workflow continuity、framework/operational harness 与 frontend runtime 证据，"
                        "再重新执行宿主 runtime validation 与 product audit。"
                    ),
                    file_refs=[
                        ".super-dev/review-state/host-runtime-validation.json",
                        ".super-dev/workflow-state.json",
                        "output/",
                    ],
                )
            )
        return findings

    def _check_product_agent_surface(self) -> list[ProductAuditFinding]:
        findings: list[ProductAuditFinding] = []
        try:
            from ..experts import list_experts

            expert_ids = {item["id"] for item in list_experts()}
        except Exception:
            expert_ids = set()
        if "PRODUCT" not in expert_ids:
            findings.append(
                ProductAuditFinding(
                    owner="PRODUCT",
                    category="agent-system",
                    severity="critical",
                    title="缺少顶级 Product Agent",
                    summary="当前专家体系缺少站在全局产品视角汇总审查、串联交互与交付闭环的顶级角色。",
                    recommendation="增加 `PRODUCT` 角色，并让其参与首次上手、产品审查和功能缺口识别。",
                    file_refs=[
                        "super_dev/experts/service.py",
                        "super_dev/orchestrator/experts.py",
                        "super_dev/cli.py",
                    ],
                )
            )
        return findings

    def _check_oversized_modules(self) -> list[ProductAuditFinding]:
        findings: list[ProductAuditFinding] = []
        oversized: list[tuple[str, int]] = []
        for relative in (
            "super_dev/cli.py",
            "super_dev/creators/document_generator.py",
            "super_dev/integrations/manager.py",
        ):
            file_path = self.project_dir / relative
            if not file_path.exists():
                continue
            line_count = sum(1 for _ in file_path.open(encoding="utf-8", errors="ignore"))
            if line_count >= 2500:
                oversized.append((relative, line_count))
        for relative, line_count in oversized:
            severity = "high" if line_count >= 5000 else "medium"
            findings.append(
                ProductAuditFinding(
                    owner="CODE",
                    category="maintainability",
                    severity=severity,
                    title=f"核心模块过大：{relative}",
                    summary=f"{relative} 当前约 {line_count} 行，职责边界过宽，会拖慢产品迭代和故障定位。",
                    recommendation="按命令路由、宿主适配、报告生成、状态机等维度拆分模块，先削减高频改动文件的复杂度。",
                    file_refs=[relative],
                )
            )
        return findings
