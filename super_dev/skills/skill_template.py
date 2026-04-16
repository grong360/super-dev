"""
Skill Template Engine — unified skill rendering with host-specific frontmatter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..seeai_design_system import (
    SEEAI_ARCHETYPE_DETECTION_HINTS,
    SEEAI_COMPACT_DOC_SECTIONS,
    SEEAI_COMPLEXITY_PATTERNS,
    SEEAI_COMPLEXITY_REDUCTION_RULES,
    SEEAI_EXECUTION_GUARDRAILS,
    SEEAI_FAILURE_PROTOCOL,
    SEEAI_FIRST_RESPONSE_TEMPLATE,
    SEEAI_JUDGE_CHECKLIST,
    SEEAI_MODULE_TRUTH_RULES,
    SEEAI_QUALITY_FLOOR,
    SEEAI_RESEARCH_PRIORITIES,
    SEEAI_SEARCH_QUERIES,
    get_seeai_archetype_playbooks,
    get_seeai_design_packs,
)

SUPER_DEV_VERSION = "2.3.9"
SEEAI_SKILL_NAME = "super-dev-seeai"


@dataclass
class SkillFrontmatter:
    """标准化 skill frontmatter 字段。"""

    name: str = "super-dev"
    description: str = (
        "Super Dev pipeline governance for research-first," " commercial-grade AI coding delivery"
    )
    when_to_use: str = (
        "Use when the user says /super-dev, super-dev:, or super-dev："
        " followed by a requirement. Activate the Super Dev pipeline"
        " for research-first, commercial-grade project delivery."
    )
    allowed_tools: list[str] = field(default_factory=lambda: ["Read", "Edit", "Write", "Bash"])
    model: str | None = None
    effort: str | None = None
    context: str | None = None
    user_invocable: bool = True
    version: str = SUPER_DEV_VERSION
    paths: list[str] | None = None
    argument_hint: str | None = "requirement description"
    arguments: list[str] | None = None
    disable_model_invocation: bool = False

    def to_yaml_lines(self, host: str) -> list[str]:
        """Render frontmatter fields as YAML lines (without delimiters)."""
        lines: list[str] = []
        lines.append(f"name: {self.name}")
        lines.append(f"description: {self.description}")

        if host == "claude-code":
            lines.append(f"when-to-use: {self.when_to_use}")
            if self.allowed_tools:
                tools_str = ", ".join(self.allowed_tools)
                lines.append(f"allowed-tools: {tools_str}")
            if self.model:
                lines.append(f"model: {self.model}")
            if self.effort:
                lines.append(f"effort: {self.effort}")
            if self.context:
                lines.append(f"context: {self.context}")
            lines.append(f"user-invocable: {str(self.user_invocable).lower()}")
            lines.append(f"version: {self.version}")
            if self.paths:
                lines.append("paths:")
                for p in self.paths:
                    lines.append(f"  - {p}")
            if self.argument_hint:
                lines.append(f"argument-hint: {self.argument_hint}")
            if self.arguments:
                lines.append("arguments:")
                for a in self.arguments:
                    lines.append(f"  - {a}")
            if self.disable_model_invocation:
                lines.append("disable-model-invocation: true")
            # Runtime enforcement hook: block emoji in UI source files
            lines.append("hooks:")
            lines.append("  PreToolUse:")
            lines.append('    - matcher: "Write|Edit"')
            lines.append("      hooks:")
            lines.append("        - type: command")
            lines.append(
                '          command: "python3 -c \\"'
                "import sys,re,json;"
                "d=json.loads(sys.stdin.read());"
                "c=d.get('tool_input',{}).get('content','')or d.get('tool_input',{}).get('new_string','')or'';"
                "p=d.get('tool_input',{}).get('file_path','');"
                "e=p.rsplit('.',1)[-1]if '.' in p else'';"
                "print(json.dumps({'decision':'block','reason':'Super Dev: emoji detected in '+e+' file, use icon library'}"
                "if e in('tsx','ts','jsx','js','vue','svelte')and bool(re.search(r'[\\\\u2600-\\\\u27BF\\\\U0001F300-\\\\U0001FAFF]',c))else{}))"
                '\\""'
            )
            lines.append("          timeout: 5")
        elif host == "codex-cli":
            lines.append(f"when_to_use: {self.when_to_use}")
            lines.append(f"version: {self.version}")
        else:
            # Generic format — underscore keys
            lines.append(f"when_to_use: {self.when_to_use}")
            if self.allowed_tools:
                tools_str = ", ".join(self.allowed_tools)
                lines.append(f"allowed_tools: {tools_str}")
            if self.model:
                lines.append(f"model: {self.model}")
            if self.effort:
                lines.append(f"effort: {self.effort}")
            if self.context:
                lines.append(f"context: {self.context}")
            lines.append(f"user_invocable: {str(self.user_invocable).lower()}")
            lines.append(f"version: {self.version}")
            if self.paths:
                lines.append("paths:")
                for p in self.paths:
                    lines.append(f"  - {p}")
            if self.argument_hint:
                lines.append(f"argument_hint: {self.argument_hint}")
            if self.arguments:
                lines.append("arguments:")
                for a in self.arguments:
                    lines.append(f"  - {a}")
            if self.disable_model_invocation:
                lines.append("disable_model_invocation: true")

        return lines


class SuperDevSkillContent:
    """Generates the body content for a Super Dev skill file."""

    def __init__(self, skill_name: str, host: str) -> None:
        self.skill_name = skill_name
        self.host = host

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    def render_body(self) -> str:
        """Return the full Markdown body (everything below the frontmatter)."""
        if self.skill_name == SEEAI_SKILL_NAME:
            if self.host == "codex-cli":
                return self._render_seeai_codex_body()
            return self._render_seeai_generic_body()
        if self.host == "codex-cli":
            return self._render_codex_body()
        return self._render_generic_body()

    # ------------------------------------------------------------------
    # Codex CLI body
    # ------------------------------------------------------------------

    def _render_codex_body(self) -> str:
        sections = [
            f"# {self.skill_name} for Codex CLI",
            self._section_critical_reminders(),
            self._section_activation_rules_codex(),
            self._section_trigger_codex(),
            self._section_runtime_contract_codex(),
            self._section_cli_command_guide(),
            self._section_first_response_contract(),
            self._section_knowledge_contract(),
            self._section_pre_code_gate(),
            self._section_session_continuity(),
            self._section_implementation_closure(),
            self._section_phase_enforcement(),
            self._section_required_behavior_codex(),
            self._section_never_do(),
            self._section_common_mistakes(),
            self._section_error_recovery(),
            self._section_agent_teams(),
            self._section_flow_contract(),
        ]
        return "\n\n".join(sections) + "\n"

    def _render_seeai_codex_body(self) -> str:
        sections = [
            "# Super Dev SEEAI - 赛事极速版 (Codex)",
            self._section_critical_reminders(),
            self._section_seeai_activation_rules_codex(),
            self._section_seeai_trigger_codex(),
            self._section_seeai_runtime_contract_codex(),
            self._section_seeai_first_response_contract(),
            self._section_seeai_first_response_template(),
            self._section_seeai_research_protocol(),
            self._section_seeai_compact_doc_template(),
            self._section_seeai_design_system(),
            self._section_seeai_execution_guardrails(),
            self._section_seeai_complexity_reduction(),
            self._section_seeai_tech_stack_matrix(),
            self._section_seeai_game_templates(),
            self._section_seeai_page_templates(),
            self._section_seeai_competition_doc_templates(),
            self._section_seeai_project_archetypes(),
            self._section_seeai_archetype_detection_hints(),
            self._section_seeai_quality_floor(),
            self._section_seeai_competition_tools(),
            self._section_seeai_required_behavior_codex(),
            self._section_seeai_session_continuity(),
            self._section_implementation_closure(),
            self._section_seeai_never_do(),
            self._section_seeai_flow_contract(),
        ]
        return "\n\n".join(sections) + "\n"

    def _section_activation_rules_codex(self) -> str:
        return (
            "## Direct Activation Rule（强制）\n"
            "\n"
            "- If this skill is invoked, Super Dev pipeline mode is already active.\n"
            "- Do not spend a turn saying you will read the skill first,"
            " explain the skill, or decide whether to enter the workflow.\n"
            '- Do not answer with variants of "我先读取 skill 再判断流程".\n'
            "- If this file is loaded from `~/.codex/skills`,"
            " treat it as the compatibility mirror of the same Super Dev contract."
        )

    def _section_trigger_codex(self) -> str:
        return (
            "## 触发方式（强制）\n"
            "\n"
            "- Treat `super-dev: <需求描述>` and `super-dev：<需求描述>`"
            " as the AGENTS-driven natural-language fallback entry point.\n"
            "- Treat `$super-dev` as the explicit official Skill mention"
            " when the Codex host exposes skills by name.\n"
            "- In Codex desktop/app, if the slash list shows this enabled skill,"
            " selecting `/super-dev` from that list is valid because it resolves"
            " to this Skill rather than a custom project slash command.\n"
            "- Do not treat it as ordinary chat.\n"
            "- 当前宿主负责调用模型、工具、终端与实际代码修改。\n"
            "- Super Dev 不是大模型平台，也不提供自己的代码生成 API。"
        )

    def _section_seeai_activation_rules_codex(self) -> str:
        return (
            "## Direct Activation Rule（强制）\n"
            "\n"
            "- If this skill is invoked, Super Dev SEEAI competition mode is already active.\n"
            "- Do not spend a turn explaining the skill or deciding whether to enter the workflow.\n"
            "- Treat this as a distinct fast-delivery contract optimized for time-boxed competition work.\n"
            "- Keep quality, but compress the path aggressively after Spec.\n"
        )

    def _section_seeai_trigger_codex(self) -> str:
        return (
            "## 触发方式（强制）\n"
            "\n"
            "- Treat `super-dev-seeai: <需求描述>` and `super-dev-seeai：<需求描述>` as the AGENTS-driven natural-language SEEAI entry.\n"
            "- Treat `$super-dev-seeai` as the explicit Codex CLI Skill entry for the competition mode.\n"
            "- In Codex App/Desktop, selecting `/super-dev-seeai` from the slash Skill list is the official app entry.\n"
            "- Do not route SEEAI requests back to ordinary chat or to the full standard Super Dev contract.\n"
        )

    def _section_seeai_runtime_contract_codex(self) -> str:
        return (
            "## Runtime Contract（强制）\n"
            "\n"
            "- Super Dev SEEAI is still Super Dev governance, but with a competition-fast contract.\n"
            "- The host remains responsible for model execution, tools, search, terminal, and edits.\n"
            "- Use Codex native web/search/edit/terminal capabilities for research, building, and validation.\n"
            "- Keep local `super-dev` CLI for governance artifacts only when it materially helps the fast path.\n"
            "- The mode is designed for 30-minute showcase builds such as a polished landing page, mini-game, or focused demo tool.\n"
            "- Default decision rule: protect one demo path first, one wow point second, and only then add extra engineering depth.\n"
        )

    def _section_runtime_contract_codex(self) -> str:
        return (
            "## Runtime Contract（强制）\n"
            "\n"
            "- Super Dev 由两部分组成：\n"
            "  1. 当前项目内的本地 Python CLI 工具\n"
            "  2. 当前宿主里的规则/Skill/命令映射\n"
            "- 当前宿主负责调用模型、联网、终端、编辑器与实际代码修改。\n"
            "- 当用户通过 Codex App/Desktop 的 `/super-dev` skill 入口、"
            "Codex CLI 的 `$super-dev`，或 `super-dev: ...` / `super-dev：...`"
            " 回退入口触发时，都意味着你必须进入 Super Dev 流水线。\n"
            "- 需要研究、设计、编码、运行、调试时，"
            "优先使用 Codex 自身的 web/search/terminal/edit 能力。\n"
            "- 需要做治理动作时，才使用本地 `super-dev` CLI。"
        )

    def _section_required_behavior_codex(self) -> str:
        return (
            "## Required behavior\n"
            "\n"
            "1. First reply: say Super Dev pipeline mode is active"
            " and the current phase is `research`.\n"
            "2. Before the first reply, read `.super-dev/WORKFLOW.md`"
            " and `output/*-bootstrap.md` when present and treat them"
            " as the explicit bootstrap contract for this repository.\n"
            "3. Read `knowledge/` and"
            " `output/knowledge-cache/*-knowledge-bundle.json` when present.\n"
            "4. Use Codex native web/search/edit/terminal capabilities to produce:\n"
            "   - `output/*-research.md`\n"
            "   - `output/*-prd.md`\n"
            "   - `output/*-architecture.md`\n"
            "   - `output/*-uiux.md`\n"
            "5. Write the required artifacts into the repository workspace."
            " Chat-only summaries do not count as completion.\n"
            "6. Stop after the three core documents"
            " and wait for explicit confirmation.\n"
            "7. Only after confirmation, create"
            " `.super-dev/changes/*/proposal.md` and"
            " `.super-dev/changes/*/tasks.md`,"
            " then continue with frontend-first implementation.\n"
            "8. If the user says the UI is unsatisfactory, requests a redesign,"
            " or says the page looks AI-generated, first update"
            " `output/*-uiux.md`, then redo the frontend,"
            " rerun frontend runtime and UI review,"
            " and only then continue.\n"
            "9. If the user says the architecture is wrong"
            " or the technical plan must change, first update"
            " `output/*-architecture.md`, then realign Spec/tasks"
            " and implementation before continuing.\n"
            "10. If the user says quality or security is not acceptable,"
            " first fix the issues, rerun quality gate"
            " and `super-dev release proof-pack`,"
            " and only then continue."
        )

    def _section_seeai_required_behavior_codex(self) -> str:
        return (
            "## Required behavior\n"
            "\n"
            "1. First reply: say Super Dev SEEAI mode is active and the current phase is `research`.\n"
            "2. Use a strict timebox: 0-4 min research, 4-8 min compact docs, 8-10 min confirmation, 10-12 min compact Spec, 12-27 min build sprint, 27-30 min polish/handoff.\n"
            "3. Run a fast research pass and write `output/*-research.md` as a real file.\n"
            "4. Draft compact `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` in the same session and save them as real files.\n"
            "5. Scope the work in P0/P1/P2 order: P0 demo path, P1 wow point, P2 only-if-time-allows extras.\n"
            "6. Stop after the three compact core documents and wait for explicit confirmation.\n"
            "7. Only after confirmation, create a compact Spec / tasks breakdown.\n"
            "8. After Spec, move directly into an integrated full-stack build sprint: frontend first, backend if needed, then final polish.\n"
            "9. If backend or integration work threatens the schedule, degrade to mock data, local state, or a simulated high-fidelity demo path instead of missing the showcase.\n"
            "10. Do not require a separate preview confirmation gate in SEEAI mode.\n"
            "11. End with a concise demo summary, key亮点, and how to present the result quickly.\n"
            "12. When writing or refreshing `.super-dev/workflow-state.json`, persist `flow_variant = seeai` so resume/continue stays in SEEAI mode.\n"
        )

    # ------------------------------------------------------------------
    # Generic body (all other hosts)
    # ------------------------------------------------------------------

    def _render_generic_body(self) -> str:
        sections = [
            f"# {self.skill_name} - Super Dev AI Coding Skill",
            self._section_critical_reminders(),
            self._section_version_banner(),
            "---",
            self._section_role_definition(),
            self._section_positioning(),
            self._section_trigger_generic(),
            self._section_runtime_contract_generic(),
            self._section_cli_command_guide(),
            self._section_first_response_contract(),
            self._section_knowledge_contract(),
            self._section_pre_code_gate(),
            self._section_session_continuity(),
            self._section_implementation_closure(),
            self._section_phase_enforcement(),
            self._section_common_mistakes(),
            self._section_error_recovery(),
            self._section_agent_teams(),
            self._section_flow_contract(),
        ]
        return "\n\n".join(sections) + "\n"

    def _render_seeai_generic_body(self) -> str:
        sections = [
            "# Super Dev SEEAI - 赛事极速版",
            self._section_critical_reminders(),
            self._section_seeai_trigger_generic(),
            self._section_seeai_runtime_contract_generic(),
            self._section_seeai_first_response_contract(),
            self._section_seeai_first_response_template(),
            self._section_seeai_research_protocol(),
            self._section_seeai_compact_doc_template(),
            self._section_seeai_design_system(),
            self._section_seeai_execution_guardrails(),
            self._section_seeai_complexity_reduction(),
            self._section_seeai_tech_stack_matrix(),
            self._section_seeai_game_templates(),
            self._section_seeai_page_templates(),
            self._section_seeai_competition_doc_templates(),
            self._section_seeai_project_archetypes(),
            self._section_seeai_archetype_detection_hints(),
            self._section_seeai_quality_floor(),
            self._section_seeai_competition_tools(),
            self._section_seeai_session_continuity(),
            self._section_implementation_closure(),
            self._section_seeai_never_do(),
            self._section_seeai_flow_contract(),
        ]
        return "\n\n".join(sections) + "\n"

    def _section_version_banner(self) -> str:
        return (
            f"> 版本: {SUPER_DEV_VERSION} | 适用工具:"
            " Claude Code, Codex CLI, OpenCode, Cursor, Antigravity 等所有 AI Coding 工具"
        )

    def _section_role_definition(self) -> str:
        return (
            "## Skill 角色定义\n"
            "\n"
            '你是"**超级开发战队**"的一员，由 11 位专家协同完成流水线式'
            " AI Coding 交付。当用户调用 Super Dev 时，"
            "你需要根据任务类型自动切换专家角色："
        )

    def _section_positioning(self) -> str:
        return (
            "## 定位边界（强制）\n"
            "\n"
            "- 当前宿主负责调用模型、工具、终端与实际代码修改。\n"
            "- Super Dev 不是大模型平台，也不提供自己的代码生成 API。\n"
            "- 你的职责是利用宿主现有能力，严格执行 Super Dev"
            " 的流程规范、设计约束、质量门禁与交付标准。\n"
            "- 不要把 Super Dev 当作独立编码平台；"
            "真正的实现动作仍在当前宿主上下文完成。"
        )

    def _section_trigger_generic(self) -> str:
        return (
            "## 触发方式与命令路由（强制）\n"
            "\n"
            "用户只需在宿主中输入 `/super-dev <参数>`。\n"
            "宿主通过 Bash 工具自动执行对应的 CLI 命令，用户无需打开终端。\n"
            "唯一需要用户在终端手动执行的命令是 `pip install super-dev`（安装/升级）。\n"
            "\n"
            "### 路由规则\n"
            "\n"
            "**规则 1 — 已知子命令 → 用 Bash 工具执行 `super-dev <完整参数>`**\n"
            "\n"
            "已知子命令完整列表：\n"
            "```\n"
            "init, bootstrap, setup, install, start, onboard, detect, doctor, migrate,\n"
            "run, status, next, continue, resume, jump, confirm,\n"
            "review, release, quality, enforce,\n"
            "spec, task, config, policy, governance, knowledge,\n"
            "memory, hooks, experts, compact,\n"
            "analyze, repo-map, impact, regression-guard, dependency-graph,\n"
            "feature-checklist, product-audit,\n"
            "create, pipeline, fix, wizard,\n"
            "generate, design, deploy, preview, expert, metrics,\n"
            "skill, integrate, update, clean, completion, feedback\n"
            "```\n"
            "\n"
            "示例：\n"
            "- `/super-dev init` → Bash: `super-dev init`\n"
            "- `/super-dev status` → Bash: `super-dev status`\n"
            "- `/super-dev run research` → Bash: `super-dev run research`\n"
            "- `/super-dev enforce validate` → Bash: `super-dev enforce validate`\n"
            "- `/super-dev quality` → Bash: `super-dev quality`\n"
            "- `/super-dev review docs --status confirmed` → Bash: `super-dev review docs --status confirmed`\n"
            "- `/super-dev release proof-pack` → Bash: `super-dev release proof-pack`\n"
            "- `/super-dev detect --auto` → Bash: `super-dev detect --auto`\n"
            "- `/super-dev setup claude-code` → Bash: `super-dev setup claude-code`\n"
            "- `/super-dev doctor --fix` → Bash: `super-dev doctor --fix`\n"
            "\n"
            "**规则 2 — 自然语言（中文/英文描述）→ 进入 pipeline 模式**\n"
            "\n"
            "示例：\n"
            "- `/super-dev 做一个电商系统`\n"
            "- `/super-dev Build a user auth system`\n"
            "- `super-dev: 做一个电商系统`（冒号触发，等效）\n"
            "- `super-dev：做一个电商系统`（中文冒号也识别）\n"
            "\n"
            "**规则 3 — 无参数 → 运行 `super-dev` 查看当前状态并继续**"
        )

    def _section_seeai_trigger_generic(self) -> str:
        return (
            "## 触发方式与命令路由（强制）\n"
            "\n"
            "用户在宿主内使用比赛专用入口：`/super-dev-seeai <需求>` 或 `super-dev-seeai: <需求>` / `super-dev-seeai：<需求>`。\n"
            "该入口进入 Super Dev SEEAI 赛事极速版，而不是标准 Super Dev 长流程。\n"
            "\n"
            "### SEEAI 模式行为\n"
            "- 保留 research / 三文档 / docs confirm / spec。\n"
            "- 文档必须压缩成比赛短版，不走标准重治理模板。\n"
            "- Spec 确认后直接进入前后端一体化快速开发，不再拆 preview confirm。\n"
            "- 最终必须给出一个可演示、可讲解、视觉完成度够高的作品。\n"
            "- 默认目标不是“工程最完整”，而是“在评审时间内最好看、最好讲、最容易演示”。\n"
        )

    def _section_runtime_contract_generic(self) -> str:
        return (
            "## Runtime Contract（强制）\n"
            "\n"
            "- Super Dev 由两部分组成：\n"
            "  1. 当前项目内的本地 Python CLI 工具\n"
            "  2. 当前宿主里的规则/Skill/命令映射\n"
            "- 当前宿主负责调用模型、联网、终端、编辑器与实际代码修改。\n"
            "- 当用户触发 `/super-dev ...`、`super-dev: ...`"
            " 或 `super-dev：...` 时，意味着你必须进入 Super Dev 流水线。\n"
            "- 需要生成或刷新文档、Spec、质量报告、交付产物时，"
            "优先调用本地 `super-dev` CLI。\n"
            "- 需要研究、设计、编码、运行、调试时，"
            "优先使用宿主自身的 browse/search/terminal/edit 能力。\n"
            '- 不要等待用户解释"Super Dev 是什么"；'
            "你要把它理解为当前项目已经安装好的开发治理协议。"
        )

    def _section_seeai_runtime_contract_generic(self) -> str:
        return (
            "## Runtime Contract（强制）\n"
            "\n"
            "- Super Dev SEEAI 是比赛专用的快速工作版，目标是在极短时间内交付高完成度展示作品。\n"
            "- 当前宿主负责调用模型、联网、终端、编辑器与实际代码修改。\n"
            "- 需要研究、设计、编码、运行、调试时，优先使用宿主自身能力。\n"
            "- 文档与 Spec 仍然保留，但必须压缩，避免标准模式的重流程拖慢节奏。\n"
            "- 研究和文档不是为了治理完美，而是为了锁定作品类型、wow 点、实现边界和时间盒取舍。\n"
            "- 默认遵循一个简单优先级：先保住可演示主路径，再做 wow 点，最后才做额外工程深度。\n"
        )

    def _section_cli_command_guide(self) -> str:
        return (
            "## Super Dev CLI 命令速查\n"
            "\n"
            "以下所有命令均在宿主内通过 `/super-dev <command>` 输入。\n"
            "宿主会通过 Bash 工具自动执行，无需打开终端。\n"
            "\n"
            "```bash\n"
            "# 项目初始化与宿主接入\n"
            "super-dev init                          # 初始化项目配置\n"
            "super-dev detect --auto                 # 探测已安装宿主\n"
            "super-dev setup <host>                  # 一步接入指定宿主\n"
            "super-dev doctor --fix                  # 诊断并修复接入问题\n"
            "super-dev migrate                       # 迁移到最新版本\n"
            "\n"
            "# 流水线控制\n"
            "super-dev run <phase>                   # 跳转到指定阶段\n"
            "super-dev status                        # 查看当前流程状态\n"
            "super-dev next                          # 推荐下一步\n"
            "super-dev continue                      # 继续当前流程\n"
            "super-dev confirm <phase>               # 确认指定阶段\n"
            "\n"
            "# 治理与质量\n"
            "super-dev enforce install               # 安装 enforcement hooks\n"
            "super-dev enforce validate              # 运行验证检查\n"
            "super-dev quality                       # 运行质量门禁\n"
            "super-dev review docs                   # 查看三文档确认状态\n"
            "super-dev review ui                     # 查看 UI 审查状态\n"
            "super-dev review preview                # 查看预览确认状态\n"
            "\n"
            "# 交付\n"
            "super-dev release proof-pack            # 生成交付证据包\n"
            "super-dev release readiness             # 发布就绪度检查\n"
            "\n"
            "# 查询\n"
            "super-dev memory list                   # 查看记忆条目\n"
            "super-dev experts list                  # 查看专家角色\n"
            "super-dev hooks list                    # 查看 hook 事件\n"
            "super-dev hooks history                 # 查看最近 hook 历史\n"
            "super-dev harness status                # 查看 workflow/framework/hook harness\n"
            "super-dev compact list                  # 查看压缩摘要\n"
            "super-dev config list                   # 查看项目配置\n"
            "super-dev spec list                     # 查看规范与变更\n"
            "```\n"
            "\n"
            "**重要**: 这些命令是治理执行层，宿主自身能力无法替代。"
        )

    # ------------------------------------------------------------------
    # Shared sections (used by both codex and generic)
    # ------------------------------------------------------------------

    def _section_critical_reminders(self) -> str:
        return (
            "## 关键约束提醒（每次操作前必读）\n"
            "\n"
            "以下规则在整个开发过程中始终有效，不得以任何理由违反：\n"
            "\n"
            "1. **图标系统**: 功能图标只能来自 Lucide / Heroicons / Tabler 图标库。"
            "绝对禁止使用 emoji 表情 作为功能图标、装饰图标或临时占位。"
            "如果你发现自己即将输出包含 emoji 的 UI 代码，停下来，改用图标库组件。\n"
            "\n"
            "2. **AI 模板化禁令**: 禁止紫/粉渐变主色调、禁止 emoji 图标、"
            "禁止无信息层级的卡片墙、禁止默认系统字体直出。\n"
            "\n"
            "3. **代码即交付**: 不允许\u201c先用 emoji 顶上后面再换\u201d。"
            "图标库必须在第一行 UI 代码前就锁定。\n"
            "\n"
            "4. **自检规则**: 在向用户展示任何 UI 代码或预览前，"
            "必须自检源码中不存在任何 emoji 字符"
            "（Unicode range U+2600-U+27BF, U+1F300-U+1FAFF）。"
            "发现后先替换为正式图标库再继续。"
        )

    def _section_first_response_contract(self) -> str:
        return (
            "## 首轮响应契约（强制）\n"
            "\n"
            "- 首次触发时第一轮回复必须说明：流水线已激活，当前阶段是 `research`。\n"
            "- 先读取 `.super-dev/WORKFLOW.md` 与 `output/*-bootstrap.md`（若存在）。\n"
            "- 说明固定顺序：research -> 三份核心文档 -> 等待确认"
            " -> Spec/tasks -> 前端优先 -> 后端/测试/交付。\n"
            "- 三份核心文档完成后暂停等待确认；未经确认不创建 Spec 也不编码。\n"
            "\n"
            "### research 双引擎\n"
            "\n"
            "**引擎 1: CLI 知识推送** — `super-dev run research`"
            " 触发本地知识发现，读取 `knowledge/` 和 knowledge-bundle.json。\n"
            "\n"
            "**引擎 2: 宿主联网研究** — WebFetch/WebSearch 搜索同类产品、"
            "竞品和官方文档，写入 `output/*-research.md`。\n"
            "\n"
            "两个引擎的结果都必须在 PRD/架构/UIUX 文档中被继承。"
        )

    def _section_knowledge_contract(self) -> str:
        return (
            "## 本地知识库契约（强制）\n"
            "\n"
            "- 存在 `knowledge/` 时，research 与文档阶段优先读取相关知识文件。\n"
            "- 存在 `output/knowledge-cache/*-knowledge-bundle.json` 时，"
            "先读取 local_knowledge / web_knowledge / research_summary。\n"
            "- 命中的知识是项目约束（标准/检查清单/反模式/场景包/质量门禁），"
            "必须继承到 PRD、架构、UIUX、Spec 和实现阶段。\n"
            "- 未经用户确认禁止创建 `.super-dev/changes/*` 或开始编码。\n"
            "- 产物必须真实写入项目文件，不能只在聊天中口头描述。"
        )

    def _section_session_continuity(self) -> str:
        return (
            "## 会话连续性契约（强制）\n"
            "\n"
            "- 若存在 `.super-dev/SESSION_BRIEF.md`，每次继续前必须先读取。\n"
            '- 用户在确认门/返工门说"改/补充/确认/继续"等，属于流程内动作，不退回普通聊天。\n'
            "- 修改后留在当前门里，总结变化并再次等待确认。\n"
            "- UI 不满意 -> 先更新 `output/*-uiux.md`，再重做前端 + UI review。\n"
            "- 架构不合理 -> 先更新 `output/*-architecture.md`，再调整 Spec/实现。\n"
            "- 质量不达标 -> 先修复，重新执行 quality gate + proof-pack。\n"
            "- 启用 policy 时不得默认建议降低治理强度。"
        )

    def _section_seeai_first_response_contract(self) -> str:
        return (
            "## 首轮响应契约（强制）\n"
            "\n"
            "- 首次触发时第一轮回复必须说明：Super Dev SEEAI 赛事模式已激活，当前阶段是 `research`。\n"
            "- 先快速理解需求，再做极短顺位思考：作品类型、评委 wow 点、必须完成项、主动放弃项。\n"
            "- 如果用户需求模糊，最多只补 1 个关键问题；能合理假设时直接给出假设并推进，不展开长澄清。\n"
            "- 先完成 fast research，再写 compact research / PRD / architecture / UIUX。\n"
            "- 文档确认后创建 compact Spec，然后直接进入 full-stack sprint。\n"
            "- 不要在 SEEAI 模式里重新切回标准 Super Dev 的 preview confirm / 长质量闭环。\n"
            "- 若会落盘 workflow state，必须把 `flow_variant = seeai` 一起写入。\n"
        )

    def _section_seeai_first_response_template(self) -> str:
        descriptions = {
            "作品类型": "官网类 / 小游戏类 / 工具类，三选一。",
            "评委 wow 点": "本次成品最值得被记住的一个亮点。",
            "P0 主路径": "半小时内必须真正跑通的一条演示路径。",
            "主动放弃项": "本轮明确不做的部分，避免范围失控。",
            "关键假设": "只有在用户没说清时才写，最多 1 到 2 条。",
        }
        bullets = "\n".join(
            f"- `{item}`：{descriptions[item]}" for item in SEEAI_FIRST_RESPONSE_TEMPLATE
        )
        return (
            "## 首轮输出模板（强制）\n"
            "\n"
            "SEEAI 首轮回复不要展开成长讨论。优先用极短结构锁定范围，然后立即进入 research：\n"
            "\n"
            f"{bullets}\n"
            "\n"
            "- `评委 wow 点` 要聚焦一个能被截图、讲解或实际操作看到的瞬间。\n"
            "- 锁定 `作品类型` 后，必须立刻选 1 套比赛设计包，不允许自由混搭到页面变丑。\n"
            "如果需求不缺关键信息，就不要反问。直接按这个模板给出判断，然后开始 fast research 和 compact 文档。"
        )

    def _section_seeai_research_protocol(self) -> str:
        priority_lines = "\n".join(f"- {item}" for item in SEEAI_RESEARCH_PRIORITIES)
        query_lines = "\n".join(f"- {item}" for item in SEEAI_SEARCH_QUERIES)
        return (
            "## SEEAI 顺位思考与联网研究协议（强制）\n"
            "\n"
            "比赛里 research 不是写长分析，而是用最短时间做出正确决策。顺位思考和联网搜索必须直接服务于范围压缩和稳定交付。\n"
            "\n"
            "### Research 优先级\n"
            f"{priority_lines}\n"
            "\n"
            "### 联网搜索默认方向\n"
            f"{query_lines}\n"
            "\n"
            "research 结束前，至少要回答清楚：这题属于什么题型/复杂度、wow 点是什么、P0 主路径是什么、主动放弃什么、回退栈是什么。"
        )

    def _section_seeai_compact_doc_template(self) -> str:
        compact_sections = "\n".join(
            f"- `{name}.md`：{'、'.join(sections)}。"
            for name, sections in (
                ("research", SEEAI_COMPACT_DOC_SECTIONS["research"]),
                ("prd", SEEAI_COMPACT_DOC_SECTIONS["prd"]),
                ("architecture", SEEAI_COMPACT_DOC_SECTIONS["architecture"]),
                ("uiux", SEEAI_COMPACT_DOC_SECTIONS["uiux"]),
            )
        )
        return (
            "## 比赛短文档模板（强制）\n"
            "\n"
            "SEEAI 的文档必须真实落盘到 `output/*`，但只保留比赛需要的信息：\n"
            "\n"
            f"{compact_sections}\n"
            "- `spec`：只保留一个 sprint 清单，按 `P0 -> P1 -> polish` 排序。\n"
            "\n"
            "### 推荐标题骨架\n"
            "- `research.md`：`# 题目理解` `# 参考风格` `# Wow 点` `# 主动放弃项`\n"
            "- `prd.md`：`# 作品目标` `# P0 主路径` `# P1 Wow 点` `# P2 可选项` `# 非目标`\n"
            "- `architecture.md`：`# 主循环` `# 技术栈` `# 数据流` `# 最小后端` `# 降级方案`\n"
            "- `uiux.md`：`# 视觉方向` `# 首屏/主界面` `# 关键交互` `# 动效重点` `# 设计 Token`\n"
            "- `spec`：`# Sprint Checklist` 下只列 `P0`、`P1`、`Polish`\n"
            "\n"
            "不要把文档写成长方案、长竞品分析或完整工程规划。文档存在的目的，是帮你更快做出更像成品的作品。"
        )

    def _section_seeai_design_system(self) -> str:
        pack_lines = []
        for pack in get_seeai_design_packs():
            pack_lines.append(
                f"### {pack.label}\n"
                f"- 适用：{pack.fit_for}\n"
                f"- 字体：{pack.typography}\n"
                f"- 色彩：{pack.color_story}\n"
                f"- 动效：{pack.motion_signature}\n"
                f"- 组件方向：{pack.component_direction}\n"
                f"- 守卫：{pack.guardrail}\n"
            )
        pack_block = "\n".join(pack_lines)

        return (
            "## SEEAI 比赛设计系统（强制）\n"
            "\n"
            "SEEAI 不是自由发挥式 UI。进入比赛模式后，必须先选 1 套视觉包，再推进文档和实现。\n"
            "\n"
            "### 统一视觉守卫\n"
            "- 先选题型，再选设计包，再冻结 Hero、卡片、按钮、动效层级。\n"
            "- 禁止把多个设计包混着用，导致页面脏乱或像临时拼装。\n"
            "- 禁止默认紫粉渐变、默认系统字体、通用 AI 模板 Hero。\n"
            "- 首屏必须能截图当宣传图，结果页或结束态必须能截图当演示亮点。\n"
            "\n"
            f"{pack_block}"
        )

    def _section_seeai_execution_guardrails(self) -> str:
        guardrail_lines = "\n".join(f"- {item}" for item in SEEAI_EXECUTION_GUARDRAILS)
        failure_lines = "\n".join(f"- {item}" for item in SEEAI_FAILURE_PROTOCOL)
        module_truth_lines = "\n".join(f"- {item}" for item in SEEAI_MODULE_TRUTH_RULES)
        return (
            "## SEEAI 执行守卫（强制）\n"
            "\n"
            "比赛里最致命的问题不是功能少，而是项目起不来、主路径跑不通、卡死在初始化。SEEAI 必须先防错，再求炫。\n"
            "\n"
            "### 快而稳的执行铁律\n"
            f"{guardrail_lines}\n"
            "\n"
            "### 模块真实生效规则\n"
            f"{module_truth_lines}\n"
            "\n"
            "### 失败优先回退协议\n"
            f"{failure_lines}\n"
        )

    def _section_seeai_complexity_reduction(self) -> str:
        reduction_lines = "\n".join(f"- {item}" for item in SEEAI_COMPLEXITY_REDUCTION_RULES)
        pattern_lines = "\n".join(
            f"- 模式：{item['pattern']}\n"
            f"  压缩方式：{item['rewrite_strategy']}\n"
            f"  原因：{item['reason']}"
            for item in SEEAI_COMPLEXITY_PATTERNS
        )
        return (
            "## SEEAI 复杂题压缩规则（强制）\n"
            "\n"
            "比赛题目不可能被提前穷举。SEEAI 不应该依赖题库，而要依赖通用压缩原则：先识别复杂度，再把需求压成 30 分钟能交付的 demo slice。\n"
            "\n"
            "### 通用压缩原则\n"
            f"{reduction_lines}\n"
            "\n"
            "### 常见复杂度模式\n"
            f"{pattern_lines}\n"
            "\n"
            "如果遇到未见过的新题，仍按这个顺序处理：识别题型 -> 识别复杂度 -> 砍成主演示切片 -> 锁回退栈 -> 立即开做。"
        )

    def _section_seeai_tech_stack_matrix(self) -> str:
        return (
            "## 技术栈快速决策矩阵（核心）\n"
            "\n"
            "收到题目后，根据作品类型**立刻**选择技术栈。不纠结，不混搭。\n"
            "\n"
            "### 决策树\n"
            "\n"
            "```\n"
            "题目类型？\n"
            "|-- 小游戏 / 互动动画\n"
            "|   |-- 纯2D休闲 -> HTML Canvas + Vanilla JS（零依赖，开箱即用）\n"
            "|   |-- 复杂2D游戏 -> Phaser.js（场景管理、物理引擎、精灵动画一体化）\n"
            "|   `-- 3D/沉浸感 -> Three.js + React Three Fiber（如果用React）\n"
            "|\n"
            "|-- 官网 / 展示页 / 落地页\n"
            "|   |-- 纯静态展示 -> HTML + Tailwind CDN + GSAP/Framer Motion\n"
            "|   |-- 需要路由/多页 -> React + Vite + Tailwind + Framer Motion\n"
            "|   `-- 需要SSR/SEO -> Next.js + Tailwind + Framer Motion\n"
            "|\n"
            "|-- 工具 / 应用\n"
            "|   |-- 纯前端工具 -> React + Vite + Tailwind + Zustand\n"
            "|   |-- 需要后端API -> React前端 + Express/Fastify后端\n"
            "|   `-- 实时协作 -> React + Socket.io / WebSocket\n"
            "|\n"
            "`-- 数据看板 / 可视化\n"
            "    |-- 简单图表 -> React + Recharts / Chart.js\n"
            "    |-- 复杂交互 -> React + D3.js\n"
            "    `-- 实时数据 -> React + ECharts + WebSocket\n"
            "```\n"
            "\n"
            "### 赛事推荐组合（已验证能30分钟内交付）\n"
            "\n"
            "| 组合 | 适用场景 | CDN快速启动 | 需要构建 |\n"
            "|------|---------|------------|---------|\n"
            "| **HTML+Tailwind CDN+GSAP** | 展示页/官网 | 是 | 否 |\n"
            "| **React+Vite+Tailwind+Framer** | 工具/应用/多页 | 否 | 是 |\n"
            "| **HTML Canvas+Vanilla JS** | 2D小游戏/互动 | 是 | 否 |\n"
            "| **Phaser.js** | 复杂2D游戏 | 是 | 否 |\n"
            "| **Three.js** | 3D展示/沉浸 | 是 | 否 |\n"
            "\n"
            "**赛事铁律**: 能用 CDN 零构建的优先用 CDN，省掉构建和配置时间。\n"
        )

    def _section_seeai_game_templates(self) -> str:
        return (
            "## 小游戏开发模板库（核心）\n"
            "\n"
            "### 模板1: HTML Canvas 游戏骨架\n"
            "适用于所有 2D 休闲游戏（贪吃蛇、打砖块、弹球、飞机大战等）。\n"
            "骨架包含：Canvas 初始化、游戏主循环、HUD、菜单/结束 Overlay、localStorage 最高分。\n"
            "\n"
            "```html\n"
            "<!DOCTYPE html>\n"
            '<html lang="zh-CN">\n'
            "<head>\n"
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "  <title>GAME_TITLE</title>\n"
            "  <style>\n"
            "    * { margin: 0; padding: 0; box-sizing: border-box; }\n"
            "    body { background: #0a0a0a; display: flex; justify-content: center;"
            " align-items: center; min-height: 100vh; font-family: 'Inter', sans-serif; }\n"
            "    #gameContainer { position: relative; }\n"
            "    canvas { display: block; border-radius: 12px;"
            " box-shadow: 0 0 40px rgba(59,130,246,0.3); }\n"
            "    #hud { position: absolute; top: 0; left: 0; right: 0; padding: 16px 24px;"
            " display: flex; justify-content: space-between; color: #fff; font-size: 14px;"
            " font-weight: 600; pointer-events: none; z-index: 10; }\n"
            "    #overlay { position: absolute; inset: 0; display: flex;"
            " flex-direction: column; justify-content: center; align-items: center;"
            " background: rgba(0,0,0,0.8); border-radius: 12px; z-index: 20;"
            " transition: opacity 0.3s; }\n"
            "    #overlay.hidden { opacity: 0; pointer-events: none; }\n"
            "    #overlay h1 { color: #fff; font-size: 36px; margin-bottom: 8px; }\n"
            "    #overlay p { color: #94a3b8; margin-bottom: 24px; }\n"
            "    #overlay button { padding: 12px 32px; border: none; border-radius: 8px;"
            " background: #3b82f6; color: #fff; font-size: 16px; font-weight: 600;"
            " cursor: pointer; transition: transform 0.15s, background 0.15s; }\n"
            "    #overlay button:hover { transform: scale(1.05); background: #2563eb; }\n"
            "    .score-display { background: rgba(255,255,255,0.1); padding: 6px 16px;"
            " border-radius: 20px; backdrop-filter: blur(8px); }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            '  <div id="gameContainer">\n'
            '    <canvas id="gameCanvas"></canvas>\n'
            '    <div id="hud">\n'
            '      <div class="score-display">Score: <span id="score">0</span></div>\n'
            '      <div class="score-display">Level: <span id="level">1</span></div>\n'
            '      <div class="score-display">Best: <span id="best">0</span></div>\n'
            "    </div>\n"
            '    <div id="overlay">\n'
            "      <h1>GAME_TITLE</h1>\n"
            "      <p>游戏描述</p>\n"
            '      <button id="startBtn">Start Game</button>\n'
            "    </div>\n"
            "  </div>\n"
            "  <script>\n"
            "    const CONFIG = { width: 800, height: 600, bgColor: '#0a0a0a',"
            " accentColor: '#3b82f6', fps: 60 };\n"
            "    const STATE = { MENU: 0, PLAYING: 1, PAUSED: 2, OVER: 3 };\n"
            "    let gameState = STATE.MENU, score = 0, level = 1;\n"
            "    let bestScore = parseInt(localStorage.getItem('game_best') || '0');\n"
            "    const canvas = document.getElementById('gameCanvas');\n"
            "    const ctx = canvas.getContext('2d');\n"
            "    canvas.width = CONFIG.width; canvas.height = CONFIG.height;\n"
            "    const keys = {};\n"
            "    document.addEventListener('keydown', e => { keys[e.key] = true;"
            " e.preventDefault(); });\n"
            "    document.addEventListener('keyup', e => { keys[e.key] = false; });\n"
            "    let lastTime = 0;\n"
            "    function gameLoop(timestamp) {\n"
            "      const dt = (timestamp - lastTime) / 1000; lastTime = timestamp;\n"
            "      ctx.fillStyle = CONFIG.bgColor;\n"
            "      ctx.fillRect(0, 0, CONFIG.width, CONFIG.height);\n"
            "      if (gameState === STATE.PLAYING) { update(dt); draw(); }\n"
            "      requestAnimationFrame(gameLoop);\n"
            "    }\n"
            "    function update(dt) { /* game logic */ }\n"
            "    function draw() { /* render */ }\n"
            "    function addScore(pts) {\n"
            "      score += pts;\n"
            "      document.getElementById('score').textContent = score;\n"
            "      if (score > bestScore) {\n"
            "        bestScore = score; localStorage.setItem('game_best', bestScore);\n"
            "        document.getElementById('best').textContent = bestScore;\n"
            "      }\n"
            "    }\n"
            "    function startGame() {\n"
            "      score = 0; level = 1; gameState = STATE.PLAYING;\n"
            "      document.getElementById('overlay').classList.add('hidden');\n"
            "    }\n"
            "    function gameOver() {\n"
            "      gameState = STATE.OVER;\n"
            "      const o = document.getElementById('overlay');\n"
            "      o.classList.remove('hidden');\n"
            "      o.querySelector('h1').textContent = 'Game Over';\n"
            "      o.querySelector('p').textContent = 'Final Score: ' + score;\n"
            "      o.querySelector('button').textContent = 'Play Again';\n"
            "    }\n"
            "    document.getElementById('startBtn').addEventListener('click', startGame);\n"
            "    document.getElementById('best').textContent = bestScore;\n"
            "    requestAnimationFrame(gameLoop);\n"
            "  </script>\n"
            "</body>\n"
            "</html>\n"
            "```\n"
            "\n"
            "### 模板2: 碰撞检测工具箱\n"
            "\n"
            "```javascript\n"
            "// 矩形碰撞\n"
            "function rectCollision(a, b) {\n"
            "  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h"
            " && a.y + a.h > b.y;\n"
            "}\n"
            "// 圆形碰撞\n"
            "function circleCollision(a, b) {\n"
            "  const dx = a.x - b.x, dy = a.y - b.y;\n"
            "  return dx*dx + dy*dy < (a.r + b.r) * (a.r + b.r);\n"
            "}\n"
            "// 粒子效果\n"
            "class Particle {\n"
            "  constructor(x, y, color) {\n"
            "    this.x=x; this.y=y; this.vx=(Math.random()-0.5)*8;"
            " this.vy=(Math.random()-0.5)*8;\n"
            "    this.life=1; this.decay=0.02+Math.random()*0.03;"
            " this.size=2+Math.random()*4; this.color=color;\n"
            "  }\n"
            "  update() { this.x+=this.vx; this.y+=this.vy; this.life-=this.decay;"
            " this.vy+=0.1; }\n"
            "  draw(ctx) {\n"
            "    ctx.globalAlpha=this.life; ctx.fillStyle=this.color;\n"
            "    ctx.fillRect(this.x-this.size/2, this.y-this.size/2,"
            " this.size, this.size);\n"
            "    ctx.globalAlpha=1;\n"
            "  }\n"
            "  get dead() { return this.life <= 0; }\n"
            "}\n"
            "```\n"
            "\n"
            "### 模板3: 常见游戏模式速查\n"
            "\n"
            "| 游戏类型 | 核心循环 | 关键对象 | 反馈重点 |\n"
            "|---------|---------|---------|---------|\n"
            "| 贪吃蛇 | 移动->吃食->变长->碰撞检测 | 蛇身数组、食物坐标 | 吃到食物闪烁、蛇身渐变色 |\n"
            "| 打砖块 | 发球->挡板->砖块碰撞 | 挡板、球、砖块网格 | 砖块破碎粒子、连击特效 |\n"
            "| 飞机大战 | 移动->射击->躲避->Boss | 玩家飞机、敌机数组、子弹数组 | 爆炸粒子、屏幕震动 |\n"
            "| 消除游戏 | 选择->匹配->消除->下落 | 网格数组、选中状态、动画队列 | 消除爆炸、连锁得分飞字 |\n"
            "| 跑酷 | 跳跃->障碍->加速->距离 | 角色、障碍物队列、地面 | 跳跃拉伸、落地压缩、速度线 |\n"
            "\n"
            "### 模板4: 游戏HUD/UI组件\n"
            "\n"
            "```javascript\n"
            "// 屏幕震动\n"
            "function screenShake(intensity=5, duration=200) {\n"
            "  const c = document.getElementById('gameContainer');\n"
            "  const start = Date.now();\n"
            "  function shake() {\n"
            "    const elapsed = Date.now() - start;\n"
            "    if (elapsed < duration) {\n"
            "      const f = 1 - elapsed/duration;\n"
            "      c.style.transform = `translate(${(Math.random()-0.5)*intensity*f}px,"
            "${(Math.random()-0.5)*intensity*f}px)`;\n"
            "      requestAnimationFrame(shake);\n"
            "    } else { c.style.transform = ''; }\n"
            "  }\n"
            "  shake();\n"
            "}\n"
            "// 得分飞字\n"
            "function floatingText(x, y, text, color='#fbbf24') {\n"
            "  const el = document.createElement('div');\n"
            "  el.textContent = text;\n"
            "  Object.assign(el.style, { position:'absolute', left:x+'px', top:y+'px',"
            " color, fontSize:'20px', fontWeight:'bold', pointerEvents:'none',"
            " transition:'all 0.8s ease-out', zIndex:'30' });\n"
            "  document.getElementById('gameContainer').appendChild(el);\n"
            "  requestAnimationFrame(() => { el.style.top=(y-60)+'px'; el.style.opacity='0'; });\n"
            "  setTimeout(() => el.remove(), 800);\n"
            "}\n"
            "```\n"
            "\n"
            "### 游戏开发铁律\n"
            "- 核心玩法循环必须完整：开始->游玩->结束->再来一次\n"
            "- 反馈感 > 真实物理：夸张的视觉反馈比物理精确更重要\n"
            "- 操作延迟 < 50ms：任何卡顿都会毁掉游戏体验\n"
            "- 分数/进度必须实时可见\n"
        )

    def _section_seeai_page_templates(self) -> str:
        return (
            "## 精美页面模板库（核心）\n"
            "\n"
            "### 设计Token预设（6套赛事验证主题）\n"
            "\n"
            "#### 主题A: 暗夜科技（适合科技/AI/数据类）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #0a0a0f;\n"
            "  --bg-secondary: #111827;\n"
            "  --text-primary: #f1f5f9;\n"
            "  --text-secondary: #94a3b8;\n"
            "  --accent: #3b82f6;\n"
            "  --accent-glow: rgba(59,130,246,0.4);\n"
            "  --gradient-hero: linear-gradient(135deg, #0a0a0f 0%, #1e1b4b 50%, #0a0a0f 100%);\n"
            "  --card-bg: rgba(17,24,39,0.8);\n"
            "  --card-border: rgba(59,130,246,0.15);\n"
            "}\n"
            "```\n"
            "\n"
            "#### 主题B: 日出暖橙（适合教育/社交/正能量）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #fffbf5; --bg-secondary: #fef3e2;\n"
            "  --text-primary: #1c1917; --text-secondary: #78716c;\n"
            "  --accent: #f97316; --accent-glow: rgba(249,115,22,0.3);\n"
            "  --gradient-hero: linear-gradient(135deg, #fffbf5 0%, #fed7aa 100%);\n"
            "  --card-bg: rgba(255,251,245,0.9); --card-border: rgba(249,115,22,0.15);\n"
            "}\n"
            "```\n"
            "\n"
            "#### 主题C: 翡翠绿意（适合环保/健康/生活）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #f0fdf4; --bg-secondary: #dcfce7;\n"
            "  --text-primary: #14532d; --text-secondary: #4d7c0f;\n"
            "  --accent: #16a34a; --accent-glow: rgba(22,163,74,0.3);\n"
            "  --gradient-hero: linear-gradient(135deg, #f0fdf4 0%, #bbf7d0 100%);\n"
            "  --card-bg: rgba(240,253,244,0.9); --card-border: rgba(22,163,74,0.15);\n"
            "}\n"
            "```\n"
            "\n"
            "#### 主题D: 极简黑白（适合工具/效率/专业）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #fafafa; --bg-secondary: #f4f4f5;\n"
            "  --text-primary: #18181b; --text-secondary: #71717a;\n"
            "  --accent: #18181b; --accent-glow: rgba(24,24,27,0.1);\n"
            "  --gradient-hero: linear-gradient(180deg, #fafafa 0%, #e4e4e7 100%);\n"
            "  --card-bg: #ffffff; --card-border: rgba(24,24,27,0.08);\n"
            "}\n"
            "```\n"
            "\n"
            "#### 主题E: 深海蓝绿（适合海洋/探索/游戏）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #042f2e; --bg-secondary: #134e4a;\n"
            "  --text-primary: #ccfbf1; --text-secondary: #5eead4;\n"
            "  --accent: #14b8a6; --accent-glow: rgba(20,184,166,0.4);\n"
            "  --gradient-hero: linear-gradient(135deg, #042f2e 0%, #0f766e 50%, #042f2e 100%);\n"
            "  --card-bg: rgba(19,78,74,0.6); --card-border: rgba(20,184,166,0.2);\n"
            "}\n"
            "```\n"
            "\n"
            "#### 主题F: 赛博朋克（适合潮流/音乐/创意）\n"
            "```css\n"
            ":root {\n"
            "  --bg-primary: #0c0015; --bg-secondary: #1a002e;\n"
            "  --text-primary: #f0e6ff; --text-secondary: #c084fc;\n"
            "  --accent: #e879f9; --accent-secondary: #06ffa5;\n"
            "  --accent-glow: rgba(232,121,249,0.4);\n"
            "  --gradient-hero: linear-gradient(135deg, #0c0015 0%, #2d1b69 50%, #0c0015 100%);\n"
            "  --card-bg: rgba(26,0,46,0.8); --card-border: rgba(232,121,249,0.2);\n"
            "}\n"
            "```\n"
            "\n"
            "**禁止使用**: 紫粉渐变、默认蓝色模板感配色。\n"
            "\n"
            "### 动效预设工具箱\n"
            "\n"
            "```javascript\n"
            "// 1. 滚动渐入（Intersection Observer）\n"
            "function setupScrollReveal() {\n"
            "  const observer = new IntersectionObserver(entries => {\n"
            "    entries.forEach(e => { if(e.isIntersecting) {"
            " e.target.classList.add('revealed'); observer.unobserve(e.target); } });\n"
            "  }, { threshold: 0.1 });\n"
            "  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));\n"
            "}\n"
            "// CSS: .reveal { opacity:0; transform:translateY(30px);"
            " transition:all 0.6s cubic-bezier(0.16,1,0.3,1); }\n"
            "// .reveal.revealed { opacity:1; transform:translateY(0); }\n"
            "\n"
            "// 2. 数字滚动动画\n"
            "function animateNumber(el, target, duration=1500) {\n"
            "  const start = parseInt(el.textContent)||0; const t0 = performance.now();\n"
            "  function update(now) {\n"
            "    const p = Math.min((now-t0)/duration, 1);\n"
            "    const eased = 1 - Math.pow(1-p, 3);\n"
            "    el.textContent = Math.round(start + (target-start)*eased).toLocaleString();\n"
            "    if(p<1) requestAnimationFrame(update);\n"
            "  }\n"
            "  requestAnimationFrame(update);\n"
            "}\n"
            "\n"
            "// 3. 鼠标跟随光晕\n"
            "function setupCursorGlow(container) {\n"
            "  const glow = document.createElement('div');\n"
            "  Object.assign(glow.style, { position:'absolute', width:'400px', height:'400px',\n"
            "    borderRadius:'50%', pointerEvents:'none',\n"
            "    background:'radial-gradient(circle, var(--accent-glow) 0%, transparent 70%)',\n"
            "    transform:'translate(-50%,-50%)', zIndex:'0', opacity:'0.6' });\n"
            "  container.style.position = 'relative';\n"
            "  container.appendChild(glow);\n"
            "  container.addEventListener('mousemove', e => {\n"
            "    const r = container.getBoundingClientRect();\n"
            "    glow.style.left = (e.clientX-r.left)+'px';\n"
            "    glow.style.top = (e.clientY-r.top)+'px';\n"
            "  });\n"
            "}\n"
            "\n"
            "// 4. 打字机效果\n"
            "function typeWriter(el, text, speed=60) {\n"
            "  let i = 0; el.textContent = '';\n"
            "  function type() { if(i<text.length) { el.textContent += text.charAt(i++);"
            " setTimeout(type, speed); } }\n"
            "  type();\n"
            "}\n"
            "\n"
            "// 5. 卡片3D倾斜\n"
            "function setupTiltCard(card, intensity=15) {\n"
            "  card.addEventListener('mousemove', e => {\n"
            "    const r = card.getBoundingClientRect();\n"
            "    const x = (e.clientX-r.left)/r.width - 0.5;\n"
            "    const y = (e.clientY-r.top)/r.height - 0.5;\n"
            "    card.style.transform = `perspective(800px) rotateY(${x*intensity}deg)"
            " rotateX(${-y*intensity}deg) scale(1.02)`;\n"
            "  });\n"
            "  card.addEventListener('mouseleave', () => { card.style.transform = ''; });\n"
            "}\n"
            "```\n"
            "\n"
            "### Hero区域模板（3种高转化布局）\n"
            "\n"
            "#### Hero A: 大标题+CTA+背景动画（通用）\n"
            "```html\n"
            '<section style="min-height:100vh;display:flex;align-items:center;'
            "justify-content:center;position:relative;overflow:hidden;"
            'background:var(--bg-primary)">\n'
            '  <div style="position:absolute;inset:0;opacity:0.5;'
            'background:var(--gradient-hero)"></div>\n'
            '  <div style="position:relative;z-index:10;text-align:center;'
            'max-width:800px;padding:0 24px">\n'
            '    <div style="display:inline-block;padding:6px 16px;border-radius:20px;'
            "background:var(--accent);color:#fff;font-size:13px;font-weight:600;"
            'margin-bottom:24px">Tagline</div>\n'
            '    <h1 style="font-size:clamp(36px,6vw,72px);font-weight:800;'
            'color:var(--text-primary);line-height:1.1;margin-bottom:16px">'
            '主标题 <span style="color:var(--accent)">关键词高亮</span></h1>\n'
            '    <p style="font-size:18px;color:var(--text-secondary);margin-bottom:32px;'
            'max-width:600px;margin-left:auto;margin-right:auto">副标题</p>\n'
            '    <div style="display:flex;gap:12px;justify-content:center">\n'
            '      <a href="#cta" style="padding:14px 32px;border-radius:8px;'
            "background:var(--accent);color:#fff;text-decoration:none;"
            'font-weight:600">Primary CTA</a>\n'
            "    </div>\n"
            "  </div>\n"
            "</section>\n"
            "```\n"
            "\n"
            "#### Hero B: 左文右图（产品/工具类）\n"
            "```html\n"
            '<section style="min-height:100vh;display:grid;'
            "grid-template-columns:1fr 1fr;align-items:center;gap:48px;"
            'padding:80px 48px;background:var(--bg-primary)">\n'
            "  <div>\n"
            '    <h1 style="font-size:48px;font-weight:800;'
            'color:var(--text-primary)">标题</h1>\n'
            '    <p style="font-size:18px;color:var(--text-secondary);'
            'margin-bottom:24px">描述</p>\n'
            '    <button style="padding:12px 28px;border-radius:8px;'
            "background:var(--accent);color:#fff;border:none;"
            'font-weight:600;cursor:pointer">Get Started</button>\n'
            "  </div>\n"
            '  <div style="aspect-ratio:4/3;border-radius:16px;'
            'background:var(--card-bg);border:1px solid var(--card-border)"></div>\n'
            "</section>\n"
            "```\n"
            "\n"
            "#### Hero C: 全屏动态背景+居中标题（展示类）\n"
            "```html\n"
            '<section style="height:100vh;display:flex;align-items:center;'
            'justify-content:center;position:relative">\n'
            '  <div style="position:absolute;inset:0;'
            'background:var(--gradient-hero);z-index:1"></div>\n'
            '  <div style="position:relative;z-index:10;text-align:center;color:#fff">\n'
            '    <h1 style="font-size:clamp(40px,8vw,80px);font-weight:900;'
            'text-shadow:0 2px 20px rgba(0,0,0,0.3)">主标题</h1>\n'
            '    <p style="font-size:20px;max-width:600px;margin:16px auto 0;'
            'opacity:0.85">副标题</p>\n'
            "  </div>\n"
            "</section>\n"
            "```\n"
            "\n"
            "### 页面开发铁律\n"
            "- 首屏3秒内传达核心价值，不允许普通模板感\n"
            "- 至少一个让人记住的动效瞬间（鼠标跟随/数字滚动/粒子背景）\n"
            "- 所有颜色使用 CSS 变量，不硬编码 hex\n"
            "- 移动端至少可用，桌面端完美\n"
        )

    def _section_seeai_competition_doc_templates(self) -> str:
        return (
            "## 赛事文档模板库（核心）\n"
            "\n"
            "比赛不只看代码，**文档和演示决定最终名次**。以下模板在 Spec 确认后立即生成。\n"
            "\n"
            "### 模板1: 参赛项目 README\n"
            "\n"
            "```markdown\n"
            "# PROJECT_NAME\n"
            "\n"
            "> 一句话描述项目核心价值（评委3秒内能理解）\n"
            "\n"
            "## 项目亮点\n"
            "- 亮点1（技术实现/设计/创新）\n"
            "- 亮点2\n"
            "- 亮点3\n"
            "\n"
            "## 技术栈\n"
            "\n"
            "| 层级 | 技术 | 选型理由 |\n"
            "|------|------|----------|\n"
            "| 前端 | XXX | 快速/美观/生态 |\n"
            '| 后端 | XXX（如无则写"纯前端"） | 必要性 |\n'
            "| 数据 | XXX | 轻量/够用 |\n"
            "| 部署 | XXX | 一键/零配置 |\n"
            "\n"
            "## 快速开始\n"
            "```bash\n"
            "npm install && npm run dev\n"
            "```\n"
            "\n"
            "## 功能演示路径\n"
            "1. 打开首页 -> 看到XXX\n"
            "2. 点击XXX -> 触发XXX\n"
            "3. 完成XXX -> 看到结果\n"
            "```\n"
            "\n"
            "### 模板2: 技术亮点文档\n"
            "\n"
            "```markdown\n"
            "## 1. 创新点：XXX\n"
            "**问题**: 为什么要做这个\n"
            "**方案**: 具体怎么实现的\n"
            "**效果**: 数据/截图/对比\n"
            "\n"
            "## 2. 技术难点突破：XXX\n"
            "**挑战**: 遇到什么问题\n"
            "**解决**: 怎么解决的\n"
            "**收获**: 学到了什么\n"
            "```\n"
            "\n"
            "### 模板3: 演示脚本（30秒版 + 2分钟版）\n"
            "\n"
            "```markdown\n"
            "## 30秒电梯演讲\n"
            "大家好，我们是TEAM_NAME。我们做了PROJECT_NAME。\n"
            "它解决的核心问题是【痛点】。我们的方案是【一句话方案】。\n"
            "最大的亮点是【wow点】。谢谢！\n"
            "\n"
            "## 2分钟完整演示\n"
            "### 开场（15秒）：我们注意到一个问题... 切到首页展示痛点场景\n"
            "### 核心演示（60秒）：按功能顺序走一条完整主路径\n"
            "### 亮点展示（30秒）：展示技术亮点/创新设计\n"
            "### 总结（15秒）：一句话总结核心价值 + 未来展望\n"
            "\n"
            "## 演示注意\n"
            "- 准备备用演示路径（主路径出问题时的Plan B）\n"
            "- 数据预填充，不要现场输入\n"
            "- 不依赖网络，本地运行\n"
            "```\n"
            "\n"
            "### 模板4: 答辩准备卡\n"
            "\n"
            "```markdown\n"
            "## 必答题\n"
            "1. 技术方案为什么这样选？ -> 性能/生态/时间权衡\n"
            "2. 再给一周时间优先做什么？ -> 核心体验/用户反馈\n"
            "3. 最大的技术挑战？ -> 具体问题+解决方案\n"
            "4. 和竞品相比核心差异？ -> 创新点+用户价值\n"
            "5. 用户体验有什么特别设计？ -> 细节+数据支撑\n"
            "\n"
            "## 加分回答（主动提及）\n"
            "- 我们不只做了功能，还关注了XXX细节\n"
            "- 我们在有限时间内做了降级方案确保演示稳定\n"
            "\n"
            "## 减分避免\n"
            '- 不要说"时间不够所以没做完"\n'
            '- 不要说"这个功能比较简单"\n'
            '- 不要说"AI帮我们写的"（改说"我们利用AI辅助提升了开发效率"）\n'
            "```\n"
            "\n"
            "### 赛事文档铁律\n"
            "- 文档必须落盘到 output/* 和项目根目录 README.md\n"
            "- 技术亮点不能空泛，必须有具体的方案描述\n"
            "- 演示脚本必须提前演练一遍，确保路径完整无断点\n"
            '- 答辩回答不要说"时间不够"或"AI写的"\n'
        )

    def _section_seeai_project_archetypes(self) -> str:
        playbook_lines = []
        for playbook in get_seeai_archetype_playbooks():
            preferred_packs = " / ".join(playbook.preferred_design_packs)
            playbook_lines.append(
                f"- {playbook.label}：优先 {playbook.focus}。\n"
                f"  默认技术栈：{playbook.default_stack}。\n"
                f"  默认 sprint：{' -> '.join(playbook.sprint_plan)}。\n"
                f"  默认设计包：{preferred_packs}。\n"
                f"  Hero 策略：{playbook.hero_strategy}\n"
                f"  wow 模式：{playbook.wow_pattern}\n"
                f"  运行检查点：{playbook.runtime_checkpoint}\n"
                f"  回退栈：{playbook.fallback_stack}"
            )
        playbook_block = "\n".join(playbook_lines)
        return (
            "## 作品类型决策模板\n"
            "\n"
            "进入 SEEAI 后，优先先判断当前更像哪一类题，再决定研究和实现重心：\n"
            "\n"
            f"{playbook_block}\n"
            "\n"
            "如果需求跨多类，默认选最容易形成强演示效果的那一类做主轴，其余只做辅助。"
        )

    def _section_seeai_archetype_detection_hints(self) -> str:
        detection_lines = "\n".join(
            f"- 如果需求强调{hint}" for hint in SEEAI_ARCHETYPE_DETECTION_HINTS
        )
        return (
            "## 题型识别提示\n"
            "\n"
            "在首轮判断时，优先用需求关键词快速归类，不要犹豫太久：\n"
            "\n"
            f"{detection_lines}\n"
            "- 如果用户同时提到官网 + 交互玩法，先判断评审更容易记住哪一面，把那一面作为主轴。\n"
        )

    def _section_seeai_quality_floor(self) -> str:
        floor_lines = "\n".join(f"- {item}" for item in SEEAI_QUALITY_FLOOR)
        judge_lines = "\n".join(f"- {item}" for item in SEEAI_JUDGE_CHECKLIST)
        return (
            "## 比赛质量底线\n"
            "\n"
            "即使在半小时里，也必须守住这些底线：\n"
            "\n"
            f"{floor_lines}\n"
            "\n"
            "### 评委视角自检\n"
            f"{judge_lines}\n"
        )

    def _section_seeai_competition_tools(self) -> str:
        return (
            "## 赛事专用能力\n"
            "\n"
            "### 评委视角优化\n"
            "- 每个作品必须有一个2分钟能讲完的完整演示故事线\n"
            "- 标题/首屏/Hero区域在3秒内传达核心价值\n"
            "- 结果页/完成页让评委有完成感，而不是半成品感\n"
            "- 动效不在于多，在于有1-2个让人记住的瞬间\n"
            "\n"
            "### 降级策略\n"
            "- 后端来不及 -> 用 localStorage / mock API，但要标注demo数据\n"
            "- 多页面来不及 -> 做好单页的完整体验，胜过5个半成品页面\n"
            "- 复杂交互来不及 -> 简化流程，但保留核心闭环\n"
            "- 响应式来不及 -> 保证桌面端完美，移动端可用\n"
            "\n"
            "### 演示准备\n"
            "- 准备一段30秒的口头介绍：这是什么 + 给谁用 + 核心价值 + wow点\n"
            "- 准备一条完整的主流程演示路径（从开始到结束无断点）\n"
            "- 准备一个备选路径（如果主路径出了问题）\n"
            "- 确保首屏截图就能当宣传图用\n"
        )

    def _section_seeai_session_continuity(self) -> str:
        return (
            "## 会话连续性契约（强制）\n"
            "\n"
            "- 若存在 `.super-dev/SESSION_BRIEF.md`，每次继续前必须先读取。\n"
            '- 用户在 SEEAI 模式里说"改一下 / 再炫一点 / 补个功能 / 继续做"等，属于当前比赛流程内动作。\n'
            "- 文档确认前，任何修改都先落在 compact research / PRD / architecture / UIUX 上。\n"
            "- Spec 之后，任何修改默认回到当前 full-stack sprint，不额外拆出新的长门禁。\n"
        )

    def _section_pre_code_gate(self) -> str:
        return (
            "## 编码前门禁（Spec 确认后、编码开始前必须执行）\n"
            "\n"
            "跳过任何一步都会导致大量返工：\n"
            "\n"
            "### 第 1 步：技术栈预研（最关键）\n"
            "- 读取项目依赖文件（package.json / requirements.txt / go.mod 等），"
            "找到主要依赖的精确版本号\n"
            "- 用 WebFetch 查阅每个主要框架的官方文档："
            "Getting Started、Migration Guide、API Reference\n"
            "- **不确定 API 写法时，先查官方文档再写代码，永远不要猜**\n"
            "\n"
            "### 第 2 步：读取项目配置\n"
            "- `super-dev.yaml` 确认技术栈选择\n"
            "- 框架配置文件、tsconfig.json、.env.example\n"
            "- 已有代码目录结构\n"
            "\n"
            "### 第 3 步：声明 UI 工具链\n"
            "- 声明并确认图标库（Lucide/Heroicons/Tabler）和组件库已安装\n"
            "- 不声明 = 不允许写 UI 代码\n"
            "\n"
            "### 第 4 步：确认 API 契约和设计 token\n"
            "- 读取 output/*-architecture.md 中的 API 定义\n"
            "- 读取 output/*-uiux.md 中的设计 token\n"
            "\n"
            "### 第 5 步：生成脚手架并验证构建\n"
            "- `super-dev generate components` + `super-dev generate types`\n"
            "- 运行构建命令确认零错误后才开始写业务代码\n"
        )

    def _section_phase_enforcement(self) -> str:
        return (
            "## 编码阶段持续治理\n"
            "\n"
            "读取 `.super-dev/pipeline-state.json` 了解当前在哪个阶段。\n"
            "根据阶段调整你的工作重点：research 阶段侧重调研，frontend 阶段侧重 UI 实现，"
            "quality 阶段侧重测试和门禁。\n"
            "\n"
            "每次进入新阶段时宣告: `Super Dev | [N/9] 阶段名 开始 | 主导专家: XXX`\n"
            "\n"
            "### 每次写文件前自检\n"
            '- [ ] "use client" 是否需要？（Next.js）\n'
            "- [ ] 图标来自声明的图标库？（不是 emoji）\n"
            "- [ ] 颜色来自设计 token？（不是硬编码 hex）\n"
            "- [ ] import 路径正确？API 路径与架构文档一致？\n"
            "\n"
            "### 每完成一个功能后\n"
            "1. build 无错误 2. lint 无 error 3. 无控制台红色错误\n"
            "4. 对比 output/*-uiux.md 视觉一致 5. 运行 validate-superdev.sh（如有）"
        )

    def _section_common_mistakes(self) -> str:
        blocks: list[str] = [
            "## 宿主常犯错误速查（每次编码前扫一眼）",
        ]

        # Top 3 with code examples
        blocks.append(
            "### 错误 1: 使用 emoji 作为图标\n"
            "```tsx\n"
            "// ❌ <button>🔍 搜索</button>\n"
            "// ✅ import { Search } from 'lucide-react'\n"
            "//    <button><Search size={16} /> 搜索</button>\n"
            "```"
        )

        blocks.append(
            "### 错误 2: 紫色渐变 AI 模板\n"
            "```tsx\n"
            "// ❌ bg-gradient-to-r from-purple-500 to-pink-500\n"
            "// ✅ 使用 output/*-uiux.md 定义的品牌色: bg-primary + text-heading-1\n"
            "```"
        )

        blocks.append(
            "### 错误 3: 前后端 API 路径不一致\n"
            "```\n"
            "// ❌ 架构文档写 /api/users，后端实际是 /api/v1/users\n"
            "// ✅ 编码前先确认 output/*-architecture.md 中的 API 路径\n"
            "```"
        )

        # Next.js: one-liner summaries
        if self._is_nextjs_likely():
            blocks.append(
                "### Next.js 常见错误（一行速查）\n"
                "- 用 `<img>` 而非 `next/image` Image 组件\n"
                "- 用 `<a>` 而非 `next/link` Link 组件\n"
                "- 在 Server Component 中使用 useState/useEffect（需 `'use client'` 或改 async）\n"
                "- 用 Express 风格 handler(req,res) 而非 Route Handler export async function GET()"
            )

        return "\n\n".join(blocks)

    def _is_nextjs_likely(self) -> bool:
        """Check if the project is likely using Next.js based on skill name/host hints."""
        name_lower = self.skill_name.lower()
        return "next" in name_lower or "nextjs" in name_lower

    def _section_implementation_closure(self) -> str:
        return (
            "## 实现闭环契约（强制）\n"
            "\n"
            "- 每轮修改后先做最小 diff review 再汇报完成。\n"
            "- 运行 build / type-check / test / runtime smoke。\n"
            "- 新增代码必须接入真实调用链；未接入则删除，禁止留 unused code。\n"
            "- 新增日志/告警/埋点必须验证会在真实路径触发。"
        )

    def _section_never_do(self) -> str:
        return (
            "## Never do this\n"
            "\n"
            "- Never jump straight into coding"
            " after `super-dev:` or `super-dev：`.\n"
            "- Never create Spec or implementation work"
            " before the documents are confirmed.\n"
            "- 未经用户明确确认，禁止创建 `.super-dev/changes/*`。\n"
            "- Use local `super-dev` CLI for governance actions only;"
            " keep research, drafting, coding, and debugging inside"
            f" {self._host_display_name()}."
        )

    def _section_seeai_never_do(self) -> str:
        return (
            "## Never do this\n"
            "\n"
            "- Never skip research, the three compact core documents, or Spec entirely.\n"
            "- Never expand SEEAI mode back into the full standard Super Dev long chain unless the user explicitly asks to switch modes.\n"
            "- Never stop after frontend to wait for a separate preview gate in SEEAI mode.\n"
            "- Never sacrifice baseline polish and demoability just to move fast.\n"
        )

    def _section_error_recovery(self) -> str:
        return (
            "## 错误恢复策略\n"
            "\n"
            "遇到错误时按以下优先级恢复：\n"
            "\n"
            "**阶段 1 -- 便宜恢复（不丢失上下文）**\n"
            '- Token 超限？注入"继续，不要回顾"然后重试\n'
            "- 工具失败？注入错误详情 + 备选方案，继续\n"
            "- 权限拒绝？说明允许什么，继续\n"
            "\n"
            "**阶段 2 -- 上下文重建（可能丢失细节）**\n"
            "- Prompt 过长？压缩旧上下文，保留最近内容\n"
            "- 多次失败？丢弃非关键历史，只保留关键决策\n"
            "\n"
            "**阶段 3 -- 暴露错误（无法恢复）**\n"
            "- 提供: 什么失败了 + 为什么 + 下一步建议\n"
            "- 运行 `super-dev doctor --fix` 尝试自动修复\n"
            "\n"
            "永远不要在尝试阶段 1-2 之前就暴露错误给用户。"
        )

    def _section_agent_teams(self) -> str:
        return (
            "## Agent Teams 协作（支持 Teams 功能的宿主）\n"
            "\n"
            "如果宿主支持 Agent Teams（如 Claude Code 的 /teams），"
            "可以让多位 Super Dev 专家并行工作：\n"
            "\n"
            "**研究阶段**: PM + ARCHITECT 并行调研\n"
            "**文档阶段**: PRD / Architecture / UIUX 可并行起草\n"
            "**编码阶段**: 前端 + 后端可并行开发（注意 API 契约对齐）\n"
            "**质量阶段**: Security + QA + Performance 并行审查\n"
            "\n"
            "使用 Teams 时的约束：\n"
            "- 每个 teammate 必须声明自己的专家角色\n"
            "- teammates 之间通过共享文件（output/*.md）传递上下文\n"
            "- 修改同一文件前必须协调（避免冲突）\n"
            "- 质量门禁结果必须等所有 teammates 完成后汇总"
        )

    def _section_flow_contract(self) -> str:
        return (
            "## Super Dev System Flow Contract\n"
            "\n"
            "- SUPER_DEV_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>"
            "frontend>preview_confirm>backend>quality>delivery\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: required\n"
            "- HOST_PARITY: required"
        )

    def _section_seeai_flow_contract(self) -> str:
        return (
            "## Super Dev SEEAI Flow Contract\n"
            "\n"
            "- SUPER_DEV_SEEAI_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>build_fullstack>polish>handoff\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: omitted\n"
            "- QUALITY_STYLE: speed_with_showcase_quality"
        )

    def _host_display_name(self) -> str:
        display_map = {
            "codex-cli": "Codex",
            "claude-code": "Claude Code",
            "cursor": "Cursor",
            "cursor-cli": "Cursor",
            "windsurf": "Windsurf",
        }
        return display_map.get(self.host, "the host")


class SkillTemplate:
    """Renders a complete SKILL.md file from frontmatter + body content."""

    def __init__(
        self,
        frontmatter: SkillFrontmatter,
        content: SuperDevSkillContent,
    ) -> None:
        self.frontmatter = frontmatter
        self.content = content

    def render(self, host: str) -> str:
        """Render the full SKILL.md content for the given host."""
        fm_lines = self.frontmatter.to_yaml_lines(host)
        fm_block = "---\n" + "\n".join(fm_lines) + "\n---"
        body = self.content.render_body()
        return fm_block + "\n" + body

    @classmethod
    def for_builtin(cls, skill_name: str, host: str) -> SkillTemplate:
        """Factory: create a template pre-configured for the built-in skill."""
        if skill_name == SEEAI_SKILL_NAME:
            if host == "codex-cli":
                fm = SkillFrontmatter(
                    name=skill_name,
                    description="Activate the Super Dev SEEAI competition mode inside Codex CLI.",
                    when_to_use=(
                        "Use when the user says /super-dev-seeai, super-dev-seeai:,"
                        " or super-dev-seeai： followed by a requirement."
                        " Activate the fast competition delivery mode."
                    ),
                )
            else:
                fm = SkillFrontmatter(
                    name=skill_name,
                    description=(
                        "Super Dev SEEAI competition mode for fast, high-quality"
                        " showcase delivery under tight time limits"
                    ),
                    when_to_use=(
                        "Use when the user says /super-dev-seeai, super-dev-seeai:,"
                        " or super-dev-seeai： followed by a requirement."
                        " Activate the competition fast mode."
                    ),
                )
            content = SuperDevSkillContent(skill_name=skill_name, host=host)
            return cls(frontmatter=fm, content=content)
        if host == "codex-cli":
            fm = SkillFrontmatter(
                name=skill_name,
                description="Activate the Super Dev pipeline inside Codex CLI.",
            )
        else:
            fm = SkillFrontmatter(
                name=skill_name,
                description=(
                    "Super Dev pipeline governance for research-first,"
                    " commercial-grade AI coding delivery"
                ),
            )
        content = SuperDevSkillContent(skill_name=skill_name, host=host)
        return cls(frontmatter=fm, content=content)
