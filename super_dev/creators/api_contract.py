"""
API 契约生成器 — 从架构文档生成前后端共享的 TypeScript 类型定义。

解决的问题：
  - 前后端 API 路径和类型定义不一致
  - 手动维护共享类型容易遗漏
  - 从架构文档自动提取 API 定义，生成可直接使用的 TypeScript 代码
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class APIContractGenerator:
    """Generates shared TypeScript type definitions from architecture documents."""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_shared_types(
        self,
        project_dir: str | Path,
        arch_content: str | None = None,
    ) -> str:
        """Parse the architecture doc and generate shared TypeScript types.

        Parameters
        ----------
        project_dir:
            Project root; used to locate ``output/*-architecture.md`` if
            *arch_content* is not provided.
        arch_content:
            If given, used directly instead of reading from disk.

        Returns
        -------
        str
            TypeScript source code for ``output/shared/types.ts``.
        """
        try:
            project_dir = Path(project_dir)

            if arch_content is None:
                arch_content = self._read_architecture_doc(project_dir)
            if not arch_content:
                logger.info("No architecture content found; generating minimal types.")
                arch_content = ""

            models = self._extract_models(arch_content)
            routes = self._extract_routes(arch_content)

            return self._render_types_ts(models, routes)
        except Exception:
            logger.exception("generate_shared_types failed")
            return self._render_types_ts([], [])

    def generate_api_client(
        self,
        project_dir: str | Path,
        arch_content: str | None = None,
    ) -> str:
        """Generate a typed fetch-based API client.

        Parameters
        ----------
        project_dir:
            Project root.
        arch_content:
            Optional architecture doc content override.

        Returns
        -------
        str
            TypeScript source code for ``output/shared/api-client.ts``.
        """
        try:
            project_dir = Path(project_dir)

            if arch_content is None:
                arch_content = self._read_architecture_doc(project_dir)
            if not arch_content:
                arch_content = ""

            models = self._extract_models(arch_content)
            routes = self._extract_routes(arch_content)

            return self._render_api_client_ts(models, routes)
        except Exception:
            logger.exception("generate_api_client failed")
            return self._render_api_client_ts([], [])

    def generate_for_project(self, project_dir: str | Path) -> list[Path]:
        """Read config, generate types and api-client, write to ``output/shared/``.

        Returns the list of written file paths (absolute).
        """
        try:
            project_dir = Path(project_dir)

            types_code = self.generate_shared_types(project_dir)
            client_code = self.generate_api_client(project_dir)

            output_root = project_dir / "output" / "shared"
            output_root.mkdir(parents=True, exist_ok=True)

            written: list[Path] = []

            types_path = output_root / "types.ts"
            types_path.write_text(types_code, encoding="utf-8")
            written.append(types_path)

            client_path = output_root / "api-client.ts"
            client_path.write_text(client_code, encoding="utf-8")
            written.append(client_path)

            logger.info("API contract files written to %s", output_root)
            return written
        except Exception:
            logger.exception("generate_for_project failed")
            return []

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _read_architecture_doc(self, project_dir: Path) -> str:
        """Read the first ``output/*-architecture.md`` file found."""
        output_dir = project_dir / "output"
        if not output_dir.is_dir():
            return ""
        candidates = sorted(output_dir.glob("*-architecture.md"))
        if not candidates:
            return ""
        return candidates[0].read_text(encoding="utf-8")

    @staticmethod
    def _extract_models(content: str) -> list[dict[str, Any]]:
        """Extract data model definitions from architecture markdown.

        Looks for patterns like:
        - ``### User`` followed by field lists (``- id: string``)
        - Table-formatted models (``| field | type | description |``)
        """
        models: list[dict[str, Any]] = []
        if not content:
            return models

        # Pattern 1: heading + field list
        # e.g.  ### User\n- id: string\n- email: string
        model_block_re = re.compile(
            r"#{2,4}\s+(\w+)\s*(?:模型|Model|Entity|实体)?\s*\n" r"((?:\s*[-*]\s+\w+.*\n)+)",
            re.IGNORECASE,
        )
        for match in model_block_re.finditer(content):
            name = match.group(1).strip()
            fields_block = match.group(2)
            fields = _parse_field_list(fields_block)
            if fields:
                models.append({"name": name, "fields": fields})

        # Pattern 2: table format
        # | field | type | ...
        table_re = re.compile(
            r"#{2,4}\s+(\w+)\s*\n"
            r"\s*\|.*field.*\|.*type.*\|\s*\n"
            r"\s*\|[-| ]+\|\s*\n"
            r"((?:\s*\|.*\|\s*\n)+)",
            re.IGNORECASE,
        )
        existing_names = {m["name"] for m in models}
        for match in table_re.finditer(content):
            name = match.group(1).strip()
            if name in existing_names:
                continue
            rows = match.group(2)
            fields = _parse_field_table(rows)
            if fields:
                models.append({"name": name, "fields": fields})

        return models

    @staticmethod
    def _extract_routes(content: str) -> list[dict[str, str]]:
        """Extract API route definitions from architecture markdown.

        Looks for patterns like:
        - ``GET /api/users`` or ``POST /api/auth/login``
        - Table rows with method and path columns
        """
        routes: list[dict[str, str]] = []
        if not content:
            return routes

        seen: set[str] = set()

        # Pattern: METHOD /api/path
        route_re = re.compile(
            r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/api/[\w/{}:*-]+)",
            re.IGNORECASE,
        )
        for match in route_re.finditer(content):
            method = match.group(1).upper()
            path = match.group(2).strip()
            key = f"{method} {path}"
            if key not in seen:
                seen.add(key)
                routes.append({"method": method, "path": path})

        return routes

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_types_ts(
        self,
        models: list[dict[str, Any]],
        routes: list[dict[str, str]],
    ) -> str:
        """Render the shared ``types.ts`` file."""
        lines: list[str] = [
            "// output/shared/types.ts — Auto-generated from output/*-architecture.md",
            "// Do NOT edit manually. Re-generate with: super-dev generate types",
            "",
            "export interface ApiResponse<T> {",
            "  success: boolean;",
            "  data: T;",
            "  error?: string;",
            "}",
            "",
        ]

        if models:
            for model in models:
                lines.append(f"export interface {model['name']} {{")
                for fld in model["fields"]:
                    optional = "?" if fld.get("optional") else ""
                    lines.append(f"  {fld['name']}{optional}: {fld['type']};")
                lines.append("}")
                lines.append("")
        else:
            # Emit a placeholder model so the file is always useful
            lines.extend(
                [
                    "export interface User {",
                    "  id: string;",
                    "  email: string;",
                    "  name: string;",
                    "  createdAt: string;",
                    "}",
                    "",
                ]
            )

        # Route constants
        lines.append("// API Route constants")
        lines.append("export const API_ROUTES = {")

        if routes:
            for route in routes:
                const_name = self._route_to_const_name(route["method"], route["path"])
                ts_path = self._path_to_ts(route["path"])
                lines.append(f"  {const_name}: {ts_path},")
        else:
            # Emit placeholders
            lines.append('  USERS: "/api/users",')
            lines.append("  USER_BY_ID: (id: string) => `/api/users/${id}` as const,")
            lines.append('  AUTH_LOGIN: "/api/auth/login",')
            lines.append('  AUTH_REGISTER: "/api/auth/register",')

        lines.append("} as const;")
        lines.append("")

        return "\n".join(lines)

    def _render_api_client_ts(
        self,
        models: list[dict[str, Any]],
        routes: list[dict[str, str]],
    ) -> str:
        """Render the ``api-client.ts`` file."""
        # Determine imports from types.ts
        model_names = [m["name"] for m in models]
        type_imports = ", ".join(model_names) if model_names else "User"

        lines: list[str] = [
            "// output/shared/api-client.ts — Auto-generated from output/*-architecture.md",
            "// Do NOT edit manually. Re-generate with: super-dev generate types",
            "",
            f'import type {{ {type_imports}, ApiResponse }} from "./types";',
            'import {{ API_ROUTES }} from "./types";',
            "",
            "async function fetchApi<T>(",
            "  url: string,",
            "  options?: RequestInit,",
            "): Promise<ApiResponse<T>> {",
            "  const res = await fetch(url, {",
            '    headers: { "Content-Type": "application/json", ...options?.headers },',
            "    ...options,",
            "  });",
            "  return res.json();",
            "}",
            "",
        ]

        # Build grouped api object
        groups = self._group_routes(routes)

        lines.append("export const api = {")
        if groups:
            for group_name, group_routes in groups.items():
                lines.append(f"  {group_name}: {{")
                for route in group_routes:
                    fn_line = self._route_to_api_method(route, models)
                    lines.append(f"    {fn_line}")
                lines.append("  },")
        else:
            # Placeholder
            lines.extend(
                [
                    "  users: {",
                    "    list: () => fetchApi<User[]>(API_ROUTES.USERS),",
                    "    getById: (id: string) => fetchApi<User>(API_ROUTES.USER_BY_ID(id)),",
                    "  },",
                    "  auth: {",
                    "    login: (email: string, password: string) =>",
                    "      fetchApi<{ token: string }>(API_ROUTES.AUTH_LOGIN, {",
                    '        method: "POST",',
                    "        body: JSON.stringify({ email, password }),",
                    "      }),",
                    "  },",
                ]
            )

        lines.append("};")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _route_to_const_name(method: str, path: str) -> str:
        """Convert ``GET /api/users/:id`` to ``GET_USER_BY_ID``."""
        # Strip /api/ prefix
        trimmed = re.sub(r"^/api/?", "", path)
        # Replace path params with descriptive text
        trimmed = re.sub(r"[/:{}]+", "_", trimmed)
        trimmed = trimmed.strip("_").upper()
        if not trimmed:
            trimmed = "ROOT"
        # Prefix method only for non-GET
        if method != "GET":
            return f"{method}_{trimmed}"
        return trimmed

    @staticmethod
    def _path_to_ts(path: str) -> str:
        """Convert route path to TypeScript constant or arrow function.

        ``/api/users`` -> ``"/api/users"``
        ``/api/users/:id`` -> ``(id: string) => `/api/users/${id}` as const``
        """
        params = re.findall(r":(\w+)|{(\w+)}", path)
        if not params:
            return f'"{path}"'
        # Flatten param names
        param_names = [p[0] or p[1] for p in params]
        ts_params = ", ".join(f"{name}: string" for name in param_names)
        ts_path = path
        for name in param_names:
            ts_path = re.sub(rf":{name}|{{{name}}}", f"${{{name}}}", ts_path)
        return f"({ts_params}) => `{ts_path}` as const"

    @staticmethod
    def _group_routes(routes: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
        """Group routes by their first path segment after ``/api/``."""
        groups: dict[str, list[dict[str, str]]] = {}
        for route in routes:
            trimmed = re.sub(r"^/api/?", "", route["path"])
            segment = trimmed.split("/")[0] if trimmed else "root"
            groups.setdefault(segment, []).append(route)
        return groups

    @staticmethod
    def _route_to_api_method(route: dict[str, str], models: list[dict[str, Any]]) -> str:
        """Generate a single api method line for a route."""
        method = route["method"]
        path = route["path"]

        # Derive function name
        trimmed = re.sub(r"^/api/?", "", path)
        parts = [p for p in trimmed.split("/") if not p.startswith(":") and not p.startswith("{")]
        param_parts = re.findall(r":(\w+)|{(\w+)}", path)
        param_names = [p[0] or p[1] for p in param_parts]

        if method == "GET" and not param_names:
            fn_name = "list"
        elif method == "GET" and param_names:
            fn_name = "getById"
        elif method == "POST":
            fn_name = "create"
        elif method == "PUT" or method == "PATCH":
            fn_name = "update"
        elif method == "DELETE":
            fn_name = "remove"
        else:
            fn_name = method.lower()

        # Determine const name
        const_name = APIContractGenerator._route_to_const_name(method, path)

        # Build return type guess
        first_model = parts[0].rstrip("s").capitalize() if parts else "unknown"
        matching_model = next(
            (m["name"] for m in models if m["name"].lower() == first_model.lower()),
            first_model,
        )
        return_type = f"{matching_model}[]" if fn_name == "list" else matching_model

        if param_names:
            ts_params = ", ".join(f"{n}: string" for n in param_names)
            route_call = f"API_ROUTES.{const_name}({', '.join(param_names)})"
        else:
            ts_params = ""
            route_call = f"API_ROUTES.{const_name}"

        if method in {"POST", "PUT", "PATCH"}:
            body_param = "data: Record<string, unknown>"
            all_params = f"{ts_params}, {body_param}" if ts_params else body_param
            return (
                f"{fn_name}: ({all_params}) =>\n"
                f"      fetchApi<{return_type}>({route_call}, "
                f'{{ method: "{method}", body: JSON.stringify(data) }}),'
            )

        if ts_params:
            return f"{fn_name}: ({ts_params}) => fetchApi<{return_type}>({route_call}),"

        return f"{fn_name}: () => fetchApi<{return_type}>({route_call}),"


# ======================================================================
# Module-level helpers for parsing field definitions
# ======================================================================


def _parse_field_list(block: str) -> list[dict[str, str | bool]]:
    """Parse ``- fieldName: type`` lines into a list of field dicts."""
    fields: list[dict[str, str | bool]] = []
    for line in block.strip().splitlines():
        line = line.strip().lstrip("-*").strip()
        # Patterns: "id: string", "id (string)", "id - string"
        match = re.match(r"(\w+)\s*[:()\-|]\s*(\w+)", line)
        if match:
            name = match.group(1)
            raw_type = match.group(2).lower()
            ts_type = _map_to_ts_type(raw_type)
            optional = "?" in line or "optional" in line.lower()
            fields.append({"name": name, "type": ts_type, "optional": optional})
    return fields


def _parse_field_table(rows: str) -> list[dict[str, str | bool]]:
    """Parse markdown table rows into field dicts."""
    fields: list[dict[str, str | bool]] = []
    for line in rows.strip().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2:
            name = cells[0].strip()
            raw_type = cells[1].strip().lower()
            if name and raw_type and not name.startswith("-"):
                ts_type = _map_to_ts_type(raw_type)
                fields.append({"name": name, "type": ts_type})
    return fields


def _map_to_ts_type(raw: str) -> str:
    """Map common type names to TypeScript type strings."""
    mapping = {
        "string": "string",
        "str": "string",
        "text": "string",
        "varchar": "string",
        "char": "string",
        "uuid": "string",
        "int": "number",
        "integer": "number",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "number": "number",
        "bigint": "number",
        "bool": "boolean",
        "boolean": "boolean",
        "date": "string",
        "datetime": "string",
        "timestamp": "string",
        "json": "Record<string, unknown>",
        "jsonb": "Record<string, unknown>",
        "array": "unknown[]",
    }
    return mapping.get(raw, "string")
