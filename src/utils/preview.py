"""
Preview helpers for checking the app on a developer machine.

HOSPITAL_SCREEN=1366x768
    Simulates the hospital PC's screen: every window that would open
    maximised opens at exactly this size instead, so you can see what fits
    and what gets cut off. The title bar shows "[Preview 1366x768]".

Has no effect unless the environment variable is set.
"""
import logging
import os

log = logging.getLogger(__name__)


def apply_screen_simulation():
    value = os.environ.get("HOSPITAL_SCREEN", "").lower().strip()
    if not value:
        return
    try:
        width, height = (int(x) for x in value.split("x"))
    except ValueError:
        log.warning("HOSPITAL_SCREEN=%r is not like 1366x768 - ignored", value)
        return

    from PyQt6.QtWidgets import QWidget

    def show_as_hospital_screen(self):
        # Windows reserves ~40px for the taskbar and ~30px for the title bar
        self.resize(width, height - 70)
        self.move(0, 0)
        if "[Preview" not in self.windowTitle():
            self.setWindowTitle(f"{self.windowTitle()}  [Preview {width}x{height}]")
        self.show()
        if self.width() > width or self.height() > height - 70:
            log.warning("'%s' needs %dx%d - larger than the %dx%d screen",
                        self.windowTitle(), self.width(), self.height(), width, height)

    QWidget.showMaximized = show_as_hospital_screen
    log.info("Screen simulation active: %dx%d", width, height)
