"""
git_api.py — Erebus git integration.

Runs git subprocesses to get status, branch, and diff info.
All methods are safe to call when git is not installed or the path
is not a git repo — they return empty/fallback data rather than raising.

Called from JS via window.pywebview.api.git_*
"""

import os
import subprocess
import threading
from pathlib import Path


def _run(args: list, cwd: str, timeout: int = 5) -> tuple[int, str, str]:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", "git not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _find_repo_root(path: str) -> str | None:
    """Walk up from path to find the .git directory."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    for candidate in [p, *p.parents]:
        if (candidate / ".git").exists():
            return str(candidate)
    return None


class GitAPI:

    def __init__(self):
        self._cache      = {}   # repo_root -> {path: status_char}
        self._cache_root = None
        self._lock       = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def git_status(self, directory: str) -> dict:
        """
        Returns git status for all files under `directory`.
        Result: {
          "ok": True,
          "repo_root": "/abs/path",
          "branch": "main",
          "files": {"rel/path": "M"|"A"|"D"|"?"|"R"|"!"}
        }
        """
        root = _find_repo_root(directory)
        if not root:
            return {"ok": False, "reason": "not_a_repo"}

        rc, out, _ = _run(
            ["git", "status", "--porcelain", "-u", "--no-renames"],
            cwd=root,
        )
        if rc != 0:
            return {"ok": False, "reason": "git_error"}

        files = {}
        for line in out.splitlines():
            if len(line) < 4:
                continue
            xy   = line[:2]
            path = line[3:].strip().strip('"')
            # Collapse XY to a single status char
            x, y = xy[0], xy[1]
            if x == "?" and y == "?":
                status = "?"
            elif x in ("A",) or y in ("A",):
                status = "A"
            elif x in ("D",) or y in ("D",):
                status = "D"
            elif x in ("R",):
                status = "R"
            elif x in ("M", "T") or y in ("M", "T"):
                status = "M"
            elif x == "!" and y == "!":
                status = "!"
            else:
                status = "M"
            files[path] = status

        # Get branch name
        _, branch_out, _ = _run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
        )
        branch = branch_out.strip() or "HEAD"

        with self._lock:
            self._cache[root] = files
            self._cache_root  = root

        return {
            "ok":        True,
            "repo_root": root,
            "branch":    branch,
            "files":     files,
        }

    def git_diff(self, path: str) -> dict:
        """Return unified diff for a single file."""
        root = _find_repo_root(path)
        if not root:
            return {"ok": False, "reason": "not_a_repo"}

        rc, out, _ = _run(
            ["git", "diff", "HEAD", "--", path],
            cwd=root,
        )
        if rc != 0:
            return {"ok": False, "reason": "git_error"}

        return {"ok": True, "diff": out}

    def git_log(self, path: str, max_entries: int = 20) -> dict:
        """Return recent commits touching `path` (or whole repo if path is a dir)."""
        root = _find_repo_root(path)
        if not root:
            return {"ok": False, "reason": "not_a_repo"}

        args = [
            "git", "log",
            f"--max-count={max_entries}",
            "--pretty=format:%H%x1f%an%x1f%ae%x1f%ar%x1f%s",
            "--", path,
        ]
        rc, out, _ = _run(args, cwd=root)
        if rc != 0:
            return {"ok": False, "reason": "git_error"}

        entries = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 5:
                entries.append({
                    "hash":    parts[0][:8],
                    "author":  parts[1],
                    "email":   parts[2],
                    "when":    parts[3],
                    "message": parts[4],
                })

        return {"ok": True, "entries": entries}

    def git_branches(self, directory: str) -> dict:
        """Return local branches."""
        root = _find_repo_root(directory)
        if not root:
            return {"ok": False, "reason": "not_a_repo"}

        rc, out, _ = _run(["git", "branch", "--list"], cwd=root)
        if rc != 0:
            return {"ok": False, "reason": "git_error"}

        branches = []
        current  = None
        for line in out.splitlines():
            name = line.strip().lstrip("* ").strip()
            if line.startswith("*"):
                current = name
            if name:
                branches.append(name)

        return {"ok": True, "branches": branches, "current": current}

    def git_is_repo(self, directory: str) -> bool:
        return _find_repo_root(directory) is not None
