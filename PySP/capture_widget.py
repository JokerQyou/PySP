from PySide6.QtCore import Qt, QPoint, QRect, QSize, QObject, Signal, QSizeF
from PySide6.QtGui import QPixmap, QPainter, QCursor, QColor, QScreen, QMouseEvent
from PySide6.QtWidgets import QLabel, QRubberBand, QApplication

from rubber_band import BorderedRubberBand


class CaptureWidget(QLabel):

    captured = Signal(QPixmap)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(
            self.windowState()
            | Qt.WindowState.WindowFullScreen
        )

        self.rubber_band = BorderedRubberBand(QRubberBand.Shape.Line, self)
        self.origin = QPoint()
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()

            area = QRect(
                (
                    self.rubber_band.pos() * self.rubber_band.devicePixelRatioF() -
                    screen_geometry.topLeft()
                ),
                QSizeF(
                    self.rubber_band.width() * self.rubber_band.devicePixelRatioF(),
                    self.rubber_band.height() * self.rubber_band.devicePixelRatioF(),
                ).toSize()
            ).normalized()
            self.rubber_band.hide()
            screenshot = screen.grabWindow(0).copy(area)
            self.close()
            self.captured.emit(screenshot)
