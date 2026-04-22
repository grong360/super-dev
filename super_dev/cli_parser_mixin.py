"""CLI parser mixin helpers."""

from __future__ import annotations

import argparse

from . import __description__, __version__
from .catalogs import (
    CICD_PLATFORM_IDS,
    DOMAIN_IDS,
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PIPELINE_FRONTEND_TEMPLATE_IDS,
    PLATFORM_IDS,
    normalize_host_tool_id,
)

SUPPORTED_PLATFORMS = list(PLATFORM_IDS)
SUPPORTED_PIPELINE_FRONTENDS = list(PIPELINE_FRONTEND_TEMPLATE_IDS)
SUPPORTED_INIT_FRONTENDS = list(FULL_FRONTEND_TEMPLATE_IDS)
SUPPORTED_PIPELINE_BACKENDS = list(PIPELINE_BACKEND_IDS)
SUPPORTED_DOMAINS = list(DOMAIN_IDS)
SUPPORTED_CICD = list(CICD_PLATFORM_IDS)
SUPPORTED_HOST_TOOLS = list(HOST_TOOL_IDS)


class CliParserMixin:
    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器"""
        parser = argparse.ArgumentParser(
            prog="super-dev",
            description=__description__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "公开终端入口:\n"
                "  super-dev            安装 / 接入当前宿主\n"
                "  super-dev update     更新到最新版本\n"
                "  super-dev uninstall  清理已注入的宿主接入面\n"
                "\n"
                "宿主内主入口:\n"
                "  /super-dev <需求>\n"
                "  /super-dev-seeai <需求>\n"
                "  在宿主里说“继续当前流程”\n"
                "  在宿主里说“现在下一步是什么”\n"
                "\n"
                "高级维护口令:\n"
                "  /super-dev-work / /super-dev-run / /super-dev-review\n"
                "\n"
                "使用 'super-dev <command> -h' 查看单个命令的详细帮助\n"
                "使用 'super-dev --help-all' 查看所有命令\n"
            ),
        )

        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="增加日志详细度 (-v=INFO, -vv=DEBUG)",
        )
        parser.add_argument("--quiet", action="store_true", help="只显示错误")

        # 子命令
        subparsers = parser.add_subparsers(
            dest="command",
            title="内部维护命令索引",
            description=(
                "以下命令保留给维护 / 治理 / 高级用法。"
                "普通用户公开终端入口仍然只有 super-dev / super-dev update / super-dev uninstall。"
            ),
        )

        # init 命令
        init_parser = subparsers.add_parser(
            "init", help="初始化新项目", description="创建一个新的 Super Dev 项目"
        )
        init_parser.add_argument(
            "name", nargs="?", default=None, help="项目名称（默认使用当前目录名）"
        )
        init_parser.add_argument("-d", "--description", default="", help="项目描述")
        init_parser.add_argument(
            "-p", "--platform", choices=SUPPORTED_PLATFORMS, default="web", help="目标平台"
        )
        init_parser.add_argument(
            "-f", "--frontend", choices=SUPPORTED_INIT_FRONTENDS, default="next", help="前端框架"
        )
        init_parser.add_argument(
            "--ui-library",
            choices=[
                "mui",
                "ant-design",
                "chakra-ui",
                "mantine",
                "shadcn-ui",
                "radix-ui",
                "element-plus",
                "naive-ui",
                "vuetify",
                "primevue",
                "arco-design",
                "angular-material",
                "primeng",
                "skeleton-ui",
                "svelte-material-ui",
                "tailwind",
                "daisyui",
            ],
            help="UI 组件库",
        )
        init_parser.add_argument(
            "--style",
            choices=[
                "tailwind",
                "css-modules",
                "styled-components",
                "emotion",
                "scss",
                "less",
                "unocss",
            ],
            help="样式方案",
        )
        init_parser.add_argument(
            "--state",
            choices=["react-query", "swr", "zustand", "redux-toolkit", "jotai", "pinia", "xstate"],
            action="append",
            help="状态管理方案 (可多选)",
        )
        init_parser.add_argument(
            "--testing",
            choices=["vitest", "jest", "playwright", "cypress", "testing-library"],
            action="append",
            help="测试框架 (可多选)",
        )
        init_parser.add_argument(
            "-b", "--backend", choices=SUPPORTED_PIPELINE_BACKENDS, default="node", help="后端框架"
        )
        init_parser.add_argument("--domain", choices=SUPPORTED_DOMAINS, default="", help="业务领域")
        init_parser.add_argument(
            "--template",
            "-t",
            choices=["ecommerce", "saas", "dashboard", "mobile", "api", "blog", "miniapp"],
            help="使用预设项目模板",
        )
        product_audit_parser = subparsers.add_parser(
            "product-audit",
            help="生成产品总审查报告",
            description="从产品、交互、闭环和代码结构角度生成跨团队产品审查报告。",
        )
        product_audit_parser.add_argument(
            "path",
            nargs="?",
            default=".",
            help="项目路径 (默认为当前目录)",
        )
        product_audit_parser.add_argument(
            "-o",
            "--output",
            help="输出报告路径（默认为 output/<project>-product-audit.md 或 .json）",
        )
        product_audit_parser.add_argument(
            "-f",
            "--format",
            choices=["json", "markdown", "text"],
            default="text",
            help="输出格式",
        )
        product_audit_parser.add_argument(
            "--json",
            action="store_true",
            help="以 JSON 格式输出",
        )

        # quality 命令
        quality_parser = subparsers.add_parser(
            "quality", help="质量检查", description="运行质量检查脚本"
        )
        quality_parser.add_argument(
            "-t",
            "--type",
            choices=["prd", "architecture", "ui", "ux", "ui-review", "redteam", "code", "all"],
            default="all",
            help="检查类型",
        )

        # config 命令
        config_parser = subparsers.add_parser(
            "config",
            help=argparse.SUPPRESS,
            description="查看和修改项目配置（内部维护入口）",
        )
        config_parser.add_argument(
            "action", choices=["get", "set", "list", "validate"], help="操作"
        )
        config_parser.add_argument("key", nargs="?", help="配置键")
        config_parser.add_argument("value", nargs="?", help="配置值")

        # skill 命令 - 多平台 Skill 安装/管理
        skill_parser = subparsers.add_parser(
            "skill",
            help="内部维护：Skill 管理",
            description="安装、列出、卸载跨平台 AI Coding Skills（内部维护入口）",
        )
        skill_parser.add_argument(
            "action", choices=["list", "install", "uninstall", "targets"], help="操作类型"
        )
        skill_parser.add_argument(
            "source_or_name",
            nargs="?",
            help="install 时为来源（目录/git/super-dev），uninstall 时为 skill 名称",
        )
        skill_parser.add_argument(
            "-t",
            "--target",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            default="claude-code",
            help="目标平台 (默认: claude-code)",
        )
        skill_parser.add_argument("--name", help="安装后的 skill 名称（可选）")
        skill_parser.add_argument("--force", action="store_true", help="覆盖已存在的 skill")

        # integrate 命令 - 多平台适配配置
        integrate_parser = subparsers.add_parser(
            "integrate",
            help="内部维护：平台集成配置",
            description="为 CLI/IDE AI Coding 工具生成集成配置文件（内部维护入口）",
        )
        integrate_parser.add_argument(
            "action",
            choices=["list", "setup", "harden", "matrix", "smoke", "audit", "validate"],
            help="操作类型",
        )
        integrate_parser.add_argument(
            "-t",
            "--target",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="目标平台",
        )
        integrate_parser.add_argument("--all", action="store_true", help="对所有平台执行 setup")
        integrate_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主，仅对检测到的宿主执行审计"
        )
        integrate_parser.add_argument("--force", action="store_true", help="覆盖已存在的配置文件")
        integrate_parser.add_argument(
            "--json", action="store_true", help="以 JSON 输出集成矩阵（用于自动化）"
        )
        integrate_parser.add_argument(
            "--repair", action="store_true", help="审计时自动重装缺失或过期的宿主接入面"
        )
        integrate_parser.add_argument(
            "--no-save", action="store_true", help="不将审计结果写入 output 报告"
        )
        integrate_parser.add_argument(
            "--status",
            choices=["pending", "passed", "failed"],
            help="用于 validate：写入某个宿主的真人运行时验收状态",
        )
        integrate_parser.add_argument("--comment", help="用于 validate：补充真人运行时验收备注")
        integrate_parser.add_argument(
            "--actor", default="user", help="用于 validate：记录操作者（默认: user）"
        )
        integrate_parser.add_argument(
            "--competition-evidence-json",
            help=(
                "用于 validate：写入 SEEAI 比赛验收证据 JSON，"
                "包含 first_response/runtime_checkpoint/fallback_decision/demo_path"
            ),
        )
        integrate_parser.add_argument(
            "--verify-docs",
            action="store_true",
            help="对宿主官方文档链接执行在线可达性核验（matrix/audit）",
        )
        integrate_parser.add_argument(
            "--official-compare",
            action="store_true",
            help="对照官方文档内容校验 slash/rules/skills 能力声明（matrix/audit/harden）",
        )
        integrate_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="setup/harden/repair 时同时补齐用户级协议/命令面；默认只处理当前项目内接入面",
        )
        integrate_parser.add_argument(
            "--parity-threshold",
            type=float,
            default=95.0,
            help="宿主一致性总分门槛（默认: 95.0）",
        )

        # onboard 命令 - 首次安装向导（宿主选择 + 集成 + skill + slash）
        onboard_parser = subparsers.add_parser(
            "onboard",
            help="内部维护：首次接入向导",
            description="选择宿主 AI Coding 工具并自动完成集成、Skill 安装与 /super-dev 命令映射（内部维护入口）",
        )
        onboard_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="宿主工具（不填则进入选择模式）",
        )
        onboard_parser.add_argument("--all", action="store_true", help="对所有宿主工具执行接入")
        onboard_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主，仅对检测到的宿主执行接入"
        )
        onboard_parser.add_argument(
            "--skill-name",
            default="super-dev",
            help="安装后的 Skill 名称（默认: super-dev）",
        )
        onboard_parser.add_argument(
            "--skip-integrate", action="store_true", help="跳过规则文件集成"
        )
        onboard_parser.add_argument("--skip-skill", action="store_true", help="跳过内置 Skill 安装")
        onboard_parser.add_argument(
            "--skip-slash", action="store_true", help="跳过 /super-dev 命令映射文件生成"
        )
        onboard_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="同时写入用户级协议/命令面；默认只写当前项目内接入面",
        )
        onboard_parser.add_argument(
            "--yes", action="store_true", help="非交互模式（未指定 --host 时默认等价 --all）"
        )
        onboard_parser.add_argument(
            "--force", action="store_true", help="覆盖已存在文件并重装 Skill"
        )
        onboard_parser.add_argument(
            "--dry-run", action="store_true", help="预览将要写入的文件，不实际执行"
        )
        onboard_parser.add_argument(
            "--stable-only", action="store_true", help="仅安装 Certified 和 Compatible 级别的宿主"
        )
        onboard_parser.add_argument("--detail", action="store_true", help="显示详细落点与逐项步骤")

        # doctor 命令 - 宿主接入诊断
        doctor_parser = subparsers.add_parser(
            "doctor",
            help="内部维护：接入状态诊断",
            description="诊断当前项目在各宿主 AI Coding 工具中的集成、Skill、/super-dev 命令映射状态（内部维护入口）",
        )
        doctor_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="仅诊断指定宿主（默认诊断全部）",
        )
        doctor_parser.add_argument("--all", action="store_true", help="诊断全部宿主工具")
        doctor_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主，仅诊断检测到的宿主"
        )
        doctor_parser.add_argument(
            "--skill-name",
            default="super-dev",
            help="需要校验的 Skill 名称（默认: super-dev）",
        )
        doctor_parser.add_argument(
            "--skip-integrate", action="store_true", help="跳过集成规则文件检查"
        )
        doctor_parser.add_argument("--skip-skill", action="store_true", help="跳过 Skill 检查")
        doctor_parser.add_argument(
            "--skip-slash", action="store_true", help="跳过 /super-dev 命令映射检查"
        )
        doctor_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="repair 时也补齐用户级协议/命令面；默认只修项目内接入面",
        )
        doctor_parser.add_argument("--json", action="store_true", help="输出 JSON 诊断结果")
        doctor_parser.add_argument(
            "--repair", action="store_true", help="自动修复缺失项（集成规则 / Skill / slash 映射）"
        )
        doctor_parser.add_argument(
            "--force", action="store_true", help="修复时覆盖已有文件并重装 Skill"
        )
        doctor_parser.add_argument(
            "--detail", action="store_true", help="显示详细诊断、路径与逐项建议"
        )
        doctor_parser.add_argument("--fix", action="store_true", help="自动修复检测到的问题")

        # setup 命令 - 非技术用户一步接入
        setup_parser = subparsers.add_parser(
            "setup",
            help="内部维护：一步接入安装",
            description="一步完成宿主接入（规则 + Skill + /super-dev）并执行诊断（内部维护入口）",
        )
        setup_parser.add_argument(
            "target",
            nargs="?",
            default=None,
            type=normalize_host_tool_id,
            help="目标宿主 (如 claude-code, cursor 等)",
        )
        setup_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="宿主工具（不填默认全部）",
        )
        setup_parser.add_argument("--all", action="store_true", help="接入全部宿主工具")
        setup_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主，仅对检测到的宿主执行接入"
        )
        setup_parser.add_argument(
            "--skill-name",
            default="super-dev",
            help="安装后的 Skill 名称（默认: super-dev）",
        )
        setup_parser.add_argument("--skip-integrate", action="store_true", help="跳过规则文件集成")
        setup_parser.add_argument("--skip-skill", action="store_true", help="跳过内置 Skill 安装")
        setup_parser.add_argument(
            "--skip-slash", action="store_true", help="跳过 /super-dev 命令映射文件生成"
        )
        setup_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="同时写入用户级协议/命令面；默认只写当前项目内接入面",
        )
        setup_parser.add_argument("--skip-doctor", action="store_true", help="跳过接入诊断")
        setup_parser.add_argument("--force", action="store_true", help="覆盖已存在文件并重装 Skill")
        setup_parser.add_argument("--detail", action="store_true", help="显示详细接入与诊断信息")
        setup_parser.add_argument(
            "--yes", action="store_true", help="非交互模式（未指定 --host 时默认等价 --all）"
        )

        # install 命令 - 面向 PyPI 用户的一键安装入口
        install_parser = subparsers.add_parser(
            "install",
            help="内部维护：安装向导（宿主多选）",
            description="在终端内选择要接入的 AI Coding 宿主并完成接入安装（内部维护入口）",
        )
        install_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="宿主工具（指定后只安装该宿主）",
        )
        install_parser.add_argument("--all", action="store_true", help="安装全部宿主工具")
        install_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主并安装"
        )
        install_parser.add_argument(
            "--skill-name",
            default="super-dev",
            help="安装后的 Skill 名称（默认: super-dev）",
        )
        install_parser.add_argument(
            "--no-skill", action="store_true", help="只安装规则与 /super-dev 映射，不安装 skill"
        )
        install_parser.add_argument(
            "--skip-integrate", action="store_true", help="跳过规则文件集成"
        )
        install_parser.add_argument(
            "--skip-slash", action="store_true", help="跳过 /super-dev 命令映射文件生成"
        )
        install_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="同时写入用户级协议/命令面；默认只写当前项目内接入面",
        )
        install_parser.add_argument("--skip-doctor", action="store_true", help="跳过安装后诊断")
        install_parser.add_argument(
            "--force", action="store_true", help="覆盖已存在文件并重装 Skill"
        )
        install_parser.add_argument(
            "--yes", action="store_true", help="非交互模式（未指定 --host 时默认等价 --all）"
        )

        uninstall_parser = subparsers.add_parser(
            "uninstall",
            help="完整卸载与宿主清理",
            description="卸载 Super Dev 注入到宿主的规则、skill、slash 映射与插件增强层",
        )
        uninstall_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="宿主工具（指定后只清理该宿主）",
        )
        uninstall_parser.add_argument("--all", action="store_true", help="清理全部宿主工具")
        uninstall_parser.add_argument(
            "--auto", action="store_true", help="自动探测本机已安装宿主并清理"
        )
        uninstall_parser.add_argument(
            "--yes", action="store_true", help="非交互模式（未指定 --host 时默认等价 --all）"
        )
        uninstall_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预演将要清理的接入面与 Skill，不执行实际删除",
        )
        uninstall_parser.add_argument("--json", action="store_true", help="以 JSON 输出清理结果")

        start_parser = subparsers.add_parser(
            "start",
            help="内部维护：起步诊断入口",
            description="自动选择合适宿主、完成接入，并输出可直接复制的试用步骤（内部维护入口）",
        )
        start_parser.add_argument(
            "--idea", help="你的需求描述（可选，提供后会生成宿主内可直接使用的触发语句）"
        )
        start_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="指定宿主；默认自动检测并选择最合适的宿主",
        )
        start_parser.add_argument(
            "--skip-onboard",
            action="store_true",
            help="只输出起步步骤，不自动写入规则、Skill 与命令映射",
        )
        start_parser.add_argument(
            "--no-save-profile", action="store_true", help="不写入 super-dev.yaml 的宿主画像"
        )
        start_parser.add_argument(
            "--force", action="store_true", help="覆盖已存在的规则、Skill 或命令映射"
        )
        start_parser.add_argument(
            "--with-user-surfaces",
            action="store_true",
            help="同时写入用户级协议/命令面；默认只写当前项目内接入面",
        )
        start_parser.add_argument("--json", action="store_true", help="以 JSON 输出起步说明")

        # detect 命令 - 宿主自动探测与兼容性报告
        detect_parser = subparsers.add_parser(
            "detect",
            help="内部维护：宿主探测与兼容性报告",
            description="自动探测本机可用宿主并输出接入兼容性评分（内部维护入口）",
        )
        detect_parser.add_argument(
            "--host",
            choices=SUPPORTED_HOST_TOOLS,
            type=normalize_host_tool_id,
            help="仅分析指定宿主",
        )
        detect_parser.add_argument(
            "--all", action="store_true", help="分析全部宿主（默认仅分析自动探测到的宿主）"
        )
        detect_parser.add_argument(
            "--auto", action="store_true", help="显式启用自动探测模式（默认行为）"
        )
        detect_parser.add_argument(
            "--skill-name",
            default="super-dev",
            help="用于兼容性评分的 Skill 名称（默认: super-dev）",
        )
        detect_parser.add_argument(
            "--skip-integrate", action="store_true", help="评分时跳过集成规则文件检查"
        )
        detect_parser.add_argument(
            "--skip-skill", action="store_true", help="评分时跳过 Skill 检查"
        )
        detect_parser.add_argument(
            "--skip-slash", action="store_true", help="评分时跳过 /super-dev 命令映射检查"
        )
        detect_parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
        detect_parser.add_argument(
            "--no-save", action="store_true", help="不写入 output/host-compatibility 报告文件"
        )
        detect_parser.add_argument(
            "--save-profile",
            action="store_true",
            help="将本次 selected_targets 保存到 super-dev.yaml 的 host_profile_targets，并启用 host_profile_enforce_selected",
        )

        update_parser = subparsers.add_parser(
            "update",
            help="升级到最新版本",
            description="检查 PyPI 最新版本并使用 pip 或 uv 升级当前 super-dev",
        )
        update_parser.add_argument(
            "--check", action="store_true", help="只检查最新版本，不执行升级"
        )
        update_parser.add_argument(
            "--method", choices=["auto", "pip", "uv"], default="auto", help="升级方式（默认: auto）"
        )

        clean_parser = subparsers.add_parser(
            "clean",
            help=argparse.SUPPRESS,
            description="清理 output/ 目录中的历史产物文件，保留最近一次运行的结果",
        )
        clean_parser.add_argument(
            "--all", action="store_true", help="删除 output/ 目录下的所有产物文件"
        )
        clean_parser.add_argument(
            "--keep", type=int, default=1, help="保留最近 N 次运行的产物（默认: 1）"
        )
        clean_parser.add_argument(
            "--dry-run", action="store_true", help="只显示将要删除的文件，不实际删除"
        )

        review_parser = subparsers.add_parser(
            "review", help="管理文档确认等评审状态", description="记录或查看三文档确认状态"
        )
        review_subparsers = review_parser.add_subparsers(dest="review_command")

        review_docs_parser = review_subparsers.add_parser("docs", help="查看或更新三文档确认状态")
        review_docs_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的三文档确认状态；不传则仅查看当前状态",
        )
        review_docs_parser.add_argument("--comment", default="", help="确认意见或修改要求")
        review_docs_parser.add_argument("--run-id", default="", help="关联的运行 ID（可选）")
        review_docs_parser.add_argument("--actor", default="user", help="记录操作者（默认: user）")
        review_docs_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        review_baseline_parser = review_subparsers.add_parser(
            "baseline", help="查看或更新已有项目 baseline 确认状态"
        )
        review_baseline_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的 baseline 确认状态；不传则仅查看当前状态",
        )
        review_baseline_parser.add_argument("--comment", default="", help="baseline 确认意见或修改要求")
        review_baseline_parser.add_argument("--run-id", default="", help="关联的运行 ID（可选）")
        review_baseline_parser.add_argument(
            "--actor", default="user", help="记录操作者（默认: user）"
        )
        review_baseline_parser.add_argument(
            "--prepare",
            action="store_true",
            help="先生成/刷新 baseline audit 草稿，再进入 baseline 确认",
        )
        review_baseline_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        review_ui_parser = review_subparsers.add_parser("ui", help="查看或更新 UI 改版状态")
        review_ui_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的 UI 改版状态；不传则仅查看当前状态",
        )
        review_ui_parser.add_argument("--comment", default="", help="UI 改版意见或确认说明")
        review_ui_parser.add_argument("--run-id", default="", help="关联的运行 ID（可选）")
        review_ui_parser.add_argument("--actor", default="user", help="记录操作者（默认: user）")
        review_ui_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        review_preview_parser = review_subparsers.add_parser(
            "preview", help="查看或更新前端预览确认状态"
        )
        review_preview_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的预览确认状态；不传则仅查看当前状态",
        )
        review_preview_parser.add_argument("--comment", default="", help="预览确认意见或修改要求")
        review_preview_parser.add_argument("--run-id", default="", help="关联的运行 ID（可选）")
        review_preview_parser.add_argument(
            "--actor", default="user", help="记录操作者（默认: user）"
        )
        review_preview_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        review_architecture_parser = review_subparsers.add_parser(
            "architecture", help="查看或更新架构返工状态"
        )
        review_architecture_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的架构返工状态；不传则仅查看当前状态",
        )
        review_architecture_parser.add_argument(
            "--comment", default="", help="架构返工意见或确认说明"
        )
        review_architecture_parser.add_argument(
            "--run-id", default="", help="关联的运行 ID（可选）"
        )
        review_architecture_parser.add_argument(
            "--actor", default="user", help="记录操作者（默认: user）"
        )
        review_architecture_parser.add_argument(
            "--json", action="store_true", help="以 JSON 格式输出"
        )

        review_quality_parser = review_subparsers.add_parser(
            "quality", help="查看或更新质量返工状态"
        )
        review_quality_parser.add_argument(
            "--status",
            choices=["pending_review", "revision_requested", "confirmed"],
            help="要写入的质量返工状态；不传则仅查看当前状态",
        )
        review_quality_parser.add_argument("--comment", default="", help="质量返工意见或确认说明")
        review_quality_parser.add_argument("--run-id", default="", help="关联的运行 ID（可选）")
        review_quality_parser.add_argument(
            "--actor", default="user", help="记录操作者（默认: user）"
        )
        review_quality_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        release_parser = subparsers.add_parser(
            "release",
            help="发布收尾与就绪度检查",
            description="检查当前仓库距离对外发布还剩哪些关键缺口",
        )
        release_subparsers = release_parser.add_subparsers(dest="release_command")

        release_readiness_parser = release_subparsers.add_parser("readiness", help="发布就绪度评估")
        release_readiness_parser.add_argument(
            "--verify-tests",
            action="store_true",
            help="执行 pytest -q，并把测试结果纳入发布就绪度评分",
        )
        release_readiness_parser.add_argument(
            "--json", action="store_true", help="以 JSON 输出结果"
        )
        release_proof_pack_parser = release_subparsers.add_parser(
            "proof-pack", help="生成交付证据包摘要"
        )
        release_proof_pack_parser.add_argument(
            "--verify-tests",
            action="store_true",
            help="执行 release readiness 时纳入 pytest -q 结果",
        )
        release_proof_pack_parser.add_argument(
            "--json", action="store_true", help="以 JSON 输出结果"
        )

        # spec 命令 - Spec-Driven Development
        spec_parser = subparsers.add_parser(
            "spec", help="规范驱动开发 (SDD)", description="管理规范和变更提案"
        )
        spec_subparsers = spec_parser.add_subparsers(
            dest="spec_action",
            title="SDD 命令",
            description="使用 'super-dev spec <command> -h' 查看帮助",
        )

        # spec init
        spec_subparsers.add_parser("init", help="初始化 SDD 目录结构")

        # spec list
        spec_list_parser = spec_subparsers.add_parser("list", help="列出所有变更")
        spec_list_parser.add_argument(
            "--status",
            choices=["draft", "proposed", "approved", "in_progress", "completed", "archived"],
            help="按状态过滤",
        )

        # spec show
        spec_show_parser = spec_subparsers.add_parser("show", help="显示变更详情")
        spec_show_parser.add_argument("change_id", help="变更 ID")

        # spec propose
        spec_propose_parser = spec_subparsers.add_parser("propose", help="创建变更提案")
        spec_propose_parser.add_argument("change_id", help="变更 ID (如 add-user-auth)")
        spec_propose_parser.add_argument("--title", required=True, help="变更标题")
        spec_propose_parser.add_argument("--description", required=True, help="变更描述")
        spec_propose_parser.add_argument("--motivation", help="变更动机/背景")
        spec_propose_parser.add_argument("--impact", help="影响范围")
        spec_propose_parser.add_argument(
            "--no-scaffold",
            action="store_true",
            help="仅创建 proposal，不生成 spec/plan/tasks/checklist 模板",
        )

        # spec add-req
        spec_add_req_parser = spec_subparsers.add_parser("add-req", help="向变更添加需求")
        spec_add_req_parser.add_argument("change_id", help="变更 ID")
        spec_add_req_parser.add_argument("spec_name", help="规范名称 (如 auth, user-profile)")
        spec_add_req_parser.add_argument("req_name", help="需求名称")
        spec_add_req_parser.add_argument("description", help="需求描述")

        spec_scaffold_parser = spec_subparsers.add_parser(
            "scaffold", help="为变更生成 spec/plan/tasks/checklist 四件套"
        )
        spec_scaffold_parser.add_argument("change_id", help="变更 ID")
        spec_scaffold_parser.add_argument("--force", action="store_true", help="强制覆盖已存在文件")

        spec_quality_parser = spec_subparsers.add_parser("quality", help="评估 Spec 完整度与质量分")
        spec_quality_parser.add_argument("change_id", help="变更 ID")
        spec_quality_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

        # spec archive
        spec_archive_parser = spec_subparsers.add_parser("archive", help="归档已完成的变更")
        spec_archive_parser.add_argument("change_id", help="变更 ID")
        spec_archive_parser.add_argument("-y", "--yes", action="store_true", help="跳过确认")

        # spec validate
        spec_validate_parser = spec_subparsers.add_parser("validate", help="验证规格格式和结构")
        spec_validate_parser.add_argument(
            "change_id", nargs="?", help="变更 ID (留空则验证所有变更)"
        )
        spec_validate_parser.add_argument(
            "-v", "--verbose", action="store_true", help="显示详细信息"
        )

        # spec view
        spec_view_parser = spec_subparsers.add_parser(
            "view", help="交互式仪表板 - 显示所有规范和变更"
        )
        spec_view_parser.add_argument("--refresh", action="store_true", help="强制刷新数据")

        # spec trace
        spec_trace_parser = spec_subparsers.add_parser("trace", help="生成需求追溯矩阵")
        spec_trace_parser.add_argument("change_id", help="变更 ID")
        spec_trace_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
        spec_trace_parser.add_argument(
            "--save",
            action="store_true",
            help="保存追溯矩阵到 .super-dev/changes/<id>/traceability.md",
        )

        # spec consistency
        spec_consistency_parser = spec_subparsers.add_parser(
            "consistency", help="检测 Spec-Code 一致性（防止 spec-code 漂移）"
        )
        spec_consistency_parser.add_argument("change_id", help="变更 ID")
        spec_consistency_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
        spec_consistency_parser.add_argument(
            "--save",
            action="store_true",
            help="保存报告到 .super-dev/changes/<id>/consistency.md",
        )

        # spec acceptance
        spec_acceptance_parser = spec_subparsers.add_parser("acceptance", help="生成验收检查清单")
        spec_acceptance_parser.add_argument("change_id", help="变更 ID")
        spec_acceptance_parser.add_argument(
            "--save",
            action="store_true",
            help="保存验收清单到 .super-dev/changes/<id>/acceptance.md",
        )

        # task 命令 - 独立执行/查看 Spec 任务闭环
        task_parser = subparsers.add_parser(
            "task",
            help="Spec 任务闭环执行",
            description="执行或查看 `.super-dev/changes/*/tasks.md` 的任务状态",
        )
        task_parser.add_argument("action", choices=["run", "status", "list"], help="任务操作类型")
        task_parser.add_argument("change_id", nargs="?", help="变更 ID（run/status 必填）")
        task_parser.add_argument(
            "-p", "--platform", choices=SUPPORTED_PLATFORMS, help="目标平台（可选，默认取项目配置）"
        )
        task_parser.add_argument(
            "-f",
            "--frontend",
            choices=SUPPORTED_PIPELINE_FRONTENDS,
            help="前端框架（可选，默认取项目配置）",
        )
        task_parser.add_argument(
            "-b",
            "--backend",
            choices=SUPPORTED_PIPELINE_BACKENDS,
            help="后端框架（可选，默认取项目配置）",
        )
        task_parser.add_argument(
            "-d", "--domain", choices=SUPPORTED_DOMAINS, help="业务领域（可选，默认取项目配置）"
        )
        task_parser.add_argument(
            "--project-name", help="任务执行报告中的项目名（默认取配置名或 change_id）"
        )
        task_parser.add_argument(
            "--max-retries", type=int, default=1, help="失败自动修复重试次数（默认: 1）"
        )

        design_parser = subparsers.add_parser(
            "design",
            help="设计灵感工作流",
            description="列出、推荐并应用设计灵感锚点，驱动 UIUX / UI 契约生成",
        )
        design_subparsers = design_parser.add_subparsers(
            dest="design_command",
            title="设计命令",
            description="使用 'super-dev design <command> -h' 查看帮助",
        )

        design_list_parser = design_subparsers.add_parser(
            "list",
            help="列出设计灵感锚点",
            description="列出内置设计灵感库，供 UI/UX 方向选择与参考",
        )
        design_list_parser.add_argument("--product-type", help="产品类型过滤")
        design_list_parser.add_argument("--industry", help="行业过滤")
        design_list_parser.add_argument("--style", help="风格过滤")
        design_list_parser.add_argument("--frontend", help="前端栈过滤")
        design_list_parser.add_argument(
            "-n", "--max-results", type=int, default=10, help="最大结果数 (默认: 10)"
        )

        design_recommend_parser = design_subparsers.add_parser(
            "recommend",
            help="推荐设计灵感锚点",
            description="结合当前项目配置或需求描述，推荐最合适的设计灵感方向",
        )
        design_recommend_parser.add_argument(
            "--idea", default="", help="显式需求描述；未提供时优先读取 super-dev.yaml 中的 description"
        )
        design_recommend_parser.add_argument("--product-type", help="显式指定产品类型")
        design_recommend_parser.add_argument("--industry", help="显式指定行业")
        design_recommend_parser.add_argument("--style", help="显式指定风格")
        design_recommend_parser.add_argument("--frontend", help="显式指定前端栈")
        design_recommend_parser.add_argument(
            "-n", "--max-results", type=int, default=3, help="最大推荐数 (默认: 3)"
        )

        design_apply_parser = design_subparsers.add_parser(
            "apply",
            help="应用设计灵感锚点",
            description="将指定设计灵感写入项目配置，并可同步重生成 uiux/ui-contract",
        )
        design_apply_parser.add_argument("slug", help="设计灵感 slug，例如 linear.app / vercel / stripe")
        design_apply_parser.add_argument(
            "--idea", default="", help="可选需求描述；仅在当前项目 description 为空时作为补充上下文"
        )
        design_apply_parser.add_argument(
            "--write-uiux",
            dest="write_uiux",
            action="store_true",
            help="应用后同步重生成 output/*-uiux.md 和 output/*-ui-contract.json（默认开启）",
        )
        design_apply_parser.add_argument(
            "--no-write-uiux",
            dest="write_uiux",
            action="store_false",
            help="仅写入配置与灵感记录，不重生成 UI 文档",
        )
        design_apply_parser.set_defaults(write_uiux=True)

        # pipeline 命令 - 完整流水线
        pipeline_parser = subparsers.add_parser(
            "pipeline",
            help="运行完整流水线 (从想法到部署)",
            description="执行完整开发流水线：需求增强 → 文档 → 前端实施蓝图 → Spec → 宿主实现参考 → 审查与门禁 → 交付配置",
        )
        pipeline_parser.add_argument("description", help="功能描述 (如 '用户认证系统')")
        pipeline_parser.add_argument(
            "--mode",
            choices=["feature", "bugfix"],
            default="feature",
            help="请求模式（默认 feature；bugfix 会启用轻量缺陷修复路径）",
        )
        pipeline_parser.add_argument(
            "-p", "--platform", choices=SUPPORTED_PLATFORMS, default="web", help="目标平台"
        )
        pipeline_parser.add_argument(
            "-f",
            "--frontend",
            choices=SUPPORTED_PIPELINE_FRONTENDS,
            default="react",
            help="前端框架",
        )
        pipeline_parser.add_argument(
            "-b", "--backend", choices=SUPPORTED_PIPELINE_BACKENDS, default="node", help="后端框架"
        )
        pipeline_parser.add_argument(
            "-d", "--domain", choices=SUPPORTED_DOMAINS, default="", help="业务领域"
        )
        pipeline_parser.add_argument("--name", help="项目名称 (默认根据描述生成)")
        pipeline_parser.add_argument(
            "--cicd", choices=SUPPORTED_CICD, default="all", help="CI/CD 平台"
        )
        pipeline_parser.add_argument("--skip-redteam", action="store_true", help="跳过红队审查")
        pipeline_parser.add_argument(
            "--skip-scaffold", action="store_true", help="跳过宿主实现参考模板输出"
        )
        pipeline_parser.add_argument(
            "--skip-quality-gate", action="store_true", help="跳过质量门禁检查"
        )
        pipeline_parser.add_argument(
            "--offline", action="store_true", help="离线模式（禁用联网检索）"
        )
        pipeline_parser.add_argument(
            "--quality-threshold",
            type=int,
            default=None,
            help="质量门禁阈值（可选；默认按场景自动判定）",
        )
        pipeline_parser.add_argument(
            "--skip-rehearsal-verify",
            action="store_true",
            help="跳过发布演练验证（默认执行）",
        )
        pipeline_parser.add_argument(
            "--resume",
            action="store_true",
            help="恢复模式：优先复用上次已完成阶段产物（含自动降级与审计报告）",
        )

        # run 命令 - 运行控制（如失败恢复）
        run_parser = subparsers.add_parser(
            "run", help="运行控制", description="运行控制命令（恢复、状态、阶段回跳、阶段确认）"
        )
        run_parser.add_argument(
            "stage_selector",
            nargs="?",
            help="快捷阶段入口（如 research/prd/architecture/uiux/frontend/backend/quality）",
        )
        run_parser.add_argument(
            "--resume",
            action="store_true",
            help="恢复最近一次失败的 pipeline 运行",
        )
        run_parser.add_argument(
            "--status",
            action="store_true",
            help="查看当前流程状态、阶段确认与推荐下一步",
        )
        run_parser.add_argument(
            "--phase",
            help="从指定阶段继续执行（如 docs/spec/frontend/backend/quality/delivery）",
        )
        run_parser.add_argument(
            "--jump",
            help="跳转到指定阶段并继续执行（会先展示影响面）",
        )
        run_parser.add_argument(
            "--confirm",
            dest="confirm_phase",
            help="确认指定阶段（docs/ui/architecture/quality/frontend/backend/delivery）",
        )
        run_parser.add_argument(
            "--comment",
            default="",
            help="阶段确认备注",
        )
        run_parser.add_argument(
            "--actor",
            default="cli-user",
            help="阶段确认操作者",
        )
        run_parser.add_argument(
            "--json",
            action="store_true",
            help="状态输出使用 JSON 格式",
        )

        status_parser = subparsers.add_parser(
            "status",
            help="查看当前流程状态",
            description="快捷别名，等同于 super-dev run --status",
        )
        status_parser.add_argument(
            "--json",
            action="store_true",
            help="状态输出使用 JSON 格式",
        )

        next_parser = subparsers.add_parser(
            "next",
            help="给出当前仓库唯一推荐下一步",
            description="基于当前仓库的初始化状态、运行状态和交付证据，输出当前最应该执行的一步。",
        )
        next_parser.add_argument(
            "--json",
            action="store_true",
            help="以 JSON 输出推荐结果",
        )

        continue_parser = subparsers.add_parser(
            "continue",
            help="继续当前仓库的 Super Dev 流程",
            description="比 next 更自然的继续入口，会直接告诉你当前步骤、下一步动作和宿主里第一句该发什么。",
        )
        continue_parser.add_argument(
            "--json",
            action="store_true",
            help="以 JSON 输出继续建议",
        )

        resume_parser = subparsers.add_parser(
            "resume",
            help="回到当前仓库的 Super Dev 流程",
            description="面向真实恢复场景的直觉入口。适合下班关掉、重开电脑、第二天回来继续开发时使用。",
        )
        resume_parser.add_argument(
            "--json",
            action="store_true",
            help="以 JSON 输出恢复建议",
        )

        jump_parser = subparsers.add_parser(
            "jump",
            help="跳转到指定阶段",
            description="快捷别名，等同于 super-dev run --jump <stage>",
        )
        jump_parser.add_argument(
            "stage",
            help="目标阶段（如 docs/frontend/backend/quality）",
        )

        confirm_parser = subparsers.add_parser(
            "confirm",
            help="确认指定阶段",
            description="快捷别名，等同于 super-dev run --confirm <phase>",
        )
        confirm_parser.add_argument(
            "phase",
            help="需要确认的阶段（如 docs/preview/frontend/backend/quality）",
        )
        confirm_parser.add_argument(
            "--comment",
            default="",
            help="阶段确认备注",
        )
        confirm_parser.add_argument(
            "--actor",
            default="cli-user",
            help="阶段确认操作者",
        )

        # enforce 命令 - 宿主侧执行机制
        enforce_parser = subparsers.add_parser(
            "enforce",
            help=argparse.SUPPRESS,
            description="安装、验证和查看宿主侧 hooks 与验证规则（内部维护入口）",
        )
        enforce_subparsers = enforce_parser.add_subparsers(
            dest="enforce_action",
            title="Enforce 命令",
            description="使用 'super-dev enforce <command> -h' 查看帮助",
        )
        enforce_install_parser = enforce_subparsers.add_parser(
            "install", help="安装宿主 hooks 和验证脚本"
        )
        enforce_install_parser.add_argument(
            "--host",
            choices=["claude-code"],
            default="claude-code",
            help="目标宿主 (默认 claude-code)",
        )
        enforce_install_parser.add_argument(
            "--frontend", default="", help="前端框架 (用于验证脚本)"
        )
        enforce_install_parser.add_argument(
            "--backend", default="", help="后端框架 (用于 pre-code checklist)"
        )
        enforce_install_parser.add_argument(
            "--icon-library", default="lucide", help="图标库 (默认 lucide)"
        )
        enforce_subparsers.add_parser("validate", help="运行验证脚本")
        enforce_subparsers.add_parser("status", help="查看 enforcement 状态")

        # generate 命令 - 项目脚手架生成
        generate_parser = subparsers.add_parser(
            "generate",
            help=argparse.SUPPRESS,
            description="根据前端框架类型生成内部实施参考模板（内部维护入口）",
        )
        generate_subparsers = generate_parser.add_subparsers(
            dest="generate_action",
            title="生成命令",
            description="使用 'super-dev generate <command> -h' 查看帮助",
        )
        scaffold_parser = generate_subparsers.add_parser("scaffold", help="生成内部实施参考模板")
        scaffold_parser.add_argument(
            "--frontend",
            choices=["next"],
            default="next",
            help="前端框架 (默认 next)",
        )
        scaffold_parser.add_argument("--name", default="", help="项目名称 (可选)")

        generate_subparsers.add_parser(
            "components",
            help="从 UIUX 规范导出内部组件参考模板",
        )
        generate_subparsers.add_parser(
            "types",
            help="从架构文档导出共享 TypeScript 参考类型",
        )
        generate_subparsers.add_parser(
            "tailwind",
            help="从 UIUX 规范导出 tailwind.config.ts 参考模板",
        )

        # completion 命令 - shell 补全脚本
        completion_parser = subparsers.add_parser(
            "completion",
            help=argparse.SUPPRESS,
            description="输出 bash/zsh/fish 补全脚本，可通过 eval 加载",
        )
        completion_parser.add_argument(
            "shell",
            choices=["bash", "zsh", "fish"],
            help="shell 类型",
        )

        # feedback 命令 - 打开反馈页面
        subparsers.add_parser(
            "feedback",
            help=argparse.SUPPRESS,
            description="在浏览器中打开 GitHub Issues 页面",
        )

        # migrate 命令 - 项目版本迁移
        subparsers.add_parser(
            "migrate",
            help=argparse.SUPPRESS,
            description="将 2.2.0+ 项目配置迁移到 2.4.0（更新配置、规则文件与 hooks）",
        )

        # compliance 命令 — 规格合规检查
        compliance_parser = subparsers.add_parser(
            "compliance",
            help="规格合规检查 (Spec Compliance)",
            description="检查 PRD 要求与实现代码的可追溯性，架构漂移检测，UIUX 合规验证",
        )
        compliance_parser.add_argument(
            "--type",
            choices=["all", "spec", "architecture", "uiux"],
            default="all",
            help="检查类型 (默认: all)",
        )
        compliance_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
        compliance_parser.add_argument(
            "--save", action="store_true", help="保存报告到 output/"
        )

        return parser
