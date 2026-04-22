"""User-facing host experience tiers and strengths."""

from __future__ import annotations

from typing import Any


def _profile(
    *,
    tier: str,
    label: str,
    best_for: str,
    resume_style: str,
    market_focus: str,
    strengths: tuple[str, ...] = (),
    preferred_entries: tuple[str, ...] = (),
    native_resume: tuple[str, ...] = (),
    start_playbook: tuple[str, ...] = (),
    repair_playbook: str = "",
) -> dict[str, Any]:
    return {
        "tier": tier,
        "label": label,
        "best_for": best_for,
        "resume_style": resume_style,
        "market_focus": market_focus,
        "strengths": list(strengths),
        "preferred_entries": list(preferred_entries),
        "native_resume": list(native_resume),
        "start_playbook": list(start_playbook),
        "repair_playbook": repair_playbook,
    }


_EXPERIENCE_PROFILES: dict[str, dict[str, Any]] = {
    "antigravity": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Gemini 风格工作流、GEMINI.md + custom commands 协同与 Agent Chat 连续开发",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("GEMINI.md + custom commands", "Agent Chat 连续性", "推荐 workflow 增强"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Antigravity Agent Chat 里直接用 /super-dev，保持同一条工作流连续性。",
            "避免动作: 不要先切回普通聊天再补一大段背景。",
        ),
        repair_playbook="如果 GEMINI.md、custom commands 或推荐 workflow 没刷新，先重开当前 Antigravity Agent Chat，再回到 /super-dev。",
    ),
    "claude": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Claude Projects、方向确认、文档审阅与知识驱动协作",
        resume_style="task-thread",
        market_focus="global",
        strengths=("Projects", "Project Instructions/Knowledge", "desktop extensions/MCP"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("回当前 Claude Project 会话继续", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 先在当前 Claude Project 里挂好 instructions / knowledge，再直接用 super-dev:。",
            "避免动作: 不要把 Claude Desktop 当成有稳定仓库级 dotfile 注入的 CLI 宿主。",
        ),
        repair_playbook="如果当前 Project 没挂好 instructions、knowledge 或 extensions，先补齐 Claude Project 配置，再回到 super-dev:。",
    ),
    "claude-code": _profile(
        tier="flagship",
        label="Flagship",
        best_for="长流程商业项目开发与高密度连续协作",
        resume_style="session-first",
        market_focus="global",
        strengths=("长会话稳定性", "slash 触发直接", "文档到交付闭环"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Claude Code 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Claude Code 会话里直接用 /super-dev，不要先退回普通聊天交代背景。",
            "避免动作: 不要先手写一串 spec / quality / release 命令来替代宿主入口。",
        ),
        repair_playbook="如果 slash 或技能没刷新，先重开当前 Claude Code 会话，再回到 /super-dev。",
    ),
    "codex": _profile(
        tier="flagship",
        label="Flagship",
        best_for="Codex App/Desktop 项目会话、Skill 入口与深度流程治理",
        resume_style="skill-and-session",
        market_focus="global",
        strengths=("App/Desktop Skill 入口", "AGENTS + Skills 主面", "多阶段证据链"),
        preferred_entries=("/super-dev 你的需求", "super-dev: 你的需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Codex 会话继续"),
        start_playbook=(
            "起手建议: App/Desktop 优先从 / 列表里的 super-dev 进入，不要先退回普通聊天。",
            "避免动作: 不要把桌面端入口和 CLI 的 $super-dev 混成同一个宿主。",
        ),
        repair_playbook="如果 Skill 列表没刷新，先重开当前 Codex App/Desktop 会话，再回到 /super-dev。",
    ),
    "codex-cli": _profile(
        tier="flagship",
        label="Flagship",
        best_for="Codex CLI 显式 Skill 入口、长流程治理与仓库级 Skills 协作",
        resume_style="skill-and-session",
        market_focus="global",
        strengths=("CLI $skill 入口", "AGENTS + Skills 主面", "多阶段证据链"),
        preferred_entries=("$super-dev", "super-dev: 你的需求"),
        native_resume=("$super-dev", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 在 Codex CLI 里优先显式输入 $super-dev，不要先把 App/Desktop 的 / 列表入口和 CLI 混成一个宿主。",
            "避免动作: 不要一上来先跑一串 release / proof-pack / quality 命令。",
        ),
        repair_playbook="如果 CLI Skill 入口没刷新，先重开当前 Codex CLI 会话，再回到 $super-dev。",
    ),
    "droid-cli": _profile(
        tier="flagship",
        label="Flagship",
        best_for="Factory 模型工作流、skills-first slash 入口与标准流 / SEEAI 双模式冲刺",
        resume_style="factory-session",
        market_focus="global",
        strengths=("Factory rules + skills 主面", "标准流与比赛流双栈", "session/headless 双恢复"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("droid exec --session-id <id>", "/super-dev 继续当前流程"),
        start_playbook=(
            "起手建议: 优先留在当前 Factory session 里用 /super-dev，并确认 `.factory/skills/` 已接住 slash；只有无界面恢复时再走 droid exec --session-id <id>。",
            "避免动作: 不要先新开一个脱离当前 session 的普通对话。",
        ),
        repair_playbook="如果 rules / skills 没生效，先重开当前 Factory session，再回到 /super-dev；`.factory/commands/` 只作为 legacy slash compatibility 排查。",
    ),
    "cline": _profile(
        tier="standard",
        label="Standard",
        best_for="面板内项目协作、规则驱动文本入口与项目级 skills 闭环",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("面板内连续协作", ".clinerules + skills", "文本入口稳定"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Cline 面板继续"),
        start_playbook=(
            "起手建议: 优先在当前 Cline 面板里直接用 super-dev:，不要先退回普通聊天。",
            "避免动作: 不要新开一个平行面板再重新解释同一个项目。",
        ),
        repair_playbook="如果 .clinerules 或 .cline/skills 没加载，先重开当前 Cline 面板，再回到 super-dev:。",
    ),
    "codebuddy": _profile(
        tier="flagship",
        label="Flagship",
        best_for="IDE 内全链路开发与比赛模式一体化冲刺",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("IDE 内连续开发", "SEEAI 快速冲刺", "agents/commands/skills 一体化"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前会话继续"),
        start_playbook=(
            "起手建议: 直接在当前 IDE Agent Chat 里进入 /super-dev，保持同一条会话连续性。",
            "避免动作: 不要切回新的普通聊天线程再重新交代同一项目。",
        ),
        repair_playbook="如果 agents / commands / skills 没刷新，先重开当前 IDE 会话，再回到 /super-dev。",
    ),
    "codebuddy-cn": _profile(
        tier="flagship",
        label="Flagship",
        best_for="中文 IDE 内全链路开发与比赛模式一体化冲刺",
        resume_style="agent-chat-continuity",
        market_focus="cn",
        strengths=("中文 IDE 协作", "SEEAI 快速冲刺", "rules/commands/agents/skills 一体化"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前会话继续"),
        start_playbook=(
            "起手建议: 直接在当前 CodeBuddyCN IDE Agent Chat 里进入 /super-dev，保持同一条会话连续性。",
            "避免动作: 不要切回新的普通聊天线程再重新交代同一项目。",
        ),
        repair_playbook="如果 rules / commands / agents / skills 没刷新，先重开当前 IDE 会话，再回到 /super-dev。",
    ),
    "codebuddy-cli": _profile(
        tier="flagship",
        label="Flagship",
        best_for="CLI 项目流与 SEEAI 快速冲刺",
        resume_style="session-first",
        market_focus="global",
        strengths=("CLI 节奏快", "比赛模式直达", "命令面强"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 CodeBuddy CLI 会话继续"),
        start_playbook=(
            "起手建议: 直接从当前 CLI 会话进入 /super-dev，保持同一条项目流。",
            "避免动作: 不要先新开普通聊天线程再回来补治理状态。",
        ),
        repair_playbook="如果 CLI 入口没刷新，先重开当前 CodeBuddy CLI 会话，再回到 /super-dev。",
    ),
    "copilot-cli": _profile(
        tier="standard",
        label="Standard",
        best_for="CLI 项目上下文、AGENTS.md、copilot-instructions、skills 与 custom agents 协同的文本流",
        resume_style="session-first",
        market_focus="global",
        strengths=("项目上下文清晰", "instructions + agents + skills", "文本入口稳定"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Copilot CLI 会话继续"),
        start_playbook=(
            "起手建议: 优先留在当前 Copilot CLI 项目会话里直接用 super-dev:，并让当前会话先读取 AGENTS.md 与 copilot-instructions。",
            "避免动作: 不要先切去别的 shell 会话再试图手工恢复流程。",
        ),
        repair_playbook="如果 AGENTS.md、copilot-instructions、skills 或 custom agent 没生效，先重开当前 Copilot CLI 会话，再回到 super-dev:。",
    ),
    "cursor-cli": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Cursor CLI 项目上下文、AGENTS.md + rules 协同的轻量文本流",
        resume_style="session-first",
        market_focus="global",
        strengths=("项目 rules 协同", "CLI 节奏快", "文本入口直接"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Cursor CLI 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Cursor CLI 项目会话里直接用 super-dev:。",
            "避免动作: 不要先跳去普通聊天或手工堆一串治理命令。",
        ),
        repair_playbook="如果 AGENTS.md 或 .cursor/rules 没加载，先重开当前 Cursor CLI 会话，再回到 super-dev:；根 CLAUDE.md 只作为兼容说明核对。",
    ),
    "cursor": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Cursor IDE Agent Chat、beta commands 与项目 rules 协同",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("IDE Agent Chat", "beta commands", "项目 rules 协同"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Cursor Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Cursor Agent Chat 里直接用 /super-dev，保持当前项目上下文。",
            "避免动作: 不要先新开一个普通聊天窗口再重述需求。",
        ),
        repair_playbook="如果 beta commands 或 .cursor/rules 没刷新，先重开当前 Cursor Agent Chat，再回到 /super-dev。",
    ),
    "gemini-cli": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Gemini CLI 项目流、GEMINI.md + settings + custom commands 协同",
        resume_style="session-first",
        market_focus="global",
        strengths=("GEMINI.md 协议面", "settings + custom commands", "slash/text 双入口"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Gemini CLI 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Gemini CLI 项目会话里使用注入出来的 /super-dev，并确认 GEMINI.md、settings 与 custom commands 已加载。",
            "避免动作: 不要把 /super-dev 误当成宿主原生命令，也不要先把需求丢回普通聊天，再手工追流程状态。",
        ),
        repair_playbook="如果 GEMINI.md、settings 或 custom commands 没生效，先重开当前 Gemini CLI 会话，再回到 /super-dev；兼容 skills 仅作为增强层核对。",
    ),
    "kiro-cli": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Kiro CLI steering + slash + skills 的项目流",
        resume_style="session-first",
        market_focus="global",
        strengths=("steering 驱动", "slash 入口", "skills 协同"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Kiro CLI 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Kiro CLI 会话里直接用 /super-dev，先让 steering 接住流程。",
            "避免动作: 不要先在普通聊天里绕一圈再切回 slash。",
        ),
        repair_playbook="如果 steering 或 skills 没加载，先重开当前 Kiro CLI 会话，再回到 /super-dev。",
    ),
    "kiro": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Kiro IDE Agent Chat、steering 与 slash 入口协同",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("Agent Chat 连续性", "steering 驱动", "slash 入口"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Kiro Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Kiro Agent Chat 里直接用 /super-dev。",
            "避免动作: 不要为了继续流程新开工作区或新聊天线程。",
        ),
        repair_playbook="如果 steering、slash 或 skills 没生效，先重开当前 Kiro Agent Chat，再回到 /super-dev。",
    ),
    "kilo-code": _profile(
        tier="standard",
        label="Standard",
        best_for="规则驱动的文本入口与轻量项目接入",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("规则驱动", "文本入口轻量", "项目级接入简单"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Kilo Code 面板继续"),
        start_playbook=(
            "起手建议: 优先在当前 Kilo Code 面板里直接用 super-dev:。",
            "避免动作: 不要先切去普通聊天再回来补上下文。",
        ),
        repair_playbook="如果 .kilocode/rules 或 commands 没生效，先重开当前 Kilo Code 面板，再回到 super-dev:。",
    ),
    "kimi-code": _profile(
        tier="flagship",
        label="Flagship",
        best_for="中文项目协作、AGENTS + explicit Skill / Flow 入口与 native session resume",
        resume_style="native-resume",
        market_focus="cn",
        strengths=("中文协作体验", "AGENTS + explicit Skill / Flow 入口", "原生 continue / session resume"),
        preferred_entries=("/skill:super-dev 你的需求", "super-dev: 你的需求"),
        native_resume=("kimi --continue", "kimi --session <id>"),
        start_playbook=(
            "起手建议: 中文项目优先用 /skill:super-dev，并确保当前会话已经读取项目根 AGENTS.md；需要更强结构化流程时再考虑 /flow:super-dev。",
            "避免动作: 不要先用普通聊天描述一大段背景再切回 Skill，也不要把 `.kimi/skills/` 误当成唯一官方硬前提。",
        ),
        repair_playbook="如果 Skill 入口没刷新，先重开 Kimi Code，再回到 /skill:super-dev；恢复优先 kimi --continue、kimi --session <id> 或运行中的 /sessions / /resume，`.kimi/skills/` 只按增强层排查。",
    ),
    "opencode": _profile(
        tier="specialized",
        label="Specialized",
        best_for="OpenCode 会话内 slash 流程与 AGENTS/commands/skills 协同",
        resume_style="session-first",
        market_focus="global",
        strengths=("slash 入口", "AGENTS + commands + skills", "会话内恢复直接"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 OpenCode 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 OpenCode 会话里直接用 /super-dev，并让 AGENTS、commands、skills 先接住流程；`.opencode/agents/` 作为增强层再核对。",
            "避免动作: 不要新开普通聊天会话再重讲同一项目。",
        ),
        repair_playbook="如果 AGENTS、commands 或 skills 没刷新，先重开当前 OpenCode 会话，再回到 /super-dev；`.opencode/agents/` 作为增强层排查。",
    ),
    "qoder-cli": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Qoder CLI slash 项目流与 AGENTS/rules/commands/skills 协同",
        resume_style="session-first",
        market_focus="global",
        strengths=("slash 入口", "AGENTS + rules/commands/skills 协同", "比赛模式直达"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Qoder CLI 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Qoder CLI 会话里直接用 /super-dev，并让 AGENTS、rules、commands、skills 先接住流程；`.qoder/agents/` 作为增强层再核对。",
            "避免动作: 不要先切去普通 shell 再手工追流程状态。",
        ),
        repair_playbook="如果 AGENTS、rules、commands 或 skills 没加载，先重开当前 Qoder CLI 会话，再回到 /super-dev；`.qoder/agents/` 作为增强层排查。",
    ),
    "qwen-code": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Qwen Code 项目上下文、commands/skills/agents 协同与 /resume 续跑",
        resume_style="native-resume",
        market_focus="global",
        strengths=("QWEN.md 协议面", "commands + skills + agents", "/resume 续跑"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/resume",),
        start_playbook=(
            "起手建议: 优先在当前 Qwen Code 会话里直接用 /super-dev，让 QWEN.md 和 commands 接住流程。",
            "避免动作: 不要先退回普通聊天再手工补流程状态。",
        ),
        repair_playbook="如果 QWEN.md、commands、skills 或 agents 没生效，先重开当前 Qwen Code 会话，再回到 /super-dev 或 /resume；/restore 只用于 checkpoint 回滚。",
    ),
    "qoder": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Qoder IDE Agent Chat、slash 入口与 AGENTS/rules/commands/skills 协同",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("IDE Agent Chat", "slash 入口", "AGENTS + rules/commands/skills 协同"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Qoder Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Qoder Agent Chat 里直接用 /super-dev，保持同一条工作流，并让 AGENTS、rules、commands、skills 先接住流程。",
            "避免动作: 不要先新开普通聊天线程再重述需求。",
        ),
        repair_playbook="如果 AGENTS、rules、commands 或 skills 没刷新，先重开当前 Qoder Agent Chat，再回到 /super-dev；`.qoder/agents/` 作为增强层排查。",
    ),
    "roo-code": _profile(
        tier="standard",
        label="Standard",
        best_for="项目 rules/commands 驱动的轻量文本流",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("rules/commands 简洁", "文本入口稳定", "项目级接入直接"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Roo Code 面板继续"),
        start_playbook=(
            "起手建议: 优先在当前 Roo Code 面板里直接用 super-dev:。",
            "避免动作: 不要先开一个新的平行线程再补流程状态。",
        ),
        repair_playbook="如果 .roo/rules 或 .roo/commands 没加载，先重开当前 Roo Code 面板，再回到 super-dev:。",
    ),
    "vscode-copilot": _profile(
        tier="standard",
        label="Standard",
        best_for="Copilot Chat + @workspace 项目上下文协作",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("@workspace 上下文", "copilot-instructions", "文本入口稳定"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Copilot Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Copilot Chat 里直接用 super-dev:，并保留 @workspace 项目上下文。",
            "避免动作: 不要在新聊天里重新交代同一项目背景。",
        ),
        repair_playbook="如果 copilot-instructions 或项目上下文没生效，先重开当前 Copilot Chat，再回到 super-dev:。",
    ),
    "trae": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Trae IDE 文本入口、project rules 与兼容 skill 协同",
        resume_style="workspace-continuity",
        market_focus="global",
        strengths=("project rules", "文本入口稳定", "工作区连续性"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("super-dev: 继续当前流程", "回当前 Trae Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Trae Agent Chat 里直接用 super-dev:，保持同一工作区连续性。",
            "避免动作: 不要先切去新的普通聊天线程再重讲项目。",
        ),
        repair_playbook="如果 project rules 或兼容 skill 没刷新，先重开当前 Trae Agent Chat，再回到 super-dev:。",
    ),
    "trae-cn": _profile(
        tier="flagship",
        label="Flagship",
        best_for="中文 IDE 工作区协作、计划流和项目级连续开发",
        resume_style="workspace-continuity",
        market_focus="cn",
        strengths=("中文工作区协作", "计划流连续性", "项目级 rules/skills"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("回当前 TraeCN 工作区会话继续", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 中文工作区优先直接用 super-dev:，保持同一工作区/线程连续性。",
            "避免动作: 不要切到新的普通对话线程再重新交代上下文。",
        ),
        repair_playbook="如果规则或技能未生效，先重开当前 TraeCN 工作区线程，再用 super-dev: 继续当前流程。",
    ),
    "trae-solo": _profile(
        tier="flagship",
        label="Flagship",
        best_for="工作区级 slash 流程、Rules/Commands/Skills 一体接入",
        resume_style="workspace-continuity",
        market_focus="global",
        strengths=("workspace 级 slash", "rules/commands/skills 一体", "工作区恢复自然"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前工作区会话继续"),
        start_playbook=(
            "起手建议: 优先在当前工作区直接用 /super-dev，保持同一工作区连续性。",
            "避免动作: 不要为了继续流程先新开工作区或新聊天面板。",
        ),
        repair_playbook="如果 workspace 规则或技能没刷新，先重开当前工作区会话，再回到 /super-dev。",
    ),
    "trae-solocn": _profile(
        tier="flagship",
        label="Flagship",
        best_for="中文工作区协作、MTC/Code 双模式与 Super Dev 治理协同",
        resume_style="workspace-continuity",
        market_focus="cn",
        strengths=("中文工作区协作", "MTC/Code 双模式", "plan/spec 与治理协同"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("回当前工作区会话继续", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 中文工作区优先用 super-dev:，让 MTC / Code 在当前线程里继续协作。",
            "避免动作: 不要切到新的普通对话线程再重新交代上下文。",
        ),
        repair_playbook="如果规则或技能未生效，先重开当前工作区线程，再用 super-dev: 继续当前流程。",
    ),
    "windsurf": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Windsurf Agent Chat、AGENTS + workflow + skills 协同与 slash 入口",
        resume_style="agent-chat-continuity",
        market_focus="global",
        strengths=("AGENTS + workflow 驱动", "slash 入口", "skills 协同"),
        preferred_entries=("/super-dev 你的需求", "/super-dev-seeai 比赛需求"),
        native_resume=("/super-dev 继续当前流程", "回当前 Windsurf Agent Chat 会话继续"),
        start_playbook=(
            "起手建议: 优先在当前 Windsurf Agent Chat 里直接用 /super-dev，沿用当前会话连续性，并确认 AGENTS.md 已被当前工作区读取。",
            "避免动作: 不要先新开普通聊天线程再回到 slash 入口。",
        ),
        repair_playbook="如果 AGENTS、workflows 或 skills 没生效，先重开当前 Windsurf Agent Chat，再回到 /super-dev。",
    ),
    "workbuddy": _profile(
        tier="specialized",
        label="Specialized",
        best_for="Skill + MCP 手动接入和任务型工作台协作",
        resume_style="task-thread",
        market_focus="cn",
        strengths=("任务型工作台", "Skills + MCP", "人工验收闭环清晰"),
        preferred_entries=("super-dev: 你的需求", "super-dev-seeai: 比赛需求"),
        native_resume=("回当前任务线程继续", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 优先在当前任务线程里触发 super-dev:，保持任务上下文完整。",
            "避免动作: 不要在新线程里重新开一个平行任务流。",
        ),
        repair_playbook="如果 Skills 或 MCP 没接好，先修当前任务工作台，再回到 super-dev:；文件侧 Skill 导入面只作为补充模型排查。",
    ),
}


def build_host_experience_profile(host_id: str) -> dict[str, Any]:
    profile = dict(_EXPERIENCE_PROFILES.get(host_id, {}))
    if profile:
        return profile
    return _profile(
        tier="standard",
        label="Standard",
        best_for="标准项目接入、宿主内持续开发与交付闭环",
        resume_style="host-session",
        market_focus="global",
        strengths=("项目接入", "宿主内持续开发", "交付闭环"),
        preferred_entries=("/super-dev 你的需求", "super-dev: 你的需求"),
        native_resume=("/super-dev 继续当前流程", "super-dev: 继续当前流程"),
        start_playbook=(
            "起手建议: 优先留在当前宿主会话里进入 Super Dev，不要先切回普通聊天。",
        ),
        repair_playbook="如果入口或规则没刷新，先重开当前宿主会话，再回到 Super Dev 入口。",
    )


def build_host_resume_guidance(host_id: str) -> list[str]:
    profile = build_host_experience_profile(host_id)
    preferred_entries = [
        str(item).strip()
        for item in profile.get("preferred_entries", [])
        if str(item).strip()
    ][:2]
    native_resume = [
        str(item).strip()
        for item in profile.get("native_resume", [])
        if str(item).strip()
    ][:2]
    resume_style = str(profile.get("resume_style", "")).strip()

    lines: list[str] = []
    if preferred_entries:
        lines.append(f"优先入口: {' / '.join(preferred_entries)}")
    if native_resume:
        lines.append(f"原生恢复: {' / '.join(native_resume)}")

    style_lines = {
        "native-resume": "优先沿用宿主原生 continue / resume，不要重新开题。",
        "factory-session": "优先保留当前 Factory session；需要无界面恢复时，再走宿主原生命令恢复。",
        "workspace-continuity": "优先沿用当前 workspace continuity，不要重新新建工作区或新分支。",
        "skill-and-session": "优先沿用当前 Skill / session 入口，不要先退回普通聊天。",
        "session-first": "优先沿用当前宿主会话恢复，不要先走新的普通聊天入口。",
        "agent-chat-continuity": "优先沿用当前 Agent Chat 连续性，不要切到新的聊天线程。",
        "task-thread": "优先沿用当前任务线程，不要重新开一个新的任务流。",
        "host-session": "优先沿用当前宿主会话继续当前流程。",
    }
    style_line = style_lines.get(resume_style, "")
    if style_line:
        lines.append(style_line)
    return lines


def build_host_start_playbook(host_id: str) -> list[str]:
    profile = build_host_experience_profile(host_id)
    playbook = [
        str(item).strip()
        for item in profile.get("start_playbook", [])
        if str(item).strip()
    ]
    return playbook[:3]


def build_host_repair_guidance(host_id: str) -> str:
    profile = build_host_experience_profile(host_id)
    guidance = str(profile.get("repair_playbook", "")).strip()
    if not guidance:
        return ""
    return f" {guidance}"


def build_host_standard_first_prompt(host_id: str) -> str:
    prompt_map = {
        "claude": "super-dev: 你的需求",
        "claude-code": "/super-dev 你的需求",
        "codex": "/super-dev 你的需求",
        "codex-cli": "$super-dev",
        "droid-cli": "/super-dev 你的需求",
        "codebuddy": "/super-dev 你的需求",
        "codebuddy-cn": "/super-dev 你的需求",
        "codebuddy-cli": "/super-dev 你的需求",
        "kimi-code": "/skill:super-dev 你的需求",
        "qwen-code": "/super-dev 你的需求",
        "trae-cn": "super-dev: 你的需求",
        "trae-solo": "/super-dev 你的需求",
        "trae-solocn": "super-dev: 你的需求",
        "workbuddy": "super-dev: 你的需求",
    }
    if host_id in prompt_map:
        return prompt_map[host_id]
    profile = build_host_experience_profile(host_id)
    preferred_entries = [
        str(item).strip()
        for item in profile.get("preferred_entries", [])
        if str(item).strip()
    ]
    return preferred_entries[0] if preferred_entries else "/super-dev 你的需求"


def build_host_competition_first_prompt(host_id: str) -> str:
    prompt_map = {
        "claude": "super-dev-seeai: 比赛需求",
        "claude-code": "/super-dev-seeai 比赛需求",
        "codex": "/super-dev-seeai 比赛需求",
        "codex-cli": "$super-dev-seeai",
        "droid-cli": "/super-dev-seeai 比赛需求",
        "codebuddy": "/super-dev-seeai 比赛需求",
        "codebuddy-cn": "/super-dev-seeai 比赛需求",
        "codebuddy-cli": "/super-dev-seeai 比赛需求",
        "kimi-code": "super-dev-seeai: 比赛需求",
        "qwen-code": "/super-dev-seeai 比赛需求",
        "trae-cn": "super-dev-seeai: 比赛需求",
        "trae-solo": "/super-dev-seeai 比赛需求",
        "trae-solocn": "super-dev-seeai: 比赛需求",
        "workbuddy": "super-dev-seeai: 比赛需求",
    }
    if host_id in prompt_map:
        return prompt_map[host_id]
    profile = build_host_experience_profile(host_id)
    preferred_entries = [
        str(item).strip()
        for item in profile.get("preferred_entries", [])
        if str(item).strip()
    ]
    for item in preferred_entries:
        if "seeai" in item.lower():
            return item
    if preferred_entries:
        primary = preferred_entries[0]
        if primary.startswith("/"):
            return "/super-dev-seeai 比赛需求"
        if primary.startswith("$super-dev"):
            return "$super-dev-seeai"
        if primary.startswith("super-dev:") or primary.startswith("super-dev："):
            return "super-dev-seeai: 比赛需求"
    return "super-dev-seeai: 比赛需求"


def build_host_official_workflow_checks(host_id: str, usage: dict[str, Any]) -> list[str]:
    host = str(usage.get("host", "")).strip() or host_id
    protocol_mode = str(usage.get("host_protocol_mode", "")).strip()
    project_surfaces = [
        str(item).strip()
        for item in usage.get("official_project_surfaces", [])
        if str(item).strip()
    ][:3]
    user_surfaces = [
        str(item).strip()
        for item in usage.get("official_user_surfaces", [])
        if str(item).strip()
    ][:3]
    competition_project_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_project_surfaces", [])
        if str(item).strip()
    ][:2]
    competition_user_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_user_surfaces", [])
        if str(item).strip()
    ][:2]
    optional_project_surfaces = [
        str(item).strip()
        for item in usage.get("optional_project_surfaces", [])
        if str(item).strip()
    ][:2]
    optional_user_surfaces = [
        str(item).strip()
        for item in usage.get("optional_user_surfaces", [])
        if str(item).strip()
    ][:2]

    lines: list[str] = []
    if protocol_mode:
        protocol_scope = "官方协议面" if protocol_mode.startswith("official") else "当前推荐接入模型"
        lines.append(
            f"确认 {host} 按 {protocol_mode} {protocol_scope}真实加载 Super Dev，而不是只检测到文件存在。"
        )
    if project_surfaces or user_surfaces:
        joined = []
        if project_surfaces:
            joined.append(f"项目侧 {' / '.join(project_surfaces)}")
        if user_surfaces:
            joined.append(f"用户侧 {' / '.join(user_surfaces)}")
        lines.append(f"确认官方接入面真实生效: {'；'.join(joined)}")
    if optional_project_surfaces or optional_user_surfaces:
        joined = []
        if optional_project_surfaces:
            joined.append(f"项目侧 {' / '.join(optional_project_surfaces)}")
        if optional_user_surfaces:
            joined.append(f"用户侧 {' / '.join(optional_user_surfaces)}")
        lines.append(f"如启用当前增强接入面，再确认: {'；'.join(joined)}")
    if competition_project_surfaces:
        lines.append(
            f"确认 SEEAI 项目补充面真实生效: {' / '.join(competition_project_surfaces)}"
        )
    if competition_user_surfaces:
        lines.append(
            f"确认 SEEAI 用户级补充面真实生效: {' / '.join(competition_user_surfaces)}"
        )

    host_specific = {
        "antigravity": "确认当前 Antigravity Agent Chat 真实加载 GEMINI.md、.gemini/commands 与当前推荐 `.agent/workflows/`；skills 只按兼容增强层核对。",
        "claude": "确认当前 Claude Project 真实挂上 Project Instructions、Project Knowledge 与需要的 extensions / MCP。",
        "claude-code": "确认当前 Claude Code 会话真实读取 CLAUDE.md、.claude/CLAUDE.md、可选 .claude/settings*.json、.claude/skills 与 .claude/agents，而不是只把文件写进仓库。",
        "cline": "确认当前 Cline 面板真实读取 .clinerules 与 .cline/skills，而不是只检测到项目文件存在。",
        "codebuddy": "确认当前 CodeBuddy 会话真实加载 CODEBUDDY.md、rules、commands、agents、skills，并能直接走 /super-dev。",
        "codebuddy-cn": "确认当前 CodeBuddyCN IDE 会话真实加载 CODEBUDDY.md、rules、commands、agents、skills，并能直接走 /super-dev。",
        "codebuddy-cli": "确认当前 CodeBuddy CLI 会话真实加载 CODEBUDDY.md、commands 与 skills，并能直接走 /super-dev。",
        "codex": "确认 Codex App/Desktop 的 / 列表 super-dev 真实可用，并已读取仓库 AGENTS 与 Skills。",
        "codex-cli": "确认当前 Codex CLI 会话里的 $super-dev 真实可用，并已读取仓库 AGENTS 与 Skills。",
        "copilot-cli": "确认当前 Copilot CLI 会话真实读取 AGENTS.md、.github/copilot-instructions.md、.github/skills 与 .github/agents，而不是只写入了文件。",
        "cursor-cli": "确认当前 Cursor CLI 会话真实读取 AGENTS.md 与 .cursor/rules，并能按 super-dev: 延续流程；根 CLAUDE.md 只作为兼容说明。",
        "cursor": "确认当前 Cursor Agent Chat 真实加载 AGENTS.md 与 .cursor/rules；若使用 `.cursor/commands`，把它视为 beta 增强面而不是唯一官方合同。",
        "droid-cli": "确认当前 Factory session 真实加载 AGENTS.md、.factory/rules、.factory/skills，并仅把 .factory/commands 视为 legacy slash compatibility。",
        "gemini-cli": "确认当前 Gemini CLI 会话真实加载 GEMINI.md、可选 .gemini/settings.json 与 .gemini/commands，并把 /super-dev 视为注入出来的 custom command；skills 仅作增强层核对。",
        "kiro-cli": "确认当前 Kiro CLI 会话真实加载 AGENTS.md、.kiro/steering 与 skills；slash 入口是否出现以宿主命令面实际暴露为准。",
        "kiro": "确认当前 Kiro Agent Chat 真实加载 AGENTS.md、.kiro/steering 与 skills；slash 入口是否出现以宿主命令面实际暴露为准。",
        "kilo-code": "确认当前 Kilo Code 面板真实加载 .kilocode/rules 与 commands，并能按 super-dev: 连续工作。",
        "kimi-code": "确认当前 Kimi Code 会话真实读取项目根 AGENTS.md，并且 /skill:super-dev、/flow:super-dev、kimi --continue、kimi --session <id> / /sessions / /resume 这条显式入口与恢复链至少一条真实可用；`.kimi/skills/` 只按增强层核对。",
        "opencode": "确认当前 OpenCode 会话真实加载 AGENTS.md、.opencode/commands、.opencode/skills，并能直接走 /super-dev；`.opencode/agents/` 只按增强层核对。",
        "qoder-cli": "确认当前 Qoder CLI 会话真实加载 AGENTS.md、`.qoder/rules`、`.qoder/commands`、`.qoder/skills`，而不是只检测到文件存在；`.qoder/agents/` 只按增强层核对。",
        "qoder": "确认当前 Qoder Agent Chat 真实加载 AGENTS.md、`.qoder/rules`、`.qoder/commands`、`.qoder/skills`，而不是只检测到文件存在；`.qoder/agents/` 只按增强层核对。",
        "qwen-code": "确认当前 Qwen Code 会话真实加载 QWEN.md、.qwen/commands、.qwen/skills、.qwen/agents，并能用 /resume 续跑；/restore 只用于 checkpoint 回滚。",
        "roo-code": "确认当前 Roo Code 面板真实加载 .roo/rules 与 .roo/commands，并能按 super-dev: 连续流程。",
        "vscode-copilot": "确认当前 Copilot Chat 真实读取 .github/copilot-instructions.md 与 @workspace 项目上下文。",
        "trae": "确认当前 Trae Agent Chat 真实加载 .trae/project_rules.md / .trae/rules.md，并能按 super-dev: 延续同一工作区流程。",
        "trae-cn": "确认当前 TraeCN 工作区线程真实加载项目 rules / skills，并能按 super-dev: 延续同一中文工作区流程。",
        "trae-solo": "确认当前 Trae SOLO 工作区已按当前推荐 rules / commands / skills 模型生效，并能直接用 /super-dev 保持工作区连续性。",
        "trae-solocn": "确认当前 Trae SOLOCN 中文工作区已按当前推荐 `.trae/rules + .trae/skills + ~/.trae-cn/skills` 模型生效，并与内建 /plan /spec、MTC / Code 协同。",
        "windsurf": "确认当前 Windsurf Agent Chat 真实加载 AGENTS.md、.windsurf/rules、.windsurf/workflows、.windsurf/skills，并能直接走 /super-dev。",
        "workbuddy": "确认当前 WorkBuddy 任务工作台已启用 Skills、MCP 与项目目录授权；若使用文件侧 Skill 导入面，应把它视为当前接入模型的补充面而不是唯一官方合同。",
    }
    line = host_specific.get(host_id, "")
    if line:
        lines.append(line)
    return lines


def build_host_official_pass_criteria(host_id: str, usage: dict[str, Any]) -> list[str]:
    host = str(usage.get("host", "")).strip() or host_id
    protocol_mode = str(usage.get("host_protocol_mode", "")).strip()
    checks = build_host_official_workflow_checks(host_id, usage)
    competition_project_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_project_surfaces", [])
        if str(item).strip()
    ]
    competition_user_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_user_surfaces", [])
        if str(item).strip()
    ]
    if checks:
        contract_label = (
            "官方工作流面" if protocol_mode.startswith("official") else "当前推荐接入模型"
        )
        first_line = (
            f"{host} {contract_label}、入口链和恢复链均已真人验收通过。"
            if not competition_project_surfaces and not competition_user_surfaces
            else f"{host} {contract_label}、入口链、恢复链与 SEEAI 补充面均已真人验收通过。"
        )
        return [first_line, *checks[:3]]
    fallback_label = "官方工作流面" if protocol_mode.startswith("official") else "当前推荐接入模型"
    return [f"{host} {fallback_label}已真人验收通过。"]


def build_host_post_onboard_self_check(host_id: str, usage: dict[str, Any]) -> list[str]:
    host = str(usage.get("host", "")).strip() or host_id
    preferred_entries = [
        str(item).strip()
        for item in build_host_experience_profile(host_id).get("preferred_entries", [])
        if str(item).strip()
    ][:2]
    native_resume = [
        str(item).strip()
        for item in build_host_experience_profile(host_id).get("native_resume", [])
        if str(item).strip()
    ][:2]
    competition_project_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_project_surfaces", [])
        if str(item).strip()
    ][:2]
    competition_user_surfaces = [
        str(item).strip()
        for item in usage.get("managed_competition_user_surfaces", [])
        if str(item).strip()
    ][:2]
    official_checks = build_host_official_workflow_checks(host_id, usage)

    lines: list[str] = []
    if preferred_entries:
        lines.append(f"{host} 接入后先确认入口可用: {' / '.join(preferred_entries)}")
    if competition_project_surfaces:
        lines.append(
            f"{host} 接入后再确认 SEEAI 项目补充面已写入: {' / '.join(competition_project_surfaces)}"
        )
    if competition_user_surfaces:
        lines.append(
            f"{host} 接入后再确认 SEEAI 用户级补充面已写入: {' / '.join(competition_user_surfaces)}"
        )
    if official_checks:
        lines.append(official_checks[0])
    if native_resume:
        lines.append(f"{host} 接入后再确认恢复链可用: {' / '.join(native_resume)}")
    return lines[:3]
