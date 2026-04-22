"""
Skill 管理测试
"""

from pathlib import Path

import pytest

from super_dev.skills import SkillManager


class TestSkillManager:
    def test_managed_builtin_skill_names_exclude_legacy_aliases(self):
        legacy_names = SkillManager.legacy_cleanup_skill_names()
        assert SkillManager.managed_builtin_skill_names("codex-cli") == [
            "super-dev",
            "super-dev-seeai",
        ]
        assert legacy_names[0] not in SkillManager.managed_builtin_skill_names("claude-code")
        assert legacy_names == [f"{SkillManager.DEFAULT_SKILL_NAME}-core"]

    def test_coverage_gaps_are_empty(self):
        gaps = SkillManager.coverage_gaps()
        assert gaps["missing_in_skill_targets"] == []
        assert gaps["extra_in_skill_targets"] == []

    def test_target_path_kind_distinguishes_official_and_observed(self):
        assert SkillManager.target_path_kind("antigravity") == "official-user-surface"
        assert SkillManager.target_path_kind("claude-code") == "official-user-surface"
        assert SkillManager.target_path_kind("cline") == "official-user-surface"
        assert SkillManager.target_path_kind("qoder-cli") == "official-user-surface"
        assert SkillManager.target_path_kind("kimi-code") == "official-user-surface"
        assert SkillManager.target_path_kind("trae-solocn") == "official-user-surface"
        assert SkillManager.target_path_kind("trae") == "observed-compatibility-surface"
        assert SkillManager.target_path_kind("trae-solo") == "observed-compatibility-surface"
        assert SkillManager.TARGET_PATHS["antigravity"] == "~/.gemini/skills"
        assert SkillManager.TARGET_PATHS["claude-code"] == "~/.claude/skills"
        assert SkillManager.TARGET_PATHS["cline"] == "~/.cline/skills"
        assert SkillManager.TARGET_PATHS["codex-cli"] == "~/.agents/skills"
        assert SkillManager.COMPATIBILITY_MIRROR_PATHS["kimi-code"] == [
            "~/.config/agents/skills",
            "~/.agents/skills",
        ]
        assert SkillManager.TARGET_PATHS["qoder"] == "~/.qoder/skills"
        assert SkillManager.TARGET_PATHS["kiro"] == "~/.kiro/skills"
        assert SkillManager.TARGET_PATHS["windsurf"] == "~/.codeium/windsurf/skills"
        assert SkillManager.TARGET_PATHS["opencode"] == "~/.config/opencode/skills"
        assert SkillManager.TARGET_PATHS["kimi-code"] == "~/.kimi/skills"
        assert SkillManager.TARGET_PATHS["trae-solocn"] == "~/.trae-cn/skills"

    def test_install_from_directory_and_uninstall(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        source_skill = temp_project_dir / "my-skill"
        source_skill.mkdir(parents=True, exist_ok=True)
        (source_skill / "SKILL.md").write_text("# My Skill", encoding="utf-8")

        manager = SkillManager(temp_project_dir)
        result = manager.install(
            source=str(source_skill),
            target="codex-cli",
            name="my-skill",
        )

        assert result.path.exists()
        assert "my-skill" in manager.list_installed("codex-cli")

        removed = manager.uninstall("my-skill", "codex-cli")
        assert not removed.exists()

    @pytest.mark.parametrize(
        "target",
        list(SkillManager.TARGET_PATHS.keys()),
    )
    def test_install_builtin_skill(self, temp_project_dir: Path, target: str, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = SkillManager(temp_project_dir)
        result = manager.install(source="super-dev", target=target, name="super-dev")

        assert result.path.exists()
        assert (result.path / "SKILL.md").exists()
        skill_content = (result.path / "SKILL.md").read_text(encoding="utf-8")
        assert skill_content.startswith("---\nname: super-dev\n")
        assert "当前宿主负责调用模型、工具、终端与实际代码修改" in skill_content
        assert "Super Dev 不是大模型平台" in skill_content
        assert "Runtime Contract（强制）" in skill_content
        assert "首轮响应契约（强制）" in skill_content
        assert "当前阶段是 `research`" in skill_content
        assert "三份核心文档完成后暂停等待确认" in skill_content
        assert "本地知识库契约（强制）" in skill_content
        assert "output/knowledge-cache/*-knowledge-bundle.json" in skill_content
        assert "未经用户确认禁止创建 `.super-dev/changes/*`" in skill_content
        assert "super-dev：" in skill_content
        assert ".super-dev/SESSION_BRIEF.md" in skill_content
        assert "确认门/返工门" in skill_content
        assert "super-dev" in manager.list_installed(target)

        removed = manager.uninstall("super-dev", target)
        assert not removed.exists()

    def test_codex_builtin_skill_no_duplicate_mirrors(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = SkillManager(temp_project_dir)

        legacy_name = SkillManager.legacy_cleanup_skill_names()[0]
        result = manager.install(source="super-dev", target="codex-cli", name="super-dev")

        primary_skill = result.path / "SKILL.md"
        metadata_file = result.path / "agents" / "openai.yaml"
        assert primary_skill.exists()
        assert metadata_file.exists()
        # No mirrors should exist in ~/.codex/skills/
        codex_mirror = fake_home / ".codex" / "skills" / "super-dev" / "SKILL.md"
        codex_legacy_mirror = fake_home / ".codex" / "skills" / legacy_name / "SKILL.md"
        assert not codex_mirror.exists()
        assert not codex_legacy_mirror.exists()
        # Legacy skill alias should not exist in ~/.agents/skills/
        agents_legacy = fake_home / ".agents" / "skills" / legacy_name / "SKILL.md"
        assert not agents_legacy.exists()
        primary_content = primary_skill.read_text(encoding="utf-8")
        metadata_content = metadata_file.read_text(encoding="utf-8")
        assert "Do not answer with variants of" in primary_content
        assert "$super-dev" in primary_content
        assert "interface:" in metadata_content
        assert 'display_name: "Super Dev"' in metadata_content
        assert "$super-dev" in metadata_content
        assert "slash skill list" in metadata_content
        assert "allow_implicit_invocation: true" in metadata_content
        assert {"super-dev", "super-dev-seeai"} == set(manager.list_installed("codex-cli"))

        manager.uninstall("super-dev", "codex-cli")
        assert not primary_skill.exists()

    def test_codex_builtin_skill_installs_seeai_metadata(self, temp_project_dir: Path, monkeypatch):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = SkillManager(temp_project_dir)

        manager.install(source="super-dev", target="codex-cli", name="super-dev")

        seeai_skill = fake_home / ".agents" / "skills" / "super-dev-seeai" / "SKILL.md"
        metadata_file = (
            fake_home / ".agents" / "skills" / "super-dev-seeai" / "agents" / "openai.yaml"
        )
        assert seeai_skill.exists()
        assert metadata_file.exists()
        seeai_content = seeai_skill.read_text(encoding="utf-8")
        assert "$super-dev-seeai" in seeai_content
        assert "比赛短文档模板" in seeai_content
        assert "首轮输出模板（强制）" in seeai_content
        assert "`P0 主路径`" in seeai_content
        assert "# 作品目标" in seeai_content
        assert "官网类" in seeai_content
        assert "默认技术栈：React/Vite 或 Next.js + Tailwind + Framer Motion" in seeai_content
        assert "默认 sprint：主循环可玩 -> 积分/胜负反馈 -> 特效/音效 -> 复玩和 polish" in seeai_content
        assert "题型识别提示" in seeai_content
        assert "品牌、官网、落地页、活动宣传、首屏" in seeai_content
        assert "时间不够时优先删功能，不要删完成度、动效记忆点和演示闭环" in seeai_content
        assert "SEEAI 比赛设计系统（强制）" in seeai_content
        assert "Arena Neon" in seeai_content
        assert "SEEAI 执行守卫（强制）" in seeai_content
        assert "12 分钟内必须跑出第一个可见" in seeai_content
        assert "模块真实生效规则" in seeai_content
        assert "每个保留下来的模块都必须真实启动" in seeai_content
        assert "初始化失败一次后，立刻切到更轻的备选栈" in seeai_content
        assert "评委视角自检" in seeai_content
        metadata_content = metadata_file.read_text(encoding="utf-8")
        assert 'display_name: "Super Dev SEEAI"' in metadata_content
        assert "$super-dev-seeai" in metadata_content

    def test_codex_no_compatibility_mirror_when_codex_home_set(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        codex_home = temp_project_dir / "custom-codex-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        codex_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.setenv("CODEX_HOME", str(codex_home))
        manager = SkillManager(temp_project_dir)

        result = manager.install(source="super-dev", target="codex-cli", name="super-dev")

        legacy_name = SkillManager.legacy_cleanup_skill_names()[0]
        assert (result.path / "SKILL.md").exists()
        # No mirror should be created in CODEX_HOME since we removed codex-cli mirrors
        assert not (codex_home / "skills" / "super-dev" / "SKILL.md").exists()
        assert not (codex_home / "skills" / legacy_name / "SKILL.md").exists()

    def test_cleanup_legacy_skill_aliases_removes_legacy_alias(
        self, temp_project_dir: Path, monkeypatch
    ):
        fake_home = temp_project_dir / "fake-home"
        fake_home.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("HOME", str(fake_home))
        manager = SkillManager(temp_project_dir)

        legacy_name = SkillManager.legacy_cleanup_skill_names()[0]
        legacy_dir = fake_home / ".agents" / "skills" / legacy_name
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "SKILL.md").write_text("# legacy", encoding="utf-8")

        removed = manager.cleanup_legacy_skill_aliases("codex-cli")

        assert removed == [legacy_name]
        assert not legacy_dir.exists()
