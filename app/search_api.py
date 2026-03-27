"""
search_api.py — Erebus find-in-files search backend.

Uses ripgrep (rg) when available — fast, respects .gitignore.
Falls back to a pure-Python recursive grep when rg is not installed.

Called from JS via window.pywebview.api.search_*
"""

import os
import re
import subprocess
import shutil
from pathlib import Path


MAX_RESULTS   = 500   # cap total matches to avoid flooding the UI
MAX_FILE_SIZE = 1 * 1024 * 1024  # skip files > 1 MB in Python fallback

TEXT_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss",
    ".json", ".toml", ".yaml", ".yml", ".xml", ".md", ".txt", ".sh", ".bash",
    ".zsh", ".fish", ".conf", ".cfg", ".ini", ".env", ".c", ".cpp", ".h",
    ".hpp", ".rs", ".go", ".rb", ".lua", ".vim", ".sql", ".log", ".diff",
    ".gitignore", ".patch",
}


def _has_rg() -> bool:
    return shutil.which("rg") is not None


def _search_rg(query: str, directory: str,
               case_sensitive: bool, regex: bool,
               include_hidden: bool) -> dict:
    args = [
        "rg",
        "--line-number",
        "--column",
        "--no-heading",
        "--color=never",
        f"--max-count={MAX_RESULTS}",
        "--max-filesize=1M",
    ]
    if not case_sensitive:
        args.append("--ignore-case")
    if not regex:
        args.append("--fixed-strings")
    if include_hidden:
        args.append("--hidden")

    args += ["--", query, directory]

    try:
        result = subprocess.run(
            args,
            capture_output=True, text=True, timeout=15,
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Search timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    matches = []
    for line in result.stdout.splitlines():
        # format: filepath:line:col:text
        parts = line.split(":", 3)
        if len(parts) >= 4:
            matches.append({
                "file":   parts[0],
                "line":   int(parts[1]),
                "col":    int(parts[2]),
                "text":   parts[3],
            })
        if len(matches) >= MAX_RESULTS:
            break

    return {
        "ok":      True,
        "matches": matches,
        "count":   len(matches),
        "engine":  "ripgrep",
        "truncated": len(matches) >= MAX_RESULTS,
    }


def _search_python(query: str, directory: str,
                   case_sensitive: bool, regex: bool,
                   include_hidden: bool) -> dict:
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query if regex else re.escape(query), flags)
    except re.error as e:
        return {"ok": False, "error": f"Invalid regex: {e}"}

    root = Path(directory)
    matches = []

    def _walk(p: Path):
        try:
            for child in sorted(p.iterdir()):
                if not include_hidden and child.name.startswith("."):
                    continue
                if child.is_symlink():
                    continue
                if child.is_dir():
                    _walk(child)
                elif child.is_file():
                    if child.suffix.lower() not in TEXT_EXTS:
                        continue
                    try:
                        size = child.stat().st_size
                    except OSError:
                        continue
                    if size > MAX_FILE_SIZE:
                        continue
                    _search_file(child)
                if len(matches) >= MAX_RESULTS:
                    return
        except PermissionError:
            pass

    def _search_file(p: Path):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return
        for i, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m:
                matches.append({
                    "file": str(p),
                    "line": i,
                    "col":  m.start() + 1,
                    "text": line,
                })
            if len(matches) >= MAX_RESULTS:
                return

    _walk(root)

    return {
        "ok":      True,
        "matches": matches,
        "count":   len(matches),
        "engine":  "python",
        "truncated": len(matches) >= MAX_RESULTS,
    }


class SearchAPI:

    def search_files(self, query: str, directory: str,
                     case_sensitive: bool = False,
                     regex: bool = False,
                     include_hidden: bool = False) -> dict:
        """
        Search for `query` in all text files under `directory`.
        Returns list of {file, line, col, text} matches.
        """
        if not query:
            return {"ok": True, "matches": [], "count": 0}

        d = str(Path(os.path.expanduser(directory)).resolve())
        if not os.path.isdir(d):
            return {"ok": False, "error": "Directory not found"}

        if _has_rg():
            return _search_rg(query, d, case_sensitive, regex, include_hidden)
        else:
            return _search_python(query, d, case_sensitive, regex, include_hidden)

    def search_has_rg(self) -> bool:
        return _has_rg()
