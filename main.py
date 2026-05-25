from pathlib import Path
import os
import sys

# Force Qt to use safer software rendering on Windows demo machines before QApplication exists.
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_ANGLE_PLATFORM", "warp")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from _uiux.main_handler import MainWindow


ROOT = Path(__file__).resolve().parent


def _load_qss(app: QApplication) -> None:
    # Keep the uploaded stylesheet by default, but allow instant fallback during
    # debugging: set E2E_MOCK_DISABLE_QSS=1 before running python main.py.
    if os.environ.get("E2E_MOCK_DISABLE_QSS") == "1":
        return
    qss_path = ROOT / "assets" / "styles" / "kakao_talk_dark_v2.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    app = QApplication(sys.argv)
    app.setApplicationName("E2E GUI Mock Portfolio")
    _load_qss(app)
    win = MainWindow(project_root=ROOT)
    win.resize(1440, 880)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
