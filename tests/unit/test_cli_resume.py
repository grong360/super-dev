from types import SimpleNamespace

from super_dev.catalogs import PRIMARY_HOST_TOOL_IDS
from super_dev.cli import SuperDevCLI


def test_resume_stage_resolution_matrix() -> None:
    cli = SuperDevCLI()

    assert cli._resolve_resume_start_stage(None, skip_redteam=False) is None
    assert cli._resolve_resume_start_stage(4, skip_redteam=False) is None
    assert cli._resolve_resume_start_stage(5, skip_redteam=False) == 5
    assert cli._resolve_resume_start_stage(6, skip_redteam=False) == 5
    assert cli._resolve_resume_start_stage(6, skip_redteam=True) == 6
    assert cli._resolve_resume_start_stage(7, skip_redteam=False) == 7
    assert cli._resolve_resume_start_stage(8, skip_redteam=False) == 8
    assert cli._resolve_resume_start_stage(9, skip_redteam=False) == 9
    assert cli._resolve_resume_start_stage(12, skip_redteam=False) == 9


def test_extract_resume_context_prefers_state_and_backfills_from_metrics() -> None:
    cli = SuperDevCLI()
    run_state = {
        "context": {
            "scenario": "0-1",
            "enriched_description": "state-enriched",
        }
    }
    metrics_payload = {
        "stages": [
            {"stage": "1", "details": {"scenario": "1-N+1"}},
            {"stage": "3", "details": {"change_id": "change-from-metrics"}},
        ]
    }

    context = cli._extract_resume_context(run_state=run_state, metrics_payload=metrics_payload)

    assert context["scenario"] == "0-1"
    assert context["enriched_description"] == "state-enriched"
    assert context["change_id"] == "change-from-metrics"


def test_detect_failed_stage_from_metrics_payload() -> None:
    cli = SuperDevCLI()
    payload = {
        "success": False,
        "stages": [
            {"stage": "0", "success": True},
            {"stage": "6", "success": False},
            {"stage": "7", "success": False},
        ],
    }

    assert cli._detect_failed_stage_from_metrics_payload(payload) == 6


def test_adjust_resume_stage_falls_back_when_docs_missing(temp_project_dir) -> None:
    cli = SuperDevCLI()
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    adjusted, reasons = cli._adjust_resume_stage_for_artifacts(
        project_dir=temp_project_dir,
        output_dir=output_dir,
        project_name="resume-demo",
        resume_from_stage=7,
    )

    assert adjusted == 1
    assert reasons


def test_adjust_resume_stage_keeps_stage_when_docs_complete(temp_project_dir) -> None:
    cli = SuperDevCLI()
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    required = cli._stage_one_artifact_paths(output_dir=output_dir, project_name="resume-demo")
    for path in required.values():
        path.write_text("ok", encoding="utf-8")
    (output_dir / "resume-demo-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    change_dir = temp_project_dir / ".super-dev" / "changes" / "resume-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "proposal.md").write_text("# proposal", encoding="utf-8")
    (change_dir / "tasks.md").write_text("# tasks", encoding="utf-8")

    adjusted, reasons = cli._adjust_resume_stage_for_artifacts(
        project_dir=temp_project_dir,
        output_dir=output_dir,
        project_name="resume-demo",
        resume_from_stage=7,
    )

    assert adjusted == 7
    assert reasons == []


def test_write_resume_audit_outputs_json_and_markdown(temp_project_dir) -> None:
    cli = SuperDevCLI()
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_name": "resume-demo",
        "status": "running",
        "run_state_status": "failed",
        "detected_failed_stage": 7,
        "initial_resume_stage": 7,
        "final_resume_stage": 1,
        "planned_skipped_stages": [0],
        "fallback_reasons": ["缺少前置文档产物: prd"],
        "started_at": "2026-03-04T00:00:00+00:00",
        "finished_at": "",
    }

    files = cli._write_resume_audit(
        output_dir=output_dir,
        project_name="resume-demo",
        payload=payload,
    )

    assert files["json"].exists()
    assert files["markdown"].exists()
    markdown = files["markdown"].read_text(encoding="utf-8")
    assert "Resume Audit" in markdown


def test_public_host_targets_prioritize_primary_product_scope() -> None:
    cli = SuperDevCLI()
    integration_manager = SimpleNamespace(
        list_targets=lambda: [SimpleNamespace(name=host_id) for host_id in (
            *PRIMARY_HOST_TOOL_IDS,
            "legacy-host",
        )]
    )

    targets = cli._public_host_targets(integration_manager=integration_manager)

    assert targets == list(PRIMARY_HOST_TOOL_IDS)


def test_public_host_targets_fallback_to_available_targets_when_primary_absent() -> None:
    cli = SuperDevCLI()
    integration_manager = SimpleNamespace(
        list_targets=lambda: [SimpleNamespace(name=host_id) for host_id in ("droid-cli",)]
    )

    targets = cli._public_host_targets(integration_manager=integration_manager)

    assert targets == ["droid-cli"]


def test_resolve_pipeline_stage_selector_supports_aliases() -> None:
    cli = SuperDevCLI()

    assert cli._resolve_pipeline_stage_selector("research") == 0
    assert cli._resolve_pipeline_stage_selector("docs") == 1
    assert cli._resolve_pipeline_stage_selector("prd") == 1
    assert cli._resolve_pipeline_stage_selector("architecture") == 1
    assert cli._resolve_pipeline_stage_selector("uiux") == 1
    assert cli._resolve_pipeline_stage_selector("spec") == 2
    assert cli._resolve_pipeline_stage_selector("frontend") == 3
    assert cli._resolve_pipeline_stage_selector("backend") == 4
    assert cli._resolve_pipeline_stage_selector("quality") == 6
    assert cli._resolve_pipeline_stage_selector("delivery") == 11
    assert cli._resolve_pipeline_stage_selector("12") == 12
    assert cli._resolve_pipeline_stage_selector("unknown") is None


def test_stage_jump_impact_includes_core_messages() -> None:
    cli = SuperDevCLI()
    docs_impact = cli._stage_jump_impact(1)
    frontend_impact = cli._stage_jump_impact(3)
    quality_impact = cli._stage_jump_impact(6)

    assert any("PRD" in item for item in docs_impact)
    assert any("前端实施蓝图" in item for item in frontend_impact)
    assert any("质量" in item or "交付" in item for item in quality_impact)


def test_run_confirm_phase_updates_run_state_for_generic_phase(temp_project_dir, monkeypatch) -> None:
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    cli._write_pipeline_run_state(
        temp_project_dir,
        {
            "status": "failed",
            "pipeline_args": {"description": "demo"},
        },
    )

    code = cli._cmd_run_confirm_phase(
        phase_name="frontend",
        comment="前端预览已通过",
        actor="tester",
    )
    assert code == 0

    run_state = cli._read_pipeline_run_state(temp_project_dir) or {}
    confirmations = run_state.get("phase_confirmations") or {}
    assert "frontend" in confirmations
    assert confirmations["frontend"]["status"] == "confirmed"


def test_run_confirm_phase_initializes_status_when_missing(temp_project_dir, monkeypatch) -> None:
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)

    code = cli._cmd_run_confirm_phase(
        phase_name="frontend",
        comment="前端预览已通过",
        actor="tester",
    )
    assert code == 0

    run_state = cli._read_pipeline_run_state(temp_project_dir) or {}
    assert run_state["status"] == "running"
    assert run_state["status_normalized"] == "running"


def test_run_status_recommendation_treats_missing_scope_status_as_unknown() -> None:
    cli = SuperDevCLI()

    recommendation = cli._run_status_recommendation(
        run_state={"status": "running"},
        docs_state={"status": "confirmed"},
        preview_state={"status": "confirmed"},
        ui_state={"status": "confirmed"},
        architecture_state={"status": "confirmed"},
        quality_state={"status": "confirmed"},
    )

    assert recommendation == "在宿主里继续当前流程，并优先补齐缺失范围与高优先级功能项"


def test_run_status_uses_running_for_existing_confirmation_only_state(
    temp_project_dir, monkeypatch, capsys
) -> None:
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    cli._write_pipeline_run_state(
        temp_project_dir,
        {
            "phase_confirmations": {
                "frontend": {
                    "status": "confirmed",
                    "actor": "tester",
                }
            }
        },
    )

    code = cli._cmd_run_status(type("Args", (), {"json": True})())

    assert code == 0
    output = capsys.readouterr().out
    assert '"status": "running"' in output


def test_status_alias_routes_to_run_status(monkeypatch) -> None:
    cli = SuperDevCLI()
    called = {"status": False}

    def _fake_status(_args):
        called["status"] = True
        return 0

    monkeypatch.setattr(cli, "_cmd_run_status", _fake_status)
    assert cli.run(["status"]) == 0
    assert called["status"] is True


def test_jump_alias_routes_to_run_from_stage(monkeypatch) -> None:
    cli = SuperDevCLI()
    called = {}

    def _fake_jump(*, stage_selector: str, show_impact: bool):
        called["stage_selector"] = stage_selector
        called["show_impact"] = show_impact
        return 0

    monkeypatch.setattr(cli, "_cmd_run_from_stage", _fake_jump)
    assert cli.run(["jump", "frontend"]) == 0
    assert called == {"stage_selector": "frontend", "show_impact": True}


def test_confirm_alias_routes_to_run_confirm_phase(monkeypatch) -> None:
    cli = SuperDevCLI()
    called = {}

    def _fake_confirm(*, phase_name: str, comment: str, actor: str):
        called["phase_name"] = phase_name
        called["comment"] = comment
        called["actor"] = actor
        return 0

    monkeypatch.setattr(cli, "_cmd_run_confirm_phase", _fake_confirm)
    assert cli.run(["confirm", "docs", "--comment", "ok"]) == 0
    assert called == {"phase_name": "docs", "comment": "ok", "actor": "cli-user"}


def test_run_positional_stage_routes_to_targeted_refresh(monkeypatch) -> None:
    cli = SuperDevCLI()
    called = {"target": ""}

    def _fake_refresh(target: str):
        called["target"] = target
        return 0

    monkeypatch.setattr(cli, "_cmd_run_targeted_refresh", _fake_refresh)
    assert cli.run(["run", "research"]) == 0
    assert called["target"] == "research"
