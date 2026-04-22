from super_dev.host_adapters import (
    SpecialAdapterContext,
    build_special_usage_profile,
    get_adapter_mode_override,
    get_competition_smoke_extra_steps,
    get_pass_criteria,
    get_resume_checklist,
    get_runtime_checklist,
    get_special_install_surfaces,
    render_manual_install_guidance,
)


def test_workbuddy_special_adapter_builds_manual_usage_profile():
    profile = build_special_usage_profile(
        SpecialAdapterContext(
            target="workbuddy",
            category="ide",
            usage_location="WorkBuddy 当前任务会话",
            usage_notes=("note-a",),
        )
    )

    assert profile is not None
    assert profile["usage_mode"] == "manual-workbench-skill"
    assert profile["trigger_context"] == "WorkBuddy 当前任务/对话会话"
    assert profile["entry_variants"][1]["entry"] == "super-dev-seeai: <需求描述>"
    assert "WorkBuddy" in profile["notes"]


def test_droid_cli_uses_host_profile_instead_of_manual_install_guidance():
    payload = render_manual_install_guidance(
        host_id="droid-cli",
        command_name="setup",
        docs=["https://docs.factory.ai/cli/configuration/agents-md"],
    )

    assert payload is None


def test_codebuddy_special_adapter_exposes_competition_steps_and_surfaces():
    steps = get_competition_smoke_extra_steps("codebuddy")
    surfaces = get_special_install_surfaces("codebuddy")

    assert any("P0/P1/P2" in step for step in steps)
    assert any("12 分钟内先跑出首个可见界面" in step for step in steps)
    assert surfaces is not None
    assert ".codebuddy/commands/super-dev-seeai.md" in surfaces["optional_project_surfaces"]
    assert "~/.codebuddy/skills/super-dev-seeai/SKILL.md" in surfaces["official_user_surfaces"]


def test_workbuddy_adapter_mode_override_is_skill_only():
    assert get_adapter_mode_override("workbuddy") == "skill-only"
    assert get_adapter_mode_override("claude-code") == ""


def test_kimi_and_trae_solo_special_adapters_expose_official_entry_models():
    kimi = build_special_usage_profile(
        SpecialAdapterContext(
            target="kimi-code",
            category="cli",
            usage_location="Kimi Code 当前项目会话",
            usage_notes=("note-a",),
        )
    )
    trae_solo = build_special_usage_profile(
        SpecialAdapterContext(
            target="trae-solo",
            category="ide",
            usage_location="Trae SOLO 当前 workspace",
            usage_notes=("note-a",),
        )
    )

    assert kimi is not None
    assert kimi["usage_mode"] == "agents-skills-native-resume"
    assert any(item["entry"] == "/skill:super-dev <需求描述>" for item in kimi["entry_variants"])
    assert "kimi --continue" in kimi["notes"]

    assert trae_solo is not None
    assert trae_solo["usage_mode"] == "workspace-rules-slash-skill"
    assert trae_solo["trigger_command"] == "/super-dev <需求描述>"
    assert any(item["entry"] == "/super-dev-seeai" for item in trae_solo["entry_variants"])


def test_kimi_special_adapter_treats_dot_kimi_agents_as_compatibility_surface():
    surfaces = get_special_install_surfaces("kimi-code")

    assert surfaces is not None
    assert "AGENTS.md" in surfaces["official_project_surfaces"]
    assert ".kimi/skills/super-dev/SKILL.md" in surfaces["optional_project_surfaces"]
    assert "~/.kimi/skills/super-dev/SKILL.md" in surfaces["optional_user_surfaces"]
    assert ".kimi/AGENTS.md" not in surfaces["official_project_surfaces"]
    assert ".kimi/AGENTS.md" in surfaces["observed_compatibility_surfaces"]


def test_runtime_validation_helpers_expose_structured_metadata():
    for host_id in (
        "codebuddy-cli",
        "codebuddy",
        "droid-cli",
        "kimi-code",
        "trae-solo",
        "trae-solocn",
        "workbuddy",
    ):
        runtime_checklist = get_runtime_checklist(host_id)
        pass_criteria = get_pass_criteria(host_id)
        resume_checklist = get_resume_checklist(host_id)

        assert runtime_checklist
        assert pass_criteria
        assert resume_checklist
        assert all(isinstance(item, str) for item in runtime_checklist)
        assert all(isinstance(item, str) for item in pass_criteria)
        assert all(isinstance(item, str) for item in resume_checklist)


def test_runtime_validation_payload_is_present_in_usage_profiles():
    profile = build_special_usage_profile(
        SpecialAdapterContext(
            target="droid-cli",
            category="cli",
            usage_location="Droid CLI 当前项目会话",
            usage_notes=("note-a",),
        )
    )

    assert profile is not None
    assert profile["usage_mode"] == "factory-slash-and-skill"
    assert profile["trigger_command"] == "/super-dev <需求描述>"
    runtime_validation = profile["runtime_validation"]
    assert runtime_validation["runtime_checklist"]
    assert runtime_validation["pass_criteria"]
    assert runtime_validation["resume_checklist"]
    assert any(
        "12 分钟内先跑出第一个可见界面" in item
        for item in runtime_validation["runtime_checklist"]
    )
    assert any("droid exec --session-id" in item for item in runtime_validation["resume_checklist"])
