# Super Dev 2.4.0 内部产品强化蓝图

> 这是一份内部规划蓝图，不是公开合同源；公开对外口径以 README、WORKFLOW_GUIDE 和宿主矩阵为准。

更新时间：2026-04-22

## 一句话定位

`Super Dev` 不是模型平台，不是主写代码的 agent，也不是“一键生成项目”的脚手架产品。

`Super Dev` 是一个面向商业级软件交付的宿主教练系统：

- 宿主负责搜索、推理、写代码、跑命令、改文件
- `Super Dev` 负责图纸、节奏、审美、门禁、验收、交付证据

它真正卖的不是 codegen，而是：

- 让任何宿主更像顶级产品团队
- 让任何项目更像商业级交付项目
- 让用户一上手就感觉“这个工具真的懂开发、懂设计、懂交付”

---

## 2.4.0 的目标

`2.4.0` 不是“小修小补”，而应该是一版让用户明显感知产品成熟度跃迁的版本。

用户要感受到的变化应该是：

1. 一接入就知道怎么开始，不迷路
2. 已有项目不会乱冲，会先 baseline
3. 宿主像被训练过，不会跳步骤，不会胡写
4. UI 明显更高级，没 AI 味
5. 质量和交付更像真正商业项目
6. 各种宿主和平台都像“原生支持”一样顺

---

## 产品主原则

### 1. 宿主执行，Super Dev 指导

核心分工必须始终稳定：

- 宿主执行 research、写文档、写代码、跑验证、交付产物
- `Super Dev` 冻结正确流程、正确设计方向、正确质量门和正确交付要求

### 2. 先图纸，后实现

商业项目必须遵循：

- 先 research
- 再 PRD / Architecture / UIUX
- 再 Spec / tasks
- 再 frontend
- 再 preview confirm
- 再 backend
- 再 quality / delivery

不能让宿主“先写再补”。

### 3. 先方向，后页面

UI 不是先搭页面，而是先锁：

- 视觉方向
- 品牌气质
- 字体系统
- token system
- icon library
- component ecosystem
- page skeleton

### 4. 先验收路径，后宣传支持

任何宿主、框架、平台，只有满足以下几件事，才算真的适配：

- 能正确触发
- 能正确恢复
- 能通过首轮 smoke
- 能通过标准流验收
- 能通过 SEEAI 比赛流验收

---

## 让用户“眼前一亮”的六条主线

## 1. 交互层：像产品，不像工具箱

### 当前正确方向

- 终端公开面已经收成：
  - `super-dev`
  - `super-dev update`
  - `super-dev uninstall`
- 宿主公开面已经收成：
  - `/super-dev`
  - `/super-dev-work`
  - `/super-dev-run`
  - `/super-dev-review`
  - `/super-dev-seeai`

### 还要继续加强

- 默认入口要更“傻瓜但专业”
  - 用户只需要说一句需求，系统自动判断 `new / evolve / patch / variant / resume`
- 宿主第一句要更宿主化
  - 不同宿主给不同的第一句，不再只是统一模板
- 恢复动作要更自然
  - “继续当前流程”“现在下一步是什么”要真正成为第一入口
- 安装器要更像 onboarding 产品
  - 不只是告诉用户写了哪些文件
  - 要告诉用户：
    - 你现在可以在哪个宿主里开工
    - 标准流是否 ready
    - 比赛流是否 ready
    - 接入后第一句是什么

### 这条线的惊艳点

用户装完之后，不需要读很多文档，就能：

- 看到自己应该在哪个宿主里继续
- 知道第一句怎么说
- 知道现在是不是已经能开工
- 知道如果中断了该怎么恢复

---

## 2. 流程层：像成熟团队，不像随机聊天

### 当前正确方向

- 已有项目主链已经补成：
  - `baseline -> baseline confirmation -> delta research -> docs -> docs_confirm -> spec -> frontend -> preview_confirm -> backend -> quality -> delivery`
- `resume` 已是第一类场景

### 还要继续加强

- 把 canonical stages 再彻底执行化
  - 不只是状态上这样叫
  - 而是所有产物、门禁、报告都围绕这条链
- 把每一阶段的输入/输出再做成硬合同
  - `research` 产物是什么
  - `docs_confirm` 必须锁哪些内容
  - `frontend` 阶段什么叫合格
  - `quality` 阶段什么叫必须回退
- 把“禁止越级”做得更明显
  - 宿主不能绕过 docs / preview gate 直接冲下一阶段

### 这条线的惊艳点

用户会明显感受到：

- 这个工具不会让项目跑偏
- 它像一个真正会带团队的负责人
- 它不是随便回复，而是在带项目

---

## 3. 宿主层：像原生支持，不像兼容适配

### 当前正确方向

- 26 宿主矩阵已进入正式协议层
- 已有：
  - `adaptation_contract`
  - `official_alignment`
  - `host_experience_profile`
  - `post_onboard_self_check`
  - `standard_flow_ready`
  - `competition_flow_ready`

### 还要继续加强

- 每个宿主都要有自己的：
  - start playbook
  - resume playbook
  - repair playbook
  - official workflow checks
  - pass criteria
  - first prompts
- 安装后 smoke guide 继续细化成宿主专项验收
- 宿主官方对齐程度表达要继续克制
  - 不把“当前推荐模型”说成“官方原生能力”

### 这条线的惊艳点

用户会觉得：

- 这个工具不是“声称支持很多宿主”
- 而是真的懂每个宿主怎么工作

---

## 4. UI 层：像设计总监，不像模板生成器

### 当前正确方向

- 已有：
  - `art_direction_candidates`
  - `design_direction_manifest`
  - `anti_ai_slop_guardrails`
  - `critique_rubric`

### 还要继续加强

- 把 UI 的强项继续从“结构冻结”推进到“真实审美治理”
- 每个项目至少保留 2-3 个视觉方向候选
- 把“AI 味”审查再具体化：
  - cliché hero
  - 紫粉渐变
  - 过宽留白
  - 默认字体
  - 无品牌识别
  - 组件像 demo 站
- 引入 screenshot-based visual judge
  - 不只检查文档和代码
  - 还检查结果是否真的高级
- 框架层要变成 playbook，不是主叙事里的 scaffold
  - `Next.js / Vue / Nuxt / Angular / Expo / Flutter / Tauri / uni-app ...`
  - 核心是告诉宿主“在这个框架里要怎样做得像商业产品”

### 这条线的惊艳点

用户会感觉：

- 它真的懂设计
- 它不会把宿主带去做 AI 模板页
- 它是在带着宿主做品牌级界面

---

## 5. 质量层：像商业交付，不像开发自嗨

### 当前正确方向

- 已有：
  - `quality gate`
  - `proof-pack`
  - `release-readiness`
  - `product-audit`

### 还要继续加强

- 把这几套治理摘要继续收成统一真源
- 继续减少“多个地方重复解释同一状态”的情况
- 增强真正高价值的检查：
  - UI 是否真的过关
  - 宿主是否真的按冻结协议执行
  - 是否真的形成了交付证据闭环

### 这条线的惊艳点

用户会感觉：

- 这个工具不是只会提建议
- 它会强制把项目推到可交付

---

## 6. 生命周期层：像成熟产品，不像脚本集合

### 当前正确方向

- 已有：
  - 项目优先接入
  - `--with-user-surfaces`
  - uninstall `--dry-run`
  - cleanup report
  - onboard smoke guide

### 还要继续加强

- 增加跨平台安装器 CI
  - macOS / Linux / Windows
- 增加更明显的 onboarding success state
- 增加更产品化的 cleanup summary
- Windows 侧补齐更原生的入口体验

### 这条线的惊艳点

用户会感觉：

- 安装、升级、卸载都很稳
- 工具有“大厂产品”的完成度

---

## 框架与平台的正确定位

框架支持不能继续走偏成“我们自己在生成项目”。

正确定位是：

- `Super Dev` 不替宿主写完整项目
- `Super Dev` 给宿主对应框架的执行图纸、实现约束、UI 契约和验收规则

所以对这些主流栈的加强重点应该是：

- `React / Next.js / Remix / Gatsby`
- `Vue / Nuxt`
- `Angular`
- `Svelte / SvelteKit`
- `React Native / Expo`
- `Flutter`
- `uni-app / Taro`
- `Tauri / Electron / Wails`
- `Ionic / Capacitor`

每个框架都需要：

- UI/UX 实施 playbook
- 平台限制说明
- 必过场景
- 宿主实现提示
- 验收 checklist

而不是只多一个 scaffold。

---

## 2.4.0 之后的强制优先级

### P0

- 统一产品叙事：宿主执行，Super Dev 指导
- 继续强化宿主专项验收
- 继续强化 UI screenshot review 与 anti-AI-slop

### P1

- canonical stages 真正执行化
- 统一 delivery governance snapshot
- 跨平台安装器 CI

### P2

- 继续清理结构债
- 继续压缩重复文档真源
- 持续偿还类型债

---

## 最终要达到的用户感受

一个真正成熟的 `Super Dev 2.4.0`，用户用完应该会有这几个感受：

1. “它不抢宿主的活，但它把宿主带得特别专业。”
2. “它不像脚本工具，更像一个完整的交付系统。”
3. “它很懂商业项目，不只是懂代码。”
4. “它对 UI 审美有要求，不会让我做出 AI 味页面。”
5. “它会把我一步步带到可交付，而不是只会生成一堆文件。”

这才是 `Super Dev` 真正能让人眼前一亮的地方。
