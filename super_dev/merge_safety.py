"""
Merge safety checker — detects silently dropped code hunks after git merge.

Standard git workflow practice: after merging branches, verify that
no code was accidentally lost due to conflict resolution.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def check_recent_merge(project_dir: Path) -> dict[str, Any]:
    """Check if the last commit was a merge commit.

    Returns a dict with:
        merge_detected (bool): True if HEAD is a merge commit.
        merge_sha (str): The SHA of the merge commit, or empty string.
        parent_shas (list[str]): SHA list of the merge parents.
    """
    project_dir = Path(project_dir).resolve()

    # A merge commit has more than one parent.
    parent_line = _run_git(["rev-parse", "HEAD^@"], cwd=project_dir)
    if not parent_line:
        return {"merge_detected": False, "merge_sha": "", "parent_shas": []}

    parents = [line for line in parent_line.splitlines() if line.strip()]
    if len(parents) < 2:
        return {"merge_detected": False, "merge_sha": "", "parent_shas": parents}

    merge_sha = _run_git(["rev-parse", "HEAD"], cwd=project_dir)
    return {
        "merge_detected": True,
        "merge_sha": merge_sha,
        "parent_shas": parents,
    }


def _files_changed_in_merge(project_dir: Path, merge_sha: str, parent_sha: str) -> list[str]:
    """Return list of files that differ between a parent and the merge result."""
    output = _run_git(["diff", "--name-only", parent_sha, merge_sha], cwd=project_dir)
    if not output:
        return []
    return [f for f in output.splitlines() if f.strip()]


def _get_file_at_commit(project_dir: Path, commit: str, filepath: str) -> list[str]:
    """Return the lines of a file at a given commit, or empty list if missing."""
    content = _run_git(["show", f"{commit}:{filepath}"], cwd=project_dir)
    if not content:
        return []
    return content.splitlines()


def _find_dropped_blocks(
    parent_lines: list[str],
    merge_lines: list[str],
    min_block_size: int = 5,
) -> list[dict[str, Any]]:
    """Find contiguous blocks of lines present in parent but absent in merge result.

    Only reports blocks of *min_block_size* or more non-blank lines.
    """
    merge_set = set(merge_lines)
    dropped_blocks: list[dict[str, Any]] = []
    current_block: list[str] = []
    block_start = 0

    for idx, line in enumerate(parent_lines):
        stripped = line.strip()
        # Skip blank lines for block detection
        if not stripped:
            if current_block:
                if len(current_block) >= min_block_size:
                    dropped_blocks.append(
                        {
                            "start_line": block_start + 1,
                            "end_line": block_start + len(current_block),
                            "line_count": len(current_block),
                            "preview": current_block[0],
                        }
                    )
                current_block = []
            continue

        if line not in merge_set:
            if not current_block:
                block_start = idx
            current_block.append(line)
        else:
            if current_block and len(current_block) >= min_block_size:
                dropped_blocks.append(
                    {
                        "start_line": block_start + 1,
                        "end_line": block_start + len(current_block),
                        "line_count": len(current_block),
                        "preview": current_block[0],
                    }
                )
            current_block = []

    # Flush remaining block
    if current_block and len(current_block) >= min_block_size:
        dropped_blocks.append(
            {
                "start_line": block_start + 1,
                "end_line": block_start + len(current_block),
                "line_count": len(current_block),
                "preview": current_block[0],
            }
        )

    return dropped_blocks


def detect_dropped_hunks(
    project_dir: Path,
    min_block_size: int = 5,
) -> dict[str, Any]:
    """Compare the merge result with both parent commits and detect dropped code.

    Returns:
        {
            "merge_detected": bool,
            "dropped_files": [
                {
                    "file": str,
                    "parent": str,  # which parent SHA the code came from
                    "blocks": [{"start_line": int, "end_line": int, "line_count": int, "preview": str}]
                },
                ...
            ],
            "safe": bool,  # True if no significant code was dropped
        }
    """
    project_dir = Path(project_dir).resolve()
    merge_info = check_recent_merge(project_dir)

    if not merge_info["merge_detected"]:
        return {"merge_detected": False, "dropped_files": [], "safe": True}

    merge_sha = merge_info["merge_sha"]
    parents = merge_info["parent_shas"]
    dropped_files: list[dict[str, Any]] = []

    # Collect all files changed between each parent and the merge
    checked_combos: set[tuple[str, str]] = set()

    for parent_sha in parents:
        changed = _files_changed_in_merge(project_dir, merge_sha, parent_sha)
        for filepath in changed:
            combo = (parent_sha, filepath)
            if combo in checked_combos:
                continue
            checked_combos.add(combo)

            # Skip binary / non-text files by extension
            if filepath.endswith(
                (".png", ".jpg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".lock")
            ):
                continue

            parent_lines = _get_file_at_commit(project_dir, parent_sha, filepath)
            merge_lines = _get_file_at_commit(project_dir, merge_sha, filepath)

            if not parent_lines:
                continue

            blocks = _find_dropped_blocks(parent_lines, merge_lines, min_block_size)
            if blocks:
                dropped_files.append(
                    {
                        "file": filepath,
                        "parent": parent_sha[:8],
                        "blocks": blocks,
                    }
                )

    return {
        "merge_detected": True,
        "dropped_files": dropped_files,
        "safe": len(dropped_files) == 0,
    }
