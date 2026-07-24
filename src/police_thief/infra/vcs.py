"""Best-effort discovery of the git commit hash that produced this running
process (FR-087: the declaration JSON's ``github_commit`` field, Appendix F
mandatory rule 5).

A running process can never be *certain* of its own containing commit — it
might be started from a dirty working tree, a detached checkout, or no git
repository at all — so this always degrades to a documented placeholder
rather than raising or lying with a stale/fabricated hash.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

UNKNOWN_COMMIT = "unknown"

# src/police_thief/infra/vcs.py -> parents[0]=infra, [1]=police_thief, [2]=src, [3]=repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def current_commit_hash(repo_dir: Path | None = None, *, timeout_seconds: float = 5.0) -> str:
    """Return ``git rev-parse HEAD`` run inside ``repo_dir`` (defaults to this
    package's own repo root, so the result doesn't depend on the caller's
    current working directory), or :data:`UNKNOWN_COMMIT` if git isn't
    installed, this isn't a git checkout, or the working tree is dirty in a
    way that makes the hash misleading. Never raises.
    """
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir or _REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return UNKNOWN_COMMIT
    if result.returncode != 0:
        return UNKNOWN_COMMIT
    commit = result.stdout.strip()
    return commit if commit else UNKNOWN_COMMIT
