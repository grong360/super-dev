from pathlib import Path

from super_dev.host_experience_profile import (
    _EXPERIENCE_PROFILES,
    build_host_competition_first_prompt,
    build_host_experience_profile,
    build_host_official_pass_criteria,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from super_dev.host_registry import list_host_ids
from super_dev.host_usage_profile import serialize_host_usage_profile
from super_dev.integrations.manager import IntegrationManager


def test_build_host_resume_guidance_exposes_kimi_native_resume_and_entries():
    lines = build_host_resume_guidance("kimi-code")

    assert any("优先入口:" in item and "/skill:super-dev" in item for item in lines)
    assert any("原生恢复:" in item and "kimi --continue" in item for item in lines)
    assert any("原生 continue / resume" in item for item in lines)


def test_build_host_resume_guidance_exposes_droid_factory_session_language():
    lines = build_host_resume_guidance("droid-cli")

    assert any("优先入口:" in item and "/super-dev 你的需求" in item for item in lines)
    assert any("原生恢复:" in item and "droid exec --session-id <id>" in item for item in lines)
    assert any("Factory session" in item for item in lines)


def test_build_host_start_playbook_exposes_kimi_skill_first_guidance():
    lines = build_host_start_playbook("kimi-code")

    assert any("/skill:super-dev" in item for item in lines)
    assert any("不要先用普通聊天" in item for item in lines)


def test_build_host_standard_first_prompt_prefers_kimi_skill_entry():
    assert build_host_standard_first_prompt("kimi-code") == "/skill:super-dev 你的需求"


def test_build_host_competition_first_prompt_prefers_seeai_entry():
    assert build_host_competition_first_prompt("trae-solocn") == "super-dev-seeai: 比赛需求"


def test_build_host_competition_first_prompt_prefers_antigravity_slash_entry():
    assert build_host_competition_first_prompt("antigravity") == "/super-dev-seeai 比赛需求"


def test_build_host_standard_first_prompt_prefers_qoder_slash_entry():
    assert build_host_standard_first_prompt("qoder-cli") == "/super-dev 你的需求"


def test_build_host_start_playbook_exposes_gemini_cli_specific_guidance():
    lines = build_host_start_playbook("gemini-cli")

    assert any("Gemini CLI" in item for item in lines)
    assert any("/super-dev" in item for item in lines)


def test_build_host_start_playbook_exposes_copilot_agents_and_instructions_context():
    lines = build_host_start_playbook("copilot-cli")

    assert any("AGENTS.md" in item for item in lines)
    assert any("copilot-instructions" in item for item in lines)


def test_build_host_standard_first_prompt_prefers_vscode_copilot_text_entry():
    assert build_host_standard_first_prompt("vscode-copilot") == "super-dev: 你的需求"


def test_build_host_repair_guidance_exposes_droid_factory_repair_priority():
    guidance = build_host_repair_guidance("droid-cli")

    assert "Factory session" in guidance
    assert "/super-dev" in guidance
    assert "legacy" in guidance


def test_build_host_official_workflow_checks_exposes_kimi_skill_chain():
    lines = build_host_official_workflow_checks(
        "kimi-code",
        {
            "host": "Kimi Code",
            "host_protocol_mode": "official-agents-entry",
            "official_project_surfaces": ["AGENTS.md"],
            "official_user_surfaces": [],
            "optional_project_surfaces": [".kimi/skills/super-dev/SKILL.md"],
            "optional_user_surfaces": ["~/.kimi/skills/super-dev/SKILL.md"],
        },
    )

    assert any("official-agents-entry" in item for item in lines)
    assert any("AGENTS.md" in item for item in lines)
    assert any("/skill:super-dev" in item for item in lines)
    assert any("kimi --session <id>" in item for item in lines)


def test_build_host_official_workflow_checks_exposes_qwen_agents_and_resume_semantics():
    lines = build_host_official_workflow_checks(
        "qwen-code",
        {
            "host": "Qwen Code",
            "host_protocol_mode": "official-context",
            "official_project_surfaces": [
                "QWEN.md",
                ".qwen/commands/super-dev.md",
                ".qwen/skills/super-dev/SKILL.md",
                ".qwen/agents/super-dev.md",
            ],
            "official_user_surfaces": [
                "~/.qwen/QWEN.md",
                "~/.qwen/skills/super-dev/SKILL.md",
                "~/.qwen/agents/super-dev.md",
            ],
        },
    )

    assert any("QWEN.md" in item for item in lines)
    assert any(".qwen/agents/super-dev.md" in item for item in lines)
    assert any("/resume" in item for item in lines)
    assert any("/restore" in item and "checkpoint" in item for item in lines)


def test_build_host_official_workflow_checks_exposes_trae_workspace_contract():
    lines = build_host_official_workflow_checks(
        "trae",
        {
            "host": "Trae IDE",
            "host_protocol_mode": "official-context",
            "official_project_surfaces": [".trae/project_rules.md", ".trae/rules.md"],
            "official_user_surfaces": [],
        },
    )

    assert any("official-context" in item for item in lines)
    assert any(".trae/project_rules.md" in item for item in lines)
    assert any("Trae Agent Chat" in item for item in lines)


def test_build_host_official_workflow_checks_exposes_codebuddy_cli_contract():
    lines = build_host_official_workflow_checks(
        "codebuddy-cli",
        {
            "host": "CodeBuddy CLI",
            "host_protocol_mode": "official-commands-skills",
            "official_project_surfaces": ["CODEBUDDY.md", ".codebuddy/commands/super-dev.md"],
            "official_user_surfaces": [".codebuddy/skills/super-dev/SKILL.md"],
        },
    )

    assert any("official-commands-skills" in item for item in lines)
    assert any("CodeBuddy CLI" in item for item in lines)
    assert any("/super-dev" in item for item in lines)


def test_build_host_official_workflow_checks_exposes_workbuddy_mcp_contract():
    lines = build_host_official_workflow_checks(
        "workbuddy",
        {
            "host": "WorkBuddy",
            "host_protocol_mode": "manual-task-workbench-mcp",
            "official_project_surfaces": [],
            "official_user_surfaces": [],
            "optional_user_surfaces": ["~/.workbuddy/skills/super-dev/SKILL.md"],
            "managed_competition_user_surfaces": ["~/.workbuddy/skills/super-dev-seeai/SKILL.md"],
        },
    )

    assert any("manual-task-workbench-mcp" in item for item in lines)
    assert any("WorkBuddy" in item for item in lines)
    assert any("MCP" in item for item in lines)
    assert any("SEEAI 用户级补充面" in item for item in lines)


def test_build_host_official_workflow_checks_exposes_qoder_agents_as_enhancement_surface():
    lines = build_host_official_workflow_checks(
        "qoder-cli",
        {
            "host": "Qoder CLI",
            "host_protocol_mode": "official-commands-rules-skills",
            "official_project_surfaces": [
                "AGENTS.md",
                ".qoder/rules/super-dev.md",
                ".qoder/commands/super-dev.md",
                ".qoder/skills/super-dev/SKILL.md",
            ],
            "official_user_surfaces": [
                "~/.qoder/AGENTS.md",
                "~/.qoder/commands/super-dev.md",
                "~/.qoder/skills/super-dev/SKILL.md",
            ],
            "optional_project_surfaces": [".qoder/agents/super-dev.md"],
            "optional_user_surfaces": ["~/.qoder/agents/super-dev.md"],
        },
    )

    assert any("AGENTS.md" in item for item in lines)
    assert any(".qoder/rules/super-dev.md" in item for item in lines)
    assert any(".qoder/commands/super-dev.md" in item for item in lines)
    assert any(".qoder/agents/super-dev.md" in item for item in lines)


def test_build_host_official_pass_criteria_exposes_droid_factory_contract():
    lines = build_host_official_pass_criteria(
        "droid-cli",
        {
            "host": "Droid CLI",
            "host_protocol_mode": "official-rules-skills",
            "official_project_surfaces": [
                "AGENTS.md",
                ".factory/rules/super-dev.md",
                ".factory/commands/super-dev.md",
            ],
            "official_user_surfaces": ["~/.factory/AGENTS.md"],
            "managed_competition_project_surfaces": [
                ".factory/commands/super-dev-seeai.md",
                ".factory/skills/super-dev-seeai/SKILL.md",
            ],
        },
    )

    assert any("SEEAI 项目补充面" in item for item in lines)
    assert any("official-rules-skills" in item for item in lines)
    assert any("super-dev-seeai" in item for item in lines)


def test_build_host_post_onboard_self_check_exposes_kimi_entry_and_resume_chain():
    lines = build_host_post_onboard_self_check(
        "kimi-code",
        {
            "host": "Kimi Code",
            "host_protocol_mode": "official-agents-entry",
            "official_project_surfaces": ["AGENTS.md"],
            "official_user_surfaces": [],
            "optional_project_surfaces": [".kimi/skills/super-dev/SKILL.md"],
            "optional_user_surfaces": ["~/.kimi/skills/super-dev/SKILL.md"],
            "managed_competition_user_surfaces": ["~/.kimi/skills/super-dev-seeai/SKILL.md"],
        },
    )

    assert any("接入后先确认入口可用" in item and "/skill:super-dev" in item for item in lines)
    assert any("official-agents-entry" in item for item in lines)
    assert any("SEEAI 用户级补充面已写入" in item and "super-dev-seeai" in item for item in lines)


def test_all_supported_hosts_have_explicit_experience_profiles():
    host_ids = list_host_ids()

    assert host_ids
    assert set(host_ids) == set(_EXPERIENCE_PROFILES)


def test_all_supported_hosts_expose_complete_host_entry_and_resume_contract():
    for host_id in list_host_ids():
        profile = build_host_experience_profile(host_id)

        assert profile["tier"]
        assert profile["label"]
        assert profile["best_for"]
        assert profile["resume_style"]
        assert profile["market_focus"]
        assert profile["strengths"]
        assert build_host_start_playbook(host_id)
        assert build_host_resume_guidance(host_id)
        assert build_host_repair_guidance(host_id)
        assert "super-dev" in build_host_standard_first_prompt(host_id).lower()
        assert "seeai" in build_host_competition_first_prompt(host_id).lower()


def test_all_supported_hosts_usage_profiles_expose_full_workflow_acceptance_layers():
    manager = IntegrationManager(Path(".").resolve())

    for host_id in list_host_ids():
        adapter = manager.get_adapter_profile(host_id)
        usage = serialize_host_usage_profile(
            profile=adapter,
            target=host_id,
            final_trigger=adapter.trigger_command,
            managed_competition_project_surfaces=manager.managed_competition_project_surfaces(
                host_id
            ),
            managed_competition_user_surfaces=manager.managed_competition_user_surfaces(host_id),
            include_host_id=True,
            include_capability_labels=True,
            include_docs_fields=True,
            skill_slash_entry_host_id=host_id,
            skill_slash_entry_note="test",
            flow_host_id=host_id,
        )

        assert usage["host_protocol_mode"]
        assert usage["standard_flow_first_prompt"]
        assert usage["competition_flow_first_prompt"]
        assert usage["host_start_playbook"]
        assert usage["host_resume_guidance"]
        assert usage["post_onboard_self_check"]
        assert usage["official_workflow_checks"]
        assert usage["official_pass_criteria"]
        assert usage["host_repair_playbook"]
