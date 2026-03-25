"""
main.py — Erebus entry point.

Launches the pywebview window and wires together:
  - FsAPI      (filesystem operations)
  - PtyManager (real PTY shell sessions)
  - SetupAPI   (first-launch wizard)
  - Config     (TOML loader + defaults)

PTY output is forwarded to the frontend via window.evaluate_js().
All other operations go through the pywebview JS API (window.pywebview.api.*).
"""

import os
import sys
import threading
import json
import queue

import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from setup         import setup_needed, get_setup_data, complete_setup
from pty_bridge    import PtyManager
from fs_api        import FsAPI


# ── PTY output forwarding ─────────────────────────────────────────────────────
_pty_queue: queue.Queue = queue.Queue()
_window_ref = None


def _pty_output(session_id: str, data: str):
    """Called from PtySession read threads. Enqueues for JS dispatch."""
    _pty_queue.put((session_id, data))


def _pty_dispatcher():
    """Drains the PTY output queue and forwards data to JS."""
    while True:
        try:
            session_id, data = _pty_queue.get(timeout=0.05)
        except queue.Empty:
            continue
        if _window_ref is None:
            continue
        safe = json.dumps(data)
        sid  = json.dumps(session_id)
        js   = f"if(typeof ptyOutput==='function')ptyOutput({sid},{safe});"
        try:
            _window_ref.evaluate_js(js)
        except Exception:
            pass


# ── Unified JS API ─────────────────────────────────────────────────────────────

class ErebusAPI:
    def __init__(self, pty_manager: PtyManager, fs: FsAPI):
        self._pty = pty_manager
        self._fs  = fs

    # Setup
    def is_setup_needed(self):
        return setup_needed()

    def get_setup_data(self):
        return get_setup_data()

    def complete_setup(self, choices):
        return complete_setup(choices)

    # PTY
    def pty_new(self, session_id, shell, cwd="~", cols=220, rows=50):
        return self._pty.new_session(session_id, shell, os.path.expanduser(cwd), cols, rows)

    def pty_write(self, session_id, data):
        return self._pty.write(session_id, data)

    def pty_resize(self, session_id, cols, rows):
        return self._pty.resize(session_id, cols, rows)

    def pty_kill(self, session_id):
        return self._pty.kill_session(session_id)

    def pty_list(self):
        return self._pty.list_sessions()

    # Filesystem
    def fs_list(self, path):          return self._fs.list_dir(path)
    def fs_stat(self, path):          return self._fs.stat_path(path)
    def fs_read(self, path):          return self._fs.read_file(path)
    def fs_write(self, path, content):return self._fs.write_file(path, content)
    def fs_create_file(self, path):   return self._fs.create_file(path)
    def fs_create_dir(self, path):    return self._fs.create_dir(path)
    def fs_rename(self, old, new):    return self._fs.rename(old, new)
    def fs_delete(self, path):        return self._fs.delete(path)
    def fs_copy(self, src, dst):      return self._fs.copy(src, dst)
    def fs_home(self):                return self._fs.home_dir()
    def fs_drives(self):              return self._fs.get_drives()
    def fs_resolve(self, path):       return self._fs.resolve_path(path)
    def fs_xdg_open(self, path):      return self._fs.xdg_open(path)

    # Config
    def get_config(self):
        return load_config()

    def reload_config(self):
        return {"ok": True, "config": load_config()}


# ── Window callbacks ───────────────────────────────────────────────────────────

def on_loaded(window, config, first_run):
    global _window_ref
    _window_ref = window

    theme  = config["theme"]
    layout = config["layout"]
    config_json = json.dumps(config)

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
    window.EREBUS_CONFIG = {config_json};
    if (typeof onErebusReady === 'function') {{
        onErebusReady(window.EREBUS_CONFIG, {str(first_run).lower()});
    }}
}})();
"""
    window.evaluate_js(js)


def main():
    config    = load_config()
    theme     = config["theme"]
    first_run = setup_needed()

    pty_manager = PtyManager()
    fs          = FsAPI()
    api         = ErebusAPI(pty_manager, fs)

    pty_manager.set_output_callback(_pty_output)

    disp = threading.Thread(target=_pty_dispatcher, daemon=True)
    disp.start()

    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

    window = webview.create_window(
        title="Erebus",
        url=ui_path,
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
