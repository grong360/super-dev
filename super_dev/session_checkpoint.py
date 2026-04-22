"""Session checkpoint — save/restore pipeline state for crash recovery."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHECKPOINT_DIR = ".super-dev/checkpoints/sessions"


def save_checkpoint(project_dir: Path, phase: str, context: dict[str, Any]) -> Path:
    """Save a checkpoint after completing a phase."""
    checkpoint_dir = project_dir / CHECKPOINT_DIR
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "completed_phases": context.get("completed_phases", []),
        "user_input": {
            k: v
            for k, v in context.get("user_input", {}).items()
            if isinstance(v, str | int | float | bool | list)
        },
        "metadata": context.get("metadata", {}),
    }

    filepath = checkpoint_dir / "latest.json"
    filepath.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath

