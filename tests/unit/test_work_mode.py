from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.work_mode import detect_work_mode, work_mode_requires_baseline
from super_dev.workflow_state import detect_pipeline_summary


def test_detect_work_mode_defaults_to_new(temp_project_dir: Path):
    assert detect_work_mode(temp_project_dir, {}) == "new"
    assert work_mode_requires_baseline("new") is False


def test_detect_work_mode_uses_baseline_artifacts_for_existing_project(temp_project_dir: Path):
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n", encoding="utf-8"
    )

    assert detect_work_mode(temp_project_dir, {}) == "evolve"
    assert work_mode_requires_baseline("evolve") is True


def test_detect_work_mode_detects_variant_scope_from_contract(temp_project_dir: Path):
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-variant-contract.json").write_text(
        json.dumps({"mode": "variant"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert detect_work_mode(temp_project_dir, {}) == "variant"
    assert work_mode_requires_baseline("variant") is True


def test_detect_work_mode_detects_patch_scope_from_contract(temp_project_dir: Path):
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{temp_project_dir.name}-patch-scope.json").write_text(
        json.dumps({"mode": "patch"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert detect_work_mode(temp_project_dir, {}) == "patch"
    assert work_mode_requires_baseline("patch") is True


@pytest.mark.parametrize("work_mode", ["evolve", "variant", "patch"])
def test_detect_pipeline_summary_blocks_existing_project_without_baseline(
    temp_project_dir: Path,
    work_mode: str,
):
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    superdev_dir = temp_project_dir / ".super-dev"
    superdev_dir.mkdir(parents=True, exist_ok=True)
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": work_mode}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == work_mode
    assert summary["artifacts"]["baseline_required"] is True
    assert summary["artifacts"]["baseline"] is False
    assert summary["workflow_status"] == "missing_baseline"
    assert summary["current_stage_canonical_id"] == "baseline"
    assert any(card["id"] == "existing_project_baseline" for card in summary["scenario_cards"])
