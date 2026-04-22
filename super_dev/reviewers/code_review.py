"""
代码审查指南生成器 - 生成项目特定的代码审查清单

开发：Excellent（11964948@qq.com）
功能：生成针对项目的代码审查指南和清单
作用：开发过程中和开发后进行代码审查
创建时间：2025-12-30
"""

from pathlib import Path
from typing import cast


class CodeReviewGenerator:
    """代码审查指南生成器"""

    def __init__(self, project_dir: Path, name: str, tech_stack: dict):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.tech_stack = tech_stack
        self.platform = tech_stack.get("platform", "web")
        self.frontend = tech_stack.get("frontend", "react")
        self.backend = tech_stack.get("backend", "node")
        self.domain = tech_stack.get("domain", "")

        # 加载专家工具箱以注入治理检查清单
        try:
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            self._code_toolkit = toolkits.get("CODE")
            self._security_toolkit = toolkits.get("SECURITY")
        except Exception:
            self._code_toolkit = None
            self._security_toolkit = None

    def generate(self) -> str:
        """生成代码审查指南"""
        review_guide = f"""# {self.name} - 代码审查指南

> **生成时间**: 自动生成
> **技术栈**: 前端 {self.frontend} | 后端 {self.backend} | 平台 {self.platform}

---

## 审查流程

### 第 1 步: 自动化检查
运行以下命令，确保所有检查通过：

```bash
# Linter
npm run lint  # 或 python -m pylint .

# 类型检查
npm run type-check  # 或 mypy .

# 格式检查
npm run format:check  # 或 black --check .

# 测试
npm test  # 或 pytest
```

### 第 2 步: 功能审查
- [ ] 代码实现了需求中的所有功能
- [ ] 边界条件处理正确
- [ ] 错误处理完善
- [ ] 日志记录恰当

### 第 3 步: 安全审查
- [ ] 输入验证完整
- [ ] 输出编码正确
- [ ] 认证授权正确实现
- [ ] 敏感数据已保护

### 第 4 步: 性能审查
- [ ] 无明显性能问题
- [ ] 数据库查询优化
- [ ] 缓存使用恰当
- [ ] 资源使用合理

---

## 通用审查项

### 代码质量

**命名规范:**
- [ ] 变量/函数命名清晰，见名知意
- [ ] 类名使用 PascalCase
- [ ] 函数名使用 camelCase (前端) 或 snake_case (后端)
- [ ] 常量使用 SCREAMING_SNAKE_CASE
- [ ] 布尔值使用 is/has/should 前缀

**函数设计:**
- [ ] 函数职责单一，不超过 50 行
- [ ] 参数数量合理 (不超过 5 个)
- [ ] 避免深层嵌套 (不超过 3 层)
- [ ] 返回值类型一致
- [ ] 无重复代码 (DRY 原则)

**错误处理:**
- [ ] 所有异常被捕获
- [ ] 错误信息清晰有用
- [ ] 不吞掉异常
- [ ] 资源正确释放 (使用 try-finally 或 with)
- [ ] 不返回 `null`/`None` 给前端 (使用统一错误响应)

**注释和文档:**
- [ ] 复杂逻辑有注释说明
- [ ] 公共 API 有文档注释
- [ ] TODO 注释有跟踪 issue
- [ ] 注释与代码保持一致

### 安全性

**输入验证:**
- [ ] 所有用户输入验证
- [ ] 验证类型、长度、格式
- [ ] 使用白名单而非黑名单
- [ ] SQL/命令注入防护 (使用参数化查询)

**认证授权:**
- [ ] 敏感操作需要认证
- [ ] 权限检查正确
- [ ] Token/Session 有效期合理
- [ ] HTTPS 强制使用

**数据保护:**
- [ ] 密码使用强哈希 (bcrypt/Argon2)
- [ ] 敏感数据不记录到日志
- [ ] 敏感数据不暴露给前端
- [ ] 加密存储敏感配置

### 性能

**数据库:**
- [ ] 查询使用索引
- [ ] 避免全列查询（优先明确列名）
- [ ] 避免 N+1 查询
- [ ] 使用连接池
- [ ] 分页大数据集

**API:**
- [ ] 响应大小合理
- [ ] 实施缓存策略
- [ ] 异步处理耗时操作
- [ ] 实施速率限制

**前端:**
- [ ] 避免不必要的重渲染
- [ ] 使用 React.memo/useMemo/useCallback
- [ ] 懒加载路由和组件
- [ ] 图片优化和懒加载

### 测试

**单元测试:**
- [ ] 核心逻辑有单元测试
- [ ] 测试覆盖率 > 80%
- [ ] 边界条件有测试
- [ ] 错误情况有测试

**集成测试:**
- [ ] API 端点有集成测试
- [ ] 关键流程有测试
- [ ] 数据库操作有测试

---

## 前端特定审查 ({self.frontend.upper()})

{self._generate_frontend_review()}

---

## 后端特定审查 ({self.backend.upper()})

{self._generate_backend_review()}

---

## 领域特定审查 ({self.domain.upper() if self.domain else "通用"})

{self._generate_domain_review()}

---

## 审查清单模板

### Pull Request 审查清单

**提交前自检:**
- [ ] 代码符合团队规范
- [ ] Linter 无错误
- [ ] 所有测试通过
- [ ] 新增代码有测试
- [ ] 文档已更新
- [ ] 本轮新增函数/方法/字段/模块都已接入真实调用链，未接入的已删除
- [ ] 本轮修改没有引入新的编译错误、构建失败或新增 warning
- [ ] 新增日志/埋点/告警/恢复逻辑已经挂到真实入口，不是只定义未调用
- [ ] 已按本次 diff 做过最小自审，确认不存在死代码、无效分支或遗留临时补丁

**Reviewers 检查:**
- [ ] 代码逻辑正确
- [ ] 无安全漏洞
- [ ] 无性能问题
- [ ] 错误处理完善
- [ ] 代码可维护

---

## 常见问题检查表

### 1. 空值处理
- [ ] 使用可选链 `?.` 访问属性
- [ ] 使用空值合并 `??` 提供默认值
- [ ] 函数参数验证空值
- [ ] 数据库查询结果检查空值

### 2. 异步处理
- [ ] async/await 正确使用
- [ ] Promise/异常正确处理
- [ ] 并发控制合理
- [ ] 超时处理设置

### 3. 资源管理
- [ ] 文件句柄正确关闭
- [ ] 数据库连接释放
- [ ] 订阅/监听器清理
- [ ] 定时器清理

### 4. 状态管理
- [ ] 状态不可变修改
- [ ] 状态更新正确
- [ ] 副作用隔离
- [ ] 状态持久化合理

### 5. 实现闭环
- [ ] 新增 helper、配置项、日志函数、埋点函数都存在明确调用点
- [ ] 新增兜底逻辑在真实异常路径上可达，不是形式化补丁
- [ ] 构建日志中的新 warning 已逐项处理，而不是默认忽略
- [ ] 代码审查结论覆盖“为什么加、在哪里用、如果不用是否该删”

---

## 审查工具

### 推荐工具

**前端 ({self.frontend}):**
- ESLint - 代码检查
- Prettier - 代码格式化
- TypeScript - 类型检查
- Jest - 单元测试

**后端 ({self.backend}):**
- pylint/flake8 - 代码检查
- black/autopep8 - 代码格式化
- mypy - 类型检查 (Python)
- pytest - 单元测试

### CI/CD 集成

在 CI 流水线中自动运行以下检查：

```yaml
# .github/workflows/review.yml
name: Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Lint
        run: npm run lint
      - name: Type Check
        run: npm run type-check
      - name: Test
        run: npm test -- --coverage
      - name: Security Scan
        run: npm audit
```

---

## 审查反馈模板

### 建设性反馈

**示例:**

> 我注意到在 `UserService.ts:45` 中，直接使用了 `user.email` 而没有检查 `user` 是否为 `null`。这可能导致运行时错误。
>
> 建议: 使用可选链 `user?.email` 或在函数开始时验证参数。
>
> 参考: https://github.com/our-team/frontend-handbook/blob/main/null-safety.md

### 需要修改的反馈

**示例:**

> [需要修改] 在 `AuthController.java:123` 中，SQL 查询使用了字符串拼接，存在 SQL 注入风险。
>
> 请修改为参数化查询:
> ```java
> // 错误：通过字符串拼接构造数据库查询语句
> String query = buildQueryByConcat(email);
>
> // 正确：使用参数占位符并绑定参数
> String query = buildPreparedQueryWithParams(email);
> ```
>
> 参考: OWASP SQL Injection Prevention Cheat Sheet

---

## 审查完成后

### 通过审查
- [ ] 批准并合并 PR
- [ ] 感谢贡献者
- [ ] 更新相关文档

### 需要修改
- [ ] 在 PR 中留下具体反馈
- [ ] 标注需要修改的文件和行号
- [ ] 提供修改建议和参考资料
- [ ] 设置修改后的截止时间

---

## 附录: 代码审查最佳实践

1. **及时响应**: 收到审查请求后 24 小时内完成审查
2. **建设性反馈**: 提供具体、可操作的改进建议
3. **尊重贡献者**: 评论针对代码而非个人
4. **讨论复杂问题**: 面对面或视频会议讨论
5. **持续学习**: 分享审查中学到的经验
"""

        # 注入技术栈差异化审查清单
        review_guide += self._generate_stack_specific_checklist()

        # 注入代码复杂度分析
        review_guide += self._generate_complexity_analysis()

        # 注入命名规范检查
        review_guide += self._generate_naming_convention_checks()

        # 注入专家 Playbook 具体检查项
        review_guide += self._generate_expert_playbook_checks()

        # 注入专家工具箱治理检查清单
        review_guide += self._inject_expert_checklists()

        return review_guide  # nosec B608

    def _generate_frontend_review(self) -> str:
        """生成前端特定审查内容"""
        if self.frontend == "react":
            return """
**React 特定:**
- [ ] 组件拆分合理 (不超过 200 行)
- [ ] Props 类型定义完整 (TypeScript/PropTypes)
- [ ] State 使用恰当 (useState/useReducer)
- [ ] Effect 依赖正确 (useEffect)
- [ ] Context 使用合理 (避免过度使用)
- [ ] 性能优化 (memo/useMemo/useCallback)
- [ ] Key 属性正确 (列表渲染)
- [ ] 事件处理函数稳定 (useCallback)

**Hooks 使用:**
- [ ] 自定义 Hook 可复用
- [ ] Hook 规则遵守 (只在顶层调用)
- [ ] Effect 依赖数组完整
- [ ] 清理函数正确返回

**状态管理:**
- [ ] 全局状态使用 Redux/Zustand
- [ ] 本地状态使用 useState
- [ ] 表单状态使用 Form 库
- [ ] 服务端状态使用 React Query/SWR
"""
        elif self.frontend == "vue":
            return """
**Vue 特定:**
- [ ] 组件拆分合理 (不超过 200 行)
- [ ] Props 类型定义完整
- [ ] Emits 事件声明完整
- [ ] Computed 使用恰当
- [ ] Watch 使用合理
- [ ] 生命周期钩子正确
- [ ] Ref/Reactive 使用正确

**Composition API:**
- [ ] `<script setup>` 语法使用
- [ ] Composable 函数可复用
- [ ] 响应式类型正确 (ref/reactive)
- [ ] 生命周期使用正确

**状态管理:**
- [ ] 全局状态使用 Pinia
- [ ] 本地状态使用 reactive/ref
- [ ] 表单状态使用 Form 库
"""
        else:
            return """
**通用前端:**
- [ ] 组件拆分合理
- [ ] Props 类型定义
- [ ] 状态管理清晰
- [ ] 事件处理正确
- [ ] 样式隔离良好
"""

    def _generate_backend_review(self) -> str:
        """生成后端特定审查内容"""
        if self.backend == "node":
            return """
**Node.js 特定:**
- [ ] 异步错误处理 (try-catch)
- [ ] Promise 正确使用
- [ ] 内存泄漏检查 (监听器清理)
- [ ] 依赖安全 (npm audit)
- [ ] 环境变量管理 (.env)
- [ ] 中间件顺序正确
- [ ] 请求体验证

**Express/NestJS:**
- [ ] 路由命名规范 (RESTful)
- [ ] 中间件职责单一
- [ ] 错误处理中间件
- [ ] 请求验证 (express-validator/class-validator)
- [ ] 响应格式统一
"""
        elif self.backend == "python":
            return """
**Python 特定:**
- [ ] 类型提示完整 (Type Hints)
- [ ] 异常处理具体
- [ ] 资源清理 (with 语句)
- [ ] 依赖安全 (pip audit)
- [ ] 虚拟环境使用
- [ ] PEP 8 规范遵守

**FastAPI/Django:**
- [ ] Pydantic 模型验证
- [ ] 路由命名规范 (RESTful)
- [ ] 中间件/装饰器使用
- [ ] 数据库会话管理
- [ ] 响应格式统一
"""
        else:
            return """
**通用后端:**
- [ ] API 设计 RESTful
- [ ] 请求验证完整
- [ ] 错误处理统一
- [ ] 日志记录恰当
- [ ] 依赖注入使用
"""

    def _generate_domain_review(self) -> str:
        """生成领域特定审查内容"""
        if self.domain == "fintech":
            return """
**金融领域特定:**
- [ ] 金额计算使用 Decimal 类型
- [ ] 货币转换正确
- [ ] 交易原子性保证
- [ ] 审计日志完整
- [ ] 合规性检查 (PCI-DSS)
- [ ] 敏感数据加密
- [ ] 防重放攻击
- [ ] 幂等性保证
"""
        elif self.domain == "medical":
            return """
**医疗领域特定:**
- [ ] HIPAA 合规性
- [ ] 患者隐私保护
- [ ] 数据加密存储
- [ ] 访问控制严格
- [ ] 审计日志完整
- [ ] 数据脱敏展示
- [ ] 紧急访问机制
"""
        elif self.domain == "ecommerce":
            return """
**电商领域特定:**
- [ ] 库存并发控制
- [ ] 订单幂等性
- [ ] 支付安全
- [ ] 价格精度处理
- [ ] 优惠券逻辑
- [ ] 促销规则验证
"""
        else:
            return """
**通用领域:**
- [ ] 业务规则正确
- [ ] 数据一致性
- [ ] 事务处理合理
- [ ] 幂等性保证
"""

    # ------------------------------------------------------------------
    # 技术栈差异化审查清单
    # ------------------------------------------------------------------

    def _generate_stack_specific_checklist(self) -> str:
        """根据技术栈生成差异化的深度审查清单。"""
        sections: list[str] = [
            "\n---\n",
            "## 技术栈深度审查清单（自动生成）\n",
        ]

        backend_lower = self.backend.lower() if self.backend else ""
        frontend_lower = self.frontend.lower() if self.frontend else ""

        if backend_lower in ("python", "fastapi", "django", "flask"):
            sections.extend(self._python_deep_checklist())
        if backend_lower in ("node", "express", "nestjs", "koa"):
            sections.extend(self._javascript_deep_checklist())
        if backend_lower in ("go", "golang", "gin", "echo"):
            sections.extend(self._go_deep_checklist())
        if backend_lower in ("rust", "actix", "axum", "rocket"):
            sections.extend(self._rust_deep_checklist())

        # 前端也可能需要 JS/TS 检查
        if frontend_lower in ("react", "vue", "angular", "svelte", "next", "nuxt"):
            sections.extend(self._frontend_typescript_checklist())

        return "\n".join(sections)

    def _python_deep_checklist(self) -> list[str]:
        return [
            "### Python 深度审查\n",
            "**类型安全:**",
            "- [ ] 所有公共函数签名有完整 type hints（参数 + 返回值）",
            "- [ ] 使用 `from __future__ import annotations` 延迟求值",
            "- [ ] 避免 `Any` 类型逃逸，必要时用 `TypeVar` 或 `Protocol`",
            "- [ ] dataclass/Pydantic model 字段类型明确",
            "- [ ] Optional 类型显式标注而非隐式 None",
            "",
            "**并发安全:**",
            "- [ ] asyncio 代码中无阻塞 I/O 调用（file/socket/requests）",
            "- [ ] 线程共享数据使用 Lock/RLock/Queue 保护",
            "- [ ] 避免在 async 函数中调用 `time.sleep()`（使用 `asyncio.sleep`）",
            "- [ ] 数据库连接池配置合理，避免连接泄漏",
            "",
            "**资源管理:**",
            "- [ ] 文件/网络/数据库连接使用 `with` 语句或 `contextmanager`",
            "- [ ] 临时文件使用 `tempfile` 模块并确保清理",
            "- [ ] 大数据集处理使用 generator/iterator 而非一次性加载",
            "",
            "**Python 特有陷阱:**",
            "- [ ] 默认参数不使用可变对象（`def f(x=[])`）",
            "- [ ] 字符串格式化优先使用 f-string 而非 `%` 或 `.format()`",
            "- [ ] 比较 None 使用 `is None` 而非 `== None`",
            "- [ ] 循环中不重复创建正则编译（使用 `re.compile` 缓存）",
            "- [ ] 避免裸 `except:` 或 `except Exception:`，捕获具体异常",
            "- [ ] `__init__` 中不执行耗时 I/O 操作",
            "",
        ]

    def _javascript_deep_checklist(self) -> list[str]:
        return [
            "### JavaScript/TypeScript 深度审查\n",
            "**类型安全 (TypeScript):**",
            "- [ ] 严格模式启用（`strict: true` in tsconfig）",
            "- [ ] 避免 `any` 类型，使用 `unknown` + type guard",
            "- [ ] 接口定义优于 type alias（用于对象结构）",
            "- [ ] 泛型约束明确（`T extends Base` 而非裸 `T`）",
            "- [ ] enum 使用 `const enum` 或字面量联合类型",
            "",
            "**异步处理:**",
            "- [ ] Promise 链有 `.catch()` 或外层 try-catch",
            "- [ ] 避免 Promise 构造函数反模式（`new Promise` 包裹 async）",
            "- [ ] 并发请求使用 `Promise.all` / `Promise.allSettled`",
            "- [ ] 避免 `async void` 函数（除事件处理器）",
            "- [ ] EventEmitter 监听器在组件卸载时移除",
            "",
            "**安全特有:**",
            "- [ ] 用户输入不直接拼接 HTML（防 XSS）",
            "- [ ] `dangerouslySetInnerHTML` 内容经过 DOMPurify 清洗",
            "- [ ] Cookie 设置 `httpOnly`, `secure`, `sameSite` 属性",
            "- [ ] `JSON.parse` 外层有 try-catch",
            "- [ ] URL 参数经过 `encodeURIComponent` 编码",
            "",
            "**Node.js 特有:**",
            "- [ ] 不在事件循环中执行 CPU 密集任务（使用 worker_threads）",
            "- [ ] Stream 处理有 `error` 事件监听",
            "- [ ] 进程退出处理 `SIGTERM`/`SIGINT` 优雅关闭",
            "- [ ] 环境变量通过 schema 验证（如 `envalid`）",
            "",
        ]

    def _go_deep_checklist(self) -> list[str]:
        return [
            "### Go 深度审查\n",
            "**错误处理:**",
            "- [ ] 所有 error 返回值被检查，不使用 `_` 忽略",
            "- [ ] 自定义错误类型实现 `error` 接口",
            "- [ ] 使用 `errors.Is` / `errors.As` 进行错误匹配",
            "- [ ] 错误信息小写开头，不以标点结尾",
            '- [ ] 使用 `fmt.Errorf("%w", err)` 进行错误包装',
            "",
            "**并发安全:**",
            "- [ ] goroutine 有退出机制（context/done channel）",
            "- [ ] 共享数据使用 `sync.Mutex` 或 channel 保护",
            "- [ ] `sync.WaitGroup` 计数器正确 Add/Done/Wait",
            "- [ ] 避免 goroutine 泄漏（检查 `runtime.NumGoroutine`）",
            "- [ ] channel 有明确的关闭责任方",
            "",
            "**性能:**",
            "- [ ] 大量字符串拼接使用 `strings.Builder`",
            "- [ ] 已知容量的 slice 预分配（`make([]T, 0, n)`）",
            "- [ ] 避免在热路径中使用 `reflect`",
            "- [ ] 大结构体传指针而非值拷贝",
            "",
            "**Go 特有陷阱:**",
            "- [ ] 循环变量捕获问题（Go <1.22 中 for 循环变量复用）",
            "- [ ] `defer` 在循环中的资源释放时机",
            "- [ ] nil interface vs nil pointer 比较",
            "- [ ] map 不安全并发读写（使用 `sync.Map` 或加锁）",
            "",
        ]

    def _rust_deep_checklist(self) -> list[str]:
        return [
            "### Rust 深度审查\n",
            "**所有权与借用:**",
            "- [ ] 避免不必要的 `.clone()` 调用",
            "- [ ] 优先使用引用（`&T`/`&mut T`）而非所有权转移",
            "- [ ] 生命周期标注最小化且正确",
            "- [ ] `Arc<Mutex<T>>` 仅在真正需要共享可变状态时使用",
            "",
            "**错误处理:**",
            "- [ ] 使用 `thiserror` / `anyhow` 进行错误定义和传播",
            "- [ ] 避免 `.unwrap()` / `.expect()` 出现在生产路径",
            "- [ ] `?` 操作符正确传播错误",
            "- [ ] `panic!` 仅用于不可恢复的编程错误",
            "",
            "**unsafe 使用:**",
            "- [ ] `unsafe` 块有安全性注释说明不变量",
            "- [ ] `unsafe` 范围最小化",
            "- [ ] FFI 边界有正确的 null 检查和生命周期管理",
            "",
            "**性能:**",
            "- [ ] 热路径避免不必要的堆分配",
            "- [ ] 使用 `&str` 而非 `String` 传递只读字符串",
            "- [ ] 迭代器链优于手动循环（编译器可优化）",
            "- [ ] `#[inline]` 仅用于确认有益的小函数",
            "",
        ]

    def _frontend_typescript_checklist(self) -> list[str]:
        return [
            "### 前端 TypeScript 审查\n",
            "**组件设计:**",
            "- [ ] 组件 Props 接口完整定义，必需 vs 可选明确",
            "- [ ] 事件回调类型使用 React.XXXEventHandler",
            "- [ ] children 类型使用 `React.ReactNode`",
            "- [ ] Ref 类型正确（`React.RefObject<HTMLXXXElement>`）",
            "",
            "**状态管理:**",
            "- [ ] 服务端状态与客户端状态分离",
            "- [ ] 表单状态使用受控组件或专用库（react-hook-form）",
            "- [ ] 全局状态不包含可从 URL 派生的数据",
            "- [ ] useEffect 依赖数组完整且无遗漏",
            "",
            "**可访问性 (a11y):**",
            "- [ ] 交互元素有 `aria-label` 或关联的 `<label>`",
            "- [ ] 图片有 `alt` 属性",
            "- [ ] 表单错误信息关联到对应字段",
            "- [ ] 键盘导航可用（Tab/Enter/Escape）",
            "",
        ]

    # ------------------------------------------------------------------
    # 代码复杂度分析
    # ------------------------------------------------------------------

    def _generate_complexity_analysis(self) -> str:
        """生成代码复杂度分析指南和检测逻辑说明。"""
        return """
---

## 代码复杂度分析（自动生成）

### 函数长度检查

| 等级 | 行数 | 处理方式 |
|:---|:---|:---|
| 优秀 | <= 20 行 | 无需处理 |
| 良好 | 21-50 行 | 可接受 |
| 警告 | 51-100 行 | 建议拆分 |
| 危险 | > 100 行 | 必须拆分 |

**检测方法:**
```python
# Python: 统计 def/async def 到下一个同级 def 之间的行数
# JavaScript: 统计 function/=> 到匹配闭合括号之间的行数
# 工具: radon (Python), escomplex (JS), gocyclo (Go)
```

### 圈复杂度 (Cyclomatic Complexity)

| 等级 | 复杂度值 | 处理方式 |
|:---|:---|:---|
| 简单 | 1-5 | 无风险 |
| 中等 | 6-10 | 需要充分测试 |
| 复杂 | 11-20 | 建议重构 |
| 不可维护 | > 20 | 必须重构 |

**圈复杂度计算:**
每个判断分支 (+1): `if`, `elif`, `else`, `for`, `while`, `case`, `catch`, `&&`, `||`, `?:`

**检测工具:**
- Python: `radon cc -a -nc` 或 `mccabe`
- JavaScript: `eslint --rule 'complexity: [error, 10]'`
- Go: `gocyclo -over 10 .`
- Rust: `cargo clippy -- -W clippy::cognitive_complexity`

### 嵌套深度检查

- [ ] 函数内最大嵌套深度不超过 4 层
- [ ] if-else 链超过 3 层时使用 guard clause（提前返回）
- [ ] 回调嵌套超过 2 层时使用 async/await 或 Promise 链
- [ ] 循环内嵌套条件使用 extract method 重构

**嵌套深度简化策略:**
1. **Guard Clause**: 将异常条件提前 return
2. **Extract Method**: 将嵌套逻辑抽取为独立函数
3. **Strategy Pattern**: 将 switch/if-else 链替换为策略映射
4. **Pipeline**: 将嵌套循环替换为 map/filter/reduce 链

### 参数数量检查

- [ ] 函数参数不超过 5 个
- [ ] 超过 3 个参数考虑使用配置对象/dataclass
- [ ] 布尔参数考虑拆分为两个函数或使用枚举
"""

    # ------------------------------------------------------------------
    # 命名规范检查
    # ------------------------------------------------------------------

    def _generate_naming_convention_checks(self) -> str:
        """生成命名规范检查的具体检测规则。"""
        return """
---

## 命名规范检查（自动生成）

### 通用命名规则

| 元素 | 规范 | 正则检测 | 示例 |
|:---|:---|:---|:---|
| 类名 | PascalCase | `^[A-Z][a-zA-Z0-9]+$` | `UserService`, `OrderManager` |
| 函数名 (Python/Go) | snake_case | `^[a-z_][a-z0-9_]*$` | `get_user`, `calculate_total` |
| 函数名 (JS/TS) | camelCase | `^[a-z][a-zA-Z0-9]*$` | `getUser`, `calculateTotal` |
| 常量 | SCREAMING_SNAKE | `^[A-Z][A-Z0-9_]*$` | `MAX_RETRY`, `API_BASE_URL` |
| 布尔变量 | is/has/should 前缀 | `^(is|has|should|can|will|did)[A-Z]` | `isActive`, `hasPermission` |
| 私有成员 (Python) | 单下划线前缀 | `^_[a-z]` | `_cache`, `_validate` |
| 接口 (TS) | I 前缀或无前缀 | 团队约定统一 | `IUserService` 或 `UserService` |
| 枚举成员 | PascalCase 或 SCREAMING | 团队约定统一 | `Status.Active` 或 `STATUS_ACTIVE` |

### 反面命名模式检测

以下命名模式在代码审查中应被标记：

- [ ] **单字母变量** (除循环变量 i/j/k 外): `^[a-z]$`
- [ ] **过于通用的名称**: `data`, `info`, `temp`, `result`, `obj`, `val`, `item` (作为非局部变量)
- [ ] **类型后缀冗余**: `userList` (应为 `users`), `nameString` (应为 `name`)
- [ ] **否定命名**: `isNotValid` (应为 `isInvalid`), `noCache` (应为 `skipCache`)
- [ ] **缩写不一致**: 同项目中 `usr`/`user`, `btn`/`button`, `msg`/`message` 混用
- [ ] **数字后缀**: `handler2`, `processV2` (应使用更具描述性的名称)
- [ ] **匈牙利命名残留**: `strName`, `intCount`, `boolIsActive`

### 文件命名一致性

- [ ] Python 模块: `snake_case.py`
- [ ] JS/TS 组件: `PascalCase.tsx` 或 `kebab-case.tsx`（项目内统一）
- [ ] CSS 模块: `ComponentName.module.css`
- [ ] 测试文件: `test_xxx.py` / `xxx.test.ts` / `xxx_test.go`
- [ ] 配置文件: `kebab-case.yaml` / `.xxxrc`
"""

    # ------------------------------------------------------------------
    # 专家 Playbook 具体检查项
    # ------------------------------------------------------------------

    def _generate_expert_playbook_checks(self) -> str:
        """生成专家 Playbook 的具体检测逻辑（超越文字描述）。"""
        sections: list[str] = [
            "\n---\n",
            "## 专家 Playbook 检测规则（自动生成）\n",
            "> 以下规则包含具体的检测逻辑和正则模式，可集成到 CI 管道中。\n",
        ]

        # SQL 注入检测规则
        sections.extend(
            [
                "### SQL 注入检测\n",
                "**检测模式:**",
                "```regex",
                r"# Python f-string SQL",
                r'f["\'].*?(SELECT|INSERT|UPDATE|DELETE|DROP)\s.*?\{',
                r"# JS template literal SQL",
                r"`.*?(SELECT|INSERT|UPDATE|DELETE|DROP)\s.*?\$\{",
                r"# 字符串拼接 SQL",
                r"(SELECT|INSERT|UPDATE|DELETE|DROP)\s.*?\+\s*(req\.|request\.|params\.|query\.)",
                "```",
                "",
                "**修复模式:**",
                "- Python: 使用 SQLAlchemy ORM 或 `cursor.execute(sql, params)`",
                "- Node.js: 使用 Prisma/Knex 参数化或 `pg` 的 `$1` 占位符",
                "- Go: 使用 `db.Query(sql, args...)` 参数化查询",
                "",
            ]
        )

        # XSS 检测规则
        sections.extend(
            [
                "### XSS 检测\n",
                "**检测模式:**",
                "```regex",
                r"# React dangerouslySetInnerHTML",
                r"dangerouslySetInnerHTML\s*=\s*\{\s*\{.*__html\s*:",
                r"# 直接 innerHTML 赋值",
                r"\.innerHTML\s*=",
                r"# document.write",
                r"document\.write\s*\(",
                r"# v-html (Vue)",
                r'v-html\s*=\s*"',
                "```",
                "",
                "**修复模式:**",
                "- 使用 `DOMPurify.sanitize()` 清洗 HTML",
                "- React: 优先使用 JSX 文本节点而非 dangerouslySetInnerHTML",
                "- 服务端渲染: 使用模板引擎的自动转义功能",
                "",
            ]
        )

        # 认证检测规则
        sections.extend(
            [
                "### 认证/授权检测\n",
                "**检测模式:**",
                "```regex",
                r"# 路由缺少认证中间件",
                r"(app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"].*['\"],\s*(async\s+)?\(?",
                r"# 权限硬编码",
                r'role\s*===?\s*["\']admin["\']',
                r"# JWT 无过期设置",
                r"jwt\.sign\s*\([^)]*(?!expiresIn)[^)]*\)",
                "```",
                "",
                "**检查清单:**",
                "- [ ] 所有非公开路由有认证中间件",
                "- [ ] 权限检查使用 RBAC/ABAC 而非硬编码角色",
                "- [ ] JWT 有过期时间（建议 15 分钟 access + 7 天 refresh）",
                "- [ ] 敏感操作有二次认证或 CSRF token",
                "",
            ]
        )

        # 日志安全检测
        sections.extend(
            [
                "### 日志安全检测\n",
                "**检测模式:**",
                "```regex",
                r"# 密码/密钥记录到日志",
                r"(log|logger|console)\.(info|debug|warn|error|log)\s*\(.*?(password|secret|token|key|credential)",
                r"# 信用卡号记录",
                r"(log|logger|console)\.\w+\(.*?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
                "```",
                "",
                "**修复模式:**",
                "- 实施日志脱敏中间件，自动掩码敏感字段",
                "- 使用结构化日志，敏感字段标记为 `[REDACTED]`",
                "- 生产环境禁用 debug 级别日志",
                "",
            ]
        )

        # 错误处理检测
        sections.extend(
            [
                "### 错误处理检测\n",
                "**检测模式:**",
                "```regex",
                r"# Python 裸 except",
                r"except\s*:",
                r"# JS 空 catch",
                r"catch\s*\(\w*\)\s*\{\s*\}",
                r"# Go 忽略 error",
                r"\w+,\s*_\s*:?=\s*\w+\(",
                r"# 错误信息暴露内部细节",
                r"(res|response)\.(json|send)\s*\(\s*\{.*?(stack|trace|internal)",
                "```",
                "",
                "**检查清单:**",
                "- [ ] 不吞掉异常（空 catch 块）",
                "- [ ] 生产环境不返回堆栈跟踪",
                "- [ ] 错误边界（React ErrorBoundary）覆盖关键路由",
                "- [ ] 500 错误有通用错误响应格式",
                "",
            ]
        )

        return "\n".join(sections)

    def _inject_expert_checklists(self) -> str:
        """从专家工具箱注入治理检查清单到代码审查指南。"""
        sections: list[str] = []

        # 代码专家检查清单
        if self._code_toolkit:
            items = self._code_toolkit.get_review_checklist("quality")
            if items:
                sections.append("\n---\n")
                sections.append("## 代码专家检查清单（自动注入）\n")
                sections.append("> 以下检查项由代码专家工具箱自动注入，基于治理规则和质量维度。\n")
                for item in items:
                    sections.append(f"- [ ] {item}")
                sections.append("")

            # 注入代码专家的验证规则 ID 供追溯
            if self._code_toolkit.rules.validation_rule_ids:
                sections.append(
                    f"**关联验证规则**: {', '.join(self._code_toolkit.rules.validation_rule_ids)}\n"
                )

            # 注入代码专家的 Playbook
            if self._code_toolkit.playbook:
                sections.append("**代码专家方法论:**\n")
                for idx, step in enumerate(self._code_toolkit.playbook, 1):
                    sections.append(f"{idx}. {step}")
                sections.append("")

        # 安全专家交叉审查
        if self._security_toolkit:
            sec_items = self._security_toolkit.get_review_checklist("quality")
            if sec_items:
                sections.append("\n---\n")
                sections.append("## 安全专家交叉审查（自动注入）\n")
                sections.append(
                    "> 以下检查项由安全专家工具箱交叉注入，确保代码审查覆盖安全维度。\n"
                )
                for item in sec_items:
                    sections.append(f"- [ ] {item}")
                sections.append("")

            # 注入安全专家的验证规则 ID 供追溯
            if self._security_toolkit.rules.validation_rule_ids:
                sections.append(
                    f"**关联安全规则**: {', '.join(self._security_toolkit.rules.validation_rule_ids)}\n"
                )

            # 注入安全专家的交叉审查维度
            review_dimensions = cast(
                list[dict[str, object]], self._security_toolkit.protocol.review_dimensions
            )
            for dim in review_dimensions:
                dim_name = str(dim.get("dimension", ""))
                checklist = dim.get("checklist")
                if dim_name and isinstance(checklist, list):
                    sections.append(f"**{dim_name}:**\n")
                    for check_item in checklist:
                        if isinstance(check_item, str):
                            sections.append(f"- [ ] {check_item}")
                    sections.append("")

        return "\n".join(sections)
