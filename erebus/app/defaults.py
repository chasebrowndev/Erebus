"""
defaults.py — Erebus default configuration values.

Every value here maps 1:1 to a future ~/.config/erebus/config.toml key.
When TOML loading is implemented, this module becomes the fallback layer:
  resolved_value = toml_config.get(key) or DEFAULTS[key]

Do NOT scatter magic values throughout the codebase.
If it's configurable, it lives here first.
"""

DEFAULTS = {

    # ── Layout ────────────────────────────────────────────────────────────────
    "layout": {
        "explorer_width": 22,           # % of total window width
        "terminal_height": 32,          # % of total window height
        "terminal_position": "bottom",  # "bottom" | "right" (future)
        "show_explorer": True,
        "show_terminal": True,
        "show_editor": True,
    },

    # ── Theme ─────────────────────────────────────────────────────────────────
    "theme": {
        "preset": "erebus-default",
        "font_family": "JetBrains Mono",
        "font_size": 13,                # px
        "background": "#0a0a0a",
        "surface": "#111111",
        "surface_2": "#181818",
        "border": "#222222",
        "accent": "#ff2a2a",
        "accent_dim": "#8b0000",
        "text": "#e0e0e0",
        "text_muted": "#555555",
        "text_dim": "#333333",
        "rounded_corners": False,
        "opacity": 1.0,
    },

    # ── Shell ─────────────────────────────────────────────────────────────────
    "shell": {
        "provider": "zsh",             # zsh | bash | fish | nushell | powershell
        "scrollback": 10000,
    },

    # ── Editor ────────────────────────────────────────────────────────────────
    "editor": {
        "provider": "builtin",         # builtin | micro | neovim
        "tab_size": 4,
        "word_wrap": False,
        "line_numbers": True,
    },

    # ── Keybinds ──────────────────────────────────────────────────────────────
    "keybinds": {
        "focus_explorer": "Ctrl+E",
        "focus_terminal": "Ctrl+T",
        "focus_editor": "Ctrl+Shift+E",
        "command_palette": "Ctrl+P",
        "new_tab": "Ctrl+N",
        "close_tab": "Ctrl+W",
    },

}
