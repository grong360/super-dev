"""
平台集成管理测试
"""

from pathlib import Path
from urllib import error as urllib_error

import pytest

from super_dev.catalogs import PRIMARY_HOST_TOOL_IDS
from super_dev.host_usage_profile import serialize_host_usage_profile
from super_dev.integrations import IntegrationManager
from super_dev.skills import SkillManager


class TestIntegrationManager:
    def test_coverage_gaps_are_empty(self):
        gaps = IntegrationManager.coverage_gaps()
        assert gaps["missing_in_targets"] == []
        assert gaps["extra_in_targets"] == []
        assert gaps["missing_in_slash"] == []
        assert gaps["extra_in_slash"] == []
        assert gaps["missing_in_docs_map"] == []
        assert gaps["extra_in_docs_map"] == []
        assert gaps["missing_official_docs_url"] == []
        assert gaps["unverified_docs"] == []

    @pytest.mark.parametrize("target", PRIMARY_HOST_TOOL_IDS)
    def test_primary_hosts_usage_profile_exposes_core_host_workflow_contract(
        self, temp_project_dir: Path, target: str
    ):
        manager = IntegrationManager(temp_project_dir)
        profile = manager.get_adapter_profile(target)
        usage = serialize_host_usage_profile(
            profile=profile,
            target=target,
            final_trigger=profile.trigger_command,
            managed_competition_project_surfaces=manager.managed_competition_project_surfaces(
                target
            ),
            managed_competition_user_surfaces=manager.managed_competition_user_surfaces(target),
            host_value=profile.host,
            include_host_id=True,
            include_capability_labels=True,
            include_docs_fields=True,
            skill_slash_entry_host_id=target,
            flow_host_id=target,
        )

        assert usage["standard_flow_first_prompt"]
        assert "super-dev" in usage["standard_flow_first_prompt"].lower()
        assert usage["competition_flow_first_prompt"]
        assert "seeai" in usage["competition_flow_first_prompt"].lower()
        assert usage["host_start_playbook"]
        assert usage["post_onboard_self_check"]
        assert usage["official_workflow_checks"]
        assert usage["official_pass_criteria"]
        assert usage["host_repair_playbook"]

        if IntegrationManager.supports_slash(target):
            assert usage["standard_flow_first_prompt"].startswith("/")

        if usage["managed_competition_project_surfaces"]:
            assert any(
                "SEEAI" in item or "super-dev-seeai" in item
                for item in usage["post_onboard_self_check"] + usage["official_workflow_checks"]
            )
        if usage["managed_competition_user_surfaces"]:
            assert any(
                "SEEAI" in item or "super-dev-seeai" in item
                for item in usage["post_onboard_self_check"] + usage["official_workflow_checks"]
            )

    @pytest.mark.parametrize(
        "target",
        [
            host_id
            for host_id in PRIMARY_HOST_TOOL_IDS
            if IntegrationManager.managed_competition_project_surfaces(host_id)
        ],
    )
    def test_primary_hosts_write_all_managed_seeai_project_surfaces(
        self, temp_project_dir: Path, target: str
    ):
        manager = IntegrationManager(temp_project_dir)
        manager.setup(target, force=True)

        for relative in manager.managed_competition_project_surfaces(target):
            file_path = temp_project_dir / relative
            assert file_path.exists(), f"{target} missing SEEAI project surface: {relative}"
            content = file_path.read_text(encoding="utf-8")
            assert "SEEAI" in content or "super-dev-seeai" in content
            missing = manager.audit_surface_contract(
                target,
                f"project:{relative}",
                file_path,
                content,
            )
            assert missing == [], f"{target} surface contract gaps for {relative}: {missing}"

    @pytest.mark.parametrize(
        "target, expected_file",
        [
            (name, config.files[0])
            for name, config in IntegrationManager.TARGETS.items()
            if config.files
        ],
    )
    def test_setup_single_target(self, temp_project_dir: Path, target: str, expected_file: str):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup(target, force=True)

        assert len(files) >= len(IntegrationManager.TARGETS[target].files)
        rule_file = temp_project_dir / expected_file
        assert rule_file.exists()
        content = rule_file.read_text(encoding="utf-8")
        assert "Super Dev" in content

    def test_setup_all_targets(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        result = manager.setup_all(force=True)

        assert set(result.keys()) == set(IntegrationManager.TARGETS.keys())
        for target in IntegrationManager.TARGETS.values():
            for file_path in target.files:
                full_path = temp_project_dir / file_path
                assert full_path.exists()
                assert "Super Dev" in full_path.read_text(encoding="utf-8")

    def test_droid_seeai_project_surfaces_pass_contract_audit(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        manager.setup("droid-cli", force=True)

        for relative in (
            ".factory/commands/super-dev-seeai.md",
            ".factory/skills/super-dev-seeai/SKILL.md",
        ):
            file_path = temp_project_dir / relative
            content = file_path.read_text(encoding="utf-8")
            missing = manager.audit_surface_contract(
                "droid-cli",
                f"project:{relative}",
                file_path,
                content,
            )
            assert missing == []

    @pytest.mark.parametrize(
        "target",
        [
            host_id
            for host_id in PRIMARY_HOST_TOOL_IDS
            if IntegrationManager.managed_competition_user_surfaces(host_id)
        ],
    )
    def test_primary_hosts_write_all_managed_seeai_user_surfaces(
        self, temp_project_dir: Path, target: str, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        SkillManager(temp_project_dir).install(source="super-dev", target=target, force=True)

        for relative in manager.managed_competition_user_surfaces(target):
            file_path = manager._resolve_surface_declaration(target=target, surface=relative)
            assert file_path.exists(), f"{target} missing SEEAI user surface: {relative}"
            content = file_path.read_text(encoding="utf-8")
            assert "SEEAI" in content or "super-dev-seeai" in content

    def test_codex_setup_upserts_root_agents_without_clobbering_existing_content(
        self, temp_project_dir: Path
    ):
        agents = temp_project_dir / "AGENTS.md"
        agents.write_text(
            "# Existing Project Rules\n\n- Keep current behavior.\n", encoding="utf-8"
        )
        project_skill = temp_project_dir / ".agents" / "skills" / "super-dev" / "SKILL.md"
        seeai_project_skill = (
            temp_project_dir / ".agents" / "skills" / "super-dev-seeai" / "SKILL.md"
        )

        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("codex-cli", force=True)

        plugin_marketplace = temp_project_dir / ".agents" / "plugins" / "marketplace.json"
        plugin_manifest = (
            temp_project_dir / "plugins" / "super-dev-codex" / ".codex-plugin" / "plugin.json"
        )
        plugin_skill = (
            temp_project_dir / "plugins" / "super-dev-codex" / "skills" / "super-dev" / "SKILL.md"
        )
        assert {
            agents.resolve(),
            project_skill.resolve(),
            seeai_project_skill.resolve(),
            plugin_marketplace.resolve(),
            plugin_manifest.resolve(),
            plugin_skill.resolve(),
        } <= {item.resolve() for item in files}
        content = agents.read_text(encoding="utf-8")
        assert "# Existing Project Rules" in content
        assert "BEGIN SUPER DEV CODEX" in content
        assert "super-dev:" in content
        assert "super-dev：" in content
        assert "output/*-prd.md" in content
        assert "actual project files" in content or "repository workspace" in content
        assert "Do not spend a turn saying you will read the skill first" in content
        assert project_skill.exists()
        assert seeai_project_skill.exists()
        plugin_seeai_skill = (
            temp_project_dir
            / "plugins"
            / "super-dev-codex"
            / "skills"
            / "super-dev-seeai"
            / "SKILL.md"
        )
        assert plugin_seeai_skill.exists()

    def test_setup_creates_seeai_slash_command_for_slash_hosts(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)

        files = manager.setup("claude-code", force=True)

        seeai_command = temp_project_dir / ".claude" / "commands" / "super-dev-seeai.md"
        assert seeai_command.resolve() in {item.resolve() for item in files}
        content = seeai_command.read_text(encoding="utf-8")
        assert "/super-dev-seeai" in content
        assert "SUPER_DEV_SEEAI_FLOW_CONTRACT_V1" in content
        assert "compact Spec" in content
        assert "full-stack sprint" in content
        assert "比赛短文档模板" in content
        assert "首轮输出模板" in content
        assert "`P0 主路径`" in content
        assert "# Sprint Checklist" in content
        assert "官网类题" in content
        assert "默认技术栈：HTML Canvas + Vanilla JS；复杂玩法再上 Phaser" in content
        assert "默认 sprint：输入页/主流程 -> 结果页" in content
        assert "题型识别提示" in content
        assert "品牌、官网、落地页、活动宣传、首屏" in content
        assert "比赛设计包（先选后做）" in content
        assert "Arena Neon" in content
        assert "快而稳的执行守卫" in content
        assert "12 分钟内必须跑出第一个可见" in content
        assert "模块真实生效规则" in content
        assert "每个保留下来的模块都必须真实启动" in content
        assert "失败优先回退协议" in content

    def test_setup_creates_host_specific_seeai_surfaces_for_codebuddy_and_droid_cli(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)

        codebuddy_files = manager.setup("codebuddy", force=True)
        droid_files = manager.setup("droid-cli", force=True)

        codebuddy_seeai = temp_project_dir / ".codebuddy" / "commands" / "super-dev-seeai.md"
        codebuddy_agent = temp_project_dir / ".codebuddy" / "agents" / "super-dev.md"
        droid_seeai = temp_project_dir / ".factory" / "commands" / "super-dev-seeai.md"

        assert codebuddy_seeai.resolve() in {item.resolve() for item in codebuddy_files}
        assert droid_seeai.resolve() in {item.resolve() for item in droid_files}
        assert "CodeBuddy 比赛专项适配" in codebuddy_seeai.read_text(encoding="utf-8")
        droid_content = droid_seeai.read_text(encoding="utf-8")
        assert "Droid CLI 比赛专项适配" in droid_content
        assert "droid exec --session-id" in droid_content
        agent_content = codebuddy_agent.read_text(encoding="utf-8")
        assert "/super-dev-seeai" in agent_content
        assert "SEEAI Competition Mode" in agent_content

    def test_codex_setup_global_protocol_writes_global_codex_agents(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        global_file = manager.setup_global_protocol("codex-cli", force=True)

        expected = fake_home / ".codex" / "AGENTS.md"
        assert global_file == expected
        assert expected.exists()
        content = expected.read_text(encoding="utf-8")
        assert "BEGIN SUPER DEV CODEX" in content
        assert "super-dev:" in content
        assert "$super-dev" in content
        assert "/` list" in content or "`/` list" in content

    def test_codex_global_protocol_and_skill_paths_follow_codex_home(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        codex_home = temp_project_dir / "custom-codex-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        codex_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.setenv("CODEX_HOME", str(codex_home))

        manager = IntegrationManager(temp_project_dir)

        assert manager.resolve_global_protocol_path("codex-cli") == codex_home / "AGENTS.md"
        paths = manager.expected_skill_paths("codex-cli")
        normalized = {path.as_posix() for path in paths}
        assert any(item.endswith("/.agents/skills/super-dev/SKILL.md") for item in normalized)
        # No compatibility mirrors for codex-cli anymore
        assert not any(
            item.endswith("/custom-codex-home/skills/super-dev/SKILL.md") for item in normalized
        )

    def test_codex_expected_skill_paths_no_compatibility_mirror(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        paths = manager.expected_skill_paths("codex-cli")
        normalized = {path.as_posix() for path in paths}
        assert any(item.endswith("/.agents/skills/super-dev/SKILL.md") for item in normalized)
        # No legacy skill-alias or codex mirror paths
        legacy_name = f"{SkillManager.DEFAULT_SKILL_NAME}-core"
        assert not any(item.endswith(f"{legacy_name}/SKILL.md") for item in normalized)
        assert not any(item.endswith("/.codex/skills/super-dev/SKILL.md") for item in normalized)

    def test_readiness_surface_sets_distinguish_official_optional_and_compatibility(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)

        claude_sets = manager.readiness_surface_sets(target="claude-code", skill_name="super-dev")
        claude_optional = {path.as_posix() for path in claude_sets["optional_project"]}
        claude_required_slash = {path.as_posix() for path in claude_sets["required_slash"]}
        claude_optional_slash = {path.as_posix() for path in claude_sets["optional_slash"]}
        claude_official_skill = {path.as_posix() for path in claude_sets["official_skill"]}
        claude_compat_skill = {path.as_posix() for path in claude_sets["compatibility_skill"]}
        assert any(
            item.endswith("/CLAUDE.md")
            for item in {path.as_posix() for path in claude_sets["official_project"]}
        )
        assert any(
            item.endswith("/.claude/skills/super-dev/SKILL.md") for item in claude_official_skill
        )
        assert any(item.endswith("/.claude/commands/super-dev.md") for item in claude_optional)
        assert not claude_required_slash
        assert any(
            item.endswith("/.claude/commands/super-dev.md") for item in claude_optional_slash
        )
        assert not claude_compat_skill

        codex_sets = manager.readiness_surface_sets(target="codex-cli", skill_name="super-dev")
        codex_required_slash = {path.as_posix() for path in codex_sets["required_slash"]}
        codex_official_skill = {path.as_posix() for path in codex_sets["official_skill"]}
        codex_compat_skill = {path.as_posix() for path in codex_sets["compatibility_skill"]}
        assert not codex_required_slash
        assert any(
            item.endswith("/.agents/skills/super-dev/SKILL.md") for item in codex_official_skill
        )
        # No compatibility mirrors anymore
        assert not codex_compat_skill

    def test_adapter_profiles_cover_all_targets(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        profiles = manager.list_adapter_profiles()
        assert len(profiles) == len(IntegrationManager.TARGETS)
        by_host = {item.host: item for item in profiles}
        assert set(by_host.keys()) == set(IntegrationManager.TARGETS.keys())

        antigravity = by_host["antigravity"]
        assert antigravity.category == "ide"
        assert antigravity.usage_mode == "native-slash"
        assert antigravity.trigger_command == "/super-dev <需求描述>"
        assert antigravity.host_protocol_mode == "recommended-gemini-workflow"
        assert (
            antigravity.host_protocol_summary
            == "当前推荐接入模型: GEMINI.md + custom commands + optional workflows"
        )
        assert "GEMINI.md" in antigravity.integration_files
        assert ".agent/workflows/super-dev.md" in antigravity.integration_files
        assert ".gemini/commands/super-dev.toml" in antigravity.official_project_surfaces
        assert "~/.gemini/GEMINI.md" in antigravity.optional_user_surfaces
        assert "~/.gemini/skills/super-dev/SKILL.md" in antigravity.observed_compatibility_surfaces
        assert antigravity.requires_restart_after_onboard is True

        codex = by_host["codex-cli"]
        assert codex.category == "cli"
        assert codex.adapter_mode == "native-cli-session"
        assert codex.terminal_entry_scope.startswith("仅用于安装 / 更新 / 卸载")
        assert codex.terminal_entry == "super-dev"
        assert codex.slash_command_file == ""
        assert codex.skill_dir.startswith("~/.agents/")
        assert codex.certification_level == "certified"
        assert codex.certification_label == "Certified"
        assert codex.certification_reason
        assert codex.certification_evidence
        assert codex.usage_mode == "agents-and-skill"
        assert codex.requires_restart_after_onboard is True
        assert codex.trigger_command == "super-dev: <需求描述>"
        assert codex.entry_variants
        assert codex.entry_variants[0]["entry"] == "$super-dev"
        assert "重启 codex" in codex.usage_location
        assert any("重启 codex" in step for step in codex.post_onboard_steps)
        assert any("CLI 显式入口是 `$super-dev`" in note for note in codex.usage_notes)
        assert codex.host_protocol_mode == "official-skill"
        assert codex.host_protocol_summary == "官方 AGENTS.md + Skills + CLI $skill entry"
        assert codex.capability_labels["slash"] == "skill-list"
        assert ".agents/skills/super-dev/SKILL.md" in codex.official_project_surfaces
        assert "~/.agents/skills/super-dev/SKILL.md" in codex.official_user_surfaces
        assert "~/.codex/AGENTS.md" in codex.optional_user_surfaces
        assert ".agents/plugins/marketplace.json" in codex.optional_project_surfaces
        assert (
            "plugins/super-dev-codex/.codex-plugin/plugin.json" in codex.optional_project_surfaces
        )
        assert "~/.codex/skills/super-dev/SKILL.md" in codex.observed_compatibility_surfaces
        assert "$super-dev" in codex.primary_entry

        qoder = by_host["qoder"]
        assert qoder.category == "ide"
        assert qoder.adapter_mode == "native-ide-rule-file"
        assert qoder.integration_files[0] == "AGENTS.md"
        assert qoder.docs_verified is True
        assert qoder.certification_level == "experimental"
        assert qoder.usage_mode == "native-slash"
        assert qoder.slash_command_file == ".qoder/commands/super-dev.md"
        assert "AGENTS.md + rules + commands + skills (+ optional agents)" in qoder.host_protocol_summary
        assert ".qoder/agents/super-dev.md" in qoder.integration_files
        assert ".qoder/rules/super-dev.md" in qoder.official_project_surfaces
        assert "AGENTS.md" in qoder.official_project_surfaces
        assert "~/.qoder/commands/super-dev.md" in qoder.official_user_surfaces
        assert "~/.qoder/skills/super-dev/SKILL.md" in qoder.official_user_surfaces
        assert "~/.qoder/AGENTS.md" in qoder.official_user_surfaces
        assert "~/.qoder/agents/super-dev.md" in qoder.optional_user_surfaces
        assert ".qoder/skills/super-dev/SKILL.md" in qoder.official_project_surfaces
        assert ".qoder/agents/super-dev.md" in qoder.optional_project_surfaces
        assert qoder.observed_compatibility_surfaces == []

        codebuddy = by_host["codebuddy"]
        assert codebuddy.host_protocol_mode == "official-subagent"
        assert (
            codebuddy.host_protocol_summary
            == "官方 CODEBUDDY.md + rules + skills + task/workspace continuity"
        )
        assert "CODEBUDDY.md" in codebuddy.integration_files
        assert ".codebuddy/rules/super-dev/RULE.mdc" in codebuddy.integration_files
        assert "CODEBUDDY.md" in codebuddy.official_project_surfaces
        assert ".codebuddy/rules/super-dev/RULE.mdc" in codebuddy.official_project_surfaces
        assert ".codebuddy/agents/super-dev.md" in codebuddy.integration_files
        assert "~/.codebuddy/skills/super-dev/SKILL.md" in codebuddy.official_user_surfaces
        assert ".codebuddy/commands/super-dev-seeai.md" in codebuddy.optional_project_surfaces
        assert ".codebuddy/skills/super-dev-seeai/SKILL.md" in codebuddy.official_project_surfaces
        assert "~/.codebuddy/skills/super-dev-seeai/SKILL.md" in codebuddy.official_user_surfaces
        assert "~/.codebuddy/CODEBUDDY.md" in codebuddy.optional_user_surfaces
        assert "~/.codebuddy/agents/super-dev.md" in codebuddy.optional_user_surfaces
        assert "~/.codebuddy/commands/super-dev-seeai.md" in codebuddy.optional_user_surfaces
        assert ".codebuddy/AGENTS.md" in codebuddy.observed_compatibility_surfaces

        codebuddy_cli = by_host["codebuddy-cli"]
        assert (
            codebuddy_cli.host_protocol_summary
            == "官方 CODEBUDDY.md + rules + commands + skills + agents"
        )
        assert "CODEBUDDY.md" in codebuddy_cli.integration_files
        assert "CODEBUDDY.md" in codebuddy_cli.official_project_surfaces
        assert ".codebuddy/rules/super-dev.md" in codebuddy_cli.integration_files
        assert ".codebuddy/rules/super-dev.md" in codebuddy_cli.official_project_surfaces
        assert ".codebuddy/commands/super-dev.md" in codebuddy_cli.integration_files
        assert ".codebuddy/skills/super-dev/SKILL.md" in codebuddy_cli.integration_files
        assert ".codebuddy/agents/super-dev.md" in codebuddy_cli.integration_files
        assert ".codebuddy/agents/super-dev.md" in codebuddy_cli.official_project_surfaces
        assert ".codebuddy/commands/super-dev-seeai.md" in codebuddy_cli.official_project_surfaces
        assert (
            ".codebuddy/skills/super-dev-seeai/SKILL.md" in codebuddy_cli.official_project_surfaces
        )
        assert (
            "~/.codebuddy/skills/super-dev-seeai/SKILL.md" in codebuddy_cli.official_user_surfaces
        )
        assert "~/.codebuddy/CODEBUDDY.md" in codebuddy_cli.optional_user_surfaces
        assert "~/.codebuddy/rules/super-dev.md" in codebuddy_cli.optional_user_surfaces
        assert "~/.codebuddy/commands/super-dev-seeai.md" in codebuddy_cli.optional_user_surfaces
        assert "~/.codebuddy/agents/super-dev.md" in codebuddy_cli.optional_user_surfaces
        assert (
            ".codebuddy/skills/super-dev/SKILL.md" in codebuddy_cli.official_project_surfaces
        )
        assert ".codebuddy/AGENTS.md" in codebuddy_cli.observed_compatibility_surfaces

        droid = by_host["droid-cli"]
        assert ".factory/commands/super-dev-seeai.md" in droid.official_project_surfaces
        assert ".factory/skills/super-dev/SKILL.md" in droid.official_project_surfaces
        assert "~/.factory/skills/super-dev/SKILL.md" in droid.official_user_surfaces
        assert "~/.factory/commands/super-dev-seeai.md" in droid.optional_user_surfaces
        assert droid.host_protocol_mode == "official-factory"
        assert "AGENTS.md + .factory/rules + skills (+ legacy commands)" in droid.host_protocol_summary

        kimi = by_host["kimi-code"]
        assert kimi.category == "cli"
        assert kimi.adapter_mode == "native-cli-session"
        assert kimi.usage_mode == "agents-skills-native-resume"
        assert kimi.trigger_command == "/skill:super-dev <需求描述>"
        assert ".kimi/AGENTS.md" in kimi.integration_files
        assert kimi.host_protocol_mode == "official-agents-entry"
        assert ".kimi/skills/super-dev/SKILL.md" in kimi.optional_project_surfaces
        assert "~/.kimi/skills/super-dev/SKILL.md" in kimi.optional_user_surfaces
        assert "~/.config/agents/skills/super-dev/SKILL.md" in kimi.optional_user_surfaces
        assert any(item["entry"] == "/skill:super-dev <需求描述>" for item in kimi.entry_variants)

        qwen = by_host["qwen-code"]
        assert qwen.category == "cli"
        assert qwen.host_protocol_mode == "official-context"
        assert "QWEN.md" in qwen.official_project_surfaces
        assert ".qwen/commands/super-dev.md" in qwen.official_project_surfaces
        assert ".qwen/skills/super-dev/SKILL.md" in qwen.official_project_surfaces
        assert ".qwen/agents/super-dev.md" in qwen.official_project_surfaces
        assert "~/.qwen/QWEN.md" in qwen.official_user_surfaces
        assert "~/.qwen/skills/super-dev/SKILL.md" in qwen.official_user_surfaces
        assert "~/.qwen/commands/super-dev.md" in qwen.official_user_surfaces
        assert "~/.qwen/agents/super-dev.md" in qwen.official_user_surfaces

        claude_app = by_host["claude"]
        assert claude_app.category == "assistant"
        assert claude_app.adapter_mode == "native-desktop-assistant"
        assert claude_app.host_protocol_mode == "official-projects"
        assert claude_app.integration_files == []

        codex_app = by_host["codex"]
        assert codex_app.category == "assistant"
        assert codex_app.adapter_mode == "native-desktop-assistant"
        assert codex_app.host_protocol_mode == "official-skill"
        assert "AGENTS.md" in codex_app.official_project_surfaces
        assert ".agents/skills/super-dev/SKILL.md" in codex_app.official_project_surfaces
        assert "~/.agents/skills/super-dev/SKILL.md" in codex_app.official_user_surfaces

        codebuddy_cn = by_host["codebuddy-cn"]
        assert codebuddy_cn.category == "ide"
        assert codebuddy_cn.host_protocol_mode == "official-subagent"
        assert (
            codebuddy_cn.host_protocol_summary
            == "官方 CODEBUDDY.md + rules + skills + 中文任务/workspace continuity"
        )
        assert "CODEBUDDY.md" in codebuddy_cn.official_project_surfaces
        assert ".codebuddy/rules/super-dev/RULE.mdc" in codebuddy_cn.official_project_surfaces

        trae_cn = by_host["trae-cn"]
        assert trae_cn.category == "ide"
        assert trae_cn.host_protocol_mode == "recommended-cn-workspace-flow"
        assert ".trae/project_rules.md" in trae_cn.official_project_surfaces
        assert ".trae/rules.md" in trae_cn.official_project_surfaces
        assert ".trae/skills/super-dev/SKILL.md" in trae_cn.official_project_surfaces

        trae_solo = by_host["trae-solo"]
        assert trae_solo.category == "assistant"
        assert trae_solo.usage_mode == "workspace-rules-slash-skill"
        assert trae_solo.trigger_command == "/super-dev <需求描述>"
        assert ".trae/commands/super-dev.md" == trae_solo.slash_command_file
        assert ".trae/rules/super-dev.md" in trae_solo.official_project_surfaces
        assert ".trae/skills/super-dev/SKILL.md" in trae_solo.official_project_surfaces
        assert "~/.trae/skills/super-dev/SKILL.md" in trae_solo.observed_compatibility_surfaces

        trae_solocn = by_host["trae-solocn"]
        assert trae_solocn.category == "assistant"
        assert trae_solocn.usage_mode == "mtc-code-rules-skill"
        assert trae_solocn.trigger_command == "super-dev: <需求描述>"
        assert trae_solocn.slash_command_file == ""
        assert ".trae/rules/super-dev.md" in trae_solocn.official_project_surfaces
        assert "~/.trae-cn/skills/super-dev/SKILL.md" in trae_solocn.official_user_surfaces

        workbuddy = by_host["workbuddy"]
        assert workbuddy.category == "assistant"
        assert workbuddy.adapter_mode == "skill-only"
        assert workbuddy.usage_mode == "manual-workbench-skill"
        assert workbuddy.trigger_command == "super-dev: <需求描述>"
        assert workbuddy.slash_command_file == ""
        assert workbuddy.skill_dir == "~/.workbuddy/skills"
        assert workbuddy.host_protocol_mode == "manual-task-workbench-mcp"
        assert workbuddy.host_protocol_summary == "当前推荐任务工作台模型: Skills + MCP + task continuity"
        assert any("super-dev-seeai:" in item["entry"] for item in workbuddy.entry_variants)
        assert "~/.workbuddy/skills/super-dev/SKILL.md" in workbuddy.optional_user_surfaces

        claude = by_host["claude-code"]
        assert claude.host_protocol_mode == "official-skill"
        assert (
            claude.host_protocol_summary
            == "官方 CLAUDE.md + settings + project/user skills + subagents"
        )
        assert "CLAUDE.md" in claude.official_project_surfaces
        assert ".claude/CLAUDE.md" in claude.official_project_surfaces
        assert ".claude/skills/super-dev/SKILL.md" in claude.official_project_surfaces
        assert ".claude/agents/super-dev.md" in claude.official_project_surfaces
        assert "~/.claude/skills/super-dev/SKILL.md" in claude.official_user_surfaces
        assert "~/.claude/agents/super-dev.md" in claude.official_user_surfaces
        assert ".claude/settings.json" in claude.optional_project_surfaces
        assert "~/.claude/settings.json" in claude.optional_user_surfaces
        assert ".claude/commands/super-dev.md" in claude.optional_project_surfaces
        assert ".claude-plugin/marketplace.json" in claude.optional_project_surfaces
        assert (
            "plugins/super-dev-claude/.claude-plugin/plugin.json"
            in claude.optional_project_surfaces
        )
        assert "~/.claude/commands/super-dev.md" in claude.optional_user_surfaces
        assert claude.observed_compatibility_surfaces == []
        assert claude.skill_dir.startswith("~/.claude/skills")

        gemini = by_host["gemini-cli"]
        assert gemini.host_protocol_mode == "official-context"
        assert gemini.host_protocol_summary == "官方 GEMINI.md + settings + custom commands"
        assert "GEMINI.md" in gemini.official_project_surfaces
        assert ".gemini/settings.json" in gemini.optional_project_surfaces
        assert "~/.gemini/GEMINI.md" in gemini.optional_user_surfaces
        assert "~/.gemini/settings.json" in gemini.optional_user_surfaces
        assert "~/.gemini/commands/super-dev.toml" in gemini.optional_user_surfaces
        assert "~/.gemini/skills/super-dev/SKILL.md" in gemini.observed_compatibility_surfaces

        assert codex.precondition_status == "session-restart-required"
        assert any("重开宿主会话" in item["label"] for item in codex.precondition_items)
        assert any(
            item["status"] == "project-context-required" for item in codex.precondition_items
        )
        assert any("目标项目目录" in item for item in codex.precondition_guidance)

        cursor = by_host["cursor"]
        assert cursor.precondition_status == "project-context-required"
        assert cursor.precondition_items
        assert any("目标项目" in item for item in cursor.precondition_guidance)
        assert cursor.host_protocol_summary == "官方 Agent Chat + AGENTS.md + rules (+ beta commands)"
        assert "AGENTS.md" in cursor.official_project_surfaces
        assert "CLAUDE.md" in cursor.optional_project_surfaces
        assert ".cursor/commands/super-dev.md" in cursor.optional_project_surfaces

        kiro_cli = by_host["kiro-cli"]
        assert kiro_cli.host_protocol_mode == "official-steering"
        assert kiro_cli.host_protocol_summary == "官方 AGENTS.md + steering + skills + native resume"
        assert kiro_cli.usage_mode == "native-slash"
        assert kiro_cli.trigger_command == "/super-dev <需求描述>"
        assert "AGENTS.md" in kiro_cli.official_project_surfaces
        assert ".kiro/steering/super-dev.md" in kiro_cli.official_project_surfaces
        assert ".kiro/skills/super-dev/SKILL.md" in kiro_cli.official_project_surfaces
        assert "~/.kiro/skills/super-dev/SKILL.md" in kiro_cli.official_user_surfaces
        assert "~/.kiro/steering/super-dev.md" in kiro_cli.optional_user_surfaces
        assert "~/.kiro/steering/AGENTS.md" in kiro_cli.optional_user_surfaces

        kiro = by_host["kiro"]
        assert kiro.host_protocol_mode == "official-steering"
        assert kiro.host_protocol_summary == "官方 AGENTS.md + steering + skills + agent continuity"
        assert kiro.usage_mode == "native-slash"
        assert "AGENTS.md" in kiro.official_project_surfaces
        assert ".kiro/steering/super-dev.md" in kiro.official_project_surfaces
        assert "~/.kiro/skills/super-dev/SKILL.md" in kiro.official_user_surfaces
        assert "~/.kiro/steering/super-dev.md" in kiro.optional_user_surfaces
        assert "~/.kiro/steering/AGENTS.md" in kiro.optional_user_surfaces

        roo = by_host["roo-code"]
        assert roo.host_protocol_mode == "official-skill"
        assert roo.capability_labels["slash"] == "none"
        assert roo.slash_command_file == ""
        assert roo.host_protocol_summary == "官方 commands + rules"
        assert ".roo/rules/super-dev.md" in roo.official_project_surfaces
        assert "~/.roo/skills/super-dev/SKILL.md" in roo.official_user_surfaces
        assert "~/.roo/rules/super-dev.md" in roo.optional_user_surfaces
        assert "~/.roo/commands/super-dev.md" in roo.optional_user_surfaces

        cline = by_host["cline"]
        assert cline.host_protocol_mode == "official-context"
        assert cline.host_protocol_summary == "官方 .clinerules + skills + AGENTS.md compatibility"
        assert ".clinerules/super-dev.md" in cline.official_project_surfaces
        assert ".cline/skills/super-dev/SKILL.md" in cline.official_project_surfaces
        assert "~/.cline/skills/super-dev/SKILL.md" in cline.official_user_surfaces
        assert "~/Documents/Cline/Rules/super-dev.md" in cline.optional_user_surfaces
        assert "AGENTS.md" in cline.observed_compatibility_surfaces

        copilot = by_host["vscode-copilot"]
        assert copilot.host_protocol_mode == "official-context"
        assert copilot.capability_labels["slash"] == "none"
        assert copilot.trigger_command == "super-dev: <需求描述>"
        assert ".github/copilot-instructions.md" in copilot.official_project_surfaces
        assert "AGENTS.md" in copilot.observed_compatibility_surfaces

        copilot_cli = by_host["copilot-cli"]
        assert (
            copilot_cli.host_protocol_summary
            == "官方 copilot-instructions + AGENTS.md + skills + agents"
        )
        assert "AGENTS.md" in copilot_cli.official_project_surfaces
        assert ".github/copilot-instructions.md" in copilot_cli.official_project_surfaces
        assert ".github/agents/super-dev.md" in copilot_cli.official_project_surfaces
        assert ".github/skills/super-dev/SKILL.md" in copilot_cli.integration_files
        assert ".github/skills/super-dev/SKILL.md" in copilot_cli.official_project_surfaces
        assert "~/.copilot/copilot-instructions.md" in copilot_cli.official_user_surfaces
        assert "~/.copilot/agents/super-dev.md" in copilot_cli.official_user_surfaces
        assert "~/.copilot/skills/super-dev/SKILL.md" in copilot_cli.official_user_surfaces
        assert "AGENTS.md" not in copilot_cli.observed_compatibility_surfaces

    def test_adapter_profile_contains_docs_references_and_capability_labels(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)
        claude = manager.get_adapter_profile("claude-code")
        codex = manager.get_adapter_profile("codex-cli")

        assert len(claude.official_docs_references) >= 2
        assert claude.capability_labels["slash"] == "native"
        assert claude.capability_labels["skills"] == "official"
        assert claude.capability_labels["trigger"] == "slash"

        assert codex.capability_labels["slash"] == "skill-list"
        assert codex.capability_labels["trigger"] == "text"
        assert codex.capability_labels["skills"] == "official"

    def test_verify_official_docs_reports_reachability(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        manager = IntegrationManager(temp_project_dir)

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(req, timeout=0):
            return _Resp()

        monkeypatch.setattr("super_dev.integrations.manager.urllib_request.urlopen", _fake_urlopen)

        result = manager.verify_official_docs("claude-code")
        assert result["status"] == "verified"
        assert result["reachable"] == result["checked"]
        assert result["checked"] >= 2

    def test_host_hardening_blueprint_contains_steps(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        codex = manager.host_hardening_blueprint("codex-cli")
        claude = manager.host_hardening_blueprint("claude-code")
        codex_with_user = manager.host_hardening_blueprint(
            "codex-cli", include_user_surfaces=True
        )

        assert codex["trigger_mode"] == "text"
        assert any("install skill" in step for step in codex["required_steps"])
        assert not any("user-level slash" in step for step in codex["required_steps"])
        assert "~/.codex/AGENTS.md" not in codex["required_user_surfaces"]
        assert "~/.codex/AGENTS.md" in codex["optional_user_surfaces"]
        assert "~/.codex/AGENTS.md" in codex_with_user["required_user_surfaces"]
        assert claude["trigger_mode"] == "slash"
        assert any("setup project slash command" in step for step in claude["required_steps"])

    def test_compare_official_capabilities_reports_alignment(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        manager = IntegrationManager(temp_project_dir)

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, size=-1):
                return b"slash commands rules skills sub-agents instructions"

        def _fake_urlopen(req, timeout=0):
            return _Resp()

        monkeypatch.setattr("super_dev.integrations.manager.urllib_request.urlopen", _fake_urlopen)

        result = manager.compare_official_capabilities("claude-code")
        assert result["status"] == "passed"
        assert result["reachable_urls"] >= 1
        checks = result["checks"]
        assert checks["slash"]["ok"] is True
        assert checks["rules"]["ok"] is True

    def test_verify_official_docs_fallbacks_head_to_get(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        manager = IntegrationManager(temp_project_dir)

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _fake_urlopen(req, timeout=0, context=None):
            method = req.get_method()
            if method == "HEAD":
                raise urllib_error.HTTPError(req.full_url, 405, "Method Not Allowed", {}, None)
            return _Resp()

        monkeypatch.setattr("super_dev.integrations.manager.urllib_request.urlopen", _fake_urlopen)

        result = manager.verify_official_docs("claude-code")
        assert result["status"] == "verified"
        assert result["reachable"] == result["checked"]
        assert all(item.get("method") == "GET" for item in result["details"])

    def test_qoder_rules_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("qoder", force=True)

        assert len(files) == 7
        agents_content = (temp_project_dir / "AGENTS.md").read_text(encoding="utf-8")
        rules_content = (temp_project_dir / ".qoder" / "rules" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        skill_content = (
            temp_project_dir / ".qoder" / "skills" / "super-dev" / "SKILL.md"
        ).read_text(encoding="utf-8")
        qoder_agent_content = (
            temp_project_dir / ".qoder" / "agents" / "super-dev.md"
        ).read_text(encoding="utf-8")
        seeai_skill = temp_project_dir / ".qoder" / "skills" / "super-dev-seeai" / "SKILL.md"
        seeai_command = temp_project_dir / ".qoder" / "commands" / "super-dev-seeai.md"
        assert "Super Dev" in agents_content
        assert "Super Dev" in rules_content
        assert "super-dev：" in skill_content
        assert "Super Dev Subagent" in qoder_agent_content
        assert seeai_command.exists()
        assert seeai_skill.exists()

    def test_cline_rules_and_project_skill_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("cline", force=True)

        assert len(files) == 3
        rules_content = (temp_project_dir / ".clinerules" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        skill_content = (
            temp_project_dir / ".cline" / "skills" / "super-dev" / "SKILL.md"
        ).read_text(encoding="utf-8")
        seeai_skill = temp_project_dir / ".cline" / "skills" / "super-dev-seeai" / "SKILL.md"
        assert "Super Dev" in rules_content
        assert "super-dev：" in skill_content
        assert seeai_skill.exists()

    def test_antigravity_context_and_workflow_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("antigravity", force=True)
        slash_file = manager.setup_slash_command(target="antigravity", force=True)

        assert len(files) == 4
        context_content = (temp_project_dir / "GEMINI.md").read_text(encoding="utf-8")
        workflow_content = (temp_project_dir / ".agent" / "workflows" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        seeai_command = temp_project_dir / ".gemini" / "commands" / "super-dev-seeai.toml"
        assert slash_file is not None
        command_content = slash_file.read_text(encoding="utf-8")
        assert "Super Dev" in context_content
        assert "/super-dev" in command_content
        assert "必须暂停等待用户确认" in workflow_content
        assert seeai_command.exists()

    def test_trae_project_and_compatibility_rules_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("trae", force=True)

        assert len(files) == 2
        project_rules = (temp_project_dir / ".trae" / "project_rules.md").read_text(
            encoding="utf-8"
        )
        compatibility_rules = (temp_project_dir / ".trae" / "rules.md").read_text(encoding="utf-8")
        assert "super-dev：" in project_rules
        assert "continue Super Dev" in project_rules
        assert project_rules == compatibility_rules

    def test_kimi_code_generates_agents_and_project_skill(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("kimi-code", force=True)

        assert len(files) == 4
        assert (temp_project_dir / "AGENTS.md").exists()
        assert (temp_project_dir / ".kimi" / "AGENTS.md").exists()
        skill_file = temp_project_dir / ".kimi" / "skills" / "super-dev" / "SKILL.md"
        seeai_skill_file = temp_project_dir / ".kimi" / "skills" / "super-dev-seeai" / "SKILL.md"
        assert skill_file.exists()
        assert seeai_skill_file.exists()
        content = skill_file.read_text(encoding="utf-8")
        assert "Kimi Code" in content or "super-dev:" in content

    def test_qwen_code_generates_project_agent_and_user_agent_surface(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("qwen-code", force=True)
        global_protocol = manager.setup_global_protocol("qwen-code", force=True)
        global_agents = manager.setup_global_agent_surfaces("qwen-code", force=True)

        assert len(files) == 6
        assert (temp_project_dir / "QWEN.md").exists()
        assert (temp_project_dir / ".qwen" / "commands" / "super-dev.md").exists()
        assert (temp_project_dir / ".qwen" / "skills" / "super-dev" / "SKILL.md").exists()
        assert (temp_project_dir / ".qwen" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
        agent_file = temp_project_dir / ".qwen" / "agents" / "super-dev.md"
        assert agent_file.exists()
        assert "Qwen Code subagent" in agent_file.read_text(encoding="utf-8")
        assert global_protocol == fake_home / ".qwen" / "QWEN.md"
        assert (fake_home / ".qwen" / "agents" / "super-dev.md") in global_agents

    def test_trae_solo_generates_rules_commands_and_skill(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("trae-solo", force=True)
        slash_file = manager.setup_slash_command(target="trae-solo", force=True)

        assert len(files) == 6
        assert (temp_project_dir / ".trae" / "rules" / "super-dev.md").exists()
        assert (temp_project_dir / ".trae" / "commands" / "super-dev.md").exists()
        assert (temp_project_dir / ".trae" / "commands" / "super-dev-seeai.md").exists()
        assert (temp_project_dir / ".trae" / "skills" / "super-dev" / "SKILL.md").exists()
        assert (temp_project_dir / ".trae" / "skills" / "super-dev-seeai" / "SKILL.md").exists()
        assert slash_file.resolve() == (temp_project_dir / ".trae" / "commands" / "super-dev.md").resolve()

    def test_trae_solocn_generates_rules_and_skill(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("trae-solocn", force=True)

        assert len(files) == 3
        assert (temp_project_dir / ".trae" / "rules" / "super-dev.md").exists()
        assert (temp_project_dir / ".trae" / "skills" / "super-dev" / "SKILL.md").exists()
        assert (temp_project_dir / ".trae" / "skills" / "super-dev-seeai" / "SKILL.md").exists()

    @pytest.mark.parametrize(
        ("target", "relative"),
        [
            ("claude-code", ".claude/skills/super-dev-seeai/SKILL.md"),
            ("qoder-cli", ".qoder/skills/super-dev-seeai/SKILL.md"),
            ("kiro-cli", ".kiro/skills/super-dev-seeai/SKILL.md"),
            ("opencode", ".opencode/skills/super-dev-seeai/SKILL.md"),
        ],
    )
    def test_setup_generates_managed_competition_project_skills(
        self, temp_project_dir: Path, target: str, relative: str
    ):
        manager = IntegrationManager(temp_project_dir)

        files = manager.setup(target, force=True)

        expected = temp_project_dir / relative
        assert expected.resolve() in {item.resolve() for item in files}
        assert expected.exists()
        assert "super-dev-seeai" in expected.read_text(encoding="utf-8")

    def test_collect_managed_surface_paths_includes_managed_competition_project_skill(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)

        surfaces = manager.collect_managed_surface_paths("qoder")

        expected = temp_project_dir / ".qoder" / "skills" / "super-dev-seeai" / "SKILL.md"
        assert (
            surfaces["project:.qoder/skills/super-dev-seeai/SKILL.md"].resolve()
            == expected.resolve()
        )

    def test_roo_code_rules_and_slash_command_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("roo-code", force=True)
        slash_file = manager.setup_slash_command(target="roo-code", force=True)

        assert len(files) == 2
        rules_content = (temp_project_dir / ".roo" / "rules" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        command_content = (temp_project_dir / ".roo" / "commands" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        assert "Super Dev" in rules_content
        assert "/super-dev" in command_content
        # roo-code no longer supports slash via host_registry, so setup_slash_command returns None
        assert slash_file is None

    def test_kilo_code_rules_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("kilo-code", force=True)

        assert len(files) == 3
        rules_content = (temp_project_dir / ".kilocode" / "rules" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        assert "Super Dev" in rules_content
        assert "super-dev：" in rules_content
        assert (temp_project_dir / ".kilocode" / "skills" / "super-dev" / "SKILL.md").exists()
        assert (
            temp_project_dir / ".kilocode" / "skills" / "super-dev-seeai" / "SKILL.md"
        ).exists()

    def test_slash_content_requires_host_research_first(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        content = manager._build_slash_command_content("claude-code")

        assert "output/*-research.md" in content
        assert "同类产品" in content
        assert "宿主原生联网" in content or "browse / search" in content
        assert "宿主负责调用自身模型" in content or "编码能力来自当前宿主" in content
        assert "Super Dev 是当前项目里的本地 Python 工具 + 宿主规则/Skill 协议" in content
        assert "output/knowledge-cache/*-knowledge-bundle.json" in content
        assert "首轮响应契约（首次触发必须执行）" in content
        assert "第一轮回复必须明确当前阶段是 `research`" in content
        assert "三份核心文档完成后会暂停并等待用户确认" in content
        assert "未经用户明确确认，不得进入 Spec 或编码" in content
        assert "先按 `tasks.md` 实现并运行前端" in content

    def test_trae_rules_require_workspace_artifacts_and_fullwidth_trigger(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)
        content = manager._trae_rules()

        assert "super-dev：" in content
        assert (
            "first natural-language requirement in a new session must also continue Super Dev"
            in content
        )
        assert "project workspace" in content
        assert "instead of only replying in chat" in content
        assert "treat the step as incomplete" in content

    def test_embedded_skill_and_host_specific_surfaces_require_written_artifacts(
        self, temp_project_dir: Path
    ):
        manager = IntegrationManager(temp_project_dir)

        embedded = manager._build_embedded_skill_content(
            "codex-cli", ".agents/skills/super-dev/SKILL.md"
        )
        antigravity = manager._build_antigravity_context_content()
        claude_agent = manager._build_claude_agent_content()
        codebuddy_agent = manager._build_codebuddy_agent_content()
        workflow = manager._antigravity_workflow_rules()

        assert "super-dev:" in embedded or "super-dev：" in embedded
        assert "必须真实写入项目文件" in embedded
        assert "SESSION_BRIEF" in embedded
        assert "Chat-only summaries do not count" in antigravity
        assert "write them as project files" in antigravity
        assert "workspace files" in claude_agent
        assert "chat-only summaries" in claude_agent
        assert "first natural-language requirement" in claude_agent
        assert "continue Super Dev" in claude_agent
        assert "workspace files" in codebuddy_agent
        assert "chat-only explanations" in codebuddy_agent
        assert "只在聊天里总结不算完成" in workflow
        assert "必须暂停等待用户确认" in workflow

    def test_managed_surfaces_all_pass_contract_audit(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        skill_manager = SkillManager(temp_project_dir)

        for target in IntegrationManager.TARGETS:
            manager.setup(target, force=True)
            manager.setup_global_protocol(target, force=True)
            if manager.supports_slash(target):
                manager.setup_slash_command(target, force=True)
                manager.setup_global_slash_command(target, force=True)
            if IntegrationManager.requires_skill(target):
                skill_root = skill_manager._target_dir(target)
                if skill_manager.target_path_kind(target) == "observed-compatibility-surface":
                    skill_root.mkdir(parents=True, exist_ok=True)
                if skill_manager.skill_surface_available(target):
                    skill_manager.install(
                        "super-dev", target=target, name="super-dev", force=True
                    )

            surfaces = manager.collect_managed_surface_paths(target)
            for _, path in surfaces.items():
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8")
                missing = manager.audit_surface_contract(target, _, path, content)
                assert missing == [], f"{target} surface {path} missing contract markers: {missing}"

    def test_generic_rules_emphasize_host_governance_boundary(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)

        cli_rules = manager._generic_cli_rules("cursor-cli")
        ide_rules = manager._generic_ide_rules("cursor")
        claude_rules = manager._claude_rules()

        assert "The host remains responsible for model execution" in cli_rules
        assert "Treat Super Dev as a local Python CLI plus host-side rules/skills" in cli_rules
        assert "First-Response Contract" in cli_rules
        assert (
            "the first natural-language requirement in a new host session must also default to continuing Super Dev"
            in cli_rules
        )
        assert "current phase is `research`" in cli_rules
        assert "stop after the three core documents and wait for approval" in cli_rules
        assert "Read relevant files under `knowledge/` before drafting documents." in cli_rules
        assert "wait for explicit confirmation before creating Spec or coding" in cli_rules
        assert ".super-dev/SESSION_BRIEF.md" in cli_rules
        assert "Do not silently exit Super Dev mode" in cli_rules
        assert "host remains responsible for actual coding" in ide_rules
        assert (
            "Read relevant files under `knowledge/` before drafting the three core documents."
            in ide_rules
        )
        assert (
            "Treat Super Dev as the local Python workflow tool plus this host rule file"
            in ide_rules
        )
        assert "First-Response Contract" in ide_rules
        assert (
            "the first natural-language requirement in a new host session must also default to continuing Super Dev"
            in ide_rules
        )
        assert "current phase is `research`" in ide_rules
        assert ".super-dev/SESSION_BRIEF.md" in ide_rules
        assert "Claude Code remains the execution host" in claude_rules
        assert (
            "Read relevant files under `knowledge/` before drafting PRD, architecture, and UIUX."
            in claude_rules
        )
        assert "First-Response Contract" in claude_rules
        assert "first natural-language requirement" in claude_rules
        assert "continuing Super Dev" in claude_rules
        assert "stop after the three core documents and wait for approval" in claude_rules
        assert "wait for explicit confirmation before creating Spec or coding" in claude_rules
        assert ".super-dev/SESSION_BRIEF.md" in claude_rules

    @pytest.mark.parametrize(
        "target, expected_file",
        list(IntegrationManager.SLASH_COMMAND_FILES.items()),
    )
    def test_setup_slash_command(self, temp_project_dir: Path, target: str, expected_file: str):
        manager = IntegrationManager(temp_project_dir)
        command_file = manager.setup_slash_command(target=target, force=True)

        if not manager.supports_slash(target):
            assert command_file is None
            return

        assert command_file is not None
        assert command_file.resolve() == (temp_project_dir / expected_file).resolve()
        assert command_file.exists()
        content = command_file.read_text(encoding="utf-8")
        if command_file.suffix == ".toml":
            assert "{{args}}" in content
            assert "super-dev pipeline" in content
        else:
            assert "/super-dev" in content
            assert "$ARGUMENTS" in content
            assert ("需求描述" in content) or ("$ARGUMENTS" in content)
            assert 'super-dev pipeline "$ARGUMENTS"' not in content

    def test_setup_injects_system_flow_contract_marker(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("qoder", force=True)
        assert files
        content = files[0].read_text(encoding="utf-8")
        assert "SUPER_DEV_FLOW_CONTRACT_V1" in content
        assert (
            "PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery"
            in content
        )

    def test_setup_global_slash_command(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        command_file = manager.setup_global_slash_command(target="claude-code", force=True)

        assert command_file is not None
        expected = fake_home / ".claude" / "commands" / "super-dev.md"
        assert command_file.resolve() == expected.resolve()
        assert expected.exists()

    def test_setup_global_slash_command_opencode_uses_config_dir(
        self,
        temp_project_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        command_file = manager.setup_global_slash_command(target="opencode", force=True)

        assert command_file is not None
        expected = fake_home / ".config" / "opencode" / "commands" / "super-dev.md"
        assert command_file.resolve() == expected.resolve()
        assert expected.exists()

    def test_opencode_setup_uses_root_agents_and_global_agents(
        self,
        temp_project_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        written = manager.setup("opencode", force=True)
        global_file = manager.setup_global_protocol(target="opencode", force=True)
        global_agents = manager.setup_global_agent_surfaces(target="opencode", force=True)

        root_agents = temp_project_dir / "AGENTS.md"
        project_agent = temp_project_dir / ".opencode" / "agents" / "super-dev.md"
        assert root_agents.resolve() in [item.resolve() for item in written]
        assert (
            temp_project_dir / ".opencode" / "skills" / "super-dev" / "SKILL.md"
        ).resolve() in [item.resolve() for item in written]
        assert project_agent.resolve() in [item.resolve() for item in written]
        assert root_agents.exists()
        assert project_agent.exists()
        root_content = root_agents.read_text(encoding="utf-8")
        project_agent_content = project_agent.read_text(encoding="utf-8")
        assert "BEGIN SUPER DEV OPENCODE" in root_content
        assert "/super-dev <需求描述>" in root_content
        assert "OpenCode subagent" in project_agent_content

        assert global_file is not None
        expected_global = fake_home / ".config" / "opencode" / "AGENTS.md"
        assert global_file.resolve() == expected_global.resolve()
        assert expected_global.exists()
        expected_global_agent = fake_home / ".config" / "opencode" / "agents" / "super-dev.md"
        assert expected_global_agent.resolve() in [item.resolve() for item in global_agents]
        assert expected_global_agent.exists()

    def test_qoder_setup_uses_project_and_global_agents(
        self,
        temp_project_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        written = manager.setup("qoder-cli", force=True)
        global_file = manager.setup_global_protocol(target="qoder-cli", force=True)
        global_agents = manager.setup_global_agent_surfaces(target="qoder-cli", force=True)

        project_agent = temp_project_dir / ".qoder" / "agents" / "super-dev.md"
        assert project_agent.resolve() in [item.resolve() for item in written]
        assert project_agent.exists()
        assert "Qoder subagent" in project_agent.read_text(encoding="utf-8")

        assert global_file is not None
        expected_global = fake_home / ".qoder" / "AGENTS.md"
        assert global_file.resolve() == expected_global.resolve()
        assert expected_global.exists()
        expected_global_agent = fake_home / ".qoder" / "agents" / "super-dev.md"
        assert expected_global_agent.resolve() in [item.resolve() for item in global_agents]
        assert expected_global_agent.exists()

    def test_collect_managed_surface_paths_includes_user_agent_surfaces_for_qoder(
        self,
        temp_project_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))

        manager = IntegrationManager(temp_project_dir)
        surfaces = manager.collect_managed_surface_paths(
            target="qoder-cli",
            include_user_surfaces=True,
        )

        expected_global_agent = fake_home / ".qoder" / "agents" / "super-dev.md"
        assert any(
            key.startswith("global-agent:") and path.resolve() == expected_global_agent.resolve()
            for key, path in surfaces.items()
        )

    def test_windsurf_rules_and_project_skill_generated(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        files = manager.setup("windsurf", force=True)
        workflow_file = manager.setup_slash_command(target="windsurf", force=True)

        assert len(files) == 6
        assert (temp_project_dir / "AGENTS.md").exists()
        rules_content = (temp_project_dir / ".windsurf" / "rules" / "super-dev.md").read_text(
            encoding="utf-8"
        )
        skill_content = (
            temp_project_dir / ".windsurf" / "skills" / "super-dev" / "SKILL.md"
        ).read_text(encoding="utf-8")
        seeai_workflow = (
            temp_project_dir / ".windsurf" / "workflows" / "super-dev-seeai.md"
        ).read_text(encoding="utf-8")
        seeai_skill = (
            temp_project_dir / ".windsurf" / "skills" / "super-dev-seeai" / "SKILL.md"
        )
        assert workflow_file is not None
        workflow_content = workflow_file.read_text(encoding="utf-8")
        assert "Super Dev" in rules_content
        assert "super-dev：" in skill_content
        assert "/super-dev" in workflow_content
        assert "/super-dev-seeai" in seeai_workflow
        assert seeai_skill.exists()

    def test_remove_opencode_preserves_codex_agents_block(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        manager.setup("codex-cli", force=True)
        manager.setup("opencode", force=True)

        agents = temp_project_dir / "AGENTS.md"
        content_before = agents.read_text(encoding="utf-8")
        assert "BEGIN SUPER DEV CODEX" in content_before
        assert "BEGIN SUPER DEV OPENCODE" in content_before

        manager.remove("opencode")

        content_after = agents.read_text(encoding="utf-8")
        assert "BEGIN SUPER DEV CODEX" in content_after
        assert "BEGIN SUPER DEV OPENCODE" not in content_after

    def test_skill_only_target_skips_slash_mapping(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        assert manager.supports_slash("codex-cli") is False
        assert manager.supports_slash("kiro-cli") is True
        assert manager.setup_slash_command(target="codex-cli", force=True) is None
        assert manager.setup_slash_command(target="kiro-cli", force=True) is not None
        assert manager.setup_global_slash_command(target="codex-cli", force=True) is None
        assert manager.setup_global_slash_command(target="kiro-cli", force=True) is not None
        assert manager.supports_slash("kiro") is True
        assert manager.supports_slash("qoder") is True
        assert manager.supports_slash("trae") is False
        assert manager.supports_slash("antigravity") is True
        assert manager.requires_skill("codebuddy") is True
        assert manager.setup_slash_command(target="kiro", force=True) is not None
        assert manager.setup_slash_command(target="qoder", force=True) is not None
        assert manager.setup_slash_command(target="antigravity", force=True) is not None
        assert manager.setup_slash_command(target="trae", force=True) is None
        assert manager.setup_global_slash_command(target="trae", force=True) is None

    @pytest.mark.parametrize(
        ("target", "command_file"),
        [
            ("antigravity", ".gemini/commands/super-dev.toml"),
            ("codebuddy", ".codebuddy/commands/super-dev.md"),
            ("cursor", ".cursor/commands/super-dev.md"),
            ("kiro", ".kiro/steering/super-dev.md"),
            ("kiro-cli", ".kiro/steering/super-dev.md"),
            ("windsurf", ".windsurf/workflows/super-dev.md"),
            ("gemini-cli", ".gemini/commands/super-dev.toml"),
            ("opencode", ".opencode/commands/super-dev.md"),
            ("qoder", ".qoder/commands/super-dev.md"),
        ],
    )
    def test_verified_hosts_preserve_native_slash_model(
        self,
        temp_project_dir: Path,
        target: str,
        command_file: str,
    ):
        manager = IntegrationManager(temp_project_dir)
        profile = manager.get_adapter_profile(target)

        assert manager.supports_slash(target) is True
        assert profile.usage_mode == "native-slash"
        assert profile.trigger_command == "/super-dev <需求描述>"
        assert profile.slash_command_file == command_file

    @pytest.mark.parametrize("target", ["codex-cli", "opencode", "claude-code", "cursor"])
    def test_host_rules_embed_ui_governance_constraints(self, temp_project_dir: Path, target: str):
        manager = IntegrationManager(temp_project_dir)
        written = manager.setup(target, force=True)
        assert written

        merged = "\n".join(path.read_text(encoding="utf-8") for path in written if path.exists())
        assert "emoji" in merged.lower()
        assert "图标库" in merged or "icon" in merged.lower()
        assert "output/*-uiux.md" in merged
        assert "Claude / ChatGPT" in merged or "claude / chatgpt" in merged.lower()
        assert "design token" in merged.lower() or "design tokens" in merged.lower()

    @pytest.mark.parametrize("target", PRIMARY_HOST_TOOL_IDS)
    def test_primary_hosts_always_embed_uiux_and_continuity_contracts(
        self, temp_project_dir: Path, target: str
    ):
        manager = IntegrationManager(temp_project_dir)
        written = manager.setup(target, force=True)

        if not written:
            # Hybrid hosts (e.g. workbuddy) have no file-based integration surfaces
            pytest.skip(f"{target} setup produces no integration files (hybrid host)")

        merged = "\n".join(path.read_text(encoding="utf-8") for path in written if path.exists())
        lowered = merged.lower()
        assert "output/*-uiux.md" in merged
        assert ".super-dev/SESSION_BRIEF.md" in merged
        assert "emoji" in lowered
        assert "design token" in lowered

    def test_codex_rules_require_ui_contract_before_implementation(self, temp_project_dir: Path):
        manager = IntegrationManager(temp_project_dir)
        manager.setup("codex-cli", force=True)

        agents = temp_project_dir / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        assert "开始任何 UI 实现前" in content
        assert "图标库" in content
        assert "output/*-uiux.md" in content
        assert "emoji" in content.lower()
