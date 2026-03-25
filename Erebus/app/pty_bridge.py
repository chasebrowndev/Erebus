"""
pty_bridge.py — Erebus pseudoterminal bridge.

Spawns a real shell process inside a PTY and streams its output to the
frontend via a registered callback. Input from the frontend is written
directly into the PTY's master fd.

Each PtySession is independent — multiple terminal tabs each get their own.
"""

import os
import pty
import fcntl
import termios
import struct
import threading
import signal


class PtySession:
    def __init__(self, shell: str, cwd: str, on_output, on_exit):
        """
        shell     — full path or name of shell binary (e.g. "bash", "zsh")
        cwd       — starting working directory
        on_output — callable(session_id, data: str) fired on shell output
        on_exit   — callable(session_id) fired when shell exits
        """
        self.shell     = shell
        self.cwd       = cwd
        self.on_output = on_output
        self.on_exit   = on_exit
        self.pid       = None
        self.master_fd = None
        self._alive    = False
        self._thread   = None

    def start(self, session_id: str, cols: int = 220, rows: int = 50):
        self.session_id = session_id

        # Fork a child process connected to a PTY
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # ── Child ──────────────────────────────────────────────────────
            os.chdir(os.path.expanduser(self.cwd))
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            os.execvpe(self.shell, [self.shell, "--login"], env)
            os._exit(1)

        # ── Parent ─────────────────────────────────────────────────────────
        self._alive = True
        self._set_winsize(cols, rows)

        # Read loop in a background thread
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def write(self, data: str):
        """Send keystrokes / text into the shell."""
        if self.master_fd and self._alive:
            try:
                os.write(self.master_fd, data.encode("utf-8", errors="replace"))
            except OSError:
                pass

    def resize(self, cols: int, rows: int):
        if self.master_fd and self._alive:
            self._set_winsize(cols, rows)

    def kill(self):
        self._alive = False
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _set_winsize(self, cols: int, rows: int):
        packed = struct.pack("HHHH", rows, cols, 0, 0)
        try:
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, packed)
        except OSError:
            pass

    def _read_loop(self):
        import select as sel
        while self._alive:
            try:
                r, _, _ = sel.select([self.master_fd], [], [], 0.05)
                if r:
                    data = os.read(self.master_fd, 4096)
                    if data:
                        self.on_output(
                            self.session_id,
                            data.decode("utf-8", errors="replace")
                        )
                    else:
                        break
            except OSError:
                break

        self._alive = False
        # Reap child
        if self.pid:
            try:
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass
        self.on_exit(self.session_id)


class PtyManager:
    """
    Manages a collection of named PTY sessions.
    Thread-safe: JS calls arrive on a background thread.
    """

    def __init__(self):
        self._sessions: dict[str, PtySession] = {}
        self._lock = threading.Lock()
        self._output_cb = None  # set by main.py after window is created

    def set_output_callback(self, cb):
        """cb(session_id, data) — called from read threads, forwards to JS."""
        self._output_cb = cb

    def new_session(self, session_id: str, shell: str, cwd: str,
                    cols: int = 220, rows: int = 50) -> dict:
        def on_output(sid, data):
            if self._output_cb:
                self._output_cb(sid, data)

        def on_exit(sid):
            with self._lock:
                self._sessions.pop(sid, None)
            if self._output_cb:
                # sentinel so frontend knows the session died
                self._output_cb(sid, "\r\n[Process exited]\r\n")

        session = PtySession(shell, cwd, on_output, on_exit)
        with self._lock:
            # Kill any existing session with this id
            old = self._sessions.pop(session_id, None)
            if old:
                old.kill()
            self._sessions[session_id] = session

        session.start(session_id, cols, rows)
        return {"ok": True}

    def write(self, session_id: str, data: str) -> dict:
        with self._lock:
            s = self._sessions.get(session_id)
        if s:
            s.write(data)
            return {"ok": True}
        return {"ok": False, "error": "session not found"}

    def resize(self, session_id: str, cols: int, rows: int) -> dict:
        with self._lock:
            s = self._sessions.get(session_id)
        if s:
            s.resize(cols, rows)
            return {"ok": True}
        return {"ok": False}

    def kill_session(self, session_id: str) -> dict:
        with self._lock:
            s = self._sessions.pop(session_id, None)
        if s:
            s.kill()
        return {"ok": True}

    def list_sessions(self) -> list:
        with self._lock:
            return list(self._sessions.keys())
