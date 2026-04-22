from __future__ import annotations

import json
from pathlib import Path

from super_dev.review_state import save_baseline_confirmation, save_resume_gate
from super_dev.workflow_guard import record_stage_progress, save_bound_docs_confirmation
from super_dev.workflow_state import (
    build_host_entry_prompts,
    build_host_flow_probe,
    detect_pipeline_summary,
)


def test_build_host_entry_prompts_supports_seeai_codex():
    payload = build_host_entry_prompts(
        target="codex-cli",
        instruction="继续当前比赛项目",
        supports_slash=False,
        flow_variant="seeai",
    )

    prompts = payload["entry_prompts"]
    assert prompts["cli"].startswith("$super-dev-seeai ")
    assert prompts["fallback"].startswith("super-dev-seeai:")


def test_build_host_entry_prompts_supports_kimi_skill_and_flow_entries():
    payload = build_host_entry_prompts(
        target="kimi-code",
        instruction="继续当前流程",
        supports_slash=False,
        flow_variant="standard",
    )

    assert payload["preferred_entry"] == "skill"
    assert payload["preferred_entry_label"] == "Skill"
    assert payload["entry_labels"]["skill"] == "Skill"
    assert payload["entry_prompts"]["skill"].startswith("/skill:super-dev ")
    assert payload["entry_prompts"]["flow"].startswith("/flow:super-dev ")
    assert payload["entry_prompts"]["fallback"].startswith("super-dev:")


def test_build_host_entry_prompts_supports_droid_headless_resume_entry():
    payload = build_host_entry_prompts(
        target="droid-cli",
        instruction="继续当前流程",
        supports_slash=True,
        flow_variant="standard",
    )

    assert payload["preferred_entry"] == "slash"
    assert payload["entry_labels"]["headless"] == "Headless"
    assert payload["entry_prompts"]["slash"].startswith("/super-dev ")
    assert "droid exec --session-id" in payload["entry_prompts"]["headless"]


def test_build_host_flow_probe_uses_adapter_for_codebuddy_and_droid_cli():
    codebuddy_probe = build_host_flow_probe("codebuddy-cli")
    droid_probe = build_host_flow_probe("droid-cli")

    assert codebuddy_probe["enabled"] is True
    assert "CodeBuddy" in codebuddy_probe["title"]
    assert any("super-dev-seeai" in step for step in codebuddy_probe["steps"])
    assert "SEEAI" in codebuddy_probe["success_signal"]

    assert droid_probe["enabled"] is True
    assert "Droid CLI" in droid_probe["title"]
    assert any("super-dev-seeai" in step for step in droid_probe["steps"])
    assert any("droid exec --session-id" in step for step in droid_probe["steps"])
    assert "SEEAI" in droid_probe["success_signal"]


def test_build_host_flow_probe_preserves_codex_special_probe():
    codex_probe = build_host_flow_probe("codex-cli")

    assert codex_probe["enabled"] is True
    assert codex_probe["title"] == "Codex CLI 双入口同流程验收"
    assert any("$super-dev" in step for step in codex_probe["steps"])


def test_build_host_flow_probe_generates_generic_probe_for_official_hosts():
    qoder_probe = build_host_flow_probe("qoder")
    workbuddy_probe = build_host_flow_probe("workbuddy")

    assert qoder_probe["enabled"] is True
    assert "Qoder" in qoder_probe["title"]
    assert any("/super-dev" in step for step in qoder_probe["steps"])

    assert workbuddy_probe["enabled"] is True
    assert "WorkBuddy" in workbuddy_probe["title"]
    assert any("super-dev: <需求描述>" in step for step in workbuddy_probe["steps"])


def test_detect_pipeline_summary_seeai_skips_preview_gate(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    changes_dir = superdev_dir / "changes" / "demo-change"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text(
        "architecture", encoding="utf-8"
    )
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")
    (changes_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (changes_dir / "tasks.md").write_text("tasks", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-frontend-runtime.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"flow_variant": "seeai"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["flow_variant"] == "seeai"
    assert summary["workflow_status"] == "missing_backend"
    assert "SEEAI" in summary["recommended_command"]


def test_detect_pipeline_summary_includes_expert_governance(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    changes_dir = superdev_dir / "changes" / "demo-change"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text(
        "architecture", encoding="utf-8"
    )
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")

    record_stage_progress(temp_project_dir, stage="research", status="completed")
    record_stage_progress(temp_project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(temp_project_dir, {"status": "confirmed", "actor": "pytest"})

    summary = detect_pipeline_summary(temp_project_dir)

    governance = summary["expert_governance"]
    assert governance["missing_stages"] == []
    assert governance["covered_count"] >= 3
    docs_stage = next(stage for stage in summary["stages"] if stage["canonical_id"] == "docs")
    docs_confirm_stage = next(
        stage for stage in summary["stages"] if stage["canonical_id"] == "docs_confirm"
    )
    assert docs_stage["expert_evidence_status"] == "recorded"
    assert "PM" in docs_stage["recorded_experts"]
    assert docs_confirm_stage["expert_evidence_status"] == "recorded"
    assert "PRODUCT" in docs_confirm_stage["recorded_experts"]


def test_detect_pipeline_summary_blocks_resume_mode_on_resume_gate(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "resume"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "需要先确认恢复点",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "resume"
    assert summary["workflow_status"] == "waiting_resume_gate"
    assert summary["resume_gate"]["status"] == "pending_review"
    assert "恢复点" in summary["recommended_command"]


def test_detect_pipeline_summary_waits_for_baseline_confirmation(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n", encoding="utf-8"
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "需要先确认影响范围",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "evolve"
    assert summary["workflow_status"] == "waiting_baseline_confirmation"
    assert summary["baseline_confirmation"]["status"] == "pending_review"
    assert summary["current_stage_canonical_id"] == "baseline"
    assert "baseline" in summary["recommended_command"]


def test_detect_pipeline_summary_resume_gate_precedes_missing_baseline_for_existing_project(
    temp_project_dir: Path,
):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "variant"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认从哪个阶段恢复",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "variant"
    assert summary["artifacts"]["baseline_required"] is True
    assert summary["artifacts"]["baseline"] is False
    assert summary["workflow_status"] == "waiting_resume_gate"
    assert summary["resume_gate"]["status"] == "pending_review"


def test_detect_pipeline_summary_waits_for_baseline_confirmation_after_audit(
    temp_project_dir: Path,
):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n",
        encoding="utf-8",
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认当前项目边界和差量计划",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "evolve"
    assert summary["artifacts"]["baseline_required"] is True
    assert summary["artifacts"]["baseline"] is True
    assert summary["workflow_status"] == "waiting_baseline_confirmation"
    assert summary["current_stage_canonical_id"] == "baseline"
    assert "baseline 确认" in summary["recommended_command"]
    assert any(card["id"] == "baseline_confirmation" for card in summary["scenario_cards"])
