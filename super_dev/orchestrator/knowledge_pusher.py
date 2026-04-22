"""
知识推送引擎 (Knowledge Pusher)
按 pipeline 阶段自动检索并推送相关知识约束给宿主。

核心理念：
- 不是一次性灌入所有知识（太多、不精准）
- 也不是只在 discovery 检索一次（后续阶段没知识）
- 而是每个阶段按需推送精准的知识子集

调用时机：
- engine.py 每个阶段开始时调用 push(phase)
- prompt_generator.py 生成 Prompt 时调用 get_phase_knowledge(phase)
- quality_gate.py 质量检查时调用 get_quality_constraints()

开发：Excellent（11964948@qq.com）
创建时间：2026-03-28
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..utils import get_logger

# ---------------------------------------------------------------------------
# 阶段-知识域映射（核心配置）
# ---------------------------------------------------------------------------

PHASE_KNOWLEDGE_MAP: dict[str, dict[str, Any]] = {
    "research": {
        "domains": ["product", "architecture", "ai"],
        "categories": ["01-standards"],
        "max_files": 5,
        "focus": "竞品分析方法、需求分析框架、市场研究方法论",
    },
    "docs": {
        "domains": ["product", "architecture", "design", "security"],
        "categories": ["01-standards", "03-checklists"],
        "max_files": 8,
        "focus": "PRD编写标准、架构设计规范、UI/UX设计规范、安全基线",
    },
    "intelligence": {
        "domains": ["product", "architecture", "ai"],
        "categories": ["01-standards", "02-playbooks"],
        "max_files": 5,
        "focus": "联网研究方法、竞品分析框架、趋势洞察",
    },
    "drafting": {
        "domains": ["product", "architecture", "design", "security", "development"],
        "categories": ["01-standards", "03-checklists", "02-playbooks"],
        "max_files": 10,
        "focus": "PRD编写标准、架构设计规范、UI/UX设计规范、安全基线、工程规范",
    },
    "spec": {
        "domains": ["development", "architecture", "testing", "product"],
        "categories": ["01-standards", "03-checklists"],
        "max_files": 6,
        "focus": "需求拆解、任务规划、验收标准、技术选型约束",
    },
    "frontend": {
        "domains": ["frontend", "design", "development"],
        "categories": ["01-standards", "04-antipatterns", "03-checklists"],
        "max_files": 10,
        "focus": "前端框架最佳实践、组件设计、性能优化、无障碍、反模式",
        "tech_aware": True,
    },
    "backend": {
        "domains": ["backend", "data", "database", "security", "development", "api"],
        "categories": ["01-standards", "04-antipatterns", "03-checklists"],
        "max_files": 10,
        "focus": "后端框架最佳实践、数据库设计、API安全、反模式",
        "tech_aware": True,
    },
    "redteam": {
        "domains": ["security", "testing", "architecture"],
        "categories": ["01-standards", "03-checklists", "04-antipatterns"],
        "max_files": 8,
        "focus": "安全威胁建模、渗透测试清单、架构弱点、性能瓶颈",
    },
    "quality": {
        "domains": ["testing", "security", "operations"],
        "categories": ["01-standards", "03-checklists", "04-antipatterns"],
        "max_files": 8,
        "focus": "测试策略、安全检查清单、性能基准、质量门禁标准",
    },
    "qa": {
        "domains": ["testing", "security", "operations", "development"],
        "categories": ["01-standards", "03-checklists", "04-antipatterns"],
        "max_files": 8,
        "focus": "测试策略、安全检查清单、性能基准、质量门禁标准",
    },
    "delivery": {
        "domains": ["devops", "cicd", "operations"],
        "categories": ["01-standards", "02-playbooks", "03-checklists"],
        "max_files": 6,
        "focus": "CI/CD配置、部署策略、监控告警、发布检查清单",
    },
    "deployment": {
        "domains": ["devops", "cicd", "operations", "cloud-native"],
        "categories": ["01-standards", "02-playbooks", "03-checklists"],
        "max_files": 6,
        "focus": "部署策略、容器编排、基础设施即代码、发布门禁",
    },
}

# ---------------------------------------------------------------------------
# 技术栈关键词 → 文件名/内容匹配词
# ---------------------------------------------------------------------------

_TECH_KEYWORDS: dict[str, list[str]] = {
    # 前端框架
    "react": ["react", "jsx", "tsx", "next", "remix", "gatsby"],
    "next": ["next", "nextjs", "react", "ssr"],
    "vue": ["vue", "nuxt", "vite-vue"],
    "nuxt": ["nuxt", "vue", "ssr"],
    "angular": ["angular", "ng", "rxjs"],
    "svelte": ["svelte", "sveltekit"],
    "solid": ["solid", "solidjs"],
    # 后端框架
    "node": ["node", "express", "koa", "fastify", "nestjs", "javascript", "typescript"],
    "python": ["python", "fastapi", "django", "flask", "pytest", "async"],
    "go": ["golang", "go-", "gin", "echo"],
    "java": ["java", "spring", "maven", "gradle"],
    "rust": ["rust", "cargo", "actix", "tokio"],
    # 数据库
    "postgresql": ["postgresql", "postgres", "pg"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo", "nosql"],
    "redis": ["redis", "cache"],
    # 样式
    "tailwind": ["tailwind", "utility-first"],
    "sass": ["sass", "scss"],
}

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeFileInfo:
    """知识文件索引条目"""

    path: str
    filename: str
    domain: str
    category: str
    title: str
    size: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class KnowledgePush:
    """一次知识推送的结果"""

    phase: str
    files: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    antipatterns: list[str] = field(default_factory=list)
    focus_summary: str = ""
    tech_stack_filter: str = ""

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于 context.metadata 存储）"""
        return {
            "phase": self.phase,
            "files": self.files,
            "constraints": self.constraints,
            "antipatterns": self.antipatterns,
            "focus_summary": self.focus_summary,
            "tech_stack_filter": self.tech_stack_filter,
            "file_count": len(self.files),
            "constraint_count": len(self.constraints),
            "antipattern_count": len(self.antipatterns),
        }

    # ------------------------------------------------------------------
    # Prompt 注入
    # ------------------------------------------------------------------

    def to_prompt_injection(self) -> str:
        """生成可注入 Prompt 的知识约束文本

        返回结构化的 Markdown 片段，宿主可直接读取并遵守。
        """
        if not self.files and not self.constraints and not self.antipatterns:
            return ""

        lines: list[str] = []
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"## 知识推送 — {self.phase} 阶段")
        lines.append("")
        lines.append(f"> **聚焦**: {self.focus_summary}")
        if self.tech_stack_filter:
            lines.append(f"> **技术栈过滤**: {self.tech_stack_filter}")
        lines.append("")

        # 约束清单
        if self.constraints:
            lines.append("### 硬约束 (Agent Checklist)")
            lines.append("")
            lines.append("以下约束来自本地知识库，必须遵守，不得降级为可选参考：")
            lines.append("")
            for i, c in enumerate(self.constraints, 1):
                lines.append(f"{i}. {c}")
            lines.append("")

        # 反模式
        if self.antipatterns:
            lines.append("### 禁止项 (Anti-patterns)")
            lines.append("")
            lines.append("以下反模式必须避免：")
            lines.append("")
            for i, a in enumerate(self.antipatterns, 1):
                lines.append(f"{i}. ❌ {a}")
            lines.append("")

        # 知识来源
        if self.files:
            lines.append("### 知识来源文件")
            lines.append("")
            for f in self.files:
                relevance = f.get("relevance", 0)
                stars = "★" * min(int(relevance * 5), 5) if relevance else ""
                domain = f.get("domain", "")
                category = f.get("category", "")
                title = f.get("title", f.get("filename", ""))
                lines.append(f"- [{domain}/{category}] **{title}** {stars}")
                excerpt = f.get("excerpt", "")
                if excerpt:
                    # 截取前 120 字符
                    short = excerpt[:120].replace("\n", " ").strip()
                    if len(excerpt) > 120:
                        short += "..."
                    lines.append(f"  > {short}")
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 三层渐进式加载数据模型
# ---------------------------------------------------------------------------

# frontmatter 中 priority 文本 -> 数值映射
_PRIORITY_SCORES: dict[str, float] = {
    "critical": 4.0,
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}


@dataclass
class LayeredFileEntry:
    """三层加载中的单个文件条目"""

    path: str
    filename: str
    domain: str
    category: str
    title: str
    summary: str = ""
    priority: float = 2.0
    phase_trigger: list[str] = field(default_factory=list)
    tech_trigger: list[str] = field(default_factory=list)
    token_budget: int = 500
    related: list[str] = field(default_factory=list)
    content: str = ""  # L2 填充：全文或压缩后内容
    content_tokens: int = 0  # 全文预估 token 数
    summary_tokens: int = 0  # summary 预估 token 数


@dataclass
class LayeredKnowledgePush:
    """三层渐进式知识推送结果

    借鉴 Anthropic Progressive Disclosure (L1/L2/L3) 和 Manus Compaction 机制。

    L1 索引层: 所有匹配文件的 title + summary（轻量，约 80 tokens/文件）
    L2 详情层: 最相关文件的全文或压缩摘要（按 priority 排序填满 token 预算）
    L3 深度层: 关联的 playbook/case 引用（仅在需要时加载，不占预算）
    """

    phase: str
    l1_index: list[dict[str, Any]] = field(default_factory=list)
    l2_details: list[dict[str, Any]] = field(default_factory=list)
    l3_references: list[dict[str, Any]] = field(default_factory=list)
    total_token_budget: int = 4000
    l1_tokens_used: int = 0
    l2_tokens_used: int = 0
    focus_summary: str = ""
    tech_stack_filter: str = ""

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict"""
        return {
            "phase": self.phase,
            "l1_index": self.l1_index,
            "l2_details": [{k: v for k, v in d.items() if k != "content"} for d in self.l2_details],
            "l3_references": self.l3_references,
            "total_token_budget": self.total_token_budget,
            "l1_tokens_used": self.l1_tokens_used,
            "l2_tokens_used": self.l2_tokens_used,
            "l1_file_count": len(self.l1_index),
            "l2_file_count": len(self.l2_details),
            "l3_ref_count": len(self.l3_references),
            "focus_summary": self.focus_summary,
            "tech_stack_filter": self.tech_stack_filter,
        }

    def to_prompt_injection(self) -> str:
        """生成三层结构的 Prompt 注入文本"""
        if not self.l1_index and not self.l2_details:
            return ""

        lines: list[str] = []
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"## 知识推送 (Layered) — {self.phase} 阶段")
        lines.append("")
        lines.append(f"> **聚焦**: {self.focus_summary}")
        if self.tech_stack_filter:
            lines.append(f"> **技术栈过滤**: {self.tech_stack_filter}")
        lines.append(
            f"> **Token 预算**: {self.l1_tokens_used + self.l2_tokens_used}"
            f" / {self.total_token_budget}"
            f" (L1={self.l1_tokens_used}, L2={self.l2_tokens_used})"
        )
        lines.append("")

        # L1: 索引层
        if self.l1_index:
            lines.append("### L1 知识索引")
            lines.append("")
            for f in self.l1_index:
                title = f.get("title", f.get("filename", ""))
                summary = f.get("summary", "")
                domain = f.get("domain", "")
                priority = f.get("priority", "")
                lines.append(f"- **{title}** [{domain}] (priority={priority})")
                if summary:
                    short = summary[:150].replace("\n", " ").strip()
                    if len(summary) > 150:
                        short += "..."
                    lines.append(f"  > {short}")
            lines.append("")

        # L2: 详情层
        if self.l2_details:
            lines.append("### L2 知识详情")
            lines.append("")
            for f in self.l2_details:
                title = f.get("title", f.get("filename", ""))
                content = f.get("content", "")
                compressed = f.get("compressed", False)
                tag = " (compressed)" if compressed else ""
                lines.append(f"#### {title}{tag}")
                lines.append("")
                if content:
                    lines.append(content)
                    lines.append("")

        # L3: 深度引用
        if self.l3_references:
            lines.append("### L3 深度引用 (按需加载)")
            lines.append("")
            lines.append("以下文件可在需要时进一步加载：")
            lines.append("")
            for ref in self.l3_references:
                title = ref.get("title", ref.get("filename", ""))
                path = ref.get("path", "")
                reason = ref.get("reason", "")
                lines.append(f"- **{title}** — `{path}`")
                if reason:
                    lines.append(f"  关联原因: {reason}")
            lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class KnowledgePusher:
    """知识推送引擎

    按 pipeline 阶段自动检索知识库并推送精准子集。

    Parameters
    ----------
    knowledge_dir : Path
        知识库根目录（通常是 ``<project>/knowledge``）。
    tech_stack : dict | None
        技术栈信息，键包括 ``frontend``, ``backend``, ``database`` 等。
        用于在 ``tech_aware`` 阶段做过滤。
    project_description : str
        项目描述，用于相关性排序。
    """

    def __init__(
        self,
        knowledge_dir: Path,
        tech_stack: dict[str, str] | None = None,
        project_description: str = "",
    ):
        self.knowledge_dir = Path(knowledge_dir)
        self.tech_stack = tech_stack or {}
        self.project_description = project_description
        self.logger = get_logger("knowledge_pusher")

        # 缓存：phase -> KnowledgePush
        self._push_cache: dict[str, KnowledgePush] = {}

        # 知识演化分析器（按历史有效性调整推送优先级）
        self._evolution_analyzer = None
        try:
            from ..knowledge_evolution import KnowledgeEvolutionAnalyzer

            # 从 knowledge_dir 向上推断 project_dir
            project_dir = self.knowledge_dir.parent
            db_path = project_dir / ".super-dev" / "knowledge-stats.db"
            if db_path.exists() or (project_dir / ".super-dev").is_dir():
                self._evolution_analyzer = KnowledgeEvolutionAnalyzer(project_dir)
                self.logger.debug("知识演化分析器已加载")
        except Exception as exc:
            self.logger.debug("知识演化分析器加载失败（不影响推送）: %s", exc)

        # 文件索引
        self._file_index: list[KnowledgeFileInfo] = []
        if self.knowledge_dir.is_dir():
            self._file_index = self._build_index()
            self.logger.info(
                "知识文件索引构建完成",
                extra={"file_count": len(self._file_index)},
            )
        else:
            self.logger.warning(
                "知识目录不存在，知识推送将返回空结果",
                extra={"knowledge_dir": str(self.knowledge_dir)},
            )

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def push(self, phase: str, project_description: str = "") -> KnowledgePush:
        """推送指定阶段的知识

        Parameters
        ----------
        phase : str
            阶段名称，如 ``"frontend"``, ``"backend"``, ``"qa"`` 等。
        project_description : str
            本次推送可附加的项目描述（覆盖构造函数中的默认描述）。

        Returns
        -------
        KnowledgePush
            包含文件列表、约束、反模式和聚焦说明。
        """
        # 使用缓存
        if phase in self._push_cache:
            return self._push_cache[phase]

        config = PHASE_KNOWLEDGE_MAP.get(phase)
        if config is None:
            self.logger.debug(f"阶段 '{phase}' 无知识映射配置，返回空推送")
            empty = KnowledgePush(phase=phase, focus_summary="无匹配的知识映射")
            self._push_cache[phase] = empty
            return empty

        description = project_description or self.project_description

        # 1. 按领域过滤
        candidates = self._filter_by_domains(config["domains"])

        # 2. 按类别过滤
        candidates = self._filter_by_categories(candidates, config["categories"])

        # 3. 技术栈过滤（如果启用）
        tech_filter_desc = ""
        if config.get("tech_aware"):
            candidates, tech_filter_desc = self._filter_by_tech_stack(candidates)

        # 4. 相关性排序
        candidates = self._rank_by_relevance(candidates, description, config["focus"])

        # 5. 截断
        max_files = config.get("max_files", 8)
        selected = candidates[:max_files]

        # 6. 转为 dict 列表并提取摘要
        file_dicts = self._to_file_dicts(selected)

        # 7. 提取约束和反模式
        constraints = self._extract_constraints(selected)
        antipatterns = self._extract_antipatterns(selected)

        # 8. 从反模式目录补充（如果 selected 中反模式不够）
        if len(antipatterns) < 3:
            extra_ap = self._collect_extra_antipatterns(config["domains"])
            for ap in extra_ap:
                if ap not in antipatterns:
                    antipatterns.append(ap)
                if len(antipatterns) >= 10:
                    break

        result = KnowledgePush(
            phase=phase,
            files=file_dicts,
            constraints=constraints,
            antipatterns=antipatterns,
            focus_summary=config["focus"],
            tech_stack_filter=tech_filter_desc,
        )

        self._push_cache[phase] = result

        self.logger.info(
            f"知识推送完成: {phase}",
            extra={
                "phase": phase,
                "files": len(file_dicts),
                "constraints": len(constraints),
                "antipatterns": len(antipatterns),
                "tech_filter": tech_filter_desc,
            },
        )

        return result

    def get_phase_knowledge(self, phase: str) -> KnowledgePush:
        """获取指定阶段的知识推送（别名，方便 prompt_generator 调用）"""
        return self.push(phase)

    def get_quality_constraints(self) -> tuple[list[str], list[str]]:
        """获取质量阶段的约束和反模式（供 quality_gate 使用）

        Returns
        -------
        tuple[list[str], list[str]]
            (constraints, antipatterns)
        """
        qa_push = self.push("qa")
        return qa_push.constraints, qa_push.antipatterns

    def invalidate_cache(self, phase: str | None = None) -> None:
        """清除缓存

        Parameters
        ----------
        phase : str | None
            如果指定，只清除该阶段的缓存；否则清除全部。
        """
        if phase is None:
            self._push_cache.clear()
        else:
            self._push_cache.pop(phase, None)

    # ------------------------------------------------------------------
    # 三层渐进式加载 (Progressive Disclosure)
    # ------------------------------------------------------------------

    def push_layered(
        self,
        phase: str,
        description: str = "",
        token_budget: int = 4000,
    ) -> LayeredKnowledgePush:
        """三层渐进式知识加载

        借鉴:
        - Anthropic Progressive Disclosure (L1/L2/L3 三层加载)
        - Knowledge Activation 论文 (agent-optimized 摘要头)
        - Manus Compaction 机制 (token 预算内压缩)

        Parameters
        ----------
        phase : str
            Pipeline 阶段名称。
        description : str
            项目描述或当前任务描述，用于相关性匹配。
        token_budget : int
            本次推送的最大 token 预算（默认 4000）。

        Returns
        -------
        LayeredKnowledgePush
            包含 L1 索引、L2 详情、L3 引用的三层推送结果。
        """
        cache_key = f"layered_{phase}_{token_budget}"
        if cache_key in self._push_cache:
            cached = self._push_cache[cache_key]
            if isinstance(cached, LayeredKnowledgePush):
                return cached

        config = PHASE_KNOWLEDGE_MAP.get(phase)
        if config is None:
            self.logger.debug(f"阶段 '{phase}' 无知识映射配置，返回空分层推送")
            empty = LayeredKnowledgePush(
                phase=phase,
                total_token_budget=token_budget,
                focus_summary="无匹配的知识映射",
            )
            return empty

        desc = description or self.project_description

        # Step 1: 获取匹配文件（复用现有过滤/排序逻辑）
        matching_files = self._get_matching_files_for_layered(phase, desc, config)

        # Step 2: 读取 frontmatter，构建 LayeredFileEntry 列表
        entries = self._build_layered_entries(matching_files)

        # Step 3: 按 frontmatter phase_trigger 过滤（如果有 frontmatter）
        entries = self._filter_by_phase_trigger(entries, phase)

        # Step 4: 按 priority 排序
        entries.sort(key=lambda e: -e.priority)

        # Step 5: L1 索引层 — 所有匹配文件的 title + summary
        l1_index: list[dict[str, Any]] = []
        l1_tokens = 0
        for entry in entries:
            summary_tokens = self._estimate_tokens(f"{entry.title}: {entry.summary}")
            l1_index.append(
                {
                    "path": entry.path,
                    "filename": entry.filename,
                    "domain": entry.domain,
                    "category": entry.category,
                    "title": entry.title,
                    "summary": entry.summary,
                    "priority": self._priority_label(entry.priority),
                    "priority_score": entry.priority,
                    "phase_trigger": entry.phase_trigger,
                    "tech_trigger": entry.tech_trigger,
                    "token_budget": entry.token_budget,
                    "related": entry.related,
                    "summary_tokens": summary_tokens,
                }
            )
            l1_tokens += summary_tokens

        # Step 6: L2 详情层 — 最相关文件全文，填满剩余 token 预算
        remaining_budget = token_budget - l1_tokens
        l2_details: list[dict[str, Any]] = []
        l2_tokens = 0

        for entry in entries:
            if remaining_budget <= 0:
                break

            # 读取全文
            full_content = self._read_file_content(entry.path)
            if not full_content:
                continue

            file_tokens = self._estimate_tokens(full_content)

            if remaining_budget >= file_tokens:
                # 全文放入
                l2_details.append(
                    {
                        "path": entry.path,
                        "filename": entry.filename,
                        "title": entry.title,
                        "domain": entry.domain,
                        "content": full_content,
                        "tokens": file_tokens,
                        "compressed": False,
                    }
                )
                remaining_budget -= file_tokens
                l2_tokens += file_tokens
            elif remaining_budget > 200:
                # 超预算 → 压缩到剩余预算
                compressed = self._compress(full_content, remaining_budget)
                compressed_tokens = self._estimate_tokens(compressed)
                l2_details.append(
                    {
                        "path": entry.path,
                        "filename": entry.filename,
                        "title": entry.title,
                        "domain": entry.domain,
                        "content": compressed,
                        "tokens": compressed_tokens,
                        "compressed": True,
                    }
                )
                remaining_budget -= compressed_tokens
                l2_tokens += compressed_tokens

        # Step 7: L3 深度引用 — 关联的 playbook/case 仅列出路径
        l3_references = self._get_related_references(entries, l2_details)

        # 技术栈过滤描述
        tech_filter_desc = ""
        if config.get("tech_aware"):
            frontend = self.tech_stack.get("frontend", "")
            backend = self.tech_stack.get("backend", "")
            if frontend or backend:
                tech_filter_desc = f"frontend={frontend}, backend={backend}"

        result = LayeredKnowledgePush(
            phase=phase,
            l1_index=l1_index,
            l2_details=l2_details,
            l3_references=l3_references,
            total_token_budget=token_budget,
            l1_tokens_used=l1_tokens,
            l2_tokens_used=l2_tokens,
            focus_summary=config["focus"],
            tech_stack_filter=tech_filter_desc,
        )

        self._push_cache[cache_key] = result

        self.logger.info(
            f"分层知识推送完成: {phase}",
            extra={
                "phase": phase,
                "l1_files": len(l1_index),
                "l2_files": len(l2_details),
                "l3_refs": len(l3_references),
                "l1_tokens": l1_tokens,
                "l2_tokens": l2_tokens,
                "budget": token_budget,
                "tech_filter": tech_filter_desc,
            },
        )

        return result

    # ------------------------------------------------------------------
    # 分层加载辅助方法
    # ------------------------------------------------------------------

    def _get_matching_files_for_layered(
        self,
        phase: str,
        description: str,
        config: dict[str, Any],
    ) -> list[KnowledgeFileInfo]:
        """获取阶段匹配的文件列表（不截断，用于分层加载）"""
        candidates = self._filter_by_domains(config["domains"])
        candidates = self._filter_by_categories(candidates, config["categories"])
        if config.get("tech_aware"):
            candidates, _ = self._filter_by_tech_stack(candidates)
        candidates = self._rank_by_relevance(candidates, description, config["focus"])
        # 分层加载不截断，但设一个合理上限避免扫描过多文件
        return candidates[:30]

    def _build_layered_entries(self, files: list[KnowledgeFileInfo]) -> list[LayeredFileEntry]:
        """构建 LayeredFileEntry 列表，解析 frontmatter"""
        entries: list[LayeredFileEntry] = []
        for info in files:
            fm = self._parse_frontmatter(info.path)
            entry = LayeredFileEntry(
                path=info.path,
                filename=info.filename,
                domain=fm.get("domain", info.domain),
                category=fm.get("category", info.category),
                title=fm.get("title", info.title),
                summary=fm.get("summary", ""),
                priority=_PRIORITY_SCORES.get(fm.get("priority", "medium"), 2.0),
                phase_trigger=fm.get("phase_trigger", []),
                tech_trigger=fm.get("tech_trigger", []),
                token_budget=int(fm.get("token_budget", 500)),
                related=fm.get("related", []),
            )
            # 如果 frontmatter 没有 summary，从内容提取
            if not entry.summary:
                entry.summary = self._extract_excerpt(Path(info.path), max_chars=200)
            entry.summary_tokens = self._estimate_tokens(f"{entry.title}: {entry.summary}")
            entries.append(entry)
        return entries

    def _filter_by_phase_trigger(
        self, entries: list[LayeredFileEntry], phase: str
    ) -> list[LayeredFileEntry]:
        """按 frontmatter 中的 phase_trigger 过滤

        如果文件没有 phase_trigger（无 frontmatter），保留不过滤。
        如果有 phase_trigger 但不包含当前 phase，降低优先级但不移除。
        """
        boosted: list[LayeredFileEntry] = []
        rest: list[LayeredFileEntry] = []
        for entry in entries:
            if not entry.phase_trigger:
                # 无 frontmatter，保持原位
                boosted.append(entry)
            elif phase in entry.phase_trigger:
                # 匹配阶段，提升优先级
                entry.priority += 1.0
                boosted.append(entry)
            else:
                # 不匹配但不移除，降低优先级
                entry.priority -= 0.5
                rest.append(entry)
        return boosted + rest

    def _parse_frontmatter(self, filepath: str) -> dict[str, Any]:
        """解析文件的 YAML frontmatter"""
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                first_line = f.readline().strip()
                if first_line != "---":
                    return {}
                fm_lines: list[str] = []
                for line in f:
                    if line.strip() == "---":
                        break
                    fm_lines.append(line)
                if not fm_lines:
                    return {}
                fm_text = "".join(fm_lines)
                try:
                    data = yaml.safe_load(fm_text)
                    return data if isinstance(data, dict) else {}
                except yaml.YAMLError:
                    return {}
        except OSError:
            return {}

    def _read_file_content(self, filepath: str) -> str:
        """读取文件全部内容，跳过 frontmatter"""
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            return ""

        # 跳过 YAML frontmatter
        if content.startswith("---"):
            end = content.find("\n---", 3)
            if end > 0:
                content = content[end + 4 :].lstrip("\n")

        return content

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数

        简单实现：中文约 1.5 字符/token，英文约 4 字符/token。
        混合内容取折中值。
        """
        if not text:
            return 0
        # 计算中文字符数
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        # 非中文字符数
        other_chars = len(text) - chinese_chars
        # 中文约 1.5 字符/token，英文约 4 字符/token
        chinese_tokens = chinese_chars / 1.5
        english_tokens = other_chars / 4.0
        return max(1, int(chinese_tokens + english_tokens))

    def _compress(self, content: str, max_tokens: int) -> str:
        """压缩知识内容到 token 预算内

        Manus Compaction 策略:
        1. 优先保留 Agent Checklist 部分
        2. 保留所有 ## 标题
        3. 保留代码块（示例代码有高价值）
        4. 截断长段落文字
        """
        if self._estimate_tokens(content) <= max_tokens:
            return content

        lines = content.split("\n")
        sections: list[tuple[str, list[str]]] = []  # (section_type, lines)
        current_type = "text"
        current_lines: list[str] = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # 代码块边界
            if stripped.startswith("```"):
                if in_code_block:
                    current_lines.append(line)
                    sections.append(("code", list(current_lines)))
                    current_lines = []
                    in_code_block = False
                    current_type = "text"
                else:
                    if current_lines:
                        sections.append((current_type, list(current_lines)))
                    current_lines = [line]
                    in_code_block = True
                    current_type = "code"
                continue

            if in_code_block:
                current_lines.append(line)
                continue

            # 检测 Agent Checklist 区域
            if any(
                marker in stripped for marker in ("Agent Checklist", "## Checklist", "## 检查清单")
            ):
                if current_lines:
                    sections.append((current_type, list(current_lines)))
                current_lines = [line]
                current_type = "checklist"
                continue

            # 标题行
            if stripped.startswith("## ") or stripped.startswith("# "):
                if current_lines:
                    sections.append((current_type, list(current_lines)))
                current_lines = [line]
                current_type = "heading"
                continue

            # 普通文本
            if current_type == "heading":
                sections.append((current_type, list(current_lines)))
                current_lines = [line]
                current_type = "text"
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_type, list(current_lines)))

        # 按优先级组装，直到填满 token 预算
        # 优先级: checklist > heading > code > text
        priority_order = {"checklist": 0, "heading": 1, "code": 2, "text": 3}
        sorted_sections = sorted(
            enumerate(sections),
            key=lambda x: (priority_order.get(x[1][0], 4), x[0]),
        )

        selected_indices: set[int] = set()
        current_tokens = 0

        for idx, (section_type, section_lines) in sorted_sections:
            section_text = "\n".join(section_lines)
            section_tokens = self._estimate_tokens(section_text)

            if current_tokens + section_tokens <= max_tokens:
                selected_indices.add(idx)
                current_tokens += section_tokens
            elif section_type == "text" and max_tokens - current_tokens > 50:
                # 对文本段落做截断
                budget_left = max_tokens - current_tokens
                truncated = self._truncate_to_tokens(section_text, budget_left)
                sections[idx] = (section_type, [truncated])
                selected_indices.add(idx)
                current_tokens = max_tokens
                break

        # 按原始顺序输出
        result_lines: list[str] = []
        for idx in sorted(selected_indices):
            _, section_lines = sections[idx]
            result_lines.extend(section_lines)

        compressed = "\n".join(result_lines).strip()
        if not compressed:
            # 至少返回前 N 字符
            char_budget = max_tokens * 3  # 粗略估算
            compressed = content[:char_budget].strip()

        return compressed

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """将文本截断到指定 token 数"""
        if self._estimate_tokens(text) <= max_tokens:
            return text
        # 二分查找截断位置
        low, high = 0, len(text)
        while low < high - 1:
            mid = (low + high) // 2
            if self._estimate_tokens(text[:mid]) <= max_tokens:
                low = mid
            else:
                high = mid
        return text[:low].rstrip() + "..."

    def _get_related_references(
        self,
        all_entries: list[LayeredFileEntry],
        l2_details: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """获取 L3 深度引用：L2 文件中 related 指向的文件"""
        l2_paths = {d["path"] for d in l2_details}
        # 收集 L2 文件的 related 列表
        related_ids: set[str] = set()
        for entry in all_entries:
            if entry.path in l2_paths and entry.related:
                related_ids.update(entry.related)

        if not related_ids:
            # 补充：从 playbooks/cases 目录中找与 L2 同 domain 的文件
            return self._get_domain_playbook_refs(l2_details)

        references: list[dict[str, Any]] = []
        for info in self._file_index:
            stem = Path(info.filename).stem.lower()
            if stem in related_ids and info.path not in l2_paths:
                references.append(
                    {
                        "path": info.path,
                        "filename": info.filename,
                        "title": info.title,
                        "domain": info.domain,
                        "category": info.category,
                        "reason": "被 L2 文件的 related 字段引用",
                    }
                )
                if len(references) >= 10:
                    break

        # 补充 playbook/case 引用
        references.extend(
            self._get_domain_playbook_refs(
                l2_details, exclude={r["path"] for r in references} | l2_paths
            )
        )

        return references[:15]

    def _get_domain_playbook_refs(
        self,
        l2_details: list[dict[str, Any]],
        exclude: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """从 playbooks/cases 目录中找与 L2 同 domain 的文件"""
        exclude = exclude or set()
        l2_domains = {d.get("domain", "") for d in l2_details}
        references: list[dict[str, Any]] = []

        for info in self._file_index:
            if info.category in ("02-playbooks", "05-cases"):
                if info.domain in l2_domains and info.path not in exclude:
                    references.append(
                        {
                            "path": info.path,
                            "filename": info.filename,
                            "title": info.title,
                            "domain": info.domain,
                            "category": info.category,
                            "reason": f"同领域 ({info.domain}) 的 {info.category} 资源",
                        }
                    )
                    if len(references) >= 5:
                        break

        return references

    @staticmethod
    def _priority_label(score: float) -> str:
        """数值优先级转标签"""
        if score >= 3.5:
            return "critical"
        elif score >= 2.5:
            return "high"
        elif score >= 1.5:
            return "medium"
        return "low"

    def get_all_phases_summary(self) -> dict[str, dict[str, Any]]:
        """获取所有阶段的知识映射摘要（不触发文件读取）"""
        summary: dict[str, dict[str, Any]] = {}
        for phase_name, config in PHASE_KNOWLEDGE_MAP.items():
            domain_file_counts: dict[str, int] = {}
            for info in self._file_index:
                if info.domain in config["domains"]:
                    domain_file_counts[info.domain] = domain_file_counts.get(info.domain, 0) + 1
            summary[phase_name] = {
                "domains": config["domains"],
                "categories": config["categories"],
                "max_files": config.get("max_files", 8),
                "focus": config["focus"],
                "tech_aware": config.get("tech_aware", False),
                "available_files": sum(domain_file_counts.values()),
                "domain_breakdown": domain_file_counts,
            }
        return summary

    # ------------------------------------------------------------------
    # 索引构建
    # ------------------------------------------------------------------

    def _build_index(self) -> list[KnowledgeFileInfo]:
        """扫描知识目录，构建文件索引"""
        index: list[KnowledgeFileInfo] = []
        if not self.knowledge_dir.is_dir():
            return index

        for md_path in sorted(self.knowledge_dir.rglob("*.md")):
            # 跳过隐藏目录
            if any(part.startswith(".") for part in md_path.parts):
                continue

            rel = md_path.relative_to(self.knowledge_dir)
            parts = rel.parts

            # 解析 domain 和 category
            domain = parts[0] if len(parts) >= 1 else ""
            category = ""
            if len(parts) >= 2:
                # 如果第二层是标准子目录（01-standards 等），设为 category
                second = parts[1]
                if re.match(r"^\d{2}-", second):
                    category = second
                else:
                    # 可能是领域根目录下的文件
                    category = ""

            title = self._extract_title(md_path)
            tags = self._extract_tags_from_path(md_path, domain, category)

            try:
                size = md_path.stat().st_size
            except OSError:
                size = 0

            index.append(
                KnowledgeFileInfo(
                    path=str(md_path),
                    filename=md_path.name,
                    domain=domain,
                    category=category,
                    title=title,
                    size=size,
                    tags=tags,
                )
            )

        return index

    def _extract_title(self, path: Path) -> str:
        """从文件头部提取标题（# 开头的行）"""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# "):
                        return line[2:].strip()
                    # 跳过空行和 YAML front-matter
                    if line == "---":
                        continue
                    if line and not line.startswith("#"):
                        break
        except OSError:
            pass
        # 使用文件名
        return path.stem.replace("-", " ").replace("_", " ").title()

    def _extract_tags_from_path(self, path: Path, domain: str, category: str) -> list[str]:
        """从文件路径和名称提取标签"""
        tags: list[str] = []
        name_lower = path.stem.lower()

        # 域名作为标签
        if domain:
            tags.append(domain)
        if category:
            tags.append(category)

        # 从文件名提取关键词
        for part in re.split(r"[-_]", name_lower):
            if len(part) > 2 and part not in ("the", "and", "for", "with", "complete"):
                tags.append(part)

        return tags

    # ------------------------------------------------------------------
    # 过滤
    # ------------------------------------------------------------------

    def _filter_by_domains(self, domains: list[str]) -> list[KnowledgeFileInfo]:
        """按领域过滤"""
        result: list[KnowledgeFileInfo] = []
        domain_set = set(domains)
        for info in self._file_index:
            if info.domain in domain_set:
                result.append(info)
        return result

    def _filter_by_categories(
        self, candidates: list[KnowledgeFileInfo], categories: list[str]
    ) -> list[KnowledgeFileInfo]:
        """按类别过滤

        如果文件没有类别（域根目录下的文件），也允许通过。
        """
        category_set = set(categories)
        result: list[KnowledgeFileInfo] = []
        for info in candidates:
            if not info.category or info.category in category_set:
                result.append(info)
        return result

    def _filter_by_tech_stack(
        self, candidates: list[KnowledgeFileInfo]
    ) -> tuple[list[KnowledgeFileInfo], str]:
        """根据技术栈过滤

        React 项目只推 React 相关知识，不推 Vue/Angular。
        Python 后端只推 Python/FastAPI 知识，不推 Java/Go。

        Returns
        -------
        tuple[list[KnowledgeFileInfo], str]
            (过滤后的候选列表, 过滤描述)
        """
        frontend = self.tech_stack.get("frontend", "").lower()
        backend = self.tech_stack.get("backend", "").lower()
        database = self.tech_stack.get("database", "").lower()

        # 收集本项目的正面关键词
        positive_keywords: set[str] = set()
        for tech_val in [frontend, backend, database]:
            if tech_val:
                kws = _TECH_KEYWORDS.get(tech_val, [])
                positive_keywords.update(kws)
                positive_keywords.add(tech_val)

        # 收集排除关键词（其他竞争技术的独有关键词）
        exclude_keywords: set[str] = set()
        # 前端互斥
        frontend_families = {
            "react": {"vue", "angular", "svelte"},
            "next": {"vue", "nuxt", "angular", "svelte"},
            "vue": {"react", "angular", "svelte", "next", "remix", "gatsby"},
            "nuxt": {"react", "angular", "svelte", "next", "remix", "gatsby"},
            "angular": {"react", "vue", "svelte", "next", "nuxt"},
            "svelte": {"react", "vue", "angular", "next", "nuxt"},
        }
        if frontend in frontend_families:
            exclude_keywords.update(frontend_families[frontend])

        # 后端互斥
        backend_families = {
            "node": {"django", "flask", "spring", "gin"},
            "python": {"express", "koa", "nestjs", "spring", "gin"},
            "go": {"express", "django", "spring", "flask"},
            "java": {"express", "django", "flask", "gin"},
            "rust": {"express", "django", "spring", "flask", "gin"},
        }
        if backend in backend_families:
            exclude_keywords.update(backend_families[backend])

        # 如果没有有效的技术栈信息，不做过滤
        if not positive_keywords:
            return candidates, ""

        filtered: list[KnowledgeFileInfo] = []
        for info in candidates:
            name_lower = info.filename.lower()
            tags_lower = {t.lower() for t in info.tags}
            combined = name_lower + " " + " ".join(tags_lower)

            # 如果文件名包含排除关键词（且不包含正面关键词），跳过
            has_exclude = any(ek in combined for ek in exclude_keywords)
            has_positive = any(pk in combined for pk in positive_keywords)

            if has_exclude and not has_positive:
                continue

            filtered.append(info)

        filter_desc = f"frontend={frontend}, backend={backend}" if (frontend or backend) else ""
        return filtered, filter_desc

    # ------------------------------------------------------------------
    # 排序
    # ------------------------------------------------------------------

    def _rank_by_relevance(
        self,
        candidates: list[KnowledgeFileInfo],
        description: str,
        focus: str,
    ) -> list[KnowledgeFileInfo]:
        """按相关性排序

        评分依据：
        1. 文件名 / 标签与 focus 关键词的匹配度
        2. 文件名 / 标签与 project_description 的匹配度
        3. 类别优先级（standards > checklists > antipatterns > playbooks > cases）
        4. 文件大小（适中的文件更有价值）
        """
        focus_keywords = self._tokenize(focus)
        desc_keywords = self._tokenize(description) if description else set()

        scored: list[tuple[float, KnowledgeFileInfo]] = []

        for info in candidates:
            score = 0.0
            searchable = info.filename.lower() + " " + info.title.lower()
            searchable += " " + " ".join(t.lower() for t in info.tags)

            # focus 关键词匹配（权重高）
            for kw in focus_keywords:
                if kw in searchable:
                    score += 3.0

            # description 关键词匹配
            for kw in desc_keywords:
                if kw in searchable:
                    score += 1.5

            # 技术栈正面关键词匹配
            frontend = self.tech_stack.get("frontend", "").lower()
            backend = self.tech_stack.get("backend", "").lower()
            for tech_val in [frontend, backend]:
                if tech_val:
                    tech_kws = _TECH_KEYWORDS.get(tech_val, [tech_val])
                    for tk in tech_kws:
                        if tk in searchable:
                            score += 2.0
                            break

            # 类别优先级
            category_scores = {
                "01-standards": 2.0,
                "03-checklists": 1.8,
                "04-antipatterns": 1.5,
                "02-playbooks": 1.2,
                "05-cases": 0.8,
                "06-glossary": 0.5,
            }
            score += category_scores.get(info.category, 1.0)

            # 文件大小适中（5KB-100KB 最佳）
            if 5000 <= info.size <= 100000:
                score += 0.5
            elif info.size > 100000:
                score += 0.2  # 大文件仍有价值但提取成本高

            # 按历史有效性调整推送优先级（知识演化加权）
            if self._evolution_analyzer is not None:
                try:
                    weight = self._evolution_analyzer.get_weight_for_file(info.path)
                    score *= weight
                except Exception:
                    pass

            scored.append((score, info))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [info for _, info in scored]

    def _tokenize(self, text: str) -> set[str]:
        """将文本分词为关键词集合"""
        if not text:
            return set()
        # 中文按字/词，英文按空格和分隔符
        tokens: set[str] = set()
        # 英文 token
        for word in re.split(r"[\s,;/、，；]+", text.lower()):
            word = re.sub(r"[^\w\u4e00-\u9fff]", "", word)
            if len(word) > 1:
                tokens.add(word)
        # 中文 2-gram
        chinese_chars = re.findall(r"[\u4e00-\u9fff]+", text)
        for segment in chinese_chars:
            for i in range(len(segment) - 1):
                tokens.add(segment[i : i + 2])
        return tokens

    # ------------------------------------------------------------------
    # 文件 dict 转换
    # ------------------------------------------------------------------

    def _to_file_dicts(self, files: list[KnowledgeFileInfo]) -> list[dict[str, Any]]:
        """将 KnowledgeFileInfo 转为 dict 列表，附带摘要"""
        result: list[dict[str, Any]] = []
        for info in files:
            excerpt = self._extract_excerpt(Path(info.path))
            # 计算粗略 relevance 分数 (0-1)
            relevance = min(1.0, (info.size / 50000) + 0.3) if info.size > 0 else 0.3
            result.append(
                {
                    "path": info.path,
                    "filename": info.filename,
                    "domain": info.domain,
                    "category": info.category,
                    "title": info.title,
                    "relevance": round(relevance, 2),
                    "excerpt": excerpt,
                    "tags": info.tags,
                }
            )
        return result

    def _extract_excerpt(self, path: Path, max_chars: int = 300) -> str:
        """提取文件开头的摘要文本"""
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars + 200)
        except OSError:
            return ""

        # 跳过 YAML front-matter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3 :]

        # 跳过标题行
        lines = content.split("\n")
        text_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            text_lines.append(stripped)
            if sum(len(tl) for tl in text_lines) > max_chars:
                break

        return " ".join(text_lines)[:max_chars]

    # ------------------------------------------------------------------
    # 约束提取
    # ------------------------------------------------------------------

    def _extract_constraints(self, files: list[KnowledgeFileInfo]) -> list[str]:
        """从知识文件中提取 Agent Checklist 硬约束"""
        constraints: list[str] = []
        seen: set[str] = set()

        for info in files:
            path = Path(info.path)
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # 提取 "Agent Checklist" 区域的 checkbox 项
            for marker in ("Agent Checklist", "## Checklist", "## 检查清单"):
                idx = content.find(marker)
                if idx < 0:
                    continue
                section = content[idx : idx + 3000]
                for line in section.split("\n"):
                    line = line.strip()
                    if line.startswith("- [ ]") or line.startswith("- [x]"):
                        item = line[5:].strip()
                        if item and item not in seen:
                            seen.add(item)
                            constraints.append(item)
                    # 到下一个 ## 标题时停止
                    if line.startswith("## ") and line != marker and constraints:
                        break

            if len(constraints) >= 25:
                break

        return constraints[:25]

    # 反模式文件中常见的非反模式标题（需过滤掉）
    _AP_NOISE_TITLES: set[str] = {
        "描述",
        "错误示例",
        "正确示例",
        "检测方法",
        "修复步骤",
        "agent checklist",
        "问题代码",
        "修复代码",
        "问题",
        "解决方案",
        "示例",
        "说明",
        "参考",
        "目录",
        "概述",
        "简介",
        "总结",
        "背景",
        "原因",
        "影响",
        "建议",
        "前言",
    }

    def _extract_antipatterns(self, files: list[KnowledgeFileInfo]) -> list[str]:
        """从反模式文件中提取禁止项"""
        antipatterns: list[str] = []
        seen: set[str] = set()

        for info in files:
            # 只从 04-antipatterns 下的文件提取
            if info.category != "04-antipatterns":
                continue
            path = Path(info.path)
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # 提取反模式条目：通常以 ### 或 ** 标记
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # ### 反模式名称（至少 6 个字符，排除噪声标题）
                if line.startswith("### ") and len(line) > 8:
                    item = line[4:].strip()
                    if (
                        item
                        and item not in seen
                        and not item.startswith("#")
                        and item.lower() not in self._AP_NOISE_TITLES
                        and len(item) > 3
                    ):
                        seen.add(item)
                        antipatterns.append(item)
                # - **反模式名称**: 描述（至少 4 字符）
                match = re.match(r"^[-*]\s*\*\*(.+?)\*\*", line)
                if match:
                    item = match.group(1).strip()
                    if (
                        item
                        and item not in seen
                        and item.lower() not in self._AP_NOISE_TITLES
                        and len(item) > 3
                    ):
                        seen.add(item)
                        antipatterns.append(item)

            if len(antipatterns) >= 15:
                break

        return antipatterns[:15]

    def _collect_extra_antipatterns(self, domains: list[str]) -> list[str]:
        """从指定域的 04-antipatterns 目录补充反模式"""
        antipatterns: list[str] = []
        seen: set[str] = set()

        for info in self._file_index:
            if info.domain not in domains:
                continue
            if info.category != "04-antipatterns":
                continue
            path = Path(info.path)
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("### ") and len(line) > 8:
                    item = line[4:].strip()
                    if (
                        item
                        and item not in seen
                        and item.lower() not in self._AP_NOISE_TITLES
                        and len(item) > 3
                    ):
                        seen.add(item)
                        antipatterns.append(item)
                match = re.match(r"^[-*]\s*\*\*(.+?)\*\*", line)
                if match:
                    item = match.group(1).strip()
                    if (
                        item
                        and item not in seen
                        and item.lower() not in self._AP_NOISE_TITLES
                        and len(item) > 3
                    ):
                        seen.add(item)
                        antipatterns.append(item)

                if len(antipatterns) >= 10:
                    return antipatterns

        return antipatterns
