"""
质量顾问 (Quality Advisor)
从"被动评分"升级为"主动建议"。
不仅告诉用户"质量不达标"，还告诉"具体该补什么、怎么补"。

受 2026 质量工程趋势启发:
- Agentic Quality Intelligence (主动质量Agent)
- Test Impact Analysis (变更影响分析)
- 智能测试建议

开发：Excellent（11964948@qq.com）
功能：主动质量建议引擎
创建时间：2026-03-28
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..compliance_governance import collect_compliance_governance_signal
from ..host_runtime_governance import collect_layered_runtime_governance_gap


@dataclass
class QualityAdvice:
    """单条质量建议"""

    category: str  # testing/security/performance/documentation/architecture
    priority: str  # critical/high/medium/low
    title: str  # 建议标题
    description: str  # 详细描述
    action: str  # 具体行动（可复制执行的命令或步骤）
    effort: str  # 预估工作量: small/medium/large
    impact: str  # 预期影响: high/medium/low
    knowledge_ref: str = ""  # 相关知识文件路径


@dataclass
class QualityAdvisorReport:
    """质量顾问报告"""

    project_name: str
    timestamp: str
    quality_score: int
    advices: list[QualityAdvice] = field(default_factory=list)

    @property
    def critical_advices(self) -> list[QualityAdvice]:
        return [a for a in self.advices if a.priority == "critical"]

    @property
    def quick_wins(self) -> list[QualityAdvice]:
        """高影响+低工作量的建议"""
        return [a for a in self.advices if a.impact == "high" and a.effort == "small"]

    @property
    def high_priority(self) -> list[QualityAdvice]:
        """critical + high 优先级"""
        return [a for a in self.advices if a.priority in {"critical", "high"}]

    @property
    def medium_priority(self) -> list[QualityAdvice]:
        return [a for a in self.advices if a.priority == "medium"]

    @property
    def low_priority(self) -> list[QualityAdvice]:
        return [a for a in self.advices if a.priority == "low"]

    def to_markdown(self) -> str:
        """生成建议报告 Markdown"""
        lines: list[str] = [
            "# 质量顾问报告",
            "",
            f"**项目**: {self.project_name}",
            f"**时间**: {self.timestamp}",
            f"**当前质量分**: {self.quality_score}/100",
            f"**建议总数**: {len(self.advices)}",
            "",
            "---",
            "",
        ]

        if self.quick_wins:
            lines.append("## Quick Wins（高收益低成本）")
            lines.append("")
            for advice in self.quick_wins:
                lines.append(f"- **[{advice.priority.upper()}]** {advice.title}: {advice.action}")
            lines.append("")

        if self.critical_advices:
            lines.append("## 关键问题（必须修复）")
            lines.append("")
            for advice in self.critical_advices:
                lines.append(f"### {advice.title}")
                lines.append("")
                lines.append(f"- **类别**: {advice.category}")
                lines.append(f"- **描述**: {advice.description}")
                lines.append(f"- **行动**: {advice.action}")
                lines.append(f"- **工作量**: {advice.effort}")
                if advice.knowledge_ref:
                    lines.append(f"- **参考**: {advice.knowledge_ref}")
                lines.append("")

        non_critical_high = [a for a in self.high_priority if a.priority == "high"]
        if non_critical_high:
            lines.append("## 高优先级建议")
            lines.append("")
            for advice in non_critical_high:
                lines.append(
                    f"- **{advice.title}** ({advice.category}): "
                    f"{advice.description} → {advice.action} "
                    f"[工作量: {advice.effort}, 影响: {advice.impact}]"
                )
            lines.append("")

        if self.medium_priority:
            lines.append("## 中优先级建议")
            lines.append("")
            for advice in self.medium_priority:
                lines.append(
                    f"- **{advice.title}** ({advice.category}): "
                    f"{advice.description} → {advice.action} "
                    f"[工作量: {advice.effort}, 影响: {advice.impact}]"
                )
            lines.append("")

        if self.low_priority:
            lines.append("## 低优先级建议")
            lines.append("")
            for advice in self.low_priority:
                lines.append(
                    f"- **{advice.title}** ({advice.category}): "
                    f"{advice.description} → {advice.action}"
                )
            lines.append("")

        return "\n".join(lines)


class QualityAdvisor:
    """质量顾问 — 主动质量建议引擎"""

    # 前端源文件扩展名
    _FRONTEND_EXTS = {".tsx", ".jsx", ".vue", ".svelte", ".html"}
    # 前端源目录
    _FRONTEND_DIRS = ("frontend", "src", "app", "client", "pages", "components")
    # 跳过的目录
    _SKIP_DIRS = frozenset(
        {
            "node_modules",
            ".git",
            "dist",
            "build",
            "__pycache__",
            ".next",
            ".nuxt",
            "venv",
            ".venv",
        }
    )

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def analyze(self, quality_result: object = None) -> QualityAdvisorReport:
        """分析项目状态，生成主动建议。

        Args:
            quality_result: 可选的 QualityGateResult 实例，用于获取当前质量分数。
        """
        from datetime import datetime, timezone

        advices: list[QualityAdvice] = []
        advices.extend(self._check_host_runtime_continuity_gaps())
        advices.extend(self._check_compliance_governance_gaps())
        advices.extend(self._check_testing_gaps())
        advices.extend(self._check_security_gaps())
        advices.extend(self._check_documentation_gaps())
        advices.extend(self._check_architecture_gaps())
        advices.extend(self._check_performance_gaps())

        # 按优先级排序: critical > high > medium > low
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        advices.sort(key=lambda a: priority_order.get(a.priority, 99))

        score = 0
        if quality_result is not None:
            score = getattr(quality_result, "total_score", 0)

        return QualityAdvisorReport(
            project_name=self.project_dir.name,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            quality_score=score,
            advices=advices,
        )

    def _check_host_runtime_continuity_gaps(self) -> list[QualityAdvice]:
        """检查已人工通过但仓库级恢复闭环未完成的宿主。"""
        governance_gap = collect_layered_runtime_governance_gap(self.project_dir)
        impacted_hosts = governance_gap.get("impacted_hosts", []) if governance_gap else []
        if not isinstance(impacted_hosts, list) or not impacted_hosts:
            return []
        next_actions = governance_gap.get("next_actions", []) if governance_gap else []
        primary_action = ""
        if isinstance(next_actions, list):
            primary_action = next((str(item).strip() for item in next_actions if str(item).strip()), "")
        if not primary_action:
            primary_action = (
                "先补齐 workflow continuity / framework harness / frontend runtime 闭环，"
                "再补一次宿主真人验收记录。"
            )
        else:
            primary_action = primary_action + "，然后补一次最新的宿主真人验收记录。"

        return [
            QualityAdvice(
                category="governance",
                priority="critical",
                title="宿主 runtime 与仓库 continuity 脱节",
                description=(
                    "以下宿主已人工通过 runtime validation，但仓库级 repo probe 仍未通过："
                    + "、".join(impacted_hosts[:3])
                ),
                action=primary_action,
                effort="small",
                impact="high",
                knowledge_ref=".super-dev/review-state/host-runtime-validation.json",
            )
        ]

    def _check_compliance_governance_gaps(self) -> list[QualityAdvice]:
        signal = collect_compliance_governance_signal(self.project_dir)
        source_issues = signal.get("source_issues", [])
        if isinstance(source_issues, list) and source_issues:
            return [
                QualityAdvice(
                    category="governance",
                    priority="critical",
                    title="合规链证据状态未闭环",
                    description=str(signal.get("summary", "")).strip()
                    or "spec / architecture / uiux compliance artifacts 仍缺失或失配。",
                    action=(
                        "先重新生成 spec / architecture / uiux compliance artifacts，"
                        "确认 JSON 证据存在、可读且 identity 指向当前输入，然后重跑 quality gate。"
                    ),
                    effort="small",
                    impact="high",
                    knowledge_ref="output/",
                )
            ]
        content_issues = signal.get("content_issues", [])
        if isinstance(content_issues, list) and content_issues:
            return [
                QualityAdvice(
                    category="governance",
                    priority="high",
                    title="合规链内容仍未达标",
                    description=str(signal.get("summary", "")).strip()
                    or "合规链证据已齐，但仍有内容检查未通过。",
                    action=(
                        "优先修复 PRD traceability、architecture drift 或 UIUX 违例，"
                        "再重新执行 quality gate / proof-pack / release readiness。"
                    ),
                    effort="medium",
                    impact="high",
                    knowledge_ref="output/",
                )
            ]
        return []

    # ------------------------------------------------------------------
    # 测试缺口检查
    # ------------------------------------------------------------------

    def _check_testing_gaps(self) -> list[QualityAdvice]:
        """检查测试覆盖缺口"""
        advices: list[QualityAdvice] = []

        # 1. 检查是否有测试目录
        test_dirs = ["tests", "test", "spec", "__tests__"]
        has_test_dir = any((self.project_dir / d).exists() for d in test_dirs)
        # backend 子目录也算
        has_test_dir = has_test_dir or any(
            (self.project_dir / "backend" / d).exists() for d in test_dirs
        )

        if not has_test_dir:
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="critical",
                    title="缺少测试目录",
                    description="项目中没有找到任何测试目录（tests/, test/, spec/, __tests__/）",
                    action="mkdir -p tests/unit tests/integration && touch tests/__init__.py tests/conftest.py",
                    effort="small",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/pytest-complete.md",
                )
            )
            return advices  # 没有测试目录，后续检查意义不大

        # 2. 测试文件数量与源码比例
        source_count = self._count_source_files()
        test_count = self._count_test_files()
        if source_count > 0 and test_count == 0:
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="critical",
                    title="零测试覆盖",
                    description=f"发现 {source_count} 个源文件但 0 个测试文件",
                    action="为核心模块创建单元测试，优先覆盖公共 API 和业务逻辑入口",
                    effort="large",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/pytest-complete.md",
                )
            )
        elif source_count > 0 and test_count / source_count < 0.3:
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="high",
                    title="测试覆盖率偏低",
                    description=(
                        f"测试文件/源文件比例为 {test_count}/{source_count} "
                        f"({test_count / source_count:.0%})，建议至少达到 30%"
                    ),
                    action="识别未覆盖的核心模块，逐个补充单元测试",
                    effort="medium",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/pytest-complete.md",
                )
            )

        # 3. 集成测试
        has_integration = any(
            (self.project_dir / d / "integration").exists()
            for d in test_dirs
            if (self.project_dir / d).exists()
        )
        if not has_integration:
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="medium",
                    title="缺少集成测试",
                    description="未检测到 tests/integration/ 目录",
                    action="mkdir -p tests/integration && 创建跨模块集成测试用例",
                    effort="medium",
                    impact="medium",
                    knowledge_ref="knowledge/development/01-standards/pytest-complete.md",
                )
            )

        # 4. E2E 测试配置
        e2e_markers = [
            "playwright.config",
            "cypress.config",
            "cypress.json",
            "playwright.config.ts",
            "playwright.config.js",
        ]
        has_e2e = any((self.project_dir / m).exists() for m in e2e_markers)
        if not has_e2e and self._has_frontend():
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="medium",
                    title="缺少 E2E 测试",
                    description="前端项目未配置 Playwright 或 Cypress E2E 测试",
                    action="npx playwright init  # 或 npx cypress open",
                    effort="medium",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/playwright-complete.md",
                )
            )

        # 5. 性能测试
        perf_markers = ["locustfile.py", "k6", "artillery.yml", "artillery.yaml", "loadtest"]
        has_perf_test = any((self.project_dir / m).exists() for m in perf_markers)
        if not has_perf_test and source_count > 20:
            advices.append(
                QualityAdvice(
                    category="testing",
                    priority="low",
                    title="缺少性能测试",
                    description="中大型项目建议配置性能/负载测试",
                    action="pip install locust && touch locustfile.py  # 或使用 k6/artillery",
                    effort="medium",
                    impact="medium",
                    knowledge_ref="knowledge/development/01-standards/performance-optimization-complete.md",
                )
            )

        return advices

    # ------------------------------------------------------------------
    # 安全缺口检查
    # ------------------------------------------------------------------

    def _check_security_gaps(self) -> list[QualityAdvice]:
        """检查安全缺口"""
        advices: list[QualityAdvice] = []

        # 1. .env 文件泄露检查
        env_file = self.project_dir / ".env"
        env_example = self.project_dir / ".env.example"
        gitignore = self.project_dir / ".gitignore"
        if env_file.exists():
            env_in_gitignore = False
            if gitignore.exists():
                gi_content = gitignore.read_text(encoding="utf-8", errors="ignore")
                env_in_gitignore = ".env" in gi_content
            if not env_in_gitignore:
                advices.append(
                    QualityAdvice(
                        category="security",
                        priority="critical",
                        title=".env 文件可能被提交",
                        description=".env 文件存在但未在 .gitignore 中排除，可能泄露密钥",
                        action="echo '.env' >> .gitignore && git rm --cached .env 2>/dev/null; true",
                        effort="small",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/web-security-complete.md",
                    )
                )
        if not env_example.exists() and env_file.exists():
            advices.append(
                QualityAdvice(
                    category="security",
                    priority="high",
                    title="缺少 .env.example",
                    description="有 .env 文件但缺少 .env.example，新开发者无法知道需要哪些环境变量",
                    action="cp .env .env.example && 编辑 .env.example 移除所有真实密钥值",
                    effort="small",
                    impact="medium",
                    knowledge_ref="knowledge/development/01-standards/web-security-complete.md",
                )
            )

        # 2. 依赖漏洞扫描配置
        has_audit_config = any(
            (self.project_dir / f).exists()
            for f in [".github/workflows/ci.yml", ".github/workflows/security.yml"]
        )
        if not has_audit_config:
            advices.append(
                QualityAdvice(
                    category="security",
                    priority="high",
                    title="缺少自动依赖审计",
                    description="CI 流水线中未检测到依赖安全扫描步骤",
                    action="在 CI 中添加: pip-audit (Python) 或 npm audit (Node.js)",
                    effort="small",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/web-security-complete.md",
                )
            )

        # 3. CORS/CSP 配置
        if self._has_frontend():
            has_csp = self._search_in_sources(
                r"Content-Security-Policy|helmet|csp",
                dirs=["backend", "server", "api", "src"],
                exts={".py", ".js", ".ts"},
            )
            if not has_csp:
                advices.append(
                    QualityAdvice(
                        category="security",
                        priority="medium",
                        title="缺少 CSP/安全头配置",
                        description="未检测到 Content-Security-Policy 或 helmet 中间件",
                        action="安装并配置 helmet (Node) 或添加 CSP 响应头中间件 (Python)",
                        effort="small",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/web-security-complete.md",
                    )
                )

        # 4. 认证中间件
        has_backend = any((self.project_dir / d).exists() for d in ["backend", "server", "api"])
        if has_backend:
            has_auth = self._search_in_sources(
                r"(?:jwt|auth|Bearer|passport|oauth|session)",
                dirs=["backend", "server", "api", "src"],
                exts={".py", ".js", ".ts"},
            )
            if not has_auth:
                advices.append(
                    QualityAdvice(
                        category="security",
                        priority="high",
                        title="缺少认证机制",
                        description="后端代码中未检测到 JWT/OAuth/Session 认证逻辑",
                        action="集成认证中间件（如 PyJWT, passport.js, next-auth）",
                        effort="medium",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/oauth2-complete.md",
                    )
                )

        # 5. 输入验证
        if has_backend:
            has_validation = self._search_in_sources(
                r"(?:pydantic|marshmallow|joi|zod|class-validator|cerberus|jsonschema)",
                dirs=["backend", "server", "api", "src"],
                exts={".py", ".js", ".ts"},
            )
            if not has_validation:
                advices.append(
                    QualityAdvice(
                        category="security",
                        priority="medium",
                        title="缺少输入验证框架",
                        description="未检测到结构化输入验证库（pydantic/joi/zod 等）",
                        action="集成输入验证库（Python: pydantic; Node: zod/joi）",
                        effort="small",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/rest-api-complete.md",
                    )
                )

        return advices

    # ------------------------------------------------------------------
    # 文档缺口检查
    # ------------------------------------------------------------------

    def _check_documentation_gaps(self) -> list[QualityAdvice]:
        """检查文档缺口"""
        advices: list[QualityAdvice] = []

        # 1. README 质量
        readme = self._find_readme()
        if readme is None:
            advices.append(
                QualityAdvice(
                    category="documentation",
                    priority="high",
                    title="缺少 README",
                    description="项目根目录没有 README.md",
                    action="创建 README.md，包含项目简介、安装步骤、使用方法、配置说明",
                    effort="small",
                    impact="high",
                )
            )
        else:
            content = readme.read_text(encoding="utf-8", errors="ignore").lower()
            missing_sections: list[str] = []
            if not re.search(r"(install|安装|setup|getting started)", content):
                missing_sections.append("安装说明")
            if not re.search(r"(usage|使用|quick\s*start|快速开始)", content):
                missing_sections.append("使用方法")
            if not re.search(r"(config|配置|environment|环境变量)", content):
                missing_sections.append("配置说明")
            if missing_sections:
                advices.append(
                    QualityAdvice(
                        category="documentation",
                        priority="medium",
                        title="README 内容不完整",
                        description=f"README 缺少以下章节: {', '.join(missing_sections)}",
                        action=f"在 README.md 中补充: {', '.join(missing_sections)}",
                        effort="small",
                        impact="medium",
                    )
                )

        # 2. API 文档
        has_api = any((self.project_dir / d).exists() for d in ["backend", "server", "api"])
        if has_api:
            has_api_docs = any(
                (self.project_dir / f).exists()
                for f in [
                    "openapi.yaml",
                    "openapi.json",
                    "swagger.yaml",
                    "swagger.json",
                    "docs/api.md",
                    "backend/API_CONTRACT.md",
                ]
            )
            has_auto_docs = self._search_in_sources(
                r"(?:swagger|openapi|FastAPI|@ApiProperty|@nestjs/swagger)",
                dirs=["backend", "server", "api", "src"],
                exts={".py", ".js", ".ts"},
            )
            if not has_api_docs and not has_auto_docs:
                advices.append(
                    QualityAdvice(
                        category="documentation",
                        priority="high",
                        title="缺少 API 文档",
                        description="后端 API 缺少 OpenAPI/Swagger 文档",
                        action="创建 openapi.yaml 或集成自动文档生成（FastAPI 自带, Express 用 swagger-jsdoc）",
                        effort="medium",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/rest-api-complete.md",
                    )
                )

        # 3. CHANGELOG
        changelog_names = ["CHANGELOG.md", "CHANGELOG", "HISTORY.md", "CHANGES.md"]
        has_changelog = any((self.project_dir / f).exists() for f in changelog_names)
        if not has_changelog:
            advices.append(
                QualityAdvice(
                    category="documentation",
                    priority="low",
                    title="缺少 CHANGELOG",
                    description="项目没有变更日志文件",
                    action="touch CHANGELOG.md && 按 Keep a Changelog 格式维护版本变更记录",
                    effort="small",
                    impact="medium",
                )
            )

        # 4. 贡献指南
        contrib_names = ["CONTRIBUTING.md", "CONTRIBUTING", ".github/CONTRIBUTING.md"]
        has_contrib = any((self.project_dir / f).exists() for f in contrib_names)
        source_count = self._count_source_files()
        if not has_contrib and source_count > 10:
            advices.append(
                QualityAdvice(
                    category="documentation",
                    priority="low",
                    title="缺少贡献指南",
                    description="中大型项目建议提供 CONTRIBUTING.md",
                    action="创建 CONTRIBUTING.md，包含开发环境搭建、代码规范、PR 流程",
                    effort="small",
                    impact="low",
                )
            )

        return advices

    # ------------------------------------------------------------------
    # 架构缺口检查
    # ------------------------------------------------------------------

    def _check_architecture_gaps(self) -> list[QualityAdvice]:
        """检查架构缺口"""
        advices: list[QualityAdvice] = []

        # 1. ADR (Architecture Decision Records)
        adr_dirs = ["docs/adr", "docs/decisions", "adr", "ADR"]
        has_adr = any((self.project_dir / d).exists() for d in adr_dirs)
        source_count = self._count_source_files()
        if not has_adr and source_count > 20:
            advices.append(
                QualityAdvice(
                    category="architecture",
                    priority="medium",
                    title="缺少架构决策记录 (ADR)",
                    description="中大型项目建议维护 ADR 记录关键架构决策",
                    action="mkdir -p docs/adr && 创建 ADR 模板（编号-标题-状态-上下文-决策-后果）",
                    effort="small",
                    impact="medium",
                )
            )

        # 2. Docker 配置
        docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
        has_docker = any((self.project_dir / f).exists() for f in docker_files)
        if not has_docker and source_count > 5:
            advices.append(
                QualityAdvice(
                    category="architecture",
                    priority="medium",
                    title="缺少容器化配置",
                    description="项目没有 Dockerfile 或 docker-compose 配置",
                    action="创建 Dockerfile（多阶段构建）和 docker-compose.yml",
                    effort="medium",
                    impact="medium",
                )
            )

        # 3. CI/CD 配置
        ci_files = [
            ".github/workflows",
            ".gitlab-ci.yml",
            "Jenkinsfile",
            ".circleci/config.yml",
            "azure-pipelines.yml",
            "bitbucket-pipelines.yml",
        ]
        has_ci = any((self.project_dir / f).exists() for f in ci_files)
        if not has_ci:
            advices.append(
                QualityAdvice(
                    category="architecture",
                    priority="high",
                    title="缺少 CI/CD 配置",
                    description="未检测到任何 CI/CD 流水线配置",
                    action="补齐当前仓库的 CI/CD 配置（例如 .github/workflows/ci.yml）",
                    effort="medium",
                    impact="high",
                )
            )

        # 4. 环境变量管理
        has_env_management = any(
            (self.project_dir / f).exists()
            for f in [".env.example", ".env.template", "env.sample", ".envrc"]
        )
        has_env = (self.project_dir / ".env").exists()
        if has_env and not has_env_management:
            advices.append(
                QualityAdvice(
                    category="architecture",
                    priority="high",
                    title="环境变量管理不规范",
                    description="有 .env 文件但缺少 .env.example 模板",
                    action="cp .env .env.example && 编辑移除真实密钥值，只保留变量名和说明注释",
                    effort="small",
                    impact="medium",
                )
            )

        return advices

    # ------------------------------------------------------------------
    # 性能缺口检查
    # ------------------------------------------------------------------

    def _check_performance_gaps(self) -> list[QualityAdvice]:
        """检查性能缺口"""
        advices: list[QualityAdvice] = []

        has_backend = any((self.project_dir / d).exists() for d in ["backend", "server", "api"])
        if not has_backend:
            return advices

        # 1. 缓存配置
        has_cache = self._search_in_sources(
            r"(?:redis|memcache|cache|lru_cache|@cache|cachetools)",
            dirs=["backend", "server", "api", "src", "super_dev"],
            exts={".py", ".js", ".ts"},
        )
        if not has_cache:
            advices.append(
                QualityAdvice(
                    category="performance",
                    priority="medium",
                    title="缺少缓存策略",
                    description="后端代码中未检测到缓存配置（Redis/Memcache/LRU）",
                    action="集成缓存层（Redis 推荐），为高频查询添加缓存",
                    effort="medium",
                    impact="high",
                    knowledge_ref="knowledge/development/01-standards/redis-complete.md",
                )
            )

        # 2. 数据库索引
        has_db = self._search_in_sources(
            r"(?:CREATE\s+TABLE|db\.create|models?\.|Schema|@Entity|prisma)",
            dirs=["backend", "server", "api", "src"],
            exts={".py", ".js", ".ts", ".sql", ".prisma"},
        )
        if has_db:
            has_index = self._search_in_sources(
                r"(?:CREATE\s+INDEX|index\s*=\s*True|@Index|@@index|db_index)",
                dirs=["backend", "server", "api", "src"],
                exts={".py", ".js", ".ts", ".sql", ".prisma"},
            )
            if not has_index:
                advices.append(
                    QualityAdvice(
                        category="performance",
                        priority="medium",
                        title="缺少数据库索引",
                        description="检测到数据库模型但未发现显式索引定义",
                        action="为常用查询字段和外键添加数据库索引",
                        effort="small",
                        impact="high",
                        knowledge_ref="knowledge/development/01-standards/postgresql-complete.md",
                    )
                )

        # 3. 连接池配置
        has_pool = self._search_in_sources(
            r"(?:pool_size|connection_pool|max_connections|pool|createPool)",
            dirs=["backend", "server", "api", "src"],
            exts={".py", ".js", ".ts"},
        )
        if has_db and not has_pool:
            advices.append(
                QualityAdvice(
                    category="performance",
                    priority="low",
                    title="缺少连接池配置",
                    description="数据库连接未检测到显式连接池配置",
                    action="配置数据库连接池（pool_size, max_overflow 等参数）",
                    effort="small",
                    impact="medium",
                    knowledge_ref="knowledge/development/01-standards/postgresql-complete.md",
                )
            )

        return advices

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _has_frontend(self) -> bool:
        """检查项目是否包含前端代码"""
        return any((self.project_dir / d).exists() for d in self._FRONTEND_DIRS[:4])

    def _find_readme(self) -> Path | None:
        """查找 README 文件"""
        for name in ["README.md", "readme.md", "README", "README.rst"]:
            path = self.project_dir / name
            if path.exists():
                return path
        return None

    def _count_source_files(self) -> int:
        """统计源代码文件数量（Python + JS/TS）"""
        count = 0
        source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"}
        source_dirs = [
            "super_dev",
            "src",
            "app",
            "backend",
            "server",
            "api",
            "frontend",
            "client",
            "lib",
            "services",
        ]
        for dir_name in source_dirs:
            src_dir = self.project_dir / dir_name
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*"):
                if f.suffix in source_exts and not any(s in f.parts for s in self._SKIP_DIRS):
                    count += 1
                    if count >= 500:  # 上限防止大项目扫描过久
                        return count
        return count

    def _count_test_files(self) -> int:
        """统计测试文件数量"""
        count = 0
        test_dirs = ["tests", "test", "spec", "__tests__"]
        all_dirs = [self.project_dir / d for d in test_dirs]
        all_dirs.extend([self.project_dir / "backend" / d for d in test_dirs])
        for d in all_dirs:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.suffix in {".py", ".js", ".ts"} and not any(
                    s in f.parts for s in self._SKIP_DIRS
                ):
                    count += 1
                    if count >= 500:
                        return count
        return count

    def _search_in_sources(
        self,
        pattern: str,
        dirs: list[str],
        exts: set[str],
        max_files: int = 200,
    ) -> bool:
        """在指定目录中搜索正则匹配，找到即返回 True"""
        compiled = re.compile(pattern, re.IGNORECASE)
        scanned = 0
        for dir_name in dirs:
            src_dir = self.project_dir / dir_name
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*"):
                if f.suffix not in exts:
                    continue
                if any(s in f.parts for s in self._SKIP_DIRS):
                    continue
                scanned += 1
                if scanned > max_files:
                    return False
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if compiled.search(content):
                        return True
                except OSError:
                    continue
        return False
