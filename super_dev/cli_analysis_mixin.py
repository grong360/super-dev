"""CLI analysis command mixin helpers."""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config_manager


class CliAnalysisMixin:
    def _cmd_init(self, args) -> int:
        """初始化项目"""
        config_manager = get_config_manager()

        # 检查是否已初始化
        if config_manager.exists():
            self.console.print(
                "[yellow]项目已初始化，使用 'super-dev config set' 修改配置[/yellow]"
            )
            return 0

        name = getattr(args, "name", None) or Path.cwd().name

        # Apply template defaults (user-provided args override)
        if getattr(args, "template", None):
            from .project_templates import get_template

            tmpl = get_template(args.template)
            if tmpl:
                _tmpl_defaults = {
                    "frontend": "next",
                    "backend": "node",
                    "domain": "",
                    "platform": "web",
                }
                for key, default_val in _tmpl_defaults.items():
                    current = getattr(args, key, None)
                    if current is None or current == default_val:
                        tmpl_val = tmpl.get(key, "")
                        if tmpl_val:
                            setattr(args, key, tmpl_val)
                # Also set optional fields from template
                for opt_key in ["ui_library", "style"]:
                    if not getattr(args, opt_key, None) and tmpl.get(opt_key):
                        setattr(args, opt_key, tmpl[opt_key])
                for list_key in ["state", "testing"]:
                    if not getattr(args, list_key, None) and tmpl.get(list_key):
                        setattr(args, list_key, [tmpl[list_key]])
                if not args.description and tmpl.get("description"):
                    args.description = tmpl["description"]

        # 创建配置
        config = config_manager.create(
            name=name,
            description=args.description,
            platform=args.platform,
            frontend=args.frontend,
            backend=args.backend,
            domain=args.domain,
            ui_library=getattr(args, "ui_library", None),
            style_solution=getattr(args, "style", None),
            state_management=getattr(args, "state", []) or [],
            testing_frameworks=getattr(args, "testing", []) or [],
        )

        # 创建输出目录
        output_dir = Path.cwd() / config.output_dir
        output_dir.mkdir(exist_ok=True)
        workflow_file, summary_file = self._bootstrap_project_contract(
            project_dir=Path.cwd(),
            config=config,
        )

        self.console.print(f"[green]✓[/green] 项目已初始化: {config.name}")
        self.console.print(f"  平台: {config.platform}")
        self.console.print(f"  前端框架: {config.frontend}")
        if config.ui_library:
            self.console.print(f"  UI 组件库: {config.ui_library}")
        if config.style_solution:
            self.console.print(f"  样式方案: {config.style_solution}")
        if config.state_management:
            self.console.print(f"  状态管理: {', '.join(config.state_management)}")
        if config.testing_frameworks:
            self.console.print(f"  测试框架: {', '.join(config.testing_frameworks)}")
        self.console.print(f"  后端: {config.backend}")
        if config.domain:
            self.console.print(f"  领域: {config.domain}")
        self.console.print(f"  工作流契约: {workflow_file}")
        self.console.print(f"  Bootstrap 摘要: {summary_file}")

        self.console.print("\n[dim]下一步:[/dim]")
        self.console.print("  1. 终端输入 super-dev，进入宿主接入引导")
        self.console.print("  2. 接入完成后，在宿主里触发 Super Dev:")
        self.console.print("     /super-dev <你的需求>       (slash 宿主)")
        self.console.print("     super-dev: <你的需求>       (text 宿主)")

        return 0

    def _bootstrap_project_contract(self, project_dir: Path, config) -> tuple[Path, Path]:
        """创建显式 bootstrap 工作流契约与摘要。"""
        from .specs import SpecGenerator

        output_dir = project_dir / config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        generator = SpecGenerator(project_dir)
        generator.init_sdd()

        workflow_file = project_dir / ".super-dev" / "WORKFLOW.md"
        workflow_file.write_text(
            self._render_workflow_contract_markdown(config=config, project_dir=project_dir),
            encoding="utf-8",
        )

        summary_file = output_dir / f"{config.name}-bootstrap.md"
        summary_file.write_text(
            self._render_bootstrap_summary_markdown(config=config, project_dir=project_dir),
            encoding="utf-8",
        )
        return workflow_file, summary_file

    def _render_workflow_contract_markdown(self, config, project_dir: Path) -> str:
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        return f"""# Super Dev Workflow Contract

> Generated by `super-dev init`
> Updated: {timestamp}

## Project

- Name: {config.name}
- Description: {config.description or "待补充"}
- Platform: {config.platform}
- Frontend: {config.frontend}
- Backend: {config.backend}
- Domain: {config.domain or "未指定"}

## Bootstrap Outcome

This repository has been explicitly bootstrapped for Super Dev.

The following surfaces are now the project bootstrap contract:

- `super-dev.yaml`
- `.super-dev/WORKFLOW.md`
- `.super-dev/project.md`
- `.super-dev/AGENTS.md`
- `.super-dev/specs/`
- `.super-dev/changes/`
- `output/{config.name}-bootstrap.md`

## Required Pipeline Order

1. research
2. PRD / Architecture / UIUX
3. wait for user confirmation
4. Spec / tasks
5. frontend first + runtime validation
6. backend / integration / tests
7. quality gate
8. delivery ready + rehearsal passed

## Trigger Rules

- Native slash hosts: `/super-dev <需求描述>`
- Text-trigger fallback hosts: `super-dev: <需求描述>` or `super-dev：<需求描述>`

## Bootstrap Guidance

Use `super-dev` to open the onboarding flow, then trigger inside the host.

If the repository already has a host onboarded, trigger Super Dev directly inside the host.

## Project Context File

Fill `.super-dev/project.md` with domain constraints, architecture notes, delivery expectations, and team conventions.
"""

    def _render_bootstrap_summary_markdown(self, config, project_dir: Path) -> str:
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

        # Detect installed host surfaces
        installed_items: list[str] = []
        claude_root_md = project_dir / "CLAUDE.md"
        if claude_root_md.exists():
            installed_items.append("`CLAUDE.md` — Claude Code 主规则面")
        claude_md = project_dir / ".claude" / "CLAUDE.md"
        if claude_md.exists():
            installed_items.append("`.claude/CLAUDE.md` — Claude Code 兼容规则镜像")
        settings_json = project_dir / ".claude" / "settings.local.json"
        if settings_json.exists():
            installed_items.append("`.claude/settings.local.json` — enforcement hooks")
        skill_md = project_dir / "SKILL.md"
        if skill_md.exists():
            installed_items.append("`SKILL.md` — pipeline 治理技能")
        cursorrules = project_dir / ".cursorrules"
        if cursorrules.exists():
            installed_items.append("`.cursorrules` — Cursor 编码约束")
        windsurfrules = project_dir / ".windsurfrules"
        if windsurfrules.exists():
            installed_items.append("`.windsurfrules` — Windsurf 编码约束")

        installed_section = ""
        if installed_items:
            installed_section = (
                "\n## 已安装\n\n" + "\n".join(f"- {item}" for item in installed_items) + "\n"
            )

        return f"""# {config.name} Bootstrap

> Generated by `super-dev init`
> Updated: {timestamp}

## 项目信息

- 名称: {config.name}
- 平台: {config.platform}
- 前端: {config.frontend}
- 后端: {config.backend}
- 数据库: {config.database or "未指定"}
- 领域: {config.domain or "未指定"}

## 下一步

1. 在宿主中按宿主模型触发：原生 slash 宿主用 `/super-dev 你的需求`，Codex App/Desktop 从 `/` 列表选 `super-dev`，Codex CLI 用 `$super-dev`，自然语言回退用 `super-dev: 你的需求`
2. Super Dev 会依次执行: 研究 -> 文档 -> 确认 -> Spec -> 编码 -> 质量 -> 交付
3. 每个阶段都有对应的专家主导
{installed_section}
## 生成资产

- `super-dev.yaml`
- `.super-dev/WORKFLOW.md`
- `.super-dev/project.md`
- `.super-dev/AGENTS.md`
- `.super-dev/specs/`
- `.super-dev/changes/`

## 流程说明

1. Super Dev 强制 `research` 先行
2. 宿主依次产出:
   - `output/*-research.md`
   - `output/*-prd.md`
   - `output/*-architecture.md`
   - `output/*-uiux.md`
3. 流程暂停，等待用户确认三文档
4. 确认后才进入 Spec / 任务分解 / 编码实现

## 备注

- 本文档是仓库的初始化可见产物，供开发者和 AI 宿主参考
- `.super-dev/WORKFLOW.md` 是工作流契约
- `super-dev spec init` 可重新初始化 SDD 目录
"""

    def _cmd_product_audit(self, args) -> int:
        """生成产品总审查报告。"""
        from .analyzer import ProductAuditBuilder

        project_path = Path(args.path).resolve()
        if not project_path.exists():
            self.console.print(f"[red]项目不存在: {project_path}[/red]")
            return 1

        try:
            builder = ProductAuditBuilder(project_path)
            report = builder.build()
            output_format = "json" if args.json else args.format

            if output_format == "json":
                output = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
                if args.output:
                    Path(args.output).write_text(output, encoding="utf-8")
                else:
                    builder.write(report)
                    sys.stdout.write(output + "\n")
                return 0

            self.console.print(f"[cyan]正在生成 Product Audit: {project_path}[/cyan]")

            if output_format == "markdown":
                output = report.to_markdown()
                if args.output:
                    Path(args.output).write_text(output, encoding="utf-8")
                    self.console.print(f"[green]Product Audit 已保存到: {args.output}[/green]")
                else:
                    paths = builder.write(report)
                    self.console.print("[green]Product Audit 已生成[/green]")
                    self.console.print(f"  Markdown: {paths['markdown']}")
                    self.console.print(f"  JSON: {paths['json']}")
                return 0

            paths = builder.write(report)
            self.console.print("[green]Product Audit 已生成[/green]")
            self.console.print(f"  项目: {report.project_name}")
            self.console.print(f"  状态: {report.status}")
            self.console.print(f"  分数: {report.score}/100")
            self.console.print(f"  Markdown: {paths['markdown']}")
            self.console.print(f"  JSON: {paths['json']}")
            self.console.print(f"  发现问题: {len(report.findings)}")
            self.console.print("")
            self.console.print(f"[cyan]{report.summary}[/cyan]")
            if report.findings:
                self.console.print("")
                self.console.print("[yellow]优先问题:[/yellow]")
                for item in report.findings[:5]:
                    self.console.print(f"  - [{item.severity}] {item.title}")
            return 0 if report.status == "ready" else 1

        except Exception as e:
            self.console.print(f"[red]Product Audit 生成失败: {e}[/red]")
            self.logger.error(
                "Product Audit 生成失败",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            if "--debug" in sys.argv or "-d" in sys.argv:
                self.console.print(traceback.format_exc())
            return 1

            self.console.print(f"  节点数: {report.node_count}")
            self.console.print(f"  边数: {report.edge_count}")
            self.console.print(f"  关键节点: {len(report.critical_nodes)}")
            self.console.print(f"  关键路径: {len(report.critical_paths)}")
            self.console.print("")
            self.console.print(f"[cyan]{report.summary}[/cyan]")
            return 0

        except Exception as e:
            self.console.print(f"[red]Dependency Graph 生成失败: {e}[/red]")
            self.logger.error(
                "Dependency Graph 生成失败",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            if "--debug" in sys.argv or "-d" in sys.argv:
                self.console.print(traceback.format_exc())
            return 1
