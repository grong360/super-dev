from pathlib import Path

from super_dev.review_state import (
    latest_workflow_snapshot_file,
    load_baseline_confirmation,
    load_recent_workflow_snapshots,
    load_resume_gate,
    load_workflow_state,
    save_baseline_confirmation,
    save_resume_gate,
    save_workflow_state,
    workflow_state_file,
)


def test_load_workflow_state_falls_back_to_latest_snapshot(temp_project_dir: Path) -> None:
    payload = {
        "status": "waiting_preview_confirmation",
        "workflow_mode": "revise",
        "current_step_label": "等待前端预览确认",
        "recommended_command": "前端预览确认，可以继续",
    }
    save_workflow_state(temp_project_dir, payload)
    workflow_state_file(temp_project_dir).write_text("{invalid", encoding="utf-8")

    restored = load_workflow_state(temp_project_dir)

    assert restored is not None
    assert restored["status"] == "waiting_preview_confirmation"
    assert restored["current_step_label"] == "等待前端预览确认"
    assert latest_workflow_snapshot_file(temp_project_dir).exists()


def test_load_recent_workflow_snapshots_returns_latest_first(temp_project_dir: Path) -> None:
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_docs_confirmation",
            "workflow_mode": "revise",
            "current_step_label": "等待三文档确认",
            "recommended_command": "文档确认，可以继续",
        },
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_preview_confirmation",
            "workflow_mode": "revise",
            "current_step_label": "等待前端预览确认",
            "recommended_command": "前端预览确认，可以继续",
        },
    )

    snapshots = load_recent_workflow_snapshots(temp_project_dir, limit=2)

    assert len(snapshots) == 2
    assert snapshots[0]["current_step_label"] == "等待前端预览确认"
    assert snapshots[1]["current_step_label"] == "等待三文档确认"
    assert snapshots[0]["path"].endswith(".json")


def test_save_and_load_resume_gate(temp_project_dir: Path) -> None:
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "current_step_label": "等待恢复点确认",
            "recommended_command": "在宿主里先确认恢复点",
        },
    )

    payload = load_resume_gate(temp_project_dir)

    assert payload is not None
    assert payload["status"] == "pending_review"
    assert payload["current_step_label"] == "等待恢复点确认"




def test_save_and_load_baseline_confirmation(temp_project_dir: Path) -> None:
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "current_step_label": "等待 baseline 确认",
            "recommended_command": "在宿主里先确认 baseline",
        },
    )

    payload = load_baseline_confirmation(temp_project_dir)

    assert payload is not None
    assert payload["status"] == "pending_review"
    assert payload["current_step_label"] == "等待 baseline 确认"
