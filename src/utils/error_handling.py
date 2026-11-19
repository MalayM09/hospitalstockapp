"""
Logging and crash handling.

The packaged .exe has no console, so without this an unexpected error simply
closes the app with no message. Here every unhandled exception is:
  1. written to logs/app.log (rotating, kept small), and
  2. shown to the user in a dialog, while the app keeps running.
"""
import logging
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

from utils.db_path import get_log_dir

_dialog_open = False


def setup_logging():
    log_file = get_log_dir() / "app.log"
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    if sys.stderr is not None:  # stderr is None in a windowed PyInstaller build
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        root.addHandler(console)

    logging.getLogger(__name__).info("---- Application started ----")
    return log_file


def _show_error_dialog(exc_type, exc_value):
    global _dialog_open
    from PyQt6.QtWidgets import QApplication, QMessageBox

    if QApplication.instance() is None or _dialog_open:
        return
    _dialog_open = True
    try:
        log_file = get_log_dir() / "app.log"
        QMessageBox.critical(
            None,
            "Unexpected Error",
            "Something went wrong, but your saved data is safe.\n\n"
            f"Error: {exc_type.__name__}: {exc_value}\n\n"
            f"Details were written to:\n{log_file}\n\n"
            "If this keeps happening, please send that file for support.",
        )
    finally:
        _dialog_open = False


def _excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.getLogger("crash").error(
        "Unhandled exception:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    )
    try:
        _show_error_dialog(exc_type, exc_value)
    except Exception:
        pass


def _thread_excepthook(args):
    _excepthook(args.exc_type, args.exc_value, args.exc_traceback)


def install_exception_hook():
    # With sys.excepthook set, PyQt6 reports errors raised inside slots here
    # instead of aborting the whole application.
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
