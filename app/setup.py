"""
setup.py — Erebus first-launch setup wizard.

Detects installed shells, editors, and terminals on the system, then exposes
that data to the frontend so the user can pick their preferences.
Called by main.py before the main window opens when no config exists.
"""

import os
import shutil
import pwd
from pathlib import Path

CONFIG_DIR  = Path.home() / ".config" / "erebus"
CONFIG_FILE = CONFIG_DIR / "config.toml"
SETUP_FLAG  = CONFIG_DIR / ".setup_complete"


# ── Detection ─────────────────────────────────────────────────────────────────

def _which_any(names: list) -> list:
    return [n for n in names if shutil.which(n)]


def detect_shells() -> list:
    known = ["bash", "zsh", "fish", "dash", "ksh", "tcsh", "nushell", "elvish", "xonsh"]
    found = _which_any(known)
    try:
        with open("/etc/shells") as f:
            for line in f:
                name = os.path.basename(line.strip())
                if name and not name.startswith("#") and name not in found and shutil.which(name):
                    found.append(name)
    except FileNotFoundError:
        pass
    return found


def detect_editors() -> list:
    known = [
        "nvim", "vim", "vi", "nano", "micro", "helix", "hx",
        "emacs", "code", "codium", "subl", "geany", "kate", "gedit",
    ]
    return _which_any(known)


def detect_terminals() -> list:
    known = [
        "kitty", "alacritty", "wezterm", "foot",
        "gnome-terminal", "konsole", "xfce4-terminal",
        "tilix", "terminator", "urxvt", "st", "xterm",
    ]
    return _which_any(known)


def get_current_shell() -> str:
    env = os.environ.get("SHELL", "")
    if env:
        return os.path.basename(env)
    try:
        return os.path.basename(pwd.getpwuid(os.getuid()).pw_shell)
    except Exception:
        return "bash"


# ── Public API ────────────────────────────────────────────────────────────────

def setup_needed() -> bool:
    """True when neither a config file nor the setup-complete flag exists."""
    return not SETUP_FLAG.exists() and not CONFIG_FILE.exists()


def detect_platform() -> dict:
    """Detect OS/distro info for the setup wizard display."""
    import platform as _platform
    info = {"distro": "", "wsl": False, "wsl2": False, "wslg": False}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["distro"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except FileNotFoundError:
        info["distro"] = _platform.system()
    # WSL detection
    try:
        with open("/proc/version") as f:
            v = f.read().lower()
            if "microsoft" in v or "wsl" in v:
                info["wsl"] = True
                info["wsl2"] = "wsl2" in v or "wsl 2" in v
    except FileNotFoundError:
        pass
    if info["wsl"]:
        info["wslg"] = Path("/mnt/wslg").exists()
    return info


def get_setup_data() -> dict:
    """
    Return everything the frontend wizard needs:
    lists of available tools and sensible pre-selections.
    """
    shells    = detect_shells()
    editors   = detect_editors()
    terminals = detect_terminals()
    cur_shell = get_current_shell()

    # Pre-select the user's current shell if we detected it
    sel_shell = cur_shell if cur_shell in shells else (shells[0] if shells else "bash")

    # Prefer serious terminal editors; fall back to whatever's there
    editor_pref = ["nvim", "vim", "micro", "helix", "hx", "nano", "code", "codium"]
    sel_editor  = next((e for e in editor_pref if e in editors), editors[0] if editors else "nano")

    term_pref   = ["kitty", "alacritty", "wezterm", "foot", "gnome-terminal", "konsole"]
    sel_term    = next((t for t in term_pref if t in terminals), terminals[0] if terminals else "")

    warnings = []
    if not shells:
        warnings.append("No supported shells detected. Install bash or zsh.")
    if not editors:
        warnings.append("No text editors detected. Install nano, vim, or nvim.")

    return {
        "shells":            shells,
        "editors":           editors,
        "terminals":         terminals,
        "selected_shell":    sel_shell,
        "selected_editor":   sel_editor,
        "selected_terminal": sel_term,
        "home_dir":          str(Path.home()),
        "platform":          detect_platform(),
        "warnings":          warnings,
    }


def complete_setup(choices: dict) -> dict:
    """
    Write the user's choices to config.toml and mark setup as done.
    Called from the frontend via pywebview JS API.
    Returns {"ok": True} or {"ok": False, "error": "..."}.
    """
    try:
        _write_config(choices)
        SETUP_FLAG.touch()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── Config writer ─────────────────────────────────────────────────────────────

def _write_config(c: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    shell   = c.get("shell", "bash")
    editor  = c.get("editor", "nano")
    term    = c.get("terminal", "")
    path    = c.get("start_path", str(Path.home()))
    theme   = c.get("theme", "dark")

    # Determine if the chosen editor runs in a terminal
    gui_editors = {"code", "codium", "subl", "atom", "geany", "kate", "gedit", "mousepad"}
    editor_in_terminal = editor not in gui_editors

    lines = [
        "# Erebus configuration — generated by first-launch setup",
        "# Edit freely. All keys are optional; missing keys fall back to defaults.",
        "",
        "[shell]",
        f'command = "{shell}"',
        f'provider = "{shell}"',
        "scrollback = 10000",
        "",
        "[editor]",
        f'command = "{editor}"',
        f'provider = "{editor}"',
        f"terminal = {str(editor_in_terminal).lower()}",
        "tab_size = 4",
        "word_wrap = false",
        "line_numbers = true",
        "",
        "[terminal]",
        f'emulator = "{term}"',
        "",
        "[ui]",
        f'start_path = "{path}"',
        f'theme = "{theme}"',
        "",
    ]

    CONFIG_FILE.write_text("\n".join(lines))
