from PySide6.QtCore import Qt, QPoint, QSizeF
from PySide6.QtWidgets import QLabel, QGraphicsDropShadowEffect, QMenu, QApplication, QFileDialog
from PySide6.QtGui import QPixmap, QAction, QMouseEvent, QClipboard, QWheelEvent, QCursor
from loguru import logger


class ImageLabel(QLabel):
    def __init__(self, img: QPixmap, pos: QPoint, parent=None):
        super().__init__(parent)
        self.original_pixmap = img
        self.setPixmap(img)
        self.setFixedSize(img.deviceIndependentSize().toSize())
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setBlurRadius(10)
        shadow.setOffset(1)
        self.setGraphicsEffect(shadow)

        # 用于记录拖动时的鼠标位置
        self.mouse_offset = QPoint()
        self.move(pos)

    def mousePressEvent(self, event: QMouseEvent):
        self.raise_()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_offset = event.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.mouse_offset)

    def show_context_menu(self, event: QMouseEvent):
        menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_image)
        menu.addAction(copy_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_image)
        menu.addAction(save_action)

        if self.size() != self.original_pixmap.deviceIndependentSize().toSize():
            reset_zoom_action = QAction("Reset Zoom", self)
            reset_zoom_action.triggered.connect(self.reset_zoom)
            menu.addAction(reset_zoom_action)

        destroy_action = QAction("Destroy", self)
        destroy_action.triggered.connect(self.destroy_image)
        menu.addAction(destroy_action)

        menu.exec(event.globalPos())

    def copy_image(self):
        QApplication.clipboard().setPixmap(self.pixmap(), mode=QClipboard.Mode.Clipboard)

    def destroy_image(self):
        logger.debug('shot.destroy')
        self.close()
        self.deleteLater()

    def wheelEvent(self, event: QWheelEvent):
        top_widget = QApplication.widgetAt(QCursor.pos())
        if top_widget is not self or event.angleDelta().y() == 0:
            return event.ignore

        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        logger.debug(
            'shot.zoom, delta_y={y}, zoom_factor={zf}, current_size=({cw}, {ch})',
            y=event.angleDelta().y(),
            zf=zoom_factor,
            cw=self.size().width(),
            ch=self.size().height(),
        )
        new_size = QSizeF(self.size()) * zoom_factor
        new_pixmap = self.original_pixmap.scaled(
            (new_size * self.devicePixelRatioF()).toSize(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        top_widget.setPixmap(new_pixmap)
        top_widget.setFixedSize(new_pixmap.deviceIndependentSize().toSize())
        # top_widget.adjustSize()

        # Adjust the position of the window based on the zoom factor and the cursor position.
        cursor_pos_in_widget = event.position()
        widget_top_left = top_widget.pos()
        new_pos = widget_top_left + (
            cursor_pos_in_widget * (1 - zoom_factor)
        ).toPoint()
        top_widget.move(new_pos)

    def reset_zoom(self):
        self.setPixmap(self.original_pixmap)
        self.setFixedSize(
            self.original_pixmap.deviceIndependentSize().toSize()
        )
        logger.debug(
            'shot.zoom.reset, new_size=({w}, {h})',
            w=self.size().width(),
            h=self.size().height(),
        )
        # self.adjustSize()

    def save_image(self):
        selected = QFileDialog.getSaveFileName(
            self, "Save image as",
            filter="PNG image (*.png)", selectedFilter="PNG image (*.png)",
        )
        print(selected)
        if len(selected) > 0 and selected[0] != '':
            self.original_pixmap.save(selected[0], "png")
