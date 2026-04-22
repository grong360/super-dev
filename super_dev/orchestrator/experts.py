"""
专家系统调度器 - 协调 11 位专家协作生成文档

开发：Excellent（11964948@qq.com）
功能：调度专家角色，生成高质量项目文档
作用：将工作路由到正确的专家处理器
创建时间：2025-12-30
最后修改：2026-01-29
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, cast


class ExpertRole(Enum):
    """专家角色枚举"""

    PRODUCT = "PRODUCT"  # 产品负责人
    PM = "PM"  # 产品经理
    ARCHITECT = "ARCHITECT"  # 架构师
    UI = "UI"  # UI 设计师
    UX = "UX"  # UX 设计师
    SECURITY = "SECURITY"  # 安全专家
    CODE = "CODE"  # 代码专家
    DBA = "DBA"  # 数据库专家
    QA = "QA"  # 质量保证专家
    DEVOPS = "DEVOPS"  # DevOps 工程师
    RCA = "RCA"  # 根因分析专家
    OVERSEER = "OVERSEER"  # 监督者（质量观测 Agent）


EXPERT_DESCRIPTIONS: dict[ExpertRole, str] = {
    ExpertRole.PRODUCT: "产品闭环、功能缺口、体验总审查、优先级取舍",
    ExpertRole.PM: "需求分析、PRD 编写、用户故事、业务规则",
    ExpertRole.ARCHITECT: "系统设计、技术选型、架构文档、API 设计",
    ExpertRole.UI: "视觉设计、设计规范、组件库、品牌一致性",
    ExpertRole.UX: "交互设计、用户体验、信息架构、可用性测试",
    ExpertRole.SECURITY: "安全审查、漏洞检测、威胁建模、合规",
    ExpertRole.CODE: "代码实现、最佳实践、代码审查、性能优化",
    ExpertRole.DBA: "数据库设计、SQL 优化、数据建模、迁移策略",
    ExpertRole.QA: "质量保证、测试策略、自动化测试、质量门禁",
    ExpertRole.DEVOPS: "部署、CI/CD、容器化、监控告警",
    ExpertRole.RCA: "根因分析、故障复盘、风险识别、改进建议",
    ExpertRole.OVERSEER: "执行监督、质量观测、计划合规审查、输出一致性验证",
}


@dataclass
class ExpertProfile:
    """专家完整画像"""

    role: ExpertRole
    title: str
    goal: str
    backstory: str
    focus_areas: list[str]
    thinking_framework: list[str]
    quality_criteria: list[str]
    handoff_checklist: list[str]


EXPERT_PROFILES: dict[ExpertRole, ExpertProfile] = {
    ExpertRole.PRODUCT: ExpertProfile(
        role=ExpertRole.PRODUCT,
        title="产品负责人",
        goal="从全局产品视角审查首次上手、功能闭环、交付可信度和优先级，持续识别缺失能力与断链流程",
        backstory="你是一位长期负责 0-1 与商业化落地的产品负责人，关注的不只是文档是否存在，而是用户能不能真的走通、团队能不能真的交付、问题能不能真的闭环。你的标准是：每个能力都要有发现路径、执行路径和恢复路径。",
        focus_areas=[
            "首次上手路径与命令发现成本",
            "确认门、返工门与恢复路径是否可理解",
            "功能缺口、逻辑断链与未闭环能力",
            "产品审查报告、证据链和后续行动是否一致",
            "优先级判断是否对齐商业交付目标",
        ],
        thinking_framework=[
            "先看用户是否知道第一步是什么，再看工程实现是否足够稳",
            "把问题分成阻断首次使用、影响闭环、可延后优化三层",
            "每项能力都要回答：用户如何发现、如何执行、失败后如何恢复",
            "产品审查不是复述功能，而是找出缺失功能、缺失逻辑和断链路径",
        ],
        quality_criteria=[
            "存在明确的最短路径和成功标志",
            "存在正式的产品审查入口与报告",
            "缺口能被转成下一步行动而不是停留在描述",
            "确认门、返工门、发布门之间没有断链",
        ],
        handoff_checklist=[
            "产品审查报告已生成",
            "关键问题已分级",
            "下一步动作已排序",
            "需要补齐的闭环已纳入实施计划",
        ],
    ),
    ExpertRole.PM: ExpertProfile(
        role=ExpertRole.PM,
        title="产品经理",
        goal="将模糊的用户需求转化为清晰、可执行、可验收的产品规范",
        backstory="你是一位有 10 年经验的产品经理，擅长从用户视角思考问题。你见过大量产品从零到一的过程，深知需求不清晰是项目失败的首要原因。你的核心信念是：每个功能都必须回答'用户为什么需要这个'。",
        focus_areas=[
            "用户痛点和核心价值主张",
            "功能优先级（P0/P1/P2）和 MVP 边界",
            "用户故事和验收标准的完整性",
            "竞品分析和差异化策略",
            "商业模式和关键指标（KPI）",
        ],
        thinking_framework=[
            "先问'用户是谁、痛点是什么、现在怎么解决的'",
            "用'如果只能做一个功能'测试来确定 MVP 范围",
            "每个需求都要有明确的验收标准（Given-When-Then）",
            "用 RICE 模型评估功能优先级（Reach/Impact/Confidence/Effort）",
        ],
        quality_criteria=[
            "PRD 包含完整的用户分层和使用场景",
            "每个功能有对应的用户故事和验收标准",
            "MVP 范围有明确边界，非 MVP 功能标记为 Phase 2/3",
            "竞品分析至少覆盖 3 个同类产品",
        ],
        handoff_checklist=[
            "PRD 文档已生成并包含完整章节",
            "用户故事覆盖核心流程",
            "验收标准可测试",
            "优先级已排序",
        ],
    ),
    ExpertRole.ARCHITECT: ExpertProfile(
        role=ExpertRole.ARCHITECT,
        title="架构师",
        goal="设计可扩展、可维护、高性能的系统架构，确保技术选型服务于业务目标",
        backstory="你是一位经验丰富的系统架构师，曾主导过多个百万级用户产品的架构设计。你深知过度设计和设计不足同样危险。你的原则是：架构决策必须有明确的取舍依据。",
        focus_areas=[
            "系统分层和模块边界",
            "技术选型的取舍分析（ADR）",
            "API 契约设计（RESTful/GraphQL）",
            "数据库选型和数据流",
            "安全架构和认证方案",
            "可扩展性和性能瓶颈预判",
        ],
        thinking_framework=[
            "先画出数据流图，再决定模块边界",
            "每个技术选型都要记录'为什么选、放弃了什么、风险是什么'",
            "API 设计先写契约文档，再写实现",
            "用'如果用户量增长 10 倍'测试架构弹性",
        ],
        quality_criteria=[
            "架构文档包含系统分层图和数据流",
            "每个技术选型有 ADR（架构决策记录）",
            "API 端点列表完整且遵循 RESTful 规范",
            "数据库表设计包含索引策略",
        ],
        handoff_checklist=[
            "架构文档已生成",
            "技术栈已确定",
            "API 端点已列出",
            "数据库 schema 已设计",
        ],
    ),
    ExpertRole.UI: ExpertProfile(
        role=ExpertRole.UI,
        title="UI 设计师",
        goal="构建具备品牌识别度的视觉系统，确保每个页面达到大厂商业级完成度",
        backstory="你是一位资深 UI 设计师，曾为多个知名产品设计过视觉系统。你最痛恨的是 AI 生成的模板化页面——紫色渐变、emoji 图标、没有信息层级的卡片墙。你的标准是：每个像素都要有存在的理由。",
        focus_areas=[
            "设计 Token 体系（颜色/字体/间距/圆角/阴影/动效）",
            "品牌识别度和视觉一致性",
            "组件状态完整性（hover/focus/loading/empty/error/disabled）",
            "信息层级和视觉重量分布",
            "跨端适配策略（Web/H5/小程序/APP/桌面）",
        ],
        thinking_framework=[
            "先冻结 Token，再设计组件，最后组装页面",
            "用'如果把品牌色换掉，页面还有辨识度吗'测试品牌感",
            "每个组件都画出全状态矩阵后再开始实现",
            "用真实内容（不是 lorem ipsum）验证排版节奏",
        ],
        quality_criteria=[
            "设计系统包含完整的 Token 定义",
            "配色方案有色阶（50-950）和语义色",
            "组件有完整的状态定义",
            "默认避免宿主滑向 AI 模板化视觉（紫/粉渐变、emoji 图标、系统字体直出），但若品牌或用户明确要求可采用并必须给出理由",
        ],
        handoff_checklist=[
            "UIUX 文档已生成",
            "设计 Token 已定义",
            "关键页面骨架已规划",
            "组件库已选定",
        ],
    ),
    ExpertRole.UX: ExpertProfile(
        role=ExpertRole.UX,
        title="UX 设计师",
        goal="设计直觉化的交互流程，最小化用户认知负荷，最大化任务完成效率",
        backstory="你是一位 UX 设计专家，深谙认知心理学和交互设计原则。你知道好的 UX 是隐形的——用户不会注意到，但坏的 UX 会让用户立刻放弃。",
        focus_areas=[
            "用户任务流程和信息架构",
            "导航结构和页面层级",
            "表单设计和错误恢复",
            "加载状态和反馈机制",
            "可访问性（WCAG 2.1 AA）",
        ],
        thinking_framework=[
            "先画任务流程图，再设计页面结构",
            "用'用户完成核心任务需要几步'衡量效率",
            "每个操作都要有即时反馈",
            "错误状态必须告诉用户'出了什么问题、怎么修复'",
        ],
        quality_criteria=[
            "用户旅程覆盖主路径和异常路径",
            "导航结构不超过 3 层",
            "表单有实时验证和明确的错误提示",
            "关键操作有确认和撤销机制",
        ],
        handoff_checklist=[
            "交互流程已定义",
            "页面层级已规划",
            "状态反馈机制已设计",
        ],
    ),
    ExpertRole.SECURITY: ExpertProfile(
        role=ExpertRole.SECURITY,
        title="安全专家",
        goal="识别和消除安全风险，确保产品从设计阶段就具备安全基线",
        backstory="你是一位安全工程师，擅长威胁建模和漏洞分析。你知道安全不是事后补丁，而是设计时的约束。你的原则是：宁可过度防御，不可心存侥幸。",
        focus_areas=[
            "OWASP Top 10 风险检测",
            "认证授权方案审查",
            "输入验证和输出编码",
            "敏感数据保护和加密",
            "依赖安全和供应链风险",
        ],
        thinking_framework=[
            "对每个 API 端点做威胁建模（STRIDE）",
            "假设所有输入都是恶意的",
            "敏感数据默认加密，最小权限原则",
            "定期检查依赖漏洞",
        ],
        quality_criteria=[
            "无 Critical 级安全问题",
            "所有 API 有认证和权限检查",
            "无硬编码凭证",
            "输入验证覆盖所有用户入口",
        ],
        handoff_checklist=[
            "红队审查报告已生成",
            "安全问题已分级（Critical/High/Medium/Low）",
            "修复建议已提供",
        ],
    ),
    ExpertRole.CODE: ExpertProfile(
        role=ExpertRole.CODE,
        title="代码专家",
        goal="编写清晰、可维护、高性能的代码，确保工程质量达到商业级标准",
        backstory="你是一位资深全栈工程师，精通多种技术栈。你信奉 Clean Code 原则，认为代码是写给人看的，顺便让机器执行。",
        focus_areas=[
            "代码结构和模块划分",
            "错误处理和边界条件",
            "性能优化和资源管理",
            "代码可读性和命名规范",
            "测试覆盖和持续集成",
        ],
        thinking_framework=[
            "函数不超过 30 行，一个函数只做一件事",
            "先写接口（type/interface），再写实现",
            "错误处理不能吞掉异常，必须有日志",
            "先让代码工作，再优化性能",
        ],
        quality_criteria=[
            "Linter 零警告",
            "测试覆盖核心业务逻辑",
            "无 TODO/FIXME 残留",
            "命名清晰见名知意",
        ],
        handoff_checklist=[
            "代码审查指南已生成",
            "AI 提示词已生成",
            "编码规范已明确",
        ],
    ),
    ExpertRole.DBA: ExpertProfile(
        role=ExpertRole.DBA,
        title="数据库专家",
        goal="设计高效、可靠的数据层，确保数据一致性和查询性能",
        backstory="你是一位数据库专家，精通关系型和 NoSQL 数据库设计。你知道数据模型的错误在后期修复成本极高，所以必须在设计阶段就做对。",
        focus_areas=[
            "数据建模和实体关系设计",
            "索引策略和查询优化",
            "数据迁移和版本管理",
            "数据一致性和事务设计",
            "备份恢复和数据安全",
        ],
        thinking_framework=[
            "先画 ER 图，再建表",
            "每个查询都要有索引支撑",
            "迁移脚本必须可回滚",
            "敏感数据必须加密存储",
        ],
        quality_criteria=[
            "数据库 schema 有完整的索引策略",
            "迁移脚本已生成且可执行",
            "无 N+1 查询风险",
            "敏感数据已标记加密要求",
        ],
        handoff_checklist=[
            "迁移脚本已生成",
            "数据模型已设计",
            "索引策略已规划",
        ],
    ),
    ExpertRole.QA: ExpertProfile(
        role=ExpertRole.QA,
        title="QA 专家",
        goal="建立全面的质量保障体系，确保交付物在功能、性能、安全各维度达标",
        backstory="你是一位质量保证专家，信奉'质量是设计出来的，不是测试出来的'。你的目标不是找 bug，而是建立让 bug 无处藏身的体系。",
        focus_areas=[
            "测试策略和测试金字塔",
            "质量门禁和通过标准",
            "自动化测试覆盖率",
            "性能基准和回归检测",
            "交付证据和审计链",
        ],
        thinking_framework=[
            "先定义'什么算通过'，再设计测试",
            "单元测试覆盖核心逻辑，集成测试覆盖关键路径",
            "每次提交都要过 CI 门禁",
            "质量分数必须量化，不能主观判断",
        ],
        quality_criteria=[
            "质量门禁评分 >= 80",
            "无 Critical 级失败项",
            "测试覆盖率 >= 80%（核心逻辑）",
            "所有 API 有集成测试",
        ],
        handoff_checklist=[
            "质量门禁报告已生成",
            "测试结果已汇总",
            "阻塞项已标记",
        ],
    ),
    ExpertRole.DEVOPS: ExpertProfile(
        role=ExpertRole.DEVOPS,
        title="DevOps 工程师",
        goal="构建自动化的构建、测试、部署流水线，确保交付过程可重复、可回滚",
        backstory="你是一位 DevOps 工程师，信奉'一切皆代码'。你的目标是让部署变成一键操作，回滚变成安全网。",
        focus_areas=[
            "CI/CD 流水线设计",
            "容器化和编排策略",
            "部署策略（蓝绿/灰度/金丝雀）",
            "监控告警和日志聚合",
            "灾难恢复和 SLA",
        ],
        thinking_framework=[
            "构建一次，到处部署",
            "每次部署都要有回滚方案",
            "监控先行，不要等出问题再加",
            "基础设施即代码",
        ],
        quality_criteria=[
            "CI/CD 配置已生成",
            "Docker 构建可复现",
            "部署有回滚手册",
            "健康检查端点已定义",
        ],
        handoff_checklist=[
            "CI/CD 配置已生成",
            "部署文档已完成",
            "回滚手册已编写",
        ],
    ),
    ExpertRole.OVERSEER: ExpertProfile(
        role=ExpertRole.OVERSEER,
        title="监督者（Overseer Agent）",
        goal="以独立第三方视角持续观测执行过程，确保每个阶段的输出与计划一致、质量达标、无偏离",
        backstory="你是一位独立的质量监督者，借鉴 codingsys 的 Dispatcher 验证模式。你不参与实现，只做观测和判定。你的角色类似生产线上的质检员——在每个检查点独立审查产出物，对比计划与实际的偏差，并在发现问题时及时暂停流水线。你信奉'信任但验证'原则。",
        focus_areas=[
            "计划与执行的一致性（Plan-Execute 合规）",
            "阶段产出物与 Spec/PRD 的对齐度",
            "跨阶段数据流的完整性（上游输出是否被下游正确消费）",
            "Claude Code 主执行者的行为合规性",
            "Codex 审查意见是否被正确处理",
            "质量分数趋势和异常检测",
        ],
        thinking_framework=[
            "每个检查点先读计划，再看实际产出，最后比对偏差",
            "用'如果这个产出物交给下游，下游能正常工作吗'测试完整性",
            "发现偏差时先判定严重级别（阻断/警告/建议），再决定是否暂停",
            "Codex 审查结果必须独立验证，不盲信也不忽视",
        ],
        quality_criteria=[
            "每个阶段产出物与计划步骤有明确的对应关系",
            "质量分数不低于配置的门禁阈值",
            "无未处理的 Codex 审查意见（Critical/High 级别）",
            "跨阶段数据依赖无断链",
        ],
        handoff_checklist=[
            "Overseer 审查报告已生成",
            "偏差项已分级并记录",
            "阻断项已通知主执行者修正",
            "审查通过的阶段已标记为 verified",
        ],
    ),
    ExpertRole.RCA: ExpertProfile(
        role=ExpertRole.RCA,
        title="根因分析专家",
        goal="从表象追溯到根因，制定防止复发的系统性改进措施",
        backstory="你是一位根因分析专家，擅长用 5-Why 和鱼骨图追溯问题根因。你知道修复 bug 只是开始，防止同类问题再次发生才是目标。",
        focus_areas=[
            "问题现象和复现条件",
            "根因追溯（5-Why）",
            "影响范围和回归风险",
            "修复方案和验证计划",
            "防复发措施和流程改进",
        ],
        thinking_framework=[
            "先复现，再分析，最后修复",
            "问 5 次'为什么'找到真正的根因",
            "修复后必须有回归测试",
            "把经验写回知识库防止复发",
        ],
        quality_criteria=[
            "根因已明确（不是症状）",
            "修复方案有回归测试覆盖",
            "影响范围已评估",
            "防复发措施已记录",
        ],
        handoff_checklist=[
            "根因分析报告已生成",
            "修复方案已提供",
            "回归测试已设计",
        ],
    ),
}


def get_expert_profile(role: ExpertRole) -> ExpertProfile:
    """获取专家完整画像"""
    return EXPERT_PROFILES[role]


def get_expert_prompt_section(role: ExpertRole) -> str:
    """生成专家身份提示词段落，用于注入 AI 提示词"""
    profile = EXPERT_PROFILES[role]
    focus = "\n".join(f"  - {f}" for f in profile.focus_areas)
    thinking = "\n".join(f"  - {t}" for t in profile.thinking_framework)
    quality = "\n".join(f"  - {q}" for q in profile.quality_criteria)
    return (
        f"### {profile.title}（{profile.role.value}）\n\n"
        f"**目标**: {profile.goal}\n\n"
        f"**背景**: {profile.backstory}\n\n"
        f"**关注点**:\n{focus}\n\n"
        f"**思维框架**:\n{thinking}\n\n"
        f"**质量标准**:\n{quality}\n"
    )


@dataclass
class ExpertOutput:
    """专家输出"""

    role: ExpertRole
    document_type: str  # prd | architecture | uiux | redteam | quality-gate | ...
    content: str
    quality_score: int = 85  # 0-100
    metadata: dict = field(default_factory=dict)


@dataclass
class ExpertTeamResult:
    """专家团队协作结果"""

    outputs: list[ExpertOutput] = field(default_factory=list)
    total_score: float = 0.0
    summary: str = ""

    def get_output(self, doc_type: str) -> ExpertOutput | None:
        for out in self.outputs:
            if out.document_type == doc_type:
                return out
        return None


class ExpertDispatcher:
    """
    专家调度器

    根据任务类型将工作路由到正确的专家处理器，
    并协调多专家协作完成文档生成任务。
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def dispatch_document_generation(
        self,
        name: str,
        description: str,
        platform: str = "web",
        frontend: str = "react",
        backend: str = "node",
        domain: str = "",
        language_preferences: list[str] | None = None,
        **kwargs,
    ) -> ExpertTeamResult:
        """
        调度多专家协作生成完整项目文档集

        调用顺序：PM → ARCHITECT → UI/UX → SECURITY → DBA → QA → DEVOPS
        """
        result = ExpertTeamResult()

        pm_profile = EXPERT_PROFILES.get(ExpertRole.PM)
        arch_profile = EXPERT_PROFILES.get(ExpertRole.ARCHITECT)
        ui_profile = EXPERT_PROFILES.get(ExpertRole.UI)

        # 1. PM 专家：生成 PRD（带专家视角）
        prd_content, prd_score = self._generate_document_with_expert(
            document_type="prd",
            profile=pm_profile,
            name=name,
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            language_preferences=language_preferences,
            required_sections=["产品愿景", "功能需求", "验收标准"],
            **kwargs,
        )
        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.PM,
                document_type="prd",
                content=prd_content,
                quality_score=prd_score,
                metadata={"name": name, "platform": platform, "expert_active": True},
            )
        )

        # 2. ARCHITECT 专家：生成架构文档（带专家视角）
        arch_content, arch_score = self._generate_document_with_expert(
            document_type="architecture",
            profile=arch_profile,
            name=name,
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            language_preferences=language_preferences,
            required_sections=["技术栈", "数据库", "API", "安全"],
            **kwargs,
        )
        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.ARCHITECT,
                document_type="architecture",
                content=arch_content,
                quality_score=arch_score,
                metadata={"frontend": frontend, "backend": backend, "expert_active": True},
            )
        )

        # 3. UI/UX 专家：生成 UI/UX 文档（带专家视角）
        uiux_content, uiux_score = self._generate_document_with_expert(
            document_type="uiux",
            profile=ui_profile,
            name=name,
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            language_preferences=language_preferences,
            required_sections=["设计系统", "色彩", "组件"],
            **kwargs,
        )
        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.UI,
                document_type="uiux",
                content=uiux_content,
                quality_score=uiux_score,
                metadata={"platform": platform, "expert_active": True},
            )
        )

        # 4. 计算团队总分（含专家自检结果）
        scores = [o.quality_score for o in result.outputs]
        result.total_score = sum(scores) / len(scores) if scores else 0.0
        active_experts = [o for o in result.outputs if o.metadata.get("expert_active")]
        result.summary = (
            f"专家团队协作完成：{len(active_experts)} 位专家参与，"
            f"生成 {len(result.outputs)} 份文档，"
            f"平均质量分 {result.total_score:.0f}/100"
        )

        return result

    async def dispatch_document_generation_async(
        self,
        name: str,
        description: str,
        platform: str = "web",
        frontend: str = "react",
        backend: str = "node",
        domain: str = "",
        language_preferences: list[str] | None = None,
        **kwargs,
    ) -> ExpertTeamResult:
        """
        异步并行版本：调度多专家协作生成完整项目文档集

        PM / ARCHITECT / UI-UX 三份文档并行生成，最后汇总评分。
        若并行执行失败，自动退回到顺序执行。
        """
        logger = logging.getLogger(__name__)
        pm_profile = EXPERT_PROFILES.get(ExpertRole.PM)
        arch_profile = EXPERT_PROFILES.get(ExpertRole.ARCHITECT)
        ui_profile = EXPERT_PROFILES.get(ExpertRole.UI)

        try:
            loop = asyncio.get_running_loop()
            executor = ThreadPoolExecutor(max_workers=3)

            prd_future = loop.run_in_executor(
                executor,
                lambda: self._generate_document_with_expert(
                    document_type="prd",
                    profile=pm_profile,
                    name=name,
                    description=description,
                    platform=platform,
                    frontend=frontend,
                    backend=backend,
                    domain=domain,
                    language_preferences=language_preferences,
                    required_sections=["产品愿景", "功能需求", "验收标准"],
                    **kwargs,
                ),
            )
            arch_future = loop.run_in_executor(
                executor,
                lambda: self._generate_document_with_expert(
                    document_type="architecture",
                    profile=arch_profile,
                    name=name,
                    description=description,
                    platform=platform,
                    frontend=frontend,
                    backend=backend,
                    domain=domain,
                    language_preferences=language_preferences,
                    required_sections=["技术栈", "数据库", "API", "安全"],
                    **kwargs,
                ),
            )
            uiux_future = loop.run_in_executor(
                executor,
                lambda: self._generate_document_with_expert(
                    document_type="uiux",
                    profile=ui_profile,
                    name=name,
                    description=description,
                    platform=platform,
                    frontend=frontend,
                    backend=backend,
                    domain=domain,
                    language_preferences=language_preferences,
                    required_sections=["设计系统", "色彩", "组件"],
                    **kwargs,
                ),
            )

            (prd_content, prd_score), (arch_content, arch_score), (uiux_content, uiux_score) = await asyncio.gather(
                prd_future,
                arch_future,
                uiux_future,
            )
            executor.shutdown(wait=False)
            logger.info("并行文档生成完成 (3 docs)")
        except Exception as exc:
            logger.warning("并行文档生成失败，退回顺序执行: %s", exc)
            return self.dispatch_document_generation(
                name=name,
                description=description,
                platform=platform,
                frontend=frontend,
                backend=backend,
                domain=domain,
                language_preferences=language_preferences,
                **kwargs,
            )

        result = ExpertTeamResult()

        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.PM,
                document_type="prd",
                content=prd_content,
                quality_score=prd_score,
                metadata={"name": name, "platform": platform, "expert_active": True},
            )
        )

        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.ARCHITECT,
                document_type="architecture",
                content=arch_content,
                quality_score=arch_score,
                metadata={"frontend": frontend, "backend": backend, "expert_active": True},
            )
        )

        result.outputs.append(
            ExpertOutput(
                role=ExpertRole.UI,
                document_type="uiux",
                content=uiux_content,
                quality_score=uiux_score,
                metadata={"platform": platform, "expert_active": True},
            )
        )

        scores = [o.quality_score for o in result.outputs]
        result.total_score = sum(scores) / len(scores) if scores else 0.0
        result.summary = (
            f"专家团队协作完成（并行模式）：{len(result.outputs)} 位专家在线生成 {len(result.outputs)} 份文档，"
            f"平均质量分 {result.total_score:.0f}/100"
        )

        return result

    def _generate_document_with_expert(
        self,
        *,
        document_type: Literal["prd", "architecture", "uiux"],
        profile: ExpertProfile | None,
        name: str,
        description: str,
        platform: str,
        frontend: str,
        backend: str,
        domain: str,
        language_preferences: list[str] | None,
        required_sections: list[str],
        **kwargs,
    ) -> tuple[str, int]:
        from ..creators.document_generator import DocumentGenerator

        generator = DocumentGenerator(
            name=name,
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            language_preferences=language_preferences,
            **kwargs,
        )
        if profile:
            generator.expert_context = {
                "role": profile.title,
                "goal": profile.goal,
                "thinking": profile.thinking_framework,
                "quality": profile.quality_criteria,
            }
        generate_fn = {
            "prd": generator.generate_prd,
            "architecture": generator.generate_architecture,
            "uiux": generator.generate_uiux,
        }[document_type]
        content = generate_fn()
        score = self._score_document(content, required_sections)
        if profile:
            score = self._expert_quality_check(content, profile, score)
        return content, score

    def dispatch_redteam_review(
        self,
        name: str,
        tech_stack: dict,
    ) -> ExpertOutput:
        """SECURITY 专家：调度红队审查"""
        from ..reviewers.redteam import RedTeamReviewer

        reviewer = RedTeamReviewer(
            project_dir=self.project_dir,
            name=name,
            tech_stack=tech_stack,
        )
        report = reviewer.review()
        content = report.to_markdown()

        return ExpertOutput(
            role=ExpertRole.SECURITY,
            document_type="redteam",
            content=content,
            quality_score=report.total_score,
            metadata={
                "passed": report.passed,
                "pass_threshold": report.pass_threshold,
                "blocking_reasons": report.blocking_reasons,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "security_issues": [
                    self._serialize_security_issue(i) for i in report.security_issues
                ],
                "performance_issues": [
                    self._serialize_performance_issue(i) for i in report.performance_issues
                ],
                "architecture_issues": [
                    self._serialize_architecture_issue(i) for i in report.architecture_issues
                ],
            },
        )

    def dispatch_quality_gate(
        self,
        name: str,
        tech_stack: dict,
        redteam_report=None,
        threshold_override: int | None = None,
        host_compatibility_min_score_override: int | None = None,
        host_compatibility_min_ready_hosts_override: int | None = None,
    ) -> ExpertOutput:
        """QA 专家：调度质量门禁检查"""
        from ..reviewers.quality_gate import QualityGateChecker

        checker = QualityGateChecker(
            project_dir=self.project_dir,
            name=name,
            tech_stack=tech_stack,
            threshold_override=threshold_override,
            host_compatibility_min_score_override=host_compatibility_min_score_override,
            host_compatibility_min_ready_hosts_override=host_compatibility_min_ready_hosts_override,
        )
        result = checker.check(redteam_report=redteam_report)
        content = result.to_markdown()
        from ..reviewers.ui_review import UIReviewReport

        ui_review_report = cast(UIReviewReport | None, checker.latest_ui_review_report)
        ui_review_payload = ui_review_report.to_dict() if ui_review_report is not None else None

        return ExpertOutput(
            role=ExpertRole.QA,
            document_type="quality-gate",
            content=content,
            quality_score=result.total_score,
            metadata={
                "passed": result.passed,
                "scenario": result.scenario,
                "weighted_score": result.weighted_score,
                "ui_review": ui_review_payload,
            },
        )

    def dispatch_code_review(
        self,
        name: str,
        tech_stack: dict,
    ) -> ExpertOutput:
        """CODE 专家：调度代码审查"""
        from ..reviewers.code_review import CodeReviewGenerator

        generator = CodeReviewGenerator(
            project_dir=self.project_dir,
            name=name,
            tech_stack=tech_stack,
        )
        content = generator.generate()

        return ExpertOutput(
            role=ExpertRole.CODE,
            document_type="code-review",
            content=content,
            quality_score=85,
            metadata={"tech_stack": tech_stack},
        )

    def dispatch_ai_prompt(self, name: str) -> ExpertOutput:
        """CODE 专家：生成 AI 提示词"""
        from ..creators.prompt_generator import AIPromptGenerator

        generator = AIPromptGenerator(
            project_dir=self.project_dir,
            name=name,
        )
        content = generator.generate()

        return ExpertOutput(
            role=ExpertRole.CODE,
            document_type="ai-prompt",
            content=content,
            quality_score=90,
            metadata={"name": name},
        )

    def dispatch_cicd(
        self,
        name: str,
        tech_stack: dict,
        cicd_platform: str = "github",
    ) -> ExpertOutput:
        """DEVOPS 专家：生成 CI/CD 配置"""
        from ..deployers.cicd import CICDGenerator

        generator = CICDGenerator(
            project_dir=self.project_dir,
            name=name,
            tech_stack=tech_stack,
            platform=self._normalize_cicd_platform(cicd_platform),
        )
        generated_files = generator.generate()
        content = self._render_generated_files_markdown(
            title=f"{name} - CI/CD 配置",
            generated_files=generated_files,
        )

        return ExpertOutput(
            role=ExpertRole.DEVOPS,
            document_type="cicd",
            content=content,
            quality_score=88,
            metadata={
                "platform": cicd_platform,
                "generated_files": list(generated_files.keys()),
                "generated_file_contents": generated_files,
            },
        )

    def dispatch_migration(
        self,
        name: str,
        tech_stack: dict,
        orm: str = "prisma",
    ) -> ExpertOutput:
        """DBA 专家：生成数据库迁移脚本"""
        from ..deployers.migration import MigrationGenerator

        generator = MigrationGenerator(
            project_dir=self.project_dir,
            name=name,
            tech_stack=tech_stack,
            orm_type=self._normalize_orm_type(orm),
        )
        generated_files = generator.generate()
        content = self._render_generated_files_markdown(
            title=f"{name} - 数据库迁移脚本",
            generated_files=generated_files,
        )

        return ExpertOutput(
            role=ExpertRole.DBA,
            document_type="migration",
            content=content,
            quality_score=87,
            metadata={
                "orm": orm,
                "generated_files": list(generated_files.keys()),
                "generated_file_contents": generated_files,
            },
        )

    def list_experts(self) -> list[dict]:
        """列出所有专家信息"""
        return [
            {
                "role": role.value,
                "description": desc,
            }
            for role, desc in EXPERT_DESCRIPTIONS.items()
        ]

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _score_document(self, content: str, required_keywords: list[str]) -> int:
        """基于关键词检测评估文档质量分"""
        if not content:
            return 0
        base = 70
        per_keyword = 10
        for kw in required_keywords:
            if kw in content:
                base += per_keyword
        # 长度加分（越详细越好，上限 100）
        length_bonus = min(10, len(content) // 2000)
        return min(100, base + length_bonus)

    def _expert_quality_check(self, content: str, profile: ExpertProfile, base_score: int) -> int:
        """用专家的 quality_criteria 验证文档内容，调整评分。"""
        if not content or not profile.quality_criteria:
            return base_score

        met = 0
        for criterion in profile.quality_criteria:
            # 提取标准中的关键词做简单匹配
            keywords = [w for w in criterion.replace("、", " ").split() if len(w) >= 2]
            if any(kw in content for kw in keywords[:3]):
                met += 1

        total = len(profile.quality_criteria)
        if total == 0:
            return base_score

        ratio = met / total
        # 专家自检通过率影响最终评分
        # 通过率 > 80% → 加分；< 50% → 扣分
        if ratio >= 0.8:
            return min(100, base_score + 5)
        elif ratio < 0.5:
            return max(0, base_score - 10)
        return base_score

    def _serialize_security_issue(self, issue) -> dict:
        return {
            "severity": issue.severity,
            "category": issue.category,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "cwe": issue.cwe,
            "file_path": issue.file_path,
            "line": issue.line,
        }

    def _serialize_performance_issue(self, issue) -> dict:
        return {
            "severity": issue.severity,
            "category": issue.category,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "impact": issue.impact,
            "file_path": issue.file_path,
            "line": issue.line,
        }

    def _serialize_architecture_issue(self, issue) -> dict:
        return {
            "severity": issue.severity,
            "category": issue.category,
            "description": issue.description,
            "recommendation": issue.recommendation,
            "adr_needed": issue.adr_needed,
            "file_path": issue.file_path,
            "line": issue.line,
        }

    def _normalize_cicd_platform(
        self, platform: str
    ) -> Literal["github", "gitlab", "jenkins", "azure", "bitbucket", "all"]:
        normalized = (platform or "").strip().lower()
        allowed = {"github", "gitlab", "jenkins", "azure", "bitbucket", "all"}
        if normalized in allowed:
            return cast(
                Literal["github", "gitlab", "jenkins", "azure", "bitbucket", "all"],
                normalized,
            )
        return "github"

    def _normalize_orm_type(self, orm: str):
        from ..deployers.migration import ORMType

        mapping = {
            "prisma": ORMType.PRISMA,
            "typeorm": ORMType.TYPEORM,
            "sequelize": ORMType.SEQUELIZE,
            "sqlalchemy": ORMType.SQLALCHEMY,
            "django": ORMType.DJANGO,
            "mongoose": ORMType.MONGOOSE,
        }
        return mapping.get((orm or "").strip().lower(), ORMType.PRISMA)

    def _render_generated_files_markdown(self, title: str, generated_files: dict[str, str]) -> str:
        lines = [
            f"# {title}",
            "",
            f"共生成 {len(generated_files)} 个文件。",
            "",
            "## 文件列表",
            "",
        ]
        for file_path in sorted(generated_files.keys()):
            lines.append(f"- `{file_path}`")
        lines.append("")
        return "\n".join(lines)
