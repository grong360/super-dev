# Scripts 目录

## 可用脚本

### `../install.sh`

宿主安装向导（默认交互式，多选 CLI/IDE 宿主）。

```bash
# 交互式向导
./install.sh

# 非交互（全部宿主）
./install.sh --targets all

# 非交互（仅规则，不装 skill）
./install.sh --targets all --no-skill
```

### `preflight.sh`

发布前非交互质量门禁脚本（推荐先跑）。

```bash
./scripts/preflight.sh
```

可选参数：

```bash
./scripts/preflight.sh --allow-dirty --skip-package --skip-benchmark --skip-delivery-smoke --skip-host-compat-gate
```

### `check_delivery_ready.py`

交付门禁检查脚本（支持直接检查 manifest 或 smoke 全链路验证）。

```bash
# 检查当前项目最新 manifest
python3 scripts/check_delivery_ready.py --project-dir .

# 运行离线 smoke，验证 pipeline 到交付包端到端
python3 scripts/check_delivery_ready.py --smoke --project-dir .
```

### `check_host_compatibility.py`

宿主兼容性门禁脚本（读取 `output/*-host-compatibility.json` 并执行阈值校验）。

```bash
# 默认读取 super-dev.yaml（host_compatibility_min_score / host_compatibility_min_ready_hosts），无配置时使用 80/1
python3 scripts/check_host_compatibility.py --project-dir .

# 自定义阈值和 ready host 最低数量
python3 scripts/check_host_compatibility.py --project-dir . --min-score 85 --min-ready-hosts 1
```

### `audit_development_kb.py`

开发知识库分层覆盖审计脚本（检查分层覆盖与知识库级达标状态）。

```bash
python3 scripts/audit_development_kb.py
```

### `audit_ai_kb.py`

AI开发知识库完整性审计脚本（检查AI域关键文档与达标状态）。

```bash
python3 scripts/audit_ai_kb.py
```

### `check_knowledge_gates.py`

开发知识门禁脚本（校验UI门禁、场景矩阵、全流程阶段、模板资产、关键资产与文档头规范）。

```bash
python3 scripts/check_knowledge_gates.py --project-dir .
```

可输出多格式报告：

```bash
python3 scripts/check_knowledge_gates.py --project-dir . --format json --out artifacts/knowledge-gate-report.json
python3 scripts/check_knowledge_gates.py --project-dir . --format md --out artifacts/knowledge-gate-report.md
python3 scripts/check_knowledge_gates.py --project-dir . --format html --out artifacts/knowledge-gate-report.html
python3 scripts/check_knowledge_gates.py --project-dir . --format junit --out artifacts/knowledge-gate-junit.xml
```

可配置文档陈旧阈值：

```bash
python3 scripts/check_knowledge_gates.py --project-dir . --stale-days 120
```

### `generate_lifecycle_packet.py`

从全流程模板层自动生成一套可交付阶段包（含manifest）。

```bash
python3 scripts/generate_lifecycle_packet.py --project-dir . --name order-center-v1
```

可选参数：

```bash
python3 scripts/generate_lifecycle_packet.py --project-dir . --name order-center-v1 --stages requirement,design,architecture
python3 scripts/generate_lifecycle_packet.py --project-dir . --name order-center-v1 --force
```

### `publish.sh`

交互式发布脚本（适合手动发布流程）。

```bash
./scripts/publish.sh
```

### `release.sh`

完整发布脚本（包含 PyPI 发布、git tag、GitHub Release）。

```bash
./scripts/release.sh
```

常见用法：

```bash
# 完整发布到 PyPI，并创建/推送 tag
./scripts/release.sh --repository pypi --push-tag --yes

# 对已有 tag + dist 产物补发 GitHub Release（不重复上传 PyPI）
./scripts/release.sh --skip-publish --github-release --generate-notes --yes

# 使用自定义 Release Notes
./scripts/release.sh --skip-publish --github-release --notes-file docs/releases/2.4.0.md --title "v2.4.0 - Super Dev" --yes
```

## 推荐顺序（2.4.0）

1. `./scripts/preflight.sh`
2. `python3 -m build && twine check dist/*`
3. `twine upload dist/*`
4. `./scripts/release.sh --repository pypi --push-tag --github-release --generate-notes --yes`
