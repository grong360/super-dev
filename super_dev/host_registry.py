"""Formal host registry for Super Dev.

This module keeps host metadata in one place so callers can read display names,
install modes, trigger surfaces, and documentation surfaces without depending
on the larger integration manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HostInstallMode(str, Enum):
    """How a host is installed and maintained."""

    PROJECT = "project"
    USER = "user"
    HYBRID = "hybrid"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class HostDefinition:
    """Immutable metadata for a supported host."""

    host_id: str
    display_name: str
    install_mode: HostInstallMode
    protocol_mode: str
    protocol_summary: str
    supports_slash: bool
    triggers: tuple[str, ...]
    docs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HostRegistry:
    """Read-only registry with lookup helpers."""

    definitions: tuple[HostDefinition, ...]
    _by_id: dict[str, HostDefinition] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        by_id: dict[str, HostDefinition] = {}
        duplicates: list[str] = []
        for definition in self.definitions:
            if definition.host_id in by_id:
                duplicates.append(definition.host_id)
            by_id[definition.host_id] = definition
        if duplicates:
            duplicate_list = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"Duplicate host ids in registry: {duplicate_list}")
        object.__setattr__(self, "_by_id", by_id)

    def get(self, host_id: str) -> HostDefinition | None:
        return self._by_id.get(host_id)

    def require(self, host_id: str) -> HostDefinition:
        definition = self.get(host_id)
        if definition is None:
            raise KeyError(host_id)
        return definition

    def list_host_ids(self) -> tuple[str, ...]:
        return tuple(definition.host_id for definition in self.definitions)

    def list_by_install_mode(self, install_mode: HostInstallMode) -> tuple[HostDefinition, ...]:
        return tuple(
            definition for definition in self.definitions if definition.install_mode == install_mode
        )

    def list_manual_hosts(self) -> tuple[HostDefinition, ...]:
        return self.list_by_install_mode(HostInstallMode.MANUAL)

    def list_hybrid_hosts(self) -> tuple[HostDefinition, ...]:
        return self.list_by_install_mode(HostInstallMode.HYBRID)

    def list_project_hosts(self) -> tuple[HostDefinition, ...]:
        return self.list_by_install_mode(HostInstallMode.PROJECT)

    def list_user_hosts(self) -> tuple[HostDefinition, ...]:
        return self.list_by_install_mode(HostInstallMode.USER)


def _tuple(*items: str) -> tuple[str, ...]:
    return tuple(item for item in items if item)


DEFAULT_HOST_REGISTRY = HostRegistry(
    definitions=(
        HostDefinition(
            host_id="antigravity",
            display_name="Antigravity",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="recommended-gemini-workflow",
            protocol_summary="当前推荐接入模型: GEMINI.md + custom commands + optional workflows",
            supports_slash=True,
            triggers=_tuple("super-dev: <需求描述>", "super-dev：<需求描述>", "/super-dev"),
            docs=_tuple(
                "Project root `GEMINI.md`",
                "Project-level `.gemini/commands/` (custom commands)",
                "Current recommended enhancement: `.agent/workflows/`",
                "Optional user-level `~/.gemini/GEMINI.md` (`--with-user-surfaces`)",
                "Optional user-level `~/.gemini/commands/` (`--with-user-surfaces`)",
                "Current compatibility enhancement: `~/.gemini/skills/super-dev/SKILL.md`",
            ),
        ),
        HostDefinition(
            host_id="claude",
            display_name="Claude",
            install_mode=HostInstallMode.MANUAL,
            protocol_mode="official-projects",
            protocol_summary="官方 Projects + project instructions + project knowledge + desktop extensions/MCP",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "Claude Projects",
                "Claude Project Instructions",
                "Claude Project Knowledge",
                "Claude Desktop extensions / local MCP",
            ),
        ),
        HostDefinition(
            host_id="claude-code",
            display_name="Claude Code",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 CLAUDE.md + settings + project/user skills + subagents",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `CLAUDE.md`",
                "Project-level `.claude/CLAUDE.md`",
                "Optional project-level `.claude/settings.json`",
                "Optional project-level `.claude/settings.local.json`",
                "Project-level `.claude/skills/super-dev/`",
                "Project-level `.claude/agents/super-dev.md`",
                "Optional user-level `~/.claude/CLAUDE.md` (`--with-user-surfaces`)",
                "Optional user-level `~/.claude/settings.json` (`--with-user-surfaces`)",
                "User-level `~/.claude/skills/super-dev/`",
                "User-level `~/.claude/agents/super-dev.md`",
                "Optional project-level `.claude/commands/super-dev.md`",
            ),
        ),
        HostDefinition(
            host_id="cline",
            display_name="Cline",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-context",
            protocol_summary="官方 .clinerules + skills + AGENTS.md compatibility",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.clinerules/`",
                "Project-level `.cline/skills/`",
                "User-level `~/.cline/skills/super-dev/SKILL.md`",
            ),
        ),
        HostDefinition(
            host_id="codebuddy-cli",
            display_name="CodeBuddy CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-subagent",
            protocol_summary="官方 CODEBUDDY.md + rules + commands + skills + agents",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `CODEBUDDY.md`",
                "Project-level `.codebuddy/rules/`",
                "Project-level `.codebuddy/commands/`",
                "Project-level `.codebuddy/skills/`",
                "Project-level `.codebuddy/agents/`",
                "User-level `~/.codebuddy/CODEBUDDY.md`",
                "User-level `~/.codebuddy/rules/`",
                "User-level `~/.codebuddy/skills/`",
                "User-level `~/.codebuddy/agents/`",
            ),
        ),
        HostDefinition(
            host_id="codebuddy",
            display_name="CodeBuddy",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-subagent",
            protocol_summary="官方 CODEBUDDY.md + rules + skills + task/workspace continuity",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `CODEBUDDY.md`",
                "Project-level `.codebuddy/rules/`",
                "Project-level `.codebuddy/skills/`",
                "User-level `~/.codebuddy/CODEBUDDY.md`",
                "User-level `~/.codebuddy/skills/`",
                "Current implementation enhancements: `.codebuddy/commands/` + `.codebuddy/agents/`",
            ),
        ),
        HostDefinition(
            host_id="codebuddy-cn",
            display_name="CodeBuddyCN",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-subagent",
            protocol_summary="官方 CODEBUDDY.md + rules + skills + 中文任务/workspace continuity",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `CODEBUDDY.md`",
                "Project-level `.codebuddy/rules/`",
                "Project-level `.codebuddy/skills/`",
                "User-level `~/.codebuddy/CODEBUDDY.md`",
                "User-level `~/.codebuddy/skills/`",
                "Current implementation enhancements: `.codebuddy/commands/` + `.codebuddy/agents/`",
            ),
        ),
        HostDefinition(
            host_id="droid-cli",
            display_name="Droid CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-factory",
            protocol_summary="官方 AGENTS.md + .factory/rules + skills (+ legacy commands)",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.factory/rules/`",
                "Project-level `.factory/skills/`",
                "Project-level `.factory/commands/` (legacy slash compatibility)",
                "Optional user-level `~/.factory/AGENTS.md` (`--with-user-surfaces`)",
                "User-level `~/.factory/skills/`",
                "Optional user-level `~/.factory/commands/` (`--with-user-surfaces`)",
            ),
        ),
        HostDefinition(
            host_id="codex",
            display_name="Codex",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 AGENTS.md + Skills + App/Desktop enabled Skill entry",
            supports_slash=False,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.agents/skills/super-dev/`",
                "Project-level `.agents/skills/super-dev-seeai/`",
                "User-level `~/.agents/skills/super-dev/`",
                "Optional user-level `~/.codex/AGENTS.md` (`--with-user-surfaces`)",
            ),
        ),
        HostDefinition(
            host_id="codex-cli",
            display_name="Codex CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 AGENTS.md + Skills + CLI $skill entry",
            supports_slash=False,
            triggers=_tuple("$super-dev", "$super-dev-seeai", "super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.agents/skills/super-dev/`",
                "Project-level `.agents/skills/super-dev-seeai/`",
                "User-level `~/.agents/skills/super-dev/`",
                "User-level `~/.agents/skills/super-dev-seeai/`",
                "Optional repo plugin enhancement: `.agents/plugins/marketplace.json`",
                "Optional user-level `~/.codex/AGENTS.md` (`--with-user-surfaces`)",
            ),
        ),
        HostDefinition(
            host_id="copilot-cli",
            display_name="Copilot CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-context",
            protocol_summary="官方 copilot-instructions + AGENTS.md + skills + agents",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project root `.github/copilot-instructions.md`",
                "Project-level `.github/instructions/**/*.instructions.md`",
                "Project-level `.github/agents/`",
                "Project-level `.github/skills/`",
                "User-level `~/.copilot/copilot-instructions.md`",
                "User-level `~/.copilot/agents/`",
                "User-level `~/.copilot/skills/`",
                "Optional custom instructions dirs via `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`",
            ),
        ),
        HostDefinition(
            host_id="cursor-cli",
            display_name="Cursor CLI",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-context",
            protocol_summary="官方 AGENTS.md + .cursor/rules + native resume",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.cursor/rules/`",
                "Optional root `CLAUDE.md` compatibility context",
                "Cursor Settings > User Rules",
            ),
        ),
        HostDefinition(
            host_id="cursor",
            display_name="Cursor",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-context",
            protocol_summary="官方 Agent Chat + AGENTS.md + rules (+ beta commands)",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.cursor/rules/`",
                "Optional root `CLAUDE.md` compatibility context",
                "Optional project-level `.cursor/commands/` (beta)",
                "Cursor Settings > User Rules",
            ),
        ),
        HostDefinition(
            host_id="gemini-cli",
            display_name="Gemini CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-context",
            protocol_summary="官方 GEMINI.md + settings + custom commands",
            supports_slash=True,
            triggers=_tuple("super-dev:", "super-dev：", "/super-dev"),
            docs=_tuple(
                "Project root `GEMINI.md`",
                "Project-level `.gemini/commands/`",
                "Optional project-level `.gemini/settings.json`",
                "Optional user-level `~/.gemini/GEMINI.md` (`--with-user-surfaces`)",
                "Optional user-level `~/.gemini/commands/` (`--with-user-surfaces`)",
                "Optional user-level `~/.gemini/settings.json` (`--with-user-surfaces`)",
                "Current compatibility enhancement: `~/.gemini/skills/super-dev/SKILL.md`",
            ),
        ),
        HostDefinition(
            host_id="kiro-cli",
            display_name="Kiro CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-steering",
            protocol_summary="官方 AGENTS.md + steering + skills + native resume",
            supports_slash=True,
            triggers=_tuple("super-dev:", "super-dev：", "/super-dev"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.kiro/steering/`",
                "Project-level `.kiro/skills/`",
                "User-level `~/.kiro/steering/`",
                "User-level `~/.kiro/skills/`",
            ),
        ),
        HostDefinition(
            host_id="kiro",
            display_name="Kiro",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-steering",
            protocol_summary="官方 AGENTS.md + steering + skills + agent continuity",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.kiro/steering/`",
                "Project-level `.kiro/skills/`",
                "User-level `~/.kiro/steering/`",
                "User-level `~/.kiro/skills/`",
            ),
        ),
        HostDefinition(
            host_id="kilo-code",
            display_name="Kilo Code",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-skill",
            protocol_summary="官方 commands + rules",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project-level `.kilocode/rules/`",
                "Project-level `.kilocode/commands/`",
            ),
        ),
        HostDefinition(
            host_id="kimi-code",
            display_name="Kimi Code",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-agents-entry",
            protocol_summary="AGENTS.md + explicit /skill:/flow entries + native session resume",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Current explicit entries used by this integration: `/skill:super-dev` and `/flow:super-dev`",
                "Native resume surfaces observed in Kimi Code: `kimi --continue` / `kimi --session <id>` / `/sessions` / `/resume`",
                "Current implementation enhancement: project-level `.kimi/skills/`",
                "Optional user-level `~/.kimi/skills/` (`--with-user-surfaces`)",
                "Optional shared skill directories: `~/.config/agents/skills/` or `~/.agents/skills/`",
                "Project-level `.kimi/AGENTS.md` (compatibility enhancement)",
            ),
        ),
        HostDefinition(
            host_id="opencode",
            display_name="OpenCode",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 AGENTS.md + commands + skills (+ optional agents)",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev："),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.opencode/commands/`",
                "Project-level `.opencode/skills/`",
                "User-level `~/.config/opencode/AGENTS.md`",
                "User-level `~/.config/opencode/commands/`",
                "User-level `~/.config/opencode/skills/`",
                "Optional project-level `.opencode/agents/`",
                "Optional user-level `~/.config/opencode/agents/`",
            ),
        ),
        HostDefinition(
            host_id="qoder-cli",
            display_name="Qoder CLI",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.qoder/rules/`",
                "Project-level `.qoder/commands/`",
                "Project-level `.qoder/skills/`",
                "User-level `~/.qoder/AGENTS.md`",
                "User-level `~/.qoder/commands/`",
                "User-level `~/.qoder/skills/`",
                "Optional project-level `.qoder/agents/`",
                "Optional user-level `~/.qoder/agents/`",
            ),
        ),
        HostDefinition(
            host_id="qoder",
            display_name="Qoder",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-skill",
            protocol_summary="官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.qoder/rules/`",
                "Project-level `.qoder/commands/`",
                "Project-level `.qoder/skills/`",
                "User-level `~/.qoder/AGENTS.md`",
                "User-level `~/.qoder/commands/`",
                "User-level `~/.qoder/skills/`",
                "Optional project-level `.qoder/agents/`",
                "Optional user-level `~/.qoder/agents/`",
            ),
        ),
        HostDefinition(
            host_id="qwen-code",
            display_name="Qwen Code",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-context",
            protocol_summary="官方 QWEN.md + settings + commands + skills + agents + /resume",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `QWEN.md`",
                "Project-level `.qwen/settings.json`",
                "Project-level `.qwen/commands/`",
                "Project-level `.qwen/skills/`",
                "Project-level `.qwen/agents/`",
                "User-level `~/.qwen/QWEN.md`",
                "User-level `~/.qwen/settings.json`",
                "User-level `~/.qwen/commands/`",
                "User-level `~/.qwen/skills/`",
                "User-level `~/.qwen/agents/`",
            ),
        ),
        HostDefinition(
            host_id="roo-code",
            display_name="Roo Code",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-skill",
            protocol_summary="官方 commands + rules",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project-level `.roo/rules/`",
                "Project-level `.roo/commands/`",
            ),
        ),
        HostDefinition(
            host_id="vscode-copilot",
            display_name="Copilot",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="official-context",
            protocol_summary="官方 copilot-instructions.md + @workspace 项目上下文",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev："),
            docs=_tuple(
                "Project-level `.github/copilot-instructions.md`",
                "Project root `AGENTS.md` (compatibility enhancement)",
            ),
        ),
        HostDefinition(
            host_id="trae",
            display_name="Trae",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="recommended-project-context",
            protocol_summary="当前推荐项目上下文模型: project rules + compatibility rules + optional skills",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "Current recommended project context: `.trae/project_rules.md`",
                "Optional compatibility `.trae/rules.md`",
                "Optional user-level `~/.trae/user_rules.md` (`--with-user-surfaces`)",
                "Optional user-level `~/.trae/rules.md` (`--with-user-surfaces`)",
                "Current implementation enhancement: `~/.trae/skills/super-dev/SKILL.md`",
            ),
        ),
        HostDefinition(
            host_id="trae-cn",
            display_name="TraeCN",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="recommended-cn-workspace-flow",
            protocol_summary="当前推荐中文工作区模型: workspace skills + built-in /plan /spec + CN continuity",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "Current recommended project context: `.trae/project_rules.md` + `.trae/rules.md`",
                "Project-level `.trae/skills/`",
                "User-level `~/.trae-cn/skills/`",
                "Built-in `/plan` + `/spec` + CN continuity",
            ),
        ),
        HostDefinition(
            host_id="trae-solo",
            display_name="Trae SOLO",
            install_mode=HostInstallMode.PROJECT,
            protocol_mode="workspace-rules-commands-skills",
            protocol_summary="当前推荐工作区接入模型: rules + commands + skills + workspace continuity",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md` / `CLAUDE.md` compatibility enhancement",
                "Current recommended project-level `.trae/rules/`",
                "Current recommended project-level `.trae/commands/`",
                "Current recommended project-level `.trae/skills/`",
            ),
        ),
        HostDefinition(
            host_id="trae-solocn",
            display_name="Trae SOLOCN",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="workspace-mtc-code-skills",
            protocol_summary="当前推荐中文工作区模型: MTC / Code + skills + built-in /plan /spec + continuity",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "Current recommended project-level `.trae/rules/`",
                "Current recommended project-level `.trae/skills/`",
                "Current recommended user-level `~/.trae-cn/skills/`",
                "Built-in `/plan` and `/spec`",
            ),
        ),
        HostDefinition(
            host_id="windsurf",
            display_name="Windsurf",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="official-workflow",
            protocol_summary="官方 AGENTS.md + rules + workflows + skills",
            supports_slash=True,
            triggers=_tuple("/super-dev", "super-dev:", "super-dev：", "/super-dev-seeai"),
            docs=_tuple(
                "Project root `AGENTS.md`",
                "Project-level `.windsurf/rules/`",
                "Project-level `.windsurf/workflows/`",
                "Project-level `.windsurf/skills/`",
                "Optional user-level `~/.codeium/windsurf/skills/` (`--with-user-surfaces`)",
            ),
        ),
        HostDefinition(
            host_id="workbuddy",
            display_name="WorkBuddy",
            install_mode=HostInstallMode.HYBRID,
            protocol_mode="manual-task-workbench-mcp",
            protocol_summary="当前推荐任务工作台模型: Skills + MCP + task continuity",
            supports_slash=False,
            triggers=_tuple("super-dev:", "super-dev：", "super-dev-seeai:", "super-dev-seeai："),
            docs=_tuple(
                "WorkBuddy 当前任务 / 对话会话",
                "WorkBuddy 技能市场 / 技能导入",
                "WorkBuddy MCP 配置 (`~/.workbuddy/mcp.json` 或项目 `.workbuddy/mcp.json`)",
                "项目工作目录或授权文件夹",
            ),
        ),
    )
)


HOST_REGISTRY = DEFAULT_HOST_REGISTRY


def get_host_definition(host_id: str) -> HostDefinition | None:
    """Return the registered definition for a host id."""

    return HOST_REGISTRY.get(host_id)


def get_display_name(host_id: str) -> str | None:
    definition = get_host_definition(host_id)
    return definition.display_name if definition else None


def get_install_mode(host_id: str) -> HostInstallMode | None:
    definition = get_host_definition(host_id)
    return definition.install_mode if definition else None


def get_protocol_mode(host_id: str) -> str | None:
    definition = get_host_definition(host_id)
    return definition.protocol_mode if definition else None


def get_protocol_summary(host_id: str) -> str | None:
    definition = get_host_definition(host_id)
    return definition.protocol_summary if definition else None


def supports_slash(host_id: str) -> bool:
    definition = get_host_definition(host_id)
    return definition.supports_slash if definition else False


def get_triggers(host_id: str) -> tuple[str, ...]:
    definition = get_host_definition(host_id)
    return definition.triggers if definition else ()


def get_docs(host_id: str) -> tuple[str, ...]:
    definition = get_host_definition(host_id)
    return definition.docs if definition else ()


def iter_host_definitions() -> tuple[HostDefinition, ...]:
    return HOST_REGISTRY.definitions


def list_host_ids() -> tuple[str, ...]:
    return HOST_REGISTRY.list_host_ids()


def list_manual_hosts() -> tuple[HostDefinition, ...]:
    return HOST_REGISTRY.list_manual_hosts()


def list_hybrid_hosts() -> tuple[HostDefinition, ...]:
    return HOST_REGISTRY.list_hybrid_hosts()


def list_project_hosts() -> tuple[HostDefinition, ...]:
    return HOST_REGISTRY.list_project_hosts()


def list_user_hosts() -> tuple[HostDefinition, ...]:
    return HOST_REGISTRY.list_user_hosts()


__all__ = [
    "DEFAULT_HOST_REGISTRY",
    "HOST_REGISTRY",
    "HostDefinition",
    "HostInstallMode",
    "HostRegistry",
    "get_display_name",
    "get_docs",
    "get_host_definition",
    "get_install_mode",
    "get_protocol_mode",
    "get_protocol_summary",
    "get_triggers",
    "iter_host_definitions",
    "list_host_ids",
    "list_hybrid_hosts",
    "list_manual_hosts",
    "list_project_hosts",
    "list_user_hosts",
    "supports_slash",
]
