"""
file_watcher.py — Erebus file change watcher.

Polls open editor files for mtime changes (no watchdog dependency needed).
When a file changes externally, calls on_change(path, new_content).

Uses a single background thread scanning all watched paths every second.
Thread-safe: watch/unwatch can be called from any thread.
"""

import os
import threading
import time
from pathlib import Path


class FileWatcher:
    def __init__(self, on_change):
        """
        on_change(path: str, new_content: str | None)
          path        — absolute path that changed
          new_content — new file content, or None if file was deleted
        """
        self._on_change  = on_change
        self._watched    = {}   # path -> last mtime
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()
        self._thread     = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def watch(self, path: str):
        """Start watching a file path."""
        p = Path(path)
        try:
            mtime = p.stat().st_mtime
        except OSError:
            mtime = 0
        with self._lock:
            self._watched[path] = mtime

    def unwatch(self, path: str):
        """Stop watching a file path."""
        with self._lock:
            self._watched.pop(path, None)

    def unwatch_all(self):
        with self._lock:
            self._watched.clear()

    def stop(self):
        self._stop_event.set()

    def _loop(self):
        while not self._stop_event.is_set():
            time.sleep(1.0)
            with self._lock:
                snapshot = dict(self._watched)

            for path, last_mtime in snapshot.items():
                p = Path(path)
                try:
                    mtime = p.stat().st_mtime
                except OSError:
                    # File was deleted
                    with self._lock:
                        self._watched.pop(path, None)
                    self._on_change(path, None)
                    continue

                if mtime != last_mtime:
                    with self._lock:
                        self._watched[path] = mtime
                    # Read new content
                    try:
                        content = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        try:
                            content = p.read_text(encoding="latin-1")
                        except Exception:
                            content = None
                    except Exception:
                        content = None
                    self._on_change(path, content)
