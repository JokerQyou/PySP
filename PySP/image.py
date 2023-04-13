from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QLabel, QGraphicsDropShadowEffect, QMenu, QApplication
from PySide6.QtGui import QPixmap, QAction, QMouseEvent, QClipboard


class ImageLabel(QLabel):
    def __init__(self, img: QPixmap, parent=None):
        super().__init__(parent)
        self.setPixmap(img)
        self.setFixedSize(img.deviceIndependentSize().toSize())
        # self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setBlurRadius(10)
        shadow.setOffset(1)
        self.setGraphicsEffect(shadow)

        # 用于记录拖动时的鼠标位置
        self.mouse_offset = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
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

        destroy_action = QAction("Destroy", self)
        destroy_action.triggered.connect(self.destroy_image)
        menu.addAction(destroy_action)

        menu.exec(event.globalPos())

    def copy_image(self):
        QApplication.clipboard().setPixmap(self.pixmap(), mode=QClipboard.Mode.Clipboard)

    def destroy_image(self):
        self.close()
