"""IntegrationManager content builder mixin helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .. import __version__
from ..seeai_design_system import (
    SEEAI_EXECUTION_GUARDRAILS,
    SEEAI_FAILURE_PROTOCOL,
    SEEAI_MODULE_TRUTH_RULES,
    get_seeai_archetype_playbooks,
    get_seeai_design_packs,
)
from ..skills.skill_template import SkillTemplate


class IntegrationManagerContentMixin:
    def _conversation_continuity_contract_en(self) -> str:
        return (
            "## Conversation Continuity Contract\n"
            "- If `.super-dev/SESSION_BRIEF.md` exists, read it before responding and treat it as the active workflow state.\n"
            "- If the workflow is waiting for docs confirmation, preview confirmation, UI revision, architecture revision, or quality revision, then user replies like `修改`, `补充`, `继续改`, `确认`, `通过`, `继续`, or detailed feedback remain inside the current Super Dev stage.\n"
            "- After each requested revision inside a gate, stay in the same stage, update the required artifacts, summarize what changed, and wait again for explicit confirmation.\n"
            "- Do not silently exit Super Dev mode because the user asked for several edits, follow-up questions, or extra constraints.\n"
            "- Only leave the current Super Dev workflow if the user explicitly says to cancel the workflow, restart from scratch, or switch back to normal chat.\n\n"
        )

    def _build_kiro_global_steering_content(self) -> str:
        return (
            "---\n"
            "inclusion: manual\n"
            "name: super-dev\n"
            "description: Super Dev global steering for research-first commercial-grade delivery\n"
            "---\n\n"
            "# Super Dev Global Steering\n\n"
            "This global steering file activates Super Dev governance for Kiro workspaces that opt into the pipeline.\n\n"
            "## Activation\n"
            "- Prefer `/super-dev <需求描述>` when the current Kiro host surface exposes the Super Dev slash or skill entry.\n"
            "- If the current Kiro session only accepts natural language, treat `super-dev: ...` as the fallback and enter the Super Dev workflow immediately.\n"
            "- Treat project-local `.kiro/steering/super-dev.md` as long-term steering context, while `.kiro/skills/` remains the explicit task/skill execution surface.\n\n"
            "## Required Sequence\n"
            "1. Research first\n"
            "2. Draft PRD, architecture, and UIUX\n"
            "3. Stop for user confirmation\n"
            "4. Create Spec/tasks only after confirmation\n"
            "5. Frontend runtime verification before backend and delivery\n\n"
            "## Boundary\n"
            "- Kiro remains the execution host.\n"
            "- Super Dev is the governance layer and local Python tooling, not a separate model platform.\n"
        )

    def _build_kiro_steering_content(self, target: str) -> str:
        frontmatter = (
            "---\n"
            "inclusion: auto\n"
            "name: super-dev\n"
            "description: Super Dev pipeline governance for research-first commercial-grade delivery\n"
            "---\n\n"
        )
        input_block = (
            "## Slash Input\n"
            "- Requirement: `$ARGUMENTS`\n"
            "- If slash arguments are empty, ask the user to restate the requirement and stay inside Super Dev mode.\n\n"
            "## Host-First Execution Rule\n"
            "- Do the real work inside the host after `/super-dev` is triggered; do not bounce normal development back into `super-dev pipeline`.\n"
            "- Only return to the terminal for maintenance actions: `super-dev`, `super-dev update`, or `super-dev uninstall`.\n\n"
        )
        rules = (
            self._generic_cli_rules(target)
            if target == "kiro-cli"
            else self._generic_ide_rules(target)
        )
        return frontmatter + input_block + rules

    def _build_codebuddy_rule_content(self) -> str:
        return (
            "---\n"
            'description: "Super Dev pipeline governance for CodeBuddy. Activate on /super-dev or super-dev:"\n'
            "alwaysApply: true\n"
            "---\n\n"
            f"{self._generic_ide_rules('codebuddy')}"
        )

    def setup_all(self, force: bool = False) -> dict[str, list[Path]]:
        result: dict[str, list[Path]] = {}
        for target in self.TARGETS:
            result[target] = self.setup(target=target, force=force)
        return result

    def _upsert_managed_block(
        self,
        *,
        file_path: Path,
        begin: str,
        end: str,
        block_content: str,
    ) -> bool:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        managed = f"{begin}\n{block_content.rstrip()}\n{end}\n"
        if begin in existing and end in existing:
            start = existing.index(begin)
            stop = existing.index(end, start) + len(end)
            updated = f"{existing[:start]}{managed}{existing[stop:]}"
        elif existing.strip():
            spacer = (
                "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
            )
            updated = f"{existing}{spacer}{managed}"
        else:
            updated = managed
        if updated == existing:
            return False
        file_path.write_text(updated, encoding="utf-8")
        return True

    def _remove_managed_block(
        self,
        *,
        file_path: Path,
        begin: str,
        end: str,
    ) -> bool:
        if not file_path.exists():
            return False
        existing = file_path.read_text(encoding="utf-8")
        if begin not in existing or end not in existing:
            return False
        start = existing.index(begin)
        stop = existing.index(end, start) + len(end)
        if stop < len(existing) and existing[stop : stop + 1] == "\n":
            stop += 1
        updated = existing[:start] + existing[stop:]
        updated = updated.strip()
        if not updated:
            file_path.unlink(missing_ok=True)
            return True
        file_path.write_text(updated + "\n", encoding="utf-8")
        return True

    def setup_slash_command(self, target: str, force: bool = False) -> Path | None:
        return self.setup_slash_command_for_scope(target=target, force=force, scope="project")

    def setup_seeai_slash_command(self, target: str, force: bool = False) -> Path | None:
        return self.setup_seeai_slash_command_for_scope(target=target, force=force, scope="project")

    def setup_global_slash_command(self, target: str, force: bool = False) -> Path | None:
        return self.setup_slash_command_for_scope(target=target, force=force, scope="global")

    def setup_global_seeai_slash_command(self, target: str, force: bool = False) -> Path | None:
        return self.setup_seeai_slash_command_for_scope(target=target, force=force, scope="global")

    def setup_slash_command_for_scope(
        self, target: str, force: bool = False, scope: str = "project"
    ) -> Path | None:
        if not self.supports_slash(target):
            return None
        command_file = self.resolve_slash_command_path(
            target=target,
            scope=scope,
            project_dir=self.project_dir,
        )
        if command_file.exists() and not force:
            return None
        command_file.parent.mkdir(parents=True, exist_ok=True)
        builder = (
            self._build_toml_command_content
            if command_file.suffix == ".toml"
            else self._build_slash_command_content
        )
        command_content = self._append_flow_contract(
            content=builder(target),
            relative=command_file.name,
        )
        command_file.write_text(command_content, encoding="utf-8")
        return command_file

    def setup_seeai_slash_command_for_scope(
        self,
        target: str,
        force: bool = False,
        scope: str = "project",
    ) -> Path | None:
        if not self.supports_slash(target):
            return None
        command_file = self.resolve_seeai_slash_command_path(
            target=target,
            scope=scope,
            project_dir=self.project_dir,
        )
        if command_file.exists() and not force:
            return None
        command_file.parent.mkdir(parents=True, exist_ok=True)
        builder = (
            self._build_seeai_toml_command_content
            if command_file.suffix == ".toml"
            else self._build_seeai_slash_command_content
        )
        command_content = self._append_flow_contract(
            content=builder(target),
            relative=command_file.name,
        )
        command_file.write_text(command_content, encoding="utf-8")
        return command_file

    @classmethod
    def resolve_slash_command_path(
        cls,
        *,
        target: str,
        scope: str,
        project_dir: Path | None = None,
    ) -> Path:
        if not cls.supports_slash(target):
            raise ValueError(f"Unsupported target: {target}")

        if scope == "project":
            if project_dir is None:
                raise ValueError("project_dir is required when scope='project'")
            relative = cls.SLASH_COMMAND_FILES[target]
            return Path(project_dir).resolve() / relative

        if scope == "global":
            relative = cls.GLOBAL_SLASH_COMMAND_FILES.get(target, cls.SLASH_COMMAND_FILES[target])
            return Path.home() / relative

        raise ValueError(f"Unsupported slash scope: {scope}")

    @classmethod
    def resolve_seeai_slash_command_path(
        cls,
        *,
        target: str,
        scope: str,
        project_dir: Path | None = None,
    ) -> Path:
        base = cls.resolve_slash_command_path(target=target, scope=scope, project_dir=project_dir)
        return base.with_name(base.name.replace("super-dev", "super-dev-seeai"))

    @classmethod
    def supports_slash(cls, target: str) -> bool:
        from ..host_registry import get_host_definition
        from ..host_registry import supports_slash as registry_supports_slash

        if get_host_definition(target) is not None:
            return registry_supports_slash(target)
        return target in cls.SLASH_COMMAND_FILES and target not in cls.NO_SLASH_TARGETS

    @classmethod
    def requires_skill(cls, target: str) -> bool:
        return target not in cls.NO_SKILL_TARGETS

    def setup_all_slash_commands(self, force: bool = False) -> dict[str, Path | None]:
        result: dict[str, Path | None] = {}
        for target in self.TARGETS:
            result[target] = self.setup_slash_command(target=target, force=force)
        return result

    def _build_content(self, target: str) -> str:
        return self._build_file_content(target=target, relative="")

    def _build_file_content(self, target: str, relative: str) -> str:
        if target in {"codex", "codex-cli"} and relative == "AGENTS.md":
            return self._build_codex_agents_content()

        if target == "claude-code" and relative in {"CLAUDE.md", ".claude/CLAUDE.md"}:
            return self._claude_rules()

        if target == "claude-code" and relative == ".claude-plugin/marketplace.json":
            return self._build_claude_repo_marketplace_content()

        if (
            target == "claude-code"
            and relative == "plugins/super-dev-claude/.claude-plugin/plugin.json"
        ):
            return self._build_claude_plugin_manifest_content()

        if target == "claude-code" and relative == "plugins/super-dev-claude/README.md":
            return self._build_claude_plugin_readme_content()

        if target == "claude-code" and relative == "plugins/super-dev-claude/commands/super-dev.md":
            return self._build_slash_command_content("claude-code")

        if target in {"codex", "codex-cli"} and relative == ".agents/plugins/marketplace.json":
            return self._build_codex_repo_marketplace_content()

        if (
            target in {"codex", "codex-cli"}
            and relative == "plugins/super-dev-codex/.codex-plugin/plugin.json"
        ):
            return self._build_codex_plugin_manifest_content()

        if target in {"codex", "codex-cli"} and relative == "plugins/super-dev-codex/README.md":
            return self._build_codex_plugin_readme_content()

        if (
            target in {"codex", "codex-cli"}
            and relative == "plugins/super-dev-codex/skills/super-dev/SKILL.md"
        ):
            return self._build_codex_plugin_skill_content(skill_name="super-dev")

        if (
            target in {"codex", "codex-cli"}
            and relative == "plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md"
        ):
            return self._build_codex_plugin_skill_content(skill_name="super-dev-seeai")

        if target == "claude-code" and relative.endswith(".claude/agents/super-dev.md"):
            return self._build_claude_agent_content()

        if target in {"codebuddy", "codebuddy-cn"} and relative.endswith(
            ".codebuddy/rules/super-dev/RULE.mdc"
        ):
            return self._build_codebuddy_rule_content()

        if target in {"codebuddy", "codebuddy-cn"} and relative.endswith(
            ".codebuddy/agents/super-dev.md"
        ):
            return self._build_codebuddy_agent_content()

        if target == "opencode" and relative.endswith(".opencode/agents/super-dev.md"):
            return self._build_opencode_agent_content()

        if target in {"qoder", "qoder-cli"} and relative.endswith(".qoder/agents/super-dev.md"):
            return self._build_qoder_agent_content()

        if target == "copilot-cli" and relative.endswith(".github/agents/super-dev.md"):
            return self._build_copilot_agent_content()

        if target == "qwen-code" and relative.endswith(".qwen/agents/super-dev.md"):
            return self._build_qwen_agent_content()

        if target in {"trae", "trae-cn"}:
            return self._trae_rules()

        if relative.endswith("/skills/super-dev/SKILL.md") or relative.endswith(
            "/skills/super-dev-seeai/SKILL.md"
        ):
            return self._build_embedded_skill_content(target=target, relative=relative)

        if relative.endswith("/commands/super-dev.toml"):
            return self._build_toml_command_content(target)
        if relative.endswith("/commands/super-dev-seeai.toml"):
            return self._build_seeai_toml_command_content(target)

        # Route command files to slash command content generator
        if relative.endswith("/commands/super-dev.md"):
            return self._build_slash_command_content(target)
        if relative.endswith("/commands/super-dev-seeai.md") or relative.endswith(
            "/workflows/super-dev-seeai.md"
        ):
            return self._build_seeai_slash_command_content(target)

        if target in {"cursor", "cursor-cli"}:
            rules_body = (
                "# Super Dev Pipeline Rules\n"
                "- When the user triggers `/super-dev ...`, enter Super Dev pipeline mode immediately.\n"
                "- Start with research and write output/*-research.md as a real file in the repository.\n"
                "- Always read and maintain output/*-prd.md, output/*-architecture.md, and output/*-uiux.md as source-of-truth project files.\n"
                "- Summarize the three core documents to the user and wait for user confirmation before creating Spec/tasks or writing code.\n"
                "- Create Spec/tasks only after confirmation.\n"
                "- Execute frontend-first delivery before backend/database tasks, then run quality gate before release.\n"
                "- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from output/*-uiux.md.\n"
                "- Do not use emoji as functional icons or placeholders.\n"
                "- For non-conversational AI products, avoid Claude / ChatGPT-style sidebar chat shells unless the UI plan explicitly justifies them.\n"
                "- Keep using the component ecosystem and design token direction defined in output/*-uiux.md rather than switching ad hoc.\n"
                "- If `.super-dev/SESSION_BRIEF.md` exists, read it before responding and keep the current Super Dev gate active across follow-up edits.\n"
                "\n## Coding Constraints (active during ALL coding phases)\n"
                "- Before writing ANY code, run `cat package.json` to check framework versions. If unsure, read official docs first.\n"
                "- Icons MUST come from Lucide/Heroicons/Tabler. No emoji as icons. No purple/pink gradient themes.\n"
                "- Frontend fetch URLs must exactly match backend route definitions.\n"
                "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
                "- After completing a feature, run build + lint. Fix errors before moving on.\n"
            )
            cursor_template = self.templates_dir / ".cursorrules.template"
            if cursor_template.exists():
                body = cursor_template.read_text(encoding="utf-8")
                rules_body = f"{body}\n\n{rules_body}"
            return (
                "---\n"
                'description: "Super Dev pipeline governance - research-first commercial-grade delivery. Activates when user says /super-dev or super-dev:"\n'
                "alwaysApply: true\n"
                "---\n\n"
                f"{rules_body}"
            )

        if target in {"kiro", "kiro-cli"} and relative.endswith("steering/super-dev.md"):
            return self._build_kiro_steering_content(target)

        if target == "antigravity":
            if relative.endswith(".agent/workflows/super-dev.md"):
                return self._antigravity_workflow_rules()
            return self._build_antigravity_context_content()

        if target in {
            "cursor",
            "windsurf",
            "cline",
            "continue",
            "vscode-copilot",
            "kilo-code",
            "roo-code",
            "augment",
            "qoder",
            "qwen-code",
            "kiro",
            "trae",
            "trae-cn",
            "trae-solo",
            "trae-solocn",
            "codebuddy",
            "codebuddy-cn",
            "tongyi-lingma",
            "codegeex",
        }:
            return self._generic_ide_rules(target)

        if target in {
            "codex",
            "codex-cli",
            "copilot-cli",
            "droid-cli",
            "opencode",
            "gemini-cli",
            "kimi-code",
            "kiro-cli",
            "cursor-cli",
            "qoder-cli",
            "codebuddy-cli",
            "qwen-code",
        }:
            return self._generic_cli_rules(target)

        if target == "claude-code":
            return self._claude_rules()

        return self._generic_cli_rules(target)

    def _build_codex_agents_content(self) -> str:
        return (
            "# Super Dev for Codex CLI\n\n"
            "Treat Codex App/Desktop selecting `super-dev` or `super-dev-seeai` from the `/` list, Codex CLI explicit `$super-dev` / `$super-dev-seeai`, and natural-language `super-dev:` / `super-dev：` / `super-dev-seeai:` / `super-dev-seeai：` messages as valid Super Dev entry points.\n\n"
            "If the repository already contains active Super Dev workflow context, the first natural-language requirement in a new session must also continue Super Dev rather than normal chat.\n\n"
            "## Direct Activation Rule\n"
            "- Do not spend a turn saying you will read the skill first, explain the skill, or decide whether to enter the workflow.\n"
            "- Treat the current trigger as already authorized to execute the full Super Dev pipeline.\n"
            "- If a compatibility skill under `~/.codex/skills/` is loaded, treat it as the same Super Dev contract, not a fallback mode.\n\n"
            "## Preferred official entry order\n"
            "- Codex App/Desktop: prefer selecting `super-dev` from the `/` list. This is the enabled Skill entry, not a custom project slash command file.\n"
            "- Codex CLI: prefer explicit `$super-dev`.\n"
            "- Natural-language fallback for both surfaces: `super-dev: <需求描述>` or `super-dev：<需求描述>` through AGENTS.md.\n\n"
            "## SEEAI Competition Mode\n"
            "- If the user triggers `super-dev-seeai`, enter the SEEAI competition-fast contract instead of the standard long chain.\n"
            "- SEEAI keeps research -> compact docs -> docs confirmation -> compact spec, then goes directly into a full-stack sprint and final polish.\n"
            "- SEEAI still requires real files in `output/`, but the documents must stay compact and competition-oriented.\n\n"
            "## Required execution\n"
            "1. First reply: state that Super Dev pipeline mode is active and the current phase is `research`.\n"
            "2. Read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` when available.\n"
            "3. Use Codex native web/search/edit/terminal capabilities to perform similar-product research and write `output/*-research.md` into the repository workspace.\n"
            "4. Draft `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` in the same Codex session and save them as actual project files.\n"
            "5. Stop after the three core documents, summarize them, and wait for explicit confirmation.\n"
            "6. Only after confirmation, create `.super-dev/changes/*/proposal.md` and `.super-dev/changes/*/tasks.md`, then continue with frontend-first implementation.\n\n"
            "## Constraints\n"
            "- Do not start coding directly after `/super-dev` skill entry, `$super-dev`, `super-dev:`, or `super-dev：`.\n"
            "- Do not create Spec before document confirmation.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, first fix the issues, rerun the quality gate, refresh any delivery evidence the reports ask for, and only then continue.\n"
            "- 开始任何 UI 实现前，必须先锁定 `output/*-uiux.md` 中冻结的图标库、字体系统、design token system、组件生态和页面骨架。\n"
            "- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style sidebar chat shells unless the UI plan explicitly justifies them.\n"
            "- Keep using the component ecosystem and design token direction defined in `output/*-uiux.md` rather than switching ad hoc.\n"
            "- If a required artifact is only described in chat and not written into the repository, treat the step as incomplete.\n"
            "- Codex remains the execution host; Super Dev is the local governance workflow.\n"
            "- Use local `super-dev` CLI only for governance actions such as doctor, review, quality, release readiness, or update; do not outsource the main coding workflow to the CLI.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Super Dev System Flow Contract\n"
            "- SUPER_DEV_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: required\n"
            "- HOST_PARITY: required\n"
        )

    def _build_codex_repo_marketplace_content(self) -> str:
        payload = {
            "name": "super-dev-local",
            "interface": {
                "displayName": "Super Dev Local Plugins",
            },
            "plugins": [
                {
                    "name": "super-dev-codex",
                    "source": {
                        "source": "local",
                        "path": "./plugins/super-dev-codex",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def _build_codex_plugin_manifest_content(self) -> str:
        payload = {
            "name": "super-dev-codex",
            "version": __version__,
            "description": "Codex App/Desktop enhancement bundle for the full Super Dev pipeline.",
            "author": {
                "name": "Shangyan Technology",
                "email": "11964948@qq.com",
                "url": "https://github.com/shangyankeji/super-dev",
            },
            "homepage": "https://github.com/shangyankeji/super-dev",
            "repository": "https://github.com/shangyankeji/super-dev",
            "license": "MIT",
            "keywords": ["codex", "super-dev", "workflow", "skills", "agents"],
            "skills": "./skills/",
            "interface": {
                "displayName": "Super Dev for Codex",
                "shortDescription": "Research-first governed delivery pipeline for Codex App/Desktop.",
                "longDescription": "Adds a repo-local Codex plugin surface for Super Dev so Codex App/Desktop can expose the same governed research -> docs -> confirmation -> implementation flow more consistently alongside AGENTS.md and Skills.",
                "developerName": "Shangyan Technology",
                "category": "Productivity",
                "capabilities": ["Interactive", "Write"],
                "websiteURL": "https://github.com/shangyankeji/super-dev",
                "privacyPolicyURL": "https://github.com/shangyankeji/super-dev/blob/main/README_EN.md",
                "termsOfServiceURL": "https://github.com/shangyankeji/super-dev/blob/main/README_EN.md",
                "defaultPrompt": [
                    "Use Super Dev to research and design this product before coding.",
                    "Continue the current Super Dev workflow from the active gate.",
                    "Review the current repository and resume the Super Dev pipeline.",
                ],
                "brandColor": "#2563EB",
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def _build_codex_plugin_readme_content(self) -> str:
        return (
            "# Super Dev Codex Plugin\n\n"
            "This is an optional local Codex plugin scaffold for repositories that want a richer Codex App/Desktop surface than `AGENTS.md + Skills` alone.\n\n"
            "It does not replace the official Super Dev Codex integration surfaces:\n\n"
            "- `AGENTS.md`\n"
            "- `.agents/skills/super-dev/SKILL.md`\n"
            "- `CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`, only when explicitly enabling `--with-user-surfaces`)\n"
            "- `~/.agents/skills/super-dev/SKILL.md`\n\n"
            "Use this plugin scaffold as an advanced Codex App/Desktop enhancement when you want the repository to expose a repo-local plugin entry in addition to the official AGENTS/Skills model.\n\n"
            "Plugin root:\n\n"
            "- `.codex-plugin/plugin.json`\n"
            "- `skills/super-dev/SKILL.md`\n"
            "- optional legacy compatibility alias files may still exist for cleanup or migration, but the public skill name remains `super-dev`.\n\n"
            "Marketplace entry:\n\n"
            "- `.agents/plugins/marketplace.json`\n\n"
            "The plugin skill should behave exactly like the main Codex Super Dev workflow:\n\n"
            "- App/Desktop slash list entry: `super-dev`\n"
            "- App/Desktop SEEAI slash list entry: `super-dev-seeai`\n"
            "- CLI explicit skill mention: `$super-dev`\n"
            "- CLI explicit SEEAI skill mention: `$super-dev-seeai`\n"
            "- AGENTS fallback: `super-dev: <需求描述>`\n"
            "- Existing-project work (`evolve` / `variant` / `patch`) must baseline the repository before docs/spec.\n"
            "- Resume is a first-class default path: continue with `super-dev: 继续当前流程` or `super-dev-run: resume` when the host does not support slash.\n"
        )

    def _build_codex_plugin_skill_content(self, *, skill_name: str) -> str:
        if skill_name == "super-dev-seeai":
            return (
                "---\n"
                "name: super-dev-seeai\n"
                "description: Super Dev SEEAI Codex App/Desktop competition entry.\n"
                "when_to_use: Use when the user wants the fast competition flow inside Codex App/Desktop.\n"
                f"version: {__version__}\n"
                "---\n\n"
                "# Super Dev SEEAI for Codex Plugin\n\n"
                "- Treat this as the competition-fast mode for showcase builds.\n"
                "- Enter research first, then compact PRD / architecture / UIUX, wait for docs confirmation, create compact Spec, and move into one integrated build sprint.\n"
                "- Do not expand back into the standard preview gate unless the user explicitly switches modes.\n"
                "- Keep the result demoable, visually intentional, and runnable.\n"
            )
        return (
            "---\n"
            "name: super-dev\n"
            "description: Super Dev Codex App/Desktop plugin entry.\n"
            "when_to_use: Use when the user wants to enter or resume the Super Dev pipeline inside Codex App/Desktop.\n"
            f"version: {__version__}\n"
            "---\n\n"
            "# Super Dev for Codex Plugin\n\n"
            "## Activation Contract\n\n"
            "- If this plugin skill is invoked, Super Dev pipeline mode is already active.\n"
            "- Do not explain the skill or summarize what it is before acting.\n"
            "- Treat the Codex App/Desktop `/`-list entry `super-dev` as equivalent to Codex CLI `$super-dev`.\n"
            "- If `AGENTS.md` or `.super-dev/SESSION_BRIEF.md` exists, read them before replying.\n\n"
            "## Required First Reply\n\n"
            "- State that Super Dev pipeline mode is active.\n"
            "- State that the current phase is `research`, unless `.super-dev/SESSION_BRIEF.md` shows an active confirmation or revision gate.\n"
            "- Promise to stop after research + PRD + architecture + UIUX for explicit confirmation before implementation.\n\n"
            "## Required Workflow\n\n"
            "1. Detect whether the work is `new`, `evolve`, `variant`, `patch`, or `resume`.\n"
            "2. For `evolve`, `variant`, and `patch`, baseline the current repository first and write `output/*-baseline-audit.md` / `.json` before docs/spec.\n"
            "3. Read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` when present.\n"
            "4. Produce `output/*-research.md`.\n"
            "5. Produce `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md`.\n"
            "6. Wait for explicit confirmation.\n"
            "7. Only then create `.super-dev/changes/*/proposal.md` and `.super-dev/changes/*/tasks.md`.\n"
            "8. Implement frontend first, then backend, then quality and delivery.\n\n"
            "## Continuity Rules\n\n"
            "- If the workflow is already waiting for docs confirmation, preview confirmation, UI revision, architecture revision, or quality revision, stay inside the current Super Dev gate.\n"
            "- User replies like `修改`, `补充`, `继续改`, `确认`, `通过`, `继续` remain inside the current gate.\n"
            "- Resume is a normal path: after reopening the host, continue from `.super-dev/SESSION_BRIEF.md`, workflow state, review state, and `output/*` rather than restarting from scratch.\n"
            "- Do not silently fall back to ordinary chat.\n\n"
            "## UI Rules\n\n"
            "- Lock icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md` before any UI implementation.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style chat shells unless the UI plan explicitly justifies them.\n"
        )

    def _build_claude_repo_marketplace_content(self) -> str:
        payload = {
            "name": "super-dev-local",
            "plugins": [
                {
                    "name": "super-dev-claude",
                    "source": "./plugins/super-dev-claude",
                    "version": __version__,
                }
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def _build_claude_plugin_manifest_content(self) -> str:
        payload = {
            "name": "super-dev-claude",
            "version": __version__,
            "description": "Claude Code enhancement bundle for the full Super Dev pipeline.",
            "author": {
                "name": "Shangyan Technology",
                "email": "11964948@qq.com",
            },
            "homepage": "https://github.com/shangyankeji/super-dev",
            "repository": "https://github.com/shangyankeji/super-dev",
            "license": "MIT",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    def _build_claude_plugin_readme_content(self) -> str:
        return (
            "# Super Dev Claude Plugin\n\n"
            "This is an optional repo-local Claude Code plugin enhancement.\n\n"
            "Primary Claude integration surfaces remain:\n\n"
            "- `CLAUDE.md`\n"
            "- `.claude/CLAUDE.md` (compatibility mirror)\n"
            "- `.claude/skills/super-dev/SKILL.md`\n"
            "- `~/.claude/CLAUDE.md`\n"
            "- `~/.claude/skills/super-dev/SKILL.md`\n\n"
            "Compatibility enhancement surfaces remain available:\n\n"
            "- `.claude/commands/super-dev.md`\n"
            "This plugin enhancement adds a repo-local Claude plugin surface through:\n\n"
            "- `.claude-plugin/marketplace.json`\n"
            "- `plugins/super-dev-claude/.claude-plugin/plugin.json`\n"
            "- `plugins/super-dev-claude/commands/super-dev.md`\n"
            "- `plugins/super-dev-claude/skills/super-dev/SKILL.md`\n"
        )

    def _build_claude_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: Activate the Super Dev pipeline for research-first, commercial-grade project delivery. Use when user says /super-dev or super-dev: followed by a requirement.\n"
            "model: inherit\n"
            "---\n"
            "# Super Dev Subagent\n\n"
            "You are the Claude Code subagent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `/super-dev ...` as the entry point into the Super Dev pipeline.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n"
            "- Use the local Python `super-dev` CLI for governance artifacts, checks, and delivery reports.\n"
            "- Use the host's native tools for browsing, coding, terminal execution, and debugging.\n\n"
            "## First Response Contract\n"
            "- On the first reply after `/super-dev ...`, explicitly say Super Dev pipeline mode is active.\n"
            "- If the repository already has active Super Dev workflow context, the first natural-language requirement in a new host session must also continue Super Dev rather than plain chat.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as workspace files.\n"
            "- chat-only summaries do not count as completion.\n"
            "- If a required artifact is missing from the workspace, keep working until it is written.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Implementation Closure Contract\n"
            "- After each code change, do a minimal diff review before claiming completion.\n"
            "- Run project-native build / compile / type-check / test / runtime smoke when available.\n"
            "- Ensure newly added functions, methods, fields, modules, and log hooks are wired into real call paths; delete them if unused.\n"
            "- Do not leave newly introduced unused code, dead branches, or helper functions that are only defined but never called.\n"
            "- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style chat shells unless the UI plan explicitly justifies them.\n"
            "- Keep using the design token direction and component ecosystem frozen in `output/*-uiux.md` rather than switching ad hoc.\n\n"
            "## Boundary\n"
            "- Claude Code remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Prefer repository-local rules and commands as the source of project-specific context.\n"
        )

    def _build_codebuddy_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: CodeBuddy subagent that activates the Super Dev pipeline for research-first, commercial-grade delivery.\n"
            "---\n"
            "# Super Dev Agent\n\n"
            "You are the CodeBuddy agent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `/super-dev ...` as the entry point into the Super Dev pipeline.\n"
            "- Treat `/super-dev-seeai ...` and `super-dev-seeai: ...` as the entry points into the SEEAI competition-fast pipeline.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n"
            "- Use the local Python `super-dev` CLI for governance artifacts, checks, and delivery reports.\n"
            "- Use CodeBuddy native tools for browsing, coding, terminal execution, and debugging.\n\n"
            "## SEEAI Competition Mode\n"
            "- In SEEAI mode, keep research -> compact docs -> docs confirmation -> compact spec, then go straight into one integrated full-stack sprint.\n"
            "- Bias toward one project-bound Agent Chat, fast P0/P1/P2 scoping, and strong demoability within a 30-minute timebox.\n"
            "- If slash command indexing lags, continue in the same session with `super-dev-seeai: <需求>` instead of switching out of the mode.\n\n"
            "## First Response Contract\n"
            "- On the first reply after `/super-dev ...`, explicitly say Super Dev pipeline mode is active.\n"
            "- On the first reply after `/super-dev-seeai ...` or `super-dev-seeai: ...`, explicitly say Super Dev SEEAI competition mode is active.\n"
            "- If the repository already has active Super Dev workflow context, the first natural-language requirement in a new host session must also continue Super Dev rather than plain chat.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as real workspace files.\n"
            "- Do not treat chat-only explanations as completed deliverables.\n"
            "- If a required artifact is not present in the repository, continue until it is written.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Implementation Closure Contract\n"
            "- After each code change, do a minimal diff review before claiming completion.\n"
            "- Run project-native build / compile / type-check / test / runtime smoke when available.\n"
            "- Ensure newly added functions, methods, fields, modules, and log hooks are wired into real call paths; delete them if unused.\n"
            "- Do not leave newly introduced unused code, dead branches, or helper functions that are only defined but never called.\n"
            "- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style chat shells unless the UI plan explicitly justifies them.\n"
            "- Keep using the design token direction and component ecosystem frozen in `output/*-uiux.md` rather than switching ad hoc.\n\n"
            "## Boundary\n"
            "- CodeBuddy remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Prefer repository-local rules, commands, and this agent file as the source of project-specific context.\n"
        )

    def _build_opencode_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: OpenCode subagent that activates the Super Dev pipeline for research-first commercial delivery.\n"
            "mode: subagent\n"
            "---\n"
            "# Super Dev Agent\n\n"
            "You are the OpenCode subagent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `/super-dev ...` as the project entry point into the Super Dev pipeline.\n"
            "- Treat `super-dev: ...` as the natural-language fallback when the slash list is not the best fit for the current recovery path.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n"
            "- Use the local Python `super-dev` CLI for governance artifacts, quality reports, and delivery evidence.\n\n"
            "## First Response Contract\n"
            "- On the first reply after `/super-dev ...`, explicitly say Super Dev pipeline mode is active.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as real workspace files.\n"
            "- chat-only summaries do not count as completion.\n"
            "- If a required artifact is not present in the repository, continue until it is written.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Boundary\n"
            "- OpenCode remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Keep repository-local `AGENTS.md`, `.opencode/commands/`, `.opencode/skills/`, and this agent file aligned as one contract.\n"
        )

    def _build_qoder_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: Qoder subagent that activates the Super Dev pipeline for research-first commercial delivery.\n"
            "tools: Read, Write, Grep, Glob, Bash\n"
            "---\n"
            "# Super Dev Subagent\n\n"
            "You are the Qoder subagent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `/super-dev ...` as the main entry point into the Super Dev pipeline.\n"
            "- Treat `super-dev: ...` as the natural-language fallback when slash or current recovery context calls for it.\n"
            "- Keep Qoder `AGENTS.md`, `.qoder/rules/`, `.qoder/commands/`, `.qoder/skills/`, and this subagent file aligned.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n\n"
            "## First Response Contract\n"
            "- On the first reply after `/super-dev ...`, explicitly say Super Dev pipeline mode is active.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as real workspace files.\n"
            "- Write documents into the repository workspace instead of only replying in chat.\n"
            "- chat-only summaries do not count as completion.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Boundary\n"
            "- Qoder remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Prefer repository-local `AGENTS.md`, `.qoder/rules/`, `.qoder/commands/`, `.qoder/skills/`, and this subagent file as the source of project context.\n"
        )

    def _build_qwen_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: Qwen Code subagent that activates the Super Dev pipeline for research-first commercial delivery.\n"
            "tools: Read, Write, Grep, Glob, Bash, WebSearch, WebFetch\n"
            "---\n"
            "# Super Dev Subagent\n\n"
            "You are the Qwen Code subagent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `/super-dev ...` as the main entry point into the Super Dev pipeline.\n"
            "- Treat `super-dev: ...` as the natural-language fallback when the current recovery path benefits from text entry.\n"
            "- Keep `QWEN.md`, `.qwen/commands/`, `.qwen/skills/`, and `.qwen/agents/` aligned as one project contract.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n\n"
            "## First Response Contract\n"
            "- On the first reply after `/super-dev ...`, explicitly say Super Dev pipeline mode is active.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as real workspace files.\n"
            "- Write documents into the repository workspace instead of only replying in chat.\n"
            "- chat-only summaries do not count as completion.\n\n"
            "## Session Contract\n"
            "- Use `/resume` to continue a previous Qwen Code session.\n"
            "- Treat `/restore` as checkpoint rollback only, not as the default way to continue the current Super Dev workflow.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Boundary\n"
            "- Qwen Code remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Prefer repository-local `QWEN.md`, `.qwen/commands/`, `.qwen/skills/`, and this subagent file as the source of project context.\n"
        )

    def _build_copilot_agent_content(self) -> str:
        return (
            "---\n"
            "name: super-dev\n"
            "description: Copilot CLI custom agent that activates the Super Dev pipeline for research-first commercial delivery.\n"
            "---\n"
            "# Super Dev Agent\n\n"
            "You are the Copilot CLI custom agent that activates Super Dev governance mode.\n\n"
            "## Purpose\n"
            "- Treat `super-dev: ...` as the main natural-language entry into the Super Dev pipeline.\n"
            "- Keep `AGENTS.md`, `.github/copilot-instructions.md`, `.github/skills/`, and this custom agent aligned as one project contract.\n"
            "- Enforce the sequence: research -> three core docs -> wait for confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n\n"
            "## First Response Contract\n"
            "- On the first reply after a Super Dev entry, explicitly say Super Dev pipeline mode is active.\n"
            "- Explicitly say the current phase is `research`.\n"
            "- Explicitly state that you will read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` first when present.\n"
            "- Explicitly promise that you will stop after PRD, architecture, and UIUX for user confirmation before creating Spec or writing code.\n\n"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` as real workspace files.\n"
            "- Chat-only summaries do not count as completion.\n\n"
            "## Revision Contract\n"
            "- If the user requests UI changes, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime plus UI review.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign Spec/tasks and implementation.\n"
            "- If the user requests quality or security remediation, fix the issues first, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Boundary\n"
            "- Copilot CLI remains the execution host.\n"
            "- Super Dev is the governance layer, not a separate model platform.\n"
            "- Prefer repository-local `AGENTS.md`, `.github/copilot-instructions.md`, `.github/skills/`, and this custom agent as the source of project context.\n"
        )

    def _build_embedded_skill_content(self, target: str, relative: str) -> str:
        if "/skills/super-dev-seeai/SKILL.md" in relative:
            skill_name = "super-dev-seeai"
        else:
            skill_name = "super-dev"
        template = SkillTemplate.for_builtin(skill_name, target)
        return template.render(target)

    def _build_slash_command_content(self, target: str) -> str:
        if target == "windsurf":
            return (
                "---\n"
                "description: Super Dev 流水线式开发编排（先文档/Spec，再编码）\n"
                "---\n\n"
                "# /super-dev (windsurf)\n\n"
                "在当前项目触发 Super Dev 流水线。\n\n"
                "## 输入\n"
                "- 需求描述: `$ARGUMENTS`\n\n"
                "## 定位边界\n"
                "- 宿主负责调用自身模型、工具与实际编码。\n"
                "- Super Dev 负责流程规范、质量门禁、审计产物与交付标准。\n\n"
                "## 本地知识库要求\n"
                "- 先读取当前项目 `knowledge/` 下与需求相关的知识文件。\n"
                "- 若存在 `output/knowledge-cache/*-knowledge-bundle.json`，必须先读取其中的 `local_knowledge`、`web_knowledge` 与 `research_summary`。\n"
                "- 命中的本地知识应被继承到 PRD / 架构 / UIUX / Spec，而不是只停留在 research 文档。\n\n"
                "## 强制执行顺序\n"
                "1. 先使用宿主原生联网 / browse / search 研究同类产品，沉淀 `output/*-research.md`\n"
                "2. 再生成 `output/*-prd.md`、`output/*-architecture.md`、`output/*-uiux.md`\n"
                "3. 三份文档完成后，先向用户汇报文档摘要与路径，等待明确确认；未经确认不得创建 Spec 或开始编码\n"
                "4. 用户确认后，再生成 `.super-dev/changes/*/proposal.md` 与 `tasks.md`\n"
                "5. 先实现并运行前端，再进入后端、联调、测试与交付\n\n"
                "## 研究要求\n"
                "- 至少研究 3 到 5 个可借鉴产品\n"
                "- 总结共性功能、关键交互、信息架构、商业表达与差异化方向\n"
                "- 未完成 research 阶段前不得直接进入编码\n\n"
            "## 宿主执行方式\n"
            "- `/super-dev` 触发后，直接留在宿主里继续研究、出文档、实现和修订，不要把正常开发再转回 `super-dev pipeline`。\n"
            "- 只有安装、升级、卸载或宿主注入故障时，才回终端运行 `super-dev`、`super-dev update`、`super-dev uninstall`。\n"
        )

        if target in {"kiro", "kiro-cli"}:
            return self._build_kiro_steering_content(target)

        return (
            f"# /super-dev ({target})\n\n"
            "在当前项目触发 Super Dev 的流水线式开发编排。\n\n"
            "## 输入\n"
            "- 需求描述: `$ARGUMENTS`\n"
            "- 如果未提供参数，先要求用户补全需求后再执行。\n\n"
            "## Super Dev Runtime Contract\n"
            "- Super Dev 是当前项目里的本地 Python 工具 + 宿主规则/Skill 协议，不是独立模型平台。\n"
            "- 宿主负责推理、联网、编码、运行终端与修改文件。\n"
            "- 当用户触发 `/super-dev` 时，你要把它视为“进入 Super Dev 流水线”，而不是普通聊天命令。\n"
            "- 需要生成文档、Spec、质量报告、交付产物时，优先调用本地 `super-dev` CLI。\n"
            "- 需要研究、设计、编码、运行、修复时，优先使用宿主自身的 browse/search/terminal/edit 能力。\n\n"
            "## Local Knowledge Contract\n"
            "- 优先读取当前项目 `knowledge/` 目录里与需求相关的知识文件。\n"
            "- 若存在 `output/knowledge-cache/*-knowledge-bundle.json`，必须读取其中命中的 `local_knowledge`、`web_knowledge` 与 `research_summary`。\n"
            "- 本地知识命中的规范、检查清单、反模式、场景包默认是当前项目的硬约束，后续三文档、Spec 与实现都要继承。\n\n"
            f"{self._first_response_contract_zh()}"
            "## 强制执行顺序（不可跳步）\n"
            "1. 先使用宿主原生联网 / browse / search 能力研究同类产品，并先产出：\n"
            "   - `output/*-research.md`\n"
            "   - 至少包含 3-5 个对标产品、共性功能、关键流程、信息架构、交互模式、差异化方向\n"
            "2. 再生成三份核心文档，再进入编码阶段：\n"
            "   - `output/*-prd.md`\n"
            "   - `output/*-architecture.md`\n"
            "   - `output/*-uiux.md`\n"
            "3. 三份核心文档完成后，必须先暂停并向用户汇报文档路径、摘要与待确认事项；未经用户明确确认，不得进入 Spec 或编码。\n"
            "4. 用户确认后，再创建 Spec 变更与任务清单：\n"
            "   - `.super-dev/changes/*/proposal.md`\n"
            "   - `.super-dev/changes/*/tasks.md`\n"
            "5. 先按 `tasks.md` 实现并运行前端，确保前端可演示、可审查、无明显错误。\n"
            "6. 再实现后端、联调、测试、质量门禁与可审计交付清单。\n\n"
            "## 宿主执行方式（优先）\n"
            "- `/super-dev` 触发后，直接留在宿主里继续当前流程，不要把正常开发再转发成 `super-dev pipeline`。\n"
            "- 需要恢复时，优先使用 `/super-dev-run resume` 或等价的非 slash 文本入口。\n"
            "- 只有安装、升级、卸载或宿主注入故障时，才回终端运行 `super-dev`、`super-dev update`、`super-dev uninstall`。\n\n"
            "## 实现阶段要求\n"
            "- 如果宿主具备联网能力，必须优先在宿主中完成同类产品研究，不能跳过 research 阶段直接编码。\n"
            "- 研究结论必须回填到 `output/*-research.md`，并用于约束 PRD / 架构 / UIUX。\n"
            "- 编码前必须先读取 `output/*-prd.md`、`output/*-architecture.md`、`output/*-uiux.md`，并完成用户确认门。\n"
            "- 如果用户要求修改文档，只允许回到文档阶段修订，不能绕过确认门直接建 Spec 或开工。\n"
            "- UI 必须遵循 UI/UX 文档，禁止直接输出模板化、同质化页面。\n"
            "- 默认避免宿主自动滑向“AI 感”设计：紫/粉渐变主视觉、emoji 充当功能图标、默认系统字体直出；只有用户或品牌明确要求时才可采用，并写清理由。\n"
            "- 开始任何 UI 实现前，必须先声明图标库；功能图标只能来自 Lucide / Heroicons / Tabler / 官方组件图标。\n"
            "- 非对话式 AI 产品默认避免复刻 Claude / ChatGPT 式侧栏聊天壳层、窄中栏对话布局和同款中性色配色；若业务确实需要则必须写明适配理由。\n"
            "- 编码前必须先明确视觉方向、字体系统、颜色 token、间距 token、栅格系统、组件状态矩阵。\n"
            "- 页面必须提供可访问交互：可见 `focus` 态、合理 hover/active、兼容 reduced-motion。\n"
            "- 严禁在三文档与 Spec 缺失时直接宣称“已完成”。\n\n"
            "## 汇报格式（每次回复都要包含）\n"
            "- 当前阶段（文档 / Spec / 实现 / 质量 / 交付）\n"
            "- 本次变更文件路径\n"
            "- 下一步动作\n\n"
            "## 说明\n"
            "- 宿主负责调用自身模型、工具与实际编码；Super Dev 只提供治理协议。\n"
            "- Super Dev 不提供模型能力；编码能力来自当前宿主。\n"
            "- 在宿主会话中执行本流程，确保上下文连续与结果可审计。\n"
        )

    def _build_toml_command_content(self, target: str) -> str:
        prompt = self._build_slash_command_content(target).replace("$ARGUMENTS", "{{args}}")
        return (
            'description = "Activate the Super Dev pipeline for the current project."\n'
            'prompt = """\n'
            f"{prompt.rstrip()}\n"
            '"""'
        )

    def _build_seeai_slash_command_content(self, target: str) -> str:
        host_notes = ""
        if target in {"codebuddy", "codebuddy-cli"}:
            host_notes = (
                "## CodeBuddy 比赛专项适配\n"
                "- 优先固定在同一个项目级 Agent Chat / CLI 会话里完成半小时冲刺，避免来回切换子会话造成上下文损耗。\n"
                "- 如果 `/super-dev-seeai` 没有立刻出现在命令列表，直接在同一会话里输入 `super-dev-seeai: <需求>` 继续，不要换模式。\n"
                "- 比赛态默认按 P0/P1/P2 取舍：P0 先保证主演示路径能跑，P1 再补一个 wow 交互，P2 只在剩余时间充足时追加。\n\n"
            )
        elif target == "droid-cli":
            host_notes = (
                "## Droid CLI 比赛专项适配\n"
                "- 优先固定在同一个 Droid session 里完成比赛冲刺，避免频繁重开会话导致上下文漂移。\n"
                "- 如果当前 slash 菜单还没刷新，直接使用 `super-dev-seeai: <需求>` 文本入口，不要等待索引刷新。\n"
                "- 如需 headless 续跑，优先使用 `droid exec --session-id <id> \"continue with next steps\"`，不要重新开题。\n\n"
            )
        design_pack_lines = "\n".join(
            f"- {pack.label}：{pack.fit_for}；守卫：{pack.guardrail}"
            for pack in get_seeai_design_packs()
        )
        playbook_lines = "\n".join(
            f"- {playbook.label}：检查点={playbook.runtime_checkpoint}；回退栈={playbook.fallback_stack}"
            for playbook in get_seeai_archetype_playbooks()
        )
        execution_guardrails = "\n".join(f"- {item}" for item in SEEAI_EXECUTION_GUARDRAILS)
        module_truth_rules = "\n".join(f"- {item}" for item in SEEAI_MODULE_TRUTH_RULES)
        failure_protocol = "\n".join(f"- {item}" for item in SEEAI_FAILURE_PROTOCOL)
        return (
            f"# /super-dev-seeai ({target})\n\n"
            "在当前项目触发 Super Dev SEEAI 赛事极速版。\n\n"
            "## 输入\n"
            "- 需求描述: `$ARGUMENTS`\n"
            "- 如果未提供参数，先要求用户补全需求后再执行。\n\n"
            "## SEEAI 定位\n"
            "- 面向比赛或超短时间盒交付，例如精美官网、小游戏、展示型工具或单功能 demo。\n"
            "- 保留 research / 三文档 / docs confirm / spec，但全部压缩成比赛快版。\n"
            "- Spec 确认后直接进入前后端一体化快速开发，不再拆 preview confirm。\n"
            "- 若宿主会更新 `.super-dev/workflow-state.json`，必须显式写入 `flow_variant = seeai`，确保恢复和继续提示仍然回到 SEEAI 模式。\n\n"
            "## 半小时时间盒\n"
            "- 0-4 分钟：fast research，锁定评审场景、竞品风格和作品 wow 点。\n"
            "- 4-8 分钟：输出 compact research / PRD / architecture / UIUX。\n"
            "- 8-10 分钟：等用户确认文档和方向，不展开长讨论。\n"
            "- 10-12 分钟：生成 compact Spec / tasks，只保留最小可交付路径。\n"
            "- 12-27 分钟：一体化 full-stack sprint，先把主展示面做成，再补最小必要后端/数据层。\n"
            "- 27-30 分钟：polish、demo 路径检查、讲解词和亮点总结。\n\n"
            "## 首轮输出模板\n"
            "- `作品类型`：官网类 / 小游戏类 / 工具类，三选一。\n"
            "- `评委 wow 点`：本次作品最值得被记住的一个亮点。\n"
            "- `P0 主路径`：半小时内必须真实跑通的一条演示路径。\n"
            "- `主动放弃项`：本轮明确不做的部分，避免范围失控。\n"
            "- `关键假设`：只有在用户没说清时才写，最多 1 到 2 条。\n"
            "- 如果需求不缺关键输入，不要长时间澄清，直接进入 fast research。\n\n"
            "## 范围裁剪规则\n"
            "- P0：必须完成一个可演示主路径，首页/主玩法/主工具流程必须能跑。\n"
            "- P1：补一个明显 wow 点，例如强主视觉、动画、排行榜、分享页、彩蛋交互。\n"
            "- P2：只有在剩余时间充足时才加扩展能力，例如真数据库、登录、复杂后台。\n\n"
            "## 比赛短文档模板\n"
            "- `research.md`：题目理解、评委 wow 点、参考风格、主动放弃项。\n"
            "- `prd.md`：P0 主路径、P1 wow 点、P2 可选项、非目标。\n"
            "- `architecture.md`：页面/玩法主循环、技术栈、最小后端、降级方案。\n"
            "- `uiux.md`：视觉关键词、主 KV、页面骨架、关键动效。\n"
            "- `spec`：只保留一个 sprint 清单，按 `P0 -> P1 -> polish` 排序。\n\n"
            "### 推荐标题骨架\n"
            "- `research.md`：`# 题目理解` `# 参考风格` `# Wow 点` `# 主动放弃项`\n"
            "- `prd.md`：`# 作品目标` `# P0 主路径` `# P1 Wow 点` `# P2 可选项` `# 非目标`\n"
            "- `architecture.md`：`# 主循环` `# 技术栈` `# 数据流` `# 最小后端` `# 降级方案`\n"
            "- `uiux.md`：`# 视觉方向` `# 首屏/主界面` `# 关键交互` `# 动效重点` `# 设计 Token`\n"
            "- `spec`：`# Sprint Checklist` 下只列 `P0`、`P1`、`Polish`\n\n"
            "## 作品类型决策\n"
            "- 官网类题：优先主视觉、品牌叙事、首屏信息密度和滚动节奏。\n"
            "  默认技术栈：React/Vite 或 Next.js + Tailwind + Framer Motion。\n"
            "  默认 sprint：Hero/首屏 -> 亮点区/叙事 -> CTA/滚动动效 -> 最终 polish。\n"
            "- 小游戏类题：优先核心玩法循环、反馈感、积分/胜负和再次游玩闭环。\n"
            "  默认技术栈：HTML Canvas + Vanilla JS；复杂玩法再上 Phaser。\n"
            "  默认 sprint：主循环可玩 -> 积分/胜负反馈 -> 特效/音效 -> 复玩和 polish。\n"
            "- 工具类题：优先一个高价值主流程、输入输出清晰、结果页直观。\n\n"
            "  默认技术栈：React + Vite + Tailwind；必要时补最小 Express/Fastify 后端。\n"
            "  默认 sprint：输入页/主流程 -> 结果页 -> 分享/导出等演示加分项 -> 最终 polish。\n\n"
            "## 题型识别提示\n"
            "- 提到品牌、官网、落地页、活动宣传、首屏，默认按官网类处理。\n"
            "- 提到玩法、得分、胜负、闯关、点击反馈，默认按小游戏类处理。\n"
            "- 提到生成、分析、查询、输入输出、结果页、效率提升，默认按工具类处理。\n"
            "- 如果需求跨多类，先选最容易让评委记住的那一类做主轴。\n\n"
            "## 比赛设计包（先选后做）\n"
            "- 进入 SEEAI 后必须先锁 1 套视觉包，再推进实现，不允许自由混搭到页面变丑。\n"
            f"{design_pack_lines}\n\n"
            "## 快而稳的执行守卫\n"
            f"{execution_guardrails}\n\n"
            "## 模块真实生效规则\n"
            f"{module_truth_rules}\n\n"
            "## 题型运行检查点与回退栈\n"
            f"{playbook_lines}\n\n"
            "## 失败优先回退协议\n"
            f"{failure_protocol}\n\n"
            "## 降级策略\n"
            "- 如果真实后端会拖慢交付，优先用本地 mock、JSON、内存态或静态数据把演示路径跑通。\n"
            "- 如果鉴权、支付、上传等不是评审主轴，优先做高保真演示流，不强行接完整生产链路。\n"
            "- 如果时间吃紧，砍掉次要页面和长尾功能，保住视觉完成度、主流程和讲解效果。\n\n"
            f"{host_notes}"
            "## 必须执行的顺序\n"
            "1. 先做 fast research，快速吸收竞品、参考作品与评审导向，并写入 `output/*-research.md`\n"
            "2. 再生成 compact `output/*-prd.md`、`output/*-architecture.md`、`output/*-uiux.md`\n"
            "3. 三份 compact 文档完成后，必须先等待用户明确确认\n"
            "4. 用户确认后，再创建 compact Spec / tasks\n"
            "5. Spec 之后直接进入 full-stack sprint：先做主展示前端，再补最小必要后端/数据层，然后统一 polish\n"
            "6. 最后输出 demo 路径、亮点总结与如何讲解这个作品\n\n"
            "## 设计与质量要求\n"
            "- 速度优先，但不能做成未抛光的半成品。\n"
            "- 默认追求高展示性、强主视觉、明确 wow 点，但保持题型适配，不强制所有作品都是营销页。\n"
            "- 文案、按钮、交互、主流程必须可演示，禁止明显占位和 AI slop。\n"
            "- 功能图标只能来自 Lucide / Heroicons / Tabler，禁止 emoji。\n"
            "- 时间不够时优先删功能，不要删完成度；至少保住一个 wow 点和一条主演示路径。\n\n"
            "## 禁止事项\n"
            "- 不要跳过 research / 三文档 / docs confirm / spec。\n"
            "- 不要把 SEEAI 模式扩回标准 Super Dev 的 preview gate / 长质量闭环。\n"
            "- 不要在文档确认前直接开工。\n"
            "\n## Super Dev SEEAI Flow Contract\n"
            "- SUPER_DEV_SEEAI_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>build_fullstack>polish>handoff\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: omitted\n"
            "- QUALITY_STYLE: speed_with_showcase_quality\n"
        )

    def _build_seeai_toml_command_content(self, target: str) -> str:
        prompt = self._build_seeai_slash_command_content(target).replace("$ARGUMENTS", "{{args}}")
        return (
            'description = "Activate the Super Dev SEEAI competition sprint for the current project."\n'
            'prompt = """\n'
            f"{prompt.rstrip()}\n"
            '"""'
        )

    def _generic_cli_rules(self, target: str) -> str:
        if target == "codex-cli":
            trigger_lines = (
                "## Trigger\n"
                "- Codex App/Desktop preferred: choose `super-dev` from the `/` list. This is the enabled Skill entry rather than a project custom slash file.\n"
                "- Codex CLI preferred: `$super-dev`.\n"
                "- AGENTS-driven natural-language fallback: `super-dev: <需求描述>` or `super-dev：<需求描述>`.\n"
                "- SEEAI competition mode: App/Desktop choose `super-dev-seeai`, CLI use `$super-dev-seeai`, or say `super-dev-seeai: <需求描述>` / `super-dev-seeai：<需求描述>`.\n"
                "- Local terminal only handles install / update / uninstall; normal development should stay in the live Codex host session.\n\n"
            )
        elif self.supports_slash(target):
            trigger_lines = (
                "## Trigger\n"
                "- Preferred: `/super-dev <需求描述>`\n"
                "- SEEAI competition mode: `/super-dev-seeai <需求描述>`\n"
                "- Local terminal only handles install / update / uninstall; normal development should stay in the host session.\n\n"
            )
        else:
            trigger_lines = (
                "## Trigger\n"
                "- Preferred: say `super-dev: <需求描述>` or `super-dev：<需求描述>` in the host chat so AGENTS.md + the `super-dev` skill can govern the workflow.\n"
                "- SEEAI competition mode: say `super-dev-seeai: <需求描述>` or `super-dev-seeai：<需求描述>` in the host chat.\n"
                "- Local terminal only handles install / update / uninstall.\n"
                "- Do not rely on `/super-dev` in this host.\n\n"
            )
        return (
            f"# Super Dev Integration for {target}\n\n"
            "Super Dev 是“超级开发战队”，一个流水线式 AI Coding 辅助工具。\n"
            "Super Dev does not provide model inference or coding APIs.\n"
            "The host remains responsible for model execution, tools, and actual code generation.\n"
            "Use the host model/runtime as-is; Super Dev only enforces the delivery protocol.\n"
            "Use Super Dev generated artifacts as source of truth.\n\n"
            "## Runtime Contract\n"
            "- Treat Super Dev as a local Python CLI plus host-side rules/skills, not as a separate model provider.\n"
            "- When the user triggers Super Dev, enter the protocol immediately instead of treating it as normal chat.\n"
            "- When the user triggers `super-dev-seeai`, switch to the SEEAI competition-fast contract: research -> compact docs -> docs confirmation -> compact spec -> full-stack sprint -> polish/handoff.\n"
            "- Use host-native web/search/browse for research and host-native editing/execution for implementation.\n"
            "- Use local `super-dev` commands to generate/update documents, spec artifacts, quality reports, and delivery outputs.\n\n"
            f"{self._first_response_contract_en()}"
            "## Local Knowledge Contract\n"
            "- Read relevant files under `knowledge/` before drafting documents.\n"
            "- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read its `local_knowledge`, `web_knowledge`, and `research_summary` first.\n"
            "- Treat matched local knowledge, checklists, anti-patterns, and scenario packs as project constraints that must flow into docs, spec, and implementation.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            f"{trigger_lines}"
            "## Work Mode Contract\n"
            "- Detect `new`, `evolve`, `variant`, `patch`, and `resume` before planning execution.\n"
            "- `new` may go directly into research.\n"
            "- `evolve`, `variant`, and `patch` must baseline the current repository before generating docs or Spec.\n"
            "- `resume` is a normal default path after a closed window, reboot, or next-day continuation.\n\n"
            "## Required Context\n"
            "- output/*-prd.md\n"
            "- output/*-architecture.md\n"
            "- output/*-uiux.md\n"
            "- output/*-execution-plan.md\n"
            "- .super-dev/changes/*/tasks.md\n\n"
            "## Execution Order\n"
            "1. Detect the work mode and, for existing-project work, baseline the current repository first into `output/*-baseline-audit.md` / `.json`\n"
            "2. Use the host's native browse/search/web capability to research similar products first and produce output/*-research.md as a real repository file\n"
            "3. Freeze PRD, architecture and UIUX documents and write them into output/* files in the repository workspace rather than only describing them in chat\n"
            "4. Stop after the three core documents, summarize them to the user, and wait for explicit confirmation before creating Spec or coding\n"
            "5. Create Spec proposal/tasks only after the user confirms the documents\n"
            "6. Implement and run the frontend first so it becomes demonstrable before backend-heavy work\n"
            "7. Implement backend APIs and data layer, then run tests, quality gate, and release preparation\n"
            "8. If the user says the UI is unsatisfactory, asks for a redesign, or says the page looks AI-generated, first update `output/*-uiux.md`, then redo frontend implementation, rerun frontend runtime and UI review, and only then continue.\n"
            "9. If the user says the architecture is wrong or the technical plan must change, first update `output/*-architecture.md`, then realign tasks and implementation before continuing.\n"
            "10. If the user says quality or security is not acceptable, first fix the issues, rerun the quality gate, refresh any delivery evidence the reports ask for, and only then continue.\n"
            "11. Before any UI implementation, first lock the icon library, typography, token system, component ecosystem, and page skeleton according to `output/*-uiux.md`.\n"
            "12. Do not use emoji as functional icons or placeholders, and do not leave icon decisions for later.\n"
            "13. For non-conversational AI products, default to avoiding Claude / ChatGPT-style sidebar chat shells, narrow-center conversation layouts, and the same neutral chat color shell unless the UI plan explicitly justifies it.\n"
            "14. UI implementation must use the recommended component ecosystem/design token direction from `output/*-uiux.md`, not switch ad hoc.\n"
            "\n\n## Coding Constraints (active during ALL coding phases)\n\n"
            "These rules apply every time you write or edit a file:\n\n"
            "### Tech Stack Pre-Research\n"
            "- Before writing ANY code, run `cat package.json` (or equivalent) to check framework versions.\n"
            "- If unsure about an API, use WebFetch to read official docs first. Never guess.\n\n"
            "### Icon & Visual Rules\n"
            "- Icons MUST come from a declared icon library (Lucide/Heroicons/Tabler). No emoji as icons.\n"
            "- No purple/pink gradient themes. No default system font only.\n\n"
            "### Frontend/Backend Alignment\n"
            "- Frontend fetch URLs must exactly match backend route definitions.\n"
            "- Define API paths as shared constants when possible.\n\n"
            "### Per-File Self-Check\n"
            "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
            "- After completing a feature, run build + lint. Fix errors before moving on.\n"
        )

    def _generic_ide_rules(self, target: str) -> str:
        windsurf_frontmatter = ""
        if target == "windsurf":
            windsurf_frontmatter = "---\n" "trigger: always_on\n" "---\n\n"
        return (
            f"{windsurf_frontmatter}"
            f"# Super Dev IDE Rules ({target})\n\n"
            "## Positioning\n"
            "- Super Dev is a host-level workflow governor, not an LLM platform.\n"
            "- Keep using the host's model capabilities; do not expect extra model APIs from Super Dev.\n"
            "- The host remains responsible for actual coding, tool execution, and file changes.\n\n"
            "## Runtime Contract\n"
            "- Treat Super Dev as the local Python workflow tool plus this host rule file, not as a separate coding engine.\n"
            "- When the user says `/super-dev ...`, `super-dev: ...`, or `super-dev：...`, immediately enter the Super Dev pipeline.\n"
            "- When the user says `/super-dev-seeai ...`, `super-dev-seeai: ...`, or `super-dev-seeai：...`, enter the SEEAI competition-fast contract.\n"
            "- Use host-native browse/search/web for research and host-native editing/terminal for implementation.\n"
            "- Use local `super-dev` commands when you need to generate or refresh documents, spec artifacts, quality reports, or delivery manifests.\n\n"
            f"{self._first_response_contract_en()}"
            "## Local Knowledge Contract\n"
            "- Read relevant files under `knowledge/` before drafting the three core documents.\n"
            "- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read it first and inherit its matched local knowledge into PRD, architecture, UIUX, Spec, and execution.\n"
            "- Treat local knowledge hits as hard project constraints, especially for standards, anti-patterns, checklists, and scenario packs.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Work Mode Contract\n"
            "- Detect `new`, `evolve`, `variant`, `patch`, and `resume` before planning implementation.\n"
            "- Existing-project work must baseline the current repository before docs/spec.\n"
            "- Resume is the default continuation path after closing the host, rebooting, or returning later.\n\n"
            "## Working Agreement\n"
            "- If the host supports browse/search/web, research similar products first and write the findings into output/*-research.md.\n"
            "- For `evolve`, `variant`, and `patch`, first produce `output/*-baseline-audit.md` / `.json` so docs and implementation stay aligned with the current codebase.\n"
            "- Generate PRD, architecture and UIUX documents before coding, write them into output/* files instead of only replying in chat, then pause and ask the user to confirm the three documents.\n"
            "- In SEEAI mode, keep the same document gate, but compress the documents and go straight from Spec into one integrated full-stack sprint without a separate preview gate.\n"
            "- If the user requests revisions, update the documents first and ask again; do not create Spec or code before confirmation.\n"
            "- Chat-only summaries do not count as completion; if a required artifact is not written into the repository workspace, treat the step as incomplete.\n"
            "- If the user requests a UI redesign or says the UI is unsatisfactory, first update `output/*-uiux.md`, then redo the frontend, and rerun frontend runtime + UI review before continuing.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign tasks and implementation before continuing.\n"
            "- If the user requests quality or security remediation, first fix the issues, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n"
            "- Respect Spec tasks sequence.\n"
            "- Implement and run the frontend before moving into backend-heavy work.\n"
            "- Keep architecture and UIUX consistency.\n\n"
            "## Delivery Criteria\n"
            "- Frontend can be demonstrated early.\n"
            "- Backend and migration scripts match specs.\n"
            "- Security/performance checks are resolved.\n"
            "- Quality gate threshold is met for the current scenario.\n"
            "- UI must avoid AI-looking output (purple/pink gradient-first theme, emoji as icons, default-font-only pages).\n"
            "- Before any UI implementation, lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style sidebar chat shells unless the UI plan explicitly justifies it.\n"
            "- UI must define typography, design tokens, grid, component states and trust signals before page implementation.\n"
            "- Prefer the component ecosystem and design token baseline recommended in output/*-uiux.md instead of switching UI libraries ad hoc.\n"
            "\n\n## Coding Constraints (active during ALL coding phases)\n\n"
            "These rules apply every time you write or edit a file:\n\n"
            "### Tech Stack Pre-Research\n"
            "- Before writing ANY code, run `cat package.json` (or equivalent) to check framework versions.\n"
            "- If unsure about an API, use WebFetch to read official docs first. Never guess.\n\n"
            "### Icon & Visual Rules\n"
            "- Icons MUST come from a declared icon library (Lucide/Heroicons/Tabler). No emoji as icons.\n"
            "- No purple/pink gradient themes. No default system font only.\n\n"
            "### Frontend/Backend Alignment\n"
            "- Frontend fetch URLs must exactly match backend route definitions.\n"
            "- Define API paths as shared constants when possible.\n\n"
            "### Per-File Self-Check\n"
            "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
            "- After completing a feature, run build + lint. Fix errors before moving on.\n"
        )

    def _trae_rules(self) -> str:
        return (
            "# Super Dev Trae Rules\n\n"
            "## Critical Trigger Switch\n"
            "- If a user message starts with `super-dev:` or `super-dev：`, immediately switch into Super Dev pipeline mode.\n"
            "- If a user message starts with `super-dev-seeai:` or `super-dev-seeai：`, immediately switch into Super Dev SEEAI competition mode.\n"
            "- If the repository already has active Super Dev workflow context, the first natural-language requirement in a new session must also continue Super Dev.\n"
            "- Do not treat `super-dev:` or `super-dev：` as normal chat, brainstorming, or generic coding mode.\n"
            "- Do not treat `super-dev-seeai:` or `super-dev-seeai：` as ordinary chat either; they are competition-mode entries.\n"
            "- After `super-dev:` or `super-dev：` is seen, do not start implementation directly.\n"
            "- Your first reply must say `SMOKE_OK` when the user is smoke-testing, or explicitly say Super Dev pipeline mode is active.\n"
            "- Your first reply must explicitly say the current phase is `research`.\n"
            "- Your first reply must explicitly promise the sequence: research -> three core documents -> wait for user confirmation -> Spec/tasks -> frontend runtime verification -> backend/tests/delivery.\n"
            "- After the three core documents are generated, you must stop and wait for approval before creating Spec or writing code.\n\n"
            "## Runtime Contract\n"
            "- Treat Super Dev as the local Python workflow tool plus Trae rule files, not as a separate coding engine.\n"
            "- Keep using the host's model, tools, browse/search/web and editor capabilities.\n"
            "- Use local `super-dev` commands when you need to generate or refresh documents, specs, quality reports, or delivery manifests.\n"
            "- The host remains responsible for coding, tool execution, and file changes.\n\n"
            "## Local Knowledge Contract\n"
            "- Read relevant files under `knowledge/` before drafting the three core documents.\n"
            "- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read it first and carry its matched local knowledge into PRD, architecture, UIUX, Spec, and execution.\n"
            "- Treat matched standards, anti-patterns, checklists, baselines, and scenario packs as hard constraints.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Working Agreement\n"
            "- If browse/search/web is available, research similar products first and write `output/*-research.md` into the project workspace.\n"
            "- Generate PRD, architecture, and UIUX before coding and save them as `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` instead of only replying in chat.\n"
            "- Ask the user to confirm or revise the three documents before creating Spec or code.\n"
            "- If a document is mentioned in chat but not written to the repository, treat the step as incomplete and keep working until the file exists.\n"
            "- If the user requests a UI redesign or says the UI is unsatisfactory, first update `output/*-uiux.md`, then redo the frontend, and rerun frontend runtime + UI review before continuing.\n"
            "- If the user requests architecture changes, first update `output/*-architecture.md`, then realign tasks and implementation before continuing.\n"
            "- If the user requests quality or security remediation, first fix the issues, rerun the quality gate, and refresh any delivery evidence the reports ask for before continuing.\n"
            "- Implement frontend first and verify runtime before moving into backend-heavy work.\n"
            "- Keep UI implementation consistent with `output/*-uiux.md` and avoid AI-looking templates.\n"
            "- Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- Keep using the design token direction and component ecosystem frozen in `output/*-uiux.md` rather than switching ad hoc.\n"
            "\n\n## Coding Constraints (active during ALL coding phases)\n\n"
            "These rules apply every time you write or edit a file:\n\n"
            "### Tech Stack Pre-Research\n"
            "- Before writing ANY code, run `cat package.json` (or equivalent) to check framework versions.\n"
            "- If unsure about an API, use WebFetch to read official docs first. Never guess.\n\n"
            "### Icon & Visual Rules\n"
            "- Icons MUST come from a declared icon library (Lucide/Heroicons/Tabler). No emoji as icons.\n"
            "- No purple/pink gradient themes. No default system font only.\n\n"
            "### Frontend/Backend Alignment\n"
            "- Frontend fetch URLs must exactly match backend route definitions.\n"
            "- Define API paths as shared constants when possible.\n\n"
            "### Per-File Self-Check\n"
            "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
            "- After completing a feature, run build + lint. Fix errors before moving on.\n"
        )

    def _claude_rules(self) -> str:
        return (
            "# Super Dev Claude Code Integration\n\n"
            "This project uses a pipeline-driven development model.\n\n"
            "## Positioning\n"
            "- Super Dev does not own a model endpoint.\n"
            "- Claude Code remains the execution host for coding capability.\n"
            "- Super Dev provides governance: protocol, gates, and audit artifacts.\n\n"
            "## Runtime Contract\n"
            "- Treat Super Dev as the local Python workflow tool plus Claude Code `CLAUDE.md + Skills` integration.\n"
            "- Primary surfaces are project-root `CLAUDE.md`, compatibility mirror `.claude/CLAUDE.md`, project-level `.claude/skills/super-dev/`, and user-level `~/.claude/skills/super-dev/`.\n"
            "- Compatibility surface `.claude/commands/super-dev.md` remains installed so older Claude Code builds still converge onto the same Super Dev workflow.\n"
            "- Optional repo enhancement surfaces `.claude-plugin/marketplace.json` and `plugins/super-dev-claude/.claude-plugin/plugin.json` can expose a richer Claude-native plugin layer without replacing the base `CLAUDE.md + Skills` contract.\n"
            "- When the user triggers `/super-dev`, `super-dev:`, or `super-dev：`, enter the Super Dev pipeline immediately rather than handling it like casual chat.\n"
            "- Use Claude Code browse/search for research and Claude Code terminal/editing for implementation.\n"
            "- Use local `super-dev` commands whenever you need to generate/update docs, spec artifacts, quality reports, and delivery outputs.\n\n"
            f"{self._first_response_contract_en()}"
            "## Local Knowledge Contract\n"
            "- Read relevant files under `knowledge/` before drafting PRD, architecture, and UIUX.\n"
            "- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read it first and inherit its local knowledge hits into later stages.\n"
            "- Treat matched local standards, scenario packs, and checklists as hard constraints, not optional hints.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Before coding\n"
            "1. If Claude Code browse/search is available, research similar products first and write output/*-research.md as a real repository file\n"
            "2. Read output/*-prd.md\n"
            "3. Read output/*-architecture.md\n"
            "4. Read output/*-uiux.md\n"
            "5. Summarize the three core documents to the user and wait for explicit confirmation before creating Spec or coding\n"
            "6. Chat-only summaries do not count as completion; the required artifacts must exist in the workspace\n"
            "7. Read output/*-execution-plan.md\n"
            "8. Follow .super-dev/changes/*/tasks.md after confirmation, with frontend-first implementation and runtime verification\n\n"
            "9. If the user requests a UI redesign or says the UI is unsatisfactory, first update `output/*-uiux.md`, then redo the frontend, and rerun frontend runtime + UI review before continuing.\n\n"
            "## Output Quality\n"
            "- Keep security/performance constraints from red-team report.\n"
            "- Ensure quality gate threshold is met before merge.\n"
            "- UI must follow output/*-uiux.md and avoid AI-looking templates (purple gradient, emoji icons, default-font-only).\n"
            "- Before any UI implementation, lock the icon library, typography, design token system, component ecosystem, and page skeleton from output/*-uiux.md.\n"
            "- Do not use emoji as functional icons or placeholders.\n"
            "- For non-conversational AI products, avoid Claude / ChatGPT-style shells unless the UI plan explicitly justifies them.\n"
            "- UI implementation must define typography system, design tokens, page hierarchy and component states before polishing visuals.\n"
            "- Prioritize real screenshots, trust modules, proof points and task flows over decorative hero sections.\n\n"
            "## Coding Constraints (active during ALL coding phases)\n\n"
            "These rules apply every time you write or edit a file. They are NOT suggestions:\n\n"
            "### Tech Stack Pre-Research\n"
            "- Before writing ANY code, run `cat package.json` (or equivalent) to check framework versions.\n"
            "- If unsure about an API for the installed version, use WebFetch to read official docs first.\n"
            "- Never guess API signatures. Check docs.\n\n"
            "### Icon & Visual Rules\n"
            "- Icons MUST come from a declared icon library (Lucide/Heroicons/Tabler). No emoji as icons.\n"
            "- No purple/pink gradient themes. No default system font only.\n"
            "- Before showing any UI code, self-check: no emoji characters in the source.\n\n"
            "### Frontend/Backend Alignment\n"
            "- Frontend fetch URLs must exactly match backend route definitions.\n"
            "- Define API paths as shared constants when possible.\n\n"
            "### Per-File Self-Check\n"
            "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
            "- After completing a feature, run build + lint. Fix errors before moving on.\n\n"
            "### Host-First Governance During Coding\n"
            "- 完成 UI 后，优先在宿主里继续当前流程并触发 `/super-dev-review ui`，不要把内部 CLI 当成日常开发入口。\n"
            "- 需要进入质量与交付时，优先在宿主里继续当前流程或用 `/super-dev-run quality`、`/super-dev-review quality` 这类宿主交互面。\n"
            "- 终端侧 `super-dev` CLI 保留给维护与治理补救，不负责日常脚手架、实现与返工调度。\n\n"
            "## Four-Layer Governance Model\n\n"
            "Super Dev governance operates at four layers:\n\n"
            "**Layer 1 — CLAUDE.md (Persistent Rules)**\n"
            "Project-root `CLAUDE.md` is the canonical persistent memory surface. `.claude/CLAUDE.md` is kept as a compatibility mirror for builds that still read nested memory files.\n\n"
            "**Layer 2 — Skills (Primary Execution Contract)**\n"
            "Project-level `.claude/skills/super-dev/` and user-level `~/.claude/skills/super-dev/` carry the primary Super Dev execution contract. Claude Code only uses `super-dev` as the single skill name; old legacy aliases are only retained for cleanup/migration paths.\n\n"
            "**Layer 3 — Hooks (Runtime Enforcement)**\n"
            "PreToolUse hooks validate every file write. PostToolUse hooks audit results.\n"
            "Hooks are auto-registered when /super-dev is invoked.\n\n"
            "**Layer 4 — CLI Commands & Optional Plugin Enhancement (On-Demand Checks)**\n"
            "Maintenance-only CLI checks may still exist behind the scenes, but ordinary development should stay on host entry surfaces instead of teaching users `enforce` / `quality` command habits.\n"
            "If Claude Code surfaces repo plugins, `.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json` should enhance the same Super Dev flow rather than fork it.\n"
        )

    def _antigravity_workflow_rules(self) -> str:
        """
        生成 Antigravity IDE 专属工作流配置。
        文件写入 .agent/workflows/super-dev.md，
        格式遵循 Antigravity Skill YAML frontmatter + markdown 规范。
        """
        return """\
---
description: Super Dev 流水线式 AI Coding 辅助工作流 - 从需求到交付的 12 阶段自动化流程
---

# Super Dev Pipeline Workflow

## 角色定义

本工作流激活 11 位专家角色自动协作：

| 专家 | 职责 |
|:---|:---|
| PRODUCT | 首次上手、产品闭环、功能缺口与优先级总审查 |
| PM | 需求分析、PRD 生成、用户故事 |
| ARCHITECT | 架构设计、技术选型、API 契约 |
| UI/UX | 设计系统、交互规范、原型设计 |
| SECURITY | 红队审查、OWASP 检测、威胁建模 |
| CODE | 代码实现、最佳实践、代码审查 |
| DBA | 数据库设计、迁移脚本、索引优化 |
| QA | 测试策略、质量门禁、覆盖率要求 |
| DEVOPS | CI/CD 配置、容器化、监控告警 |
| RCA | 根因分析、故障复盘、风险识别 |

## 工作流步骤

### 前置：读取必备文档

在写任何一行代码前，必须先读取：

1. `output/*-prd.md` — 产品需求和验收标准
2. `output/*-architecture.md` — 技术栈和 API 设计
3. `output/*-uiux.md` — 设计系统和组件规范
4. `output/*-execution-plan.md` — 阶段任务路线图
5. `.super-dev/changes/*/tasks.md` — 具体实现任务清单

### 第 0 阶段：需求增强与同类产品研究

优先在宿主里输入 `/super-dev 你的需求描述`；不支持 slash 的宿主使用 `super-dev: 你的需求描述`。

- 解析自然语言需求，注入领域知识库
- 优先使用宿主原生联网能力研究同类产品、关键流程、页面结构和交互模式
- 联网检索补充市场和技术背景
- 输出 `output/*-research.md`，沉淀对标结论、共性功能和差异化机会
- 输出结构化需求蓝图

### 第 1 阶段：专业文档生成

自动生成：
- `output/*-prd.md` — PRD（产品需求文档）
- `output/*-architecture.md` — 架构设计文档
- `output/*-uiux.md` — UI/UX 设计文档
- 以上产物必须真实写入项目工作区；只在聊天里总结不算完成

### 第 2-4 阶段：实施准备

- 前端实施蓝图与演示验证（前端先行原则）
- Spec 规范（结构化规范风格）
- 宿主实现参考 + API 契约

### 第 5-6 阶段：质量保障

- 红队审查（安全 + 性能 + 架构）
- 质量门禁（统一标准：80+）

### 第 7-8 阶段：交付准备

- 代码审查指南
- AI 提示词生成（直接传给 AI 开始开发）

### 第 9-11 阶段：部署与交付

- CI/CD 配置（GitHub/GitLab/Jenkins/Azure/Bitbucket）
- 数据库迁移脚本（Prisma/TypeORM/SQLAlchemy 等 6 种 ORM）
- 项目交付包（manifest + report + zip）

## 执行规则

- 进入 Super Dev 流程后，第一轮必须明确当前阶段是 `research`
- 三份核心文档完成后，必须暂停等待用户确认
- 未经用户确认，不得创建 `.super-dev/changes/*` 或开始编码
- **前端先行**：先完成可演示前端，再实现后端 API
- **禁止 emoji 图标**：使用 Lucide/Heroicons/Tabler Icons
- **参数化查询**：禁止字符串拼接 SQL
- **任务跟踪**：每完成一项在 tasks.md 标记 `[x]`
- **质量门禁**：交付前在宿主里继续当前流程进入 quality，不要把质量阶段重新讲成一组独立终端命令

## 常用宿主交互

```bash
/super-dev 需求                          # 默认主入口
/super-dev-work evolve "在当前项目里新增功能"  # 已有项目增量
/super-dev-run resume                    # 窗口关闭/第二天继续
/super-dev baseline 确认，可以继续当前流程    # 已有项目先确认 baseline
super-dev                                # 仅用于终端接入/重装
```
"""

    def _build_antigravity_context_content(self) -> str:
        return (
            "# Super Dev Antigravity Context\n\n"
            "Antigravity remains the execution host for model reasoning, browsing, terminal work, and code changes.\n"
            "Super Dev is the governance layer and local Python toolchain.\n\n"
            "## Trigger\n"
            "- Preferred: `/super-dev <需求描述>`\n"
            "- Local terminal only handles install / update / uninstall; it does not replace the Antigravity host session.\n\n"
            "## Required First Response Contract\n"
            f"{self._first_response_contract_en()}"
            "## Local Knowledge Contract\n"
            "- Read `knowledge/` first when relevant.\n"
            "- If `output/knowledge-cache/*-knowledge-bundle.json` exists, inherit its local knowledge hits into research, PRD, architecture, UIUX, Spec, and implementation.\n\n"
            f"{self._conversation_continuity_contract_en()}"
            "## Artifact Contract\n"
            "- Write `output/*-research.md`, `output/*-prd.md`, `output/*-architecture.md`, and `output/*-uiux.md` into the repository workspace.\n"
            "- Chat-only summaries do not count as finished artifacts.\n"
            "- If a required artifact is missing from the workspace, continue until it exists.\n\n"
            "## Required Execution Order\n"
            "1. Research similar products first using host-native browse/search and write `output/*-research.md`\n"
            "2. Generate PRD, architecture, and UIUX and write them as project files\n"
            "3. Stop and wait for explicit user confirmation before Spec or coding\n"
            "4. Create Spec/tasks only after confirmation\n"
            "5. Implement and run the frontend first\n"
            "6. Continue with backend, tests, quality gate, and delivery\n"
            "7. If the user requests a UI redesign, first update `output/*-uiux.md`, then redo the frontend and rerun frontend runtime + UI review\n"
            "8. If the user requests architecture changes, first update `output/*-architecture.md`, then realign tasks and implementation\n"
            "9. If the user requests quality remediation, first fix the issues, rerun the quality gate, refresh any delivery evidence the reports ask for, and only then continue\n"
            "10. Before any UI implementation, first lock the icon library, typography, design token system, component ecosystem, and page skeleton from `output/*-uiux.md`\n"
            "11. Do not use emoji as functional icons or placeholders\n"
            "12. Keep using the design token direction and component ecosystem frozen in `output/*-uiux.md` rather than switching ad hoc\n\n"
            "## Coding Constraints (active during ALL coding phases)\n\n"
            "- Before writing ANY code, run `cat package.json` to check framework versions. If unsure, read official docs first.\n"
            "- Icons MUST come from Lucide/Heroicons/Tabler. No emoji as icons. No purple/pink gradient themes.\n"
            "- Frontend fetch URLs must exactly match backend route definitions.\n"
            "- Before writing each file: correct imports, no emoji, colors from tokens only.\n"
            "- After completing a feature, run build + lint. Fix errors before moving on.\n"
        )
