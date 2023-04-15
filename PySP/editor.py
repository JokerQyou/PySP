from dataclasses import dataclass
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QObject, Signal, QSizeF
from PySide6.QtGui import QPixmap, QPainter, QCursor, QColor, QScreen, QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QLabel, QRubberBand, QApplication
from loguru import logger

from rubber_band import BorderedRubberBand


@dataclass
class ImageData:
    image: QPixmap
    position: QPoint


class Editor(QLabel):

    edited = Signal(ImageData)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(
            self.windowState()
            | Qt.WindowState.WindowFullScreen
        )

        self.rubber_band = BorderedRubberBand(
            QRubberBand.Shape.Rectangle, self
        )
        self.origin = QPoint()
        self.dragging = False
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setVisible(False)
        self.original_pixmap = QPixmap()

    def edit_new_capture(self, pixmap: QPixmap):
        logger.debug('editor.new_capture')
        self.original_pixmap = pixmap
        self.origin = QPoint()
        self.setPixmap(pixmap)
        self.showFullScreen()
        pass

    def keyPressEvent(self, ev: QKeyEvent) -> None:
        if ev.key() == Qt.Key.Key_Escape:
            self.close()
            return ev.ignore()
        return super().keyPressEvent(ev)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.dragging = True
            logger.debug(
                'snap.drag.start @({x}, {y})', x=self.origin.x(), y=self.origin.y(),
            )
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.rubber_band.setGeometry(QRect.span(self.origin, event.pos()))

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()

            topLeft = (
                self.rubber_band.pos().toPointF() * self.rubber_band.devicePixelRatioF() -
                screen_geometry.topLeft().toPointF()
            )  .toPoint()
            size = QSizeF(
                self.rubber_band.width() * self.rubber_band.devicePixelRatioF(),
                self.rubber_band.height() * self.rubber_band.devicePixelRatioF(),
            ).toSize()
            logger.debug(
                'shot.drag.end, size=({w}*{h})', w=size.width(), h=size.height())
            area = QRect(topLeft, size).normalized()
            self.rubber_band.hide()
            screenshot = self.original_pixmap.copy(area)

            data = ImageData(
                screenshot,
                (topLeft.toPointF() / self.rubber_band.devicePixelRatioF()).toPoint()
            )
            self.close()
            self.edited.emit(data)
