"""
统一维护 Super Dev 的枚举目录（平台、前后端模板、领域、语言偏好等）。

该模块用于消除 CLI / Config / Web API 之间的重复定义，保证单一真源。
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any, cast

from .host_adapters import get_pass_criteria, get_resume_checklist, get_runtime_checklist

PLATFORM_CATALOG: list[dict[str, str]] = [
    {"id": "web", "name": "Web 应用"},
    {"id": "mobile", "name": "H5 / APP"},
    {"id": "wechat", "name": "微信小程序（MiniApp）"},
    {"id": "desktop", "name": "桌面应用"},
]

PIPELINE_FRONTEND_TEMPLATE_CATALOG: list[dict[str, str]] = [
    {"id": "react", "name": "React"},
    {"id": "vue", "name": "Vue"},
    {"id": "angular", "name": "Angular"},
    {"id": "svelte", "name": "Svelte"},
    {"id": "none", "name": "无"},
]

FULL_FRONTEND_TEMPLATE_CATALOG: list[dict[str, str]] = [
    {"id": "next", "name": "Next.js"},
    {"id": "remix", "name": "Remix"},
    {"id": "react-vite", "name": "React + Vite"},
    {"id": "gatsby", "name": "Gatsby"},
    {"id": "nuxt", "name": "Nuxt"},
    {"id": "vue-vite", "name": "Vue + Vite"},
    {"id": "angular", "name": "Angular"},
    {"id": "sveltekit", "name": "SvelteKit"},
    {"id": "astro", "name": "Astro"},
    {"id": "solid", "name": "Solid"},
    {"id": "qwik", "name": "Qwik"},
    {"id": "expo", "name": "Expo"},
    {"id": "react-native", "name": "React Native"},
    {"id": "flutter", "name": "Flutter"},
    {"id": "uni-app", "name": "uni-app"},
    {"id": "taro", "name": "Taro"},
    {"id": "tauri", "name": "Tauri"},
    {"id": "electron", "name": "Electron"},
    {"id": "wails", "name": "Wails"},
    {"id": "ionic", "name": "Ionic"},
    {"id": "capacitor", "name": "Capacitor"},
    {"id": "react", "name": "React"},
    {"id": "vue", "name": "Vue"},
    {"id": "svelte", "name": "Svelte"},
    {"id": "none", "name": "无"},
]

BACKEND_TEMPLATE_CATALOG: list[dict[str, str]] = [
    {"id": "node", "name": "Node.js"},
    {"id": "python", "name": "Python"},
    {"id": "go", "name": "Go"},
    {"id": "java", "name": "Java"},
    {"id": "rust", "name": "Rust"},
    {"id": "php", "name": "PHP"},
    {"id": "ruby", "name": "Ruby"},
    {"id": "csharp", "name": "C# (.NET)"},
    {"id": "kotlin", "name": "Kotlin"},
    {"id": "swift", "name": "Swift"},
    {"id": "elixir", "name": "Elixir"},
    {"id": "scala", "name": "Scala"},
    {"id": "dart", "name": "Dart"},
    {"id": "none", "name": "无"},
]

DOMAIN_CATALOG: list[dict[str, str]] = [
    {"id": "", "name": "通用"},
    {"id": "fintech", "name": "金融科技"},
    {"id": "ecommerce", "name": "电子商务"},
    {"id": "medical", "name": "医疗健康"},
    {"id": "social", "name": "社交媒体"},
    {"id": "iot", "name": "物联网"},
    {"id": "education", "name": "在线教育"},
    {"id": "auth", "name": "认证安全"},
    {"id": "content", "name": "内容平台"},
    {"id": "saas", "name": "SaaS"},
]

CICD_PLATFORM_CATALOG: list[dict[str, str]] = [
    {"id": "all", "name": "全部平台"},
    {"id": "github", "name": "GitHub Actions"},
    {"id": "gitlab", "name": "GitLab CI"},
    {"id": "jenkins", "name": "Jenkins"},
    {"id": "azure", "name": "Azure DevOps"},
    {"id": "bitbucket", "name": "Bitbucket Pipelines"},
]

LANGUAGE_PREFERENCE_CATALOG: list[dict[str, str]] = [
    {"id": "python", "name": "Python"},
    {"id": "typescript", "name": "TypeScript"},
    {"id": "javascript", "name": "JavaScript"},
    {"id": "go", "name": "Go"},
    {"id": "java", "name": "Java"},
    {"id": "csharp", "name": "C#"},
    {"id": "cpp", "name": "C++"},
    {"id": "c", "name": "C"},
    {"id": "rust", "name": "Rust"},
    {"id": "kotlin", "name": "Kotlin"},
    {"id": "swift", "name": "Swift"},
    {"id": "objective-c", "name": "Objective-C"},
    {"id": "php", "name": "PHP"},
    {"id": "ruby", "name": "Ruby"},
    {"id": "scala", "name": "Scala"},
    {"id": "dart", "name": "Dart"},
    {"id": "elixir", "name": "Elixir"},
    {"id": "erlang", "name": "Erlang"},
    {"id": "clojure", "name": "Clojure"},
    {"id": "haskell", "name": "Haskell"},
    {"id": "ocaml", "name": "OCaml"},
    {"id": "fsharp", "name": "F#"},
    {"id": "lua", "name": "Lua"},
    {"id": "perl", "name": "Perl"},
    {"id": "groovy", "name": "Groovy"},
    {"id": "r", "name": "R"},
    {"id": "julia", "name": "Julia"},
    {"id": "matlab", "name": "MATLAB"},
    {"id": "sql", "name": "SQL"},
    {"id": "bash", "name": "Bash"},
    {"id": "powershell", "name": "PowerShell"},
    {"id": "solidity", "name": "Solidity"},
    {"id": "zig", "name": "Zig"},
    {"id": "nim", "name": "Nim"},
    {"id": "fortran", "name": "Fortran"},
    {"id": "assembly", "name": "Assembly"},
]

PLATFORM_IDS: tuple[str, ...] = tuple(item["id"] for item in PLATFORM_CATALOG)
PIPELINE_FRONTEND_TEMPLATE_IDS: tuple[str, ...] = tuple(
    item["id"] for item in PIPELINE_FRONTEND_TEMPLATE_CATALOG
)
FULL_FRONTEND_TEMPLATE_IDS: tuple[str, ...] = tuple(
    item["id"] for item in FULL_FRONTEND_TEMPLATE_CATALOG
)
PIPELINE_BACKEND_IDS: tuple[str, ...] = tuple(item["id"] for item in BACKEND_TEMPLATE_CATALOG)
DOMAIN_IDS: tuple[str, ...] = tuple(item["id"] for item in DOMAIN_CATALOG)
CICD_PLATFORM_IDS: tuple[str, ...] = tuple(item["id"] for item in CICD_PLATFORM_CATALOG)
CICD_PLATFORM_TARGET_IDS: tuple[str, ...] = tuple(
    item for item in CICD_PLATFORM_IDS if item != "all"
)

HOST_TOOL_CATALOG: list[dict[str, str]] = [
    {"id": "antigravity", "name": "Antigravity"},
    {"id": "claude", "name": "Claude"},
    {"id": "claude-code", "name": "Claude Code"},
    {"id": "cline", "name": "Cline"},
    {"id": "codebuddy-cli", "name": "CodeBuddy CLI"},
    {"id": "codebuddy", "name": "CodeBuddy"},
    {"id": "codebuddy-cn", "name": "CodeBuddyCN"},
    {"id": "droid-cli", "name": "Droid CLI"},
    {"id": "codex", "name": "Codex"},
    {"id": "codex-cli", "name": "Codex CLI"},
    {"id": "copilot-cli", "name": "Copilot CLI"},
    {"id": "cursor-cli", "name": "Cursor CLI"},
    {"id": "windsurf", "name": "Windsurf"},
    {"id": "gemini-cli", "name": "Gemini CLI"},
    {"id": "kimi-code", "name": "Kimi Code"},
    {"id": "kilo-code", "name": "Kilo Code"},
    {"id": "kiro-cli", "name": "Kiro CLI"},
    {"id": "opencode", "name": "OpenCode"},
    {"id": "qoder-cli", "name": "Qoder CLI"},
    {"id": "qwen-code", "name": "Qwen Code"},
    {"id": "roo-code", "name": "Roo Code"},
    {"id": "vscode-copilot", "name": "Copilot"},
    {"id": "cursor", "name": "Cursor"},
    {"id": "kiro", "name": "Kiro"},
    {"id": "qoder", "name": "Qoder"},
    {"id": "trae", "name": "Trae"},
    {"id": "trae-cn", "name": "TraeCN"},
    {"id": "trae-solo", "name": "Trae SOLO"},
    {"id": "trae-solocn", "name": "Trae SOLOCN"},
    {"id": "workbuddy", "name": "WorkBuddy"},
]

HOST_TOOL_IDS: tuple[str, ...] = tuple(item["id"] for item in HOST_TOOL_CATALOG)
HOST_TOOL_NAME_MAP: dict[str, str] = {item["id"]: item["name"] for item in HOST_TOOL_CATALOG}
HOST_TOOL_ALIASES: dict[str, list[str]] = {
    "claude": ["claude-app", "claude-desktop"],
    "claude-code": ["claude-cli", "claudecode"],
    "droid-cli": ["droid", "factory", "factory-droid"],
    "codebuddy-cn": ["codebuddycn"],
    "codex": ["codex-app", "codex-desktop"],
    "codex-cli": ["codexcli", "openai-codex-cli"],
    "copilot-cli": ["copilot"],
    "cursor-cli": ["cursor-agent"],
    "gemini-cli": ["gemini"],
    "kimi-code": ["kimi", "moonshot-kimi"],
    "opencode": ["open-code"],
    "qwen-code": ["qwen", "qwen-cli", "qwencli"],
    "trae-cn": ["traecn", "trae-ide-cn"],
    "trae-solo": ["traesolo"],
    "trae-solocn": ["trae-solo-cn", "traecnsolo"],
    "workbuddy": ["work-buddy", "腾讯虾"],
    "vscode-copilot": ["copilot-chat", "vscode"],
}

PRIMARY_CLI_HOST_TOOL_IDS: tuple[str, ...] = (
    "claude-code",
    "droid-cli",
    "codex-cli",
    "copilot-cli",
    "gemini-cli",
    "kimi-code",
    "opencode",
    "kiro-cli",
    "cursor-cli",
    "qoder-cli",
    "codebuddy-cli",
    "qwen-code",
)

PRIMARY_IDE_HOST_TOOL_IDS: tuple[str, ...] = (
    "antigravity",
    "cursor",
    "windsurf",
    "kiro",
    "qoder",
    "codebuddy",
    "trae",
    "trae-cn",
    "codebuddy-cn",
)

DESKTOP_ASSISTANT_HOST_TOOL_IDS: tuple[str, ...] = (
    "claude",
    "codex",
    "workbuddy",
    "trae-solo",
    "trae-solocn",
)

PRIMARY_HOST_TOOL_IDS: tuple[str, ...] = (
    PRIMARY_CLI_HOST_TOOL_IDS + PRIMARY_IDE_HOST_TOOL_IDS + DESKTOP_ASSISTANT_HOST_TOOL_IDS
)
SPECIAL_INSTALL_HOST_TOOL_IDS: tuple[str, ...] = ()
PRODUCT_HOST_TOOL_IDS: tuple[str, ...] = PRIMARY_HOST_TOOL_IDS + SPECIAL_INSTALL_HOST_TOOL_IDS

CLI_HOST_TOOL_IDS: tuple[str, ...] = (
    "claude-code",
    "codebuddy-cli",
    "droid-cli",
    "codex-cli",
    "copilot-cli",
    "cursor-cli",
    "gemini-cli",
    "kimi-code",
    "kiro-cli",
    "opencode",
    "qoder-cli",
    "qwen-code",
)
IDE_HOST_TOOL_IDS: tuple[str, ...] = (
    "antigravity",
    "cline",
    "codebuddy",
    "codebuddy-cn",
    "cursor",
    "kiro",
    "kilo-code",
    "qoder",
    "roo-code",
    "trae",
    "trae-cn",
    "vscode-copilot",
    "windsurf",
)
ASSISTANT_HOST_TOOL_IDS: tuple[str, ...] = (
    "claude",
    "codex",
    "trae-solo",
    "trae-solocn",
    "workbuddy",
)

HOST_TOOL_CATEGORY_MAP: dict[str, str] = {}
for _host_id in HOST_TOOL_IDS:
    if _host_id in CLI_HOST_TOOL_IDS:
        HOST_TOOL_CATEGORY_MAP[_host_id] = "cli"
    elif _host_id in ASSISTANT_HOST_TOOL_IDS:
        HOST_TOOL_CATEGORY_MAP[_host_id] = "assistant"
    else:
        HOST_TOOL_CATEGORY_MAP[_host_id] = "ide"

HOST_RUNTIME_VALIDATION_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "antigravity": {
        "runtime_checklist": [
            "确认当前 Antigravity Prompt / Agent Chat 绑定的是目标项目，而不是其他工作区。",
            "确认 `GEMINI.md`、`.gemini/commands/super-dev.toml` 与当前推荐 `.agent/workflows/super-dev.md` 已在新会话里一起生效。",
            "确认触发后直接进入 Super Dev 流水线，而不是退回普通 Gemini 对话。",
        ],
        "pass_criteria": [
            "Antigravity 在新聊天里真实读取了 GEMINI 上下文、custom commands 与当前推荐 workflow。",
        ],
        "resume_checklist": [
            "Antigravity 恢复时要确认重新打开的 Prompt / Agent Chat 已重新加载 GEMINI 上下文、custom commands 与当前推荐 workflow。",
        ],
    },
    "droid-cli": {
        "runtime_checklist": [
            "确认当前 Droid CLI 会话就在目标项目目录中，并且项目根 `AGENTS.md` 已被当前会话读取。",
            "确认 `.factory/rules/`、`.factory/commands/` 与 `.factory/skills/` 已存在并在当前会话中可见。",
            "确认 `/super-dev` 或 `/super-dev-seeai` 能在当前 Droid 会话中直接触发，而不是退回普通聊天。",
            "若使用续跑，确认 `droid exec --session-id <id> \"continue with next steps\"` 能继续当前 session。",
        ],
        "pass_criteria": [
            "Droid CLI 在当前项目会话中真实读取 `AGENTS.md + .factory/rules + .factory/commands + .factory/skills`，并稳定进入 Super Dev 流程。",
            "Droid CLI 的 SEEAI 入口在同一 session 中仍保留比赛快链路和恢复能力。",
        ],
        "resume_checklist": [
            "Droid CLI 恢复时优先确认当前 session 仍绑定目标项目，并在需要时使用 `droid exec --session-id <id>` 继续。",
        ],
    },
    "claude-code": {
        "runtime_checklist": [
            "确认当前 Claude Code 会话就在目标项目目录中，不是在其他工作区触发。",
            "确认项目根 `CLAUDE.md`、兼容 `.claude/CLAUDE.md`、项目级 `.claude/skills/super-dev/` 与用户级 `~/.claude/skills/` 已被当前会话重新加载。",
            "确认 `/super-dev` 直接进入 Super Dev，而不是普通聊天或旁路兼容命令面。",
            "确认改文档、补充、继续修改等自然语言仍留在当前 Super Dev 流程内。",
            "比赛模式验收时，确认 `/super-dev-seeai` 会进入 30 分钟比赛链路，并在 12 分钟内先跑出第一个可见、可点击、可截图的界面。",
            "确认 SEEAI 若初始化失败一次，会立刻切轻量回退栈，而不是继续死磕重配置方案。",
            "若 execution_mode 为 plan-execute，确认 .super-dev/plans/ 目录可写且 PlanExecutor 已初始化。",
            "若 codex_review_enabled 为 true，确认 codex CLI 可用（运行 which codex 验证）且 Overseer 已启用。",
        ],
        "pass_criteria": [
            "Claude Code 在 `CLAUDE.md + skills` 主模型下进入并保持同一条 Super Dev 流程，兼容 commands/agents 与可选 plugin enhancement 不会造成分叉。",
            "Claude Code 的 SEEAI 入口会保住比赛主路径：先跑出可演示界面，再补 wow 点，初始化失败会主动降级回退栈。",
            "Plan-Execute 模式下，每个阶段执行前有对应的 execution plan 文件。Overseer 审查报告在 .super-dev/overseer/ 中持续更新。",
        ],
        "resume_checklist": [
            "Claude Code 恢复时不能绕过当前确认门或返工门，并要确认重新打开的会话再次读取了 `CLAUDE.md + skills`。",
            "若当前是 SEEAI 比赛模式，恢复后仍应保持当前回退栈与演示主路径，不要重新做重初始化方案。",
        ],
    },
    "cline": {
        "runtime_checklist": [
            "确认当前 Cline 聊天面板绑定的是目标工作区，而不是其他 VS Code 工作区。",
            "确认 `.clinerules/` 与项目级 `.cline/skills/` 已在当前工作区重新加载。",
            "确认使用 `super-dev:` 继续补充或返工时，Cline 不会退回普通对话。",
        ],
        "pass_criteria": [
            "Cline 在目标工作区真实读取了 `.clinerules/` 与 `.cline/skills/`。",
        ],
        "resume_checklist": [
            "Cline 恢复时要确认聊天仍绑定目标工作区，并重新读取 `.clinerules/`。",
        ],
    },
    "codebuddy-cli": {
        "runtime_checklist": [
            "确认当前 CodeBuddy CLI 会话就在目标项目目录中，再触发 `/super-dev`。",
            "确认项目级 `.codebuddy/commands/`、`.codebuddy/skills/` 与兼容 `AGENTS.md` 都被当前会话加载。",
            "确认文档返工与确认门阶段仍然保持在 Super Dev 流程内。",
            "比赛模式验收时，确认 `/super-dev-seeai` 或 `super-dev-seeai:` 会进入半小时时间盒，而不是回到标准长链路。",
            "确认比赛模式会按 P0/P1/P2 控制范围，优先保住主演示路径，再补 wow 点。",
        ],
        "pass_criteria": [
            "CodeBuddy CLI 真实读取了项目级 commands、skills 与兼容规则面。",
            "CodeBuddy CLI 的 SEEAI 入口会进入 compact docs + compact spec + full-stack sprint 的比赛合同。",
        ],
        "resume_checklist": [
            "CodeBuddy CLI 恢复时要确认仍在目标项目目录，并重新加载 `.codebuddy/commands/` 与 skills。",
            "若正在 SEEAI 比赛模式中恢复，确认继续语句仍回到当前比赛合同，而不是重新开题。",
        ],
    },
    "codebuddy": {
        "runtime_checklist": [
            "确认当前 CodeBuddy Agent Chat 绑定的是目标项目，而不是其他工作区。",
            "确认 `.codebuddy/commands/`、`.codebuddy/agents/` 与 `.codebuddy/skills/` 已在当前会话真实生效。",
            "确认用户继续说“改一下 / 补充 / 继续改”时，CodeBuddy 仍然停留在当前确认门内。",
            "比赛模式验收时，确认 `/super-dev-seeai` 或 `super-dev-seeai:` 进入的是 30 分钟比赛链路，而不是标准 preview gate 流程。",
            "确认比赛模式下固定同一个 Agent Chat 仍能持续沿用当前上下文，不因子会话切换而丢失范围控制。",
        ],
        "pass_criteria": [
            "CodeBuddy 在目标工作区真实读取了 commands、agents 与 skills。",
            "CodeBuddy 的 SEEAI 入口会保留 compact 文档确认门，并在 Spec 后直接进入一体化快速开发。",
        ],
        "resume_checklist": [
            "CodeBuddy 恢复时要确认 Agent Chat 仍在目标项目，并继续当前确认门而不是重新开题。",
            "若当前是 SEEAI 比赛模式，恢复后仍应保持在同一个比赛冲刺会话里，而不是切回标准模式。",
        ],
    },
    "codex-cli": {
        "runtime_checklist": [
            "确认接入完成后已经彻底重开 codex，新会话会重新加载 AGENTS.md 与官方 Skills。",
            "确认项目根 `AGENTS.md`、项目级 `.agents/skills/super-dev/` 与官方用户级 Skills 一起生效；只有显式启用 `--with-user-surfaces` 时才再检查 `CODEX_HOME/AGENTS.md`（默认 `~/.codex/AGENTS.md`）。",
            "确认 repo plugin enhancement 已落地：`.agents/plugins/marketplace.json` 与 `plugins/super-dev-codex/.codex-plugin/plugin.json` 存在，并且 Codex App/Desktop 能看到本地 plugin 面。",
            "确认 Codex CLI 当前终端就在目标项目目录里，并优先使用 `$super-dev` 显式调用 Skill。",
            "确认 Codex App/Desktop 若在 `/` 列表里出现 `super-dev`，它被当作已启用 Skill 入口，而不是项目自定义 slash 文件。",
            "确认 `super-dev:` 仍可作为 AGENTS 驱动的自然语言回退入口，但不是 Codex 官方主触发面。",
            "比赛模式验收时，确认 `$super-dev-seeai`、App/Desktop 的 `/super-dev-seeai` 或 `super-dev-seeai:` 会进入 30 分钟比赛链路，并在 12 分钟内先跑出第一个可见、可点击、可截图的界面。",
            "确认 SEEAI 若初始化失败一次，会立刻切轻量回退栈，而不是继续死磕重配置方案。",
            "确认会话没有先解释 skill 或退回普通聊天，而是直接进入 Super Dev 流程。",
            "若被用于 Claude-Codex 混合模式审查，确认 codex --quiet --prompt 可正常执行。",
        ],
        "pass_criteria": [
            "重开 codex 后的新会话确实加载了项目 AGENTS.md、项目级 `.agents/skills/super-dev/` 与官方 Skills，并识别 repo plugin enhancement；若显式启用了 `--with-user-surfaces`，则额外确认全局 AGENTS 已生效。",
            "无论使用 Codex App/Desktop 的 `/super-dev` Skill 入口、CLI 的 `$super-dev`，还是 `super-dev:` 回退入口，都会进入同一条 Super Dev 流程。",
            "Codex 的 SEEAI 模式会优先保住比赛主路径：先跑出可演示界面，再补 wow 点，初始化失败会主动降级到更轻的回退栈。",
        ],
        "resume_checklist": [
            "Codex 必须在新会话里恢复，不能复用接入前的旧会话；若 App/Desktop 没看到本地 plugin 面，先确认 repo marketplace 已被当前项目加载。",
            "恢复时优先沿用当前会话表面：App/Desktop 继续从 `/` 列表选 `super-dev`，CLI 继续用 `$super-dev`；如果当前是在自然语言上下文中恢复，也要保持同一条 Super Dev 流程。",
            "若当前是 SEEAI 比赛模式，恢复后仍应保持当前回退栈与演示主路径，不要重新做重初始化方案。",
        ],
    },
    "copilot-cli": {
        "runtime_checklist": [
            "确认当前 Copilot CLI 会话就在目标项目目录，并已读取 `.github/copilot-instructions.md`。",
            "确认项目级 `.github/skills/` 与用户级 `~/.copilot/skills/` 已一起生效。",
            "确认使用 `super-dev:` 继续返工或确认时，Copilot CLI 不会退回普通聊天。",
        ],
        "pass_criteria": [
            "Copilot CLI 真实读取了 copilot-instructions 与 skills，并保持当前流程连续。",
        ],
        "resume_checklist": [
            "Copilot CLI 恢复时要确认新会话再次读取 `.github/copilot-instructions.md`。",
        ],
    },
    "cursor-cli": {
        "runtime_checklist": [
            "确认当前 Cursor CLI 终端就在目标项目目录，并已读取项目根 `AGENTS.md` / `CLAUDE.md` 与 `.cursor/rules/`。",
            "如果命令列表未刷新，先重开一次 Cursor CLI 会话再验收。",
            "确认规则来自当前项目而不是其他工作区残留上下文。",
        ],
        "pass_criteria": [
            "Cursor CLI 使用的是当前项目规则，而不是错误目录或旧会话上下文。",
        ],
        "resume_checklist": [
            "Cursor CLI 恢复时要确认当前终端目录仍是目标项目。",
        ],
    },
    "cursor": {
        "runtime_checklist": [
            "确认在正确项目工作区的 Agent Chat 中触发，而不是错误工作区。",
            "确认 `/super-dev` 后读取的是当前工作区规则，而不是旧会话上下文。",
            "确认用户持续修改 UI / 文档时仍然留在 Super Dev 流程中。",
        ],
        "pass_criteria": [
            "Cursor Agent Chat 绑定到正确工作区，并在返工阶段保持流程连续性。",
        ],
        "resume_checklist": [
            "Cursor Agent Chat 恢复时要确认仍在正确工作区。",
        ],
    },
    "gemini-cli": {
        "runtime_checklist": [
            "确认当前 Gemini CLI 会话就在目标项目目录，并已读取 `GEMINI.md`。",
            "确认 `/super-dev` 后先做 research，而不是直接编码。",
            "确认重开会话后仍能根据当前仓库上下文继续现有 Super Dev 流程。",
        ],
        "pass_criteria": [
            "Gemini CLI 真实读取了 `GEMINI.md`，并按 slash 流程执行而非普通聊天。",
        ],
        "resume_checklist": [
            "Gemini CLI 恢复时要确认新会话再次读取了 `GEMINI.md`。",
        ],
    },
    "kiro-cli": {
        "runtime_checklist": [
            "确认当前 Kiro CLI 会话就在目标项目目录，并已重新加载 `AGENTS.md`、`.kiro/steering/` 与 `.kiro/skills/`。",
            "确认使用 `/super-dev` 触发时，Kiro CLI 按 steering 流程执行而不是普通聊天。",
            "确认文档返工、确认门与继续修改都还能留在当前流程内。",
        ],
        "pass_criteria": [
            "Kiro CLI 在新会话里真实读取了 AGENTS.md、steering 与 skills，并保持流程连续。",
        ],
        "resume_checklist": [
            "Kiro CLI 恢复时要确认新会话再次加载 AGENTS.md、`.kiro/steering/` 与 skills。",
        ],
    },
    "kiro": {
        "runtime_checklist": [
            "确认当前 Kiro IDE Agent Chat 打开的就是目标项目，而不是其他工作区。",
            "确认 `AGENTS.md`、`.kiro/steering/` 与 `.kiro/skills/` 已在新的 Agent Chat 里生效。",
            "确认用户在确认门里补充和修改时，Kiro IDE 仍然留在 Super Dev 流程内。",
        ],
        "pass_criteria": [
            "Kiro IDE 在目标工作区真实读取了 AGENTS.md、steering 与 skills。",
        ],
        "resume_checklist": [
            "Kiro IDE 恢复时要确认重新打开的 Agent Chat 仍加载当前项目的 AGENTS.md、steering 与 skills。",
        ],
    },
    "kilo-code": {
        "runtime_checklist": [
            "确认当前 Kilo Code 聊天面板绑定的是目标工作区，并已重新加载 `.kilocode/rules/`。",
            "确认使用 `super-dev:` 继续返工或确认时，Kilo Code 不会退回普通对话。",
            "确认当前工作区里的规则比旧聊天残留上下文优先。",
        ],
        "pass_criteria": [
            "Kilo Code 在目标工作区真实读取了 `.kilocode/rules/` 并保持流程连续。",
        ],
        "resume_checklist": [
            "Kilo Code 恢复时要确认聊天仍在目标工作区，并重新读取 `.kilocode/rules/`。",
        ],
    },
    "opencode": {
        "runtime_checklist": [
            "确认当前 OpenCode 会话就是目标项目目录，并使用 `/super-dev` 进入。",
            "如果命令列表没刷新，重开一次当前 OpenCode 会话后再验收。",
            "确认项目级 AGENTS.md、commands、skills 都被当前会话真实加载。",
        ],
        "pass_criteria": [
            "项目级 AGENTS.md、commands、skills 被当前 OpenCode 会话真实读取。",
        ],
        "resume_checklist": [
            "OpenCode 必须在当前项目会话里恢复，不允许切到普通聊天上下文。",
        ],
    },
    "qoder-cli": {
        "runtime_checklist": [
            "确认当前 Qoder CLI 会话就在目标项目目录，并且 `/super-dev` 命令已经刷新可见。",
            "确认 `.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/` 都被当前会话加载。",
            "确认文档返工和确认门阶段不会退回普通聊天。",
        ],
        "pass_criteria": [
            "Qoder CLI 真实读取了 rules、commands 与 skills，并保持流程连续。",
        ],
        "resume_checklist": [
            "Qoder CLI 恢复时要确认新会话再次加载 `.qoder/rules/`、commands 与 skills。",
        ],
    },
    "qoder": {
        "runtime_checklist": [
            "确认当前 Qoder IDE Agent Chat 绑定的是目标项目，而不是其他工作区。",
            "确认 `.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/` 在当前 IDE 会话里真实生效。",
            "确认用户持续修改文档或 UI 时，Qoder IDE 仍然留在当前 Super Dev 流程内。",
        ],
        "pass_criteria": [
            "Qoder IDE 在目标工作区真实读取了 rules、commands 与 skills。",
        ],
        "resume_checklist": [
            "Qoder IDE 恢复时要确认 Agent Chat 仍在目标项目，并继续当前确认门。",
        ],
    },
    "roo-code": {
        "runtime_checklist": [
            "确认当前 Roo Code 聊天位于目标项目工作区，并且 `/super-dev` 命令已刷新可用。",
            "确认 `.roo/rules/` 与 `.roo/commands/` 已在当前聊天真实加载。",
            "确认返工与确认阶段继续使用 Roo Code 当前工作区规则，而不是普通聊天。",
        ],
        "pass_criteria": [
            "Roo Code 在目标工作区真实读取了 `.roo/rules/` 与 `.roo/commands/`。",
        ],
        "resume_checklist": [
            "Roo Code 恢复时要确认聊天仍位于目标工作区，并重新加载 `.roo/` 规则与命令。",
        ],
    },
    "trae": {
        "runtime_checklist": [
            "确认当前 Trae Agent Chat 绑定的是目标项目工作区，而不是其他项目。",
            "确认 `.trae/project_rules.md` 或兼容 `.trae/rules.md` 已在当前聊天里真实加载。",
            "确认使用 `super-dev:` 继续补充、返工或确认时，Trae 不会退回普通对话。",
        ],
        "pass_criteria": [
            "Trae 在目标工作区真实读取了项目规则，并在返工阶段保持流程连续。",
        ],
        "resume_checklist": [
            "Trae 恢复时要确认新聊天仍绑定目标项目，并重新读取 `.trae/project_rules.md`。",
        ],
    },
    "vscode-copilot": {
        "runtime_checklist": [
            "确认当前 VS Code Copilot Chat 绑定的是目标项目工作区，而不是其他工作区。",
            "确认 `.github/copilot-instructions.md` 已被当前聊天真实加载。",
            "确认继续说“改一下 / 补充 / 确认”时，Copilot Chat 仍然留在当前 Super Dev 流程内。",
        ],
        "pass_criteria": [
            "VS Code Copilot 在目标工作区真实读取了 copilot-instructions，并保持流程连续。",
        ],
        "resume_checklist": [
            "VS Code Copilot 恢复时要确认聊天仍在目标工作区，并重新读取 `.github/copilot-instructions.md`。",
        ],
    },
    "windsurf": {
        "runtime_checklist": [
            "确认当前 Windsurf Agent Chat / Workflow 入口绑定的是目标项目工作区。",
            "确认 `AGENTS.md`、`.windsurf/rules/`、`.windsurf/workflows/` 与 `.windsurf/skills/` 已在当前会话真实加载。",
            "确认通过 workflow 或 `/super-dev` 返工时，Windsurf 仍然留在当前流程内。",
        ],
        "pass_criteria": [
            "Windsurf 在目标工作区真实读取了 AGENTS、rules、workflows 与 skills。",
        ],
        "resume_checklist": [
            "Windsurf 恢复时要确认 Agent Chat / Workflow 已重新加载当前项目的 AGENTS、rules、workflow 与 skills。",
        ],
    },
}


def host_runtime_validation_overrides(target: str) -> dict[str, list[str]]:
    adapter_runtime_checklist = list(get_runtime_checklist(target))
    adapter_pass_criteria = list(get_pass_criteria(target))
    adapter_resume_checklist = list(get_resume_checklist(target))
    if adapter_runtime_checklist or adapter_pass_criteria or adapter_resume_checklist:
        return {
            "runtime_checklist": adapter_runtime_checklist,
            "pass_criteria": adapter_pass_criteria,
            "resume_checklist": adapter_resume_checklist,
        }
    return HOST_RUNTIME_VALIDATION_OVERRIDES.get(target, {})


HOST_COMMAND_CANDIDATES: dict[str, list[str]] = {
    "antigravity": ["antigravity"],
    "claude": ["claude"],
    "claude-code": ["claude", "claude-code"],
    "cline": ["cline"],
    "codebuddy-cli": ["codebuddy", "codebuddy-cli"],
    "codebuddy-cn": ["codebuddy-cn"],
    "droid-cli": ["droid", "factory-droid"],
    "codebuddy": ["codebuddy"],
    "codex": ["codex"],
    "codex-cli": ["codex"],
    "copilot-cli": ["copilot", "copilot-cli"],
    "cursor-cli": ["cursor-agent", "cursor", "cursor-cli"],
    "windsurf": ["windsurf"],
    "gemini-cli": ["gemini", "gemini-cli"],
    "kimi-code": ["kimi", "kimi-code"],
    "kilo-code": ["kilo-code"],
    "kiro-cli": ["kiro"],
    "opencode": ["opencode"],
    "qoder-cli": ["qoder", "qoder-cli"],
    "qwen-code": ["qwen", "qwen-code"],
    "roo-code": ["roo", "roo-code"],
    "cursor": ["cursor"],
    "qoder": ["qoder"],
    "trae": ["trae"],
    "trae-cn": ["trae-cn", "traecn"],
    "trae-solo": ["trae-solo", "traesolo"],
    "trae-solocn": ["trae-solocn", "traecnsolo"],
    "workbuddy": ["workbuddy"],
}

HOST_PATH_PATTERNS: dict[str, list[str]] = {
    "antigravity": [
        "~/Applications/Antigravity.app",
        "/Applications/Antigravity.app",
        "%LOCALAPPDATA%/Programs/Google/Antigravity/Antigravity.exe",
        "%PROGRAMFILES%/Google/Antigravity/Antigravity.exe",
        "%PROGRAMFILES(X86)%/Google/Antigravity/Antigravity.exe",
        "%LOCALAPPDATA%/Programs/Antigravity/Antigravity.exe",
        "%PROGRAMFILES%/Antigravity/Antigravity.exe",
        "%PROGRAMFILES(X86)%/Antigravity/Antigravity.exe",
    ],
    "claude": [
        "~/Applications/Claude.app",
        "/Applications/Claude.app",
        "%LOCALAPPDATA%/Programs/Claude/Claude.exe",
        "%PROGRAMFILES%/Claude/Claude.exe",
        "%PROGRAMFILES(X86)%/Claude/Claude.exe",
    ],
    "codebuddy": [
        "~/Applications/CodeBuddy.app",
        "/Applications/CodeBuddy.app",
        "%LOCALAPPDATA%/Programs/CodeBuddy/CodeBuddy.exe",
        "%PROGRAMFILES%/CodeBuddy/CodeBuddy.exe",
        "%PROGRAMFILES(X86)%/CodeBuddy/CodeBuddy.exe",
    ],
    "codebuddy-cn": [
        "~/Applications/CodeBuddy.app",
        "/Applications/CodeBuddy.app",
        "%LOCALAPPDATA%/Programs/CodeBuddy/CodeBuddy.exe",
        "%PROGRAMFILES%/CodeBuddy/CodeBuddy.exe",
        "%PROGRAMFILES(X86)%/CodeBuddy/CodeBuddy.exe",
    ],
    "codex": [
        "~/Applications/Codex.app",
        "/Applications/Codex.app",
        "~/Applications/OpenAI Codex.app",
        "/Applications/OpenAI Codex.app",
        "%LOCALAPPDATA%/Programs/Codex/Codex.exe",
        "%PROGRAMFILES%/Codex/Codex.exe",
        "%PROGRAMFILES(X86)%/Codex/Codex.exe",
        "%LOCALAPPDATA%/Programs/OpenAI Codex/Codex.exe",
        "%PROGRAMFILES%/OpenAI Codex/Codex.exe",
        "%PROGRAMFILES(X86)%/OpenAI Codex/Codex.exe",
    ],
    "codex-cli": [
        "~/Applications/Codex.app",
        "/Applications/Codex.app",
        "~/Applications/OpenAI Codex.app",
        "/Applications/OpenAI Codex.app",
        "%LOCALAPPDATA%/Programs/Codex/Codex.exe",
        "%PROGRAMFILES%/Codex/Codex.exe",
        "%PROGRAMFILES(X86)%/Codex/Codex.exe",
        "%LOCALAPPDATA%/Programs/OpenAI Codex/Codex.exe",
        "%PROGRAMFILES%/OpenAI Codex/Codex.exe",
        "%PROGRAMFILES(X86)%/OpenAI Codex/Codex.exe",
    ],
    "kimi-code": [
        "~/.kimi",
    ],
    "qwen-code": [
        "~/.qwen",
    ],
    "cursor-cli": [
        "~/Applications/Cursor.app",
        "/Applications/Cursor.app",
        "%LOCALAPPDATA%/Programs/Cursor/Cursor.exe",
        "%PROGRAMFILES%/Cursor/Cursor.exe",
        "%PROGRAMFILES(X86)%/Cursor/Cursor.exe",
    ],
    "cursor": [
        "~/Applications/Cursor.app",
        "/Applications/Cursor.app",
        "%LOCALAPPDATA%/Programs/Cursor/Cursor.exe",
        "%PROGRAMFILES%/Cursor/Cursor.exe",
        "%PROGRAMFILES(X86)%/Cursor/Cursor.exe",
    ],
    "kiro": [
        "~/Applications/Kiro.app",
        "/Applications/Kiro.app",
        "%LOCALAPPDATA%/Programs/Kiro/Kiro.exe",
        "%PROGRAMFILES%/Kiro/Kiro.exe",
        "%PROGRAMFILES(X86)%/Kiro/Kiro.exe",
    ],
    "windsurf": [
        "~/Applications/Windsurf.app",
        "/Applications/Windsurf.app",
        "%LOCALAPPDATA%/Programs/Windsurf/Windsurf.exe",
        "%PROGRAMFILES%/Windsurf/Windsurf.exe",
        "%PROGRAMFILES(X86)%/Windsurf/Windsurf.exe",
    ],
    "qoder-cli": [
        "~/Applications/Qoder.app",
        "/Applications/Qoder.app",
        "%LOCALAPPDATA%/Programs/Qoder/Qoder.exe",
        "%PROGRAMFILES%/Qoder/Qoder.exe",
        "%PROGRAMFILES(X86)%/Qoder/Qoder.exe",
    ],
    "qoder": [
        "~/Applications/Qoder.app",
        "/Applications/Qoder.app",
        "%LOCALAPPDATA%/Programs/Qoder/Qoder.exe",
        "%PROGRAMFILES%/Qoder/Qoder.exe",
        "%PROGRAMFILES(X86)%/Qoder/Qoder.exe",
    ],
    "trae": [
        "~/Applications/Trae.app",
        "/Applications/Trae.app",
        "%LOCALAPPDATA%/Programs/Trae/Trae.exe",
        "%PROGRAMFILES%/Trae/Trae.exe",
        "%PROGRAMFILES(X86)%/Trae/Trae.exe",
    ],
    "trae-cn": [
        "~/Applications/Trae.app",
        "/Applications/Trae.app",
        "%LOCALAPPDATA%/Programs/Trae/Trae.exe",
        "%PROGRAMFILES%/Trae/Trae.exe",
        "%PROGRAMFILES(X86)%/Trae/Trae.exe",
    ],
    "vscode-copilot": [
        "~/Applications/Visual Studio Code.app",
        "/Applications/Visual Studio Code.app",
        "%LOCALAPPDATA%/Programs/Microsoft VS Code/Code.exe",
        "%PROGRAMFILES%/Microsoft VS Code/Code.exe",
        "%PROGRAMFILES(X86)%/Microsoft VS Code/Code.exe",
    ],
    "workbuddy": [
        "~/Applications/WorkBuddy.app",
        "/Applications/WorkBuddy.app",
        "%LOCALAPPDATA%/Programs/WorkBuddy/WorkBuddy.exe",
        "%PROGRAMFILES%/WorkBuddy/WorkBuddy.exe",
        "%PROGRAMFILES(X86)%/WorkBuddy/WorkBuddy.exe",
    ],
}


def _expand_host_pattern(pattern: str) -> str:
    expanded = pattern
    windows_aliases = {
        "%LOCALAPPDATA%": os.environ.get("LOCALAPPDATA", ""),
        "%APPDATA%": os.environ.get("APPDATA", ""),
        "%PROGRAMFILES%": os.environ.get("PROGRAMFILES", ""),
        "%PROGRAMFILES(X86)%": os.environ.get("PROGRAMFILES(X86)", ""),
        "%USERPROFILE%": os.environ.get("USERPROFILE", str(Path.home())),
    }
    for key, value in windows_aliases.items():
        if key in expanded:
            expanded = expanded.replace(key, value)
    return os.path.expanduser(os.path.expandvars(expanded))


def host_path_candidates(host_id: str) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for pattern in HOST_PATH_PATTERNS.get(host_id, []):
        expanded = _expand_host_pattern(pattern)
        if not expanded or expanded in seen:
            continue
        seen.add(expanded)
        candidates.append(expanded)
    return candidates


def _host_path_override_env_keys(host_id: str) -> list[str]:
    normalized = host_id.upper().replace("-", "_")
    return [
        f"SUPER_DEV_HOST_PATH_{normalized}",
        f"SUPER_DEV_HOST_LOCATION_{normalized}",
    ]


def _split_override_paths(raw: str) -> list[str]:
    if not raw.strip():
        return []
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    chunks: list[str] = []
    for line in normalized.split("\n"):
        line = line.strip()
        if not line:
            continue
        if os.pathsep in line:
            chunks.extend(item.strip() for item in line.split(os.pathsep) if item.strip())
        else:
            chunks.append(line)
    return chunks


def host_override_path_candidates(host_id: str) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for key in _host_path_override_env_keys(host_id):
        for item in _split_override_paths(os.environ.get(key, "")):
            expanded = _expand_host_pattern(item)
            if not expanded or expanded in seen:
                continue
            seen.add(expanded)
            candidates.append(expanded)
    return candidates


def _host_windows_probe_names(host_id: str) -> list[str]:
    names: set[str] = set()
    for command in HOST_COMMAND_CANDIDATES.get(host_id, []):
        cmd = command.strip()
        if not cmd:
            continue
        names.add(cmd)
        names.add(f"{cmd}.exe")
        names.add(f"{cmd}.cmd")
    for pattern in HOST_PATH_PATTERNS.get(host_id, []):
        base = Path(_expand_host_pattern(pattern)).name.strip()
        if base:
            names.add(base)
    return sorted(item for item in names if item)


def _normalize_windows_launch_target(value: str) -> str:
    cleaned = str(value).strip().strip('"')
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    for suffix in (".exe", ".cmd", ".bat", ".ps1", ".app"):
        index = lowered.find(suffix)
        if index != -1:
            return cleaned[: index + len(suffix)]
    return cleaned.split(" ", 1)[0]


def _windows_registry_path_candidates(host_id: str) -> list[str]:
    with contextlib.suppress(ImportError):
        import winreg as _winreg  # type: ignore[import-not-found]

        winreg = cast(Any, _winreg)

        seen: set[str] = set()
        candidates: list[str] = []
        for probe_name in _host_windows_probe_names(host_id):
            subkey = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{probe_name}"
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                with contextlib.suppress(FileNotFoundError, OSError):
                    key = winreg.OpenKey(hive, subkey)
                    try:
                        for value_name in (None, ""):
                            with contextlib.suppress(FileNotFoundError, OSError, TypeError):
                                raw_value, _ = winreg.QueryValueEx(key, value_name)
                                candidate = _normalize_windows_launch_target(raw_value)
                                if candidate and candidate not in seen:
                                    seen.add(candidate)
                                    candidates.append(candidate)
                        with contextlib.suppress(FileNotFoundError, OSError):
                            raw_path, _ = winreg.QueryValueEx(key, "Path")
                            folder = _normalize_windows_launch_target(raw_path)
                            if folder:
                                joined = str(Path(folder) / probe_name)
                                if joined not in seen:
                                    seen.add(joined)
                                    candidates.append(joined)
                    finally:
                        winreg.CloseKey(key)
        return candidates
    return []


def _windows_package_manager_candidates(host_id: str) -> list[str]:
    base_patterns = [
        "%LOCALAPPDATA%/Microsoft/WinGet/Links",
        "%LOCALAPPDATA%/Microsoft/WindowsApps",
        "%USERPROFILE%/scoop/shims",
        "%PROGRAMDATA%/chocolatey/bin",
        "%APPDATA%/npm",
    ]
    seen: set[str] = set()
    candidates: list[str] = []
    for base_pattern in base_patterns:
        base = _expand_host_pattern(base_pattern)
        if not base:
            continue
        for probe_name in _host_windows_probe_names(host_id):
            candidate = str(Path(base) / probe_name)
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def host_detection_path_candidates(host_id: str) -> list[tuple[str, str]]:
    probes: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _append(kind: str, values: list[str]) -> None:
        for value in values:
            item = (kind, value)
            if not value or item in seen:
                continue
            seen.add(item)
            probes.append(item)

    _append("env", host_override_path_candidates(host_id))
    _append("path", host_path_candidates(host_id))
    _append("registry", _windows_registry_path_candidates(host_id))
    _append("shim", _windows_package_manager_candidates(host_id))
    return probes


def host_path_override_guide(host_id: str) -> dict[str, object]:
    env_keys = _host_path_override_env_keys(host_id)
    primary_key = env_keys[0] if env_keys else ""
    probe_names = _host_windows_probe_names(host_id)
    probe_name = probe_names[0] if probe_names else host_id
    unix_example = f"/path/to/{probe_name}"
    windows_example = f"C:\\path\\to\\{probe_name}"
    return {
        "env_key": primary_key,
        "legacy_env_keys": env_keys[1:],
        "unix_example": unix_example,
        "windows_example": windows_example,
        "unix_export": f"export {primary_key}={unix_example}" if primary_key else "",
        "powershell_export": f"$env:{primary_key}='{windows_example}'" if primary_key else "",
        "hint": (
            f"如果装在自定义目录，先设置 `{primary_key}=<安装路径>` 再重试。" if primary_key else ""
        ),
        "supported_detection_sources": [
            "命令命中",
            "默认安装路径",
            "自定义路径覆盖",
            "Windows 注册信息",
            "Windows shim / 包管理器目录",
        ],
    }


def host_display_name(host_id: str) -> str:
    return HOST_TOOL_NAME_MAP.get(host_id, host_id)


def normalize_host_tool_id(value: str) -> str:
    normalized = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    if normalized in HOST_TOOL_IDS:
        return normalized
    for host_id, aliases in HOST_TOOL_ALIASES.items():
        if normalized in aliases:
            return host_id
    for host_id, host_name in HOST_TOOL_NAME_MAP.items():
        simplified_name = host_name.lower().replace("_", "-").replace(" ", "-")
        simplified_without_cli = simplified_name.removesuffix("-cli")
        candidates = {simplified_name}
        if simplified_without_cli not in HOST_TOOL_IDS:
            candidates.add(simplified_without_cli)
        if normalized in candidates:
            return host_id
    return normalized
