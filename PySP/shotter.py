from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap, QGuiApplication
from typing import Optional, Any
from mss import mss
from mss.models import Monitor
from mss.screenshot import ScreenShot
from loguru import logger

from PIL import ImageQt, Image


class SimpleScreenShot(ScreenShot):
    def __init__(self, data: bytearray, monitor: Monitor, **_: Any) -> None:
        self.data = data
        self.monitor = monitor


class Shotter (QObject):

    captured = Signal(QPixmap)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.capturer = mss()
        # self.capturer.cls_image = SimpleScreenShot

    def take(self):
        data: ScreenShot = self.capturer.grab(self.capturer.monitors[0])
        image = ImageQt.ImageQt(
            Image.frombytes('RGB', data.size, data.bgra, 'raw', 'BGRX')
        )
        logger.debug(
            'shot.new raw_image_size={}, data_valid={}',
            data.size,
            not image.isNull(),
        )
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(
            QGuiApplication.primaryScreen().devicePixelRatio()
        )
        self.captured.emit(pixmap)
