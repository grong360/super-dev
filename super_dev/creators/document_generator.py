"""
文档生成器 - 高质量 PRD、架构、UI/UX 文档生成

开发：Excellent（11964948@qq.com）
功能：专家级文档生成
作用：生成专业、细致、完整的项目文档
创建时间：2025-12-30
最后修改：2025-01-04
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .document_generator_content_mixin import DocumentGeneratorContentMixin
from .requirement_parser import RequirementParser

logger = logging.getLogger(__name__)


class DocumentGenerator(DocumentGeneratorContentMixin):
    """文档生成器 - 生成专家级项目文档"""

    def __init__(
        self,
        name: str,
        description: str,
        request_mode: str = "feature",
        platform: str = "web",
        frontend: str = "next",
        backend: str = "node",
        domain: str = "",
        ui_library: str | None = None,
        style_solution: str | None = None,
        state_management: list[str] | None = None,
        testing_frameworks: list[str] | None = None,
        design_inspiration_slug: str | None = None,
        language_preferences: list[str] | None = None,
        knowledge_summary: dict | None = None,
    ):
        """初始化文档生成器"""
        self.name = name
        self.description = description
        self.request_mode = request_mode if request_mode in {"feature", "bugfix"} else "feature"
        self.platform = platform
        self.frontend = frontend
        self.backend = backend
        self.domain = domain or "general"
        self.ui_library = ui_library
        self.style_solution = style_solution
        self.state_management = state_management or []
        self.testing_frameworks = testing_frameworks or []
        self.design_inspiration_slug = str(design_inspiration_slug or "").strip()
        self.language_preferences = self._normalize_language_preferences(language_preferences)
        self.knowledge_summary: dict = knowledge_summary or {}
        self.expert_context: dict | None = None  # 专家视角注入（由 ExpertDispatcher 设置）
        self.requirement_parser = RequirementParser()

        # Prompt 模板管理器（加载失败不影响文档生成）
        self._template_mgr = None
        try:
            from .prompt_templates import PromptTemplateManager

            self._template_mgr = PromptTemplateManager()
        except Exception:
            logger.debug("Prompt 模板管理器加载失败，将跳过模板版本标记")

    def _request_mode(self) -> str:
        if self.request_mode in {"feature", "bugfix"}:
            return self.request_mode
        return self.requirement_parser.detect_request_mode(self.description)

    def generate_ui_contract(self) -> dict:
        """生成跨阶段 UI 契约，供前端实现与后续返工持续继承。"""
        analysis = self._analyze_project_for_design()
        ui_intelligence = self._get_ui_intelligence(analysis)
        design_system_bundle = self._get_design_system_bundle(analysis, ui_intelligence)
        return self._build_ui_contract_payload(analysis, ui_intelligence, design_system_bundle)

    def _normalize_language_preferences(self, values: list[str] | None) -> list[str]:
        normalized: list[str] = []
        for item in values or []:
            if not isinstance(item, str):
                continue
            token = item.strip().lower()
            if token and token not in normalized:
                normalized.append(token)
        return normalized

    def _display_language_name(self, language: str) -> str:
        mapping = {
            "csharp": "C#",
            "cpp": "C++",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "objective-c": "Objective-C",
            "matlab": "MATLAB",
            "php": "PHP",
            "sql": "SQL",
            "r": "R",
        }
        if language in mapping:
            return mapping[language]
        if language in {
            "go",
            "java",
            "ruby",
            "scala",
            "swift",
            "kotlin",
            "rust",
            "dart",
            "elixir",
            "lua",
        }:
            return language.capitalize()
        return language.replace("-", " ").title()

    def _language_preferences_inline(self) -> str:
        if not self.language_preferences:
            return "未指定（默认支持主流语言）"
        return " / ".join(self._display_language_name(item) for item in self.language_preferences)

    def _analyze_project_for_design(self) -> dict:
        """分析项目特征用于设计推荐"""
        # 从描述中提取特征
        description_lower = self.description.lower()

        # 产品类型
        product_type = "general"
        if any(
            word in description_lower
            for word in ["dashboard", "仪表盘", "后台", "admin", "workbench", "workspace", "工作台"]
        ):
            product_type = "dashboard"
        elif any(
            word in description_lower
            for word in [
                "landing",
                "落地页",
                "营销页",
                "官网",
                "官方网站",
                "official website",
                "marketing",
            ]
        ):
            product_type = "landing"
        elif any(word in description_lower for word in ["saas", "软件服务", "platform", "平台"]):
            product_type = "saas"
        elif any(word in description_lower for word in ["电商", "商城", "shop", "store", "mall"]):
            product_type = "ecommerce"
        elif any(word in description_lower for word in ["blog", "博客", "内容", "cms"]):
            product_type = "content"

        # 行业
        industry = "general"
        if any(word in description_lower for word in ["医疗", "健康", "health", "medical", "care"]):
            industry = "healthcare"
        elif any(
            word in description_lower for word in ["金融", "支付", "fintech", "金融科技", "banking"]
        ):
            industry = "fintech"
        elif any(word in description_lower for word in ["教育", "培训", "education", "learning"]):
            industry = "education"
        elif any(word in description_lower for word in ["法律", "法务", "legal", "律师"]):
            industry = "legal"
        elif any(word in description_lower for word in ["政务", "government", "public"]):
            industry = "government"
        elif any(
            word in description_lower for word in ["美容", "美业", "beauty", "spa", "wellness"]
        ):
            industry = "beauty"

        # 风格倾向
        style = "modern"
        if any(word in description_lower for word in ["极简", "minimal", "简约"]):
            style = "minimal"
        elif any(
            word in description_lower for word in ["专业", "商务", "business", "professional"]
        ):
            style = "professional"
        elif any(word in description_lower for word in ["活泼", "fun", "playful", "活力"]):
            style = "playful"
        elif any(word in description_lower for word in ["奢华", "luxury", "高端", "premium"]):
            style = "luxury"

        return {
            "product_type": product_type,
            "industry": industry,
            "style": style,
            "domain": self.domain,
            "platform": self.platform,
            "frontend": self.frontend,
        }

    def _extract_tech_keywords(self) -> dict:
        """
        从描述中提取技术栈关键词

        Returns:
            dict: 包含提取的技术关键词分类
        """
        description = self.description
        keywords: dict[str, list[str]] = {
            "ai_frameworks": [],  # AI 框架：LangGraph, LangChain, Transformers 等
            "agent_tools": [],  # Agent 工具：AutoGPT, BabyAGI, CrewAI 等
            "ml_libraries": [],  # ML 库：PyTorch, TensorFlow, scikit-learn 等
            "vector_stores": [],  # 向量数据库：Pinecone, Chroma, Weaviate 等
            "orchestration": [],  # 编排工具：Airflow, Prefect, Dagster 等
            "other_keywords": [],  # 其他技术关键词
        }

        # AI 框架
        ai_frameworks = ["LangGraph", "LangChain", "LlamaIndex", "Haystack", "Semantic Kernel"]
        for framework in ai_frameworks:
            if framework in description:
                keywords["ai_frameworks"].append(framework)

        # Agent 工具
        agent_tools = ["AutoGPT", "BabyAGI", "CrewAI", "AgentOps", "E2B"]
        for tool in agent_tools:
            if tool in description:
                keywords["agent_tools"].append(tool)

        # ML 库
        ml_libraries = ["PyTorch", "TensorFlow", "Keras", "scikit-learn", "XGBoost", "LightGBM"]
        for lib in ml_libraries:
            if lib in description:
                keywords["ml_libraries"].append(lib)

        # 向量数据库
        vector_stores = ["Pinecone", "Chroma", "Weaviate", "Qdrant", "Milvus", "FAISS"]
        for store in vector_stores:
            if store in description:
                keywords["vector_stores"].append(store)

        # 编排工具
        orchestration = ["Airflow", "Prefect", "Dagster", "Argo Workflows", "Temporal"]
        for tool in orchestration:
            if tool in description:
                keywords["orchestration"].append(tool)

        # 提取 Agent 相关关键词
        if "Agent" in description or "agent" in description or "智能体" in description:
            keywords["other_keywords"].append("Multi-Agent System")

        if "RAG" in description or "检索增强" in description:
            keywords["other_keywords"].append("RAG (Retrieval-Augmented Generation)")

        if "LLM" in description or "大语言模型" in description or "GPT" in description:
            keywords["other_keywords"].append("LLM Integration")

        return keywords

    def _expert_header(self) -> str:
        """生成专家视角说明（如果有专家上下文）"""
        if not self.expert_context:
            return ""
        role = self.expert_context.get("role", "")
        goal = self.expert_context.get("goal", "")
        thinking = self.expert_context.get("thinking", [])
        thinking_text = "\n".join(f"  - {t}" for t in thinking[:3]) if thinking else ""
        return f"""
> **审查专家**: {role}
> **专家目标**: {goal}
> **思考框架**:
{thinking_text}
"""

    def generate_prd(self) -> str:
        """生成高质量 PRD 文档"""
        expert_header = self._expert_header()
        doc = f"""# {self.name} - 产品需求文档 (PRD)

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **版本**: v2.4.0
> **状态**: 草稿
{expert_header}

---

## 文档信息

| 项目 | 内容 |
|:---|:---|
| **项目名称** | {self.name} |
| **项目描述** | {self.description} |
| **目标平台** | {self.platform.upper()} |
| **业务领域** | {self.domain.upper()} |
| **语言偏好** | {self._language_preferences_inline()} |

---

## 1. 产品概述

### 1.1 产品愿景

{self._generate_vision()}

### 1.2 目标用户

{self._generate_target_users()}

### 1.3 核心价值

{self._generate_value_proposition()}

### 1.4 市场与对标结论

{self._generate_market_context()}

### 1.5 用户分层与使用场景

{self._generate_user_segment_matrix()}

### 1.6 需求澄清问题

{self._generate_clarification_questions()}

### 1.7 联网研究证据与方案对比

{self._generate_research_evidence_brief()}

{self._generate_knowledge_constraints_section()}

### 1.8 关键决策账本

{self._generate_decision_ledger()}

### 1.9 用户到专业交付统一协议

{self._generate_user_to_pro_protocol()}

---

## 2. 功能需求

### 2.1 核心功能 (MVP)

{self._generate_core_features()}

### 2.2 扩展功能 (Phase 2)

{self._generate_extended_features()}

### 2.3 用户故事

{self._generate_user_stories()}

### 2.4 功能优先级与范围边界

{self._generate_scope_priorities()}

### 2.5 边界场景与异常路径

{self._generate_edge_cases()}

### 2.6 实施方案分层与取舍

{self._generate_solution_tradeoffs()}

---

## 3. 非功能需求

### 3.1 性能要求

- **响应时间**: API 响应时间 < 200ms (P95)
- **并发用户**: 支持 1000+ 并发用户
- **页面加载**: 首屏加载时间 < 2s

### 3.2 安全要求

- **数据加密**: 传输层 TLS 1.3+
- **身份认证**: JWT Token 认证
- **权限控制**: RBAC 角色权限
- **数据保护**: 敏感数据加密存储

### 3.3 可用性要求

- **系统可用性**: 99.9% SLA
- **容错机制**: 自动故障转移
- **数据备份**: 每日自动备份

### 3.4 兼容性要求

- **浏览器**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **移动端**: iOS 14+, Android 10+
- **分辨率**: 320px - 4K

### 3.5 商业交付要求

{self._generate_delivery_requirements()}

---

## 4. 用户流程

### 4.1 主要用户旅程

{self._generate_user_journeys()}

### 4.2 页面结构

{self._generate_page_structure()}

---

## 5. 数据模型

### 5.1 核心实体

{self._generate_data_entities()}

### 5.2 关系图

```
[ER 图将在架构文档中详细说明]
```

---

## 6. 业务规则

{self._generate_business_rules()}

---

## 7. 验收标准

### 7.1 功能验收

{self._generate_acceptance_criteria()}

### 7.2 性能验收

- [ ] API 响应时间测试通过
- [ ] 并发压力测试通过
- [ ] 页面性能测试通过

### 7.3 安全验收

- [ ] 渗透测试通过
- [ ] 数据加密验证通过
- [ ] 权限控制验证通过

### 7.4 业务验收矩阵

{self._generate_acceptance_matrix()}

---

## 8. 发布计划

### 8.1 MVP (v1.0)

**时间**: 4 周
**范围**: 核心功能 + 基础架构

### 8.2 Phase 2 (v1.5)

**时间**: MVP 后 2 周
**范围**: 扩展功能 + 性能优化

### 8.3 Phase 3 (v2.0)

**时间**: Phase 2 后 4 周
**范围**: 高级功能 + 生态集成

---

## 9. 成功指标

| 指标 | 目标 | 测量方式 |
|:---|:---|:---|
| **用户增长** | 月活用户 1000+ | Analytics |
| **留存率** | 7 日留存 40%+ | Analytics |
| **满意度** | NPS 50+ | 用户调研 |
| **性能** | API 响应 < 200ms | APM |

### 9.1 经营与产品指标补充

{self._generate_business_kpis()}

---

## 10. 风险与限制

### 10.1 技术风险

{self._generate_technical_risks()}

### 10.2 业务风险

{self._generate_business_risks()}

### 10.3 依赖限制

{self._generate_dependencies()}

### 10.4 上线前置条件

{self._generate_launch_dependencies()}

---

## 附录

### A. 术语表

{self._generate_glossary()}

### B. 参考文档

{self._generate_references()}

### C. 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|:---|:---|:---|:---|
| v2.4.0 | {datetime.now().strftime('%Y-%m-%d')} | 初始版本 | Super Dev |
"""

        # 追加 Prompt 模板版本标记
        if self._template_mgr:
            try:
                template = self._template_mgr.get_template("prd-generator")
                doc += f"\n\n<!-- Generated with prompt template: prd-generator v{template.version} -->\n"
            except Exception:
                pass

        return doc

    def generate_architecture(self) -> str:
        """生成架构设计文档"""
        doc = f"""# {self.name} - 架构设计文档

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **版本**: v2.4.0
> **架构师**: Super Dev ARCHITECT 专家

---

## 1. 架构概述

### 1.1 系统目标

- **可扩展性**: 支持水平扩展，应对业务增长
- **可用性**: 99.9% 系统可用性
- **性能**: 低延迟、高吞吐
- **安全性**: 端到端安全防护

### 1.2 架构原则

1. **服务拆分**: 按业务领域拆分微服务
2. **数据库分离**: 读写分离、缓存层
3. **异步处理**: 消息队列解耦
4. **监控运维**: 全链路追踪、实时告警

### 1.3 需求到架构的落地映射

{self._generate_architecture_fit()}

### 1.4 架构选型取舍与证据链

{self._generate_architecture_decision_matrix()}

### 1.5 架构决策账本

{self._generate_architecture_ledger()}

{self._generate_knowledge_constraints_section()}

### 1.6 Agent 执行流水线（全端）

{self._generate_agent_delivery_pipeline()}

---

## 2. 技术栈

### 2.0 语言工程策略

- **业务偏好语言**: {self._language_preferences_inline()}
- **落地策略**: 文档、Spec 与实现建议优先按偏好语言输出；跨模块场景可混合使用最合适语言。

### 2.1 前端技术栈

| 层级 | 技术选型 | 说明 |
|:---|:---|:---|
| **框架** | {self.frontend.title()} | 组件化开发 |
| **状态管理** | {self._get_state_management()} | 全局状态管理 |
| **UI 框架** | {self._get_ui_library()} | 组件库 |
| **构建工具** | {self._get_build_tool()} | 打包构建 |
| **HTTP 客户端** | Axios | API 请求 |
| **路由** | React Router | 页面路由 |

### 2.2 后端技术栈

| 层级 | 技术选型 | 说明 |
|:---|:---|:---|
| **运行时** | {self.backend.title()} | 服务器运行时 |
| **框架** | {self._get_backend_framework()} | Web 框架 |
| **API 规范** | RESTful | 接口设计 |
| **认证** | JWT | Token 认证 |
| **ORM** | {self._get_orm()} | 数据库 ORM |
| **验证** | Joi/Zod | 数据验证 |

{self._generate_ai_ml_stack()}

### 2.3 数据存储

| 存储 | 技术选型 | 用途 |
|:---|:---|:---|
| **主数据库** | {self._get_database()} | 持久化存储 |
| **缓存** | Redis | 缓存层 |
| **文件存储** | {self._get_file_storage()} | 文件/图片 |
| **搜索** | Elasticsearch | 全文搜索 |

### 2.4 基础设施

| 组件 | 技术选型 | 说明 |
|:---|:---|:---|
| **容器化** | Docker | 应用容器 |
| **编排** | Kubernetes | 容器编排 |
| **CI/CD** | GitHub Actions | 持续集成 |
| **监控** | Prometheus + Grafana | 指标监控 |
| **日志** | ELK Stack | 日志分析 |
| **追踪** | Jaeger | 分布式追踪 |

---

## 3. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                       用户层                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Web App  │  │ iOS App  │  │ Android  │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
└───────┼────────────┼────────────┼────────────────────────┘
        │            │            │
┌───────┼────────────┼────────────┼────────────────────────┐
│       │    CDN     │            │                      │
│  ┌────▼────────────┴────────┐    │                      │
│  │      负载均衡器          │    │                      │
│  └──────┬────────────────────┘    │                      │
└─────────┼─────────────────────────┼──────────────────────┘
          │                         │
┌─────────┼─────────────────────────┼──────────────────────┐
│         │      API 网关层         │                      │
│  ┌──────▼─────────────────────────▼──┐                   │
│  │  API Gateway (Kong / Nginx)      │                   │
│  │  - 认证授权                     │                   │
│  │  - 限流熔断                     │                   │
│  │  - 路由转发                     │                   │
│  └──────┬────────────────────────────┘                   │
└─────────┼──────────────────────────────────────────────┘
          │
┌─────────┼──────────────────────────────────────────────┐
│         │      服务层                                  │
│  ┌──────▼──────┐  ┌──────────┐  ┌──────────┐          │
│  │   API 服务  │  │ Auth 服务 │  │ User 服务 │  ...    │
│  └─────────────┘  └──────────┘  └──────────┘          │
└─────────┼──────────────────────────────────────────────┘
          │
┌─────────┼──────────────────────────────────────────────┐
│         │      数据层                                  │
│  ┌──────▼──────┐  ┌──────────┐  ┌──────────┐          │
│  │ PostgreSQL  │  │  Redis   │  │   S3     │          │
│  └─────────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 分层架构

#### 3.2.1 表现层 (Presentation Layer)

- **职责**: 用户界面、交互逻辑
- **技术**: {self.frontend.title()} + {self._get_ui_library()}
- **组件**:
  - 页面组件 (Pages)
  - 业务组件 (Components)
  - 布局组件 (Layouts)
  - 服务层 (Services)

#### 3.2.2 API 层 (API Layer)

- **职责**: 请求处理、协议转换
- **技术**: {self._get_backend_framework()}
- **组件**:
  - 路由定义
  - 中间件
  - 控制器
  - 请求验证

#### 3.2.3 业务层 (Business Layer)

- **职责**: 业务逻辑、规则引擎
- **组件**:
  - 服务
  - 领域模型
  - 业务规则
  - 工作流引擎

#### 3.2.4 数据访问层 (Data Access Layer)

- **职责**: 数据持久化、缓存管理
- **技术**: {self._get_orm()} + Redis
- **组件**:
  - Repository
  - DAO
  - Cache Manager
- Transaction Manager

### 3.3 关键时序图

{self._generate_sequence_diagram()}

---

## 4. 核心模块设计

### 4.1 认证授权模块

{self._generate_auth_module_design()}

### 4.2 用户管理模块

{self._generate_user_module_design()}

### 4.3 业务模块

{self._generate_business_module_design()}

### 4.4 领域边界与职责拆分

{self._generate_domain_boundaries()}

---

## 5. 数据库设计

### 5.1 数据库选型

**主数据库**: PostgreSQL
- 理由: 成熟稳定、功能丰富、ACID 支持
- 版本: PostgreSQL 14+

**缓存**: Redis
- 理由: 高性能、数据结构丰富
- 用途: 会话存储、热点数据缓存

### 5.2 表结构设计

{self._generate_database_schema()}

### 5.3 索引策略

{self._generate_index_strategy()}

---

## 6. API 设计

### 6.1 RESTful 规范

```
GET    /api/resources          # 列表
GET    /api/resources/:id      # 详情
POST   /api/resources          # 创建
PUT    /api/resources/:id      # 更新
PATCH  /api/resources/:id      # 部分更新
DELETE /api/resources/:id      # 删除
```

### 6.2 核心 API 端点

{self._generate_api_endpoints()}

### 6.3 错误码规范

```
200 OK               # 成功
201 Created          # 创建成功
400 Bad Request      # 请求错误
401 Unauthorized     # 未认证
403 Forbidden        # 无权限
404 Not Found        # 不存在
422 Unprocessable   # 验证失败
500 Server Error     # 服务器错误
```

### 6.4 集成契约与版本策略

{self._generate_integration_contracts()}

---

## 7. 安全设计

### 7.1 认证机制

- **方式**: JWT (JSON Web Token)
- **流程**:
  1. 用户登录获取 Token
  2. 请求携带 Token
  3. 服务验证 Token
  4. Token 过期重新获取

### 7.2 授权机制

- **模型**: RBAC (Role-Based Access Control)
- **角色**:
  - 超级管理员
  - 管理员
  - 普通用户
  - 访客

### 7.3 数据加密

- **传输加密**: TLS 1.3
- **存储加密**: AES-256
- **密码加密**: bcrypt

### 7.4 安全防护

- **SQL 注入**: 参数化查询
- **XSS**: 输出转义
- **CSRF**: Token 验证
- **限流**: 令牌桶算法

---

## 8. 性能设计

### 8.1 性能目标

| 指标 | 目标值 |
|:---|:---|
| **API 响应时间** | P50 < 100ms, P95 < 200ms, P99 < 500ms |
| **页面加载时间** | FCP < 1.5s, LCP < 2.5s |
| **并发用户** | 1000+ 并发 |
| **QPS** | 5000+ QPS |

### 8.2 性能优化策略

{self._generate_performance_optimization()}

### 8.3 容错与降级策略

{self._generate_failure_strategy()}

---

## 9. 可观测性

### 9.1 监控指标

- **系统指标**: CPU、内存、磁盘、网络
- **应用指标**: QPS、响应时间、错误率
- **业务指标**: DAU、订单量、转化率

### 9.2 日志规范

- **格式**: JSON
- **级别**: DEBUG, INFO, WARN, ERROR
- **内容**: 时间戳、级别、消息、上下文

### 9.3 告警策略

- **告警渠道**: 邮件、钉钉、PagerDuty
- **告警级别**: P0-P4
- **响应时间**: P0 < 15min, P1 < 30min

### 9.4 审计与可追溯性

{self._generate_audit_strategy()}

---

## 10. 部署架构

### 10.1 容器化

```dockerfile
# 多阶段构建
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package*.json ./
RUN npm ci --production
EXPOSE 3000
CMD ["npm", "start"]
```

### 10.2 Kubernetes 部署

{self._generate_k8s_config()}

### 10.3 CI/CD 流程

```yaml
# GitHub Actions
name: CI/CD
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: npm test
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: kubectl apply -f k8s/
```

### 10.4 发布与回滚策略

{self._generate_release_strategy()}

---

## 附录

### A. 技术选型对比

{self._generate_tech_comparison()}

### B. 架构决策记录 (ADR)

{self._generate_adr()}

### C. 参考文档

- [12-Factor App](https://12factor.net/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [REST API Design](https://restfulapi.net/)
"""

        # 追加 Prompt 模板版本标记
        if self._template_mgr:
            try:
                template = self._template_mgr.get_template("architecture-generator")
                doc += f"\n\n<!-- Generated with prompt template: architecture-generator v{template.version} -->\n"
            except Exception:
                pass

        # 自动生成 ADR 文件（失败不影响文档生成）
        try:
            from .adr_generator import ADRGenerator

            adr_gen = ADRGenerator(Path.cwd())
            adrs = adr_gen.generate_from_architecture(
                {
                    "database": (
                        self.backend
                        if "sql" in self.backend.lower() or "postgres" in self.backend.lower()
                        else "postgresql"
                    ),
                    "frontend": self.frontend,
                    "backend": self.backend,
                    "platform": self.platform,
                }
            )
            adr_gen.save_all(adrs)
        except Exception:
            logger.debug("ADR 自动生成失败，跳过")

        return doc

    def generate_uiux(self) -> str:
        """生成智能 UI/UX 设计文档（基于设计引擎推荐）"""
        # 获取智能设计推荐
        recommendations = self._get_design_recommendations()
        analysis = self._analyze_project_for_design()
        ui_intelligence = self._get_ui_intelligence(analysis)
        design_system_bundle = self._get_design_system_bundle(analysis, ui_intelligence)

        # 构建文档
        doc_parts = []

        # 文档头部
        doc_parts.append(
            f"""# {self.name} - UI/UX 设计文档

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **版本**: v2.4.0
> **设计师**: Super Dev UI/UX 专家

---

## 0. 设计分析

### 0.1 项目特征

基于需求描述，AI 分析出以下项目特征：

| 特征 | 分析结果 | 说明 |
|:---|:---|:---|
| **产品类型** | {analysis['product_type'].title()} | {self._get_product_type_desc(analysis['product_type'])} |
| **行业领域** | {analysis['industry'].title()} | {self._get_industry_desc(analysis['industry'])} |
| **风格倾向** | {analysis['style'].title()} | {self._get_style_desc(analysis['style'])} |
| **技术栈** | {self.frontend.upper()} | 前端框架 |
| **语言偏好** | {self._language_preferences_inline()} | 生成文档与实现建议的优先语言 |

### 0.2 设计推荐摘要

AI 基于项目特征，从设计数据库中为您推荐：

"""
        )

        # 添加推荐摘要
        if recommendations.get("styles"):
            doc_parts.append(
                f"""**推荐风格**: {', '.join([s.get('name', s.get('Style Category', 'Unknown')) for s in recommendations['styles'][:2]])}
"""
            )

        if recommendations.get("colors"):
            color = recommendations["colors"]
            doc_parts.append(
                f"""**推荐配色**: {color.get('name', color.get('Palette Name', 'Standard'))}
"""
            )

        if recommendations.get("fonts"):
            doc_parts.append(
                f"""**推荐字体**: {', '.join([f.get('Font Pairing Name', 'Professional') for f in recommendations['fonts'][:2]])}
"""
            )

        doc_parts.append(
            f"""**推荐组件生态**: {ui_intelligence['primary_library']['name']}
"""
        )

        doc_parts.append(
            f"""
---

## 1. 设计概述

### 1.1 设计理念

{self._generate_design_principles(analysis)}

### 1.2 设计原则

1. **视觉层级清晰**: 通过字号、字重、颜色和间距建立信息优先级，用户无需思考即可找到关键内容
2. **交互反馈即时**: 每个操作（点击、悬停、提交）都有明确的视觉或动效反馈，消除操作不确定性
3. **移动优先响应式**: 从 375px 开始设计，逐步增强到桌面端，确保核心流程在任何设备上完整可用
4. **无障碍合规**: 符合 WCAG 2.1 AA，对比度 4.5:1+，可见焦点态，键盘可达，支持 reduced-motion

{self._generate_knowledge_constraints_section()}

### 1.3 商业级 UI 执行红线（强制）

1. **禁止 AI 模板化视觉**：禁止直接输出同质化模板页面与缺少信息层级的“拼块式 UI”。
2. **默认避免紫/粉渐变主视觉**：除非品牌规范明确要求、用户主动偏好或产品定位确实适合，否则不建议把紫色或粉色渐变作为主品牌视觉。
3. **禁止 emoji 充当功能图标**：功能图标统一使用专业 SVG 图标库（如 Lucide/Heroicons/Tabler）。
4. **非对话产品默认避免 Claude / ChatGPT 同款界面骨架**：如果产品不是聊天工具，默认不应直接复用灰黑侧栏聊天布局、窄中栏会话壳层和同款中性色配色；如确有理由采用，必须在 UIUX 文档中解释适配原因。
5. **必须先冻结图标系统**：在页面设计前明确图标库、使用边界和替换策略，功能按钮不得临时混入 emoji。
6. **禁止默认系统字体直出**：必须在文档中明确品牌字体组合与字号层级，页面必须体现明确字重与层级节奏。
7. **必须具备可访问交互**：可见 focus 态、可读对比度、键盘可达、并兼容 reduced-motion。
8. **必须有设计 token**：颜色、间距、圆角、阴影和动效时长需以 token 形式统一管理。

### 1.4 商业级体验目标

{self._generate_ui_strategy(ui_intelligence)}

### 1.5 设计 Intelligence 结论

{self._render_ui_intelligence_summary(ui_intelligence)}

{self._render_ui_decision_manifest(ui_intelligence, design_system_bundle)}

{self._render_screen_recipe_manifest(analysis, ui_intelligence)}

{self._render_design_execution_protocol(analysis, ui_intelligence)}

---

## 2. 设计系统

### 2.1 色彩规范

"""
        )

        # 智能配色推荐
        if recommendations.get("colors"):
            color = recommendations["colors"]
            doc_parts.append(
                f"""#### 推荐配色方案: {color.get('name', 'Professional Palette')}

**推荐理由**: 基于 {analysis['industry']} {analysis['product_type']} 产品的最佳实践

| 颜色 | 用途 | Hex | 备注 |
|:---|:---|:---|:---|
| **Primary** | 主要操作、强调 | {color.get('primary', color.get('Primary (Hex)', '#2563EB'))} | 主色调 |
| **Secondary** | 次要操作 | {color.get('secondary', color.get('Secondary (Hex)', '#64748B'))} | 辅助色 |
| **CTA** | 行动号召 | {color.get('accent', color.get('CTA (Hex)', '#2563EB'))} | 转化按钮 |
| **Background** | 页面背景 | {color.get('background', color.get('Background (Hex)', '#F9FAFB'))} | 背景色 |
| **Text** | 正文文本 | {color.get('text', color.get('Text (Hex)', '#111827'))} | 文本色 |
| **Border** | 边框线条 | {color.get('border', color.get('Border (Hex)', '#E5E7EB'))} | 分割线 |

**Tailwind 配置**:
```javascript
// tailwind.config.js
module.exports = {{
  theme: {{
    extend: {{
      colors: {{
        primary: '{color.get('primary', color.get('Primary (Hex)', '#2563EB'))}',
        secondary: '{color.get('secondary', color.get('Secondary (Hex)', '#64748B'))}',
        cta: '{color.get('accent', color.get('CTA (Hex)', '#2563EB'))}',
      }}
    }}
  }}
}}
```

"""
            )
            primary_hex = color.get("primary", color.get("Primary (Hex)", "#2563EB"))
            doc_parts.append(
                f"""
#### 色阶系统

| 梯度 | Primary | Neutral | 用途 |
|:---|:---|:---|:---|
| **50** | {self._lighten(primary_hex, 0.95)} | #F9FAFB | 最浅背景 |
| **100** | {self._lighten(primary_hex, 0.9)} | #F3F4F6 | 悬停背景 |
| **200** | {self._lighten(primary_hex, 0.8)} | #E5E7EB | 边框 |
| **300** | {self._lighten(primary_hex, 0.7)} | #D1D5DB | 禁用文本 |
| **400** | {self._lighten(primary_hex, 0.6)} | #9CA3AF | 占位文本 |
| **500** | {primary_hex} | #6B7280 | 主色 |
| **600** | {self._darken(primary_hex, 0.85)} | #4B5563 | 次要文本 |
| **700** | {self._darken(primary_hex, 0.7)} | #374151 | 标题文本 |
| **800** | {self._darken(primary_hex, 0.55)} | #1F2937 | 正文文本 |
| **900** | {self._darken(primary_hex, 0.4)} | #111827 | 最深文本 |

#### 语义色

| 语义 | 颜色 | 背景 | 用途 |
|:---|:---|:---|:---|
| **Success** | #059669 | #ECFDF5 | 成功状态、完成提示 |
| **Warning** | #D97706 | #FFFBEB | 警告提示、注意事项 |
| **Error** | #DC2626 | #FEF2F2 | 错误状态、删除确认 |
| **Info** | #2563EB | #EFF6FF | 信息提示、引导说明 |

---

"""
            )
        else:
            # 默认配色
            doc_parts.append(
                """#### 主色调

| 颜色 | 用途 | Hex | RGB |
|:---|:---|:---|:---|
| **Primary** | 主要操作、强调 | #2563EB | rgb(37, 99, 235) |
| **Secondary** | 次要操作 | #64748B | rgb(100, 116, 139) |
| **Success** | 成功状态 | #10B981 | rgb(16, 185, 129) |
| **Warning** | 警告状态 | #F59E0B | rgb(245, 158, 11) |
| **Error** | 错误状态 | #EF4444 | rgb(239, 68, 68) |

"""
            )
            doc_parts.append(
                f"""
#### 色阶系统

| 梯度 | Primary | Neutral | 用途 |
|:---|:---|:---|:---|
| **50** | {self._lighten('#2563EB', 0.95)} | #F9FAFB | 最浅背景 |
| **100** | {self._lighten('#2563EB', 0.9)} | #F3F4F6 | 悬停背景 |
| **200** | {self._lighten('#2563EB', 0.8)} | #E5E7EB | 边框 |
| **300** | {self._lighten('#2563EB', 0.7)} | #D1D5DB | 禁用文本 |
| **400** | {self._lighten('#2563EB', 0.6)} | #9CA3AF | 占位文本 |
| **500** | #2563EB | #6B7280 | 主色 |
| **600** | {self._darken('#2563EB', 0.85)} | #4B5563 | 次要文本 |
| **700** | {self._darken('#2563EB', 0.7)} | #374151 | 标题文本 |
| **800** | {self._darken('#2563EB', 0.55)} | #1F2937 | 正文文本 |
| **900** | {self._darken('#2563EB', 0.4)} | #111827 | 最深文本 |

#### 语义色

| 语义 | 颜色 | 背景 | 用途 |
|:---|:---|:---|:---|
| **Success** | #059669 | #ECFDF5 | 成功状态、完成提示 |
| **Warning** | #D97706 | #FFFBEB | 警告提示、注意事项 |
| **Error** | #DC2626 | #FEF2F2 | 错误状态、删除确认 |
| **Info** | #2563EB | #EFF6FF | 信息提示、引导说明 |

---

"""
            )

        # 智能字体推荐
        doc_parts.append(
            """### 2.2 字体规范
"""
        )

        if recommendations.get("fonts"):
            doc_parts.append(
                """#### 推荐字体组合

"""
            )
            for font in recommendations["fonts"][:2]:
                doc_parts.append(
                    f"""**{font.get('name', font.get('Font Pairing Name', 'Professional'))}**
- **Heading**: {font.get('heading_font', font.get('Heading Font', 'Inter'))}
- **Body**: {font.get('body_font', font.get('Body Font', 'Roboto'))}
- **风格**: {font.get('mood', font.get('Mood/Style Keywords', 'Professional'))}
- **适用**: {font.get('best_for', font.get('Best For', 'General purpose'))}

**Google Fonts 导入**:
```html
{font.get('css_import', font.get('CSS Import', '<link href="https://fonts.googleapis.cn/css2?family=Manrope:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet">'))}
```

"""
                )

        # Always add full typography scale
        doc_parts.append(
            """#### 字号层级

| 级别 | 大小 | 字重 | 行高 | 字间距 | 用途 |
|:---|:---|:---|:---|:---|:---|
| **Display** | 48px / 3rem | 800 | 1.1 | -0.02em | 首屏大标题 |
| **H1** | 36px / 2.25rem | 700 | 1.2 | -0.015em | 页面标题 |
| **H2** | 28px / 1.75rem | 600 | 1.25 | -0.01em | 章节标题 |
| **H3** | 22px / 1.375rem | 600 | 1.3 | 0 | 卡片/模块标题 |
| **H4** | 18px / 1.125rem | 600 | 1.35 | 0 | 小标题 |
| **Body Large** | 18px / 1.125rem | 400 | 1.6 | 0 | 正文大字 |
| **Body** | 16px / 1rem | 400 | 1.5 | 0 | 正文 |
| **Body Small** | 14px / 0.875rem | 400 | 1.5 | 0 | 辅助文本 |
| **Caption** | 12px / 0.75rem | 500 | 1.4 | 0.02em | 标签、注释 |
| **Overline** | 11px / 0.6875rem | 700 | 1.6 | 0.08em | 分类标签（大写） |

---

"""
        )

        doc_parts.append(
            f"""
{self._render_design_token_freeze_output(ui_intelligence, design_system_bundle)}

"""
        )

        if not recommendations.get("fonts"):
            doc_parts.append(
                """#### 字体家族

```css
font-family: 'Plus Jakarta Sans', 'Noto Sans SC', 'PingFang SC', 'Segoe UI', sans-serif;
```

"""
            )

        # 间距和圆角规范保持不变
        doc_parts.append(
            f"""### 2.3 间距规范

使用 8px 基础单位:
- **xs**: 4px
- **sm**: 8px
- **md**: 16px
- **lg**: 24px
- **xl**: 32px
- **2xl**: 48px

### 2.4 圆角规范

| 元素 | 圆角 |
|:---|:---|
| **按钮** | 8px |
| **卡片** | 12px |
| **输入框** | 8px |
| **弹窗** | 16px |
| **标签/徽章** | 6px |
| **头像** | 9999px（全圆） |

### 2.5 组件样式规范（宿主必须遵守）

#### 按钮系统

| 变体 | 背景 | 文字 | 圆角 | 高度 | 阴影 | Hover |
|:---|:---|:---|:---|:---|:---|:---|
| **Primary** | primary-500 | white | 8px | 40px | sm | primary-600 + shadow-md |
| **Secondary** | white | neutral-700 | 8px | 40px | ring-1 neutral-200 | neutral-50 bg |
| **Ghost** | transparent | neutral-600 | 8px | 40px | none | neutral-100 bg |
| **Destructive** | error-500 | white | 8px | 40px | sm | error-600 |
| **CTA (大)** | primary-500 | white | 12px | 48px | md | primary-600 + scale-[1.02] |

#### 卡片系统

```css
/* 标准卡片 */
.card {{
  background: white;
  border: 1px solid var(--neutral-200);
  border-radius: 12px;
  padding: 24px;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}}
.card:hover {{
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}}

/* 高亮卡片（推荐/当前选中） */
.card-featured {{
  border: 2px solid var(--primary-500);
  box-shadow: 0 0 0 4px var(--primary-50);
}}
```

#### 表单输入

```css
.input {{
  height: 40px;
  padding: 8px 12px;
  border: 1px solid var(--neutral-300);
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.15s, box-shadow 0.15s;
}}
.input:focus {{
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--primary-100);
  outline: none;
}}
.input-error {{
  border-color: var(--error-500);
  box-shadow: 0 0 0 3px var(--error-50);
}}
```

#### 阴影层级

| 层级 | CSS | 用途 |
|:---|:---|:---|
| **shadow-xs** | `0 1px 2px rgba(0,0,0,0.05)` | 输入框、小元素 |
| **shadow-sm** | `0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)` | 按钮、标签 |
| **shadow-md** | `0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)` | 卡片、下拉菜单 |
| **shadow-lg** | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | 弹窗、浮层 |
| **shadow-xl** | `0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)` | 模态框 |

#### 动效规范

| 类型 | 时长 | 缓动 | 用途 |
|:---|:---|:---|:---|
| **micro** | 100ms | ease-out | 颜色、透明度变化 |
| **short** | 200ms | ease-in-out | hover、focus 状态 |
| **medium** | 300ms | ease-in-out | 展开、收起、切换 |
| **long** | 500ms | cubic-bezier(0.4, 0, 0.2, 1) | 页面过渡、模态框 |

### 2.6 视觉方向与品牌感

{self._generate_visual_direction()}

### 2.7 布局栅格与密度策略

{self._generate_layout_system(ui_intelligence)}

### 2.8 组件生态与实现基线

{self._render_component_ecosystem(ui_intelligence)}

### 2.9 组件库使用规范

{self._generate_component_library_guide(ui_intelligence)}

### 2.10 多端适配与平台化设计策略

{self._render_cross_platform_strategy(ui_intelligence)}

### 2.11 商业级设计质量门禁

{self._render_ui_quality_gate(ui_intelligence)}

### 2.12 精美 UI 执行工作流（Stitch 范式）

{self._render_ui_execution_workflow(ui_intelligence)}

---

## 3. 页面结构

### 3.1 整体布局
"""
        )

        # 如果有 Landing 页面推荐，添加它
        if recommendations.get("landing"):
            landing = recommendations["landing"]
            landing_sections = landing.get("sections", "")
            if isinstance(landing_sections, list):
                landing_sections_text = "\n".join(
                    f"- {s.get('name', s)}" if isinstance(s, dict) else f"- {s}"
                    for s in landing_sections[:8]
                )
            else:
                landing_sections_text = str(landing_sections)

            cta_strategy = landing.get("cta_strategy", {})
            if isinstance(cta_strategy, dict):
                cta_strategy_text = ", ".join(f"{k}: {v}" for k, v in cta_strategy.items())
            else:
                cta_strategy_text = str(cta_strategy)

            doc_parts.append(
                f"""
#### 推荐页面布局: {landing.get('name', 'Standard Layout')}

**布局类型**: {landing.get('category', 'classic').title()}

**页面结构**:
{landing_sections_text}

**CTA 策略**: {cta_strategy_text}

**转化优化**:
{chr(10).join(f"- {tip}" for tip in landing.get('conversion_tips', [])[:5])}

**适用场景**: {', '.join(landing.get('best_for', [])[:3])}

---

"""
            )
        else:
            doc_parts.append(
                """
```
┌─────────────────────────────────────────────────┐
│  Header (Logo, Nav, User)                       │
├──────────┬──────────────────────────────────────┤
│          │                                       │
│ Sidebar  │         Main Content                 │
│ (Nav)    │                                       │
│          │                                       │
│          │                                       │
├──────────┴──────────────────────────────────────┤
│  Footer                                          │
└─────────────────────────────────────────────────┘
```

---

"""
            )

        # 添加其他部分（保持原有的内容结构）
        doc_parts.append(
            f"""### 3.2 页面骨架优先级

{self._render_page_blueprints(ui_intelligence)}

### 3.3 导航结构

{self._generate_navigation_structure()}

---

## 4. 核心页面设计

### 4.1 登录页面

{self._generate_login_page_design()}

### 4.2 列表页面

{self._generate_list_page_design()}

### 4.3 详情页面

{self._generate_detail_page_design()}

### 4.4 表单页面

{self._generate_form_page_design()}

---

## 5. 组件设计

### 5.1 基础组件

{self._generate_base_components()}

### 5.2 业务组件

{self._generate_business_components()}

### 5.3 组件状态矩阵

{self._generate_component_state_matrix()}

### 5.4 图标、图表与内容模块

{self._render_visual_assets_strategy(ui_intelligence)}

### 5.5 组件落地清单（Tailwind / 生态组件）

{self._render_component_implementation_manifest(ui_intelligence)}

---

## 6. 交互设计

### 6.1 加载状态

- **页面加载**: 骨架屏
- **按钮加载**: Spinner + 禁用
- **数据加载**: Loading 动画

### 6.2 错误处理

- **网络错误**: 友好提示 + 重试按钮
- **表单错误**: 字段级提示
- **系统错误**: 错误页面 + 返回按钮

### 6.3 空状态

- **无数据**: 空状态插图 + 引导文案
- **搜索无结果**: 提示 + 清空按钮

### 6.4 动效与反馈系统

{self._generate_motion_system(ui_intelligence)}

---

## 7. 响应式设计

### 7.1 断点定义

| 设备 | 宽度 | 说明 |
|:---|:---|:---|
| **Mobile** | < 640px | 手机竖屏 |
| **Tablet** | 640px - 1024px | 平板/手机横屏 |
| **Desktop** | 1024px - 1440px | 桌面 |
| **Large** | > 1440px | 大屏 |

### 7.2 响应式策略

- **Mobile First**: 从小屏开始设计
- **流式布局**: Flexbox + Grid
- **响应式图片**: srcset + sizes
- **响应式字体**: clamp() 函数

### 7.3 商业化与信任设计

{self._generate_trust_and_conversion_rules(ui_intelligence)}

---

## 8. 用户流程

### 8.1 主要用户旅程

{self._generate_user_journeys_ui()}

### 8.2 交互流程图

```
用户 → [页面] → [操作] → [反馈] → [下一步]
```

---

## 9. 微交互

### 9.1 按钮交互

- **悬停**: 背景色变化
- **点击**: 缩放动画
- **禁用**: 透明度降低

### 9.2 表单交互

- **聚焦**: 边框高亮
- **输入**: 实时验证
- **提交**: Loading 状态

### 9.3 列表交互

- **悬停**: 操作按钮显示
- **点击**: 选中状态
- **拖拽**: 视觉反馈

---

## 10. 设计交付物

### A. 设计资产

- Figma 设计稿链接
- 图标库 (Heroicons / Lucide)
- 图片资源 (Unsplash / Pexels)

### B. 插件资源

- {ui_intelligence['primary_library']['name']} 组件生态
- Figma 插件推荐

### C. 设计参考

- [Dribbble](https://dribbble.com/)
- [Behance](https://www.behance.net/)
- [Mobbin](https://mobbin.com/)
"""
        )

        # 添加 UX 最佳实践部分
        if recommendations.get("ux_tips"):
            doc_parts.append(
                """

---

## 11. UX 最佳实践

基于项目特征，AI 为您推荐以下 UX 最佳实践：

"""
            )
            for i, tip in enumerate(recommendations["ux_tips"][:5], 1):
                guideline = tip.get("guideline", tip)
                domain = guideline.get("domain", "UX")
                domain_text = domain.value if hasattr(domain, "value") else str(domain)
                complexity = guideline.get("complexity", "medium")
                complexity_text = str(complexity).title()
                doc_parts.append(
                    f"""### {i}. {guideline.get('topic', 'Best Practice')} ({domain_text})

**最佳实践**:
{guideline.get('best_practice', 'Follow industry standards')}

**避免**:
{guideline.get('anti_pattern', 'Common mistakes to avoid')}

**影响**: {guideline.get('impact', 'Improved user experience')}

**实施难度**: {complexity_text}

"""
                )

        doc = "\n".join(doc_parts)

        # 追加 Prompt 模板版本标记
        if self._template_mgr:
            try:
                template = self._template_mgr.get_template("uiux-generator")
                doc += f"\n\n<!-- Generated with prompt template: uiux-generator v{template.version} -->\n"
            except Exception:
                pass

        return doc
