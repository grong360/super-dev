"""
开发：Excellent（11964948@qq.com）
功能：配置管理器 - 管理项目配置
作用：读取、验证、持久化 super-dev.yaml 配置
创建时间：2025-12-30
最后修改：2025-12-30
"""

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from super_dev.catalogs import (
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PLATFORM_IDS,
)


@dataclass
class ProjectConfig:
    """项目配置"""

    name: str
    description: str = ""
    version: str = "2.4.0"
    author: str = ""
    license: str = "MIT"

    # 技术栈
    platform: str = "web"  # web, mobile(H5/APP), wechat(miniapp), desktop
    frontend: str = (
        "next"  # 扩展支持：next, remix, react-vite, gatsby, nuxt, vue-vite, angular, sveltekit, astro, solid, qwik
    )
    backend: str = (
        "node"  # node, python, go, java, rust, php, ruby, csharp, kotlin, swift, elixir, scala, dart
    )
    database: str = "postgresql"  # postgresql, mysql, mongodb, redis

    # 前端配置 (扩展)
    ui_library: str | None = None  # UI 组件库
    style_solution: str | None = None  # 样式方案
    state_management: list[str] = field(default_factory=list)  # 状态管理
    testing_frameworks: list[str] = field(default_factory=list)  # 测试框架
    design_inspiration_slug: str = ""  # 显式设计灵感锚点

    # 领域知识
    domain: str = ""  # fintech, ecommerce, medical, social, iot, education
    language_preferences: list[str] = field(default_factory=list)  # 语言偏好（用于文档/实现建议）
    knowledge_allowed_domains: list[str] = field(default_factory=list)  # 联网知识白名单域名
    knowledge_cache_ttl_seconds: int = 1800  # 知识缓存 TTL（秒）

    # 工作流配置
    phases: list[str] = field(
        default_factory=lambda: [
            "discovery",
            "intelligence",
            "drafting",
            "redteam",
            "qa",
            "delivery",
            "deployment",
        ]
    )

    # 专家配置
    experts: list[str] = field(
        default_factory=lambda: ["PM", "ARCHITECT", "UI", "UX", "SECURITY", "CODE"]
    )

    # 质量门禁
    quality_gate: int = 80
    host_compatibility_min_score: int = 80
    host_compatibility_min_ready_hosts: int = 1
    host_profile_targets: list[str] = field(
        default_factory=list
    )  # 目标宿主画像（用于质量门禁和运营看板）
    host_profile_enforce_selected: bool = False  # 仅按 host_profile_targets 计算宿主兼容性

    # Plan-Execute 与 Overseer 配置
    execution_mode: str = "standard"  # standard | plan-execute
    overseer_enabled: bool = False  # 启用 Overseer 质量监督
    codex_review_enabled: bool = False  # 启用 Codex 独立审查（Claude-Codex 混合模式）
    codex_review_phases: list[str] = field(
        default_factory=lambda: ["drafting", "redteam", "qa"]
    )  # 哪些阶段触发 Codex 审查
    overseer_halt_on_critical: bool = True  # Overseer 发现 Critical 偏差时暂停流水线
    plan_failure_budget: int = 3  # Plan-Execute 步骤默认失败预算

    # 输出目录
    output_dir: str = "output"

    # CLI 设置
    cli: dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """配置管理器"""

    CONFIG_FILENAME = "super-dev.yaml"
    DEFAULT_CONFIG: dict[str, Any] = {
        "name": "my-project",
        "description": "A Super Dev project",
        "version": "2.4.0",
        "platform": "web",
        "frontend": "next",  # 默认使用 Next.js
        "backend": "node",
        "database": "postgresql",
        "domain": "",
        "language_preferences": [],
        "knowledge_allowed_domains": [],
        "knowledge_cache_ttl_seconds": 1800,
        "phases": [
            "discovery",
            "intelligence",
            "drafting",
            "redteam",
            "qa",
            "delivery",
            "deployment",
        ],
        "experts": ["PM", "ARCHITECT", "UI", "UX", "SECURITY", "CODE"],
        "quality_gate": 80,
        "host_compatibility_min_score": 80,
        "host_compatibility_min_ready_hosts": 1,
        "host_profile_targets": [],
        "host_profile_enforce_selected": False,
        "execution_mode": "standard",
        "overseer_enabled": False,
        "codex_review_enabled": False,
        "codex_review_phases": ["drafting", "redteam", "qa"],
        "overseer_halt_on_critical": True,
        "plan_failure_budget": 3,
        "output_dir": "output",
        # 前端配置
        "ui_library": None,
        "style_solution": None,
        "state_management": [],
        "testing_frameworks": [],
        "design_inspiration_slug": "",
    }

    def __init__(self, project_dir: Path | None = None):
        """
        初始化配置管理器

        Args:
            project_dir: 项目目录，默认为当前目录
        """
        self.project_dir = Path.cwd() if project_dir is None else project_dir
        self.config_path = self.project_dir / self.CONFIG_FILENAME
        self._config: ProjectConfig | None = None

    @property
    def config(self) -> ProjectConfig:
        """获取配置（延迟加载）"""
        if self._config is None:
            self._config = self.load()
        return self._config

    def exists(self) -> bool:
        """检查配置文件是否存在"""
        return self.config_path.exists()

    def load(self) -> ProjectConfig:
        """
        加载配置文件

        Returns:
            ProjectConfig: 项目配置对象
        """
        if not self.exists():
            # 返回默认配置
            return ProjectConfig(**cast(dict[str, Any], self.DEFAULT_CONFIG.copy()))

        with open(self.config_path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        data = loaded if isinstance(loaded, dict) else {}

        # 合并默认配置
        config_data: dict[str, Any] = {**self.DEFAULT_CONFIG, **data}

        # Validate merged config (warnings only, not blocking)
        try:
            from .schema_validator import validate_config

            schema_errors = validate_config(config_data)
            if schema_errors:
                import logging

                logging.getLogger("super_dev.config").warning(
                    "Config schema validation warnings: %s",
                    "; ".join(schema_errors),
                )
        except Exception:
            pass

        # 过滤掉 ProjectConfig 不支持的字段，避免 TypeError
        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        config_data = {k: v for k, v in config_data.items() if k in valid_fields}

        return ProjectConfig(**cast(dict[str, Any], config_data))

    def save(self, config: ProjectConfig | None = None) -> None:
        """
        保存配置文件

        Args:
            config: 要保存的配置，默认使用当前配置
        """
        config_to_save = config or self._config
        if config_to_save is None:
            raise ValueError("No config to save")

        # 转换为字典（排除 None 值）
        data = {
            k: v
            for k, v in config_to_save.__dict__.items()
            if v is not None and not k.startswith("_")
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._config = config_to_save

    def create(self, **kwargs: Any) -> ProjectConfig:
        """
        创建新配置

        Args:
            **kwargs: 配置参数

        Returns:
            ProjectConfig: 新创建的配置对象
        """
        config_data: dict[str, Any] = {**self.DEFAULT_CONFIG, **kwargs}
        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        config_data = {k: v for k, v in config_data.items() if k in valid_fields}
        candidate = ProjectConfig(**cast(dict[str, Any], config_data))
        errors = self._collect_validation_errors(candidate)
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
        self._config = candidate
        self.save()
        return candidate

    def update(self, **kwargs: Any) -> ProjectConfig:
        """
        更新配置

        Args:
            **kwargs: 要更新的配置参数

        Returns:
            ProjectConfig: 更新后的配置对象
        """
        if not self.exists():
            return self.create(**kwargs)

        # 类型转换映射
        type_converters: dict[str, type[int]] = {
            "quality_gate": int,  # 质量门禁必须是整数
            "knowledge_cache_ttl_seconds": int,
            "host_compatibility_min_score": int,
            "host_compatibility_min_ready_hosts": int,
            "plan_failure_budget": int,
        }

        # 转换类型
        converted_kwargs: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key == "knowledge_allowed_domains" and isinstance(value, str):
                converted_kwargs[key] = [item.strip() for item in value.split(",") if item.strip()]
                continue
            if key == "language_preferences" and isinstance(value, str):
                converted_kwargs[key] = [item.strip() for item in value.split(",") if item.strip()]
                continue
            if key == "host_profile_targets" and isinstance(value, str):
                converted_kwargs[key] = [item.strip() for item in value.split(",") if item.strip()]
                continue
            if key == "host_profile_enforce_selected" and isinstance(value, str):
                lowered = value.strip().lower()
                converted_kwargs[key] = lowered in {"1", "true", "yes", "y", "on"}
                continue
            if key == "overseer_enabled" and isinstance(value, str):
                lowered = value.strip().lower()
                converted_kwargs[key] = lowered in {"1", "true", "yes", "y", "on"}
                continue
            if key == "codex_review_enabled" and isinstance(value, str):
                lowered = value.strip().lower()
                converted_kwargs[key] = lowered in {"1", "true", "yes", "y", "on"}
                continue
            if key == "overseer_halt_on_critical" and isinstance(value, str):
                lowered = value.strip().lower()
                converted_kwargs[key] = lowered in {"1", "true", "yes", "y", "on"}
                continue
            if key == "codex_review_phases" and isinstance(value, str):
                converted_kwargs[key] = [item.strip() for item in value.split(",") if item.strip()]
                continue
            if key in type_converters and isinstance(value, str):
                try:
                    converted_kwargs[key] = type_converters[key](value)
                except (ValueError, TypeError):
                    converted_kwargs[key] = value
            else:
                converted_kwargs[key] = value

        # 合并现有配置
        current_data: dict[str, Any] = dict(self.config.__dict__)
        updated_data: dict[str, Any] = {**current_data, **converted_kwargs}
        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        updated_data = {k: v for k, v in updated_data.items() if k in valid_fields}

        candidate = ProjectConfig(**cast(dict[str, Any], updated_data))
        errors = self._collect_validation_errors(candidate)
        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
        self._config = candidate
        self.save()
        return candidate

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键（支持点号分隔的嵌套键）
            default: 默认值

        Returns:
            配置值
        """
        value = self.config
        for part in key.split("."):
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default
        return value

    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置

        Returns:
            (是否有效, 错误列表)
        """
        errors = self._collect_validation_errors(self.config)
        return len(errors) == 0, errors

    def _collect_validation_errors(self, config: ProjectConfig) -> list[str]:
        """收集配置错误列表"""
        errors: list[str] = []

        # 验证必需字段
        if not config.name:
            errors.append("项目名称不能为空")

        # 验证平台
        valid_platforms = list(PLATFORM_IDS)
        if config.platform not in valid_platforms:
            errors.append(f"平台必须是: {', '.join(valid_platforms)}")

        # 验证前端框架
        valid_frontends = list(FULL_FRONTEND_TEMPLATE_IDS)
        if config.frontend not in valid_frontends:
            errors.append(f"前端框架必须是: {', '.join(valid_frontends)}")

        # 验证后端框架
        valid_backends = list(PIPELINE_BACKEND_IDS)
        if config.backend not in valid_backends:
            errors.append(f"后端框架必须是: {', '.join(valid_backends)}")

        # 验证质量门禁
        if not 0 <= config.quality_gate <= 100:
            errors.append("质量门禁必须在 0-100 之间")
        if not 0 <= config.host_compatibility_min_score <= 100:
            errors.append("host_compatibility_min_score 必须在 0-100 之间")
        if config.host_compatibility_min_ready_hosts < 0:
            errors.append("host_compatibility_min_ready_hosts 不能小于 0")
        if not isinstance(config.host_profile_enforce_selected, bool):
            errors.append("host_profile_enforce_selected 必须是布尔值")
        if not isinstance(config.host_profile_targets, list):
            errors.append("host_profile_targets 必须是字符串列表")
        else:
            invalid_targets = [
                item
                for item in config.host_profile_targets
                if not isinstance(item, str) or not item.strip()
            ]
            if invalid_targets:
                errors.append("host_profile_targets 包含非法项")
            unsupported_targets = [
                item
                for item in config.host_profile_targets
                if isinstance(item, str) and item.strip() and item not in HOST_TOOL_IDS
            ]
            if unsupported_targets:
                errors.append(
                    "host_profile_targets 包含不支持的宿主: "
                    + ", ".join(sorted(set(unsupported_targets)))
                )

        # 验证执行模式
        valid_execution_modes = ("standard", "plan-execute")
        if config.execution_mode not in valid_execution_modes:
            errors.append(f"execution_mode 必须是: {', '.join(valid_execution_modes)}")
        if config.plan_failure_budget < 1:
            errors.append("plan_failure_budget 不能小于 1")

        # 验证知识增强配置
        if config.knowledge_cache_ttl_seconds < 0:
            errors.append("knowledge_cache_ttl_seconds 不能小于 0")
        if not isinstance(config.language_preferences, list):
            errors.append("language_preferences 必须是字符串列表")
        else:
            invalid_language_items = [
                item
                for item in config.language_preferences
                if not isinstance(item, str) or not item.strip()
            ]
            if invalid_language_items:
                errors.append("language_preferences 包含非法项")
        if not isinstance(config.knowledge_allowed_domains, list):
            errors.append("knowledge_allowed_domains 必须是字符串列表")
        else:
            invalid_items = [
                item
                for item in config.knowledge_allowed_domains
                if not isinstance(item, str) or not item.strip()
            ]
            if invalid_items:
                errors.append("knowledge_allowed_domains 包含非法项")

        return errors

    # ------------------------------------------------------------------
    # Configuration Schema Validation (Deep)
    # ------------------------------------------------------------------

    CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
        "name": {"type": "str", "required": True, "min_length": 1, "max_length": 128},
        "description": {"type": "str", "required": False, "max_length": 1024},
        "version": {"type": "str", "required": False, "pattern": r"^\d+\.\d+\.\d+"},
        "platform": {"type": "str", "required": True, "allowed": list(PLATFORM_IDS)},
        "frontend": {"type": "str", "required": True, "allowed": list(FULL_FRONTEND_TEMPLATE_IDS)},
        "backend": {"type": "str", "required": True, "allowed": list(PIPELINE_BACKEND_IDS)},
        "database": {
            "type": "str",
            "required": False,
            "allowed": ["postgresql", "mysql", "mongodb", "redis", "sqlite", ""],
        },
        "quality_gate": {"type": "int", "required": False, "min": 0, "max": 100},
        "execution_mode": {
            "type": "str",
            "required": False,
            "allowed": ["standard", "plan-execute"],
        },
        "plan_failure_budget": {"type": "int", "required": False, "min": 1, "max": 10},
        "host_compatibility_min_score": {"type": "int", "required": False, "min": 0, "max": 100},
        "host_compatibility_min_ready_hosts": {"type": "int", "required": False, "min": 0},
        "knowledge_cache_ttl_seconds": {"type": "int", "required": False, "min": 0},
        "output_dir": {"type": "str", "required": False},
    }

    def validate_schema(
        self, data: dict[str, Any] | None = None
    ) -> tuple[bool, list[dict[str, str]]]:
        """
        对配置进行深度 schema 校验。

        Args:
            data: 要校验的配置字典。若为 None 则使用当前已加载的配置。

        Returns:
            (是否通过, 问题列表)，每个问题包含 field/severity/message
        """
        import re

        if data is None:
            data = self.config.__dict__.copy()

        issues: list[dict[str, str]] = []

        for field_name, rules in self.CONFIG_SCHEMA.items():
            value = data.get(field_name)
            field_type = rules.get("type", "str")

            # Required check
            if rules.get("required") and (
                value is None or (isinstance(value, str) and not value.strip())
            ):
                issues.append(
                    {
                        "field": field_name,
                        "severity": "error",
                        "message": f"必填字段 '{field_name}' 未设置或为空",
                    }
                )
                continue

            if value is None:
                continue

            # Type check
            if field_type == "str" and not isinstance(value, str):
                issues.append(
                    {
                        "field": field_name,
                        "severity": "error",
                        "message": f"'{field_name}' 应为字符串，实际为 {type(value).__name__}",
                    }
                )
                continue
            if field_type == "int" and not isinstance(value, int):
                issues.append(
                    {
                        "field": field_name,
                        "severity": "error",
                        "message": f"'{field_name}' 应为整数，实际为 {type(value).__name__}",
                    }
                )
                continue

            # String constraints
            if isinstance(value, str):
                min_len = rules.get("min_length")
                max_len = rules.get("max_length")
                if min_len is not None and len(value) < min_len:
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "error",
                            "message": f"'{field_name}' 长度不能少于 {min_len} 个字符",
                        }
                    )
                if max_len is not None and len(value) > max_len:
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "warning",
                            "message": f"'{field_name}' 长度超过推荐的 {max_len} 个字符",
                        }
                    )
                pattern = rules.get("pattern")
                if pattern and not re.match(pattern, value):
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "error",
                            "message": f"'{field_name}' 格式不符合要求（期望: {pattern}）",
                        }
                    )
                allowed = rules.get("allowed")
                if allowed and value and value not in allowed:
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "error",
                            "message": f"'{field_name}' 值 '{value}' 不在允许的列表中",
                        }
                    )

            # Integer constraints
            if isinstance(value, int):
                min_val = rules.get("min")
                max_val = rules.get("max")
                if min_val is not None and value < min_val:
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "error",
                            "message": f"'{field_name}' 值 {value} 小于最小值 {min_val}",
                        }
                    )
                if max_val is not None and value > max_val:
                    issues.append(
                        {
                            "field": field_name,
                            "severity": "error",
                            "message": f"'{field_name}' 值 {value} 大于最大值 {max_val}",
                        }
                    )

        # Check for unknown fields
        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        for key in data:
            if key not in valid_fields and not key.startswith("_"):
                issues.append(
                    {
                        "field": key,
                        "severity": "warning",
                        "message": f"未知配置字段 '{key}'，可能已废弃或拼写错误",
                    }
                )

        has_errors = any(i["severity"] == "error" for i in issues)
        return not has_errors, issues

    # ------------------------------------------------------------------
    # Configuration Migration
    # ------------------------------------------------------------------

    CONFIG_MIGRATIONS: list[dict[str, Any]] = [
        {
            "from_version": "1.0",
            "to_version": "2.0",
            "description": "从 v1.0 迁移到 v2.0：新增 host 兼容性配置",
            "transforms": {
                "host_compatibility_min_score": lambda data: data.get(
                    "host_compatibility_min_score", 80
                ),
                "host_compatibility_min_ready_hosts": lambda data: data.get(
                    "host_compatibility_min_ready_hosts", 1
                ),
                "host_profile_targets": lambda data: data.get("host_profile_targets", []),
                "host_profile_enforce_selected": lambda data: data.get(
                    "host_profile_enforce_selected", False
                ),
            },
            "removals": [],
        },
        {
            "from_version": "2.0",
            "to_version": "2.1",
            "description": "从 v2.0 迁移到 v2.1：新增知识增强和前端扩展配置",
            "transforms": {
                "language_preferences": lambda data: data.get("language_preferences", []),
                "knowledge_allowed_domains": lambda data: data.get("knowledge_allowed_domains", []),
                "knowledge_cache_ttl_seconds": lambda data: data.get(
                    "knowledge_cache_ttl_seconds", 1800
                ),
                "ui_library": lambda data: data.get("ui_library"),
                "style_solution": lambda data: data.get("style_solution"),
                "state_management": lambda data: data.get("state_management", []),
                "testing_frameworks": lambda data: data.get("testing_frameworks", []),
            },
            "removals": [],
        },
        {
            "from_version": "2.1",
            "to_version": "2.2",
            "description": "从 v2.1 迁移到 v2.2：标准化版本号",
            "transforms": {},
            "removals": ["deprecated_field"],
        },
        {
            "from_version": "2.2",
            "to_version": "2.3",
            "description": "从 v2.2 迁移到 v2.3：新增 Plan-Execute、Overseer 和 Claude-Codex 混合模式配置",
            "transforms": {
                "execution_mode": lambda data: data.get("execution_mode", "standard"),
                "overseer_enabled": lambda data: data.get("overseer_enabled", False),
                "codex_review_enabled": lambda data: data.get("codex_review_enabled", False),
                "codex_review_phases": lambda data: data.get(
                    "codex_review_phases", ["drafting", "redteam", "qa"]
                ),
                "overseer_halt_on_critical": lambda data: data.get(
                    "overseer_halt_on_critical", True
                ),
                "plan_failure_budget": lambda data: data.get("plan_failure_budget", 3),
            },
            "removals": [],
        },
    ]

    def migrate_config(self, target_version: str = "2.4.0") -> tuple[bool, list[str]]:
        """
        将配置文件从当前版本迁移到目标版本。

        Args:
            target_version: 目标版本号

        Returns:
            (是否需要迁移, 迁移日志)
        """
        if not self.exists():
            return False, ["配置文件不存在，无需迁移"]

        with open(self.config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        current_version = str(raw.get("version", "1.0.0"))
        current_major_minor = ".".join(current_version.split(".")[:2])
        target_major_minor = ".".join(target_version.split(".")[:2])

        if current_major_minor == target_major_minor:
            return False, [f"配置已是目标版本 {target_version}，无需迁移"]

        logs: list[str] = []
        migrated_data = dict(raw)
        applied = False

        for migration in self.CONFIG_MIGRATIONS:
            from_v = migration["from_version"]
            to_v = migration["to_version"]

            if current_major_minor <= from_v and to_v <= target_major_minor:
                logs.append(f"应用迁移: {migration['description']}")

                # Apply transforms
                for field_name, transform_fn in migration.get("transforms", {}).items():
                    if field_name not in migrated_data:
                        migrated_data[field_name] = transform_fn(migrated_data)
                        logs.append(f"  + 添加字段 '{field_name}'")

                # Apply removals
                for removal in migration.get("removals", []):
                    if removal in migrated_data:
                        del migrated_data[removal]
                        logs.append(f"  - 移除已废弃字段 '{removal}'")

                applied = True

        if applied:
            migrated_data["version"] = target_version
            logs.append(f"版本号更新为 {target_version}")

            # Backup original
            backup_path = self.config_path.with_suffix(".yaml.bak")
            import shutil

            shutil.copy2(self.config_path, backup_path)
            logs.append(f"原配置已备份到 {backup_path}")

            # Save migrated config
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(migrated_data, f, allow_unicode=True, default_flow_style=False)
            logs.append("迁移完成并保存")

            # Reload
            self._config = None

        return applied, logs

    # ------------------------------------------------------------------
    # Configuration Template Generation
    # ------------------------------------------------------------------

    PROJECT_TYPE_TEMPLATES: dict[str, dict[str, Any]] = {
        "saas-web": {
            "description": "SaaS Web 应用推荐配置",
            "config": {
                "platform": "web",
                "frontend": "next",
                "backend": "node",
                "database": "postgresql",
                "quality_gate": 85,
                "domain": "saas",
                "ui_library": "shadcn/ui",
                "style_solution": "tailwindcss",
                "state_management": ["zustand"],
                "testing_frameworks": ["vitest", "playwright"],
            },
        },
        "ecommerce": {
            "description": "电商平台推荐配置",
            "config": {
                "platform": "web",
                "frontend": "next",
                "backend": "node",
                "database": "postgresql",
                "quality_gate": 90,
                "domain": "ecommerce",
                "ui_library": "shadcn/ui",
                "style_solution": "tailwindcss",
                "state_management": ["zustand", "tanstack-query"],
                "testing_frameworks": ["vitest", "playwright", "cypress"],
            },
        },
        "dashboard": {
            "description": "后台管理系统推荐配置",
            "config": {
                "platform": "web",
                "frontend": "react-vite",
                "backend": "python",
                "database": "postgresql",
                "quality_gate": 80,
                "domain": "dashboard",
                "ui_library": "ant-design",
                "style_solution": "css-modules",
                "state_management": ["zustand"],
                "testing_frameworks": ["vitest"],
            },
        },
        "mobile-app": {
            "description": "移动端 APP 推荐配置",
            "config": {
                "platform": "mobile",
                "frontend": "react-vite",
                "backend": "node",
                "database": "postgresql",
                "quality_gate": 85,
                "domain": "mobile",
                "testing_frameworks": ["jest"],
            },
        },
        "miniapp-wechat": {
            "description": "微信小程序推荐配置",
            "config": {
                "platform": "wechat",
                "frontend": "react-vite",
                "backend": "node",
                "database": "mysql",
                "quality_gate": 80,
                "domain": "miniapp",
            },
        },
        "api-service": {
            "description": "纯后端 API 服务推荐配置",
            "config": {
                "platform": "web",
                "frontend": "react-vite",
                "backend": "python",
                "database": "postgresql",
                "quality_gate": 90,
                "testing_frameworks": ["pytest"],
            },
        },
    }

    def generate_template(self, project_type: str, name: str = "") -> ProjectConfig:
        """
        根据项目类型生成推荐配置。

        Args:
            project_type: 项目类型（saas-web, ecommerce, dashboard, mobile-app 等）
            name: 项目名称

        Returns:
            生成的 ProjectConfig 对象
        """
        template = self.PROJECT_TYPE_TEMPLATES.get(project_type)
        if not template:
            available = ", ".join(sorted(self.PROJECT_TYPE_TEMPLATES.keys()))
            raise ValueError(f"未知的项目类型 '{project_type}'，可用类型: {available}")

        config_data: dict[str, Any] = {**self.DEFAULT_CONFIG, **template["config"]}
        if name:
            config_data["name"] = name

        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        config_data = {k: v for k, v in config_data.items() if k in valid_fields}

        return ProjectConfig(**cast(dict[str, Any], config_data))

    @classmethod
    def list_templates(cls) -> list[dict[str, str]]:
        """列出所有可用的项目类型模板"""
        return [
            {"type": key, "description": val["description"]}
            for key, val in cls.PROJECT_TYPE_TEMPLATES.items()
        ]

    # ------------------------------------------------------------------
    # Multi-Environment Configuration
    # ------------------------------------------------------------------

    ENVIRONMENT_OVERRIDES: dict[str, dict[str, Any]] = {
        "development": {
            "quality_gate": 70,
            "description_suffix": " (Development)",
        },
        "staging": {
            "quality_gate": 85,
            "description_suffix": " (Staging)",
        },
        "production": {
            "quality_gate": 95,
            "description_suffix": " (Production)",
        },
    }

    def load_environment_config(self, environment: str) -> ProjectConfig:
        """
        加载特定环境的配置（合并基础配置 + 环境覆盖文件）。

        优先级: 环境文件 > 基础配置 > 默认值

        Args:
            environment: 环境名（development/staging/production）

        Returns:
            合并后的 ProjectConfig
        """
        base_config = self.load()

        # Try to load environment-specific file
        env_file = self.project_dir / f"super-dev.{environment}.yaml"
        env_overrides: dict[str, Any] = {}
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            env_overrides = loaded if isinstance(loaded, dict) else {}

        # Apply built-in environment defaults
        builtin = self.ENVIRONMENT_OVERRIDES.get(environment, {})
        desc_suffix = builtin.pop("description_suffix", "")

        # Merge: base -> builtin -> file overrides
        merged: dict[str, Any] = {**base_config.__dict__}
        for key, value in builtin.items():
            if key not in env_overrides:
                merged[key] = value
        merged.update(env_overrides)

        if desc_suffix and not merged.get("description", "").endswith(desc_suffix):
            merged["description"] = merged.get("description", "") + desc_suffix

        valid_fields = {f.name for f in dataclasses.fields(ProjectConfig)}
        merged = {k: v for k, v in merged.items() if k in valid_fields}

        return ProjectConfig(**cast(dict[str, Any], merged))

    def save_environment_config(self, environment: str, overrides: dict[str, Any]) -> None:
        """
        保存环境特定的配置覆盖。

        Args:
            environment: 环境名
            overrides: 要覆盖的配置键值对
        """
        env_file = self.project_dir / f"super-dev.{environment}.yaml"
        existing: dict[str, Any] = {}
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            existing = loaded if isinstance(loaded, dict) else {}

        merged = {**existing, **overrides}
        with open(env_file, "w", encoding="utf-8") as f:
            yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)

    def list_environments(self) -> list[dict[str, str]]:
        """列出所有已配置的环境"""
        envs: list[dict[str, str]] = []
        for env_name in ("development", "staging", "production"):
            env_file = self.project_dir / f"super-dev.{env_name}.yaml"
            status = "configured" if env_file.exists() else "default"
            envs.append(
                {
                    "name": env_name,
                    "status": status,
                    "file": str(env_file) if env_file.exists() else "",
                }
            )
        # Check for custom environments
        for f in self.project_dir.glob("super-dev.*.yaml"):
            env_name = f.stem.replace("super-dev.", "")
            if env_name not in ("development", "staging", "production"):
                envs.append(
                    {
                        "name": env_name,
                        "status": "custom",
                        "file": str(f),
                    }
                )
        return envs


# 全局配置管理器缓存（按项目目录隔离）
_global_config_managers: dict[Path, ConfigManager] = {}


def get_config_manager(project_dir: Path | None = None) -> ConfigManager:
    """
    获取全局配置管理器实例

    Args:
        project_dir: 项目目录

    Returns:
        ConfigManager: 配置管理器实例
    """
    project_root = (Path.cwd() if project_dir is None else Path(project_dir)).resolve()
    manager = _global_config_managers.get(project_root)
    if manager is None:
        manager = ConfigManager(project_root)
        _global_config_managers[project_root] = manager
    return manager
