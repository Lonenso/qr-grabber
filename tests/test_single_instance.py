import os
from unittest.mock import MagicMock, patch

from src.utils.single_instance import SingleInstance, show_already_running_message


def test_acquire_and_release_lock(tmp_path):
    lock = SingleInstance("qr_grabber_test", lock_dir=tmp_path)

    assert lock.acquire() is True
    assert lock.lock_path.exists()
    lock._handle.seek(0)
    assert lock._handle.read() == str(os.getpid())

    lock.release()

    assert lock._handle is None


def test_second_instance_is_blocked_until_release(tmp_path):
    first_lock = SingleInstance("qr_grabber_test", lock_dir=tmp_path)
    second_lock = SingleInstance("qr_grabber_test", lock_dir=tmp_path)

    assert first_lock.acquire() is True
    assert second_lock.acquire() is False

    first_lock.release()

    assert second_lock.acquire() is True

    second_lock.release()


def test_release_without_acquire_is_safe(tmp_path):
    lock = SingleInstance("qr_grabber_test", lock_dir=tmp_path)

    lock.release()

    assert lock._handle is None


@patch("tkinter.messagebox.showwarning")
@patch("tkinter.Tk")
def test_show_already_running_message(mock_tk, mock_showwarning):
    root = MagicMock()
    mock_tk.return_value = root

    show_already_running_message("QR Grabber")

    mock_tk.assert_called_once()
    root.withdraw.assert_called_once()
    root.attributes.assert_called_once_with("-topmost", True)
    root.destroy.assert_called_once()
    mock_showwarning.assert_called_once_with(
        "QR Grabber is already running",
        "Another QR Grabber instance is already open.\n\n"
        "Use the existing tray icon or Ctrl+Alt+Q shortcut instead.",
    )
