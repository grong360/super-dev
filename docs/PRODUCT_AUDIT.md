# Super Dev 产品审查

> 维护者文档。它用于治理、审计和交付把关，不是普通用户的第一入口。

这份文档只回答一件事：

- 如何从产品、交互、闭环和代码结构角度，审查当前项目是否真的“能用、能交付、能恢复”

同时默认遵守当前产品边界：

- 终端公开命令只保留 `super-dev / super-dev update / super-dev uninstall`
- 真正开发主路径在宿主里完成
- 已有项目的 `evolve / variant / patch` 必须先 `baseline -> baseline confirmation`
- `resume` 是默认场景，不是异常场景

---

## 命令入口

最直接的方式：

```bash
super-dev product-audit
```

会生成：

- `output/<project>-product-audit.md`
- `output/<project>-product-audit.json`

---

## 它审查什么

`product-audit` 不是单纯的代码扫描，它会同时看这几层：

1. 首次上手
2. 最短路径是否清晰
3. 用户是否知道成功标志是什么
4. 文档入口是否有断链
5. review / quality / proof-pack / release readiness 是否形成闭环
6. 是否存在会拖慢产品演进的超大核心模块

如果当前仓库本身就是 `super-dev` 项目，还会额外检查：

- 是否存在顶级 `PRODUCT` 专家
- 是否已经具备产品审查入口
- 是否把产品审查纳入 proof-pack 与 release readiness

---

## 推荐顺序

如果你要做一次完整的产品级审查，建议按这个顺序：

```bash
super-dev product-audit
super-dev quality --type all
```

含义：

1. 先看产品闭环和首次上手
2. 再看已有项目增量开发时是否会漏 `baseline -> baseline confirmation`
3. 再看恢复链是否成立
4. 再看质量门禁
5. 最后再查看 proof-pack 与 release readiness 的维护者报告

---

## 如何解释结果

`product-audit` 会输出：

- `score`
- `status`
- `strengths`
- `findings`
- `next_actions`

常见状态：

- `ready`: 当前没有阻断级产品问题
- `attention`: 存在需要尽快修复的缺口
- `revision_required`: 有 critical 问题，先修再继续交付

常见产品级 finding 现在尤其要看这几类：

- 公开入口是否还在误导用户离开宿主主路径
- 现有项目迭代时是否会跳过 baseline 或 baseline confirmation 直接开工
- 关闭窗口、关机、第二天回来后能不能继续当前流程
- quality / proof-pack / readiness 是否引用同一轮证据

---

## 和 proof-pack / release readiness 的关系

从现在开始，`product-audit` 不应是独立动作。

它应该和下面两类交付证据一起看：

- proof-pack
- release readiness

也就是说，产品审查结果要进入交付证据，而不是只停留在讨论里。

## 对已有项目特别重要

如果你当前做的不是 0-1，而是：

- `evolve`
- `variant`
- `patch`

那 `product-audit` 应该优先回答这几个问题：

1. 系统有没有先识别当前项目的功能、架构、代码边界和 UI 现状
2. baseline 工件是否存在并且已经过 baseline confirmation
3. 差量三文档是不是建立在已确认 baseline 之上，而不是凭空重写
4. 恢复当前流程时，宿主是不是会继续已有 run，而不是重新研究一遍
