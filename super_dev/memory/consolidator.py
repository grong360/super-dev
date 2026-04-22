"""
Dream 整合器 — 4 阶段后台记忆整合。

4 阶段流程:
  1. Orient: 扫描记忆目录，读取 INDEX，了解现有 topic
  2. Gather Signal: 从最近 pipeline 执行中收集新信号
  3. Consolidate: 写入/更新记忆文件，合并而非创建近似重复
  4. Prune and Index: 更新 MEMORY.md，解决矛盾，删除过时条目

触发条件 (全部满足):
  - 距上次整合 ≥ min_hours (默认 24h)
  - 自上次整合以来 ≥ min_sessions (默认 5)
  - 无其他整合进程运行中

开发：Super Dev Team
创建时间：2026-03-31
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import MAX_INDEX_BYTES, MAX_INDEX_LINES, MemoryEntry, MemoryStore


@dataclass
class ConsolidationConfig:
    """整合触发配置"""

    min_hours: float = 24.0  # 距上次整合的最小小时数
    min_sessions: int = 5  # 最小 pipeline 执行次数
    max_memory_files: int = 200  # 最大记忆文件数
    index_max_lines: int = MAX_INDEX_LINES
    index_max_bytes: int = MAX_INDEX_BYTES


@dataclass
class ConsolidationResult:
    """整合执行结果"""

    phase: str = ""  # orient/gather/consolidate/prune
    files_created: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    contradictions_resolved: int = 0
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


class MemoryConsolidator:
    """Dream 记忆整合器"""

    LOCK_FILE = ".consolidation-lock"
    STATE_FILE = ".consolidation-state.json"

    def __init__(
        self,
        memory_dir: Path,
        config: ConsolidationConfig | None = None,
    ):
        self.memory_dir = Path(memory_dir)
        self.config = config or ConsolidationConfig()
        self.store = MemoryStore(self.memory_dir)

    def should_consolidate(self) -> bool:
        """检查是否满足整合触发条件"""
        # 条件 1: 锁文件检查
        lock_path = self.memory_dir / self.LOCK_FILE
        if lock_path.exists():
            return False

        # 条件 2: 时间间隔
        state = self._load_state()
        last_consolidated = state.get("last_consolidated_at", "")
        if last_consolidated:
            try:
                last_dt = datetime.fromisoformat(last_consolidated)
                hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_since < self.config.min_hours:
                    return False
            except (ValueError, TypeError):
                pass  # 状态损坏，允许整合

        # 条件 3: 会话计数
        sessions_since = state.get("sessions_since_consolidation", 0)
        if sessions_since < self.config.min_sessions:
            return False

        return True

    def increment_session_count(self) -> None:
        """每次 pipeline 执行后调用，增加会话计数"""
        state = self._load_state()
        state["sessions_since_consolidation"] = state.get("sessions_since_consolidation", 0) + 1
        self._save_state(state)

    def consolidate(self) -> ConsolidationResult:
        """执行 4 阶段整合"""
        result = ConsolidationResult()
        start = time.monotonic()

        # 获取锁
        lock_path = self.memory_dir / self.LOCK_FILE
        try:
            lock_path.touch(exist_ok=False)
        except FileExistsError:
            result.errors.append("另一个整合进程正在运行")
            return result

        try:
            # Phase 1: Orient
            result.phase = "orient"
            self.store.scan()  # 确认目录状态

            # Phase 2: Gather Signal
            result.phase = "gather"
            all_entries = self.store.list_all()

            # 按类型分组
            by_type: dict[str, list[MemoryEntry]] = {}
            for entry in all_entries:
                by_type.setdefault(entry.type, []).append(entry)

            # Phase 3: Consolidate
            result.phase = "consolidate"

            # 3a. 检测重复和近似重复
            for mem_type, entries in by_type.items():
                seen_names: dict[str, MemoryEntry] = {}
                for entry in entries:
                    normalized = entry.name.lower().strip()
                    if normalized in seen_names:
                        # 保留更新的，删除旧的
                        older = seen_names[normalized]
                        if entry.updated_at > older.updated_at:
                            self.store.delete(older.filename)
                            seen_names[normalized] = entry
                            result.files_deleted += 1
                        else:
                            self.store.delete(entry.filename)
                            result.files_deleted += 1
                        result.contradictions_resolved += 1
                    else:
                        seen_names[normalized] = entry

            # 3b. 检测矛盾 (同一 topic 的 project 记忆有冲突内容)
            project_entries = by_type.get("project", [])
            if len(project_entries) > self.config.max_memory_files:
                # 保留最新的 max_memory_files 个
                sorted_entries = sorted(project_entries, key=lambda e: e.updated_at, reverse=True)
                for old_entry in sorted_entries[self.config.max_memory_files :]:
                    self.store.delete(old_entry.filename)
                    result.files_deleted += 1

            # Phase 4: Prune and Index
            result.phase = "prune"
            self.store.update_index()

            # 更新整合状态
            state = self._load_state()
            state["last_consolidated_at"] = datetime.now(timezone.utc).isoformat()
            state["sessions_since_consolidation"] = 0
            state["last_result"] = {
                "files_created": result.files_created,
                "files_updated": result.files_updated,
                "files_deleted": result.files_deleted,
                "contradictions_resolved": result.contradictions_resolved,
            }
            self._save_state(state)

        except Exception as e:
            result.errors.append(str(e))
        finally:
            # 释放锁
            lock_path.unlink(missing_ok=True)

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def _load_state(self) -> dict[str, Any]:
        """加载整合状态"""
        state_path = self.memory_dir / self.STATE_FILE
        if not state_path.exists():
            return {}
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self, state: dict[str, Any]) -> None:
        """保存整合状态"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.memory_dir / self.STATE_FILE
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
