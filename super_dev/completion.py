"""Shell 补全脚本生成。"""

# 所有顶级子命令
_SUBCOMMANDS = [
    "update",
    "uninstall",
]


def generate_bash_completion() -> str:
    """生成 Bash 补全脚本。"""
    cmds = " ".join(_SUBCOMMANDS)
    return f"""\
# super-dev bash completion
# 使用方法: eval "$(super-dev completion bash)"

_super_dev_completions() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local commands="{cmds}"

    if [[ ${{COMP_CWORD}} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${{commands}}" -- "${{cur}}") )
    fi
}}

complete -F _super_dev_completions super-dev
"""


def generate_zsh_completion() -> str:
    """生成 Zsh 补全脚本。"""
    cmds = " ".join(f"'{c}'" for c in _SUBCOMMANDS)
    return f"""\
#compdef super-dev
# super-dev zsh completion
# 使用方法: eval "$(super-dev completion zsh)"

_super_dev() {{
    local -a commands
    commands=({cmds})

    _arguments '1:command:compadd -a commands'
}}

compdef _super_dev super-dev
"""


def generate_fish_completion() -> str:
    """生成 Fish 补全脚本。"""
    lines = [
        "# super-dev fish completion",
        "# 使用方法: super-dev completion fish | source",
        "",
    ]
    for cmd in _SUBCOMMANDS:
        lines.append(f"complete -c super-dev -n '__fish_use_subcommand' " f"-a '{cmd}' -d '{cmd}'")
    return "\n".join(lines) + "\n"
