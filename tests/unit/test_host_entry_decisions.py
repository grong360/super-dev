from pathlib import Path
from types import SimpleNamespace

from super_dev.host_entry_decisions import (
    build_detected_host_decision_card,
    build_host_repair_action,
    host_selection_reason,
)


def test_build_host_repair_action_prefers_kimi_skill_and_native_resume():
    usage = {
        "host": "Kimi Code",
        "trigger_command": "super-dev: <需求描述>",
        "experience_profile": {
            "preferred_entries": ["super-dev: 你的需求", "/skill:super-dev 你的需求"],
            "native_resume": ["kimi --continue", "kimi --resume"],
        },
    }

    action = build_host_repair_action(
        target="kimi-code",
        usage=usage,
        phase="runtime",
        host_name="Kimi Code",
    )

    assert "Kimi Code" in action
    assert "kimi --continue" in action
    assert "/skill:super-dev" in action


def test_build_host_repair_action_prefers_droid_slash_for_surface_repair():
    usage = {
        "host": "Droid CLI",
        "trigger_command": "/super-dev <需求描述>",
        "experience_profile": {
            "preferred_entries": ["/super-dev 你的需求", "/super-dev-seeai 比赛需求"],
            "native_resume": ["droid exec --session-id <id>", "/super-dev 继续当前流程"],
        },
    }

    action = build_host_repair_action(
        target="droid-cli",
        usage=usage,
        phase="surface",
        host_name="Droid CLI",
    )

    assert "重新运行 super-dev" in action
    assert "/super-dev 你的需求" in action
    assert "Factory session" in action


def test_build_host_repair_action_prefers_claude_slash_resume_for_validation():
    usage = {
        "host": "Claude Code",
        "trigger_command": "/super-dev <需求描述>",
        "experience_profile": {
            "preferred_entries": ["/super-dev 你的需求"],
            "native_resume": ["/super-dev 继续当前流程", "回当前 Claude Code 会话继续"],
        },
    }

    action = build_host_repair_action(
        target="claude-code",
        usage=usage,
        phase="validation",
        host_name="Claude Code",
    )

    assert "Claude Code" in action
    assert "/super-dev 继续当前流程" in action
    assert "重开当前 Claude Code 会话" in action


def test_host_selection_reason_includes_best_for_and_protocol_for_flagship_host():
    manager = SimpleNamespace(
        get_adapter_profile=lambda _target: SimpleNamespace(
            certification_level="certified",
            host_protocol_mode="official-skill",
        ),
        supports_slash=lambda _target: True,
    )

    reason = host_selection_reason(integration_manager=manager, target="kimi-code")

    assert "旗舰宿主" in reason
    assert "中文项目协作" in reason
    assert "official-skill" in reason


def test_build_detected_host_decision_card_mentions_competition_project_supplements():
    project_dir = Path("/tmp/demo-project")
    manager = SimpleNamespace(
        get_adapter_profile=lambda _target: SimpleNamespace(
            certification_level="certified",
            certification_label="Certified",
            category="cli",
        ),
        supports_slash=lambda _target: False,
        readiness_surface_sets=lambda **_kwargs: {
            "official_project": [],
            "official_user": [],
            "optional_project": [],
            "optional_user": [],
            "compatibility": [],
            "official_skill": [],
            "optional_skill": [],
            "compatibility_skill": [],
            "required_slash": [],
            "optional_slash": [],
            "compatibility_slash": [],
        },
        managed_competition_project_surfaces=lambda _target: [".kimi/skills/super-dev-seeai/SKILL.md"],
        managed_competition_user_surfaces=lambda _target: ["~/.kimi/skills/super-dev-seeai/SKILL.md"],
        _resolve_surface_declaration=lambda **kwargs: Path(str(kwargs["surface"]).replace("~/", "/tmp/home/")),
        project_dir=project_dir,
    )
    usage = {
        "host": "Kimi Code",
        "trigger_command": "super-dev: <需求描述>",
        "primary_entry": "super-dev: 你的需求",
        "precondition_label": "ready",
        "path_override": {},
        "experience_profile": {
            "label": "Flagship",
            "best_for": "中文项目协作",
            "resume_style": "native-resume",
            "strengths": ["中文协作体验"],
            "preferred_entries": ["super-dev: 你的需求", "/skill:super-dev 你的需求"],
            "native_resume": ["kimi --continue", "kimi --resume"],
        },
        "managed_competition_project_surfaces": [".kimi/skills/super-dev-seeai/SKILL.md"],
        "host_protocol_mode": "official-agents-entry",
        "official_project_surfaces": ["AGENTS.md"],
        "official_user_surfaces": [],
        "optional_project_surfaces": [".kimi/skills/super-dev/SKILL.md"],
        "optional_user_surfaces": ["~/.kimi/skills/super-dev/SKILL.md"],
    }
    card = build_detected_host_decision_card(
        project_dir=project_dir,
        integration_manager=manager,
        detected_targets=["kimi-code"],
        detected_meta={"kimi-code": ["PATH"]},
        preferred_targets=None,
        usage_profile_fn=lambda _target: usage,
        session_resume_card_fn=lambda _project_dir, _target: {"enabled": False},
        explain_detection_details_fn=lambda _meta: {"kimi-code": ["PATH"]},
        workflow_mode_label_fn=lambda _mode: "开始新流程",
        candidate_trigger_fn=lambda _target, _usage, _profile: "super-dev: 你的需求",
        first_action_fn=lambda _target, _usage, _profile, _card: "先用 super-dev: 你的需求",
        first_suggestion_text_fn=lambda _target, _candidates: "super-dev: 你的需求",
        default_action_examples=["super-dev: 做一个新项目"],
        no_host_card_fn=lambda: {},
    )

    assert any("官方补充检查" in line for line in card["lines"])
    assert any("super-dev-seeai" in line for line in card["lines"])
