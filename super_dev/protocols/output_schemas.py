"""
治理产出的结构化 Schema 定义

开发：Excellent（11964948@qq.com）
功能：定义所有治理输出的 JSON Schema
作用：确保治理产出格式统一、可验证、可被外部系统消费
创建时间：2025-12-30
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 质量门禁报告 Schema
# ---------------------------------------------------------------------------

QUALITY_GATE_SCHEMA: dict = {
    "type": "object",
    "required": ["project_name", "score", "passed", "checks"],
    "properties": {
        "project_name": {"type": "string"},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "passed": {"type": "boolean"},
        "threshold": {"type": "integer", "minimum": 0, "maximum": 100},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "category", "status", "score"],
                "properties": {
                    "name": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "documentation",
                            "security",
                            "performance",
                            "testing",
                            "code_quality",
                            "architecture",
                        ],
                    },
                    "status": {"type": "string", "enum": ["passed", "failed", "warning"]},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "details": {"type": "string"},
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 红队报告 Schema
# ---------------------------------------------------------------------------

REDTEAM_REPORT_SCHEMA: dict = {
    "type": "object",
    "required": ["project_name", "issues", "summary"],
    "properties": {
        "project_name": {"type": "string"},
        "summary": {
            "type": "object",
            "properties": {
                "total_issues": {"type": "integer", "minimum": 0},
                "critical": {"type": "integer", "minimum": 0},
                "high": {"type": "integer", "minimum": 0},
                "medium": {"type": "integer", "minimum": 0},
                "low": {"type": "integer", "minimum": 0},
            },
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "category", "description", "recommendation"],
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "cwe": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line": {"type": "integer"},
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 追溯矩阵 Schema
# ---------------------------------------------------------------------------

TRACEABILITY_MATRIX_SCHEMA: dict = {
    "type": "object",
    "required": ["project_name", "entries"],
    "properties": {
        "project_name": {"type": "string"},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["requirement_id", "status"],
                "properties": {
                    "requirement_id": {"type": "string"},
                    "requirement_text": {"type": "string"},
                    "spec_section": {"type": "string"},
                    "implementation_files": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "test_files": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "status": {
                        "type": "string",
                        "enum": ["covered", "partial", "missing"],
                    },
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 治理总报告 Schema
# ---------------------------------------------------------------------------

GOVERNANCE_REPORT_SCHEMA: dict = {
    "type": "object",
    "required": ["project_name", "version", "quality_gate", "redteam"],
    "properties": {
        "project_name": {"type": "string"},
        "version": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "quality_gate": QUALITY_GATE_SCHEMA,
        "redteam": REDTEAM_REPORT_SCHEMA,
        "traceability": TRACEABILITY_MATRIX_SCHEMA,
        "dora_metrics": {"$ref": "#/$defs/dora_metrics"},
    },
    "$defs": {
        "dora_metrics": {
            "type": "object",
            "properties": {
                "deployment_frequency": {"type": "string"},
                "lead_time_for_changes": {"type": "string"},
                "change_failure_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "time_to_restore_service": {"type": "string"},
            },
        },
    },
}

# ---------------------------------------------------------------------------
# DORA 指标 Schema
# ---------------------------------------------------------------------------

DORA_METRICS_SCHEMA: dict = {
    "type": "object",
    "required": ["deployment_frequency", "lead_time_for_changes"],
    "properties": {
        "deployment_frequency": {
            "type": "string",
            "description": "部署频率，如 daily / weekly / monthly",
        },
        "lead_time_for_changes": {
            "type": "string",
            "description": "变更前置时间，如 <1h / <1d / <1w",
        },
        "change_failure_rate": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "变更失败率 (0-1)",
        },
        "time_to_restore_service": {
            "type": "string",
            "description": "服务恢复时间，如 <1h / <1d",
        },
    },
}

# ---------------------------------------------------------------------------
# Baseline Audit Schema
# ---------------------------------------------------------------------------

BASELINE_AUDIT_SCHEMA: dict = {
    "type": "object",
    "required": ["project_name", "work_mode"],
    "properties": {
        "project_name": {"type": "string"},
        "work_mode": {
            "type": "string",
            "enum": ["new", "evolve", "variant", "patch", "resume"],
        },
        "generated_at": {"type": "string", "format": "date-time"},
        "current_state": {"type": "object"},
        "architecture_summary": {"type": "object"},
        "ui_summary": {"type": "object"},
        "constraints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "delta_scope": {
            "type": "object",
            "properties": {
                "goals": {"type": "array", "items": {"type": "string"}},
                "affected_modules": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Schema 注册表
# ---------------------------------------------------------------------------

_SCHEMA_REGISTRY: dict[str, dict] = {
    "quality_gate": QUALITY_GATE_SCHEMA,
    "redteam_report": REDTEAM_REPORT_SCHEMA,
    "traceability_matrix": TRACEABILITY_MATRIX_SCHEMA,
    "governance_report": GOVERNANCE_REPORT_SCHEMA,
    "dora_metrics": DORA_METRICS_SCHEMA,
    "baseline_audit": BASELINE_AUDIT_SCHEMA,
}


# ---------------------------------------------------------------------------
# 轻量级验证器（不依赖 jsonschema 外部库）
# ---------------------------------------------------------------------------


class OutputValidator:
    """输出验证器 — 确保治理产出符合 Schema。

    提供轻量级的 JSON Schema 验证能力，覆盖 ``type``、``required``、
    ``enum``、``minimum``/``maximum`` 等常用约束。如果环境中安装了
    ``jsonschema`` 库则自动使用完整验证。
    """

    def validate(self, data: dict, schema_name: str) -> tuple[bool, list[str]]:  # type: ignore[type-arg]
        """验证数据是否符合指定 Schema。

        Returns:
            ``(is_valid, errors)`` — 若通过则 ``errors`` 为空列表。
        """
        schema = self.get_schema(schema_name)
        if schema is None:
            return False, [f"未知 schema: {schema_name}"]

        # 优先使用 jsonschema 库（如果可用）
        try:
            import jsonschema  # type: ignore[import-untyped]

            try:
                jsonschema.validate(instance=data, schema=schema)
                return True, []
            except jsonschema.ValidationError as exc:
                return False, [exc.message]
        except ImportError:
            pass

        # 回退到内置轻量验证
        errors = self._validate_object(data, schema, path="$")
        return len(errors) == 0, errors

    def get_schema(self, name: str) -> dict | None:  # type: ignore[type-arg]
        """获取指定 Schema，不存在时返回 ``None``。"""
        return _SCHEMA_REGISTRY.get(name)

    # ------------------------------------------------------------------
    # 轻量内置验证
    # ------------------------------------------------------------------

    def _validate_object(self, data: object, schema: dict, path: str) -> list[str]:  # type: ignore[type-arg]
        errors: list[str] = []
        expected_type = schema.get("type")

        # type check
        if expected_type:
            if not self._check_type(data, expected_type):
                errors.append(f"{path}: 期望类型 {expected_type}，实际 {type(data).__name__}")
                return errors

        if expected_type == "object" and isinstance(data, dict):
            # required
            for key in schema.get("required", []):
                if key not in data:
                    errors.append(f"{path}: 缺少必需字段 '{key}'")
            # properties
            props = schema.get("properties", {})
            for key, sub_schema in props.items():
                if key in data:
                    errors.extend(self._validate_object(data[key], sub_schema, f"{path}.{key}"))

        elif expected_type == "array" and isinstance(data, list):
            items_schema = schema.get("items")
            if items_schema:
                for idx, item in enumerate(data):
                    errors.extend(self._validate_object(item, items_schema, f"{path}[{idx}]"))

        # enum
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: 值 {data!r} 不在允许范围 {schema['enum']}")

        # minimum / maximum
        if isinstance(data, int | float):
            if "minimum" in schema and data < schema["minimum"]:
                errors.append(f"{path}: 值 {data} 小于最小值 {schema['minimum']}")
            if "maximum" in schema and data > schema["maximum"]:
                errors.append(f"{path}: 值 {data} 大于最大值 {schema['maximum']}")

        return errors

    @staticmethod
    def _check_type(value: object, expected: str) -> bool:
        type_map: dict[str, type | tuple[type, ...]] = {
            "object": dict,
            "array": list,
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
        }
        py_type = type_map.get(expected)
        if py_type is None:
            return True  # 未知类型不做限制
        # Python 中 bool 是 int 的子类，需要特殊处理
        if expected == "integer" and isinstance(value, bool):
            return False
        return isinstance(value, py_type)
