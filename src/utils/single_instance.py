import os
import tempfile
from pathlib import Path
from typing import Optional, Union

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows-only branch
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX-only branch
    msvcrt = None


class SingleInstance:
    """Prevent more than one running instance of the application."""

    def __init__(
        self, app_name: str, lock_dir: Optional[Union[str, os.PathLike]] = None
    ):
        self.app_name = app_name
        base_dir = Path(lock_dir) if lock_dir is not None else Path(tempfile.gettempdir())
        self.lock_path = base_dir / f"{app_name}.lock"
        self._handle = None

    def acquire(self) -> bool:
        """Try to acquire the process lock."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")

        try:
            self._ensure_lock_byte(handle)
            self._lock_handle(handle)
            handle.seek(0)
            handle.truncate()
            handle.write(str(os.getpid()))
            handle.flush()
            self._handle = handle
            return True
        except OSError:
            handle.close()
            return False

    def release(self) -> None:
        """Release the process lock if it is held."""
        if self._handle is None:
            return

        try:
            self._unlock_handle(self._handle)
        finally:
            self._handle.close()
            self._handle = None

    def _ensure_lock_byte(self, handle) -> None:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write("\0")
            handle.flush()
        handle.seek(0)

    def _lock_handle(self, handle) -> None:
        if os.name == "nt":
            if msvcrt is None:  # pragma: no cover - defensive fallback
                raise OSError("msvcrt is unavailable on this platform")
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return

        if fcntl is None:  # pragma: no cover - defensive fallback
            raise OSError("fcntl is unavailable on this platform")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock_handle(self, handle) -> None:
        handle.seek(0)
        if os.name == "nt":
            if msvcrt is not None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def show_already_running_message(app_name: str) -> None:
    """Display a friendly message when a second instance is launched."""
    title = f"{app_name} is already running"
    message = (
        f"Another {app_name} instance is already open.\n\n"
        "Use the existing tray icon or Ctrl+Alt+Q shortcut instead."
    )

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showwarning(title, message)
        root.destroy()
    except Exception:
        print(message, file=os.sys.stderr)
