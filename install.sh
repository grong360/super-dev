#!/usr/bin/env bash
#
# Super Dev 宿主安装向导
#
# 用法:
#   ./install.sh                                # 交互式向导（支持多选宿主）
#   ./install.sh --targets claude-code,codex-cli,droid-cli,kimi-code,qwen-code,cursor,trae,workbuddy,codex
#   ./install.sh --targets all --no-skill
#
# 说明:
#   这是仓库内的 macOS/Linux 便捷入口。
#   Windows、已安装 PyPI/uv 工具的用户，直接运行 `super-dev` 即可。
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}${NC} $1"; }
success() { echo -e "${GREEN}${NC} $1"; }
warning() { echo -e "${YELLOW}${NC} $1"; }
error() { echo -e "${RED}${NC} $1"; }

ALL_TARGETS_CSV="claude-code,codex-cli,opencode,droid-cli,gemini-cli,kiro-cli,cursor-cli,copilot-cli,qoder-cli,codebuddy-cli,kimi-code,qwen-code,antigravity,cursor,windsurf,kiro,trae,trae-cn,codebuddy,codebuddy-cn,qoder,claude,codex,workbuddy,trae-solo,trae-solocn"
CLI_TARGETS_CSV="claude-code,codex-cli,opencode,droid-cli,gemini-cli,kiro-cli,cursor-cli,copilot-cli,qoder-cli,codebuddy-cli,kimi-code,qwen-code"
IDE_TARGETS_CSV="antigravity,cursor,windsurf,kiro,trae,trae-cn,codebuddy,codebuddy-cn,qoder"
ASSISTANT_TARGETS_CSV="claude,codex,workbuddy,trae-solo,trae-solocn"

TARGETS="$ALL_TARGETS_CSV"
WITH_SKILL="true"
WITH_USER_SURFACES="false"
GUIDED="auto"
TARGETS_EXPLICIT="false"

IFS=',' read -r -a ALL_TARGET_ARRAY <<< "$ALL_TARGETS_CSV"
IFS=',' read -r -a CLI_TARGET_ARRAY <<< "$CLI_TARGETS_CSV"
IFS=',' read -r -a IDE_TARGET_ARRAY <<< "$IDE_TARGETS_CSV"
IFS=',' read -r -a ASSISTANT_TARGET_ARRAY <<< "$ASSISTANT_TARGETS_CSV"

HOST_TOTAL_COUNT="${#ALL_TARGET_ARRAY[@]}"
CLI_HOST_COUNT="${#CLI_TARGET_ARRAY[@]}"
IDE_HOST_COUNT="${#IDE_TARGET_ARRAY[@]}"
ASSISTANT_HOST_COUNT="${#ASSISTANT_TARGET_ARRAY[@]}"

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

is_valid_target() {
  local target="$1"
  local item
  for item in "${ALL_TARGET_ARRAY[@]}"; do
    if [[ "$item" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}

append_unique_target() {
  local target="$1"
  local existing
  for existing in "${SELECTED_TARGETS[@]-}"; do
    if [[ "$existing" == "$target" ]]; then
      return 0
    fi
  done
  SELECTED_TARGETS+=("$target")
}

join_targets_csv() {
  local arr=("$@")
  local out=""
  local item
  for item in "${arr[@]}"; do
    if [[ -z "$out" ]]; then
      out="$item"
    else
      out="${out},${item}"
    fi
  done
  printf '%s' "$out"
}

print_host_usage_summary() {
  local target="$1"
  python3 - "$target" <<'PY'
import sys
from pathlib import Path

from super_dev.integrations.manager import IntegrationManager
from super_dev.host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from super_dev.workflow_state import load_framework_playbook_summary

target = sys.argv[1]
manager = IntegrationManager(Path.cwd())
profile = manager.get_adapter_profile(target)
protocol = profile.host_protocol_summary or profile.host_protocol_mode
final_trigger = str(profile.trigger_command).replace("<需求描述>", "你的需求")
seeai_surfaces = manager.managed_competition_project_surfaces(target)
seeai_user_surfaces = manager.managed_competition_user_surfaces(target)
post_checks = build_host_post_onboard_self_check(
    target,
    {
        "host": profile.host,
        "host_protocol_mode": profile.host_protocol_mode,
        "official_project_surfaces": list(profile.official_project_surfaces),
        "official_user_surfaces": list(profile.official_user_surfaces),
        "managed_competition_project_surfaces": seeai_surfaces,
        "managed_competition_user_surfaces": seeai_user_surfaces,
    },
)
official_checks = build_host_official_workflow_checks(
    target,
    {
        "host": profile.host,
        "host_protocol_mode": profile.host_protocol_mode,
        "official_project_surfaces": list(profile.official_project_surfaces),
        "official_user_surfaces": list(profile.official_user_surfaces),
        "managed_competition_project_surfaces": seeai_surfaces,
        "managed_competition_user_surfaces": seeai_user_surfaces,
    },
)
start_playbook = build_host_start_playbook(target)
standard_first_prompt = build_host_standard_first_prompt(target)
competition_first_prompt = build_host_competition_first_prompt(target)
repair_playbook = build_host_repair_guidance(target).strip()
framework_playbook = load_framework_playbook_summary(Path.cwd())

print("  终端到此为止，真正开发回到宿主里。")
print(f"  回宿主位置: {profile.trigger_context}")
print(f"  主入口: {final_trigger}")
print(f"  接入后重启: {'是' if profile.requires_restart_after_onboard else '否'}")
print(f"  标准流第一句: {standard_first_prompt}")
print(f"  比赛流第一句: {competition_first_prompt}")
if start_playbook:
    print("  先这样开始:")
    for step in start_playbook[:3]:
        print(f"    - {step}")
if framework_playbook:
    print("  框架焦点 (Framework Coaching Focus):")
    print(f"    - Framework: {framework_playbook.get('framework', '-')}")
    validation_surfaces = framework_playbook.get("validation_surfaces", [])
    if isinstance(validation_surfaces, list) and validation_surfaces:
        print("    - 必验场景:")
        for item in validation_surfaces[:4]:
            print(f"      · {item}")
    delivery_evidence = framework_playbook.get("delivery_evidence", [])
    if isinstance(delivery_evidence, list) and delivery_evidence:
        print("    - 交付证据:")
        for item in delivery_evidence[:4]:
            print(f"      · {item}")
if post_checks:
    print("  接入后先验:")
    for step in post_checks[:4]:
        print(f"    - {step}")
if official_checks:
    print("  Smoke / 官方验收:")
    for step in official_checks[:4]:
        print(f"    - {step}")
print("  成功标志:")
print("    1. 宿主第一轮回复明确说：当前阶段是 research。")
print("    2. 宿主先写 research、PRD、Architecture、UIUX，再停下来等你确认。")
if repair_playbook:
    print("  如果没有进入 research -> 三文档 -> 等待确认:")
    print(f"    - {repair_playbook}")
PY
}

latest_onboard_smoke_guide() {
  local latest
  latest="$(ls -1t output/maintenance/host-onboard-smoke-*.md 2>/dev/null | head -n 1 || true)"
  if [[ -n "$latest" ]]; then
    echo "$latest"
  fi
}

parse_targets_csv() {
  local raw="$1"
  local normalized
  local token

  normalized="$(echo "$raw" | tr 'A-Z' 'a-z' | tr ' ' ',')"
  IFS=',' read -r -a raw_tokens <<< "$normalized"

  SELECTED_TARGETS=()
  for token in "${raw_tokens[@]}"; do
    token="$(trim "$token")"
    if [[ -z "$token" ]]; then
      continue
    fi
    if [[ "$token" == "all" ]]; then
      SELECTED_TARGETS=("${ALL_TARGET_ARRAY[@]}")
      TARGETS="$(join_targets_csv "${SELECTED_TARGETS[@]}")"
      return 0
    fi
    if [[ "$token" == "cli" ]]; then
      local cli_target
      for cli_target in "${CLI_TARGET_ARRAY[@]}"; do
        append_unique_target "$cli_target"
      done
      continue
    fi
    if [[ "$token" == "ide" ]]; then
      local ide_target
      for ide_target in "${IDE_TARGET_ARRAY[@]}"; do
        append_unique_target "$ide_target"
      done
      continue
    fi
    if [[ "$token" == "assistant" || "$token" == "desktop" ]]; then
      local assistant_target
      for assistant_target in "${ASSISTANT_TARGET_ARRAY[@]}"; do
        append_unique_target "$assistant_target"
      done
      continue
    fi
    if ! is_valid_target "$token"; then
      return 1
    fi
    append_unique_target "$token"
  done

  if [[ "${#SELECTED_TARGETS[@]}" -eq 0 ]]; then
    return 1
  fi

  TARGETS="$(join_targets_csv "${SELECTED_TARGETS[@]}")"
  return 0
}

prompt_yes_no() {
  local prompt="$1"
  local default_yes="$2"
  local answer=""
  local normalized=""

  if [[ "$default_yes" == "true" ]]; then
    read -r -p "$prompt [Y/n]: " answer
  else
    read -r -p "$prompt [y/N]: " answer
  fi
  normalized="$(echo "${answer:-}" | tr 'A-Z' 'a-z')"
  normalized="$(trim "$normalized")"

  if [[ -z "$normalized" ]]; then
    [[ "$default_yes" == "true" ]] && return 0 || return 1
  fi
  case "$normalized" in
    y|yes|1|true) return 0 ;;
    n|no|0|false) return 1 ;;
    *) [[ "$default_yes" == "true" ]] && return 0 || return 1 ;;
  esac
}

run_guided_selector() {
  local index=1
  local input=""
  local normalized=""
  local token=""
  local target=""

  echo ""
  echo -e "${GREEN}Super Dev 安装向导${NC}"
  echo "=================================="
  echo "定位：终端只负责接入；真正开发回到宿主里。"
  echo "默认主线：回宿主 -> 复制第一句 -> 看框架焦点与必验场景 -> 按 smoke guide 验收"
  echo "触发规则：支持 slash 的宿主使用 /super-dev；不支持 slash 的宿主使用 super-dev: 或 super-dev："
  echo "当前宿主矩阵：${HOST_TOTAL_COUNT} 个（CLI ${CLI_HOST_COUNT} / IDE ${IDE_HOST_COUNT} / 桌面助手 ${ASSISTANT_HOST_COUNT}）"
  echo "请选择要接入的宿主工具（支持多选）"
  echo ""
  echo "CLI 宿主:"
  for target in "${CLI_TARGET_ARRAY[@]}"; do
    printf "  %2d. %s\n" "$index" "$target"
    index=$((index + 1))
  done
  echo ""
  echo "IDE 宿主:"
  for target in "${IDE_TARGET_ARRAY[@]}"; do
    printf "  %2d. %s\n" "$index" "$target"
    index=$((index + 1))
  done
  echo ""
  echo "桌面助手宿主:"
  for target in "${ASSISTANT_TARGET_ARRAY[@]}"; do
    printf "  %2d. %s\n" "$index" "$target"
    index=$((index + 1))
  done
  echo ""
  echo "快捷输入:"
  echo "  cli  = 全选 CLI"
  echo "  ide  = 全选 IDE"
  echo "  assistant / desktop = 全选桌面助手"
  echo "  all  = 全选全部"
  echo "  也可直接输入宿主 id（如 codex-cli,droid-cli,kimi-code,qwen-code,trae,trae-cn,codex,claude）"

  while true; do
    read -r -p "请输入编号/宿主ID（逗号分隔，可多选）: " input
    normalized="$(echo "$input" | tr 'A-Z' 'a-z' | tr ' ' ',')"
    IFS=',' read -r -a tokens <<< "$normalized"
    SELECTED_TARGETS=()

    for token in "${tokens[@]}"; do
      token="$(trim "$token")"
      if [[ -z "$token" ]]; then
        continue
      fi

      if [[ "$token" == "all" ]]; then
        SELECTED_TARGETS=("${ALL_TARGET_ARRAY[@]}")
        break
      elif [[ "$token" == "cli" ]]; then
        for target in "${CLI_TARGET_ARRAY[@]}"; do
          append_unique_target "$target"
        done
        continue
      elif [[ "$token" == "ide" ]]; then
        for target in "${IDE_TARGET_ARRAY[@]}"; do
          append_unique_target "$target"
        done
        continue
      elif [[ "$token" == "assistant" || "$token" == "desktop" ]]; then
        for target in "${ASSISTANT_TARGET_ARRAY[@]}"; do
          append_unique_target "$target"
        done
        continue
      fi

      if [[ "$token" =~ ^[0-9]+$ ]]; then
        if [[ "$token" -lt 1 || "$token" -gt "${#ALL_TARGET_ARRAY[@]}" ]]; then
          SELECTED_TARGETS=()
          break
        fi
        append_unique_target "${ALL_TARGET_ARRAY[$((token - 1))]}"
        continue
      fi

      if is_valid_target "$token"; then
        append_unique_target "$token"
      else
        SELECTED_TARGETS=()
        break
      fi
    done

    if [[ "${#SELECTED_TARGETS[@]}" -gt 0 ]]; then
      TARGETS="$(join_targets_csv "${SELECTED_TARGETS[@]}")"
      break
    fi
    warning "输入无效，请重新选择。"
  done

  if prompt_yes_no "是否安装内置 Skill?" "true"; then
    WITH_SKILL="true"
  else
    WITH_SKILL="false"
  fi

  if prompt_yes_no "是否显式启用用户级增强面（跨项目共享规则/commands/skills）?" "false"; then
    WITH_USER_SURFACES="true"
  else
    WITH_USER_SURFACES="false"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --targets)
      TARGETS="${2:-$ALL_TARGETS_CSV}"
      TARGETS_EXPLICIT="true"
      shift 2
      ;;
    --no-skill)
      WITH_SKILL="false"
      shift
      ;;
    --with-user-surfaces)
      WITH_USER_SURFACES="true"
      shift
      ;;
    --guided)
      GUIDED="true"
      shift
      ;;
    --no-guided)
      GUIDED="false"
      shift
      ;;
    --help|-h)
      cat <<'EOF'
Super Dev Installer

Options:
  --targets <list>   目标平台，逗号分隔，或 all/cli/ide/assistant
                     可选: claude-code,codex-cli,opencode,droid-cli,gemini-cli,kiro-cli,cursor-cli,copilot-cli,qoder-cli,codebuddy-cli,kimi-code,qwen-code,antigravity,cursor,windsurf,kiro,trae,trae-cn,codebuddy,codebuddy-cn,qoder,claude,codex,workbuddy,trae-solo,trae-solocn
  --no-skill         只生成宿主集成和 /super-dev 映射，不安装内置 skill
  --with-user-surfaces
                     显式补齐用户级增强面（跨项目共享 rules / commands / skills）
  --guided           强制进入交互式安装向导
  --no-guided        跳过交互向导（需配合 --targets）
  -h, --help         显示帮助
EOF
      exit 0
      ;;
    *)
      error "未知参数: $1"
      exit 1
      ;;
  esac
done

if ! command -v super-dev >/dev/null 2>&1; then
  error "未检测到 super-dev 命令。请先安装 super-dev 后再运行本脚本。"
  error "示例: pip install -U super-dev"
  error "可选: uv tool install super-dev"
  error "开发模式: uv sync && uv run super-dev"
  error "或使用 pip 开发安装: pip install -e ."
  exit 1
fi

if [[ "$GUIDED" == "true" ]]; then
  run_guided_selector
elif [[ "$GUIDED" == "auto" && "$TARGETS_EXPLICIT" == "false" ]]; then
  if [[ -t 0 ]]; then
    run_guided_selector
  else
    warning "检测到非交互终端，自动使用 all 目标。可通过 --targets 指定。"
    TARGETS="$ALL_TARGETS_CSV"
  fi
fi

if ! parse_targets_csv "$TARGETS"; then
  error "无效的 --targets: $TARGETS"
  exit 1
fi

echo ""
echo -e "${GREEN}Super Dev Installer${NC}"
echo "=================================="
echo "Targets: $TARGETS"
echo "Install skill: $WITH_SKILL"
echo "User surfaces opt-in: $WITH_USER_SURFACES"
echo "触发规则: slash 宿主 => /super-dev 你的需求；非 slash 宿主 => super-dev: 你的需求"
echo ""

if [[ -t 0 ]]; then
  if ! prompt_yes_no "确认开始安装?" "true"; then
    warning "已取消安装。"
    exit 0
  fi
fi

IFS=',' read -r -a target_list <<< "$TARGETS"

for target in "${target_list[@]}"; do
  target="$(trim "$target")"
  if [[ -z "$target" ]]; then
    continue
  fi

  info "接入宿主: $target"
  onboard_cmd=(super-dev onboard --host "$target" --yes --force)
  doctor_cmd=(super-dev doctor --host "$target")

  if [[ "$WITH_SKILL" != "true" ]]; then
    onboard_cmd+=(--skip-skill)
    doctor_cmd+=(--skip-skill)
  fi

  if [[ "$WITH_USER_SURFACES" == "true" ]]; then
    onboard_cmd+=(--with-user-surfaces)
    doctor_cmd+=(--with-user-surfaces)
  fi

  if "${onboard_cmd[@]}"; then
    success "接入完成: $target"
    latest_smoke_guide="$(latest_onboard_smoke_guide)"
    if [[ -n "$latest_smoke_guide" ]]; then
      info "下一步先看 smoke guide: $latest_smoke_guide"
    fi
  else
    warning "接入失败: $target"
    warning "先不要继续开发；回终端执行: super-dev doctor --host $target --repair --force"
    continue
  fi

  if "${doctor_cmd[@]}" >/dev/null; then
    success "诊断通过: $target"
  else
    warning "诊断未通过: $target"
    warning "先不要继续开发；回终端执行: super-dev doctor --host $target --repair --force"
  fi

  print_host_usage_summary "$target"
done

echo ""
echo -e "${GREEN}=================================="
echo " 安装完成"
echo "==================================${NC}"
echo ""
echo "已接入宿主:"
for target in "${SELECTED_TARGETS[@]}"; do
  echo "  - $target"
done
latest_smoke_guide="$(latest_onboard_smoke_guide)"
echo ""
echo "终端到此为止，真正开发回到宿主里。"
echo ""
echo "现在只做这四步:"
echo "  1. 完全关闭宿主并重开项目，确保新会话重新加载接入面"
if [[ -n "$latest_smoke_guide" ]]; then
  echo "  2. 打开 smoke guide：$latest_smoke_guide"
else
  echo "  2. 打开 smoke guide：output/maintenance/host-onboard-smoke-*.md"
fi
echo "  3. 先看框架焦点、必验场景和交付证据，再复制“标准流第一句”或“比赛流第一句”"
echo "  4. 按 smoke guide 验收；只有没进入 research -> 三文档 -> 等待确认，才回终端跑 doctor"
echo ""
echo "成功标志:"
echo "  - 宿主第一轮回复明确说：当前阶段是 research"
echo "  - 宿主先写三份核心文档，并在三文档后停下来等你确认"
echo ""
echo "终端维护入口:"
echo "  - super-dev doctor --host <host> --repair --force"
echo "  - super-dev update"
echo "  - super-dev uninstall --dry-run"
echo "  - super-dev uninstall"
