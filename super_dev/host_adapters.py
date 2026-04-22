"""Specialized host adapters for high-variance hosts.

This module carries host-specific integration behavior for hosts that need
deeper guidance than the generic slash/text workflow path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SpecialAdapterContext:
    """Context needed to render host-specific adapter content."""

    target: str
    category: str
    usage_location: str
    usage_notes: tuple[str, ...]
    text_trigger_prefix: str = "super-dev:"
    seeai_text_trigger_prefix: str = "super-dev-seeai:"


@dataclass(frozen=True, slots=True)
class ManualInstallGuidance:
    """Manual install copy for hosts that do not use the unified installer."""

    title: str
    lines: tuple[str, ...]
    border_style: str = "yellow"
    plain_fallback: str = ""


@dataclass(frozen=True, slots=True)
class HostSpecialAdapter:
    """Specialized behavior for hosts that diverge from generic handling."""

    host_id: str
    adapter_mode_override: str = ""
    install_surfaces: dict[str, tuple[str, ...]] = field(default_factory=dict)
    runtime_checklist: tuple[str, ...] = ()
    pass_criteria: tuple[str, ...] = ()
    resume_checklist: tuple[str, ...] = ()
    competition_smoke_extra_steps: tuple[str, ...] = ()
    flow_probe: dict[str, Any] = field(default_factory=dict)
    manual_install_guidance: ManualInstallGuidance | None = None

    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        raise NotImplementedError


def _runtime_validation_payload(adapter: HostSpecialAdapter) -> dict[str, list[str]]:
    return {
        "runtime_checklist": list(adapter.runtime_checklist),
        "pass_criteria": list(adapter.pass_criteria),
        "resume_checklist": list(adapter.resume_checklist),
    }


@dataclass(frozen=True, slots=True)
class _CodeBuddyCliAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "native-slash",
            "primary_entry": "在 CodeBuddy CLI 当前项目会话里优先使用 `/super-dev <需求描述>`；比赛模式优先使用 `/super-dev-seeai <需求描述>`。",
            "trigger_command": "/super-dev <需求描述>",
            "entry_variants": [
                {
                    "surface": "cli",
                    "label": "CodeBuddy CLI",
                    "entry": "/super-dev",
                    "mode": "official-subagent-slash",
                    "priority": "preferred",
                    "notes": "标准 Super Dev 主流程入口。",
                },
                {
                    "surface": "competition",
                    "label": "CodeBuddy CLI SEEAI",
                    "entry": "/super-dev-seeai",
                    "mode": "official-subagent-slash",
                    "priority": "preferred",
                    "notes": "比赛半小时极速版入口。",
                },
                {
                    "surface": "fallback",
                    "label": "Natural Language Fallback",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "rules-natural-language-fallback",
                    "priority": "fallback",
                    "notes": "当 slash 不可用时的自然语言回退入口。",
                },
            ],
            "trigger_context": "CodeBuddy CLI 当前项目会话",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "确认项目内已生成 `CODEBUDDY.md`、`.codebuddy/commands/super-dev.md`、`.codebuddy/commands/super-dev-seeai.md`、`.codebuddy/skills/super-dev/SKILL.md` 与 `.codebuddy/skills/super-dev-seeai/SKILL.md`。",
                "确认用户目录已生成 `~/.codebuddy/CODEBUDDY.md`、`~/.codebuddy/commands/` 与 `~/.codebuddy/skills/`。",
                "在 CodeBuddy CLI 当前项目会话里优先输入 `/super-dev <需求描述>`；比赛模式优先输入 `/super-dev-seeai <需求描述>`。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "CodeBuddy CLI 当前最佳接入面是 CODEBUDDY.md + commands + skills，并保持同一会话内连续完成 research、文档、Spec 与实现。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _CodeBuddyIdeAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "native-slash",
            "primary_entry": "在 CodeBuddy 的 Agent Chat 里优先使用 `/super-dev <需求描述>`；比赛模式优先使用 `/super-dev-seeai <需求描述>`。",
            "trigger_command": "/super-dev <需求描述>",
            "entry_variants": [
                {
                    "surface": "ide",
                    "label": "CodeBuddy",
                    "entry": "/super-dev",
                    "mode": "official-subagent-slash",
                    "priority": "preferred",
                    "notes": "标准 Super Dev 主流程入口。",
                },
                {
                    "surface": "competition",
                    "label": "CodeBuddy SEEAI",
                    "entry": "/super-dev-seeai",
                    "mode": "official-subagent-slash",
                    "priority": "preferred",
                    "notes": "比赛半小时极速版入口。",
                },
                {
                    "surface": "fallback",
                    "label": "Natural Language Fallback",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "rules-natural-language-fallback",
                    "priority": "fallback",
                    "notes": "当 slash 不可用时的自然语言回退入口。",
                },
            ],
            "trigger_context": "CodeBuddy Agent Chat",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "确认项目内已生成 `CODEBUDDY.md`、`.codebuddy/rules/super-dev/RULE.mdc`、`.codebuddy/commands/super-dev.md`、`.codebuddy/commands/super-dev-seeai.md`、`.codebuddy/agents/super-dev.md`、`.codebuddy/skills/super-dev/SKILL.md` 与 `.codebuddy/skills/super-dev-seeai/SKILL.md`。",
                "确认用户目录已生成 `~/.codebuddy/CODEBUDDY.md`、`~/.codebuddy/commands/`、`~/.codebuddy/agents/` 与 `~/.codebuddy/skills/`。",
                "在 CodeBuddy 的 Agent Chat 里优先输入 `/super-dev <需求描述>`；比赛模式优先输入 `/super-dev-seeai <需求描述>`。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "CodeBuddy 需要规则、commands、agents 与 skills 四层同时稳定工作，比赛模式下优先保住 P0 主路径与 wow 点。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _DroidCliAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "factory-slash-and-skill",
            "primary_entry": "在 Droid CLI 当前项目会话里优先使用 `/super-dev <需求描述>`；底层优先由 `.factory/skills/` 承接 slash，`.factory/commands/` 仅保留为 legacy compatibility。比赛模式优先 `/super-dev-seeai <需求描述>`。",
            "trigger_command": "/super-dev <需求描述>",
            "entry_variants": [
                {
                    "surface": "cli",
                    "label": "Droid CLI Slash",
                    "entry": "/super-dev",
                    "mode": "factory-slash",
                    "priority": "preferred",
                    "notes": "标准 Super Dev 主流程入口。",
                },
                {
                    "surface": "fallback",
                    "label": "Droid CLI Text Fallback",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "factory-text-fallback",
                    "priority": "fallback",
                    "notes": "slash 暂时不可用或当前正处于会话连续恢复时的自然语言回退入口。",
                },
                {
                    "surface": "competition",
                    "label": "Droid CLI SEEAI",
                    "entry": "/super-dev-seeai",
                    "mode": "factory-slash",
                    "priority": "preferred",
                    "notes": "比赛半小时极速版入口；需要时回退 `super-dev-seeai:`。",
                },
            ],
            "trigger_context": "Droid CLI 当前项目会话",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "确认项目根 `AGENTS.md` 已写入 Super Dev 合同，并补齐 `.factory/rules/super-dev.md`。",
                "确认项目级 `.factory/skills/super-dev/SKILL.md` 与 `.factory/skills/super-dev-seeai/SKILL.md` 已生成，作为优先 slash/skill 面。",
                "确认 `.factory/commands/super-dev.md` 与 `.factory/commands/super-dev-seeai.md` 仅作为 legacy slash compatibility 一起保留。",
                "如需跨项目沿用同一套宿主心智，再显式启用 `--with-user-surfaces` 补齐 `~/.factory/AGENTS.md` 与用户级 `.factory/*`。",
                "在 Droid CLI 当前会话里优先使用 `/super-dev` 或 `/super-dev-seeai`；需要继续当前流程时保留同一 session。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "Droid CLI 的核心适配面是 `AGENTS.md + .factory/rules + .factory/skills`。Factory 官方已明确 skills 可以直接作为 `/command` 使用，因此 `.factory/skills/` 是主入口，`.factory/commands/` 只保留为 legacy slash compatibility；需要恢复时优先继续同一个 session，而不是重新开题。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _KimiCodeAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "agents-skills-native-resume",
            "primary_entry": "在 Kimi Code 当前项目会话里优先使用 `/skill:super-dev <需求描述>`；需要结构化流程时再考虑 `/flow:super-dev <需求描述>`，`super-dev: <需求描述>` 只保留为统一宿主回退入口。",
            "trigger_command": "/skill:super-dev <需求描述>",
            "entry_variants": [
                {
                    "surface": "skill",
                    "label": "Kimi Code Skill",
                    "entry": "/skill:super-dev <需求描述>",
                    "mode": "official-skill-entry",
                    "priority": "preferred",
                    "notes": "Kimi Code 当前优先显式 Skill 入口。",
                },
                {
                    "surface": "flow",
                    "label": "Kimi Code Flow",
                    "entry": "/flow:super-dev <需求描述>",
                    "mode": "official-flow-entry",
                    "priority": "optional",
                    "notes": "当宿主已安装对应 flow 时的显式流程入口。",
                },
                {
                    "surface": "fallback",
                    "label": "Kimi Code Text Fallback",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "agents-natural-language",
                    "priority": "fallback",
                    "notes": "与其他宿主保持一致的自然语言回退入口。",
                },
            ],
            "trigger_context": "Kimi Code 当前项目会话",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": True,
            "post_onboard_steps": [
                "先确认项目根 `AGENTS.md` 已生成，并由当前会话真实读取。",
                "若仓库里启用了 `.kimi/skills/super-dev/SKILL.md`，把它视为当前集成增强面而不是唯一官方硬合同；`.kimi/AGENTS.md` 只作为兼容增强面。",
                "如果显式启用了用户级增强面，再检查 `~/.kimi/skills/`、`~/.config/agents/skills/` 或 `~/.agents/skills/` 是否已同步。",
                "优先在当前项目会话里输入 `/skill:super-dev <需求描述>`；需要结构化流程时再考虑 `/flow:super-dev <需求描述>`。",
                "中断恢复时优先使用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，而不是重新开题。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "Kimi Code 当前主链按 `AGENTS.md + explicit /skill:/flow entries + native session continue / resume` 建模，原生恢复优先 `kimi --continue`、`kimi --session <id>` 与运行中的 `/sessions` / `/resume`；`.kimi/skills/` 与 `.kimi/AGENTS.md` 继续保留为当前集成增强面而不是对外宣称的唯一文件合同。自然语言 `super-dev:` 只保留为统一宿主回退入口。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _TraeSoloAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "workspace-rules-slash-skill",
            "primary_entry": "在 Trae SOLO 当前 workspace 里优先使用 `/super-dev <需求描述>`；如果 slash 刷新慢，再回退到 `super-dev: <需求描述>`。",
            "trigger_command": "/super-dev <需求描述>",
            "entry_variants": [
                {
                    "surface": "workspace",
                    "label": "Trae SOLO",
                    "entry": "/super-dev",
                    "mode": "workspace-slash",
                    "priority": "preferred",
                    "notes": "官方 custom slash commands 入口。",
                },
                {
                    "surface": "fallback",
                    "label": "Trae SOLO Fallback",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "workspace-natural-language",
                    "priority": "fallback",
                    "notes": "slash 未刷新或当前会话已在连续恢复路径中时使用。",
                },
                {
                    "surface": "competition",
                    "label": "Trae SOLO SEEAI",
                    "entry": "/super-dev-seeai",
                    "mode": "workspace-slash",
                    "priority": "preferred",
                    "notes": "比赛快链路入口；必要时回退到 `super-dev-seeai:`。",
                },
            ],
            "trigger_context": "Trae SOLO 当前 workspace / task session",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": True,
            "post_onboard_steps": [
                "确认项目根 `AGENTS.md`、`.trae/rules/super-dev.md`、`.trae/commands/super-dev.md` 与 `.trae/skills/super-dev/SKILL.md` 已生成。",
                "重新打开当前 workspace，让 Rules / Commands / Skills 在新会话里一起生效。",
                "优先输入 `/super-dev <需求描述>`；slash 刷新慢时回退到 `super-dev: <需求描述>`。",
                "恢复时优先沿用当前 workspace continuity，不要重新开题。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "Trae SOLO 当前最佳接入面是 `AGENTS.md + .trae/rules + .trae/commands + .trae/skills`。官方文档已经公开 Rules、custom slash commands、Skills 与 workspace continuity，因此更适合把 Super Dev 作为项目级工作流层接入，而不是只靠自然语言热启动。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _TraeSoloCnAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "mtc-code-rules-skill",
            "primary_entry": "在 Trae SOLOCN 当前工作区里优先使用 `super-dev: <需求描述>`；它会与宿主内建的 `/plan`、`/spec` 和 MTC / Code 双模式协同，而不是替代它们。",
            "trigger_command": f"{context.text_trigger_prefix} <需求描述>",
            "entry_variants": [
                {
                    "surface": "default",
                    "label": "Trae SOLOCN",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "workspace-natural-language",
                    "priority": "preferred",
                    "notes": "最稳定的默认入口。",
                },
                {
                    "surface": "competition",
                    "label": "Trae SOLOCN SEEAI",
                    "entry": f"{context.seeai_text_trigger_prefix} <需求描述>",
                    "mode": "workspace-natural-language",
                    "priority": "preferred",
                    "notes": "比赛半小时极速版入口。",
                },
                {
                    "surface": "builtin",
                    "label": "Trae SOLOCN Built-ins",
                    "entry": "/plan · /spec",
                    "mode": "builtin-mtc-code",
                    "priority": "context",
                    "notes": "宿主原生结构化入口，会与 Super Dev 的 baseline / docs / spec 治理层协同。",
                },
            ],
            "trigger_context": "Trae SOLOCN 当前 workspace / task session",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": True,
            "post_onboard_steps": [
                "确认 `.trae/rules/super-dev.md`、`.trae/skills/super-dev/SKILL.md` 与 `~/.trae-cn/skills/super-dev/SKILL.md` 已同步。",
                "优先在当前工作区输入 `super-dev: <需求描述>`；不要先脱离当前任务再重开题。",
                "如果宿主正在使用 `/plan` 或 `/spec`，让它们与 Super Dev 的 baseline / 文档确认链协同，而不是两套流程互相覆盖。",
                "恢复时优先续跑当前工作区和当前任务，不要重新进入新会话重做 baseline。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "Trae SOLOCN 当前最佳接入面是 `.trae/rules + .trae/skills + ~/.trae-cn/skills`，并与宿主内建的 MTC / Code 双模式、`/plan`、`/spec` 协同工作。Super Dev 负责项目交付治理与阶段门禁，宿主内建结构化功能负责执行体验增强。",
            "runtime_validation": _runtime_validation_payload(self),
        }


@dataclass(frozen=True, slots=True)
class _WorkBuddyAdapter(HostSpecialAdapter):
    def build_usage_profile(self, context: SpecialAdapterContext) -> dict[str, object]:
        return {
            "usage_mode": "manual-workbench-skill",
            "primary_entry": "在 WorkBuddy 当前任务/对话会话中输入 `super-dev: <需求描述>`；比赛模式使用 `super-dev-seeai: <需求描述>`。接入方式为手动启用 Skills，而不是自动写项目规则文件。",
            "trigger_command": f"{context.text_trigger_prefix} <需求描述>",
            "entry_variants": [
                {
                    "surface": "default",
                    "label": "WorkBuddy",
                    "entry": f"{context.text_trigger_prefix} <需求描述>",
                    "mode": "manual-skill-natural-language",
                    "priority": "preferred",
                    "notes": "标准 Super Dev 入口。",
                },
                {
                    "surface": "competition",
                    "label": "WorkBuddy SEEAI",
                    "entry": f"{context.seeai_text_trigger_prefix} <需求描述>",
                    "mode": "manual-skill-natural-language",
                    "priority": "preferred",
                    "notes": "比赛半小时极速版入口。",
                },
            ],
            "trigger_context": "WorkBuddy 当前任务/对话会话",
            "usage_location": context.usage_location,
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "在 WorkBuddy 中确认当前任务会话绑定了目标项目目录或授权文件夹。",
                "手动启用 Super Dev 标准版与 SEEAI 比赛版 Skills。",
                "在同一个任务会话里输入 `super-dev: <需求描述>` 或 `super-dev-seeai: <需求描述>`。",
            ],
            "usage_notes": list(context.usage_notes),
            "notes": "WorkBuddy 当前按手动接入宿主建模：宿主负责自然语言任务、自主执行、本地文件操作和 Skills/MCP；Super Dev 负责标准流程与 SEEAI 比赛合同。",
            "runtime_validation": _runtime_validation_payload(self),
        }


HOST_SPECIAL_ADAPTERS: dict[str, HostSpecialAdapter] = {
    "codebuddy-cli": _CodeBuddyCliAdapter(
        host_id="codebuddy-cli",
        install_surfaces={
            "official_project_surfaces": (
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev.md",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/commands/super-dev-seeai.md",
                ".codebuddy/skills/super-dev/SKILL.md",
                ".codebuddy/skills/super-dev-seeai/SKILL.md",
                ".codebuddy/agents/super-dev.md",
            ),
            "official_user_surfaces": (
                "~/.codebuddy/skills/super-dev/SKILL.md",
                "~/.codebuddy/skills/super-dev-seeai/SKILL.md",
            ),
            "optional_user_surfaces": (
                "~/.codebuddy/CODEBUDDY.md",
                "~/.codebuddy/rules/super-dev.md",
                "~/.codebuddy/commands/super-dev.md",
                "~/.codebuddy/commands/super-dev-seeai.md",
                "~/.codebuddy/agents/super-dev.md",
            ),
            "observed_compatibility_surfaces": (".codebuddy/AGENTS.md",),
        },
        runtime_checklist=(
            "确认当前 CodeBuddy CLI 会话就在目标项目目录中，再触发 `/super-dev`。",
            "确认项目级 `.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/`、`.codebuddy/agents/` 与兼容 `AGENTS.md` 都被当前会话加载。",
            "确认文档返工与确认门阶段仍然保持在 Super Dev 流程内。",
            "比赛模式验收时，确认 `/super-dev-seeai` 或 `super-dev-seeai:` 会进入半小时时间盒，而不是回到标准长链路。",
            "确认比赛模式会按 P0/P1/P2 控制范围，优先保住主演示路径，再补 wow 点。",
            "确认 SEEAI 会在 12 分钟内先跑出第一个可见、可点击、可截图的界面，而不是卡在初始化或配置阶段。",
        ),
        pass_criteria=(
            "CodeBuddy CLI 真实读取了项目级 rules、commands、skills、subagents 与兼容规则面。",
            "CodeBuddy CLI 的 SEEAI 入口会进入 compact docs + compact spec + full-stack sprint 的比赛合同。",
            "CodeBuddy CLI 的 SEEAI 模式在初始化失败一次后会切到更轻的回退栈，而不是继续死磕重配置方案。",
        ),
        resume_checklist=(
            "CodeBuddy CLI 恢复时要确认仍在目标项目目录，并重新加载 `.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/` 与 `.codebuddy/agents/`。",
            "若正在 SEEAI 比赛模式中恢复，确认继续语句仍回到当前比赛合同，而不是重新开题。",
        ),
        competition_smoke_extra_steps=(
            "确认宿主首轮先给出作品类型、wow 点、P0 主路径和主动放弃项，再声明 30 分钟比赛链路与 P0/P1/P2 取舍。",
            "确认宿主首轮同时承诺 12 分钟内先跑出首个可见界面，并在初始化失败时立即切轻量回退栈。",
        ),
        flow_probe={
            "enabled": True,
            "title": "CodeBuddy 标准流 / SEEAI 双模式验收",
            "summary": "分别验证标准入口和 SEEAI 入口，确认 CodeBuddy CLI 会按不同合同执行，但都持续留在 Super Dev 流程内。",
            "steps": (
                "先用 `/super-dev` 触发一次，确认首轮进入标准 Super Dev research，而不是直接编码。",
                "再用 `/super-dev-seeai` 或 `super-dev-seeai:` 触发一次，确认进入 30 分钟比赛链路，而不是标准 preview gate 流程。",
                "在 SEEAI 会话里继续说“继续改 / 再炫一点 / 补一个功能”，确认仍留在当前比赛冲刺，不会退回普通聊天。",
                "确认 Slash 如果刷新较慢，回退到 `super-dev-seeai:` 仍会进入同一条 SEEAI 比赛合同。",
                "确认 SEEAI 不会长时间卡在初始化；若原技术栈起不来，会主动降级到更轻的回退栈并保住主演示路径。",
            ),
            "success_signal": "CodeBuddy CLI 的标准入口和 SEEAI 入口都能稳定进入对应合同，并在多轮修改、确认和恢复时保持流程连续。",
        },
    ),
    "codebuddy": _CodeBuddyIdeAdapter(
        host_id="codebuddy",
        install_surfaces={
            "official_project_surfaces": (
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev/RULE.mdc",
                ".codebuddy/skills/super-dev/SKILL.md",
                ".codebuddy/skills/super-dev-seeai/SKILL.md",
            ),
            "official_user_surfaces": (
                "~/.codebuddy/skills/super-dev/SKILL.md",
                "~/.codebuddy/skills/super-dev-seeai/SKILL.md",
            ),
            "optional_project_surfaces": (
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/commands/super-dev-seeai.md",
                ".codebuddy/agents/super-dev.md",
            ),
            "optional_user_surfaces": (
                "~/.codebuddy/CODEBUDDY.md",
                "~/.codebuddy/commands/super-dev.md",
                "~/.codebuddy/commands/super-dev-seeai.md",
                "~/.codebuddy/agents/super-dev.md",
            ),
            "observed_compatibility_surfaces": (".codebuddy/rules.md", ".codebuddy/AGENTS.md"),
        },
        runtime_checklist=(
            "确认当前 CodeBuddy Agent Chat 绑定的是目标项目，而不是其他工作区。",
            "确认 `CODEBUDDY.md`、`.codebuddy/rules/` 与 `.codebuddy/skills/` 已在当前会话真实生效；`.codebuddy/commands/`、`.codebuddy/agents/` 只按增强层核对。",
            "确认用户继续说“改一下 / 补充 / 继续改”时，CodeBuddy 仍然停留在当前确认门内。",
            "比赛模式验收时，确认 `/super-dev-seeai` 或 `super-dev-seeai:` 进入的是 30 分钟比赛链路，而不是标准 preview gate 流程。",
            "确认比赛模式下固定同一个 Agent Chat 仍能持续沿用当前上下文，不因子会话切换而丢失范围控制。",
            "确认 SEEAI 会在 12 分钟内先跑出第一个可见、可点击、可截图的界面，而不是停留在初始化阶段。",
        ),
        pass_criteria=(
            "CodeBuddy 在目标工作区真实读取了 CODEBUDDY.md、rules 与 skills；如启用了 commands / agents，也要确认增强面生效。",
            "CodeBuddy 的 SEEAI 入口会保留 compact 文档确认门，并在 Spec 后直接进入一体化快速开发。",
            "CodeBuddy 的 SEEAI 模式在初始化失败一次后会主动切到更轻的回退栈，优先保住主路径。",
        ),
        resume_checklist=(
            "CodeBuddy 恢复时要确认 Agent Chat 仍在目标项目，并继续当前确认门而不是重新开题。",
            "若当前是 SEEAI 比赛模式，恢复后仍应保持在同一个比赛冲刺会话里，而不是切回标准模式。",
        ),
        competition_smoke_extra_steps=(
            "确认宿主首轮先给出作品类型、wow 点、P0 主路径和主动放弃项，再声明 30 分钟比赛链路与 P0/P1/P2 取舍。",
            "确认宿主首轮同时承诺 12 分钟内先跑出首个可见界面，并在初始化失败时立即切轻量回退栈。",
        ),
        flow_probe={
            "enabled": True,
            "title": "CodeBuddy 标准流 / SEEAI 双模式验收",
            "summary": "分别验证标准入口和 SEEAI 入口，确认 CodeBuddy 会按不同合同执行，但都持续留在 Super Dev 流程内。",
            "steps": (
                "先用 `/super-dev` 触发一次，确认首轮进入标准 Super Dev research，而不是直接编码。",
                "再用 `/super-dev-seeai` 或 `super-dev-seeai:` 触发一次，确认进入 30 分钟比赛链路，而不是标准 preview gate 流程。",
                "在 SEEAI 会话里继续说“继续改 / 再炫一点 / 补一个功能”，确认仍留在当前比赛冲刺，不会退回普通聊天。",
                "确认 Slash 如果刷新较慢，回退到 `super-dev-seeai:` 仍会进入同一条 SEEAI 比赛合同。",
                "确认 SEEAI 不会长时间卡在初始化；若原技术栈起不来，会主动降级到更轻的回退栈并保住主演示路径。",
            ),
            "success_signal": "CodeBuddy 的标准入口和 SEEAI 入口都能稳定进入对应合同，并在多轮修改、确认和恢复时保持流程连续。",
        },
    ),
    "droid-cli": _DroidCliAdapter(
        host_id="droid-cli",
        install_surfaces={
            "official_project_surfaces": (
                "AGENTS.md",
                ".factory/rules/super-dev.md",
                ".factory/skills/super-dev/SKILL.md",
                ".factory/skills/super-dev-seeai/SKILL.md",
                ".factory/commands/super-dev.md",
                ".factory/commands/super-dev-seeai.md",
            ),
            "official_user_surfaces": (
                "~/.factory/skills/super-dev/SKILL.md",
                "~/.factory/skills/super-dev-seeai/SKILL.md",
            ),
            "optional_user_surfaces": (
                "~/.factory/AGENTS.md",
                "~/.factory/commands/super-dev.md",
                "~/.factory/commands/super-dev-seeai.md",
            ),
            "observed_compatibility_surfaces": (),
        },
        runtime_checklist=(
            "确认当前 Droid CLI 会话就在目标项目目录中，并已读取项目根 `AGENTS.md`。",
            "确认 `.factory/rules/` 与 `.factory/skills/` 已在当前会话可见；`.factory/commands/` 只作为 legacy slash compatibility 一起保留。",
            "确认 `/super-dev` 与 `/super-dev-seeai` 都能在当前会话中触发，而不是退回普通聊天。",
            "确认 SEEAI 会在 12 分钟内先跑出第一个可见界面；如果原方案初始化失败，会立刻切更轻的回退栈。",
        ),
        pass_criteria=(
            "Droid CLI 在目标项目中真实读取了 `AGENTS.md + .factory/rules + .factory/skills`，并保留 `.factory/commands` 作为 legacy slash compatibility，且标准模式与 SEEAI 模式都进入同一条 Super Dev 合同体系。",
            "Droid CLI 的 SEEAI 入口会保留 compact 文档确认门，并在 Spec 后直接进入一体化快速开发与最终 polish。",
            "Droid CLI 在 session 恢复后仍能沿用同一条流程，而不是重新开题。",
        ),
        resume_checklist=(
            "Droid CLI 恢复时要确认当前 session 仍绑定目标项目，并在需要时使用 `droid exec --session-id <id>` 继续。",
            "若当前处于 SEEAI 比赛模式，恢复后仍应回到当前比赛冲刺，而不是重新开始普通流水线。",
        ),
        competition_smoke_extra_steps=(
            "确认宿主首轮先给出作品类型、wow 点、P0 主路径和主动放弃项，再进入 compact 文档。",
            "确认宿主首轮同时承诺 12 分钟内先跑出首个可见界面，并在初始化失败时立即切轻量回退栈。",
        ),
        flow_probe={
            "enabled": True,
            "title": "Droid CLI 标准流 / SEEAI 验收",
            "summary": "验证 Droid CLI 在同一个项目 session 中能稳定运行标准入口和 SEEAI 比赛入口。",
            "steps": (
                "先用 `/super-dev` 触发一次，确认进入标准 Super Dev research，而不是直接编码。",
                "再用 `/super-dev-seeai` 或 `super-dev-seeai:` 触发一次，确认进入 30 分钟比赛链路，并保留 compact docs confirm gate。",
                "在 SEEAI 模式里继续说“继续做 / 做最终 polish / 补一个 wow 点”，确认 Droid 不会切回普通聊天或重新开题。",
                "确认如需 headless 恢复，可通过 `droid exec --session-id <id> \"continue with next steps\"` 继续当前冲刺。",
                "确认 SEEAI 不会卡在初始化；若当前栈起不来，会主动降级到更轻的回退栈并继续交付主路径。",
            ),
            "success_signal": "Droid CLI 的标准入口和 SEEAI 入口都能在当前项目 session 里稳定进入对应 Super Dev 合同，并保持比赛冲刺连续性。",
        },
    ),
    "kimi-code": _KimiCodeAdapter(
        host_id="kimi-code",
        install_surfaces={
            "official_project_surfaces": ("AGENTS.md",),
            "official_user_surfaces": (),
            "optional_project_surfaces": (".kimi/skills/super-dev/SKILL.md",),
            "optional_user_surfaces": (
                "~/.kimi/skills/super-dev/SKILL.md",
                "~/.config/agents/skills/super-dev/SKILL.md",
                "~/.agents/skills/super-dev/SKILL.md",
            ),
            "observed_compatibility_surfaces": (".kimi/AGENTS.md",),
        },
        runtime_checklist=(
            "确认当前 Kimi Code 会话就在目标项目目录中，并已读取项目根 `AGENTS.md`。",
            "如果当前项目启用了 `.kimi/skills/` 或用户级 skill 目录，把它视为当前增强面并验证其确实生效。",
            "如果项目里额外写入了 `.kimi/AGENTS.md`，把它视为兼容增强面，而不是官方必需面。",
            "确认 `/skill:super-dev` 是默认显式入口；如需结构化流程，`/flow:super-dev` 也能把会话拉进同一条 Super Dev 流程。",
            "确认中断恢复时，`kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume` 能继续当前流程而不是重新开题。",
        ),
        pass_criteria=(
            "Kimi Code 在目标项目会话中真实读取了 `AGENTS.md`，并且 `/skill:` / `/flow:` 至少一条官方入口链可稳定工作。",
            "若当前项目启用了 `.kimi/skills` 或用户级 skill 目录，这些增强面也已在真实会话里被验证可用。",
            "Kimi Code 的官方 `/skill:` 入口与可选 `/flow:` 入口都能稳定进入同一条 Super Dev 合同，自然语言入口仅作为回退面。",
            "Kimi Code 的 continue / resume 不会绕过当前 gate，而是继续当前阶段。",
        ),
        resume_checklist=(
            "恢复时优先使用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，并确认当前 session 仍绑定目标项目。",
            "若当前已卡在 docs_confirm / preview_confirm / baseline confirmation，恢复后必须先回到对应 gate。",
        ),
    ),
    "trae-solo": _TraeSoloAdapter(
        host_id="trae-solo",
        install_surfaces={
            "official_project_surfaces": (
                "AGENTS.md",
                ".trae/rules/super-dev.md",
                ".trae/commands/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ),
            "official_user_surfaces": (),
            "observed_compatibility_surfaces": ("~/.trae/skills/super-dev/SKILL.md",),
        },
        runtime_checklist=(
            "确认 Trae SOLO 当前 workspace 绑定的是目标项目，而不是其他工作区。",
            "确认 `.trae/rules/`、`.trae/commands/` 与 `.trae/skills/` 已在当前 workspace 一起生效。",
            "确认 `/super-dev` 与 `/super-dev-seeai` 能进入对应 Super Dev 合同，而不是退回普通聊天。",
            "确认 desktop/web continuity 恢复后仍沿用当前流程状态，不会重新开题。",
        ),
        pass_criteria=(
            "Trae SOLO 在当前 workspace 中真实读取了 rules、commands 与 skills。",
            "Trae SOLO 的 slash 入口和自然语言回退入口都能进入同一条 Super Dev 流程。",
            "Trae SOLO 的 continuity 恢复不会绕过当前 gate。",
        ),
        resume_checklist=(
            "恢复时优先沿用当前 workspace continuity，不要重新新建工作区或会话。",
            "如果当前卡在 docs_confirm / preview_confirm / baseline confirmation，恢复后必须先回到对应 gate。",
        ),
    ),
    "trae-solocn": _TraeSoloCnAdapter(
        host_id="trae-solocn",
        install_surfaces={
            "official_project_surfaces": (
                ".trae/rules/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ),
            "official_user_surfaces": ("~/.trae-cn/skills/super-dev/SKILL.md",),
            "observed_compatibility_surfaces": (),
        },
        runtime_checklist=(
            "确认 Trae SOLOCN 当前工作区绑定的是目标项目，而不是其他目录。",
            "确认 `.trae/skills/` 与 `~/.trae-cn/skills/` 已在当前工作区生效。",
            "确认 `super-dev:` 默认入口能稳定把会话拉进 Super Dev，而不会和宿主内建 `/plan`、`/spec` 冲突。",
            "确认恢复时仍沿用当前任务进度与当前模式，而不是重新开题。",
        ),
        pass_criteria=(
            "Trae SOLOCN 在当前工作区真实读取了 `.trae/skills` 与 `~/.trae-cn/skills`。",
            "Trae SOLOCN 的默认自然语言入口能与宿主内建 `/plan` / `/spec` 协同工作。",
            "Trae SOLOCN 的恢复不会绕过当前 Super Dev gate。",
        ),
        resume_checklist=(
            "恢复时优先沿用当前工作区和当前任务，不要重新启动新的工作流分支。",
            "如果当前已进入 baseline / docs_confirm / preview_confirm，恢复后先回到对应 gate。",
        ),
    ),
    "workbuddy": _WorkBuddyAdapter(
        host_id="workbuddy",
        adapter_mode_override="skill-only",
        install_surfaces={
            "official_project_surfaces": (),
            "official_user_surfaces": (),
            "optional_user_surfaces": ("~/.workbuddy/skills/super-dev/SKILL.md",),
            "observed_compatibility_surfaces": (),
        },
        runtime_checklist=(
            "确认任务会话已经手动启用 Super Dev 标准版与 SEEAI 比赛版 Skills。",
            "确认自然语言入口可用且保持当前项目上下文。",
            "确认恢复后仍继续同一个 task/chat，而不是跳转成新任务。",
            "确认 SEEAI 会在 12 分钟内先跑出第一个可见界面；如果原方案起不来，会直接改走更轻的回退栈。",
        ),
        pass_criteria=(
            "手动启用的 Skills 可稳定接管标准流程与 SEEAI 比赛流程。",
            "自然语言入口可在当前会话中直接触发。",
            "恢复会话后仍可继续同一作品任务。",
            "SEEAI 比赛模式不会长时间卡在初始化或配置阶段，而会主动降级方案保住演示闭环。",
        ),
        resume_checklist=(
            "检查当前任务是否已经锁定作品类型。",
            "检查 compact docs 或 spec 是否已写入。",
            "检查是否需要继续当前比赛 sprint。",
        ),
        competition_smoke_extra_steps=(
            "确认 WorkBuddy 首轮先给出作品类型、wow 点、P0 主路径和主动放弃项，再进入 fast research 与 compact 文档。",
            "确认 WorkBuddy 首轮同时承诺 12 分钟内先跑出首个可见界面，并在初始化失败时立即切轻量回退栈。",
        ),
        manual_install_guidance=ManualInstallGuidance(
            title="WorkBuddy 手动安装",
            border_style="yellow",
            plain_fallback="请直接在 WorkBuddy 内手动启用 Super Dev 标准版与 SEEAI 比赛版 Skills。",
            lines=(
                "WorkBuddy 不走 `super-dev {command_name}` 统一接入流。",
                "请直接在 WorkBuddy 的技能市场/技能导入能力中手动启用：",
                "",
                "`Super Dev`（标准流程）",
                "`Super Dev SEEAI`（比赛模式）",
                "",
                "启用完成后，在 WorkBuddy 当前任务会话里触发：`super-dev:`；比赛模式使用 `super-dev-seeai:`。",
                "{extra_doctor}",
            ),
        ),
    ),
}


def get_special_adapter(host_id: str) -> HostSpecialAdapter | None:
    return HOST_SPECIAL_ADAPTERS.get(host_id)


def build_special_usage_profile(context: SpecialAdapterContext) -> dict[str, object] | None:
    adapter = get_special_adapter(context.target)
    if adapter is None:
        return None
    return adapter.build_usage_profile(context)


def get_special_install_surfaces(host_id: str) -> dict[str, list[str]] | None:
    adapter = get_special_adapter(host_id)
    if adapter is None or not adapter.install_surfaces:
        return None
    return {key: list(value) for key, value in adapter.install_surfaces.items()}


def get_competition_smoke_extra_steps(host_id: str) -> tuple[str, ...]:
    adapter = get_special_adapter(host_id)
    if adapter is None:
        return ()
    return adapter.competition_smoke_extra_steps


def get_runtime_checklist(host_id: str) -> tuple[str, ...]:
    adapter = get_special_adapter(host_id)
    if adapter is None:
        return ()
    return adapter.runtime_checklist


def get_pass_criteria(host_id: str) -> tuple[str, ...]:
    adapter = get_special_adapter(host_id)
    if adapter is None:
        return ()
    return adapter.pass_criteria


def get_resume_checklist(host_id: str) -> tuple[str, ...]:
    adapter = get_special_adapter(host_id)
    if adapter is None:
        return ()
    return adapter.resume_checklist


def get_special_flow_probe(host_id: str) -> dict[str, Any] | None:
    adapter = get_special_adapter(host_id)
    if adapter is None or not adapter.flow_probe:
        return None
    return dict(adapter.flow_probe)


def render_manual_install_guidance(
    *,
    host_id: str,
    command_name: str,
    docs: list[str] | tuple[str, ...],
) -> dict[str, Any] | None:
    adapter = get_special_adapter(host_id)
    guidance = adapter.manual_install_guidance if adapter is not None else None
    if guidance is None:
        return None

    extra_doctor = (
        f"如需让维护者核对接入说明，可再执行 `super-dev doctor --host {host_id}`。"
        if command_name != "doctor"
        else ""
    )
    lines: list[str] = []
    for line in guidance.lines:
        rendered = line.format(command_name=command_name, extra_doctor=extra_doctor).strip()
        if rendered or not line:
            lines.append(rendered)
    while lines and not lines[-1]:
        lines.pop()
    if docs:
        lines.append("")
        lines.append("官方文档:")
        for url in docs[:2]:
            lines.append(f"- {url}")
    return {
        "title": guidance.title,
        "lines": lines,
        "border_style": guidance.border_style,
        "plain_fallback": guidance.plain_fallback,
    }


def get_adapter_mode_override(host_id: str) -> str:
    adapter = get_special_adapter(host_id)
    if adapter is None:
        return ""
    return adapter.adapter_mode_override


__all__ = [
    "HostSpecialAdapter",
    "ManualInstallGuidance",
    "SpecialAdapterContext",
    "build_special_usage_profile",
    "get_adapter_mode_override",
    "get_competition_smoke_extra_steps",
    "get_pass_criteria",
    "get_resume_checklist",
    "get_special_adapter",
    "get_special_flow_probe",
    "get_special_install_surfaces",
    "get_runtime_checklist",
    "render_manual_install_guidance",
]
