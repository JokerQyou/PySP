from tray_icon import TrayIcon
from PySide6.QtWidgets import QApplication
import sys

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray_icon = TrayIcon()
    tray_icon.show()
    sys.exit(app.exec())
