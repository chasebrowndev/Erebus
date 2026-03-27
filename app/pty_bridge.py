"""
pty_bridge.py — Erebus pseudoterminal bridge.

Spawns a real shell process inside a PTY and streams its output to the
frontend via a registered callback. Input from the frontend is written
directly into the PTY's master fd.

Each PtySession is independent — multiple terminal tabs each get their own.

Two session modes:
  new_session  — spawns a login shell (for terminal tabs)
  exec_session — execs an arbitrary command directly with no shell wrapper
                 (for external editor tabs — no prompt, no echo, no RC noise)
"""

import os
import pty
import fcntl
import termios
import struct
import threading
import signal
import shutil


class PtySession:
    def __init__(self, argv: list, cwd: str, env: dict, on_output, on_exit):
        """
        argv      — command + args to exec, e.g. ["nvim", "/path/to/file"]
        cwd       — starting working directory
        env       — environment dict for the child process
        on_output — callable(session_id, data: str) fired on output
        on_exit   — callable(session_id) fired when process exits
        """
        self.argv      = argv
        self.cwd       = cwd
        self.env       = env
        self.on_output = on_output
        self.on_exit   = on_exit
        self.pid       = None
        self.master_fd = None
        self._alive    = False
        self._thread   = None

    def start(self, session_id: str, cols: int = 220, rows: int = 50):
        self.session_id = session_id

        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # ── Child ──────────────────────────────────────────────────────
            try:
                os.chdir(os.path.expanduser(self.cwd))
            except OSError:
                pass
            os.execvpe(self.argv[0], self.argv, self.env)
            os._exit(1)

        # ── Parent ─────────────────────────────────────────────────────────
        self._alive = True
        self._set_winsize(cols, rows)

        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def write(self, data: str):
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
        self._output_cb = None

    def set_output_callback(self, cb):
        self._output_cb = cb

    # ── Shell session (terminal tabs) ─────────────────────────────────────────

    def new_session(self, session_id: str, shell: str, cwd: str,
                    cols: int = 220, rows: int = 50) -> dict:
        """Spawn a login shell. Used for terminal panel tabs."""
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        shell_name = os.path.basename(shell)
        login_shells = {"bash", "zsh", "sh", "dash", "ksh", "mksh", "rbash"}
        argv = [shell, "--login"] if shell_name in login_shells else [shell]

        return self._start(session_id, argv, cwd, env, cols, rows,
                           exit_sentinel="\r\n[Process exited]\r\n")

    # ── Direct exec session (external editor tabs) ────────────────────────────

    def exec_session(self, session_id: str, cmd: str, args: list,
                     cwd: str, cols: int = 220, rows: int = 50) -> dict:
        """
        Exec an arbitrary command directly in a PTY — no shell wrapper.
        The process starts immediately with no prompt, no echo, no RC noise.
        Used for external editor tabs (nvim, micro, helix, etc.).
        """
        # Resolve the binary so we can give a clear error if not found
        binary = shutil.which(cmd) or cmd
        argv   = [binary] + (args or [])

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        # Prevent editors from inheriting Erebus-specific env noise
        env.pop("PROMPT_COMMAND", None)

        return self._start(session_id, argv, cwd, env, cols, rows,
                           exit_sentinel=None)   # no sentinel — JS handles close

    # ── Shared internals ──────────────────────────────────────────────────────

    def _start(self, session_id: str, argv: list, cwd: str, env: dict,
               cols: int, rows: int, exit_sentinel) -> dict:
        def on_output(sid, data):
            if self._output_cb:
                self._output_cb(sid, data)

        def on_exit(sid):
            with self._lock:
                self._sessions.pop(sid, None)
            if self._output_cb and exit_sentinel:
                self._output_cb(sid, exit_sentinel)

        session = PtySession(argv, cwd, env, on_output, on_exit)
        with self._lock:
            old = self._sessions.pop(session_id, None)
            if old:
                old.kill()
            self._sessions[session_id] = session

        try:
            session.start(session_id, cols, rows)
        except Exception as e:
            with self._lock:
                self._sessions.pop(session_id, None)
            return {"ok": False, "error": str(e)}

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
