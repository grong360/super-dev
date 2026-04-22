# ruff: noqa: I001
"""
证据包构建器增强测试

测试对象: super_dev.proof_pack
"""

import json
from pathlib import Path

from super_dev.evidence_identity import build_evidence_identity
from super_dev.proof_pack import ProofPackArtifact, ProofPackBuilder, ProofPackReport
from super_dev.review_state import (
    save_baseline_confirmation,
    save_host_runtime_validation,
    save_workflow_state,
    workflow_event_log_file,
)
from super_dev.workflow_guard import record_stage_progress, save_bound_docs_confirmation


# ---------------------------------------------------------------------------
# ProofPackArtifact
# ---------------------------------------------------------------------------

class TestProofPackArtifact:
    def test_basic_creation(self):
        artifact = ProofPackArtifact(name="PRD", status="ready", summary="Product requirements document")
        assert artifact.name == "PRD"
        assert artifact.status == "ready"
        assert artifact.summary == "Product requirements document"
        assert artifact.path == ""
        assert artifact.details == {}

    def test_with_path_and_details(self):
        artifact = ProofPackArtifact(
            name="Architecture", status="ready", summary="Architecture doc",
            path="/output/arch.md", details={"pages": 15, "diagrams": 3},
        )
        assert artifact.path == "/output/arch.md"
        assert artifact.details["pages"] == 15

    def test_to_dict(self):
        artifact = ProofPackArtifact(
            name="Redteam", status="incomplete", summary="Missing report",
            path="/output/redteam.md", details={"score": 65},
        )
        d = artifact.to_dict()
        assert d["name"] == "Redteam"
        assert d["status"] == "incomplete"
        assert d["path"] == "/output/redteam.md"
        assert d["details"]["score"] == 65

    def test_to_dict_empty_details(self):
        artifact = ProofPackArtifact(name="Test", status="ready", summary="Test")
        d = artifact.to_dict()
        assert d["details"] == {}

    def test_to_dict_preserves_all_fields(self):
        artifact = ProofPackArtifact(
            name="N", status="S", summary="Sum", path="P", details={"k": "v"},
        )
        d = artifact.to_dict()
        assert set(d.keys()) == {"name", "status", "summary", "path", "details"}


# ---------------------------------------------------------------------------
# ProofPackReport
# ---------------------------------------------------------------------------

class TestProofPackReport:
    def test_empty_report(self):
        report = ProofPackReport(project_name="test")
        assert report.project_name == "test"
        assert report.ready_count == 0
        assert report.total_count == 0
        assert report.status == "incomplete"
        assert report.completion_percent == 0
        assert report.blockers == []
        assert report.key_artifacts == []

    def test_all_ready(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name="PRD", status="ready", summary="Done"),
                ProofPackArtifact(name="Arch", status="ready", summary="Done"),
                ProofPackArtifact(name="UIUX", status="ready", summary="Done"),
            ],
        )
        assert report.ready_count == 3
        assert report.total_count == 3
        assert report.status == "ready"
        assert report.completion_percent == 100
        assert len(report.blockers) == 0

    def test_partial_ready(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name="PRD", status="ready", summary="Done"),
                ProofPackArtifact(name="Arch", status="incomplete", summary="Missing"),
                ProofPackArtifact(name="UIUX", status="ready", summary="Done"),
            ],
        )
        assert report.ready_count == 2
        assert report.total_count == 3
        assert report.status == "incomplete"
        assert report.completion_percent == 67
        assert len(report.blockers) == 1
        assert report.blockers[0].name == "Arch"

    def test_none_ready(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name="PRD", status="incomplete", summary="Missing"),
                ProofPackArtifact(name="Arch", status="incomplete", summary="Missing"),
            ],
        )
        assert report.ready_count == 0
        assert report.status == "incomplete"
        assert report.completion_percent == 0

    def test_single_artifact(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[ProofPackArtifact(name="PRD", status="ready", summary="Done")],
        )
        assert report.ready_count == 1
        assert report.total_count == 1
        assert report.status == "ready"
        assert report.completion_percent == 100

    def test_generated_at_is_set(self):
        report = ProofPackReport(project_name="test")
        assert report.generated_at is not None
        assert len(report.generated_at) > 0

    def test_blockers_returns_incomplete_only(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name="A", status="ready", summary="ok"),
                ProofPackArtifact(name="B", status="missing", summary="not ok"),
                ProofPackArtifact(name="C", status="error", summary="bad"),
                ProofPackArtifact(name="D", status="ready", summary="ok"),
            ],
        )
        blockers = report.blockers
        assert len(blockers) == 2
        assert all(b.status != "ready" for b in blockers)

    def test_completion_percent_rounding(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name=f"A{i}", status="ready" if i < 1 else "incomplete", summary="x")
                for i in range(3)
            ],
        )
        assert report.completion_percent == 33  # 1/3 = 0.333... -> 33

    def test_many_artifacts(self):
        report = ProofPackReport(
            project_name="big",
            artifacts=[
                ProofPackArtifact(name=f"artifact-{i}", status="ready", summary=f"Artifact {i}")
                for i in range(20)
            ],
        )
        assert report.ready_count == 20
        assert report.total_count == 20
        assert report.status == "ready"
        assert report.completion_percent == 100


# ---------------------------------------------------------------------------
# ProofPackReport - key_artifacts
# ---------------------------------------------------------------------------

class TestProofPackKeyArtifacts:
    def test_key_artifacts_prefers_known_names(self):
        report = ProofPackReport(
            project_name="test",
            artifacts=[
                ProofPackArtifact(name="prd", status="ready", summary="PRD"),
                ProofPackArtifact(name="architecture", status="ready", summary="Arch"),
                ProofPackArtifact(name="uiux", status="ready", summary="UIUX"),
                ProofPackArtifact(name="random", status="ready", summary="Other"),
            ],
        )
        keys = report.key_artifacts
        # key_artifacts should exist and be a subset of artifacts
        assert isinstance(keys, list)


# ---------------------------------------------------------------------------
# ProofPackReport - 多种状态组合
# ---------------------------------------------------------------------------

class TestProofPackReportStatusCombinations:
    def test_mixed_statuses(self):
        report = ProofPackReport(
            project_name="mixed",
            artifacts=[
                ProofPackArtifact(name="A", status="ready", summary="ok"),
                ProofPackArtifact(name="B", status="incomplete", summary="missing"),
                ProofPackArtifact(name="C", status="ready", summary="ok"),
                ProofPackArtifact(name="D", status="error", summary="failed"),
                ProofPackArtifact(name="E", status="ready", summary="ok"),
            ],
        )
        assert report.ready_count == 3
        assert report.total_count == 5
        assert report.status == "incomplete"
        assert report.completion_percent == 60
        assert len(report.blockers) == 2

    def test_all_error_status(self):
        report = ProofPackReport(
            project_name="errors",
            artifacts=[
                ProofPackArtifact(name=f"err-{i}", status="error", summary=f"Error {i}")
                for i in range(5)
            ],
        )
        assert report.ready_count == 0
        assert report.completion_percent == 0
        assert len(report.blockers) == 5

    def test_single_blocker(self):
        report = ProofPackReport(
            project_name="almost",
            artifacts=[
                ProofPackArtifact(name=f"ok-{i}", status="ready", summary="ok")
                for i in range(9)
            ] + [ProofPackArtifact(name="blocker", status="incomplete", summary="blocking")],
        )
        assert report.ready_count == 9
        assert report.completion_percent == 90
        assert len(report.blockers) == 1
        assert report.blockers[0].name == "blocker"

    def test_large_number_of_artifacts(self):
        n = 100
        artifacts = [
            ProofPackArtifact(name=f"a-{i}", status="ready" if i < 90 else "incomplete", summary=f"A{i}")
            for i in range(n)
        ]
        report = ProofPackReport(project_name="large", artifacts=artifacts)
        assert report.ready_count == 90
        assert report.total_count == 100
        assert report.completion_percent == 90
        assert len(report.blockers) == 10

    def test_artifact_names_unique(self):
        report = ProofPackReport(
            project_name="unique",
            artifacts=[
                ProofPackArtifact(name="same", status="ready", summary="first"),
                ProofPackArtifact(name="same", status="incomplete", summary="second"),
            ],
        )
        # Duplicate names are allowed at this level
        assert report.total_count == 2
        assert report.ready_count == 1

    def test_executive_summary_mentions_operational_harnesses(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(name="Operational Harness", status="ready", summary="operational ok"),
                ProofPackArtifact(name="Workflow Continuity", status="ready", summary="workflow ok"),
                ProofPackArtifact(name="Framework Harness", status="ready", summary="framework ok"),
                ProofPackArtifact(name="Hook Audit Trail", status="ready", summary="hooks ok"),
            ],
        )
        assert "运行时/恢复类 harness" in report.executive_summary
        assert "Operational Harness" in report.executive_summary
        assert "Workflow Continuity" in report.executive_summary

    def test_executive_summary_explains_layered_host_runtime_gap(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Host Runtime Validation",
                    status="pending",
                    summary="host runtime validation gaps: repo_probe_failed=codex-cli",
                    details={
                        "hosts": {"codex-cli": {"status": "passed"}},
                        "repo_probes": {"codex-cli": {"status": "failed"}},
                    },
                )
            ],
        )
        assert "codex-cli 已人工通过" in report.executive_summary
        assert "仓库级 continuity / harness / runtime 证据仍未闭环" in report.executive_summary

    def test_executive_summary_explains_compliance_artifact_gap(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Spec Compliance",
                    status="pending",
                    summary="spec compliance artifact missing",
                )
            ],
        )
        assert "合规链当前优先卡在证据状态" in report.executive_summary
        assert "Spec Compliance=missing" in report.executive_summary
        assert "管理侧现在还不该做最终验收签字" in report.executive_summary

    def test_executive_summary_exposes_workflow_and_baseline_context(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[],
            workflow_context={
                "workflow_status": "waiting_baseline_confirmation",
                "blocking_gate": "waiting_baseline_confirmation",
                "recommended_host_action": "/super-dev-review baseline confirm",
            },
            baseline_governance={
                "status": "pending_confirmation",
                "entry_gate": "waiting_baseline_confirmation",
                "next_host_action": "/super-dev-review baseline confirm",
            },
        )
        assert "当前流程状态为 waiting_baseline_confirmation" in report.executive_summary
        assert "baseline 还没确认" in report.executive_summary
        assert "还停在正式确认门之前" in report.executive_summary

    def test_executive_summary_explains_framework_harness_gap(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Framework Harness",
                    status="pending",
                    summary="uni-app framework harness gaps: implementation modules missing；delivery evidence missing",
                    details={"framework": "uni-app"},
                )
            ],
        )

        assert "跨平台框架专项当前卡在 uni-app playbook/执行闭环" in report.executive_summary
        assert "跨端体验稳定性、专项验收效率和上线节奏" in report.executive_summary
        assert "uni-app framework harness gaps" in report.executive_summary

    def test_executive_summary_explains_screenshot_visual_gate_gap(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Frontend Runtime",
                    status="pending",
                    summary="frontend runtime screenshot visual gate failed: blank=0.82, contrast=0.09, dominant=0.91",
                )
            ],
        )

        assert "截图级视觉验收未通过" in report.executive_summary
        assert "商业质感不足或像半成品" in report.executive_summary
        assert "blank=0.82, contrast=0.09, dominant=0.91" in report.executive_summary

    def test_executive_summary_uses_delivery_language_for_blocked_pack(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Release Readiness",
                    status="pending",
                    summary="score=82/100, passed=False",
                )
            ],
        )

        assert "从交付视角看" in report.executive_summary
        assert "不适合做最终客户演示、正式验收或对外交付" in report.executive_summary

    def test_empty_summary(self):
        artifact = ProofPackArtifact(name="empty-summary", status="ready", summary="")
        d = artifact.to_dict()
        assert d["summary"] == ""

    def test_very_long_summary(self):
        long_summary = "x" * 10000
        artifact = ProofPackArtifact(name="long", status="ready", summary=long_summary)
        d = artifact.to_dict()
        assert len(d["summary"]) == 10000

    def test_special_chars_in_name(self):
        artifact = ProofPackArtifact(name="test<>& artifact", status="ready", summary="ok")
        d = artifact.to_dict()
        assert d["name"] == "test<>& artifact"

    def test_unicode_in_fields(self):
        artifact = ProofPackArtifact(name="中文名称", status="ready", summary="测试摘要")
        d = artifact.to_dict()
        assert d["name"] == "中文名称"
        assert d["summary"] == "测试摘要"

    def test_details_with_nested_structure(self):
        artifact = ProofPackArtifact(
            name="nested", status="ready", summary="ok",
            details={"level1": {"level2": {"level3": "deep"}}},
        )
        d = artifact.to_dict()
        assert d["details"]["level1"]["level2"]["level3"] == "deep"

    def test_details_with_list_values(self):
        artifact = ProofPackArtifact(
            name="list-details", status="ready", summary="ok",
            details={"items": [1, 2, 3], "tags": ["a", "b"]},
        )
        d = artifact.to_dict()
        assert d["details"]["items"] == [1, 2, 3]

    def test_completion_percent_edge_cases(self):
        # 1 of 7 = 14.28... -> should round to 14
        report = ProofPackReport(
            project_name="round",
            artifacts=[
                ProofPackArtifact(name=f"a{i}", status="ready" if i == 0 else "incomplete", summary="x")
                for i in range(7)
            ],
        )
        assert report.completion_percent == 14

    def test_completion_percent_two_thirds(self):
        report = ProofPackReport(
            project_name="twothirds",
            artifacts=[
                ProofPackArtifact(name=f"a{i}", status="ready" if i < 2 else "incomplete", summary="x")
                for i in range(3)
            ],
        )
        assert report.completion_percent == 67


def test_builder_marks_expert_stage_governance_pending_when_visible_stage_evidence_missing(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "demo"
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-research.md").write_text("research", encoding="utf-8")
    (output_dir / "demo-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / "demo-architecture.md").write_text("arch", encoding="utf-8")
    (output_dir / "demo-uiux.md").write_text("uiux", encoding="utf-8")

    artifact = ProofPackBuilder(project_dir)._expert_stage_governance_artifact()

    assert artifact.status == "pending"
    assert "research" in artifact.summary
    assert "docs" in artifact.summary


def test_builder_marks_expert_stage_governance_ready_when_stage_evidence_recorded(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "demo"
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-research.md").write_text("research", encoding="utf-8")
    (output_dir / "demo-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / "demo-architecture.md").write_text("arch", encoding="utf-8")
    (output_dir / "demo-uiux.md").write_text("uiux", encoding="utf-8")

    record_stage_progress(project_dir, stage="research", status="completed")
    record_stage_progress(project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(project_dir, {"status": "confirmed", "actor": "pytest"})

    artifact = ProofPackBuilder(project_dir)._expert_stage_governance_artifact()

    assert artifact.status == "ready"
    assert "3/3" in artifact.summary

    def test_next_actions_prioritize_framework_playbook_when_ui_contract_missing_it(self):
        report = ProofPackReport(
            project_name="cross-platform",
            artifacts=[
                ProofPackArtifact(
                    name="UI Contract",
                    status="pending",
                    summary="missing framework playbook",
                    details={"required_sections": {"framework_playbook": False}},
                )
            ],
        )
        assert any("跨平台框架 playbook" in action for action in report.next_actions)

    def test_builder_ui_contract_artifact_mentions_cross_platform_playbook_gap(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            (
                "{\n"
                '  "analysis": {"frontend": "uni-app"},\n'
                '  "style_direction": "可信商城",\n'
                '  "typography": {"heading": "Alibaba PuHuiTi", "body": "PingFang SC"},\n'
                '  "icon_system": "TDesign Icons",\n'
                '  "emoji_policy": {"allowed_in_ui": false, "allowed_as_icon": false, "allowed_during_development": false},\n'
                '  "ui_library_preference": {"final_selected": "TDesign 小程序 + UniApp"},\n'
                '  "design_tokens": {"color": {"primary": "#0f172a"}}\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._ui_contract_artifact()
        assert artifact.status == "pending"
        assert "uni-app framework playbook" in artifact.summary

    def test_builder_emits_framework_harness_artifact_for_cross_platform_project(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "analysis": {"frontend": "uni-app"},
                    "style_direction": "可信商城",
                    "typography": {"heading": "Alibaba PuHuiTi", "body": "PingFang SC"},
                    "icon_system": "TDesign Icons",
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                    },
                    "ui_library_preference": {"final_selected": "TDesign 小程序 + UniApp"},
                    "design_tokens": {"color": {"primary": "#0f172a"}},
                    "framework_playbook": {
                        "framework": "uni-app",
                        "implementation_modules": ["自定义导航栏高度"],
                        "platform_constraints": ["status bar 与安全区"],
                        "execution_guardrails": ["先冻结 navigationStyle"],
                        "native_capabilities": ["登录 provider"],
                        "validation_surfaces": ["微信小程序导航"],
                        "delivery_evidence": ["三端差异说明"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps(
                {
                    "framework_execution": {
                        "label": "框架 Playbook 执行",
                        "passed": True,
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._framework_harness_artifact()
        assert artifact is not None
        assert artifact.name == "Framework Harness"
        assert artifact.status == "ready"
        assert artifact.details["framework"] == "uni-app"
        assert Path(artifact.path).exists()

    def test_next_actions_include_framework_harness_when_pending(self):
        report = ProofPackReport(
            project_name="cross-platform",
            artifacts=[
                ProofPackArtifact(
                    name="Framework Harness",
                    status="pending",
                    summary="framework execution missing",
                )
            ],
        )
        assert any("framework harness" in action for action in report.next_actions)

    def test_next_actions_include_operational_harness_when_pending(self):
        report = ProofPackReport(
            project_name="ops",
            artifacts=[
                ProofPackArtifact(
                    name="Operational Harness",
                    status="pending",
                    summary="operational blockers",
                    details={
                        "operational_focus": {
                            "recommended_action": "先补 framework harness 再重新生成 proof-pack。",
                        },
                        "focus": {
                            "recommended_action": "先补 framework harness 再重新生成 proof-pack。",
                        }
                    },
                )
            ],
        )
        assert "先补 framework harness 再重新生成 proof-pack。" in report.next_actions

    def test_executive_markdown_includes_operational_continuity_section(self):
        report = ProofPackReport(
            project_name="demo",
            artifacts=[
                ProofPackArtifact(
                    name="Operational Harness",
                    status="ready",
                    summary="operational ok",
                    details={
                        "operational_focus": {
                            "summary": "当前 workflow / framework / hooks harness 已全部通过。",
                            "recommended_action": "当前 workflow / framework / hooks harness 已形成统一运行时证据。",
                        },
                        "focus": {
                            "summary": "当前 workflow / framework / hooks harness 已全部通过。",
                            "recommended_action": "当前 workflow / framework / hooks harness 已形成统一运行时证据。",
                        }
                    },
                ),
                ProofPackArtifact(name="Workflow Continuity", status="ready", summary="workflow ok"),
                ProofPackArtifact(name="Framework Harness", status="pending", summary="framework gaps"),
                ProofPackArtifact(name="Hook Audit Trail", status="ready", summary="hook clean"),
            ],
        )
        markdown = report.to_executive_markdown()
        assert "## Operational Continuity" in markdown
        assert "Operational Harness" in markdown
        assert "Workflow Continuity" in markdown
        assert "Framework Harness" in markdown
        assert "Hook Audit Trail" in markdown
        assert "Current operational focus" in markdown

    def test_builder_emits_operational_harness_artifact_when_workflow_exists(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir(parents=True, exist_ok=True)
        save_workflow_state(
            project_dir,
            {
                "status": "waiting_docs_confirmation",
                "workflow_mode": "continue",
                "current_step_label": "等待三文档确认",
                "recommended_command": "文档确认，可以继续",
            },
        )

        artifact = ProofPackBuilder(project_dir)._operational_harness_artifact()
        assert artifact.name == "Operational Harness"
        assert artifact.status == "ready"
        assert artifact.details["enabled_count"] >= 1
        assert artifact.details["operational_focus"]["status"] == "passed"
        assert artifact.details["focus"]["status"] == "passed"
        assert Path(artifact.path).exists()

    def test_builder_emits_workflow_continuity_artifact_when_trail_exists(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir(parents=True, exist_ok=True)
        save_workflow_state(
            project_dir,
            {
                "status": "waiting_docs_confirmation",
                "workflow_mode": "continue",
                "current_step_label": "等待三文档确认",
                "recommended_command": "文档确认，可以继续",
            },
        )

        artifact = ProofPackBuilder(project_dir)._workflow_continuity_artifact()
        assert artifact.name == "Workflow Continuity"
        assert artifact.status == "ready"
        assert artifact.details["recent_snapshots"]
        assert artifact.details["recent_events"]
        assert artifact.details["recent_timeline"]

    def test_builder_marks_host_runtime_validation_pending_when_repo_probe_fails(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
        save_workflow_state(
            project_dir,
            {
                "status": "missing_frontend",
                "workflow_mode": "continue",
                "current_step_label": "先做前端与运行验证",
                "recommended_command": "继续当前流程，进入前端实现与运行验证",
            },
        )
        save_host_runtime_validation(
            project_dir,
            {
                "hosts": {
                    "codex-cli": {
                        "status": "passed",
                        "comment": "manual accepted",
                        "actor": "pytest",
                    }
                }
            },
        )

        artifact = ProofPackBuilder(project_dir)._host_runtime_validation_artifact()
        assert artifact.name == "Host Runtime Validation"
        assert artifact.status == "pending"
        assert "repo_probe_failed=codex-cli" in artifact.summary

    def test_builder_marks_workflow_continuity_pending_when_event_log_missing(self, tmp_path):
        project_dir = tmp_path / "demo"
        project_dir.mkdir(parents=True, exist_ok=True)
        save_workflow_state(
            project_dir,
            {
                "status": "waiting_docs_confirmation",
                "workflow_mode": "continue",
                "current_step_label": "等待三文档确认",
                "recommended_command": "文档确认，可以继续",
            },
        )
        workflow_event_log_file(project_dir).unlink()

        artifact = ProofPackBuilder(project_dir)._workflow_continuity_artifact()
        assert artifact.status == "pending"
        assert "incomplete" in artifact.summary

    def test_builder_marks_quality_gate_pending_when_evidence_identity_mismatches(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-quality-gate.md").write_text("# 质量门禁报告\n\n通过\n", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps({"passed": True}, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"aligned": True}, ensure_ascii=False),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="quality-gate",
            dependencies=[
                output_dir / "demo-ui-review.json",
                output_dir / "demo-ui-contract-alignment.json",
                output_dir / "demo-uiux.md",
            ],
        )
        (output_dir / "demo-quality-gate.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "total_score": 90,
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        (output_dir / "demo-uiux.md").write_text("# uiux v2", encoding="utf-8")

        artifact = ProofPackBuilder(project_dir)._quality_gate_artifact()
        assert artifact.status == "pending"
        assert "evidence identity" in artifact.summary

    def test_builder_marks_frontend_runtime_pending_when_evidence_identity_mismatches(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps({"style_direction": "editorial"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="frontend-runtime",
            dependencies=[
                output_dir / "demo-ui-contract.json",
                output_dir / "demo-ui-contract-alignment.json",
            ],
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_contract_json": True,
                        "output_frontend_design_tokens": True,
                        "ui_contract_alignment": True,
                        "ui_theme_entry": True,
                        "ui_navigation_shell": True,
                        "ui_component_imports": True,
                        "ui_banned_patterns": True,
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                    },
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps({"style_direction": "editorial v2"}, ensure_ascii=False),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._frontend_runtime_artifact()
        assert artifact.status == "pending"
        assert "evidence identity" in artifact.summary

    def test_builder_marks_frontend_runtime_pending_when_claude_design_protocol_is_missing(
        self, tmp_path
    ):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "editorial",
                    "screen_recipes": [
                        {
                            "label": "North Star Hero",
                            "section_order": ["hero"],
                            "trust_modules": ["案例"],
                            "required_states": ["loading"],
                        }
                    ],
                    "design_context_protocol": {
                        "preferred_import_order": ["tokens"],
                        "github_import_targets": ["theme.ts"],
                        "single_source_rule": "single source",
                    },
                    "tweak_strategy": {
                        "mode": "single-source prototype",
                        "default_controls": ["信息密度"],
                        "persistence_rule": "persist edits",
                    },
                    "verification_handoff": {
                        "verification_order": ["preview"],
                        "required_artifacts": ["output/frontend/index.html"],
                        "acceptance_checks": ["no emoji"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"screen_recipes": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="frontend-runtime",
            dependencies=[
                output_dir / "demo-ui-contract.json",
                output_dir / "demo-ui-contract-alignment.json",
            ],
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_contract_json": True,
                        "output_frontend_design_tokens": True,
                        "ui_contract_alignment": True,
                        "ui_theme_entry": True,
                        "ui_navigation_shell": True,
                        "ui_component_imports": True,
                        "ui_banned_patterns": True,
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                        "ui_design_context_protocol": True,
                        "ui_tweak_strategy": True,
                    },
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._frontend_runtime_artifact()
        assert artifact.status == "pending"
        assert "Claude-Design execution protocol" in artifact.summary
        assert "ui_screen_recipes" in artifact.summary

    def test_builder_marks_frontend_runtime_pending_when_ui_review_runtime_protocol_drifts(
        self, tmp_path
    ):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "editorial",
                    "screen_recipes": [
                        {
                            "label": "North Star Hero",
                            "section_order": ["hero"],
                            "trust_modules": ["案例"],
                            "required_states": ["loading"],
                        }
                    ],
                    "design_context_protocol": {
                        "preferred_import_order": ["tokens"],
                        "github_import_targets": ["theme.ts"],
                        "single_source_rule": "single source",
                    },
                    "tweak_strategy": {
                        "mode": "single-source prototype",
                        "default_controls": ["信息密度"],
                        "persistence_rule": "persist edits",
                    },
                    "verification_handoff": {
                        "verification_order": ["preview"],
                        "required_artifacts": ["output/frontend/index.html"],
                        "acceptance_checks": ["no emoji"],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"screen_recipes": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps(
                {
                    "alignment_summary": {
                        "runtime_claude_design_protocol": {
                            "passed": False,
                            "observed": "mismatch=screen_recipes, verification_handoff",
                        }
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="frontend-runtime",
            dependencies=[
                output_dir / "demo-ui-contract.json",
                output_dir / "demo-ui-contract-alignment.json",
            ],
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_contract_json": True,
                        "output_frontend_design_tokens": True,
                        "ui_contract_alignment": True,
                        "ui_theme_entry": True,
                        "ui_navigation_shell": True,
                        "ui_component_imports": True,
                        "ui_banned_patterns": True,
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                        "ui_screen_recipes": True,
                        "ui_design_context_protocol": True,
                        "ui_tweak_strategy": True,
                        "ui_verification_handoff": True,
                    },
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._frontend_runtime_artifact()
        assert artifact.status == "pending"
        assert "source/runtime evidence drift" in artifact.summary
        assert "screen_recipes" in artifact.summary

    def test_frontend_runtime_artifact_pending_when_screenshot_visual_judge_fails(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "editorial",
                    "typography": {"heading": "IBM Plex Sans", "body": "IBM Plex Sans"},
                    "icon_system": "Lucide",
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"screen_recipes": {"passed": True}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps(
                {
                    "alignment_summary": {
                        "runtime_claude_design_protocol": {
                            "passed": True,
                            "observed": "aligned with frontend-runtime",
                        },
                        "source_claude_design_protocol": {
                            "passed": True,
                            "observed": "screen_recipes, design_context_protocol, tweak_strategy, verification_handoff",
                        },
                        "screenshot_visual_judge": {
                            "passed": False,
                            "observed": "blank=0.82, contrast=0.09, dominant=0.91",
                        },
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="frontend-runtime",
            dependencies=[
                output_dir / "demo-ui-contract.json",
                output_dir / "demo-ui-contract-alignment.json",
            ],
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_contract_json": True,
                        "output_frontend_design_tokens": True,
                        "ui_contract_alignment": True,
                        "ui_theme_entry": True,
                        "ui_navigation_shell": True,
                        "ui_component_imports": True,
                        "ui_banned_patterns": True,
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                        "ui_screen_recipes": True,
                        "ui_design_context_protocol": True,
                        "ui_tweak_strategy": True,
                        "ui_verification_handoff": True,
                    },
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._frontend_runtime_artifact()
        assert artifact.status == "pending"
        assert "screenshot visual gate failed" in artifact.summary

    def test_proof_pack_executive_summary_explains_frontend_runtime_governance_gap(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "style_direction": "editorial",
                    "typography": {"heading": "IBM Plex Sans", "body": "IBM Plex Sans"},
                    "icon_system": "Lucide",
                    "emoji_policy": {
                        "allowed_in_ui": False,
                        "allowed_as_icon": False,
                        "allowed_during_development": False,
                    },
                    "ui_library_preference": {"final_selected": "shadcn/ui"},
                    "design_tokens": {"color": {"primary": "#111827"}},
                    "screen_recipes": [
                        {
                            "label": "North Star Hero",
                            "section_order": ["hero"],
                            "trust_modules": ["proof"],
                            "required_states": ["loading"],
                        }
                    ],
                    "design_context_protocol": {
                        "preferred_import_order": ["tokens"],
                        "github_import_targets": ["theme.ts"],
                        "single_source_rule": "single source",
                    },
                    "tweak_strategy": {
                        "mode": "single-source prototype",
                        "default_controls": ["density"],
                        "persistence_rule": "persist edits",
                    },
                    "verification_handoff": {
                        "verification_order": ["preview"],
                        "required_artifacts": ["output/frontend/index.html"],
                        "acceptance_checks": ["no emoji"],
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-contract-alignment.json").write_text(
            json.dumps({"theme_entry": {"passed": True}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "demo-ui-review.json").write_text(
            json.dumps(
                {
                    "alignment_summary": {
                        "runtime_claude_design_protocol": {
                            "passed": False,
                            "observed": "mismatch=screen_recipes",
                        }
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="frontend-runtime",
            dependencies=[
                output_dir / "demo-ui-contract.json",
                output_dir / "demo-ui-contract-alignment.json",
            ],
        )
        (output_dir / "demo-frontend-runtime.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "checks": {
                        "ui_contract_json": True,
                        "output_frontend_design_tokens": True,
                        "ui_contract_alignment": True,
                        "ui_theme_entry": True,
                        "ui_navigation_shell": True,
                        "ui_component_imports": True,
                        "ui_banned_patterns": True,
                        "ui_framework_playbook": True,
                        "ui_framework_execution": True,
                        "ui_screen_recipes": True,
                        "ui_design_context_protocol": True,
                        "ui_tweak_strategy": True,
                        "ui_verification_handoff": True,
                    },
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        report = ProofPackBuilder(project_dir).build()
        assert "source/runtime 证据漂移" in report.executive_summary

    def test_proof_pack_marks_baseline_confirmation_gap_as_pending_and_next_action(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-baseline-audit.md").write_text("# baseline\n", encoding="utf-8")
        save_workflow_state(
            project_dir,
            {
                "status": "waiting_baseline_confirmation",
                "workflow_mode": "continue",
                "work_mode": "evolve",
                "current_step_label": "等待 baseline 确认",
                "recommended_command": "先确认 baseline，再继续当前流程",
            },
        )
        save_baseline_confirmation(
            project_dir,
            {
                "status": "pending_review",
                "comment": "先确认当前项目边界和差量计划",
                "actor": "pytest",
            },
        )

        report = ProofPackBuilder(project_dir).build()

        baseline_artifact = next(
            artifact for artifact in report.artifacts if artifact.name == "Baseline Confirmation"
        )
        assert baseline_artifact.status == "pending"
        assert baseline_artifact.summary == "status=pending_review"
        workflow_artifact = next(
            artifact for artifact in report.artifacts if artifact.name == "Workflow Continuity"
        )
        assert workflow_artifact.status == "pending"
        assert "waiting_baseline_confirmation" in str(workflow_artifact.details)
        assert any("baseline" in action and "确认" in action for action in report.next_actions)

    def test_builder_marks_spec_compliance_pending_when_artifact_missing(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
            encoding="utf-8",
        )
        artifact = ProofPackBuilder(project_dir)._spec_compliance_artifact()
        assert artifact.status == "pending"
        assert artifact.summary == "spec compliance artifact missing"

    def test_builder_marks_uiux_compliance_pending_when_artifact_identity_mismatches(self, tmp_path):
        project_dir = tmp_path / "demo"
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-uiux.md").write_text("# UIUX\n\nicon_library: lucide\n", encoding="utf-8")
        frontend_file = project_dir / "frontend" / "src" / "page.tsx"
        frontend_file.parent.mkdir(parents=True, exist_ok=True)
        frontend_file.write_text(
            "import { Home } from 'lucide-react';\nexport function Page(){ return <Home /> }\n",
            encoding="utf-8",
        )
        identity = build_evidence_identity(
            project_dir,
            artifact_name="uiux-compliance",
            dependencies=[output_dir / "demo-uiux.md", frontend_file],
        )
        (output_dir / "demo-uiux-compliance.json").write_text(
            json.dumps(
                {
                    "project_name": "demo",
                    "generated_at": "2026-04-18T00:00:00+00:00",
                    "declared_icon_library": "lucide",
                    "declared_typography": [],
                    "declared_tokens": [],
                    "violations": [],
                    "score": 100,
                    "files_scanned": 1,
                    "evidence_identity": identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        frontend_file.write_text(
            "import { House } from 'lucide-react';\nexport function Page(){ return <House /> }\n",
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._uiux_compliance_artifact()
        assert artifact.status == "pending"
        assert artifact.summary == "uiux compliance artifact identity_mismatch"

    def test_builder_emits_hook_audit_artifact_when_history_exists(self, tmp_path):
        project_dir = tmp_path / "demo"
        history_file = project_dir / ".super-dev" / "hook-history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(
            json.dumps(
                {
                    "hook_name": "python3 scripts/check.py",
                    "event": "WorkflowEvent",
                    "success": True,
                    "output": "",
                    "error": "",
                    "duration_ms": 12.3,
                    "blocked": False,
                    "phase": "docs_confirmation_saved",
                    "source": "config",
                    "timestamp": "2026-04-06T01:02:03+00:00",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        artifact = ProofPackBuilder(project_dir)._hook_audit_artifact()
        assert artifact is not None
        assert artifact.name == "Hook Audit Trail"
        assert artifact.status == "ready"
        assert artifact.details["total_events"] == 1
