from pathlib import Path

from super_dev.host_diagnostics import build_host_injection_closure


def _surface_sets(*, default_paths: list[Path], optional_user_paths: list[Path]) -> dict[str, list[Path]]:
    return {
        "official_project": default_paths,
        "official_user": [],
        "optional_project": [],
        "optional_user": optional_user_paths,
        "compatibility": [],
        "official_skill": [],
        "optional_skill": [],
        "compatibility_skill": [],
        "required_slash": [],
        "optional_slash": [],
        "compatibility_slash": [],
    }


def test_build_host_injection_closure_marks_project_first_ready_with_opt_in_available(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    project_surface.write_text("# agents\n", encoding="utf-8")
    optional_user_surface = tmp_path / "user-command.md"

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[optional_user_surface],
        ),
    )

    assert closure["status"] == "project_default_ready_with_user_opt_in_available"
    assert closure["project_default_ready"] is True
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["user_surface_opt_in_available"] is True
    assert closure["explicit_user_surfaces_ready"] is False
    assert closure["opt_in_flag"] == "--with-user-surfaces"
    assert str(optional_user_surface) in closure["missing_optional_user_surfaces"]
    assert closure["competition_project_surfaces_ready"] is False
    assert closure["missing_managed_competition_project_surfaces"] == []


def test_build_host_injection_closure_marks_explicit_user_surfaces_ready(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    optional_user_surface = tmp_path / "user-command.md"
    project_surface.write_text("# agents\n", encoding="utf-8")
    optional_user_surface.write_text("# cmd\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[optional_user_surface],
        ),
    )

    assert closure["status"] == "project_default_ready_with_user_opt_in_enabled"
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["explicit_user_surfaces_ready"] is True
    assert closure["missing_optional_user_surfaces"] == []


def test_build_host_injection_closure_marks_missing_competition_project_surfaces(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    competition_surface = tmp_path / ".qoder" / "skills" / "super-dev-seeai" / "SKILL.md"
    project_surface.write_text("# agents\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[],
        ),
        managed_competition_project_paths=[competition_surface],
    )

    assert closure["competition_project_surfaces_ready"] is False
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert str(competition_surface) in closure["missing_managed_competition_project_surfaces"]
    assert closure["status"].endswith("_competition_incomplete")


def test_build_host_injection_closure_keeps_standard_ready_when_competition_user_surface_missing(
    tmp_path: Path,
) -> None:
    user_skill_surface = tmp_path / ".workbuddy" / "skills" / "super-dev" / "SKILL.md"
    user_skill_surface.parent.mkdir(parents=True, exist_ok=True)
    user_skill_surface.write_text("# skill\n", encoding="utf-8")
    seeai_user_surface = tmp_path / ".workbuddy" / "skills" / "super-dev-seeai" / "SKILL.md"

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[],
            optional_user_paths=[],
        )
        | {
            "official_user": [user_skill_surface],
            "official_skill": [],
        },
        managed_competition_user_paths=[seeai_user_surface],
    )

    assert closure["project_default_ready"] is True
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert closure["competition_user_surfaces_ready"] is False
    assert str(seeai_user_surface) in closure["missing_managed_competition_user_surfaces"]
