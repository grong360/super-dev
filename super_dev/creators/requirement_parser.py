"""
需求解析器 - 将自然语言需求转换为可执行结构

增强版：支持目标用户提取、核心功能推导、商业约束识别、
技术栈偏好检测、非功能性需求推导、需求间依赖关系分析。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict


class KeywordRule(TypedDict):
    spec_name: str
    req_name: str
    keywords: tuple[str, ...]
    description: str
    scenario: dict[str, str]


@dataclass
class RequirementBlueprint:
    """结构化需求"""

    spec_name: str
    req_name: str
    description: str
    scenarios: list[dict]
    priority: str = "high"
    dependencies: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    non_functional: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "spec_name": self.spec_name,
            "req_name": self.req_name,
            "description": self.description,
            "scenarios": self.scenarios,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "acceptance_criteria": self.acceptance_criteria,
            "non_functional": self.non_functional,
        }


@dataclass
class RequirementAnalysis:
    """需求深度分析结果"""

    target_users: list[str]
    core_features: list[str]
    differentiation: list[str]
    business_constraints: dict[str, str]
    tech_preferences: dict[str, str]
    non_functional_requirements: dict[str, str]
    industry_domain: str
    product_type: str
    scale_expectation: str
    inferred_modules: list[str]

    def to_dict(self) -> dict:
        return {
            "target_users": self.target_users,
            "core_features": self.core_features,
            "differentiation": self.differentiation,
            "business_constraints": self.business_constraints,
            "tech_preferences": self.tech_preferences,
            "non_functional_requirements": self.non_functional_requirements,
            "industry_domain": self.industry_domain,
            "product_type": self.product_type,
            "scale_expectation": self.scale_expectation,
            "inferred_modules": self.inferred_modules,
        }


# ---------------------------------------------------------------------------
# Domain keyword maps
# ---------------------------------------------------------------------------

_INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ecommerce": (
        "电商",
        "购物",
        "商品",
        "订单",
        "购物车",
        "库存",
        "物流",
        "快递",
        "ecommerce",
        "shop",
        "store",
        "product",
        "cart",
        "order",
        "inventory",
        "支付",
        "退款",
        "优惠券",
        "促销",
        "秒杀",
        "拼团",
        "评价",
        "商品详情",
    ),
    "saas": (
        "SaaS",
        "订阅",
        "计费",
        "多租户",
        "租户",
        "workspace",
        "team",
        "套餐",
        "定价",
        "付费",
        "会员",
        "企业版",
        "专业版",
        "免费版",
        "billing",
        "subscription",
        "plan",
        "tenant",
    ),
    "education": (
        "教育",
        "课程",
        "学习",
        "考试",
        "培训",
        "学员",
        "教师",
        "学校",
        "education",
        "course",
        "learn",
        "exam",
        "quiz",
        "student",
        "teacher",
        "在线教育",
        "直播课",
        "录播",
        "题库",
        "作业",
    ),
    "healthcare": (
        "医疗",
        "健康",
        "医院",
        "诊所",
        "挂号",
        "问诊",
        "病历",
        "处方",
        "healthcare",
        "medical",
        "hospital",
        "patient",
        "doctor",
        "diagnosis",
        "体检",
        "预约",
        "药",
        "健康管理",
    ),
    "fintech": (
        "金融",
        "理财",
        "投资",
        "贷款",
        "保险",
        "银行",
        "股票",
        "基金",
        "fintech",
        "finance",
        "loan",
        "insurance",
        "trading",
        "payment",
        "转账",
        "账户",
        "风控",
        "信用",
        "征信",
    ),
    "content": (
        "内容",
        "文章",
        "博客",
        "社区",
        "论坛",
        "帖子",
        "评论",
        "标签",
        "content",
        "blog",
        "forum",
        "post",
        "comment",
        "tag",
        "category",
        "CMS",
        "发布",
        "编辑",
        "富文本",
        "专栏",
        "作者",
    ),
    "social": (
        "社交",
        "聊天",
        "好友",
        "关注",
        "粉丝",
        "动态",
        "朋友圈",
        "social",
        "chat",
        "friend",
        "follow",
        "feed",
        "message",
        "group",
        "私信",
        "群聊",
        "互动",
        "点赞",
        "收藏",
    ),
    "tool": (
        "工具",
        "效率",
        "自动化",
        "转换",
        "生成",
        "计算",
        "分析",
        "tool",
        "utility",
        "converter",
        "generator",
        "calculator",
        "analyzer",
        "批量",
        "处理",
        "导入",
        "导出",
        "模板",
    ),
    "government": (
        "政务",
        "公共服务",
        "办事",
        "审批",
        "申报",
        "政务大厅",
        "government",
        "public service",
        "citizen",
        "permit",
        "license",
        "窗口",
        "办理",
        "流程",
        "监督",
    ),
    "realestate": (
        "房产",
        "房源",
        "租房",
        "买房",
        "楼盘",
        "中介",
        "物业",
        "real estate",
        "property",
        "rent",
        "house",
        "apartment",
        "二手房",
        "新房",
        "看房",
        "签约",
    ),
}

_PRODUCT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dashboard": ("后台", "管理", "admin", "dashboard", "panel", "管控", "运营", "CMS"),
    "landing": ("官网", "落地页", "landing", "首页", "宣传", "营销", "展示", "介绍"),
    "marketplace": ("平台", "市场", "marketplace", "撮合", "交易", "供需"),
    "mobile_app": ("小程序", "APP", "app", "移动端", "手机", "H5", "微信"),
    "api_service": ("API", "接口服务", "开放平台", "开发者", "SDK"),
}

_USER_PERSONA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "consumer": (
        "消费者",
        "用户",
        "客户",
        "买家",
        "普通用户",
        "个人",
        "C端",
        "consumer",
        "customer",
        "user",
        "buyer",
    ),
    "business": (
        "企业",
        "商家",
        "B端",
        "商户",
        "供应商",
        "合作伙伴",
        "门店",
        "business",
        "merchant",
        "vendor",
        "supplier",
        "B2B",
        "enterprise",
    ),
    "admin": (
        "管理员",
        "运营",
        "超级管理员",
        "后台人员",
        "审核员",
        "admin",
        "operator",
        "manager",
        "moderator",
    ),
    "developer": (
        "开发者",
        "程序员",
        "工程师",
        "技术",
        "SDK",
        "API用户",
        "developer",
        "engineer",
        "programmer",
    ),
}

_SCALE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "small": ("小型", "个人", "单人", "MVP", "demo", "原型", "起步", "试水"),
    "medium": ("中型", "团队", "中小", "成长", "扩展", "几百", "几千"),
    "large": (
        "大型",
        "企业级",
        "高并发",
        "百万",
        "千万",
        "海量",
        "分布式",
        "enterprise",
        "scale",
        "high-traffic",
        "million",
    ),
}

_NFR_KEYWORDS: dict[str, tuple[tuple[str, str], ...]] = {
    "performance": (
        ("高性能", "接口响应时间不超过 200ms"),
        ("快速", "首屏加载不超过 2 秒"),
        ("高并发", "支持 1000+ 并发请求"),
        ("流畅", "动画帧率不低于 60fps"),
        ("实时", "数据延迟不超过 1 秒"),
    ),
    "security": (
        ("安全", "必须通过 OWASP Top 10 安全审查"),
        ("加密", "敏感数据必须加密存储和传输"),
        ("合规", "符合 GDPR / 等保 / 数据安全法要求"),
        ("权限", "基于角色的细粒度权限控制"),
    ),
    "reliability": (
        ("稳定", "服务可用性不低于 99.9%"),
        ("可靠", "关键操作必须支持幂等和重试"),
        ("容灾", "支持多机房容灾和快速恢复"),
    ),
    "scalability": (
        ("可扩展", "支持水平扩展和模块化架构"),
        ("弹性", "支持按需扩缩容"),
        ("多租户", "支持租户隔离和独立配置"),
    ),
    "accessibility": (
        ("无障碍", "符合 WCAG 2.1 AA 标准"),
        ("国际化", "支持多语言和多时区"),
        ("响应式", "适配桌面、平板和手机"),
    ),
}

_TECH_PREFERENCE_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "frontend": {
        "react": ("React", "react"),
        "vue": ("Vue", "vue"),
        "next": ("Next.js", "next", "nextjs"),
        "nuxt": ("Nuxt", "nuxt", "nuxtjs"),
        "angular": ("Angular", "angular"),
        "svelte": ("Svelte", "svelte"),
        "expo": ("Expo", "expo"),
        "flutter": ("Flutter", "flutter"),
        "react_native": ("React Native", "react-native", "rn"),
        "uni_app": ("uni-app", "uniapp", "uni-app"),
        "taro": ("Taro", "taro"),
        "tauri": ("Tauri", "tauri"),
        "electron": ("Electron", "electron"),
        "wails": ("Wails", "wails"),
        "ionic": ("Ionic", "ionic"),
        "capacitor": ("Capacitor", "capacitor"),
    },
    "backend": {
        "node": ("Node.js", "node", "nodejs", "express", "koa", "nest"),
        "python": ("Python", "python", "django", "flask", "fastapi"),
        "go": ("Go", "go", "golang"),
        "java": ("Java", "java", "spring", "springboot"),
        "rust": ("Rust", "rust"),
    },
    "database": {
        "postgresql": ("PostgreSQL", "postgres", "pg"),
        "mysql": ("MySQL", "mysql"),
        "mongodb": ("MongoDB", "mongo", "mongodb"),
        "redis": ("Redis", "redis"),
        "sqlite": ("SQLite", "sqlite"),
        "supabase": ("Supabase", "supabase"),
        "firebase": ("Firebase", "firebase"),
    },
}

_TECH_PREFERENCE_PRIORITY: dict[str, dict[str, int]] = {
    "frontend": {
        "expo": 120,
        "react_native": 110,
        "next": 105,
        "nuxt": 105,
        "tauri": 100,
        "electron": 100,
        "wails": 100,
        "ionic": 95,
        "capacitor": 95,
        "uni_app": 95,
        "taro": 95,
        "flutter": 90,
        "angular": 85,
        "svelte": 85,
        "vue": 80,
        "react": 70,
    }
}

_BUSINESS_CONSTRAINT_PATTERNS: list[tuple[str, str]] = [
    (r"(\d+)人[以]?内?", "team_size"),
    (r"(\d+)[万]?预算", "budget"),
    (r"(\d+)[周月天]内", "deadline"),
    (r"必须.*?([\w\u4e00-\u9fff]+)", "mandatory_tech"),
    (r"不能用.*?([\w\u4e00-\u9fff]+)", "excluded_tech"),
    (r"已有的.*?([\w\u4e00-\u9fff]+)", "existing_system"),
    (r"已有(\d+)万?用户", "existing_users"),
    (r"日活(\d+)", "dau"),
]


class RequirementParser:
    """将一句话需求解析为规范、阶段和前端模块"""

    _BUGFIX_KEYWORDS = (
        "bug",
        "bugfix",
        "fix",
        "hotfix",
        "回归",
        "修bug",
        "修复",
        "报错",
        "错误",
        "异常",
        "崩溃",
        "故障",
        "问题",
        "失效",
        "无法",
        "不生效",
        "不工作",
        "不对",
        "失败",
        "crash",
        "error",
        "exception",
        "regression",
    )

    _KEYWORD_RULES: list[KeywordRule] = [
        {
            "spec_name": "auth",
            "req_name": "secure-authentication",
            "keywords": (
                "登录",
                "注册",
                "认证",
                "oauth",
                "auth",
                "password",
                "账号",
                "密码",
                "验证码",
            ),
            "description": "系统应支持安全认证与会话管理。",
            "scenario": {
                "given": "用户处于未登录状态",
                "when": "提交有效凭据",
                "then": "系统完成鉴权并建立安全会话",
            },
        },
        {
            "spec_name": "profile",
            "req_name": "profile-management",
            "keywords": ("用户中心", "个人资料", "profile", "account", "设置", "个人信息"),
            "description": "用户应可查看和更新个人资料与偏好设置。",
            "scenario": {
                "given": "用户已经登录",
                "when": "在个人中心提交更新",
                "then": "资料变更被持久化并反馈成功状态",
            },
        },
        {
            "spec_name": "search",
            "req_name": "search-and-filter",
            "keywords": ("搜索", "筛选", "filter", "query", "检索", "查找", "过滤"),
            "description": "系统应提供可组合的搜索和筛选能力。",
            "scenario": {
                "given": "列表数据可访问",
                "when": "用户输入关键词并选择筛选条件",
                "then": "系统返回符合条件的数据结果",
            },
        },
        {
            "spec_name": "workflow",
            "req_name": "workflow-orchestration",
            "keywords": ("流程", "工作流", "pipeline", "审批", "自动化", "编排", "状态机"),
            "description": "系统应支持可追踪的流程编排与状态流转。",
            "scenario": {
                "given": "业务对象处于待处理状态",
                "when": "触发流程节点执行",
                "then": "状态按规则推进并记录审计信息",
            },
        },
        {
            "spec_name": "analytics",
            "req_name": "dashboard-insights",
            "keywords": ("报表", "统计", "dashboard", "分析", "指标", "图表", "数据看板"),
            "description": "系统应提供关键指标看板与洞察视图。",
            "scenario": {
                "given": "业务数据已入库",
                "when": "用户访问分析页面",
                "then": "系统渲染最新指标并支持维度切换",
            },
        },
        {
            "spec_name": "notification",
            "req_name": "notification-center",
            "keywords": ("通知", "消息", "提醒", "订阅", "message", "推送", "邮件", "短信"),
            "description": "系统应提供通知中心和订阅推送能力。",
            "scenario": {
                "given": "触发业务事件",
                "when": "事件匹配通知规则",
                "then": "用户收到站内消息或外部通知",
            },
        },
        {
            "spec_name": "billing",
            "req_name": "payment-and-billing",
            "keywords": (
                "支付",
                "账单",
                "billing",
                "付款",
                "订阅计费",
                "收费",
                "定价",
                "充值",
                "退款",
            ),
            "description": "系统应支持支付流程、账单记录与对账。",
            "scenario": {
                "given": "用户发起付费行为",
                "when": "支付网关返回交易结果",
                "then": "系统更新订单状态并生成账单条目",
            },
        },
        {
            "spec_name": "content",
            "req_name": "content-management",
            "keywords": ("内容", "文章", "帖子", "cms", "发布", "管理", "编辑", "富文本"),
            "description": "系统应支持内容的创建、审核与发布管理。",
            "scenario": {
                "given": "编辑已填写内容草稿",
                "when": "提交发布申请",
                "then": "内容进入审核并在通过后上线",
            },
        },
        {
            "spec_name": "rbac",
            "req_name": "role-based-access",
            "keywords": ("权限", "角色", "RBAC", "授权", "角色管理", "部门", "组织"),
            "description": "系统应支持基于角色的细粒度权限控制。",
            "scenario": {
                "given": "管理员配置了角色权限策略",
                "when": "用户尝试访问受保护资源",
                "then": "系统根据角色策略允许或拒绝访问",
            },
        },
        {
            "spec_name": "file",
            "req_name": "file-management",
            "keywords": ("上传", "下载", "文件", "附件", "图片", "oss", "s3", "存储"),
            "description": "系统应支持文件上传、存储、预览和下载管理。",
            "scenario": {
                "given": "用户选择本地文件",
                "when": "触发上传操作",
                "then": "文件存储到远端并返回可访问 URL",
            },
        },
        {
            "spec_name": "import_export",
            "req_name": "data-import-export",
            "keywords": ("导入", "导出", "Excel", "CSV", "批量", "数据迁移"),
            "description": "系统应支持结构化数据的批量导入导出。",
            "scenario": {
                "given": "用户准备符合模板的数据文件",
                "when": "触发导入操作",
                "then": "系统校验数据并批量写入，返回导入结果报告",
            },
        },
        {
            "spec_name": "schedule",
            "req_name": "task-scheduling",
            "keywords": ("定时", "调度", "cron", "计划任务", "排期", "预约"),
            "description": "系统应支持定时任务调度与执行监控。",
            "scenario": {
                "given": "管理员配置了定时任务",
                "when": "到达预定执行时间",
                "then": "系统自动执行任务并记录执行日志",
            },
        },
        {
            "spec_name": "log",
            "req_name": "audit-logging",
            "keywords": ("审计", "操作日志", "审计日志", "操作记录", "追溯", "变更记录"),
            "description": "系统应记录关键操作的审计日志，支持追溯查询。",
            "scenario": {
                "given": "用户执行了关键业务操作",
                "when": "操作完成",
                "then": "系统记录操作人、时间、内容和结果",
            },
        },
    ]

    _SOURCE_DIRS = (
        "src",
        "app",
        "backend",
        "frontend",
        "services",
        "api",
        "server",
        "client",
        "lib",
    )

    _PROJECT_FILES = (
        "package.json",
        "requirements.txt",
        "go.mod",
        "pom.xml",
        "Cargo.toml",
        "pyproject.toml",
    )

    # Dependency map: spec_name -> list of spec_names it depends on
    _DEPENDENCY_MAP: dict[str, list[str]] = {
        "profile": ["auth"],
        "rbac": ["auth"],
        "billing": ["auth"],
        "notification": ["auth"],
        "content": ["auth"],
        "file": ["auth"],
        "import_export": ["auth"],
        "schedule": ["auth"],
        "log": ["auth"],
        "search": [],
        "workflow": ["auth"],
        "analytics": ["auth"],
    }

    # ------------------------------------------------------------------
    # Deep analysis
    # ------------------------------------------------------------------

    def analyze_requirement(self, description: str) -> RequirementAnalysis:
        """Deep analysis of a natural language requirement.

        Extracts target users, core features, differentiation points,
        business constraints, tech preferences, NFRs, industry domain,
        product type, scale expectations, and inferred modules.
        """
        text = (description or "").strip()

        target_users = self._extract_target_users(text)
        core_features = self._extract_core_features(text)
        differentiation = self._extract_differentiation(text)
        business_constraints = self._extract_business_constraints(text)
        tech_preferences = self._extract_tech_preferences(text)
        nfrs = self._extract_non_functional_requirements(text)
        industry = self._detect_industry_domain(text)
        product_type = self._detect_product_type(text)
        scale = self._detect_scale(text)
        modules = self._infer_modules_from_description(text)

        return RequirementAnalysis(
            target_users=target_users,
            core_features=core_features,
            differentiation=differentiation,
            business_constraints=business_constraints,
            tech_preferences=tech_preferences,
            non_functional_requirements=nfrs,
            industry_domain=industry,
            product_type=product_type,
            scale_expectation=scale,
            inferred_modules=modules,
        )

    def parse_requirements(self, description: str) -> list[dict]:
        """Parse structured requirement list with priority and dependencies."""
        text = (description or "").strip()
        lowered = text.lower()
        parsed: list[RequirementBlueprint] = []

        analysis = self.analyze_requirement(description)

        # Core requirement
        parsed.append(
            RequirementBlueprint(
                spec_name="core",
                req_name="business-core-flow",
                description=f"系统应完整支持以下业务目标：{text or '核心业务流程实现'}",
                scenarios=[
                    {
                        "given": "用户进入系统首页",
                        "when": "按业务路径完成主要操作",
                        "then": "系统成功返回结果并展示下一步引导",
                    }
                ],
                priority="critical",
                dependencies=[],
                acceptance_criteria=[
                    "核心业务流程可端到端完成",
                    "前端页面可正常渲染和交互",
                    "后端API返回正确响应",
                ],
                non_functional=analysis.non_functional_requirements,
            )
        )

        for rule in self._KEYWORD_RULES:
            if any(keyword.lower() in lowered for keyword in rule["keywords"]):
                spec_name = rule["spec_name"]
                deps = self._DEPENDENCY_MAP.get(spec_name, [])
                priority = "high" if spec_name in ("auth", "rbac") else "medium"
                acceptance = self._generate_acceptance_criteria(spec_name, rule["description"])
                nfrs = self._derive_nfrs_for_spec(spec_name, analysis.non_functional_requirements)

                parsed.append(
                    RequirementBlueprint(
                        spec_name=spec_name,
                        req_name=rule["req_name"],
                        description=rule["description"],
                        scenarios=[rule["scenario"]],
                        priority=priority,
                        dependencies=deps,
                        acceptance_criteria=acceptance,
                        non_functional=nfrs,
                    )
                )

        # If no keyword matched, generate generic requirements based on analysis
        if len(parsed) == 1:
            for feature in analysis.core_features[:3]:
                slug = re.sub(r"[^a-z0-9]+", "-", feature.lower()).strip("-") or "feature"
                parsed.append(
                    RequirementBlueprint(
                        spec_name=slug,
                        req_name=f"{slug}-implementation",
                        description=f"实现{feature}的完整功能。",
                        scenarios=[
                            {
                                "given": f"用户需要使用{feature}",
                                "when": f"触发{feature}相关操作",
                                "then": f"系统正确执行{feature}并返回结果",
                            }
                        ],
                        priority="high",
                        dependencies=[],
                        acceptance_criteria=[
                            f"{feature}功能可正常使用",
                            f"{feature}操作有明确的状态反馈",
                        ],
                        non_functional={},
                    )
                )

            parsed.append(
                RequirementBlueprint(
                    spec_name="operation",
                    req_name="observability-and-maintenance",
                    description="系统应具备可观测性、日志和可维护的运维能力。",
                    scenarios=[
                        {
                            "given": "系统在生产环境运行",
                            "when": "出现异常或性能下降",
                            "then": "可通过监控与日志快速定位问题",
                        }
                    ],
                    priority="medium",
                    dependencies=["auth"] if any(r.spec_name == "auth" for r in parsed) else [],
                    acceptance_criteria=[
                        "关键操作有日志记录",
                        "异常时有告警机制",
                        "系统状态可监控",
                    ],
                    non_functional={},
                )
            )

        return self._deduplicate_requirements(parsed)

    # ------------------------------------------------------------------
    # Feature analysis methods
    # ------------------------------------------------------------------

    def _extract_target_users(self, text: str) -> list[str]:
        """Extract target user personas from description."""
        found: list[str] = []
        for persona, keywords in _USER_PERSONA_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                labels = {
                    "consumer": "普通消费者（C端用户）",
                    "business": "企业/商家（B端用户）",
                    "admin": "管理员/运营人员",
                    "developer": "开发者",
                }
                found.append(labels.get(persona, persona))
        if not found:
            found.append("普通用户（默认）")
        return found

    def _extract_core_features(self, text: str) -> list[str]:
        """Extract core features by splitting on common delimiters and filtering."""
        # Split on sentence delimiters and conjunctions
        parts = re.split(r"[，,。.!！？?；;、\n]+", text)
        features: list[str] = []
        for part in parts:
            part = part.strip()
            if not part or len(part) < 2:
                continue
            # Filter out pure function words
            if part in ("和", "与", "或", "包括", "需要", "我要", "做一个", "开发"):
                continue
            features.append(part)
        return features[:10]

    def _extract_differentiation(self, text: str) -> list[str]:
        """Extract differentiation points from description."""
        patterns = [
            r"不同于.{0,5}的是[，,]?\s*([^，,。.]+)",
            r"区别于.{0,5}[，,]?\s*([^，,。.]+)",
            r"核心.{0,2}(?:优势|特色|卖点|差异)[是为：:]\s*([^，,。.]+)",
            r"(?:独特|创新|特色|专属)的[^，,。.]{0,10}",
            r"主打([^，,。.]+)",
        ]
        points: list[str] = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            points.extend(m.strip() for m in matches if m.strip())
        return points[:5]

    def _extract_business_constraints(self, text: str) -> dict[str, str]:
        """Extract business constraints like team size, budget, deadline."""
        constraints: dict[str, str] = {}
        for pattern, key in _BUSINESS_CONSTRAINT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                constraints[key] = match.group(0)
        return constraints

    def _extract_tech_preferences(self, text: str) -> dict[str, str]:
        """Extract technology preferences from description."""
        lowered = text.lower()
        prefs: dict[str, str] = {}
        for category, techs in _TECH_PREFERENCE_KEYWORDS.items():
            best_match: tuple[int, int, int, str] | None = None
            priorities = _TECH_PREFERENCE_PRIORITY.get(category, {})
            for tech_name, keywords in techs.items():
                matched = [kw for kw in keywords if kw.lower() in lowered]
                if not matched:
                    continue
                score = (
                    len(matched),
                    priorities.get(tech_name, 0),
                    max(len(kw) for kw in matched),
                    tech_name,
                )
                if best_match is None or score[:2] > best_match[:2]:
                    best_match = score
            if best_match is not None:
                prefs[category] = best_match[3]
        return prefs

    def _extract_non_functional_requirements(self, text: str) -> dict[str, str]:
        """Extract non-functional requirements from description."""
        nfrs: dict[str, str] = {}
        for category, patterns in _NFR_KEYWORDS.items():
            for keyword, requirement in patterns:
                if keyword in text:
                    nfrs[category] = requirement
                    break
        return nfrs

    def _detect_industry_domain(self, text: str) -> str:
        """Detect industry domain from description."""
        lowered = text.lower()
        best_domain = ""
        best_count = 0
        for domain, keywords in _INDUSTRY_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw.lower() in lowered)
            if count > best_count:
                best_count = count
                best_domain = domain
        return best_domain or "general"

    def _detect_product_type(self, text: str) -> str:
        """Detect product type from description."""
        lowered = text.lower()
        for ptype, keywords in _PRODUCT_TYPE_KEYWORDS.items():
            if any(kw.lower() in lowered for kw in keywords):
                return ptype
        return "web_app"

    def _detect_scale(self, text: str) -> str:
        """Detect scale expectation from description."""
        for scale, keywords in _SCALE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return scale
        return "medium"

    def _infer_modules_from_description(self, text: str) -> list[str]:
        """Infer required modules based on description content."""
        lowered = text.lower()
        modules: list[str] = []

        # Common module inferences
        inferences: list[tuple[tuple[str, ...], str]] = [
            (("用户", "注册", "登录", "账号"), "用户管理模块"),
            (("商品", "产品", "服务"), "商品/产品管理模块"),
            (("订单", "交易", "购买"), "订单管理模块"),
            (("支付", "付款", "收费"), "支付模块"),
            (("消息", "通知", "推送"), "消息通知模块"),
            (("报表", "统计", "数据"), "数据报表模块"),
            (("权限", "角色", "管理"), "权限管理模块"),
            (("文件", "图片", "上传"), "文件管理模块"),
            (("搜索", "检索", "筛选"), "搜索模块"),
            (("评论", "评价", "反馈"), "评价反馈模块"),
            (("分享", "社交", "互动"), "社交互动模块"),
            (("地图", "位置", "定位"), "地图/位置模块"),
            (("日历", "排期", "预约"), "日历排期模块"),
            (("IM", "聊天", "会话"), "即时通讯模块"),
        ]

        for keywords, module_name in inferences:
            if any(kw in text or kw.lower() in lowered for kw in keywords):
                modules.append(module_name)

        return modules[:8] if modules else ["核心业务模块"]

    def _generate_acceptance_criteria(self, spec_name: str, description: str) -> list[str]:
        """Generate acceptance criteria for a spec."""
        criteria_map: dict[str, list[str]] = {
            "auth": [
                "用户可通过邮箱/手机号注册",
                "登录后获得有效 token 并正确跳转",
                "密码加密存储，不明文传输",
                "支持登出和 token 失效",
            ],
            "profile": [
                "用户可查看和编辑个人资料",
                "修改后实时生效并有成功提示",
                "头像上传并正确显示",
            ],
            "search": [
                "搜索结果在 500ms 内返回",
                "支持关键词+筛选条件组合查询",
                "无结果时显示友好空态",
            ],
            "workflow": [
                "流程状态变更可追溯",
                "每个节点有明确的操作人和时间",
                "支持驳回和重新提交",
            ],
            "analytics": [
                "数据看板正确展示统计指标",
                "支持时间范围筛选",
                "图表可交互（hover 展示详情）",
            ],
            "notification": [
                "用户可收到站内通知",
                "通知已读/未读状态正确",
                "支持标记全部已读",
            ],
            "billing": [
                "支付流程完整可用",
                "支付成功后订单状态正确更新",
                "支持查看历史账单",
            ],
            "content": [
                "支持富文本编辑",
                "内容发布前可预览",
                "支持草稿保存",
            ],
            "rbac": [
                "角色可自定义权限",
                "权限变更即时生效",
                "无权限时显示友好提示而非报错",
            ],
            "file": [
                "支持常见文件格式上传",
                "上传有进度显示",
                "大文件支持断点续传",
            ],
        }
        return criteria_map.get(
            spec_name,
            [
                f"{description}功能完整可用",
                "操作有明确的状态反馈",
                "异常情况有友好的错误提示",
            ],
        )

    def _derive_nfrs_for_spec(self, spec_name: str, global_nfrs: dict[str, str]) -> dict[str, str]:
        """Derive spec-specific non-functional requirements."""
        spec_nfrs: dict[str, str] = {}

        if spec_name == "auth":
            spec_nfrs["security"] = "密码 bcrypt 加密，token 有效期 24h，支持 rate limiting"
        elif spec_name == "search":
            spec_nfrs["performance"] = "搜索响应时间 < 500ms，支持分页"
        elif spec_name == "billing":
            spec_nfrs["security"] = "支付数据不落地，符合 PCI-DSS 基本要求"
            spec_nfrs["reliability"] = "支付操作必须幂等，支持重试"
        elif spec_name == "file":
            spec_nfrs["performance"] = "单文件上传不超过 50MB，支持分片上传"
        elif spec_name == "analytics":
            spec_nfrs["performance"] = "报表生成不超过 5s，支持大数据量分页"

        # Merge global NFRs
        for key, value in global_nfrs.items():
            if key not in spec_nfrs:
                spec_nfrs[key] = value

        return spec_nfrs

    # ------------------------------------------------------------------
    # Core API (preserved)
    # ------------------------------------------------------------------

    def detect_request_mode(self, description: str) -> str:
        """Detect if the request is a feature or bugfix."""
        lowered = (description or "").strip().lower()
        return (
            "bugfix" if any(keyword in lowered for keyword in self._BUGFIX_KEYWORDS) else "feature"
        )

    def detect_scenario(self, project_dir: Path) -> str:
        """Detect 0-1 / 1-N+1 scenario."""
        path = Path(project_dir).resolve()
        has_source = any((path / item).exists() for item in self._SOURCE_DIRS)
        has_project_file = any((path / item).exists() for item in self._PROJECT_FILES)
        return "1-N+1" if (has_source or has_project_file) else "0-1"

    def build_execution_phases(
        self,
        scenario: str,
        requirements: list[dict],
        request_mode: str = "feature",
    ) -> list[dict]:
        """Generate execution phase plan."""
        req_titles = [req.get("req_name", "requirement") for req in requirements]
        focus = ", ".join(req_titles[:4])
        if len(req_titles) > 4:
            focus += " ..."

        def phase(
            *,
            phase_id: str,
            title: str,
            objective: str,
            deliverables: list[str],
            host_playbook: list[str],
            hard_gates: list[str],
        ) -> dict:
            return {
                "id": phase_id,
                "title": title,
                "objective": objective,
                "deliverables": deliverables,
                "host_playbook": host_playbook,
                "hard_gates": hard_gates,
            }

        if request_mode == "bugfix":
            return [
                phase(
                    phase_id="phase-1",
                    title="问题复现与影响分析",
                    objective="先锁定错误现象、复现步骤、影响范围与回归风险。",
                    deliverables=["问题摘要", "复现步骤", "影响范围清单", "回归风险说明"],
                    host_playbook=[
                        "先复现、再定位、后修复；不要先动代码。",
                        "明确真实用户影响链路和回归面，再决定修复边界。",
                    ],
                    hard_gates=["必须写清复现步骤和影响范围后才能进入补丁文档。"],
                ),
                phase(
                    phase_id="phase-2",
                    title="轻量文档冻结",
                    objective="以补丁方式更新 PRD / Architecture / UIUX，记录根因与修复边界。",
                    deliverables=["补丁 PRD", "补丁架构说明", "补丁 UIUX", "确认门状态"],
                    host_playbook=[
                        "先把补丁边界写进文档，再让宿主改代码。",
                        "如果修复影响 UI 或架构，必须同步更新对应文档真源。",
                    ],
                    hard_gates=["docs_confirm 未通过前，不允许进入补丁实现。"],
                ),
                phase(
                    phase_id="phase-3",
                    title="定点修复与回归验证",
                    objective="完成最小必要修复，并覆盖主路径与回归风险。",
                    deliverables=["修复实现", "前端运行验证", "回归测试结果"],
                    host_playbook=[
                        "只做最小必要修复，避免顺手改出第二个问题。",
                        "所有修复必须带主路径回归和异常路径验证。",
                    ],
                    hard_gates=["质量回归未完成前，不允许进入交付。"],
                ),
                phase(
                    phase_id="phase-4",
                    title="质量门禁与交付",
                    objective="重新通过 quality gate、proof pack 与发布检查。",
                    deliverables=["质量门禁报告", "Proof Pack", "交付说明"],
                    host_playbook=[
                        "把这次修复的根因、验证和风险留进交付证据。",
                        "没有质量门和 proof-pack，就不算修复闭环。",
                    ],
                    hard_gates=["quality gate 未恢复通过前，不允许宣告修复完成。"],
                ),
            ]

        if scenario == "0-1":
            return [
                phase(
                    phase_id="phase-1",
                    title="需求对齐与文档冻结",
                    objective="冻结 PRD/架构/UIUX 文档并建立执行边界。",
                    deliverables=["PRD v1", "Architecture v1", "UIUX v1", "风险清单"],
                    host_playbook=[
                        "先 research，再冻结三份核心文档；不要边聊边写代码。",
                        "UIUX 里必须先锁图标、字体、token、组件生态和页面骨架。",
                    ],
                    hard_gates=["docs_confirm 未通过前，不允许创建 Spec 或开始实现。"],
                ),
                phase(
                    phase_id="phase-2",
                    title="前端先行交付",
                    objective="先交付可演示前端，以便快速验证业务流程。",
                    deliverables=["前端信息架构", "页面骨架", "设计令牌", "交互演示"],
                    host_playbook=[
                        "先做可演示主路径，再补次级页面；宿主必须围绕 UI 契约实现。",
                        "必须先落实视觉方向、品牌信号、证明构图、组件工艺和框架 playbook。",
                    ],
                    hard_gates=["preview_confirm 未通过前，不允许进入 backend / quality / delivery。"],
                ),
                phase(
                    phase_id="phase-3",
                    title="后端与数据能力",
                    objective="围绕核心流程构建 API、数据模型和权限控制。",
                    deliverables=["API 契约", "数据库迁移", "服务模块", "鉴权策略"],
                    host_playbook=[
                        "后端围绕已确认的前端主路径补齐，不做文档之外的自由发挥。",
                        "接口、权限、错误态和回退策略必须与前端场景逐一对应。",
                    ],
                    hard_gates=["没有已确认预览，就不允许把宿主推进后端实现。"],
                ),
                phase(
                    phase_id="phase-4",
                    title="联调与质量门禁",
                    objective="完成端到端联调并通过质量门禁。",
                    deliverables=["红队审查报告", "质量门禁报告", "回归测试清单"],
                    host_playbook=[
                        "把 UI、运行时、接口、权限、空态、异常态一起联调，不只测 happy path。",
                        "质量门失败时先修问题，再刷新证据，不能跳去交付。",
                    ],
                    hard_gates=["quality gate 未通过前，不允许进入发布准备。"],
                ),
                phase(
                    phase_id="phase-5",
                    title="上线与迭代计划",
                    objective="准备上线交付并规划 1-N+1 迭代路线。",
                    deliverables=["发布清单", "运维手册", "迭代 Backlog"],
                    host_playbook=[
                        "交付要沉淀 proof-pack、release-readiness 和关键演示证据。",
                        "把下一轮迭代明确成 backlog，而不是发布后再靠聊天回忆。",
                    ],
                    hard_gates=["交付证据不齐，不允许宣告商业级交付完成。"],
                ),
            ]

        return [
            phase(
                phase_id="phase-1",
                title="增量需求与影响分析",
                objective="确认变更边界、兼容性和风险。",
                deliverables=["变更影响矩阵", "兼容性策略", "回滚方案"],
                host_playbook=[
                    "先建立 baseline，再判断增量需求会影响哪些文档、页面和接口。",
                    "不要把已有项目当 0-1 重做；先尊重现状，再设计变化。",
                ],
                hard_gates=["baseline 未确认前，不允许宿主直接冲实现。"],
            ),
            phase(
                phase_id="phase-2",
                title="前端模块扩展",
                objective="优先扩展用户可感知模块并保持设计一致性。",
                deliverables=["新增页面/组件", "交互更新", "文案与埋点更新"],
                host_playbook=[
                    "先改用户感知最强的页面和流程，再扩散到技术细节。",
                    "新增模块必须继承既有 token、组件生态和新的 UI 契约，不允许另起一套视觉语言。",
                ],
                hard_gates=["preview_confirm 未通过前，不允许进入增量后端和发布。"],
            ),
            phase(
                phase_id="phase-3",
                title="后端能力扩展",
                objective="按规范增加接口与数据能力，避免破坏存量系统。",
                deliverables=["增量 API", "迁移脚本", "灰度开关"],
                host_playbook=[
                    "先对齐前端/产品路径再扩接口，保证改动有真实调用链。",
                    "兼容性、回滚、灰度策略要与新增接口一起设计。",
                ],
                hard_gates=["没有已确认预览，不允许宿主推进后端能力扩展。"],
            ),
            phase(
                phase_id="phase-4",
                title="回归验证与发布",
                objective="覆盖关键链路并完成灰度/正式发布。",
                deliverables=["回归测试结果", "发布报告", "监控告警确认"],
                host_playbook=[
                    "把旧功能、增量功能、权限链路和异常态一起回归，不只验新增 happy path。",
                    "先过 quality gate，再整理 proof-pack 和 release-readiness。",
                ],
                hard_gates=["quality gate 未通过前，不允许进入发布动作。"],
            ),
            phase(
                phase_id="phase-5",
                title="持续优化",
                objective=f"围绕 {focus or '核心需求'} 持续迭代优化。",
                deliverables=["性能优化清单", "体验优化清单", "后续版本计划"],
                host_playbook=[
                    "把性能、体验、稳定性和商业转化继续列成下一轮明确任务。",
                    "继续沿同一套流程推进，而不是回到自由聊天式开发。",
                ],
                hard_gates=["没有明确 backlog 和证据，不算增量闭环完成。"],
            ),
        ]

    def build_frontend_modules(self, requirements: list[dict]) -> list[dict]:
        """Generate frontend-first delivery module list."""
        modules = [
            {
                "name": "需求总览面板",
                "goal": "集中展示需求摘要、优先级和执行状态。",
                "core_elements": ["需求卡片", "优先级标签", "状态标识"],
            },
            {
                "name": "文档工作台",
                "goal": "统一管理 PRD、架构和 UIUX 文档入口。",
                "core_elements": ["文档卡片", "版本信息", "快速跳转"],
            },
            {
                "name": "执行路线图",
                "goal": "可视化 0-1 / 1-N+1 阶段任务。",
                "core_elements": ["阶段时间线", "里程碑", "风险提示"],
            },
        ]

        for req in requirements[:4]:
            modules.append(
                {
                    "name": f"{req.get('spec_name', 'core')} 模块",
                    "goal": req.get("description", "实现核心业务能力"),
                    "core_elements": [
                        f"{req.get('req_name', 'requirement')} 视图",
                        "关键交互入口",
                        "状态反馈组件",
                    ],
                }
            )

        return modules

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_subject(self, description: str) -> str:
        cleaned = re.sub(r"\s+", " ", description.strip())
        if not cleaned:
            return "核心业务"
        separators = r"[，,。.!！？;；/]+"
        segment = re.split(separators, cleaned)[0]
        return segment[:40]

    def _deduplicate_requirements(self, requirements: list[RequirementBlueprint]) -> list[dict]:
        seen = set()
        result = []
        for item in requirements:
            key = (item.spec_name, item.req_name)
            if key in seen:
                continue
            seen.add(key)
            result.append(item.to_dict())
        return result
