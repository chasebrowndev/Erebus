"""
main.py — Erebus entry point.

Launches the pywebview window and injects the resolved config into the
frontend via webview.evaluate_js() once the page loads.

On first launch (no config + no .setup_complete flag), the setup wizard
overlay is shown instead of the normal workspace.
"""

import os
import sys
import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from setup import setup_needed, get_setup_data, complete_setup


def get_ui_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "index.html")


# ── pywebview JS API ──────────────────────────────────────────────────────────

class ErebusAPI:
    """
    Methods on this class are callable from JS via window.pywebview.api.*
    They run on a background thread — keep them fast and thread-safe.
    """

    def get_setup_data(self):
        """Return detected shells/editors/terminals as a JSON-serialisable dict."""
        return get_setup_data()

    def complete_setup(self, choices):
        """
        Persist the user's first-launch choices.
        `choices` is passed through from JS as a dict.
        Returns {"ok": True} or {"ok": False, "error": "..."}.
        """
        return complete_setup(choices)

    def is_setup_needed(self):
        return setup_needed()


# ── Window callbacks ──────────────────────────────────────────────────────────

def on_loaded(window, config, first_run: bool):
    """
    Runs after the page finishes loading.
    1. Injects CSS variables and CONFIG values from the resolved config.
    2. If it's a first run, tells the frontend to show the setup wizard.
    """
    theme  = config["theme"]
    layout = config["layout"]
    shell  = config["shell"]
    editor = config["editor"]

    js = f"""
    (function() {{
        const r = document.documentElement.style;
        r.setProperty('--font',            '{theme["font_family"]}, monospace');
        r.setProperty('--font-size',       '{theme["font_size"]}px');
        r.setProperty('--bg',              '{theme["background"]}');
        r.setProperty('--surface',         '{theme["surface"]}');
        r.setProperty('--surface-2',       '{theme["surface_2"]}');
        r.setProperty('--border',          '{theme["border"]}');
        r.setProperty('--accent',          '{theme["accent"]}');
        r.setProperty('--accent-dim',      '{theme["accent_dim"]}');
        r.setProperty('--text',            '{theme["text"]}');
        r.setProperty('--text-muted',      '{theme["text_muted"]}');
        r.setProperty('--text-dim',        '{theme["text_dim"]}');
        r.setProperty('--radius',          '{"6px" if theme["rounded_corners"] else "0px"}');
        r.setProperty('--explorer-width',  '{layout["explorer_width"]}%');
        r.setProperty('--terminal-height', '{layout["terminal_height"]}%');

        CONFIG.explorerWidth  = {layout["explorer_width"]};
        CONFIG.terminalHeight = {layout["terminal_height"]};
        CONFIG.showExplorer   = {"true" if layout["show_explorer"] else "false"};
        CONFIG.showTerminal   = {"true" if layout["show_terminal"] else "false"};

        const sbShell  = document.querySelector('#statusbar-left .sb-item:nth-child(2)');
        const sbEditor = document.querySelector('#statusbar-left .sb-item:nth-child(3)');
        if (sbShell)  sbShell.textContent  = '{shell["provider"].upper()}';
        if (sbEditor) sbEditor.textContent = '{editor["provider"].upper()} EDITOR';

        console.log('[erebus] Config injected.');

        if ({str(first_run).lower()}) {{
            if (typeof showSetupWizard === 'function') showSetupWizard();
        }}
    }})();
    """
    window.evaluate_js(js)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    config    = load_config()
    theme     = config["theme"]
    first_run = setup_needed()

    api    = ErebusAPI()
    window = webview.create_window(
        title="Erebus",
        url=get_ui_path(),
        js_api=api,
        width=1280,
        height=800,
        min_size=(800, 500),
        background_color=theme["background"],
        frameless=False,
        easy_drag=False,
    )

    window.events.loaded += lambda: on_loaded(window, config, first_run)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
