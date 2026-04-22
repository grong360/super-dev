# 贡献指南 | Contributing Guide

感谢你对 Super Dev 的贡献！/ Thank you for contributing to Super Dev!

## 如何贡献 | How to Contribute

1. Fork [super-dev](https://github.com/shangyankeji/super-dev) 仓库
2. 创建功能分支：`git checkout -b feat/your-feature`
3. 提交更改并推送到你的 Fork
4. 提交 Pull Request 到 `main` 分支

## 开发环境 | Development Setup

```bash
# 需要 Python 3.10+
pip install -e ".[dev]"
```

## 代码风格 | Code Style

使用 **ruff** 和 **black**，行长度 100 字符。

```bash
ruff check super_dev/        # 检查
ruff check --fix super_dev/  # 自动修复
black super_dev/             # 格式化
mypy super_dev/              # 类型检查
```

## 测试 | Testing

```bash
pytest                              # 全部测试
pytest tests/unit/test_xxx.py -v    # 单文件
pytest --cov=super_dev              # 覆盖率
```

请为新代码添加对应的单元测试。

## 提交规范 | Commit Conventions

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(scope): description    # 新功能
fix(scope): description     # 修复
docs: description           # 文档
ci: description             # CI/CD
chore: description          # 维护
```

常用 scope：`orchestrator`、`enforcement`、`cli`、`website`、`hosts`。

## PR 要求 | PR Requirements

- 清晰的 PR 描述，说明变更原因和内容
- 所有测试通过（`pytest`）
- Lint 通过（`ruff check` + `black --check`）
- 新功能需包含测试用例

## 报告问题 | Reporting Issues

请在 [GitHub Issues](https://github.com/shangyankeji/super-dev/issues) 提交 Bug 或功能建议，包含复现步骤和环境信息。
