"""
知识演化引擎 (Knowledge Evolution Engine)

借鉴 OpenSpace 的 SkillStore + ExecutionAnalyzer 自演化理念：
- 追踪每个知识文件的使用频率、命中率、约束违反率
- 数据驱动优化：用得多且有效的知识加权，无效的降权
- 每轮 pipeline 执行后分析知识效果，生成改进建议

存储: .super-dev/knowledge-stats.db (SQLite)

开发：Excellent（11964948@qq.com）
创建时间：2026-03-28
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .utils import get_logger

_logger = get_logger("knowledge_evolution")

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeFileStats:
    """单个知识文件的统计数据"""

    file_path: str
    domain: str = ""
    category: str = ""
    total_references: int = 0
    """总引用次数"""
    total_constraints_pushed: int = 0
    """推送的约束次数"""
    constraints_followed: int = 0
    """约束被遵循的次数"""
    constraints_violated: int = 0
    """约束被违反的次数"""
    effectiveness_score: float = 0.0
    """有效性评分 0-1"""
    last_used: str = ""
    """最后使用时间 (ISO 8601)"""
    last_updated: str = ""
    """最后更新时间 (ISO 8601)"""

    @property
    def compliance_rate(self) -> float:
        """约束遵循率"""
        total = self.constraints_followed + self.constraints_violated
        if total == 0:
            return 0.0
        return self.constraints_followed / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "domain": self.domain,
            "category": self.category,
            "total_references": self.total_references,
            "total_constraints_pushed": self.total_constraints_pushed,
            "constraints_followed": self.constraints_followed,
            "constraints_violated": self.constraints_violated,
            "effectiveness_score": round(self.effectiveness_score, 4),
            "compliance_rate": round(self.compliance_rate, 4),
            "last_used": self.last_used,
            "last_updated": self.last_updated,
        }


@dataclass
class EvolutionSuggestion:
    """知识演化改进建议"""

    suggestion_type: str
    """类型: boost / demote / review / create / retire"""
    file_path: str
    """目标知识文件路径"""
    reason: str
    """建议原因"""
    priority: int = 0
    """优先级 1-5 (5 最高)"""
    data: dict[str, Any] = field(default_factory=dict)
    """附加数据"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.suggestion_type,
            "file_path": self.file_path,
            "reason": self.reason,
            "priority": self.priority,
            "data": self.data,
        }


@dataclass
class EvolutionReport:
    """知识演化报告"""

    generated_at: str
    total_knowledge_files: int = 0
    tracked_files: int = 0
    total_pipeline_runs: int = 0
    top_effective: list[KnowledgeFileStats] = field(default_factory=list)
    least_effective: list[KnowledgeFileStats] = field(default_factory=list)
    never_used: list[str] = field(default_factory=list)
    high_violation_constraints: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[EvolutionSuggestion] = field(default_factory=list)
    weight_adjustments: dict[str, float] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines: list[str] = [
            "# 知识演化报告",
            "",
            f"**生成时间**: {self.generated_at}",
            f"**知识库文件数**: {self.total_knowledge_files}",
            f"**已追踪文件数**: {self.tracked_files}",
            f"**Pipeline 执行次数**: {self.total_pipeline_runs}",
            "",
            "---",
            "",
        ]

        # Top effective
        if self.top_effective:
            lines.append("## 最有效的知识文件 (Top 10)")
            lines.append("")
            lines.append("| 排名 | 文件 | 引用次数 | 有效性 | 遵循率 |")
            lines.append("|------|------|----------|--------|--------|")
            for i, s in enumerate(self.top_effective[:10], 1):
                short_path = _short_path(s.file_path)
                lines.append(
                    f"| {i} | {short_path} | {s.total_references} "
                    f"| {s.effectiveness_score:.0%} | {s.compliance_rate:.0%} |"
                )
            lines.append("")

        # Least effective
        if self.least_effective:
            lines.append("## 最无效的知识文件 (Bottom 10)")
            lines.append("")
            lines.append("| 排名 | 文件 | 引用次数 | 有效性 | 违反次数 |")
            lines.append("|------|------|----------|--------|----------|")
            for i, s in enumerate(self.least_effective[:10], 1):
                short_path = _short_path(s.file_path)
                lines.append(
                    f"| {i} | {short_path} | {s.total_references} "
                    f"| {s.effectiveness_score:.0%} | {s.constraints_violated} |"
                )
            lines.append("")

        # Never used
        if self.never_used:
            lines.append(f"## 从未使用的知识文件 ({len(self.never_used)} 个)")
            lines.append("")
            for fp in self.never_used[:30]:
                lines.append(f"- {_short_path(fp)}")
            if len(self.never_used) > 30:
                lines.append(f"- ... 还有 {len(self.never_used) - 30} 个")
            lines.append("")

        # High violation constraints
        if self.high_violation_constraints:
            lines.append("## 高频违反的约束 (需加强教学)")
            lines.append("")
            lines.append("| 约束 | 来源文件 | 违反次数 | 遵循次数 |")
            lines.append("|------|----------|----------|----------|")
            for c in self.high_violation_constraints[:15]:
                lines.append(
                    f"| {c['constraint'][:60]} | {_short_path(c['file_path'])} "
                    f"| {c['violated']} | {c['followed']} |"
                )
            lines.append("")

        # Suggestions
        if self.suggestions:
            lines.append("## 改进建议")
            lines.append("")
            type_icons = {
                "boost": "UP",
                "demote": "DOWN",
                "review": "CHECK",
                "create": "NEW",
                "retire": "DEL",
            }
            for sug in self.suggestions:
                icon = type_icons.get(sug.suggestion_type, "?")
                lines.append(
                    f"- [{icon}] (P{sug.priority}) **{_short_path(sug.file_path)}**: "
                    f"{sug.reason}"
                )
            lines.append("")

        # Weight adjustments
        if self.weight_adjustments:
            lines.append("## 知识权重调整建议")
            lines.append("")
            lines.append("| 文件 | 建议权重 |")
            lines.append("|------|----------|")
            sorted_weights = sorted(
                self.weight_adjustments.items(), key=lambda x: x[1], reverse=True
            )
            for fp, w in sorted_weights[:20]:
                marker = "+" if w > 1.0 else ("-" if w < 1.0 else "=")
                lines.append(f"| {_short_path(fp)} | {marker}{w:.2f} |")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_knowledge_files": self.total_knowledge_files,
            "tracked_files": self.tracked_files,
            "total_pipeline_runs": self.total_pipeline_runs,
            "top_effective": [s.to_dict() for s in self.top_effective],
            "least_effective": [s.to_dict() for s in self.least_effective],
            "never_used": self.never_used,
            "high_violation_constraints": self.high_violation_constraints,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "weight_adjustments": self.weight_adjustments,
        }


def _short_path(file_path: str) -> str:
    """缩短知识文件路径用于显示"""
    parts = Path(file_path).parts
    # 只保留 knowledge/ 之后的路径
    try:
        idx = list(parts).index("knowledge")
        return "/".join(parts[idx:])
    except ValueError:
        # 尝试只保留最后 3 层
        if len(parts) > 3:
            return ".../" + "/".join(parts[-3:])
        return file_path


# ---------------------------------------------------------------------------
# SQLite 数据库
# ---------------------------------------------------------------------------


class KnowledgeStatsDB:
    """知识统计数据库 (SQLite)

    所有操作都用 try/except 包裹，数据库故障不影响主流程。
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path(".super-dev/knowledge-stats.db")
        self._conn: sqlite3.Connection | None = None
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
        except Exception as exc:
            _logger.warning("知识统计数据库初始化失败: %s", exc)

    def _get_conn(self) -> sqlite3.Connection | None:
        """获取数据库连接 (懒初始化)"""
        if self._conn is not None:
            return self._conn
        try:
            self._conn = sqlite3.connect(str(self.db_path), timeout=5)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            return self._conn
        except Exception as exc:
            _logger.warning("无法连接知识统计数据库: %s", exc)
            return None

    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = self._get_conn()
        if conn is None:
            return
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_stats (
                    file_path     TEXT PRIMARY KEY,
                    domain        TEXT DEFAULT '',
                    category      TEXT DEFAULT '',
                    total_references      INTEGER DEFAULT 0,
                    total_constraints_pushed INTEGER DEFAULT 0,
                    constraints_followed  INTEGER DEFAULT 0,
                    constraints_violated  INTEGER DEFAULT 0,
                    effectiveness_score   REAL DEFAULT 0.0,
                    last_used     TEXT DEFAULT '',
                    last_updated  TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS pipeline_knowledge_usage (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id    TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    phase     TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS constraint_violations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id      TEXT NOT NULL,
                    file_path   TEXT NOT NULL,
                    constraint_text TEXT NOT NULL,
                    followed    INTEGER NOT NULL DEFAULT 0,
                    timestamp   TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evolution_suggestions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id          TEXT NOT NULL,
                    suggestion_type TEXT NOT NULL,
                    file_path       TEXT NOT NULL,
                    reason          TEXT NOT NULL,
                    priority        INTEGER DEFAULT 0,
                    data_json       TEXT DEFAULT '{}',
                    timestamp       TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_usage_run ON pipeline_knowledge_usage(run_id);
                CREATE INDEX IF NOT EXISTS idx_usage_file ON pipeline_knowledge_usage(file_path);
                CREATE INDEX IF NOT EXISTS idx_violation_run ON constraint_violations(run_id);
                CREATE INDEX IF NOT EXISTS idx_violation_file ON constraint_violations(file_path);
                CREATE INDEX IF NOT EXISTS idx_suggestion_run ON evolution_suggestions(run_id);
            """
            )
            conn.commit()
        except Exception as exc:
            _logger.warning("数据库表初始化失败: %s", exc)

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ── 写入操作 ─────────────────────────────────────────────

    def record_usage(
        self, file_path: str, phase: str, run_id: str, domain: str = "", category: str = ""
    ) -> None:
        """记录一次知识引用"""
        conn = self._get_conn()
        if conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            # 更新或插入 knowledge_stats
            conn.execute(
                """
                INSERT INTO knowledge_stats (file_path, domain, category, total_references, last_used, last_updated)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    total_references = total_references + 1,
                    domain = CASE WHEN excluded.domain != '' THEN excluded.domain ELSE domain END,
                    category = CASE WHEN excluded.category != '' THEN excluded.category ELSE category END,
                    last_used = excluded.last_used,
                    last_updated = excluded.last_updated
            """,
                (file_path, domain, category, now, now),
            )

            # 插入使用记录
            conn.execute(
                """
                INSERT INTO pipeline_knowledge_usage (run_id, file_path, phase, timestamp)
                VALUES (?, ?, ?, ?)
            """,
                (run_id, file_path, phase, now),
            )

            conn.commit()
        except Exception as exc:
            _logger.debug("记录知识使用失败: %s", exc)

    def record_constraint_result(
        self, file_path: str, constraint: str, followed: bool, run_id: str
    ) -> None:
        """记录约束遵循/违反"""
        conn = self._get_conn()
        if conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            # 记录约束结果
            conn.execute(
                """
                INSERT INTO constraint_violations (run_id, file_path, constraint_text, followed, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (run_id, file_path, constraint, 1 if followed else 0, now),
            )

            # 更新统计
            if followed:
                conn.execute(
                    """
                    UPDATE knowledge_stats SET
                        constraints_followed = constraints_followed + 1,
                        last_updated = ?
                    WHERE file_path = ?
                """,
                    (now, file_path),
                )
            else:
                conn.execute(
                    """
                    UPDATE knowledge_stats SET
                        constraints_violated = constraints_violated + 1,
                        last_updated = ?
                    WHERE file_path = ?
                """,
                    (now, file_path),
                )

            conn.commit()
        except Exception as exc:
            _logger.debug("记录约束结果失败: %s", exc)

    def record_constraints_pushed(self, file_path: str, count: int) -> None:
        """记录推送的约束数量"""
        conn = self._get_conn()
        if conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO knowledge_stats (file_path, total_constraints_pushed, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    total_constraints_pushed = total_constraints_pushed + excluded.total_constraints_pushed,
                    last_updated = excluded.last_updated
            """,
                (file_path, count, now),
            )
            conn.commit()
        except Exception as exc:
            _logger.debug("记录约束推送数失败: %s", exc)

    def update_effectiveness_scores(self) -> None:
        """批量更新所有文件的有效性评分

        有效性 = (引用次数 * 0.4) + (约束遵循率 * 0.6)
        归一化到 0-1。
        """
        conn = self._get_conn()
        if conn is None:
            return
        try:
            rows = conn.execute(
                """
                SELECT file_path, total_references, constraints_followed, constraints_violated
                FROM knowledge_stats
            """
            ).fetchall()

            if not rows:
                return

            # 找到最大引用次数用于归一化
            max_refs = max((r["total_references"] for r in rows), default=1)
            max_refs = max(max_refs, 1)

            now = datetime.now(timezone.utc).isoformat()
            for row in rows:
                ref_score = min(row["total_references"] / max_refs, 1.0)
                total_constraints = row["constraints_followed"] + row["constraints_violated"]
                compliance = (
                    row["constraints_followed"] / total_constraints
                    if total_constraints > 0
                    else 0.5  # 无约束数据时中性评分
                )
                effectiveness = ref_score * 0.4 + compliance * 0.6

                conn.execute(
                    """
                    UPDATE knowledge_stats SET effectiveness_score = ?, last_updated = ?
                    WHERE file_path = ?
                """,
                    (round(effectiveness, 4), now, row["file_path"]),
                )

            conn.commit()
        except Exception as exc:
            _logger.debug("更新有效性评分失败: %s", exc)

    def save_suggestion(self, suggestion: EvolutionSuggestion, run_id: str) -> None:
        """保存改进建议"""
        conn = self._get_conn()
        if conn is None:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO evolution_suggestions
                    (run_id, suggestion_type, file_path, reason, priority, data_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    run_id,
                    suggestion.suggestion_type,
                    suggestion.file_path,
                    suggestion.reason,
                    suggestion.priority,
                    json.dumps(suggestion.data, ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()
        except Exception as exc:
            _logger.debug("保存改进建议失败: %s", exc)

    # ── 读取操作 ─────────────────────────────────────────────

    def get_file_stats(self, file_path: str) -> KnowledgeFileStats | None:
        """获取文件统计"""
        conn = self._get_conn()
        if conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT * FROM knowledge_stats WHERE file_path = ?", (file_path,)
            ).fetchone()
            if row is None:
                return None
            return KnowledgeFileStats(
                file_path=row["file_path"],
                domain=row["domain"],
                category=row["category"],
                total_references=row["total_references"],
                total_constraints_pushed=row["total_constraints_pushed"],
                constraints_followed=row["constraints_followed"],
                constraints_violated=row["constraints_violated"],
                effectiveness_score=row["effectiveness_score"],
                last_used=row["last_used"],
                last_updated=row["last_updated"],
            )
        except Exception as exc:
            _logger.debug("获取文件统计失败: %s", exc)
            return None

    def get_top_effective(self, limit: int = 20) -> list[KnowledgeFileStats]:
        """获取最有效的知识文件"""
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_stats
                WHERE total_references > 0
                ORDER BY effectiveness_score DESC, total_references DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [self._row_to_stats(r) for r in rows]
        except Exception as exc:
            _logger.debug("获取最有效文件失败: %s", exc)
            return []

    def get_least_effective(self, limit: int = 20) -> list[KnowledgeFileStats]:
        """获取最无效的知识文件（候选降权/删除）"""
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_stats
                WHERE total_references > 0
                ORDER BY effectiveness_score ASC, constraints_violated DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [self._row_to_stats(r) for r in rows]
        except Exception as exc:
            _logger.debug("获取最无效文件失败: %s", exc)
            return []

    def get_never_used(self, all_knowledge_files: list[str] | None = None) -> list[str]:
        """获取从未被使用的知识文件

        Args:
            all_knowledge_files: 知识库中所有文件路径列表。
                如果提供，返回列表中未出现在 DB 的文件；
                否则仅返回 DB 中引用次数为 0 的记录。
        """
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            if all_knowledge_files:
                tracked = set()
                rows = conn.execute(
                    "SELECT file_path FROM knowledge_stats WHERE total_references > 0"
                ).fetchall()
                for r in rows:
                    tracked.add(r["file_path"])
                return [fp for fp in all_knowledge_files if fp not in tracked]
            else:
                rows = conn.execute(
                    "SELECT file_path FROM knowledge_stats WHERE total_references = 0"
                ).fetchall()
                return [r["file_path"] for r in rows]
        except Exception as exc:
            _logger.debug("获取未使用文件失败: %s", exc)
            return []

    def get_high_violation_constraints(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取高频违反的约束"""
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                """
                SELECT
                    constraint_text,
                    file_path,
                    SUM(CASE WHEN followed = 0 THEN 1 ELSE 0 END) AS violated,
                    SUM(CASE WHEN followed = 1 THEN 1 ELSE 0 END) AS followed_count
                FROM constraint_violations
                GROUP BY constraint_text, file_path
                HAVING violated > 0
                ORDER BY violated DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [
                {
                    "constraint": r["constraint_text"],
                    "file_path": r["file_path"],
                    "violated": r["violated"],
                    "followed": r["followed_count"],
                }
                for r in rows
            ]
        except Exception as exc:
            _logger.debug("获取高频违反约束失败: %s", exc)
            return []

    def get_total_pipeline_runs(self) -> int:
        """获取 pipeline 执行总次数 (按 run_id 去重)"""
        conn = self._get_conn()
        if conn is None:
            return 0
        try:
            row = conn.execute(
                "SELECT COUNT(DISTINCT run_id) AS cnt FROM pipeline_knowledge_usage"
            ).fetchone()
            return int(row["cnt"]) if row else 0
        except Exception as exc:
            _logger.debug("获取 pipeline 执行次数失败: %s", exc)
            return 0

    def get_tracked_file_count(self) -> int:
        """获取已追踪的文件数量"""
        conn = self._get_conn()
        if conn is None:
            return 0
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM knowledge_stats WHERE total_references > 0"
            ).fetchone()
            return int(row["cnt"]) if row else 0
        except Exception as exc:
            _logger.debug("获取追踪文件数失败: %s", exc)
            return 0

    def get_recent_suggestions(self, limit: int = 20) -> list[EvolutionSuggestion]:
        """获取最近的改进建议"""
        conn = self._get_conn()
        if conn is None:
            return []
        try:
            rows = conn.execute(
                """
                SELECT * FROM evolution_suggestions
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
            return [
                EvolutionSuggestion(
                    suggestion_type=r["suggestion_type"],
                    file_path=r["file_path"],
                    reason=r["reason"],
                    priority=r["priority"],
                    data=json.loads(r["data_json"]) if r["data_json"] else {},
                )
                for r in rows
            ]
        except Exception as exc:
            _logger.debug("获取改进建议失败: %s", exc)
            return []

    @staticmethod
    def _row_to_stats(row: sqlite3.Row) -> KnowledgeFileStats:
        return KnowledgeFileStats(
            file_path=row["file_path"],
            domain=row["domain"],
            category=row["category"],
            total_references=row["total_references"],
            total_constraints_pushed=row["total_constraints_pushed"],
            constraints_followed=row["constraints_followed"],
            constraints_violated=row["constraints_violated"],
            effectiveness_score=row["effectiveness_score"],
            last_used=row["last_used"],
            last_updated=row["last_updated"],
        )


# ---------------------------------------------------------------------------
# 知识演化分析器
# ---------------------------------------------------------------------------


class KnowledgeEvolutionAnalyzer:
    """知识演化分析器 -- pipeline 执行后分析知识效果

    核心职责:
    1. 分析单次 pipeline 执行中知识的使用效果
    2. 生成跨 run 的知识演化报告
    3. 建议知识权重调整

    Parameters
    ----------
    project_dir : Path
        项目根目录。
    """

    def __init__(self, project_dir: Path | str = "."):
        self.project_dir = Path(project_dir).resolve()
        self.db = KnowledgeStatsDB(self.project_dir / ".super-dev" / "knowledge-stats.db")
        self.knowledge_dir = self.project_dir / "knowledge"

    # ── 单次分析 ──────────────────────────────────────────────

    def analyze_pipeline_run(
        self,
        run_id: str,
        knowledge_push_data: dict[str, Any] | None = None,
        quality_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """分析一次 pipeline 执行的知识使用效果

        Args:
            run_id: Pipeline 运行 ID
            knowledge_push_data: 知识推送数据，格式:
                ``{"phase": {"files": [...], "constraints": [...], ...}, ...}``
            quality_result: 质量门禁结果，格式:
                ``{"score": 85, "passed": True, "violations": [...]}``

        Returns:
            分析结果摘要
        """
        knowledge_push_data = knowledge_push_data or {}
        quality_result = quality_result or {}

        analysis: dict[str, Any] = {
            "run_id": run_id,
            "files_pushed": 0,
            "constraints_pushed": 0,
            "constraints_evaluated": 0,
            "suggestions_generated": 0,
        }

        try:
            # 1. 记录推送的知识文件
            for phase, push_info in knowledge_push_data.items():
                if not isinstance(push_info, dict):
                    continue
                files = push_info.get("files", [])
                for f in files:
                    if isinstance(f, dict):
                        fp = f.get("path", f.get("file_path", ""))
                        domain = f.get("domain", "")
                        category = f.get("category", "")
                    elif isinstance(f, str):
                        fp = f
                        domain = ""
                        category = ""
                    else:
                        continue
                    if fp:
                        self.db.record_usage(fp, phase, run_id, domain, category)
                        analysis["files_pushed"] += 1

                # 2. 记录推送的约束数
                constraints = push_info.get("constraints", [])
                analysis["constraints_pushed"] += len(constraints)

            # 3. 从质量结果中提取约束遵循/违反
            violations = quality_result.get("violations", [])
            for v in violations:
                if not isinstance(v, dict):
                    continue
                fp = v.get("source_file", v.get("file_path", ""))
                constraint = v.get("constraint", v.get("rule", ""))
                followed = v.get("followed", v.get("passed", False))
                if fp and constraint:
                    self.db.record_constraint_result(fp, constraint, followed, run_id)
                    analysis["constraints_evaluated"] += 1

            # 4. 更新有效性评分
            self.db.update_effectiveness_scores()

            # 5. 生成改进建议
            suggestions = self._generate_suggestions(run_id)
            analysis["suggestions_generated"] = len(suggestions)

            _logger.info(
                "知识演化分析完成: run=%s, files=%d, constraints=%d, suggestions=%d",
                run_id,
                analysis["files_pushed"],
                analysis["constraints_evaluated"],
                analysis["suggestions_generated"],
            )
        except Exception as exc:
            _logger.warning("知识演化分析异常: %s", exc)

        return analysis

    # ── 报告生成 ──────────────────────────────────────────────

    def generate_evolution_report(self) -> EvolutionReport:
        """生成知识演化报告"""
        now = datetime.now(timezone.utc).isoformat()

        # 统计知识库总文件数
        total_files = self._count_knowledge_files()
        all_files = self._list_knowledge_files()

        # 从数据库获取统计
        top_effective = self.db.get_top_effective(10)
        least_effective = self.db.get_least_effective(10)
        never_used = self.db.get_never_used(all_files)
        high_violations = self.db.get_high_violation_constraints(15)
        total_runs = self.db.get_total_pipeline_runs()
        tracked_count = self.db.get_tracked_file_count()

        # 权重建议
        weights = self.suggest_knowledge_weights()

        # 收集现有建议
        suggestions = self.db.get_recent_suggestions(20)

        return EvolutionReport(
            generated_at=now,
            total_knowledge_files=total_files,
            tracked_files=tracked_count,
            total_pipeline_runs=total_runs,
            top_effective=top_effective,
            least_effective=least_effective,
            never_used=never_used,
            high_violation_constraints=high_violations,
            suggestions=suggestions,
            weight_adjustments=weights,
        )

    def save_evolution_report(self, report: EvolutionReport, output_dir: str = "output") -> Path:
        """保存演化报告到文件"""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "knowledge-evolution-report.md"
        try:
            path.write_text(report.to_markdown(), encoding="utf-8")
            _logger.info("知识演化报告已保存: %s", path)

            # 同时保存 JSON
            json_path = out / "knowledge-evolution-report.json"
            json_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            _logger.warning("保存演化报告失败: %s", exc)
        return path

    # ── 知识权重 ──────────────────────────────────────────────

    def suggest_knowledge_weights(self) -> dict[str, float]:
        """基于历史数据建议知识权重调整

        Returns:
            ``{file_path: weight}`` 字典。
            weight > 1.0 表示加权（高效知识），weight < 1.0 表示降权（低效知识）。
        """
        weights: dict[str, float] = {}

        try:
            top = self.db.get_top_effective(50)
            least = self.db.get_least_effective(50)

            for stats in top:
                if stats.effectiveness_score > 0.8:
                    weights[stats.file_path] = 1.5
                elif stats.effectiveness_score > 0.6:
                    weights[stats.file_path] = 1.2

            for stats in least:
                if stats.total_references >= 5 and stats.effectiveness_score < 0.3:
                    weights[stats.file_path] = 0.5
                elif stats.total_references >= 3 and stats.effectiveness_score < 0.2:
                    weights[stats.file_path] = 0.3
        except Exception as exc:
            _logger.debug("计算知识权重失败: %s", exc)

        return weights

    def get_weight_for_file(self, file_path: str) -> float:
        """获取单个文件的推荐权重

        Returns:
            权重值，默认 1.0 (无历史数据时)。
        """
        try:
            stats = self.db.get_file_stats(file_path)
            if stats is None:
                return 1.0
            if stats.total_references < 3:
                return 1.0  # 样本太少，不调整
            if stats.effectiveness_score > 0.8:
                return 1.5
            if stats.effectiveness_score > 0.6:
                return 1.2
            if stats.effectiveness_score < 0.3 and stats.total_references >= 5:
                return 0.5
            if stats.effectiveness_score < 0.2 and stats.total_references >= 3:
                return 0.3
        except Exception:
            pass
        return 1.0

    # ── 内部方法 ──────────────────────────────────────────────

    def _generate_suggestions(self, run_id: str) -> list[EvolutionSuggestion]:
        """基于当前数据生成改进建议"""
        suggestions: list[EvolutionSuggestion] = []

        try:
            # 建议 1: 高效知识 boost
            top = self.db.get_top_effective(5)
            for s in top:
                if s.effectiveness_score > 0.8 and s.total_references >= 5:
                    sug = EvolutionSuggestion(
                        suggestion_type="boost",
                        file_path=s.file_path,
                        reason=f"高效知识 (有效性={s.effectiveness_score:.0%}, "
                        f"引用={s.total_references})，建议提高推送优先级",
                        priority=3,
                        data={
                            "effectiveness": s.effectiveness_score,
                            "references": s.total_references,
                        },
                    )
                    suggestions.append(sug)
                    self.db.save_suggestion(sug, run_id)

            # 建议 2: 低效知识 demote
            least = self.db.get_least_effective(5)
            for s in least:
                if s.effectiveness_score < 0.3 and s.total_references >= 5:
                    sug = EvolutionSuggestion(
                        suggestion_type="demote",
                        file_path=s.file_path,
                        reason=f"低效知识 (有效性={s.effectiveness_score:.0%}, "
                        f"违反={s.constraints_violated})，建议降低推送优先级或修订内容",
                        priority=4,
                        data={
                            "effectiveness": s.effectiveness_score,
                            "violations": s.constraints_violated,
                        },
                    )
                    suggestions.append(sug)
                    self.db.save_suggestion(sug, run_id)

            # 建议 3: 高频违反约束 -> 需加强教学
            violations = self.db.get_high_violation_constraints(5)
            for v in violations:
                if v["violated"] >= 3:
                    sug = EvolutionSuggestion(
                        suggestion_type="review",
                        file_path=v["file_path"],
                        reason=f"约束 '{v['constraint'][:50]}' 被违反 {v['violated']} 次，"
                        f"建议检查约束表述是否清晰、是否需要拆分或强化",
                        priority=5,
                        data={
                            "constraint": v["constraint"],
                            "violated": v["violated"],
                            "followed": v["followed"],
                        },
                    )
                    suggestions.append(sug)
                    self.db.save_suggestion(sug, run_id)

            # 建议 4: 从未使用的知识文件 -> 审查必要性
            all_files = self._list_knowledge_files()
            never_used = self.db.get_never_used(all_files)
            if len(never_used) > 10:
                # 只建议前 5 个
                for fp in never_used[:5]:
                    sug = EvolutionSuggestion(
                        suggestion_type="retire",
                        file_path=fp,
                        reason="知识文件从未被引用，建议审查是否仍有价值或需要改善标签/标题匹配",
                        priority=2,
                        data={"total_never_used": len(never_used)},
                    )
                    suggestions.append(sug)
                    self.db.save_suggestion(sug, run_id)
        except Exception as exc:
            _logger.debug("生成改进建议异常: %s", exc)

        return suggestions

    def _count_knowledge_files(self) -> int:
        """统计知识库中的 .md 文件数"""
        if not self.knowledge_dir.is_dir():
            return 0
        return sum(1 for _ in self.knowledge_dir.rglob("*.md"))

    def _list_knowledge_files(self) -> list[str]:
        """列出知识库中所有 .md 文件路径"""
        if not self.knowledge_dir.is_dir():
            return []
        return sorted(str(p) for p in self.knowledge_dir.rglob("*.md"))
