"""
main.py — Erebus entry point.

Wires together: FsAPI, PtyManager, GitAPI, SearchAPI,
FileWatcher, SetupAPI, and Config into a single pywebview window.
"""

import os
import sys
import threading
import json
import queue

import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config, save_config
from setup         import setup_needed, get_setup_data, complete_setup
from pty_bridge    import PtyManager
from fs_api        import FsAPI
from git_api       import GitAPI
from search_api    import SearchAPI
from file_watcher  import FileWatcher

# ── PTY output queue ──────────────────────────────────────────────────────────
_pty_queue: queue.Queue = queue.Queue()
_js_queue:  queue.Queue = queue.Queue()   # generic JS events → frontend
_window_ref = None


def _pty_output(session_id: str, data: str):
    _pty_queue.put(("pty", session_id, data))


def _file_changed(path: str, content):
    _js_queue.put(("file_changed", path, content))


def _dispatch_loop():
    """Drain both queues and forward to JS."""
    while True:
        # Drain PTY queue (high priority)
        try:
            kind, *args = _pty_queue.get(timeout=0.02)
            if _window_ref:
                sid, data = args
                js = f"if(typeof ptyOutput==='function')ptyOutput({json.dumps(sid)},{json.dumps(data)});"
                try: _window_ref.evaluate_js(js)
                except: pass
        except queue.Empty:
            pass

        # Drain JS event queue
        try:
            kind, *args = _js_queue.get_nowait()
            if _window_ref:
                if kind == "file_changed":
                    path, content = args
                    js = f"if(typeof onFileChanged==='function')onFileChanged({json.dumps(path)},{json.dumps(content)});"
                    try: _window_ref.evaluate_js(js)
                    except: pass
        except queue.Empty:
            pass


# ── Unified JS API ─────────────────────────────────────────────────────────────
class ErebusAPI:
    def __init__(self, pty: PtyManager, fs: FsAPI,
                 git: GitAPI, search: SearchAPI, watcher: FileWatcher):
        self._pty     = pty
        self._fs      = fs
        self._git     = git
        self._search  = search
        self._watcher = watcher

    # ── Setup ─────────────────────────────────────────────────────────────────
    def is_setup_needed(self):        return setup_needed()
    def get_setup_data(self):         return get_setup_data()
    def complete_setup(self, c):      return complete_setup(c)

    # ── Config ────────────────────────────────────────────────────────────────
    def get_config(self):             return load_config()
    def reload_config(self):          return {"ok": True, "config": load_config()}
    def save_config_toml(self, toml_text: str):  return save_config(toml_text)

    # ── PTY ───────────────────────────────────────────────────────────────────
    def pty_new(self, sid, shell, cwd="~", cols=220, rows=50):
        return self._pty.new_session(sid, shell, os.path.expanduser(cwd), cols, rows)
    def pty_exec(self, sid, cmd, args, cwd="~", cols=220, rows=50):
        return self._pty.exec_session(sid, cmd, args, os.path.expanduser(cwd), cols, rows)
    def pty_write(self, sid, data):   return self._pty.write(sid, data)
    def pty_resize(self, sid, c, r):  return self._pty.resize(sid, c, r)
    def pty_kill(self, sid):          return self._pty.kill_session(sid)
    def pty_list(self):               return self._pty.list_sessions()

    # ── Filesystem ────────────────────────────────────────────────────────────
    def fs_list(self, p):             return self._fs.list_dir(p)
    def fs_stat(self, p):             return self._fs.stat_path(p)
    def fs_read(self, p):             return self._fs.read_file(p)
    def fs_write(self, p, c):         return self._fs.write_file(p, c)
    def fs_create_file(self, p):      return self._fs.create_file(p)
    def fs_create_dir(self, p):       return self._fs.create_dir(p)
    def fs_rename(self, o, n):        return self._fs.rename(o, n)
    def fs_delete(self, p):           return self._fs.delete(p)
    def fs_copy(self, s, d):          return self._fs.copy(s, d)
    def fs_home(self):                return self._fs.home_dir()
    def fs_drives(self):              return self._fs.get_drives()
    def fs_resolve(self, p):          return self._fs.resolve_path(p)
    def fs_xdg_open(self, p):         return self._fs.xdg_open(p)

    # ── File watcher ──────────────────────────────────────────────────────────
    def watch_file(self, path: str):  self._watcher.watch(path); return {"ok": True}
    def unwatch_file(self, path: str):self._watcher.unwatch(path); return {"ok": True}

    # ── Git ───────────────────────────────────────────────────────────────────
    def git_status(self, d):          return self._git.git_status(d)
    def git_diff(self, p):            return self._git.git_diff(p)
    def git_log(self, p, n=20):       return self._git.git_log(p, n)
    def git_branches(self, d):        return self._git.git_branches(d)
    def git_is_repo(self, d):         return self._git.git_is_repo(d)

    # ── Search ────────────────────────────────────────────────────────────────
    def search_files(self, q, d, cs=False, rx=False, hidden=False):
        return self._search.search_files(q, d, cs, rx, hidden)
    def search_has_rg(self):          return self._search.search_has_rg()


# ── Window callback ────────────────────────────────────────────────────────────
def on_loaded(window, config, first_run):
    global _window_ref
    _window_ref = window

    t  = config["theme"]
    l  = config["layout"]
    cj = json.dumps(config)

    js = f"""
(function(){{
  const r=document.documentElement.style;
  r.setProperty('--font',            '{t["font_family"]}, monospace');
  r.setProperty('--font-size',       '{t["font_size"]}px');
  r.setProperty('--bg',              '{t["background"]}');
  r.setProperty('--surface',         '{t["surface"]}');
  r.setProperty('--surface-2',       '{t["surface_2"]}');
  r.setProperty('--border',          '{t["border"]}');
  r.setProperty('--accent',          '{t["accent"]}');
  r.setProperty('--accent-dim',      '{t["accent_dim"]}');
  r.setProperty('--text',            '{t["text"]}');
  r.setProperty('--text-muted',      '{t["text_muted"]}');
  r.setProperty('--text-dim',        '{t["text_dim"]}');
  r.setProperty('--radius',          '{"6px" if t["rounded_corners"] else "0px"}');
  r.setProperty('--explorer-width',  '{l["explorer_width"]}%');
  r.setProperty('--terminal-height', '{l["terminal_height"]}%');
  window.EREBUS_CONFIG={cj};
  if(typeof onErebusReady==='function') onErebusReady(window.EREBUS_CONFIG,{str(first_run).lower()});
}})();
"""
    window.evaluate_js(js)


def main():
    config    = load_config()
    first_run = setup_needed()

    pty     = PtyManager()
    fs      = FsAPI()
    git     = GitAPI()
    search  = SearchAPI()
    watcher = FileWatcher(_file_changed)
    api     = ErebusAPI(pty, fs, git, search, watcher)

    pty.set_output_callback(_pty_output)

    disp = threading.Thread(target=_dispatch_loop, daemon=True)
    disp.start()

    ui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

    window = webview.create_window(
        title="Erebus", url=ui, js_api=api,
        width=1280, height=800, min_size=(800, 500),
        background_color=config["theme"]["background"],
        frameless=False, easy_drag=False,
        text_select=True,
    )

    window.events.loaded += lambda: on_loaded(window, config, first_run)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
