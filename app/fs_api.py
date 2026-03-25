"""
fs_api.py — Erebus filesystem API.

All methods are called from JS via window.pywebview.api.*
They run on a pywebview background thread — keep them fast.

Every method returns a plain dict so pywebview can serialise it to JS.
"""

import os
import stat
import shutil
import mimetypes
import threading
from pathlib import Path
from datetime import datetime


# File types we'll open in the built-in editor (by extension)
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss",
    ".json", ".toml", ".yaml", ".yml", ".xml", ".md", ".txt", ".sh", ".bash",
    ".zsh", ".fish", ".conf", ".cfg", ".ini", ".env", ".gitignore",
    ".dockerfile", ".makefile", ".c", ".cpp", ".h", ".hpp", ".rs", ".go",
    ".rb", ".lua", ".vim", ".sql", ".csv", ".log", ".diff", ".patch",
    "", # no extension — try as text
}

MAX_EDITOR_BYTES = 2 * 1024 * 1024  # 2 MB — anything bigger, refuse to load


def _entry_info(path: Path) -> dict:
    """Build a serialisable dict for a single filesystem entry.

    Uses stat() with a fallback to lstat() so broken symlinks
    (e.g. ~/.steampath -> deleted target) are shown as entries
    rather than crashing the whole directory listing.
    """
    is_link = path.is_symlink()

    try:
        st = path.stat()          # follows symlinks; raises on broken link
        broken = False
    except (FileNotFoundError, OSError):
        if is_link:
            # Broken symlink — use lstat so we can still show the entry
            try:
                st = path.lstat()
                broken = True
            except OSError:
                return {
                    "name": path.name, "path": str(path),
                    "type": "file", "symlink": True, "broken": True,
                    "ext": path.suffix.lower(), "size": 0, "modified": "",
                    "readable": False, "editable": False,
                }
        else:
            return {
                "name": path.name, "path": str(path),
                "type": "unknown", "symlink": False, "broken": False,
                "ext": path.suffix.lower(), "size": 0, "modified": "",
                "readable": False, "editable": False,
            }
    except PermissionError:
        return {
            "name": path.name, "path": str(path),
            "type": "unknown", "symlink": is_link, "broken": False,
            "ext": path.suffix.lower(), "size": 0, "modified": "",
            "readable": False, "editable": False,
        }

    is_dir = stat.S_ISDIR(st.st_mode)
    ext    = path.suffix.lower()

    return {
        "name":     path.name,
        "path":     str(path),
        "type":     "dir" if is_dir else "file",
        "symlink":  is_link,
        "broken":   broken,
        "ext":      ext,
        "size":     st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "readable": True,
        "editable": (not is_dir) and (not broken) and (ext in TEXT_EXTENSIONS),
    }


class FsAPI:

    # ── Directory listing ─────────────────────────────────────────────────────

    def list_dir(self, path: str) -> dict:
        """
        Returns sorted directory contents.
        Dirs first, then files, both alphabetically case-insensitive.
        Hidden entries (dot-files) are included but flagged.
        Broken symlinks are included as non-navigable entries.
        """
        p = Path(os.path.expanduser(path)).resolve()
        if not p.exists():
            return {"ok": False, "error": f"Path does not exist: {p}"}
        if not p.is_dir():
            return {"ok": False, "error": f"Not a directory: {p}"}

        entries = []
        try:
            for child in p.iterdir():
                info = _entry_info(child)
                info["hidden"] = child.name.startswith(".")
                entries.append(info)
        except PermissionError as e:
            return {"ok": False, "error": str(e)}

        entries.sort(key=lambda e: (
            0 if e["type"] == "dir" else 1,
            e["name"].lower()
        ))

        return {
            "ok":      True,
            "path":    str(p),
            "parent":  str(p.parent) if p.parent != p else None,
            "entries": entries,
        }

    def stat_path(self, path: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        if not p.exists():
            return {"ok": False, "error": "Not found"}
        info = _entry_info(p)
        info["ok"] = True
        info["abs_path"] = str(p)
        return info

    # ── File read / write ─────────────────────────────────────────────────────

    def read_file(self, path: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        if not p.exists():
            return {"ok": False, "error": "File not found"}
        if p.is_dir():
            return {"ok": False, "error": "Path is a directory"}
        if p.stat().st_size > MAX_EDITOR_BYTES:
            return {"ok": False, "error": "File too large to open in editor (> 2 MB)"}

        # Try UTF-8 first, fall back to latin-1
        for enc in ("utf-8", "latin-1"):
            try:
                content = p.read_text(encoding=enc)
                return {
                    "ok":      True,
                    "path":    str(p),
                    "name":    p.name,
                    "ext":     p.suffix.lower(),
                    "content": content,
                    "encoding": enc,
                    "size":    p.stat().st_size,
                }
            except UnicodeDecodeError:
                continue

        return {"ok": False, "error": "Binary file — cannot open in editor"}

    def write_file(self, path: str, content: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"ok": True, "path": str(p), "size": p.stat().st_size}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── File / directory operations ───────────────────────────────────────────

    def create_file(self, path: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        if p.exists():
            return {"ok": False, "error": "Already exists"}
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return {"ok": True, "path": str(p)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_dir(self, path: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return {"ok": True, "path": str(p)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rename(self, old_path: str, new_path: str) -> dict:
        src = Path(os.path.expanduser(old_path)).resolve()
        dst = Path(os.path.expanduser(new_path)).resolve()
        if not src.exists():
            return {"ok": False, "error": "Source not found"}
        if dst.exists():
            return {"ok": False, "error": "Destination already exists"}
        try:
            src.rename(dst)
            return {"ok": True, "new_path": str(dst)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete(self, path: str) -> dict:
        p = Path(os.path.expanduser(path)).resolve()
        if not p.exists():
            return {"ok": False, "error": "Not found"}
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def copy(self, src_path: str, dst_path: str) -> dict:
        src = Path(os.path.expanduser(src_path)).resolve()
        dst = Path(os.path.expanduser(dst_path)).resolve()
        if not src.exists():
            return {"ok": False, "error": "Source not found"}
        try:
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return {"ok": True, "dst": str(dst)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Utility ───────────────────────────────────────────────────────────────

    def home_dir(self) -> str:
        return str(Path.home())

    def resolve_path(self, path: str) -> dict:
        try:
            p = Path(os.path.expanduser(path)).resolve()
            return {"ok": True, "path": str(p), "exists": p.exists()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def path_exists(self, path: str) -> bool:
        return Path(os.path.expanduser(path)).exists()

    def get_drives(self) -> list:
        """Returns root + home as quick-access roots."""
        return [
            {"label": "Root",  "path": "/"},
            {"label": "Home",  "path": str(Path.home())},
        ]
