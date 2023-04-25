from PySide6.QtCore import Qt, QPoint, QSizeF
from PySide6.QtWidgets import QLabel, QGraphicsDropShadowEffect, QMenu, QApplication, QFileDialog
from PySide6.QtGui import QPixmap, QAction, QMouseEvent, QClipboard, QWheelEvent, QCursor
from loguru import logger

from theme import ThemeContainer


class ImageLabel(QLabel):
    def __init__(self, img: QPixmap, pos: QPoint, themer: ThemeContainer, parent=None):
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
        self.setStyleSheet("QLabel{ border: 1px solid black; }")
        # self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, on=True)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setBlurRadius(10)
        shadow.setOffset(1)
        self.setGraphicsEffect(shadow)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 用于记录拖动时的鼠标位置
        self.mouse_offset = QPoint()
        self.move(pos)

        self.animations = []
        self.themer = themer

    def mousePressEvent(self, event: QMouseEvent):
        self.raise_()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_offset = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPos() - self.mouse_offset)
        super().mouseMoveEvent(event)

    def show_context_menu(self, pos: QPoint):
        menu = QMenu(self)

        copy_action = QAction(
            self.themer.get_icon('CopyToClipboard'), "Copy", self,
        )
        copy_action.triggered.connect(self.copy_image)
        menu.addAction(copy_action)

        save_action = QAction(
            self.themer.get_icon('Save'), "Save", self,
        )
        save_action.triggered.connect(self.save_image)
        menu.addAction(save_action)

        if self.size() != self.original_pixmap.deviceIndependentSize().toSize():
            reset_zoom_action = QAction(
                self.themer.get_icon('ZoomReset'), "Reset Zoom", self,
            )
            reset_zoom_action.triggered.connect(self.reset_zoom)
            menu.addAction(reset_zoom_action)

        destroy_action = QAction(
            self.themer.get_icon('Delete'), "Destroy", self,
        )
        destroy_action.triggered.connect(self.destroy_image)
        menu.addAction(destroy_action)

        menu.exec(self.mapToGlobal(pos))

    def copy_image(self):
        logger.debug('image.copy')
        QApplication.clipboard().setPixmap(self.pixmap(), mode=QClipboard.Mode.Clipboard)

    def destroy_image(self):
        logger.debug('image.destroy')
        self.close()
        self.deleteLater()

    def wheelEvent(self, event: QWheelEvent):
        top_widget = QApplication.widgetAt(QCursor.pos())
        if top_widget is not self or event.angleDelta().y() == 0:
            return event.ignore()

        # control + mouse wheel to adjust window opacity, up is more opaque, down is more transparent
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            opacity = self.windowOpacity()
            opacity += 0.05 if event.angleDelta().y() > 0 else -0.05
            opacity = max(0.05, min(1, opacity))
            self.setWindowOpacity(opacity)
            return event.accept()

        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_size = QSizeF(self.size()) * zoom_factor
        logger.debug(
            'image.zoom.{op}, delta_y={y}, zoom_factor={zf}, from={cw}*{ch}, to={nw}*{nh}',
            op='out'if zoom_factor < 1 else 'in',
            y=event.angleDelta().y(),
            zf=zoom_factor,
            cw=self.size().width(),
            ch=self.size().height(),
            nw=new_size.width(),
            nh=new_size.height(),
        )
        new_pixmap = self.original_pixmap.scaled(
            (new_size * self.devicePixelRatioF()).toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        cursor_pos_in_widget = event.position()
        self_pos = self.pos()
        new_pos = self_pos + (
            cursor_pos_in_widget * (1 - zoom_factor)
        ).toPoint()
        self.setPixmap(new_pixmap)
        self.setFixedSize(new_pixmap.deviceIndependentSize().toSize())
        self.move(new_pos)

    def reset_zoom(self):
        cursor_pos = QCursor.pos()
        self_pos = self.pos()
        cursor_pos_in_widget = cursor_pos - self_pos
        zoom_factor = float(
            self.original_pixmap.deviceIndependentSize().width()) / float(self.width())
        new_pos = self_pos + (
            cursor_pos_in_widget.toPointF() * (1 - zoom_factor)
        ).toPoint()
        logger.debug(
            'current_size={cw}*{ch}, new_size={nw}*{nh}, zoom_factor={zf}, cussor_in=({ciwx}, {ciwy}), new_pos=({nx}, {ny})',
            cw=self.width(),
            ch=self.height(),
            nw=self.original_pixmap.deviceIndependentSize().width(),
            nh=self.original_pixmap.deviceIndependentSize().height(),
            zf=zoom_factor,
            ciwx=cursor_pos_in_widget.x(),
            ciwy=cursor_pos_in_widget.y(),
            nx=new_pos.x(),
            ny=new_pos.y(),
        )
        self.setPixmap(self.original_pixmap)
        self.setFixedSize(
            self.original_pixmap.deviceIndependentSize().toSize()
        )
        self.move(new_pos)
        logger.debug(
            'image.zoom.reset, new_size=({w}*{h})',
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
