"""Tests for the formal host registry module."""

from super_dev.host_registry import (
    HOST_REGISTRY,
    HostInstallMode,
    get_display_name,
    get_docs,
    get_host_definition,
    get_install_mode,
    get_protocol_mode,
    get_protocol_summary,
    get_triggers,
    list_host_ids,
    list_hybrid_hosts,
    list_manual_hosts,
    list_project_hosts,
    supports_slash,
)


def test_registry_exposes_key_and_manual_hosts():
    host_ids = set(list_host_ids())

    assert {
        "claude",
        "claude-code",
        "codex",
        "codex-cli",
        "codebuddy-cli",
        "codebuddy",
        "codebuddy-cn",
        "droid-cli",
        "kimi-code",
        "qwen-code",
        "trae-cn",
        "trae-solo",
        "trae-solocn",
        "vscode-copilot",
        "workbuddy",
    }.issubset(host_ids)
    assert len(host_ids) == len(list_host_ids())


def test_registry_helpers_return_expected_host_metadata():
    claude = get_host_definition("claude-code")
    assert claude is not None
    assert get_display_name("claude-code") == "Claude Code"
    assert get_install_mode("claude-code") == HostInstallMode.HYBRID
    assert get_protocol_mode("claude-code") == "official-skill"
    assert (
        get_protocol_summary("claude-code")
        == "官方 CLAUDE.md + settings + project/user skills + subagents"
    )
    assert supports_slash("claude-code") is True
    assert "/super-dev" in get_triggers("claude-code")
    assert "Project root `CLAUDE.md`" in get_docs("claude-code")
    assert "User-level `~/.claude/skills/super-dev/`" in get_docs("claude-code")

    claude_app = get_host_definition("claude")
    assert claude_app is not None
    assert get_display_name("claude") == "Claude"
    assert get_install_mode("claude") == HostInstallMode.MANUAL
    assert get_protocol_mode("claude") == "official-projects"
    assert (
        get_protocol_summary("claude")
        == "官方 Projects + project instructions + project knowledge + desktop extensions/MCP"
    )
    assert supports_slash("claude") is False

    codex_app = get_host_definition("codex")
    assert codex_app is not None
    assert get_display_name("codex") == "Codex"
    assert get_install_mode("codex") == HostInstallMode.HYBRID
    assert get_protocol_mode("codex") == "official-skill"
    assert (
        get_protocol_summary("codex")
        == "官方 AGENTS.md + Skills + App/Desktop enabled Skill entry"
    )
    assert supports_slash("codex") is False

    codex = get_host_definition("codex-cli")
    assert codex is not None
    assert get_protocol_mode("codex-cli") == "official-skill"
    assert (
        get_protocol_summary("codex-cli")
        == "官方 AGENTS.md + Skills + CLI $skill entry"
    )
    assert supports_slash("codex-cli") is False

    codebuddy = get_host_definition("codebuddy")
    assert codebuddy is not None
    assert get_protocol_mode("codebuddy") == "official-subagent"
    assert (
        get_protocol_summary("codebuddy")
        == "官方 CODEBUDDY.md + rules + skills + task/workspace continuity"
    )
    assert supports_slash("codebuddy") is True

    droid = get_host_definition("droid-cli")
    assert droid is not None
    assert get_display_name("droid-cli") == "Droid CLI"
    assert get_install_mode("droid-cli") == HostInstallMode.HYBRID
    assert get_protocol_mode("droid-cli") == "official-factory"
    assert (
        get_protocol_summary("droid-cli")
        == "官方 AGENTS.md + .factory/rules + skills (+ legacy commands)"
    )
    assert supports_slash("droid-cli") is True
    assert "/super-dev-seeai" in get_triggers("droid-cli")
    assert "Project-level `.factory/skills/`" in get_docs("droid-cli")
    assert "Project-level `.factory/commands/` (legacy slash compatibility)" in get_docs(
        "droid-cli"
    )

    kimi = get_host_definition("kimi-code")
    assert kimi is not None
    assert get_display_name("kimi-code") == "Kimi Code"
    assert get_install_mode("kimi-code") == HostInstallMode.HYBRID
    assert get_protocol_mode("kimi-code") == "official-agents-entry"
    assert (
        get_protocol_summary("kimi-code")
        == "AGENTS.md + explicit /skill:/flow entries + native session resume"
    )
    assert supports_slash("kimi-code") is False
    assert "Project root `AGENTS.md`" in get_docs("kimi-code")
    assert "Current explicit entries used by this integration: `/skill:super-dev` and `/flow:super-dev`" in get_docs(
        "kimi-code"
    )

    copilot_cli = get_host_definition("copilot-cli")
    assert copilot_cli is not None
    assert (
        get_protocol_summary("copilot-cli")
        == "官方 copilot-instructions + AGENTS.md + skills + agents"
    )
    assert "Project root `AGENTS.md`" in get_docs("copilot-cli")
    assert "User-level `~/.copilot/copilot-instructions.md`" in get_docs("copilot-cli")
    assert "User-level `~/.copilot/agents/`" in get_docs("copilot-cli")

    codebuddy_cli = get_host_definition("codebuddy-cli")
    assert codebuddy_cli is not None
    assert (
        get_protocol_summary("codebuddy-cli")
        == "官方 CODEBUDDY.md + rules + commands + skills + agents"
    )
    assert "Project-level `.codebuddy/rules/`" in get_docs("codebuddy-cli")
    assert "Project-level `.codebuddy/agents/`" in get_docs("codebuddy-cli")

    cursor_cli = get_host_definition("cursor-cli")
    assert cursor_cli is not None
    assert get_protocol_summary("cursor-cli") == "官方 AGENTS.md + .cursor/rules + native resume"
    assert "Project root `AGENTS.md`" in get_docs("cursor-cli")
    assert "Project-level `.cursor/rules/`" in get_docs("cursor-cli")

    qwen = get_host_definition("qwen-code")
    assert qwen is not None
    assert (
        get_protocol_summary("qwen-code")
        == "官方 QWEN.md + settings + commands + skills + agents + /resume"
    )
    assert "Project-level `.qwen/agents/`" in get_docs("qwen-code")
    assert "User-level `~/.qwen/QWEN.md`" in get_docs("qwen-code")
    assert "User-level `~/.qwen/agents/`" in get_docs("qwen-code")

    opencode = get_host_definition("opencode")
    assert opencode is not None
    assert get_protocol_summary("opencode") == "官方 AGENTS.md + commands + skills (+ optional agents)"
    assert "Optional project-level `.opencode/agents/`" in get_docs("opencode")
    assert "Optional user-level `~/.config/opencode/agents/`" in get_docs("opencode")

    qoder_cli = get_host_definition("qoder-cli")
    assert qoder_cli is not None
    assert (
        get_protocol_summary("qoder-cli")
        == "官方 AGENTS.md + rules + commands + skills (+ optional agents)"
    )
    assert "Project root `AGENTS.md`" in get_docs("qoder-cli")
    assert "Optional project-level `.qoder/agents/`" in get_docs("qoder-cli")
    assert "Optional user-level `~/.qoder/agents/`" in get_docs("qoder-cli")

    cursor_ide = get_host_definition("cursor")
    assert cursor_ide is not None
    assert get_display_name("cursor") == "Cursor"
    assert get_protocol_summary("cursor") == "官方 Agent Chat + AGENTS.md + rules (+ beta commands)"
    assert "Optional project-level `.cursor/commands/` (beta)" in get_docs("cursor")

    kiro_cli = get_host_definition("kiro-cli")
    assert kiro_cli is not None
    assert get_protocol_summary("kiro-cli") == "官方 AGENTS.md + steering + skills + native resume"
    assert "Project root `AGENTS.md`" in get_docs("kiro-cli")

    kiro_ide = get_host_definition("kiro")
    assert kiro_ide is not None
    assert get_protocol_summary("kiro") == "官方 AGENTS.md + steering + skills + agent continuity"
    assert "Project root `AGENTS.md`" in get_docs("kiro")

    trae_solo = get_host_definition("trae-solo")
    assert trae_solo is not None
    assert get_display_name("trae-solo") == "Trae SOLO"
    assert get_install_mode("trae-solo") == HostInstallMode.PROJECT
    assert get_protocol_mode("trae-solo") == "workspace-rules-commands-skills"
    assert supports_slash("trae-solo") is True

    trae_solocn = get_host_definition("trae-solocn")
    assert trae_solocn is not None
    assert get_display_name("trae-solocn") == "Trae SOLOCN"
    assert get_install_mode("trae-solocn") == HostInstallMode.HYBRID
    assert get_protocol_mode("trae-solocn") == "workspace-mtc-code-skills"
    assert supports_slash("trae-solocn") is False

    copilot = get_host_definition("vscode-copilot")
    assert copilot is not None
    assert get_display_name("vscode-copilot") == "Copilot"
    assert get_install_mode("vscode-copilot") == HostInstallMode.PROJECT
    assert get_protocol_mode("vscode-copilot") == "official-context"
    assert supports_slash("vscode-copilot") is False

    workbuddy = get_host_definition("workbuddy")
    assert workbuddy is not None
    assert get_display_name("workbuddy") == "WorkBuddy"
    assert get_install_mode("workbuddy") == HostInstallMode.HYBRID
    assert get_protocol_mode("workbuddy") == "manual-task-workbench-mcp"
    assert get_protocol_summary("workbuddy") == "当前推荐任务工作台模型: Skills + MCP + task continuity"
    assert supports_slash("workbuddy") is False
    assert "super-dev-seeai:" in get_triggers("workbuddy")
    assert "WorkBuddy 技能市场 / 技能导入" in get_docs("workbuddy")


def test_registry_groups_by_install_mode():
    manual_hosts = {item.host_id for item in list_manual_hosts()}
    hybrid_hosts = {item.host_id for item in list_hybrid_hosts()}
    project_hosts = {item.host_id for item in list_project_hosts()}

    assert manual_hosts == {"claude"}
    assert {
        "claude-code",
        "codex",
        "codex-cli",
        "codebuddy-cli",
        "codebuddy",
        "codebuddy-cn",
        "droid-cli",
        "kimi-code",
        "qwen-code",
        "trae-cn",
        "trae-solocn",
        "workbuddy",
    }.issubset(hybrid_hosts)
    assert {
        "cursor",
        "cursor-cli",
        "roo-code",
        "kilo-code",
        "vscode-copilot",
        "trae-solo",
    }.issubset(project_hosts)
    assert manual_hosts.isdisjoint(hybrid_hosts)
    assert manual_hosts.isdisjoint(project_hosts)


def test_registry_protocol_fields_are_populated_for_key_hosts():
    key_hosts = {
        "antigravity",
        "claude-code",
        "claude",
        "codebuddy-cli",
        "codebuddy",
        "codebuddy-cn",
        "codex",
        "codex-cli",
        "droid-cli",
        "gemini-cli",
        "kimi-code",
        "kiro",
        "kiro-cli",
        "qoder",
        "qoder-cli",
        "qwen-code",
        "trae-cn",
        "trae-solo",
        "trae-solocn",
        "vscode-copilot",
        "windsurf",
        "workbuddy",
    }

    for host_id in key_hosts:
        assert get_protocol_mode(host_id)
        assert get_protocol_summary(host_id)


def test_registry_is_frozen_and_unknown_hosts_are_safe():
    definition = get_host_definition("does-not-exist")
    assert definition is None
    assert get_display_name("does-not-exist") is None
    assert get_install_mode("does-not-exist") is None
    assert get_protocol_mode("does-not-exist") is None
    assert get_protocol_summary("does-not-exist") is None
    assert get_triggers("does-not-exist") == ()
    assert get_docs("does-not-exist") == ()
    assert supports_slash("does-not-exist") is False
    assert HOST_REGISTRY.require("claude-code").host_id == "claude-code"
