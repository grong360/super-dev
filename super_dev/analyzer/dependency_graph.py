from __future__ import annotations

import ast
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .analyzer import ProjectAnalyzer
from .repo_map import RepoMapBuilder, RepoMapReport

SUPPORTED_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx"}


@dataclass
class DependencyEdge:
    source: str
    target: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "kind": self.kind}


@dataclass
class DependencyNode:
    path: str
    inbound: int
    outbound: int
    score: int
    role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "inbound": self.inbound,
            "outbound": self.outbound,
            "score": self.score,
            "role": self.role,
        }


@dataclass
class CriticalPath:
    entry_point: str
    path: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"entry_point": self.entry_point, "path": list(self.path), "reason": self.reason}


@dataclass
class DependencyGraphReport:
    project_name: str
    project_path: str
    summary: str
    node_count: int
    edge_count: int
    critical_nodes: list[DependencyNode] = field(default_factory=list)
    critical_paths: list[CriticalPath] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "summary": self.summary,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "critical_nodes": [item.to_dict() for item in self.critical_nodes],
            "critical_paths": [item.to_dict() for item in self.critical_paths],
            "edges": [item.to_dict() for item in self.edges],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Dependency Graph",
            "",
            f"- Project: `{self.project_name}`",
            f"- Path: `{self.project_path}`",
            f"- Nodes: `{self.node_count}`",
            f"- Edges: `{self.edge_count}`",
            "",
            self.summary,
            "",
            "## Critical Nodes",
            "",
        ]
        if self.critical_nodes:
            for node in self.critical_nodes:
                lines.append(
                    f"- **{node.path}**: inbound={node.inbound}, outbound={node.outbound}, score={node.score}, role={node.role}"
                )
        else:
            lines.append("- None")
        lines.extend(["", "## Critical Paths", ""])
        if self.critical_paths:
            for item in self.critical_paths:
                lines.append(f"- **{item.entry_point}** -> {' -> '.join(item.path)}")
                lines.append(f"  - {item.reason}")
        else:
            lines.append("- None")
        lines.extend(["", "## Sample Edges", ""])
        if self.edges:
            for edge in self.edges[:30]:
                lines.append(f"- `{edge.source}` -> `{edge.target}` ({edge.kind})")
        else:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)


class DependencyGraphBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = self.project_dir.name
        self.analyzer = ProjectAnalyzer(self.project_dir)
        self.repo_map_builder = RepoMapBuilder(self.project_dir)

    def build(self) -> DependencyGraphReport:
        files = self._collect_source_files()
        path_index = {
            str(path.relative_to(self.project_dir)).replace("\\", "/"): path for path in files
        }
        module_index = self._build_module_index(files)
        edges = self._build_edges(files, module_index, path_index)
        inbound, outbound = self._degree(edges)
        repo_map = self.repo_map_builder.build()
        critical_nodes = self._critical_nodes(path_index, inbound, outbound, repo_map=repo_map)
        critical_paths = self._critical_paths(edges, critical_nodes, repo_map=repo_map)

        summary = (
            f"The dependency graph highlights `{len(path_index)}` source nodes and `{len(edges)}` internal import edges. "
            "Use the critical nodes and paths first when you need to understand blast radius, debug high-risk flows, "
            "or decide where to place regression coverage."
        )
        return DependencyGraphReport(
            project_name=self.project_name,
            project_path=str(self.project_dir),
            summary=summary,
            node_count=len(path_index),
            edge_count=len(edges),
            critical_nodes=critical_nodes,
            critical_paths=critical_paths,
            edges=edges,
        )

    def write(self, report: DependencyGraphReport) -> dict[str, Path]:
        md_path = self.output_dir / f"{self.project_name}-dependency-graph.md"
        json_path = self.output_dir / f"{self.project_name}-dependency-graph.json"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _collect_source_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.project_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in SUPPORTED_SUFFIXES:
                continue
            if self.analyzer._should_ignore_path(path):
                continue
            files.append(path)
        return files

    def _build_module_index(self, files: list[Path]) -> dict[str, str]:
        module_index: dict[str, str] = {}
        for path in files:
            rel = str(path.relative_to(self.project_dir)).replace("\\", "/")
            if path.suffix == ".py":
                dotted = ".".join(path.relative_to(self.project_dir).with_suffix("").parts)
                module_index[dotted] = rel
                if path.name == "__init__.py":
                    pkg = ".".join(path.relative_to(self.project_dir).parent.parts)
                    if pkg:
                        module_index[pkg] = rel
            else:
                stem = rel.rsplit(".", 1)[0]
                module_index[stem] = rel
                module_index[stem.replace("/", ".")] = rel
        return module_index

    def _build_edges(
        self,
        files: list[Path],
        module_index: dict[str, str],
        path_index: dict[str, Path],
    ) -> list[DependencyEdge]:
        edges: list[DependencyEdge] = []
        seen: set[tuple[str, str, str]] = set()
        for path in files:
            source = str(path.relative_to(self.project_dir)).replace("\\", "/")
            imports = self._extract_imports(path)
            for raw_import, kind in imports:
                target = self._resolve_import(source, raw_import, kind, module_index, path_index)
                if not target or target == source:
                    continue
                key = (source, target, kind)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(DependencyEdge(source=source, target=target, kind=kind))
        edges.sort(key=lambda item: (item.source, item.target, item.kind))
        return edges

    def _extract_imports(self, path: Path) -> list[tuple[str, str]]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        if path.suffix == ".py":
            return self._extract_python_imports(path, content)
        return self._extract_js_imports(content)

    def _extract_python_imports(self, path: Path, content: str) -> list[tuple[str, str]]:
        imports: list[tuple[str, str]] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return imports
        source_parts = list(path.relative_to(self.project_dir).with_suffix("").parts)
        if source_parts and source_parts[-1] == "__init__":
            source_parts = source_parts[:-1]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, "python-import"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    base = source_parts[:-1]
                    if node.level > 1:
                        base = source_parts[: max(0, len(source_parts) - node.level)]
                    prefix = ".".join(base)
                    module = ".".join(part for part in [prefix, module] if part)
                if module:
                    imports.append((module, "python-from"))
        return imports

    @staticmethod
    def _extract_js_imports(content: str) -> list[tuple[str, str]]:
        imports: list[tuple[str, str]] = []
        for match in re.finditer(
            r"""from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\(\s*['"]([^'"]+)['"]\s*\)""",
            content,
        ):
            raw = match.group(1) or match.group(2) or match.group(3)
            if raw:
                imports.append((raw, "module-import"))
        return imports

    def _resolve_import(
        self,
        source: str,
        raw_import: str,
        kind: str,
        module_index: dict[str, str],
        path_index: dict[str, Path],
    ) -> str:
        if kind.startswith("python"):
            if raw_import in module_index:
                return module_index[raw_import]
            return ""
        if not raw_import.startswith("."):
            if raw_import in module_index:
                return module_index[raw_import]
            return ""
        source_dir = Path(source).parent
        base = (source_dir / raw_import).as_posix()
        candidates = [
            base.lstrip("./"),
            f"{base.lstrip('./')}.ts",
            f"{base.lstrip('./')}.tsx",
            f"{base.lstrip('./')}.js",
            f"{base.lstrip('./')}.jsx",
            f"{base.lstrip('./')}/index.ts",
            f"{base.lstrip('./')}/index.tsx",
            f"{base.lstrip('./')}/index.js",
            f"{base.lstrip('./')}/index.jsx",
        ]
        for candidate in candidates:
            normalized = str(Path(candidate)).replace("\\", "/")
            if normalized in path_index:
                return normalized
        return ""

    @staticmethod
    def _degree(edges: list[DependencyEdge]) -> tuple[dict[str, int], dict[str, int]]:
        inbound: dict[str, int] = defaultdict(int)
        outbound: dict[str, int] = defaultdict(int)
        for edge in edges:
            outbound[edge.source] += 1
            inbound[edge.target] += 1
        return inbound, outbound

    def _critical_nodes(
        self,
        path_index: dict[str, Path],
        inbound: dict[str, int],
        outbound: dict[str, int],
        repo_map: RepoMapReport | None = None,
    ) -> list[DependencyNode]:
        if repo_map is None:
            repo_map = self.repo_map_builder.build()
        entry_paths = {item.path for item in repo_map.entry_points}
        nodes: list[DependencyNode] = []
        for rel in path_index:
            in_count = inbound.get(rel, 0)
            out_count = outbound.get(rel, 0)
            score = in_count * 3 + out_count * 2
            role = "entry-point" if rel in entry_paths else "internal"
            if score > 0 or role == "entry-point":
                nodes.append(
                    DependencyNode(
                        path=rel, inbound=in_count, outbound=out_count, score=score, role=role
                    )
                )
        nodes.sort(key=lambda item: (item.score, item.inbound, item.outbound), reverse=True)
        return nodes[:10]

    def _critical_paths(
        self,
        edges: list[DependencyEdge],
        critical_nodes: list[DependencyNode],
        repo_map: RepoMapReport | None = None,
    ) -> list[CriticalPath]:
        adjacency: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            adjacency[edge.source].append(edge.target)
        if repo_map is None:
            repo_map = self.repo_map_builder.build()
        entry_points = [item.path for item in repo_map.entry_points]
        targets = [item.path for item in critical_nodes[:5] if item.role != "entry-point"]
        paths: list[CriticalPath] = []
        for entry in entry_points[:5]:
            for target in targets:
                found = self._shortest_path(entry, target, adjacency)
                if found and len(found) > 1:
                    paths.append(
                        CriticalPath(
                            entry_point=entry,
                            path=found,
                            reason="Entry point reaches a high-centrality internal dependency path.",
                        )
                    )
        return paths[:8]

    @staticmethod
    def _shortest_path(start: str, end: str, adjacency: dict[str, list[str]]) -> list[str]:
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
        visited = {start}
        while queue:
            node, path = queue.popleft()
            if node == end:
                return path
            for neighbor in adjacency.get(node, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, [*path, neighbor]))
        return []
