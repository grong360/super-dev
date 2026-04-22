"""
多平台 AI Coding 工具集成管理器
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse

from ..catalogs import HOST_TOOL_CATEGORY_MAP, HOST_TOOL_IDS
from ..host_adapters import (
    SpecialAdapterContext,
    build_special_usage_profile,
    get_adapter_mode_override,
    get_competition_smoke_extra_steps,
    get_special_install_surfaces,
)
from ..host_registry import get_display_name, get_protocol_mode, get_protocol_summary
from ..seeai_smoke_scenarios import (
    build_seeai_evidence_template,
    build_seeai_smoke_suite,
    get_seeai_acceptance_gates,
)
from .manager_content_mixin import IntegrationManagerContentMixin


@dataclass
class IntegrationTarget:
    name: str
    description: str
    files: list[str]
    optional_files: list[str] = field(default_factory=list)


@dataclass
class HostAdapterProfile:
    host: str
    category: str
    adapter_mode: str
    host_model_provider: str
    certification_level: str
    certification_label: str
    certification_reason: str
    certification_evidence: list[str]
    official_docs_url: str
    docs_verified: bool
    primary_entry: str
    terminal_entry: str
    terminal_entry_scope: str
    integration_files: list[str]
    slash_command_file: str
    skill_dir: str
    detection_commands: list[str]
    detection_paths: list[str]
    notes: str
    usage_mode: str
    trigger_command: str
    entry_variants: list[dict[str, str]]
    trigger_context: str
    usage_location: str
    requires_restart_after_onboard: bool
    post_onboard_steps: list[str]
    usage_notes: list[str]
    smoke_test_prompt: str
    smoke_test_steps: list[str]
    smoke_success_signal: str
    competition_smoke_test_prompt: str
    competition_smoke_test_steps: list[str]
    competition_smoke_success_signal: str
    competition_smoke_suite: list[dict[str, object]]
    competition_acceptance_gates: list[str]
    competition_evidence_template: dict[str, object]
    precondition_status: str
    precondition_label: str
    precondition_guidance: list[str]
    precondition_signals: dict[str, bool]
    precondition_items: list[dict[str, object]]
    host_protocol_mode: str
    host_protocol_summary: str
    official_project_surfaces: list[str]
    official_user_surfaces: list[str]
    optional_project_surfaces: list[str]
    optional_user_surfaces: list[str]
    observed_compatibility_surfaces: list[str]
    official_docs_references: list[str]
    docs_check_status: str
    docs_check_summary: str
    capability_labels: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class IntegrationManager(IntegrationManagerContentMixin):
    """为不同 AI Coding 平台生成集成配置"""

    TEXT_TRIGGER_PREFIX = "super-dev:"
    TEXT_TRIGGER_PREFIX_FULLWIDTH = "super-dev："
    SEEAI_TEXT_TRIGGER_PREFIX = "super-dev-seeai:"
    SEEAI_TEXT_TRIGGER_PREFIX_FULLWIDTH = "super-dev-seeai："
    CODEX_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV CODEX -->"
    CODEX_AGENTS_END = "<!-- END SUPER DEV CODEX -->"
    OPENCODE_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV OPENCODE -->"
    OPENCODE_AGENTS_END = "<!-- END SUPER DEV OPENCODE -->"
    QODER_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV QODER -->"
    QODER_AGENTS_END = "<!-- END SUPER DEV QODER -->"
    CURSOR_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV CURSOR -->"
    CURSOR_AGENTS_END = "<!-- END SUPER DEV CURSOR -->"
    KIRO_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV KIRO -->"
    KIRO_AGENTS_END = "<!-- END SUPER DEV KIRO -->"
    DROID_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV DROID -->"
    DROID_AGENTS_END = "<!-- END SUPER DEV DROID -->"
    COPILOT_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV COPILOT -->"
    COPILOT_AGENTS_END = "<!-- END SUPER DEV COPILOT -->"
    KIMI_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV KIMI -->"
    KIMI_AGENTS_END = "<!-- END SUPER DEV KIMI -->"
    TRAE_SOLO_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV TRAE SOLO -->"
    TRAE_SOLO_AGENTS_END = "<!-- END SUPER DEV TRAE SOLO -->"
    CLAUDE_RULES_BEGIN = "<!-- BEGIN SUPER DEV CLAUDE -->"
    CLAUDE_RULES_END = "<!-- END SUPER DEV CLAUDE -->"
    NO_SKILL_TARGETS: set[str] = {
        "claude",
        "cline",
        "kilo-code",
        "vscode-copilot",
    }
    HOST_USAGE_LOCATIONS: dict[str, str] = {
        "antigravity": "打开 Antigravity 的 Agent Chat / Prompt 面板，并确保当前工作区就是目标项目。",
        "claude": "打开 Claude Desktop 当前 Project，对准目标项目的 instructions / knowledge / extensions 后触发。",
        "claude-code": "在项目目录启动 Claude Code 当前会话后，直接在同一会话里触发。",
        "cline": "在 VS Code 的 Cline 面板中，绑定当前项目后触发。",
        "codebuddy-cli": "在项目目录启动 CodeBuddy CLI 会话后触发。",
        "codebuddy": "打开 CodeBuddy 的 Agent Chat，在项目上下文内触发。",
        "codebuddy-cn": "打开 CodeBuddyCN IDE 的 Agent Chat，在项目上下文内触发。",
        "droid-cli": "在项目目录启动 Droid CLI 会话后触发，优先沿用当前 Factory session；需要无界面续跑时再用 droid exec。",
        "codex": "打开 Codex App/Desktop 当前会话，并确保工作区就是目标项目后触发。",
        "codex-cli": "在项目目录完成接入后，重启 codex，然后在新的 Codex 会话里触发。",
        "copilot-cli": "在项目目录启动 Copilot CLI 会话后触发。",
        "cursor-cli": "在项目目录启动 Cursor CLI 当前会话后触发。",
        "cursor": "打开 Cursor 的 Agent Chat，并确保当前工作区就是目标项目。",
        "windsurf": "打开 Windsurf 的 Agent Chat 或 Workflow 入口，在项目上下文内触发。",
        "gemini-cli": "在项目目录启动 Gemini CLI 会话后触发。",
        "kimi-code": "在项目目录启动 Kimi Code 会话后触发，优先沿用同一个 session。",
        "kiro-cli": "在项目目录启动 Kiro CLI 会话后触发。",
        "opencode": "在项目目录启动 OpenCode 会话后触发。",
        "qoder-cli": "在项目目录启动 Qoder CLI 会话后触发。",
        "qwen-code": "在项目目录启动 Qwen Code 会话后触发，优先沿用当前 session 的 /resume 能力；/restore 仅用于 checkpoint 回滚。",
        "roo-code": "在 VS Code 的 Roo Code 聊天面板中触发。",
        "vscode-copilot": "在 VS Code Copilot Chat 绑定当前项目后触发。",
        "kilo-code": "在 VS Code 的 Kilo Code 聊天面板中触发。",
        "kiro": "打开 Kiro IDE 的 Agent Chat 或 AI 面板，在项目上下文内触发。",
        "qoder": "打开 Qoder IDE 的 Agent Chat，在当前项目内触发。",
        "trae": "打开 Trae IDE Agent Chat，在当前项目上下文内直接触发。",
        "trae-cn": "打开 TraeCN IDE 当前工作区，在项目上下文内直接触发。",
        "trae-solo": "打开 Trae SOLO Desktop/Web 工作区，在当前项目上下文内直接触发。",
        "trae-solocn": "打开 Trae SOLOCN 当前工作区，在目标项目上下文内直接触发。",
        "workbuddy": "打开 WorkBuddy 当前任务/对话会话，并确保工作目录或授权文件夹指向目标项目后触发。",
    }

    @classmethod
    def _managed_agents_markers(cls, target: str) -> tuple[str, str] | None:
        markers = {
            "codex": (cls.CODEX_AGENTS_BEGIN, cls.CODEX_AGENTS_END),
            "codex-cli": (cls.CODEX_AGENTS_BEGIN, cls.CODEX_AGENTS_END),
            "opencode": (cls.OPENCODE_AGENTS_BEGIN, cls.OPENCODE_AGENTS_END),
            "qoder": (cls.QODER_AGENTS_BEGIN, cls.QODER_AGENTS_END),
            "qoder-cli": (cls.QODER_AGENTS_BEGIN, cls.QODER_AGENTS_END),
            "cursor": (cls.CURSOR_AGENTS_BEGIN, cls.CURSOR_AGENTS_END),
            "cursor-cli": (cls.CURSOR_AGENTS_BEGIN, cls.CURSOR_AGENTS_END),
            "kiro": (cls.KIRO_AGENTS_BEGIN, cls.KIRO_AGENTS_END),
            "kiro-cli": (cls.KIRO_AGENTS_BEGIN, cls.KIRO_AGENTS_END),
            "droid-cli": (cls.DROID_AGENTS_BEGIN, cls.DROID_AGENTS_END),
            "copilot-cli": (cls.COPILOT_AGENTS_BEGIN, cls.COPILOT_AGENTS_END),
            "kimi-code": (cls.KIMI_AGENTS_BEGIN, cls.KIMI_AGENTS_END),
            "trae-solo": (cls.TRAE_SOLO_AGENTS_BEGIN, cls.TRAE_SOLO_AGENTS_END),
        }
        return markers.get(target)

    HOST_USAGE_NOTES: dict[str, list[str]] = {
        "antigravity": [
            "Antigravity 当前优先按 `GEMINI.md + custom commands` 模式接入，`.agent/workflows/` 继续作为当前推荐增强面。",
            "项目内会写入 `GEMINI.md`、`.gemini/commands/super-dev.toml` 与 `.agent/workflows/super-dev.md`。",
            "默认只写项目级 `GEMINI.md` 与项目命令面；用户级 `~/.gemini/GEMINI.md`、`~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时补齐，`~/.gemini/skills/` 继续只作为兼容增强层。",
            "接入后建议新开一个 Antigravity Chat，使 GEMINI 上下文、custom command 与推荐 workflow 一起生效。",
        ],
        "claude": [
            "Claude Desktop 当前官方优先面是 Projects、Project Instructions、Project Knowledge 与 desktop extensions / local MCP。",
            "Super Dev 不再假装 Claude Desktop 存在稳定的项目级 dotfile 自动注入；默认按 Project 模板和会话继续心智来适配。",
            "如果你需要最强项目内文件注入与可重复执行，优先选择 Claude Code；Claude Desktop 更适合项目审阅、方向确认与轻量协作。",
        ],
        "claude-code": [
            "推荐作为首选 CLI 宿主之一。",
            "若维护者需要核对接入面，可执行 super-dev doctor --host claude-code，确认根 `CLAUDE.md`、`.claude/CLAUDE.md`、可选 `.claude/settings*.json`、`.claude/skills/`、`.claude/agents/` 与可选 plugin enhancement 一起生效。",
            "Claude Code 当前更接近官方主模型：项目根 `CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户 `.claude/skills/` 与项目/用户 `.claude/agents/` 是正式主面。",
            "`.claude/commands/` 仅保留为兼容增强面，不再作为唯一主接入面。",
            "仓库内还会额外生成可选的 repo plugin enhancement：`.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json`。",
        ],
        "cline": [
            "Cline 优先使用 `.clinerules/` 规则目录，并补充项目级 `.cline/skills/` 让宿主在当前工作区内直接理解 Super Dev 协议。",
            "用户级 `~/.cline/skills/super-dev/SKILL.md` 会作为全局增强面一起安装。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，减少与内建 slash 的语义冲突。",
        ],
        "codebuddy-cli": [
            "在当前 CLI 会话中直接输入即可。",
            "如果会话早于接入动作启动，建议重开会话后再试。",
            "官方文档已公开 `CODEBUDDY.md`、`.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/`、`.codebuddy/agents/` 与对应用户级目录。",
            "比赛场景优先使用 `/super-dev-seeai` 或 `super-dev-seeai:`，让宿主按半小时时间盒压缩 research / 文档 / spec / 一体化开发。",
        ],
        "codebuddy": [
            "建议在项目级 Agent Chat 中使用，不要脱离项目上下文。",
            "先让宿主完成 research，再继续文档和编码。",
            "官方文档对 IDE 侧更强的是 `CODEBUDDY.md`、rules、skills 与任务/workspace 连续性；commands/agents 保留为当前实现增强面。",
            "比赛模式下优先固定一个 Agent Chat，使用 `/super-dev-seeai` 或 `super-dev-seeai:`，减少切换子会话带来的上下文损耗。",
        ],
        "codebuddy-cn": [
            "CodeBuddyCN 当前按 `CODEBUDDY.md + rules + skills + 中文任务/workspace continuity` 建模，commands/agents 仅保留为当前实现增强面。",
            "建议固定同一个 Agent Chat 完成 research、三文档、确认门与实现，减少跨线程导致的上下文丢失。",
        ],
        "droid-cli": [
            "Droid CLI 官方核心面是 `AGENTS.md + .factory/rules + .factory/skills`；`.factory/commands/` 继续保留为 legacy slash compatibility。",
            "Factory 官方文档已经明确 skills 可以直接暴露 `/command`，新的工作流优先写进 `.factory/skills/`，而不是只依赖 `.factory/commands/`。",
            "项目级 `.factory/skills/` 会作为优先 slash/skill 面；`.factory/commands/` 仅作为兼容补强一起保留。",
            "需要跨项目保持同一宿主习惯时，再显式启用 `--with-user-surfaces`，补齐 `~/.factory/AGENTS.md`、`~/.factory/commands/` 与 `~/.factory/skills/`。",
            "恢复已有 session 时，优先沿用当前 Droid session；需要 headless 继续时再使用 `droid exec --session-id <id>`。",
        ],
        "codex": [
            "Codex Desktop/App 当前官方优先面是仓库 AGENTS.md、仓库/用户级 Skills 与 App 内 `/` 列表的已启用 Skill 入口。",
            "默认先在 App/Desktop 的 `/` 列表里选择 `super-dev`；需要显式终端治理时再切回 Codex CLI 的 `$super-dev`。",
            "若想跨项目复用统一协作心智，再显式启用 `--with-user-surfaces` 写入 `~/.codex/AGENTS.md`。",
        ],
        "codex-cli": [
            "Codex CLI 官方不走自定义项目 slash；CLI 显式入口是 `$super-dev`。",
            "默认依赖项目根 AGENTS.md、项目级 .agents/skills/super-dev/SKILL.md 与官方用户级技能目录 ~/.agents/skills/super-dev/SKILL.md；全局 CODEX_HOME/AGENTS.md（默认 ~/.codex/AGENTS.md）只在显式 `--with-user-surfaces` 时写入。",
            "仓库内还会额外生成 `.agents/plugins/marketplace.json` 与 `plugins/super-dev-codex/`，作为可选 repo plugin 增强层。",
            "所有宿主统一使用 super-dev 技能名称，onboard / migrate 会自动清理旧版 Super Dev 遗留别名残留。",
            "如果旧会话没加载新 Skill，重启 codex 再试。",
        ],
        "copilot-cli": [
            "Copilot CLI 官方优先面是 `AGENTS.md`、`.github/copilot-instructions.md`、`.github/skills/` 与 custom agents 目录 `.github/agents/` / `~/.copilot/agents/`。",
            "如需跨项目沿用同一套上下文，再显式启用 `--with-user-surfaces` 写入 `~/.copilot/copilot-instructions.md`。",
            "如果团队把额外 instructions 放进其他目录，可通过 `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 继续纳入加载面。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，不走自定义 slash。",
            "如果宿主未加载项目规则，重启 copilot 会话再试。",
        ],
        "cursor-cli": [
            "适合终端内连续执行研究、文档和编码。",
            "若命令列表未刷新，可重开一次 Cursor CLI 会话。",
            "官方文档确认 Cursor CLI 会读取项目根 `AGENTS.md` 与 `.cursor/rules/` 作为规则上下文；根 `CLAUDE.md` 只保留为兼容说明。",
        ],
        "cursor": [
            "建议固定在同一个 Agent Chat 会话里完成整条流水线。",
            "如果项目规则没加载，先重新打开工作区或重新发起聊天。",
            "Cursor 官方项目上下文面是项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只保留为兼容说明，`.cursor/commands/` 作为 beta 增强面使用。",
        ],
        "windsurf": [
            "当前按 IDE slash/workflow 模式适配。",
            "更适合在同一个 Workflow 里连续完成研究、三文档、确认门、Spec 与编码。",
            "官方文档公开 `AGENTS.md`、`.windsurf/workflows/` 与 `.windsurf/skills/`，仓库同时把 `.windsurf/rules/` 保留为当前项目约束面。",
            "当前项目侧以 `AGENTS.md` + `.windsurf/rules/` + `.windsurf/workflows/` + `.windsurf/skills/` 为主接入面。",
        ],
        "gemini-cli": [
            "优先在同一会话中完成 research -> 三文档 -> 用户确认 -> Spec -> 前端运行验证 -> 后端/交付。",
            "若宿主支持联网，先让它完成同类产品研究。",
            "Gemini CLI 官方文档明确 `GEMINI.md`、`.gemini/settings.json` 与 `.gemini/commands/*.toml` 的项目级上下文与命令目录；`/super-dev` 应理解为注入出来的 custom command，而不是宿主原生命令。",
            "用户级 `~/.gemini/GEMINI.md`、`~/.gemini/settings.json` 与 `~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时补齐，`~/.gemini/skills/` 继续只保留为兼容增强面。",
        ],
        "kimi-code": [
            "Kimi Code 官方主链按项目根 `AGENTS.md` + `/skill:` / `/flow:` + native session resume 建模。",
            "`.kimi/skills/` 与 `~/.kimi/skills/` 继续保留为当前增强面，`.kimi/AGENTS.md` 保留为兼容增强面，不再把这些路径对外宣称为唯一官方硬合同。",
            "显式官方入口优先使用 `/skill:super-dev <需求描述>`；需要结构化流程时再考虑 `/flow:super-dev <需求描述>`，自然语言 `super-dev:` 保留为统一宿主回退入口。",
            "Kimi Code 恢复时优先沿用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，而不是重新开题。",
        ],
        "kiro-cli": [
            "Kiro CLI 当前优先按 `AGENTS.md + .kiro/steering/super-dev.md + .kiro/skills/` 适配，steering 负责长期上下文与行为约束。",
            "如果 steering 或 skills 未刷新，重新进入项目目录后重开 Kiro CLI 会话。",
            "官方文档已公开工作区 `AGENTS.md`、`.kiro/steering/`、`.kiro/skills/`，以及全局 `~/.kiro/steering/`、`~/.kiro/skills/`。",
        ],
        "opencode": [
            "按 CLI slash 模式使用。",
            "即使你也使用全局命令目录，仍建议保留项目级接入文件。",
            "官方文档已公开项目根 `AGENTS.md`、`.opencode/commands/`、`.opencode/skills/` 与对应用户级目录；`.opencode/agents/` 继续作为当前增强层管理。",
        ],
        "qoder-cli": [
            "适合命令行流水线开发。",
            "若 slash 未生效，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 已生成，并检查 `.qoder/rules/` 与 `.qoder/skills/` 是否存在；`.qoder/agents/` 继续作为增强层核对。",
            "官方文档核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/`，`.qoder/agents/` 继续作为当前增强层。",
            "Qoder 官方规则目录是 `.qoder/rules/`，不要再依赖单文件 `.qoder/rules.md`。",
        ],
        "qwen-code": [
            "Qwen Code 官方文档已公开 `QWEN.md`、`.qwen/settings.json`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`。",
            "Qwen Code 的会话续跑主入口是 `/resume`；`/restore` 只负责 checkpoint 回滚，不应被当成继续当前流程的主入口。",
            "当前最佳接入面是 `QWEN.md + settings + commands + skills + agents`，优先在同一个 session 内完成 research、三文档、Spec 与实现。",
        ],
        "roo-code": [
            "Roo Code 支持项目级 `.roo/rules/` 与 `.roo/commands/`，建议与 `/super-dev` 命令一起使用。",
            "在同一会话连续完成 research、三文档确认、Spec 与开发实现。",
        ],
        "vscode-copilot": [
            "VS Code Copilot 建议使用 `.github/copilot-instructions.md` 固化流水线约束。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，确保与 Copilot Chat 一致。",
        ],
        "kilo-code": [
            "Kilo Code 优先使用 `.kilocode/rules/` 规则目录，确保项目约束在每次任务开始时自动注入。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，减少与内建 slash 的语义冲突。",
        ],
        "kiro": [
            "Kiro IDE 当前优先按 `AGENTS.md + steering + skills` 模式触发，steering 负责长期上下文与行为约束。",
            "如果 steering 或 Skill 未加载，先重开项目窗口或新开一个 Agent Chat。",
            "Kiro 官方已公开工作区 `AGENTS.md`、`.kiro/steering/`、`.kiro/skills/` 与全局 `~/.kiro/steering/`、`~/.kiro/skills/`。",
        ],
        "qoder": [
            "Qoder IDE 当前优先按项目级 `AGENTS.md + commands + rules + skills` 模式触发，可直接使用 /super-dev；`.qoder/agents/` 继续作为增强层。",
            "若新增命令未出现，重新打开项目或新开一个 Agent Chat。",
            "官方文档核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/`。",
        ],
        "trae": [
            "不要输入 /super-dev。",
            "Trae 默认优先依赖项目级 `.trae/project_rules.md` 与 `.trae/rules.md`；用户级 `~/.trae/user_rules.md` / `~/.trae/rules.md` 仅在显式 `--with-user-surfaces` 时写入，用于跨项目复用当前已观测到的规则加载面。",
            "若检测到宿主级 ~/.trae/skills/super-dev/SKILL.md，则会额外增强。",
            "安装后建议新开一个 Trae Agent Chat，让新的规则与 Skill 一起生效。",
            "随后按 output/* 与 .super-dev/changes/*/tasks.md 推进开发。",
        ],
        "trae-cn": [
            "TraeCN 当前按中文工作区流建模，优先保持在同一个工作区/线程里完成 baseline、文档确认与实现。",
            "如果当前工作区已经进入 MTC / Code 某一侧，恢复时优先续跑当前任务，不要重新开题。",
        ],
        "trae-solo": [
            "Trae SOLO 当前优先按 `AGENTS.md + .trae/rules + .trae/commands + .trae/skills` 这套工作区接入模型来承接 Super Dev，并直接在工作区里使用 `/super-dev`。",
            "这套 `.trae/*` 文件面应视为当前最稳的集成模型，而不是对外宣称为宿主唯一官方文件合同。",
            "如果桌面端 slash 刷新慢，可以先回退到 `super-dev: <需求描述>`；恢复时优先沿用当前 workspace continuity，不要重新开题。",
        ],
        "trae-solocn": [
            "Trae SOLOCN 当前优先按 `.trae/rules + .trae/skills + ~/.trae-cn/skills` 这套中文工作区接入模型承接 Super Dev，主入口仍用 `super-dev: <需求描述>`。",
            "中国区公开面更明确的是 `MTC / Code` 双模式、Skills 以及内建 `/plan` `/spec`；`.trae/*` 文件面在仓库里属于当前推荐集成模型，而不是硬编码成唯一官方合同。",
            "如果需要继续当前流程，优先在同一工作区直接说“继续当前流程”；只有在维护场景里才显式回到内部命令面。",
        ],
        "workbuddy": [
            "WorkBuddy 当前推荐通过任务工作台 + Skills + MCP 承接 Super Dev；若启用文件导入型 Skill，仓库会把它视为当前接入模型的补充面，而不是官方主合同。",
            "主入口是 `super-dev: <需求描述>`；赛事模式使用 `super-dev-seeai: <需求描述>`。",
            "也可在 WorkBuddy 技能市场搜索 Super Dev 手动启用，并确认 MCP 与项目目录授权已经就绪。",
        ],
    }
    HOST_PRECONDITION_GUIDANCE: dict[str, list[str]] = {
        "claude": [
            "Claude Desktop 触发前先确认当前 Project 已挂上 Project Instructions、Project Knowledge 与需要的 extensions / MCP。",
            "如果当前会话还没切到目标项目的 Project，不要直接继续流程。",
        ],
        "codex-cli": [
            "Codex 接入后必须重启 `codex`，旧会话不会自动重新加载 AGENTS.md 与宿主级 Skill。",
            "触发前确认当前终端已经进入目标项目目录，并重新打开新的 Codex 会话。",
        ],
        "codex": [
            "Codex Desktop 触发前确认当前会话就是目标项目，并且 `/` 列表里的 super-dev Skill 已启用。",
            "若刚完成接入，优先完全关闭旧会话并重开 App/Desktop 会话。",
        ],
        "antigravity": [
            "Antigravity 接入后建议重新打开 Prompt / Agent Chat，让 GEMINI.md、custom commands 与当前推荐 workflow 一起加载。",
            "触发前确认当前工作区就是目标项目。",
        ],
        "trae": [
            "Trae 接入后建议完全关闭旧 Agent Chat，重新打开项目后再发起新会话。",
            "触发前确认当前 Agent Chat 绑定的是目标项目工作区。",
        ],
        "cursor": [
            "Cursor 需要在目标项目工作区的 Agent Chat 中触发，避免把 `AGENTS.md`、`.cursor/rules/` 与 beta `.cursor/commands/` 加载到错误工作区。",
        ],
        "cursor-cli": [
            "Cursor CLI 触发前确认当前终端已进入目标项目目录，并让会话读取项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只保留为兼容说明。",
        ],
        "gemini-cli": [
            "Gemini CLI 触发前确认当前终端已进入目标项目目录，并让新的会话读取 `GEMINI.md`、可选 `.gemini/settings.json` 与 `.gemini/commands/`。",
        ],
        "kimi-code": [
            "Kimi Code 触发前确认当前终端已进入目标项目目录，并让当前会话读取项目根 `AGENTS.md`。",
            "如果项目或用户级 `.kimi/skills/` 已启用，再确认这些增强面也已被当前会话读取。",
            "如果刚完成接入，优先新开一个 Kimi Code session；显式入口优先 `/skill:super-dev`，恢复时优先使用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`。",
        ],
        "kiro": [
            "Kiro IDE 接入后建议重新打开 Agent Chat，让 `AGENTS.md`、steering / skills 在新会话里生效。",
            "触发前确认当前工作区就是目标项目。",
        ],
        "kiro-cli": [
            "Kiro CLI 触发前确认当前终端已进入目标项目目录，并让新会话读取 `AGENTS.md`、`.kiro/steering/` 与 skills。",
        ],
        "qoder": [
            "Qoder IDE 触发前确认当前 Agent Chat 绑定的是目标项目；若新命令未出现，重新打开项目或新建会话。",
            "若项目里额外启用了 `.qoder/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "qoder-cli": [
            "Qoder CLI 触发前确认当前终端已进入目标项目目录。",
            "若项目里额外启用了 `.qoder/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "qwen-code": [
            "Qwen Code 触发前确认当前终端已进入目标项目目录，并让当前会话读取 `QWEN.md`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`。",
            "如果显式启用了用户级 surface，再确认 `~/.qwen/QWEN.md` 已被当前会话读取。",
            "如果刚完成接入，优先新开一个 Qwen Code session；恢复时优先使用 `/resume`，只有需要回滚工具修改时才使用 `/restore`。",
        ],
        "trae-solo": [
            "Trae SOLO 接入后建议重新打开当前 workspace，让 Rules / Commands / Skills 一起在新会话里生效。",
            "触发前确认当前 workspace 就是目标项目，并优先沿用当前 workspace 的连续恢复能力。",
        ],
        "trae-solocn": [
            "Trae SOLOCN 触发前确认当前工作区就是目标项目，并且 `.trae/skills/` 与 `~/.trae-cn/skills/` 已同步。",
            "如果当前会话已在 MTC / Code 双模式中的某一侧工作，恢复时优先续跑当前任务，而不是重新开题。",
        ],
        "trae-cn": [
            "TraeCN 触发前确认当前工作区就是目标项目，并优先在同一工作区/线程内继续当前流程。",
            "若当前工作区已进入 MTC / Code 某一侧，恢复时优先续跑当前任务。",
        ],
        "codebuddy": [
            "CodeBuddy 触发前确认当前 Agent Chat 位于目标项目上下文。",
            "比赛模式建议固定同一个 Agent Chat，并优先准备主展示路径需要的素材和上下文。",
        ],
        "codebuddy-cn": [
            "CodeBuddyCN 触发前确认当前 Agent Chat 位于目标项目上下文。",
            "优先固定同一个 Agent Chat 完成 research、三文档、Spec 与实现。",
        ],
        "codebuddy-cli": [
            "CodeBuddy CLI 触发前确认当前终端已进入目标项目目录。",
            "确认项目级 `.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/` 与 `.codebuddy/agents/` 都已被当前会话加载。",
            "比赛模式优先使用当前已加载规则的会话，避免重新开多个 CLI 会话打散时间盒。",
        ],
        "droid-cli": [
            "Droid CLI 触发前确认当前终端已进入目标项目目录，并让当前会话读取项目根 `AGENTS.md`。",
            "若 slash 或技能目录刚更新，优先在同一项目目录重开一个 Droid 会话后再触发。",
        ],
        "copilot-cli": [
            "Copilot CLI 触发前确认当前终端已进入目标项目目录，并让新的会话读取 `AGENTS.md`、`.github/copilot-instructions.md` 与 `.github/skills/`。",
            "如果显式启用了用户级 surface，再确认 `~/.copilot/copilot-instructions.md` 也已被新会话加载。",
        ],
        "windsurf": [
            "Windsurf 触发前确认当前 Agent Chat / Workflow 绑定的是目标项目工作区，并已读取项目根 `AGENTS.md`。",
        ],
        "opencode": [
            "OpenCode 触发前确认当前终端已进入目标项目目录。",
            "若项目里额外启用了 `.opencode/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "claude-code": [
            "Claude Code 触发前确认当前会话就是目标项目目录下的当前会话。",
        ],
        "cline": [
            "Cline 触发前确认当前聊天绑定的是目标工作区，并让 `.clinerules/` 已被重新加载。",
        ],
        "kilo-code": [
            "Kilo Code 触发前确认当前聊天绑定的是目标工作区，并让 `.kilocode/rules/` 已被重新加载。",
        ],
        "roo-code": [
            "Roo Code 触发前确认当前聊天位于目标项目工作区，并重新加载 `.roo/` 规则与命令。",
        ],
        "vscode-copilot": [
            "VS Code Copilot 触发前确认当前工作区就是目标项目，并让新的 Chat 会话读取项目级说明文件。",
        ],
        "workbuddy": [
            "WorkBuddy 触发前确认当前授权目录或工作目录已经指向目标项目。",
            "确认当前任务会话已启用 Super Dev 相关 Skills；比赛模式优先启用 SEEAI 版本。",
        ],
    }
    HOST_FAMILY_MAP: dict[str, str] = {
        "antigravity": "antigravity",
        "claude": "claude",
        "claude-code": "claude",
        "cline": "cline",
        "codebuddy-cli": "codebuddy",
        "codebuddy": "codebuddy",
        "codebuddy-cn": "codebuddy",
        "droid-cli": "droid-cli",
        "codex": "codex",
        "codex-cli": "codex",
        "copilot-cli": "copilot-cli",
        "cursor-cli": "cursor",
        "cursor": "cursor",
        "windsurf": "windsurf",
        "gemini-cli": "gemini",
        "kimi-code": "kimi-code",
        "kilo-code": "kilo-code",
        "kiro-cli": "kiro",
        "kiro": "kiro",
        "qoder-cli": "qoder",
        "qoder": "qoder",
        "qwen-code": "qwen",
        "roo-code": "roo-code",
        "vscode-copilot": "vscode-copilot",
        "opencode": "opencode",
        "trae": "trae",
        "trae-cn": "trae",
        "trae-solo": "trae",
        "trae-solocn": "trae",
        "workbuddy": "workbuddy",
    }
    PREFERRED_FAMILY_TARGETS: dict[str, str] = {
        "codebuddy": "codebuddy-cli",
        "cursor": "cursor-cli",
        "kiro": "kiro-cli",
        "qoder": "qoder-cli",
        "trae": "trae-solo",
    }
    SHARED_DETECTION_FILES: set[str] = {
        "AGENTS.md",
        "CODEBUDDY.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursor/rules/super-dev.mdc",
        ".kiro/steering/super-dev.md",
    }

    TARGETS: dict[str, IntegrationTarget] = {
        "antigravity": IntegrationTarget(
            name="antigravity",
            description="Antigravity IDE 工作流 + Gemini 上下文注入",
            files=["GEMINI.md", ".gemini/commands/super-dev.toml", ".agent/workflows/super-dev.md"],
        ),
        "claude": IntegrationTarget(
            name="claude",
            description="Claude Desktop Project / Instructions / Knowledge 手动接入",
            files=[],
        ),
        "claude-code": IntegrationTarget(
            name="claude-code",
            description="Claude Code CLI 深度集成",
            files=[
                "CLAUDE.md",
                ".claude/CLAUDE.md",
                ".claude/skills/super-dev/SKILL.md",
                ".claude/agents/super-dev.md",
                ".claude/commands/super-dev.md",
                ".claude-plugin/marketplace.json",
                "plugins/super-dev-claude/.claude-plugin/plugin.json",
                "plugins/super-dev-claude/README.md",
                "plugins/super-dev-claude/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".claude/CLAUDE.md",
                ".claude/commands/super-dev.md",
                ".claude-plugin/marketplace.json",
                "plugins/super-dev-claude/.claude-plugin/plugin.json",
                "plugins/super-dev-claude/README.md",
                "plugins/super-dev-claude/skills/super-dev/SKILL.md",
            ],
        ),
        "cline": IntegrationTarget(
            name="cline",
            description="Cline IDE 规则注入",
            files=[".clinerules/super-dev.md", ".cline/skills/super-dev/SKILL.md"],
        ),
        "codebuddy-cli": IntegrationTarget(
            name="codebuddy-cli",
            description="CodeBuddy CLI 项目规则注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev.md",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
                ".codebuddy/agents/super-dev.md",
            ],
        ),
        "codebuddy": IntegrationTarget(
            name="codebuddy",
            description="CodeBuddy rules + agent protocol 注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev/RULE.mdc",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/agents/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
            ],
        ),
        "codebuddy-cn": IntegrationTarget(
            name="codebuddy-cn",
            description="CodeBuddyCN IDE rules + agent protocol 注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev/RULE.mdc",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/agents/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
            ],
        ),
        "droid-cli": IntegrationTarget(
            name="droid-cli",
            description="Droid CLI 官方 AGENTS + .factory rules/commands/skills 接入",
            files=[
                "AGENTS.md",
                ".factory/rules/super-dev.md",
                ".factory/commands/super-dev.md",
                ".factory/commands/super-dev-seeai.md",
                ".factory/skills/super-dev/SKILL.md",
                ".factory/skills/super-dev-seeai/SKILL.md",
            ],
        ),
        "codex": IntegrationTarget(
            name="codex",
            description="Codex App/Desktop 项目上下文注入",
            files=[
                "AGENTS.md",
                ".agents/skills/super-dev/SKILL.md",
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
        ),
        "codex-cli": IntegrationTarget(
            name="codex-cli",
            description="Codex 项目上下文注入",
            files=[
                "AGENTS.md",
                ".agents/skills/super-dev/SKILL.md",
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
        ),
        "copilot-cli": IntegrationTarget(
            name="copilot-cli",
            description="Copilot CLI 指令注入",
            files=[
                "AGENTS.md",
                ".github/copilot-instructions.md",
                ".github/skills/super-dev/SKILL.md",
                ".github/agents/super-dev.md",
            ],
        ),
        "cursor-cli": IntegrationTarget(
            name="cursor-cli",
            description="Cursor CLI 项目规则注入",
            files=["AGENTS.md", ".cursor/rules/super-dev.mdc"],
        ),
        "windsurf": IntegrationTarget(
            name="windsurf",
            description="Windsurf IDE AGENTS + 规则 + Workflow 注入",
            files=[
                "AGENTS.md",
                ".windsurf/rules/super-dev.md",
                ".windsurf/workflows/super-dev.md",
                ".windsurf/skills/super-dev/SKILL.md",
            ],
        ),
        "gemini-cli": IntegrationTarget(
            name="gemini-cli",
            description="Gemini CLI 项目规则注入",
            files=["GEMINI.md", ".gemini/commands/super-dev.toml"],
        ),
        "kimi-code": IntegrationTarget(
            name="kimi-code",
            description="Kimi Code AGENTS + Skill 增强接入",
            files=[
                "AGENTS.md",
                ".kimi/AGENTS.md",
                ".kimi/skills/super-dev/SKILL.md",
            ],
        ),
        "kilo-code": IntegrationTarget(
            name="kilo-code",
            description="Kilo Code 规则 + Skill 注入",
            files=[".kilocode/rules/super-dev.md", ".kilocode/skills/super-dev/SKILL.md"],
        ),
        "kiro-cli": IntegrationTarget(
            name="kiro-cli",
            description="Kiro CLI 项目规则注入",
            files=["AGENTS.md", ".kiro/steering/super-dev.md", ".kiro/skills/super-dev/SKILL.md"],
        ),
        "qoder-cli": IntegrationTarget(
            name="qoder-cli",
            description="Qoder CLI 项目规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".qoder/rules/super-dev.md",
                ".qoder/commands/super-dev.md",
                ".qoder/skills/super-dev/SKILL.md",
                ".qoder/agents/super-dev.md",
            ],
        ),
        "qwen-code": IntegrationTarget(
            name="qwen-code",
            description="Qwen Code 项目规则 + 命令 + Skill + Agent 注入",
            files=[
                "QWEN.md",
                ".qwen/commands/super-dev.md",
                ".qwen/skills/super-dev/SKILL.md",
                ".qwen/agents/super-dev.md",
            ],
        ),
        "roo-code": IntegrationTarget(
            name="roo-code",
            description="Roo Code 规则 + 命令注入",
            files=[".roo/rules/super-dev.md", ".roo/commands/super-dev.md"],
        ),
        "vscode-copilot": IntegrationTarget(
            name="vscode-copilot",
            description="Copilot 仓库级指令注入",
            files=[".github/copilot-instructions.md"],
        ),
        "opencode": IntegrationTarget(
            name="opencode",
            description="OpenCode 项目规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".opencode/commands/super-dev.md",
                ".opencode/skills/super-dev/SKILL.md",
                ".opencode/agents/super-dev.md",
            ],
        ),
        "cursor": IntegrationTarget(
            name="cursor",
            description="Cursor IDE 规则注入",
            files=["AGENTS.md", ".cursor/rules/super-dev.mdc"],
        ),
        "kiro": IntegrationTarget(
            name="kiro",
            description="Kiro IDE 项目规则注入",
            files=["AGENTS.md", ".kiro/steering/super-dev.md", ".kiro/skills/super-dev/SKILL.md"],
        ),
        "qoder": IntegrationTarget(
            name="qoder",
            description="Qoder IDE 规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".qoder/rules/super-dev.md",
                ".qoder/commands/super-dev.md",
                ".qoder/skills/super-dev/SKILL.md",
                ".qoder/agents/super-dev.md",
            ],
        ),
        "trae": IntegrationTarget(
            name="trae",
            description="Trae IDE 项目规则 + 宿主 Skill 注入",
            files=[".trae/project_rules.md", ".trae/rules.md"],
        ),
        "trae-cn": IntegrationTarget(
            name="trae-cn",
            description="TraeCN IDE 中文工作区规则 + Skills 接入",
            files=[".trae/project_rules.md", ".trae/rules.md", ".trae/skills/super-dev/SKILL.md"],
        ),
        "trae-solo": IntegrationTarget(
            name="trae-solo",
            description="Trae SOLO Rules + Commands + Skills 接入",
            files=[
                "AGENTS.md",
                ".trae/rules/super-dev.md",
                ".trae/commands/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ],
        ),
        "trae-solocn": IntegrationTarget(
            name="trae-solocn",
            description="Trae SOLOCN Rules + Skills 接入",
            files=[
                ".trae/rules/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ],
        ),
        "workbuddy": IntegrationTarget(
            name="workbuddy",
            description="WorkBuddy 桌面工作台 Skill 接入",
            files=[],
        ),
    }
    SLASH_COMMAND_FILES: dict[str, str] = {
        "antigravity": ".gemini/commands/super-dev.toml",
        "claude-code": ".claude/commands/super-dev.md",
        "codebuddy-cli": ".codebuddy/commands/super-dev.md",
        "codebuddy": ".codebuddy/commands/super-dev.md",
        "codebuddy-cn": ".codebuddy/commands/super-dev.md",
        "droid-cli": ".factory/commands/super-dev.md",
        "cursor-cli": ".cursor/commands/super-dev.md",
        "windsurf": ".windsurf/workflows/super-dev.md",
        "gemini-cli": ".gemini/commands/super-dev.toml",
        "kiro-cli": ".kiro/steering/super-dev.md",
        "kiro": ".kiro/steering/super-dev.md",
        "opencode": ".opencode/commands/super-dev.md",
        "qoder-cli": ".qoder/commands/super-dev.md",
        "qwen-code": ".qwen/commands/super-dev.md",
        "qoder": ".qoder/commands/super-dev.md",
        "roo-code": ".roo/commands/super-dev.md",
        "cursor": ".cursor/commands/super-dev.md",
        "trae-solo": ".trae/commands/super-dev.md",
    }
    GLOBAL_SLASH_COMMAND_FILES: dict[str, str] = {
        "antigravity": ".gemini/commands/super-dev.toml",
        "claude-code": ".claude/commands/super-dev.md",
        "codebuddy-cli": ".codebuddy/commands/super-dev.md",
        "codebuddy": ".codebuddy/commands/super-dev.md",
        "codebuddy-cn": ".codebuddy/commands/super-dev.md",
        "droid-cli": ".factory/commands/super-dev.md",
        "opencode": ".config/opencode/commands/super-dev.md",
        "qoder-cli": ".qoder/commands/super-dev.md",
        "qoder": ".qoder/commands/super-dev.md",
        "qwen-code": ".qwen/commands/super-dev.md",
    }
    NO_SLASH_TARGETS: set[str] = {
        "claude",
        "cline",
        "codex",
        "codex-cli",
        "copilot-cli",
        "kimi-code",
        "kilo-code",
        "trae",
        "trae-cn",
        "trae-solocn",
        "vscode-copilot",
        "workbuddy",
    }

    @classmethod
    def host_family(cls, target: str) -> str:
        return cls.HOST_FAMILY_MAP.get(target, target)

    @classmethod
    def preferred_target_for_family(cls, family: str, candidates: list[str] | None = None) -> str:
        preferred = cls.PREFERRED_FAMILY_TARGETS.get(family, family)
        if candidates and preferred not in candidates:
            return sorted(candidates)[0]
        return preferred

    @classmethod
    def family_targets(cls, family: str) -> list[str]:
        return [
            target
            for target, current_family in cls.HOST_FAMILY_MAP.items()
            if current_family == family
        ]

    @classmethod
    def target_detection_markers(cls, target: str) -> list[str]:
        integration = cls.TARGETS[target]
        markers: list[str] = [
            relative for relative in integration.files if relative not in cls.SHARED_DETECTION_FILES
        ]
        slash_file = cls.SLASH_COMMAND_FILES.get(target)
        if slash_file and slash_file not in markers:
            markers.append(slash_file)
        return markers

    @staticmethod
    def _string_value(value: object, default: str = "") -> str:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or default
        return default

    @staticmethod
    def _bool_value(value: object, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        return default

    @classmethod
    def _string_list(cls, value: object) -> list[str]:
        if not isinstance(value, Iterable) or isinstance(value, str | bytes | dict):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @classmethod
    def _string_dict(cls, value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): cls._string_value(item) for key, item in value.items()}

    @classmethod
    def _bool_dict(cls, value: object) -> dict[str, bool]:
        if not isinstance(value, dict):
            return {}
        return {str(key): cls._bool_value(item) for key, item in value.items()}

    @classmethod
    def _object_dict(cls, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        return {str(key): item for key, item in value.items()}

    @classmethod
    def _dict_list(cls, value: object) -> list[dict[str, object]]:
        if not isinstance(value, Iterable) or isinstance(value, str | bytes | dict):
            return []
        normalized: list[dict[str, object]] = []
        for item in value:
            if isinstance(item, dict):
                normalized.append({str(key): item_value for key, item_value in item.items()})
        return normalized

    def install_manifest_path(self) -> Path:
        return self.project_dir / ".super-dev" / "install-manifest.json"

    def load_install_manifest(self) -> dict[str, Any]:
        file_path = self.install_manifest_path()
        if not file_path.exists():
            return {"version": 1, "targets": {}, "updated_at": ""}
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return {"version": 1, "targets": {}, "updated_at": ""}
        if not isinstance(payload, dict):
            return {"version": 1, "targets": {}, "updated_at": ""}
        targets = payload.get("targets", {})
        if not isinstance(targets, dict):
            targets = {}
        return {
            "version": int(payload.get("version", 1) or 1),
            "targets": targets,
            "updated_at": str(payload.get("updated_at", "")).strip(),
        }

    def save_install_manifest(self, payload: dict[str, Any]) -> Path:
        current = self.load_install_manifest()
        current.update(payload)
        current["version"] = int(current.get("version", 1) or 1)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        file_path = self.install_manifest_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return file_path

    OFFICIAL_DOCS_INDEX: dict[str, tuple[str, ...]] = {
        "antigravity": ("https://antigravity.im/documentation",),
        "claude": (
            "https://support.anthropic.com/en/articles/9487310-what-are-projects",
            "https://support.anthropic.com/en/articles/10185728-understanding-and-managing-project-knowledge",
            "https://support.anthropic.com/en/articles/11433263-using-styles-in-claude",
        ),
        "claude-code": (
            "https://docs.anthropic.com/en/docs/claude-code/slash-commands",
            "https://docs.anthropic.com/en/docs/claude-code/hooks",
            "https://docs.anthropic.com/en/docs/claude-code/sdk",
            "https://docs.anthropic.com/en/docs/claude-code/settings#claude-md-memory",
            "https://docs.anthropic.com/en/docs/claude-code/sub-agents",
        ),
        "cline": ("https://docs.cline.bot/customization/cline-rules",),
        "codebuddy-cli": (
            "https://www.codebuddy.ai/docs/cli/slash-commands",
            "https://www.codebuddy.ai/docs/cli/skills",
            "https://www.codebuddy.ai/docs/cli/plugins",
        ),
        "codebuddy": (
            "https://www.codebuddy.ai/docs/cli/ide-integrations",
            "https://www.codebuddy.ai/docs/zh/ide/User-guide/Rules",
            "https://www.codebuddy.ai/docs/ide/Features/Subagents",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Skills",
        ),
        "codebuddy-cn": (
            "https://www.codebuddy.ai/docs/zh/ide/User-guide/Rules",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Commands",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Skills",
        ),
        "droid-cli": (
            "https://docs.factory.ai/factory-cli/configuration/agents-md",
            "https://docs.factory.ai/factory-cli/configuration/skills",
            "https://docs.factory.ai/factory-cli/configuration/custom-slash-commands",
            "https://docs.factory.ai/cli/configuration/custom-droids",
            "https://docs.factory.ai/reference/cli-reference",
        ),
        "codex-cli": (
            "https://developers.openai.com/codex/cli",
            "https://developers.openai.com/codex/guides/agents-md",
            "https://developers.openai.com/codex/skills",
            "https://developers.openai.com/codex/app/commands",
        ),
        "codex": (
            "https://developers.openai.com/codex/cli",
            "https://developers.openai.com/codex/guides/agents-md",
            "https://developers.openai.com/codex/skills",
            "https://developers.openai.com/codex/app/commands",
        ),
        "copilot-cli": (
            "https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-agents/invoke-custom-agents",
        ),
        "cursor-cli": (
            "https://docs.cursor.com/en/cli/overview",
            "https://docs.cursor.com/en/cli/using",
            "https://docs.cursor.com/en/context/rules",
        ),
        "windsurf": (
            "https://docs.windsurf.com/plugins/cascade/workflows",
            "https://docs.windsurf.com/windsurf/cascade/memories#custom-skills",
            "https://docs.windsurf.com/windsurf/cascade/memories",
        ),
        "gemini-cli": (
            "https://google-gemini.github.io/gemini-cli/docs/",
            "https://google-gemini.github.io/gemini-cli/docs/cli/gemini-md.html",
            "https://google-gemini.github.io/gemini-cli/docs/get-started/configuration.html",
            "https://google-gemini.github.io/gemini-cli/docs/cli/custom-commands.html",
            "https://google-gemini.github.io/gemini-cli/docs/cli/commands.html",
        ),
        "kimi-code": (
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/getting-started.html",
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/interaction.html",
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/sessions.html",
            "https://www.kimi.com/code/docs/en/kimi-cli.html",
        ),
        "kilo-code": ("https://kilocode.ai/docs/features/rules",),
        "kiro-cli": (
            "https://kiro.dev/docs/cli/",
            "https://kiro.dev/docs/steering/",
            "https://kiro.dev/docs/cli/skills/",
            "https://kiro.dev/docs/cli/reference/slash-commands/",
        ),
        "opencode": (
            "https://opencode.ai/docs/rules/",
            "https://opencode.ai/docs/commands/",
            "https://opencode.ai/docs/skills/",
            "https://opencode.ai/docs/agents/",
        ),
        "qoder-cli": (
            "https://docs.qoder.com/cli/using-cli",
            "https://docs.qoder.com/zh/user-guide/rules",
            "https://docs.qoder.com/user-guide/commands",
            "https://docs.qoder.com/cli/skills",
            "https://docs.qoder.com/en/cli/user-guide/subagent",
        ),
        "qwen-code": (
            "https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/",
            "https://qwenlm.github.io/qwen-code-docs/en/subagents/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/",
        ),
        "roo-code": (
            "https://docs.roocode.com/features/slash-commands",
            "https://docs.roocode.com/features/custom-instructions",
            "https://docs.roocode.com/features/custom-modes",
        ),
        "vscode-copilot": (
            "https://docs.github.com/en/copilot/how-tos/copilot-chat/customize-copilot/add-repository-instructions",
            "https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot",
        ),
        "cursor": (
            "https://docs.cursor.com/en/agent/chat/commands",
            "https://docs.cursor.com/en/context/rules",
        ),
        "kiro": (
            "https://kiro.dev/docs/",
            "https://kiro.dev/docs/steering/",
            "https://kiro.dev/docs/cli/skills/",
        ),
        "qoder": (
            "https://docs.qoder.com/zh/user-guide/rules",
            "https://docs.qoder.com/user-guide/commands",
            "https://docs.qoder.com/user-guide/skills",
            "https://docs.qoder.com/en/cli/user-guide/subagent",
        ),
        "trae": ("https://docs.trae.ai/docs/what-is-trae-rules",),
        "trae-cn": (
            "https://www.trae.cn/",
            "https://www.trae.cn/changelog",
            "https://forum.trae.cn/t/topic/36",
        ),
        "trae-solo": (
            "https://docs.trae.ai/solo?_lang=en",
            "https://docs.trae.ai/solo/rules?_lang=en",
            "https://docs.trae.ai/solo/slash-commands?_lang=en",
            "https://docs.trae.ai/solo/skills?_lang=en",
        ),
        "trae-solocn": (
            "https://www.trae.cn/solo",
            "https://www.trae.cn/changelog",
            "https://forum.trae.cn/t/topic/36",
            "https://forum.trae.cn/t/topic/7556",
        ),
        "workbuddy": (
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Product-Guide",
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide",
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Right-Sidebar",
        ),
    }
    OFFICIAL_DOCS: dict[str, str] = {
        key: (values[0] if values else "") for key, values in OFFICIAL_DOCS_INDEX.items()
    }
    DOCS_VERIFIED_TARGETS: set[str] = {
        key for key, values in OFFICIAL_DOCS_INDEX.items() if bool(values)
    }
    HOST_CERTIFICATIONS: dict[str, dict[str, object]] = {
        "antigravity": {
            "level": "experimental",
            "reason": "Antigravity 当前按公开可证实的 GEMINI 上下文 + custom commands 建模，并结合仓库推荐的 workflow 增强面接入；安装面可用，但官方本地注入文档证据仍偏弱。",
            "evidence": [
                "公开资料能确认 GEMINI 上下文、命令面与自然语言/Prompt 工作方式",
                "`.agent/workflows/` 与 `~/.gemini/skills/` 继续按当前推荐增强模型保留，不再对外宣称为严格官方硬合同",
                "Super Dev 已按项目 `GEMINI.md` + `.gemini/commands/` 主面接入，并把 workflow / skill 面降成推荐增强模型",
            ],
        },
        "claude": {
            "level": "compatible",
            "reason": "Claude Desktop 官方明确支持 Projects、Project Instructions、Project Knowledge 与 desktop extensions / MCP，当前接入按这些正式面而不是猜测 dotfile 路径建模。",
            "evidence": [
                "官方帮助中心公开 Projects、Project Knowledge 与 Styles/Instructions",
                "Super Dev 已把 Claude Desktop 建模成项目/知识/扩展驱动的桌面助手，而不是伪装成文件注入宿主",
            ],
        },
        "claude-code": {
            "level": "certified",
            "reason": "已收敛到 Claude Code 的官方主模型：项目根 CLAUDE.md + 可选 settings + 项目/用户 skills + 项目/用户 subagents，并仅把 commands/plugin 保留为增强层。",
            "evidence": [
                "Anthropic 官方文档公开项目/用户 settings、CLAUDE.md 与 `.claude/agents/`",
                "Anthropic 官方文档公开 project/user subagents 位于 `.claude/agents/` 与 `~/.claude/agents/`",
                "Super Dev 已补齐 `CLAUDE.md + .claude/CLAUDE.md + .claude/skills + .claude/agents`，并把 `.claude/commands` 留作兼容增强面",
            ],
        },
        "codebuddy-cn": {
            "level": "compatible",
            "reason": "CodeBuddyCN 当前按 `CODEBUDDY.md + rules + skills + 中文任务/workspace continuity` 建模，commands/agents 仅保留为当前实现增强面。",
            "evidence": [
                "官方中文 IDE 文档公开 Rules、Skills 与工作流能力",
                "Super Dev 已为 CodeBuddyCN 建模 CODEBUDDY.md + rules + skills 主面，并保留 commands/agents 增强层",
            ],
        },
        "codex-cli": {
            "level": "certified",
            "reason": "已按 Codex CLI 的真实能力改成 AGENTS.md + Skills 主面，CLI 官方显式入口是 `$super-dev`，不再把 `/super-dev` 误当成 CLI 原生入口。",
            "evidence": [
                "官方产品说明明确 Skills 是 Codex 的主扩展面",
                "Super Dev 已为 Codex CLI 修正成 AGENTS.md + `.agents/skills` + `~/.agents/skills`",
                "repo plugin enhancement 保留为可选高级增强，不再和 CLI 官方入口混写",
                "接入后需要重启的行为已被显式建模与测试覆盖",
            ],
        },
        "codex": {
            "level": "certified",
            "reason": "Codex App/Desktop 与 CLI 共用 AGENTS.md + Skills 主面，当前已单独建模桌面端 Skill 入口与项目级接入面。",
            "evidence": [
                "官方文档明确 AGENTS.md、Skills 与 Codex App/Desktop commands",
                "Super Dev 已把 Codex App/Desktop 从 Codex CLI 中拆出，形成独立桌面助手宿主模型",
            ],
        },
        "kimi-code": {
            "level": "compatible",
            "reason": "Kimi Code 官方文档已明确 AGENTS.md、/skill:/flow: 与 session continue / resume；仓库继续把 `.kimi/skills/` 保留为当前增强层而不是对外宣称的唯一官方文件合同。",
            "evidence": [
                "官方文档公开项目级 `AGENTS.md` 与官方 `/skill:`、`/flow:` 入口",
                "官方文档公开 `/skill:`、`/flow:`、`kimi --continue`、`kimi --session` 与运行中的 `/sessions` / `/resume`",
                "Super Dev 已改为 AGENTS + explicit entry + native resume 的 Kimi 宿主模型接入，并把 `.kimi/skills/` 收成增强层",
            ],
        },
        "trae": {
            "level": "compatible",
            "reason": "Trae 官方公开面当前可确认的是项目 rules；用户 rules 与兼容 rules 继续作为可选增强面建模，skills 仍按增强处理，因此当前保持稳定兼容而非认证级。",
            "evidence": [
                "公开文档确认 Trae project rules 机制，user rules 作为可选增强面保留",
                "本机已存在 ~/.trae/rules.md，可作为兼容规则面在显式启用用户级面时协同生效",
                "本机若存在 ~/.trae/skills，可作为兼容增强路径协同生效",
                "Super Dev 已同时建模项目 rules、用户 rules、兼容 rules 面与可选宿主级 Skill 增强",
            ],
        },
        "trae-solo": {
            "level": "compatible",
            "reason": "Trae SOLO 公开资料能确认 workspace continuity 与 rules/commands/skills 能力；仓库已把 `.trae/*` 收成当前推荐工作区接入模型，而不是过度宣称为唯一官方文件合同。",
            "evidence": [
                "公开 SOLO 文档可确认 workspace continuity 与 rules / commands / skills 能力",
                "仓库把 `.trae/rules/` + `.trae/commands/` + `.trae/skills/` 作为当前推荐接入模型",
                "Super Dev 保留 `super-dev:` 作为 slash 未刷新的自然语言回退入口",
            ],
        },
        "trae-solocn": {
            "level": "compatible",
            "reason": "Trae SOLOCN 中国区资料更明确的是 MTC / Code、Skills 与内建 `/plan` `/spec`；仓库已把 `.trae/*` + `~/.trae-cn/skills` 收成当前推荐中文工作区模型，而不是把这些路径硬写成唯一官方合同。",
            "evidence": [
                "官方中国区页面与 changelog 明确 MTC / Code 双模式",
                "官方 changelog 明确内建 `/plan` 与 `/spec`",
                "Super Dev 已改为中文工作区 continuity + rules/skills + natural-language primary entry 模型",
            ],
        },
        "codebuddy-cli": {
            "level": "compatible",
            "reason": "官方文档已明确 CODEBUDDY.md + rules + commands + skills + subagents，当前接入已扩展到完整主面，但仍缺少长期真机回归矩阵。",
            "evidence": [
                "官方文档公开 CODEBUDDY.md、CLI rules、slash commands、skills 与 sub-agents",
                "Super Dev 已改为写入 CODEBUDDY.md + rules + commands + skills + agents，并保留 AGENTS.md compatibility 观察面",
            ],
        },
        "droid-cli": {
            "level": "compatible",
            "reason": "Factory Droid 官方文档已经明确 `AGENTS.md`、`.factory/rules/`、`.factory/skills/`、legacy `.factory/commands/` 与 `droid exec` 的 session 模型，当前接入已按官方宿主面建模。",
            "evidence": [
                "官方文档公开 `AGENTS.md` 作为 Droid 的仓库/用户 briefing packet",
                "官方文档公开 `.factory/rules/`、`.factory/skills/` 与 `.factory/commands/` 目录，并明确 skills 已能直接作为 `/command` 使用",
                "官方文档公开 `droid exec --session-id` 作为会话续跑方式",
                "Super Dev 已改为 `AGENTS.md + .factory/rules + .factory/skills` 主面接入，并把 `.factory/commands` 留作 legacy slash compatibility",
            ],
        },
        "cursor-cli": {
            "level": "compatible",
            "reason": "Cursor CLI 官方文档已明确项目根 AGENTS.md 与 `.cursor/rules/` 的上下文模型，当前接入链路完整；根 `CLAUDE.md` 仅保留为兼容说明，但仍需更多运行级认证样本。",
            "evidence": [
                "官方文档公开 Cursor CLI 会读取项目根 `AGENTS.md` 与 `.cursor/rules/`",
                "Super Dev 已改为共享 AGENTS.md + `.cursor/rules/` 宿主模型，并保留根 `CLAUDE.md` 作为兼容说明",
            ],
        },
        "gemini-cli": {
            "level": "compatible",
            "reason": "Gemini CLI 已按官方 GEMINI.md + settings + custom commands 建模，兼容 skill 面已降到增强层，但还未提升到认证级真机矩阵。",
            "evidence": [
                "官方文档公开 GEMINI.md、settings、custom commands 与会话/恢复命令",
                "Super Dev 已提供项目级 GEMINI.md + .gemini/commands 主面，并把 skills 降到兼容增强层",
            ],
        },
        "kiro-cli": {
            "level": "compatible",
            "reason": "已按 Kiro 官方 AGENTS.md + steering + skills 机制接入，steering 负责长期上下文与行为约束，不再把它误写成 slash 本身。",
            "evidence": [
                "官方文档公开 Kiro CLI 会读取工作区/全局 AGENTS.md、steering 与 skills",
                "Super Dev 已改为 AGENTS.md + `.kiro/steering/` + `.kiro/skills/` + `~/.kiro/steering/` + `~/.kiro/skills/` 接入",
            ],
        },
        "qoder-cli": {
            "level": "compatible",
            "reason": "Qoder CLI 已按官方 `AGENTS.md + .qoder/rules + .qoder/commands + .qoder/skills` 接入，并把 `.qoder/agents/` 收成增强层。",
            "evidence": [
                "官方文档公开项目/用户 `AGENTS.md`、`.qoder/rules/`、commands、skills 与 subagents",
                "Super Dev 已改为 AGENTS + rules + slash command + skills 主接入面，并把 agents 保留为增强层",
            ],
        },
        "qwen-code": {
            "level": "compatible",
            "reason": "Qwen Code 官方文档已明确 QWEN.md、settings、commands、skills、subagents 与 `/resume` / checkpoint restore，当前接入已按官方宿主面建模。",
            "evidence": [
                "官方文档公开 `QWEN.md`、`.qwen/settings.json`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`",
                "官方文档说明 `/resume` 用于继续会话，`/restore` 用于 checkpoint 回滚",
                "Super Dev 已改为 QWEN.md + settings + commands + skills + agents 的 Qwen Code 接入模型",
            ],
        },
        "codebuddy": {
            "level": "experimental",
            "reason": "IDE 侧已对齐官方 CODEBUDDY.md + rules + skills + 任务/workspace 连续性；commands/agents 保留为当前实现增强面，但长期行为仍缺少持续真机验证。",
            "evidence": [
                "官方文档公开 IDE rules、skills 与工作流能力",
                "Super Dev 已写入 CODEBUDDY.md、rules、skills 主接入面，并保留 commands/agents 作为增强层",
            ],
        },
        "copilot-cli": {
            "level": "compatible",
            "reason": "Copilot CLI 已按官方 copilot-instructions + AGENTS.md + skills + agents 面建模，文本触发稳定，但自定义 agent 的长期真机回归仍不足。",
            "evidence": [
                "官方文档公开 AGENTS.md、.github/copilot-instructions.md 与 .github/instructions/**/*.instructions.md",
                "官方文档公开 .github/skills 与 ~/.copilot/skills",
                "官方文档公开 Copilot CLI custom agents 目录 .github/agents 与 ~/.copilot/agents",
                "Super Dev 已写入 AGENTS.md、.github/copilot-instructions.md、.github/skills/super-dev/SKILL.md 与 .github/agents/super-dev.md",
            ],
        },
        "cursor": {
            "level": "experimental",
            "reason": "IDE Agent Chat 能力已按官方 AGENTS.md + rules 建模；根 `CLAUDE.md` 只作为兼容说明，`.cursor/commands/` 作为 beta 增强面，项目级 slash 行为仍需持续运行级验证。",
            "evidence": [
                "官方文档公开 Agent commands、rules，以及项目根 AGENTS.md 上下文",
                "Super Dev 已改为共享 AGENTS.md + `.cursor/rules/` 宿主模型，并保留 `.cursor/commands/` 作为增强层",
            ],
        },
        "windsurf": {
            "level": "experimental",
            "reason": "当前已按官方 AGENTS.md + workflows + skills 与仓库项目 rules 收敛到同一模型，交互模式可用但还未达到认证级稳定性。",
            "evidence": [
                "官方文档公开 AGENTS.md、workflows 与 custom skills",
                "Super Dev 已写入 `AGENTS.md`、`.windsurf/rules/`、`.windsurf/workflows/` 与 skills",
            ],
        },
        "opencode": {
            "level": "experimental",
            "reason": "官方 AGENTS + commands + skills 路径已适配，`.opencode/agents/` 继续作为增强层管理，但仍需要更强的运行级认证覆盖。",
            "evidence": [
                "官方文档公开项目根 AGENTS.md、~/.config/opencode/AGENTS.md、commands、skills 与 agents",
                "Super Dev 已写入项目级 AGENTS、commands、skills，并把 agents 保留为增强层，同时补齐用户级 AGENTS / commands / skills 管理链",
            ],
        },
        "kilo-code": {
            "level": "experimental",
            "reason": "Kilo Code 按 .kilocode/rules/ 规则目录适配，与 Roo Code 生态类似，但仍需更多真机验证。",
            "evidence": [
                "Kilo Code 支持项目级 .kilocode/rules/ 规则目录",
                "Super Dev 已写入规则文件",
            ],
        },
        "kiro": {
            "level": "experimental",
            "reason": "IDE 侧已按官方 AGENTS.md + steering + skills + Agent Chat continuity 对齐；steering 只负责长期上下文，不再误写成 slash 本体。",
            "evidence": [
                "官方文档公开工作区/全局 steering、skills，以及工作区和全局 AGENTS.md 支持",
                "Super Dev 已改为 AGENTS.md + `.kiro/steering/` + `.kiro/skills/` + `~/.kiro/steering/` + `~/.kiro/skills/` 接入",
            ],
        },
        "qoder": {
            "level": "experimental",
            "reason": "官方文档已明确 `AGENTS.md + .qoder/rules + commands + skills`；当前已切到完整主面，并把 `.qoder/agents/` 收成增强层，但仍需要更多真机样本。",
            "evidence": [
                "官方文档公开项目/用户 `AGENTS.md`、`.qoder/rules/`、commands、skills 与 subagents",
                "Super Dev 已改为 AGENTS + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/` 主接入面，并把 `.qoder/agents/` 保留为增强层",
            ],
        },
        "workbuddy": {
            "level": "experimental",
            "reason": "WorkBuddy 公开资料能确认任务工作台、Skills、MCP 与项目目录授权；仓库保留 `~/.workbuddy/skills/` 作为当前接入模型的补充面，但不再把它对外宣称为唯一官方文件合同。",
            "evidence": [
                "官方文档公开 WorkBuddy 支持自然语言任务、Skills 扩展、MCP 与本地文件夹授权执行",
                "官方文档公开右侧边栏与任务工作台协同查看项目文件和结果",
                "Super Dev 已为 WorkBuddy 建立标准模式、SEEAI 比赛模式、任务线程恢复与 MCP 验收指引",
            ],
        },
        "vscode-copilot": {
            "level": "experimental",
            "reason": "VS Code Copilot 仅支持 .github/copilot-instructions.md 作为项目指令面，不支持自定义 Skill 或 slash 命令，因此接入深度有限。",
            "evidence": [
                "官方文档公开 .github/copilot-instructions.md 作为项目级指令",
                "Copilot Chat 的 @workspace 指令会读取 copilot-instructions.md",
                "Super Dev 已写入 .github/copilot-instructions.md，但不支持 Skill 和 slash",
            ],
        },
    }
    CERTIFICATION_LABELS: dict[str, str] = {
        "certified": "Certified",
        "compatible": "Compatible",
        "experimental": "Experimental",
    }
    TEXT_TRIGGER_PREFIXES: tuple[str, str] = (TEXT_TRIGGER_PREFIX, TEXT_TRIGGER_PREFIX_FULLWIDTH)
    SEEAI_TEXT_TRIGGER_PREFIXES: tuple[str, str] = (
        SEEAI_TEXT_TRIGGER_PREFIX,
        SEEAI_TEXT_TRIGGER_PREFIX_FULLWIDTH,
    )
    CONTRACT_TRIGGER_GROUPS: dict[str, tuple[str, ...]] = {
        "slash": ("/super-dev", "/super-dev-seeai"),
        "text": TEXT_TRIGGER_PREFIXES + SEEAI_TEXT_TRIGGER_PREFIXES,
    }
    CONTRACT_DOC_GROUP: tuple[str, ...] = (
        "output/*-research.md",
        "output/*-prd.md",
        "output/*-architecture.md",
        "output/*-uiux.md",
        "three core documents",
        "three core docs",
        "三份核心文档",
        "PRD, architecture, and UIUX",
        "PRD / Architecture / UIUX",
        "PRD / 架构 / UIUX",
        "Draft PRD, architecture, and UIUX",
    )
    CONTRACT_CONFIRMATION_GROUP: tuple[str, ...] = (
        "wait for explicit confirmation",
        "wait for approval",
        "wait for user confirmation",
        "for user confirmation",
        "Stop for user confirmation",
        "Create Spec/tasks only after confirmation",
        "先向用户汇报文档摘要与路径，等待明确确认",
        "等待确认",
        "用户未确认前禁止创建 Spec",
        "未经确认不得创建 Spec",
        "暂停等待用户确认",
        "等待用户确认",
        "stop after the three core documents",
    )
    CONTRACT_ARTIFACT_GROUP: tuple[str, ...] = (
        "workspace files",
        "project files",
        "repository workspace",
        "project workspace",
        "项目文件",
        "真实写入项目文件",
        "chat-only summaries do not count",
        "只在聊天里总结不算完成",
        "instead of only replying in chat",
    )
    CONTRACT_FLOW_GROUP: tuple[str, ...] = (
        "SUPER_DEV_FLOW_CONTRACT_V1",
        "PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery",
        "DOC_CONFIRM_GATE: required",
        "PREVIEW_CONFIRM_GATE: required",
        "HOST_PARITY: required",
    )

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.templates_dir = self.project_dir / "templates"

    def _flow_contract_markdown_block(self) -> str:
        return (
            "## Super Dev System Flow Contract\n"
            "- SUPER_DEV_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: required\n"
            "- HOST_PARITY: required\n"
        )

    def _flow_contract_toml_block(self) -> str:
        return (
            "# SUPER_DEV_FLOW_CONTRACT_V1\n"
            "# PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery\n"
            "# DOC_CONFIRM_GATE: required\n"
            "# PREVIEW_CONFIRM_GATE: required\n"
            "# HOST_PARITY: required\n"
        )

    def _append_flow_contract(self, *, content: str, relative: str) -> str:
        normalized = content or ""
        if (
            "SUPER_DEV_FLOW_CONTRACT_V1" in normalized
            or "SUPER_DEV_SEEAI_FLOW_CONTRACT_V1" in normalized
        ):
            return normalized
        if str(relative).endswith(".toml"):
            return f"{normalized.rstrip()}\n\n{self._flow_contract_toml_block()}"
        return f"{normalized.rstrip()}\n\n{self._flow_contract_markdown_block()}"

    def _first_response_contract_zh(self) -> str:
        return (
            "## 首轮响应契约（首次触发必须执行）\n"
            "- 当用户通过宿主支持的 Super Dev 入口触发（例如 `/super-dev ...`、`$super-dev`、`super-dev: ...`、`super-dev：...`、`/super-dev-seeai ...`、`$super-dev-seeai`、`super-dev-seeai: ...` 或 `super-dev-seeai：...`）后，第一轮回复必须明确：已进入对应的 Super Dev 流水线，而不是普通聊天。\n"
            "- 如果仓库里已经存在 `super-dev.yaml`、`.super-dev/WORKFLOW.md`、`output/*`、`.super-dev/review-state/*` 或未完成的 run state，新会话里的第一次自然语言需求也必须默认继续 Super Dev 流程，而不是退回普通聊天。\n"
            "- 第一轮回复前，优先读取 `.super-dev/WORKFLOW.md` 与 `output/*-bootstrap.md`（若存在），把其中的初始化契约视为当前仓库的显式 bootstrap 规则。\n"
            "- 第一轮回复必须明确当前阶段是 `research`，会先读取 `knowledge/` 与 `output/knowledge-cache/*-knowledge-bundle.json`（若存在），再用宿主原生联网研究同类产品。\n"
            "- 标准模式的后续顺序是：research -> 三份核心文档 -> 等待用户确认 -> Spec / tasks -> 前端优先并运行验证 -> 后端 / 测试 / 交付。\n"
            "- SEEAI 模式的后续顺序是：research -> 比赛短版三文档 -> 等待用户确认 -> compact Spec -> full-stack sprint -> polish / handoff。\n"
            "- 两种模式都必须明确承诺：三份核心文档完成后会暂停并等待用户确认；未经确认不会创建 Spec，也不会开始编码。\n\n"
        )

    def _first_response_contract_en(self) -> str:
        return (
            "## First-Response Contract\n"
            "- On the first reply after a host-supported Super Dev entry (for example `/super-dev ...`, `$super-dev`, `super-dev: ...`, `super-dev：...`, `/super-dev-seeai ...`, `$super-dev-seeai`, `super-dev-seeai: ...`, or `super-dev-seeai：...`), explicitly state that the matching Super Dev mode is now active rather than normal chat mode.\n"
            "- If the repository already contains `super-dev.yaml`, `.super-dev/WORKFLOW.md`, `output/*`, `.super-dev/review-state/*`, or an unfinished run state, the first natural-language requirement in a new host session must also default to continuing Super Dev rather than plain chat.\n"
            "- Before the first reply, read `.super-dev/WORKFLOW.md` and `output/*-bootstrap.md` when present, and treat them as the explicit bootstrap contract for this repository.\n"
            "- The first reply must explicitly state that the current phase is `research`, and that you will read `knowledge/` plus `output/knowledge-cache/*-knowledge-bundle.json` first when available before similar-product research.\n"
            "- In standard mode, the next sequence is research -> three core documents -> wait for user confirmation -> Spec / tasks -> frontend first with runtime verification -> backend / tests / delivery.\n"
            "- In SEEAI mode, the next sequence is research -> compact competition docs -> wait for user confirmation -> compact Spec -> full-stack sprint -> polish / handoff.\n"
            "- Both modes must explicitly promise that they will stop after the three core documents and wait for approval before creating Spec or writing code.\n\n"
        )

    @classmethod
    def coverage_gaps(cls) -> dict[str, list[str]]:
        declared = set(HOST_TOOL_IDS)
        target_keys = set(cls.TARGETS)
        slash_keys = set(cls.SLASH_COMMAND_FILES)
        slash_required = declared - cls.NO_SLASH_TARGETS
        docs_keys = set(cls.OFFICIAL_DOCS)
        verified_keys = set(cls.DOCS_VERIFIED_TARGETS)
        declared_with_docs = {item for item, value in cls.OFFICIAL_DOCS.items() if bool(value)}
        return {
            "missing_in_targets": sorted(declared - target_keys),
            "extra_in_targets": sorted(target_keys - declared),
            "missing_in_slash": sorted(slash_required - slash_keys),
            "extra_in_slash": sorted(slash_keys - slash_required),
            "missing_in_docs_map": sorted(declared - docs_keys),
            "extra_in_docs_map": sorted(docs_keys - declared),
            "missing_official_docs_url": sorted(declared - declared_with_docs),
            "unverified_docs": sorted(declared - verified_keys),
        }

    def list_targets(self) -> list[IntegrationTarget]:
        return list(self.TARGETS.values())

    @classmethod
    def required_integration_files(cls, target: str) -> list[str]:
        target_info = cls.TARGETS.get(target)
        if target_info is None:
            return []
        optional = set(target_info.optional_files)
        return [item for item in target_info.files if item not in optional]

    @classmethod
    def optional_integration_files(cls, target: str) -> list[str]:
        target_info = cls.TARGETS.get(target)
        if target_info is None:
            return []
        return list(target_info.optional_files)

    def get_adapter_profile(self, target: str) -> HostAdapterProfile:
        from ..catalogs import HOST_COMMAND_CANDIDATES, host_path_candidates
        from ..skills import SkillManager

        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        category = HOST_TOOL_CATEGORY_MAP.get(target, "ide")
        integration_files = list(self.required_integration_files(target))
        slash_file = self.SLASH_COMMAND_FILES.get(target, "") if self.supports_slash(target) else ""
        skill_dir = SkillManager.TARGET_PATHS.get(target, "") if self.requires_skill(target) else ""
        docs_references = self._official_docs_references(target)
        docs_url = docs_references[0] if docs_references else ""
        docs_verified = bool(docs_references)
        adapter_mode = self._adapter_mode(
            target=target, category=category, integration_files=integration_files
        )
        usage = dict(self._usage_profile(target=target, category=category))
        if not self._dict_list(usage.get("entry_variants")):
            usage["entry_variants"] = self._default_entry_variants(
                target=target,
                usage=usage,
            )
        certification = self._certification_profile(target)
        smoke = self._smoke_profile(target=target, category=category)
        preconditions = self._precondition_profile(target=target)
        surfaces = self._install_surfaces(target=target)
        protocol = self._protocol_profile(target=target)
        capability_labels = self._capability_labels(target=target)

        return HostAdapterProfile(
            host=target,
            category=category,
            adapter_mode=adapter_mode,
            host_model_provider="host",
            certification_level=self._string_value(certification.get("level"), "experimental"),
            certification_label=self._string_value(
                certification.get("label"), self.CERTIFICATION_LABELS["experimental"]
            ),
            certification_reason=self._string_value(certification.get("reason")),
            certification_evidence=self._string_list(certification.get("evidence")),
            official_docs_url=docs_url,
            docs_verified=docs_verified,
            primary_entry=self._string_value(usage.get("primary_entry")),
            terminal_entry="super-dev",
            terminal_entry_scope="仅用于安装 / 更新 / 卸载；正常开发应回到宿主会话",
            integration_files=integration_files,
            slash_command_file=slash_file,
            skill_dir=skill_dir,
            detection_commands=self._string_list(HOST_COMMAND_CANDIDATES.get(target, [])),
            detection_paths=self._string_list(host_path_candidates(target)),
            notes=self._string_value(usage.get("notes")),
            usage_mode=self._string_value(usage.get("usage_mode")),
            trigger_command=self._string_value(usage.get("trigger_command")),
            entry_variants=[
                self._string_dict(item) for item in self._dict_list(usage.get("entry_variants"))
            ],
            trigger_context=self._string_value(usage.get("trigger_context")),
            usage_location=self._string_value(usage.get("usage_location")),
            requires_restart_after_onboard=self._bool_value(
                usage.get("requires_restart_after_onboard")
            ),
            post_onboard_steps=self._string_list(usage.get("post_onboard_steps")),
            usage_notes=self._string_list(usage.get("usage_notes")),
            smoke_test_prompt=self._string_value(smoke.get("smoke_test_prompt")),
            smoke_test_steps=self._string_list(smoke.get("smoke_test_steps")),
            smoke_success_signal=self._string_value(smoke.get("smoke_success_signal")),
            competition_smoke_test_prompt=self._string_value(
                smoke.get("competition_smoke_test_prompt")
            ),
            competition_smoke_test_steps=self._string_list(
                smoke.get("competition_smoke_test_steps")
            ),
            competition_smoke_success_signal=self._string_value(
                smoke.get("competition_smoke_success_signal")
            ),
            competition_smoke_suite=self._dict_list(smoke.get("competition_smoke_suite")),
            competition_acceptance_gates=self._string_list(
                smoke.get("competition_acceptance_gates")
            ),
            competition_evidence_template=self._object_dict(
                smoke.get("competition_evidence_template")
            ),
            precondition_status=self._string_value(preconditions.get("status")),
            precondition_label=self._string_value(preconditions.get("label")),
            precondition_guidance=self._string_list(preconditions.get("guidance")),
            precondition_signals=self._bool_dict(preconditions.get("signals")),
            precondition_items=self._dict_list(preconditions.get("items")),
            host_protocol_mode=self._string_value(protocol.get("mode")),
            host_protocol_summary=self._string_value(protocol.get("summary")),
            official_project_surfaces=self._string_list(
                surfaces.get("official_project_surfaces")
            ),
            official_user_surfaces=self._string_list(surfaces.get("official_user_surfaces")),
            optional_project_surfaces=self._string_list(
                surfaces.get("optional_project_surfaces")
            ),
            optional_user_surfaces=self._string_list(surfaces.get("optional_user_surfaces")),
            observed_compatibility_surfaces=self._string_list(
                surfaces.get("observed_compatibility_surfaces")
            ),
            official_docs_references=docs_references,
            docs_check_status="declared" if docs_references else "missing",
            docs_check_summary=(
                f"declared {len(docs_references)} refs"
                if docs_references
                else "no official docs references"
            ),
            capability_labels=capability_labels,
        )

    def _default_entry_variants(
        self,
        *,
        target: str,
        usage: dict[str, object],
    ) -> list[dict[str, str]]:
        label = get_display_name(target) or target
        trigger = self._string_value(usage.get("trigger_command")) or (
            "/super-dev <需求描述>"
            if self.supports_slash(target)
            else f"{self.TEXT_TRIGGER_PREFIX} <需求描述>"
        )
        variants: list[dict[str, str]] = []
        if self.supports_slash(target):
            variants.append(
                {
                    "surface": "default",
                    "label": label,
                    "entry": trigger,
                    "mode": "native-slash",
                    "priority": "preferred",
                    "notes": "优先使用宿主原生 slash 入口进入当前 Super Dev 流程。",
                }
            )
            variants.append(
                {
                    "surface": "fallback",
                    "label": f"{label} Fallback",
                    "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                    "mode": "rules-natural-language-fallback",
                    "priority": "fallback",
                    "notes": "当 slash 未刷新或当前会话已在恢复路径中时，回退到统一自然语言入口。",
                }
            )
        else:
            variants.append(
                {
                    "surface": "default",
                    "label": label,
                    "entry": trigger,
                    "mode": "rules-natural-language",
                    "priority": "preferred",
                    "notes": "在当前宿主会话中使用统一自然语言入口进入 Super Dev 流程。",
                }
            )
        return variants

    def _certification_profile(self, target: str) -> dict[str, object]:
        raw = self.HOST_CERTIFICATIONS.get(target, {})
        level = str(raw.get("level", "experimental")).strip().lower()
        if level not in self.CERTIFICATION_LABELS:
            level = "experimental"
        normalized_evidence = self._string_list(raw.get("evidence"))
        return {
            "level": level,
            "label": self.CERTIFICATION_LABELS[level],
            "reason": str(raw.get("reason", "")).strip(),
            "evidence": normalized_evidence,
        }

    def list_adapter_profiles(self, targets: list[str] | None = None) -> list[HostAdapterProfile]:
        selected = targets or sorted(self.TARGETS.keys())
        return [self.get_adapter_profile(target) for target in selected]

    def host_hardening_blueprint(
        self,
        target: str,
        *,
        include_user_surfaces: bool = False,
    ) -> dict[str, object]:
        profile = self.get_adapter_profile(target)
        trigger_mode = "slash" if self.supports_slash(target) else "text"
        required_steps = [
            "setup project integration files",
            "inject system flow contract markers",
            "audit surface contract markers",
            "generate host usage profile",
        ]
        if self.supports_slash(target):
            required_steps.append("setup project slash command")
            if include_user_surfaces:
                required_steps.append("setup user-level slash command")
        if self.requires_skill(target):
            required_steps.append("install skill to host skill directory")
        required_user_surfaces = list(profile.official_user_surfaces)
        if include_user_surfaces:
            required_user_surfaces.extend(
                item for item in profile.optional_user_surfaces if item not in required_user_surfaces
            )
        protocol_mode = str(profile.host_protocol_mode or "")
        if protocol_mode:
            required_steps.append(f"apply host protocol mode: {protocol_mode}")
        return {
            "host": target,
            "trigger_mode": trigger_mode,
            "final_trigger": profile.trigger_command,
            "required_steps": required_steps,
            "required_project_surfaces": list(profile.official_project_surfaces),
            "required_user_surfaces": required_user_surfaces,
            "optional_project_surfaces": list(profile.optional_project_surfaces),
            "optional_user_surfaces": list(profile.optional_user_surfaces),
            "with_user_surfaces": include_user_surfaces,
        }

    def _official_docs_references(self, target: str) -> list[str]:
        references = list(self.OFFICIAL_DOCS_INDEX.get(target, ()))
        return [item.strip() for item in references if isinstance(item, str) and item.strip()]

    def _capability_labels(self, *, target: str) -> dict[str, str]:
        slash_label = "native" if self.supports_slash(target) else "none"
        if target in {"codex", "codex-cli"}:
            slash_label = "skill-list"
        protocol = self._protocol_profile(target=target)
        mode = str(protocol.get("mode", "")).strip().lower()
        if mode in {"official-context", "official-steering"}:
            rules_label = "official"
        elif mode.startswith("official"):
            rules_label = "official"
        else:
            rules_label = "compat"
        if self.requires_skill(target):
            compatibility_skill_targets = {
                "cursor-cli",
                "cursor",
                "gemini-cli",
                "trae",
                "trae-solo",
            }
            skill_label = "compat" if target in compatibility_skill_targets else "official"
        else:
            skill_label = "none"
        trigger_label = "slash" if self.supports_slash(target) else "text"
        return {
            "slash": slash_label,
            "rules": rules_label,
            "skills": skill_label,
            "trigger": trigger_label,
        }

    def verify_official_docs(
        self, target: str, *, timeout_seconds: float = 5.0
    ) -> dict[str, object]:
        references = self._official_docs_references(target)
        if not references:
            return {
                "target": target,
                "status": "missing",
                "checked": 0,
                "reachable": 0,
                "unreachable": 0,
                "details": [],
            }
        details: list[dict[str, object]] = []
        reachable = 0
        for url in references:
            probe = self._probe_official_url(url=url, timeout_seconds=timeout_seconds)
            ok = bool(probe.get("reachable", False))
            code = probe.get("status_code")
            reason = str(probe.get("error", ""))
            if ok:
                reachable += 1
            details.append(
                {
                    "url": url,
                    "reachable": ok,
                    "status_code": code,
                    "error": reason,
                    "method": str(probe.get("method", "")),
                    "tls_mode": str(probe.get("tls_mode", "")),
                }
            )
        checked = len(details)
        status = "verified" if reachable == checked else ("partial" if reachable > 0 else "failed")
        return {
            "target": target,
            "status": status,
            "checked": checked,
            "reachable": reachable,
            "unreachable": checked - reachable,
            "details": details,
        }

    def _fetch_official_doc_excerpt(
        self,
        url: str,
        *,
        timeout_seconds: float = 5.0,
        max_bytes: int = 120000,
    ) -> dict[str, object]:
        probe = self._probe_official_url(
            url=url,
            timeout_seconds=timeout_seconds,
            read_content=True,
            max_bytes=max_bytes,
        )
        return {
            "url": url,
            "reachable": bool(probe.get("reachable", False)),
            "status_code": probe.get("status_code"),
            "error": str(probe.get("error", "")),
            "content": str(probe.get("content", "")),
            "method": str(probe.get("method", "")),
            "tls_mode": str(probe.get("tls_mode", "")),
        }

    def _probe_official_url(
        self,
        *,
        url: str,
        timeout_seconds: float,
        read_content: bool = False,
        max_bytes: int = 120000,
    ) -> dict[str, object]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {
                "url": url,
                "reachable": False,
                "status_code": None,
                "error": f"unsupported_url_scheme:{parsed.scheme or 'missing'}",
                "content": "",
                "method": "",
                "tls_mode": "strict",
            }
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; super-dev-host-audit/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        attempts: list[tuple[str, bool]]
        if read_content:
            attempts = [("GET", True), ("GET", False)]
        else:
            attempts = [("HEAD", True), ("GET", True), ("GET", False)]
        last_error = ""
        last_status: int | None = None
        for method, strict_tls in attempts:
            try:
                req = urllib_request.Request(url, headers=headers, method=method)
                if not strict_tls:
                    # 不降级到不安全连接，跳过此尝试
                    continue
                with urllib_request.urlopen(req, timeout=timeout_seconds) as resp:  # nosec B310
                    status = int(getattr(resp, "status", 200))
                    content = ""
                    if read_content and method == "GET":
                        content = resp.read(max_bytes).decode("utf-8", errors="ignore")
                    return {
                        "url": url,
                        "reachable": 200 <= status < 400,
                        "status_code": status,
                        "error": "",
                        "content": content,
                        "method": method,
                        "tls_mode": "strict" if strict_tls else "insecure-fallback",
                    }
            except urllib_error.HTTPError as exc:
                status = int(getattr(exc, "code", 0) or 0)
                last_status = status
                last_error = str(exc)
                if method == "HEAD" and status in {401, 403, 405, 406, 429}:
                    continue
                if 200 <= status < 400:
                    return {
                        "url": url,
                        "reachable": True,
                        "status_code": status,
                        "error": str(exc),
                        "content": "",
                        "method": method,
                        "tls_mode": "strict" if strict_tls else "insecure-fallback",
                    }
                if method == "GET" and not strict_tls:
                    break
            except Exception as exc:
                last_error = str(exc)
                if method == "HEAD":
                    continue
                if method == "GET" and strict_tls:
                    continue
                break
        try:
            return {
                "url": url,
                "reachable": False,
                "status_code": last_status,
                "error": last_error,
                "content": "",
                "method": "GET",
                "tls_mode": "strict",
            }
        except Exception:
            return {
                "url": url,
                "reachable": False,
                "status_code": last_status,
                "error": last_error,
                "content": "",
                "method": "GET",
                "tls_mode": "strict",
            }

    def compare_official_capabilities(
        self, target: str, *, timeout_seconds: float = 5.0
    ) -> dict[str, object]:
        references = self._official_docs_references(target)
        expected = self._capability_labels(target=target)
        if not references:
            return {
                "target": target,
                "status": "missing",
                "expected": expected,
                "checked_urls": 0,
                "reachable_urls": 0,
                "checks": {},
                "details": [],
            }
        fetched = [
            self._fetch_official_doc_excerpt(url, timeout_seconds=timeout_seconds)
            for url in references
        ]
        reachable = [item for item in fetched if bool(item.get("reachable", False))]
        corpus = "\n".join(str(item.get("content", "")).lower() for item in reachable)
        checks: dict[str, dict[str, object]] = {}
        keyword_map: dict[str, tuple[str, ...]] = {
            "slash": ("slash", "/super-dev", "commands", "workflow"),
            "rules": ("rules", "instruction", "guideline", "agents.md", "steering", "context"),
            "skills": ("skill", "skills", "subagent", "sub-agents", "agent"),
        }
        required = 0
        passed = 0
        for capability in ("slash", "rules", "skills"):
            label = str(expected.get(capability, "")).strip().lower()
            if label == "none":
                checks[capability] = {
                    "expected": label,
                    "ok": True,
                    "matched_keywords": [],
                    "reason": "not-required",
                }
                continue
            required += 1
            keywords = keyword_map.get(capability, ())
            matched = [item for item in keywords if item in corpus]
            ok = bool(matched) and bool(reachable)
            if ok:
                passed += 1
            checks[capability] = {
                "expected": label,
                "ok": ok,
                "matched_keywords": matched,
                "reason": (
                    "matched"
                    if ok
                    else ("no-reachable-docs" if not reachable else "keyword-mismatch")
                ),
            }
        if not reachable:
            status = "unknown"
        elif required == 0:
            status = "passed"
        elif passed == required:
            status = "passed"
        elif passed > 0:
            status = "partial"
        else:
            status = "failed"
        return {
            "target": target,
            "status": status,
            "expected": expected,
            "checked_urls": len(fetched),
            "reachable_urls": len(reachable),
            "checks": checks,
            "details": [
                {
                    "url": str(item.get("url", "")),
                    "reachable": bool(item.get("reachable", False)),
                    "status_code": item.get("status_code"),
                    "error": str(item.get("error", "")),
                }
                for item in fetched
            ],
        }

    @classmethod
    def _codex_home_dir(cls) -> Path:
        raw = os.getenv("CODEX_HOME", "").strip()
        if raw:
            return Path(raw).expanduser()
        return Path.home() / ".codex"

    @classmethod
    def resolve_global_protocol_path(cls, target: str) -> Path | None:
        mapping = {
            "claude": None,
            "claude-code": Path.home() / ".claude" / "CLAUDE.md",
            "codebuddy-cli": Path.home() / ".codebuddy" / "CODEBUDDY.md",
            "codebuddy": Path.home() / ".codebuddy" / "CODEBUDDY.md",
            "codebuddy-cn": Path.home() / ".codebuddy" / "CODEBUDDY.md",
            "droid-cli": Path.home() / ".factory" / "AGENTS.md",
            "codex": cls._codex_home_dir() / "AGENTS.md",
            "codex-cli": cls._codex_home_dir() / "AGENTS.md",
            "copilot-cli": Path.home() / ".copilot" / "copilot-instructions.md",
            "kiro-cli": Path.home() / ".kiro" / "steering" / "super-dev.md",
            "kiro": Path.home() / ".kiro" / "steering" / "super-dev.md",
            "gemini-cli": Path.home() / ".gemini" / "GEMINI.md",
            "antigravity": Path.home() / ".gemini" / "GEMINI.md",
            "opencode": Path.home() / ".config" / "opencode" / "AGENTS.md",
            "qoder-cli": Path.home() / ".qoder" / "AGENTS.md",
            "qoder": Path.home() / ".qoder" / "AGENTS.md",
            "qwen-code": Path.home() / ".qwen" / "QWEN.md",
            "trae": Path.home() / ".trae" / "user_rules.md",
            "trae-cn": Path.home() / ".trae-cn" / "skills" / "super-dev" / "SKILL.md",
        }
        return mapping.get(target)

    @classmethod
    def resolve_compatibility_protocol_path(cls, target: str) -> Path | None:
        if target in {"trae", "trae-cn"}:
            return Path.home() / ".trae" / "rules.md"
        return None

    @classmethod
    def expected_skill_path(
        cls,
        target: str,
        skill_name: str = "super-dev",
        project_dir: Path | None = None,
    ) -> Path | None:
        paths = cls.expected_skill_paths(
            target=target, skill_name=skill_name, project_dir=project_dir
        )
        return paths[0] if paths else None

    @classmethod
    def expected_skill_paths(
        cls,
        target: str,
        skill_name: str = "super-dev",
        project_dir: Path | None = None,
    ) -> list[Path]:
        from ..skills import SkillManager

        if not cls.requires_skill(target):
            return []
        paths: list[Path] = []
        project_root = Path(project_dir).resolve() if project_dir is not None else None
        surface_kind = SkillManager.target_path_kind(target)
        for name in SkillManager.compatibility_skill_names(target, skill_name):
            if project_root is not None:
                if target in {"codex", "codex-cli"}:
                    paths.append(project_root / ".agents" / "skills" / name / "SKILL.md")
                elif target == "claude-code":
                    paths.append(project_root / ".claude" / "skills" / name / "SKILL.md")
                elif target in {"codebuddy", "codebuddy-cli", "codebuddy-cn"}:
                    paths.append(project_root / ".codebuddy" / "skills" / name / "SKILL.md")
                elif target == "kimi-code":
                    paths.append(project_root / ".kimi" / "skills" / name / "SKILL.md")
                elif target == "qwen-code":
                    paths.append(project_root / ".qwen" / "skills" / name / "SKILL.md")
                elif target == "trae-cn":
                    paths.append(project_root / ".trae" / "skills" / name / "SKILL.md")
                elif target in {"trae-solo", "trae-solocn"}:
                    paths.append(project_root / ".trae" / "skills" / name / "SKILL.md")
            if target not in SkillManager.TARGET_PATHS:
                continue
            target_root = Path(SkillManager.TARGET_PATHS[target]).expanduser()
            if surface_kind == "observed-compatibility-surface" and not target_root.exists():
                continue
            paths.append(target_root / name / "SKILL.md")
            for mirror in SkillManager.COMPATIBILITY_MIRROR_PATHS.get(target, []):
                mirror_root = (
                    cls._codex_home_dir() / "skills"
                    if target in {"codex", "codex-cli"}
                    else Path(mirror).expanduser()
                )
                paths.append(mirror_root / name / "SKILL.md")
        deduped: list[Path] = []
        seen: set[str] = set()
        for item in paths:
            key = str(item)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @classmethod
    def contract_validation_groups(cls, target: str) -> list[tuple[str, tuple[str, ...]]]:
        trigger_group = cls.CONTRACT_TRIGGER_GROUPS[
            "slash" if cls.supports_slash(target) else "text"
        ]
        return [
            ("trigger", trigger_group),
            ("documents", cls.CONTRACT_DOC_GROUP),
            ("confirmation", cls.CONTRACT_CONFIRMATION_GROUP),
            ("artifacts", cls.CONTRACT_ARTIFACT_GROUP),
            ("flow", cls.CONTRACT_FLOW_GROUP),
        ]

    @classmethod
    def audit_contract_text(cls, target: str, content: str) -> list[str]:
        normalized = content or ""
        missing: list[str] = []
        for label, options in cls.contract_validation_groups(target):
            if not any(option in normalized for option in options):
                missing.append(label)
        return missing

    @classmethod
    def contract_validation_groups_for_surface(
        cls,
        target: str,
        surface_key: str,
        surface_path: Path,
    ) -> list[tuple[str, tuple[str, ...]]]:
        groups = cls.contract_validation_groups(target)
        trigger_group = groups[0]
        documents_group = groups[1]
        confirmation_group = groups[2]
        artifacts_group = groups[3]
        flow_group = groups[4]

        normalized = surface_path.as_posix()

        if (
            normalized.endswith("/plugins/marketplace.json")
            or normalized.endswith("/.codex-plugin/plugin.json")
            or normalized.endswith("/.claude-plugin/plugin.json")
            or normalized.endswith("/.claude-plugin/marketplace.json")
        ):
            return []

        if normalized.endswith("/plugins/super-dev-codex/README.md") or normalized.endswith(
            "/plugins/super-dev-claude/README.md"
        ):
            return []

        if (
            "/plugins/super-dev-codex/skills/" in normalized
            or "/plugins/super-dev-claude/skills/" in normalized
        ):
            return []

        if "super-dev-seeai" in normalized:
            if (
                surface_key.startswith("project-slash:")
                or surface_key.startswith("global-slash:")
                or normalized.endswith("/commands/super-dev-seeai.md")
                or normalized.endswith("/commands/super-dev-seeai.toml")
                or normalized.endswith("/workflows/super-dev-seeai.md")
            ):
                return [trigger_group, flow_group]
            if surface_key.startswith("skill:") or "/skills/super-dev-seeai/" in normalized:
                return [trigger_group, flow_group]

        if (
            surface_key.startswith("project-slash:")
            or surface_key.startswith("global-slash:")
            or normalized.endswith("/commands/super-dev.md")
            or normalized.endswith("/commands/super-dev.toml")
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if surface_key.startswith("skill:"):
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if surface_key.startswith("compatibility-protocol:"):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if normalized.endswith(".agent/workflows/super-dev.md"):
            return [documents_group, confirmation_group, flow_group]

        if normalized.endswith("/agents/super-dev.md"):
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if normalized.endswith("AGENTS.md") and cls._managed_agents_markers(target) is not None:
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if normalized.endswith("GEMINI.md"):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if normalized.endswith("/steering/AGENTS.md") or normalized.endswith(
            "/steering/super-dev.md"
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if (
            normalized.endswith("/rules.md")
            or normalized.endswith("/project_rules.md")
            or normalized.endswith("/rules/super-dev.md")
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        return [documents_group, confirmation_group, flow_group]

    @classmethod
    def audit_surface_contract(
        cls,
        target: str,
        surface_key: str,
        surface_path: Path,
        content: str,
    ) -> list[str]:
        normalized = content or ""
        missing: list[str] = []
        for label, options in cls.contract_validation_groups_for_surface(
            target, surface_key, surface_path
        ):
            if not any(option in normalized for option in options):
                missing.append(label)
        return missing

    def collect_managed_surface_paths(
        self,
        target: str,
        skill_name: str = "super-dev",
        *,
        include_user_surfaces: bool = True,
    ) -> dict[str, Path]:
        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        surfaces: dict[str, Path] = {}
        for relative in self.TARGETS[target].files:
            surfaces[f"project:{relative}"] = self.project_dir / relative
        for relative in self.managed_competition_project_surfaces(target):
            surfaces[f"project:{relative}"] = self.project_dir / relative

        if include_user_surfaces:
            protocol_path = self.resolve_global_protocol_path(target)
            if protocol_path is not None:
                surfaces[f"global-protocol:{protocol_path}"] = protocol_path
            for surface in self.managed_user_agent_surfaces(target):
                surface_path = self._resolve_surface_declaration(target=target, surface=surface)
                surfaces[f"global-agent:{surface_path}"] = surface_path

        compatibility_protocol_path = self.resolve_compatibility_protocol_path(target)
        if compatibility_protocol_path is not None:
            surfaces[f"compatibility-protocol:{compatibility_protocol_path}"] = (
                compatibility_protocol_path
            )

        if self.supports_slash(target):
            project_slash = self.resolve_slash_command_path(
                target=target, scope="project", project_dir=self.project_dir
            )
            if project_slash is not None:
                surfaces[f"project-slash:{project_slash}"] = project_slash
            if include_user_surfaces:
                global_slash = self.resolve_slash_command_path(target=target, scope="global")
                if global_slash is not None and global_slash != project_slash:
                    surfaces[f"global-slash:{global_slash}"] = global_slash

        from ..skills import SkillManager

        managed_skill_names = SkillManager.managed_builtin_skill_names(target)
        if skill_name not in managed_skill_names:
            managed_skill_names.append(skill_name)
        for managed_skill_name in managed_skill_names:
            for skill_path in self.expected_skill_paths(target=target, skill_name=managed_skill_name):
                surfaces[f"skill:{skill_path}"] = skill_path

        return surfaces

    def _resolve_surface_declaration(self, *, target: str, surface: str) -> Path:
        normalized = str(surface).strip()
        if normalized == "~/.codex/AGENTS.md":
            return self.resolve_global_protocol_path("codex") or Path(normalized).expanduser()
        if normalized.startswith("~/"):
            return Path(normalized).expanduser()
        return self.project_dir / normalized

    def surface_path_groups(
        self,
        *,
        target: str,
    ) -> dict[str, dict[str, Path]]:
        surfaces = self._install_surfaces(target=target)
        groups: dict[str, dict[str, Path]] = {
            "official_project": {},
            "official_user": {},
            "optional_project": {},
            "optional_user": {},
            "compatibility": {},
        }
        mapping = {
            "official_project_surfaces": "official_project",
            "official_user_surfaces": "official_user",
            "optional_project_surfaces": "optional_project",
            "optional_user_surfaces": "optional_user",
            "observed_compatibility_surfaces": "compatibility",
        }
        for source_key, group_key in mapping.items():
            for surface in surfaces.get(source_key, []):
                if not isinstance(surface, str) or not surface.strip():
                    continue
                path = self._resolve_surface_declaration(target=target, surface=surface)
                groups[group_key][surface] = path
        return groups

    def managed_surface_classification(
        self,
        *,
        target: str,
        skill_name: str = "super-dev",
    ) -> dict[str, dict[str, Any]]:
        managed = self.collect_managed_surface_paths(target=target, skill_name=skill_name)
        groups = self.surface_path_groups(target=target)
        group_path_sets = {
            name: {str(path.resolve()) for path in surfaces.values()}
            for name, surfaces in groups.items()
        }
        classified: dict[str, dict[str, Any]] = {}
        for surface_key, surface_path in managed.items():
            resolved = str(surface_path.resolve())
            group = "unclassified"
            for candidate, path_set in group_path_sets.items():
                if resolved in path_set:
                    group = candidate
                    break
            classified[surface_key] = {
                "path": surface_path,
                "group": group,
                "required": group in {"official_project", "official_user"},
            }
        return classified

    def readiness_surface_sets(
        self,
        *,
        target: str,
        skill_name: str = "super-dev",
    ) -> dict[str, list[Path]]:
        groups = self.surface_path_groups(target=target)
        skill_paths = self.expected_skill_paths(
            target=target,
            skill_name=skill_name,
            project_dir=self.project_dir,
        )

        official_skill_paths: list[Path] = []
        optional_skill_paths: list[Path] = []
        compatibility_skill_paths: list[Path] = []
        for path in skill_paths:
            resolved = str(path.resolve())
            if resolved in {
                str(item.resolve()) for item in groups["official_project"].values()
            } or resolved in {str(item.resolve()) for item in groups["official_user"].values()}:
                official_skill_paths.append(path)
            elif resolved in {
                str(item.resolve()) for item in groups["optional_project"].values()
            } or resolved in {str(item.resolve()) for item in groups["optional_user"].values()}:
                optional_skill_paths.append(path)
            else:
                compatibility_skill_paths.append(path)

        project_slash: Path | None = None
        global_slash: Path | None = None
        if self.supports_slash(target):
            project_slash = self.resolve_slash_command_path(
                target=target,
                scope="project",
                project_dir=self.project_dir,
            )
            global_slash = self.resolve_slash_command_path(target=target, scope="global")
        required_slash_paths: list[Path] = []
        optional_slash_paths: list[Path] = []
        compatibility_slash_paths: list[Path] = []
        official_project_resolved = {str(item.resolve()) for item in groups["official_project"].values()}
        official_user_resolved = {str(item.resolve()) for item in groups["official_user"].values()}
        optional_project_resolved = {str(item.resolve()) for item in groups["optional_project"].values()}
        optional_user_resolved = {str(item.resolve()) for item in groups["optional_user"].values()}
        require_user_level_slash = not bool(official_project_resolved)
        for slash_path in [project_slash, global_slash]:
            if slash_path is None:
                continue
            resolved = str(slash_path.resolve())
            if resolved in official_project_resolved or (
                require_user_level_slash and resolved in official_user_resolved
            ):
                required_slash_paths.append(slash_path)
            elif (
                resolved in official_user_resolved
                or resolved in optional_project_resolved
                or resolved in optional_user_resolved
            ):
                optional_slash_paths.append(slash_path)
            else:
                compatibility_slash_paths.append(slash_path)

        return {
            "official_project": list(groups["official_project"].values()),
            "official_user": list(groups["official_user"].values()),
            "optional_project": list(groups["optional_project"].values()),
            "optional_user": list(groups["optional_user"].values()),
            "compatibility": list(groups["compatibility"].values()),
            "official_skill": official_skill_paths,
            "optional_skill": optional_skill_paths,
            "compatibility_skill": compatibility_skill_paths,
            "required_slash": required_slash_paths,
            "optional_slash": optional_slash_paths,
            "compatibility_slash": compatibility_slash_paths,
        }

    def remove(self, target: str) -> list[Path]:
        """卸载指定宿主的 Super Dev 集成文件"""
        surfaces = self.collect_managed_surface_paths(target=target)
        removed: list[Path] = []
        for _key, path in surfaces.items():
            if path.exists():
                try:
                    if path.name == "AGENTS.md":
                        markers = self._managed_agents_markers(target)
                        if markers is not None and self._remove_managed_block(
                            file_path=path,
                            begin=markers[0],
                            end=markers[1],
                        ):
                            removed.append(path)
                            continue
                    if target == "claude-code" and path.name == "CLAUDE.md":
                        if self._remove_managed_block(
                            file_path=path,
                            begin=self.CLAUDE_RULES_BEGIN,
                            end=self.CLAUDE_RULES_END,
                        ):
                            removed.append(path)
                            continue
                    path.unlink()
                    removed.append(path)
                    # 清理空父目录
                    parent = path.parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except OSError:
                    pass
        return removed

    def _adapter_mode(self, *, target: str, category: str, integration_files: list[str]) -> str:
        first_file = integration_files[0] if integration_files else ""
        adapter_override = get_adapter_mode_override(target)
        if adapter_override:
            return adapter_override
        if category == "cli":
            return "native-cli-session"
        if category == "assistant":
            return "native-desktop-assistant"
        if first_file.startswith(".super-dev/skills/"):
            return "compat-layer-via-project-skill"
        if target == "vscode-copilot":
            return "native-copilot-instruction-file"
        return "native-ide-rule-file"

    def _usage_profile(self, *, target: str, category: str) -> dict[str, object]:
        usage_location = self.HOST_USAGE_LOCATIONS.get(target, "")
        usage_notes = list(self.HOST_USAGE_NOTES.get(target, []))
        shared_usage_notes = [
            "普通开发尽量留在宿主里，不要把终端里的维护命令当成日常主入口。",
            "已有项目做 evolve / variant / patch 时，先让宿主完成 baseline，再进入差量文档与实现。",
            "窗口关闭、电脑重启或第二天回来时，优先直接在宿主里说“继续当前流程”或使用 resume 入口。",
        ]
        for note in shared_usage_notes:
            if note not in usage_notes:
                usage_notes.append(note)
        special_usage = build_special_usage_profile(
            SpecialAdapterContext(
                target=target,
                category=category,
                usage_location=usage_location,
                usage_notes=tuple(usage_notes),
                text_trigger_prefix=self.TEXT_TRIGGER_PREFIX,
                seeai_text_trigger_prefix=self.SEEAI_TEXT_TRIGGER_PREFIX,
            )
        )
        if special_usage is not None:
            return special_usage
        if target == "codex":
            return {
                "usage_mode": "desktop-skill-and-agents",
                "primary_entry": "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；自然语言回退入口是 `super-dev: <需求描述>`。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "desktop",
                        "label": "Codex App/Desktop",
                        "entry": "/super-dev",
                        "mode": "enabled-skill-slash-entry",
                        "priority": "preferred",
                        "notes": "在 `/` 列表中直接选择 `super-dev`；这是已启用 Skill 的官方入口。",
                    },
                    {
                        "surface": "all",
                        "label": "Natural Language Fallback",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "agents-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "由项目 AGENTS.md 驱动的自然语言入口。",
                    },
                ],
                "trigger_context": "Codex App/Desktop 当前会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重开 Codex App/Desktop，使项目 AGENTS 与 Skills 生效。",
                    "优先从 `/` 列表选择 `super-dev` 或 `super-dev-seeai`。",
                    "已有项目先 baseline；恢复时优先直接说 `super-dev: 继续当前流程`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Codex App/Desktop 与 Codex CLI 共用 AGENTS.md + Skills 主面，但桌面端以 `/` 列表里的已启用 Skill 入口为第一入口。",
            }
        if target == "codex-cli":
            return {
                "usage_mode": "agents-and-skill",
                "primary_entry": "Codex CLI 优先显式输入 `$super-dev`；回退可用 `super-dev: <需求描述>` 作为 AGENTS 驱动的自然语言入口。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "cli",
                        "label": "Codex CLI",
                        "entry": "$super-dev",
                        "mode": "explicit-skill",
                        "priority": "preferred",
                        "notes": "CLI 中官方显式调用 Skill 的方式，最符合 Codex Skills 文档。",
                    },
                    {
                        "surface": "all",
                        "label": "Codex App/Desktop + CLI",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "agents-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "默认由项目 AGENTS.md 驱动的自然语言入口；若显式启用 `--with-user-surfaces`，也可跨项目沿用全局 AGENTS 作为统一回退方式。",
                    },
                ],
                "trigger_context": "Codex 当前会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重启 codex，使项目根 AGENTS.md、项目级 .agents/skills/super-dev、repo marketplace `.agents/plugins/marketplace.json`、repo plugin `plugins/super-dev-codex/` 与 ~/.agents/skills/super-dev/SKILL.md 生效；如需跨项目用户级协议面，再显式启用 `--with-user-surfaces` 写入 CODEX_HOME/AGENTS.md。",
                    "Codex CLI 优先显式输入 `$super-dev`。",
                    "已有项目做增量迭代、派生版本或缺陷修复时，先让宿主完成 baseline，再继续三文档与实现。",
                    "中断后恢复优先用 `super-dev: 继续当前流程`，需要显式阶段跳转时使用 `super-dev-run: resume`。",
                    "如果你已经在自然语言上下文里继续当前流程，也可以直接说 `super-dev: <需求描述>`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Codex CLI 官方最佳接入面是项目根 AGENTS.md + 分层 `.agents/skills` + 官方用户 skills 目录 ~/.agents/skills；repo 级 `.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json` 作为可选 repo plugin enhancement 保留。CODEX_HOME/AGENTS.md（默认 ~/.codex/AGENTS.md）改成显式 `--with-user-surfaces` 才写入，用于跨项目复用统一宿主心智。Codex CLI 的官方显式入口是 `$super-dev`；`super-dev:` 作为 AGENTS 驱动的自然语言回退入口保留。已有项目的 `evolve / variant / patch` 必须先 baseline；恢复默认按当前 workflow state 继续，而不是重新开题。",
            }
        if target == "claude":
            return {
                "usage_mode": "desktop-projects-manual",
                "primary_entry": "在 Claude Desktop 当前 Project 中直接说 `super-dev: <需求描述>`；比赛模式说 `super-dev-seeai: <比赛需求>`。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "desktop",
                        "label": "Claude Project",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "projects-natural-language",
                        "priority": "preferred",
                        "notes": "依赖 Claude Project Instructions / Knowledge / extensions 的官方项目面。",
                    }
                ],
                "trigger_context": "Claude Desktop 当前 Project",
                "usage_location": usage_location,
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "在 Claude 当前 Project 中挂上 Project Instructions、Project Knowledge 与需要的 extensions / local MCP。",
                    "随后直接说 `super-dev: <需求描述>`，不要先开普通闲聊线程。",
                ],
                "usage_notes": usage_notes,
                "notes": "Claude Desktop 当前按 Projects / Instructions / Knowledge / extensions 官方面建模，不依赖仓库 dotfile 自动注入。",
            }
        if target == "claude-code":
            return {
                "usage_mode": "native-slash-and-skill",
                "primary_entry": "在 Claude Code 当前项目会话里优先使用 `/super-dev <需求描述>`；底层由项目根 `CLAUDE.md`、项目级 `.claude/CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户 `.claude/skills/` 与项目/用户 `.claude/agents/` 驱动，`.claude/commands/` 只作为兼容增强面保留。",
                "trigger_command": "/super-dev <需求描述>",
                "entry_variants": [
                    {
                        "surface": "app_cli",
                        "label": "Claude Code",
                        "entry": "/super-dev",
                        "mode": "native-slash",
                        "priority": "preferred",
                        "notes": "Slash 仍是用户最直接的触发入口，但其底层应汇入根 `CLAUDE.md` + skills-first 的同一条 Super Dev 流程。",
                    },
                    {
                        "surface": "all",
                        "label": "Fallback",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "rules-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "自然语言回退入口仍保留，用于当前会话已在项目上下文中继续当前 Super Dev 流程。",
                    },
                ],
                "trigger_context": "Claude Code 当前项目会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "确认项目根 `CLAUDE.md` 与项目级 `.claude/CLAUDE.md` 都已写入 Super Dev 规则块。",
                    "如果需要宿主级配置增强，确认 `.claude/settings.json` / `.claude/settings.local.json` 已包含当前接入所需配置与 hooks。",
                    "确认项目级 `.claude/skills/super-dev/SKILL.md` 与用户级 `~/.claude/skills/super-dev/SKILL.md` 已存在。",
                    "确认项目级 `.claude/agents/super-dev.md` 与用户级 `~/.claude/agents/super-dev.md` 已存在。",
                    "如需兼容命令面，再确认 `.claude/commands/super-dev.md` 已生成。",
                    "若要启用增强层，确认 `.claude-plugin/marketplace.json` 与 `plugins/super-dev-claude/.claude-plugin/plugin.json` 已存在。",
                    "在 Claude Code 当前项目会话里输入 `/super-dev <需求描述>` 触发完整流程。",
                    "已有项目的增量开发先做 baseline；关闭窗口或第二天回来时，优先说“继续当前流程”或显式执行 `/super-dev-run resume`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Claude Code 当前最佳接入面是项目根 `CLAUDE.md` + 项目级 `.claude/CLAUDE.md` + 可选 `.claude/settings*.json` + 项目/用户 `.claude/skills/` + 项目/用户 `.claude/agents/`；`.claude/commands/` 保留为兼容增强面；repo 级 `.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json` 作为可选 plugin enhancement 一并提供。已有项目的 `evolve / variant / patch` 必须先 baseline；恢复是默认场景，不应重新开题。",
            }
        if target == "antigravity":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Antigravity Agent Chat 输入 `/super-dev <需求描述>`（由 GEMINI.md + custom commands 主面承接；`.agent/workflows` 与 `~/.gemini/skills/` 只作为增强层）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Antigravity IDE Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Antigravity，或至少新开一个 Agent Chat。",
                    "确认项目内已生成 `GEMINI.md`、`.gemini/commands/super-dev.toml` 与 `.agent/workflows/super-dev.md`。",
                    "若当前安装启用了增强层，再确认 `~/.gemini/skills/super-dev/SKILL.md` 已存在；只有显式 `--with-user-surfaces` 时才检查 `~/.gemini/GEMINI.md` 与 `~/.gemini/commands/super-dev.toml`。",
                    "在 Antigravity Agent Chat 输入 `/super-dev <需求描述>` 触发完整流程。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”。",
                ],
                "usage_notes": usage_notes,
                "notes": "Antigravity 当前按 GEMINI 上下文面 + custom commands 主面接入；`.agent/workflows` 与宿主级 Skill 只保留为当前推荐增强层。",
            }
        if target == "trae":
            return {
                "usage_mode": "rules-and-skill",
                "primary_entry": "在 Trae Agent Chat 输入 `super-dev: <需求描述>`（默认由 .trae/project_rules.md + .trae/rules.md 生效；用户级 ~/.trae/* 仅在显式 `--with-user-surfaces` 时写入；兼容 Skill 若检测到会额外增强）",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "trigger_context": "Trae Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Trae，或至少新开一个 Agent Chat，使新的规则与兼容 Skill（若已安装）一起生效。",
                    "默认确认项目内已生成 `.trae/project_rules.md` 与 `.trae/rules.md`；只有显式 `--with-user-surfaces` 时再检查 `~/.trae/user_rules.md` 与 `~/.trae/rules.md`。",
                    "确保当前项目就是已接入 Super Dev 的工作区。",
                    "输入 `super-dev: <需求描述>` 触发完整流程。",
                    "按 output/* 与 .super-dev/changes/*/tasks.md 执行开发。",
                ],
                "usage_notes": usage_notes,
                "notes": "该宿主当前默认以项目级 `.trae/project_rules.md` 与 `.trae/rules.md` 为核心接入面；用户级 `~/.trae/user_rules.md` / `~/.trae/rules.md` 改成显式 `--with-user-surfaces` 时才写入，若检测到 ~/.trae/skills，则会增强安装 super-dev Skill。",
            }
        if target == "kiro":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Kiro IDE Agent Chat 输入 `/super-dev <需求描述>`（由 `.kiro/steering/super-dev.md` + `.kiro/skills/` / `~/.kiro/steering/` + `~/.kiro/skills/` 生效）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Kiro IDE Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Kiro，或至少新开一个 Agent Chat，使 steering 与 skills 一起生效。",
                    "确保当前项目就是已接入 Super Dev 的工作区。",
                    "优先输入 `/super-dev <需求描述>` 触发完整流程；若当前会话只接受自然语言，再回退到 `super-dev: <需求描述>`。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”或执行 `/super-dev-run resume`。",
                    "按 output/* 与 .super-dev/changes/*/tasks.md 执行开发。",
                ],
                "usage_notes": usage_notes,
                "notes": "该宿主当前走官方 steering + skills 模式：项目级 `.kiro/steering/super-dev.md` 负责长期行为约束，项目级 `.kiro/skills/` 与 `~/.kiro/skills/` 提供能力增强，`~/.kiro/steering/` 提供全局 steering 记忆。",
            }
        if target == "kiro-cli":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Kiro CLI 会话输入 `/super-dev <需求描述>`（由 `.kiro/steering/super-dev.md` + `.kiro/skills/` / `~/.kiro/steering/` + `~/.kiro/skills/` 生效）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Kiro CLI 当前会话",
                "usage_location": usage_location
                or "进入目标项目目录后，重开 Kiro CLI 会话再触发。",
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重开 Kiro CLI，使 `.kiro/steering/` 与 skills 在新会话里生效。",
                    "确认项目内已生成 `.kiro/steering/super-dev.md` 与 `.kiro/skills/super-dev/SKILL.md`。",
                    "确认用户目录已生成 `~/.kiro/steering/super-dev.md` 与 `~/.kiro/skills/super-dev/SKILL.md`。",
                    "在 Kiro CLI 会话里优先输入 `/super-dev <需求描述>`；若当前会话只接受自然语言，再回退到 `super-dev: <需求描述>`。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”或显式执行 `/super-dev-run resume`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Kiro CLI 当前按官方 steering + skills 模式触发：steering 负责长期上下文和行为约束，skills 负责让宿主理解完整 Super Dev 流程；slash 入口是否出现应以宿主命令面实际暴露为准。",
            }
        if self.supports_slash(target):
            if category == "cli":
                return {
                    "usage_mode": "native-slash",
                    "primary_entry": "/super-dev <需求描述>（在该 CLI 宿主会话内）",
                    "trigger_command": "/super-dev <需求描述>",
                    "trigger_context": "当前 CLI 宿主会话",
                    "usage_location": usage_location
                    or "在项目目录启动宿主当前 CLI 会话后，直接在同一会话里触发。",
                    "requires_restart_after_onboard": False,
                    "post_onboard_steps": [
                    "保持在宿主当前会话中执行 /super-dev。",
                    "已有项目的 `evolve / variant / patch` 先 baseline，再继续文档和实现。",
                    "中断后恢复优先用 `/super-dev-run resume`，不支持 slash 时使用 `super-dev: 继续当前流程`。",
                    "让宿主先完成同类产品研究，再继续文档与编码阶段。",
                ],
                    "usage_notes": usage_notes
                    or [
                        "建议在同一会话里连续完成 research、文档、Spec 与编码。",
                        "接入时还会安装宿主级 super-dev Skill，让宿主理解完整流水线契约。",
                    ],
                    "notes": "CLI 宿主建议直接在当前会话执行 slash 命令；slash 负责触发，host skill 负责让宿主理解 Super Dev 流水线协议。已有项目先 baseline，恢复默认回到当前 workflow state。",
                }
            if category == "assistant":
                return {
                    "usage_mode": "desktop-slash",
                    "primary_entry": "/super-dev <需求描述>（在桌面助手当前工作区/会话内）",
                    "trigger_command": "/super-dev <需求描述>",
                    "trigger_context": "桌面助手当前工作区/会话",
                    "usage_location": usage_location
                    or "打开桌面助手当前工作区/会话，并保持目标项目上下文后触发。",
                    "requires_restart_after_onboard": False,
                    "post_onboard_steps": [
                        "在当前桌面助手工作区/会话中直接执行 /super-dev。",
                        "已有项目的 `evolve / variant / patch` 先 baseline，再继续三文档和实现。",
                        "中断后恢复优先说“继续当前流程”或直接回当前工作区/线程续跑。",
                    ],
                    "usage_notes": usage_notes,
                    "notes": "桌面助手优先通过当前工作区/会话触发；slash 负责进入流程，skills / rules / continuity 负责保持连续性。",
                }
            return {
                "usage_mode": "native-slash",
                "primary_entry": "/super-dev <需求描述>（在 IDE Agent Chat 内）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "IDE Agent Chat",
                "usage_location": usage_location
                or "打开宿主 IDE 的 Agent Chat，在当前项目上下文内触发。",
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "在 IDE Agent Chat 中执行 /super-dev。",
                    "已有项目的 `evolve / variant / patch` 先 baseline，再继续三文档和实现。",
                    "中断后恢复优先用 `/super-dev-run resume`，不支持 slash 的宿主则直接说“继续当前流程”。",
                    "保持研究、文档、Spec 与编码在同一上下文中连续完成。",
                ],
                "usage_notes": usage_notes
                or [
                    "建议固定在项目级 Agent Chat 中完成整条流水线。",
                    "接入时还会安装宿主级 super-dev Skill，让宿主理解完整流水线契约。",
                ],
                "notes": "IDE 宿主优先通过 Agent Chat 触发；slash 负责触发，host skill 负责让宿主理解 Super Dev 流水线协议。已有项目先 baseline，恢复默认回到当前 workflow state。",
            }
        return {
            "usage_mode": "rules-only",
            "primary_entry": "输入 `super-dev: <需求描述>`（由项目规则生效）",
            "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
            "entry_variants": [
                {
                    "surface": "default",
                    "label": "Default",
                    "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                    "mode": "rules-natural-language",
                    "priority": "preferred",
                    "notes": "由项目规则文件驱动的标准入口。",
                }
            ],
            "trigger_context": "宿主当前会话",
            "usage_location": usage_location
            or (
                "在桌面助手当前会话里触发。"
                if category == "assistant"
                else "在宿主当前项目会话里触发。"
            ),
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "直接在宿主会话输入 `super-dev: <需求描述>`。",
                "已有项目先 baseline；关闭窗口或第二天回来时直接说 `super-dev: 继续当前流程`。",
                "按 output/* 与 tasks.md 继续执行开发流程。",
            ],
            "usage_notes": usage_notes
            or [
                "该宿主当前通过规则文件约束执行流程。",
            ],
            "notes": "该宿主通过项目规则文件约束执行流程。已有项目先 baseline，恢复默认沿用当前 workflow state 与 output 工件。",
        }

    def _smoke_profile(self, *, target: str, category: str) -> dict[str, object]:
        trigger = (
            self.TEXT_TRIGGER_PREFIX
            + " 请先不要开始编码，只回复 SMOKE_OK，并确认已读取当前项目中的 Super Dev 规则。"
        )
        competition_trigger = (
            self.SEEAI_TEXT_TRIGGER_PREFIX
            + " 请先不要开始编码，只回复 SEEAI_SMOKE_OK，并说明你会按半小时比赛链路执行：先 fast research、再 compact 三文档、确认后 compact Spec、然后 full-stack sprint；同时承诺 12 分钟内先跑出第一个可见界面，若初始化失败会立刻切轻量回退栈，且保留下来的模块都必须真实启动并进入主演示路径。"
        )
        if self.supports_slash(target):
            trigger = "/super-dev 请先不要开始编码，只回复 SMOKE_OK，并确认已读取当前项目中的 Super Dev 规则。"
            competition_trigger = "/super-dev-seeai 请先不要开始编码，只回复 SEEAI_SMOKE_OK，并说明你会按半小时比赛链路执行：先 fast research、再 compact 三文档、确认后 compact Spec、然后 full-stack sprint；同时承诺 12 分钟内先跑出第一个可见界面，若初始化失败会立刻切轻量回退栈，且保留下来的模块都必须真实启动并进入主演示路径。"
        if target == "codex":
            steps = [
                "完成接入后先重开 Codex App/Desktop。",
                "进入已接入 Super Dev 的目标项目工作区。",
                f"优先在 Codex App/Desktop 会话输入：{trigger}",
                "如果 `/` 列表里出现 `super-dev`，优先直接选择它。",
            ]
            competition_steps = [
                "完成接入后先重开 Codex App/Desktop。",
                "进入已接入 Super Dev 的目标项目工作区。",
                f"优先在 Codex App/Desktop 会话输入：{competition_trigger}",
                "如果 `/` 列表里出现 `super-dev-seeai`，优先直接选择它。",
            ]
        elif target == "codex-cli":
            steps = [
                "完成接入后先重启 codex。",
                "进入已接入 Super Dev 的项目目录。",
                f"优先在 Codex 会话输入：{trigger}",
                "如果你想显式调用官方 Skill，可输入 `$super-dev`；如果桌面端 `/` 列表里出现 `super-dev`，也可以直接选择它。",
            ]
            competition_steps = [
                "完成接入后先重启 codex。",
                "进入已接入 Super Dev 的项目目录。",
                f"优先在 Codex 会话输入：{competition_trigger}",
                "如果你想显式调用官方 SEEAI Skill，可输入 `$super-dev-seeai`；如果桌面端 `/` 列表里出现 `super-dev-seeai`，也可以直接选择它。",
            ]
        else:
            steps = [
                "进入已接入 Super Dev 的项目目录或工作区。",
                f"在宿主正确的聊天/会话入口输入：{trigger}",
            ]
            competition_steps = [
                "进入已接入 Super Dev 的项目目录或工作区。",
                f"在宿主正确的聊天/会话入口输入：{competition_trigger}",
            ]
        if category == "ide":
            steps.insert(1, "确认当前 Agent Chat/Workflow 绑定的是目标项目。")
            competition_steps.insert(1, "确认当前 Agent Chat/Workflow 绑定的是目标项目。")
        elif category == "assistant":
            steps.insert(1, "确认当前桌面助手会话/工作区绑定的是目标项目。")
            competition_steps.insert(1, "确认当前桌面助手会话/工作区绑定的是目标项目。")
        competition_steps.extend(get_competition_smoke_extra_steps(target))
        competition_suite = build_seeai_smoke_suite(
            "$super-dev-seeai"
            if target == "codex-cli"
            else (
                "/super-dev-seeai"
                if self.supports_slash(target)
                else self.SEEAI_TEXT_TRIGGER_PREFIX
            )
        )
        return {
            "smoke_test_prompt": trigger,
            "smoke_test_steps": steps,
            "smoke_success_signal": "宿主回复 SMOKE_OK，并明确表示已读取当前项目内的 Super Dev 规则/AGENTS/命令映射，且没有直接开始编码。",
            "competition_smoke_test_prompt": competition_trigger,
            "competition_smoke_test_steps": competition_steps,
            "competition_smoke_success_signal": "宿主回复 SEEAI_SMOKE_OK，并在首轮明确给出作品类型、wow 点、P0 主路径、主动放弃项，同时表示将按半小时比赛链路执行：fast research -> compact 三文档 -> docs confirm -> compact Spec -> full-stack sprint；且明确承诺 12 分钟内先跑出首个可见界面，初始化失败会立刻切轻量回退栈，保留下来的模块都必须真实启动并进入主演示路径。",
            "competition_smoke_suite": competition_suite,
            "competition_acceptance_gates": get_seeai_acceptance_gates(),
            "competition_evidence_template": build_seeai_evidence_template(),
        }

    def _precondition_profile(self, *, target: str) -> dict[str, object]:
        guidance = list(self.HOST_PRECONDITION_GUIDANCE.get(target, []))
        items: list[dict[str, object]] = []
        usage = self._usage_profile(
            target=target, category=HOST_TOOL_CATEGORY_MAP.get(target, "ide")
        )

        context_item: dict[str, object] = {
            "status": "project-context-required",
            "label": "需在目标项目/工作区内触发",
            "guidance": [str(usage["usage_location"]).strip()],
            "signals": {
                "project_dir_exists": self.project_dir.exists(),
            },
        }
        if str(usage["usage_location"]).strip():
            items.append(context_item)

        if bool(usage["requires_restart_after_onboard"]):
            items.append(
                {
                    "status": "session-restart-required",
                    "label": "接入后需重开宿主会话",
                    "guidance": [
                        "完成接入或维护修复后，关闭旧会话并新开一个宿主会话，再触发 Super Dev。",
                    ],
                    "signals": {},
                }
            )

        extra = [item for item in guidance if isinstance(item, str) and item.strip()]
        if extra and items:
            first_guidance = self._string_list(items[0].get("guidance"))
            items[0]["guidance"] = list(dict.fromkeys([*first_guidance, *extra]))

        if not items:
            return {
                "status": "none",
                "label": "无额外前置条件",
                "guidance": [],
                "signals": {},
                "items": [],
            }

        priority = {
            "host-auth-required": 0,
            "session-restart-required": 1,
            "project-context-required": 2,
        }
        primary = min(
            items,
            key=lambda item: priority.get(str(item.get("status", "")), 99),
        )
        combined_guidance: list[str] = []
        combined_signals: dict[str, bool] = {}
        for item in items:
            for guidance_item in self._string_list(item.get("guidance")):
                if guidance_item not in combined_guidance:
                    combined_guidance.append(guidance_item)
            for key, value in self._bool_dict(item.get("signals")).items():
                combined_signals[key] = value

        return {
            "status": str(primary.get("status", "none")),
            "label": str(primary.get("label", "无额外前置条件")),
            "guidance": combined_guidance,
            "signals": combined_signals,
            "items": items,
        }

    def _protocol_profile(self, *, target: str) -> dict[str, str]:
        registry_mode = str(get_protocol_mode(target) or "").strip()
        registry_summary = str(get_protocol_summary(target) or "").strip()
        if registry_mode or registry_summary:
            return {
                "mode": registry_mode or "custom",
                "summary": registry_summary or registry_mode or "custom host protocol",
            }

        mapping = {
            "claude-code": {
                "mode": "official-skill",
                "summary": "官方 CLAUDE.md + settings + project/user skills + subagents",
            },
            "antigravity": {
                "mode": "recommended-gemini-workflow",
                "summary": "当前推荐接入模型: GEMINI.md + custom commands + optional workflows",
            },
            "codebuddy-cli": {
                "mode": "official-skill",
                "summary": "官方 CODEBUDDY.md + commands + skills + AGENTS.md compatibility",
            },
            "codebuddy": {
                "mode": "official-subagent",
                "summary": "官方 CODEBUDDY.md + rules + skills + task/workspace continuity",
            },
            "vscode-copilot": {
                "mode": "official-context",
                "summary": "官方 copilot-instructions + AGENTS.md compatibility",
            },
            "cline": {
                "mode": "official-context",
                "summary": "官方 .clinerules + skills + AGENTS.md compatibility",
            },
            "roo-code": {
                "mode": "official-skill",
                "summary": "官方 commands + rules",
            },
            "qoder-cli": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            },
            "qoder": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            },
            "windsurf": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + workflows + skills",
            },
            "opencode": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + commands + skills (+ optional agents)",
            },
            "kilo-code": {
                "mode": "official-rules",
                "summary": "官方 rules",
            },
            "kiro": {
                "mode": "official-steering",
                "summary": "官方 AGENTS.md + steering + skills + agent continuity",
            },
            "codex": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + Skills + App/Desktop enabled Skill entry",
            },
            "codex-cli": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + Skills + CLI $skill entry",
            },
            "copilot-cli": {
                "mode": "official-context",
                "summary": "官方 copilot-instructions + AGENTS.md + skills + agents",
            },
            "cursor-cli": {
                "mode": "official-context",
                "summary": "官方 AGENTS.md + .cursor/rules + native resume",
            },
            "cursor": {
                "mode": "official-context",
                "summary": "官方 Agent Chat + AGENTS.md + rules (+ beta commands)",
            },
            "gemini-cli": {
                "mode": "official-context",
                "summary": "官方 GEMINI.md + settings + custom commands",
            },
            "kimi-code": {
                "mode": "official-agents-entry",
                "summary": "AGENTS.md + explicit /skill:/flow entries + native session resume",
            },
            "qwen-code": {
                "mode": "official-context",
                "summary": "官方 QWEN.md + settings + commands + skills + agents + /resume",
            },
            "droid-cli": {
                "mode": "official-factory",
                "summary": "官方 AGENTS.md + .factory/rules + skills (+ legacy commands)",
            },
            "kiro-cli": {
                "mode": "official-steering",
                "summary": "官方 AGENTS.md + steering + skills + native resume",
            },
            "trae": {
                "mode": "recommended-project-context",
                "summary": "当前推荐项目上下文模型: project rules + compatibility rules + optional skills",
            },
            "trae-cn": {
                "mode": "recommended-cn-workspace-flow",
                "summary": "当前推荐中文工作区模型: workspace skills + built-in /plan /spec + CN continuity",
            },
            "trae-solo": {
                "mode": "workspace-rules-commands-skills",
                "summary": "当前推荐工作区接入模型: rules + commands + skills + workspace continuity",
            },
            "trae-solocn": {
                "mode": "workspace-mtc-code-skills",
                "summary": "当前推荐中文工作区模型: MTC / Code + skills + built-in /plan /spec + continuity",
            },
            "codebuddy-cn": {
                "mode": "official-subagent",
                "summary": "官方 CODEBUDDY.md + rules + skills + 中文任务/workspace continuity",
            },
            "workbuddy": {
                "mode": "manual-task-workbench-mcp",
                "summary": "当前推荐任务工作台模型: Skills + MCP + task continuity",
            },
        }
        return mapping.get(target, {"mode": "none", "summary": ""})

    def _install_surfaces(self, *, target: str) -> dict[str, list[str]]:
        adapter_surfaces = get_special_install_surfaces(target)
        if adapter_surfaces is not None:
            adapter_surfaces.setdefault("optional_project_surfaces", [])
            adapter_surfaces.setdefault("optional_user_surfaces", [])
            return adapter_surfaces
        by_target: dict[str, dict[str, list[str]]] = {
            "claude": {
                "official_project_surfaces": [],
                "official_user_surfaces": [],
                "optional_project_surfaces": [],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
            "claude-code": {
                "official_project_surfaces": [
                    "CLAUDE.md",
                    ".claude/CLAUDE.md",
                    ".claude/skills/super-dev/SKILL.md",
                    ".claude/agents/super-dev.md",
                ],
                "official_user_surfaces": [
                    "~/.claude/skills/super-dev/SKILL.md",
                    "~/.claude/agents/super-dev.md",
                ],
                "optional_project_surfaces": [
                    ".claude/settings.json",
                    ".claude/settings.local.json",
                    ".claude/commands/super-dev.md",
                    ".claude-plugin/marketplace.json",
                    "plugins/super-dev-claude/.claude-plugin/plugin.json",
                    "plugins/super-dev-claude/README.md",
                    "plugins/super-dev-claude/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": [
                    "~/.claude/CLAUDE.md",
                    "~/.claude/settings.json",
                    "~/.claude/commands/super-dev.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "antigravity": {
                "official_project_surfaces": [
                    "GEMINI.md",
                    ".gemini/commands/super-dev.toml",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": [
                    ".agent/workflows/super-dev.md",
                ],
                "optional_user_surfaces": [
                    "~/.gemini/GEMINI.md",
                    "~/.gemini/commands/super-dev.toml",
                ],
                "observed_compatibility_surfaces": ["~/.gemini/skills/super-dev/SKILL.md"],
            },
            "vscode-copilot": {
                "official_project_surfaces": [".github/copilot-instructions.md"],
                "official_user_surfaces": [],
                "observed_compatibility_surfaces": ["AGENTS.md"],
            },
            "cline": {
                "official_project_surfaces": [
                    ".clinerules/super-dev.md",
                    ".cline/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.cline/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": ["~/Documents/Cline/Rules/super-dev.md"],
                "observed_compatibility_surfaces": ["AGENTS.md"],
            },
            "kilo-code": {
                "official_project_surfaces": [
                    ".kilocode/rules/super-dev.md",
                    ".kilocode/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.kilocode/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "roo-code": {
                "official_project_surfaces": [
                    ".roo/rules/super-dev.md",
                    ".roo/commands/super-dev.md",
                ],
                "official_user_surfaces": ["~/.roo/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.roo/rules/super-dev.md",
                    "~/.roo/commands/super-dev.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "codex-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".agents/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [
                    ".agents/plugins/marketplace.json",
                    "plugins/super-dev-codex/.codex-plugin/plugin.json",
                    "plugins/super-dev-codex/README.md",
                    "plugins/super-dev-codex/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": ["~/.codex/AGENTS.md"],
                "observed_compatibility_surfaces": ["~/.codex/skills/super-dev/SKILL.md"],
            },
            "codex": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".agents/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [
                    ".agents/plugins/marketplace.json",
                    "plugins/super-dev-codex/.codex-plugin/plugin.json",
                    "plugins/super-dev-codex/README.md",
                    "plugins/super-dev-codex/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": ["~/.codex/AGENTS.md"],
                "observed_compatibility_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                    "~/.codex/skills/super-dev/SKILL.md",
                ],
            },
            "copilot-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".github/copilot-instructions.md",
                    ".github/agents/super-dev.md",
                    ".github/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.copilot/copilot-instructions.md",
                    "~/.copilot/agents/super-dev.md",
                    "~/.copilot/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "cursor-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".cursor/rules/super-dev.mdc",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": ["CLAUDE.md"],
                "observed_compatibility_surfaces": [
                    "~/.cursor/skills/super-dev/SKILL.md",
                ],
            },
            "cursor": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".cursor/rules/super-dev.mdc",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": ["CLAUDE.md", ".cursor/commands/super-dev.md"],
                "optional_user_surfaces": ["~/.cursor/commands/super-dev.md"],
                "observed_compatibility_surfaces": [
                    "~/.cursor/skills/super-dev/SKILL.md",
                ],
            },
            "windsurf": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".windsurf/rules/super-dev.md",
                    ".windsurf/workflows/super-dev.md",
                    ".windsurf/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [],
                "optional_user_surfaces": ["~/.codeium/windsurf/skills/super-dev/SKILL.md"],
                "observed_compatibility_surfaces": [],
            },
            "gemini-cli": {
                "official_project_surfaces": ["GEMINI.md", ".gemini/commands/super-dev.toml"],
                "official_user_surfaces": [],
                "optional_project_surfaces": [".gemini/settings.json"],
                "optional_user_surfaces": [
                    "~/.gemini/GEMINI.md",
                    "~/.gemini/settings.json",
                    "~/.gemini/commands/super-dev.toml",
                    "~/.gemini/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": ["~/.gemini/skills/super-dev/SKILL.md"],
            },
            "kiro-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".kiro/steering/super-dev.md",
                    ".kiro/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.kiro/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.kiro/steering/super-dev.md",
                    "~/.kiro/steering/AGENTS.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "kiro": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".kiro/steering/super-dev.md",
                    ".kiro/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.kiro/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.kiro/steering/super-dev.md",
                    "~/.kiro/steering/AGENTS.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "opencode": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".opencode/commands/super-dev.md",
                    ".opencode/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.config/opencode/AGENTS.md",
                    "~/.config/opencode/commands/super-dev.md",
                    "~/.config/opencode/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [".opencode/agents/super-dev.md"],
                "optional_user_surfaces": ["~/.config/opencode/agents/super-dev.md"],
                "observed_compatibility_surfaces": [],
            },
            "qoder-cli": {
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
                "observed_compatibility_surfaces": [],
            },
            "qoder": {
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
                "observed_compatibility_surfaces": [],
            },
            "trae": {
                "official_project_surfaces": [".trae/project_rules.md"],
                "official_user_surfaces": [],
                "optional_user_surfaces": ["~/.trae/user_rules.md"],
                "observed_compatibility_surfaces": [
                    ".trae/rules.md",
                    "~/.trae/rules.md",
                    "~/.trae/skills/super-dev/SKILL.md",
                ],
            },
            "trae-cn": {
                "official_project_surfaces": [
                    ".trae/project_rules.md",
                    ".trae/rules.md",
                    ".trae/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.trae-cn/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": ["~/.trae/user_rules.md"],
                "observed_compatibility_surfaces": [
                    ".trae/rules.md",
                    "~/.trae/rules.md",
                ],
            },
            "codebuddy-cn": {
                "official_project_surfaces": [
                    "CODEBUDDY.md",
                    ".codebuddy/rules/super-dev/RULE.mdc",
                    ".codebuddy/skills/super-dev/SKILL.md",
                    ".codebuddy/skills/super-dev-seeai/SKILL.md",
                ],
                "official_user_surfaces": ["~/.codebuddy/skills/super-dev/SKILL.md"],
                "optional_project_surfaces": [
                    ".codebuddy/commands/super-dev.md",
                    ".codebuddy/agents/super-dev.md",
                    ".codebuddy/commands/super-dev-seeai.md",
                ],
                "optional_user_surfaces": [
                    "~/.codebuddy/CODEBUDDY.md",
                    "~/.codebuddy/agents/super-dev.md",
                    "~/.codebuddy/commands/super-dev-seeai.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "qwen-code": {
                "official_project_surfaces": [
                    "QWEN.md",
                    ".qwen/commands/super-dev.md",
                    ".qwen/skills/super-dev/SKILL.md",
                    ".qwen/agents/super-dev.md",
                ],
                "official_user_surfaces": [
                    "~/.qwen/QWEN.md",
                    "~/.qwen/skills/super-dev/SKILL.md",
                    "~/.qwen/commands/super-dev.md",
                    "~/.qwen/agents/super-dev.md",
                ],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
        }
        surfaces = by_target.get(
            target,
            {
                "official_project_surfaces": [],
                "official_user_surfaces": [],
                "optional_project_surfaces": [],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
        )
        surfaces.setdefault("optional_project_surfaces", [])
        surfaces.setdefault("optional_user_surfaces", [])
        return surfaces

    def setup(self, target: str, force: bool = False) -> list[Path]:
        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        written_files: list[Path] = []
        integration = self.TARGETS[target]
        for relative in integration.files:
            file_path = self.project_dir / relative
            markers = self._managed_agents_markers(target)
            if relative == "AGENTS.md" and markers is not None:
                block_content = self._append_flow_contract(
                    content=self._build_file_content(target=target, relative=relative),
                    relative=relative,
                )
                updated = self._upsert_managed_block(
                    file_path=file_path,
                    begin=markers[0],
                    end=markers[1],
                    block_content=block_content,
                )
                if updated:
                    written_files.append(file_path)
                continue
            if target == "claude-code" and relative in {"CLAUDE.md", ".claude/CLAUDE.md"}:
                block_content = self._append_flow_contract(
                    content=self._build_file_content(target=target, relative=relative),
                    relative=relative,
                )
                updated = self._upsert_managed_block(
                    file_path=file_path,
                    begin=self.CLAUDE_RULES_BEGIN,
                    end=self.CLAUDE_RULES_END,
                    block_content=block_content,
                )
                if updated:
                    written_files.append(file_path)
                continue
            if file_path.exists() and not force:
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=relative),
                relative=relative,
            )
            file_path.write_text(content, encoding="utf-8")
            written_files.append(file_path)

        # Auto-install enforcement hooks for supported hosts
        if target == "claude-code":
            try:
                from .._enforcement_bridge import auto_install_enforcement

                enforcement_files = auto_install_enforcement(self.project_dir)
                written_files.extend(enforcement_files)
            except Exception:
                pass  # Graceful degradation — enforcement is optional

        written_files.extend(self._setup_seeai_mode_surfaces(target=target, force=force))

        return written_files

    def _setup_seeai_mode_surfaces(self, *, target: str, force: bool) -> list[Path]:
        written: list[Path] = []
        seen: set[str] = set()

        def _append(path: Path | None) -> None:
            if path is None:
                return
            key = str(path.resolve())
            if key in seen:
                return
            seen.add(key)
            written.append(path)

        if self.supports_slash(target):
            seeai_slash = self.setup_seeai_slash_command(target=target, force=force)
            _append(seeai_slash)

        for relative in self.managed_competition_project_surfaces(target):
            file_path = self.project_dir / relative
            if file_path.exists() and not force:
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=relative),
                relative=relative,
            )
            file_path.write_text(content, encoding="utf-8")
            _append(file_path)

        return written

    @classmethod
    def managed_competition_project_surfaces(cls, target: str) -> list[str]:
        if target not in cls.TARGETS:
            return []

        candidates: list[str] = []
        if cls.supports_slash(target):
            seeai_slash_relative = cls.SLASH_COMMAND_FILES[target].replace(
                "super-dev",
                "super-dev-seeai",
            )
            if seeai_slash_relative not in candidates:
                candidates.append(seeai_slash_relative)
        project_files = tuple(cls.TARGETS[target].files) + tuple(cls.TARGETS[target].optional_files)
        for relative in project_files:
            normalized = relative.replace("\\", "/")
            if "super-dev-seeai" not in normalized:
                continue
            if relative not in candidates:
                candidates.append(relative)
        for relative in project_files:
            if "/skills/super-dev/SKILL.md" not in relative:
                continue
            candidate = relative.replace(
                "/skills/super-dev/SKILL.md",
                "/skills/super-dev-seeai/SKILL.md",
            )
            if candidate == relative or candidate in project_files or candidate in candidates:
                continue
            candidates.append(candidate)
        return candidates

    @classmethod
    def managed_competition_user_surfaces(cls, target: str) -> list[str]:
        if target not in cls.TARGETS:
            return []

        from ..skills import SkillManager

        supplemental = [
            name
            for name in SkillManager.supplemental_builtin_skills(target)
            if isinstance(name, str) and name.strip()
        ]
        if not supplemental:
            return []

        base = SkillManager.TARGET_PATHS.get(target)
        if not isinstance(base, str) or not base.strip():
            return []
        normalized_base = base.replace("\\", "/").rstrip("/")
        managed: list[str] = []
        for extra_name in supplemental:
            derived = f"{normalized_base}/{extra_name}/SKILL.md"
            if derived not in managed:
                managed.append(derived)
        return managed

    @classmethod
    def managed_user_agent_surfaces(
        cls,
        target: str,
        *,
        include_optional: bool = True,
    ) -> list[str]:
        if target not in cls.TARGETS:
            return []

        declared = cls(Path.cwd())._install_surfaces(target=target)
        surfaces: list[str] = []
        candidate_keys = ["official_user_surfaces"]
        if include_optional:
            candidate_keys.append("optional_user_surfaces")
        for key in candidate_keys:
            for item in declared.get(key, []):
                if not isinstance(item, str):
                    continue
                normalized = item.replace("\\", "/").strip()
                if not normalized.endswith("/agents/super-dev.md"):
                    continue
                if normalized not in surfaces:
                    surfaces.append(normalized)
        return surfaces

    def setup_global_agent_surfaces(self, target: str, force: bool = False) -> list[Path]:
        written: list[Path] = []
        for surface in self.managed_user_agent_surfaces(target):
            surface_path = self._resolve_surface_declaration(target=target, surface=surface)
            if surface_path.exists() and not force:
                continue
            surface_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=surface),
                relative=surface_path.as_posix(),
            )
            surface_path.write_text(content, encoding="utf-8")
            written.append(surface_path)
        return written

    def setup_global_protocol(self, target: str, force: bool = False) -> Path | None:
        protocol_file = self.resolve_global_protocol_path(target)

        markers = self._managed_agents_markers(target)
        if protocol_file is not None and protocol_file.name == "AGENTS.md" and markers is not None:
            content = (
                self._build_codex_agents_content()
                if target in {"codex", "codex-cli"}
                else self._build_content(target)
            )
            block_content = self._append_flow_contract(
                content=content,
                relative=protocol_file.as_posix(),
            )
            updated = self._upsert_managed_block(
                file_path=protocol_file,
                begin=markers[0],
                end=markers[1],
                block_content=block_content,
            )
            return protocol_file if updated or protocol_file.exists() else None

        if target == "claude-code" and protocol_file is not None:
            block_content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=protocol_file.name),
                relative=protocol_file.as_posix(),
            )
            updated = self._upsert_managed_block(
                file_path=protocol_file,
                begin=self.CLAUDE_RULES_BEGIN,
                end=self.CLAUDE_RULES_END,
                block_content=block_content,
            )
            return protocol_file if updated or protocol_file.exists() else None

        if target in {"codebuddy", "codebuddy-cli", "codebuddy-cn"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"kiro", "kiro-cli"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_kiro_global_steering_content(),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"gemini-cli", "qwen-code"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target == "antigravity" and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_antigravity_context_content(),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target == "opencode" and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"trae", "trae-cn"} and protocol_file is not None:
            compatibility_file = self.resolve_compatibility_protocol_path(target)
            content = self._append_flow_contract(
                content=self._build_content(target),
                relative=protocol_file.as_posix(),
            )
            if protocol_file.exists() and not force:
                if compatibility_file is not None and not compatibility_file.exists():
                    compatibility_file.parent.mkdir(parents=True, exist_ok=True)
                    compatibility_file.write_text(
                        self._append_flow_contract(
                            content=content,
                            relative=compatibility_file.as_posix(),
                        ),
                        encoding="utf-8",
                    )
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(content, encoding="utf-8")
            if compatibility_file is not None:
                compatibility_file.parent.mkdir(parents=True, exist_ok=True)
                compatibility_file.write_text(
                    self._append_flow_contract(
                        content=content,
                        relative=compatibility_file.as_posix(),
                    ),
                    encoding="utf-8",
                )
            return protocol_file

        return None
