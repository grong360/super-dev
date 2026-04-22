"""CLI design inspiration mixin helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import ConfigManager, get_config_manager


class CliDesignMixin:
    def _resolve_design_command_context(
        self,
        *,
        idea: str = "",
        frontend: str = "",
        product_type: str = "",
        industry: str = "",
        style: str = "",
    ) -> dict[str, object]:
        project_dir = Path.cwd()
        config_manager = get_config_manager(project_dir)
        config = config_manager.load()
        config_exists = config_manager.exists()
        base_name = str(config.name or "").strip() if config_exists else project_dir.name
        if not base_name:
            base_name = project_dir.name or "my-project"
        project_name = self._sanitize_project_name(base_name)
        description = str(idea or "").strip() or str(config.description or "").strip() or project_name
        platform_value = str(config.platform or "web").strip() or "web"
        frontend_value = str(frontend or config.frontend or "next").strip() or "next"
        backend_value = str(config.backend or "node").strip() or "node"
        domain_value = str(config.domain or "").strip()

        from .creators import DocumentGenerator

        generator = DocumentGenerator(
            name=project_name,
            description=description,
            platform=platform_value,
            frontend=frontend_value,
            backend=backend_value,
            domain=domain_value,
            ui_library=config.ui_library,
            style_solution=config.style_solution,
            state_management=list(config.state_management or []),
            testing_frameworks=list(config.testing_frameworks or []),
            design_inspiration_slug=str(getattr(config, "design_inspiration_slug", "") or ""),
            language_preferences=list(config.language_preferences or []),
        )
        analysis = generator._analyze_project_for_design()
        if product_type:
            analysis["product_type"] = product_type.strip().lower()
        if industry:
            analysis["industry"] = industry.strip().lower()
        if style:
            analysis["style"] = style.strip().lower()
        return {
            "project_dir": project_dir,
            "project_name": project_name,
            "description": description,
            "platform": platform_value,
            "frontend": frontend_value,
            "backend": backend_value,
            "domain": domain_value,
            "analysis": analysis,
            "config_manager": config_manager,
            "config_exists": config_exists,
        }

    def _render_design_inspiration_list(self, inspirations: list[dict[str, object]]) -> None:
        if not inspirations:
            self.console.print("[yellow]未找到匹配的设计灵感锚点[/yellow]")
            return
        self.console.print(f"[green]设计灵感锚点 ({len(inspirations)} 个):[/green]\n")
        for idx, item in enumerate(inspirations, 1):
            signals = " / ".join(str(signal) for signal in list(item.get("signals", []))[:3])
            self.console.print(
                f"[cyan]{idx}. {item.get('name', 'N/A')}[/cyan]  [dim]slug={item.get('slug', 'N/A')}[/dim]"
            )
            self.console.print(f"    方向: {item.get('direction', 'N/A')}")
            self.console.print(f"    理由: {item.get('rationale', 'N/A')}")
            if signals:
                self.console.print(f"    参考信号: {signals}")
            source = str(item.get("source", "")).strip()
            if source:
                self.console.print(f"    来源: {source}")
            self.console.print()

    def _cmd_design(self, args) -> int:
        from .design import UIIntelligenceAdvisor

        if args.design_command == "list":
            advisor = UIIntelligenceAdvisor()
            inspirations = [
                item.to_dict()
                for item in advisor.list_design_references(
                    product_type=str(getattr(args, "product_type", "") or "").strip().lower() or None,
                    industry=str(getattr(args, "industry", "") or "").strip().lower() or None,
                    style=str(getattr(args, "style", "") or "").strip().lower() or None,
                    frontend=str(getattr(args, "frontend", "") or "").strip() or None,
                    limit=max(int(getattr(args, "max_results", 10) or 10), 1),
                )
            ]
            self._render_design_inspiration_list(inspirations)
            return 0

        if args.design_command == "recommend":
            advisor = UIIntelligenceAdvisor()
            context = self._resolve_design_command_context(
                idea=str(getattr(args, "idea", "") or ""),
                frontend=str(getattr(args, "frontend", "") or ""),
                product_type=str(getattr(args, "product_type", "") or ""),
                industry=str(getattr(args, "industry", "") or ""),
                style=str(getattr(args, "style", "") or ""),
            )
            analysis = context["analysis"]
            if not isinstance(analysis, dict):
                self.console.print("[red]无法解析当前项目的设计上下文[/red]")
                return 1
            profile = advisor.recommend(
                description=str(context["description"]),
                frontend=str(context["frontend"]),
                product_type=str(analysis.get("product_type", "general")),
                industry=str(analysis.get("industry", "general")),
                style=str(analysis.get("style", "modern")),
            )
            inspirations = [
                item
                for item in list(profile.get("design_references", []))[: max(int(getattr(args, "max_results", 3) or 3), 1)]
                if isinstance(item, dict)
            ]
            self.console.print("[cyan]设计灵感推荐[/cyan]")
            self.console.print(
                f"  项目: {context['project_name']} | 前端: {context['frontend']} | 产品类型: {analysis.get('product_type', 'general')}"
            )
            self.console.print(
                f"  行业: {analysis.get('industry', 'general')} | 风格: {analysis.get('style', 'modern')}"
            )
            self.console.print("  真源: 内部仍以 output/*-uiux.md + output/*-ui-contract.json 为准\n")
            self._render_design_inspiration_list(inspirations)
            return 0

        if args.design_command == "apply":
            advisor = UIIntelligenceAdvisor()
            selected = advisor.get_design_reference(args.slug)
            if selected is None:
                self.console.print(f"[red]未知设计灵感 slug: {args.slug}[/red]")
                self.console.print("[dim]先运行 `super-dev design list` 查看可用 slug[/dim]")
                return 1
            context = self._resolve_design_command_context(idea=str(getattr(args, "idea", "") or ""))
            config_manager = context["config_manager"]
            if not isinstance(config_manager, ConfigManager):
                self.console.print("[red]无法加载项目配置管理器[/red]")
                return 1
            if not bool(context["config_exists"]):
                config_manager.create(
                    name=str(context["project_name"]),
                    description=str(context["description"]),
                    platform=str(context["platform"]),
                    frontend=str(context["frontend"]),
                    backend=str(context["backend"]),
                    domain=str(context["domain"]),
                )
            update_payload: dict[str, object] = {"design_inspiration_slug": selected.slug}
            if (
                str(getattr(args, "idea", "") or "").strip()
                and not str(config_manager.config.description or "").strip()
            ):
                update_payload["description"] = str(getattr(args, "idea", "")).strip()
            updated_config = config_manager.update(**update_payload)

            output_dir = Path.cwd() / str(updated_config.output_dir or "output")
            output_dir.mkdir(parents=True, exist_ok=True)
            project_name = self._sanitize_project_name(str(updated_config.name or context["project_name"]))
            record_path = output_dir / f"{project_name}-design-inspiration.json"
            record_payload = {
                "slug": selected.slug,
                "name": selected.name,
                "rationale": selected.rationale,
                "direction": selected.direction,
                "source": selected.source,
                "signals": list(selected.signals),
                "cautions": list(selected.cautions),
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }
            record_path.write_text(
                json.dumps(record_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.console.print(f"[green]✓[/green] 已应用设计灵感: {selected.name} ({selected.slug})")
            self.console.print(f"  来源: {selected.source}")
            self.console.print(f"  已写入配置: design_inspiration_slug = {selected.slug}")
            self.console.print(f"  记录文件: {record_path}")
            if getattr(args, "write_uiux", True):
                return self._cmd_run_targeted_refresh("uiux")
            return 0

        self.console.print("[yellow]请指定 design 子命令: list / recommend / apply[/yellow]")
        return 1
