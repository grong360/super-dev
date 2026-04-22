"""
Spec-Code 一致性检测器

开发：Excellent（11964948@qq.com）
功能：检测代码实现是否偏离 Spec 描述，防止 spec-code 漂移
作用：确保 spec 和实际代码保持同步，防止 spec-code 漂移
创建时间：2026-03-28
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import yaml  # type: ignore[import-untyped]


@dataclass
class ConsistencyIssue:
    """一致性问题"""

    severity: str  # critical/high/medium/low
    category: str  # missing_implementation/extra_code/api_mismatch/config_drift
    spec_reference: str  # spec 中的描述
    actual_state: str  # 实际代码状态
    suggestion: str  # 修复建议

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "spec_reference": self.spec_reference,
            "actual_state": self.actual_state,
            "suggestion": self.suggestion,
        }


@dataclass
class ConsistencyReport:
    """一致性检测报告"""

    change_id: str
    timestamp: str
    issues: list[ConsistencyIssue] = field(default_factory=list)
    consistency_score: int = 100  # 0-100

    @property
    def passed(self) -> bool:
        return not any(i.severity == "critical" for i in self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "low")

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        lines: list[str] = []
        lines.append(f"# Spec-Code 一致性报告: {self.change_id}")
        lines.append("")
        lines.append(f"> 生成时间: {self.timestamp}")
        lines.append(f"> 一致性分数: {self.consistency_score}/100")
        status_text = "通过" if self.passed else "未通过 (存在 critical 问题)"
        lines.append(f"> 状态: {status_text}")
        lines.append("")

        # 总览
        lines.append("## 问题总览")
        lines.append("")
        lines.append("| 严重程度 | 数量 |")
        lines.append("|----------|------|")
        lines.append(f"| Critical | {self.critical_count} |")
        lines.append(f"| High | {self.high_count} |")
        lines.append(f"| Medium | {self.medium_count} |")
        lines.append(f"| Low | {self.low_count} |")
        lines.append("")

        if not self.issues:
            lines.append("没有发现一致性问题。Spec 与代码完全同步。")
            lines.append("")
            return "\n".join(lines)

        # 按类别分组
        categories: dict[str, list[ConsistencyIssue]] = {}
        for issue in self.issues:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)

        category_labels = {
            "missing_implementation": "缺失实现",
            "api_mismatch": "API 不匹配",
            "config_drift": "配置漂移",
            "task_drift": "任务漂移",
            "dependency_drift": "依赖漂移",
        }

        for category, issues in categories.items():
            label = category_labels.get(category, category)
            lines.append(f"## {label}")
            lines.append("")
            lines.append("| 严重程度 | Spec 描述 | 实际状态 | 建议 |")
            lines.append("|----------|-----------|----------|------|")
            for issue in issues:
                lines.append(
                    f"| {issue.severity} | {issue.spec_reference} "
                    f"| {issue.actual_state} | {issue.suggestion} |"
                )
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp,
            "consistency_score": self.consistency_score,
            "passed": self.passed,
            "issue_count": len(self.issues),
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "low": self.low_count,
            "issues": [i.to_dict() for i in self.issues],
        }


# -- 路由提取正则 --

# FastAPI: @app.get("/path"), @router.post("/path") 等
_FASTAPI_ROUTE_PATTERN = re.compile(
    r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# Express: app.get("/path", ...), router.post("/path", ...)
_EXPRESS_ROUTE_PATTERN = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# Flask: @app.route("/path", methods=["GET"])
_FLASK_ROUTE_PATTERN = re.compile(
    r"@(?:app|blueprint|bp)\.(route)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

# Spec 中的 API 端点模式: GET /api/users, POST /api/auth/login
_SPEC_API_PATTERN = re.compile(
    r"(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9/_\-{}:]+)",
    re.IGNORECASE,
)

# tasks.md 中已完成的任务
_TASK_COMPLETED_PATTERN = re.compile(r"^-\s*\[x\]\s*(.+)$", re.IGNORECASE)
_TASK_PENDING_PATTERN = re.compile(r"^-\s*\[ \]\s*(.+)$")


class SpecConsistencyChecker:
    """Spec-Code 一致性检测器"""

    # 严重程度对应的分数扣减
    _SEVERITY_PENALTY = {
        "critical": 20,
        "high": 10,
        "medium": 5,
        "low": 2,
    }

    def __init__(self, project_dir: Path | str):
        self.project_dir = Path(project_dir).resolve()
        self.changes_dir = self.project_dir / ".super-dev" / "changes"

    def check(self, change_id: str) -> ConsistencyReport:
        """执行一致性检测"""
        issues: list[ConsistencyIssue] = []
        issues.extend(self._check_api_consistency(change_id))
        issues.extend(self._check_config_consistency())
        issues.extend(self._check_dependency_consistency())
        issues.extend(self._check_task_completion(change_id))
        score = self._calculate_score(issues)
        return ConsistencyReport(
            change_id=change_id,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            issues=issues,
            consistency_score=score,
        )

    def _check_api_consistency(self, change_id: str) -> list[ConsistencyIssue]:
        """检查 API 一致性: spec 中声明的端点 vs 代码中实际的路由"""
        issues: list[ConsistencyIssue] = []

        # 1. 从 spec/proposal 中提取 API 端点描述
        spec_endpoints = self._extract_spec_endpoints(change_id)
        if not spec_endpoints:
            return issues

        # 2. 扫描实际代码中的路由定义
        code_endpoints = self._extract_code_endpoints()

        # 3. 比较: spec 中有但代码中没有 = missing_implementation
        code_paths = {path.lower() for _, path in code_endpoints}
        for method, path in spec_endpoints:
            # 将 path 参数 {id} 规范化为匹配
            normalized = re.sub(r"\{[^}]+\}", "*", path.lower())
            found = False
            for cp in code_paths:
                cp_normalized = re.sub(r"\{[^}]+\}", "*", cp)
                cp_normalized = re.sub(r":[a-zA-Z_]+", "*", cp_normalized)
                if cp_normalized == normalized or cp == path.lower():
                    found = True
                    break
            if not found:
                issues.append(
                    ConsistencyIssue(
                        severity="high",
                        category="api_mismatch",
                        spec_reference=f"Spec 声明 {method.upper()} {path}",
                        actual_state="代码中未找到对应路由",
                        suggestion=f"实现 {method.upper()} {path} 端点或更新 spec 移除该端点",
                    )
                )

        return issues

    def _check_config_consistency(self) -> list[ConsistencyIssue]:
        """检查配置一致性: super-dev.yaml 声明的技术栈 vs 实际项目"""
        issues: list[ConsistencyIssue] = []

        config_path = self.project_dir / "super-dev.yaml"
        if not config_path.exists():
            return issues

        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return issues

        # 检查 frontend 配置
        frontend_cfg = config.get("frontend", {})
        if isinstance(frontend_cfg, dict):
            framework = frontend_cfg.get("framework", "")
            if framework:
                # 检查 package.json 中是否有该框架
                pkg_json = self.project_dir / "package.json"
                frontend_pkg = self.project_dir / "frontend" / "package.json"
                found_framework = False
                for pj in [pkg_json, frontend_pkg]:
                    if pj.exists():
                        try:
                            content = pj.read_text(encoding="utf-8").lower()
                            # 框架名称映射
                            framework_packages = {
                                "react": ["react"],
                                "vue": ["vue"],
                                "angular": ["@angular/core"],
                                "svelte": ["svelte"],
                                "next": ["next"],
                                "nuxt": ["nuxt"],
                                "vite-react": ["react", "vite"],
                            }
                            packages = framework_packages.get(
                                framework.lower(), [framework.lower()]
                            )
                            if all(pkg in content for pkg in packages):
                                found_framework = True
                                break
                        except Exception:
                            continue

                if not found_framework:
                    # 检查是否有 frontend 目录或 package.json
                    has_frontend_dir = (self.project_dir / "frontend").is_dir()
                    has_any_pkg = pkg_json.exists() or frontend_pkg.exists()
                    if has_frontend_dir or has_any_pkg:
                        issues.append(
                            ConsistencyIssue(
                                severity="medium",
                                category="config_drift",
                                spec_reference=(f"super-dev.yaml 声明前端框架: {framework}"),
                                actual_state="package.json 中未找到对应框架依赖",
                                suggestion=(f"安装 {framework} 依赖或更新 super-dev.yaml 配置"),
                            )
                        )

        # 检查 backend 配置
        backend_cfg = config.get("backend", {})
        if isinstance(backend_cfg, dict):
            framework = backend_cfg.get("framework", "")
            if framework:
                backend_packages = {
                    "express": ("package.json", "express"),
                    "fastapi": ("pyproject.toml", "fastapi"),
                    "flask": ("pyproject.toml", "flask"),
                    "django": ("pyproject.toml", "django"),
                    "gin": ("go.mod", "gin"),
                    "nest": ("package.json", "@nestjs/core"),
                    "spring": ("pom.xml", "spring"),
                }
                check_file, check_pkg = backend_packages.get(
                    framework.lower(), ("", framework.lower())
                )
                if check_file:
                    target = self.project_dir / check_file
                    backend_target = self.project_dir / "backend" / check_file
                    found = False
                    for tf in [target, backend_target]:
                        if tf.exists():
                            try:
                                content = tf.read_text(encoding="utf-8").lower()
                                if check_pkg.lower() in content:
                                    found = True
                                    break
                            except Exception:
                                continue
                    if not found and (target.exists() or backend_target.exists()):
                        issues.append(
                            ConsistencyIssue(
                                severity="medium",
                                category="config_drift",
                                spec_reference=(f"super-dev.yaml 声明后端框架: {framework}"),
                                actual_state=f"{check_file} 中未找到 {check_pkg}",
                                suggestion=(f"安装 {framework} 依赖或更新 super-dev.yaml 配置"),
                            )
                        )

        # 检查 database 配置
        db_cfg = config.get("database", {})
        if isinstance(db_cfg, dict):
            db_type = str(db_cfg.get("type", "")).strip()
            if db_type:
                # 检查是否有对应的 docker-compose 或环境配置
                compose_files = [
                    self.project_dir / "docker-compose.yml",
                    self.project_dir / "docker-compose.yaml",
                ]
                found_db = False
                for cf in compose_files:
                    if cf.exists():
                        try:
                            content = cf.read_text(encoding="utf-8").lower()
                            db_images = {
                                "postgresql": ["postgres"],
                                "postgres": ["postgres"],
                                "mysql": ["mysql", "mariadb"],
                                "mongodb": ["mongo"],
                                "redis": ["redis"],
                                "sqlite": [],  # SQLite 不需要容器
                            }
                            images = cast(list[str], db_images.get(db_type.lower(), [db_type.lower()]))
                            if not images or any(img in content for img in images):
                                found_db = True
                                break
                        except Exception:
                            continue

                if not found_db and db_type.lower() != "sqlite":
                    # 只在有 docker-compose 文件时检查
                    if any(cf.exists() for cf in compose_files):
                        issues.append(
                            ConsistencyIssue(
                                severity="low",
                                category="config_drift",
                                spec_reference=(f"super-dev.yaml 声明数据库: {db_type}"),
                                actual_state="docker-compose 中未找到对应数据库服务",
                                suggestion=(
                                    f"在 docker-compose 中添加 {db_type} 服务"
                                    " 或更新 super-dev.yaml"
                                ),
                            )
                        )

        return issues

    def _check_dependency_consistency(self) -> list[ConsistencyIssue]:
        """检查依赖一致性: architecture.md 中提到的技术 vs 实际依赖"""
        issues: list[ConsistencyIssue] = []

        # 查找 architecture 文档
        arch_files = (
            list((self.project_dir / "output").glob("*-architecture.md"))
            if (self.project_dir / "output").exists()
            else []
        )
        if not arch_files:
            return issues

        arch_file = max(arch_files, key=lambda p: p.stat().st_mtime)
        try:
            arch_content = arch_file.read_text(encoding="utf-8")
        except Exception:
            return issues

        # 提取架构文档中明确提到的技术栈/库（在 "技术栈" 或 "dependencies" 段落中）
        tech_mentions = self._extract_tech_mentions(arch_content)
        if not tech_mentions:
            return issues

        # 收集实际依赖
        actual_deps = self._collect_actual_dependencies()
        if not actual_deps:
            return issues

        # 检查架构文档中提到但实际未安装的技术
        for tech, context in tech_mentions:
            tech_lower = str(tech).lower()
            # 模糊匹配: 允许别名
            aliases = {
                "postgresql": {"pg", "postgres", "postgresql", "psycopg2"},
                "express": {"express"},
                "react": {"react"},
                "vue": {"vue"},
                "redis": {"redis", "ioredis"},
                "prisma": {"prisma", "@prisma/client"},
                "sequelize": {"sequelize"},
                "typeorm": {"typeorm"},
                "jest": {"jest"},
                "pytest": {"pytest"},
                "docker": set(),  # Docker 不是代码依赖
                "nginx": set(),  # Nginx 不是代码依赖
                "kubernetes": set(),  # K8s 不是代码依赖
            }
            # 跳过基础设施工具（不是代码依赖）
            infra_tools = {"docker", "nginx", "kubernetes", "k8s", "helm", "terraform"}
            if tech_lower in infra_tools:
                continue

            check_names = cast(set[str], aliases.get(tech_lower, {tech_lower}))
            if not check_names:
                continue

            found = any(name in actual_deps for name in check_names)
            if not found:
                issues.append(
                    ConsistencyIssue(
                        severity="medium",
                        category="dependency_drift",
                        spec_reference=f"架构文档提及 {tech} ({context})",
                        actual_state="项目依赖中未找到该库",
                        suggestion=f"安装 {tech} 或从架构文档中移除该依赖描述",
                    )
                )

        return issues

    def _check_task_completion(self, change_id: str) -> list[ConsistencyIssue]:
        """检查任务完成一致性: 标记为完成的任务是否有对应代码"""
        issues: list[ConsistencyIssue] = []

        change_dir = self.changes_dir / change_id
        tasks_file = change_dir / "tasks.md"
        if not tasks_file.exists():
            return issues

        try:
            content = tasks_file.read_text(encoding="utf-8")
        except Exception:
            return issues

        # 收集项目中的源码文件
        source_files = self._collect_source_files()
        file_contents: dict[str, str] = {}
        for fp in source_files:
            try:
                rel = str(fp.relative_to(self.project_dir))
                file_contents[rel] = fp.read_text(encoding="utf-8").lower()
            except (OSError, UnicodeDecodeError):
                continue

        # 解析已完成的任务
        for line in content.splitlines():
            match = _TASK_COMPLETED_PATTERN.match(line.strip())
            if not match:
                continue
            task_text = match.group(1).strip()

            # 从任务文本中提取关键词
            keywords = self._extract_keywords(task_text)
            if len(keywords) < 2:
                continue

            # 检查是否有对应代码
            found_code = False
            for _rel_path, file_content in file_contents.items():
                hits = sum(1 for kw in keywords if kw in file_content)
                if hits >= max(2, len(keywords) // 3):
                    found_code = True
                    break

            if not found_code:
                issues.append(
                    ConsistencyIssue(
                        severity="high",
                        category="task_drift",
                        spec_reference=f"任务标记完成: {task_text[:80]}",
                        actual_state="未找到对应的代码实现",
                        suggestion="确认任务是否真的完成，或补充实现代码",
                    )
                )

        return issues

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _extract_spec_endpoints(self, change_id: str) -> list[tuple[str, str]]:
        """从 spec/proposal 中提取 API 端点 (method, path)"""
        endpoints: list[tuple[str, str]] = []
        change_dir = self.changes_dir / change_id
        if not change_dir.exists():
            return endpoints

        # 搜索 proposal.md 和 specs/**/*.md
        md_files: list[Path] = []
        proposal = change_dir / "proposal.md"
        if proposal.exists():
            md_files.append(proposal)
        specs_dir = change_dir / "specs"
        if specs_dir.exists():
            md_files.extend(specs_dir.rglob("*.md"))

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue
            for match in _SPEC_API_PATTERN.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                if (method, path) not in endpoints:
                    endpoints.append((method, path))

        return endpoints

    def _extract_code_endpoints(self) -> list[tuple[str, str]]:
        """从项目代码中提取实际路由定义 (method, path)"""
        endpoints: list[tuple[str, str]] = []
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}
        exclude_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            ".ruff_cache",
        }

        for item in self.project_dir.rglob("*"):
            if not item.is_file() or item.suffix not in extensions:
                continue
            parts = item.relative_to(self.project_dir).parts
            if any(p in exclude_dirs for p in parts):
                continue
            # 跳过测试文件
            if item.name.startswith("test_") or item.name.endswith("_test.py"):
                continue

            try:
                content = item.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            for pattern in [_FASTAPI_ROUTE_PATTERN, _EXPRESS_ROUTE_PATTERN, _FLASK_ROUTE_PATTERN]:
                for match in pattern.finditer(content):
                    method = match.group(1).upper()
                    if method == "ROUTE":
                        method = "GET"  # Flask @app.route default
                    path = match.group(2)
                    if (method, path) not in endpoints:
                        endpoints.append((method, path))

        return endpoints

    def _extract_tech_mentions(self, arch_content: str) -> list[tuple[str, str]]:
        """从架构文档中提取技术栈提及"""
        mentions: list[tuple[str, str]] = []
        # 在"技术栈"或"Technology"相关段落中查找
        in_tech_section = False
        section_context = ""

        for line in arch_content.splitlines():
            stripped = line.strip()
            # 检测技术栈段落
            if re.match(
                r"^#{1,3}\s+.*(技术栈|技术选型|Technology|Tech Stack|Dependencies"
                r"|依赖|框架|Framework)",
                stripped,
                re.IGNORECASE,
            ):
                in_tech_section = True
                section_context = stripped
                continue
            # 新段落开始时退出
            if re.match(r"^#{1,3}\s+", stripped) and in_tech_section:
                in_tech_section = False
                continue

            if in_tech_section and stripped:
                # 提取列表项中的技术名称
                list_match = re.match(
                    r"^[-*]\s+\**([A-Za-z][A-Za-z0-9._/-]+)\**",
                    stripped,
                )
                if list_match:
                    tech = list_match.group(1).strip()
                    if len(tech) > 1 and not tech.startswith("http"):
                        mentions.append((tech, section_context))

        return mentions

    def _collect_actual_dependencies(self) -> set[str]:
        """收集项目中实际安装的依赖名称"""
        deps: set[str] = set()

        # package.json
        for pkg_path in [
            self.project_dir / "package.json",
            self.project_dir / "frontend" / "package.json",
            self.project_dir / "backend" / "package.json",
        ]:
            if pkg_path.exists():
                try:
                    import json

                    data = json.loads(pkg_path.read_text(encoding="utf-8"))
                    for key in ["dependencies", "devDependencies", "peerDependencies"]:
                        if isinstance(data.get(key), dict):
                            deps.update(k.lower() for k in data[key])
                except Exception:
                    continue

        # pyproject.toml
        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                # 简单提取 dependencies 列表中的包名
                for match in re.finditer(
                    r'^\s*"?([a-zA-Z][a-zA-Z0-9_-]+)',
                    content,
                    re.MULTILINE,
                ):
                    deps.add(match.group(1).lower())
            except Exception:
                pass

        # requirements.txt
        req_txt = self.project_dir / "requirements.txt"
        if req_txt.exists():
            try:
                for line in req_txt.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pkg_name = re.split(r"[>=<!\[]", line)[0].strip()
                        if pkg_name:
                            deps.add(pkg_name.lower())
            except Exception:
                pass

        return deps

    def _collect_source_files(self) -> list[Path]:
        """收集项目中的源码文件"""
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
        exclude_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            ".ruff_cache",
        }
        results: list[Path] = []
        for item in self.project_dir.rglob("*"):
            if not item.is_file() or item.suffix not in extensions:
                continue
            parts = item.relative_to(self.project_dir).parts
            if any(p in exclude_dirs for p in parts):
                continue
            if item.name.startswith("test_") or item.name.endswith("_test.py"):
                continue
            results.append(item)
        return sorted(results)

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """从文本中提取搜索关键词"""
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "must",
            "can",
            "need",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "and",
            "or",
            "but",
            "not",
            "no",
            "all",
            "any",
            "each",
            "every",
            "that",
            "this",
            "it",
            "its",
            "their",
            "them",
            "they",
            "he",
            "she",
            "we",
            "you",
            "able",
            "when",
            "if",
            "then",
            "than",
            "also",
            "just",
            "only",
            "both",
            "add",
            "create",
            "update",
            "delete",
            "implement",
            "setup",
            "configure",
            "build",
            "make",
            "use",
            "set",
            "get",
        }
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
        return [w for w in words if w not in stop_words]

    def _calculate_score(self, issues: list[ConsistencyIssue]) -> int:
        """根据问题严重程度计算一致性分数"""
        score = 100
        for issue in issues:
            penalty = self._SEVERITY_PENALTY.get(issue.severity, 2)
            score -= penalty
        return max(0, score)
