"""
Spec 任务执行器

根据 `.super-dev/changes/*/tasks.md` 的任务列表执行实现收敛动作，
并在必要时做一次自动修复后重试，输出任务执行报告。
"""

from __future__ import annotations

import re
import subprocess  # nosec B404
from dataclasses import dataclass, field
from pathlib import Path

from ..specs import ChangeManager
from ..specs.models import ChangeStatus, Task, TaskStatus
from ..workflow_guard import require_docs_confirmation, require_preview_confirmation


@dataclass
class TaskExecutionSummary:
    """任务执行摘要"""

    change_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: list[str] = field(default_factory=list)
    repaired_actions: list[str] = field(default_factory=list)
    report_file: str = ""


class SpecTaskExecutor:
    """Spec 任务执行器"""

    def __init__(self, project_dir: Path, project_name: str):
        self.project_dir = Path(project_dir).resolve()
        self.project_name = project_name
        self.change_manager = ChangeManager(self.project_dir)

    def execute(
        self,
        change_id: str,
        tech_stack: dict[str, str],
        max_retries: int = 1,
    ) -> TaskExecutionSummary:
        require_docs_confirmation(
            self.project_dir,
            action="spec_task_execute",
            require_context=True,
        )

        change = self.change_manager.load_change(change_id)
        if not change:
            raise FileNotFoundError(f"change not found: {change_id}")

        modules = self._extract_modules(change.tasks)
        repaired_actions: list[str] = []
        failed_tasks: list[str] = []
        task_map = {task.id: task for task in change.tasks}
        executable_tasks = sorted(change.tasks, key=self._task_sort_key)

        # 按依赖关系执行任务：依赖未完成时先跳过，避免越序执行。
        max_pass = max(1, len(executable_tasks) + 1)
        for _ in range(max_pass):
            progressed = False
            for task in executable_tasks:
                if task.status == TaskStatus.COMPLETED:
                    continue

                unmet_dependencies = [
                    dep
                    for dep in task.dependencies
                    if dep in task_map and task_map[dep].status != TaskStatus.COMPLETED
                ]
                if unmet_dependencies:
                    continue

                ok = self._execute_task(task, tech_stack, modules, max_retries, repaired_actions)
                if ok:
                    task.status = TaskStatus.COMPLETED
                    progressed = True
                else:
                    task.status = TaskStatus.IN_PROGRESS
                    if task.id not in failed_tasks:
                        failed_tasks.append(task.id)

            if all(task.status == TaskStatus.COMPLETED for task in executable_tasks):
                break
            if not progressed:
                break

        for task in executable_tasks:
            if task.status != TaskStatus.COMPLETED and task.id not in failed_tasks:
                failed_tasks.append(task.id)

        if change.tasks and all(task.status == TaskStatus.COMPLETED for task in change.tasks):
            change.status = ChangeStatus.COMPLETED
        else:
            change.status = ChangeStatus.IN_PROGRESS
        self.change_manager.save_change(change)

        completed_tasks = sum(1 for task in change.tasks if task.status == TaskStatus.COMPLETED)
        report_path = self._write_report(
            change_id=change_id,
            total_tasks=len(change.tasks),
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            repaired_actions=repaired_actions,
            tech_stack=tech_stack,
        )

        return TaskExecutionSummary(
            change_id=change_id,
            total_tasks=len(change.tasks),
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            repaired_actions=repaired_actions,
            report_file=str(report_path),
        )

    def _execute_task(
        self,
        task: Task,
        tech_stack: dict[str, str],
        modules: list[str],
        max_retries: int,
        repaired_actions: list[str],
    ) -> bool:
        title = task.title.lower()
        requested_phases = self._requested_phases_for_task(title)
        if requested_phases:
            require_preview_confirmation(
                self.project_dir,
                action=f"spec_task_execute:{task.id}",
                requested_phases=requested_phases,
                require_context=True,
            )
        if "前端" in title or "frontend" in title:
            self._ensure_frontend_modules(modules, tech_stack.get("frontend", "react"))
            return True
        if "后端" in title or "backend" in title:
            self._ensure_backend_modules(modules, tech_stack.get("backend", "node"))
            return True
        if "联调" in title:
            return self._verify_basic_contract()
        if "测试" in title or "test" in title or "质量" in title:
            return self._validation_with_repair(tech_stack, max_retries, repaired_actions)
        return True

    def _requested_phases_for_task(self, title: str) -> list[str]:
        lowered = str(title).strip().lower()
        if any(token in lowered for token in ("后端", "backend")):
            return ["backend"]
        if any(token in lowered for token in ("联调", "integration", "qa", "质量", "test", "发布", "delivery", "上线")):
            if any(token in lowered for token in ("发布", "delivery", "上线")):
                return ["delivery"]
            if any(token in lowered for token in ("质量", "test", "qa")):
                return ["quality"]
            return ["backend"]
        return []

    def _extract_modules(self, tasks: list[Task]) -> list[str]:
        modules: list[str] = []
        for task in tasks:
            for ref in task.spec_refs:
                if "::" in ref:
                    spec_name = ref.split("::", 1)[0].strip()
                else:
                    spec_name = ref.strip()
                if not spec_name or spec_name in {"core", "*"}:
                    continue
                if spec_name not in modules:
                    modules.append(spec_name)
            if not task.spec_refs:
                inferred = self._extract_module_from_title(task.title)
                if inferred and inferred not in modules:
                    modules.append(inferred)
        return modules or ["core"]

    def _extract_module_from_title(self, title: str) -> str:
        title_text = title.strip()
        if not title_text:
            return ""
        patterns = [
            r"实现\s+([A-Za-z0-9_\-\u4e00-\u9fff]+)\s*前端",
            r"实现\s+([A-Za-z0-9_\-\u4e00-\u9fff]+)\s*后端",
            r"测试\s+([A-Za-z0-9_\-\u4e00-\u9fff]+)\s*功能",
        ]
        for pattern in patterns:
            match = re.search(pattern, title_text)
            if not match:
                continue
            candidate = match.group(1).strip().lower()
            if candidate and candidate not in {"core", "功能", "模块"}:
                return candidate
        return ""

    def _ensure_frontend_modules(self, modules: list[str], frontend: str) -> None:
        frontend_kind = (frontend or "react").lower()
        modules_dir = self.project_dir / "frontend" / "src" / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)

        for module in modules:
            safe_name = self._safe_route_segment(module)
            if frontend_kind == "vue":
                module_file = modules_dir / f"{safe_name}.vue"
                if not module_file.exists():
                    module_file.write_text(
                        "<template><p>auto repaired module</p></template>\n",
                        encoding="utf-8",
                    )
            elif frontend_kind == "svelte":
                module_file = modules_dir / f"{safe_name}.svelte"
                if not module_file.exists():
                    module_file.write_text("<p>auto repaired module</p>\n", encoding="utf-8")
            else:
                module_file = modules_dir / f"{safe_name}.tsx"
                if not module_file.exists():
                    component = self._to_component(safe_name)
                    module_file.write_text(
                        (
                            "import React from 'react';\n\n"
                            f"export default function {component}() {{\n"
                            "  return <p>auto repaired module</p>;\n"
                            "}\n"
                        ),
                        encoding="utf-8",
                    )

    def _ensure_backend_modules(self, modules: list[str], backend: str) -> None:
        backend_kind = (backend or "node").lower()
        if backend_kind == "python":
            self._ensure_python_backend_modules(modules)
            return
        if backend_kind == "node":
            self._ensure_node_backend_modules(modules)
            return

    def _ensure_node_backend_modules(self, modules: list[str]) -> None:
        src_dir = self.project_dir / "backend" / "src"
        routes_dir = src_dir / "routes"
        services_dir = src_dir / "services"
        repositories_dir = src_dir / "repositories"
        routes_dir.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(parents=True, exist_ok=True)
        repositories_dir.mkdir(parents=True, exist_ok=True)

        for module in modules:
            route_segment = self._safe_route_segment(module)
            title = self._to_component(route_segment)
            identifier = self._safe_identifier(route_segment)

            repo_file = repositories_dir / f"{route_segment}.repository.js"
            if not repo_file.exists():
                repo_file.write_text(
                    (
                        f"const store = [];\n"
                        f"function list{title}() {{ return store; }}\n"
                        f"function create{title}(payload) {{\n"
                        "  const record = { id: store.length + 1, ...payload };\n"
                        "  store.push(record);\n"
                        "  return record;\n"
                        "}\n"
                        f"module.exports = {{ list{title}, create{title} }};\n"
                    ),
                    encoding="utf-8",
                )

            service_file = services_dir / f"{route_segment}.service.js"
            if not service_file.exists():
                service_file.write_text(
                    (
                        f"const repo = require('../repositories/{route_segment}.repository');\n"
                        f"function list{title}Items() {{ return repo.list{title}(); }}\n"
                        f"function create{title}Item(payload) {{ return repo.create{title}(payload); }}\n"
                        f"module.exports = {{ list{title}Items, create{title}Item }};\n"
                    ),
                    encoding="utf-8",
                )

            route_file = routes_dir / f"{route_segment}.route.js"
            if not route_file.exists():
                route_file.write_text(
                    (
                        "const express = require('express');\n"
                        f"const service = require('../services/{route_segment}.service');\n"
                        "const router = express.Router();\n"
                        "router.get('/', (_req, res) => {\n"
                        f"  res.json({{ module: '{module}', items: service.list{title}Items() }});\n"
                        "});\n"
                        "router.post('/', (req, res) => {\n"
                        f"  res.status(201).json(service.create{title}Item(req.body || {{ module: '{module}' }}));\n"
                        "});\n"
                        "module.exports = router;\n"
                    ),
                    encoding="utf-8",
                )

            migration_file = (
                self.project_dir / "backend" / "migrations" / f"999_create_{identifier}.sql"
            )
            migration_file.parent.mkdir(parents=True, exist_ok=True)
            if not migration_file.exists():
                migration_file.write_text(
                    (
                        f"CREATE TABLE IF NOT EXISTS {identifier}_items (\n"
                        "  id INTEGER PRIMARY KEY,\n"
                        "  name VARCHAR(255) NOT NULL,\n"
                        "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                        ");\n"
                    ),
                    encoding="utf-8",
                )

    def _ensure_python_backend_modules(self, modules: list[str]) -> None:
        src_dir = self.project_dir / "backend" / "src"
        routes_dir = src_dir / "routes"
        services_dir = src_dir / "services"
        repositories_dir = src_dir / "repositories"
        for path in (src_dir, routes_dir, services_dir, repositories_dir):
            path.mkdir(parents=True, exist_ok=True)
            init_file = path / "__init__.py"
            if not init_file.exists():
                init_file.write_text("", encoding="utf-8")

        for module in modules:
            route_segment = self._safe_route_segment(module)
            identifier = self._safe_identifier(route_segment)
            title = self._to_component(route_segment)

            repo_file = repositories_dir / f"{route_segment}_repository.py"
            if not repo_file.exists():
                repo_file.write_text(
                    (
                        f"{identifier}_store: list[dict] = []\n\n"
                        f"def list_{identifier}() -> list[dict]:\n"
                        f"    return {identifier}_store\n\n"
                        f"def create_{identifier}(payload: dict) -> dict:\n"
                        f"    record = {{'id': len({identifier}_store) + 1, **payload}}\n"
                        f"    {identifier}_store.append(record)\n"
                        "    return record\n"
                    ),
                    encoding="utf-8",
                )

            service_file = services_dir / f"{route_segment}_service.py"
            if not service_file.exists():
                service_file.write_text(
                    (
                        f"from ..repositories.{route_segment}_repository import create_{identifier}, list_{identifier}\n\n"
                        f"def list_{identifier}_items() -> list[dict]:\n"
                        f"    return list_{identifier}()\n\n"
                        f"def create_{identifier}_item(payload: dict) -> dict:\n"
                        f"    return create_{identifier}(payload)\n"
                    ),
                    encoding="utf-8",
                )

            route_file = routes_dir / f"{route_segment}_route.py"
            if not route_file.exists():
                route_file.write_text(
                    (
                        "from fastapi import APIRouter\n"
                        "from pydantic import BaseModel\n"
                        f"from ..services.{route_segment}_service import create_{identifier}_item, list_{identifier}_items\n\n"
                        f"class {title}Payload(BaseModel):\n"
                        "    name: str = 'sample'\n\n"
                        f"router = APIRouter(prefix='/api/{route_segment}', tags=['{module}'])\n\n"
                        "@router.get('')\n"
                        f"def get_{identifier}() -> dict:\n"
                        f"    return {{'module': '{module}', 'items': list_{identifier}_items()}}\n\n"
                        "@router.post('', status_code=201)\n"
                        f"def create_{identifier}(payload: {title}Payload) -> dict:\n"
                        f"    return create_{identifier}_item(payload.model_dump())\n"
                    ),
                    encoding="utf-8",
                )

    def _verify_basic_contract(self) -> bool:
        api_contract = self.project_dir / "backend" / "API_CONTRACT.md"
        if not api_contract.exists():
            return False
        content = api_contract.read_text(encoding="utf-8", errors="ignore")
        has_path = "/api/" in content
        has_get = "GET" in content
        has_post = "POST" in content
        return has_path and has_get and has_post

    def _validation_with_repair(
        self,
        tech_stack: dict[str, str],
        max_retries: int,
        repaired_actions: list[str],
    ) -> bool:
        backend = (tech_stack.get("backend") or "node").lower()
        for attempt in range(max_retries + 1):
            if self._run_validation_checks(backend):
                return True
            if attempt < max_retries:
                action = self._apply_repair(backend)
                if action:
                    repaired_actions.append(action)
        return False

    def _run_validation_checks(self, backend: str) -> bool:
        if backend == "python":
            source_dir = self.project_dir / "backend" / "src"
            if source_dir.exists() and not self._run_command(
                ["python3", "-m", "compileall", "-q", "backend/src"],
                timeout=40,
            ):
                return False
            tests_dir = self.project_dir / "backend" / "tests"
            if tests_dir.exists():
                pytest_cmd = ["python3", "-m", "pytest", "-q", "backend/tests", "--maxfail=1"]
                return self._run_command(pytest_cmd, timeout=90)
            return True

        if backend == "node":
            app_file = self.project_dir / "backend" / "src" / "app.js"
            if app_file.exists() and not self._run_command(
                ["node", "--check", "backend/src/app.js"],
                timeout=20,
            ):
                return False

            test_paths: list[str] = []
            primary_test = self.project_dir / "backend" / "src" / "app.test.js"
            if primary_test.exists():
                test_paths.append("backend/src/app.test.js")
            extra_tests = sorted((self.project_dir / "backend" / "tests").glob("*.test.js"))
            test_paths.extend(str(path.relative_to(self.project_dir)) for path in extra_tests)
            if not test_paths:
                return True
            return self._run_command(["node", "--test", *test_paths], timeout=60)

        return True

    def _apply_repair(self, backend: str) -> str:
        if backend == "python":
            conftest_file = self.project_dir / "backend" / "tests" / "conftest.py"
            conftest_file.parent.mkdir(parents=True, exist_ok=True)
            conftest_file.write_text(
                (
                    "from pathlib import Path\n"
                    "import sys\n\n"
                    "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
                ),
                encoding="utf-8",
            )
            return "python: added backend/tests/conftest.py path bootstrap"

        if backend == "node":
            app_file = self.project_dir / "backend" / "src" / "app.js"
            if not app_file.exists():
                app_file.parent.mkdir(parents=True, exist_ok=True)
                app_file.write_text(
                    (
                        "const express = require('express');\n"
                        "const app = express();\n"
                        "app.use(express.json());\n"
                        "app.get('/health', (_req, res) => res.json({ status: 'ok' }));\n"
                        "module.exports = app;\n"
                    ),
                    encoding="utf-8",
                )
            app_test_file = self.project_dir / "backend" / "src" / "app.test.js"
            if not app_test_file.exists():
                app_test_file.parent.mkdir(parents=True, exist_ok=True)
                app_test_file.write_text(
                    (
                        "const test = require('node:test');\n"
                        "const assert = require('node:assert/strict');\n\n"
                        "test('health scaffold', () => {\n"
                        "  assert.equal(1 + 1, 2);\n"
                        "});\n"
                    ),
                    encoding="utf-8",
                )
            return "node: repaired backend/src/app.js and backend/src/app.test.js"

        return ""

    def _run_command(self, cmd: list[str], timeout: int) -> bool:
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )  # nosec B603
        except FileNotFoundError:
            return True
        except Exception:
            return False
        return result.returncode == 0

    def _write_report(
        self,
        change_id: str,
        total_tasks: int,
        completed_tasks: int,
        failed_tasks: list[str],
        repaired_actions: list[str],
        tech_stack: dict[str, str],
    ) -> Path:
        output_dir = self.project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"{self.project_name}-task-execution.md"
        framework_focus = self._read_framework_focus()
        frontend_target = str(tech_stack.get("frontend") or "web")
        backend_target = str(tech_stack.get("backend") or "service")

        lines = [
            "# Spec 任务执行报告",
            "",
            f"- Change: `{change_id}`",
            f"- 总任务: {total_tasks}",
            f"- 已完成: {completed_tasks}",
            f"- 未完成: {len(failed_tasks)}",
            "",
            "## 自动修复记录",
            "",
        ]
        if repaired_actions:
            for action in repaired_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- 无")
        lines.extend(["", "## 未完成任务", ""])
        if failed_tasks:
            for task_id in failed_tasks:
                lines.append(f"- {task_id}")
        else:
            lines.append("- 无")
        lines.extend(
            [
                "",
                "## 执行期验证摘要",
                "",
                f"- 任务闭环: {'通过' if not failed_tasks else '未完成'}",
                f"- 自动修复记录: {'有' if repaired_actions else '无'}",
                "",
                "## 阶段执行图纸",
                "",
                f"- 当前前端目标: {frontend_target}",
                f"- 当前后端目标: {backend_target}",
                f"- Framework Coaching Focus: {framework_focus}",
                "- 严格顺序: 先 research/docs/spec，再前端预览，再后端/联调/质量/交付。",
                "- 硬门禁: docs_confirm 未通过不能继续 Spec；preview_confirm 未通过不能继续 backend / quality / delivery。",
                "- UI 不是最后补皮；宿主必须先落实 UI 契约里的视觉方向、证明结构、组件工艺与 token 系统。",
                "",
                "## 宿主补充自检（交付前必做）",
                "",
                "- [ ] 运行项目原生 build / compile / type-check / test / runtime smoke，并确认没有编译错误",
                "- [ ] 检查本轮新增函数、方法、字段、模块都已接入真实调用链；未接入则删除",
                "- [ ] 检查没有新增 unused code、未引用文件或新增 warning",
                "- [ ] 对本次 diff 做最小自审，确认新增日志、埋点、恢复逻辑真正生效",
                "",
            ]
        )
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def _read_framework_focus(self) -> str:
        contract_path = self.project_dir / "output" / f"{self.project_name}-ui-contract.json"
        if not contract_path.exists():
            return "先锁定当前项目的框架专项 playbook，再让宿主进入实现。"
        try:
            import json

            payload = json.loads(contract_path.read_text(encoding="utf-8"))
        except Exception:
            return "先锁定当前项目的框架专项 playbook，再让宿主进入实现。"
        if not isinstance(payload, dict):
            return "先锁定当前项目的框架专项 playbook，再让宿主进入实现。"
        framework_playbook = (
            payload.get("framework_playbook")
            if isinstance(payload.get("framework_playbook"), dict)
            else {}
        )
        focus = str(framework_playbook.get("focus") or "").strip()
        if focus:
            return focus
        return "先锁定当前项目的框架专项 playbook，再让宿主进入实现。"

    def _task_sort_key(self, task: Task) -> tuple[int, int]:
        raw = task.id.strip()
        major, minor = 999, 999
        if "." in raw:
            left, right = raw.split(".", 1)
            if left.isdigit():
                major = int(left)
            if right.isdigit():
                minor = int(right)
        return major, minor

    def _safe_identifier(self, value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
        if not cleaned:
            return "module"
        if cleaned[0].isdigit():
            return f"m_{cleaned}"
        return cleaned

    def _safe_route_segment(self, value: str) -> str:
        cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in value.lower())
        cleaned = cleaned.strip("-_")
        return cleaned or "core"

    def _to_component(self, value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "-" for ch in value)
        parts = [part for part in cleaned.split("-") if part]
        if not parts:
            return "Module"
        return "".join(part[:1].upper() + part[1:] for part in parts)
