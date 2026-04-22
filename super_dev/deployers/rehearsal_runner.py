"""
开发：Excellent（11964948@qq.com）
功能：发布演练执行器
作用：验证发布就绪度，执行预发布检查清单
创建时间：2025-12-30
最后修改：2026-03-20
"""

from __future__ import annotations

import json
import os
import re
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..evidence_identity import build_evidence_identity
from ..reviewers.redteam import load_redteam_evidence


@dataclass
class RehearsalCheck:
    name: str
    passed: bool
    detail: str
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass
class RehearsalResult:
    project_name: str
    checks: list[RehearsalCheck] = field(default_factory=list)
    threshold: int = 80
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evidence_identity: dict[str, Any] = field(default_factory=dict)

    @property
    def failed_checks(self) -> list[RehearsalCheck]:
        return [check for check in self.checks if not check.passed]

    def _weight(self, severity: str) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(severity, 2)

    @property
    def score(self) -> int:
        if not self.checks:
            return 0
        total_weight = sum(self._weight(check.severity) for check in self.checks)
        if total_weight <= 0:
            return 0
        passed_weight = sum(self._weight(check.severity) for check in self.checks if check.passed)
        return int((passed_weight / total_weight) * 100)

    @property
    def passed(self) -> bool:
        has_critical_failure = any(
            (not check.passed and check.severity == "critical") for check in self.checks
        )
        return self.score >= self.threshold and not has_critical_failure

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "score": self.score,
            "passed": self.passed,
            "threshold": self.threshold,
            "failed_checks": [check.name for check in self.failed_checks],
            "checks": [check.to_dict() for check in self.checks],
            "evidence_identity": dict(self.evidence_identity),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Launch Rehearsal Report",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Score: {self.score}/100",
            f"- Threshold: {self.threshold}",
            f"- Passed: {'yes' if self.passed else 'no'}",
            f"- Failed checks: {len(self.failed_checks)}",
            "",
            "## Checks",
            "",
            "| Check | Result | Severity | Detail |",
            "|:---|:---:|:---:|:---|",
        ]
        for check in self.checks:
            marker = "PASS" if check.passed else "FAIL"
            lines.append(f"| {check.name} | {marker} | {check.severity} | {check.detail} |")
        lines.append("")

        # 治理状态摘要
        governance_check = next((c for c in self.checks if c.name == "Governance Status"), None)
        if governance_check:
            lines.extend(
                [
                    "## Governance Status",
                    "",
                ]
            )
            parts = governance_check.detail.split("; ")
            for part in parts:
                lines.append(f"- {part}")
            lines.append("")

        return "\n".join(lines)


class LaunchRehearsalRunner:
    """执行发布演练检查并输出报告"""

    def __init__(self, project_dir: Path, project_name: str, cicd_platform: str):
        self.project_dir = Path(project_dir).resolve()
        self.project_name = project_name
        self.cicd_platform = cicd_platform or "github"

    def run(self) -> RehearsalResult:
        # 接入效能度量
        metrics_collector = None
        try:
            from ..metrics.pipeline_metrics import PipelineMetricsCollector

            collector = PipelineMetricsCollector(
                metrics_dir=str(self.project_dir / "output" / "metrics-history")
            )
            collector.start_run(self.project_name)
            collector.record_phase_start("rehearsal")
            metrics_collector = collector
        except Exception:
            pass

        result = RehearsalResult(project_name=self.project_name)
        result.checks.extend(
            [
                self._check_redteam_report(),
                self._check_quality_gate_report(),
                self._check_pipeline_metrics(),
                self._check_delivery_manifest(),
                self._check_rehearsal_documents(),
                self._check_migration_files(),
                self._check_cicd_files(),
                self._check_governance_status(),
                # 扩展预检项
                self._check_dns_reachability(),
                self._check_ssl_certificate(),
                self._check_port_conflicts(),
                # 回滚方案验证
                self._check_rollback_readiness(),
                # 容量预估
                self._estimate_capacity(),
            ]
        )

        # 发布风险评分（基于以上所有检查结果）
        result.checks.append(self._calculate_release_risk(result.checks))

        # 记录演练结束度量
        if metrics_collector is not None:
            try:
                metrics_collector.record_phase_end("rehearsal")
                metrics_collector.current_run.quality_gate_score = result.score
                metrics_collector.current_run.quality_gate_passed = result.passed
                metrics_collector.finish_run()
            except Exception:
                pass

        return result

    def write(self, rehearsal_result: RehearsalResult) -> dict[str, Path]:
        output_dir = self.project_dir / "output" / "rehearsal"
        output_dir.mkdir(parents=True, exist_ok=True)
        md_file = output_dir / f"{self.project_name}-rehearsal-report.md"
        json_file = output_dir / f"{self.project_name}-rehearsal-report.json"
        rehearsal_result.evidence_identity = build_evidence_identity(
            self.project_dir,
            artifact_name="rehearsal-report",
            dependencies=[
                self.project_dir / "output" / f"{self.project_name}-quality-gate.json",
                self.project_dir / "output" / f"{self.project_name}-quality-gate.md",
                self.project_dir / "output" / f"{self.project_name}-release-readiness.json",
                self.project_dir / "output" / f"{self.project_name}-proof-pack.json",
                self.project_dir
                / "output"
                / "delivery"
                / f"{self.project_name}-delivery-manifest.json",
            ],
        )
        md_file.write_text(rehearsal_result.to_markdown(), encoding="utf-8")
        json_file.write_text(
            json.dumps(rehearsal_result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_file, "json": json_file}

    def _check_redteam_report(self) -> RehearsalCheck:
        evidence = load_redteam_evidence(self.project_dir, self.project_name)
        if evidence is None:
            return RehearsalCheck(
                "Redteam Report", False, "missing output/*-redteam.{json,md}", severity="critical"
            )
        detail = (
            f"{evidence.path.name}, score={evidence.total_score}/{evidence.pass_threshold}, "
            f"critical={evidence.critical_count}"
        )
        return RehearsalCheck(
            "Redteam Report",
            evidence.passed,
            detail if evidence.passed else "; ".join(evidence.blocking_reasons) or detail,
            severity="critical" if not evidence.passed else "low",
        )

    def _check_quality_gate_report(self) -> RehearsalCheck:
        json_path = self.project_dir / "output" / f"{self.project_name}-quality-gate.json"
        file_path = self.project_dir / "output" / f"{self.project_name}-quality-gate.md"
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            if isinstance(payload, dict) and payload:
                passed = bool(payload.get("passed", False))
                total_score = payload.get("total_score", 0)
                summary_payload = payload.get("summary", {})
                if not isinstance(summary_payload, dict):
                    summary_payload = {}
                executive_summary = str(summary_payload.get("executive_summary", "")).strip()
                detail = f"quality score={total_score}"
                if not passed:
                    detail = f"quality gate report indicates failed; quality score={total_score}"
                if executive_summary:
                    detail = f"{detail}: {executive_summary}"
                governance_state = self._extract_frontend_governance_state(executive_summary)
                if governance_state and not passed:
                    detail = f"{detail}; ui_governance={governance_state}"
                return RehearsalCheck(
                    "Quality Gate",
                    passed,
                    detail,
                    severity="critical" if not passed else "medium",
                )
        if not file_path.exists():
            return RehearsalCheck(
                "Quality Gate", False, "missing output/*-quality-gate.md", severity="critical"
            )

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        executive_summary = self._extract_quality_gate_executive_summary(text)
        if "未通过" in text or "failed" in lowered:
            detail = "quality gate report indicates failed"
            if executive_summary:
                detail = f"{detail}: {executive_summary}"
            governance_state = self._extract_frontend_governance_state(executive_summary)
            if governance_state:
                detail = f"{detail}; ui_governance={governance_state}"
            return RehearsalCheck(
                "Quality Gate", False, detail, severity="critical"
            )

        score_match = re.search(r"(总分|Score)\D+(\d{1,3})/100", text, re.IGNORECASE)
        score = int(score_match.group(2)) if score_match else 0

        passed = False
        if "状态" in text and "通过" in text and "未通过" not in text:
            passed = True
        if "Passed" in text and "Failed" not in text:
            passed = True
        if score_match:
            passed = passed and score >= 80

        detail = f"quality score={score}" if score_match else "quality gate report detected"
        return RehearsalCheck(
            "Quality Gate", passed, detail, severity="critical" if not passed else "medium"
        )

    def _extract_quality_gate_executive_summary(self, text: str) -> str:
        marker = "## 执行摘要"
        if marker not in text:
            return ""
        _, _, remainder = text.partition(marker)
        lines = [line.strip() for line in remainder.splitlines()]
        for line in lines:
            if not line or line.startswith("#") or line == "---":
                continue
            return line
        return ""

    def _extract_frontend_governance_state(self, executive_summary: str) -> str:
        summary = str(executive_summary).strip()
        if not summary:
            return ""
        if "契约冻结" in summary:
            return "contract_freeze_incomplete"
        if "source/runtime 证据漂移" in summary:
            return "source_runtime_drift"
        if "runtime 证明" in summary:
            return "runtime_execution_missing"
        if "源码/预览落地" in summary:
            return "source_execution_missing"
        return ""

    def _check_pipeline_metrics(self) -> RehearsalCheck:
        metrics_file = self.project_dir / "output" / f"{self.project_name}-pipeline-metrics.json"
        if not metrics_file.exists():
            return RehearsalCheck("Pipeline Metrics", False, "missing pipeline metrics json")
        try:
            payload = json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            return RehearsalCheck("Pipeline Metrics", False, "pipeline metrics parse failed")
        success = bool(payload.get("success"))
        score = payload.get("success_rate", 0)
        return RehearsalCheck(
            "Pipeline Metrics",
            success,
            f"success_rate={score}",
            severity="high" if not success else "low",
        )

    def _check_delivery_manifest(self) -> RehearsalCheck:
        delivery_dir = self.project_dir / "output" / "delivery"
        manifest_candidates = sorted(
            delivery_dir.glob(f"{self.project_name}-delivery-manifest.json")
        )
        if not manifest_candidates:
            return RehearsalCheck(
                "Delivery Manifest", False, "missing delivery manifest", severity="critical"
            )
        manifest_file = manifest_candidates[-1]
        try:
            payload = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            return RehearsalCheck(
                "Delivery Manifest", False, "manifest parse failed", severity="high"
            )
        status = str(payload.get("status", "")).lower()
        return RehearsalCheck(
            "Delivery Manifest",
            status == "ready",
            f"status={status or 'unknown'}",
            severity="critical" if status != "ready" else "low",
        )

    def _check_rehearsal_documents(self) -> RehearsalCheck:
        rehearsal_dir = self.project_dir / "output" / "rehearsal"
        required = [
            f"{self.project_name}-launch-rehearsal.md",
            f"{self.project_name}-rollback-playbook.md",
            f"{self.project_name}-smoke-checklist.md",
        ]
        missing = [item for item in required if not (rehearsal_dir / item).exists()]
        if missing:
            return RehearsalCheck(
                "Rehearsal Documents",
                False,
                f"missing: {', '.join(missing)}",
                severity="high",
            )
        return RehearsalCheck(
            "Rehearsal Documents", True, "launch/rollback/smoke docs ready", severity="low"
        )

    def _check_migration_files(self) -> RehearsalCheck:
        backend_migrations = list((self.project_dir / "backend" / "migrations").glob("*.sql"))
        root_migrations = list((self.project_dir / "migrations").glob("*.sql"))
        total = len(backend_migrations) + len(root_migrations)
        return RehearsalCheck(
            "Migration Files",
            total > 0,
            f"{total} migration files",
            severity="high" if total == 0 else "low",
        )

    def _check_cicd_files(self) -> RehearsalCheck:
        cicd_map = {
            "github": [".github/workflows/ci.yml", ".github/workflows/cd.yml"],
            "gitlab": [".gitlab-ci.yml"],
            "jenkins": ["Jenkinsfile"],
            "azure": [".azure-pipelines.yml"],
            "bitbucket": ["bitbucket-pipelines.yml"],
            "all": [
                ".github/workflows/ci.yml",
                ".github/workflows/cd.yml",
                ".gitlab-ci.yml",
                "Jenkinsfile",
                ".azure-pipelines.yml",
                "bitbucket-pipelines.yml",
            ],
        }
        expected = cicd_map.get(self.cicd_platform, cicd_map["github"])
        missing = [item for item in expected if not (self.project_dir / item).exists()]
        if missing:
            return RehearsalCheck(
                "CI/CD Files",
                False,
                f"missing: {', '.join(missing)}",
                severity="high",
            )
        return RehearsalCheck("CI/CD Files", True, f"{len(expected)} files found")

    # ------------------------------------------------------------------
    # 扩展预检项
    # ------------------------------------------------------------------

    def _check_dns_reachability(self, domain: str = "") -> RehearsalCheck:
        """检查目标域名 DNS 可达性。"""
        import socket

        if not domain:
            # 尝试从配置或环境变量推断域名
            env_file = self.project_dir / ".env.production"
            if env_file.exists():
                try:
                    for line in env_file.read_text(encoding="utf-8").splitlines():
                        if line.strip().startswith("DOMAIN="):
                            domain = line.split("=", 1)[1].strip().strip("\"'")
                            break
                except Exception:
                    pass

            if not domain:
                domain = f"{self.project_name}.example.com"

        # 占位域名不做强制检查
        is_placeholder = "example.com" in domain or "localhost" in domain

        try:
            addresses = socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ip_list = list({addr[4][0] for addr in addresses})
            return RehearsalCheck(
                "DNS Reachability",
                True,
                f"{domain} -> {', '.join(ip_list[:3])}",
                severity="low",
            )
        except socket.gaierror:
            severity = "low" if is_placeholder else "high"
            return RehearsalCheck(
                "DNS Reachability",
                is_placeholder,  # 占位域名视为通过
                f"DNS 解析失败: {domain}" + (" (placeholder domain)" if is_placeholder else ""),
                severity=severity,
            )
        except Exception as e:
            return RehearsalCheck(
                "DNS Reachability",
                is_placeholder,
                f"DNS 检查异常: {e}" + (" (placeholder domain)" if is_placeholder else ""),
                severity="low" if is_placeholder else "medium",
            )

    def _check_ssl_certificate(self, domain: str = "", port: int = 443) -> RehearsalCheck:
        """检查目标域名 SSL 证书有效期。"""
        if not domain:
            domain = f"{self.project_name}.example.com"

        is_placeholder = "example.com" in domain or "localhost" in domain

        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    if not cert:
                        return RehearsalCheck(
                            "SSL Certificate",
                            False,
                            f"无法获取 {domain} 的 SSL 证书信息",
                            severity="high",
                        )

                    not_after_str = cert.get("notAfter", "")
                    # 格式: 'Dec 31 23:59:59 2025 GMT'
                    not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                    not_after = not_after.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    days_remaining = (not_after - now).days

                    if days_remaining < 0:
                        return RehearsalCheck(
                            "SSL Certificate",
                            False,
                            f"{domain} SSL 证书已过期 ({not_after_str})",
                            severity="critical",
                        )
                    elif days_remaining < 14:
                        return RehearsalCheck(
                            "SSL Certificate",
                            False,
                            f"{domain} SSL 证书将在 {days_remaining} 天内过期",
                            severity="high",
                        )
                    elif days_remaining < 30:
                        return RehearsalCheck(
                            "SSL Certificate",
                            True,
                            f"{domain} SSL 证书剩余 {days_remaining} 天（建议续期）",
                            severity="medium",
                        )
                    else:
                        return RehearsalCheck(
                            "SSL Certificate",
                            True,
                            f"{domain} SSL 证书有效，剩余 {days_remaining} 天",
                            severity="low",
                        )
        except (TimeoutError, ConnectionRefusedError, OSError):
            return RehearsalCheck(
                "SSL Certificate",
                is_placeholder,  # 占位域名视为通过
                f"无法连接 {domain}:{port}，跳过 SSL 检查"
                + (" (placeholder domain)" if is_placeholder else ""),
                severity="low" if is_placeholder else "medium",
            )
        except Exception as e:
            return RehearsalCheck(
                "SSL Certificate",
                is_placeholder,
                f"SSL 检查异常: {type(e).__name__}: {e}"
                + (" (placeholder domain)" if is_placeholder else ""),
                severity="low" if is_placeholder else "medium",
            )

    def _check_port_conflicts(self) -> RehearsalCheck:
        """检查常用端口是否存在冲突。"""
        import socket

        # 从项目配置和 docker-compose 推断需要的端口
        ports_to_check = [3000, 3001, 5432, 6379, 80, 443, 8080]

        # 尝试从 docker-compose 或 .env 中读取实际端口
        for env_file_name in (".env", ".env.production", ".env.local"):
            env_path = self.project_dir / env_file_name
            if env_path.exists():
                try:
                    for line in env_path.read_text(encoding="utf-8").splitlines():
                        stripped = line.strip()
                        if stripped.startswith("#") or "=" not in stripped:
                            continue
                        key, value = stripped.split("=", 1)
                        if "PORT" in key.upper():
                            try:
                                port_val = int(value.strip().strip("\"'"))
                                if 1 <= port_val <= 65535 and port_val not in ports_to_check:
                                    ports_to_check.append(port_val)
                            except ValueError:
                                pass
                except Exception:
                    pass

        conflicts: list[str] = []
        for port in ports_to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(("127.0.0.1", port))
                    if result == 0:
                        conflicts.append(str(port))
            except Exception:
                pass

        if conflicts:
            return RehearsalCheck(
                "Port Conflicts",
                True,  # 信息性警告，不阻塞发布
                f"端口已被占用: {', '.join(conflicts)} (确保部署环境端口可用)",
                severity="low",
            )
        return RehearsalCheck(
            "Port Conflicts",
            True,
            f"已检查 {len(ports_to_check)} 个端口，无冲突",
            severity="low",
        )

    # ------------------------------------------------------------------
    # 回滚方案验证
    # ------------------------------------------------------------------

    def _check_rollback_readiness(self) -> RehearsalCheck:
        """检查回滚方案是否就绪：回滚脚本、数据库回滚、配置回退。"""
        findings: list[str] = []
        issues: list[str] = []

        # 1. 检查回滚 Playbook
        rollback_playbook = (
            self.project_dir / "output" / "rehearsal" / f"{self.project_name}-rollback-playbook.md"
        )
        if rollback_playbook.exists():
            findings.append("rollback-playbook.md found")
        else:
            issues.append("缺少回滚 Playbook")

        # 2. 检查数据库迁移是否有回滚脚本
        has_db_rollback = False
        migration_dirs = [
            self.project_dir / "prisma" / "migrations",
            self.project_dir / "alembic" / "versions",
            self.project_dir / "backend" / "migrations",
            self.project_dir / "migrations",
        ]
        for mig_dir in migration_dirs:
            if not mig_dir.exists():
                continue
            # Prisma 迁移默认有 down migration
            if "prisma" in str(mig_dir):
                has_db_rollback = True
                findings.append("Prisma migrations detected (auto-rollback support)")
                break
            # Alembic 检查 downgrade 函数
            for py_file in mig_dir.glob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if "def downgrade" in content:
                        has_db_rollback = True
                        findings.append(f"DB downgrade found in {py_file.name}")
                        break
                except Exception:
                    pass
            # SQL 回滚脚本
            for sql_file in mig_dir.glob("*down*.sql"):
                has_db_rollback = True
                findings.append(f"DB rollback SQL: {sql_file.name}")
                break
            for sql_file in mig_dir.glob("*rollback*.sql"):
                has_db_rollback = True
                findings.append(f"DB rollback SQL: {sql_file.name}")
                break

        if not has_db_rollback:
            issues.append("未检测到数据库回滚脚本 (down migration / rollback SQL)")

        # 3. 检查 CI/CD 是否有回滚步骤
        has_cicd_rollback = False
        cicd_files = [
            self.project_dir / ".github" / "workflows" / "cd.yml",
            self.project_dir / ".gitlab-ci.yml",
            self.project_dir / "Jenkinsfile",
        ]
        for cicd_file in cicd_files:
            if not cicd_file.exists():
                continue
            try:
                content = cicd_file.read_text(encoding="utf-8", errors="ignore")
                if re.search(
                    r"rollback|roll-back|revert|undo|previous[_-]?version", content, re.IGNORECASE
                ):
                    has_cicd_rollback = True
                    findings.append(f"CI/CD rollback step in {cicd_file.name}")
                    break
            except Exception:
                pass

        if not has_cicd_rollback:
            issues.append("CI/CD 配置中未检测到回滚步骤")

        # 4. 检查是否有配置回退机制
        has_config_backup = False
        for pattern in ("*.backup", "*.bak", "config.prev.*"):
            if list(self.project_dir.glob(pattern)):
                has_config_backup = True
                break
        # 检查 K8s 配置版本标签
        k8s_dir = self.project_dir / "output" / "deploy" / "kubernetes"
        charts_dir = self.project_dir / "charts"
        if k8s_dir.exists() or charts_dir.exists():
            findings.append("K8s configs detected (Helm/kubectl rollback available)")
            has_config_backup = True

        if not has_config_backup and not has_cicd_rollback:
            issues.append("未检测到配置回退机制")

        # 综合判定
        detail_parts = findings + [f"[ISSUE] {iss}" for iss in issues]
        passed = len(issues) <= 2  # 允许最多 2 个缺失项（早期项目常态）
        severity = "low" if not issues else ("medium" if len(issues) >= 3 else "low")

        return RehearsalCheck(
            "Rollback Readiness",
            passed,
            "; ".join(detail_parts) if detail_parts else "no rollback artifacts found",
            severity=severity,
        )

    # ------------------------------------------------------------------
    # 容量预估
    # ------------------------------------------------------------------

    def _estimate_capacity(self) -> RehearsalCheck:
        """基于代码分析估算资源需求。"""
        estimates: dict[str, str] = {}

        # 1. 代码规模分析
        total_lines = 0
        total_files = 0
        language_lines: dict[str, int] = {}
        ext_to_lang = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".java": "Java",
            ".rs": "Rust",
            ".sql": "SQL",
        }
        skip_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            "dist",
            "build",
            ".venv",
            "venv",
            ".next",
            "output",
            ".super-dev",
        }

        for dirpath, dirnames, filenames in os.walk(self.project_dir):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                lang = ext_to_lang.get(ext)
                if not lang:
                    continue
                file_path = Path(dirpath) / filename
                try:
                    if file_path.stat().st_size > 500_000:
                        continue
                    lines = file_path.read_text(encoding="utf-8", errors="ignore").count("\n")
                    total_lines += lines
                    total_files += 1
                    language_lines[lang] = language_lines.get(lang, 0) + lines
                except Exception:
                    continue

        # 2. 基于规模估算资源
        if total_lines < 5000:
            app_tier = "small"
            cpu_rec = "250m-500m"
            mem_rec = "128Mi-256Mi"
            replicas_rec = "1-2"
        elif total_lines < 30000:
            app_tier = "medium"
            cpu_rec = "500m-1000m"
            mem_rec = "256Mi-512Mi"
            replicas_rec = "2-3"
        elif total_lines < 100000:
            app_tier = "large"
            cpu_rec = "1000m-2000m"
            mem_rec = "512Mi-1Gi"
            replicas_rec = "3-5"
        else:
            app_tier = "enterprise"
            cpu_rec = "2000m-4000m"
            mem_rec = "1Gi-4Gi"
            replicas_rec = "5+"

        estimates["tier"] = app_tier
        estimates["files"] = str(total_files)
        estimates["lines"] = str(total_lines)
        estimates["cpu"] = cpu_rec
        estimates["memory"] = mem_rec
        estimates["replicas"] = replicas_rec

        # 3. 检查是否有数据库（影响资源需求）
        has_db = False
        db_indicators = [
            self.project_dir / "prisma" / "schema.prisma",
            self.project_dir / "alembic.ini",
        ]
        for indicator in db_indicators:
            if indicator.exists():
                has_db = True
                break
        if not has_db:
            # 检查 docker-compose 中的数据库服务
            for compose_file in ("docker-compose.yml", "docker-compose.yaml", "compose.yml"):
                compose_path = self.project_dir / compose_file
                if compose_path.exists():
                    try:
                        content = compose_path.read_text(encoding="utf-8", errors="ignore")
                        if re.search(
                            r"postgres|mysql|mongodb|mariadb|redis", content, re.IGNORECASE
                        ):
                            has_db = True
                            break
                    except Exception:
                        pass

        if has_db:
            estimates["db_memory"] = "256Mi-1Gi (depending on dataset size)"
            estimates["db_storage"] = "10Gi-50Gi (with PVC)"

        # 4. 语言分布
        lang_summary = ", ".join(
            f"{lang}={lines}L"
            for lang, lines in sorted(language_lines.items(), key=lambda x: -x[1])[:5]
        )

        detail = (
            f"tier={app_tier}; {total_files} files/{total_lines} lines; "
            f"cpu={cpu_rec}; memory={mem_rec}; replicas={replicas_rec}"
        )
        if lang_summary:
            detail += f"; langs=[{lang_summary}]"
        if has_db:
            detail += "; db=detected"

        return RehearsalCheck(
            "Capacity Estimation",
            True,  # 信息性检查，总是通过
            detail,
            severity="low",
        )

    # ------------------------------------------------------------------
    # 发布风险评分
    # ------------------------------------------------------------------

    def _calculate_release_risk(self, checks: list[RehearsalCheck]) -> RehearsalCheck:
        """综合各项检查生成发布风险等级。"""
        # 统计各严重度的失败数
        critical_failures = sum(1 for c in checks if not c.passed and c.severity == "critical")
        high_failures = sum(1 for c in checks if not c.passed and c.severity == "high")
        medium_failures = sum(1 for c in checks if not c.passed and c.severity == "medium")
        low_failures = sum(1 for c in checks if not c.passed and c.severity == "low")
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.passed)

        # 风险评分（0-100，越低越好）
        risk_score = 0
        risk_score += critical_failures * 30
        risk_score += high_failures * 15
        risk_score += medium_failures * 5
        risk_score += low_failures * 2
        risk_score = min(100, risk_score)

        # 风险等级
        if risk_score >= 60 or critical_failures > 0:
            risk_level = "CRITICAL"
            recommendation = "禁止发布：存在严重阻塞项，必须修复后重新评估"
        elif risk_score >= 30 or high_failures >= 2:
            risk_level = "HIGH"
            recommendation = "强烈建议推迟发布：修复 high 级别问题后重新评估"
        elif risk_score >= 15 or high_failures >= 1:
            risk_level = "MEDIUM"
            recommendation = "有条件发布：确保回滚方案就绪，建议灰度发布"
        elif risk_score >= 5:
            risk_level = "LOW"
            recommendation = "可以发布：小幅风险，建议监控关键指标"
        else:
            risk_level = "MINIMAL"
            recommendation = "可以发布：风险极低"

        detail = (
            f"risk_level={risk_level}; risk_score={risk_score}/100; "
            f"passed={passed_checks}/{total_checks}; "
            f"critical_fail={critical_failures}; high_fail={high_failures}; "
            f"medium_fail={medium_failures}; recommendation={recommendation}"
        )

        passed = risk_level in ("MINIMAL", "LOW", "MEDIUM")
        severity = (
            "critical"
            if risk_level == "CRITICAL"
            else "high" if risk_level == "HIGH" else "medium" if risk_level == "MEDIUM" else "low"
        )

        return RehearsalCheck(
            "Release Risk Assessment",
            passed,
            detail,
            severity=severity,
        )

    def _check_governance_status(self) -> RehearsalCheck:
        """检查治理状态：治理报告是否存在、验证规则是否全部通过、知识引用覆盖率。"""
        governance_dir = self.project_dir / "output" / "governance"
        report_files: list[Path] = []
        if governance_dir.exists():
            report_files.extend(governance_dir.glob("governance-report-*.md"))
        report_files.extend((self.project_dir / "output").glob("governance-report-*.md"))
        report_files = sorted({path.resolve(): path for path in report_files}.values())
        if not report_files:
            output_dir = self.project_dir / "output"
            pipeline_contracts = sorted(output_dir.glob("*-pipeline-contract.md"))
            metrics_snapshot = output_dir / f"{self.project_name}-pipeline-metrics.json"
            knowledge_cache_dir = output_dir / "knowledge-cache"
            has_live_governance = (
                bool(pipeline_contracts)
                and metrics_snapshot.exists()
                and knowledge_cache_dir.exists()
                and any(knowledge_cache_dir.glob("*-knowledge-bundle.json"))
            )
            if has_live_governance:
                return RehearsalCheck(
                    "Governance Status",
                    True,
                    "report=pending-finalization; validation=IN_PROGRESS; knowledge_coverage=pending-finalization",
                    severity="low",
                )
            return RehearsalCheck(
                "Governance Status",
                False,
                "missing governance report in output/ or output/governance/",
                severity="high",
            )

        latest_report = report_files[-1]
        text = latest_report.read_text(encoding="utf-8", errors="ignore")

        # 检查验证规则是否通过
        validation_passed = True
        if "FAILED" in text and "**状态**: FAILED" in text:
            validation_passed = False

        # 检查知识引用覆盖率
        knowledge_coverage = ""
        coverage_match = re.search(r"命中率[：:]\s*([\d.]+%?)", text)
        if not coverage_match:
            coverage_match = re.search(r"hit_rate[：:]\s*([\d.]+%?)", text, re.IGNORECASE)
        if coverage_match:
            knowledge_coverage = coverage_match.group(1)

        details: list[str] = [f"report={latest_report.name}"]
        if not validation_passed:
            details.append("validation=FAILED")
        else:
            details.append("validation=PASSED")
        if knowledge_coverage:
            details.append(f"knowledge_coverage={knowledge_coverage}")
        else:
            details.append("knowledge_coverage=unknown")

        return RehearsalCheck(
            "Governance Status",
            validation_passed,
            "; ".join(details),
            severity="high" if not validation_passed else "low",
        )
