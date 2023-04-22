import sys
from PySide6.QtWidgets import QApplication
from dataclasses import dataclass
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QSize, QObject, Signal, QSizeF
from PySide6.QtGui import QPixmap, QPainter, QCursor, QColor, QScreen, QMouseEvent, QKeyEvent, QPen, QAction
from PySide6.QtWidgets import QLabel, QRubberBand, QApplication, QGraphicsScene, QGraphicsView, QToolBar, QPushButton, QToolButton
from PySide6.QtGui import QGuiApplication
from PIL import ImageQt, Image
from mss import ScreenShotError, mss
from loguru import logger

from theme import ThemeContainer


@dataclass
class ImageData:
    image: QPixmap
    position: QPoint


class Editor(QLabel):

    pinned = Signal(ImageData)
    saved = Signal(QPixmap)
    copied = Signal(QPixmap)

    def __init__(self, themer: ThemeContainer):
        super().__init__()

        self.themer = themer

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

        # 原始的图片
        self.original_pixmap = QPixmap()

        self.scene = QGraphicsScene(self)
        self.graphicsView = QGraphicsView(self.scene, self)

        # Floating toolbar
        toolbar = QToolBar(self)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #F3F3F3;
                border: 2px solid #007ACC;
            }
        """)
        self.action_cancel: QAction = toolbar.addAction(
            self.themer.get_icon("Quit"), "Cancel",
        )
        self.action_cancel.triggered.connect(self.close)
        self.action_cancel.setShortcut("Esc")

        self.action_pin: QAction = toolbar.addAction(
            self.themer.get_icon("Pin"), "Pin",
        )
        self.action_pin.triggered.connect(self.pin_result)

        self.action_save: QAction = toolbar.addAction(
            self.themer.get_icon("Save"), "Save as",
        )
        self.action_save.triggered.connect(self.save_result)

        self.action_copy: QAction = toolbar.addAction(
            self.themer.get_icon("CopyToClipboard"), "Copy",
        )
        self.action_copy.triggered.connect(self.copy_result)

        self.toolbar = toolbar
        self.toolbar.hide()

        self.themer.themeChanged.connect(self.update_toolbar_icons)

        self.selectionArea = QRect()
        self.dragging = False

    def update_toolbar_icons(self):
        self.action_cancel.setIcon(self.themer.get_icon("Quit"))
        self.action_pin.setIcon(self.themer.get_icon("Pin"))
        self.action_save.setIcon(self.themer.get_icon("Save"))
        self.action_copy.setIcon(self.themer.get_icon("CopyToClipboard"))

    def edit_new_capture(self, pixmap: QPixmap):
        logger.debug('editor.new_capture')
        self.original_pixmap = pixmap
        # self.setPixmap(pixmap)

        self.scene.clear()
        self.setPixmap(self.original_pixmap)
        self.setFixedSize(
            self.original_pixmap.deviceIndependentSize().toSize(),
        )

        self.showFullScreen()
        self.toolbar.show()
        self.update_toolbar()
        self.adjust_toolbar_position()
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        pass

    def get_result(self) -> QPixmap:
        area = self.selectionArea.normalized()
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        dpr = self.original_pixmap.devicePixelRatioF()

        topLeft = (
            area.topLeft().toPointF() * dpr - screen_geometry.topLeft().toPointF()
        ).toPoint()
        size = QSizeF(area.width() * dpr, area.height() * dpr).toSize()
        pixmap_area = QRectF(topLeft, size).toRect()
        screenshot = self.original_pixmap.copy(pixmap_area)
        return screenshot

    def pin_result(self):
        area = self.selectionArea.normalized()
        self.pinned.emit(ImageData(
            image=self.get_result(),
            position=area.topLeft(),
        ))
        self.close()

    def copy_result(self):
        self.copied.emit(self.get_result())
        self.close()

    def save_result(self):
        self.saved.emit(self.get_result())
        # self.close()

    def closeEvent(self, event):
        self.toolbar.hide()
        self.scene.clear()
        self.original_pixmap = QPixmap()
        self.selectionArea = QRect()
        self.dragging = False
        self.hide()
        return event.ignore()

    def update_toolbar(self):
        area = self.selectionArea.normalized()
        if area.isEmpty():
            self.toolbar.hide()
            return

        if not self.toolbar.isVisible():
            self.toolbar.show()
        self.action_copy.setEnabled(not area.isEmpty())
        self.action_save.setEnabled(not area.isEmpty())
        self.action_pin.setEnabled(not area.isEmpty())
        self.adjust_toolbar_position()

    def adjust_toolbar_position(self):
        # when there's a valid selection area, put the toolbar:
        #  - if there's enough space below the selection area, below the selection area (to the left)
        #  - else: on the bottom line of selection area (also to the left)
        area = self.selectionArea.normalized()

        toolbarTopLeft = area.bottomLeft()
        # toolbarTopLeft.setX(toolbarTopLeft.x() - 2)  # border width is 2px
        if toolbarTopLeft.y() + self.toolbar.height() > self.height():
            toolbarTopLeft.setY(area.bottomLeft().y() - self.toolbar.height())
        self.toolbar.move(toolbarTopLeft)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        # Save current pen for later use
        original_pen = painter.pen()
        # Draw a dimmed effect over the whole screenshot
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        # If there's a valid selected area, draw that part of the screenshot without dimmed effect
        area = self.selectionArea.normalized()
        if not area.isEmpty():
            painter.drawPixmap(
                area.topLeft(),
                self.original_pixmap,
                QRectF(
                    area.topLeft().toPointF() * self.original_pixmap.devicePixelRatioF(),
                    area.size().toSizeF() * self.original_pixmap.devicePixelRatioF(),
                ).toRect()
            )
            # 007ACC to RGB is 0, 122, 204
            selectionBorderPen = QPen(QColor(0, 122, 204, 255), 2)
            painter.setPen(selectionBorderPen)
            painter.drawRect(area)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.selectionArea.normalized().isEmpty():
            logger.debug('drag.start @({x}, {y})', x=event.x(), y=event.y())
            self.dragging = True
            self.selectionArea.setTopLeft(event.position().toPoint())
            # self.update()
            # self.update_toolbar()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            self.selectionArea.setBottomRight(event.position().toPoint())
            # area = self.selectionArea.normalized()
            # logger.debug(
            #     'drag.drag topLeft=({x}, {y}) size=({w}, {h})',
            #     x=area.x(), y=area.y(),
            #     w=area.width(), h=area.height(),
            # )
            self.update()
            self.update_toolbar()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.dragging and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.selectionArea.setBottomRight(event.position().toPoint())
            self.update()
            self.update_toolbar()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


if __name__ == '__main__':
    from tray_icon import TrayIcon

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    capturer = mss()
    data: ScreenShotError = capturer.grab(capturer.monitors[0])
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

    themer = ThemeContainer()
    editor = Editor(themer)
    editor.edit_new_capture(pixmap)
    sys.exit(app.exec())
