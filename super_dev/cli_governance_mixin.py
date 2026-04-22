"""CLI mixin for governance commands: enforce and generate."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

try:
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class CliGovernanceMixin:
    """Mixin that adds enforce and generate subcommands."""

    # ------------------------------------------------------------------
    # enforce commands
    # ------------------------------------------------------------------

    def _cmd_enforce(self, args: Any) -> int:
        """Route enforce subcommands: install / validate / status."""
        action = getattr(args, "enforce_action", None)
        if action == "install":
            return self._cmd_enforce_install(args)
        if action == "validate":
            return self._cmd_enforce_validate(args)
        if action == "status":
            return self._cmd_enforce_status(args)
        self.console.print("[yellow]请指定 enforce 子命令: install / validate / status[/yellow]")
        return 1

    def _cmd_enforce_install(self, args: Any) -> int:
        """Install enforcement hooks, validation script, and pre-code checklist."""
        try:
            from .enforcement import HostHooksConfigurator
        except Exception as exc:
            self.console.print(f"[red]加载 enforcement 模块失败: {exc}[/red]")
            return 1

        project_dir = Path.cwd()
        host = getattr(args, "host", "claude-code")
        frontend = getattr(args, "frontend", "")
        backend = getattr(args, "backend", "")
        icon_library = getattr(args, "icon_library", "lucide")

        configurator = HostHooksConfigurator(project_dir)
        results: list[str] = []

        # 1. Install hooks
        try:
            settings_path = configurator.install_hooks(host=host)
            results.append(f"Hooks 已安装 -> {settings_path.relative_to(project_dir)}")
        except Exception as exc:
            self.console.print(f"[red]Hooks 安装失败: {exc}[/red]")

        # 2. Generate validation script
        try:
            from .enforcement.validation import ValidationScriptGenerator

            gen = ValidationScriptGenerator()
            script_path = gen.generate(project_dir, frontend=frontend, icon_library=icon_library)
            results.append(f"验证脚本 -> {script_path.relative_to(project_dir)}")
        except Exception as exc:
            self.console.print(f"[red]验证脚本生成失败: {exc}[/red]")

        # 3. Generate pre-code checklist
        try:
            checklist_path = configurator.generate_pre_code_checklist(
                frontend=frontend, backend=backend
            )
            results.append(f"编码前清单 -> {checklist_path.relative_to(project_dir)}")
        except Exception as exc:
            self.console.print(f"[red]编码前清单生成失败: {exc}[/red]")

        if results:
            self.console.print("[green]Enforcement 安装完成:[/green]")
            for r in results:
                self.console.print(f"  {r}")
        else:
            self.console.print("[red]未安装任何 enforcement 组件。[/red]")
            return 1

        return 0

    def _cmd_enforce_validate(self, _args: Any) -> int:
        """Run the validation script."""
        project_dir = Path.cwd()
        script_path = project_dir / "scripts" / "validate-superdev.sh"
        if not script_path.exists():
            self.console.print(
                "[yellow]未找到验证脚本。" "请先运行 'super-dev enforce install'。[/yellow]"
            )
            return 1

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                self.console.print(result.stdout.rstrip())
            if result.stderr:
                self.console.print(f"[dim]{result.stderr.rstrip()}[/dim]")
            return result.returncode
        except subprocess.TimeoutExpired:
            self.console.print("[red]验证脚本执行超时。[/red]")
            return 1
        except Exception as exc:
            self.console.print(f"[red]验证脚本执行失败: {exc}[/red]")
            return 1

    def _cmd_enforce_status(self, _args: Any) -> int:
        """Show enforcement status."""
        try:
            from .enforcement import HostHooksConfigurator
        except Exception as exc:
            self.console.print(f"[red]加载 enforcement 模块失败: {exc}[/red]")
            return 1

        project_dir = Path.cwd()
        configurator = HostHooksConfigurator(project_dir)
        status = configurator.get_status(host="claude-code")

        if RICH_AVAILABLE:
            table = Table(title="Enforcement Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status")
            for key, val in status.items():
                if key == "host":
                    continue
                label = key.replace("_", " ").title()
                if isinstance(val, bool):
                    indicator = "[green]Active[/green]" if val else "[red]Not installed[/red]"
                else:
                    indicator = str(val)
                table.add_row(label, indicator)
            self.console.print(table)
        else:
            self.console.print(f"Host: {status.get('host', 'unknown')}")
            for key, val in status.items():
                if key == "host":
                    continue
                label = key.replace("_", " ").title()
                indicator = "Active" if val else "Not installed"
                self.console.print(f"  {label}: {indicator}")

        # Also check pre-code gate completion
        try:
            from .enforcement.pre_code_gate import PreCodeGate

            gate = PreCodeGate()
            complete, incomplete = gate.check_completion(project_dir)
            if (project_dir / ".super-dev" / "PRE_CODE_CHECKLIST.md").exists():
                if complete:
                    self.console.print("\n[green]Pre-code checklist: ALL COMPLETE[/green]")
                else:
                    self.console.print(
                        f"\n[yellow]Pre-code checklist: "
                        f"{len(incomplete)} item(s) remaining[/yellow]"
                    )
                    for item in incomplete[:5]:
                        self.console.print(f"  - {item}")
        except Exception:
            pass

        return 0

    # ------------------------------------------------------------------
    # generate commands
    # ------------------------------------------------------------------

    def _cmd_generate(self, args: Any) -> int:
        """Route generate subcommands."""
        action = getattr(args, "generate_action", None)
        if action == "scaffold":
            return self._cmd_generate_scaffold(args)
        if action == "components":
            return self._cmd_generate_components(args)
        if action == "types":
            return self._cmd_generate_types(args)
        if action == "tailwind":
            return self._cmd_generate_tailwind(args)
        self.console.print(
            "[yellow]请指定 generate 子命令: scaffold / components / types / tailwind[/yellow]"
        )
        return 1

    def _cmd_generate_scaffold(self, args: Any) -> int:
        """Generate internal implementation reference files."""
        frontend = getattr(args, "frontend", "next")

        if frontend != "next":
            self.console.print(
                f"[yellow]前端框架 '{frontend}' 的内部实施参考模板暂未支持 (coming soon)[/yellow]"
            )
            return 1

        from .creators.nextjs_scaffold import NextjsScaffoldGenerator

        project_dir = Path.cwd()
        project_name = getattr(args, "name", "") or project_dir.name

        generator = NextjsScaffoldGenerator()
        files = generator.generate(project_dir, project_name)

        self.console.print(f"[green]Next.js 内部实施参考模板已生成 ({len(files)} files):[/green]")
        for f in files:
            try:
                rel = f.relative_to(project_dir)
            except ValueError:
                rel = f
            self.console.print(f"  {rel}")

        return 0

    def _cmd_generate_components(self, _args: Any) -> int:
        """Generate internal UI component reference files from UIUX spec."""
        try:
            from .creators.component_scaffold import ComponentScaffoldGenerator

            project_dir = Path.cwd()
            generator = ComponentScaffoldGenerator()
            written = generator.generate_for_project(project_dir)

            if not written:
                self.console.print(
                    "[yellow]未生成组件参考文件（请确认 frontend 为 React 系框架）[/yellow]"
                )
                return 1

            self.console.print(f"[green]组件实施参考已生成 ({len(written)} files):[/green]")
            for f in written:
                try:
                    rel = f.relative_to(project_dir)
                except ValueError:
                    rel = f
                self.console.print(f"  {rel}")
            return 0
        except Exception as exc:
            self.console.print(f"[red]组件参考生成失败: {exc}[/red]")
            return 1

    def _cmd_generate_types(self, _args: Any) -> int:
        """Generate shared TypeScript types from architecture doc."""
        try:
            from .creators.api_contract import APIContractGenerator

            project_dir = Path.cwd()
            generator = APIContractGenerator()
            written = generator.generate_for_project(project_dir)

            if not written:
                self.console.print("[yellow]未生成类型文件[/yellow]")
                return 1

            self.console.print(f"[green]API 类型已生成 ({len(written)} files):[/green]")
            for f in written:
                try:
                    rel = f.relative_to(project_dir)
                except ValueError:
                    rel = f
                self.console.print(f"  {rel}")
            return 0
        except Exception as exc:
            self.console.print(f"[red]类型生成失败: {exc}[/red]")
            return 1

    def _cmd_generate_tailwind(self, _args: Any) -> int:
        """Generate tailwind.config.ts from UIUX spec."""
        try:
            from .creators.component_scaffold import ComponentScaffoldGenerator

            project_dir = Path.cwd()
            generator = ComponentScaffoldGenerator()
            files = generator.generate_all(project_dir)

            if "tailwind.config.ts" not in files:
                self.console.print(
                    "[yellow]未生成 tailwind 配置（请确认 frontend 为 React 系框架）[/yellow]"
                )
                return 1

            output_path = project_dir / "output" / "components" / "tailwind.config.ts"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(files["tailwind.config.ts"], encoding="utf-8")

            try:
                rel = output_path.relative_to(project_dir)
            except ValueError:
                rel = output_path
            self.console.print(f"[green]Tailwind 配置已生成:[/green] {rel}")
            return 0
        except Exception as exc:
            self.console.print(f"[red]Tailwind 配置生成失败: {exc}[/red]")
            return 1

    # ------------------------------------------------------------------
    # completion 命令
    # ------------------------------------------------------------------

    def _cmd_completion(self, args: Any) -> int:
        """输出 shell 补全脚本。"""
        shell = getattr(args, "shell", None)
        if not shell:
            self.console.print("[yellow]请指定 shell 类型: bash / zsh / fish[/yellow]")
            return 1

        from .completion import (
            generate_bash_completion,
            generate_fish_completion,
            generate_zsh_completion,
        )

        generators = {
            "bash": generate_bash_completion,
            "zsh": generate_zsh_completion,
            "fish": generate_fish_completion,
        }
        gen = generators.get(shell)
        if gen is None:
            self.console.print(f"[red]不支持的 shell 类型: {shell}[/red]")
            return 1

        print(gen())  # noqa: T201 — 直接 print 以便 eval 捕获
        return 0

    # ------------------------------------------------------------------
    # feedback 命令
    # ------------------------------------------------------------------

    def _cmd_feedback(self, _args: Any) -> int:
        """打开 GitHub Issues 页面。"""
        url = "https://github.com/shangyankeji/super-dev/issues"
        try:
            import webbrowser

            webbrowser.open(url)
            self.console.print(f"[green]已在浏览器中打开反馈页面:[/green] {url}")
        except Exception:
            self.console.print(f"请在浏览器中打开: {url}")
        return 0

    # ------------------------------------------------------------------
    # migrate 命令
    # ------------------------------------------------------------------

    def _cmd_migrate(self, _args: Any) -> int:
        """执行项目迁移 (2.2.0+ -> 2.4.0)。"""
        from .migrate import migrate_project

        project_dir = Path.cwd()
        self.console.print("[cyan]正在执行 2.2.0+ → 2.4.0 迁移...[/cyan]\n")

        changes = migrate_project(project_dir)

        if not changes:
            self.console.print("[green]项目已是最新状态，无需迁移。[/green]")
            return 0

        self.console.print(f"[green]迁移完成，共 {len(changes)} 项变更:[/green]")
        for change in changes:
            self.console.print(f"  - {change}")
        return 0
