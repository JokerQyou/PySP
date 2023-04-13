from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QPixmap
from capture_widget import CaptureWidget
from image import ImageLabel


class TrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.setIcon(QIcon("icon.png"))

        self.menu = QMenu()
        self.capture_action = QAction("Capture", self)
        self.capture_action.triggered.connect(self.start_capture)
        self.menu.addAction(self.capture_action)

        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

        self.setContextMenu(self.menu)

        self.activated.connect(self.start_capture)

        self.images = []

    def start_capture(self):
        self.capture_widget = CaptureWidget()
        self.capture_widget.captured.connect(self.handle_new_capture)
        self.capture_widget.showFullScreen()

    def handle_new_capture(self, img: QPixmap):
        # self.capture_widget.destroy()
        print('new captured image!')
        print(img.width(), 'x', img.height())
        image = ImageLabel(img)
        self.images.append(image)
        image.destroyed.connect(lambda _: self.images.remove(image))
        image.show()
