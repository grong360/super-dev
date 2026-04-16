"""CLI release/quality/metrics mixin helpers."""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .config import ConfigManager
from .proof_pack import ProofPackBuilder
from .release_readiness import ReleaseReadinessEvaluator


class CliReleaseQualityMixin:
    def _cmd_release(self, args) -> int:
        """发布就绪度检查"""
        if args.release_command == "proof-pack":
            project_dir = Path.cwd()
            builder = ProofPackBuilder(project_dir)
            report = builder.build(verify_tests=bool(args.verify_tests))
            files = builder.write(report)
            payload = report.to_dict()
            payload["report_file"] = str(files["markdown"])
            payload["json_file"] = str(files["json"])
            payload["summary_file"] = str(files["summary"])

            if args.json:
                self.console.print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0 if report.status == "ready" else 1

            status = (
                "[green]ready[/green]"
                if report.status == "ready"
                else "[yellow]incomplete[/yellow]"
            )
            self.console.print(
                f"[cyan]Proof Pack[/cyan] {status} 证据就绪: {report.ready_count}/{report.total_count}"
            )
            self.console.print(f"  [green]✓[/green] Markdown: {files['markdown']}")
            self.console.print(f"  [green]✓[/green] JSON: {files['json']}")
            self.console.print(f"  [green]✓[/green] Summary: {files['summary']}")
            self.console.print(f"  [dim]{report.executive_summary}[/dim]")
            if report.blockers:
                self.console.print("  [yellow]待补齐项:[/yellow]")
                for artifact in report.blockers[:8]:
                    self.console.print(f"    - {artifact.name}: {artifact.summary}")
                self.console.print("  [cyan]推荐动作:[/cyan]")
                for action in report.next_actions[:5]:
                    self.console.print(f"    - {action}")
            else:
                self.console.print("  [green]所有关键交付证据均已就绪。[/green]")
            return 0 if report.status == "ready" else 1

        if args.release_command != "readiness":
            self.console.print(
                "[yellow]请指定 release 子命令，例如 `super-dev release readiness` 或 `super-dev release proof-pack`[/yellow]"
            )
            return 1

        project_dir = Path.cwd()
        evaluator = ReleaseReadinessEvaluator(project_dir)
        report = evaluator.evaluate(verify_tests=bool(args.verify_tests))
        files = evaluator.write(report)
        payload = report.to_dict()
        payload["report_file"] = str(files["markdown"])
        payload["json_file"] = str(files["json"])

        if args.json:
            self.console.print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if report.passed else 1

        status = "[green]通过[/green]" if report.passed else "[yellow]未完成[/yellow]"
        self.console.print(f"[cyan]发布就绪度[/cyan] {status} 分数: {report.score}/100")
        self.console.print(f"  [green]✓[/green] Markdown: {files['markdown']}")
        self.console.print(f"  [green]✓[/green] JSON: {files['json']}")

        if report.failed_checks:
            self.console.print("  [yellow]待收尾项:[/yellow]")
            for check in report.failed_checks[:8]:
                recommendation = f" | 建议: {check.recommendation}" if check.recommendation else ""
                self.console.print(f"    - {check.name}: {check.detail}{recommendation}")
        else:
            self.console.print("  [green]所有关键发布项均已满足。[/green]")

        return 0 if report.passed else 1

    def _cmd_studio(self, args) -> int:
        """启动交互工作台 API"""
        try:
            import uvicorn
        except ImportError:
            self.console.print("[red]缺少依赖: uvicorn[/red]")
            self.console.print("[dim]请安装: pip install fastapi uvicorn[/dim]")
            return 1

        self.console.print(f"[cyan]启动 Super Dev Studio: http://{args.host}:{args.port}[/cyan]")
        uvicorn.run(
            "super_dev.web.api:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
        return 0

    def _cmd_expert(self, args) -> int:
        """调用专家"""
        from .experts import (
            has_expert,
            has_expert_team,
            list_expert_teams,
            list_experts,
            save_expert_advice,
            save_team_advice,
        )

        # 处理 --list 选项
        if args.list:
            self.console.print("[cyan]可用专家列表:[/cyan]")
            for expert in list_experts():
                self.console.print(
                    f"  [green]{expert['id']:<10}[/green] {expert['name']} - {expert['description']}"
                )
            return 0

        if args.list_teams:
            self.console.print("[cyan]可用专家团队:[/cyan]")
            for team in list_expert_teams():
                self.console.print(
                    f"  [green]{team['id']:<16}[/green] {team['name']} - {team['description']}"
                )
            return 0

        prompt = " ".join(args.prompt) if args.prompt else ""
        if args.team:
            self.console.print(f"[cyan]调用专家团队: {args.expert_name}[/cyan]")
            self.console.print(f"[dim]提示词: {prompt or '(无)'}[/dim]")
            if not args.expert_name or not has_expert_team(args.expert_name):
                self.console.print(f"[red]未知专家团队: {args.expert_name or '(未提供)'}[/red]")
                return 1
            report_file, _ = save_team_advice(
                project_dir=Path.cwd(),
                team_id=args.expert_name,
                prompt=prompt,
            )
            self.console.print(f"[green]✓[/green] 团队审查报告已生成: {report_file}")
            return 0

        # 如果没有提供专家名称，显示帮助
        if not args.expert_name:
            self.console.print(
                "[yellow]请提供专家名称，或使用 --list / --list-teams 查看可用专家[/yellow]"
            )
            return 1

        self.console.print(f"[cyan]调用专家: {args.expert_name}[/cyan]")
        self.console.print(f"[dim]提示词: {prompt or '(无)'}[/dim]")
        if not has_expert(args.expert_name):
            self.console.print(f"[red]未知专家: {args.expert_name}[/red]")
            return 1

        report_file, _ = save_expert_advice(
            project_dir=Path.cwd(),
            expert_id=args.expert_name,
            prompt=prompt,
        )
        self.console.print(f"[green]✓[/green] 专家建议已生成: {report_file}")
        return 0

    def _cmd_quality(self, args) -> int:
        """质量检查"""
        from .reviewers import QualityGateChecker, UIReviewReviewer
        from .reviewers.redteam import load_persisted_redteam_report

        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config_manager = ConfigManager(project_dir)
        config = config_manager.load()

        project_name = self._sanitize_project_name(config.name or project_dir.name)
        tech_stack = {
            "platform": config.platform,
            "frontend": self._normalize_pipeline_frontend(config.frontend),
            "backend": config.backend,
            "domain": config.domain,
        }

        self.console.print(f"[cyan]运行质量检查: {args.type}[/cyan]")

        if args.type == "ui-review":
            reviewer = UIReviewReviewer(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            report = reviewer.review()
            review_file = output_dir / f"{project_name}-ui-review.md"
            review_json_file = output_dir / f"{project_name}-ui-review.json"
            alignment_file = output_dir / f"{project_name}-ui-contract-alignment.md"
            alignment_json_file = output_dir / f"{project_name}-ui-contract-alignment.json"
            review_file.write_text(report.to_markdown(), encoding="utf-8")
            review_json_file.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            alignment_file.write_text(report.alignment_markdown(), encoding="utf-8")
            alignment_json_file.write_text(
                json.dumps(report.alignment_summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            status = "[green]通过[/green]" if report.passed else "[yellow]需修正[/yellow]"
            self.console.print(f"  {status} 总分: {report.score}/100")
            self.console.print(f"  [green]✓[/green] 报告: {review_file}")
            self.console.print(f"  [green]✓[/green] JSON: {review_json_file}")
            self.console.print(f"  [green]✓[/green] UI 契约对齐: {alignment_file}")
            self.console.print(f"  [green]✓[/green] UI 契约对齐 JSON: {alignment_json_file}")
            if report.findings:
                self.console.print("[yellow]主要问题:[/yellow]")
                for finding in report.findings[:5]:
                    self.console.print(f"  - [{finding.level}] {finding.title}")
            return 0 if report.passed else 1

        if args.type == "redteam":
            from .reviewers import RedTeamReviewer

            reviewer = RedTeamReviewer(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            report = reviewer.review()
            report_file = output_dir / f"{project_name}-redteam.md"
            report_json_file = output_dir / f"{project_name}-redteam.json"
            report_file.write_text(report.to_markdown(), encoding="utf-8")
            report_json_file.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            status = "[green]通过[/green]" if report.passed else "[yellow]需修正[/yellow]"
            self.console.print(f"  {status} 总分: {report.total_score}/100")
            self.console.print(f"  [green]✓[/green] 报告: {report_file}")
            self.console.print(f"  [green]✓[/green] JSON: {report_json_file}")
            if report.blocking_reasons:
                self.console.print("[yellow]阻断原因:[/yellow]")
                for reason in report.blocking_reasons:
                    self.console.print(f"  - {reason}")
            return 0 if report.passed else 1

        # 轻量文档检查
        if args.type in {"prd", "architecture", "ui", "ux"}:
            pattern_map = {
                "prd": "*-prd.md",
                "architecture": "*-architecture.md",
                "ui": "*-uiux.md",
                "ux": "*-uiux.md",
            }
            expected_pattern = pattern_map[args.type]
            matched = sorted(output_dir.glob(expected_pattern))
            if matched:
                self.console.print(
                    f"[green]✓[/green] 检测到 {len(matched)} 个文档: {expected_pattern}"
                )
                for file_path in matched[:5]:
                    self.console.print(f"  - {file_path}")
                return 0

            self.console.print(f"[red]未找到文档: output/{expected_pattern}[/red]")
            return 1

        # 代码或全量检查走质量门禁评估
        gate_checker = QualityGateChecker(
            project_dir=project_dir,
            name=project_name,
            tech_stack=tech_stack,
            host_compatibility_min_score_override=config.host_compatibility_min_score,
            host_compatibility_min_ready_hosts_override=config.host_compatibility_min_ready_hosts,
        )
        persisted_redteam = load_persisted_redteam_report(project_dir, project_name)
        gate_result = gate_checker.check(
            redteam_report=persisted_redteam[1] if persisted_redteam else None
        )

        gate_file = output_dir / f"{project_name}-quality-gate.md"
        gate_file.write_text(gate_result.to_markdown(), encoding="utf-8")
        if gate_checker.latest_ui_review_report is not None:
            ui_review_file = output_dir / f"{project_name}-ui-review.md"
            ui_review_json_file = output_dir / f"{project_name}-ui-review.json"
            alignment_file = output_dir / f"{project_name}-ui-contract-alignment.md"
            alignment_json_file = output_dir / f"{project_name}-ui-contract-alignment.json"
            ui_review_file.write_text(
                gate_checker.latest_ui_review_report.to_markdown(),
                encoding="utf-8",
            )
            ui_review_json_file.write_text(
                json.dumps(
                    gate_checker.latest_ui_review_report.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            alignment_file.write_text(
                gate_checker.latest_ui_review_report.alignment_markdown(),
                encoding="utf-8",
            )
            alignment_json_file.write_text(
                json.dumps(
                    gate_checker.latest_ui_review_report.alignment_summary,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if (output_dir / "frontend" / "index.html").exists():
                self._write_frontend_runtime_validation(
                    project_dir=project_dir,
                    output_dir=output_dir,
                    project_name=project_name,
                )

        scenario_label = "0-1 新建项目" if gate_result.scenario == "0-1" else "1-N+1 增量开发"
        status = "[green]通过[/green]" if gate_result.passed else "[red]未通过[/red]"

        self.console.print(f"  [dim]场景: {scenario_label}[/dim]")
        self.console.print(f"  {status} 总分: {gate_result.total_score}/100")
        self.console.print(f"  [green]✓[/green] 报告: {gate_file}")
        if gate_checker.latest_ui_review_report is not None:
            self.console.print(
                f"  [green]✓[/green] UI 审查: {output_dir / f'{project_name}-ui-review.md'}"
            )
            self.console.print(
                f"  [green]✓[/green] UI 审查 JSON: {output_dir / f'{project_name}-ui-review.json'}"
            )
            self.console.print(
                f"  [green]✓[/green] UI 契约对齐: {output_dir / f'{project_name}-ui-contract-alignment.md'}"
            )

        if not gate_result.passed and gate_result.critical_failures:
            self.console.print("[yellow]关键失败项:[/yellow]")
            for failure in gate_result.critical_failures:
                self.console.print(f"  - {failure}")

        # Post-merge safety check: detect silently dropped code hunks
        from .merge_safety import detect_dropped_hunks

        merge_result = detect_dropped_hunks(project_dir)
        if merge_result["merge_detected"]:
            if merge_result["safe"]:
                self.console.print("[green]  ✓ 合并安全检查通过 — 未检测到丢失的代码块[/green]")
            else:
                self.console.print(
                    f"[red]  ✗ 合并安全检查: 检测到 {len(merge_result['dropped_files'])} "
                    f"个文件可能丢失代码块[/red]"
                )
                for entry in merge_result["dropped_files"]:
                    self.console.print(
                        f"    [yellow]{entry['file']}[/yellow] (来自 {entry['parent']})"
                    )
                    for block in entry["blocks"][:3]:
                        self.console.print(
                            f"      行 {block['start_line']}-{block['end_line']} "
                            f"({block['line_count']} 行)"
                        )

        return 0 if gate_result.passed else 1

    def _cmd_metrics(self, args) -> int:
        """查看最近一次流水线指标"""
        output_dir = Path.cwd() / "output"
        if not output_dir.exists():
            self.console.print("[yellow]未找到 output 目录，请先执行流水线[/yellow]")
            return 1

        if args.history:
            limit = max(1, int(args.limit))
            history_dir = output_dir / "metrics-history"
            candidates: list[Path] = []
            if history_dir.exists():
                candidates.extend(history_dir.glob("*-pipeline-metrics-*.json"))
            if not candidates:
                candidates.extend(output_dir.glob("*-pipeline-metrics.json"))
            if args.project:
                prefix = f"{self._sanitize_project_name(args.project)}-pipeline-metrics"
                candidates = [item for item in candidates if item.name.startswith(prefix)]
            candidates = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[
                :limit
            ]
            if not candidates:
                self.console.print("[yellow]未找到 pipeline 历史指标文件[/yellow]")
                return 1

            items: list[dict[str, Any]] = []
            for file_path in candidates:
                try:
                    payload = json.loads(file_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                items.append(
                    {
                        "file": file_path.name,
                        "project": payload.get("project_name", ""),
                        "success": bool(payload.get("success", False)),
                        "success_rate": float(payload.get("success_rate", 0)),
                        "duration": float(payload.get("total_duration_seconds", 0)),
                        "started_at": str(payload.get("started_at", "")),
                    }
                )

            if not items:
                self.console.print("[yellow]指标文件存在但无法解析[/yellow]")
                return 1

            run_count = len(items)
            success_count = sum(1 for item in items if item["success"])
            avg_duration = sum(item["duration"] for item in items) / run_count
            avg_success_rate = sum(item["success_rate"] for item in items) / run_count
            self.console.print("[cyan]Pipeline 历史趋势[/cyan]")
            self.console.print(f"  记录数: {run_count}")
            self.console.print(f"  成功次数: {success_count}/{run_count}")
            self.console.print(f"  平均成功率: {avg_success_rate:.1f}%")
            self.console.print(f"  平均耗时: {avg_duration:.2f}s")
            self.console.print("  最近记录:")
            for item in items:
                marker = "✓" if item["success"] else "✗"
                started_at = item["started_at"] or "-"
                self.console.print(
                    f"    {marker} {item['file']} | {item['project']} | "
                    f"success_rate={item['success_rate']:.1f}% | duration={item['duration']:.2f}s | start={started_at}"
                )
            return 0

        if args.project:
            metrics_file = (
                output_dir / f"{self._sanitize_project_name(args.project)}-pipeline-metrics.json"
            )
            if not metrics_file.exists():
                self.console.print(f"[red]未找到指标文件: {metrics_file.name}[/red]")
                return 1
        else:
            candidates = sorted(
                output_dir.glob("*-pipeline-metrics.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if not candidates:
                self.console.print(
                    '[yellow]未找到 pipeline 指标文件，请先运行 super-dev "需求"[/yellow]'
                )
                return 1
            metrics_file = candidates[0]

        try:
            payload = json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            self.console.print(f"[red]指标文件解析失败: {metrics_file.name}[/red]")
            return 1
        self.console.print(f"[cyan]Pipeline 指标: {metrics_file.name}[/cyan]")
        self.console.print(f"  项目: {payload.get('project_name', '')}")
        self.console.print(f"  成功: {payload.get('success', False)}")
        self.console.print(f"  成功率: {payload.get('success_rate', 0)}%")
        self.console.print(f"  总耗时: {payload.get('total_duration_seconds', 0)}s")
        if payload.get("started_at"):
            self.console.print(f"  开始时间(UTC): {payload.get('started_at')}")
        if payload.get("finished_at"):
            self.console.print(f"  结束时间(UTC): {payload.get('finished_at')}")
        self.console.print(f"  阶段数: {len(payload.get('stages', []))}")
        if payload.get("failure_reason"):
            self.console.print(f"  失败原因: {payload['failure_reason']}")
        self.console.print(f"  文件: {metrics_file}")

        # Show per-phase cost data from PipelineCostTracker if available
        try:
            from .pipeline_cost import PipelineCostTracker

            tracker = PipelineCostTracker()
            cost = tracker.load(Path.cwd())
            if cost and cost.phases:
                self.console.print("\n[cyan]Per-Phase Cost Breakdown:[/cyan]")
                for name, phase_cost in cost.phases.items():
                    parts = [f"{phase_cost.duration_seconds:.2f}s"]
                    if phase_cost.files_read:
                        parts.append(f"read={phase_cost.files_read}")
                    if phase_cost.files_written:
                        parts.append(f"written={phase_cost.files_written}")
                    if phase_cost.commands_executed:
                        parts.append(f"cmds={phase_cost.commands_executed}")
                    self.console.print(f"  {name}: {' | '.join(parts)}")
                self.console.print(f"  Total: {cost.total_duration:.2f}s")
        except Exception:
            pass

        return 0

    # ------------------------------------------------------------------
    # history — list past pipeline runs
    # ------------------------------------------------------------------

    def _cmd_history(self, args) -> int:
        """列出过去的流水线运行记录。"""
        project_dir = Path.cwd()
        history_dir = project_dir / ".super-dev" / "workflow-history"
        events_file = project_dir / ".super-dev" / "workflow-events.jsonl"

        # Collect run records from workflow-history snapshots
        records: list[dict[str, Any]] = []

        if history_dir.exists():
            for snapshot_file in sorted(
                history_dir.glob("workflow-state-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                try:
                    payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                status_raw = str(
                    payload.get("status", "") or payload.get("workflow_status", "")
                ).strip()
                run_id = payload.get("run_id", snapshot_file.stem)
                phase = str(payload.get("current_step_label", "")).strip() or status_raw
                quality_score = payload.get("quality_score", "")
                timestamp = str(payload.get("updated_at", "")).strip()
                records.append(
                    {
                        "run_id": run_id,
                        "phase": phase,
                        "status": status_raw,
                        "quality_score": quality_score,
                        "timestamp": timestamp,
                    }
                )

        # Also parse workflow-events.jsonl for additional entries
        if events_file.exists():
            seen_ids: set[str] = {r["run_id"] for r in records}
            try:
                lines = events_file.read_text(encoding="utf-8").splitlines()
            except Exception:
                lines = []
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except Exception:
                    continue
                evt_id = evt.get("source_path", "") + evt.get("timestamp", "")
                if evt_id in seen_ids:
                    continue
                seen_ids.add(evt_id)
                records.append(
                    {
                        "run_id": evt.get("event", ""),
                        "phase": evt.get("current_step_label", ""),
                        "status": evt.get("status", ""),
                        "quality_score": "",
                        "timestamp": evt.get("timestamp", ""),
                    }
                )

        # Also check for latest.json
        latest_file = history_dir / "latest.json" if history_dir.exists() else None
        if latest_file and latest_file.exists():
            try:
                payload = json.loads(latest_file.read_text(encoding="utf-8"))
                run_id = payload.get("run_id", "latest")
                phase = str(payload.get("current_step_label", "")).strip()
                status_raw = str(
                    payload.get("status", "") or payload.get("workflow_status", "")
                ).strip()
                quality_score = payload.get("quality_score", "")
                timestamp = str(payload.get("updated_at", "")).strip()
                # Avoid duplicate if latest already in history
                if not any(r["run_id"] == run_id and r["timestamp"] == timestamp for r in records):
                    records.insert(
                        0,
                        {
                            "run_id": run_id,
                            "phase": phase or status_raw,
                            "status": status_raw,
                            "quality_score": quality_score,
                            "timestamp": timestamp,
                        },
                    )
            except Exception:
                pass

        # Filter by status
        status_filter = getattr(args, "status", None)
        if status_filter:
            status_lower = status_filter.lower()
            filtered: list[dict[str, Any]] = []
            for rec in records:
                rec_status = rec["status"].lower()
                if status_lower == "success" and "success" in rec_status:
                    filtered.append(rec)
                elif status_lower == "failed" and ("fail" in rec_status or "error" in rec_status):
                    filtered.append(rec)
                elif status_lower == "running" and (
                    "running" in rec_status or "progress" in rec_status
                ):
                    filtered.append(rec)
            records = filtered

        # Sort by timestamp descending
        records.sort(key=lambda r: r["timestamp"], reverse=True)

        # Apply limit
        limit = max(1, getattr(args, "limit", 10))
        records = records[:limit]

        if not records:
            self.console.print("[yellow]未找到历史流水线运行记录[/yellow]")
            self.console.print(
                "  提示: 运行一次流水线后，记录会自动保存在 .super-dev/workflow-history/"
            )
            return 0

        if RICH_AVAILABLE:
            table = Table(title="Pipeline History")
            table.add_column("Run ID", style="cyan", max_width=36)
            table.add_column("Phase", style="white")
            table.add_column("Status", style="white")
            table.add_column("Quality", justify="right")
            table.add_column("Timestamp", style="dim")
            for rec in records:
                status_style = self._status_style(rec["status"])
                table.add_row(
                    str(rec["run_id"])[:36],
                    str(rec["phase"])[:40],
                    f"[{status_style}]{rec['status']}[/{status_style}]",
                    str(rec["quality_score"]) if rec["quality_score"] else "-",
                    rec["timestamp"][:25],
                )
            self.console.print(table)
        else:
            for rec in records:
                self.console.print(
                    f"  {rec['run_id'][:36]}  {rec['phase'][:40]}  "
                    f"{rec['status']}  {rec['quality_score'] or '-'}  {rec['timestamp'][:25]}"
                )

        return 0

    @staticmethod
    def _status_style(status: str) -> str:
        """Return a Rich style string for a status value."""
        s = status.lower()
        if "success" in s or "done" in s or "complete" in s:
            return "green"
        if "fail" in s or "error" in s:
            return "red"
        if "running" in s or "progress" in s:
            return "yellow"
        return "white"

    # ------------------------------------------------------------------
    # cost — show LLM cost report
    # ------------------------------------------------------------------

    def _cmd_cost(self, _args) -> int:
        """显示流水线各阶段的 LLM 调用耗时与 token 消耗。"""
        project_dir = Path.cwd()

        # Load pipeline cost from .super-dev/metrics/pipeline-cost.json
        cost_data: dict[str, Any] | None = None
        cost_path = project_dir / ".super-dev" / "metrics" / "pipeline-cost.json"
        if cost_path.exists():
            try:
                cost_data = json.loads(cost_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Also check for pipeline metrics in output/
        metrics_data: dict[str, Any] | None = None
        output_dir = project_dir / "output"
        if output_dir.exists():
            candidates = sorted(
                output_dir.glob("*-pipeline-metrics.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                try:
                    metrics_data = json.loads(candidates[0].read_text(encoding="utf-8"))
                except Exception:
                    pass

        if not cost_data and not metrics_data:
            self.console.print("[yellow]未找到成本或指标数据[/yellow]")
            self.console.print("  提示: 运行一次流水线后，成本数据会自动保存在 .super-dev/metrics/")
            self.console.print("  查看指标: super-dev metrics")
            return 0

        # Build a unified table from available data
        rows: list[dict[str, str]] = []

        if cost_data and cost_data.get("phases"):
            for name, phase in cost_data["phases"].items():
                duration = float(phase.get("duration_seconds", 0))
                files_read = int(phase.get("files_read", 0))
                files_written = int(phase.get("files_written", 0))
                cmds = int(phase.get("commands_executed", 0))
                # Estimate tokens based on file operations (rough heuristic)
                estimated_tokens = (files_read + files_written) * 500 + cmds * 200
                # Rough cost estimate at ~$0.01 per 1K tokens
                cost_estimate = estimated_tokens / 1000 * 0.01
                rows.append(
                    {
                        "phase": name,
                        "duration": f"{duration:.2f}s",
                        "estimated_tokens": f"{estimated_tokens:,}",
                        "files_read": str(files_read),
                        "files_written": str(files_written),
                        "cost_estimate": f"${cost_estimate:.4f}",
                    }
                )
            # Add total row
            total_duration = float(cost_data.get("total_duration", 0))
            total_tokens = sum(int(r["estimated_tokens"].replace(",", "")) for r in rows)
            total_cost = total_tokens / 1000 * 0.01
            rows.append(
                {
                    "phase": "[bold]TOTAL[/bold]",
                    "duration": f"{total_duration:.2f}s",
                    "estimated_tokens": f"{total_tokens:,}",
                    "files_read": "",
                    "files_written": "",
                    "cost_estimate": f"${total_cost:.4f}",
                }
            )

        if metrics_data:
            self.console.print(
                f"[cyan]Pipeline Metrics[/cyan]  project={metrics_data.get('project_name', '')}"
            )
            self.console.print(
                f"  success={metrics_data.get('success', False)}  "
                f"success_rate={metrics_data.get('success_rate', 0)}%  "
                f"total_duration={metrics_data.get('total_duration_seconds', 0)}s"
            )
            if metrics_data.get("started_at"):
                self.console.print(f"  started: {metrics_data['started_at']}")
            if metrics_data.get("finished_at"):
                self.console.print(f"  finished: {metrics_data['finished_at']}")

        if not rows:
            self.console.print("[yellow]成本数据中无阶段明细[/yellow]")
            return 0

        if RICH_AVAILABLE:
            table = Table(title="Pipeline Cost Report")
            table.add_column("Phase", style="cyan")
            table.add_column("Duration", justify="right")
            table.add_column("Est. Tokens", justify="right")
            table.add_column("Files Read", justify="right")
            table.add_column("Files Written", justify="right")
            table.add_column("Cost Est.", justify="right", style="green")
            for row in rows:
                table.add_row(
                    row["phase"],
                    row["duration"],
                    row["estimated_tokens"],
                    row["files_read"],
                    row["files_written"],
                    row["cost_estimate"],
                )
            self.console.print(table)
        else:
            for row in rows:
                self.console.print(
                    f"  {row['phase']:<20} {row['duration']:>10} "
                    f"{row['estimated_tokens']:>12} {row['cost_estimate']:>10}"
                )

        self.console.print(
            "\n  [dim]Note: Token counts and costs are rough estimates based on file operations.[/dim]"
        )
        return 0

    # ------------------------------------------------------------------
    # diff — show pipeline changes
    # ------------------------------------------------------------------

    def _cmd_diff(self, args) -> int:
        """对比当前与上一阶段的文件变更。"""
        project_dir = Path.cwd()
        output_dir = project_dir / "output"

        phase_filter = getattr(args, "phase", None)

        if not output_dir.exists():
            self.console.print("[yellow]未找到 output 目录，请先执行流水线[/yellow]")
            return 0

        # Collect files from output/
        files: list[dict[str, Any]] = []
        for item in sorted(output_dir.rglob("*")):
            if not item.is_file():
                continue
            if item.name.startswith("."):
                continue
            stat = item.stat()
            rel_path = str(item.relative_to(output_dir))

            # Apply phase filter
            if phase_filter and phase_filter.lower() not in rel_path.lower():
                continue

            files.append(
                {
                    "path": rel_path,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

        if not files:
            self.console.print("[yellow]output 目录中无产物文件[/yellow]")
            return 0

        # Sort by modification time descending
        files.sort(key=lambda f: f["modified"], reverse=True)

        # Display file listing
        if RICH_AVAILABLE:
            table = Table(title="Output Artifacts")
            table.add_column("File", style="cyan")
            table.add_column("Size", justify="right")
            table.add_column("Modified", style="dim")
            for f in files[:50]:  # Cap display
                mtime = datetime.datetime.fromtimestamp(
                    f["modified"], tz=datetime.timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
                size_str = self._format_file_size(f["size"])
                table.add_row(f["path"], size_str, mtime)
            self.console.print(table)
        else:
            for f in files[:50]:
                mtime = datetime.datetime.fromtimestamp(
                    f["modified"], tz=datetime.timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
                size_str = self._format_file_size(f["size"])
                self.console.print(f"  {f['path']:<50} {size_str:>10}  {mtime}")

        # Try git diff on output directory
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "--", "output/"],
                capture_output=True,
                text=True,
                cwd=str(project_dir),
                timeout=10,
            )
            if result.stdout.strip():
                self.console.print("\n[cyan]Git Diff (output/):[/cyan]")
                self.console.print(result.stdout.strip())
            else:
                self.console.print(
                    "\n[dim]No uncommitted changes detected in output/ via git.[/dim]"
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.console.print("\n[dim]Git not available or timed out.[/dim]")

        return 0

    @staticmethod
    def _format_file_size(size: int) -> str:
        """Format file size in human-readable form."""
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    # ==================== v3.0 Intelligence Commands ====================

    def _cmd_compliance(self, args) -> int:
        """Run spec compliance checks."""
        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        check_type = getattr(args, "type", "all")
        as_json = getattr(args, "json", False)
        save = getattr(args, "save", False)

        results: dict[str, Any] = {}

        if check_type in ("all", "spec"):
            from ..reviewers.spec_compliance import run_spec_compliance

            report = run_spec_compliance(project_dir, output_dir if save else None)
            results["spec_compliance"] = report.to_dict()
            if not as_json:
                self.console.print("\n[bold]Spec Compliance[/bold]")
                self.console.print(
                    f"  Requirements: {report.total_requirements} | "
                    f"Found: {report.found} | Partial: {report.partial} | Missing: {report.missing}"
                )
                self.console.print(f"  Coverage: {report.coverage_percent}% | Score: {report.score}/100")

        if check_type in ("all", "architecture"):
            from ..reviewers.architecture_drift import run_architecture_drift

            report = run_architecture_drift(project_dir, output_dir if save else None)
            results["architecture_drift"] = report.to_dict()
            if not as_json:
                self.console.print("\n[bold]Architecture Drift[/bold]")
                self.console.print(
                    f"  Drifts: {report.total_drifts} | Critical: {report.critical_count} | Score: {report.score}/100"
                )

        if check_type in ("all", "uiux"):
            from ..reviewers.uiux_compliance import run_uiux_compliance

            report = run_uiux_compliance(project_dir, output_dir if save else None)
            results["uiux_compliance"] = report.to_dict()
            if not as_json:
                self.console.print("\n[bold]UIUX Compliance[/bold]")
                self.console.print(
                    f"  Files scanned: {report.files_scanned} | Violations: {report.total_violations} | "
                    f"Critical: {report.critical_count} | Score: {report.score}/100"
                )

        if as_json:
            self.console.print_json(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    def _cmd_parity(self, args) -> int:
        """Run multi-host parity check."""
        from ..integrations.parity_verifier import run_parity_check

        project_dir = Path.cwd()
        reference = getattr(args, "reference", "claude-code")
        as_json = getattr(args, "json", False)
        save = getattr(args, "save", False)

        report = run_parity_check(project_dir, reference, project_dir / "output" if save else None)

        if as_json:
            self.console.print_json(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            self.console.print("\n[bold]Multi-Host Parity Report[/bold]")
            self.console.print(f"  Hosts scanned: {report.hosts_scanned}")
            self.console.print(f"  Total items: {report.total_items}")
            self.console.print(f"  Parity issues: {report.parity_issues}")
            self.console.print(f"  Score: {report.score}/100")

            issues = [d for d in report.diffs if d.is_parity_issue]
            if issues:
                self.console.print("\n[yellow]Parity issues found:[/yellow]")
                for d in issues[:10]:
                    missing = ", ".join(d.hosts_missing_it) or "(none)"
                    self.console.print(f"  - {d.item_name} ({d.item_type}): missing in [{missing}]")
        return 0

    def _cmd_hooks(self, args) -> int:
        """Manage host hooks."""
        hooks_action = getattr(args, "hooks_action", None)
        if hooks_action != "generate":
            self.console.print("[yellow]Usage: super-dev hooks generate [--host HOST] [--dry-run][/yellow]")
            return 1

        from ..hooks.host_hooks_generator import generate_host_hooks

        project_dir = Path.cwd()
        hosts = getattr(args, "host", None)
        dry_run = getattr(args, "dry_run", False)

        result = generate_host_hooks(project_dir, hosts, dry_run)

        self.console.print(f"\n[bold]Hooks Generation[/bold] {'(dry-run)' if dry_run else ''}")
        for config in result.generated:
            self.console.print(f"  [green]+[/green] {config.host_name}: {config.config_path}")
        for err in result.errors:
            self.console.print(f"  [red]x[/red] {err}")
        return 0

    def _cmd_context(self, args) -> int:
        """Manage codified context."""
        context_action = getattr(args, "context_action", None)

        if context_action == "evolve":
            from ..memory.codified_context import evolve_codified_context

            report = evolve_codified_context(Path.cwd())

            if getattr(args, "json", False):
                self.console.print_json(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
            else:
                self.console.print("\n[bold]Codified Context Evolution[/bold]")
                self.console.print(f"  Entries: {report.total_entries}")
                self.console.print(f"  Total chars: {report.total_chars}")
                self.console.print(f"  Output: {report.output_path}")

        elif context_action == "brief":
            from ..memory.session_auto_brief import generate_auto_brief

            result = generate_auto_brief(Path.cwd())

            if getattr(args, "json", False):
                self.console.print_json(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                self.console.print("\n[bold]Auto Session Brief[/bold]")
                self.console.print(f"  Phases: {result.phases_completed}/{result.phases_total}")
                self.console.print(f"  Current: {result.current_phase or '(none)'}")
                self.console.print(f"  Next: {result.next_step}")
                self.console.print(f"  Output: {result.brief_path}")
        else:
            self.console.print("[yellow]Usage: super-dev context <evolve|brief>[/yellow]")
            return 1
        return 0

    def _cmd_testgen(self, args) -> int:
        """Generate tests from spec artifacts."""
        from ..creators.test_generator import run_test_generation

        project_dir = Path.cwd()
        as_json = getattr(args, "json", False)

        report = run_test_generation(project_dir)

        if as_json:
            self.console.print_json(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            self.console.print("\n[bold]Test Generation Report[/bold]")
            self.console.print(f"  Acceptance tests: {report.acceptance_tests}")
            self.console.print(f"  Contract tests: {report.contract_tests}")
            self.console.print(f"  Total generated: {report.total_generated}")
            for t in report.tests:
                self.console.print(f"  [green]+[/green] {t.test_type}: {t.path}")
        return 0

    def _cmd_feedback_collect(self, args) -> int:
        """Collect feedback from git history."""
        from ..reviewers.feedback_collector import run_feedback_collection

        project_dir = Path.cwd()
        max_commits = getattr(args, "max_commits", 100)

        report = run_feedback_collection(project_dir, max_commits)

        if getattr(args, "json", False):
            self.console.print_json(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            self.console.print("\n[bold]Feedback Collection Report[/bold]")
            self.console.print(f"  Commits analyzed: {report.total_commits_analyzed}")
            self.console.print(f"  Feedback entries: {report.feedback_entries}")
            if report.domain_distribution:
                self.console.print("  Domain distribution:")
                for domain, count in sorted(
                    report.domain_distribution.items(), key=lambda x: -x[1]
                ):
                    self.console.print(f"    - {domain}: {count}")
        return 0
