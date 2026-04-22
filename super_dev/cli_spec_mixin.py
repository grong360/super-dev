"""CLI spec command mixin helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import get_config_manager
from .terminal import create_console


class CliSpecMixin:
    def _cmd_spec(self, args) -> int:
        """Spec-Driven Development 命令"""
        from .specs import ChangeManager, SpecGenerator, SpecManager
        from .specs.models import ChangeStatus

        project_dir = Path.cwd()

        if args.spec_action == "init":
            generator = SpecGenerator(project_dir)
            generator.init_sdd()
            config = get_config_manager(project_dir).config
            workflow_file, summary_file = self._bootstrap_project_contract(
                project_dir=project_dir,
                config=config,
            )

            self.console.print("[green]✓[/green] SDD 目录结构已初始化")
            self.console.print("  [dim].super-dev/specs/[/dim] - 当前规范")
            self.console.print("  [dim].super-dev/changes/[/dim] - 变更提案")
            self.console.print("  [dim].super-dev/archive/[/dim] - 已归档变更")
            self.console.print(f"  [dim]{workflow_file}[/dim] - 工作流契约")
            self.console.print(f"  [dim]{summary_file}[/dim] - Bootstrap 摘要")
            self.console.print("")
            self.console.print("[cyan]下一步:[/cyan]")
            self.console.print("  1. 编辑 .super-dev/project.md 填写项目上下文")
            self.console.print("  2. 查看 output/*-bootstrap.md 确认初始化结果")
            self.console.print("  3. 运行 'super-dev spec propose <id>' 创建变更提案")

        elif args.spec_action == "list":
            manager = ChangeManager(project_dir)
            status_filter = None
            if args.status:
                status_filter = ChangeStatus(args.status)

            changes = manager.list_changes(status=status_filter)

            if not changes:
                self.console.print("[dim]没有找到变更[/dim]")
                return 0

            self.console.print("[cyan]变更列表:[/cyan]")
            for change in changes:
                status_color = {
                    ChangeStatus.DRAFT: "dim",
                    ChangeStatus.PROPOSED: "yellow",
                    ChangeStatus.APPROVED: "blue",
                    ChangeStatus.IN_PROGRESS: "cyan",
                    ChangeStatus.COMPLETED: "green",
                    ChangeStatus.ARCHIVED: "dim",
                }.get(change.status, "white")

                self.console.print(
                    f"  [{status_color}]{change.id}[/] - {change.title} " f"({change.status.value})"
                )
                if change.tasks:
                    rate = change.completion_rate
                    completed = sum(1 for t in change.tasks if t.status.value == "completed")
                    self.console.print(
                        f"    [dim]进度: {rate:.0f}% ({completed}/{len(change.tasks)} 任务)[/dim]"
                    )

        elif args.spec_action == "show":
            manager = ChangeManager(project_dir)
            loaded_change = manager.load_change(args.change_id)

            if not loaded_change:
                self.console.print(f"[red]变更不存在: {args.change_id}[/red]")
                return 1

            self.console.print(f"[cyan]变更详情: {loaded_change.id}[/cyan]")
            self.console.print(f"  标题: {loaded_change.title}")
            self.console.print(f"  状态: {loaded_change.status.value}")

            if loaded_change.proposal:
                self.console.print("")
                self.console.print("[cyan]提案:[/cyan]")
                if loaded_change.proposal.description:
                    self.console.print(f"  {loaded_change.proposal.description}")
                if loaded_change.proposal.motivation:
                    self.console.print(f"[dim]动机: {loaded_change.proposal.motivation}[/dim]")

            if loaded_change.tasks:
                self.console.print("")
                self.console.print("[cyan]任务:[/cyan]")
                for task in loaded_change.tasks:
                    checkbox = "[x]" if task.status.value == "completed" else "[ ]"
                    self.console.print(f"  {checkbox} {task.id}: {task.title}")

            if loaded_change.spec_deltas:
                self.console.print("")
                self.console.print("[cyan]规范变更:[/cyan]")
                for delta in loaded_change.spec_deltas:
                    self.console.print(f"  - {delta.spec_name} ({delta.delta_type.value})")

        elif args.spec_action == "propose":
            if not self._ensure_execution_gates(project_dir, action_label="创建 Spec 变更"):
                return 1
            generator = SpecGenerator(project_dir)
            change = generator.create_change(
                change_id=args.change_id,
                title=args.title,
                description=args.description,
                motivation=args.motivation or "",
                impact=args.impact or "",
            )
            scaffolded_files: dict[str, Path] = {}
            if not bool(getattr(args, "no_scaffold", False)):
                scaffolded_files = generator.scaffold_change_artifacts(change.id, force=False)

            self.console.print(f"[green]✓[/green] 变更提案已创建: {change.id}")
            self.console.print(f"  [dim].super-dev/changes/{change.id}/[/dim]")
            if scaffolded_files:
                self.console.print("  [dim]已生成 spec/plan/tasks/checklist 四件套[/dim]")
            self.console.print("")
            self.console.print("[cyan]下一步:[/cyan]")
            self.console.print(
                f"  1. 运行 'super-dev spec add-req {change.id} <spec> <req> <desc>' 添加需求"
            )
            self.console.print("  2. 运行 'super-dev spec validate {change.id} -v' 先做规格校验")
            self.console.print(f"  3. 或 'super-dev spec show {change.id}' 查看详情")

        elif args.spec_action == "add-req":
            generator = SpecGenerator(project_dir)
            delta = generator.add_requirement_to_change(
                change_id=args.change_id,
                spec_name=args.spec_name,
                requirement_name=args.req_name,
                description=args.description,
            )

            self.console.print("[green]✓[/green] 需求已添加到变更")
            self.console.print(f"  规范: {delta.spec_name}")
            self.console.print(f"  需求: {args.req_name}")

        elif args.spec_action == "scaffold":
            generator = SpecGenerator(project_dir)
            try:
                generated = generator.scaffold_change_artifacts(
                    args.change_id,
                    force=bool(getattr(args, "force", False)),
                )
            except FileNotFoundError as e:
                self.console.print(f"[red]{e}[/red]")
                return 1
            self.console.print(f"[green]✓[/green] 已生成模板: {args.change_id}")
            for _, file_path in sorted(generated.items(), key=lambda item: str(item[1])):
                self.console.print(f"  [dim]{file_path.relative_to(project_dir)}[/dim]")

        elif args.spec_action == "archive":
            if not args.yes:
                self.console.print(f"[yellow]即将归档变更: {args.change_id}[/yellow]")
                self.console.print("[dim]这将把规范增量合并到主规范中[/dim]")
                response = input("确认? (y/N): ")
                if response.lower() != "y":
                    self.console.print("[dim]已取消[/dim]")
                    return 0

            change_manager = ChangeManager(project_dir)
            spec_manager = SpecManager(project_dir)

            try:
                change = change_manager.archive_change(args.change_id, spec_manager)
                self.console.print(f"[green]✓[/green] 变更已归档: {change.id}")
                self.console.print(f"  [dim].super-dev/archive/{change.id}/[/dim]")
            except FileNotFoundError as e:
                self.console.print(f"[red]{e}[/red]")
                return 1
            except Exception as e:
                self.console.print(f"[red]归档失败: {e}[/red]")
                return 1

        elif args.spec_action == "validate":
            from .specs import SpecValidator

            validator = SpecValidator(project_dir)

            if args.change_id:
                result = validator.validate_change(args.change_id)
                self.console.print(f"[cyan]验证变更: {args.change_id}[/cyan]")
            else:
                result = validator.validate_all()
                self.console.print("[cyan]验证所有变更[/cyan]")

            self.console.print(result.to_summary())

            if args.verbose or (not result.is_valid):
                for error in result.errors:
                    self.console.print(f"  [red]错误[/red]: {error.message}")
                    if error.line > 0:
                        self.console.print(f"    [dim]{error.file}:{error.line}[/dim]")

                for warning in result.warnings:
                    self.console.print(f"  [yellow]警告[/yellow]: {warning.message}")
                    if warning.line > 0:
                        self.console.print(f"    [dim]{warning.file}:{warning.line}[/dim]")

            return 0 if result.is_valid else 1

        elif args.spec_action == "quality":
            from rich.table import Table

            from .specs import SpecValidator

            validator = SpecValidator(project_dir)
            report = validator.assess_change_quality(args.change_id)
            if getattr(args, "json", False):
                sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
                return 0 if report.score >= 75 else 1

            score_color = (
                "green" if report.score >= 90 else ("yellow" if report.score >= 75 else "red")
            )
            self.console.print(
                f"[cyan]Spec 质量评估: {report.change_id}[/cyan] "
                f"[{score_color}]{report.score:.1f}[/] ({report.level})"
            )

            table = Table(show_header=True, header_style="bold magenta", expand=True)
            table.add_column("维度", style="cyan", min_width=10, ratio=1)
            table.add_column("结果", style="white", min_width=6, max_width=10, justify="center")
            table.add_column("说明", style="dim", ratio=3, overflow="fold")
            for key, item in report.checks.items():
                passed = bool(item.get("passed", False))
                reason = str(item.get("reason", "")).strip() or "-"
                table.add_row(key, "[green]pass[/green]" if passed else "[red]fail[/red]", reason)
            self.console.print(table)

            if report.blockers:
                self.console.print("[yellow]缺口:[/yellow]")
                for blocker in report.blockers:
                    self.console.print(f"  - {blocker}")

            if report.suggestions:
                self.console.print("[cyan]建议动作:[/cyan]")
                for suggestion in report.suggestions:
                    self.console.print(f"  - {suggestion}")

            if report.action_plan:
                self.console.print("[cyan]执行计划:[/cyan]")
                for item in report.action_plan:
                    priority = str(item.get("priority", "")).strip()
                    step = str(item.get("step", "")).strip()
                    command = str(item.get("command", "")).strip()
                    prefix = f"[{priority}] " if priority else ""
                    self.console.print(f"  - {prefix}{step}")
                    if command:
                        self.console.print(f"    [dim]{command}[/dim]")

            return 0 if report.score >= 75 else 1

        elif args.spec_action == "view":
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text

            console = create_console()
            change_manager = ChangeManager(project_dir)
            spec_manager = SpecManager(project_dir)

            changes = change_manager.list_changes()
            specs = spec_manager.list_specs()

            title = Text.assemble(
                ("Super Dev ", "bold cyan"),
                ("Spec Dashboard", "bold white"),
            )
            console.print(Panel(title, padding=(0, 1), expand=True))

            if changes:
                table = Table(
                    title="活跃变更", show_header=True, header_style="bold magenta", expand=True
                )
                table.add_column("ID", style="cyan", ratio=2)
                table.add_column("标题", style="white", ratio=3)
                table.add_column("状态", style="yellow", min_width=8)
                table.add_column("进度", style="green", min_width=8)
                table.add_column("任务", style="blue", min_width=6)

                for change in changes:
                    progress = f"{change.completion_rate:.0f}%"
                    tasks = f"{sum(1 for t in change.tasks if t.status.value == 'completed')}/{len(change.tasks)}"
                    table.add_row(
                        change.id,
                        change.title or "(无标题)",
                        change.status.value,
                        progress,
                        tasks,
                    )

                console.print(table)
            else:
                console.print("[dim]没有活跃变更[/dim]")

            if specs:
                console.print("")
                specs_table = Table(
                    title="当前规范", show_header=True, header_style="bold green", expand=True
                )
                specs_table.add_column("规范名称", style="cyan", ratio=1)
                specs_table.add_column("文件路径", style="dim", ratio=2, overflow="fold")

                for spec_name in specs:
                    spec_path = spec_manager.get_spec_path(spec_name)
                    specs_table.add_row(spec_name, str(spec_path.relative_to(project_dir)))

                console.print(specs_table)

            console.print("")
            stats_table = Table(show_header=False, box=None, expand=True)
            stats_table.add_column("指标", style="bold white", ratio=1)
            stats_table.add_column("数量", style="cyan", min_width=6)

            stats_table.add_row("活跃变更", str(len(changes)))
            stats_table.add_row("规范文件", str(len(specs)))
            stats_table.add_row(
                "待处理任务",
                str(sum(1 for c in changes for t in c.tasks if t.status.value == "pending")),
            )

            console.print(stats_table)
            return 0

        elif args.spec_action == "trace":
            from .specs.traceability import RequirementTracer

            tracer = RequirementTracer(project_dir)
            matrix = tracer.generate_matrix(args.change_id)

            if getattr(args, "json", False):
                sys.stdout.write(json.dumps(matrix.to_dict(), ensure_ascii=False, indent=2) + "\n")
            else:
                md = matrix.to_markdown()
                self.console.print(f"[cyan]需求追溯矩阵: {args.change_id}[/cyan]")
                self.console.print(
                    f"  总需求: {matrix.total_count}  "
                    f"已覆盖: {matrix.covered_count}  "
                    f"部分: {matrix.partial_count}  "
                    f"未覆盖: {matrix.uncovered_count}"
                )
                coverage_color = (
                    "green"
                    if matrix.coverage_rate >= 80
                    else ("yellow" if matrix.coverage_rate >= 50 else "red")
                )
                self.console.print(
                    f"  覆盖率: [{coverage_color}]{matrix.coverage_rate:.1f}%[/]  "
                    f"SHALL/MUST: [{coverage_color}]{matrix.shall_coverage:.1f}%[/]"
                )

                if matrix.requirements:
                    self.console.print("")
                    for req in matrix.requirements:
                        status_icon = {
                            "covered": "[green]ok[/green]",
                            "partial": "[yellow]~[/yellow]",
                            "uncovered": "[red]--[/red]",
                        }.get(req.status, "[red]--[/red]")
                        text_short = req.text[:70] + "..." if len(req.text) > 70 else req.text
                        self.console.print(
                            f"  {status_icon} {req.id} [{req.priority}] {text_short}"
                        )

                if getattr(args, "save", False):
                    save_path = (
                        project_dir / ".super-dev" / "changes" / args.change_id / "traceability.md"
                    )
                    save_path.write_text(md, encoding="utf-8")
                    self.console.print(
                        f"\n[green]已保存:[/green] {save_path.relative_to(project_dir)}"
                    )

            return 0

        elif args.spec_action == "consistency":
            from .specs.consistency_checker import SpecConsistencyChecker

            checker = SpecConsistencyChecker(project_dir)
            report = checker.check(args.change_id)

            if getattr(args, "json", False):
                sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
            else:
                score_color = (
                    "green"
                    if report.consistency_score >= 90
                    else ("yellow" if report.consistency_score >= 70 else "red")
                )
                status_text = "[green]通过[/green]" if report.passed else "[red]未通过[/red]"
                self.console.print(
                    f"[cyan]Spec-Code 一致性检测: {args.change_id}[/cyan]  "
                    f"{status_text}  "
                    f"[{score_color}]{report.consistency_score}/100[/]"
                )
                self.console.print(
                    f"  问题: {len(report.issues)} 项 "
                    f"(critical={report.critical_count}, high={report.high_count}, "
                    f"medium={report.medium_count}, low={report.low_count})"
                )

                if report.issues:
                    self.console.print("")
                    for issue in report.issues:
                        severity_color = {
                            "critical": "red",
                            "high": "yellow",
                            "medium": "blue",
                            "low": "dim",
                        }.get(issue.severity, "white")
                        self.console.print(
                            f"  [{severity_color}]{issue.severity.upper()}[/] "
                            f"[{issue.category}] {issue.spec_reference}"
                        )
                        self.console.print(f"    [dim]实际: {issue.actual_state}[/dim]")
                        self.console.print(f"    [dim]建议: {issue.suggestion}[/dim]")

                if getattr(args, "save", False):
                    md = report.to_markdown()
                    save_path = (
                        project_dir / ".super-dev" / "changes" / args.change_id / "consistency.md"
                    )
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    save_path.write_text(md, encoding="utf-8")
                    self.console.print(
                        f"\n[green]已保存:[/green] {save_path.relative_to(project_dir)}"
                    )

            return 0

        elif args.spec_action == "acceptance":
            from .specs.traceability import RequirementTracer

            tracer = RequirementTracer(project_dir)
            checklist = tracer.generate_acceptance_checklist(args.change_id)

            self.console.print(f"[cyan]验收检查清单: {args.change_id}[/cyan]")
            self.console.print(checklist)

            if getattr(args, "save", False):
                save_path = (
                    project_dir / ".super-dev" / "changes" / args.change_id / "acceptance.md"
                )
                save_path.write_text(checklist, encoding="utf-8")
                self.console.print(f"\n[green]已保存:[/green] {save_path.relative_to(project_dir)}")

            return 0

        else:
            self.console.print("[yellow]请指定 SDD 命令[/yellow]")
            return 1

        return 0
