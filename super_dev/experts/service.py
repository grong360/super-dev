"""专家建议服务。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_EXPERT_META: list[dict[str, str]] = [
    {"id": "PRODUCT", "name": "产品负责人", "description": "产品闭环、功能缺口、体验总审查"},
    {"id": "PM", "name": "产品经理", "description": "需求分析、PRD编写"},
    {"id": "ARCHITECT", "name": "架构师", "description": "系统设计、技术选型"},
    {"id": "UI", "name": "UI设计师", "description": "视觉设计、设计规范"},
    {"id": "UX", "name": "UX设计师", "description": "交互设计、用户体验"},
    {"id": "SECURITY", "name": "安全专家", "description": "安全审查、漏洞检测"},
    {"id": "CODE", "name": "开发专家", "description": "代码实现、最佳实践"},
    {"id": "DBA", "name": "数据库专家", "description": "数据库设计、优化"},
    {"id": "QA", "name": "测试专家", "description": "质量保证、测试策略"},
    {"id": "DEVOPS", "name": "运维专家", "description": "部署、CI/CD"},
    {"id": "RCA", "name": "故障侦探", "description": "根因分析、复盘改进"},
]


_EXPERT_PLAYBOOKS: dict[str, list[str]] = {
    "PRODUCT": [
        "先看首次上手路径、成功标志和失败恢复是否清晰，再看实现细节。",
        "从产品完整性角度盘点缺失能力、断链流程和交付证据缺口。",
        "把问题按“阻断首次使用 / 影响闭环 / 可延后优化”分层，优先修阻断项。",
    ],
    "PM": [
        "明确目标用户、核心场景与北极星指标。",
        "将需求拆分为 MUST/SHOULD/COULD，并定义验收标准。",
        "补充边界条件与失败场景，避免需求歧义。",
    ],
    "ARCHITECT": [
        "先定义系统边界与模块职责，再确定通信契约。",
        "对关键链路做容量估算与扩展策略（缓存/队列/分片）。",
        "沉淀可演进架构决策记录（ADR），降低后续返工风险。",
    ],
    "UI": [
        "统一设计 token（颜色、间距、字体）并固化到组件层。",
        "优先实现高频核心页面，保证视觉一致性和可读性。",
        "在桌面与移动端分别验证层级、对比度和可触达性。",
    ],
    "UX": [
        "梳理关键任务流并减少不必要步骤。",
        "定义空状态、错误态与加载态，避免流程中断。",
        "通过可观测埋点验证转化漏斗并持续迭代。",
    ],
    "SECURITY": [
        "建立威胁模型并优先修复高危攻击面。",
        "对认证、授权、输入校验和密钥管理做最小权限设计。",
        "将 SAST/依赖漏洞扫描纳入 CI 阶段阻断高风险变更。",
    ],
    "CODE": [
        "保持单一职责与清晰边界，减少隐式耦合。",
        "核心逻辑补充单元测试和回归测试用例。",
        "对异常处理、日志与可观测性做统一约束。",
    ],
    "DBA": [
        "先建模实体关系，再补充索引和约束策略。",
        "对高频查询设计覆盖索引并验证执行计划。",
        "迁移脚本确保可回滚，发布时采用灰度策略。",
    ],
    "QA": [
        "按风险优先级制定测试策略（冒烟/回归/性能）。",
        "建立关键路径自动化测试并接入质量门禁。",
        "输出缺陷分级和修复 SLA，形成闭环。",
    ],
    "DEVOPS": [
        "统一环境配置与密钥管理，减少环境漂移。",
        "构建 CI/CD 流水线并开启发布审计与回滚策略。",
        "完善监控告警与容量基线，保障上线稳定性。",
    ],
    "RCA": [
        "先确认用户影响范围，再聚焦首个异常时间点。",
        "使用时间线 + 5 Whys 还原根因链路。",
        "输出可执行改进项并设置验证指标防止复发。",
    ],
}

_TEAM_META: list[dict[str, str]] = [
    {
        "id": "PRODUCT_AUDIT",
        "name": "产品审查团队",
        "description": "产品负责人牵头，联动 PM/UX/ARCHITECT/SECURITY/CODE/QA/DEVOPS 做全项目闭环审查",
    },
]

_TEAM_COMPOSITION: dict[str, list[str]] = {
    "PRODUCT_AUDIT": ["PRODUCT", "PM", "UX", "ARCHITECT", "SECURITY", "CODE", "QA", "DEVOPS"],
}


def list_experts() -> list[dict[str, str]]:
    return list(_EXPERT_META)


def list_expert_teams() -> list[dict[str, str]]:
    return list(_TEAM_META)


def has_expert(expert_id: str) -> bool:
    return expert_id in _EXPERT_PLAYBOOKS


def has_expert_team(team_id: str) -> bool:
    return team_id in _TEAM_COMPOSITION


def render_expert_advice_markdown(expert_id: str, prompt: str = "") -> str:
    suggestions = _EXPERT_PLAYBOOKS.get(expert_id, [])
    lines = [
        f"# {expert_id} 专家建议",
        "",
        f"**输入问题**: {prompt or '(未提供，输出通用建议)'}",
        "",
        "## 建议清单",
        "",
    ]
    for idx, item in enumerate(suggestions, 1):
        lines.append(f"{idx}. {item}")
    lines.extend(
        [
            "",
            "## 下一步执行",
            "",
            "1. 将建议映射到当前 Spec 或任务清单。",
            "2. 标注优先级并安排负责人。",
            "3. 完成后运行 `super-dev quality --type all` 复核。",
            "",
        ]
    )
    return "\n".join(lines)


def render_team_advice_markdown(team_id: str, prompt: str = "") -> str:
    if team_id not in _TEAM_COMPOSITION:
        raise ValueError(f"unknown team: {team_id}")

    members = _TEAM_COMPOSITION[team_id]
    lines = [
        f"# {team_id} 团队审查报告",
        "",
        f"**输入问题**: {prompt or '(未提供，按仓库级全面审查输出)'}",
        "",
        "## 团队组成",
        "",
    ]
    for member in members:
        meta = next(
            (item for item in _EXPERT_META if item["id"] == member),
            {"name": member, "description": ""},
        )
        lines.append(f"- **{member}**: {meta['name']} - {meta['description']}")

    lines.extend(
        [
            "",
            "## 审查维度",
            "",
            "1. 产品与上手路径：用户是否知道怎么开始、怎么继续、怎么确认流程完成。",
            "2. 交互与信息架构：主路径、确认门、失败恢复、状态反馈是否闭环。",
            "3. 功能完整性：是否存在承诺了但没有真实做成的能力、文档断链或命令断链。",
            "4. 技术与架构：代码结构是否支持持续迭代，协议/规则是否有单一真相源。",
            "5. 质量与安全：红队、质量门禁、proof-pack、release readiness 是否引用同一套证据。",
            "6. 交付闭环：报告、任务执行、自检、评审状态、发布证据是否一致。",
            "",
            "## 输出要求",
            "",
            "1. 先按严重级别列出问题，必须带文件路径与原因。",
            "2. 再给出按优先级排序的修复建议。",
            "3. 最后输出一个从 P0 到 P2 的补全路线图。",
            "",
            "## 下一步执行",
            "",
            "1. 先生成正式审查报告并写入 `output/`。",
            "2. 按 P0/P1 优先级直接修复闭环漏洞和断链能力。",
            "3. 修复后重新执行质量门禁，并刷新 proof-pack / release readiness 等交付证据。",
            "",
        ]
    )
    return "\n".join(lines)


def save_expert_advice(project_dir: Path, expert_id: str, prompt: str = "") -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    content = render_expert_advice_markdown(expert_id=expert_id, prompt=prompt)
    file_path = output_dir / f"expert-{expert_id.lower()}-advice.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path, content


def save_team_advice(project_dir: Path, team_id: str, prompt: str = "") -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    content = render_team_advice_markdown(team_id=team_id, prompt=prompt)
    file_path = output_dir / f"team-{team_id.lower().replace('_', '-')}-report.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path, content


def list_expert_advice_history(project_dir: Path, limit: int = 20) -> list[dict[str, str]]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    if not output_dir.exists():
        return []

    items: list[dict[str, str]] = []
    files = sorted(
        output_dir.glob("expert-*-advice.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for file_path in files[:limit]:
        name = file_path.name
        expert_id = name.removeprefix("expert-").removesuffix("-advice.md").upper()
        items.append(
            {
                "file_name": name,
                "file_path": str(file_path),
                "expert_id": expert_id,
                "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            }
        )
    return items


def read_expert_advice(project_dir: Path, file_name: str) -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    if "/" in file_name or "\\" in file_name:
        raise ValueError("invalid file name")
    if not (file_name.startswith("expert-") and file_name.endswith("-advice.md")):
        raise ValueError("invalid file name")

    file_path = (output_dir / file_name).resolve()
    if not file_path.exists():
        raise FileNotFoundError(file_name)
    if output_dir.resolve() not in file_path.parents:
        raise ValueError("invalid file path")

    return file_path, file_path.read_text(encoding="utf-8")
