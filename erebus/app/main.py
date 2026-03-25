"""
main.py — Erebus entry point.

Launches the pywebview window and injects the resolved config
into the frontend via webview.evaluate_js() once the page loads.
"""

import os
import webview

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config


def get_ui_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "index.html")


def on_loaded(window, config):
    """
    Called after the webview page finishes loading.
    Injects the resolved config into the JS CONFIG object and CSS variables.
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
    }})();
    """
    window.evaluate_js(js)


def main():
    config = load_config()
    theme  = config["theme"]

    window = webview.create_window(
        title="Erebus",
        url=get_ui_path(),
        width=1280,
        height=800,
        min_size=(800, 500),
        background_color=theme["background"],
        frameless=False,
        easy_drag=False,
    )

    window.events.loaded += lambda: on_loaded(window, config)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
